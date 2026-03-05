// ============================================
// AI DPR Analysis System - Frontend JavaScript
// ============================================

const API_BASE = '';
let currentFilePath = null;
let currentDocumentId = null;
let currentState = null;
let currentProjectType = null;
let currentProjectCost = null;
let analysisData = null;
let qualityData = null;
let riskData = null;

// ---- Utility: build query string, skipping empty values ----
function buildQuery(params) {
    const qs = Object.entries(params)
        .filter(([, v]) => v !== null && v !== undefined && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');
    return qs ? `?${qs}` : '';
}

// ---- Tab Navigation ----
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
}

// ---- File Upload ----
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const uploadForm = document.getElementById('upload-form');

uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', e => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-over'));
uploadArea.addEventListener('drop', e => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        showFileInfo(e.dataTransfer.files[0]);
    }
});
fileInput.addEventListener('change', () => {
    if (fileInput.files.length) showFileInfo(fileInput.files[0]);
});

function showFileInfo(file) {
    document.getElementById('file-info').classList.remove('hidden');
    document.getElementById('file-name').textContent = file.name;
    document.getElementById('file-size').textContent = `(${(file.size / 1024 / 1024).toFixed(2)} MB)`;
    uploadArea.style.display = 'none';
}

function clearFile() {
    fileInput.value = '';
    document.getElementById('file-info').classList.add('hidden');
    uploadArea.style.display = 'block';
}

// ---- Form Submit ----
uploadForm.addEventListener('submit', async e => {
    e.preventDefault();
    if (!fileInput.files.length) {
        alert('Please select a DPR file to upload');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('state', document.getElementById('state-select').value);
    formData.append('project_type', document.getElementById('project-type').value);
    formData.append('project_name', document.getElementById('project-name').value);
    formData.append('project_cost_crores', document.getElementById('project-cost').value || 0);

    currentState = document.getElementById('state-select').value;
    currentProjectType = document.getElementById('project-type').value;
    currentProjectCost = parseFloat(document.getElementById('project-cost').value) || null;

    const progressDiv = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const uploadBtn = document.getElementById('upload-btn');

    progressDiv.classList.remove('hidden');
    uploadBtn.disabled = true;

    try {
        // Step 1: Upload
        progressFill.style.width = '20%';
        progressText.textContent = '📤 Uploading DPR...';

        const uploadResp = await fetch(`${API_BASE}/api/upload/dpr`, {
            method: 'POST', body: formData
        });
        const uploadResult = await uploadResp.json();

        if (!uploadResp.ok) throw new Error(uploadResult.detail || 'Upload failed');

        currentFilePath = uploadResult.file_path;
        currentDocumentId = uploadResult.document_id;

        // Step 2: NLP Analysis
        progressFill.style.width = '40%';
        progressText.textContent = '🧠 Running NLP Analysis...';

        try {
            const analysisResp = await fetch(
                `${API_BASE}/api/analysis/analyze${buildQuery({
                    file_path: currentFilePath,
                    document_id: currentDocumentId,
                    state: currentState
                })}`,
                { method: 'POST' }
            );
            analysisData = await analysisResp.json();
            if (analysisResp.ok) {
                renderAnalysis(analysisData);
            } else {
                console.warn('Analysis returned error:', analysisData);
            }
        } catch (analysisErr) {
            console.warn('Analysis step failed:', analysisErr);
        }

        // Step 3: Quality Scoring
        progressFill.style.width = '65%';
        progressText.textContent = '⭐ Calculating Quality Score...';

        try {
            const qualityResp = await fetch(
                `${API_BASE}/api/scoring/quality-score${buildQuery({
                    file_path: currentFilePath,
                    document_id: currentDocumentId,
                    state: currentState,
                    project_type: currentProjectType
                })}`,
                { method: 'POST' }
            );
            qualityData = await qualityResp.json();
            if (qualityResp.ok) {
                renderQualityScore(qualityData);
            } else {
                console.warn('Quality scoring returned error:', qualityData);
            }
        } catch (qualityErr) {
            console.warn('Quality scoring step failed:', qualityErr);
        }

        // Step 4: Risk Prediction
        progressFill.style.width = '85%';
        progressText.textContent = '🎯 Predicting Risks...';

        try {
            const riskResp = await fetch(
                `${API_BASE}/api/risk/predict${buildQuery({
                    file_path: currentFilePath,
                    document_id: currentDocumentId,
                    state: currentState,
                    project_type: currentProjectType,
                    project_cost_crores: currentProjectCost
                })}`,
                { method: 'POST' }
            );
            riskData = await riskResp.json();
            if (riskResp.ok) {
                renderRiskPrediction(riskData);
            } else {
                console.warn('Risk prediction returned error:', riskData);
            }
        } catch (riskErr) {
            console.warn('Risk prediction step failed:', riskErr);
        }

        // Done
        progressFill.style.width = '100%';
        progressText.textContent = '✅ Analysis Complete! Navigate tabs to view results.';

        setTimeout(() => switchTab('analysis'), 1500);

    } catch (err) {
        progressText.textContent = `❌ Error: ${err.message}`;
        progressFill.style.background = 'var(--danger)';
        console.error(err);
    } finally {
        uploadBtn.disabled = false;
    }
});

// ---- Render Analysis Results ----
function renderAnalysis(data) {
    document.getElementById('analysis-placeholder').classList.add('hidden');
    document.getElementById('analysis-results').classList.remove('hidden');

    const nlp = data.nlp_analysis || {};
    const summary = nlp.summary || {};
    const stats = nlp.text_statistics || {};

    document.getElementById('stat-pages').textContent = data.total_pages || 0;
    document.getElementById('stat-words').textContent = (stats.total_words || 0).toLocaleString();
    document.getElementById('stat-sections').textContent = `${summary.sections_found || 0}/${summary.sections_total || 14}`;
    document.getElementById('stat-financial').textContent = summary.total_financial_figures || 0;

    // Sections
    const sections = nlp.sections || {};
    const sectionsList = document.getElementById('sections-list');
    sectionsList.innerHTML = '';

    const sectionNames = {
        executive_summary: 'Executive Summary', project_background: 'Project Background',
        objectives: 'Objectives', scope_of_work: 'Scope of Work',
        technical_feasibility: 'Technical Feasibility', financial_analysis: 'Financial Analysis',
        cost_estimates: 'Cost Estimates', implementation_schedule: 'Implementation Schedule',
        institutional_framework: 'Institutional Framework', environmental_impact: 'Environmental Impact',
        risk_assessment: 'Risk Assessment', monitoring_evaluation: 'Monitoring & Evaluation',
        sustainability: 'Sustainability', annexures: 'Annexures'
    };

    for (const [key, name] of Object.entries(sectionNames)) {
        const sec = sections[key] || {};
        sectionsList.innerHTML += `
            <div class="section-item">
                <div class="section-status">
                    <i class="fas ${sec.found ? 'fa-check-circle found' : 'fa-times-circle missing'}"></i>
                    <span>${name}</span>
                </div>
                <span class="section-words">${sec.found ? sec.word_count + ' words' : 'Missing'}</span>
            </div>`;
    }

    // Entities
    const entities = nlp.entities || {};
    const entitiesList = document.getElementById('entities-list');
    entitiesList.innerHTML = '';

    const entityTypes = [
        { key: 'organizations', label: 'Organizations', cls: 'org' },
        { key: 'locations', label: 'Locations', cls: 'loc' },
        { key: 'monetary_values', label: 'Financial', cls: 'money' },
        { key: 'dates', label: 'Dates', cls: '' }
    ];

    for (const type of entityTypes) {
        const items = entities[type.key] || [];
        if (items.length) {
            entitiesList.innerHTML += `<h4 style="margin: 10px 0 5px;">${type.label} (${items.length})</h4>
                <div class="entity-tags">
                    ${items.slice(0, 15).map(e => `<span class="entity-tag ${type.cls}">${e.text}</span>`).join('')}
                    ${items.length > 15 ? `<span class="entity-tag">+${items.length - 15} more</span>` : ''}
                </div>`;
        }
    }
}

// ---- Render Quality Score ----
function renderQualityScore(data) {
    document.getElementById('quality-placeholder').classList.add('hidden');
    document.getElementById('quality-results').classList.remove('hidden');

    const report = data.quality_report || {};
    const score = report.composite_score || 0;
    const grade = report.grade || '-';
    const scores = report.scores || {};

    // Grade circle
    const circle = document.getElementById('grade-circle');
    document.getElementById('grade-letter').textContent = grade;
    document.getElementById('grade-score').textContent = score.toFixed(1);
    document.getElementById('grade-description').textContent = report.grade_description || '';

    const color = score >= 80 ? 'var(--success)' : score >= 60 ? 'var(--accent)' :
                  score >= 40 ? 'var(--warning)' : 'var(--danger)';
    circle.style.borderColor = color;
    circle.style.color = color;

    // Score bars
    const barsContainer = document.getElementById('score-bars');
    barsContainer.innerHTML = '';

    const scoreItems = [
        { name: 'Section Completeness', key: 'section_completeness', color: '#3b82f6' },
        { name: 'Technical Depth', key: 'technical_depth', color: '#8b5cf6' },
        { name: 'Financial Accuracy', key: 'financial_accuracy', color: '#f59e0b' },
        { name: 'Compliance', key: 'compliance', color: '#10b981' },
        { name: 'Risk Assessment Quality', key: 'risk_assessment_quality', color: '#ef4444' }
    ];

    for (const item of scoreItems) {
        const s = scores[item.key] || {};
        const val = s.score || 0;
        barsContainer.innerHTML += `
            <div class="score-bar-item">
                <div class="score-bar-header">
                    <span>${item.name} (${(s.weight * 100).toFixed(0)}%)</span>
                    <span>${val.toFixed(1)}/100</span>
                </div>
                <div class="score-bar-track">
                    <div class="score-bar-fill" style="width: ${val}%; background: ${item.color};"></div>
                </div>
            </div>`;
    }

    // Quality chart
    renderQualityChart(scoreItems, scores);

    // Recommendations
    const recsContainer = document.getElementById('quality-recommendations');
    const recs = report.recommendations || [];
    recsContainer.innerHTML = recs.map(r => {
        const cls = r.includes('❌') || r.includes('MISSING') ? 'critical' :
                    r.includes('⚠️') ? 'warning' : '';
        return `<div class="rec-item ${cls}">${r}</div>`;
    }).join('');
}

function renderQualityChart(items, scores) {
    const ctx = document.getElementById('quality-chart');
    if (!ctx) return;

    if (window.qualityChart) window.qualityChart.destroy();

    window.qualityChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: items.map(i => i.name),
            datasets: [{
                label: 'Score',
                data: items.map(i => (scores[i.key] || {}).score || 0),
                backgroundColor: 'rgba(59,130,246,0.2)',
                borderColor: '#3b82f6',
                borderWidth: 2,
                pointBackgroundColor: '#3b82f6'
            }]
        },
        options: {
            scales: {
                r: {
                    beginAtZero: true, max: 100,
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { display: false },
                    pointLabels: { color: '#94a3b8', font: { size: 11 } }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
}

// ---- Render Risk Prediction ----
function renderRiskPrediction(data) {
    document.getElementById('risk-placeholder').classList.add('hidden');
    document.getElementById('risk-results').classList.remove('hidden');

    const report = data.risk_report || {};
    const summary = report.risk_summary || {};

    // Risk level
    const level = (summary.overall_risk_level || 'Unknown').toLowerCase();
    const badge = document.getElementById('risk-level-badge');
    badge.textContent = summary.overall_risk_level || 'Unknown';
    badge.className = `risk-badge ${level}`;

    // Cost risk
    const costPct = summary.cost_overrun_probability || 0;
    document.getElementById('cost-risk-pct').textContent = `${costPct.toFixed(1)}%`;
    const costBar = document.getElementById('cost-risk-bar');
    costBar.style.width = `${costPct}%`;
    costBar.style.background = costPct > 70 ? 'var(--danger)' :
                                costPct > 50 ? 'var(--warning)' :
                                costPct > 30 ? 'var(--accent)' : 'var(--success)';

    // Delay risk
    const delayPct = summary.delay_probability || 0;
    document.getElementById('delay-risk-pct').textContent = `${delayPct.toFixed(1)}%`;
    const delayBar = document.getElementById('delay-risk-bar');
    delayBar.style.width = `${delayPct}%`;
    delayBar.style.background = delayPct > 70 ? 'var(--danger)' :
                                 delayPct > 50 ? 'var(--warning)' :
                                 delayPct > 30 ? 'var(--accent)' : 'var(--success)';

    // Monte Carlo
    const mc = report.monte_carlo_simulation || {};
    if (mc.simulated) {
        const mcStats = document.getElementById('monte-carlo-stats');
        const costSim = mc.cost_simulation || {};
        const delaySim = mc.delay_simulation || {};
        mcStats.innerHTML = `
            <div class="stats-grid" style="margin-top: 15px;">
                <div class="stat-card">
                    <div class="stat-label">Base Cost (₹ Cr)</div>
                    <div class="stat-value">${costSim.base_cost_crores || '-'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Expected Cost (P50)</div>
                    <div class="stat-value">${costSim.p50_cost || '-'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Worst Case (P90)</div>
                    <div class="stat-value text-danger">${costSim.p90_cost || '-'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Expected Delay (months)</div>
                    <div class="stat-value text-warning">${delaySim.p50_delay_months || '-'}</div>
                </div>
            </div>`;

        renderMonteCarloChart(costSim);
    }

    // Explainability
    const explain = report.explainability || {};
    const explainDiv = document.getElementById('explainability-content');
    explainDiv.innerHTML = '';

    if (explain.narrative) {
        explainDiv.innerHTML += `<div style="white-space:pre-line; line-height:1.8; margin-bottom:20px;">${explain.narrative}</div>`;
    }

    // Risk drivers
    const drivers = explain.top_risk_drivers || [];
    if (drivers.length) {
        explainDiv.innerHTML += '<h4 style="margin:15px 0 10px;">🔴 Top Risk Drivers</h4>';
        drivers.forEach(d => {
            explainDiv.innerHTML += `
                <div class="rec-item critical">
                    <strong>${d.factor}</strong> — Severity: ${d.severity}
                </div>`;
        });
    }

    // Protective factors
    const protective = explain.top_protective_factors || [];
    if (protective.length) {
        explainDiv.innerHTML += '<h4 style="margin:15px 0 10px;">🟢 Protective Factors</h4>';
        protective.forEach(p => {
            explainDiv.innerHTML += `
                <div class="rec-item" style="border-left-color: var(--success);">
                    ✅ ${p.factor}
                </div>`;
        });
    }

    // Mitigation
    const mitigations = report.mitigation_strategies || [];
    const mitigationDiv = document.getElementById('mitigation-content');
    mitigationDiv.innerHTML = mitigations.map(m => `
        <div class="mitigation-item">
            <h4>⚠️ ${m.risk}</h4>
            <p><strong>Recommendation:</strong> ${m.recommendation}</p>
            <p class="impact">📈 Expected Impact: ${m.impact}</p>
        </div>
    `).join('');
}

function renderMonteCarloChart(costSim) {
    const ctx = document.getElementById('monte-carlo-chart');
    if (!ctx) return;

    if (window.mcChart) window.mcChart.destroy();

    const labels = ['P10', 'P50', 'P75', 'P90', 'Max'];
    const values = [costSim.p10_cost, costSim.p50_cost, costSim.p75_cost, costSim.p90_cost, costSim.max_cost];
    const colors = ['#10b981', '#3b82f6', '#f59e0b', '#ea580c', '#dc2626'];

    window.mcChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Projected Cost (₹ Crores)',
                data: values,
                backgroundColor: colors.map(c => c + '80'),
                borderColor: colors,
                borderWidth: 2,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                x: { ticks: { color: '#94a3b8' } }
            },
            plugins: {
                legend: { display: false },
                title: { display: true, text: 'Cost Distribution (Monte Carlo)', color: '#94a3b8' }
            }
        }
    });
}

// ---- Initialize Dashboard Tab ----
function initDashboard() {
    const mdoNERStates = ['Arunachal Pradesh', 'Assam', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Sikkim', 'Tripura'];
    const mdoTags = document.getElementById('mdoner-tags');
    if (mdoTags) {
        mdoTags.innerHTML = mdoNERStates.map(s => `<span class="state-tag">🏔️ ${s}</span>`).join('');
    }

    const gradeTable = document.getElementById('grade-table');
    if (gradeTable) {
        const grades = [
            ['A+', '90-100', '🟢 Excellent'], ['A', '80-89', '🟢 Very Good'],
            ['B+', '70-79', '🔵 Good'], ['B', '60-69', '🔵 Satisfactory'],
            ['C', '50-59', '🟡 Below Average'], ['D', '40-49', '🟠 Poor'],
            ['F', '0-39', '🔴 Fail']
        ];
        gradeTable.innerHTML = grades.map(([g, r, d]) =>
            `<div class="grade-table-row"><span><strong>${g}</strong></span><span>${r}</span><span>${d}</span></div>`
        ).join('');
    }
}

// Init on load
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
    loadLearningStatus();
});


// ──── Model Learning Functions ────

async function loadLearningStatus() {
    try {
        const resp = await fetch(`${API_BASE}/api/learning/status`);
        if (!resp.ok) return;
        const data = await resp.json();

        const td = data.training_data || {};
        document.getElementById('learn-total-samples').textContent = td.total || 0;
        document.getElementById('learn-corrected').textContent = td.user_corrected || 0;
        document.getElementById('learn-model-version').textContent = `v${data.current_model_version || 0}`;
        document.getElementById('learn-new-samples').textContent = data.new_samples_since_last_train || 0;

        // Summary
        const summaryDiv = document.getElementById('learning-summary');
        summaryDiv.innerHTML = `<span style="line-height:1.8;">${data.learning_summary || ''}</span>`;

        // Retrain button state
        const retrainMsg = document.getElementById('retrain-message');
        const retrainBtn = document.getElementById('retrain-btn');
        if (data.retrain_recommended) {
            retrainMsg.innerHTML = `🔄 <strong>${data.new_samples_since_last_train} new DPR(s)</strong> available for training. Retraining is recommended!`;
            retrainBtn.classList.add('pulse');
        } else if (td.total === 0) {
            retrainMsg.textContent = 'Upload DPRs first to generate training data, then retrain the models.';
        } else {
            retrainMsg.textContent = `Models are up to date. Upload ${data.retrain_threshold - data.new_samples_since_last_train} more DPR(s) before next retrain.`;
        }

        // Version history chart
        if (data.version_history && data.version_history.length > 0) {
            renderAccuracyChart(data.version_history);
            renderVersionHistory(data.version_history);
        }

    } catch (err) {
        console.warn('Could not load learning status:', err);
    }
}

function renderAccuracyChart(history) {
    const ctx = document.getElementById('accuracy-chart');
    if (!ctx) return;
    if (window.accuracyChart) window.accuracyChart.destroy();

    // Reverse to chronological order
    const sorted = [...history].reverse();
    const labels = sorted.map(v => `v${v.version}`);

    const costR2 = sorted.map(v => {
        const m = v.cost_metrics || {};
        return (m.r2 || 0) * 100;
    });
    const riskAcc = sorted.map(v => {
        const m = v.risk_metrics || {};
        return (m.accuracy || 0) * 100;
    });
    const realSamples = sorted.map(v => v.real_samples || 0);

    window.accuracyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Cost Model R² (%)',
                    data: costR2,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59,130,246,0.15)',
                    fill: true,
                    tension: 0.3,
                    borderWidth: 2,
                    pointRadius: 4,
                },
                {
                    label: 'Risk Classifier Accuracy (%)',
                    data: riskAcc,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16,185,129,0.15)',
                    fill: true,
                    tension: 0.3,
                    borderWidth: 2,
                    pointRadius: 4,
                },
                {
                    label: 'Real DPR Samples',
                    data: realSamples,
                    borderColor: '#f59e0b',
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.3,
                    borderWidth: 2,
                    pointRadius: 3,
                    yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: {
                    beginAtZero: true, max: 100,
                    title: { display: true, text: 'Accuracy (%)', color: '#94a3b8' },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#94a3b8' },
                },
                y1: {
                    position: 'right',
                    beginAtZero: true,
                    title: { display: true, text: 'DPR Samples', color: '#94a3b8' },
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#94a3b8' },
                },
                x: { ticks: { color: '#94a3b8' } }
            },
            plugins: {
                legend: { labels: { color: '#94a3b8' } },
                title: { display: true, text: 'Model Accuracy Improvement Over Versions', color: '#94a3b8' }
            }
        }
    });
}

function renderVersionHistory(history) {
    const container = document.getElementById('version-history-list');
    if (!container || !history.length) return;

    container.innerHTML = '<h4 style="margin-bottom:10px; color:#e2e8f0;">Training History</h4>';
    history.forEach(v => {
        const costR2 = v.cost_metrics ? `R²: ${(v.cost_metrics.r2 * 100).toFixed(1)}%` : '-';
        const riskAcc = v.risk_metrics ? `Acc: ${(v.risk_metrics.accuracy * 100).toFixed(1)}%` : '-';
        const date = v.trained_at ? new Date(v.trained_at).toLocaleDateString() : '-';

        container.innerHTML += `
            <div class="section-item" style="margin-bottom:5px;">
                <div class="section-status">
                    <i class="fas fa-code-branch" style="color: #3b82f6;"></i>
                    <span><strong>v${v.version}</strong> — ${v.real_samples} real + ${v.total_samples - v.real_samples} synthetic samples</span>
                </div>
                <span style="color: #94a3b8; font-size: 0.85em;">
                    Cost ${costR2} | Risk ${riskAcc} | ${date}
                </span>
            </div>`;
    });
}

async function retrainModels() {
    const btn = document.getElementById('retrain-btn');
    const progress = document.getElementById('retrain-progress');
    const progressFill = document.getElementById('retrain-progress-fill');
    const progressText = document.getElementById('retrain-progress-text');
    const resultDiv = document.getElementById('retrain-result');

    btn.disabled = true;
    progress.classList.remove('hidden');
    resultDiv.classList.add('hidden');

    progressFill.style.width = '30%';
    progressFill.style.background = 'var(--accent)';
    progressText.textContent = '🧠 Training ML models with accumulated DPR data...';

    try {
        const resp = await fetch(`${API_BASE}/api/learning/retrain`, { method: 'POST' });
        const data = await resp.json();

        if (!resp.ok) throw new Error(data.detail || 'Training failed');

        progressFill.style.width = '100%';
        progressFill.style.background = 'var(--success)';
        progressText.textContent = '✅ Training complete!';

        const models = data.training_report?.models || {};
        const costR2 = models.cost_overrun?.r2 ? `${(models.cost_overrun.r2 * 100).toFixed(1)}%` : '-';
        const riskAcc = models.risk_classifier?.accuracy ? `${(models.risk_classifier.accuracy * 100).toFixed(1)}%` : '-';

        resultDiv.classList.remove('hidden');
        resultDiv.innerHTML = `
            <div style="background: rgba(16,185,129,0.1); padding: 15px; border-radius: 8px; border-left: 4px solid var(--success);">
                <h4 style="color: var(--success); margin-bottom: 10px;">🎉 Model v${data.model_version} trained successfully!</h4>
                <p><strong>${data.real_samples_used}</strong> real DPR(s) used for training</p>
                <p>Cost Model R²: <strong>${costR2}</strong> | Risk Classifier Accuracy: <strong>${riskAcc}</strong></p>
                <p style="color: #94a3b8; margin-top: 8px;">Future predictions will now use the improved models.</p>
            </div>`;

        // Refresh learning status
        setTimeout(loadLearningStatus, 1000);

    } catch (err) {
        progressFill.style.width = '100%';
        progressFill.style.background = 'var(--danger)';
        progressText.textContent = `❌ Error: ${err.message}`;
    } finally {
        btn.disabled = false;
    }
}

async function submitFeedback() {
    const docId = document.getElementById('feedback-doc-id').value;
    if (!docId) {
        alert('Please enter a Document ID');
        return;
    }

    const params = { document_id: docId };
    const cost = document.getElementById('feedback-cost').value;
    const delay = document.getElementById('feedback-delay').value;
    const risk = document.getElementById('feedback-risk').value;
    if (cost) params.actual_cost_overrun = cost;
    if (delay) params.actual_delay_months = delay;
    if (risk) params.actual_risk_level = risk;

    const resultDiv = document.getElementById('feedback-result');

    try {
        const resp = await fetch(
            `${API_BASE}/api/learning/feedback${buildQuery(params)}`,
            { method: 'POST' }
        );
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || 'Feedback failed');

        resultDiv.classList.remove('hidden');
        resultDiv.innerHTML = `
            <div style="background: rgba(16,185,129,0.1); padding: 12px; border-radius: 8px; border-left: 4px solid var(--success);">
                ✅ ${data.message} (Fields updated: ${data.corrected_fields.join(', ')})
            </div>`;

        // Clear form
        document.getElementById('feedback-cost').value = '';
        document.getElementById('feedback-delay').value = '';
        document.getElementById('feedback-risk').value = '';

        setTimeout(loadLearningStatus, 500);

    } catch (err) {
        resultDiv.classList.remove('hidden');
        resultDiv.innerHTML = `<div style="background:rgba(239,68,68,0.1);padding:12px;border-radius:8px;border-left:4px solid var(--danger);">❌ ${err.message}</div>`;
    }
}
