# 🎬 Video Downloader - Flask Web Application

A complete Flask web application for downloading videos from YouTube and online movie sites with real-time progress tracking via WebSocket.

## Features

✅ **Real-time Progress Tracking** - WebSocket-based live updates of download progress  
✅ **YouTube & Website Support** - Works with YouTube, movie sites, and other video platforms  
✅ **Queue Management** - Sequential download queue with pending/downloading/completed/failed states  
✅ **File Management** - Browse, download, and delete downloaded files  
✅ **Dark Theme UI** - Modern, responsive interface with TailwindCSS  
✅ **Error Handling** - Graceful error messages and retry suggestions  
✅ **Multiple URL Support** - Add multiple URLs at once (separated by newlines or commas)  
✅ **Duplicate Detection** - Warns about duplicate URLs in queue  

## Tech Stack

- **Backend**: Flask 3.0.0 + Flask-SocketIO 5.3.6
- **Video Engine**: yt-dlp 2024.1.1
- **Real-time Communication**: Socket.IO + eventlet
- **Frontend**: HTML5 + TailwindCSS + JavaScript
- **Threading**: Python's queue.Queue for sequential downloads

## Prerequisites

### System Requirements

1. **Python 3.8+** - Download from [python.org](https://www.python.org)
2. **ffmpeg** - Required for merging HLS/DASH streams
   
   **Installation:**
   - **macOS**: `brew install ffmpeg`
   - **Windows**: `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org)
   - **Ubuntu/Debian**: `sudo apt install ffmpeg`
   - **Arch**: `sudo pacman -S ffmpeg`

## Installation & Setup

### 1. Clone or Extract Project

```bash
cd video_mp3download
```

### 2. Create Virtual Environment (Recommended)

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify ffmpeg Installation

```bash
ffmpeg -version
```

If command not found, ensure ffmpeg is properly installed.

## Running the Application

### Start the Server

```bash
python app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
```

### Access the Web UI

Open your browser and navigate to:
```
http://localhost:5000
```

## Project Structure

```
video-downloader/
├── app.py                 # Flask app with Socket.IO & queue management
├── downloader.py          # VideoDownloader class & yt-dlp wrapper
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Single-page UI
├── static/
│   └── app.js             # Frontend JavaScript & Socket.IO client
└── downloads/             # Downloaded videos directory (auto-created)
```

## Usage Guide

### Adding Videos to Download

1. **Paste URLs**: Copy video URLs into the textarea
   - Supports YouTube links: `https://www.youtube.com/watch?v=...`
   - Supports multiple URLs (newline or comma-separated)
   - Example:
     ```
     https://www.youtube.com/watch?v=dQw4w9WgXcQ
     https://example.com/video/123
     ```

2. **Click "Add to Queue"** - URLs are validated and added to the download queue

3. **Monitor Downloads** - Watch real-time progress:
   - Download percentage
   - Download speed (MB/s)
   - Estimated time remaining

### Queue Management

- **Queue States**:
  - 🔄 **Downloading**: Currently being downloaded
  - ⏳ **Pending**: Waiting to be downloaded
  - ✅ **Completed**: Successfully downloaded
  - ❌ **Failed**: Download failed with error message

- **Clear Completed**: Remove finished jobs from queue display
- **View Warnings**: Duplicates and invalid URLs are shown as warnings

### File Management

- **Downloaded Files**: Browse all downloaded videos
- **Download**: Click the download button to save file to your computer
- **Delete**: Remove files from the downloads folder

## API Endpoints

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve main UI |
| `POST` | `/api/add` | Add URLs to queue |
| `GET` | `/api/status` | Get queue status |
| `GET` | `/api/files` | List downloaded files |
| `GET` | `/api/download/<filename>` | Download file |
| `DELETE` | `/api/files/<filename>` | Delete file |
| `POST` | `/api/queue/clear` | Clear completed jobs |

### Socket.IO Events

**Received by Client:**
- `queue_update`: Queue state changed
- `download_progress`: Progress update during download
- `download_complete`: Download finished successfully
- `download_error`: Download failed
- `files_updated`: File list changed

**Sent by Client:**
- `connect`: Connection established

## Configuration

### Download Output Directory

To change where videos are saved, edit `app.py`:

```python
OUTPUT_DIR = "./downloads"  # Change this line
```

### Flask Debug Mode

Production deployment:
```python
socketio.run(app, debug=False, host='0.0.0.0', port=5000)
```

### Change Port

```python
socketio.run(app, debug=True, host='0.0.0.0', port=8080)  # Change port to 8080
```

## Troubleshooting

### Issue: "ffmpeg not found"
**Solution**: Ensure ffmpeg is installed and in your PATH
```bash
# Verify installation
ffmpeg -version
which ffmpeg  # macOS/Linux
where ffmpeg  # Windows
```

### Issue: "Connection refused" or "Cannot connect to localhost:5000"
**Solution**: 
- Ensure Flask server is running
- Check if port 5000 is already in use: `lsof -i :5000` (macOS/Linux)

### Issue: YouTube download fails with "access denied"
**Solution**:
- YouTube may rate-limit requests
- Wait a few minutes before trying again
- Try with a different video

### Issue: Large file downloads very slowly
**Solution**:
- Check your internet connection
- The Q. shows actual download speed from the source
- Some sources may have bandwidth limits

### Issue: Downloaded file is corrupted
**Solution**:
- Ensure download completed (100%)
- Ensure ffmpeg is properly installed
- Try a different source video

## Advanced Usage

### Download from Multiple Sites

The app supports downloading from various platforms:
- YouTube
- Vimeo
- TikTok
- Facebook
- Instagram
- Dailymotion
- Soundcloud
- And many more supported by yt-dlp

### Sequential Processing

Downloads are processed sequentially (one at a time). This prevents:
- Overloading your internet
- System resource exhaustion
- Getting blocked by video hosts

### File Organization

Downloaded files are automatically organized in the `downloads/` folder with:
- Original video title as filename
- Proper file extension (`.mp4` preferred)
- Human-readable sizes displayed in UI

## Performance Tips

1. **Connection**: Faster internet = faster downloads
2. **Source**: Quality/format affects download speed
3. **Queue**: Process downloads when not using heavy applications
4. **ffmpeg**: Ensure ffmpeg is in your PATH for optimal merging

## Security Notes

- **Local Use Only**: For production, add authentication
- **File Security**: The app prevents directory traversal attacks
- **URL Validation**: URLs are validated before processing
- **No Data Collection**: No personal data is stored

## Limitations

- Sequential downloads (by design)
- Respects video source's DRM/copyright protections
- Some sites may block automated downloads
- Downloaded files remain until manually deleted

## Development

### Enable Debug Mode

Edit `app.py`:
```python
if __name__ == '__main__':
    socketio.run(app, debug=True)  # Set debug=True
```

### View Console Logs

Check Flask console for detailed logs during downloads

### Modify UI Styling

Edit `templates/index.html` - uses TailwindCSS CDN  
Edit `static/app.js` - JavaScript logic

## Requirements

```
Flask==3.0.0
Flask-SocketIO==5.3.6
yt-dlp==2024.1.1
eventlet==0.35.1
python-socketio==5.11.0
python-engineio==4.9.0
```

## License

This project is provided as-is for educational purposes.

## Support

For issues with:
- **Flask/Python**: Check Flask documentation
- **yt-dlp**: Visit [yt-dlp GitHub](https://github.com/yt-dlp/yt-dlp)
- **Socket.IO**: Check Socket.IO documentation
- **ffmpeg**: Visit [ffmpeg.org](https://ffmpeg.org)

## Disclaimer

Use this tool responsibly. Respect:
- Copyright laws in your jurisdiction
- Website terms of service
- Content creator rights
- Local regulations regarding downloading

---

**Happy downloading! 🎬**
