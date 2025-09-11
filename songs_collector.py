import os
import yt_dlp
import csv
import time

# ------------------- CONFIG -------------------
PLAYLISTS = [
    "https://www.youtube.com/playlist?list=PL5X_-JbCGoGNFz8xNDKfkuePx02Q1X4cR",
    "https://www.youtube.com/playlist?list=PL5X_-JbCGoGNs1MrilPbWrQ2wdSatVsUz"
]
OUTPUT_DIR = "datasets"
COOKIES_FILE = "youtube-com_cookies.txt"
DOWNLOADED_FILE = "downloaded_songs.txt"
FAILED_FILE = os.path.join(OUTPUT_DIR, "failed_videos.csv")
LOG_FILE = os.path.join(OUTPUT_DIR, "download_log.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------- LOAD LOG -------------------
if os.path.exists(DOWNLOADED_FILE):
    with open(DOWNLOADED_FILE, "r") as f:
        downloaded_songs = set(line.strip() for line in f.readlines())
else:
    downloaded_songs = set()

# ------------------- YT-DLP OPTIONS -------------------
ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": os.path.join(OUTPUT_DIR, "%(title)s.%(ext)s"),
    "ignoreerrors": True,
    "cachedir": False,
    "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
    "extractor_retries": 3,
    "fragment_retries": 3,
    "retry_sleep_functions": {"http": lambda n: min(4 ** n, 60)},
    "postprocessors": [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
    ],
}

video_urls = []

# ------------------- EXTRACT ALL VIDEO URLS -------------------
extract_opts = {
    "ignoreerrors": True, 
    "cachedir": False,
    "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
    "extractor_retries": 3,
    "fragment_retries": 3,
}

with yt_dlp.YoutubeDL(extract_opts) as ydl:
    for playlist_url in PLAYLISTS:
        print(f"Extracting playlist: {playlist_url}")
        try:
            info = ydl.extract_info(playlist_url, download=False)
            if "entries" not in info:
                continue
            for entry in info["entries"]:
                if not entry:
                    continue
                video_id = entry.get("id")
                if video_id:
                    video_urls.append(f"https://www.youtube.com/watch?v={video_id}")
        except Exception as e:
            print(f"❌ Failed to extract playlist {playlist_url}: {e}")
            continue

print(f"Total videos found: {len(video_urls)}")

# ------------------- DOWNLOAD VIDEOS -------------------
failed_videos = []
successful_downloads = 0

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    for i, url in enumerate(video_urls, 1):
        try:
            print(f"\n[{i}/{len(video_urls)}] Processing: {url}")
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "Unknown Title")
            
            if title in downloaded_songs:
                print(f"✅ Skipping already downloaded: {title}")
                continue
                
            print(f"⬇️  Downloading: {title}")
            ydl.download([url])
            
            # Log successful download
            downloaded_songs.add(title)
            with open(DOWNLOADED_FILE, "a", encoding="utf-8") as f:
                f.write(title + "\n")
            
            # Log to CSV
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([url, title, "SUCCESS", ""])
            
            successful_downloads += 1
            print(f"✅ Successfully downloaded: {title}")
            
            # Small delay to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Failed to download {url}: {error_msg}")
            
            # Log failed download
            failed_videos.append({"url": url, "error": error_msg})
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([url, "FAILED", "ERROR", error_msg])

print(f"\n📊 Download Summary:")
print(f"✅ Successful downloads: {successful_downloads}")
print(f"❌ Failed downloads: {len(failed_videos)}")

# Save failed videos to CSV
if failed_videos:
    with open(FAILED_FILE, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["url", "error"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(failed_videos)
    print(f"📝 Failed videos logged to: {FAILED_FILE}")
