# Environment Setup
Progress update: The local sensor node and municipal dashboard are in place, and both the Python syntax check and Next.js build completed.  
Changes: Added the local WebSocket sensor node and the municipal dashboard UI; next run the setup and boot sequence below.

## Python dependencies
Install the packages required for webcam capture, telemetry simulation, and WebSocket streaming.
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\backend\requirements.txt
```

## Dashboard dependencies
Install the Node packages required to run the municipal control room UI.
```powershell
Set-Location .\municipal-dashboard
npm install
```

## Optional: override the sensor WebSocket URL
Use this if the sensor node is not running on `ws://localhost:8000`.
```powershell
$env:NEXT_PUBLIC_SENSOR_WS_URL = "ws://localhost:8000"
```

# Boot Sequence
## Start the sensor node
This starts the local webcam stream and simulated PIR/thermal telemetry.
```powershell
python .\backend\sensor_node.py
```

## Start the dashboard
This launches the control room interface that consumes the WebSocket stream.
```powershell
Set-Location .\municipal-dashboard
npm run dev
```

# Demo Script
## Validate Increment 1 (Detection & Monitoring)
Open http://localhost:3000 and confirm the live video frame updates, PIR toggles, and the thermal grid animates.

## Trigger Increment 3 Tier 1 (Deterrable)
Click “Simulate Tier 1 Threat (Wildlife)” and call out the strobe overlay, siren tone, and continued telemetry flow.

## Trigger Increment 3 Tier 2 (Non-Deterrable)
Click “Simulate Tier 2 Threat (Armed Intruder)” and call out the new dispatch payload entry in the log.

## Reset
Click “Reset Response” to stop the siren and strobe before repeating the sequence.

Made changes.