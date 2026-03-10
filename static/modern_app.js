// Modern Violence Detection UI - JavaScript
// Part 1: Core Functionality

// ============================================================================
// Tab Management
// ============================================================================
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const targetTab = tab.dataset.tab;

        // Update tabs
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        tab.classList.add('active');
        document.getElementById(`${targetTab}-content`).classList.add('active');

        // Clear results
        document.getElementById('results-container').innerHTML = '';
    });
});

// ============================================================================
// Drag & Drop File Upload
// ============================================================================
function setupDropZone(zoneId, inputId, fileInfoId) {
    const dropZone = document.getElementById(zoneId);
    const fileInput = document.getElementById(inputId);
    const fileInfo = document.getElementById(fileInfoId);

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            displayFileInfo(files[0], fileInfo);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            displayFileInfo(e.target.files[0], fileInfo);
        }
    });
}

function displayFileInfo(file, infoElement) {
    const size = (file.size / (1024 * 1024)).toFixed(2);
    infoElement.innerHTML = `
        <strong>${file.name}</strong><br>
        <small>${size} MB</small>
    `;
    infoElement.classList.add('show');
}

// Setup all drop zones
setupDropZone('video-drop-zone', 'video-input', 'video-file-info');
setupDropZone('video-only-drop-zone', 'video-only-input', 'video-only-file-info');

// ============================================================================
// Form Submissions
// ============================================================================

// Multimodal Form
document.getElementById('multimodal-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);

    showLoading('Analyzing multi-modal content...');

    try {
        const response = await fetch('/predict', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        hideLoading();

        if (data.success) {
            displayExplainableResults(data);
        } else {
            showError(data.message);
        }
    } catch (error) {
        hideLoading();
        showError('Analysis failed: ' + error.message);
    }
});

// Video Form
document.getElementById('video-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);

    showLoading('Analyzing video with temporal consistency...');

    try {
        const response = await fetch('/predict_video', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        hideLoading();

        if (data.success) {
            displayVideoResults(data);
        } else {
            showError(data.message);
        }
    } catch (error) {
        hideLoading();
        showError('Analysis failed: ' + error.message);
    }
});

// Text Form
document.getElementById('text-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = document.getElementById('text-input').value;

    showLoading('Analyzing text with intent classification...');

    try {
        const response = await fetch('/predict_text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        const data = await response.json();
        hideLoading();

        if (data.success) {
            displayTextResults(data);
        } else {
            showError(data.message);
        }
    } catch (error) {
        hideLoading();
        showError('Analysis failed: ' + error.message);
    }
});

// ============================================================================
// Loading State
// ============================================================================
function showLoading(message = 'Analyzing...') {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('loading-status').textContent = message;
    document.getElementById('results-container').innerHTML = '';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showError(message) {
    document.getElementById('results-container').innerHTML = `
        <div class="glass-card" style="border-color: var(--danger);">
            <h2 style="color: var(--danger); margin-bottom: 1rem;">⚠️ Error</h2>
            <p style="font-size: 1.1rem;">${escapeHtml(message)}</p>
        </div>
    `;
}

// ============================================================================
// Security
// ============================================================================
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// Background Particles Animation
// ============================================================================
function initParticles() {
    const container = document.getElementById('particles');
    const particleCount = 50;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.style.position = 'absolute';
        particle.style.width = Math.random() * 3 + 1 + 'px';
        particle.style.height = particle.style.width;
        particle.style.background = 'rgba(255, 255, 255, 0.3)';
        particle.style.borderRadius = '50%';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animation = `float ${Math.random() * 10 + 10}s ease-in-out infinite`;
        particle.style.animationDelay = Math.random() * 5 + 's';
        container.appendChild(particle);
    }
}

// CSS for particle animation
const style = document.createElement('style');
style.textContent = `
    @keyframes float {
        0%, 100% { transform: translateY(0) translateX(0); opacity: 0; }
        10% { opacity: 0.3; }
        90% { opacity: 0.3; }
        50% { transform: translateY(-100px) translateX(50px); }
    }
`;
document.head.appendChild(style);

initParticles();
