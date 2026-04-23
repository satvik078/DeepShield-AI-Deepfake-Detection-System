/**
 * Dashboard Logic
 * File upload, webcam capture, prediction display, and Grad-CAM rendering.
 */

document.addEventListener('DOMContentLoaded', () => {
    if (!requireAuth()) return;

    initTabs();
    initImageUpload();
    initVideoUpload();
    initWebcam();
    loadUserInfo();
});

// ── User Info ──────────────────────────────────────────────
async function loadUserInfo() {
    try {
        const data = await API.request('/auth/me');
        const user = data.user;
        const welcome = document.getElementById('welcome-name');
        if (welcome) welcome.textContent = user.name;
    } catch (e) {
        console.error('Failed to load user info:', e);
    }
}

// ── Tab Navigation ─────────────────────────────────────────
function initTabs() {
    const btns = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');

    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tab;

            btns.forEach(b => b.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(`tab-${target}`).classList.add('active');

            // Stop webcam when switching away
            if (target !== 'webcam') stopWebcam();
        });
    });
}

// ── Image Upload ───────────────────────────────────────────
function initImageUpload() {
    const area = document.getElementById('image-upload-area');
    const input = document.getElementById('image-input');
    const preview = document.getElementById('image-preview');
    const previewImg = document.getElementById('image-preview-img');
    const analyzeBtn = document.getElementById('analyze-image-btn');

    if (!area) return;

    // Drag & Drop
    ['dragenter', 'dragover'].forEach(evt => {
        area.addEventListener(evt, e => {
            e.preventDefault();
            area.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(evt => {
        area.addEventListener(evt, e => {
            e.preventDefault();
            area.classList.remove('dragover');
        });
    });

    area.addEventListener('drop', e => {
        const file = e.dataTransfer.files[0];
        if (file) handleImageSelect(file);
    });

    input.addEventListener('change', e => {
        if (e.target.files[0]) handleImageSelect(e.target.files[0]);
    });

    function handleImageSelect(file) {
        if (!file.type.startsWith('image/')) {
            showToast('Please select an image file.', 'error');
            return;
        }

        const reader = new FileReader();
        reader.onload = e => {
            previewImg.src = e.target.result;
            preview.classList.add('show');
            analyzeBtn.classList.remove('hidden');
            analyzeBtn.dataset.file = file.name;
        };
        reader.readAsDataURL(file);

        // Store file for later upload
        analyzeBtn._file = file;
    }

    analyzeBtn.addEventListener('click', () => analyzeImage(analyzeBtn._file));
}

async function analyzeImage(file) {
    if (!file) return;

    const btn = document.getElementById('analyze-image-btn');
    const results = document.getElementById('image-results');
    const loading = document.getElementById('loading-overlay');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Analyzing...';
    loading.classList.add('show');

    try {
        const data = await API.uploadFile('/predict/image', file);

        displayImageResult(data);
        results.classList.add('show');
        showToast('Analysis complete!', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🔍 Analyze Image';
        loading.classList.remove('show');
    }
}

function displayImageResult(data) {
    const { prediction, heatmap, explanation } = data;

    // Badge
    const badge = document.getElementById('result-badge');
    badge.className = `result-badge ${prediction.label.toLowerCase()}`;
    badge.textContent = `${prediction.label}`;

    // Confidence
    const bar = document.getElementById('confidence-bar');
    const label = document.getElementById('confidence-value');
    bar.style.width = `${prediction.confidence}%`;
    bar.className = `confidence-bar ${prediction.label === 'FAKE' ? 'danger' : ''}`;
    label.textContent = `${prediction.confidence}%`;

    // Heatmap
    const heatmapImg = document.getElementById('heatmap-img');
    if (heatmap) {
        heatmapImg.src = `data:image/png;base64,${heatmap}`;
        heatmapImg.parentElement.classList.remove('hidden');
    }

    // Explanation
    const summary = document.getElementById('explanation-summary');
    const details = document.getElementById('explanation-details');
    summary.textContent = explanation.summary;
    details.innerHTML = explanation.details.map(d => `<li>${d}</li>`).join('');

    // Risk level
    const risk = document.getElementById('risk-level');
    if (risk && explanation.risk_level) {
        const colors = { low: 'var(--accent-green)', medium: 'var(--accent-orange)', high: 'var(--accent-red)' };
        risk.textContent = explanation.risk_level.toUpperCase();
        risk.style.color = colors[explanation.risk_level] || 'var(--text-secondary)';
    }
}

// ── Video Upload ───────────────────────────────────────────
function initVideoUpload() {
    const area = document.getElementById('video-upload-area');
    const input = document.getElementById('video-input');
    const preview = document.getElementById('video-preview');
    const previewVid = document.getElementById('video-preview-vid');
    const analyzeBtn = document.getElementById('analyze-video-btn');

    if (!area) return;

    ['dragenter', 'dragover'].forEach(evt => {
        area.addEventListener(evt, e => {
            e.preventDefault();
            area.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(evt => {
        area.addEventListener(evt, e => {
            e.preventDefault();
            area.classList.remove('dragover');
        });
    });

    area.addEventListener('drop', e => {
        const file = e.dataTransfer.files[0];
        if (file) handleVideoSelect(file);
    });

    input.addEventListener('change', e => {
        if (e.target.files[0]) handleVideoSelect(e.target.files[0]);
    });

    function handleVideoSelect(file) {
        if (!file.type.startsWith('video/')) {
            showToast('Please select a video file.', 'error');
            return;
        }

        const url = URL.createObjectURL(file);
        previewVid.src = url;
        preview.classList.add('show');
        analyzeBtn.classList.remove('hidden');
        analyzeBtn._file = file;
    }

    analyzeBtn.addEventListener('click', () => analyzeVideo(analyzeBtn._file));
}

async function analyzeVideo(file) {
    if (!file) return;

    const btn = document.getElementById('analyze-video-btn');
    const results = document.getElementById('video-results');
    const loading = document.getElementById('loading-overlay');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Processing video...';
    loading.classList.add('show');
    document.getElementById('loading-text').textContent = 'Analyzing video frames... This may take a moment.';

    try {
        const data = await API.uploadFile('/predict/video', file);

        displayVideoResult(data);
        results.classList.add('show');
        showToast('Video analysis complete!', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🎬 Analyze Video';
        loading.classList.remove('show');
    }
}

function displayVideoResult(data) {
    const { aggregate, video_info, frames_analyzed, faces_detected } = data;

    const badge = document.getElementById('video-result-badge');
    badge.className = `result-badge ${aggregate.label.toLowerCase()}`;
    badge.textContent = aggregate.label;

    const bar = document.getElementById('video-confidence-bar');
    const label = document.getElementById('video-confidence-value');
    bar.style.width = `${aggregate.confidence}%`;
    bar.className = `confidence-bar ${aggregate.label === 'FAKE' ? 'danger' : ''}`;
    label.textContent = `${aggregate.confidence}%`;

    // Video stats
    const stats = document.getElementById('video-stats');
    stats.innerHTML = `
        <div class="stat-item">
            <span class="stat-label">Frames Analyzed</span>
            <span class="stat-value">${frames_analyzed}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Faces Detected</span>
            <span class="stat-value">${faces_detected}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Fake Frames</span>
            <span class="stat-value">${aggregate.fake_frames} (${aggregate.fake_ratio}%)</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Duration</span>
            <span class="stat-value">${video_info.duration?.toFixed(1) || '—'}s</span>
        </div>
    `;
}

// ── Webcam ─────────────────────────────────────────────────
let webcamStream = null;
let webcamInterval = null;

function initWebcam() {
    const startBtn = document.getElementById('start-webcam-btn');
    const stopBtn = document.getElementById('stop-webcam-btn');

    if (startBtn) startBtn.addEventListener('click', startWebcam);
    if (stopBtn) stopBtn.addEventListener('click', stopWebcam);
}

async function startWebcam() {
    const video = document.getElementById('webcam-video');
    const startBtn = document.getElementById('start-webcam-btn');
    const stopBtn = document.getElementById('stop-webcam-btn');
    const liveLabel = document.getElementById('webcam-live');

    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: 'user' },
        });
        video.srcObject = webcamStream;
        await video.play();

        startBtn.classList.add('hidden');
        stopBtn.classList.remove('hidden');
        if (liveLabel) liveLabel.classList.remove('hidden');

        // Start real-time detection loop (every 2 seconds)
        webcamInterval = setInterval(captureAndPredict, 2000);

        showToast('Webcam started. Real-time detection active.', 'success');
    } catch (error) {
        showToast('Camera access denied. Please allow camera permissions.', 'error');
    }
}

function stopWebcam() {
    if (webcamStream) {
        webcamStream.getTracks().forEach(t => t.stop());
        webcamStream = null;
    }
    if (webcamInterval) {
        clearInterval(webcamInterval);
        webcamInterval = null;
    }

    const video = document.getElementById('webcam-video');
    const startBtn = document.getElementById('start-webcam-btn');
    const stopBtn = document.getElementById('stop-webcam-btn');
    const liveLabel = document.getElementById('webcam-live');

    if (video) video.srcObject = null;
    if (startBtn) startBtn.classList.remove('hidden');
    if (stopBtn) stopBtn.classList.add('hidden');
    if (liveLabel) liveLabel.classList.add('hidden');
}

async function captureAndPredict() {
    const video = document.getElementById('webcam-video');
    if (!video || !webcamStream) return;

    // Capture frame to canvas
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    const frameBase64 = canvas.toDataURL('image/jpeg', 0.8);

    try {
        const data = await API.request('/predict/webcam', {
            method: 'POST',
            body: { frame: frameBase64 },
        });

        displayWebcamResult(data);
    } catch (e) {
        // Silently fail for individual frames
        console.warn('Webcam prediction error:', e.message);
    }
}

function displayWebcamResult(data) {
    const { prediction } = data;
    const badge = document.getElementById('webcam-result-badge');
    const conf = document.getElementById('webcam-confidence');

    if (!badge) return;

    if (prediction.label === 'NO FACE') {
        badge.className = 'result-badge';
        badge.textContent = 'NO FACE';
        badge.style.background = 'rgba(100,100,100,0.2)';
        badge.style.color = 'var(--text-muted)';
        badge.style.border = '1px solid rgba(100,100,100,0.3)';
        if (conf) conf.textContent = '';
        return;
    }

    badge.className = `result-badge ${prediction.label.toLowerCase()}`;
    badge.textContent = prediction.label;
    badge.style.background = '';
    badge.style.color = '';
    badge.style.border = '';

    if (conf) conf.textContent = `${prediction.confidence}%`;
}
