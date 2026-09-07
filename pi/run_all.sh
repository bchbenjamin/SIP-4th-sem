#!/bin/bash

# Wait for pip install to finish
echo "Waiting for tensorflow to be installed..."
while ! bash -c "source ~/edge-ai/pi/.venv/bin/activate && python3 -c 'import tensorflow' &> /dev/null"; do
  sleep 10
done
echo "Tensorflow is installed!"

# Wait for download_media.py to finish
echo "Waiting for download_media.py to finish..."
while pgrep -f download_media.py > /dev/null; do
  sleep 10
done
echo "Downloads finished!"

echo "Starting tmux sessions..."
tmux new-session -d -s train "source ~/edge-ai/pi/.venv/bin/activate && python3 ~/edge-ai/train_weapon.py > ~/edge-ai/logs/train.log 2>&1"
tmux new-session -d -s video "source ~/edge-ai/pi/.venv/bin/activate && python3 ~/edge-ai/app_batch.py --input-dir ~/edge-ai/test_videos --output-dir ~/edge-ai/object-detection-using-webcam/screenshots > ~/edge-ai/logs/video.log 2>&1"
tmux new-session -d -s audio "source ~/edge-ai/pi/.venv/bin/activate && python3 ~/edge-ai/sound_event_batch.py --input-dir ~/edge-ai/test_audio --output-dir ~/edge-ai/Real-Time-Sound-Event-Detection/screenshots > ~/edge-ai/logs/audio.log 2>&1"
echo "All sessions started in tmux."
