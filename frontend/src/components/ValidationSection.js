import React, { useState } from 'react';
import '../validation-observatory.css';

const PANELS = [
  { id: 'overview', label: 'Overview' },
  { id: 'transformations', label: 'AI Transforms' },
  { id: 'geography', label: 'Geography' },
  { id: 'matrix', label: 'Matrix' },
  { id: 'features', label: 'Features' },
  { id: 'violations', label: 'Violations' },
  { id: 'integrity', label: 'Integrity' },
  { id: 'charts', label: 'Analytics' },
];

function scoreLevel(s) {
  if (s >= 85) return 'high';
  if (s >= 70) return 'mid';
  return 'low';
}

const GEO_META = {
  All: { flag: '\u{1F30D}', label: 'Global', accent: 'rgba(0,212,255,0.12)' },
  Global: { flag: '\u{1F30D}', label: 'Global', accent: 'rgba(0,212,255,0.12)' },
  India: { flag: '\u{1F1EE}\u{1F1F3}', label: 'India', accent: 'rgba(255,153,51,0.12)' },
  US: { flag: '\u{1F1FA}\u{1F1F8}', label: 'United States', accent: 'rgba(0,82,180,0.12)' },
};

/* ====== Sub-components ====== */

function ComplianceRing({ score }) {
  const circumference = 2 * Math.PI * 44;
  const dash = (score / 100) * circumference;
  const color = score >= 85 ? '#00e88f' : score >= 70 ? '#f0a030' : '#ff4757';

  return (
    <div className="obs-ring-card">
      <div className="obs-ring-wrap">
        <svg className="obs-ring-svg" viewBox="0 0 100 100">
          <circle className="obs-ring-track" cx="50" cy="50" r="44" />
          <circle
            className="obs-ring-value-circle"
            cx="50" cy="50" r="44"
            stroke={color}
            strokeDasharray={`${dash} ${circumference}`}
          />
        </svg>
        <div className="obs-ring-center">
          <span className="obs-ring-number">{Math.round(score)}</span>
          <span className="obs-ring-label">Compliance</span>
        </div>
      </div>
    </div>
  );
}

function StatTiles({ data }) {
  const integrityPassed = Object.values(data.data_integrity_checks || {}).filter(c => c.status).length;
  const integrityTotal = Object.keys(data.data_integrity_checks || {}).length;
  const totalViolations = data.feature_validations?.reduce((s, v) => s + (v.violations?.length || 0), 0) || 0;

  const tiles = [
    { icon: '\u{1F4CB}', num: data.total_features_extracted, label: 'Extracted', accent: 'var(--obs-cyan)' },
    { icon: '\u{2705}', num: data.features_published, label: 'Published', accent: 'var(--obs-emerald)' },
    { icon: '\u{1F6AB}', num: data.features_filtered, label: 'Filtered', accent: 'var(--obs-coral)' },
    { icon: '\u{1F6E1}\u{FE0F}', num: `${integrityPassed}/${integrityTotal}`, label: 'Integrity', accent: 'var(--obs-cyan)' },
    { icon: '\u{26A0}\u{FE0F}', num: totalViolations, label: 'Violations', accent: 'var(--obs-amber)' },
  ];

  return (
    <div className="obs-stat-grid">
      {tiles.map((t, i) => (
        <div key={i} className="obs-stat-tile" style={{ '--tile-accent': t.accent }}>
          <span className="obs-stat-icon" style={{ color: t.accent }}>{t.icon}</span>
          <div className="obs-stat-number">{t.num}</div>
          <div className="obs-stat-label">{t.label}</div>
        </div>
      ))}
    </div>
  );
}

function TransformationsPanel({ data }) {
  const comparisons = data.before_after_comparison?.comparisons || [];
  if (!comparisons.length) {
    return <div className="obs-empty"><div className="obs-empty-icon">{'\u{1F504}'}</div><h3>No Transformation Data</h3><p>Process a document to see before/after comparisons</p></div>;
  }

  return (
    <div className="obs-transformations">
      {comparisons.map((comp, i) => {
        const cs = comp.changes_summary || {};
        return (
          <div key={i} className="obs-transform-card">
            <div className="obs-transform-header">
              <div className="obs-transform-title">{comp.feature_name}</div>
              <div className="obs-transform-badges">
                {cs.sections_modified?.map((s, j) => <span key={j} className="obs-badge obs-badge--cyan">{s}</span>)}
                {cs.acronyms_bolded > 0 && <span className="obs-badge obs-badge--emerald">{cs.acronyms_bolded} acronyms bolded</span>}
                {cs.temporal_words_removed?.length > 0 && <span className="obs-badge obs-badge--coral">{cs.temporal_words_removed.length} temporal words</span>}
              </div>
            </div>
            <div className="obs-transform-body">
              <div className="obs-diff-pane obs-diff-before">
                <span className="obs-diff-label obs-diff-label--before">Original</span>
                {comp.before && (
                  <>
                    <div className="obs-diff-section">
                      <div className="obs-diff-section-title">Title</div>
                      {comp.before.title}
                    </div>
                    <div className="obs-diff-section">
                      <div className="obs-diff-section-title">Problem Statement</div>
                      {comp.before.problem_statement}
                    </div>
                    <div className="obs-diff-section">
                      <div className="obs-diff-section-title">Enhancement</div>
                      {comp.before.enhancement}
                    </div>
                    <div className="obs-diff-section">
                      <div className="obs-diff-section-title">Impact</div>
                      {comp.before.impact}
                    </div>
                  </>
                )}
              </div>
              <div className="obs-diff-arrow">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              </div>
              <div className="obs-diff-pane obs-diff-after">
                <span className="obs-diff-label obs-diff-label--after">AI Refined</span>
                {comp.after && (
                  <>
                    <div className="obs-diff-section">
                      <div className="obs-diff-section-title">Title</div>
                      {comp.after.title}
                    </div>
                    <div className="obs-diff-section">
                      <div className="obs-diff-section-title">Description</div>
                      {comp.after.description}
                    </div>
                    <div className="obs-diff-section">
                      <div className="obs-diff-section-title">Problem Statement</div>
                      {comp.after.problem_statement}
                    </div>
                    <div className="obs-diff-section">
                      <div className="obs-diff-section-title">Enhancement</div>
                      {comp.after.enhancement}
                    </div>
                    <div className="obs-diff-section">
                      <div className="obs-diff-section-title">Impact</div>
                      {comp.after.impact}
                    </div>
                  </>
                )}
              </div>
            </div>
            <div className="obs-transform-stats">
              <div className="obs-transform-stat"><span className="num">{cs.words_before || 0}</span> words before</div>
              <div className="obs-transform-stat"><span className="num">{cs.words_after || 0}</span> words after</div>
              <div className="obs-transform-stat"><span className="num">{cs.sections_modified?.length || 0}</span> sections modified</div>
              <div className="obs-transform-stat"><span className="num">{cs.acronyms_bolded || 0}</span> acronyms enforced</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function GeographyPanel({ data }) {
  const vizGeo = data.visualization_data?.geography_distribution || {};
  const counts = vizGeo.counts || data.geography_distribution || {};
  const featuresByGeo = vizGeo.features_by_geography || {};
  const maxCount = Math.max(...Object.values(counts), 1);

  if (!Object.keys(counts).length) {
    return <div className="obs-empty"><div className="obs-empty-icon">{'\u{1F30D}'}</div><h3>No Geography Data</h3><p>Process a document to see distribution</p></div>;
  }

  return (
    <div className="obs-geo-grid">
      {Object.entries(counts).map(([region, count]) => {
        const meta = GEO_META[region] || { flag: '\u{1F310}', label: region, accent: 'rgba(0,212,255,0.12)' };
        const features = featuresByGeo[region] || [];
        return (
          <div key={region} className="obs-geo-card" style={{ '--geo-accent': meta.accent }}>
            <div className="obs-geo-flag">{meta.flag}</div>
            <div className="obs-geo-name">{meta.label}</div>
            <div className="obs-geo-count">{count}</div>
            <div className="obs-geo-sublabel">Features</div>
            <div className="obs-geo-bar">
              <div className="obs-geo-bar-fill" style={{ width: `${(count / maxCount) * 100}%` }} />
            </div>
            {features.length > 0 && (
              <div className="obs-geo-features">
                {features.map((f, j) => <div key={j} className="obs-geo-feature-item" title={f}>{f}</div>)}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function MatrixPanel({ data }) {
  const heatmap = data.visualization_data?.compliance_heatmap;
  if (!heatmap?.data?.length) {
    return <div className="obs-empty"><div className="obs-empty-icon">{'\u{1F9EE}'}</div><h3>No Matrix Data</h3><p>Process a document to see the compliance matrix</p></div>;
  }

  return (
    <div className="obs-matrix">
      <table className="obs-matrix-table">
        <thead>
          <tr>
            <th className="obs-matrix-th">Feature</th>
            {heatmap.categories.map((c, i) => <th key={i} className="obs-matrix-th">{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {heatmap.data.map((row, i) => (
            <tr key={i}>
              <td className="obs-matrix-feature" title={row.feature}>{row.feature}</td>
              {heatmap.categories.map((cat, j) => {
                const val = row.scores?.[cat] ?? 100;
                return (
                  <td key={j} className="obs-matrix-cell" data-level={scoreLevel(val)}>
                    {Math.round(val)}%
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FeaturesPanel({ data }) {
  const [expanded, setExpanded] = useState(null);
  const validations = data.feature_validations || [];
  if (!validations.length) {
    return <div className="obs-empty"><div className="obs-empty-icon">{'\u{1F4CA}'}</div><h3>No Feature Data</h3><p>Process a document to see feature compliance</p></div>;
  }

  return (
    <div className="obs-features-list">
      {validations.map((v, i) => {
        const level = scoreLevel(v.compliance_score);
        const isOpen = expanded === i;
        return (
          <div key={i} className={`obs-feature-row ${isOpen ? 'expanded' : ''}`} onClick={() => setExpanded(isOpen ? null : i)}>
            <div>
              <div className="obs-feature-name">{v.feature_name}</div>
              <div className="obs-feature-bar-track">
                <div className="obs-feature-bar-fill" data-level={level} style={{ width: `${v.compliance_score}%` }} />
              </div>
            </div>
            <div className="obs-feature-score" data-level={level}>{Math.round(v.compliance_score)}%</div>
            {isOpen && (
              <div className="obs-feature-detail">
                {v.violations?.length > 0 && (
                  <div className="obs-feature-violations">
                    {v.violations.map((viol, j) => <div key={j} className="obs-violation-line">{viol}</div>)}
                  </div>
                )}
                {v.category_scores && (
                  <div className="obs-feature-cats">
                    {Object.entries(v.category_scores).map(([cat, score]) => (
                      <span key={cat} className="obs-cat-chip" style={{
                        color: score >= 85 ? 'var(--obs-emerald)' : score >= 70 ? 'var(--obs-amber)' : 'var(--obs-coral)',
                        background: score >= 85 ? 'rgba(0,232,143,0.1)' : score >= 70 ? 'rgba(240,160,48,0.1)' : 'rgba(255,71,87,0.1)',
                        border: `1px solid ${score >= 85 ? 'rgba(0,232,143,0.3)' : score >= 70 ? 'rgba(240,160,48,0.3)' : 'rgba(255,71,87,0.3)'}`,
                      }}>{cat}: {Math.round(score)}%</span>
                    ))}
                  </div>
                )}
                {v.acronyms_found?.length > 0 && (
                  <div className="obs-feature-cats" style={{ marginTop: 6 }}>
                    {v.acronyms_found.map((a, j) => (
                      <span key={j} className="obs-badge" style={{
                        color: a.status === 'bolded' ? 'var(--obs-emerald)' : 'var(--obs-coral)',
                        borderColor: a.status === 'bolded' ? 'rgba(0,232,143,0.3)' : 'rgba(255,71,87,0.3)',
                        background: a.status === 'bolded' ? 'rgba(0,232,143,0.08)' : 'rgba(255,71,87,0.08)',
                      }}>{a.acronym} {a.status === 'bolded' ? '\u2713' : '\u2717'}</span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ViolationsPanel({ data }) {
  const vizChart = data.visualization_data?.rubric_violations_chart || {};
  const violations = data.rubric_violations || [];

  return (
    <div className="obs-violations-panel">
      {vizChart.categories?.length > 0 && (
        <div className="obs-violations-summary">
          {vizChart.categories.map((cat, i) => (
            <div key={i} className="obs-viol-cat-card">
              <div className="obs-viol-count">{vizChart.counts?.[i] || 0}</div>
              <div className="obs-viol-cat-name">{cat}</div>
            </div>
          ))}
          <div className="obs-viol-cat-card">
            <div className="obs-viol-count" style={{ color: 'var(--obs-magenta)' }}>{vizChart.total_violations || 0}</div>
            <div className="obs-viol-cat-name">Total</div>
          </div>
        </div>
      )}
      {violations.length > 0 ? (
        <div className="obs-violations-feed">
          {violations.map((v, i) => {
            const match = v.match(/^\[(.+?)\]\s*(.+)$/);
            return (
              <div key={i} className="obs-viol-item" style={{ '--i': i }}>
                <div className="obs-viol-dot" />
                <div className="obs-viol-text">
                  {match ? <><span className="obs-viol-feature">{match[1]}</span> &mdash; {match[2]}</> : v}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="obs-empty"><div className="obs-empty-icon">{'\u2705'}</div><h3>No Violations</h3><p>All features passed compliance checks</p></div>
      )}
    </div>
  );
}

function IntegrityPanel({ data }) {
  const checks = data.data_integrity_checks || {};
  return (
    <div className="obs-integrity-grid">
      {Object.entries(checks).map(([key, check]) => (
        <div key={key} className="obs-integrity-check">
          <div className={`obs-integrity-indicator ${check.status ? 'pass' : 'fail'}`}>
            {check.status ? '\u2713' : '\u2717'}
          </div>
          <div className="obs-integrity-label">{check.label || key.replace(/_/g, ' ')}</div>
        </div>
      ))}
    </div>
  );
}

/* ====== Analytics — Creative Insights Dashboard ====== */

function RadarChart({ categories, scores }) {
  const n = categories.length;
  if (n < 3) return null;
  const cx = 120, cy = 120, R = 90;
  const angleStep = (2 * Math.PI) / n;
  const colors = ['#00d4ff', '#ff2d78', '#00e88f', '#f0a030', '#a855f7', '#ff6b6b'];

  const pointAt = (i, r) => {
    const angle = -Math.PI / 2 + i * angleStep;
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
  };

  const gridLevels = [0.25, 0.5, 0.75, 1.0];
  const dataPoints = categories.map((_, i) => pointAt(i, (scores[i] / 100) * R));
  const dataPath = dataPoints.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ') + ' Z';

  return (
    <svg viewBox="0 0 240 240" style={{ width: '100%', maxWidth: 280, margin: '0 auto', display: 'block', filter: 'drop-shadow(0 0 20px rgba(0,212,255,0.15))' }}>
      {gridLevels.map((level, li) => (
        <polygon key={li} points={categories.map((_, i) => pointAt(i, R * level).join(',')).join(' ')}
          fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
      ))}
      {categories.map((_, i) => {
        const [x, y] = pointAt(i, R);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="rgba(255,255,255,0.08)" strokeWidth="1" />;
      })}
      <polygon points={dataPath.replace(/[MLZ]/g, (m) => m === 'Z' ? '' : '').replace(/,/g, ',').trim()}
        fill="url(#radarGrad)" stroke="#00d4ff" strokeWidth="2" style={{ filter: 'drop-shadow(0 0 8px rgba(0,212,255,0.4))' }}>
        <animate attributeName="opacity" from="0" to="1" dur="0.8s" fill="freeze" />
      </polygon>
      <defs>
        <linearGradient id="radarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="rgba(0,212,255,0.25)" />
          <stop offset="100%" stopColor="rgba(255,45,120,0.15)" />
        </linearGradient>
      </defs>
      {dataPoints.map(([x, y], i) => (
        <g key={i}>
          <circle cx={x} cy={y} r="4" fill={colors[i % colors.length]} stroke="#fff" strokeWidth="1.5">
            <animate attributeName="r" from="0" to="4" dur="0.5s" begin={`${i * 0.1}s`} fill="freeze" />
          </circle>
        </g>
      ))}
      {categories.map((cat, i) => {
        const [x, y] = pointAt(i, R + 22);
        return <text key={i} x={x} y={y} textAnchor="middle" dominantBaseline="middle"
          fill={colors[i % colors.length]} fontSize="8" fontWeight="600" fontFamily="'DM Sans', sans-serif">{cat.split(' ')[0]}</text>;
      })}
    </svg>
  );
}

function GeoMapVisual({ geoCounts, geoSegregation }) {
  const regions = {
    India: { x: 540, y: 200, r: 22, color: '#ff9933', glow: 'rgba(255,153,51,0.5)', flag: '\u{1F1EE}\u{1F1F3}' },
    US: { x: 160, y: 160, r: 22, color: '#3b82f6', glow: 'rgba(59,130,246,0.5)', flag: '\u{1F1FA}\u{1F1F8}' },
    All: { x: 350, y: 120, r: 28, color: '#00e88f', glow: 'rgba(0,232,143,0.5)', flag: '\u{1F30D}' },
    Global: { x: 350, y: 120, r: 28, color: '#00e88f', glow: 'rgba(0,232,143,0.5)', flag: '\u{1F30D}' },
  };
  const counts = geoCounts || {};
  const segregation = geoSegregation || {};

  return (
    <div style={{ position: 'relative', background: 'linear-gradient(135deg, rgba(10,5,30,0.9), rgba(20,10,50,0.9))', borderRadius: 16, padding: '24px 16px', border: '1px solid rgba(0,212,255,0.15)' }}>
      <svg viewBox="0 0 700 350" style={{ width: '100%', opacity: 0.12 }}>
        <ellipse cx="350" cy="175" rx="320" ry="150" fill="none" stroke="#00d4ff" strokeWidth="0.5" strokeDasharray="4 4" />
        <ellipse cx="350" cy="175" rx="240" ry="110" fill="none" stroke="#a855f7" strokeWidth="0.3" strokeDasharray="3 3" />
        <path d="M80,160 Q120,80 200,100 Q280,60 350,90 Q420,60 500,100 Q580,80 620,160 Q640,220 580,270 Q500,320 400,310 Q300,320 200,280 Q120,250 80,160Z" fill="rgba(0,212,255,0.03)" stroke="rgba(0,212,255,0.08)" strokeWidth="1" />
        <path d="M130,150 Q160,120 200,130 Q240,110 270,140 Q260,180 230,190 Q180,200 150,180Z" fill="rgba(59,130,246,0.06)" stroke="rgba(59,130,246,0.12)" strokeWidth="0.8" />
        <path d="M500,160 Q520,130 560,150 Q580,180 570,220 Q540,250 510,240 Q490,210 500,160Z" fill="rgba(255,153,51,0.06)" stroke="rgba(255,153,51,0.12)" strokeWidth="0.8" />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', justifyContent: 'center', alignItems: 'center', flexWrap: 'wrap', gap: 16, padding: 24 }}>
        {Object.entries(counts).map(([geo, count]) => {
          const r = regions[geo] || regions.All;
          const segFeatures = segregation[geo] || [];
          return (
            <div key={geo} style={{
              background: `linear-gradient(135deg, ${r.color}15, ${r.color}08)`,
              border: `1.5px solid ${r.color}40`,
              borderRadius: 16, padding: '20px 24px', minWidth: 180,
              boxShadow: `0 0 30px ${r.glow}, inset 0 1px 0 rgba(255,255,255,0.05)`,
              transition: 'transform 0.3s, box-shadow 0.3s', cursor: 'default',
            }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-4px) scale(1.02)'; e.currentTarget.style.boxShadow = `0 0 50px ${r.glow}`; }}
            onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = `0 0 30px ${r.glow}`; }}
            >
              <div style={{ fontSize: 28, marginBottom: 4 }}>{r.flag}</div>
              <div style={{ fontSize: 13, color: r.color, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase' }}>{geo}</div>
              <div style={{ fontSize: 36, fontWeight: 800, color: '#fff', fontFamily: "'Space Mono', monospace", lineHeight: 1.1 }}>{count}</div>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', marginBottom: 8 }}>features</div>
              {segFeatures.length > 0 && (
                <div style={{ borderTop: `1px solid ${r.color}25`, paddingTop: 8, marginTop: 4 }}>
                  {segFeatures.slice(0, 4).map((f, i) => (
                    <div key={i} style={{ fontSize: 10, color: 'rgba(255,255,255,0.6)', padding: '2px 0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 200 }} title={f}>
                      {'\u2022'} {f}
                    </div>
                  ))}
                  {segFeatures.length > 4 && <div style={{ fontSize: 10, color: r.color }}>+{segFeatures.length - 4} more</div>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AnimatedGauge({ value, label, color, max = 100 }) {
  const pct = Math.min(value / max, 1);
  const dashLen = pct * 188;
  return (
    <div style={{ textAlign: 'center' }}>
      <svg viewBox="0 0 80 50" style={{ width: 120 }}>
        <path d="M10,45 A30,30 0 0,1 70,45" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" strokeLinecap="round" />
        <path d="M10,45 A30,30 0 0,1 70,45" fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={`${dashLen} 188`} style={{ filter: `drop-shadow(0 0 6px ${color})`, transition: 'stroke-dasharray 1.2s cubic-bezier(0.4,0,0.2,1)' }}>
          <animate attributeName="stroke-dasharray" from="0 188" to={`${dashLen} 188`} dur="1.2s" fill="freeze" />
        </path>
        <text x="40" y="42" textAnchor="middle" fill="#fff" fontSize="14" fontWeight="800" fontFamily="'Space Mono', monospace">{Math.round(value)}</text>
      </svg>
      <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)', marginTop: -4, fontWeight: 600 }}>{label}</div>
    </div>
  );
}

function BubbleChart({ validations }) {
  if (!validations?.length) return null;
  const maxScore = 100;
  const colors = ['#00d4ff', '#ff2d78', '#00e88f', '#f0a030', '#a855f7', '#ff6b6b', '#38bdf8', '#fb923c'];

  return (
    <svg viewBox="0 0 500 200" style={{ width: '100%', overflow: 'visible' }}>
      {validations.map((v, i) => {
        const score = v.compliance_score || 0;
        const r = 12 + (score / 100) * 25;
        const x = 40 + (i / Math.max(validations.length - 1, 1)) * 420;
        const y = 100 - (score / maxScore) * 60 + 20;
        const c = colors[i % colors.length];
        return (
          <g key={i}>
            <circle cx={x} cy={y} r={r} fill={`${c}20`} stroke={c} strokeWidth="1.5"
              style={{ filter: `drop-shadow(0 0 10px ${c}40)`, cursor: 'default', transition: 'all 0.3s' }}>
              <animate attributeName="r" from="0" to={r} dur="0.6s" begin={`${i * 0.08}s`} fill="freeze" />
              <animate attributeName="opacity" from="0" to="1" dur="0.4s" begin={`${i * 0.08}s`} fill="freeze" />
            </circle>
            <text x={x} y={y + 1} textAnchor="middle" dominantBaseline="middle" fill="#fff" fontSize="9" fontWeight="700"
              fontFamily="'Space Mono', monospace">{Math.round(score)}%</text>
            <text x={x} y={y + r + 14} textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="7"
              fontFamily="'DM Sans', sans-serif">{(v.feature_name || '').substring(0, 18)}</text>
          </g>
        );
      })}
      <line x1="20" y1="170" x2="480" y2="170" stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
    </svg>
  );
}

function MiniSparkline({ values, color, label }) {
  if (!values?.length) return null;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const w = 120, h = 40, pad = 4;
  const points = values.map((v, i) => {
    const x = pad + (i / Math.max(values.length - 1, 1)) * (w - 2 * pad);
    const y = h - pad - ((v - min) / range) * (h - 2 * pad);
    return `${x},${y}`;
  }).join(' ');
  const areaPoints = `${pad},${h - pad} ${points} ${w - pad},${h - pad}`;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: 120, height: 40, flexShrink: 0 }}>
        <polygon points={areaPoints} fill={`${color}15`} />
        <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 4px ${color})` }} />
        {values.map((v, i) => {
          const x = pad + (i / Math.max(values.length - 1, 1)) * (w - 2 * pad);
          const y = h - pad - ((v - min) / range) * (h - 2 * pad);
          return <circle key={i} cx={x} cy={y} r="2.5" fill={color} stroke="#fff" strokeWidth="0.5" />;
        })}
      </svg>
      <div>
        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>{label}</div>
        <div style={{ fontSize: 16, fontWeight: 800, color, fontFamily: "'Space Mono', monospace" }}>{values[values.length - 1]}%</div>
      </div>
    </div>
  );
}

function ChartsPanel({ data }) {
  const pie = data.visualization_data?.feature_comparison_pie;
  const bars = data.visualization_data?.stacked_bar_data;
  const catScores = data.category_scores || {};
  const validations = data.feature_validations || [];
  const vizGeo = data.visualization_data?.geography_distribution || {};
  const geoCounts = vizGeo.counts || data.geography_distribution || {};
  const geoSegregation = vizGeo.geography_segregation || {};
  const total = pie?.segments?.reduce((a, s) => a + s.value, 0) || 0;
  const pubPct = pie?.percentages?.Published || 0;
  const filtPct = pie?.percentages?.Filtered || 0;

  const catNames = Object.keys(catScores);
  const catVals = Object.values(catScores);
  const complianceScores = validations.map(v => Math.round(v.compliance_score || 0));
  const totalAcronyms = validations.reduce((s, v) => s + (v.acronyms_found?.filter(a => a.status === 'bolded').length || 0), 0);
  const totalViolations = validations.reduce((s, v) => s + (v.violations?.length || 0), 0);
  const avgScore = complianceScores.length ? Math.round(complianceScores.reduce((a, b) => a + b, 0) / complianceScores.length) : 0;
  const bestFeature = validations.length ? validations.reduce((a, b) => (a.compliance_score > b.compliance_score ? a : b)) : null;
  const worstFeature = validations.length ? validations.reduce((a, b) => (a.compliance_score < b.compliance_score ? a : b)) : null;

  const cardStyle = {
    background: 'linear-gradient(135deg, rgba(15,8,32,0.95), rgba(25,14,50,0.9))',
    border: '1px solid rgba(0,212,255,0.12)',
    borderRadius: 16, padding: 24,
    backdropFilter: 'blur(12px)',
    transition: 'border-color 0.3s, box-shadow 0.3s',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, animation: 'obs-fadeUp 0.5s ease-out' }}>

      {/* Row 1: Gauges */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 14 }}>
        <AnimatedGauge value={avgScore} label="Avg Compliance" color="#00d4ff" />
        <AnimatedGauge value={pubPct} label="Published %" color="#00e88f" />
        <AnimatedGauge value={totalAcronyms} label="Acronyms Fixed" color="#a855f7" max={Math.max(totalAcronyms, 1)} />
        <AnimatedGauge value={100 - (totalViolations / Math.max(validations.length * 10, 1)) * 100} label="Quality Index" color="#ff2d78" />
      </div>

      {/* Row 2: Donut + Radar side by side */}
      <div style={{ display: 'grid', gridTemplateColumns: window.innerWidth > 768 ? '1fr 1fr' : '1fr', gap: 16 }}>
        {/* Donut */}
        {pie && (
          <div style={cardStyle}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.7)', marginBottom: 16, letterSpacing: 1, textTransform: 'uppercase' }}>Feature Distribution</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 24, justifyContent: 'center', flexWrap: 'wrap' }}>
              <div style={{ position: 'relative', width: 140, height: 140 }}>
                <svg viewBox="0 0 100 100" style={{ width: '100%', transform: 'rotate(-90deg)' }}>
                  <circle cx="50" cy="50" r="38" fill="none" stroke="rgba(255,71,87,0.2)" strokeWidth="14" />
                  <circle cx="50" cy="50" r="38" fill="none" stroke="url(#donutGrad)" strokeWidth="14"
                    strokeDasharray={`${pubPct * 2.39} 239`} strokeLinecap="round"
                    style={{ filter: 'drop-shadow(0 0 8px rgba(0,232,143,0.4))', transition: 'stroke-dasharray 1s ease' }}>
                    <animate attributeName="stroke-dasharray" from="0 239" to={`${pubPct * 2.39} 239`} dur="1s" fill="freeze" />
                  </circle>
                  <defs>
                    <linearGradient id="donutGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#00e88f" />
                      <stop offset="100%" stopColor="#00d4ff" />
                    </linearGradient>
                  </defs>
                </svg>
                <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
                  <div style={{ fontSize: 28, fontWeight: 900, color: '#fff', fontFamily: "'Space Mono', monospace" }}>{total}</div>
                  <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: 1 }}>Total</div>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'linear-gradient(135deg, #00e88f, #00d4ff)', boxShadow: '0 0 8px rgba(0,232,143,0.5)' }} />
                  <span style={{ fontSize: 12, color: '#fff' }}>Published</span>
                  <span style={{ fontSize: 14, fontWeight: 800, color: '#00e88f', fontFamily: "'Space Mono', monospace", marginLeft: 4 }}>{pie?.segments?.[0]?.value || 0}</span>
                  <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>({pubPct}%)</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#ff4757', boxShadow: '0 0 8px rgba(255,71,87,0.4)' }} />
                  <span style={{ fontSize: 12, color: '#fff' }}>Filtered</span>
                  <span style={{ fontSize: 14, fontWeight: 800, color: '#ff4757', fontFamily: "'Space Mono', monospace", marginLeft: 4 }}>{pie?.segments?.[1]?.value || 0}</span>
                  <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>({filtPct}%)</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Radar */}
        {catNames.length >= 3 && (
          <div style={cardStyle}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.7)', marginBottom: 16, letterSpacing: 1, textTransform: 'uppercase' }}>Category Radar</div>
            <RadarChart categories={catNames} scores={catVals} />
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'center', marginTop: 12 }}>
              {catNames.map((cat, i) => {
                const colors = ['#00d4ff', '#ff2d78', '#00e88f', '#f0a030', '#a855f7', '#ff6b6b'];
                const c = colors[i % colors.length];
                return (
                  <span key={i} style={{ fontSize: 10, padding: '3px 10px', borderRadius: 20, border: `1px solid ${c}40`, color: c, background: `${c}10` }}>
                    {cat}: {Math.round(catVals[i])}%
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Row 3: Geography Map */}
      {Object.keys(geoCounts).length > 0 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.7)', marginBottom: 12, letterSpacing: 1, textTransform: 'uppercase' }}>Geography Intelligence</div>
          <GeoMapVisual geoCounts={geoCounts} geoSegregation={geoSegregation} />
        </div>
      )}

      {/* Row 4: Bubble scatter + Sparkline */}
      <div style={{ display: 'grid', gridTemplateColumns: window.innerWidth > 768 ? '2fr 1fr' : '1fr', gap: 16 }}>
        {validations.length > 0 && (
          <div style={cardStyle}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.7)', marginBottom: 16, letterSpacing: 1, textTransform: 'uppercase' }}>Compliance Bubble Map</div>
            <BubbleChart validations={validations} />
          </div>
        )}
        <div style={{ ...cardStyle, display: 'flex', flexDirection: 'column', gap: 16, justifyContent: 'center' }}>
          <MiniSparkline values={complianceScores} color="#00d4ff" label="Compliance Trend" />
          {bestFeature && (
            <div style={{ padding: '10px 14px', background: 'rgba(0,232,143,0.06)', borderRadius: 10, border: '1px solid rgba(0,232,143,0.15)' }}>
              <div style={{ fontSize: 9, color: '#00e88f', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>Best Performer</div>
              <div style={{ fontSize: 12, color: '#fff', marginTop: 3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{bestFeature.feature_name}</div>
              <div style={{ fontSize: 18, fontWeight: 900, color: '#00e88f', fontFamily: "'Space Mono', monospace" }}>{Math.round(bestFeature.compliance_score)}%</div>
            </div>
          )}
          {worstFeature && worstFeature !== bestFeature && (
            <div style={{ padding: '10px 14px', background: 'rgba(255,71,87,0.06)', borderRadius: 10, border: '1px solid rgba(255,71,87,0.15)' }}>
              <div style={{ fontSize: 9, color: '#ff4757', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>Needs Attention</div>
              <div style={{ fontSize: 12, color: '#fff', marginTop: 3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{worstFeature.feature_name}</div>
              <div style={{ fontSize: 18, fontWeight: 900, color: '#ff4757', fontFamily: "'Space Mono', monospace" }}>{Math.round(worstFeature.compliance_score)}%</div>
            </div>
          )}
        </div>
      </div>

      {/* Row 5: Stacked bars with animated fills */}
      {bars && bars.bars?.length > 0 && (
        <div style={cardStyle}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.7)', marginBottom: 16, letterSpacing: 1, textTransform: 'uppercase' }}>Rules Passed vs Failed</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {bars.bars.map((bar, i) => {
              const passPct = (bar.passed / bar.total) * 100;
              const failPct = (bar.failed / bar.total) * 100;
              const scoreColor = bar.compliance >= 85 ? '#00e88f' : bar.compliance >= 70 ? '#f0a030' : '#ff4757';
              return (
                <div key={i} style={{ display: 'grid', gridTemplateColumns: '140px 1fr 50px', alignItems: 'center', gap: 12 }}>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.6)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={bar.feature}>{bar.feature}</div>
                  <div style={{ height: 20, borderRadius: 10, overflow: 'hidden', display: 'flex', background: 'rgba(255,255,255,0.04)' }}>
                    <div style={{
                      width: `${passPct}%`, background: `linear-gradient(90deg, #00e88f, #00d4ff)`,
                      borderRadius: '10px 0 0 10px', transition: 'width 1s cubic-bezier(0.4,0,0.2,1)',
                      boxShadow: '0 0 12px rgba(0,232,143,0.3)',
                    }} />
                    <div style={{
                      width: `${failPct}%`, background: `linear-gradient(90deg, #ff4757, #ff2d78)`,
                      borderRadius: '0 10px 10px 0', transition: 'width 1s cubic-bezier(0.4,0,0.2,1)',
                      boxShadow: '0 0 12px rgba(255,71,87,0.3)',
                    }} />
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 800, color: scoreColor, fontFamily: "'Space Mono', monospace", textAlign: 'right' }}>{bar.compliance}%</div>
                </div>
              );
            })}
          </div>
          <div style={{ display: 'flex', gap: 16, marginTop: 14, justifyContent: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ width: 20, height: 8, borderRadius: 4, background: 'linear-gradient(90deg, #00e88f, #00d4ff)' }} />
              <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>Passed</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ width: 20, height: 8, borderRadius: 4, background: 'linear-gradient(90deg, #ff4757, #ff2d78)' }} />
              <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>Failed</span>
            </div>
          </div>
        </div>
      )}

      {/* Row 6: AI Insights summary */}
      <div style={{
        ...cardStyle,
        background: 'linear-gradient(135deg, rgba(0,212,255,0.05), rgba(168,85,247,0.05), rgba(255,45,120,0.05))',
        border: '1px solid rgba(168,85,247,0.2)',
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.7)', marginBottom: 14, letterSpacing: 1, textTransform: 'uppercase' }}>AI Processing Insights</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
          {[
            { label: 'Features Processed', value: validations.length, icon: '\u{1F9E0}', color: '#00d4ff' },
            { label: 'Acronyms Enforced', value: totalAcronyms, icon: '\u{1F520}', color: '#a855f7' },
            { label: 'Violations Detected', value: totalViolations, icon: '\u{26A0}\u{FE0F}', color: '#ff4757' },
            { label: 'Avg Compliance', value: `${avgScore}%`, icon: '\u{1F3AF}', color: '#00e88f' },
            { label: 'Best Score', value: bestFeature ? `${Math.round(bestFeature.compliance_score)}%` : 'N/A', icon: '\u{1F3C6}', color: '#f0a030' },
            { label: 'Geographies', value: Object.keys(geoCounts).length, icon: '\u{1F30D}', color: '#3b82f6' },
          ].map((item, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px',
              background: `${item.color}08`, borderRadius: 12, border: `1px solid ${item.color}20`,
              transition: 'transform 0.2s, background 0.2s', cursor: 'default',
            }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.03)'; e.currentTarget.style.background = `${item.color}14`; }}
            onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.background = `${item.color}08`; }}
            >
              <span style={{ fontSize: 22 }}>{item.icon}</span>
              <div>
                <div style={{ fontSize: 20, fontWeight: 900, color: item.color, fontFamily: "'Space Mono', monospace", lineHeight: 1 }}>{item.value}</div>
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.45)' }}>{item.label}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ====== Overview — combines key visuals on one screen ====== */
function OverviewPanel({ data }) {
  const vizChart = data.visualization_data?.rubric_violations_chart || {};
  const catScores = data.category_scores || {};
  const comparisons = data.before_after_comparison?.comparisons || [];
  const totalAcronyms = data.feature_validations?.reduce((s, v) => s + (v.acronyms_found?.filter(a => a.status === 'bolded').length || 0), 0) || 0;
  const totalTemporalRemoved = data.feature_validations?.reduce((s, v) => s + (v.temporal_words_found?.length || 0), 0) || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28, animation: 'obs-fadeUp 0.5s ease-out' }}>
      {/* Quick insights row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14 }}>
        {[
          { label: 'Acronyms Enforced', value: totalAcronyms, color: 'var(--obs-emerald)' },
          { label: 'Temporal Words Found', value: totalTemporalRemoved, color: 'var(--obs-amber)' },
          { label: 'Sections Modified', value: comparisons.reduce((s, c) => s + (c.changes_summary?.sections_modified?.length || 0), 0), color: 'var(--obs-cyan)' },
          { label: 'Total Violations', value: vizChart.total_violations || 0, color: 'var(--obs-coral)' },
        ].map((item, i) => (
          <div key={i} className="obs-stat-tile" style={{ '--tile-accent': item.color }}>
            <div className="obs-stat-number" style={{ color: item.color }}>{item.value}</div>
            <div className="obs-stat-label">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Category compliance bars */}
      {Object.keys(catScores).length > 0 && (
        <div className="obs-chart-card">
          <div className="obs-chart-title">Category Compliance</div>
          <div className="obs-stacked-bars">
            {Object.entries(catScores).map(([cat, score], i) => (
              <div key={i} className="obs-stacked-row">
                <div className="obs-stacked-label">{cat}</div>
                <div className="obs-stacked-track">
                  <div className="obs-stacked-pass" style={{ width: `${score}%`, background: score >= 85 ? 'var(--obs-emerald)' : score >= 70 ? 'var(--obs-amber)' : 'var(--obs-coral)' }} />
                </div>
                <div className="obs-stacked-pct" style={{ color: score >= 85 ? 'var(--obs-emerald)' : score >= 70 ? 'var(--obs-amber)' : 'var(--obs-coral)' }}>
                  {Math.round(score)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Integrity mini-row */}
      <IntegrityPanel data={data} />

      {/* First comparison preview */}
      {comparisons.length > 0 && (
        <div>
          <div className="obs-section-title"><span className="obs-accent" /> AI Transformation Preview</div>
          <TransformationsPanel data={{ ...data, before_after_comparison: { comparisons: comparisons.slice(0, 2) } }} />
        </div>
      )}
    </div>
  );
}

/* ====== Main Export ====== */
export default function ValidationSection({ validationData, files, onTabChange }) {
  const [panel, setPanel] = useState('overview');

  if (!validationData) {
    return (
      <div className="observatory">
        <div className="obs-empty">
          <div className="obs-empty-icon">{'\u{1F52C}'}</div>
          <h3>No Validation Data</h3>
          <p>Upload and process a document to see validation details</p>
          {onTabChange && <button className="gradient-button" onClick={() => onTabChange('upload')} style={{ marginTop: 20 }}><span className="gradient-text">Go to Upload</span></button>}
        </div>
      </div>
    );
  }

  const panelContent = {
    overview: <OverviewPanel data={validationData} />,
    transformations: <TransformationsPanel data={validationData} />,
    geography: <GeographyPanel data={validationData} />,
    matrix: <MatrixPanel data={validationData} />,
    features: <FeaturesPanel data={validationData} />,
    violations: <ViolationsPanel data={validationData} />,
    integrity: <IntegrityPanel data={validationData} />,
    charts: <ChartsPanel data={validationData} />,
  };

  return (
    <div className="observatory">
      {/* Hero */}
      <div className="obs-hero">
        <ComplianceRing score={validationData.overall_compliance_score || 0} />
        <StatTiles data={validationData} />
      </div>

      {/* Navigation */}
      <nav className="obs-nav">
        {PANELS.map(p => (
          <button key={p.id} className={`obs-nav-btn ${panel === p.id ? 'active' : ''}`} onClick={() => setPanel(p.id)}>
            {p.label}
          </button>
        ))}
      </nav>

      {/* Active Panel */}
      <div>
        <div className="obs-section-title"><span className="obs-accent" /> {PANELS.find(p => p.id === panel)?.label}</div>
        {panelContent[panel]}
      </div>
    </div>
  );
}
