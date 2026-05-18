#!/usr/bin/env python3
"""
Laptop sensor node:
- Captures webcam frames
- Compresses to JPEG
- Streams to the Pi ingest WebSocket
"""

import argparse
import asyncio
import base64
import json
import time

import cv2
import websockets


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stream webcam frames to a Pi over WebSockets.")
    parser.add_argument("--pi-host", default="192.168.1.50", help="Pi host or IP address")
    parser.add_argument("--pi-port", type=int, default=8765, help="Pi ingest WebSocket port")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--width", type=int, default=640, help="Capture width")
    parser.add_argument("--height", type=int, default=360, help="Capture height")
    parser.add_argument("--fps", type=float, default=12.0, help="Frames per second")
    parser.add_argument("--quality", type=int, default=70, help="JPEG quality (0-100)")
    parser.add_argument("--preview", action="store_true", help="Show local preview window")
    parser.add_argument("--flip", action="store_true", help="Flip image horizontally")
    parser.add_argument(
        "--backend",
        choices=["auto", "dshow", "msmf"],
        default="auto",
        help="Camera backend (Windows only)",
    )
    return parser


def open_camera(index: int, backend: str) -> cv2.VideoCapture:
    if backend == "dshow":
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    elif backend == "msmf":
        cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
    else:
        cap = cv2.VideoCapture(index)
    return cap


def encode_jpeg(frame, quality: int) -> str:
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
    ok, buffer = cv2.imencode(".jpg", frame, encode_params)
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return base64.b64encode(buffer).decode("ascii")


def build_payload(frame_id: int, ts_ms: int, jpeg_b64: str) -> str:
    payload = {
        "type": "frame",
        "frame_id": frame_id,
        "ts_ms": ts_ms,
        "jpeg_b64": jpeg_b64,
    }
    return json.dumps(payload, separators=(",", ":"))


async def stream_frames(args: argparse.Namespace) -> None:
    uri = f"ws://{args.pi_host}:{args.pi_port}/ingest"
    cap = open_camera(args.camera, args.backend)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    frame_interval = 1.0 / max(args.fps, 1.0)
    frame_id = 0

    try:
        while True:
            try:
                async with websockets.connect(
                    uri,
                    max_size=2**24,
                    ping_interval=20,
                    ping_timeout=20,
                ) as ws:
                    print(f"Connected to {uri}")
                    while True:
                        start = time.time()
                        ok, frame = cap.read()
                        if not ok:
                            continue
                        if args.flip:
                            frame = cv2.flip(frame, 1)

                        ts_ms = int(time.time() * 1000)
                        frame_id += 1
                        jpeg_b64 = encode_jpeg(frame, args.quality)
                        await ws.send(build_payload(frame_id, ts_ms, jpeg_b64))

                        if args.preview:
                            cv2.imshow("Laptop Preview", frame)
                            if cv2.waitKey(1) & 0xFF == 27:
                                return

                        elapsed = time.time() - start
                        if elapsed < frame_interval:
                            await asyncio.sleep(frame_interval - elapsed)
            except KeyboardInterrupt:
                return
            except Exception as exc:
                print(f"Connection error: {exc}. Retrying in 2 seconds...")
                await asyncio.sleep(2)
    finally:
        cap.release()
        if args.preview:
            cv2.destroyAllWindows()


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    asyncio.run(stream_frames(args))


if __name__ == "__main__":
    main()
