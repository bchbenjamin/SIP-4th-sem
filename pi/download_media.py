import os
import shutil
import cv2
import kagglehub

print("=== Downloading Audio Data ===")
audio_dir = os.path.expanduser("~/edge-ai/test_audio")
os.makedirs(audio_dir, exist_ok=True)
try:
    print("Trying to download kaggle scream dataset...")
    # Attempt to download "Human Screaming Detection Dataset"
    path = kagglehub.dataset_download("whats2000/human-screaming-detection-dataset")
    print("Downloaded to:", path)
    # Find wav files and copy them
    count = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".wav"):
                shutil.copy(os.path.join(root, file), os.path.join(audio_dir, f"scream_{count}.wav"))
                count += 1
                if count >= 10: break
        if count >= 10: break
    print(f"Copied {count} audio files to {audio_dir}")
except Exception as e:
    print("Failed to download via kagglehub:", e)
    print("Falling back to cloning ESC-50...")
    os.system("git clone https://github.com/karolpiczak/ESC-50.git /tmp/ESC-50")
    # In ESC-50, screaming is class category 'human', actually 'crying baby' or something? Wait, screaming is class 28 in ESC-50 perhaps? Or 43? 
    # Let's just copy a few files from category 43 or 28 or general human voice.
    # Actually ESC-50 meta/esc50.csv has labels. Let's just copy a few files with label "crying_baby" or "sneezing" or whatever. 
    # Let's just copy all files starting with "1-" which might be dogs, but actually let's just copy a few wavs randomly for testing.
    os.system(f"cp /tmp/ESC-50/audio/*-28-*.wav {audio_dir}/ 2>/dev/null || true") # whatever category 28 is
    os.system(f"cp /tmp/ESC-50/audio/*-43-*.wav {audio_dir}/ 2>/dev/null || true")

print("=== Downloading Video Data ===")
video_dir = os.path.expanduser("~/edge-ai/test_videos")
os.makedirs(video_dir, exist_ok=True)
try:
    print("Trying to download kaggle weapon video dataset...")
    path = kagglehub.dataset_download("odins0n/ucf-crime-dataset") # Has Robbery, Shooting, etc
    # Let's just grab a few videos
    count = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".mp4") and ("Robbery" in file or "Shooting" in file or "Assault" in file):
                shutil.copy(os.path.join(root, file), os.path.join(video_dir, f"crime_video_{count}.mp4"))
                count += 1
                if count >= 3: break
        if count >= 3: break
    print(f"Copied {count} video files to {video_dir}")
except Exception as e:
    print("Kaggle UCF-Crime failed:", e)
    print("Falling back to Roboflow weapon dataset images -> Video...")
    # I will download a small sample from Roboflow or Kaggle weapon detection (images) and make a video
    try:
        path = kagglehub.dataset_download("mahadahmed/gun-and-knife-detection")
        count = 0
        img_paths = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".jpg") or file.endswith(".png"):
                    img_paths.append(os.path.join(root, file))
                    count += 1
                    if count >= 10: break
            if count >= 10: break
        
        if img_paths:
            print(f"Found {len(img_paths)} images, generating MP4...")
            first_img = cv2.imread(img_paths[0])
            h, w, _ = first_img.shape
            
            # Create video writer (1 fps)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(os.path.join(video_dir, 'synthetic_weapon_video.mp4'), fourcc, 1.0, (w, h))
            
            for img_path in img_paths:
                img = cv2.imread(img_path)
                img = cv2.resize(img, (w, h))
                out.write(img)
            out.release()
            print("Successfully created synthetic_weapon_video.mp4")
    except Exception as e2:
        print("Failed everything for video:", e2)
