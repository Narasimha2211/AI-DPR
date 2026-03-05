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
document.addEventListener('DOMContentLoaded', initDashboard);
