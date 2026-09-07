#!/bin/bash
# Deployment script for weapon-bot

EDGE_AI="$HOME/edge-ai"
VENV="$EDGE_AI/pi/.venv"

echo "=== [1/3] Copying scripts ==="
mkdir -p "$EDGE_AI/logs"
mkdir -p "$EDGE_AI/bot_cache"

echo "=== [2/3] Setting up systemd service ==="
sudo tee /etc/systemd/system/weapon-bot.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=Weapon Detection Interactive Telegram Bot
After=network-online.target weapon-training.service
Wants=network-online.target

[Service]
Type=simple
User=benjamin
WorkingDirectory=/home/benjamin
ExecStart=/home/benjamin/edge-ai/pi/.venv/bin/python3 /home/benjamin/edge-ai/telegram_bot.py
Restart=always
RestartSec=10
StandardOutput=append:/home/benjamin/edge-ai/logs/bot.log
StandardError=append:/home/benjamin/edge-ai/logs/bot.log
Environment=HOME=/home/benjamin
Environment=PATH=/home/benjamin/edge-ai/pi/.venv/bin:/usr/local/bin:/usr/bin:/bin
# Lower priority so it doesn't starve training (training is Nice=-5)
Nice=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable weapon-bot.service

echo "=== [3/3] Restarting services ==="
sudo systemctl restart weapon-bot.service
sudo systemctl status weapon-bot.service --no-pager || true

echo "Interactive bot deployed!"
