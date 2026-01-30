// Violence Detection System - Client-Side JavaScript
// Includes client-side caching for improved performance

// =============================================================================
// Cache Configuration
// =============================================================================
const CACHE_CONFIG = {
    enabled: true,
    ttlMs: 3600000, // 1 hour in milliseconds
    maxEntries: 50,
    storageKey: 'violence_detection_cache'
};

// =============================================================================
// Cache Implementation
// =============================================================================
class ResultCache {
    constructor(config = CACHE_CONFIG) {
        this.config = config;
        this.cache = this._loadFromStorage();
    }

    _loadFromStorage() {
        if (!this.config.enabled) return new Map();
        try {
            const stored = localStorage.getItem(this.config.storageKey);
            if (stored) {
                const data = JSON.parse(stored);
                return new Map(data.entries);
            }
        } catch (e) {
            console.warn('Failed to load cache from storage:', e);
        }
        return new Map();
    }

    _saveToStorage() {
        if (!this.config.enabled) return;
        try {
            const data = {
                entries: Array.from(this.cache.entries()),
                savedAt: Date.now()
            };
            localStorage.setItem(this.config.storageKey, JSON.stringify(data));
        } catch (e) {
            console.warn('Failed to save cache to storage:', e);
        }
    }

    async _hashContent(content) {
        // Use SHA-256 for content hashing
        const encoder = new TextEncoder();
        const data = encoder.encode(content);
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    _isExpired(entry) {
        return Date.now() - entry.timestamp > this.config.ttlMs;
    }

    _evictOldest() {
        if (this.cache.size < this.config.maxEntries) return;

        // Find and remove oldest entry
        let oldestKey = null;
        let oldestTime = Infinity;

        for (const [key, entry] of this.cache) {
            if (entry.timestamp < oldestTime) {
                oldestTime = entry.timestamp;
                oldestKey = key;
            }
        }

        if (oldestKey) {
            this.cache.delete(oldestKey);
        }
    }

    async get(type, content) {
        if (!this.config.enabled) return null;

        const hash = await this._hashContent(content);
        const key = `${type}:${hash}`;
        const entry = this.cache.get(key);

        if (!entry) return null;
        if (this._isExpired(entry)) {
            this.cache.delete(key);
            this._saveToStorage();
            return null;
        }

        console.log('Cache hit for', type);
        return entry.result;
    }

    async set(type, content, result) {
        if (!this.config.enabled) return;

        const hash = await this._hashContent(content);
        const key = `${type}:${hash}`;

        this._evictOldest();

        this.cache.set(key, {
            result,
            timestamp: Date.now()
        });

        this._saveToStorage();
    }

    clear() {
        this.cache.clear();
        localStorage.removeItem(this.config.storageKey);
    }

    stats() {
        return {
            size: this.cache.size,
            maxSize: this.config.maxEntries,
            enabled: this.config.enabled
        };
    }
}

// Global cache instance
const resultCache = new ResultCache();

// =============================================================================
// Tab Navigation
// =============================================================================
function switchTab(tab) {
    // Hide all tabs
    document.querySelectorAll('.tab-pane').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));

    // Show selected tab
    document.getElementById(`${tab}-tab`).classList.add('active');
    event.target.classList.add('active');

    // Clear results
    document.getElementById('results').classList.remove('show');
}

// =============================================================================
// File Input Handling
// =============================================================================
document.getElementById('video-input')?.addEventListener('change', function(e) {
    document.getElementById('video-name').textContent = e.target.files[0]?.name || 'No file chosen';
});

document.getElementById('video-input-multi')?.addEventListener('change', function(e) {
    document.getElementById('video-name-multi').textContent = e.target.files[0]?.name || 'No file chosen';
});

// =============================================================================
// Form Submissions
// =============================================================================

// Multimodal form submission
document.getElementById('multimodal-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    showLoading();

    try {
        const response = await fetch('/predict', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || 'Request failed');
        }

        displayResults(data);
    } catch (error) {
        displayError('Error: ' + error.message);
    } finally {
        hideLoading();
    }
});

// Video form submission
document.getElementById('video-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    showLoading();

    try {
        const response = await fetch('/predict_video', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || 'Request failed');
        }

        displayVideoResults(data);
    } catch (error) {
        displayError('Error: ' + error.message);
    } finally {
        hideLoading();
    }
});

// Text form submission with caching
document.getElementById('text-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const text = document.getElementById('text-input').value.trim();
    if (!text) {
        displayError('Please enter some text to analyze');
        return;
    }

    showLoading();

    try {
        // Check cache first
        const cachedResult = await resultCache.get('text', text);
        if (cachedResult) {
            displayTextResults(cachedResult);
            hideLoading();
            return;
        }

        const response = await fetch('/predict_text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || 'Request failed');
        }

        // Cache successful result
        if (data.success) {
            await resultCache.set('text', text, data);
        }

        displayTextResults(data);
    } catch (error) {
        displayError('Error: ' + error.message);
    } finally {
        hideLoading();
    }
});

// =============================================================================
// Loading State
// =============================================================================
function showLoading() {
    document.getElementById('loading').classList.add('show');
    document.getElementById('results').classList.remove('show');
}

function hideLoading() {
    document.getElementById('loading').classList.remove('show');
}

// =============================================================================
// Result Display
// =============================================================================
function displayResults(data) {
    const resultsDiv = document.getElementById('results');

    if (!data.success) {
        displayError(data.message);
        return;
    }

    let html = '<h2 class="results-title"><span>Analysis Results</span></h2>';

    if (data.fused_prediction) {
        html += createResultCard('Fused Multimodal Prediction', data.fused_prediction);
    }

    if (data.video_prediction) {
        html += createResultCard('Video Analysis', data.video_prediction);
    }

    if (data.audio_prediction && data.audio_prediction.class !== 'Error') {
        html += createResultCard('Audio Analysis', data.audio_prediction);
    }

    if (data.text_prediction) {
        html += createResultCard('Text Analysis', data.text_prediction);
    }

    resultsDiv.innerHTML = html;
    resultsDiv.classList.add('show');
}

function displayVideoResults(data) {
    const resultsDiv = document.getElementById('results');

    if (!data.success) {
        displayError(data.message);
        return;
    }

    const html = '<h2 class="results-title"><span>Video Analysis Results</span></h2>' +
                createResultCard('Video Detection', data);

    resultsDiv.innerHTML = html;
    resultsDiv.classList.add('show');
}

function displayTextResults(data) {
    const resultsDiv = document.getElementById('results');

    if (!data.success) {
        displayError(data.message);
        return;
    }

    const html = '<h2 class="results-title"><span>Text Analysis Results</span></h2>' +
                createResultCard('Text Detection', data);

    resultsDiv.innerHTML = html;
    resultsDiv.classList.add('show');
}

function createResultCard(title, prediction) {
    if (!prediction) return '';

    const isViolence = prediction.class === 'Violence';
    const classColor = isViolence ? 'violence' : 'non-violence';
    const confidence = Math.round(prediction.confidence || 0);

    let html = `
        <div class="result-card">
            <h3>${escapeHtml(title)}</h3>
            <div class="prediction-header">
                <span class="prediction-class ${classColor}">${escapeHtml(prediction.class)}</span>
                <span class="confidence">${confidence}% Confidence</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${confidence}%"></div>
            </div>
    `;

    // Add reasoning
    if (prediction.reasoning) {
        html += `
            <div class="reasoning-box">
                <h4>Detailed Reasoning</h4>
                <p class="reasoning-text">${escapeHtml(prediction.reasoning)}</p>
            </div>
        `;
    }

    // Add keywords (for text analysis)
    if (prediction.keywords_found && prediction.keywords_found.length > 0) {
        html += `
            <div class="keywords-box">
                <h4>Keywords Detected</h4>
                <div class="keywords-list">
                    ${prediction.keywords_found.map(kw => `
                        <span class="keyword-badge">${escapeHtml(kw)}</span>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Add ML score (for text analysis)
    if (prediction.ml_score !== undefined) {
        html += `
            <div style="margin-top: 20px; color: #6c757d;">
                <strong>ML Model Score:</strong> ${prediction.ml_score.toFixed(1)}%
            </div>
        `;
    }

    // Add detected sounds (for audio analysis)
    if (prediction.detected_sounds && prediction.detected_sounds.length > 0) {
        html += `
            <div class="keywords-box">
                <h4>Detected Sounds</h4>
                <div class="keywords-list">
                    ${prediction.detected_sounds.map(sound => `
                        <span class="keyword-badge">${escapeHtml(sound)}</span>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Add violence score (for audio analysis)
    if (prediction.violence_score !== undefined) {
        html += `
            <div style="margin-top: 20px; color: #6c757d;">
                <strong>Audio Violence Score:</strong> ${prediction.violence_score.toFixed(1)}
            </div>
        `;
    }

    // Add violent frames (for video analysis)
    if (prediction.violent_frames && prediction.violent_frames.length > 0) {
        html += `
            <div class="frames-box">
                <h4>Top Violent Frames</h4>
        `;

        prediction.violent_frames.forEach((frame, idx) => {
            html += `
                <div class="frame-item">
                    <div class="frame-header">
                        <span class="frame-title">[${escapeHtml(frame.timestamp)}] Frame #${frame.frame_number}</span>
                        <span class="frame-score">Score: ${frame.score}</span>
                    </div>
                    <p class="frame-reasoning">${escapeHtml(frame.reasoning)}</p>
                    <div class="frame-indicators">
                        ${frame.indicators.map(ind => `
                            <span class="indicator-badge">${escapeHtml(ind)}</span>
                        `).join('')}
                    </div>
                </div>
            `;
        });

        html += `</div>`;
    }

    // Add statistics (for video analysis)
    if (prediction.avg_score !== undefined) {
        html += `
            <div class="stats-box">
                <h4>Video Statistics</h4>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">Average Score</div>
                        <div class="stat-value">${prediction.avg_score.toFixed(1)}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Maximum Score</div>
                        <div class="stat-value">${prediction.max_score.toFixed(1)}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Frames Analyzed</div>
                        <div class="stat-value">${prediction.total_frames_analyzed || 15}</div>
                    </div>
                </div>
            </div>
        `;
    }

    html += `</div>`;
    return html;
}

function displayError(message) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = `
        <div class="result-card" style="border-color: #dc3545; background: #f8d7da;">
            <h3 style="color: #dc3545;">Error</h3>
            <p style="color: #721c24; font-size: 1.1rem;">${escapeHtml(message)}</p>
        </div>
    `;
    resultsDiv.classList.add('show');
}

// =============================================================================
// Security: HTML Escaping (XSS Prevention)
// =============================================================================
function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') {
        return String(unsafe);
    }
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// =============================================================================
// Cache Management (for debugging/admin)
// =============================================================================
window.cacheStats = function() {
    console.table(resultCache.stats());
};

window.clearCache = function() {
    resultCache.clear();
    console.log('Cache cleared');
};
