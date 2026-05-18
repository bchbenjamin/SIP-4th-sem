"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type ThreatEvent = {
  event_id: string;
  ts_ms: number;
  tier: "tier1" | "tier2";
  labels: string[];
  max_confidence: number;
  action: string;
  latency_ms: number;
  frame_id: number;
};

type FrameMessage = {
  type: "frame";
  frame_id: number;
  annotated_b64: string;
  latency_ms: number;
  fps: number;
};

type LogMessage = {
  type: "log";
  event: ThreatEvent;
};

const MAX_LOGS = 28;

export default function Home() {
  const [connected, setConnected] = useState(false);
  const [frameSrc, setFrameSrc] = useState("");
  const [latency, setLatency] = useState<number | null>(null);
  const [avgLatency, setAvgLatency] = useState<number | null>(null);
  const [fps, setFps] = useState(0);
  const [deterrenceCount, setDeterrenceCount] = useState(0);
  const [alertCount, setAlertCount] = useState(0);
  const [logs, setLogs] = useState<ThreatEvent[]>([]);
  const [lastEvent, setLastEvent] = useState<ThreatEvent | null>(null);
  const [now, setNow] = useState(Date.now());

  const frameCounter = useRef(0);
  const latencyWindow = useRef<number[]>([]);

  useEffect(() => {
    const interval = setInterval(() => {
      setFps(frameCounter.current);
      frameCounter.current = 0;
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_PI_WS_URL || "ws://localhost:8766";
    const ws = new WebSocket(wsUrl);

    const handleOpen = () => setConnected(true);
    const handleClose = () => setConnected(false);

    ws.addEventListener("open", handleOpen);
    ws.addEventListener("close", handleClose);
    ws.addEventListener("error", handleClose);
    ws.addEventListener("message", (event) => {
      let payload: FrameMessage | LogMessage | null = null;
      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }
      if (!payload) {
        return;
      }
      if (payload.type === "frame") {
        const frameMsg = payload as FrameMessage;
        if (frameMsg.annotated_b64) {
          setFrameSrc(`data:image/jpeg;base64,${frameMsg.annotated_b64}`);
        }
        if (typeof frameMsg.latency_ms === "number") {
          setLatency(frameMsg.latency_ms);
          latencyWindow.current.push(frameMsg.latency_ms);
          if (latencyWindow.current.length > 24) {
            latencyWindow.current.shift();
          }
          const avg = Math.round(
            latencyWindow.current.reduce((a, b) => a + b, 0) /
              latencyWindow.current.length
          );
          setAvgLatency(avg);
        }
        frameCounter.current += 1;
      }
      if (payload.type === "log") {
        const logMsg = payload as LogMessage;
        setLogs((prev) => [logMsg.event, ...prev].slice(0, MAX_LOGS));
        setLastEvent(logMsg.event);
        if (logMsg.event.action === "alert") {
          setAlertCount((prev) => prev + 1);
        } else {
          setDeterrenceCount((prev) => prev + 1);
        }
      }
    });

    return () => {
      ws.removeEventListener("open", handleOpen);
      ws.removeEventListener("close", handleClose);
      ws.removeEventListener("error", handleClose);
      ws.close();
    };
  }, []);

  const timeString = useMemo(() => new Date(now).toLocaleTimeString(), [now]);
  const latencyClass = latency !== null && latency <= 500 ? "ok" : "warn";

  return (
    <div className="page">
      <header className="top-bar">
        <div>
          <div className="title">AI-Powered Street Safety Device Network</div>
          <div className="subtitle">
            Atria Institute of Technology, Bengaluru | Municipal Control Room
          </div>
        </div>
        <div className="status-row">
          <div className={`pill ${connected ? "ok" : "warn"}`}>
            Pi WebSocket: {connected ? "Online" : "Offline"}
          </div>
          <div className="pill">Latency Target: &lt; 500 ms</div>
          <div className="pill ghost">Local Time: {timeString}</div>
        </div>
      </header>

      <main className="grid">
        <section className="panel video-panel">
          <div className="panel-header">
            <div>
              <h2>Live Edge Feed</h2>
              <p>Annotated frames from the Pi edge core</p>
            </div>
            <div className="panel-badges">
              <span className="badge">FPS: {fps}</span>
              <span className="badge">Frame: {lastEvent?.frame_id ?? "-"}</span>
            </div>
          </div>
          <div className="video-frame">
            {frameSrc ? (
              <img src={frameSrc} alt="Annotated feed" />
            ) : (
              <div className="placeholder">
                <div className="scanline" />
                Awaiting stream from sensor node
              </div>
            )}
          </div>
          <div className="panel-footer">
            <div className="metric">
              <span className="label">Latest Latency</span>
              <span className={`value ${latencyClass}`}>
                {latency !== null ? `${latency} ms` : "--"}
              </span>
            </div>
            <div className="metric">
              <span className="label">Average Latency</span>
              <span className="value">
                {avgLatency !== null ? `${avgLatency} ms` : "--"}
              </span>
            </div>
            <div className="metric">
              <span className="label">Tier 2 Alerts</span>
              <span className="value alert">{alertCount}</span>
            </div>
          </div>
        </section>

        <section className="panel side-panel">
          <div className="panel-header">
            <div>
              <h2>Threat Telemetry</h2>
              <p>Deterrence vs emergency escalation</p>
            </div>
            <div className="panel-badges">
              <span className="badge">Deterrence: {deterrenceCount}</span>
              <span className="badge danger">Alerts: {alertCount}</span>
            </div>
          </div>

          <div className="stats-grid">
            <div className="stat-card">
              <span className="label">Last Tier</span>
              <span className="value">{lastEvent ? lastEvent.tier : "Idle"}</span>
              <span className="meta">Policy: Tier 1 deterrence, Tier 2 alert</span>
            </div>
            <div className="stat-card">
              <span className="label">Last Labels</span>
              <span className="value">
                {lastEvent ? lastEvent.labels.join(", ") : "--"}
              </span>
              <span className="meta">Confidence: {lastEvent ? lastEvent.max_confidence.toFixed(2) : "--"}</span>
            </div>
            <div className="stat-card">
              <span className="label">Action Executed</span>
              <span className="value">
                {lastEvent ? lastEvent.action.toUpperCase() : "--"}
              </span>
              <span className="meta">Node: Pi 5 edge core</span>
            </div>
          </div>

          <div className="log-list">
            <div className="log-header">Rolling Event Log</div>
            <div className="log-table">
              {logs.length === 0 ? (
                <div className="log-empty">No threat events yet.</div>
              ) : (
                logs.map((event) => (
                  <div key={event.event_id} className={`log-row ${event.tier}`}>
                    <div className="log-tier">{event.tier.toUpperCase()}</div>
                    <div className="log-detail">
                      <div className="log-title">
                        {event.labels.join(", ") || "Unknown"}
                      </div>
                      <div className="log-meta">
                        {new Date(event.ts_ms).toLocaleTimeString()} | Action: {event.action}
                      </div>
                    </div>
                    <div className="log-score">{event.max_confidence.toFixed(2)}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div>Lead: B C H Benjamin (1AT24CS037) | Guide: Dr. Raghunandan G H</div>
        <div>Members: Saniya J, Chetan S, Aydin Hassan K S, Chandan B D, Rohan C</div>
        <div>Mapped SDGs: SDG 12 (Law Enforcement & Governance), SDG 6 (Disaster Management)</div>
      </footer>
    </div>
  );
}
