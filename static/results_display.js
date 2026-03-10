// Results Display with Explainable AI Visualization
// Part 2: Results Rendering

// ============================================================================
// Main Results Display (Multimodal with Explainable Output)
// ============================================================================
function displayExplainableResults(data) {
    const container = document.getElementById('results-container');

    // Check if we have explainable output
    const explainable = data.explainable_output || {};
    const fused = data.fused_prediction || {};

    let html = '';

    // Main Result Card
    html += createMainResultCard(explainable, fused);

    // Timeline if available
    if (explainable.timeline && explainable.timeline.length > 0) {
        html += createTimelineCard(explainable.timeline);
    }

    // Top Factors
    if (explainable.top_factors && explainable.top_factors.length > 0) {
        html += createTopFactorsCard(explainable.top_factors);
    }

    // Confidence Breakdown
    if (explainable.confidence_breakdown) {
        html += createConfidenceBreakdownCard(explainable.confidence_breakdown);
    }

    // Evidence Details
    if (explainable.evidence) {
        html += createEvidenceCard(explainable.evidence);
    }

    // Individual Modalities
    html += '<div class="modalities-grid">';
    if (data.video_prediction) {
        html += createModalityCard('Video', data.video_prediction, '🎬');
    }
    if (data.audio_prediction && data.audio_prediction.class !== 'Error') {
        html += createModalityCard('Audio', data.audio_prediction, '🔊');
    }
    if (data.text_prediction) {
        html += createModalityCard('Text', data.text_prediction, '📝');
    }
    html += '</div>';

    container.innerHTML = html;
}

// ============================================================================
// Main Result Card
// ============================================================================
function createMainResultCard(explainable, fused) {
    const isViolent = explainable.violence_detected || fused.class === 'Violence';
    const probability = (explainable.violence_probability || fused.confidence / 100 || 0) * 100;
    const status = isViolent ? 'VIOLENCE DETECTED' : 'NO VIOLENCE';
    const color = isViolent ? 'var(--danger)' : 'var(--success)';
    const icon = isViolent ? '⚠️' : '✅';

    return `
        <div class="glass-card result-main" style="border: 2px solid ${color};">
            <div class="result-header">
                <div class="result-icon">${icon}</div>
                <div>
                    <h2 style="color: ${color}; font-size: 2rem; margin-bottom: 0.5rem;">${status}</h2>
                    <p style="font-size: 1.2rem; opacity: 0.8;">Confidence: ${probability.toFixed(1)}%</p>
                </div>
            </div>

            <div class="probability-bar">
                <div class="probability-fill" style="width: ${probability}%; background: ${color};"></div>
            </div>

            ${explainable.reasoning ? `
                <div class="reasoning-section">
                    <h3>🧠 AI Reasoning</h3>
                    <p>${escapeHtml(explainable.reasoning)}</p>
                </div>
            ` : ''}

            <div class="result-meta">
                <span>Fusion Method: ${explainable.fusion_method || 'learned_model'}</span>
                <span>Modalities: ${explainable.modality_contributions ? Object.keys(explainable.modality_contributions).length : 3}</span>
            </div>
        </div>
    `;
}

// ============================================================================
// Timeline Visualization
// ============================================================================
function createTimelineCard(timeline) {
    return `
        <div class="glass-card">
            <h3 style="margin-bottom: 1.5rem;">⏱️ Event Timeline</h3>
            <div class="timeline">
                ${timeline.map((event, idx) => `
                    <div class="timeline-item ${event.severity || 'medium'}">
                        <div class="timeline-marker"></div>
                        <div class="timeline-content">
                            <div class="timeline-time">${event.timestamp || event.seconds.toFixed(1) + 's'}</div>
                            <div class="timeline-events">
                                ${event.events.map(e => `<span class="event-badge">${escapeHtml(e)}</span>`).join('')}
                            </div>
                            <div class="timeline-modality">${event.modality}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// ============================================================================
// Top Contributing Factors
// ============================================================================
function createTopFactorsCard(factors) {
    return `
        <div class="glass-card">
            <h3 style="margin-bottom: 1.5rem;">🎯 Top Contributing Factors</h3>
            <div class="factors-grid">
                ${factors.slice(0, 6).map((factor, idx) => `
                    <div class="factor-item" style="animation-delay: ${idx * 0.1}s">
                        <div class="factor-rank">#${idx + 1}</div>
                        <div class="factor-text">${escapeHtml(factor)}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// ============================================================================
// Confidence Breakdown
// ============================================================================
function createConfidenceBreakdownCard(breakdown) {
    const components = breakdown.components || {};

    return `
        <div class="glass-card">
            <h3 style="margin-bottom: 1.5rem;">📊 Confidence Breakdown</h3>
            <div class="confidence-bars">
                ${Object.entries(components).map(([modality, data]) => `
                    <div class="confidence-item">
                        <div class="confidence-label">
                            <span>${modality.toUpperCase()}</span>
                            <span>${data.confidence.toFixed(1)}%</span>
                        </div>
                        <div class="confidence-bar-bg">
                            <div class="confidence-bar-fg" style="width: ${data.confidence}%;"></div>
                        </div>
                        ${data.method ? `<small>Method: ${data.method}</small>` : ''}
                    </div>
                `).join('')}
            </div>

            ${breakdown.fusion_factors ? `
                <div class="fusion-factors" style="margin-top: 1.5rem;">
                    <h4>Fusion Factors</h4>
                    <div class="fusion-grid">
                        <div class="fusion-item">
                            <span>Temporal Consistency</span>
                            <strong>${(breakdown.fusion_factors.temporal_consistency * 100).toFixed(1)}%</strong>
                        </div>
                        <div class="fusion-item">
                            <span>Cross-Modal Agreement</span>
                            <strong>${(breakdown.fusion_factors.cross_modal_agreement * 100).toFixed(1)}%</strong>
                        </div>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

// ============================================================================
// Evidence Details
// ============================================================================
function createEvidenceCard(evidence) {
    let html = '<div class="glass-card"><h3 style="margin-bottom: 1.5rem;">🔍 Evidence Details</h3>';

    if (evidence.video) {
        html += `
            <div class="evidence-section">
                <h4>📹 Video Evidence</h4>
                <div class="evidence-stats">
                    <span>Violent Segments: ${evidence.video.violent_segments}</span>
                    <span>Max Score: ${evidence.video.max_violence_score.toFixed(1)}</span>
                    <span>Method: ${evidence.video.analysis_method}</span>
                </div>
            </div>
        `;
    }

    if (evidence.audio) {
        html += `
            <div class="evidence-section">
                <h4>🔊 Audio Evidence</h4>
                <div class="tags-container">
                    ${evidence.audio.detected_sounds.map(s =>
                        `<span class="evidence-tag">${escapeHtml(s)}</span>`
                    ).join('')}
                </div>
            </div>
        `;
    }

    if (evidence.text) {
        html += `
            <div class="evidence-section">
                <h4>📝 Text Evidence</h4>
                <div class="tags-container">
                    ${evidence.text.keywords_found.map(k =>
                        `<span class="evidence-tag">${escapeHtml(k)}</span>`
                    ).join('')}
                </div>
                ${evidence.text.context ? `
                    <div class="context-info">
                        ${evidence.text.context.is_joke ? '<span class="context-badge joke">Joking Context</span>' : ''}
                        ${evidence.text.context.is_gaming ? '<span class="context-badge gaming">Gaming Context</span>' : ''}
                        ${evidence.text.context.is_real_threat ? '<span class="context-badge threat">Real Threat</span>' : ''}
                    </div>
                ` : ''}
            </div>
        `;
    }

    html += '</div>';
    return html;
}

// ============================================================================
// Individual Modality Cards
// ============================================================================
function createModalityCard(name, data, icon) {
    const isViolent = data.class === 'Violence';
    const color = isViolent ? 'var(--danger)' : 'var(--success)';

    return `
        <div class="glass-card modality-card">
            <div class="modality-header">
                <span class="modality-icon">${icon}</span>
                <h3>${name}</h3>
            </div>
            <div class="modality-result" style="color: ${color};">
                <span class="modality-class">${data.class}</span>
                <span class="modality-confidence">${data.confidence.toFixed(1)}%</span>
            </div>
            ${data.reasoning ? `
                <p class="modality-reasoning">${escapeHtml(data.reasoning.substring(0, 150))}...</p>
            ` : ''}
        </div>
    `;
}

// ============================================================================
// Video-Only Results
// ============================================================================
function displayVideoResults(data) {
    const container = document.getElementById('results-container');
    container.innerHTML = createMainResultCard({}, data) +
                         (data.violent_frames ? createVideoFramesCard(data.violent_frames) : '');
}

function createVideoFramesCard(frames) {
    return `
        <div class="glass-card">
            <h3 style="margin-bottom: 1.5rem;">🎬 Violent Frames Detected</h3>
            <div class="frames-grid">
                ${frames.map(frame => `
                    <div class="frame-card">
                        <div class="frame-header">
                            <span>[${frame.timestamp}] Frame #${frame.frame_number}</span>
                            <span class="frame-score">Score: ${frame.score}</span>
                        </div>
                        <p class="frame-reasoning">${escapeHtml(frame.reasoning)}</p>
                        <div class="frame-indicators">
                            ${frame.indicators.map(i => `<span class="indicator-tag">${escapeHtml(i)}</span>`).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// ============================================================================
// Text-Only Results
// ============================================================================
function displayTextResults(data) {
    const container = document.getElementById('results-container');
    container.innerHTML = createMainResultCard({}, data);
}
