// Initialize Socket.IO connection
const socket = io();

// State management
let jobs = {};
let files = {};
let stats = {
    pending: 0,
    downloading: 0,
    completed: 0,
    failed: 0
};

// Format icon mapping
const iconMap = {
    mp4: '🎬',
    mkv: '🎬',
    webm: '🎬',
    mp3: '🎵',
    m4a: '🎵',
    ogg: '🎵'
};

// Mode change handler
function onModeChange(mode) {
    const videoOptions = document.getElementById('video-options');
    const audioOptions = document.getElementById('audio-options');
    const btnIcon = document.getElementById('btn-icon');
    const btnText = document.getElementById('btn-text');
    
    if (mode === 'audio') {
        videoOptions.classList.add('hidden');
        audioOptions.classList.remove('hidden');
        btnIcon.textContent = '🎵';
        btnText.textContent = 'Add Audio to Queue';
    } else {
        videoOptions.classList.remove('hidden');
        audioOptions.classList.add('hidden');
        btnIcon.textContent = '🎬';
        btnText.textContent = 'Add Video to Queue';
    }
}

// Connect to Socket.IO
socket.on('connect', () => {
    console.log('Connected to server');
    loadFiles();
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

// Handle queue updates
socket.on('queue_update', (data) => {
    if (data.jobs) {
        jobs = {};
        stats = {
            pending: 0,
            downloading: 0,
            completed: 0,
            failed: 0
        };
        
        data.jobs.forEach(job => {
            jobs[job.job_id] = job;
            stats[job.status]++;
        });
        
        updateQueueUI();
        updateStats();
    }
});

// Handle download progress
socket.on('download_progress', (data) => {
    if (jobs[data.job_id]) {
        jobs[data.job_id].progress = data;
        updateJobUI(data.job_id);
    }
});

// Handle download complete
socket.on('download_complete', (data) => {
    if (jobs[data.job_id]) {
        jobs[data.job_id].status = 'completed';
        jobs[data.job_id].filename = data.filename;
        jobs[data.job_id].filesize = data.filesize;
        jobs[data.job_id].title = data.title;
    }
    
    stats.downloading--;
    stats.completed++;
    
    updateJobUI(data.job_id);
    updateStats();
    loadFiles();
    showToast(`✅ Download complete: ${data.title}`, 'success');
});

// Handle download error
socket.on('download_error', (data) => {
    if (jobs[data.job_id]) {
        jobs[data.job_id].status = 'failed';
        jobs[data.job_id].error = data.error;
    }
    
    stats.downloading--;
    stats.failed++;
    
    updateJobUI(data.job_id);
    updateStats();
    showToast(`❌ Download failed: ${data.error}`, 'error');
});

// Handle files updated
socket.on('files_updated', (data) => {
    if (data.files) {
        files = {};
        data.files.forEach(file => {
            files[file.filename] = file;
        });
        updateFilesUI();
    }
});

// Handle file deleted
socket.on('file_deleted', (data) => {
    if (files[data.filename]) {
        delete files[data.filename];
        updateFilesUI();
    }
});

// Add URLs to download queue
async function addToQueue() {
    const input = document.getElementById('urlInput').value.trim();
    
    if (!input) {
        showToast('Please paste at least one URL', 'warning');
        return;
    }
    
    // Get selected format options
    const mode = document.querySelector('input[name="mode"]:checked').value;
    let format, quality, bitrate;
    
    if (mode === 'audio') {
        format = document.getElementById('audio-format').value;
        bitrate = document.getElementById('audio-bitrate').value;
        quality = 'best';
    } else {
        format = document.getElementById('video-format').value;
        quality = document.getElementById('video-quality').value;
        bitrate = '192';
    }
    
    // Parse URLs - split by newlines and commas
    const urlList = input
        .split(/[\n,]+/)
        .map(url => url.trim())
        .filter(url => url.length > 0);
    
    if (urlList.length === 0) {
        showToast('No valid URLs found', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                urls: urlList,
                mode: mode,
                format: format,
                quality: quality,
                audio_bitrate: bitrate
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`✅ Added ${data.job_ids.length} URL(s) to queue`, 'success');
            
            if (data.warnings && data.warnings.length > 0) {
                data.warnings.forEach(warning => {
                    showToast(`⚠️ ${warning}`, 'warning');
                });
            }
            
            clearInput();
        } else {
            showToast(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Clear input textarea
function clearInput() {
    document.getElementById('urlInput').value = '';
}

// Load downloaded files
async function loadFiles() {
    try {
        const response = await fetch('/api/files');
        const data = await response.json();
        
        if (response.ok) {
            files = {};
            data.files.forEach(file => {
                files[file.filename] = file;
            });
            updateFilesUI();
        }
    } catch (error) {
        console.error('Error loading files:', error);
    }
}

// Download a file
async function downloadFile(filename) {
    try {
        const response = await fetch(`/api/download/${encodeURIComponent(filename)}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            showToast('Error downloading file', 'error');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Delete a file
async function deleteFile(filename) {
    if (!confirm(`Delete "${filename}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/files/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast('File deleted', 'success');
            loadFiles();
        } else {
            showToast('Error deleting file', 'error');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Clear completed jobs
async function clearCompleted() {
    try {
        const response = await fetch('/api/queue/clear', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Cleared ${data.removed_count} job(s)`, 'success');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Update queue UI
function updateQueueUI() {
    const container = document.getElementById('queueContainer');
    
    if (Object.keys(jobs).length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-400 py-8">
                <p>No downloads added yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = Object.values(jobs)
        .sort((a, b) => {
            const statusOrder = { downloading: 0, pending: 1, completed: 2, failed: 3 };
            return statusOrder[a.status] - statusOrder[b.status];
        })
        .map(job => renderJobCard(job))
        .join('');
}

// Render individual job card
function renderJobCard(job) {
    let statusIcon = '';
    let statusColor = '';
    let statusText = '';
    
    switch (job.status) {
        case 'pending':
            statusIcon = '⏳';
            statusColor = 'border-gray-600';
            statusText = 'Pending';
            break;
        case 'downloading':
            statusIcon = '🔄';
            statusColor = 'border-yellow-500';
            statusText = 'Downloading';
            break;
        case 'completed':
            statusIcon = '✅';
            statusColor = 'border-green-500';
            statusText = 'Completed';
            break;
        case 'failed':
            statusIcon = '❌';
            statusColor = 'border-red-500';
            statusText = 'Failed';
            break;
    }
    
    // Format badge
    const modeIcon = job.icon || (job.mode === 'video' ? '🎬' : '🎵');
    const qualityLabel = job.mode === 'video' ? job.quality : job.quality + 'k';
    const formatBadge = `${modeIcon} [${job.format.toUpperCase()} • ${qualityLabel}]`;
    
    let progressHTML = '';
    
    if (job.status === 'downloading') {
        const percent = job.progress?.percent || '0%';
        const percentValue = parseInt(percent) || 0;
        const speed = job.progress?.speed || 'N/A';
        const eta = job.progress?.eta || 'N/A';
        
        progressHTML = `
            <div class="mt-3">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${percentValue}%"></div>
                </div>
                <div class="flex justify-between items-center mt-2 text-sm text-gray-400">
                    <span>${percent}</span>
                    <span>• ${speed} • ETA ${eta}</span>
                </div>
            </div>
        `;
    } else if (job.status === 'failed') {
        progressHTML = `
            <div class="mt-3 text-sm text-red-400">
                <strong>Error:</strong> ${job.error || 'Unknown error'}
            </div>
        `;
    }
    
    let actionHTML = '';
    
    if (job.status === 'completed' && job.filename) {
        const fileExt = job.filename.split('.').pop().toLowerCase();
        const fileIcon = iconMap[fileExt] || '📄';
        
        actionHTML = `
            <div class="mt-3 flex gap-2">
                <button
                    onclick="downloadFile('${job.filename}')"
                    class="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold py-2 px-3 rounded transition"
                >
                    ↓ Download
                </button>
                <span class="text-sm text-gray-400 py-2">
                    ${job.filesize || 'Unknown size'}
                </span>
            </div>
        `;
    }
    
    return `
        <div class="bg-gray-700 border-l-4 ${statusColor} p-4 rounded">
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="text-xl">${statusIcon}</span>
                        <span class="text-xs font-bold text-blue-400">${formatBadge}</span>
                        <span class="text-sm font-semibold text-gray-400">${statusText}</span>
                    </div>
                    <div class="text-sm text-gray-300 break-all">${job.url}</div>
                    ${job.title ? `<div class="text-sm text-gray-400 mt-1"><strong>${job.title}</strong></div>` : ''}
                    ${progressHTML}
                    ${actionHTML}
                </div>
            </div>
        </div>
    `;
}

// Update individual job UI
function updateJobUI(jobId) {
    const container = document.getElementById('queueContainer');
    const existingCards = container.querySelectorAll('[data-job-id]');
    
    // If we don't have data-job-id attributes, rebuild the whole UI
    if (existingCards.length === 0) {
        updateQueueUI();
        return;
    }
    
    updateQueueUI();
}

// Update files UI
function updateFilesUI() {
    const container = document.getElementById('filesContainer');
    const fileArray = Object.values(files);
    
    if (fileArray.length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-400 py-8">
                <p>No files downloaded yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = fileArray
        .map(file => {
            const fileExt = file.filename.split('.').pop().toLowerCase();
            const fileIcon = iconMap[fileExt] || '📄';
            
            return `
                <div class="flex items-center justify-between bg-gray-700 p-4 rounded hover:bg-gray-650 transition">
                    <div class="flex-1 min-w-0 flex items-center gap-3">
                        <span class="text-2xl">${fileIcon}</span>
                        <div class="flex-1 min-w-0">
                            <div class="text-sm font-semibold text-gray-100 truncate">${file.filename}</div>
                            <div class="text-xs text-gray-400 mt-1">${file.size}</div>
                        </div>
                    </div>
                    <div class="flex gap-2 ml-4">
                        <button
                            onclick="downloadFile('${file.filename}')"
                            class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold py-2 px-3 rounded transition"
                        >
                            ↓ Download
                        </button>
                        <button
                            onclick="deleteFile('${file.filename}')"
                            class="bg-red-600 hover:bg-red-700 text-white text-sm font-semibold py-2 px-3 rounded transition"
                        >
                            🗑 Delete
                        </button>
                    </div>
                </div>
            `;
        })
        .join('');
}

// Update stats display
function updateStats() {
    document.getElementById('statPending').textContent = stats.pending;
    document.getElementById('statDownloading').textContent = stats.downloading;
    document.getElementById('statCompleted').textContent = stats.completed;
    document.getElementById('statFailed').textContent = stats.failed;
}

// Show toast notification
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out forwards';
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, 3000);
}

// Add slideOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
