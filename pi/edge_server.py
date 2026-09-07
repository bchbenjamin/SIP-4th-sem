#!/usr/bin/env python3
"""
Raspberry Pi 5 edge server:
- Ingests frames from the laptop over WebSockets
- Runs YOLOv8 for detections
- Classifies Tier 1 vs Tier 2 threats
- Broadcasts annotated frames and logs to dashboard clients
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np
import requests
import websockets

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - defensive import
    YOLO = None


DEFAULT_TIER1 = {
    "person",
    "dog",
    "cat",
    "horse",
    "cow",
    "sheep",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
}
DEFAULT_TIER2 = {"car", "motorcycle", "bus", "truck", "train", "knife", "gun", "weapon"}


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]


@dataclass
class ThreatEvent:
    event_id: str
    ts_ms: int
    tier: str
    labels: List[str]
    max_confidence: float
    action: str
    latency_ms: int
    frame_id: int


def load_config(path: str) -> Dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class ThreatPolicy:
    def __init__(self, config: Dict):
        self.tier1_labels = {label.lower() for label in config.get("tier1_labels", DEFAULT_TIER1)}
        self.tier2_labels = {label.lower() for label in config.get("tier2_labels", DEFAULT_TIER2)}
        self.min_confidence = float(config.get("min_confidence", 0.45))
        self.cooldown_seconds = float(config.get("cooldown_seconds", 8))

        deterrence_cfg = config.get("deterrence", {})
        self.deterrence_mode = deterrence_cfg.get("mode", "siren")
        self.siren_file = deterrence_cfg.get("siren_file", "")

        alert_cfg = config.get("alert", {})
        self.webhook_url = alert_cfg.get("webhook_url", "")


class DeterrenceController:
    def __init__(self, mode: str, siren_file: str):
        self.mode = mode
        self.siren_file = siren_file

    def trigger(self, labels: List[str]) -> str:
        if self.mode == "siren" and self.siren_file and os.path.exists(self.siren_file):
            logging.info("Deterrence siren triggered for %s", ", ".join(labels))
            # Execute actual audio playback on Raspberry Pi
            os.system(f"aplay {self.siren_file} &")
        elif self.mode == "led":
            logging.info("Deterrence LED triggered for %s", ", ".join(labels))
        else:
            logging.info("Deterrence simulated for %s", ", ".join(labels))
        return self.mode


class AlertDispatcher:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, event: ThreatEvent) -> bool:
        if not self.webhook_url:
            logging.info("Alert webhook not configured; skipping external alert")
            return False
        payload = {
            "source": "edge-pi-5",
            "event": asdict(event),
        }
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=3)
            response.raise_for_status()
            return True
        except Exception as exc:  # pragma: no cover - network variability
            logging.warning("Alert dispatch failed: %s", exc)
            return False


class YoloDetector:
    def __init__(self, model_path: str, imgsz: int, conf: float):
        self.model_path = model_path
        self.imgsz = imgsz
        self.conf = conf
        self.enabled = YOLO is not None
        self.model = YOLO(model_path) if self.enabled else None

    def infer(self, frame) -> Tuple[np.ndarray, List[Detection]]:
        if not self.enabled or self.model is None:
            annotated = frame.copy()
            cv2.putText(
                annotated,
                "YOLO UNAVAILABLE",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )
            return annotated, []

        results = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf, verbose=False)
        result = results[0]
        annotated = result.plot()

        detections: List[Detection] = []
        if result.boxes is not None and result.boxes.cls is not None:
            xyxy = result.boxes.xyxy
            cls_list = result.boxes.cls
            conf_list = result.boxes.conf

            try:
                xyxy = xyxy.cpu().numpy()
                cls_list = cls_list.cpu().numpy()
                conf_list = conf_list.cpu().numpy()
            except Exception:
                xyxy = np.array(xyxy)
                cls_list = np.array(cls_list)
                conf_list = np.array(conf_list)

            for box, cls_id, conf in zip(xyxy.tolist(), cls_list.tolist(), conf_list.tolist()):
                label = self.model.names.get(int(cls_id), str(cls_id))
                detections.append(
                    Detection(
                        label=label,
                        confidence=float(conf),
                        bbox=(int(box[0]), int(box[1]), int(box[2]), int(box[3])),
                    )
                )

        return annotated, detections


class EdgeCore:
    def __init__(self, policy: ThreatPolicy, detector: YoloDetector):
        self.policy = policy
        self.detector = detector
        self.deterrence = DeterrenceController(policy.deterrence_mode, policy.siren_file)
        self.alerts = AlertDispatcher(os.environ.get("ALERT_WEBHOOK_URL", policy.webhook_url))

        self.dashboard_clients: set = set()
        self.frame_queue: asyncio.Queue = asyncio.Queue(maxsize=2)
        self.logs: Deque[ThreatEvent] = deque(maxlen=200)

        self.latest_frame_message: Optional[str] = None
        self.last_event_ms = 0

        self.frame_counter = 0
        self.fps_window_start = time.time()
        self.current_fps = 0

    async def handler(self, websocket):
        """Route connections by path: /ingest for sensor data, / for dashboard."""
        path = "/"
        if hasattr(websocket, "request") and hasattr(websocket.request, "path"):
            path = websocket.request.path

        if path == "/ingest":
            await self.ingest_handler(websocket)
        else:
            await self.dashboard_handler(websocket)

    async def ingest_handler(self, websocket):
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue
            if data.get("type") != "frame":
                continue
            try:
                self._enqueue_frame(data)
            except Exception as exc:
                logging.warning("Failed to enqueue frame: %s", exc)

    async def dashboard_handler(self, websocket):
        self.dashboard_clients.add(websocket)
        try:
            if self.latest_frame_message:
                await websocket.send(self.latest_frame_message)
            for event in list(self.logs)[-20:]:
                await websocket.send(
                    json.dumps({"type": "log", "event": asdict(event)}, separators=(",", ":"))
                )
            async for _ in websocket:
                pass
        finally:
            self.dashboard_clients.discard(websocket)

    def _enqueue_frame(self, packet: Dict) -> None:
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self.frame_queue.put_nowait(packet)

    async def processor_loop(self) -> None:
        while True:
            packet = await self.frame_queue.get()
            frame_id = int(packet.get("frame_id", 0))
            source_ts_ms = int(packet.get("ts_ms", 0))
            jpeg_b64 = packet.get("jpeg_b64", "")

            try:
                frame = self._decode_frame(jpeg_b64)
            except Exception as exc:
                logging.warning("Frame decode failed: %s", exc)
                continue

            annotated, detections = self.detector.infer(frame)
            tier, tier_labels, max_conf = self._classify(detections)

            now_ms = int(time.time() * 1000)
            latency_ms = now_ms - source_ts_ms if source_ts_ms else 0

            self.frame_counter += 1
            self._update_fps()

            if tier and self._cooldown_passed(now_ms):
                action = self.deterrence.trigger(tier_labels) if tier == "tier1" else "alert"
                event = ThreatEvent(
                    event_id=f"evt-{now_ms}",
                    ts_ms=now_ms,
                    tier=tier,
                    labels=tier_labels,
                    max_confidence=max_conf,
                    action=action,
                    latency_ms=latency_ms,
                    frame_id=frame_id,
                )
                if tier == "tier2":
                    self.alerts.send(event)
                self.logs.append(event)
                await self._broadcast({"type": "log", "event": asdict(event)})
                self.last_event_ms = now_ms

            frame_message = self._build_frame_message(annotated, latency_ms, frame_id)
            self.latest_frame_message = frame_message
            await self._broadcast_raw(frame_message)

    def _decode_frame(self, jpeg_b64: str) -> np.ndarray:
        jpeg_bytes = base64.b64decode(jpeg_b64)
        data = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Empty frame")
        return frame

    def _classify(self, detections: List[Detection]) -> Tuple[Optional[str], List[str], float]:
        tier2_hits = [d for d in detections if d.confidence >= self.policy.min_confidence and d.label.lower() in self.policy.tier2_labels]
        tier1_hits = [d for d in detections if d.confidence >= self.policy.min_confidence and d.label.lower() in self.policy.tier1_labels]

        if tier2_hits:
            labels = sorted({d.label for d in tier2_hits})
            max_conf = max(d.confidence for d in tier2_hits)
            return "tier2", labels, max_conf
        if tier1_hits:
            labels = sorted({d.label for d in tier1_hits})
            max_conf = max(d.confidence for d in tier1_hits)
            return "tier1", labels, max_conf
        return None, [], 0.0

    def _cooldown_passed(self, now_ms: int) -> bool:
        return (now_ms - self.last_event_ms) >= int(self.policy.cooldown_seconds * 1000)

    def _update_fps(self) -> None:
        window = time.time() - self.fps_window_start
        if window >= 1.0:
            self.current_fps = int(self.frame_counter / window)
            self.frame_counter = 0
            self.fps_window_start = time.time()

    def _build_frame_message(self, frame, latency_ms: int, frame_id: int) -> str:
        ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if not ok:
            raise RuntimeError("Failed to encode annotated frame")
        b64 = base64.b64encode(buffer).decode("ascii")
        payload = {
            "type": "frame",
            "frame_id": frame_id,
            "annotated_b64": b64,
            "latency_ms": latency_ms,
            "fps": self.current_fps,
        }
        return json.dumps(payload, separators=(",", ":"))

    async def _broadcast(self, payload: Dict) -> None:
        message = json.dumps(payload, separators=(",", ":"))
        await self._broadcast_raw(message)

    async def _broadcast_raw(self, message: str) -> None:
        if not self.dashboard_clients:
            return
        to_remove = []
        coros = []
        for client in self.dashboard_clients:
            coros.append(client.send(message))
        results = await asyncio.gather(*coros, return_exceptions=True)
        for client, result in zip(list(self.dashboard_clients), results):
            if isinstance(result, Exception):
                to_remove.append(client)
        for client in to_remove:
            self.dashboard_clients.discard(client)


async def run_servers(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    policy = ThreatPolicy(config)
    detector = YoloDetector(args.model, args.imgsz, args.conf)
    core = EdgeCore(policy, detector)

    async with websockets.serve(
        core.handler,
        args.host,
        args.port,
        max_size=2**24,
        ping_interval=20,
        ping_timeout=20,
    ):
        logging.info(
            "Edge server on ws://%s:%s  (ingest: /ingest  dashboard: /)",
            args.host,
            args.port,
        )
        await core.processor_loop()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Edge inference and broadcast server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=8766, help="WebSocket port (routes /ingest and / on same port)")
    parser.add_argument("--model", default="yolov8n.pt", help="YOLOv8 model path")
    parser.add_argument("--imgsz", type=int, default=640, help="YOLO inference size")
    parser.add_argument("--conf", type=float, default=0.4, help="YOLO confidence threshold")
    parser.add_argument("--config", default="config.json", help="Threat policy config path")
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    args = build_arg_parser().parse_args()
    try:
        asyncio.run(run_servers(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
