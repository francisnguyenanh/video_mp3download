import os
import re
import uuid
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import yt_dlp


class VideoDownloader:
    def __init__(self, output_dir: str = "./downloads"):
        self.output_dir = output_dir
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def download(self, url: str, job_id: str, progress_callback: Callable, 
                 mode: str = 'video', format_type: str = 'mp4', 
                 quality: str = 'best', bitrate: str = '192') -> Dict[str, Any]:
        """
        Download a video or audio from the given URL.
        
        Args:
            url: The video URL to download
            job_id: Unique job identifier
            progress_callback: Callback function for progress updates
            mode: 'video' or 'audio'
            format_type: 'mp4', 'webm', 'mkv' (video) or 'mp3', 'm4a', 'ogg' (audio)
            quality: 'best', '1080p', '720p', '480p', '360p' (video only)
            bitrate: '320', '192', '128', '96' (audio only, kbps)
            
        Returns:
            Dictionary with keys: success, filename, filepath, title, duration, filesize, error
        """
        try:
            ydl_opts = self._get_ydl_opts(job_id, progress_callback, mode, format_type, quality, bitrate)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # For audio files, yt-dlp may change the extension after postprocessing
                if mode == 'audio':
                    # Try to find the converted file
                    filename = None
                    title = info.get('title', 'Unknown')
                    base_path = os.path.join(self.output_dir, self.sanitize_filename(title))
                    
                    # Check for converted audio files
                    for ext in [format_type, 'mp3', 'm4a', 'ogg', 'wav']:
                        potential_file = f"{base_path}.{ext}"
                        if os.path.exists(potential_file):
                            filename = os.path.basename(potential_file)
                            filepath = potential_file
                            break
                    
                    if not filename:
                        filename = ydl.prepare_filename(info)
                        filepath = os.path.join(self.output_dir, os.path.basename(filename))
                else:
                    filename = ydl.prepare_filename(info)
                    filepath = os.path.join(self.output_dir, os.path.basename(filename))
                
                return {
                    'success': True,
                    'filename': filename if filename else os.path.basename(filepath) if filepath else 'unknown',
                    'filepath': filepath,
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'filesize': os.path.getsize(filepath) if filepath and os.path.exists(filepath) else 0,
                    'error': None
                }
        
        except yt_dlp.utils.DownloadError as e:
            error_msg = f"Download error: {str(e)}"
            return {
                'success': False,
                'filename': None,
                'filepath': None,
                'title': None,
                'duration': 0,
                'filesize': 0,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            return {
                'success': False,
                'filename': None,
                'filepath': None,
                'title': None,
                'duration': 0,
                'filesize': 0,
                'error': error_msg
            }
    
    def _get_ydl_opts(self, job_id: str, progress_callback: Callable, 
                      mode: str = 'video', format_type: str = 'mp4',
                      quality: str = 'best', bitrate: str = '192') -> Dict[str, Any]:
        """
        Generate yt-dlp options with progress hook for video or audio download.
        
        Args:
            job_id: Job identifier for progress tracking
            progress_callback: Callback function for progress updates
            mode: 'video' or 'audio'
            format_type: Video format (mp4/webm/mkv) or audio format (mp3/m4a/ogg)
            quality: Video quality (best/1080p/720p/480p/360p)
            bitrate: Audio bitrate (320/192/128/96 kbps)
            
        Returns:
            Dictionary of yt-dlp options
        """
        base_opts = {
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_callback],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'retries': 3,
            'fragment_retries': 3,
            'quiet': False,
            'no_warnings': False,
        }
        
        if mode == 'audio':
            # Audio conversion configuration
            codec_map = {
                'mp3': 'mp3',
                'm4a': 'aac',
                'ogg': 'vorbis'
            }
            
            base_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': codec_map.get(format_type, 'mp3'),
                        'preferredquality': bitrate,
                    },
                    {
                        'key': 'FFmpegMetadata',
                        'add_metadata': True,
                    },
                    {
                        'key': 'EmbedThumbnail',
                    }
                ],
                'writethumbnail': True,
                'merge_output_format': format_type,
            })
        else:
            # Video download configuration
            quality_map = {
                'best':  'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]',
                '720p':  'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]',
                '480p':  'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]',
                '360p':  'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]',
            }
            
            base_opts.update({
                'format': quality_map.get(quality, quality_map['best']),
                'merge_output_format': format_type,
                'postprocessors': [
                    {'key': 'FFmpegMetadata', 'add_metadata': True}
                ],
            })
        
        return base_opts
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove special characters from filename."""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'[\s]+', '_', filename)
        return filename[:255]
    
    @staticmethod
    def format_bytes(bytes_size: int) -> str:
        """Convert bytes to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
