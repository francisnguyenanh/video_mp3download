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
    if (!jobs[data.job_id]) {
        // Job not yet in local state — request a queue refresh
        return;
    }
    jobs[data.job_id].status = 'downloading';
    jobs[data.job_id].progress = {
        percent: data.percent,
        speed: data.speed,
        eta: data.eta
    };
    updateJobInPlace(data.job_id);
    updateStats();
});

// Handle download complete
socket.on('download_complete', (data) => {
    if (jobs[data.job_id]) {
        jobs[data.job_id].status = 'completed';
        jobs[data.job_id].filename = data.filename;
        jobs[data.job_id].filesize = data.filesize;
        jobs[data.job_id].title = data.title;
    }
    
    updateStats();
    // Remove completed job from queue display
    updateQueueUI();
    loadFiles();
    showToast(`✅ Download complete: ${data.title}`, 'success');
});

// Handle download error
socket.on('download_error', (data) => {
    if (jobs[data.job_id]) {
        jobs[data.job_id].status = 'failed';
        jobs[data.job_id].error = data.error;
    }
    
    updateQueueUI();
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
    clearErrors(); // Clear previous errors
    
    if (!input) {
        showError('Please paste at least one URL');
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
        showError('No valid URLs found');
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
            clearErrors(); // Clear any existing errors
            showToast(`✅ Added ${data.job_ids.length} URL(s) to queue`, 'success');
            
            if (data.warnings && data.warnings.length > 0) {
                data.warnings.forEach(warning => {
                    showToast(`⚠️ ${warning}`, 'warning');
                });
            }
            
            clearInput();
        } else {
            // Handle detailed validation errors from server
            if (data.details && data.details.length > 0) {
                showErrors(data.details);
                showToast('Validation errors detected', 'error');
            } else {
                showError(data.error || 'An error occurred');
                showToast(`Error: ${data.error || 'An error occurred'}`, 'error');
            }
        }
    } catch (error) {
        showError(`Network error: ${error.message}`);
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

// Update queue UI — only show pending / downloading / failed
function updateQueueUI() {
    const container = document.getElementById('queueContainer');
    
    const activeJobs = Object.values(jobs).filter(j => j.status !== 'completed');
    
    if (activeJobs.length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-400 py-8">
                <p>No active downloads</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = activeJobs
        .sort((a, b) => {
            const statusOrder = { downloading: 0, pending: 1, failed: 2 };
            return statusOrder[a.status] - statusOrder[b.status];
        })
        .map(job => renderJobCard(job))
        .join('');
}

// Render individual job card
function renderJobCard(job) {
    const icon = statusIcon(job.status);
    const borderColor = statusBorderColor(job.status);
    const statusText = job.status.charAt(0).toUpperCase() + job.status.slice(1);

    // Format badge
    const modeIcon = job.icon || (job.mode === 'video' ? '🎬' : '🎵');
    const qualityLabel = job.mode === 'video' ? job.quality : (job.quality + 'k');
    const formatBadge = `${modeIcon} [${(job.format || '').toUpperCase()} &bull; ${qualityLabel}]`;

    return `
        <div class="bg-gray-700 border-l-4 ${borderColor} p-4 rounded" data-job-id="${job.job_id}">
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <div class="job-status flex items-center gap-2 mb-2">
                        <span class="text-xl">${icon}</span>
                        <span class="text-xs font-bold text-blue-400">${formatBadge}</span>
                        <span class="text-sm font-semibold text-gray-400">${statusText}</span>
                    </div>
                    <div class="text-sm text-gray-300 break-all">${job.url}</div>
                    ${job.title ? `<div class="text-sm text-gray-400 mt-1"><strong>${job.title}</strong></div>` : ''}
                    <div class="job-progress">${renderProgressHTML(job)}</div>
                </div>
            </div>
        </div>
    `;
}

// Update individual job UI in-place (for smooth progress without full re-render)
function updateJobInPlace(jobId) {
    const el = document.querySelector(`[data-job-id="${jobId}"]`);
    if (!el) {
        // Element not found — do a full rebuild
        updateQueueUI();
        return;
    }
    const job = jobs[jobId];
    if (!job) return;

    // Update border color
    el.className = el.className.replace(/border-\S+/, statusBorderColor(job.status));

    // Update status icon + text
    const statusEl = el.querySelector('.job-status');
    if (statusEl) statusEl.innerHTML = `<span class="text-xl">${statusIcon(job.status)}</span><span class="text-sm font-semibold text-gray-400">${job.status.charAt(0).toUpperCase() + job.status.slice(1)}</span>`;

    // Update progress bar
    const progressEl = el.querySelector('.job-progress');
    if (progressEl) progressEl.innerHTML = renderProgressHTML(job);
}

function statusIcon(status) {
    return { pending: '⏳', downloading: '🔄', completed: '✅', failed: '❌' }[status] || '❓';
}

function statusBorderColor(status) {
    return { pending: 'border-gray-600', downloading: 'border-yellow-500', completed: 'border-green-500', failed: 'border-red-500' }[status] || 'border-gray-600';
}

function renderProgressHTML(job) {
    if (job.status === 'downloading') {
        const percent = job.progress?.percent || '0%';
        const percentValue = parseFloat(percent) || 0;
        const speed = job.progress?.speed || 'N/A';
        const eta = job.progress?.eta || 'N/A';
        return `
            <div class="mt-3">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${percentValue}%"></div>
                </div>
                <div class="flex justify-between items-center mt-2 text-sm text-gray-400">
                    <span class="font-bold text-blue-400">${percent}</span>
                    <span>${speed} &bull; ETA ${eta}</span>
                </div>
            </div>
        `;
    } else if (job.status === 'failed') {
        return `<div class="mt-3 text-sm text-red-400"><strong>Error:</strong> ${job.error || 'Unknown error'}</div>`;
    }
    return '';
}

// Update individual job UI
function updateJobUI(jobId) {
    updateQueueUI();
}

const videoExts = new Set(['mp4', 'mkv', 'webm', 'avi', 'mov']);
const audioExts = new Set(['mp3', 'm4a', 'ogg', 'wav', 'flac']);

function getFileBadge(ext) {
    if (videoExts.has(ext)) return '<span class="text-xs font-bold bg-blue-700 text-blue-100 px-2 py-0.5 rounded">VIDEO</span>';
    if (audioExts.has(ext)) return '<span class="text-xs font-bold bg-purple-700 text-purple-100 px-2 py-0.5 rounded">AUDIO</span>';
    return '';
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
            const badge = getFileBadge(fileExt);
            const safeFilename = file.filename.replace(/'/g, "\\'");
            
            return `
                <div class="flex items-center justify-between bg-gray-700 p-4 rounded hover:bg-gray-600 transition">
                    <div class="flex-1 min-w-0 flex items-center gap-3">
                        <span class="text-2xl">${fileIcon}</span>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2 mb-1">
                                ${badge}
                                <span class="text-xs text-gray-400 uppercase">${fileExt}</span>
                            </div>
                            <div class="text-sm font-semibold text-gray-100 truncate" title="${file.filename}">${file.filename}</div>
                            <div class="text-xs text-gray-400 mt-1">${file.size}</div>
                        </div>
                    </div>
                    <div class="flex gap-2 ml-4">
                        <button
                            onclick="downloadFile('${safeFilename}')"
                            class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold py-2 px-3 rounded transition"
                        >
                            ↓ Download
                        </button>
                        <button
                            onclick="deleteFile('${safeFilename}')"
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

// Display multiple validation errors in the error messages panel
function showErrors(errorArray) {
    const errorMessages = document.getElementById('errorMessages');
    const errorList = document.getElementById('errorList');
    
    if (!errorMessages || !errorList) {
        console.error('Error display elements not found');
        return;
    }
    
    // Clear previous errors
    errorList.innerHTML = '';
    
    // Add each error as a list item
    if (Array.isArray(errorArray) && errorArray.length > 0) {
        errorArray.forEach(error => {
            const li = document.createElement('li');
            li.textContent = error;
            errorList.appendChild(li);
        });
        
        // Show the error messages panel
        errorMessages.classList.remove('hidden');
    }
}

// Display a single error message
function showError(message) {
    showErrors([message]);
}

// Clear all error messages
function clearErrors() {
    const errorMessages = document.getElementById('errorMessages');
    const errorList = document.getElementById('errorList');
    
    if (errorMessages) {
        errorMessages.classList.add('hidden');
    }
    
    if (errorList) {
        errorList.innerHTML = '';
    }
}

// Open downloads folder
async function openFolder() {
    try {
        const response = await fetch('/api/open-folder', { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            showToast(`📂 Opening folder: ${data.path}`, 'success');
        } else {
            showToast(`Cannot open folder: ${data.error}`, 'error');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
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
