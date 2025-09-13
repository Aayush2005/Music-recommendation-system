import os
import yt_dlp
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

PLAYLISTS = [
    "https://youtube.com/playlist?list=PLHuHXHyLu7BGi-vR7X6j_xh_Tt9wy7pNA&si=VuGs8JLFLaP8gq08",
    "https://youtube.com/playlist?list=PL0Z67tlyTaWphlJ8dod2fSFGmBlUW_KJJ&si=Oe9YXSJda1EWqIWH"
]

OUTPUT_DIR = "datasetsTEST"
os.makedirs(OUTPUT_DIR, exist_ok=True)
DOWNLOADED_FILE = "downloaded_songs.txt"

# Load already downloaded songs (preserve case + spaces, strip only newline)
if os.path.exists(DOWNLOADED_FILE):
    with open(DOWNLOADED_FILE, "r", encoding="utf-8") as f:
        downloaded_songs = set(line.strip("\n") for line in f if line.strip())
else:
    downloaded_songs = set()

def sanitize_title(title: str) -> str:
    return "".join(c for c in title if c not in "/\\?%*:|\"<>")

def get_ydl_opts(title=None):
    outtmpl = os.path.join(
        OUTPUT_DIR,
        f"{sanitize_title(title)}.%(ext)s" if title else "%(title)s.%(ext)s"
    )
    return {
        "format": "bestaudio",
        "outtmpl": outtmpl,
        "ignoreerrors": True,
        "cachedir": False,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    }

# Extract video URLs
all_video_urls = []
with yt_dlp.YoutubeDL({"extract_flat": True, "ignoreerrors": True}) as ydl:
    for playlist_url in PLAYLISTS:
        print(f"📥 Fetching playlist: {playlist_url}")
        info = ydl.extract_info(playlist_url, download=False)
        for entry in info.get("entries", []):
            if entry:
                all_video_urls.append({
                    "url": f"https://www.youtube.com/watch?v={entry['id']}",
                    "title": entry.get("title", "Unknown")
                })

print(f"🔎 Total videos found: {len(all_video_urls)}")

# Download function
def download_video(video):
    url, title = video["url"], video["title"]

    if title in downloaded_songs:
        print(f"⏭️ Skipping: {title}")
        return "skipped"

    try:
        time.sleep(random.uniform(1, 3))  # polite delay
        with yt_dlp.YoutubeDL(get_ydl_opts(title)) as ydl:
            ydl.download([url])
        downloaded_songs.add(title)
        with open(DOWNLOADED_FILE, "a", encoding="utf-8") as f:
            f.write(title + "\n")
        print(f"✅ Downloaded: {title}")
        return "success"
    except Exception as e:
        print(f"❌ Failed: {title} ({e})")
        return "failed"

# Multithreaded download
MAX_THREADS = 4  # safe small number for FFmpeg
with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    futures = [executor.submit(download_video, v) for v in all_video_urls]
    for future in as_completed(futures):
        future.result()
