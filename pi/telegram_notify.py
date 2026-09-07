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
RESULTS_CSV = os.path.expanduser("~/runs/detect/train/results.csv")


def send_telegram(message: str, chat_id: str = None):
    """Send a message via Telegram Bot API."""
    if chat_id is None:
        chat_id = PRIMARY_CHAT_ID
        
    if not chat_id or not BOT_TOKEN:
        print("Telegram credentials missing.", file=sys.stderr)
        return None
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }).encode()
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"Telegram send failed: {e}", file=sys.stderr)
        return None


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

    msg = (
        f"📊 <b>Training Progress Update</b>\n"
        f"🕐 {now}\n"
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
