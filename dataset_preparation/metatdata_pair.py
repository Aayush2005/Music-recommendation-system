import re
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import requests
import urllib.parse

DATASETS_DIR = "datasets"
METADATA_OUTPUT = "metadata.json"
NUM_THREADS = 10


# -------- CLEANING --------
def clean_title(raw_title: str) -> str:
    """
    Clean up raw filenames into likely song titles for API search.
    """
    title = raw_title

    # 1. Remove extension if present
    title = os.path.splitext(title)[0]

    # 2. Remove text inside parentheses/brackets
    title = re.sub(r"\([^)]*\)", "", title)
    title = re.sub(r"\[[^]]*\]", "", title)

    # 3. Remove common junk words
    junk_patterns = [
        r"\bofficial\b", r"\bvideo\b", r"\bfull\b", r"\blyrical\b",
        r"\bsong\b", r"\bfeat\b", r"\bfrom\b", r"\bmix\b", r"\bversion\b",
    ]
    for jp in junk_patterns:
        title = re.sub(jp, "", title, flags=re.IGNORECASE)

    # 4. Cut off after "-" or "|" (actors/singers often listed after this)
    if "-" in title:
        title = title.split("-")[0]
    if "|" in title:
        title = title.split("|")[0]

    # 5. Remove emojis and non-alphanumeric chars except space & basic punctuation
    title = re.sub(r"[^\w\s&']", " ", title)

    # 6. Normalize spaces
    title = re.sub(r"\s+", " ", title).strip()

    return title


# -------- UTILS --------
def list_mp3_files(directory):
    return [f for f in os.listdir(directory) if f.lower().endswith(".mp3")]


def fetch_metadata_for_title(title):
    try:
        base_url = "https://www.jiosaavn.com/api.php"
        params = {
            "__call": "search.getResults",
            "p": 1,
            "q": title,
            "_format": "json",
            "_marker": 0,
        }
        url = base_url + "?" + urllib.parse.urlencode(params)
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)

        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                song_info = results[0]
                return {
                    "song_id": str(uuid.uuid4()),  # unique ID for local dataset
                    "title": song_info.get("title"),
                    "album": song_info.get("album"),
                    "artists": song_info.get("more_info", {}).get("singers"),
                    "year": song_info.get("year"),
                    "language": song_info.get("language"),
                    "duration": song_info.get("more_info", {}).get("duration"),
                    "perma_url": song_info.get("perma_url"),
                    "image_url": song_info.get("image"),
                }
        return None
    except Exception as e:
        print(f"Error fetching metadata for '{title}': {e}")
        return None


# -------- MAIN --------
def main():
    local_files = list_mp3_files(DATASETS_DIR)
    print(f"Found {len(local_files)} mp3 files in {DATASETS_DIR}")

    if os.path.exists(METADATA_OUTPUT):
        with open(METADATA_OUTPUT, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {}

    files_to_process = [f for f in local_files if f not in existing]
    print(f"Need to fetch metadata for {len(files_to_process)} songs")

    lock = threading.Lock()

    def task(filename):
        raw_title = os.path.splitext(filename)[0]
        clean = clean_title(raw_title)
        metadata = fetch_metadata_for_title(clean)

        # assign UUID for file
        song_uuid = str(uuid.uuid4())

        # rename file to "<clean_title>_<uuid>.mp3"
        ext = os.path.splitext(filename)[1]
        new_filename = f"{clean}_{song_uuid}{ext}"
        old_path = os.path.join(DATASETS_DIR, filename)
        new_path = os.path.join(DATASETS_DIR, new_filename)
        os.rename(old_path, new_path)

        with lock:
            if metadata:
                metadata["song_id"] = song_uuid
                existing[new_filename] = metadata
                print(f"[✓] {filename} → {new_filename}")
            else:
                existing[new_filename] = {
                    "song_id": song_uuid,
                    "title": clean,
                    "metadata": None,
                }
                print(f"[x] No match: {filename} → {new_filename}")

    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = [executor.submit(task, f) for f in files_to_process]
        for fut in as_completed(futures):
            pass

    with open(METADATA_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"Metadata + renamed files saved. Output in {METADATA_OUTPUT}")


if __name__ == "__main__":
    main()
