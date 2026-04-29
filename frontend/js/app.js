// ============================================
// AI DPR Analysis System - Frontend JavaScript
// NeSETU Integrated · FastAPI Connected
// ============================================

const API_BASE = '';
let currentFilePath = null;
let currentDocumentId = null;
let currentState = null;
let currentProjectType = null;
let currentProjectCost = null;
let analysisData = null;

// ── Security: HTML entity escaping to prevent XSS ──
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const s = String(str);
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(s));
    return div.innerHTML;
}
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
    // Hide any open modals before switching tabs
    const authOverlay = document.getElementById('auth-modal-overlay');
    if (authOverlay) {
        authOverlay.classList.add('hidden');
    }
    
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
}

// ---- File Upload ----
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const uploadForm = document.getElementById('upload-form');

// Ensure elements exist before adding listeners
if (uploadArea && fileInput && uploadForm) {
    uploadArea.addEventListener('click', () => {
        console.log('Upload area clicked');
        fileInput.click();
    });
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
} else {
    console.error('Upload form elements not found:', { uploadArea, fileInput, uploadForm });
}

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
if (uploadForm) {
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

        const uploadResp = await authFetch(`${API_BASE}/api/upload/dpr`, {
            method: 'POST', body: formData
        });
        const uploadResult = await uploadResp.json();

        if (!uploadResp.ok) throw new Error(uploadResult.detail || 'Upload failed');

        currentFilePath = uploadResult.file_path;
        currentDocumentId = uploadResult.document_id;

        // Step 2: Connect to WebSocket for real-time progress
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${uploadResult.websocket_url}`;
        const ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.progress) progressFill.style.width = `${msg.progress}%`;
            if (msg.message) progressText.textContent = msg.message;

            if (msg.step === 'error') {
                progressFill.style.background = 'var(--danger)';
                uploadBtn.disabled = false;
                ws.close();
            }

            if (msg.step === 'done') {
                // Pipeline complete
                analysisData = msg.data.analysis;
                qualityData = msg.data.quality;
                riskData = msg.data.risk;

                renderAnalysis(analysisData);
                renderQualityScore(qualityData);
                renderRiskPrediction(riskData);

                setTimeout(() => switchTab('analysis'), 1500);
                uploadBtn.disabled = false;
                ws.close();
            }
        };

        ws.onclose = () => {
            if (uploadBtn.disabled) {
                // Closed unexpectedly
                progressText.textContent = '❌ Connection lost while processing.';
                progressFill.style.background = 'var(--danger)';
                uploadBtn.disabled = false;
            }
        };

    } catch (err) {
        progressText.textContent = `❌ Error: ${err.message}`;
        progressFill.style.background = 'var(--danger)';
        console.error(err);
        uploadBtn.disabled = false;
    }
    });
} else {
    console.error('Upload form not found');
}

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

    const color = score >= 80 ? 'var(--emerald)' : score >= 60 ? 'var(--gold)' :
                  score >= 40 ? 'var(--warning)' : 'var(--danger)';
    circle.style.borderColor = color;
    circle.style.color = color;

    // Score bars
    const barsContainer = document.getElementById('score-bars');
    barsContainer.innerHTML = '';

    const scoreItems = [
        { name: 'Section Completeness', key: 'section_completeness', color: '#10B981' },
        { name: 'Technical Depth', key: 'technical_depth', color: '#8B5CF6' },
        { name: 'Financial Accuracy', key: 'financial_accuracy', color: '#F59E0B' },
        { name: 'Compliance', key: 'compliance', color: '#3B82F6' },
        { name: 'Risk Assessment Quality', key: 'risk_assessment_quality', color: '#EF4444' }
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
                backgroundColor: 'rgba(16,185,129,0.15)',
                borderColor: '#10B981',
                borderWidth: 2,
                pointBackgroundColor: '#10B981'
            }]
        },
        options: {
            scales: {
                r: {
                    beginAtZero: true, max: 100,
                    grid: { color: 'rgba(255,255,255,0.06)' },
                    ticks: { display: false },
                    pointLabels: { color: '#94A3B8', font: { size: 11, family: 'Inter' } }
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
                                costPct > 30 ? 'var(--gold)' : 'var(--emerald)';

    // Delay risk
    const delayPct = summary.delay_probability || 0;
    document.getElementById('delay-risk-pct').textContent = `${delayPct.toFixed(1)}%`;
    const delayBar = document.getElementById('delay-risk-bar');
    delayBar.style.width = `${delayPct}%`;
    delayBar.style.background = delayPct > 70 ? 'var(--danger)' :
                                 delayPct > 50 ? 'var(--warning)' :
                                 delayPct > 30 ? 'var(--gold)' : 'var(--emerald)';

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
    const colors = ['#10B981', '#3B82F6', '#F59E0B', '#F97316', '#EF4444'];

    window.mcChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Projected Cost (₹ Crores)',
                data: values,
                backgroundColor: colors.map(c => c + '60'),
                borderColor: colors,
                borderWidth: 2,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#94A3B8' } },
                x: { ticks: { color: '#94A3B8' } }
            },
            plugins: {
                legend: { display: false },
                title: { display: true, text: 'Cost Distribution (Monte Carlo)', color: '#94A3B8', font: { family: 'Inter' } }
            }
        }
    });
}

// ──────────────────────────────────────────
// NeSETU Dashboard
// ──────────────────────────────────────────

const NESETU_SCHEMES = [
    {
        name: 'NESIDS — OTRI',
        icon: '🏗️',
        iconBg: 'linear-gradient(135deg, #059669, #10B981)',
        projects: 1592,
        approved: '₹20,761 Cr',
        expenditure: '₹15,949 Cr',
        uc: '₹14,285 Cr',
        link: 'https://nesetu.mdoner.gov.in/projects/project-list?scheme=NesidsO',
        desc: 'Non-Road Infrastructure: Tourism, IT, Education, Health & more'
    },
    {
        name: 'NESIDS — Roads',
        icon: '🛣️',
        iconBg: 'linear-gradient(135deg, #1E40AF, #3B82F6)',
        projects: 121,
        approved: '₹5,747 Cr',
        expenditure: '₹4,138 Cr',
        uc: '₹2,464 Cr',
        link: 'https://nesetu.mdoner.gov.in/projects/project-list?scheme=NesidsR',
        desc: 'Road connectivity for North Eastern states'
    },
    {
        name: 'PM-DevINE',
        icon: '🇮🇳',
        iconBg: 'linear-gradient(135deg, #D97706, #F59E0B)',
        projects: 48,
        approved: '₹6,046 Cr',
        expenditure: '₹2,496 Cr',
        uc: '₹595 Cr',
        link: 'https://nesetu.mdoner.gov.in/projects/project-list?scheme=pmdevine',
        desc: "Prime Minister's Development Initiative for NE"
    },
    {
        name: 'Schemes of NEC',
        icon: '🏛️',
        iconBg: 'linear-gradient(135deg, #7C3AED, #8B5CF6)',
        projects: 1824,
        approved: '₹14,422 Cr',
        expenditure: '₹12,225 Cr',
        uc: '₹11,005 Cr',
        link: 'https://nesetu.mdoner.gov.in/projects/project-list?scheme=schemesofnec',
        desc: 'North Eastern Council funded projects'
    },
    {
        name: 'Special Packages',
        icon: '📦',
        iconBg: 'linear-gradient(135deg, #DB2777, #EC4899)',
        projects: 119,
        approved: '₹2,106 Cr',
        expenditure: '₹1,354 Cr',
        uc: '₹1,125 Cr',
        link: 'https://nesetu.mdoner.gov.in/projects/project-list?scheme=specialpackage',
        desc: 'Special development packages for NE Region'
    }
];

const MDONER_STATES = [
    { name: 'Arunachal Pradesh', icon: '🏔️', capital: 'Itanagar', area: '83,743 km²' },
    { name: 'Assam', icon: '🦏', capital: 'Dispur', area: '78,438 km²' },
    { name: 'Manipur', icon: '💃', capital: 'Imphal', area: '22,327 km²' },
    { name: 'Meghalaya', icon: '🌧️', capital: 'Shillong', area: '22,429 km²' },
    { name: 'Mizoram', icon: '🎋', capital: 'Aizawl', area: '21,081 km²' },
    { name: 'Nagaland', icon: '🦅', capital: 'Kohima', area: '16,579 km²' },
    { name: 'Sikkim', icon: '⛰️', capital: 'Gangtok', area: '7,096 km²' },
    { name: 'Tripura', icon: '🌺', capital: 'Agartala', area: '10,486 km²' }
];

function renderNeSETUDashboard() {
    // Scheme cards
    const grid = document.getElementById('scheme-grid');
    if (!grid) return;

    grid.innerHTML = NESETU_SCHEMES.map(s => `
        <div class="scheme-card">
            <h3>
                <span class="scheme-icon" style="background:${s.iconBg};">${s.icon}</span>
                ${s.name}
            </h3>
            <p style="color:var(--text-muted);font-size:12px;margin:-8px 0 14px;">${s.desc}</p>
            <div class="scheme-stats">
                <div class="scheme-stat">
                    <div class="scheme-stat-label">Projects</div>
                    <div class="scheme-stat-value highlight">${s.projects.toLocaleString()}</div>
                </div>
                <div class="scheme-stat">
                    <div class="scheme-stat-label">Approved Cost</div>
                    <div class="scheme-stat-value gold">${s.approved}</div>
                </div>
                <div class="scheme-stat">
                    <div class="scheme-stat-label">Expenditure</div>
                    <div class="scheme-stat-value">${s.expenditure}</div>
                </div>
                <div class="scheme-stat">
                    <div class="scheme-stat-label">U.C. Received</div>
                    <div class="scheme-stat-value">${s.uc}</div>
                </div>
            </div>
            <a href="${s.link}" target="_blank" class="scheme-card-link">
                View on NeSETU <i class="fas fa-arrow-right"></i>
            </a>
        </div>
    `).join('');

    // States info
    const statesDiv = document.getElementById('nesetu-states-info');
    if (statesDiv) {
        statesDiv.innerHTML = `
            <div style="display:flex;flex-wrap:wrap;gap:10px;">
                ${MDONER_STATES.map(s => `
                    <div style="flex:1;min-width:180px;padding:14px;background:var(--bg-primary);border:1px solid var(--border);border-radius:var(--radius-sm);transition:all 0.3s;"
                         onmouseover="this.style.borderColor='rgba(245,158,11,0.4)';this.style.transform='translateY(-2px)'"
                         onmouseout="this.style.borderColor='var(--border)';this.style.transform='none'">
                        <div style="font-size:20px;margin-bottom:6px;">${s.icon}</div>
                        <div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:2px;">${s.name}</div>
                        <div style="font-size:11px;color:var(--text-muted);">Capital: ${s.capital}</div>
                        <div style="font-size:11px;color:var(--text-muted);">Area: ${s.area}</div>
                    </div>
                `).join('')}
            </div>`;
    }

    // NeSETU chart
    renderNeSETUChart();
}

function renderNeSETUChart() {
    const ctx = document.getElementById('nesetu-chart');
    if (!ctx) return;
    if (window.nesetuChart) window.nesetuChart.destroy();

    const labels = NESETU_SCHEMES.map(s => s.name);
    const projects = NESETU_SCHEMES.map(s => s.projects);
    const approved = NESETU_SCHEMES.map(s => parseFloat(s.approved.replace(/[₹, Cr]/g, '').replace(',', '')));
    const expenditure = NESETU_SCHEMES.map(s => parseFloat(s.expenditure.replace(/[₹, Cr]/g, '').replace(',', '')));

    window.nesetuChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Projects',
                    data: projects,
                    backgroundColor: 'rgba(16,185,129,0.6)',
                    borderColor: '#10B981',
                    borderWidth: 2,
                    borderRadius: 6,
                    yAxisID: 'y1'
                },
                {
                    label: 'Approved (₹ Cr)',
                    data: approved,
                    backgroundColor: 'rgba(245,158,11,0.5)',
                    borderColor: '#F59E0B',
                    borderWidth: 2,
                    borderRadius: 6,
                    yAxisID: 'y'
                },
                {
                    label: 'Expenditure (₹ Cr)',
                    data: expenditure,
                    backgroundColor: 'rgba(59,130,246,0.5)',
                    borderColor: '#3B82F6',
                    borderWidth: 2,
                    borderRadius: 6,
                    yAxisID: 'y'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Amount (₹ Crores)', color: '#94A3B8', font: { family: 'Inter' } },
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#94A3B8' }
                },
                y1: {
                    position: 'right',
                    beginAtZero: true,
                    title: { display: true, text: 'No. of Projects', color: '#94A3B8', font: { family: 'Inter' } },
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#94A3B8' }
                },
                x: {
                    ticks: { color: '#94A3B8', font: { size: 10, family: 'Inter' } }
                }
            },
            plugins: {
                legend: { labels: { color: '#94A3B8', font: { family: 'Inter' } } },
                title: {
                    display: true,
                    text: 'MDoNER NeSETU — Scheme-wise Breakdown (Source: nesetu.mdoner.gov.in)',
                    color: '#94A3B8',
                    font: { family: 'Inter', size: 13 }
                }
            }
        }
    });
}


// ──────────────────────────────────────────
// Dashboard & System Info
// ──────────────────────────────────────────

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
    renderNeSETUDashboard();
    loadLearningStatus();
    initializeAdminUser(); // Ensure admin user exists
});


// ──────────────────────────────────────────
// Model Learning Functions
// ──────────────────────────────────────────

async function initializeAdminUser() {
    try {
        const resp = await fetch(`${API_BASE}/api/auth/init-admin`);
        if (resp.ok) {
            console.log('✅ Admin user initialized');
        }
    } catch (err) {
        console.log('Admin user check completed');
    }
}

async function loadLearningStatus() {
    try {
        const resp = await authFetch(`${API_BASE}/api/learning/status`);
        if (!resp.ok) return;
        const data = await resp.json();

        const td = data.training_data || {};
        document.getElementById('learn-total-samples').textContent = td.total || 0;
        document.getElementById('learn-corrected').textContent = td.user_corrected || 0;
        document.getElementById('learn-model-version').textContent = `v${data.current_model_version || 0}`;
        document.getElementById('learn-new-samples').textContent = data.new_samples_since_last_train || 0;

        // Summary
        const summaryDiv = document.getElementById('learning-summary');
        summaryDiv.innerHTML = `<span style="line-height:1.8;">${escapeHtml(data.learning_summary || '')}</span>`;

        // Retrain button state
        const retrainMsg = document.getElementById('retrain-message');
        const retrainBtn = document.getElementById('retrain-btn');
        if (data.retrain_recommended) {
            retrainMsg.innerHTML = `🔄 <strong>${escapeHtml(data.new_samples_since_last_train)} new DPR(s)</strong> available for training. Retraining is recommended!`;
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
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16,185,129,0.12)',
                    fill: true, tension: 0.3, borderWidth: 2, pointRadius: 4,
                },
                {
                    label: 'Risk Classifier Accuracy (%)',
                    data: riskAcc,
                    borderColor: '#3B82F6',
                    backgroundColor: 'rgba(59,130,246,0.12)',
                    fill: true, tension: 0.3, borderWidth: 2, pointRadius: 4,
                },
                {
                    label: 'Real DPR Samples',
                    data: realSamples,
                    borderColor: '#F59E0B',
                    borderDash: [5, 5],
                    fill: false, tension: 0.3, borderWidth: 2, pointRadius: 3,
                    yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: {
                    beginAtZero: true, max: 100,
                    title: { display: true, text: 'Accuracy (%)', color: '#94A3B8' },
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#94A3B8' },
                },
                y1: {
                    position: 'right', beginAtZero: true,
                    title: { display: true, text: 'DPR Samples', color: '#94A3B8' },
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#94A3B8' },
                },
                x: { ticks: { color: '#94A3B8' } }
            },
            plugins: {
                legend: { labels: { color: '#94A3B8', font: { family: 'Inter' } } },
                title: { display: true, text: 'Model Accuracy Over Versions', color: '#94A3B8', font: { family: 'Inter' } }
            }
        }
    });
}

function renderVersionHistory(history) {
    const container = document.getElementById('version-history-list');
    if (!container || !history.length) return;

    container.innerHTML = '<h4 style="margin-bottom:10px; color:var(--text-primary);">Training History</h4>';
    history.forEach(v => {
        const costR2 = v.cost_metrics ? `R²: ${(v.cost_metrics.r2 * 100).toFixed(1)}%` : '-';
        const riskAcc = v.risk_metrics ? `Acc: ${(v.risk_metrics.accuracy * 100).toFixed(1)}%` : '-';
        const date = v.trained_at ? new Date(v.trained_at).toLocaleDateString() : '-';

        container.innerHTML += `
            <div class="section-item" style="margin-bottom:5px;">
                <div class="section-status">
                    <i class="fas fa-code-branch" style="color: var(--emerald);"></i>
                    <span><strong>v${v.version}</strong> — ${v.real_samples} real + ${v.total_samples - v.real_samples} synthetic samples</span>
                </div>
                <span style="color: var(--text-muted); font-size: 0.85em;">
                    Cost ${costR2} | Risk ${riskAcc} | ${date}
                </span>
            </div>`;
    });
}

// ──────────────────────────────────────────
// JWT Authentication Logic
// ──────────────────────────────────────────

let authToken = localStorage.getItem('aiDprToken') || null;
let currentUser = JSON.parse(localStorage.getItem('aiDprUser') || 'null');

async function authFetch(url, options = {}) {
    if (!options.headers) options.headers = {};
    if (authToken) {
        options.headers['Authorization'] = `Bearer ${authToken}`;
    }
    const response = await fetch(url, options);
    if (response.status === 401 || response.status === 403) {
        // Token expired or invalid
        logout();
        showAuthLogin();
        throw new Error('Authentication required');
    }
    return response;
}

function updateAuthUI() {
    const roleSpan = document.getElementById('header-user-role');
    const indicator = document.getElementById('auth-indicator');
    const userInfo = document.getElementById('header-user-info');
    const userNameSpan = document.getElementById('header-user-name');
    const uploadTabBtn = document.querySelector('[data-tab="upload"]');
    const authOverlay = document.getElementById('auth-modal-overlay');

    if (currentUser && authToken) {
        roleSpan.textContent = `${currentUser.role} Access`;
        indicator.style.backgroundColor = '#4ade80';
        indicator.style.boxShadow = '0 0 8px #4ade80';
        userInfo.classList.remove('hidden');
        userNameSpan.textContent = currentUser.name;
        authOverlay.classList.add('hidden');
        
        // Role based access
        if (currentUser.role === 'Viewer') {
            uploadTabBtn.style.display = 'none';
            if (document.getElementById('tab-upload').classList.contains('active')) {
                // If viewer is on upload tab, switch to dashboard
                switchTab('dashboard');
            }
        } else {
            uploadTabBtn.style.display = 'flex';
        }
    } else {
        roleSpan.textContent = 'Not Authenticated';
        indicator.style.backgroundColor = '#fca5a5';
        indicator.style.boxShadow = '0 0 8px #fca5a5';
        userInfo.classList.add('hidden');
        authOverlay.classList.remove('hidden');
    }
}

function showAuthLogin() {
    document.getElementById('auth-modal-overlay').classList.remove('hidden');
    document.getElementById('auth-password').value = '';
    document.getElementById('auth-error').classList.add('hidden');
    setTimeout(() => document.getElementById('auth-email').focus(), 300);
}

function toggleAuthPasswordVisibility() {
    const input = document.getElementById('auth-password');
    const icon = document.getElementById('auth-password-toggle-icon');
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fas fa-eye-slash';
    } else {
        input.type = 'password';
        icon.className = 'fas fa-eye';
    }
}

async function login() {
    const email = document.getElementById('auth-email').value.trim();
    const password = document.getElementById('auth-password').value.trim();
    const errorDiv = document.getElementById('auth-error');
    const errorText = document.getElementById('auth-error-text');
    const loginBtn = document.getElementById('auth-login-btn');

    if (!email || !password) {
        errorDiv.classList.remove('hidden');
        errorText.textContent = 'Please enter email and password';
        return;
    }

    loginBtn.disabled = true;
    loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Authenticating...';
    errorDiv.classList.add('hidden');

    try {
        const formData = new URLSearchParams();
        formData.append('username', email); // OAuth2 expects username
        formData.append('password', password);

        const resp = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Authentication failed');
        }

        const data = await resp.json();
        authToken = data.access_token;
        currentUser = data.user;
        
        localStorage.setItem('aiDprToken', authToken);
        localStorage.setItem('aiDprUser', JSON.stringify(currentUser));
        
        updateAuthUI();

    } catch (err) {
        errorDiv.classList.remove('hidden');
        errorText.textContent = err.message || 'Invalid credentials';
        
        const modal = document.querySelector('.admin-modal');
        modal.style.animation = 'none';
        setTimeout(() => { modal.style.animation = 'modalShake 0.4s ease'; }, 10);
    } finally {
        loginBtn.disabled = false;
        loginBtn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Authenticate';
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('aiDprToken');
    localStorage.removeItem('aiDprUser');
    updateAuthUI();
}

// Call initially
updateAuthUI();

// ──────────────────────────────────────────
// History Tab Logic
// ──────────────────────────────────────────

async function loadDocumentHistory() {
    const tbody = document.getElementById('history-table-body');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="7" style="padding: 32px; text-align: center; color: var(--text-muted);"><i class="fas fa-spinner fa-spin"></i> Loading documents...</td></tr>';
    
    try {
        const resp = await authFetch(`${API_BASE}/api/documents/list?limit=50`);
        const data = await resp.json();
        
        if (!resp.ok) throw new Error(data.detail || 'Errors loading history');
        
        if (!data.documents || data.documents.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="padding: 32px; text-align: center; color: var(--text-muted);">No documents processed yet.</td></tr>';
            return;
        }

        let html = '';
        data.documents.forEach(doc => {
            const dateStr = doc.upload_date ? new Date(doc.upload_date).toLocaleString() : '-';
            const riskClass = doc.risk_level.includes('High') || doc.risk_level.includes('Critical') ? 'text-danger' : 
                              doc.risk_level.includes('Medium') ? 'text-warning' : 'text-success';
            
            html += `
                <tr style="border-bottom: 1px solid var(--border-color); font-size: 14px;">
                    <td style="padding: 12px 16px;">
                        <input type="checkbox" class="doc-compare-checkbox" value="${doc.id}" data-name="${doc.file_name}" onchange="updateCompareSelection()">
                    </td>
                    <td style="padding: 12px 16px; font-weight: 500; color: var(--primary-blue);">${doc.file_name}</td>
                    <td style="padding: 12px 16px;">${doc.state_name}</td>
                    <td style="padding: 12px 16px; color: var(--text-muted); font-size: 13px;">${dateStr}</td>
                    <td style="padding: 12px 16px; font-weight: bold;">${doc.grade}</td>
                    <td style="padding: 12px 16px;"><span class="${riskClass}">${doc.risk_level}</span></td>
                    <td style="padding: 12px 16px; text-align: right;">
                        <button class="btn-primary" style="padding: 4px 8px; font-size: 12px; width: auto;" onclick="loadPastAnalysis('${doc.id}')">View</button>
                    </td>
                </tr>
            `;
        });
        
        tbody.innerHTML = html;
        updateCompareSelection();
        
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" style="padding: 32px; text-align: center; color: var(--danger);"><i class="fas fa-exclamation-circle"></i> ${escapeHtml(err.message)}</td></tr>`;
    }
}

async function loadPastAnalysis(docId) {
    alert("Loading past analysis data for " + docId + " will populate the tabs.");
    // In a full implementation, this triggers /api/documents/{id} and repopulates global state
}

// ──────────────────────────────────────────
// Retraining Tab Logic
// ──────────────────────────────────────────

async function retrainModels() {
    if (!currentUser || currentUser.role !== 'Admin') {
        alert("Only System Administrators can retrain the models.");
        return;
    }

    const btn = document.getElementById('retrain-btn');
    const progress = document.getElementById('retrain-progress');
    const progressFill = document.getElementById('retrain-progress-fill');
    const progressText = document.getElementById('retrain-progress-text');
    const resultDiv = document.getElementById('retrain-result');

    btn.disabled = true;
    progress.classList.remove('hidden');
    resultDiv.classList.add('hidden');

    progressFill.style.width = '30%';
    progressFill.style.background = 'var(--warning)';
    progressText.textContent = '🧠 Training ML models with accumulated DPR data...';

    try {
        const resp = await authFetch(`${API_BASE}/api/learning/retrain`, {
            method: 'POST'
        });
        const data = await resp.json();

        if (!resp.ok) {
            if (resp.status === 403) {
                adminPassword = null; // Clear cached password
                throw new Error('Session expired — please re-authenticate');
            }
            throw new Error(data.detail || 'Training failed');
        }

        progressFill.style.width = '100%';
        progressFill.style.background = 'var(--accent-emerald)';
        progressText.textContent = '✅ Training complete!';

        const models = data.training_report?.models || {};
        const costR2 = models.cost_overrun?.r2 ? `${(models.cost_overrun.r2 * 100).toFixed(1)}%` : '-';
        const riskAcc = models.risk_classifier?.accuracy ? `${(models.risk_classifier.accuracy * 100).toFixed(1)}%` : '-';

        resultDiv.classList.remove('hidden');
        resultDiv.innerHTML = `
            <div style="background: #ecfdf5; padding: 15px; border-radius: var(--radius); border-left: 4px solid var(--accent-emerald);">
                <h4 style="color: var(--accent-emerald); margin-bottom: 10px;">🎉 Model v${data.model_version} trained successfully!</h4>
                <p><strong>${data.real_samples_used}</strong> real DPR(s) used for training</p>
                <p>Cost Model R²: <strong>${costR2}</strong> | Risk Classifier Accuracy: <strong>${riskAcc}</strong></p>
                <p style="color: var(--text-muted); margin-top: 8px;">Future predictions will now use the improved models.</p>
            </div>`;

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
            <div style="background: var(--emerald-glow); padding: 12px; border-radius: var(--radius-sm); border-left: 4px solid var(--emerald);">
                ✅ ${data.message} (Fields updated: ${data.corrected_fields.join(', ')})
            </div>`;

        document.getElementById('feedback-cost').value = '';
        document.getElementById('feedback-delay').value = '';
        document.getElementById('feedback-risk').value = '';

        setTimeout(loadLearningStatus, 500);

    } catch (err) {
        resultDiv.classList.remove('hidden');
        resultDiv.innerHTML = `<div style="background:var(--danger-glow);padding:12px;border-radius:var(--radius-sm);border-left:4px solid var(--danger);">❌ ${escapeHtml(err.message)}</div>`;
    }
}

// ──────────────────────────────────────────
// PDF Export Logic
// ──────────────────────────────────────────

async function downloadPDF() {
    if (!currentDocumentId) {
        alert("No document currently loaded to export.");
        return;
    }
    
    // UI Feedback
    const btn = document.getElementById('export-pdf-btn');
    if (btn) btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    
    const url = `${API_BASE}/api/documents/export/${currentDocumentId}/pdf`;
    
    try {
        const response = await authFetch(url);
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: Failed to generate PDF`);
        }
        
        const blob = await response.blob();
        
        let filename = "AI_Evaluation.pdf";
        const disposition = response.headers.get('Content-Disposition');
        if (disposition && disposition.indexOf('attachment') !== -1) {
            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            const matches = filenameRegex.exec(disposition);
            if (matches != null && matches[1]) { 
                filename = matches[1].replace(/['"]/g, '');
            }
        }
        
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
        alert(`Error downloading PDF: ${error.message}`);
    } finally {
        if (btn) btn.innerHTML = '<i class="fas fa-file-pdf"></i> Export Original Report';
    }
}

function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
}

function updateCompareSelection() {
    // Placeholder for document comparison feature
    const checkboxes = document.querySelectorAll('.doc-compare-checkbox:checked');
    console.log(`${checkboxes.length} document(s) selected for comparison`);
}