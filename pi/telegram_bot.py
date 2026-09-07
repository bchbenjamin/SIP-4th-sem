#!/usr/bin/env python3
"""
Interactive Telegram Bot for Raspberry Pi 5.
- Responds to text messages with training status (rate-limited).
- Responds to image uploads with YOLOv8 inference.
"""

import os
import sys
import time
import requests
from io import BytesIO
from PIL import Image

HOME = os.path.expanduser("~")
sys.path.insert(0, os.path.join(HOME, "edge-ai"))
import telegram_notify

import dotenv
dotenv.load_dotenv(os.path.join(HOME, "edge-ai", ".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_CHAT_IDS = os.getenv("ALLOWED_CHAT_IDS", "").split(",")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

BOT_CACHE = os.path.join(HOME, "edge-ai", "bot_cache")
os.makedirs(BOT_CACHE, exist_ok=True)

# Rate limiting
LAST_TEXT_TIME = 0
TEXT_COOLDOWN = 10  # Seconds

# YOLO model cache
_yolo_model = None

def get_model():
    """Lazy load YOLO model."""
    global _yolo_model
    if _yolo_model is not None:
        return _yolo_model
        
    from ultralytics import YOLO
    
    # Check for best/last checkpoint first
    best_pt = os.path.join(HOME, "runs", "detect", "train", "weights", "best.pt")
    last_pt = os.path.join(HOME, "runs", "detect", "train", "weights", "last.pt")
    
    if os.path.exists(best_pt):
        print(f"Loading {best_pt}...")
        _yolo_model = YOLO(best_pt)
    elif os.path.exists(last_pt):
        print(f"Loading {last_pt}...")
        _yolo_model = YOLO(last_pt)
    else:
        print(f"Loading fallback yolov8n.pt...")
        _yolo_model = YOLO("yolov8n.pt")
        
    return _yolo_model


def handle_text(text, chat_id):
    """Handle incoming text messages."""
    global LAST_TEXT_TIME
    
    if str(chat_id) not in ALLOWED_CHAT_IDS:
        return  # Ignore messages from unauthorized users
        
    now = time.time()
    if now - LAST_TEXT_TIME < TEXT_COOLDOWN:
        print(f"Ignoring text message from {chat_id}: rate limited")
        return
        
    LAST_TEXT_TIME = now
    
    # Send progress
    msg = telegram_notify.format_progress_message()
    telegram_notify.send_telegram(msg, chat_id=str(chat_id))


def handle_photo(photo_list, chat_id):
    """Handle incoming photos."""
    if str(chat_id) not in ALLOWED_CHAT_IDS:
        return  # Ignore unauthorized
        
    print("Processing photo...")
    # photo_list is a list of PhotoSize objects. Pick the largest.
    photo = sorted(photo_list, key=lambda x: x["file_size"])[-1]
    file_id = photo["file_id"]
    
    # 1. Get file path
    resp = requests.get(f"{API_URL}/getFile?file_id={file_id}").json()
    if not resp.get("ok"):
        print("Failed to getFile")
        return
        
    file_path = resp["result"]["file_path"]
    
    # 2. Download file
    download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    img_resp = requests.get(download_url)
    
    in_path = os.path.join(BOT_CACHE, "input.jpg")
    out_path = os.path.join(BOT_CACHE, "output.jpg")
    
    with open(in_path, "wb") as f:
        f.write(img_resp.content)
        
    # 3. Run inference
    try:
        model = get_model()
        results = model.predict(in_path, save=False, conf=0.25)
        
        # Save annotated image
        res = results[0]
        res.save(filename=out_path)
        
        # Count detections
        boxes = res.boxes
        num_detections = len(boxes)
        
        caption = f"🔍 <b>Detection Results:</b>\nFound {num_detections} object(s)."
        
    except Exception as e:
        print(f"Inference error: {e}")
        caption = f"⚠️ Inference failed: {e}"
        # Fallback to original image if plotting fails
        import shutil
        shutil.copy(in_path, out_path)
        
    # 4. Upload photo
    with open(out_path, "rb") as f:
        requests.post(
            f"{API_URL}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
            files={"photo": f}
        )
        
    # Cleanup
    try:
        os.remove(in_path)
        os.remove(out_path)
    except:
        pass


def poll():
    """Main polling loop."""
    print("Bot starting...")
    offset = None
    
    while True:
        try:
            url = f"{API_URL}/getUpdates?timeout=30"
            if offset:
                url += f"&offset={offset}"
                
            resp = requests.get(url, timeout=40)
            data = resp.json()
            
            if data.get("ok"):
                for update in data["result"]:
                    offset = update["update_id"] + 1
                    
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        
                        if "text" in msg:
                            handle_text(msg["text"], chat_id)
                        elif "photo" in msg:
                            handle_photo(msg["photo"], chat_id)
                            
            time.sleep(1)
            
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    poll()
