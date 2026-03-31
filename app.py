import os
import queue
import threading
import uuid
from flask import Flask, render_template, request, send_file, jsonify
from flask_socketio import SocketIO, emit
from downloader import VideoDownloader
from pathlib import Path

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

OUTPUT_DIR = "./downloads"
downloader = VideoDownloader(OUTPUT_DIR)

download_queue = queue.Queue()
current_jobs = {}
job_lock = threading.Lock()
queue_worker_running = False


def make_progress_hook(job_id):
    """Create a progress hook for yt-dlp."""
    def hook(d):
        with job_lock:
            if job_id not in current_jobs:
                return
            
            if d['status'] == 'downloading':
                percent_str = d.get('_percent_str', '0%').strip()
                speed_str = d.get('_speed_str', 'N/A').strip()
                eta_str = d.get('_eta_str', 'N/A').strip()
                filename = d.get('info_dict', {}).get('_filename', '')
                
                current_jobs[job_id]['progress'] = {
                    'percent': percent_str,
                    'speed': speed_str,
                    'eta': eta_str
                }
                
                socketio.emit('download_progress', {
                    'job_id': job_id,
                    'percent': percent_str,
                    'speed': speed_str,
                    'eta': eta_str,
                    'filename': os.path.basename(filename) if filename else 'downloading',
                    'status': 'downloading'
                }, namespace='/')
            
            elif d['status'] == 'finished':
                current_jobs[job_id]['progress'] = {
                    'percent': '100%',
                    'status': 'converting'
                }
                socketio.emit('download_progress', {
                    'job_id': job_id,
                    'percent': '100%',
                    'status': 'merging',
                    'message': f"Processing {current_jobs[job_id]['format'].upper()}..."
                }, namespace='/')
    
    return hook


def queue_worker():
    """Process downloads from queue sequentially."""
    global queue_worker_running
    queue_worker_running = True
    
    while True:
        job = download_queue.get()
        
        if job is None:
            break
        
        job_id = job['job_id']
        url = job['url']
        mode = job.get('mode', 'video')
        format_type = job.get('format', 'mp4')
        quality = job.get('quality', 'best')
        bitrate = job.get('bitrate', '192')
        
        try:
            with job_lock:
                current_jobs[job_id]['status'] = 'downloading'
            
            socketio.emit('queue_update', {'jobs': get_jobs_summary()}, namespace='/')
            
            progress_hook = make_progress_hook(job_id)
            result = downloader.download(url, job_id, progress_hook, mode, format_type, quality, bitrate)
            
            with job_lock:
                if result['success']:
                    current_jobs[job_id]['status'] = 'completed'
                    current_jobs[job_id]['filename'] = result['filename']
                    current_jobs[job_id]['filesize'] = result['filesize']
                    current_jobs[job_id]['title'] = result['title']
                    
                    socketio.emit('download_complete', {
                        'job_id': job_id,
                        'filename': result['filename'],
                        'filesize': VideoDownloader.format_bytes(result['filesize']),
                        'title': result['title']
                    }, namespace='/')
                else:
                    current_jobs[job_id]['status'] = 'failed'
                    current_jobs[job_id]['error'] = result['error']
                    
                    socketio.emit('download_error', {
                        'job_id': job_id,
                        'error': result['error']
                    }, namespace='/')
            
            socketio.emit('queue_update', {'jobs': get_jobs_summary()}, namespace='/')
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            with job_lock:
                current_jobs[job_id]['status'] = 'failed'
                current_jobs[job_id]['error'] = error_msg
            
            socketio.emit('download_error', {
                'job_id': job_id,
                'error': error_msg
            }, namespace='/')
        
        finally:
            download_queue.task_done()


def get_jobs_summary():
    """Get summary of all jobs."""
    with job_lock:
        jobs = []
        for job_id, job_data in current_jobs.items():
            jobs.append({
                'job_id': job_id,
                'url': job_data['url'],
                'status': job_data['status'],
                'progress': job_data.get('progress', {}),
                'filename': job_data.get('filename'),
                'filesize': job_data.get('filesize'),
                'error': job_data.get('error'),
                'mode': job_data.get('mode', 'video'),
                'format': job_data.get('format', 'mp4'),
                'quality': job_data.get('quality', 'best'),
                'bitrate': job_data.get('bitrate'),
                'title': job_data.get('title', ''),
                'icon': job_data.get('icon', '🎬')
            })
        return jobs


def is_valid_url(url):
    """Check if URL is valid."""
    url = url.strip()
    return url.startswith(('http://', 'https://'))


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/add', methods=['POST'])
def add_to_queue():
    """Add URLs to download queue with format selection."""
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        mode = data.get('mode', 'video')  # 'video' or 'audio'
        format_type = data.get('format', 'mp4')
        quality = data.get('quality', 'best')
        bitrate = data.get('audio_bitrate', '192')
        
        if not urls:
            return jsonify({'error': 'No URLs provided'}), 400
        
        job_ids = []
        duplicate_count = 0
        invalid_count = 0
        
        for url in urls:
            url = url.strip()
            
            if not url:
                continue
            
            if not is_valid_url(url):
                invalid_count += 1
                continue
            
            # Check for duplicates
            with job_lock:
                is_duplicate = any(
                    job['url'] == url for job in current_jobs.values()
                )
            
            if is_duplicate:
                duplicate_count += 1
            
            job_id = str(uuid.uuid4())
            
            # Determine icon based on mode
            icon = '🎬' if mode == 'video' else '🎵'
            
            with job_lock:
                current_jobs[job_id] = {
                    'url': url,
                    'status': 'pending',
                    'progress': {},
                    'filename': None,
                    'filesize': 0,
                    'error': None,
                    'mode': mode,
                    'format': format_type,
                    'quality': quality if mode == 'video' else bitrate,
                    'bitrate': bitrate if mode == 'audio' else None,
                    'title': '',
                    'icon': icon
                }
            
            download_queue.put({
                'job_id': job_id,
                'url': url,
                'mode': mode,
                'format': format_type,
                'quality': quality,
                'bitrate': bitrate
            })
            
            job_ids.append(job_id)
        
        socketio.emit('queue_update', {'jobs': get_jobs_summary()}, namespace='/')
        
        warnings = []
        if duplicate_count > 0:
            warnings.append(f"{duplicate_count} URL(s) already in queue")
        if invalid_count > 0:
            warnings.append(f"{invalid_count} URL(s) are invalid")
        
        return jsonify({
            'success': True,
            'job_ids': job_ids,
            'warnings': warnings
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current queue status."""
    jobs = get_jobs_summary()
    
    stats = {
        'pending': sum(1 for j in jobs if j['status'] == 'pending'),
        'downloading': sum(1 for j in jobs if j['status'] == 'downloading'),
        'completed': sum(1 for j in jobs if j['status'] == 'completed'),
        'failed': sum(1 for j in jobs if j['status'] == 'failed')
    }
    
    return jsonify({
        'jobs': jobs,
        'stats': stats,
        'queue_size': download_queue.qsize()
    }), 200


@app.route('/api/files', methods=['GET'])
def list_files():
    """List all downloaded files."""
    try:
        files = []
        if os.path.exists(OUTPUT_DIR):
            for filename in os.listdir(OUTPUT_DIR):
                filepath = os.path.join(OUTPUT_DIR, filename)
                if os.path.isfile(filepath):
                    filesize = os.path.getsize(filepath)
                    files.append({
                        'filename': filename,
                        'size': VideoDownloader.format_bytes(filesize),
                        'size_bytes': filesize,
                        'timestamp': os.path.getmtime(filepath)
                    })
        
        # Sort by timestamp descending
        files.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({'files': files}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download a file."""
    try:
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # Security check
        if not os.path.abspath(filepath).startswith(os.path.abspath(OUTPUT_DIR)):
            return jsonify({'error': 'Invalid file'}), 403
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a downloaded file."""
    try:
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # Security check
        if not os.path.abspath(filepath).startswith(os.path.abspath(OUTPUT_DIR)):
            return jsonify({'error': 'Invalid file'}), 403
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        os.remove(filepath)
        
        socketio.emit('file_deleted', {'filename': filename}, namespace='/')
        
        return jsonify({'success': True}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/queue/clear', methods=['POST'])
def clear_completed_jobs():
    """Remove completed and failed jobs from queue display."""
    try:
        with job_lock:
            jobs_to_remove = [
                job_id for job_id, job_data in current_jobs.items()
                if job_data['status'] in ['completed', 'failed']
            ]
            for job_id in jobs_to_remove:
                del current_jobs[job_id]
        
        socketio.emit('queue_update', {'jobs': get_jobs_summary()}, namespace='/')
        
        return jsonify({'success': True, 'removed_count': len(jobs_to_remove)}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    emit('queue_update', {'jobs': get_jobs_summary()})
    
    files = []
    if os.path.exists(OUTPUT_DIR):
        for filename in os.listdir(OUTPUT_DIR):
            filepath = os.path.join(OUTPUT_DIR, filename)
            if os.path.isfile(filepath):
                filesize = os.path.getsize(filepath)
                files.append({
                    'filename': filename,
                    'size': VideoDownloader.format_bytes(filesize),
                    'timestamp': os.path.getmtime(filepath)
                })
    
    emit('files_updated', {'files': files})


if __name__ == '__main__':
    # Start the queue worker thread
    worker_thread = threading.Thread(target=queue_worker, daemon=True)
    worker_thread.start()
    
    # Create downloads directory if it doesn't exist
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Run the app
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
