#!/bin/bash
# Master setup script for Raspberry Pi 5 weapon detection training
# This script:
# 1. Copies all scripts into place
# 2. Downloads and merges datasets
# 3. Sets up systemd autostart service
# 4. Sets up cron job for Telegram progress updates every 30 min
# 5. Starts training immediately

set -e

EDGE_AI="$HOME/edge-ai"
VENV="$EDGE_AI/pi/.venv"
VENV_PYTHON="$VENV/bin/python3"
VENV_PIP="$VENV/bin/pip"
LOG_DIR="$EDGE_AI/logs"

mkdir -p "$LOG_DIR"

echo "=== [1/6] Activating venv and installing dependencies ==="
source "$VENV/bin/activate"
pip install --quiet kagglehub pyyaml 2>/dev/null || true

echo "=== [2/6] Running dataset download and merge ==="
cd "$HOME"
$VENV_PYTHON "$EDGE_AI/download_and_merge.py" 2>&1 | tee "$LOG_DIR/dataset.log"

echo "=== [3/6] Setting up systemd autostart service ==="
sudo tee /etc/systemd/system/weapon-training.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=Weapon Detection YOLOv8 Training
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=benjamin
WorkingDirectory=/home/benjamin
ExecStart=/home/benjamin/edge-ai/pi/.venv/bin/python3 /home/benjamin/edge-ai/train_autonomous.py
Restart=on-failure
RestartSec=120
StandardOutput=append:/home/benjamin/edge-ai/logs/train.log
StandardError=append:/home/benjamin/edge-ai/logs/train.log
Environment=HOME=/home/benjamin
Environment=PATH=/home/benjamin/edge-ai/pi/.venv/bin:/usr/local/bin:/usr/bin:/bin
# Maximize resources
Nice=-5
CPUWeight=200

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable weapon-training.service
echo "Systemd service enabled for autostart."

echo "=== [4/6] Setting up Telegram progress cron (every 30 min) ==="
# Remove any existing cron entries for this
crontab -l 2>/dev/null | grep -v "telegram_notify" > /tmp/crontab_clean || true
echo "*/30 * * * * /home/benjamin/edge-ai/pi/.venv/bin/python3 /home/benjamin/edge-ai/telegram_notify.py progress >> /home/benjamin/edge-ai/logs/telegram.log 2>&1" >> /tmp/crontab_clean
crontab /tmp/crontab_clean
rm -f /tmp/crontab_clean
echo "Cron job set: Telegram progress update every 30 minutes."

echo "=== [5/6] Increasing swap for better performance ==="
# Increase swap to 2GB for training headroom
if [ -f /etc/dphys-swapfile ]; then
    sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
    sudo systemctl restart dphys-swapfile || true
    echo "Swap increased to 2GB"
fi

echo "=== [6/6] Starting training NOW ==="
sudo systemctl start weapon-training.service
sleep 2
sudo systemctl status weapon-training.service --no-pager || true

echo ""
echo "============================================"
echo "  SETUP COMPLETE"
echo "  Training is running as a systemd service."
echo "  It will autostart on boot."
echo "  Telegram updates every 30 minutes."
echo "============================================"
