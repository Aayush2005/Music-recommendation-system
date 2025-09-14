#!/usr/bin/env python3
import os, re, json, shutil
from datetime import datetime

METADATA_FILE = "metadata.json"
BACKUP_DIR = "metadata_backups"
SCHEMA_KEYS = [
    "song_id", "title", "album", "artists", "year",
    "language", "duration", "perma_url", "image_url",
]

UUID_SUFFIX_RE = re.compile(
    r"([0-9a-f]{8}_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
    re.IGNORECASE
)

def extract_id_and_title(filename_base: str):
    """
    From filename base, extract:
      - clean title
      - song_id (full shorthex_uuid)
    Example:
      "Jaane De_870c6bde_8191c9ed-d0c9-40bb-b227-cfe8b435d13b"
      -> title="Jaane De", song_id="870c6bde_8191c9ed-d0c9-40bb-b227-cfe8b435d13b"
    """
    match = UUID_SUFFIX_RE.search(filename_base)
    if match:
        song_id = match.group(1)
        # remove the "_<song_id>" suffix from the base name
        title = filename_base[: -len(song_id) - 1]  # remove underscore + id
    else:
        song_id = None
        title = filename_base
    return song_id, title.strip()

def patch_metadata():
    if not os.path.exists(METADATA_FILE):
        raise FileNotFoundError(f"{METADATA_FILE} not found")

    # backup
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"metadata_{ts}.json")
    shutil.copyfile(METADATA_FILE, backup_path)
    print(f"[+] Backup created: {backup_path}")

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    patched, fixed_count = {}, 0
    for filename, entry in data.items():
        base = os.path.splitext(filename)[0]
        song_id, title = extract_id_and_title(base)

        # start with strict schema
        fixed = {k: None for k in SCHEMA_KEYS}
        if isinstance(entry, dict):
            for k in SCHEMA_KEYS:
                if k in entry and entry[k] is not None:
                    fixed[k] = entry[k]

        if song_id:
            fixed["song_id"] = song_id
        fixed["title"] = title

        patched[filename] = fixed
        if fixed != entry:
            fixed_count += 1

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(patched, f, ensure_ascii=False, indent=2)

    print(f"[+] Patched {fixed_count} entries.")
    print("[✓] Done. Original backed up at:", backup_path)

if __name__ == "__main__":
    patch_metadata()
