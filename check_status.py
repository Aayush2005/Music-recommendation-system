#!/usr/bin/env python3
"""
Status checker for your music collection
"""

import os
import csv
from collections import Counter

def check_downloaded_songs():
    """Check what songs have been downloaded"""
    downloaded_file = "downloaded_songs.txt"
    datasets_dir = "datasets"
    
    print("🎵 Music Collection Status")
    print("=" * 40)
    
    # Check downloaded songs list
    if os.path.exists(downloaded_file):
        with open(downloaded_file, "r", encoding="utf-8") as f:
            downloaded_songs = [line.strip() for line in f.readlines() if line.strip()]
        print(f"📝 Songs in download log: {len(downloaded_songs)}")
    else:
        downloaded_songs = []
        print("📝 No download log found")
    
    # Check actual files in datasets directory
    if os.path.exists(datasets_dir):
        files = [f for f in os.listdir(datasets_dir) if f.endswith('.mp3')]
        print(f"🎧 MP3 files in datasets: {len(files)}")
        
        # Show file extensions
        all_files = os.listdir(datasets_dir)
        extensions = Counter([os.path.splitext(f)[1].lower() for f in all_files if '.' in f])
        print(f"📁 File types: {dict(extensions)}")
        
        # Show some sample files
        if files:
            print(f"\n📀 Sample files:")
            for i, file in enumerate(files[:5]):
                print(f"   {i+1}. {file}")
            if len(files) > 5:
                print(f"   ... and {len(files) - 5} more")
    else:
        print("📁 Datasets directory not found")
    
    # Check for log files
    log_files = ["datasets/download_log.csv", "datasets/failed_videos.csv"]
    for log_file in log_files:
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    print(f"📊 {os.path.basename(log_file)}: {len(rows)} entries")
            except Exception as e:
                print(f"❌ Error reading {log_file}: {e}")
    
    # Check cookies
    if os.path.exists("youtube-com_cookies.txt"):
        with open("youtube-com_cookies.txt", "r") as f:
            cookie_content = f.read()
            if len(cookie_content) > 100:
                print("🍪 Cookies file exists and looks valid")
            else:
                print("🍪 Cookies file exists but may be incomplete")
    else:
        print("🍪 No cookies file found")
    
    print(f"\n💡 Recommendations:")
    if len(downloaded_songs) < 500:  # Assuming playlists have more songs
        print("   - Continue downloading remaining songs")
        print("   - Get fresh cookies if facing bot detection")
        print("   - Run: ./venv/bin/python songs_collector_with_cookies.py")
    else:
        print("   - Collection looks complete!")
        print("   - Consider organizing files or building your recommendation system")

def main():
    check_downloaded_songs()

if __name__ == "__main__":
    main()