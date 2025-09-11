#!/usr/bin/env python3
"""
Ubuntu downloader with cookie support for better success rate
"""

import os
import yt_dlp
import time
import random
import csv
import subprocess

# ------------------- CONFIG -------------------
PLAYLISTS = [
    "https://www.youtube.com/playlist?list=PL5X_-JbCGoGNFz8xNDKfkuePx02Q1X4cR",
    "https://www.youtube.com/playlist?list=PL5X_-JbCGoGNs1MrilPbWrQ2wdSatVsUz"
]
OUTPUT_DIR = "datasets"
DOWNLOADED_FILE = "downloaded_songs.txt"
COOKIES_FILE = "youtube_cookies.txt"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load existing downloads
if os.path.exists(DOWNLOADED_FILE):
    with open(DOWNLOADED_FILE, "r", encoding="utf-8") as f:
        downloaded_songs = set(line.strip() for line in f.readlines())
else:
    downloaded_songs = set()

print(f"📚 Already downloaded: {len(downloaded_songs)} songs")

def try_extract_cookies():
    """Try to extract cookies from browsers on Ubuntu"""
    browsers = ['firefox', 'chrome', 'chromium']
    
    for browser in browsers:
        print(f"🍪 Trying to extract cookies from {browser}...")
        try:
            cmd = [
                "yt-dlp",
                "--cookies-from-browser", browser,
                "--cookies", COOKIES_FILE,
                "--no-download",
                "--quiet",
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ Successfully extracted cookies from {browser}!")
                return True
            else:
                print(f"❌ Failed with {browser}")
                
        except Exception as e:
            print(f"❌ Error with {browser}: {e}")
    
    return False

def get_ydl_opts():
    """Get yt-dlp options with or without cookies"""
    opts = {
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
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    }
    
    # Add cookies if available
    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
        print("🍪 Using cookies for authentication")
    
    return opts

def main():
    print("🐧 Ubuntu YouTube Downloader with Cookie Support")
    print("=" * 50)
    
    # Try to extract cookies first
    if not os.path.exists(COOKIES_FILE):
        print("🍪 No cookies found. Attempting to extract from browsers...")
        if not try_extract_cookies():
            print("⚠️  Could not extract cookies. Proceeding without authentication.")
            print("💡 For better results, manually export cookies from your browser.")
    
    # Extract playlist URLs
    print("\n🔍 Extracting video URLs...")
    video_urls = []
    
    with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
        for playlist_url in PLAYLISTS:
            try:
                info = ydl.extract_info(playlist_url, download=False)
                if "entries" in info:
                    for entry in info["entries"]:
                        if entry and entry.get("id"):
                            video_urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
                print(f"✅ Extracted {len([e for e in info.get('entries', []) if e])} URLs from playlist")
                time.sleep(3)
            except Exception as e:
                print(f"❌ Failed to extract playlist: {e}")
    
    print(f"🎵 Total videos to download: {len(video_urls)}")
    
    if not video_urls:
        print("❌ No videos found. Exiting.")
        return
    
    # Download videos
    successful = 0
    failed = []
    
    for i, url in enumerate(video_urls, 1):
        try:
            print(f"\n[{i}/{len(video_urls)}] Processing video...")
            
            # Random delay
            delay = random.uniform(2, 5)
            time.sleep(delay)
            
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "Unknown")
                
                if title in downloaded_songs:
                    print(f"⏭️  Skipping: {title}")
                    continue
                
                print(f"⬇️  Downloading: {title}")
                ydl.download([url])
                
                # Log success
                downloaded_songs.add(title)
                with open(DOWNLOADED_FILE, "a", encoding="utf-8") as f:
                    f.write(title + "\n")
                
                successful += 1
                print(f"✅ Downloaded: {title}")
                
        except Exception as e:
            print(f"❌ Failed: {e}")
            failed.append({"url": url, "error": str(e)})
            
            if "Sign in to confirm" in str(e):
                print("🤖 Bot detection. Waiting 60 seconds...")
                time.sleep(60)
    
    print(f"\n📊 Summary: {successful} successful, {len(failed)} failed")
    print("🎉 Done!")

if __name__ == "__main__":
    main()