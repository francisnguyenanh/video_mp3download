# 🚀 Quick Start Guide - Video Downloader

## ⚡ 5-Minute Setup

### Step 1: Install System Dependencies

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
```bash
winget install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

### Step 2: Setup & Install Python Packages

**macOS/Linux:**
```bash
# Navigate to project folder
cd video_mp3download

# Run setup script
chmod +x setup.sh
./setup.sh
```

**Windows:**
```cmd
cd video_mp3download
setup.bat
```

**Manual Setup (All Platforms):**
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate          # macOS/Linux
# or
venv\Scripts\activate             # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Start the Server

```bash
python app.py
```

**Expected Output:**
```
 * Watching for file changes by 'watchdog'
 * Running on http://0.0.0.0:5000
```

### Step 4: Open in Browser

Visit: `http://localhost:5000` 🎉

---

## 📝 Features Tour

### 1. Add Videos to Download
- Paste YouTube URLs or video links
- Support multiple URLs (newline or comma separated)
- Automatic validation and duplicate detection

### 2. Monitor Downloads in Real-time
- See download percentage
- Current download speed (MB/s)
- Estimated time remaining (ETA)

### 3. Manage Downloaded Files
- View all downloaded videos
- Download to your computer
- Delete from downloads folder
- See file sizes in human-readable format

---

## 🔧 Configuration

### Change Download Folder

Edit `app.py` line 12:
```python
OUTPUT_DIR = "./downloads"  # Change to your preferred path
```

### Change Port (default 5000)

Edit `app.py` last line:
```python
socketio.run(app, debug=True, host='0.0.0.0', port=8080)  # Port 8080
```

### Enable/Disable Debug Mode

Edit `app.py` last line:
```python
socketio.run(app, debug=False)  # Production: False, Development: True
```

---

## 🐛 Troubleshooting

### ❌ "ffmpeg: command not found"
**Problem**: ffmpeg not installed or not in PATH  
**Solution**:
```bash
# Verify installation
ffmpeg -version

# macOS
brew install ffmpeg

# Windows (need admin)
winget install ffmpeg

# Linux
sudo apt install ffmpeg
```

### ❌ "Port 5000 already in use"
**Problem**: Another app using port 5000  
**Solution**: Change port in `app.py` or kill the process
```bash
# macOS/Linux - find process on port 5000
lsof -i :5000

# Kill it
kill -9 <PID>
```

### ❌ "Python: command not found"
**Problem**: Python not installed or not in PATH  
**Solution**:
- Download Python 3.8+ from [python.org](https://python.org)
- Ensure "Add Python to PATH" is checked during installation
- Restart terminal/CMD after installation

### ❌ "ModuleNotFoundError: No module named 'flask'"
**Problem**: Dependencies not installed  
**Solution**:
```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### ❌ "YouTube download fails"
**Problem**: Video blocked, rate-limited, or age-restricted  
**Solutions**:
1. Try a different video
2. Wait a few minutes before retrying
3. Check if video is public (not private)
4. Try from different source website

### ❌ "Downloaded file is corrupted"
**Problem**: Incomplete download or ffmpeg issue  
**Solutions**:
1. Verify ffmpeg is installed: `ffmpeg -version`
2. Check download completed (100%)
3. Ensure enough disk space
4. Try downloading again

### ❌ "Connection refused" or "localhost:5000 refused to connect"
**Problem**: Flask server not running  
**Solution**:
1. Verify Flask started (check console output)
2. Ensure no errors in terminal
3. Try different browser
4. Check firewall settings

---

## 📊 Performance Tips

| Factor | Impact | Solution |
|--------|--------|----------|
| **Internet Speed** | High | Faster connection = faster downloads |
| **Video Quality** | High | Higher quality = larger file = slower |
| **Source Site** | Medium | Some sources slower than others |
| **System CPU** | Low | Minimal - only for ffmpeg re-encoding |
| **Disk Space** | Critical | Ensure enough free space |

---

## 📋 Supported Sources

The app uses **yt-dlp**, supporting 1000+ websites:

✅ YouTube  
✅ Vimeo  
✅ TikTok  
✅ Instagram  
✅ Facebook  
✅ Twitter  
✅ Dailymotion  
✅ SoundCloud  
✅ Twitch  
✅ And many more...

---

## 🔒 Security & Legal

⚠️ **Important Reminders:**

1. **Respect Copyright** - Only download content you have rights to
2. **Check Terms** - Follow website's Terms of Service
3. **Local Use** - For production/sharing, add authentication
4. **Disk Space** - Monitor available storage
5. **Bandwidth** - Download during off-peak hours if limited

---

## 🎯 API Quick Reference

### Add Downloads
```bash
curl -X POST http://localhost:5000/api/add \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://youtube.com/watch?v=..."]}'
```

### Get Queue Status
```bash
curl http://localhost:5000/api/status
```

### List Files
```bash
curl http://localhost:5000/api/files
```

### Delete File
```bash
curl -X DELETE http://localhost:5000/api/files/filename.mp4
```

---

## 📞 Support Resources

- **Flask**: https://flask.palletsprojects.com
- **yt-dlp**: https://github.com/yt-dlp/yt-dlp
- **Socket.IO**: https://socket.io
- **ffmpeg**: https://ffmpeg.org
- **TailwindCSS**: https://tailwindcss.com

---

## 💡 Pro Tips

1. **Batch Downloads**: Add multiple URLs at once for efficient queue processing
2. **Monitor Progress**: Watch real-time stats as videos download
3. **Organize Files**: Downloaded videos are auto-organized in `downloads/` folder
4. **Clear Old Jobs**: Use "Clear Completed" button to clean up queue display
5. **File Naming**: Videos keep their original titles as filenames

---

## 📁 Project Structure at a Glance

```
video_mp3download/
├── app.py              ← Main Flask app (run this!)
├── downloader.py       ← Video download logic
├── requirements.txt    ← Python packages
├── README.md           ← Full documentation
├── QUICKSTART.md       ← This file
├── setup.sh            ← macOS/Linux setup
├── setup.bat           ← Windows setup
├── downloads/          ← Downloaded videos here
├── templates/
│   └── index.html      ← Web UI
└── static/
    └── app.js          ← JavaScript/Socket.IO
```

---

## ✅ Verification Checklist

Before running, verify:

- [ ] Python 3.8+ installed
- [ ] ffmpeg installed
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] No other service on port 5000
- [ ] Disk space available (500MB+ recommended)

---

## 🎓 Example Usage

### Download a YouTube Video
1. Copy URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
2. Paste in textarea
3. Click "Add to Queue"
4. Watch progress update in real-time
5. Download completes → Shows in file list
6. Click "Download" to save to computer

---

## 🚀 Next Steps

1. **Start the server**: `python app.py`
2. **Open browser**: `http://localhost:5000`
3. **Paste a video URL**
4. **Click "Add to Queue"**
5. **Enjoy! 🎉**

---

**Questions?** Check the full README.md for detailed documentation.

**Happy downloading! 🎬**
