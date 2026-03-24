import React, { useState, useEffect } from 'react';

const PROCESSING_STEPS = [
  { text: 'Extracting feature tables from document', icon: '\u{1F4C4}' },
  { text: 'Identifying publishable features', icon: '\u{1F50D}' },
  { text: 'AI is rewriting content with rubric constraints', icon: '\u{1F916}' },
  { text: 'Enforcing acronym formatting rules', icon: '\u{1F524}' },
  { text: 'Applying lead line and bullet structure', icon: '\u{1F4DD}' },
  { text: 'Validating against 30+ rubric rules', icon: '\u{2705}' },
  { text: 'Checking data integrity and anti-hallucination', icon: '\u{1F6E1}\u{FE0F}' },
  { text: 'Generating markdown output files', icon: '\u{1F4C1}' },
  { text: 'Computing compliance scores', icon: '\u{1F4CA}' },
  { text: 'Building validation report', icon: '\u{1F4CB}' },
  { text: 'Finalizing release notes', icon: '\u{2728}' },
];

const ZetaLoader = () => {
  const [stepIndex, setStepIndex] = useState(0);
  const [fade, setFade] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      setFade(false);
      setTimeout(() => {
        setStepIndex(prev => (prev + 1) % PROCESSING_STEPS.length);
        setFade(true);
      }, 300);
    }, 2800);
    return () => clearInterval(interval);
  }, []);

  const step = PROCESSING_STEPS[stepIndex];
  const progress = ((stepIndex + 1) / PROCESSING_STEPS.length) * 100;

  return (
    <div className="cosmos-loader">
      {/* Planet Loader SVG */}
      <div className="cosmos-loader-ring">
        <svg className="pl" width="200" height="200" viewBox="0 0 240 240">
          <circle className="pl__ring pl__ring--a" cx="120" cy="120" r="105" fill="none" stroke="#000" strokeWidth="20" strokeDasharray="0 660" strokeDashoffset="-330" strokeLinecap="round" />
          <circle className="pl__ring pl__ring--b" cx="120" cy="120" r="35" fill="none" stroke="#000" strokeWidth="20" strokeDasharray="0 220" strokeDashoffset="-110" strokeLinecap="round" />
          <circle className="pl__ring pl__ring--c" cx="85" cy="120" r="70" fill="none" stroke="#000" strokeWidth="20" strokeDasharray="0 440" strokeLinecap="round" />
          <circle className="pl__ring pl__ring--d" cx="155" cy="120" r="70" fill="none" stroke="#000" strokeWidth="20" strokeDasharray="0 440" strokeLinecap="round" />
        </svg>
      </div>

      {/* Step counter */}
      <div className="cosmos-loader-step-counter">
        <span className="cosmos-loader-step-num">{String(stepIndex + 1).padStart(2, '0')}</span>
        <span className="cosmos-loader-step-sep">/</span>
        <span className="cosmos-loader-step-total">{String(PROCESSING_STEPS.length).padStart(2, '0')}</span>
      </div>

      {/* Animated tagline */}
      <div className={`cosmos-loader-tagline ${fade ? 'visible' : ''}`}>
        <span className="cosmos-loader-icon">{step.icon}</span>
        <span className="cosmos-loader-text">{step.text}</span>
      </div>

      {/* Progress track */}
      <div className="cosmos-loader-track">
        <div className="cosmos-loader-fill" style={{ width: `${progress}%` }} />
      </div>

      <p className="cosmos-loader-sub">This may take a few moments</p>
    </div>
  );
};

export default ZetaLoader;
