import os
from roboflow import Roboflow
import shutil

def main():
    print("Downloading dataset from Roboflow...")
    rf = Roboflow(api_key='mCMBhfrder6POXLGvIll')
    project = rf.workspace('yolov7test-u13vc').project('weapon-detection-m7qso')
    version = project.version(1)
    dataset = version.download('yolov8')
    
    print(f"Dataset downloaded to: {dataset.location}")
    
    source_dir = os.path.join(dataset.location, "train", "images")
    if not os.path.exists(source_dir):
        source_dir = os.path.join(dataset.location, "valid", "images")
    
    test_dir = r"c:\SIP-Prototype\Prototype\weapon_samples"
    os.makedirs(test_dir, exist_ok=True)
    
    artifact_dir = r"C:\Users\Benjamin B C H\.gemini\antigravity-ide\brain\8fec7a48-c4a1-46c8-8173-b76367b5e431"
    
    images = os.listdir(source_dir)
    selected_images = images[:20]
    
    for img in selected_images:
        src = os.path.join(source_dir, img)
        dst = os.path.join(test_dir, img)
        dst_artifact = os.path.join(artifact_dir, img)
        shutil.copy(src, dst)
        shutil.copy(src, dst_artifact)
        
    print(f"Copied 20 images to {test_dir} and artifact directory.")
    
    # Generate the carousel markdown
    markdown = "# Weapon Detection Sample Images\n\nHere are 20 sample images extracted from the custom `weapon-detection` dataset you used for training.\n\n````carousel\n"
    for idx, img in enumerate(selected_images):
        markdown += f"![{img}](/C:/Users/Benjamin%20B%20C%20H/.gemini/antigravity-ide/brain/8fec7a48-c4a1-46c8-8173-b76367b5e431/{img})\n"
        if idx < len(selected_images) - 1:
            markdown += "<!-- slide -->\n"
    markdown += "````\n"
    
    with open(os.path.join(artifact_dir, "weapon_samples.md"), "w") as f:
        f.write(markdown)
    
    print("Markdown generated.")

if __name__ == "__main__":
    main()
