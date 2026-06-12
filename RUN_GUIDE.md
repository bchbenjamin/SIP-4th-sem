# Street Safety Prototype: Start & Stop Execution Guide

This document lists the exact commands to start, monitor, and stop the components of the AI-Powered Street Safety Device Network.

---

## 📋 Network Configuration Reference
- **Raspberry Pi 5 IP:** `10.253.13.25` (Port `8765` for Ingest, Port `8766` for Dashboard feed)
- **Laptop Dashboard Local Address:** `http://localhost:3000`

---

## 🚀 Starting the System

To run the full prototype demo, start the components in the following order:

### 1. Start the Raspberry Pi Edge Server
Run these commands on the **Raspberry Pi** (via SSH or Serial connection) to launch the YOLOv8-powered edge detection server:

* **Command to run in the background (using nohup):**
  ```bash
  nohup ~/edge-ai/pi/.venv/bin/python3 ~/edge-ai/pi/edge_server.py --config ~/edge-ai/pi/config.json --model ~/edge-ai/pi/yolov8n.pt > ~/edge-ai/pi/server.log 2>&1 &
  ```
* **Command to verify it is running:**
  ```bash
  ps aux | grep edge_server.py
  ```
* **Command to watch the logs in real-time:**
  ```bash
  tail -f ~/edge-ai/pi/server.log
  ```

---

### 2. Start the Next.js Dashboard
Run this command in a PowerShell terminal on your **Laptop** to start the web-based Control Room dashboard:

* **Command:**
  ```powershell
  cd c:\SIP-Prototype\Prototype\dashboard
  npm run dev
  ```
* Once ready, open **[http://localhost:3000](http://localhost:3000)** in Chrome/Firefox and allow microphone permissions.

---

### 3. Start the Laptop Camera Stream Client
Run this command in a separate PowerShell terminal on your **Laptop** to start capturing and streaming your webcam frames to the Raspberry Pi:

* **Command:**
  ```powershell
  cd c:\SIP-Prototype\Prototype
  .\.venv\Scripts\python.exe laptop\stream_client.py --pi-host 10.253.13.25
  ```
* The Pi server console logs will show `connection open` and begin printing YOLOv8 detections (e.g. `INFO Deterrence simulated for person`).

---

## 🛑 Stopping/Ending the System

When you are finished with the demo, follow these steps to stop all running processes cleanly:

### 1. Stop the Laptop Stream Client
* **If running in your active terminal:**
  Press `Ctrl + C` in the PowerShell window running `stream_client.py`.
* **If running in the background:**
  Run this PowerShell command to find and stop the Python stream client:
  ```powershell
  Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%stream_client%'" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  ```

---

### 2. Stop the Dashboard Server
* **If running in your active terminal:**
  Press `Ctrl + C` in the PowerShell window running `npm run dev`.
* **If running in the background:**
  Run this PowerShell command to stop whichever process is listening on the dashboard port (`3000`):
  ```powershell
  Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -Force
  ```

---

### 3. Stop the Raspberry Pi Edge Server
Run this command on the **Raspberry Pi** (via SSH) to terminate the edge core:

* **Command:**
  ```bash
  pkill -f edge_server.py
  ```
* **Verification (Should return no active process lines except your grep):**
  ```bash
  ps aux | grep edge_server.py
  ```
