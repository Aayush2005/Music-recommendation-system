import json

INPUT_FILE = "metadata.json"
OUTPUT_FILE = "metadata.json"

# strict schema fields
SCHEMA = {
    "song_id": None,
    "title": None,
    "album": None,
    "artists": None,
    "year": None,
    "language": None,
    "duration": None,
    "perma_url": None,
    "image_url": None,
}

def patch_metadata():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    patched = {}
    for filename, meta in data.items():
        fixed = SCHEMA.copy()

        # handle both "correct" and "metadata: null" cases
        if isinstance(meta, dict):
            for key in SCHEMA.keys():
                if key in meta:
                    fixed[key] = meta[key]

            # flatten "metadata": null cases
            if "metadata" in meta and meta["metadata"] is None:
                # keep song_id, title, duration if they exist
                fixed["song_id"] = meta.get("song_id")
                fixed["title"] = meta.get("title")
                fixed["duration"] = meta.get("duration")

        patched[filename] = fixed

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(patched, f, ensure_ascii=False, indent=2)

    print(f"Patched metadata saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    patch_metadata()
