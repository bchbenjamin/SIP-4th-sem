#!/usr/bin/env python3
"""
Download additional weapon detection datasets and merge all into a unified YOLO dataset.
Runs on Raspberry Pi 5.
"""

import os
import sys
import shutil
import subprocess
import glob
import random
import yaml

HOME = os.path.expanduser("~")
DATASETS_DIR = os.path.join(HOME, "edge-ai", "weapon_datasets")
UNIFIED_DIR = os.path.join(HOME, "edge-ai", "unified_weapon_dataset")
VENV_PIP = os.path.join(HOME, "edge-ai", "pi", ".venv", "bin", "pip")
VENV_PYTHON = os.path.join(HOME, "edge-ai", "pi", ".venv", "bin", "python3")

# Unified class mapping
CLASSES = ["gun", "knife"]


def log(msg):
    print(f"[dataset] {msg}", flush=True)


def check_disk_space():
    """Return free space in GB."""
    stat = os.statvfs(HOME)
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
    return free_gb


def download_kaggle_datasets():
    """Download weapon datasets from Kaggle using kagglehub."""
    log("Installing/upgrading kagglehub...")
    subprocess.run([VENV_PIP, "install", "--quiet", "kagglehub"], check=False)

    kaggle_datasets = [
        "snehilsanyal/weapon-detection-test",
        "simuletic/cctv-knife-detection-dataset",
    ]

    downloaded = []
    for ds_name in kaggle_datasets:
        free = check_disk_space()
        log(f"Free disk: {free:.1f}GB")
        if free < 3:
            log(f"Skipping {ds_name} — less than 3GB free")
            continue

        log(f"Downloading Kaggle dataset: {ds_name}")
        try:
            result = subprocess.run(
                [VENV_PYTHON, "-c", f"""
import kagglehub
path = kagglehub.dataset_download("{ds_name}")
print(path)
"""],
                capture_output=True, text=True, timeout=1800
            )
            if result.returncode == 0:
                path = result.stdout.strip().split("\n")[-1]
                log(f"Downloaded to: {path}")
                downloaded.append(("kaggle_" + ds_name.split("/")[-1], path))
            else:
                log(f"Failed: {result.stderr[:300]}")
        except Exception as e:
            log(f"Error downloading {ds_name}: {e}")

    return downloaded


def download_github_datasets():
    """Clone weapon detection repos from GitHub."""
    repos = [
        ("OD-WeaponDetection", "https://github.com/ari-dasci/OD-WeaponDetection.git"),
    ]

    downloaded = []
    for name, url in repos:
        free = check_disk_space()
        if free < 3:
            log(f"Skipping {name} — less than 3GB free")
            continue

        dest = os.path.join(DATASETS_DIR, name)
        if os.path.exists(dest):
            log(f"{name} already exists, skipping clone")
            downloaded.append((name, dest))
            continue

        log(f"Cloning {url}...")
        try:
            # Shallow clone to save space
            subprocess.run(
                ["git", "clone", "--depth", "1", url, dest],
                timeout=600, check=True
            )
            log(f"Cloned to: {dest}")
            downloaded.append((name, dest))
        except Exception as e:
            log(f"Error cloning {name}: {e}")

    return downloaded


def find_yolo_images_and_labels(root_dir):
    """Recursively find image/label pairs in YOLO format."""
    pairs = []
    image_exts = {".jpg", ".jpeg", ".png", ".bmp"}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in image_exts:
                img_path = os.path.join(dirpath, f)
                # Look for corresponding label file
                base = os.path.splitext(f)[0]

                # Try same directory
                label_path = os.path.join(dirpath, base + ".txt")

                # Try replacing 'images' with 'labels' in path
                if not os.path.exists(label_path):
                    label_path = os.path.join(
                        dirpath.replace("/images", "/labels").replace("\\images", "\\labels"),
                        base + ".txt"
                    )

                if os.path.exists(label_path):
                    pairs.append((img_path, label_path))

    return pairs


def remap_classes(label_path, class_mapping):
    """Read a YOLO label file and remap class IDs. Returns list of remapped lines."""
    lines = []
    with open(label_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 5:
                old_cls = int(parts[0])
                if old_cls in class_mapping:
                    new_cls = class_mapping[old_cls]
                    parts[0] = str(new_cls)
                    lines.append(" ".join(parts))
    return lines


def merge_datasets():
    """Merge all datasets into a unified YOLO dataset."""
    log("=== Merging all datasets ===")

    os.makedirs(UNIFIED_DIR, exist_ok=True)
    for split in ["train", "valid", "test"]:
        os.makedirs(os.path.join(UNIFIED_DIR, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(UNIFIED_DIR, split, "labels"), exist_ok=True)

    all_pairs = []
    idx = 0

    # === 1. Original Roboflow dataset ===
    roboflow_dir = os.path.join(HOME, "gun-and-knife-detection-1")
    if os.path.exists(roboflow_dir):
        log(f"Processing Roboflow dataset at {roboflow_dir}")
        # Roboflow classes: 0=gun, 1=knife (already matches our unified schema)
        class_map = {0: 0, 1: 1}

        for split_name, split_dir in [("train", "train"), ("valid", "valid"), ("test", "test")]:
            img_dir = os.path.join(roboflow_dir, split_dir, "images")
            if os.path.exists(img_dir):
                pairs = find_yolo_images_and_labels(img_dir)
                log(f"  Roboflow {split_name}: {len(pairs)} image-label pairs")
                for img_path, lbl_path in pairs:
                    ext = os.path.splitext(img_path)[1]
                    new_name = f"rf_{idx:06d}"
                    idx += 1

                    dst_img = os.path.join(UNIFIED_DIR, split_name, "images", new_name + ext)
                    dst_lbl = os.path.join(UNIFIED_DIR, split_name, "labels", new_name + ".txt")

                    shutil.copy2(img_path, dst_img)
                    remapped = remap_classes(lbl_path, class_map)
                    with open(dst_lbl, "w") as f:
                        f.write("\n".join(remapped) + "\n" if remapped else "")

    # === 2. Kaggle datasets ===
    kaggle_dir = os.path.join(os.path.expanduser("~/.cache/kagglehub/datasets"))
    if os.path.exists(kaggle_dir):
        for ds_name in os.listdir(kaggle_dir):
            ds_path = os.path.join(kaggle_dir, ds_name)
            log(f"Scanning Kaggle dataset: {ds_name}")

            # Check if there's a data.yaml to understand class mapping
            yaml_files = glob.glob(os.path.join(ds_path, "**", "data.yaml"), recursive=True)
            class_map = {0: 0, 1: 1}  # Default

            if yaml_files:
                try:
                    with open(yaml_files[0], "r") as f:
                        ds_yaml = yaml.safe_load(f)
                    if "names" in ds_yaml:
                        names = ds_yaml["names"]
                        if isinstance(names, list):
                            for i, name in enumerate(names):
                                name_lower = name.lower()
                                if "gun" in name_lower or "pistol" in name_lower or "rifle" in name_lower or "firearm" in name_lower or "weapon" in name_lower:
                                    class_map[i] = 0  # gun
                                elif "knife" in name_lower or "blade" in name_lower:
                                    class_map[i] = 1  # knife
                                else:
                                    class_map[i] = 0  # Default to gun for other weapon types
                except Exception:
                    pass

            pairs = find_yolo_images_and_labels(ds_path)
            log(f"  Found {len(pairs)} image-label pairs")

            if pairs:
                # Split 80/10/10
                random.shuffle(pairs)
                n = len(pairs)
                train_end = int(n * 0.8)
                val_end = int(n * 0.9)
                splits = {
                    "train": pairs[:train_end],
                    "valid": pairs[train_end:val_end],
                    "test": pairs[val_end:],
                }

                for split_name, split_pairs in splits.items():
                    for img_path, lbl_path in split_pairs:
                        ext = os.path.splitext(img_path)[1]
                        new_name = f"kg_{idx:06d}"
                        idx += 1

                        dst_img = os.path.join(UNIFIED_DIR, split_name, "images", new_name + ext)
                        dst_lbl = os.path.join(UNIFIED_DIR, split_name, "labels", new_name + ".txt")

                        shutil.copy2(img_path, dst_img)
                        remapped = remap_classes(lbl_path, class_map)
                        with open(dst_lbl, "w") as f:
                            f.write("\n".join(remapped) + "\n" if remapped else "")

    # === 3. GitHub OD-WeaponDetection ===
    github_dir = os.path.join(DATASETS_DIR, "OD-WeaponDetection")
    if os.path.exists(github_dir):
        log(f"Processing GitHub OD-WeaponDetection")
        pairs = find_yolo_images_and_labels(github_dir)
        log(f"  Found {len(pairs)} image-label pairs")

        # Attempt to find data.yaml for class mapping
        yaml_files = glob.glob(os.path.join(github_dir, "**", "*.yaml"), recursive=True)
        class_map = {0: 0, 1: 1}
        for yf in yaml_files:
            try:
                with open(yf, "r") as f:
                    ds_yaml = yaml.safe_load(f)
                if "names" in ds_yaml:
                    names = ds_yaml["names"]
                    if isinstance(names, list):
                        for i, name in enumerate(names):
                            name_lower = name.lower()
                            if "gun" in name_lower or "pistol" in name_lower:
                                class_map[i] = 0
                            elif "knife" in name_lower:
                                class_map[i] = 1
                            else:
                                class_map[i] = 0
                    break
            except Exception:
                continue

        if pairs:
            random.shuffle(pairs)
            n = len(pairs)
            train_end = int(n * 0.8)
            val_end = int(n * 0.9)
            splits = {
                "train": pairs[:train_end],
                "valid": pairs[train_end:val_end],
                "test": pairs[val_end:],
            }

            for split_name, split_pairs in splits.items():
                for img_path, lbl_path in split_pairs:
                    ext = os.path.splitext(img_path)[1]
                    new_name = f"gh_{idx:06d}"
                    idx += 1

                    dst_img = os.path.join(UNIFIED_DIR, split_name, "images", new_name + ext)
                    dst_lbl = os.path.join(UNIFIED_DIR, split_name, "labels", new_name + ".txt")

                    shutil.copy2(img_path, dst_img)
                    remapped = remap_classes(lbl_path, class_map)
                    with open(dst_lbl, "w") as f:
                        f.write("\n".join(remapped) + "\n" if remapped else "")

    # === Count final dataset ===
    stats = {}
    for split in ["train", "valid", "test"]:
        img_count = len(os.listdir(os.path.join(UNIFIED_DIR, split, "images")))
        lbl_count = len(os.listdir(os.path.join(UNIFIED_DIR, split, "labels")))
        stats[split] = {"images": img_count, "labels": lbl_count}
        log(f"  {split}: {img_count} images, {lbl_count} labels")

    # === Write data.yaml ===
    data_yaml = {
        "path": UNIFIED_DIR,
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": len(CLASSES),
        "names": CLASSES,
    }
    yaml_path = os.path.join(UNIFIED_DIR, "data.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(data_yaml, f, default_flow_style=False)

    log(f"Unified dataset written to {UNIFIED_DIR}")
    log(f"data.yaml: {yaml_path}")
    log(f"Total: {sum(s['images'] for s in stats.values())} images across all splits")

    return yaml_path, stats


def main():
    os.makedirs(DATASETS_DIR, exist_ok=True)

    log(f"Free disk space: {check_disk_space():.1f}GB")

    log("=== Downloading Kaggle datasets ===")
    kaggle_ds = download_kaggle_datasets()
    log(f"Downloaded {len(kaggle_ds)} Kaggle datasets")

    log("=== Downloading GitHub datasets ===")
    github_ds = download_github_datasets()
    log(f"Downloaded {len(github_ds)} GitHub datasets")

    log("=== Merging all datasets ===")
    yaml_path, stats = merge_datasets()

    # Send Telegram notification about dataset
    try:
        sys.path.insert(0, os.path.join(HOME, "edge-ai"))
        from telegram_notify import send_telegram
        total = sum(s["images"] for s in stats.values())
        msg = (
            f"📁 <b>Dataset Preparation Complete</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Total images: <b>{total}</b>\n"
            f"  🏋️ Train: {stats['train']['images']}\n"
            f"  📋 Valid: {stats['valid']['images']}\n"
            f"  🧪 Test: {stats['test']['images']}\n"
            f"🏷️ Classes: gun, knife\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        send_telegram(msg)
    except Exception as e:
        log(f"Telegram notification failed: {e}")

    return yaml_path


if __name__ == "__main__":
    main()
