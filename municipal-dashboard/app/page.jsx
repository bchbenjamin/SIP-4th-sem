"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const DEFAULT_COORDS = { lat: 12.9716, lng: 77.5946 };

function formatTime(tsMs) {
  if (!tsMs) {
    return "--";
  }
  return new Date(tsMs).toLocaleTimeString();
}

function buildDispatchPayload(type) {
  return {
    incident_type: type,
    priority: type.includes("Tier 2") ? "CRITICAL" : "MODERATE",
    gps: DEFAULT_COORDS,
    source: "Municipal Control Room",
    ts_ms: Date.now()
  };
}

export default function Home() {
  const [connected, setConnected] = useState(false);
  const [frameSrc, setFrameSrc] = useState("");
  const [lastFrameAt, setLastFrameAt] = useState(null);
  const [latencyMs, setLatencyMs] = useState(null);
  const [pirMotion, setPirMotion] = useState(false);
  const [ambientC, setAmbientC] = useState(null);
  const [maxC, setMaxC] = useState(null);
  const [thermalMatrix, setThermalMatrix] = useState(null);
  const [lastTelemetryAt, setLastTelemetryAt] = useState(null);
  const [strobeActive, setStrobeActive] = useState(false);
  const [sirenActive, setSirenActive] = useState(false);
  const [dispatchLogs, setDispatchLogs] = useState([]);

  const audioContextRef = useRef(null);
  const oscillatorRef = useRef(null);
  const gainRef = useRef(null);
  const sirenIntervalRef = useRef(null);
  const strobeTimeoutRef = useRef(null);

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_SENSOR_WS_URL || "ws://localhost:8000";
    const ws = new WebSocket(wsUrl);

    const handleOpen = () => setConnected(true);
    const handleClose = () => setConnected(false);

    ws.addEventListener("open", handleOpen);
    ws.addEventListener("close", handleClose);
    ws.addEventListener("error", handleClose);
    ws.addEventListener("message", (event) => {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }

      if (payload.type === "frame") {
        if (payload.jpeg_b64) {
          setFrameSrc(`data:image/jpeg;base64,${payload.jpeg_b64}`);
        }
        setLastFrameAt(payload.ts_ms || Date.now());
        if (payload.ts_ms) {
          setLatencyMs(Math.max(0, Date.now() - payload.ts_ms));
        }
      }

      if (payload.type === "telemetry") {
        setPirMotion(Boolean(payload.pir_motion));
        setAmbientC(payload.ambient_c);
        setMaxC(payload.max_c);
        setThermalMatrix(payload.thermal_c || null);
        setLastTelemetryAt(payload.ts_ms || Date.now());
      }
    });

    return () => {
      ws.removeEventListener("open", handleOpen);
      ws.removeEventListener("close", handleClose);
      ws.removeEventListener("error", handleClose);
      ws.close();
    };
  }, []);

  const thermalStats = useMemo(() => {
    if (!thermalMatrix || thermalMatrix.length === 0) {
      return { min: null, max: null, avg: null, grid: [] };
    }
    const flat = thermalMatrix.flat();
    const min = Math.min(...flat);
    const max = Math.max(...flat);
    const avg = flat.reduce((sum, value) => sum + value, 0) / flat.length;

    const rows = 8;
    const cols = 12;
    const grid = [];
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        const srcR = Math.floor((r / rows) * thermalMatrix.length);
        const srcC = Math.floor((c / cols) * thermalMatrix[0].length);
        grid.push(thermalMatrix[srcR][srcC]);
      }
    }

    return { min, max, avg, grid };
  }, [thermalMatrix]);

  const tempToColor = (temp) => {
    if (thermalStats.min === null || thermalStats.max === null) {
      return "#0f172a";
    }
    const span = thermalStats.max - thermalStats.min || 1;
    const t = Math.min(1, Math.max(0, (temp - thermalStats.min) / span));
    const hue = 220 - t * 160;
    return `hsl(${hue}, 70%, 50%)`;
  };

  const stopSiren = () => {
    if (sirenIntervalRef.current) {
      clearInterval(sirenIntervalRef.current);
      sirenIntervalRef.current = null;
    }
    if (oscillatorRef.current) {
      oscillatorRef.current.stop();
      oscillatorRef.current.disconnect();
      oscillatorRef.current = null;
    }
    if (gainRef.current) {
      gainRef.current.disconnect();
      gainRef.current = null;
    }
    setSirenActive(false);
  };

  const startSiren = async () => {
    if (sirenActive) {
      return;
    }
    const AudioContextImpl = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextImpl) {
      return;
    }
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContextImpl();
    }
    const audioContext = audioContextRef.current;
    if (audioContext.state === "suspended") {
      await audioContext.resume();
    }

    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    oscillator.type = "sine";
    oscillator.frequency.value = 520;
    gain.gain.value = 0.0;
    gain.gain.linearRampToValueAtTime(0.2, audioContext.currentTime + 0.2);

    oscillator.connect(gain).connect(audioContext.destination);
    oscillator.start();

    let highTone = false;
    sirenIntervalRef.current = setInterval(() => {
      highTone = !highTone;
      oscillator.frequency.setValueAtTime(highTone ? 880 : 520, audioContext.currentTime);
    }, 400);

    oscillatorRef.current = oscillator;
    gainRef.current = gain;
    setSirenActive(true);
  };

  const triggerTier1 = async () => {
    if (strobeTimeoutRef.current) {
      clearTimeout(strobeTimeoutRef.current);
    }
    setStrobeActive(true);
    await startSiren();
    strobeTimeoutRef.current = setTimeout(() => {
      setStrobeActive(false);
      stopSiren();
    }, 6000);
  };

  const triggerTier2 = () => {
    stopSiren();
    setStrobeActive(false);
    const payload = buildDispatchPayload("Tier 2 - Armed Intruder");
    setDispatchLogs((prev) => [payload, ...prev].slice(0, 8));
  };

  const triggerReset = () => {
    stopSiren();
    setStrobeActive(false);
  };

  return (
    <div className="page">
      <header className="top-bar">
        <div>
          <div className="title">AI-Powered Street Safety Device Network</div>
          <div className="subtitle">Municipal Control Room | Increment 1 + 3 Demo</div>
        </div>
        <div className="status-row">
          <div className={`pill ${connected ? "ok" : "warn"}`}>
            Sensor WebSocket: {connected ? "Online" : "Offline"}
          </div>
          <div className="pill">PIR: {pirMotion ? "Motion" : "Clear"}</div>
          <div className="pill ghost">Last Frame: {formatTime(lastFrameAt)}</div>
        </div>
      </header>

      <main className="grid">
        <section className="panel video-panel">
          <div className="panel-header">
            <div>
              <h2>Live Video Feed</h2>
              <p>Laptop webcam stream via local sensor node</p>
            </div>
            <div className="panel-badges">
              <span className="badge">Latency: {latencyMs ? `${latencyMs} ms` : "--"}</span>
              <span className="badge">Telemetry: {formatTime(lastTelemetryAt)}</span>
            </div>
          </div>
          <div className={`video-frame ${strobeActive ? "strobe-active" : ""}`}>
            {frameSrc ? (
              <img src={frameSrc} alt="Live feed" />
            ) : (
              <div className="placeholder">
                <div className="scanline" />
                Awaiting sensor node stream
              </div>
            )}
            <div className="strobe-overlay" aria-hidden="true" />
          </div>
          <div className="panel-footer">
            <div className="metric">
              <span className="label">Ambient Temp</span>
              <span className="value">{ambientC ? `${ambientC.toFixed(1)} C` : "--"}</span>
            </div>
            <div className="metric">
              <span className="label">Max Temp</span>
              <span className="value warn">{maxC ? `${maxC.toFixed(1)} C` : "--"}</span>
            </div>
            <div className="metric">
              <span className="label">Siren</span>
              <span className={`value ${sirenActive ? "warn" : "ok"}`}>
                {sirenActive ? "Active" : "Idle"}
              </span>
            </div>
          </div>
        </section>

        <section className="panel telemetry-panel">
          <div className="panel-header">
            <div>
              <h2>Telemetry Panel</h2>
              <p>Simulated PIR + MLX90640 thermal matrix</p>
            </div>
            <div className="panel-badges">
              <span className="badge">PIR Motion: {pirMotion ? "TRUE" : "FALSE"}</span>
            </div>
          </div>

          <div className="thermal-block">
            <div className="thermal-stats">
              <div>
                <span className="label">Thermal Min</span>
                <span className="value">{thermalStats.min ? `${thermalStats.min.toFixed(1)} C` : "--"}</span>
              </div>
              <div>
                <span className="label">Thermal Avg</span>
                <span className="value">{thermalStats.avg ? `${thermalStats.avg.toFixed(1)} C` : "--"}</span>
              </div>
              <div>
                <span className="label">Thermal Max</span>
                <span className="value warn">{thermalStats.max ? `${thermalStats.max.toFixed(1)} C` : "--"}</span>
              </div>
            </div>
            <div className="thermal-grid">
              {thermalStats.grid.length === 0 ? (
                <div className="thermal-empty">No thermal data yet.</div>
              ) : (
                thermalStats.grid.map((temp, idx) => (
                  <div
                    key={`cell-${idx}`}
                    className="thermal-cell"
                    style={{ backgroundColor: tempToColor(temp) }}
                    title={`${temp.toFixed(1)} C`}
                  />
                ))
              )}
            </div>
          </div>
        </section>
      </main>

      <section className="panel response-panel">
        <div className="panel-header">
          <div>
            <h2>Two-Tier Response Console</h2>
            <p>Manual simulation of deterrable vs non-deterrable threats</p>
          </div>
          <div className="panel-badges">
            <span className="badge danger">Tier 2: Armed Intruder</span>
          </div>
        </div>

        <div className="response-actions">
          <button className="btn warning" onClick={triggerTier1}>
            Simulate Tier 1 Threat (Wildlife)
          </button>
          <button className="btn danger" onClick={triggerTier2}>
            Simulate Tier 2 Threat (Armed Intruder)
          </button>
          <button className="btn ghost" onClick={triggerReset}>
            Reset Response
          </button>
        </div>

        <div className="dispatch-table">
          <div className="dispatch-header">Police Dispatch & API Log</div>
          <div className="dispatch-grid">
            <div className="dispatch-row dispatch-title">
              <span>Timestamp</span>
              <span>Payload</span>
            </div>
            {dispatchLogs.length === 0 ? (
              <div className="dispatch-empty">No dispatch events yet.</div>
            ) : (
              dispatchLogs.map((entry) => (
                <div key={entry.ts_ms} className="dispatch-row">
                  <span>{formatTime(entry.ts_ms)}</span>
                  <code>{JSON.stringify(entry)}</code>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <footer className="footer">
        <div>Increment 1: Local Sensor Node (Webcam + Simulated PIR/Thermal)</div>
        <div>Increment 3: Two-Tier Response Layer (Siren + Dispatch)</div>
      </footer>
    </div>
  );
}
