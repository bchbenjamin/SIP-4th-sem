# Raspberry Pi 5 Setup & IP Discovery Guide

This guide helps you set up a brand-new Raspberry Pi 5 and find its IP address so you can connect it to the SIP Prototype system.

## Prerequisites

Before you start, you need:
- **Raspberry Pi 5** (with power supply)
- **SD card** (blank or ready to be flashed)
- **USB Type-C cable** (to connect Pi to laptop for serial console & power)
- **Network connection** (Ethernet cable preferred; WiFi also works but requires headless setup)
- **Windows laptop** (the one running the SIP Prototype)
- **SD card flashing tool** (see Step 1 below)

---

## Step 1: Flash Raspberry Pi OS to SD Card

Since your laptop can't read SD cards directly, here are your options:

### Option A: Use Your Phone with Root (Fastest & Most Flexible)

Since you have **custom recovery and root** on your phone, you have powerful options:

#### A1: Using Termux (Recommended for Advanced Users)
1. **Install Termux** (free, from F-Droid or GitHub releases): https://f-droid.org/packages/com.termux/
2. **Grant Termux root access**:
   - Open Termux, run: `su`
   - Grant root permission when prompted
3. **Get the Raspberry Pi OS image**:
   ```bash
   cd ~/storage/downloads
   # Download RPi OS image (adjust URL to latest)
   wget https://downloads.raspberrypi.org/raspios_arm64/images/raspios_arm64-2024-03-15/2024-03-15-raspios-bookworm-arm64.img.xz
   # Decompress if needed
   unxz 2024-03-15-raspios-bookworm-arm64.img.xz
   ```
4. **Insert SD card via USB adapter**, then identify it:
   ```bash
   su
   ls /dev/block/mmcblk* # or /dev/sd*
   ```
5. **Flash with dd** (replace `sdX` with your card):
   ```bash
   dd if=~/storage/downloads/2024-03-15-raspios-bookworm-arm64.img of=/dev/mmcblk0 bs=4M status=progress
   sync
   ```
6. Eject the SD card safely

##### Termux notes: `unxz` errors and storage permissions

If you see errors like `unxz: inaccessible or not found` or `Permission denied` when running `unxz` as root, this is usually due to Android storage FUSE permissions or missing xz tools. Use the steps below:

- Ensure Termux storage access is enabled (run as non-root):

```bash
termux-setup-storage
```

- Install xz utilities (as Termux user):

```bash
pkg update
pkg install xz-utils
```

- Decompress as the Termux user (do NOT `su` before decompressing). Working in `~/storage/downloads` avoids Android FUSE permission issues:

```bash
cd ~/storage/downloads
unxz 2024-12-19-raspios-bookworm-arm64.img.xz
# or: xz -d 2024-12-19-raspios-bookworm-arm64.img.xz
```

- If you already used `su` and saw `Permission denied`, `exit` back to the Termux user, then copy the file into your Termux home and decompress there:

```bash
exit   # leave root
cp /storage/emulated/0/Download/2024-12-19-raspios-bookworm-arm64.img.xz ~/
cd ~
unxz 2024-12-19-raspios-bookworm-arm64.img.xz
```

- After decompression, become root to flash the raw image with `dd` (root is required to write block devices). **CRITICAL: NEVER write to `mmcblk0` (your phone's internal storage). Find your external SD card (usually `sda`, `sdb`, or `mmcblk1`):**

```bash
su
# 1. Plug in your SD card adapter
# 2. Find the new device name (it will likely be sda, sdb, or mmcblk1)
ls /dev/block/sd* /dev/block/mmcblk1* 2>/dev/null

# 3. Flash the image (Replace 'sda' with your actual SD card device)
# Use your exact image path from your phone
dd if=/storage/emulated/0/2024-12-19-raspios-bookworm-arm64.img of=/dev/block/sda bs=4M status=progress
sync
```

Notes:
- Running `unxz` as root often fails to access `/storage/emulated/*` paths because Android's FUSE storage is only accessible to the non-root user. Decompressing as the Termux user and then switching to `su` to `dd` avoids this.
- If `unxz` is not found after `pkg install xz-utils`, use the full path: `/data/data/com.termux/files/usr/bin/unxz`.

#### A2: Using Raspberry Pi Imager (Simplest)
1. Download the **Raspberry Pi Imager** app from Google Play
2. Open the app, insert the SD card (via USB Type-C adapter if your phone has it, or USB-A)
3. Select:
   - **OS**: Raspberry Pi OS (latest)
   - **Device**: Raspberry Pi 5
   - **Storage**: Your SD card
4. Click **Write** and wait 5–10 minutes
5. Eject the SD card safely

**A1 (Termux with root) gives you the most control and speed. A2 is simpler if your phone's imager app supports your SD card reader.**

### Option B: Use a USB SD Card Reader (Fallback)
If you want to use Windows instead of your phone:

1. Purchase a cheap **USB Type-A SD card reader** (~$5–10 on Amazon)
2. Connect it to your Windows laptop
3. Download **Raspberry Pi Imager** for Windows: https://www.raspberrypi.com/software/
4. Open the Imager, select:
   - **OS**: Raspberry Pi OS (latest)
   - **Device**: Raspberry Pi 5
   - **Storage**: Your SD card (via the USB reader)
5. Click **Write** and wait 5–10 minutes
6. Eject the card safely

**Option A (your phone with root) is faster and more direct.**

### Option C: Ask a Friend or Use a Different Laptop
If you'd rather not set up on your phone, borrow another laptop with an SD card reader.

---

Once flashed, you're ready to insert the SD card into the Pi.

## Step 2: Connect Pi via USB Type-C (Serial Console Access)

The USB Type-C cable you have can be used to:
- **Power the Pi** (if it's the right wattage)
- **Access the serial console** to interact with the Pi without HDMI/keyboard

### Using the Serial Console (Windows)

1. **Connect** the USB Type-C cable from the Pi to your laptop
2. **Find the COM port**:
   - Open **Device Manager** (Windows key + X → Device Manager)
   - Look for "USB Serial Device" or similar under **Ports (COM & LPT)**
   - Note the COM port number (e.g., **COM3**)
3. **Install a serial terminal** (if you don't have one):
   - Download **PuTTY** (free): https://www.putty.org/
   - Or use **Windows Terminal** (built-in)
4. **Connect to the serial console**:
   - **PuTTY**: Set Connection type to **Serial**, Speed to **115200**, Port to **COM3**, then click Open
   - **Windows Terminal**: Use `mode COM3:115200,N,8,1`
5. **You should see the boot messages**. Once the Pi boots, you can interact with it just like SSH!

---

## Step 2: Power On and Connect

1. Insert the flashed SD card into the Pi
2. Connect the USB Type-C cable to power the Pi (or use a separate power supply)
3. Connect an Ethernet cable to the Pi's RJ-45 port (recommended for stable network)
4. Wait 60–90 seconds for the Pi to boot
5. The Pi will auto-assign an IP via DHCP on Ethernet

**Optional**: If using WiFi instead of Ethernet:
- Use the serial console (via USB Type-C and PuTTY) to configure WiFi via `sudo nmtui`
- Or pre-configure WiFi on the SD card's boot partition before inserting (see below)

**Pre-configure WiFi on Windows** (if you want to avoid serial console):
- Mount the SD card on Windows (using a USB reader) or on another computer
- Create or edit: `boot/user-data` with:
  ```yaml
  #cloud-config
  wifi:
    version: 2
    wifis:
      wlan0:
        dhcp4: true
        access-points:
          "YOUR_SSID":
            password: "YOUR_PASSWORD"
  ```
- Replace `YOUR_SSID` and `YOUR_PASSWORD`
- Safe eject and insert into Pi

---

## Step 2a: Set Up Serial Console (Optional but Recommended)

The USB Type-C cable can give you direct terminal access to the Pi, even before it's on the network.

1. **Connect** the USB Type-C cable from the Pi to your laptop
2. **Find the COM port**:
   - Open **Device Manager** (Windows key + X → Device Manager)
   - Look for "USB Serial Device" or similar under **Ports (COM & LPT)**
   - Note the COM port number (e.g., **COM3**)
3. **Install a serial terminal** (if you don't have one):
   - Download **PuTTY** (free): https://www.putty.org/
   - Or use **Windows Terminal** (built-in)
4. **Connect to the serial console**:
   - **PuTTY**: Set Connection type to **Serial**, Speed to **115200**, Port to **COM3** (your port), then click **Open**
   - **Windows Terminal**: Run `mode COM3:115200,N,8,1` and then `telnet 127.0.0.1 <port>`
5. **You should see boot messages**. Once the Pi boots, you'll have a terminal prompt where you can run commands!

---

## Step 3: Find the Pi's IP Address (or Use Serial Console Directly)

**Note:** If you're using the serial console (USB Type-C), you can skip this step and go directly to SSH via the serial connection or Ethernet.

Choose one of these methods:

### Method 0: Serial Console (Easiest – USB Type-C)
If you've set up PuTTY or Windows Terminal on the serial port:
1. You already have terminal access to the Pi
2. Run this command:
   ```bash
   hostname -I
   ```
3. The output shows your Pi's IP address(es)
4. Make a note and proceed to **Step 4**

### Method 1: Hostname-Based Discovery (No Setup Needed)
On your Windows laptop, open **PowerShell** and run:

```powershell
ping raspberrypi.local
```

**Example output:**
```
Pinging raspberrypi.local [192.168.1.45] with 32 bytes of data:
Reply from 192.168.1.45: bytes=32 time=5ms TTL=64
```

If this works, your Pi's IP is **192.168.1.45** (or whatever is shown).

**Note:** This works if mDNS is enabled and you have Ethernet or WiFi connected.

### Method 2: Check Your Router's DHCP Clients List
1. Open your router's admin panel (usually **192.168.1.1** or **192.168.0.1** in your browser)
2. Log in with your router credentials
3. Look for "Connected Devices", "DHCP Clients", or "Active Leases"
4. Find the device named **raspberrypi** or with a Raspberry Pi MAC address (starts with `b8:27:eb`, `bc:a2:3b`, or `d8:3a:8e`)
5. Note its IP address

### Method 3: Network Scanning (Advanced)
If you have a network scanner, you can scan your subnet:

**Using nmap** (if installed):
```powershell
nmap -sn 192.168.1.0/24
```
Look for the device labeled **Raspberry Pi Foundation** or with a matching MAC prefix.

**Using arp-scan** (if installed):
```powershell
arp-scan --local
```

### Method 4: Via Serial Console (See Method 0 Above)
This is the most reliable if you have the USB Type-C cable set up.

---

## Step 4: Connect to the Pi (SSH or Serial)

You now have two ways to interact with the Pi:

### Option A: SSH via Network (Recommended for Running Services)

Once you have the Pi's IP (from Step 3), test SSH:

```powershell
ssh pi@<PI_IP>
```

**Replace `<PI_IP>` with your actual IP**, e.g.:
```powershell
ssh pi@192.168.1.45
```

**First time:**
- You may see a host key verification prompt – type `yes` and press Enter
- Default password is **raspberry**

If SSH succeeds, your Pi is fully set up and reachable.

### Option B: Serial Console via USB Type-C (For Initial Setup)

If you set up the serial console in Step 2a, you already have terminal access via PuTTY or Windows Terminal. You can use this to:
- Run commands directly on the Pi
- Configure WiFi with `sudo nmtui`
- Check the IP with `hostname -I`
- Install dependencies

Once you have an IP or serial access, proceed to **Step 5** to prepare the Pi for the SIP Prototype.

---

## Step 5: Configure the Pi for SIP Prototype

You can run these commands via **SSH** (Step 4 Option A) or **serial console** (Step 4 Option B).

**On the Pi**, run:

```bash
# Update system packages
sudo apt update
sudo apt install -y python3-venv python3-pip libopenblas-dev libatlas-base-dev libgl1

# Create edge-ai directory
mkdir -p ~/edge-ai
```

After this, you'll need to transfer the `/pi` folder from your Windows laptop to the Pi (see Step 6).

---

## Step 6: Copy the Pi Code to the Raspberry

You need to transfer the `/pi` folder from your Windows laptop to the Raspberry Pi.

### Option A: SCP via SSH (Requires Networking)

Once you have SSH access and an IP address, use SCP from PowerShell:

```powershell
scp -r "c:\SIP-Prototype\Prototype\pi" pi@<PI_IP>:~/edge-ai/
```

**Replace `<PI_IP>` with your Pi's IP address**, e.g.:
```powershell
scp -r "c:\SIP-Prototype\Prototype\pi" pi@192.168.1.45:~/edge-ai/
```

### Option B: USB Direct Transfer (No Networking Required)

If you have a USB Type-A card reader:

1. Insert the SD card into your USB reader on Windows
2. The SD card should appear as a drive (e.g., `D:\`)
3. Create a folder: `D:\pi-code\`
4. Copy `c:\SIP-Prototype\Prototype\pi` into `D:\pi-code\`
5. Eject the SD card safely
6. Insert back into the Raspberry Pi
7. On the Pi (via serial console or SSH), run:
   ```bash
   mkdir -p ~/edge-ai
   cp -r /media/pi/SDCARD/pi-code/pi ~/edge-ai/pi
   ```
   *(Adjust the mount path if different)*

### Option C: Use SFTP (Graphical)

1. Install **WinSCP** (free): https://winscp.net/
2. Create a new session:
   - Host: `<PI_IP>`
   - Username: `pi`
   - Password: `raspberry`
3. Navigate to `/home/pi` on the Pi
4. Create a folder `edge-ai`
5. Drag the `c:\SIP-Prototype\Prototype\pi` folder into `edge-ai`

**SCP (Option A) is fastest once networking is available.**

---

## Step 7: Update Dashboard Configuration

Once you have your Pi's IP, update the dashboard environment file:

On your Windows laptop, edit [dashboard/.env.local](dashboard/.env.local):

```env
NEXT_PUBLIC_PI_WS_URL=ws://<PI_IP>:8766
```

**Replace `<PI_IP>` with your actual Raspberry Pi IP**, e.g.:
```env
NEXT_PUBLIC_PI_WS_URL=ws://192.168.1.45:8766
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ping raspberrypi.local` fails | Try Method 2 (router), Method 3 (network scan), or use serial console to check IP with `hostname -I` |
| Serial console not appearing in Device Manager | Try different USB port; reinstall USB drivers; ensure USB Type-C cable is data-capable (not power-only) |
| Can't find COM port | Update drivers, try different USB ports, or check if another app has the port open |
| SSH "Permission denied" | Default password is `raspberry`; try that; or use serial console to verify boot completed |
| Pi not connecting to WiFi | Use serial console to run `sudo nmtui` and reconfigure; or use Ethernet instead |
| Serial console shows garbled text | Check speed is **115200** baud in PuTTY settings |
| Can't reach Pi on network | Ensure Ethernet is plugged in or WiFi is configured; check router for DHCP assignments |
| SCP/SFTP says "Permission denied" | Verify you're using username `pi` and password `raspberry` |
| Pi boots but no network | Use serial console to check WiFi status with `nmcli device wifi` or connect to Ethernet |

---

## Next Steps

Once you have:
- ✅ SD card flashed with Raspberry Pi OS
- ✅ USB Type-C cable connected & serial console working (or Pi on network with IP)
- ✅ Pi booted and has network access (Ethernet or WiFi)
- ✅ `/pi` folder copied to `~/edge-ai/pi`
- ✅ Dashboard [.env.local](dashboard/.env.local) updated with Pi IP

**Return to the main setup and provide the Pi IP address**, and I'll:
1. Set up and start the Pi edge server
2. Launch the dashboard dev server
3. Start the laptop stream client

---

## Quick Reference Cheatsheet

### Windows Laptop

```powershell
# Flash SD card using Raspberry Pi Imager (after download)
# Insert SD card via USB reader, select OS/Device/Storage, click Write

# Copy code to Pi via SCP
scp -r "c:\SIP-Prototype\Prototype\pi" pi@<PI_IP>:~/edge-ai/

# Update dashboard config
# Edit: c:\SIP-Prototype\Prototype\dashboard\.env.local
# Set: NEXT_PUBLIC_PI_WS_URL=ws://<PI_IP>:8766

# Start dashboard dev server
cd c:\SIP-Prototype\Prototype\dashboard
npm run dev

# Start sensor stream (after Pi is running edge server)
.\.venv\Scripts\python.exe laptop\stream_client.py --pi-host <PI_IP>
```

### Raspberry Pi (via SSH or Serial Console)

```bash
# Find your Pi's IP
hostname -I

# Update packages
sudo apt update
sudo apt install -y python3-venv python3-pip libopenblas-dev libatlas-base-dev libgl1

# Create edge-ai directory
mkdir -p ~/edge-ai

# Set up Python environment for edge server
cd ~/edge-ai/pi
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Start the edge server
python3 edge_server.py --config config.json
```

### Serial Console (Windows – via PuTTY or Windows Terminal)

```
Host: COM3 (or your COM port)
Speed: 115200 baud
Data bits: 8
Stop bits: 1
Parity: None

# Then interact with Pi commands directly
```
