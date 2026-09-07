#!/bin/bash
source ~/edge-ai/pi/.venv/bin/activate
echo "Reinstalling dependencies..."
pip install --force-reinstall tensorflow==2.14.0 sounddevice matplotlib scipy roboflow kagglehub --no-cache-dir

echo "Downloading media..."
python3 ~/edge-ai/download_media.py

echo "Launching autonomous tasks in tmux..."
tmux new-session -d -s train "source ~/edge-ai/pi/.venv/bin/activate && python3 ~/edge-ai/train_weapon.py > ~/edge-ai/logs/train.log 2>&1"
tmux new-session -d -s video "source ~/edge-ai/pi/.venv/bin/activate && python3 ~/edge-ai/app_batch.py --input-dir ~/edge-ai/test_videos --output-dir ~/edge-ai/object-detection-using-webcam/screenshots > ~/edge-ai/logs/video.log 2>&1"
tmux new-session -d -s audio "source ~/edge-ai/pi/.venv/bin/activate && python3 ~/edge-ai/sound_event_batch.py --input-dir ~/edge-ai/test_audio --output-dir ~/edge-ai/Real-Time-Sound-Event-Detection/screenshots > ~/edge-ai/logs/audio.log 2>&1"

echo "All autonomous sessions started."
