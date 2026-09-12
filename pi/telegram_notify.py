#!/usr/bin/env python3
"""Telegram notification helper for weapon detection training on Raspberry Pi 5."""

import os
import csv
import sys
import json
import urllib.request
import urllib.parse
import traceback
from datetime import datetime

import dotenv

dotenv.load_dotenv(os.path.join(os.path.expanduser("~"), "edge-ai", ".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
PRIMARY_CHAT_ID = os.getenv("PRIMARY_CHAT_ID")
ALLOWED_CHAT_IDS = os.getenv("ALLOWED_CHAT_IDS", PRIMARY_CHAT_ID or "").split(",")
RESULTS_CSV = os.path.expanduser("~/runs/detect/train/results.csv")


def send_telegram(message: str, chat_id: str = None):
    """Send a message via Telegram Bot API."""
    if chat_id is None:
        targets = ALLOWED_CHAT_IDS
    else:
        targets = [chat_id]
        
    if not targets or not BOT_TOKEN:
        print("Telegram credentials missing.", file=sys.stderr)
        return None
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    results = []
    for target in targets:
        if not target:
            continue
        data = urllib.parse.urlencode({
            "chat_id": str(target).strip(),
            "text": message,
            "parse_mode": "HTML",
        }).encode()
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=15) as resp:
                results.append(json.loads(resp.read()))
        except Exception as e:
            print(f"Telegram send failed for {target}: {e}", file=sys.stderr)
            
    return results[0] if len(results) == 1 else results


def get_latest_results():
    """Parse results.csv and return last row as dict."""
    if not os.path.exists(RESULTS_CSV):
        return None
    with open(RESULTS_CSV, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return None
    return rows[-1], len(rows)


def get_live_progress():
    """Parse train.log for live epoch/batch progress."""
    log_path = os.path.expanduser("~/edge-ai/logs/train.log")
    if not os.path.exists(log_path):
        return ""
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()[-50:]
        
        epoch_str = 'Unknown'
        batch_str = 'Unknown'
        phase = 'Training'
        
        for line in reversed(lines):
            line = line.strip()
            if '%|' in line and '/' in line and '[' in line:
                if 'Class' in line and 'Images' in line:
                    phase = 'Validating'
                parts = line.split('|')
                if len(parts) >= 3:
                    pct_part = parts[0]
                    if ':' in pct_part:
                        pct_part = pct_part.split(':')[-1]
                    pct = pct_part.strip()
                    
                    rest = parts[2].strip().split('[')
                    if len(rest) >= 2:
                        batch_prog = rest[0].strip()
                        if '<' in rest[1] and ',' in rest[1]:
                            eta = rest[1].split('<')[1].split(',')[0]
                        else:
                            eta = '?'
                        batch_str = f"{pct} ({batch_prog}) ETA: {eta}"
                        break
                        
        for line in reversed(lines):
            line = line.strip()
            if len(line.split()) > 0 and '/' in line.split()[0] and 'G' in line:
                parts = line.split()
                if '/' in parts[0]:
                    epoch_str = parts[0]
                    break
                    
        if epoch_str != 'Unknown':
            return f"🏃 <b>Live Action:</b> {phase} Epoch {epoch_str}\n⏳ <b>Batch:</b> {batch_str}\n━━━━━━━━━━━━━━━━━━━\n"
    except Exception:
        pass
    return ""


def get_system_stats():
    """Get system temperature, CPU load, network speed, and setup status."""
    stats = ""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_c = int(f.read().strip()) / 1000.0
        stats += f"🌡️ <b>Temp:</b> {temp_c:.1f}°C\n"
    except:
        pass
        
    try:
        load1, load5, load15 = os.getloadavg()
        stats += f"🧠 <b>Load (1m):</b> {load1:.2f}\n"
    except:
        pass
        
    try:
        def get_bytes():
            rx, tx = 0, 0
            for iface in ['wlan0', 'eth0']:
                try:
                    with open(f"/sys/class/net/{iface}/statistics/rx_bytes") as f: rx += int(f.read().strip())
                    with open(f"/sys/class/net/{iface}/statistics/tx_bytes") as f: tx += int(f.read().strip())
                except: pass
            return rx, tx
            
        rx1, tx1 = get_bytes()
        import time
        time.sleep(0.5)
        rx2, tx2 = get_bytes()
        
        rx_mbps = ((rx2 - rx1) * 2 * 8) / 1_000_000
        tx_mbps = ((tx2 - tx1) * 2 * 8) / 1_000_000
        stats += f"🌐 <b>Network:</b> ↓{rx_mbps:.1f} Mbps | ↑{tx_mbps:.1f} Mbps\n"
    except:
        pass
        
    try:
        log_path = os.path.expanduser("~/edge-ai/logs/train.log")
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                # Tail last 200 lines to avoid reading whole file
                import collections
                lines = collections.deque(f, 200)
            dataset_lines = [line.strip() for line in lines if '[dataset]' in line]
            if dataset_lines:
                last_dataset = dataset_lines[-1].replace('[dataset]', '').strip()
                stats += f"📥 <b>Setup Status:</b> {last_dataset}\n"
    except:
        pass
        
    return stats

def format_progress_message():
    """Create a formatted progress message from results.csv and train.log."""
    result = get_latest_results()
    if result is None:
        return "⏳ Training has not started yet or no results found."

    row, total_epochs = result
    # Clean up column names (they have leading spaces)
    row = {k.strip(): v.strip() for k, v in row.items()}

    epoch = row.get("epoch", "?")
    train_box = row.get("train/box_loss", "?")
    train_cls = row.get("train/cls_loss", "?")
    val_box = row.get("val/box_loss", "?")
    val_cls = row.get("val/cls_loss", "?")
    map50 = row.get("metrics/mAP50(B)", "?")
    map50_95 = row.get("metrics/mAP50-95(B)", "?")
    precision = row.get("metrics/precision(B)", "?")
    recall = row.get("metrics/recall(B)", "?")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    live_progress = get_live_progress()
    sys_stats = get_system_stats()

    msg = (
        f"📊 <b>Training Progress Update</b>\n"
        f"🕐 {now}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{sys_stats}"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{live_progress}"
        f"📈 Last Completed Epoch: <b>{epoch}</b> (of {total_epochs} total)\n"
        f"\n"
        f"<b>Train Loss:</b>\n"
        f"  📦 Box: {train_box}\n"
        f"  🏷️ Cls: {train_cls}\n"
        f"\n"
        f"<b>Val Loss:</b>\n"
        f"  📦 Box: {val_box}\n"
        f"  🏷️ Cls: {val_cls}\n"
        f"\n"
        f"<b>Metrics:</b>\n"
        f"  🎯 mAP50: {map50}\n"
        f"  🎯 mAP50-95: {map50_95}\n"
        f"  ✅ Precision: {precision}\n"
        f"  🔄 Recall: {recall}\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    return msg


def send_event(event_type: str, details: str = ""):
    """Send an event notification."""
    icons = {
        "start": "🚀",
        "complete": "✅",
        "crash": "🔴",
        "progress": "📊",
        "dataset": "📁",
    }
    icon = icons.get(event_type, "ℹ️")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"{icon} <b>{event_type.upper()}</b> — {now}\n{details}"
    send_telegram(msg)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "progress":
            msg = format_progress_message()
            send_telegram(msg)
        elif cmd == "start":
            send_event("start", "Training is starting on Raspberry Pi 5...")
        elif cmd == "complete":
            msg = format_progress_message()
            send_event("complete", f"Training finished!\n\n{msg}")
        elif cmd == "crash":
            tb = sys.argv[2] if len(sys.argv) > 2 else "Unknown error"
            send_event("crash", f"Training crashed!\n<pre>{tb[:500]}</pre>")
        elif cmd == "test":
            send_telegram("✅ Telegram bot is working! Connected to Raspberry Pi 5.")
        else:
            send_telegram(f"ℹ️ {cmd}: {' '.join(sys.argv[2:])}")
    else:
        msg = format_progress_message()
        send_telegram(msg)
