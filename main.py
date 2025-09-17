#!/usr/bin/env python3
"""
Flask Web App for Music Recommendation System
- Takes YouTube URL input
- Downloads audio using yt-dlp
- Runs prediction pipeline
- Returns recommendations as JSON
"""

import os
import json
import tempfile
import subprocess
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import yt_dlp
import logging
import warnings

# Suppress TensorFlow warnings for production
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
warnings.filterwarnings('ignore')

# Import prediction functions
from prediction import run as process_audio_file

app = Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Temporary directory for downloads
TEMP_DIR = Path("temp_downloads")
TEMP_DIR.mkdir(exist_ok=True)

# --- MODIFICATION START ---
# Define the path for the cookie file, which Render provides at this location
COOKIE_FILE_PATH = '/etc/secrets/cookies.txt'
# --- MODIFICATION END ---


def download_youtube_audio(url, output_path):
    """Download audio from YouTube URL using yt-dlp"""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(output_path / '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        
        # --- MODIFICATION START ---
        # Check if the cookie file exists and add it to the options
        if os.path.exists(COOKIE_FILE_PATH):
            logger.info(f"Cookie file found at {COOKIE_FILE_PATH}. Using cookies for download.")
            ydl_opts['cookiefile'] = COOKIE_FILE_PATH
        else:
            logger.info("Cookie file not found. Proceeding without cookies.")
        # --- MODIFICATION END ---
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Unknown')
            
            # Find the downloaded file
            for file in output_path.glob("*.mp3"):
                return file, title
                
        return None, None
        
    except Exception as e:
        logger.error(f"Error downloading from YouTube: {e}")
        return None, None

def cleanup_temp_files(file_path):
    """Clean up temporary files"""
    try:
        if file_path and file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.error(f"Error cleaning up {file_path}: {e}")

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/recommend', methods=['POST'])
def get_recommendations():
    """API endpoint to get recommendations from YouTube URL"""
    try:
        logger.info("Received recommendation request")
        data = request.get_json()
        
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No data provided'}), 400
            
        youtube_url = data.get('url', '').strip()
        
        if not youtube_url:
            logger.error("No YouTube URL provided")
            return jsonify({'error': 'YouTube URL is required'}), 400
        
        # Validate YouTube URL
        if 'youtube.com' not in youtube_url and 'youtu.be' not in youtube_url:
            logger.error(f"Invalid YouTube URL: {youtube_url}")
            return jsonify({'error': 'Please provide a valid YouTube URL'}), 400
        
        logger.info(f"Processing YouTube URL: {youtube_url}")
        
        try:
            # Create temporary directory for this request
            with tempfile.TemporaryDirectory(dir=TEMP_DIR) as temp_dir:
                temp_path = Path(temp_dir)
                
                # Download audio from YouTube
                logger.info("Starting YouTube download...")
                audio_file, song_title = download_youtube_audio(youtube_url, temp_path)
                
                if not audio_file:
                    logger.error("Failed to download audio from YouTube")
                    return jsonify({'error': 'Failed to download audio from YouTube. The video might be private or unavailable.'}), 500
                
                logger.info(f"Successfully downloaded: {song_title}")
                
                # Process the audio file through prediction pipeline
                logger.info("Starting prediction pipeline...")
                predictions = process_audio_file(str(audio_file))
                
                if not predictions:
                    logger.error("Prediction pipeline returned no results")
                    return jsonify({'error': 'Failed to generate recommendations. Audio processing failed.'}), 500
                
                if 'error' in predictions:
                    logger.error(f"Prediction pipeline error: {predictions['error']}")
                    return jsonify({'error': f'Audio analysis failed: {predictions["error"]}'}), 500
                
                # Add the original song info
                result = {
                    'original_song': {
                        'title': song_title,
                        'url': youtube_url
                    },
                    'recommendations': predictions.get('recommendations', []),
                    'cluster_id': predictions.get('cluster_id', -1),
                    'method': predictions.get('method', 'unknown'),
                    'total_candidates': predictions.get('total_candidates', 0)
                }
                
                logger.info(f"Successfully generated {len(result['recommendations'])} recommendations")
                return jsonify(result)
                
        except Exception as inner_e:
            logger.error(f"Error in processing pipeline: {str(inner_e)}", exc_info=True)
            return jsonify({'error': f'Processing failed: {str(inner_e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error in recommendation endpoint: {str(e)}", exc_info=True)
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Music Recommendation API is running'})

if __name__ == '__main__':
    # Check if required files exist
    required_files = [
        'clusters.json',
        'features_reduced.json', 
        'metadata.json',
        'models/yamnet_pca.joblib'
    ]
    
    missing_files = [f for f in required_files if not Path(f).exists()]
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        print("Please ensure all model files are present before starting the server.")
        exit(1)
    
    print("🎵 Starting Music Recommendation Server...")
    print("📂 Required files found ✓")
    print("🌐 Server will be available at: http://localhost:5000")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)