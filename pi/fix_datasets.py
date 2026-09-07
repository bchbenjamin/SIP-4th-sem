import os
import cv2

video_dir = os.path.expanduser("~/edge-ai/test_videos")
os.makedirs(video_dir, exist_ok=True)

img_dir = os.path.expanduser("~/.cache/kagglehub/datasets/odins0n/ucf-crime-dataset/versions/1/Train/Assault")
try:
    img_paths = [os.path.join(img_dir, f) for f in os.listdir(img_dir) if f.endswith(".png")]
    # sort by number inside the filename
    img_paths.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))
    img_paths = img_paths[:200]

    if img_paths:
        print(f"Found {len(img_paths)} images, generating MP4...")
        first_img = cv2.imread(img_paths[0])
        h, w, _ = first_img.shape
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(os.path.join(video_dir, 'synthetic_weapon_video.mp4'), fourcc, 10.0, (w, h))
        
        for img_path in img_paths:
            img = cv2.imread(img_path)
            if img is not None:
                img = cv2.resize(img, (w, h))
                out.write(img)
        out.release()
        print("Successfully created synthetic_weapon_video.mp4")
    else:
        print("No PNGs found!")
except Exception as e:
    print("Error:", e)
