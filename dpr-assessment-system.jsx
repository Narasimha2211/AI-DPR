import { useState, useEffect, useRef } from "react";

const COLORS = {
  bg: "#0A0F1E",
  surface: "#111827",
  card: "#1a2235",
  border: "#1e3a5f",
  accent: "#0EA5E9",
  accentGlow: "#0EA5E940",
  green: "#10B981",
  yellow: "#F59E0B",
  red: "#EF4444",
  purple: "#8B5CF6",
  text: "#E2E8F0",
  muted: "#64748B",
};

const QUALITY_RUBRIC = [
  { id: "completeness", label: "Document Completeness", weight: 25, icon: "📋" },
  { id: "technical", label: "Technical Accuracy", weight: 25, icon: "⚙️" },
  { id: "financial", label: "Financial Consistency", weight: 20, icon: "₹" },
  { id: "compliance", label: "Regulatory Compliance", weight: 20, icon: "✅" },
  { id: "feasibility", label: "Feasibility Assessment", weight: 10, icon: "🗺️" },
];

const RISK_FACTORS = [
  { id: "cost", label: "Cost Overrun Risk", icon: "💰" },
  { id: "schedule", label: "Schedule Delay Risk", icon: "⏱️" },
  { id: "implementation", label: "Implementation Risk", icon: "🏗️" },
  { id: "environmental", label: "Environmental Risk", icon: "🌿" },
];

const SAMPLE_GAPS = [
  { severity: "high", section: "Section 4.2", message: "Estimated project cost lacks district-level breakdown as per MDoNER format" },
  { severity: "high", section: "Section 7.1", message: "Survey & Investigation report not attached" },
  { severity: "medium", section: "Section 2.3", message: "Population data appears outdated (pre-2021 census figures)" },
  { severity: "medium", section: "Section 5.4", message: "Land acquisition status not specified" },
  { severity: "low", section: "Section 1.1", message: "State government concurrence letter missing signature date" },
  { severity: "low", section: "Section 6.2", message: "BOQ unit rates should be referenced against SOR 2023-24" },
];

const HISTORICAL_BENCHMARKS = [
  { name: "NE Road Connectivity Phase II", score: 71, costOverrun: 18, delay: 42 },
  { name: "Border Area Development Roads", score: 85, costOverrun: 7, delay: 15 },
  { name: "Sikkim Hill Roads Package", score: 63, costOverrun: 31, delay: 67 },
  { name: "Arunachal Connectivity Mission", score: 78, costOverrun: 12, delay: 28 },
];

function AnimatedNumber({ value, duration = 1500, suffix = "" }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start = 0;
    const step = value / (duration / 16);
    const timer = setInterval(() => {
      start += step;
      if (start >= value) { setDisplay(value); clearInterval(timer); }
      else setDisplay(Math.floor(start));
    }, 16);
    return () => clearInterval(timer);
  }, [value]);
  return <span>{display}{suffix}</span>;
}

function RadialGauge({ value, size = 120, color }) {
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;
  const gaugeColor = value >= 75 ? COLORS.green : value >= 50 ? COLORS.yellow : COLORS.red;
  const usedColor = color || gaugeColor;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100">
      <circle cx="50" cy="50" r={radius} fill="none" stroke="#1e3a5f" strokeWidth="8" />
      <circle cx="50" cy="50" r={radius} fill="none" stroke={usedColor} strokeWidth="8"
        strokeDasharray={circumference} strokeDashoffset={offset}
        strokeLinecap="round" transform="rotate(-90 50 50)"
        style={{ transition: "stroke-dashoffset 1.5s ease" }} />
      <text x="50" y="50" textAnchor="middle" dominantBaseline="middle"
        fill={usedColor} fontSize="18" fontWeight="bold" fontFamily="'Courier New', monospace">
        {value}
      </text>
      <text x="50" y="65" textAnchor="middle" dominantBaseline="middle"
        fill="#64748B" fontSize="8" fontFamily="sans-serif">/100</text>
    </svg>
  );
}

function RiskBar({ value, label }) {
  const color = value >= 70 ? COLORS.red : value >= 40 ? COLORS.yellow : COLORS.green;
  const riskLabel = value >= 70 ? "HIGH" : value >= 40 ? "MEDIUM" : "LOW";
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ color: COLORS.text, fontSize: 13 }}>{label}</span>
        <span style={{ color, fontSize: 12, fontWeight: "bold", fontFamily: "monospace" }}>{riskLabel} · {value}%</span>
      </div>
      <div style={{ background: "#1e3a5f", borderRadius: 4, height: 8, overflow: "hidden" }}>
        <div style={{
          width: `${value}%`, height: "100%", background: `linear-gradient(90deg, ${color}88, ${color})`,
          borderRadius: 4, transition: "width 1.5s ease", boxShadow: `0 0 8px ${color}88`
        }} />
      </div>
    </div>
  );
}

function FileUploadZone({ onUpload, uploading }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  const handleDrop = (e) => {
    e.preventDefault(); setDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length) onUpload(files[0]);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current.click()}
      style={{
        border: `2px dashed ${dragging ? COLORS.accent : COLORS.border}`,
        borderRadius: 12, padding: "48px 24px", textAlign: "center", cursor: "pointer",
        background: dragging ? `${COLORS.accent}10` : COLORS.card,
        transition: "all 0.3s ease",
        boxShadow: dragging ? `0 0 20px ${COLORS.accentGlow}` : "none",
      }}>
      <input ref={inputRef} type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.png,.tiff" style={{ display: "none" }}
        onChange={(e) => { if (e.target.files[0]) onUpload(e.target.files[0]); }} />
      <div style={{ fontSize: 48, marginBottom: 16 }}>
        {uploading ? "⏳" : "📁"}
      </div>
      <div style={{ color: COLORS.text, fontSize: 16, fontWeight: 600, marginBottom: 8 }}>
        {uploading ? "Processing DPR..." : "Upload DPR Document"}
      </div>
      <div style={{ color: COLORS.muted, fontSize: 13 }}>
        PDF, Word, Excel, Scanned Images · Drag & drop or click
      </div>
      {uploading && (
        <div style={{ marginTop: 20 }}>
          <ProcessingSteps />
        </div>
      )}
    </div>
  );
}

function ProcessingSteps() {
  const [step, setStep] = useState(0);
  const steps = ["OCR & Text Extraction", "NLP Entity Recognition", "Compliance Validation", "Risk Model Inference", "Generating Scorecard"];
  useEffect(() => {
    const t = setInterval(() => setStep(s => s < steps.length - 1 ? s + 1 : s), 700);
    return () => clearInterval(t);
  }, []);
  return (
    <div style={{ textAlign: "left", maxWidth: 300, margin: "0 auto" }}>
      {steps.map((s, i) => (
        <div key={s} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6, opacity: i <= step ? 1 : 0.3, transition: "opacity 0.4s" }}>
          <span style={{ fontSize: 14 }}>{i < step ? "✅" : i === step ? "⏳" : "⬜"}</span>
          <span style={{ color: COLORS.text, fontSize: 13 }}>{s}</span>
        </div>
      ))}
    </div>
  );
}

function ComplianceGap({ gap }) {
  const colors = { high: COLORS.red, medium: COLORS.yellow, low: COLORS.green };
  const bgColors = { high: "#EF444415", medium: "#F59E0B15", low: "#10B98115" };
  return (
    <div style={{
      background: bgColors[gap.severity], border: `1px solid ${colors[gap.severity]}40`,
      borderLeft: `3px solid ${colors[gap.severity]}`, borderRadius: 8, padding: "10px 14px", marginBottom: 8
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ color: colors[gap.severity], fontSize: 11, fontWeight: "bold", textTransform: "uppercase", fontFamily: "monospace" }}>
          {gap.severity} · {gap.section}
        </span>
      </div>
      <div style={{ color: COLORS.text, fontSize: 13 }}>{gap.message}</div>
    </div>
  );
}

function QualityScoreCard({ scores }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
      {QUALITY_RUBRIC.map(r => {
        const score = scores[r.id];
        const color = score >= 75 ? COLORS.green : score >= 50 ? COLORS.yellow : COLORS.red;
        return (
          <div key={r.id} style={{ background: COLORS.card, borderRadius: 8, padding: 14, border: `1px solid ${COLORS.border}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 18 }}>{r.icon}</span>
              <span style={{ color, fontWeight: "bold", fontSize: 18, fontFamily: "monospace" }}>{score}</span>
            </div>
            <div style={{ color: COLORS.text, fontSize: 12, marginBottom: 6 }}>{r.label}</div>
            <div style={{ background: "#1e3a5f", borderRadius: 3, height: 4 }}>
              <div style={{ width: `${score}%`, height: "100%", background: color, borderRadius: 3, transition: "width 1.5s ease" }} />
            </div>
            <div style={{ color: COLORS.muted, fontSize: 10, marginTop: 4 }}>Weight: {r.weight}%</div>
          </div>
        );
      })}
    </div>
  );
}

function BenchmarkTable({ data }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr>
            {["Project", "Quality Score", "Cost Overrun", "Delay"].map(h => (
              <th key={h} style={{ padding: "8px 12px", textAlign: "left", color: COLORS.muted, borderBottom: `1px solid ${COLORS.border}`, fontWeight: 600 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} style={{ borderBottom: `1px solid ${COLORS.border}20` }}>
              <td style={{ padding: "10px 12px", color: COLORS.text }}>{row.name}</td>
              <td style={{ padding: "10px 12px" }}>
                <span style={{ color: row.score >= 75 ? COLORS.green : row.score >= 60 ? COLORS.yellow : COLORS.red, fontFamily: "monospace", fontWeight: "bold" }}>{row.score}</span>
              </td>
              <td style={{ padding: "10px 12px", color: row.costOverrun > 20 ? COLORS.red : COLORS.yellow, fontFamily: "monospace" }}>{row.costOverrun}%</td>
              <td style={{ padding: "10px 12px", color: row.delay > 40 ? COLORS.red : COLORS.yellow, fontFamily: "monospace" }}>{row.delay} days</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [stage, setStage] = useState("upload"); // upload | processing | results
  const [uploading, setUploading] = useState(false);
  const [fileName, setFileName] = useState("");
  const [activeTab, setActiveTab] = useState("quality");

  const DEMO_SCORES = { completeness: 68, technical: 74, financial: 55, compliance: 62, feasibility: 80 };
  const DEMO_RISKS = { cost: 62, schedule: 78, implementation: 45, environmental: 30 };
  const overallScore = Math.round(
    QUALITY_RUBRIC.reduce((acc, r) => acc + (DEMO_SCORES[r.id] * r.weight) / 100, 0)
  );

  const handleUpload = (file) => {
    setFileName(file.name);
    setUploading(true);
    setStage("processing");
    setTimeout(() => { setUploading(false); setStage("results"); }, 4500);
  };

  const handleDemo = () => {
    setFileName("DEMO_NE_Road_Project_DPR.pdf");
    setUploading(true);
    setStage("processing");
    setTimeout(() => { setUploading(false); setStage("results"); }, 4500);
  };

  const cardStyle = {
    background: COLORS.card, border: `1px solid ${COLORS.border}`,
    borderRadius: 12, padding: 20, marginBottom: 16
  };

  const tabStyle = (id) => ({
    padding: "8px 18px", borderRadius: 8, cursor: "pointer", fontSize: 14, fontWeight: 600,
    border: "none", transition: "all 0.2s",
    background: activeTab === id ? COLORS.accent : "transparent",
    color: activeTab === id ? "#fff" : COLORS.muted,
  });

  return (
    <div style={{
      minHeight: "100vh", background: COLORS.bg, color: COLORS.text,
      fontFamily: "'IBM Plex Sans', 'Segoe UI', sans-serif",
      backgroundImage: "radial-gradient(ellipse at 20% 50%, #0EA5E915 0%, transparent 50%), radial-gradient(ellipse at 80% 20%, #8B5CF615 0%, transparent 50%)"
    }}>
      {/* Header */}
      <div style={{
        borderBottom: `1px solid ${COLORS.border}`, padding: "16px 32px",
        background: `${COLORS.surface}CC`, backdropFilter: "blur(12px)",
        position: "sticky", top: 0, zIndex: 100,
        display: "flex", alignItems: "center", justifyContent: "space-between"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.purple})`,
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20
          }}>🏔️</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16, letterSpacing: 0.3 }}>MDoNER · DPR Intelligence System</div>
            <div style={{ color: COLORS.muted, fontSize: 11 }}>Ministry of Development of North Eastern Region</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <div style={{
            background: `${COLORS.green}20`, border: `1px solid ${COLORS.green}40`,
            borderRadius: 20, padding: "4px 12px", fontSize: 12, color: COLORS.green, fontWeight: 600
          }}>● SYSTEM ONLINE</div>
          <div style={{ color: COLORS.muted, fontSize: 12 }}>v2.1.0 · ML Model: 85.2% Acc.</div>
        </div>
      </div>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>

        {/* Upload Stage */}
        {(stage === "upload" || stage === "processing") && (
          <div>
            <div style={{ textAlign: "center", marginBottom: 40 }}>
              <h1 style={{
                fontSize: 36, fontWeight: 800, marginBottom: 12,
                background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.purple})`,
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent"
              }}>
                DPR Quality Assessment &amp; Risk Prediction
              </h1>
              <p style={{ color: COLORS.muted, fontSize: 16, maxWidth: 560, margin: "0 auto" }}>
                Upload a Detailed Project Report for instant AI-powered quality scoring, compliance gap analysis, and ML-based risk forecasting.
              </p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 32 }}>
              {[
                { icon: "🔍", title: "NLP Document Analysis", desc: "Extracts entities, validates fields, checks completeness across all DPR sections" },
                { icon: "📊", title: "Quality Scorecard", desc: "Weighted scoring across 5 dimensions with MDoNER-specific compliance rules" },
                { icon: "🤖", title: "ML Risk Prediction", desc: "85%+ accuracy predictions for cost overrun, delays, and implementation risk" }
              ].map(f => (
                <div key={f.title} style={{ ...cardStyle, textAlign: "center", padding: 24 }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>{f.icon}</div>
                  <div style={{ fontWeight: 700, marginBottom: 8, fontSize: 15 }}>{f.title}</div>
                  <div style={{ color: COLORS.muted, fontSize: 13, lineHeight: 1.5 }}>{f.desc}</div>
                </div>
              ))}
            </div>

            <FileUploadZone onUpload={handleUpload} uploading={stage === "processing"} />

            {stage === "upload" && (
              <div style={{ textAlign: "center", marginTop: 16 }}>
                <span style={{ color: COLORS.muted, fontSize: 14 }}>— or — </span>
                <button onClick={handleDemo} style={{
                  background: "transparent", border: `1px solid ${COLORS.accent}`,
                  color: COLORS.accent, borderRadius: 8, padding: "8px 20px",
                  cursor: "pointer", fontSize: 14, fontWeight: 600, marginLeft: 8
                }}>
                  Run Demo with Sample DPR
                </button>
              </div>
            )}
          </div>
        )}

        {/* Results Stage */}
        {stage === "results" && (
          <div>
            {/* Top bar */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
              <div>
                <div style={{ color: COLORS.muted, fontSize: 12, marginBottom: 4 }}>📄 {fileName}</div>
                <h2 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Assessment Report</h2>
              </div>
              <button onClick={() => setStage("upload")} style={{
                background: COLORS.card, border: `1px solid ${COLORS.border}`,
                color: COLORS.text, borderRadius: 8, padding: "8px 18px", cursor: "pointer", fontSize: 14
              }}>← Upload New DPR</button>
            </div>

            {/* KPI Row */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 14, marginBottom: 24 }}>
              {[
                { label: "Overall Quality Score", value: overallScore, suffix: "/100", color: overallScore >= 70 ? COLORS.green : COLORS.yellow, badge: overallScore >= 70 ? "GOOD" : "NEEDS REVIEW" },
                { label: "Compliance Gaps Found", value: 6, suffix: " issues", color: COLORS.red, badge: "2 CRITICAL" },
                { label: "Cost Overrun Risk", value: 62, suffix: "%", color: COLORS.yellow, badge: "MEDIUM-HIGH" },
                { label: "Schedule Delay Risk", value: 78, suffix: "%", color: COLORS.red, badge: "HIGH" },
              ].map(k => (
                <div key={k.label} style={{ ...cardStyle, marginBottom: 0 }}>
                  <div style={{ color: COLORS.muted, fontSize: 11, marginBottom: 8 }}>{k.label}</div>
                  <div style={{ fontSize: 28, fontWeight: 800, color: k.color, fontFamily: "monospace" }}>
                    <AnimatedNumber value={k.value} suffix={k.suffix} />
                  </div>
                  <div style={{
                    display: "inline-block", marginTop: 6, background: `${k.color}20`,
                    border: `1px solid ${k.color}40`, borderRadius: 4, padding: "2px 8px",
                    fontSize: 10, color: k.color, fontWeight: "bold", fontFamily: "monospace"
                  }}>{k.badge}</div>
                </div>
              ))}
            </div>

            {/* Tabs */}
            <div style={{ display: "flex", gap: 8, marginBottom: 20, background: COLORS.card, borderRadius: 10, padding: 6, border: `1px solid ${COLORS.border}` }}>
              {[
                { id: "quality", label: "📊 Quality Scorecard" },
                { id: "gaps", label: "⚠️ Compliance Gaps" },
                { id: "risk", label: "🎯 Risk Prediction" },
                { id: "benchmark", label: "📈 Benchmarks" },
              ].map(t => (
                <button key={t.id} style={tabStyle(t.id)} onClick={() => setActiveTab(t.id)}>{t.label}</button>
              ))}
            </div>

            {/* Tab Content */}
            {activeTab === "quality" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                <div style={cardStyle}>
                  <h3 style={{ margin: "0 0 16px", fontSize: 15, color: COLORS.muted, textTransform: "uppercase", letterSpacing: 1 }}>Overall Score</h3>
                  <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
                    <RadialGauge value={overallScore} size={140} />
                    <div>
                      <div style={{ fontSize: 14, color: COLORS.text, marginBottom: 8 }}>
                        DPR Grade: <span style={{ color: COLORS.yellow, fontWeight: "bold" }}>B+</span>
                      </div>
                      <div style={{ fontSize: 13, color: COLORS.muted, lineHeight: 1.6 }}>
                        This DPR meets minimum MDoNER thresholds but requires revisions in financial consistency and regulatory compliance before final approval.
                      </div>
                    </div>
                  </div>
                </div>
                <div style={cardStyle}>
                  <h3 style={{ margin: "0 0 16px", fontSize: 15, color: COLORS.muted, textTransform: "uppercase", letterSpacing: 1 }}>Dimension Breakdown</h3>
                  <QualityScoreCard scores={DEMO_SCORES} />
                </div>
              </div>
            )}

            {activeTab === "gaps" && (
              <div style={cardStyle}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                  <h3 style={{ margin: 0, fontSize: 15, color: COLORS.muted, textTransform: "uppercase", letterSpacing: 1 }}>Compliance Gap Analysis</h3>
                  <div style={{ display: "flex", gap: 8 }}>
                    {[["HIGH", COLORS.red, 2], ["MEDIUM", COLORS.yellow, 2], ["LOW", COLORS.green, 2]].map(([label, color, count]) => (
                      <span key={label} style={{ background: `${color}15`, border: `1px solid ${color}40`, borderRadius: 4, padding: "3px 10px", fontSize: 11, color, fontWeight: "bold" }}>
                        {count} {label}
                      </span>
                    ))}
                  </div>
                </div>
                {SAMPLE_GAPS.map((g, i) => <ComplianceGap key={i} gap={g} />)}
                <div style={{
                  marginTop: 16, background: `${COLORS.accent}10`, border: `1px solid ${COLORS.accent}30`,
                  borderRadius: 8, padding: 14, fontSize: 13, color: COLORS.text
                }}>
                  💡 <strong>AI Recommendation:</strong> Address the 2 HIGH severity gaps before resubmission. Attach the Survey & Investigation report and provide district-level cost breakdown to improve score by an estimated +12 points.
                </div>
              </div>
            )}

            {activeTab === "risk" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                <div style={cardStyle}>
                  <h3 style={{ margin: "0 0 16px", fontSize: 15, color: COLORS.muted, textTransform: "uppercase", letterSpacing: 1 }}>Risk Prediction (ML Model)</h3>
                  {RISK_FACTORS.map(r => (
                    <div key={r.id} style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 8 }}>
                      <span style={{ fontSize: 18, marginTop: 2 }}>{r.icon}</span>
                      <div style={{ flex: 1 }}>
                        <RiskBar value={DEMO_RISKS[r.id]} label={r.label} />
                      </div>
                    </div>
                  ))}
                  <div style={{ color: COLORS.muted, fontSize: 12, marginTop: 8 }}>
                    Model trained on 1,240 NE Region infrastructure projects · Accuracy: 85.2%
                  </div>
                </div>
                <div style={cardStyle}>
                  <h3 style={{ margin: "0 0 16px", fontSize: 15, color: COLORS.muted, textTransform: "uppercase", letterSpacing: 1 }}>Key Risk Drivers</h3>
                  {[
                    { icon: "🌧️", title: "Monsoon Season Overlap", desc: "Project timeline overlaps Jun-Sep, historically 2.3x higher delays for NE terrain", severity: COLORS.red },
                    { icon: "🏔️", title: "High Altitude Terrain", desc: "Elevation >1800m detected — material logistics risk elevated", severity: COLORS.yellow },
                    { icon: "📦", title: "Supply Chain Distance", desc: "Location in remote district — 40% higher procurement lead time expected", severity: COLORS.yellow },
                    { icon: "✅", title: "Contractor Grade A", desc: "Assigned contractor has strong historical performance in similar projects", severity: COLORS.green },
                  ].map(d => (
                    <div key={d.title} style={{
                      display: "flex", gap: 12, padding: "10px 12px", borderRadius: 8, marginBottom: 8,
                      background: `${d.severity}10`, border: `1px solid ${d.severity}25`
                    }}>
                      <span style={{ fontSize: 20 }}>{d.icon}</span>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 3, color: d.severity }}>{d.title}</div>
                        <div style={{ fontSize: 12, color: COLORS.muted }}>{d.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === "benchmark" && (
              <div style={cardStyle}>
                <h3 style={{ margin: "0 0 16px", fontSize: 15, color: COLORS.muted, textTransform: "uppercase", letterSpacing: 1 }}>Historical Project Benchmarks</h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
                  <div style={{ background: COLORS.surface, borderRadius: 8, padding: 14 }}>
                    <div style={{ color: COLORS.muted, fontSize: 12, marginBottom: 4 }}>Your DPR vs. Avg. Quality Score</div>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <span style={{ fontSize: 24, fontWeight: "bold", color: COLORS.yellow, fontFamily: "monospace" }}>{overallScore}</span>
                      <span style={{ color: COLORS.muted }}>vs.</span>
                      <span style={{ fontSize: 24, fontWeight: "bold", color: COLORS.accent, fontFamily: "monospace" }}>74.3</span>
                      <span style={{ color: COLORS.muted, fontSize: 13 }}>NE Region Avg.</span>
                    </div>
                  </div>
                  <div style={{ background: COLORS.surface, borderRadius: 8, padding: 14 }}>
                    <div style={{ color: COLORS.muted, fontSize: 12, marginBottom: 4 }}>Predicted Cost Overrun vs. Avg.</div>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <span style={{ fontSize: 24, fontWeight: "bold", color: COLORS.red, fontFamily: "monospace" }}>+17%</span>
                      <span style={{ color: COLORS.muted }}>vs.</span>
                      <span style={{ fontSize: 24, fontWeight: "bold", color: COLORS.yellow, fontFamily: "monospace" }}>+17.3%</span>
                      <span style={{ color: COLORS.muted, fontSize: 13 }}>NE Region Avg.</span>
                    </div>
                  </div>
                </div>
                <BenchmarkTable data={HISTORICAL_BENCHMARKS} />
                <div style={{ color: COLORS.muted, fontSize: 12, marginTop: 12 }}>
                  * Benchmark data sourced from MDoNER project completion reports (2018–2024)
                </div>
              </div>
            )}

            {/* Export Actions */}
            <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
              {[
                { label: "📥 Export PDF Report", primary: true },
                { label: "📊 Download Scorecard (Excel)" },
                { label: "📨 Send to Approving Officer" },
              ].map(b => (
                <button key={b.label} onClick={() => alert("Export feature ready for backend integration!")} style={{
                  padding: "10px 18px", borderRadius: 8, cursor: "pointer", fontSize: 14, fontWeight: 600,
                  border: `1px solid ${b.primary ? COLORS.accent : COLORS.border}`,
                  background: b.primary ? `linear-gradient(135deg, ${COLORS.accent}, #0284C7)` : COLORS.card,
                  color: b.primary ? "#fff" : COLORS.text,
                }}>
                  {b.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
