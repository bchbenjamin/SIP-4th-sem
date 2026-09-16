# Street Safety Prototype: Run Guide

Authoritative start/stop reference for the AI-Powered Street Safety Device Network prototype.

---

## Network Reference

| Component | Value |
|---|---|
| Raspberry Pi IP | Stored in `.env` → `IP_ADDRESS` (typically `10.253.13.25` on campus subnet) |
| Pi edge server ingest port | `8765` |
| Pi dashboard broadcast port | `8766` |
| Laptop dashboard | `http://localhost:3000` |

To locate the Pi on a new network: `ping -4 -n 1 raspberrypi.local` (Windows) or `ping raspberrypi.local` (Linux/Mac).

---

## Starting the System

Start in this order. All three must be running for the full demo.

### 1. Start the Raspberry Pi Edge Server

SSH into the Pi from your laptop:

```bash
# Linux/Mac
ssh $USERNAME@$IP_ADDRESS

# Windows PowerShell
ssh $env:USERNAME@$env:IP_ADDRESS
```

Once connected, start the edge server in the background:

```bash
nohup ~/edge-ai/pi/.venv/bin/python3 ~/edge-ai/pi/edge_server.py \
    --config ~/edge-ai/pi/config.json \
    --model ~/edge-ai/pi/yolov8n.pt \
    > ~/edge-ai/pi/server.log 2>&1 &
```

Monitor the log:
```bash
tail -f ~/edge-ai/pi/server.log
```

Verify it's running:
```bash
ps aux | grep edge_server.py
```

### 2. Start the Next.js Dashboard

On your laptop:

```bash
cd Prototype/dashboard
npm run dev
```

Open **http://localhost:3000** in Chrome or Firefox. Allow microphone permissions when prompted.

### 3. Start the Laptop Camera Stream Client

In a separate terminal on your laptop:

```bash
cd Prototype
.venv/Scripts/python.exe laptop/stream_client.py --pi-host $PI_IP    # Windows
# or
.venv/bin/python3 laptop/stream_client.py --pi-host $PI_IP           # Linux/Mac
```

The Pi log will show `connection open` and begin printing YOLOv8 detections.

---

## Stopping the System

### Stop the Laptop Stream Client
Press `Ctrl+C` in the terminal running `stream_client.py`.

Or kill it by process:

```powershell
# Windows
Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%stream_client%'" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

### Stop the Dashboard
Press `Ctrl+C` in the terminal running `npm run dev`.

Or kill by port:

```powershell
# Windows
Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -Force
```

### Stop the Raspberry Pi Edge Server

Via SSH on the Pi:

```bash
pkill -f edge_server.py
```

Verify: `ps aux | grep edge_server.py` should return nothing.

---

## Autonomous Training (Pi-side, runs independently)

The Pi's training pipeline runs completely independently from the laptop demo system. It is managed by systemd and does not need to be started or stopped manually.

| Action | Command (run on Pi via SSH) |
|---|---|
| Check training status | `sudo systemctl status weapon-training.service` |
| Check Telegram bot status | `sudo systemctl status weapon-bot.service` |
| View training log | `tail -f ~/edge-ai/logs/train.log` |
| Check current epoch | `tail -n 5 ~/runs/detect/train/results.csv` |
| Restart training | `sudo systemctl restart weapon-training.service` |
| Stop training | `sudo systemctl stop weapon-training.service` |

Training autostarts on every boot. Checkpoints are saved every 5 epochs to `~/runs/detect/train/weights/`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Can't find Pi on network | Run `ping raspberrypi.local` or check router DHCP table; update `.env` with new IP |
| `npm run dev` fails | Ensure you're in `Prototype/dashboard/`; run `npm install` if node_modules is missing |
| Stream client can't connect | Verify edge server is running on Pi; check `IP_ADDRESS` in `.env` |
| Pi SSH refused | Pi may be rebooting; wait 60s and retry |
| Dashboard shows no feed | Check `dashboard/.env.local` has correct `NEXT_PUBLIC_PI_WS_URL` |
