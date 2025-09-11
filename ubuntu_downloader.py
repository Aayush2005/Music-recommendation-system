#!/usr/bin/env python3
"""
Ubuntu-optimized YouTube playlist downloader
This script is designed to work better on Ubuntu systems with fewer restrictions.
"""

import os
import yt_dlp
import time
import random
import csv

# ------------------- CONFIG -------------------
PLAYLISTS = [
    "https://www.youtube.com/playlist?list=PL5X_-JbCGoGNFz8xNDKfkuePx02Q1X4cR",
    "https://www.youtube.com/playlist?list=PL5X_-JbCGoGNs1MrilPbWrQ2wdSatVsUz"
]
OUTPUT_DIR = "datasets"
DOWNLOADED_FILE = "downloaded_songs.txt"
FAILED_FILE = os.path.join(OUTPUT_DIR, "failed_videos.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------- LOAD EXISTING DOWNLOADS -------------------
if os.path.exists(DOWNLOADED_FILE):
    with open(DOWNLOADED_FILE, "r", encoding="utf-8") as f:
        downloaded_songs = set(line.strip() for line in f.readlines())
else:
    downloaded_songs = set()

print(f"📚 Already downloaded: {len(downloaded_songs)} songs")

# ------------------- YT-DLP OPTIONS FOR UBUNTU -------------------
def get_ydl_opts():
    return {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(OUTPUT_DIR, "%(title)s.%(ext)s"),
        "ignoreerrors": True,
        "no_warnings": False,
        "cachedir": False,
        "extractor_retries": 3,
        "fragment_retries": 3,
        "sleep_interval": 2,
        "max_sleep_interval": 10,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ],
        # Ubuntu-friendly headers
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip,deflate",
            "Connection": "keep-alive",
        }
    }

# ------------------- EXTRACT VIDEO URLS -------------------
def extract_playlist_urls():
    video_urls = []
    extract_opts = {
        "ignoreerrors": True,
        "cachedir": False,
        "sleep_interval": 3,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
                time.sleep(5)  # Delay between playlists
                
            except Exception as e:
                print(f"❌ Failed to extract playlist {playlist_url}: {e}")
                continue
    
    return video_urls

# ------------------- DOWNLOAD VIDEOS -------------------
def download_videos(video_urls):
    failed_videos = []
    successful_downloads = 0
    skipped_downloads = 0
    
    print(f"\n🚀 Starting downloads of {len(video_urls)} videos...")
    
    for i, url in enumerate(video_urls, 1):
        try:
            print(f"\n[{i}/{len(video_urls)}] Processing: {url}")
            
            # Random delay to avoid rate limiting
            delay = random.uniform(3, 7)
            print(f"⏱️  Waiting {delay:.1f} seconds...")
            time.sleep(delay)
            
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                # First get video info
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "Unknown Title")
                
                if title in downloaded_songs:
                    print(f"⏭️  Skipping already downloaded: {title}")
                    skipped_downloads += 1
                    continue
                
                print(f"⬇️  Downloading: {title}")
                
                # Download the video
                ydl.download([url])
                
                # Log successful download
                downloaded_songs.add(title)
                with open(DOWNLOADED_FILE, "a", encoding="utf-8") as f:
                    f.write(title + "\n")
                
                successful_downloads += 1
                print(f"✅ Successfully downloaded: {title}")
                
                # Longer break every 20 downloads
                if i % 20 == 0:
                    print(f"🛑 Taking a 60-second break after {i} downloads...")
                    time.sleep(60)
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Failed to download {url}: {error_msg}")
            
            failed_videos.append({"url": url, "error": error_msg})
            
            # Handle different error types
            if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
                print("🤖 Bot detection triggered. Waiting 120 seconds...")
                time.sleep(120)
            elif "Too Many Requests" in error_msg or "429" in error_msg:
                print("🚫 Rate limited. Waiting 180 seconds...")
                time.sleep(180)
            elif "unavailable" in error_msg.lower():
                print("📹 Video unavailable, continuing...")
                continue
    
    return successful_downloads, skipped_downloads, failed_videos

def main():
    print("🐧 Ubuntu YouTube Downloader")
    print("=" * 40)
    
    # Extract video URLs
    video_urls = extract_playlist_urls()
    
    if not video_urls:
        print("❌ No videos found. Exiting.")
        return
    
    print(f"🎵 Total videos found: {len(video_urls)}")
    
    # Download videos
    successful, skipped, failed = download_videos(video_urls)
    
    # Final summary
    print(f"\n📊 Final Summary:")
    print(f"✅ Successful downloads: {successful}")
    print(f"⏭️  Skipped (already downloaded): {skipped}")
    print(f"❌ Failed downloads: {len(failed)}")
    print(f"📁 Total songs in collection: {len(downloaded_songs)}")
    
    # Save failed videos
    if failed:
        with open(FAILED_FILE, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["url", "error"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(failed)
        print(f"📝 Failed videos logged to: {FAILED_FILE}")
    
    print("🎉 Download process completed!")

if __name__ == "__main__":
    main()