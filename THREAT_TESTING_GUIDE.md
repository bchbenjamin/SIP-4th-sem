# Threat Testing & Deterrence Guide

How to test and demonstrate the AI-Powered Street Safety Device's detection capabilities.

---

## What the Current Model Detects

The Raspberry Pi is training a custom YOLOv8 model on ~9,419 weapon images (guns + knives). Until that training completes, the base `yolov8n.pt` model is also available and recognises several threat-relevant classes from COCO:

| Class | Tier | Response |
|---|---|---|
| `knife` (COCO class 43) | **Tier 2 — Severe** | Triggers emergency alert |
| `dog`, `bear`, `elephant`, `zebra` | **Tier 1 — Deterrable** | Triggers deterrent siren/LED |
| `person` | Monitored | Logged, no automatic response unless combined with weapon |

---

## Testing with the Live System

With the full stack running (see [RUN_GUIDE.md](RUN_GUIDE.md)):

### Testing Tier 1 (Animal Detection)
Hold up a photo of a dog, bear, or elephant on your phone to the webcam. The Pi will classify it as Tier 1 and play `siren.wav` via the connected speaker.

### Testing Tier 2 (Weapon Detection)
Hold up a photo of a knife or gun. The Pi will classify it as a Tier 2 severe threat and dispatch a simulated alert (logged to console and dashboard).

### Checking Results
```bash
# On the Pi — watch real-time detections
tail -f ~/edge-ai/pi/server.log
```

The dashboard at `http://localhost:3000` shows the annotated video feed with bounding boxes and tier classifications.

---

## Generating the Siren Audio

If `siren.wav` doesn't exist on the Pi, generate it:

```bash
source ~/edge-ai/pi/.venv/bin/activate
python3 ~/edge-ai/pi/generate_siren.py
```

This creates an oscillating 880–440 Hz siren tone. When Tier 1 is triggered, the Pi executes `aplay siren.wav &`.

---

## Batch Testing (Video Files)

To test against pre-recorded video files:

```bash
source ~/edge-ai/pi/.venv/bin/activate
python3 ~/edge-ai/app_batch.py \
    --input-dir ~/edge-ai/test_videos \
    --output-dir ~/edge-ai/object-detection-using-webcam/screenshots
```

Any frame where confidence exceeds 0.6 is saved as an annotated PNG. Filename format: `<video>_frame<N>_conf<score>.png`.

---

## Remote Testing via Telegram

With the Telegram bot running, you can test detection from anywhere:

1. Send any image of a weapon to the bot from your phone.
2. The Pi runs YOLOv8 inference using the latest `best.pt` checkpoint.
3. The bot replies with the annotated image (bounding boxes + confidence scores) within seconds.

This works even while training is running in the background — inference is scheduled at low priority.

---

## Training a Custom Model

Training runs autonomously on the Pi. To monitor progress:

```bash
# Check current epoch
tail -n 5 ~/runs/detect/train/results.csv

# View full training log
tail -f ~/edge-ai/logs/train.log

# Check saved checkpoints
ls ~/runs/detect/train/weights/
```

Once training is complete, `best.pt` in `~/runs/detect/train/weights/` is automatically used by the edge server and the Telegram bot for inference.

To use the custom model in the live system, update `config.json` on the Pi:

```json
{
    "model_path": "/home/<user>/runs/detect/train/weights/best.pt"
}
```

Or restart the edge server pointing to the new weights:

```bash
pkill -f edge_server.py
nohup ~/edge-ai/pi/.venv/bin/python3 ~/edge-ai/pi/edge_server.py \
    --config ~/edge-ai/pi/config.json \
    --model ~/runs/detect/train/weights/best.pt \
    > ~/edge-ai/pi/server.log 2>&1 &
```
