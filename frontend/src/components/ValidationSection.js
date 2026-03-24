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

function ChartsPanel({ data }) {
  const pie = data.visualization_data?.feature_comparison_pie;
  const bars = data.visualization_data?.stacked_bar_data;
  const total = pie?.segments?.reduce((a, s) => a + s.value, 0) || 0;
  const pubPct = pie?.percentages?.Published || 0;

  return (
    <div className="obs-charts-grid">
      {pie && (
        <div className="obs-chart-card">
          <div className="obs-chart-title">Feature Distribution</div>
          <div className="obs-donut-wrap">
            <div className="obs-donut">
              <svg viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,71,87,0.3)" strokeWidth="16" />
                <circle cx="50" cy="50" r="40" fill="none" stroke="#00e88f" strokeWidth="16"
                  strokeDasharray={`${pubPct * 2.51} 251`} strokeLinecap="round" />
              </svg>
              <div className="obs-donut-center">
                <div className="obs-donut-num">{total}</div>
                <div className="obs-donut-sub">Total</div>
              </div>
            </div>
            <div className="obs-legend">
              {pie.segments.map((seg, i) => (
                <div key={i} className="obs-legend-item">
                  <div className="obs-legend-dot" style={{ background: seg.color }} />
                  <div className="obs-legend-name">{seg.label}</div>
                  <div className="obs-legend-val">{seg.value} ({pie.percentages?.[seg.label] || 0}%)</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {bars && bars.bars?.length > 0 && (
        <div className="obs-chart-card">
          <div className="obs-chart-title">Rules Passed / Failed</div>
          <div className="obs-stacked-bars">
            {bars.bars.map((bar, i) => (
              <div key={i} className="obs-stacked-row">
                <div className="obs-stacked-label" title={bar.feature}>{bar.feature}</div>
                <div className="obs-stacked-track">
                  <div className="obs-stacked-pass" style={{ width: `${(bar.passed / bar.total) * 100}%` }} />
                  <div className="obs-stacked-fail" style={{ width: `${(bar.failed / bar.total) * 100}%` }} />
                </div>
                <div className="obs-stacked-pct" style={{ color: bar.compliance >= 85 ? 'var(--obs-emerald)' : bar.compliance >= 70 ? 'var(--obs-amber)' : 'var(--obs-coral)' }}>
                  {bar.compliance}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Category scores as a full-width card */}
      {data.category_scores && Object.keys(data.category_scores).length > 0 && (
        <div className="obs-chart-card full-width">
          <div className="obs-chart-title">Category Compliance</div>
          <div className="obs-stacked-bars">
            {Object.entries(data.category_scores).map(([cat, score], i) => (
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
