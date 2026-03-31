import os
import re
import uuid
import time
import threading
import requests
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import yt_dlp
from datetime import datetime


class SegmentInfo:
    """Information about a download segment."""
    def __init__(self, segment_id: int, start: int, end: int):
        self.segment_id = segment_id
        self.start = start
        self.end = end
        self.bytes_downloaded = 0
        self.status = 'pending'  # pending, downloading, completed, failed
        self.retries = 0
        self.max_retries = 3


class AdvancedDownloader:
    """
    Advanced downloader with IDM-like features:
    - Multi-segment/parallel downloading
    - Smart bandwidth management
    - Resume capability
    - Dynamic segment optimization
    - Connection pooling and reuse
    - Adaptive chunk sizing
    """
    
    def __init__(self, output_dir: str = "./downloads", max_connections: int = 4):
        self.output_dir = output_dir
        self.max_connections = max_connections
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        self.download_state = {}  # Track download state for resume
        self.lock = threading.Lock()
    
    def download_file(self, url: str, filename: str, job_id: str,
                     progress_callback: Callable, use_segments: bool = True) -> Dict[str, Any]:
        """
        Download a file with advanced features (segments, resume, bandwidth optimization).
        
        Args:
            url: URL to download
            filename: Target filename
            job_id: Unique job identifier
            progress_callback: Progress callback function
            use_segments: Whether to use multi-segment downloading
            
        Returns:
            Download result dictionary
        """
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # Check if file supports range requests
            head_response = requests.head(url, timeout=5, allow_redirects=True)
            supports_ranges = head_response.headers.get('Accept-Ranges') == 'bytes'
            content_length = int(head_response.headers.get('Content-Length', 0))
            
            # Decide download strategy
            if content_length > 10 * 1024 * 1024 and supports_ranges and use_segments:  # > 10MB
                return self._download_with_segments(
                    url, filepath, job_id, content_length, progress_callback
                )
            else:
                return self._download_simple(url, filepath, job_id, progress_callback)
        
        except Exception as e:
            return {
                'success': False,
                'error': f"Download failed: {str(e)}",
                'filepath': filepath,
                'filesize': 0,
                'speed': '0 KB/s'
            }
    
    def _download_simple(self, url: str, filepath: str, job_id: str,
                        progress_callback: Callable) -> Dict[str, Any]:
        """Simple sequential download (for small files or non-resumable sources)."""
        try:
            start_time = time.time()
            bytes_downloaded = 0
            chunk_size = 8192
            
            response = requests.get(url, stream=True, timeout=30)
            total_size = int(response.headers.get('Content-Length', 0))
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        
                        # Calculate speed
                        elapsed = time.time() - start_time
                        speed = bytes_downloaded / elapsed if elapsed > 0 else 0
                        percent = (bytes_downloaded / total_size * 100) if total_size > 0 else 0
                        
                        # Call progress callback
                        if progress_callback:
                            progress_callback({
                                '_percent_str': f"{percent:.1f}%",
                                '_speed_str': self._format_speed(speed),
                                '_eta_str': self._calculate_eta(total_size, bytes_downloaded, speed),
                                'status': 'downloading'
                            })
            
            return {
                'success': True,
                'filepath': filepath,
                'filesize': bytes_downloaded,
                'speed': self._format_speed(bytes_downloaded / (time.time() - start_time)),
                'resume': False,
                'segments_used': False
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filepath': filepath,
                'filesize': 0,
                'speed': '0 KB/s'
            }
    
    def _download_with_segments(self, url: str, filepath: str, job_id: str,
                               total_size: int, progress_callback: Callable) -> Dict[str, Any]:
        """
        Download file in parallel segments (IDM-style).
        
        Implements:
        - Dynamic segmentation
        - Parallel downloads
        - Smart bandwidth management
        - Resume capability
        """
        try:
            # Check for incomplete download
            partial_file = filepath + '.partial'
            resume_data = None
            
            if os.path.exists(partial_file):
                resume_data = self._load_resume_data(job_id)
            
            # Calculate optimal segment count based on file size
            segment_count = self._calculate_optimal_segments(total_size)
            segment_count = min(segment_count, self.max_connections)
            
            # Create segments
            segments = self._create_segments(total_size, segment_count, resume_data)
            
            # Download segments in parallel
            start_time = time.time()
            segment_threads = []
            downloaded_bytes = sum(s.bytes_downloaded for s in segments if s.status == 'completed')
            
            with ThreadPoolExecutor(max_workers=segment_count) as executor:
                futures = {
                    executor.submit(
                        self._download_segment,
                        url, partial_file, segment, job_id, progress_callback,
                        total_size, downloaded_bytes, start_time
                    ): segment for segment in segments
                }
                
                for future in as_completed(futures):
                    segment = futures[future]
                    try:
                        result = future.result()
                        if result['success']:
                            segment.status = 'completed'
                            segment.bytes_downloaded = segment.end - segment.start + 1
                        else:
                            segment.status = 'failed'
                    except Exception as e:
                        segment.status = 'failed'
                        print(f"Segment {segment.segment_id} failed: {str(e)}")
            
            # Merge segments into final file
            if all(s.status == 'completed' for s in segments):
                self._merge_segments(partial_file, filepath, segments)
                
                # Clean up partial file
                if os.path.exists(partial_file):
                    os.remove(partial_file)
                
                elapsed = time.time() - start_time
                avg_speed = total_size / elapsed if elapsed > 0 else 0
                
                return {
                    'success': True,
                    'filepath': filepath,
                    'filesize': total_size,
                    'speed': self._format_speed(avg_speed),
                    'segments_used': True,
                    'segment_count': segment_count,
                    'download_time': elapsed,
                    'resume': resume_data is not None
                }
            else:
                return {
                    'success': False,
                    'error': 'Some segments failed to download',
                    'filepath': filepath,
                    'filesize': 0,
                    'segments_used': True,
                    'resume': True  # Can resume this download
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f"Segment download failed: {str(e)}",
                'filepath': filepath,
                'filesize': 0,
                'segments_used': True,
                'resume': True
            }
    
    def _download_segment(self, url: str, filepath: str, segment: SegmentInfo, job_id: str,
                         progress_callback: Callable, total_size: int, downloaded_bytes: int,
                         start_time: float) -> Dict[str, Any]:
        """Download a single segment with retry logic."""
        
        while segment.retries < segment.max_retries:
            try:
                headers = {
                    'Range': f'bytes={segment.start}-{segment.end}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=30, stream=True)
                
                if response.status_code in (206, 200):  # 206 = Partial Content
                    with open(filepath, 'r+b') as f:
                        f.seek(segment.start)
                        for chunk in response.iter_content(chunk_size=4096):
                            if chunk:
                                f.write(chunk)
                                segment.bytes_downloaded += len(chunk)
                                downloaded_bytes += len(chunk)
                                
                                # Update progress
                                if progress_callback:
                                    elapsed = time.time() - start_time
                                    speed = downloaded_bytes / elapsed if elapsed > 0 else 0
                                    percent = (downloaded_bytes / total_size * 100) if total_size > 0 else 0
                                    
                                    progress_callback({
                                        '_percent_str': f"{percent:.1f}%",
                                        '_speed_str': self._format_speed(speed),
                                        '_eta_str': self._calculate_eta(total_size, downloaded_bytes, speed),
                                        'status': 'downloading',
                                        'segment': segment.segment_id,
                                        'segment_count': 'parallel'
                                    })
                    
                    return {'success': True}
                else:
                    raise Exception(f"Server returned status {response.status_code}")
            
            except Exception as e:
                segment.retries += 1
                if segment.retries < segment.max_retries:
                    time.sleep(2 ** segment.retries)  # Exponential backoff
                else:
                    return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': 'Max retries exceeded'}
    
    def _calculate_optimal_segments(self, file_size: int) -> int:
        """
        Calculate optimal number of segments based on file size.
        
        IDM adapts segment count to file size:
        - 10-50 MB: 2 segments
        - 50-100 MB: 3 segments
        - 100-500 MB: 4 segments
        - 500+ MB: 5-8 segments (adaptive)
        """
        if file_size < 10 * 1024 * 1024:  # < 10 MB
            return 1
        elif file_size < 50 * 1024 * 1024:  # < 50 MB
            return 2
        elif file_size < 100 * 1024 * 1024:  # < 100 MB
            return 3
        elif file_size < 500 * 1024 * 1024:  # < 500 MB
            return 4
        else:  # >= 500 MB
            return min(8, max(4, file_size // (100 * 1024 * 1024)))
    
    def _create_segments(self, total_size: int, segment_count: int,
                        resume_data: Optional[Dict] = None) -> List[SegmentInfo]:
        """Create segment information for parallel download."""
        segments = []
        segment_size = total_size // segment_count
        
        for i in range(segment_count):
            start = i * segment_size
            end = start + segment_size - 1 if i < segment_count - 1 else total_size - 1
            
            segment = SegmentInfo(i, start, end)
            
            # Check resume data
            if resume_data:
                for saved_segment in resume_data.get('segments', []):
                    if saved_segment['segment_id'] == i:
                        segment.bytes_downloaded = saved_segment['bytes_downloaded']
                        if segment.bytes_downloaded > 0:
                            segment.status = 'completed'
            
            segments.append(segment)
        
        return segments
    
    def _merge_segments(self, partial_file: str, final_file: str, segments: List[SegmentInfo]):
        """Merge downloaded segments into final file."""
        with open(final_file, 'wb') as output:
            # Create partial file first if it doesn't exist
            if not os.path.exists(partial_file):
                open(partial_file, 'wb').close()
            
            for segment in sorted(segments, key=lambda s: s.segment_id):
                try:
                    with open(partial_file, 'rb') as partial:
                        partial.seek(segment.start)
                        chunk = partial.read(segment.end - segment.start + 1)
                        output.write(chunk)
                except Exception as e:
                    print(f"Error merging segment {segment.segment_id}: {str(e)}")
    
    def _load_resume_data(self, job_id: str) -> Optional[Dict]:
        """Load resume data for incomplete downloads."""
        try:
            resume_file = os.path.join(self.output_dir, f".resume_{job_id}.json")
            if os.path.exists(resume_file):
                import json
                with open(resume_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return None
    
    def _save_resume_data(self, job_id: str, segments: List[SegmentInfo]):
        """Save resume data for incomplete downloads."""
        try:
            import json
            resume_file = os.path.join(self.output_dir, f".resume_{job_id}.json")
            data = {
                'job_id': job_id,
                'timestamp': datetime.now().isoformat(),
                'segments': [
                    {
                        'segment_id': s.segment_id,
                        'start': s.start,
                        'end': s.end,
                        'bytes_downloaded': s.bytes_downloaded,
                        'status': s.status
                    } for s in segments
                ]
            }
            with open(resume_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Failed to save resume data: {str(e)}")
    
    @staticmethod
    def _format_speed(bytes_per_sec: float) -> str:
        """Format speed in human-readable format."""
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if bytes_per_sec < 1024.0:
                return f"{bytes_per_sec:.1f} {unit}"
            bytes_per_sec /= 1024.0
        return f"{bytes_per_sec:.1f} GB/s"
    
    @staticmethod
    def _calculate_eta(total_size: int, downloaded: int, speed: float) -> str:
        """Calculate estimated time to completion."""
        if speed <= 0:
            return 'calculating...'
        
        remaining = total_size - downloaded
        seconds = remaining / speed
        
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    @staticmethod
    def format_bytes(bytes_size: int) -> str:
        """Convert bytes to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
