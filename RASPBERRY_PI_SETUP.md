# Raspberry Pi 5 Setup Guide

First-time setup guide for the Raspberry Pi 5 edge node in the SIP Prototype system.

---

## Prerequisites

- Raspberry Pi 5 (4GB) with power supply (27W USB-C)
- microSD card (≥32GB, Class 10 recommended)
- Network access (Ethernet recommended; Wi-Fi works)
- A laptop or phone to flash the SD card

---

## Step 1: Flash Raspberry Pi OS

### Option A: Raspberry Pi Imager (Easiest)
1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/) (Windows/Mac/Linux) or install the Android app from Google Play.
2. Select:
   - **OS:** Raspberry Pi OS Lite (64-bit) — no desktop needed
   - **Device:** Raspberry Pi 5
   - **Storage:** Your SD card
3. In the **Advanced Options** (gear icon), configure:
   - Hostname: `raspberrypi`
   - Enable SSH (password auth)
   - Set username/password
   - Configure Wi-Fi if not using Ethernet
4. Click **Write**.

### Option B: Termux on Rooted Android
```bash
# Install xz-utils as Termux user
pkg install xz-utils

# Download and decompress image (as Termux user — NOT root)
cd ~/storage/downloads
wget https://downloads.raspberrypi.org/raspios_lite_arm64/images/...img.xz
unxz *.img.xz

# Flash as root (find your SD card device first — NOT mmcblk0 which is phone storage)
su
ls /dev/block/sd* /dev/block/mmcblk1*   # Find SD card
dd if=/storage/emulated/0/Download/*.img of=/dev/block/sda bs=4M status=progress
sync
```

> **Critical:** Never write to `mmcblk0` — that is your phone's internal storage.

---

## Step 2: Boot and Find the Pi's IP

1. Insert SD card, connect Ethernet, power on.
2. Wait 60–90 seconds for first boot.
3. Find the IP:

```bash
# From your laptop
ping raspberrypi.local        # Linux/Mac
ping -4 raspberrypi.local     # Windows (force IPv4)
```

Or check your router's DHCP client list. The Pi's MAC address starts with `b8:27:eb`, `bc:a2:3b`, or `d8:3a:8e`.

4. SSH in:
```bash
ssh <username>@raspberrypi.local
# or: ssh <username>@<IP_ADDRESS>
```

---

## Step 3: System Setup

Run these on the Pi after SSH:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3-venv python3-pip libopenblas-dev libatlas-base-dev libgl1 git tmux

# Create project directory
mkdir -p ~/edge-ai
```

---

## Step 4: Copy Code to the Pi

From your laptop:

```bash
scp -r Prototype/pi <username>@raspberrypi.local:~/edge-ai/
```

Or use SFTP (WinSCP on Windows) to drag the `pi/` folder to `~/edge-ai/pi/` on the Pi.

---

## Step 5: Set Up Python Environment

On the Pi:

```bash
cd ~/edge-ai/pi
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Key packages installed: `ultralytics`, `opencv-python-headless`, `websockets`, `numpy`, `kagglehub`, `python-dotenv`

---

## Step 6: Configure Credentials

```bash
# Create .env with Telegram bot credentials
cat > ~/edge-ai/.env << EOF
BOT_TOKEN=<your_telegram_bot_token>
PRIMARY_CHAT_ID=<your_telegram_chat_id>
ALLOWED_CHAT_IDS=<comma_separated_chat_ids>
EOF
```

> Never commit `.env` to git — it's in `.gitignore`.

---

## Step 7: Set Up Autonomous Training (Systemd Services)

The training and Telegram bot run as systemd services that autostart on boot:

```bash
# Copy service files
sudo cp ~/edge-ai/pi/weapon-training.service /etc/systemd/system/
sudo cp ~/edge-ai/pi/weapon-bot.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable weapon-training.service weapon-bot.service
sudo systemctl start weapon-training.service weapon-bot.service
```

Check status:
```bash
sudo systemctl status weapon-training.service
sudo systemctl status weapon-bot.service
```

---

## Step 8: Configure Wi-Fi Priority (Optional)

The Pi uses NetworkManager. To add networks and set priority:

```bash
# Add a Wi-Fi network
sudo nmcli device wifi connect "Network_Name" password "password"

# Set priority (higher number = preferred)
sudo nmcli connection modify "TPLink_Network" connection.autoconnect-priority 100
sudo nmcli connection modify "Home_Network" connection.autoconnect-priority 50
sudo nmcli connection modify "Mobile_Hotspot" connection.autoconnect-priority 10

# View priorities
nmcli -f NAME,AUTOCONNECT-PRIORITY connection show
```

---

## Step 9: Update Dashboard Config

On your laptop, edit `dashboard/.env.local`:

```env
NEXT_PUBLIC_PI_WS_URL=ws://<PI_IP>:8766
```

And update `Prototype/.env`:

```env
IP_ADDRESS=<PI_IP>
USERNAME=<pi_username>
PASSWORD=<pi_password>
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ping raspberrypi.local` fails | Try by IP directly; check router DHCP table |
| SSH refused | Pi still booting — wait 90s and retry |
| `pip install` fails with OOM | Add `--no-cache-dir` flag; split large installs |
| Training OOM crash | Service auto-restarts with smaller batch=2, imgsz=320 — check logs with `journalctl -u weapon-training.service -n 50` |
| Telegram bot not responding | Check `sudo systemctl status weapon-bot.service`; verify `.env` has correct token and chat IDs |
| YOLOv8 import error | Activate venv first: `source ~/edge-ai/pi/.venv/bin/activate` |
