#!/bin/bash
# Ubuntu setup script for YouTube downloader

echo "🐧 Setting up YouTube downloader on Ubuntu..."

# Update system
echo "📦 Updating system packages..."
sudo apt update

# Install Python and pip if not already installed
echo "🐍 Installing Python and pip..."
sudo apt install -y python3 python3-pip python3-venv

# Install ffmpeg for audio conversion
echo "🎵 Installing ffmpeg for audio processing..."
sudo apt install -y ffmpeg

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment and install dependencies
echo "📚 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install yt-dlp

# Create datasets directory
mkdir -p datasets

echo "✅ Setup complete!"
echo ""
echo "To run the downloader:"
echo "1. source venv/bin/activate"
echo "2. python ubuntu_downloader.py"
echo ""
echo "Or run directly:"
echo "./venv/bin/python ubuntu_downloader.py"