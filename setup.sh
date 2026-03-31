#!/bin/bash

# Video Downloader - Quick Start Script for macOS

echo "🎬 Video Downloader - Quick Start Setup"
echo "========================================"
echo ""

# Check Python
echo "✓ Checking Python..."
python3 --version

# Check ffmpeg
echo "✓ Checking ffmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ffmpeg not found. Install with:"
    echo "   brew install ffmpeg"
    exit 1
fi
ffmpeg -version | head -1

# Create virtual environment
echo ""
echo "✓ Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "✓ Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Summary
echo ""
echo "✅ Setup Complete!"
echo ""
echo "To start the server, run:"
echo "   source venv/bin/activate"
echo "   python app.py"
echo ""
echo "Then open: http://localhost:5000"
echo ""
