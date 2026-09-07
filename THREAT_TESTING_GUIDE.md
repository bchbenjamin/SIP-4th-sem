# Threat Testing & Deterrence Guide

This guide explains how to demonstrate the AI-Powered Street Safety Device's deterrence capabilities using the laptop prototype and Raspberry Pi.

## 1. Using the Base Model Immediately
You **do not** need to wait for the custom Colab training to finish to test the prototype! The default `yolov8n.pt` model already knows how to detect several threats.

**Tier 1 (Animals) - Triggers Deterrent Audio/Light:**
- Open a picture of a **dog**, **bear**, **elephant**, or **zebra** on your phone.
- Hold it up to the laptop webcam.
- The Raspberry Pi will classify it as a Tier 1 threat and automatically play `siren.wav` using `aplay`.

**Tier 2 (Severe Threats / Weapons) - Triggers Alert System:**
- Open a picture of a **knife** on your phone.
- Hold it up to the webcam.
- The Raspberry Pi will classify it as a Tier 2 threat. We have modified the Pi to recognize `knife` (COCO class ID 43) as a severe weapon threat.

## 2. Generating the Siren Audio
I have created a Python script on the Raspberry Pi to generate a loud, oscillating siren tone.
Run this on your Raspberry Pi to ensure the audio file exists:
```bash
python3 ~/edge-ai/pi/generate_siren.py
```
This will create `siren.wav` in your Pi folder. When the Pi detects a Tier 1 threat (or you reconfigure it for Tier 2), it executes: `aplay siren.wav &` which will play through the Pi's connected speaker.

## 3. Training a Custom Model in Google Colab (Optional)
If you want to train the model to detect guns and other weapons not found in the base YOLOv8 model:

1. I have prepared `code.ipynb` in your repository.
2. Ensure you have the VS Code Colab extension synced, or upload `code.ipynb` to Google Drive and open it in Google Colab.
3. Replace `YOUR_API_KEY_HERE` in the second cell with your Roboflow API key.
4. Go to **Runtime > Run all**.
5. **You can go to sleep!** It will automatically download the dataset, train for 50 epochs, package the results into a `.zip`, and prompt you to download the trained `best.pt` weights.
6. Once downloaded, replace `yolov8n.pt` on your Raspberry Pi with the new model weights.
