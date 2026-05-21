#!/usr/bin/env python3
"""
Increment 1: Sensor and Acquisition Node (local, Windows-friendly).
- Captures webcam frames
- Simulates PIR + thermal telemetry
- Streams frames + telemetry via WebSocket on port 8000
"""

import argparse
import asyncio
import base64
import json
import platform
import threading
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np
import websockets


class ThermalSimulator:
    def __init__(self, height: int = 24, width: int = 32) -> None:
        self.height = height
        self.width = width
        self._lock = threading.Lock()
        self._pir_motion = False
        self._ambient_c = 26.0
        self._max_c = 26.0
        self._matrix: List[List[float]] = [
            [self._ambient_c for _ in range(self.width)] for _ in range(self.height)
        ]
        self._last_update = time.time()

    def update(self, matrix: np.ndarray, ambient_c: float, max_c: float, pir_motion: bool) -> None:
        with self._lock:
            self._matrix = matrix.tolist()
            self._ambient_c = float(ambient_c)
            self._max_c = float(max_c)
            self._pir_motion = bool(pir_motion)
            self._last_update = time.time()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "pir_motion": self._pir_motion,
                "ambient_c": self._ambient_c,
                "max_c": self._max_c,
                "thermal_c": [row[:] for row in self._matrix],
                "ts_ms": int(self._last_update * 1000),
            }


class FrameGrabber(threading.Thread):
    def __init__(
        self,
        camera_index: int,
        width: int,
        height: int,
        fps: float,
    ) -> None:
        super().__init__(daemon=True)
        self._camera_index = camera_index
        self._width = width
        self._height = height
        self._fps = fps
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_ts_ms = 0
        self._stop_event = threading.Event()

    def _open_capture(self) -> cv2.VideoCapture:
        if platform.system() == "Windows":
            cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(self._camera_index)
        return cap

    def run(self) -> None:
        cap = self._open_capture()
        if not cap.isOpened():
            print("ERROR: Could not open webcam. Check camera permissions.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        cap.set(cv2.CAP_PROP_FPS, self._fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        frame_interval = 1.0 / max(self._fps, 1.0)
        while not self._stop_event.is_set():
            ok, frame = cap.read()
            if ok:
                with self._lock:
                    self._latest_frame = frame
                    self._latest_ts_ms = int(time.time() * 1000)
            time.sleep(frame_interval)

        cap.release()

    def stop(self) -> None:
        self._stop_event.set()

    def get_frame(self) -> Tuple[Optional[np.ndarray], int]:
        with self._lock:
            if self._latest_frame is None:
                return None, 0
            return self._latest_frame.copy(), self._latest_ts_ms


def simulate_telemetry(sim: ThermalSimulator, stop_event: threading.Event, interval: float) -> None:
    rng = np.random.default_rng()
    t0 = time.time()
    height = sim.height
    width = sim.width
    y, x = np.mgrid[0:height, 0:width]

    while not stop_event.is_set():
        t = time.time() - t0
        ambient = 26.0 + 1.2 * np.sin(t / 15.0)
        noise = rng.normal(0.0, 0.35, (height, width))
        cx = int((np.sin(t / 7.0) + 1.0) * 0.5 * (width - 1))
        cy = int((np.cos(t / 9.0) + 1.0) * 0.5 * (height - 1))
        sigma = 4.0
        hotspot = np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * sigma**2)) * 7.5
        temps = ambient + noise + hotspot
        max_c = float(temps.max())
        pir_motion = max_c > ambient + 4.0 and rng.random() > 0.15

        sim.update(temps, ambient, max_c, pir_motion)
        stop_event.wait(interval)


def encode_jpeg(frame: np.ndarray, quality: int) -> str:
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
    ok, buffer = cv2.imencode(".jpg", frame, encode_params)
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return base64.b64encode(buffer).decode("ascii")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local sensor node streaming over WebSockets.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="WebSocket port")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--width", type=int, default=640, help="Capture width")
    parser.add_argument("--height", type=int, default=360, help="Capture height")
    parser.add_argument("--fps", type=float, default=10.0, help="Frames per second")
    parser.add_argument("--quality", type=int, default=70, help="JPEG quality (0-100)")
    parser.add_argument("--telemetry-hz", type=float, default=2.0, help="Telemetry updates per second")
    return parser


async def stream_client(
    websocket: websockets.WebSocketServerProtocol,
    sim: ThermalSimulator,
    grabber: FrameGrabber,
    args: argparse.Namespace,
) -> None:
    frame_interval = 1.0 / max(args.fps, 1.0)
    telemetry_interval = 1.0 / max(args.telemetry_hz, 0.5)
    last_frame = 0.0
    last_telemetry = 0.0

    try:
        while True:
            now = time.time()
            if now - last_frame >= frame_interval:
                frame, ts_ms = grabber.get_frame()
                if frame is not None:
                    jpeg_b64 = encode_jpeg(frame, args.quality)
                    payload = {
                        "type": "frame",
                        "ts_ms": ts_ms,
                        "jpeg_b64": jpeg_b64,
                        "width": frame.shape[1],
                        "height": frame.shape[0],
                    }
                    await websocket.send(json.dumps(payload, separators=(",", ":")))
                last_frame = now

            if now - last_telemetry >= telemetry_interval:
                telemetry = sim.snapshot()
                payload = {
                    "type": "telemetry",
                    "ts_ms": telemetry["ts_ms"],
                    "pir_motion": telemetry["pir_motion"],
                    "ambient_c": telemetry["ambient_c"],
                    "max_c": telemetry["max_c"],
                    "thermal_c": telemetry["thermal_c"],
                }
                await websocket.send(json.dumps(payload, separators=(",", ":")))
                last_telemetry = now

            await asyncio.sleep(0.01)
    except websockets.ConnectionClosed:
        return


async def run_server(args: argparse.Namespace) -> None:
    sim = ThermalSimulator()
    stop_event = threading.Event()
    telemetry_thread = threading.Thread(
        target=simulate_telemetry,
        args=(sim, stop_event, 1.0 / max(args.telemetry_hz, 0.5)),
        daemon=True,
    )
    telemetry_thread.start()

    grabber = FrameGrabber(args.camera, args.width, args.height, args.fps)
    grabber.start()

    async def handler(websocket: websockets.WebSocketServerProtocol):
        print(f"Client connected: {websocket.remote_address}")
        await stream_client(websocket, sim, grabber, args)
        print("Client disconnected")

    try:
        async with websockets.serve(
            handler,
            args.host,
            args.port,
            max_size=2**24,
            ping_interval=20,
            ping_timeout=20,
        ):
            print(f"Sensor node streaming on ws://{args.host}:{args.port}")
            await asyncio.Future()
    finally:
        stop_event.set()
        grabber.stop()


def main() -> None:
    args = build_parser().parse_args()
    try:
        asyncio.run(run_server(args))
    except KeyboardInterrupt:
        print("Shutting down sensor node...")


if __name__ == "__main__":
    main()
