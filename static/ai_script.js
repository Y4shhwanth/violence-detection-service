// File upload handlers
document.getElementById('video-file').addEventListener('change', function(e) {
    const fileName = e.target.files[0]?.name;
    document.getElementById('video-name').textContent = fileName ? `✓ ${fileName}` : '';
});

document.getElementById('audio-file').addEventListener('change', function(e) {
    const fileName = e.target.files[0]?.name;
    document.getElementById('audio-name').textContent = fileName ? `✓ ${fileName}` : '';
});

// Mode tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');

        const mode = this.dataset.mode;
        toggleSections(mode);
    });
});

function toggleSections(mode) {
    const videoUpload = document.getElementById('video-upload');
    const audioUpload = document.getElementById('audio-upload');
    const textSection = document.getElementById('text-section');

    // Reset visibility
    videoUpload.style.display = 'block';
    audioUpload.style.display = 'block';
    textSection.style.display = 'block';

    switch(mode) {
        case 'video':
            audioUpload.style.display = 'none';
            textSection.style.display = 'none';
            break;
        case 'text':
            videoUpload.style.display = 'none';
            audioUpload.style.display = 'none';
            break;
        case 'batch':
            // Show batch upload UI (future enhancement)
            break;
    }
}

// Analyze content
async function analyzeContent() {
    const videoFile = document.getElementById('video-file').files[0];
    const textInput = document.getElementById('text-input').value;

    if (!videoFile && !textInput) {
        alert('Please upload a video or enter text to analyze');
        return;
    }

    // Show loading
    document.getElementById('loading-overlay').style.display = 'flex';
    document.getElementById('results-section').style.display = 'none';

    // Prepare form data
    const formData = new FormData();
    if (videoFile) {
        formData.append('video', videoFile);
    }
    if (textInput) {
        formData.append('text', textInput);
    }

    try {
        const response = await fetch('/predict', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        // Hide loading
        document.getElementById('loading-overlay').style.display = 'none';

        // Show results
        displayResults(data);

        // Update processed count
        const processedCount = document.getElementById('processed-count');
        const current = parseInt(processedCount.textContent.replace(',', ''));
        processedCount.textContent = (current + 1).toLocaleString();

    } catch (error) {
        console.error('Error:', error);
        document.getElementById('loading-overlay').style.display = 'none';
        alert('Analysis failed. Please try again.');
    }
}

function displayResults(data) {
    const resultsSection = document.getElementById('results-section');
    resultsSection.style.display = 'block';

    // Determine overall result
    const fusedPrediction = data.fused_prediction || {};
    const isViolent = fusedPrediction.class === 'Violence';
    const confidence = fusedPrediction.confidence || 0;

    const resultHTML = `
        <div class="result-card ${isViolent ? 'violent' : 'safe'}">
            <div class="result-header">
                <div class="result-icon">${isViolent ? '⚠️' : '✅'}</div>
                <div class="result-main">
                    <h2>${isViolent ? 'VIOLENCE DETECTED' : 'NO VIOLENCE DETECTED'}</h2>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${confidence}%"></div>
                    </div>
                    <p class="confidence-text">${confidence.toFixed(1)}% Confidence</p>
                </div>
            </div>

            ${data.video_prediction ? `
            <div class="analysis-item">
                <h3>📹 Video Analysis</h3>
                <div class="analysis-content">
                    <div class="status ${data.video_prediction.class === 'Violence' ? 'violent' : 'safe'}">
                        ${data.video_prediction.class}
                    </div>
                    <div class="confidence">${data.video_prediction.confidence?.toFixed(1) || 0}%</div>
                </div>
                <p class="reasoning">${data.video_prediction.reasoning || 'No details available'}</p>
            </div>
            ` : ''}

            ${data.audio_prediction ? `
            <div class="analysis-item">
                <h3>🎵 Audio Analysis</h3>
                <div class="analysis-content">
                    <div class="status ${data.audio_prediction.class === 'Violence' ? 'violent' : 'safe'}">
                        ${data.audio_prediction.class}
                    </div>
                    <div class="confidence">${data.audio_prediction.confidence?.toFixed(1) || 0}%</div>
                </div>
                <p class="reasoning">${data.audio_prediction.reasoning || 'No details available'}</p>
            </div>
            ` : ''}

            ${data.text_prediction ? `
            <div class="analysis-item">
                <h3>📝 Text Analysis</h3>
                <div class="analysis-content">
                    <div class="status ${data.text_prediction.class === 'Violence' ? 'violent' : 'safe'}">
                        ${data.text_prediction.class}
                    </div>
                    <div class="confidence">${data.text_prediction.confidence?.toFixed(1) || 0}%</div>
                </div>
                <p class="reasoning">${data.text_prediction.reasoning || 'No details available'}</p>
            </div>
            ` : ''}

            ${fusedPrediction.reasoning ? `
            <div class="fusion-details">
                <h3>🔗 Fusion Analysis</h3>
                <p>${fusedPrediction.reasoning}</p>
            </div>
            ` : ''}
        </div>
    `;

    resultsSection.innerHTML = resultHTML;

    // Add result card styles dynamically
    addResultStyles();
}

function addResultStyles() {
    if (document.getElementById('result-styles')) return;

    const style = document.createElement('style');
    style.id = 'result-styles';
    style.textContent = `
        .result-card {
            background: rgba(30, 41, 59, 0.8);
            border-radius: 20px;
            padding: 2rem;
            border: 2px solid rgba(74, 222, 208, 0.3);
            animation: slideUp 0.6s ease-out;
        }

        .result-card.violent {
            border-color: rgba(239, 68, 68, 0.5);
        }

        .result-header {
            display: flex;
            gap: 2rem;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid rgba(74, 222, 208, 0.2);
        }

        .result-icon {
            font-size: 4rem;
        }

        .result-main {
            flex: 1;
        }

        .result-main h2 {
            font-size: 2rem;
            margin-bottom: 1rem;
            color: #4aded0;
        }

        .result-card.violent h2 {
            color: #ef4444;
        }

        .confidence-bar {
            width: 100%;
            height: 8px;
            background: rgba(74, 222, 208, 0.2);
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 0.5rem;
        }

        .confidence-fill {
            height: 100%;
            background: linear-gradient(90deg, #4aded0, #38bdf8);
            border-radius: 4px;
            transition: width 1s ease-out;
        }

        .violent .confidence-fill {
            background: linear-gradient(90deg, #ef4444, #dc2626);
        }

        .confidence-text {
            color: #94a3b8;
            font-size: 1.1rem;
        }

        .analysis-item {
            margin: 1.5rem 0;
            padding: 1.5rem;
            background: rgba(15, 23, 42, 0.5);
            border-radius: 16px;
        }

        .analysis-item h3 {
            margin-bottom: 1rem;
            color: #e1e8ed;
        }

        .analysis-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .status {
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-weight: 600;
        }

        .status.safe {
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
        }

        .status.violent {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }

        .confidence {
            font-size: 1.2rem;
            font-weight: 700;
            color: #4aded0;
        }

        .reasoning {
            color: #94a3b8;
            line-height: 1.6;
        }

        .fusion-details {
            margin-top: 2rem;
            padding: 1.5rem;
            background: rgba(74, 222, 208, 0.1);
            border-radius: 16px;
            border: 1px solid rgba(74, 222, 208, 0.3);
        }

        .fusion-details h3 {
            color: #4aded0;
            margin-bottom: 1rem;
        }

        .fusion-details p {
            color: #e1e8ed;
            line-height: 1.6;
        }
    `;

    document.head.appendChild(style);
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('Violence Detection AI initialized');
});
