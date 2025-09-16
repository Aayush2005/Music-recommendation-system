import os
import re
from mutagen.mp3 import MP3

DATASET_DIR = "datasets"
DOWNLOADED_FILE = "downloaded_songs.txt"
MAX_DURATION_SEC = 10 * 60  # 10 minutes

# Suffixes to normalize for duplicates
suffixes = ["LYRICAL", "FULL VIDEO", "REPRISE", "ACOUSTIC", "VERSION", "EDIT"]

# Keywords to delete outright
delete_keywords = ["REMIX", "MASHUP"]

# Regex to remove emojis
emoji_pattern = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001F900-\U0001F9FF"
    "\U00002600-\U000026FF"
    "\U00002B00-\U00002BFF"
    "\U0001FA70-\U0001FAFF"
    "]+",
    flags=re.UNICODE,
)

def normalize_title(title):
    title = os.path.splitext(title)[0]
    for suf in suffixes:
        title = re.sub(rf"\b{suf}\b", "", title, flags=re.IGNORECASE)
    title = emoji_pattern.sub("", title)
    title = re.sub(r"[^a-zA-Z0-9 ]", "", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip().lower()

# Read downloaded_songs.txt if it exists
if os.path.exists(DOWNLOADED_FILE):
    with open(DOWNLOADED_FILE, "r", encoding="utf-8") as f:
        downloaded_songs = [line.strip() for line in f if line.strip()]
else:
    downloaded_songs = []

# Map normalized titles to original for filtering
norm_to_original = {}
deleted_files = []

for f in os.listdir(DATASET_DIR):
    if not f.lower().endswith(".mp3"):
        continue

    # Delete if REMIX/MASHUP in name
    if any(kw.lower() in f.lower() for kw in delete_keywords):
        os.remove(os.path.join(DATASET_DIR, f))
        deleted_files.append(f)
        continue

    # Delete if duration > 10 min
    try:
        duration = MP3(os.path.join(DATASET_DIR, f)).info.length
        if duration > MAX_DURATION_SEC:
            os.remove(os.path.join(DATASET_DIR, f))
            deleted_files.append(f)
            continue
    except Exception as e:
        print(f"⚠️ Failed to read duration for {f}: {e}")
        continue

    # Handle duplicates by normalized name
    norm = normalize_title(f)
    if norm in norm_to_original:
        os.remove(os.path.join(DATASET_DIR, f))
        deleted_files.append(f)
    else:
        norm_to_original[norm] = f

# Update downloaded_songs.txt with remaining valid songs
remaining_titles = [os.path.splitext(f)[0] for f in norm_to_original.values()]
with open(DOWNLOADED_FILE, "w", encoding="utf-8") as f:
    for title in remaining_titles:
        f.write(title + "\n")

print(f"✅ Cleanup done. Deleted {len(deleted_files)} files.")
print(f"✅ Updated {DOWNLOADED_FILE} with {len(remaining_titles)} valid songs.")
