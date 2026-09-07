#!/usr/bin/env python3
"""
Autonomous weapon detection training script for Raspberry Pi 5.
Designed to run as a systemd service — autostart on boot, crash recovery, Telegram notifications.
Maximizes CPU and memory usage.
"""

import os
import sys
import traceback
import subprocess
import time

HOME = os.path.expanduser("~")
VENV_PYTHON = os.path.join(HOME, "edge-ai", "pi", ".venv", "bin", "python3")
UNIFIED_DATASET = os.path.join(HOME, "edge-ai", "unified_weapon_dataset", "data.yaml")
FALLBACK_DATASET = os.path.join(HOME, "gun-and-knife-detection-1", "data.yaml")
CHECKPOINT = os.path.join(HOME, "runs", "detect", "train", "weights", "last.pt")
NOTIFY_SCRIPT = os.path.join(HOME, "edge-ai", "telegram_notify.py")

# Add edge-ai to path for telegram_notify
sys.path.insert(0, os.path.join(HOME, "edge-ai"))


def notify(cmd, *args):
    """Send a Telegram notification."""
    try:
        subprocess.run(
            [VENV_PYTHON, NOTIFY_SCRIPT, cmd] + list(args),
            timeout=30, check=False,
            cwd=HOME
        )
    except Exception:
        pass


def prepare_datasets():
    """Download and merge datasets if unified dataset doesn't exist."""
    if os.path.exists(UNIFIED_DATASET):
        print(f"Unified dataset already exists at {UNIFIED_DATASET}")
        return UNIFIED_DATASET

    print("Unified dataset not found. Running download_and_merge.py...")
    merge_script = os.path.join(HOME, "edge-ai", "download_and_merge.py")
    if os.path.exists(merge_script):
        try:
            subprocess.run(
                [VENV_PYTHON, merge_script],
                timeout=7200,  # 2 hour timeout
                check=True,
                cwd=HOME
            )
        except Exception as e:
            print(f"Merge script failed: {e}")

    if os.path.exists(UNIFIED_DATASET):
        return UNIFIED_DATASET
    elif os.path.exists(FALLBACK_DATASET):
        print(f"Falling back to original dataset: {FALLBACK_DATASET}")
        return FALLBACK_DATASET
    else:
        raise FileNotFoundError("No dataset found!")


def train():
    """Run YOLOv8 training with maximum resource usage."""
    from ultralytics import YOLO

    # Determine dataset
    data_yaml = prepare_datasets()
    print(f"Using dataset: {data_yaml}")

    # Determine model — resume from checkpoint or start fresh
    if os.path.exists(CHECKPOINT):
        print(f"Resuming from checkpoint: {CHECKPOINT}")
        model = YOLO(CHECKPOINT)
        resume = True
    else:
        print("Starting fresh with yolov8n.pt")
        model = YOLO("yolov8n.pt")
        resume = False

    notify("start", f"Using dataset: {data_yaml}\nResume: {resume}")

    # Train with MAXIMUM resource usage
    # RPi5 has 4 cores and 4GB RAM
    try:
        model.train(
            data=data_yaml,
            epochs=50,
            batch=4,            # Doubled from 2 — uses more RAM
            imgsz=416,          # Larger images for better accuracy
            device="cpu",
            workers=4,          # Use ALL 4 CPU cores for data loading
            save_period=5,      # Checkpoint every 5 epochs
            project="runs/detect",
            name="train",
            exist_ok=True,
            resume=resume,
            patience=0,        # Don't early-stop — train all epochs
            cache=True,        # Cache images in RAM for speed
            plots=True,        # Generate results.png
            verbose=True,
        )
        notify("complete")
        print("Training complete!")

    except RuntimeError as e:
        if "out of memory" in str(e).lower() or "oom" in str(e).lower():
            print(f"OOM with batch=4/imgsz=416, falling back to batch=2/imgsz=320...")
            notify("crash", f"OOM — retrying with smaller batch.\n{str(e)[:200]}")

            # Retry with smaller settings
            if os.path.exists(CHECKPOINT):
                model = YOLO(CHECKPOINT)
                resume = True
            else:
                model = YOLO("yolov8n.pt")
                resume = False

            model.train(
                data=data_yaml,
                epochs=50,
                batch=2,
                imgsz=320,
                device="cpu",
                workers=4,
                save_period=5,
                project="runs/detect",
                name="train",
                exist_ok=True,
                resume=resume,
                patience=0,
                cache=False,
                plots=True,
                verbose=True,
            )
            notify("complete")
        else:
            raise


def main():
    try:
        train()
    except Exception as e:
        tb = traceback.format_exc()
        print(f"FATAL: {e}\n{tb}", file=sys.stderr)
        notify("crash", tb[:500])
        sys.exit(1)


if __name__ == "__main__":
    main()
