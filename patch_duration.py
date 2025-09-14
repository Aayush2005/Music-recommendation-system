import json
import os
from mutagen.mp3 import MP3

DATASETS_DIR = "datasets"
METADATA_FILE = "metadata.json"

def patch_durations_from_local():
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    updated = False
    for filename, info in metadata.items():
        if info.get("duration"):  # skip if already filled
            continue

        file_path = os.path.join(DATASETS_DIR, filename)
        if not os.path.exists(file_path):
            print(f"[!] File not found: {file_path}")
            continue

        try:
            audio = MP3(file_path)
            duration = int(audio.info.length)  # in seconds
            info["duration"] = duration
            updated = True
            print(f"[+] Patched duration for {filename} → {duration}s")
        except Exception as e:
            print(f"[x] Error reading duration for {filename}: {e}")

    if updated:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print("Durations patched from local files ✅")
    else:
        print("No missing durations to patch")

if __name__ == "__main__":
    patch_durations_from_local()
