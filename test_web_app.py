#!/usr/bin/env python3
"""
Simple test script for the web application
"""

import requests
import json

def test_web_app():
    """Test the web application with a sample YouTube URL"""
    
    # Test URL - a popular Hindi song
    test_url = "https://www.youtube.com/watch?v=kJa2kwoZ2a4"  # Kesariya from Brahmastra
    
    print("🧪 Testing Music Recommendation Web App")
    print(f"📺 Test URL: {test_url}")
    print("⏳ Sending request...")
    
    try:
        response = requests.post(
            'http://localhost:5000/api/recommend',
            json={'url': test_url},
            timeout=60  # 60 seconds timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Request successful!")
            print(f"🎵 Original Song: {data['original_song']['title']}")
            print(f"🎯 Method: {data['method']}")
            print(f"📊 Cluster ID: {data['cluster_id']}")
            print(f"🔢 Total Candidates: {data['total_candidates']}")
            print(f"💡 Recommendations: {len(data['recommendations'])}")
            
            print("\n🎼 Top 3 Recommendations:")
            for i, song in enumerate(data['recommendations'][:3], 1):
                print(f"  {i}. {song['title']} ({song['year']}) - {song['language']}")
            
            return True
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

if __name__ == "__main__":
    success = test_web_app()
    if success:
        print("\n🎉 Web application test passed!")
        print("🌐 You can now open http://localhost:5000 in your browser")
    else:
        print("\n💥 Web application test failed!")
        print("Make sure the server is running with: python main.py")