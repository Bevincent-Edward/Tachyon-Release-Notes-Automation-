import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import './App.css';
import './section-styles.css';
import './comprehensive-fixes.css';
import './validation-styles.css';
import './final-ui-fixes.css';
import './data-dashboard.css';
import ZetaLoader from './components/ZetaLoader';
import ZetaUploadCard from './components/ZetaUploadCard';
import ZetaFeatureCard from './components/ZetaFeatureCard';

// Use relative URL for API (works on Render and localhost)
const API_BASE_URL = '/api';

function App() {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState(null);
  const [loadingFile, setLoadingFile] = useState(false);
  const [health, setHealth] = useState(null);
  const [activeTab, setActiveTab] = useState('upload');
  const [showValidation, setShowValidation] = useState(false);
  const [validationData, setValidationData] = useState(null);
  const [selectedViz, setSelectedViz] = useState('heatmap');

  useEffect(() => {
    fetchHealth();
    fetchFiles();
  }, []);

  const fetchHealth = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/health`);
      setHealth(res.data);
    } catch (err) {
      console.error('Health check failed');
    }
  };

  const fetchFiles = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/files`);
      setFiles(res.data.files || []);
    } catch (err) {
      console.error('Failed to fetch files');
    }
  };

  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) {
      const file = droppedFiles[0];
      if (file.name.endsWith('.docx')) {
        setFile(file);
        setError(null);
        simulateUploadProgress();
      } else {
        setError('Please upload a .docx file');
      }
    }
  }, []);

  const simulateUploadProgress = () => {
    setUploadProgress(0);
    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          return 100;
        }
        return prev + Math.random() * 15;
      });
    }, 200);
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
      simulateUploadProgress();
    }
  };

  // Used in upload card
  // const handleFileSelect = (e) => {...}

  const handleUpload = async () => {
    if (!file) return;

    setProcessing(true);
    setError(null);
    setResult(null);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_BASE_URL}/process`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        }
      });

      console.log('API Response:', response.data);
      console.log('Validation Data:', response.data.validation_report);
      console.log('Visualization Data:', response.data.validation_report?.visualization_data);
      
      setResult(response.data);
      setValidationData(response.data.validation_report);
      fetchFiles();
      setActiveTab('results');
    } catch (err) {
      console.error('Processing error:', err);
      setError(err.response?.data?.detail || 'Failed to process document');
    } finally {
      setProcessing(false);
      setUploadProgress(100);
    }
  };

  const viewFile = async (filename) => {
    setLoadingFile(true);
    setSelectedFile(filename);
    try {
      const res = await axios.get(`${API_BASE_URL}/files/${filename}`);
      setFileContent(res.data.content);
      setActiveTab('files');
    } catch (err) {
      setError('Failed to load file');
    } finally {
      setLoadingFile(false);
    }
  };

  const downloadFile = async (filename) => {
    window.open(`${API_BASE_URL}/download/${filename}`, '_blank');
  };

  const downloadCSV = async () => {
    const csvFiles = files.filter(f => f.type === 'validation_csv');
    if (csvFiles.length > 0) {
      downloadFile(csvFiles[0].filename);
    }
  };

  const deleteFile = async (filename) => {
    if (!window.confirm(`Delete ${filename}?`)) return;
    try {
      await axios.delete(`${API_BASE_URL}/files/${filename}`);
      fetchFiles();
      if (selectedFile === filename) {
        setSelectedFile(null);
        setFileContent(null);
      }
    } catch (err) {
      setError('Failed to delete file');
    }
  };

  const resetUpload = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setUploadProgress(0);
    setActiveTab('upload');
  };

  const releaseNotesFiles = files.filter(f => f.type === 'release_notes');
  const reportFiles = files.filter(f => f.type === 'validation_report');
  const csvFiles = files.filter(f => f.type === 'validation_csv');

  const getStatusColor = (score) => {
    if (score >= 85) return 'var(--status-success)';
    if (score >= 70) return 'var(--status-warning)';
    return 'var(--status-danger)';
  };

  const toggleValidation = () => {
    setShowValidation(!showValidation);
  };

  // toggleValidation used for future feature
  // const toggleValidation = () => {...}

  // Visualization Components - CLEAN DASHBOARD STYLE
  const ComplianceDashboard = ({ data }) => {
    if (!data || !data.data) return null;

    // Calculate average compliance
    const allScores = data.data.flatMap(row => 
      data.categories.map(cat => row.scores[cat] || 100)
    );
    const avgCompliance = Math.round(allScores.reduce((a, b) => a + b, 0) / allScores.length);

    return (
      <div className="data-dashboard">
        {/* Overall Score Card */}
        <div className="dashboard-card">
          <div className="dashboard-card-header">
            <div className="dashboard-card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6l4 2"/>
              </svg>
            </div>
            <h3 className="dashboard-card-title">Overall Compliance</h3>
          </div>
          <div className="score-ring-container">
            <div className="score-ring">
              <svg className="score-ring-svg" viewBox="0 0 100 100">
                <defs>
                  <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#e81cff"/>
                    <stop offset="50%" stopColor="#9d4edd"/>
                    <stop offset="100%" stopColor="#40c9ff"/>
                  </linearGradient>
                </defs>
                <circle className="score-ring-bg" cx="50" cy="50" r="40"/>
                <circle 
                  className="score-ring-fill" 
                  cx="50" 
                  cy="50" 
                  r="40"
                  strokeDasharray={`${avgCompliance * 2.51} 251`}
                  strokeDashoffset="0"
                />
              </svg>
              <div className="score-ring-value">{avgCompliance}%</div>
            </div>
            <div className="score-ring-label">Average Score</div>
          </div>
        </div>

        {/* Category Scores Card */}
        <div className="dashboard-card" style={{ gridColumn: 'span 2' }}>
          <div className="dashboard-card-header">
            <div className="dashboard-card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 20V10M18 20V4M6 20v-4"/>
              </svg>
            </div>
            <h3 className="dashboard-card-title">Category Scores</h3>
          </div>
          <div>
            {data.categories.map((cat, i) => {
              const scores = data.data.map(row => row.scores[cat] || 100);
              const avgScore = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
              return (
                <div key={i} className="category-score-item">
                  <div className="category-score-name">{cat}</div>
                  <div className="category-score-bar">
                    <div 
                      className="category-score-fill" 
                      style={{ width: `${avgScore}%` }}
                    />
                  </div>
                  <div className="category-score-value">{avgScore}%</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  const GeographyDashboard = ({ data }) => {
    if (!data || !data.counts) return null;

    const maxCount = Math.max(...Object.values(data.counts), 1);

    return (
      <div className="geography-dashboard">
        {Object.entries(data.counts).map(([region, count]) => {
          const percentage = Math.round((count / maxCount) * 100);
          return (
            <div key={region} className="geo-dashboard-card">
              <div className="geo-dashboard-flag">
                {region === 'Global' ? '🌍' : region === 'India' ? '🇮🇳' : '🇺🇸'}
              </div>
              <div className="geo-dashboard-name">{region}</div>
              <div className="geo-dashboard-count">{count}</div>
              <div className="geo-dashboard-label">Features</div>
              <div className="geo-dashboard-bar">
                <div 
                  className="geo-dashboard-bar-fill" 
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const ViolationsDashboard = ({ data }) => {
    if (!data || !data.category_scores) return null;

    const violations = Object.entries(data.category_scores)
      .filter(([_, score]) => score < 100)
      .map(([category, score]) => ({
        category,
        violations: Math.round((100 - score) / 10)
      }));

    return (
      <div className="violations-dashboard">
        {violations.map((violation, i) => (
          <div key={i} className="violation-type-card">
            <div className="violation-type-icon">⚠️</div>
            <div className="violation-type-count">{violation.violations}</div>
            <div className="violation-type-label">{violation.category}</div>
          </div>
        ))}
      </div>
    );
  };

  const FeatureComplianceDashboard = ({ data }) => {
    if (!data || !data.feature_validations) return null;

    return (
      <div className="feature-compliance-breakdown">
        {data.feature_validations.map((feature, i) => (
          <div key={i} className="compliance-item">
            <div className="compliance-item-header">
              <div className="compliance-feature-full">{feature.feature_name}</div>
              <div 
                className="compliance-score-badge"
                data-score={Math.round(feature.compliance_score)}
              >
                {Math.round(feature.compliance_score)}%
              </div>
            </div>
            <div className="compliance-progress-container">
              <div 
                className="compliance-progress-fill"
                data-score={Math.round(feature.compliance_score)}
                style={{ width: `${feature.compliance_score}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    );
  };

  const BeforeAfterDashboard = ({ data }) => {
    if (!data || !data.comparisons) return null;

    return (
      <div className="before-after-comparison">
        {data.comparisons.slice(0, 5).map((comp, i) => (
          <div key={i}>
            <div className="comparison-card before">
              <div className="comparison-header before">
                <div className="comparison-title">Before</div>
              </div>
              <div className="comparison-content">
                <div className="comparison-text">{comp.before.title}</div>
              </div>
            </div>
          </div>
        ))}
        {data.comparisons.slice(0, 5).map((comp, i) => (
          <div key={i}>
            <div className="comparison-card after">
              <div className="comparison-header after">
                <div className="comparison-title">After</div>
              </div>
              <div className="comparison-content">
                <div className="comparison-text">
                  <strong>{comp.after.title}</strong>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const FeaturePie = ({ data }) => {
    if (!data || !data.segments) return null;
    
    const total = data.segments.reduce((acc, seg) => acc + seg.value, 0);
    const publishedPercent = data.percentages?.Published || 0;
    
    return (
      <div className="pie-chart-viz">
        <div className="pie-chart">
          <svg viewBox="0 0 100 100" className="pie-svg">
            <circle
              cx="50"
              cy="50"
              r="40"
              fill="transparent"
              stroke="#ef4444"
              strokeWidth="20"
              strokeDasharray={`${(100 - publishedPercent) * 2.51} 251`}
              transform="rotate(-90 50 50)"
            />
            <circle
              cx="50"
              cy="50"
              r="40"
              fill="transparent"
              stroke="#10b981"
              strokeWidth="20"
              strokeDasharray={`${publishedPercent * 2.51} 251`}
              strokeDashoffset="0"
              transform="rotate(-90 50 50)"
            />
          </svg>
          <div className="pie-center">
            <span className="pie-total">{total}</span>
            <span className="pie-label">Total</span>
          </div>
        </div>
        <div className="pie-legend">
          {data.segments.map((seg, i) => (
            <div key={i} className="pie-legend-item">
              <div className="legend-color" style={{ backgroundColor: seg.color }} />
              <span className="legend-label">{seg.label}</span>
              <span className="legend-value">{seg.value} ({data.percentages?.[seg.label]}%)</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // BeforeAfterComparison - Replaced with BeforeAfterDashboard
  // const BeforeAfterComparison = ({ data }) => {...}

  // DUPLICATE REMOVED - Using the one at line 381
  // const BeforeAfterDashboard = ({ data }) => {...}

  // RadarChart - Replaced with cleaner dashboard components
  // const RadarChart = ({ data }) => {...}

  // DUPLICATE REMOVED - Using FeaturePie at line 416
  // const FeaturePie = ({ data }) => {...}

  const StackedBarChart = ({ data }) => {
    if (!data || !data.bars) return null;
    
    return (
      <div className="stacked-bar-viz">
        {data.bars.slice(0, 8).map((bar, i) => (
          <div key={i} className="stacked-bar-item">
            <div className="stacked-bar-label">{bar.feature}</div>
            <div className="stacked-bar-container">
              <div
                className="stacked-bar-segment passed"
                style={{
                  width: `${(bar.passed / bar.total) * 100}%`,
                  backgroundColor: data.colors.passed
                }}
                title={`Passed: ${bar.passed}`}
              />
              <div
                className="stacked-bar-segment failed"
                style={{
                  width: `${(bar.failed / bar.total) * 100}%`,
                  backgroundColor: data.colors.failed
                }}
                title={`Failed: ${bar.failed}`}
              />
            </div>
            <div className="stacked-bar-value">{bar.compliance}%</div>
          </div>
        ))}
        <div className="stacked-bar-legend">
          <div className="legend-item">
            <div className="legend-segment" style={{ backgroundColor: data.colors.passed }} />
            <span>Passed</span>
          </div>
          <div className="legend-item">
            <div className="legend-segment" style={{ backgroundColor: data.colors.failed }} />
            <span>Failed</span>
          </div>
        </div>
      </div>
    );
  };

  const ViolationsChart = ({ data }) => {
    if (!data || !data.categories || data.total_violations === 0) {
      return (
        <div className="no-violations">
          <div className="no-violations-icon">✅</div>
          <p>No violations detected!</p>
        </div>
      );
    }
    
    const maxCount = Math.max(...data.counts, 1);
    
    return (
      <div className="violations-chart-viz">
        <div className="violations-bars">
          {data.categories.map((cat, i) => (
            <div key={i} className="violation-bar-item">
              <div className="violation-bar-container">
                <div
                  className="violation-bar-fill"
                  style={{
                    width: `${(data.counts[i] / maxCount) * 100}%`,
                    background: `linear-gradient(90deg, ${data.colors[i % data.colors.length]}, ${data.colors[(i + 1) % data.colors.length]}88)`
                  }}
                />
              </div>
              <div className="violation-bar-label">{cat}</div>
              <div className="violation-bar-value">{data.counts[i]}</div>
            </div>
          ))}
        </div>
        <div className="violations-total">
          <span className="total-label">Total Violations</span>
          <span className="total-value">{data.total_violations}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="app">
      {/* Header - Centered Logo with Tagline */}
      <header className="header">
        <div className="header-content">
          <div className="brand-section">
            <div className="logo-container">
              <img src="/zetalogo.png" alt="Tachyon" className="company-logo" />
            </div>
            <h1 className="app-title">Release Notes Automation Platform</h1>
            <p className="app-tagline">
              Automating enterprise release documentation with AI-powered rubric validation
            </p>
            <p className="app-description">
              Transform rough engineering drafts into polished, customer-ready release notes in seconds
            </p>
          </div>
        </div>
      </header>

      {/* Navigation Tabs - Clean Icon-based Navigation */}
      <nav className="nav-tabs">
        <button
          className={`nav-tab ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
          </svg>
          <span>Upload</span>
        </button>
        <button
          className={`nav-tab ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
        >
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4L12 14.01l-3-3"/>
          </svg>
          <span>Results</span>
        </button>
        <button
          className={`nav-tab ${activeTab === 'validation' ? 'active' : ''}`}
          onClick={() => setActiveTab('validation')}
        >
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14M16 16l-4-4-4 4M12 3v12"/>
          </svg>
          <span>Validation</span>
        </button>
        <button
          className={`nav-tab ${activeTab === 'files' ? 'active' : ''}`}
          onClick={() => setActiveTab('files')}
        >
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6"/>
          </svg>
          <span>Files</span>
        </button>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        {/* Upload Tab */}
        {activeTab === 'upload' && (
          <div className="upload-section fade-in">
            {/* Main Upload Area */}
            <div className="upload-container">
              <div className="upload-header">
                <h2 className="upload-title">Upload Release Notes</h2>
                <p className="upload-subtitle">Transform engineering drafts into polished release notes</p>
              </div>

              {processing ? (
                <ZetaLoader />
              ) : (
                <ZetaUploadCard
                  onFileSelect={(selectedFile) => {
                    setFile(selectedFile);
                    setError(null);
                    simulateUploadProgress();
                  }}
                  isDragging={isDragging}
                  setIsDragging={setIsDragging}
                  processing={processing}
                />
              )}

              {file && !processing && (
                <div className="file-selected-card fade-in">
                  <div className="file-info-row">
                    <svg className="file-icon-lg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6"/>
                    </svg>
                    <div className="file-details">
                      <p className="file-name">{file.name}</p>
                      <p className="file-size">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button className="btn-remove" onClick={() => setFile(null)}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                      </svg>
                    </button>
                  </div>

                  {uploadProgress > 0 && uploadProgress < 100 && (
                    <div className="progress-wrapper">
                      <div className="progress-bar-modern">
                        <div className="progress-fill-modern" style={{ width: `${uploadProgress}%` }}/>
                      </div>
                      <p className="progress-label">{Math.round(uploadProgress)}% uploaded</p>
                    </div>
                  )}

                  <button
                    className="gradient-button"
                    onClick={handleUpload}
                    disabled={!file || processing}
                    style={{ maxWidth: '600px', padding: '20px 48px', fontSize: '20px', fontWeight: '800', whiteSpace: 'nowrap', margin: '0 auto', display: 'flex' }}
                  >
                    {processing ? (
                      <>
                        <span className="spinner"></span>
                        <span className="gradient-text">Processing with AI...</span>
                      </>
                    ) : (
                      <>
                        <span className="gradient-text">Process Document</span>
                        <svg className="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M5 12h14M12 5l7 7-7 7"/>
                        </svg>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* Feature Cards */}
            <div className="feature-grid">
              <div className="feature-card slide-in" style={{ animationDelay: '0.1s' }}>
                <div className="feature-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8"/>
                  </svg>
                </div>
                <h3 className="feature-title">AI-Powered</h3>
                <p className="feature-desc">Automatic conversion to compliant format</p>
              </div>

              <div className="feature-card slide-in" style={{ animationDelay: '0.2s' }}>
                <div className="feature-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                  </svg>
                </div>
                <h3 className="feature-title">Validation Report</h3>
                <p className="feature-desc">Detailed compliance report with CSV export</p>
              </div>
            </div>
          </div>
        )}

        {/* Results Tab */}
        {activeTab === 'results' && (
          <div className="results-section">
            {result ? (
              <div className="results-content fade-in">
                <div className="results-header">
                  <h2 className="section-title">Processing Complete</h2>
                  <button className="btn btn-outline" onClick={resetUpload}>
                    Process Another
                  </button>
                </div>

                <div className="stats-grid">
                  <div className="stat-card scale-in" style={{ animationDelay: '0.1s' }}>
                    <span className="stat-value">{result.validation_report.total_features_extracted}</span>
                    <span className="stat-label">Total Features</span>
                  </div>
                  <div className="stat-card scale-in" style={{ animationDelay: '0.2s' }}>
                    <span className="stat-value">{result.validation_report.features_published}</span>
                    <span className="stat-label">Published</span>
                  </div>
                  <div className="stat-card scale-in" style={{ animationDelay: '0.3s' }}>
                    <span className="stat-value">{result.validation_report.features_filtered}</span>
                    <span className="stat-label">Filtered Out</span>
                  </div>
                  <div 
                    className="stat-card highlight scale-in" 
                    style={{ 
                      animationDelay: '0.4s',
                      background: `linear-gradient(135deg, ${getStatusColor(result.validation_report.overall_compliance_score)} 0%, ${getStatusColor(result.validation_report.overall_compliance_score)}88 100%)`
                    }}
                  >
                    <span className="stat-value">{result.validation_report.overall_compliance_score}%</span>
                    <span className="stat-label">Compliance Score</span>
                  </div>
                </div>

                <div className="geography-section slide-in" style={{ animationDelay: '0.5s' }}>
                  <h3 className="subsection-title">Geography Distribution</h3>
                  <div className="geography-bars">
                    {Object.entries(result.validation_report.geography_distribution).map(([geo, count], index) => (
                      <div key={geo} className="geo-item fade-in" style={{ animationDelay: `${0.1 * index}s` }}>
                        <span className="geo-label">{geo}</span>
                        <div className="geo-bar">
                          <div
                            className="geo-fill"
                            style={{ 
                              width: `${Math.min(count * 10, 100)}%`,
                              background: `linear-gradient(90deg, ${getStatusColor(result.validation_report.overall_compliance_score)}, ${getStatusColor(result.validation_report.overall_compliance_score)}88)`
                            }}
                          />
                        </div>
                        <span className="geo-count">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="downloads-section slide-in" style={{ animationDelay: '0.6s' }}>
                  <h3 className="subsection-title">Download Files</h3>
                  <div className="download-grid">
                    {/* Download All ZIP */}
                    <div className="download-card fade-in" style={{ borderColor: 'var(--color-primary)', borderWidth: '2px' }}>
                      <div className="download-icon-doc" style={{ background: 'var(--gradient-primary)' }}></div>
                      <div className="download-info">
                        <span className="download-name">All Feature Files (ZIP)</span>
                        <span className="download-type">Individual MD files + Consolidated file</span>
                      </div>
                      <button
                        className="btn btn-sm btn-success"
                        onClick={() => window.open(`${API_BASE_URL}/download-all`, '_blank')}
                      >
                        Download All
                      </button>
                    </div>
                    
                    {/* Consolidated Release Notes */}
                    <div className="download-card fade-in">
                      <div className="download-icon-doc"></div>
                      <div className="download-info">
                        <span className="download-name">release_notes_consolidated.md</span>
                        <span className="download-type">All features in one file</span>
                      </div>
                      <button
                        className="btn btn-sm"
                        onClick={() => downloadFile('release_notes_consolidated.md')}
                      >
                        Download
                      </button>
                    </div>
                    
                    {/* Validation Report MD */}
                    {reportFiles.slice(0, 1).map(file => (
                      <div key={file.filename} className="download-card fade-in">
                        <div className="download-icon-report"></div>
                        <div className="download-info">
                          <span className="download-name">{file.filename}</span>
                          <span className="download-type">Validation Report (MD)</span>
                        </div>
                        <button
                          className="btn btn-sm"
                          onClick={() => downloadFile(file.filename)}
                        >
                          Download
                        </button>
                      </div>
                    ))}
                    
                    {/* Validation Report CSV */}
                    {csvFiles.slice(0, 1).map(file => (
                      <div key={file.filename} className="download-card fade-in">
                        <div className="download-icon-csv"></div>
                        <div className="download-info">
                          <span className="download-name">{file.filename}</span>
                          <span className="download-type">Validation Report (CSV)</span>
                        </div>
                        <button
                          className="btn btn-sm btn-success"
                          onClick={() => downloadFile(file.filename)}
                        >
                          Download
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {result.validation_report.rubric_violations && result.validation_report.rubric_violations.length > 0 && (
                  <div className="violations-section slide-in" style={{ animationDelay: '0.7s' }}>
                    <h3 className="subsection-title">Rubric Violations</h3>
                    <div className="violations-list">
                      {result.validation_report.rubric_violations.map((violation, idx) => (
                        <div key={idx} className="violation-item fade-in" style={{ animationDelay: `${0.1 * idx}s` }}>
                          <span className="violation-icon">!</span>
                          <span className="violation-text">{violation}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="empty-state scale-in">
                <div className="empty-icon-chart"></div>
                <h3>No Results Yet</h3>
                <p>Upload and process a document to see results</p>
                <button className="btn btn-primary" onClick={() => setActiveTab('upload')}>
                  Go to Upload
                </button>
              </div>
            )}
          </div>
        )}

        {/* Validation Tab - Enhanced with Rich Visualizations */}
        {activeTab === 'validation' && (
          <div className="validation-section fade-in">
            {validationData ? (
              <>
                <div className="validation-header">
                  <h2 className="section-title">Data Validation Report</h2>
                  <div className="validation-controls">
                    <div className="viz-selector">
                      <button
                        className={`viz-tab ${selectedViz === 'heatmap' ? 'active' : ''}`}
                        onClick={() => setSelectedViz('heatmap')}
                      >
                        <span>Heatmap</span>
                      </button>
                      <button
                        className={`viz-tab ${selectedViz === 'geography' ? 'active' : ''}`}
                        onClick={() => setSelectedViz('geography')}
                      >
                        <span>Geography</span>
                      </button>
                      <button
                        className={`viz-tab ${selectedViz === 'radar' ? 'active' : ''}`}
                        onClick={() => setSelectedViz('radar')}
                      >
                        <span>Radar</span>
                      </button>
                      <button
                        className={`viz-tab ${selectedViz === 'before' ? 'active' : ''}`}
                        onClick={() => setSelectedViz('before')}
                      >
                        <span>Before/After</span>
                      </button>
                    </div>
                    <button
                      className="download-csv-btn"
                      onClick={downloadCSV}
                      disabled={csvFiles.length === 0}
                    >
                      <span>Download CSV</span>
                    </button>
                  </div>
                </div>

                {/* Summary Cards */}
                <div className="validation-summary-grid">
                  <div className="validation-summary-card">
                    <div className="summary-value">{validationData.overall_compliance_score}%</div>
                    <div className="summary-label">Overall Compliance</div>
                    <div className="summary-bar">
                      <div
                        className="summary-bar-fill"
                        style={{ width: `${validationData.overall_compliance_score}%` }}
                      />
                    </div>
                  </div>

                  <div className="validation-summary-card">
                    <div className="summary-value">{validationData.total_features_extracted}</div>
                    <div className="summary-label">Features Extracted</div>
                  </div>

                  <div className="validation-summary-card">
                    <div className="summary-value">{validationData.features_published}</div>
                    <div className="summary-label">Features Published</div>
                    <div className="summary-pie-mini">
                      <svg viewBox="0 0 36 36" className="circular-chart">
                        <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#ef4444" strokeWidth="4" strokeDasharray="100, 100" />
                        <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#10b981" strokeWidth="4" strokeDasharray={`${(validationData.features_published / Math.max(1, validationData.total_features_extracted)) * 100}, 100`} />
                      </svg>
                    </div>
                  </div>

                  <div className="validation-summary-card">
                    <div className="summary-value">{Object.keys(validationData.data_integrity_checks || {}).filter(k => validationData.data_integrity_checks[k]).length}/{Object.keys(validationData.data_integrity_checks || {}).length}</div>
                    <div className="summary-label">Integrity Checks Passed</div>
                  </div>
                </div>

                {/* Category Scores - NEW DASHBOARD */}
                {validationData.category_scores && (
                  <div className="category-scores-section slide-in">
                    <h3 className="subsection-title">Category-wise Compliance</h3>
                    <div className="category-bars-viz">
                      {Object.entries(validationData.category_scores).map(([cat, score], i) => (
                        <div key={i} className="category-bar-item">
                          <div className="cat-bar-label">{cat}</div>
                          <div className="cat-bar-container">
                            <div
                              className="cat-bar-fill"
                              style={{ width: `${score}%` }}
                            />
                          </div>
                          <div className="cat-bar-value">{score}%</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Rich Visualizations - NEW DASHBOARD STYLE */}
                <div className="rich-visualizations-section slide-in" style={{ animationDelay: '0.3s' }}>
                  <h3 className="subsection-title">Data Dashboard</h3>

                  {/* Visualization Tab Selector */}
                  <div className="viz-tabs">
                    <button
                      className={`viz-tab ${selectedViz === 'compliance' ? 'active' : ''}`}
                      onClick={() => setSelectedViz('compliance')}
                    >
                      <span>Compliance</span>
                    </button>
                    <button
                      className={`viz-tab ${selectedViz === 'geography' ? 'active' : ''}`}
                      onClick={() => setSelectedViz('geography')}
                    >
                      <span>Geography</span>
                    </button>
                    <button
                      className={`viz-tab ${selectedViz === 'violations' ? 'active' : ''}`}
                      onClick={() => setSelectedViz('violations')}
                    >
                      <span>Violations</span>
                    </button>
                    <button
                      className={`viz-tab ${selectedViz === 'features' ? 'active' : ''}`}
                      onClick={() => setSelectedViz('features')}
                    >
                      <span>Features</span>
                    </button>
                    <button
                      className={`viz-tab ${selectedViz === 'before' ? 'active' : ''}`}
                      onClick={() => setSelectedViz('before')}
                    >
                      <span>Before/After</span>
                    </button>
                  </div>

                  <div className="viz-tabs-content">
                    {/* Compliance Dashboard */}
                    {selectedViz === 'compliance' && (
                      <div className="viz-panel fade-in">
                        {validationData.visualization_data?.compliance_heatmap ? (
                          <ComplianceDashboard data={validationData.visualization_data.compliance_heatmap} />
                        ) : (
                          <div className="no-data-message">
                            <p>📊 Compliance dashboard will be available after processing</p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Geography Dashboard */}
                    {selectedViz === 'geography' && (
                      <div className="viz-panel fade-in">
                        {validationData.visualization_data?.geography_distribution ? (
                          <GeographyDashboard data={validationData.visualization_data.geography_distribution} />
                        ) : (
                          <div className="no-data-message">
                            <p>🌍 Geography dashboard will be available after processing</p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Violations Dashboard */}
                    {selectedViz === 'violations' && (
                      <div className="viz-panel fade-in">
                        {validationData.category_scores ? (
                          <ViolationsDashboard data={validationData} />
                        ) : (
                          <div className="no-data-message">
                            <p>⚠️ Violations data will be available after processing</p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Features Compliance */}
                    {selectedViz === 'features' && (
                      <div className="viz-panel fade-in">
                        {validationData.feature_validations ? (
                          <FeatureComplianceDashboard data={validationData} />
                        ) : (
                          <div className="no-data-message">
                            <p>📋 Feature compliance will be available after processing</p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Before/After Dashboard */}
                    {selectedViz === 'before' && (
                      <div className="viz-panel fade-in">
                        {validationData.before_after_comparison && validationData.before_after_comparison.comparisons?.length > 0 ? (
                          <BeforeAfterDashboard data={validationData.before_after_comparison} />
                        ) : (
                          <div className="no-data-message">
                            <p>📝 Before/After comparison will be available after processing</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Additional Charts Grid */}
                <div className="additional-charts-grid slide-in" style={{ animationDelay: '0.4s' }}>
                  {/* Feature Distribution Pie */}
                  {validationData.visualization_data?.feature_comparison_pie && (
                    <div className="chart-card">
                      <h4 className="chart-title">Feature Distribution</h4>
                      <FeaturePie data={validationData.visualization_data.feature_comparison_pie} />
                    </div>
                  )}
                  
                  {/* Violations Chart */}
                  {validationData.visualization_data?.rubric_violations_chart && (
                    <div className="chart-card">
                      <h4 className="chart-title">Violations by Category</h4>
                      <ViolationsChart data={validationData.visualization_data.rubric_violations_chart} />
                    </div>
                  )}
                  
                  {/* Stacked Bar - Passed/Failed */}
                  {validationData.visualization_data?.stacked_bar_data && (
                    <div className="chart-card full-width">
                      <h4 className="chart-title">Feature Compliance Breakdown</h4>
                      <StackedBarChart data={validationData.visualization_data.stacked_bar_data} />
                    </div>
                  )}
                </div>

                {/* Detailed Validation Table (Toggle) */}
                {showValidation && (
                  <div className="detailed-validation-section slide-in" style={{ animationDelay: '0.4s' }}>
                    <h3 className="subsection-title">Detailed Feature Validation</h3>
                    <div className="validation-table-container">
                      <table className="validation-table">
                        <thead>
                          <tr>
                            <th>Feature</th>
                            <th>Compliance</th>
                            <th>Rules Passed</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {validationData.feature_validations && validationData.feature_validations.map((fv, idx) => (
                            <tr key={idx} className="validation-row">
                              <td className="feature-name">{fv.feature_name}</td>
                              <td>
                                <div className="compliance-cell">
                                  <span style={{ color: getStatusColor(fv.compliance_score) }}>{fv.compliance_score}%</span>
                                </div>
                              </td>
                              <td>{fv.passed_rules}/{fv.total_rules}</td>
                              <td>
                                <span className={`status-badge-small ${fv.is_valid ? 'status-valid' : 'status-invalid'}`}>
                                  {fv.is_valid ? 'Valid' : 'Needs Review'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="empty-state scale-in">
                <div className="empty-icon-chart"></div>
                <h3>No Validation Data</h3>
                <p>Upload and process a document to see validation details</p>
                <button className="btn btn-primary" onClick={() => setActiveTab('upload')}>
                  Go to Upload
                </button>
              </div>
            )}
          </div>
        )}

        {/* Files Tab */}
        {activeTab === 'files' && (
          <div className="files-section fade-in">
            <div className="files-grid">
              {/* Release Notes Files */}
              <div className="files-column slide-in" style={{ animationDelay: '0.1s' }}>
                <h3 className="column-title">
                  <span className="column-icon-doc"></span>
                  Release Notes
                </h3>
                {releaseNotesFiles.length > 0 ? (
                  <div className="files-list">
                    {releaseNotesFiles.map((file, index) => (
                      <div 
                        key={file.filename} 
                        className="file-item fade-in" 
                        style={{ animationDelay: `${0.05 * index}s` }}
                      >
                        <div className="file-item-info" onClick={() => viewFile(file.filename)}>
                          <span className="file-item-name">{file.filename}</span>
                          <span className="file-item-meta">{(file.size / 1024).toFixed(1)} KB</span>
                        </div>
                        <div className="file-item-actions">
                          <button
                            className="btn-icon"
                            onClick={() => downloadFile(file.filename)}
                            title="Download"
                            aria-label="Download"
                          >
                            D
                          </button>
                          <button
                            className="btn-icon btn-icon-danger"
                            onClick={() => deleteFile(file.filename)}
                            title="Delete"
                            aria-label="Delete"
                          >
                            X
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-list">No release notes files</div>
                )}
              </div>

              {/* Validation Reports */}
              <div className="files-column slide-in" style={{ animationDelay: '0.2s' }}>
                <h3 className="column-title">
                  <span className="column-icon-report"></span>
                  Validation Reports
                </h3>
                {reportFiles.length > 0 ? (
                  <div className="files-list">
                    {reportFiles.map((file, index) => (
                      <div 
                        key={file.filename} 
                        className="file-item fade-in" 
                        style={{ animationDelay: `${0.05 * index}s` }}
                      >
                        <div className="file-item-info" onClick={() => viewFile(file.filename)}>
                          <span className="file-item-name">{file.filename}</span>
                          <span className="file-item-meta">{(file.size / 1024).toFixed(1)} KB</span>
                        </div>
                        <div className="file-item-actions">
                          <button
                            className="btn-icon"
                            onClick={() => downloadFile(file.filename)}
                            title="Download"
                            aria-label="Download"
                          >
                            D
                          </button>
                          <button
                            className="btn-icon btn-icon-danger"
                            onClick={() => deleteFile(file.filename)}
                            title="Delete"
                            aria-label="Delete"
                          >
                            X
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-list">No validation reports</div>
                )}
              </div>

              {/* CSV Reports */}
              <div className="files-column slide-in" style={{ animationDelay: '0.3s' }}>
                <h3 className="column-title">
                  <span className="column-icon-csv"></span>
                  CSV Reports
                </h3>
                {csvFiles.length > 0 ? (
                  <div className="files-list">
                    {csvFiles.map((file, index) => (
                      <div 
                        key={file.filename} 
                        className="file-item fade-in" 
                        style={{ animationDelay: `${0.05 * index}s` }}
                      >
                        <div className="file-item-info">
                          <span className="file-item-name">{file.filename}</span>
                          <span className="file-item-meta">{(file.size / 1024).toFixed(1)} KB</span>
                        </div>
                        <div className="file-item-actions">
                          <button
                            className="btn-icon"
                            onClick={() => downloadFile(file.filename)}
                            title="Download"
                            aria-label="Download"
                          >
                            D
                          </button>
                          <button
                            className="btn-icon btn-icon-danger"
                            onClick={() => deleteFile(file.filename)}
                            title="Delete"
                            aria-label="Delete"
                          >
                            X
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-list">No CSV reports</div>
                )}
              </div>
            </div>

            {/* File Preview */}
            {selectedFile && (
              <div className="file-preview-panel slide-in" style={{ animationDelay: '0.4s' }}>
                <div className="preview-header">
                  <h3 className="preview-title">{selectedFile}</h3>
                  <div className="preview-actions">
                    <button className="btn btn-sm" onClick={() => downloadFile(selectedFile)}>
                      Download
                    </button>
                    <button 
                      className="btn btn-sm btn-outline" 
                      onClick={() => { setSelectedFile(null); setFileContent(null); }}
                    >
                      Close
                    </button>
                  </div>
                </div>
                {loadingFile ? (
                  <div className="loading-preview">
                    <span className="spinner-large"></span>
                  </div>
                ) : (
                  <div className="preview-content">
                    <ReactMarkdown>{fileContent}</ReactMarkdown>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer - Elegant Neon */}
      <footer className="footer">
        <div className="footer-content">
          <span className="copyright-icon">©</span>
          <span className="footer-text">Powered by Benila E</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
