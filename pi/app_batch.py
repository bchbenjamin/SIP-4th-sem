import os
import cv2
import argparse
from ultralytics import YOLO

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confidence", type=float, default=0.6)
    parser.add_argument("--model", default="yolov8n.pt")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    
    print(f"Loading model {args.model}...")
    model = YOLO(args.model)
    
    for filename in os.listdir(args.input_dir):
        if not (filename.endswith(".mp4") or filename.endswith(".avi") or filename.endswith(".mov")):
            continue
            
        filepath = os.path.join(args.input_dir, filename)
        print(f"Processing video {filepath}...")
        
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            print(f"Failed to open {filepath}")
            continue
            
        frame_idx = 0
        saved_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            results = model.predict(frame, conf=args.confidence, verbose=False)
            result = results[0]
            
            # If there are any detections above the confidence threshold
            if len(result.boxes) > 0:
                max_conf = float(result.boxes.conf.max())
                annotated = result.plot()
                
                out_path = os.path.join(args.output_dir, f"{os.path.splitext(filename)[0]}_frame{frame_idx}_conf{max_conf:.2f}.png")
                cv2.imwrite(out_path, annotated)
                saved_count += 1
                
            frame_idx += 1
            
        cap.release()
        print(f"Finished {filepath}: processed {frame_idx} frames, saved {saved_count} detections.")

if __name__ == "__main__":
    main()
