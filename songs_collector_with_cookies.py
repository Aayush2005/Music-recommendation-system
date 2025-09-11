import os
import yt_dlp
import csv
import time
import random

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
    with open(DOWNLOADED_FILE, "r", encoding="utf-8") as f:
        downloaded_songs = set(line.strip() for line in f.readlines())
else:
    downloaded_songs = set()

print(f"📚 Already downloaded: {len(downloaded_songs)} songs")

# Check if cookies exist
if not os.path.exists(COOKIES_FILE):
    print(f"❌ Cookies file not found: {COOKIES_FILE}")
    print(f"💡 Run 'python cookie_helper.py' to get cookies first")
    exit(1)

# ------------------- YT-DLP OPTIONS WITH COOKIES -------------------
def get_ydl_opts():
    return {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(OUTPUT_DIR, "%(title)s.%(ext)s"),
        "ignoreerrors": True,
        "no_warnings": False,
        "cachedir": False,
        "cookiefile": COOKIES_FILE,
        "extractor_retries": 3,
        "fragment_retries": 3,
        "retry_sleep_functions": {"http": lambda n: min(2 ** n, 30)},
        "sleep_interval": 1,
        "max_sleep_interval": 5,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ],
        # Better headers to avoid detection
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    }

# ------------------- EXTRACT VIDEO URLS -------------------
video_urls = []
extract_opts = {
    "ignoreerrors": True, 
    "cachedir": False,
    "cookiefile": COOKIES_FILE,
    "extractor_retries": 3,
    "fragment_retries": 3,
    "sleep_interval": 2,
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
}

print("🔍 Extracting video URLs from playlists...")
with yt_dlp.YoutubeDL(extract_opts) as ydl:
    for playlist_url in PLAYLISTS:
        print(f"📋 Processing playlist: {playlist_url}")
        try:
            info = ydl.extract_info(playlist_url, download=False)
            if "entries" not in info:
                print(f"⚠️  No entries found in playlist")
                continue
            
            playlist_videos = 0
            for entry in info["entries"]:
                if not entry:
                    continue
                video_id = entry.get("id")
                if video_id:
                    video_urls.append(f"https://www.youtube.com/watch?v={video_id}")
                    playlist_videos += 1
            
            print(f"✅ Found {playlist_videos} videos in playlist")
            time.sleep(3)  # Delay between playlists
            
        except Exception as e:
            print(f"❌ Failed to extract playlist {playlist_url}: {e}")
            if "Sign in to confirm" in str(e):
                print("🍪 Cookie authentication failed. Try refreshing cookies.")
                exit(1)
            continue

print(f"🎵 Total videos found: {len(video_urls)}")

if not video_urls:
    print("❌ No videos found. This might be due to authentication issues.")
    print("💡 Try refreshing your cookies using cookie_helper.py")
    exit(1)

# ------------------- DOWNLOAD VIDEOS -------------------
failed_videos = []
successful_downloads = 0
skipped_downloads = 0

print(f"\n🚀 Starting downloads...")

# Process videos in smaller batches to avoid overwhelming YouTube
batch_size = 10
total_batches = (len(video_urls) + batch_size - 1) // batch_size

for batch_num in range(total_batches):
    start_idx = batch_num * batch_size
    end_idx = min(start_idx + batch_size, len(video_urls))
    batch_urls = video_urls[start_idx:end_idx]
    
    print(f"\n📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch_urls)} videos)")
    
    for i, url in enumerate(batch_urls):
        overall_idx = start_idx + i + 1
        try:
            print(f"\n[{overall_idx}/{len(video_urls)}] Processing: {url}")
            
            # Random delay to avoid rate limiting
            delay = random.uniform(2, 5)
            print(f"⏱️  Waiting {delay:.1f} seconds...")
            time.sleep(delay)
            
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "Unknown Title")
                
                if title in downloaded_songs:
                    print(f"⏭️  Skipping already downloaded: {title}")
                    skipped_downloads += 1
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
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Failed to download {url}: {error_msg}")
            
            # Log failed download
            failed_videos.append({"url": url, "error": error_msg})
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([url, "FAILED", "ERROR", error_msg])
            
            # Handle different types of errors
            if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
                print("🤖 Bot detection triggered. Waiting 60 seconds...")
                time.sleep(60)
            elif "Too Many Requests" in error_msg or "429" in error_msg:
                print("🚫 Rate limited. Waiting 120 seconds...")
                time.sleep(120)
            elif "unavailable" in error_msg.lower():
                print("📹 Video unavailable, continuing...")
                continue
    
    # Longer break between batches
    if batch_num < total_batches - 1:
        print(f"\n🛑 Batch {batch_num + 1} complete. Taking a 30-second break...")
        time.sleep(30)

print(f"\n📊 Final Summary:")
print(f"✅ Successful downloads: {successful_downloads}")
print(f"⏭️  Skipped (already downloaded): {skipped_downloads}")
print(f"❌ Failed downloads: {len(failed_videos)}")
print(f"📁 Total songs in collection: {len(downloaded_songs)}")

# Save failed videos to CSV
if failed_videos:
    with open(FAILED_FILE, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["url", "error"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(failed_videos)
    print(f"📝 Failed videos logged to: {FAILED_FILE}")

print(f"🎉 Download process completed!")

# Provide suggestions based on failure types
bot_detection_failures = sum(1 for v in failed_videos if "Sign in to confirm" in v["error"])
if bot_detection_failures > 0:
    print(f"\n💡 {bot_detection_failures} failures due to bot detection.")
    print(f"   Consider refreshing cookies or using a VPN.")

rate_limit_failures = sum(1 for v in failed_videos if "Too Many Requests" in v["error"])
if rate_limit_failures > 0:
    print(f"\n⚠️  {rate_limit_failures} failures due to rate limiting.")
    print(f"   Consider increasing delays between downloads.")