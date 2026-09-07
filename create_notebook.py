import json

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": ["# Threat Detection ML Training Pipeline\n", "Run this notebook in Google Colab to train your YOLOv8 model for the prototype."]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": ["!pip install ultralytics roboflow -q\n", "import ultralytics\n", "ultralytics.checks()"]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": ["from roboflow import Roboflow\n", "# WARNING: Enter your Roboflow API key below to download the dataset\n", "rf = Roboflow(api_key='YOUR_API_KEY_HERE')\n", "project = rf.workspace('yolov7test-u13vc').project('weapon-detection-m7qso')\n", "version = project.version(1)\n", "dataset = version.download('yolov8')"]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": ["from ultralytics import YOLO\n", "\n", "# Load a pretrained YOLO model\n", "model = YOLO('yolov8n.pt')\n", "\n", "# Train the model on the dataset for 50 epochs (change if needed)\n", "model.train(data=f\"{dataset.location}/data.yaml\", epochs=50, imgsz=640)\n"]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": ["# Once done, download the resulting model weights\n", "import shutil\n", "from google.colab import files\n", "shutil.make_archive('runs', 'zip', 'runs')\n", "files.download('runs.zip')"]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}

with open('c:/SIP-Prototype/Prototype/code.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=1)
print('Notebook overwritten successfully.')
