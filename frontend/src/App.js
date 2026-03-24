import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import './App.css';
import './section-styles.css';
import './comprehensive-fixes.css';
import './validation-styles.css';
import './final-ui-fixes.css';
import './data-dashboard.css';
import './home-page.css';
import ZetaLoader from './components/ZetaLoader';
// ZetaUploadCard replaced by inline portal in home page
import ValidationSection from './components/ValidationSection';

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
  const [, setHealth] = useState(null);
  const [activeTab, setActiveTab] = useState('upload');
  const [validationData, setValidationData] = useState(null);

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

  // Drag handlers inlined into the home page portal

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

  // File select handler inlined into portal

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
    try {
      const res = await axios.get(`${API_BASE_URL}/download/${filename}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download file');
    }
  };

  const downloadAll = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/download-all`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'release_notes.zip';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download files');
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

  // Visualization components moved to ValidationSection.js

  // Visualization components moved to ValidationSection.js

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
        {/* Upload Tab — Cosmic Portal */}
        {activeTab === 'upload' && (
          <div className="home-aurora">
            {/* Hero */}
            <div className="home-hero">
              <div className="home-eyebrow">
                <span className="home-eyebrow-dot" />
                AI-Powered Automation
              </div>
              <h2 className="home-title">
                Transform Rough Drafts into{' '}
                <span className="home-title-accent">Polished Release Notes</span>
              </h2>
              <p className="home-subtitle">
                Upload your Word document and let AI rewrite, validate, and format your release notes
                against 30+ rubric rules — in seconds.
              </p>
            </div>

            {/* Processing Loader or Upload Portal */}
            {processing ? (
              <ZetaLoader />
            ) : (
              <>
                <div className="home-portal-wrap">
                  <div
                    className={`home-portal ${isDragging ? 'dragging' : ''}`}
                    onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }}
                    onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); }}
                    onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                    onDrop={(e) => {
                      e.preventDefault(); e.stopPropagation(); setIsDragging(false);
                      const f = e.dataTransfer.files;
                      if (f.length > 0 && f[0].name.endsWith('.docx')) {
                        setFile(f[0]); setError(null); simulateUploadProgress();
                      } else { setError('Please upload a .docx file'); }
                    }}
                  >
                    <div className="home-portal-icon">
                      {isDragging ? '\u{2B07}\u{FE0F}' : '\u{1F4C4}'}
                    </div>
                    <div className="home-portal-heading">
                      {isDragging ? 'Drop your file here' : 'Upload Release Notes'}
                    </div>
                    <div className="home-portal-desc">
                      {isDragging ? 'Release to upload' : 'Drag and drop your Word document, or browse to select'}
                    </div>
                    <label className="home-portal-browse">
                      <input type="file" accept=".docx" style={{ display: 'none' }}
                        onChange={(e) => { if (e.target.files[0]) { setFile(e.target.files[0]); setError(null); simulateUploadProgress(); } }}
                      />
                      Choose .docx File
                    </label>
                    <div className="home-portal-hint">Supports .docx files only</div>
                  </div>
                </div>

                {/* Error */}
                {error && (
                  <div className="home-error">
                    <span className="home-error-icon">{'\u26A0\uFE0F'}</span>
                    <span>{error}</span>
                  </div>
                )}

                {/* File Ready Card */}
                {file && (
                  <div className="home-file-card">
                    <div className="home-file-row">
                      <div className="home-file-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6"/>
                        </svg>
                      </div>
                      <div className="home-file-meta">
                        <div className="home-file-name">{file.name}</div>
                        <div className="home-file-size">{(file.size / 1024).toFixed(1)} KB</div>
                      </div>
                      <button className="home-file-remove" onClick={() => { setFile(null); setUploadProgress(0); }}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                      </button>
                    </div>

                    {uploadProgress > 0 && uploadProgress < 100 && (
                      <div className="home-progress-wrap">
                        <div className="home-progress-track">
                          <div className="home-progress-fill" style={{ width: `${uploadProgress}%` }}/>
                        </div>
                        <div className="home-progress-label">{Math.round(uploadProgress)}% uploaded</div>
                      </div>
                    )}

                    <button className="home-process-btn" onClick={handleUpload} disabled={!file || processing}>
                      Process Document
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                    </button>
                  </div>
                )}
              </>
            )}

            {/* Feature Pillars */}
            {!processing && (
              <div className="home-features">
                <div className="home-feature-pillar" style={{ '--pillar-color': '#8b5cf6' }}>
                  <div className="home-pillar-icon">{'\u{1F916}'}</div>
                  <div className="home-pillar-title">AI-Powered Rewriting</div>
                  <div className="home-pillar-desc">Multi-LLM pipeline with Qubrid, Groq & Gemini fallback</div>
                </div>
                <div className="home-feature-pillar" style={{ '--pillar-color': '#06b6d4' }}>
                  <div className="home-pillar-icon">{'\u{1F6E1}\u{FE0F}'}</div>
                  <div className="home-pillar-title">30+ Rubric Rules</div>
                  <div className="home-pillar-desc">Deterministic validation — no hallucination allowed</div>
                </div>
                <div className="home-feature-pillar" style={{ '--pillar-color': '#ec4899' }}>
                  <div className="home-pillar-icon">{'\u{1F4CA}'}</div>
                  <div className="home-pillar-title">Rich Validation Report</div>
                  <div className="home-pillar-desc">Before/after, compliance matrix, geography insights</div>
                </div>
              </div>
            )}
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
                        onClick={downloadAll}
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
                    
                    {/* CSV option removed */}
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

        {/* Validation Tab — Data Observatory */}
        {activeTab === 'validation' && (
          <ValidationSection
            validationData={validationData}
            files={files}
            onTabChange={setActiveTab}
          />
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
