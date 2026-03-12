import React from 'react';

const ZetaLogo = ({ size = 60 }) => {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 100 100"
      style={{
        filter: 'drop-shadow(0 0 10px rgba(157, 78, 221, 0.5))'
      }}
    >
      {/* Gradient Definition */}
      <defs>
        <linearGradient id="zetaGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{ stopColor: '#e81cff', stopOpacity: 1 }} />
          <stop offset="100%" style={{ stopColor: '#40c9ff', stopOpacity: 1 }} />
        </linearGradient>
      </defs>
      
      {/* Outer Circle */}
      <circle 
        cx="50" 
        cy="50" 
        r="45" 
        fill="none" 
        stroke="url(#zetaGradient)" 
        strokeWidth="4"
        opacity="0.8"
      />
      
      {/* Z Letter */}
      <path 
        d="M 25 30 L 75 30 L 25 70 L 75 70" 
        fill="none" 
        stroke="url(#zetaGradient)" 
        strokeWidth="8" 
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      
      {/* Center Dot */}
      <circle 
        cx="50" 
        cy="50" 
        r="8" 
        fill="url(#zetaGradient)"
      />
    </svg>
  );
};

export default ZetaLogo;
