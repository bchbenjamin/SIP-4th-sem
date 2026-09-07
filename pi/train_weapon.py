import os
import roboflow
from ultralytics import YOLO

def main():
    print("Initializing Roboflow...")
    # Get API key from env or hardcode for now if env not loaded.
    # The Pi does not have .env loaded natively in this shell, but I can use the key the user provided.
    rf = roboflow.Roboflow(api_key="mCMBhfrder6POXLGvIll")
    
    # Download gun/knife detection dataset (this is Mahad Ahmed's dataset mentioned in context)
    # The universe project is mahad-ahmed/gun-and-knife-detection
    print("Downloading dataset...")
    project = rf.workspace("mahad-ahmed").project("gun-and-knife-detection")
    # Actually wait, let's use a smaller dataset if possible, or just standard download
    # A known good weapon dataset: simuletic/cctv-knife-detection-dataset-zkkaf
    try:
        dataset = project.version(1).download("yolov8")
    except Exception as e:
        print("Failed to download mahad-ahmed, trying simuletic...", e)
        project = rf.workspace("simuletic").project("cctv-knife-detection-dataset-zkkaf")
        dataset = project.version(1).download("yolov8")

    print(f"Dataset downloaded to {dataset.location}")
    
    print("Loading YOLOv8n model...")
    model = YOLO("yolov8n.pt")
    
    print("Starting training (25 epochs, checkpoints every 10)...")
    model.train(
        data=f"{dataset.location}/data.yaml",
        epochs=25,
        batch=2,  # small batch for RPi5 4GB
        imgsz=320, # small imgsz for speed/memory
        device="cpu",
        save_period=10,
        project="runs/detect",
        name="train",
        exist_ok=True,
    )
    
    print("Training finished!")
    if os.path.exists("runs/detect/train/results.png"):
        print("results.png confirmed generated.")
    else:
        print("results.png NOT found!")

if __name__ == "__main__":
    main()
