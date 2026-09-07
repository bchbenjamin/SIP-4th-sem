import os
import time
from ultralytics import YOLO, settings

def main():
    # Fix dataset permission error by setting local dataset directory
    dataset_dir = os.path.abspath(os.path.join(os.getcwd(), "datasets"))
    os.makedirs(dataset_dir, exist_ok=True)
    settings.update({'datasets_dir': dataset_dir})
    
    print("Starting YOLOv8 training on prototype dataset for exactly 3 hours...")
    
    # Load the base nano model
    model = YOLO("yolov8n.pt")
    
    # Ultralytics supports a 'time' argument (in hours) to automatically stop training
    # We use coco128.yaml which contains people, cars, animals, and knives (COCO classes).
    # This acts as our prototype "threat" dataset since it contains weapons (knives) and wild animals.
    
    try:
        model.train(
            data="coco128.yaml",
            epochs=2000,       # Set arbitrarily high so the time limit kicks in first
            time=3.0,          # Exactly 3.0 hours limit
            imgsz=640,
            batch=4,           # Small batch size for laptop CPU
            device="cpu",      # Force CPU since we are running locally on the laptop
            project="ml_pipeline/runs",
            name="threat_detection_prototype"
        )
        print("Training completed successfully after 3 hours.")
    except Exception as e:
        print(f"Training interrupted or failed: {e}")

if __name__ == "__main__":
    # Ensure ml_pipeline directory exists
    os.makedirs("ml_pipeline", exist_ok=True)
    main()
