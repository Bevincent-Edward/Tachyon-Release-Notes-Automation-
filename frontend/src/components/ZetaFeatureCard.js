import React from 'react';

const ZetaFeatureCard = ({ feature, onClick }) => {
  return (
    <div className="feature-card" onClick={onClick}>
      <div className="feature-header">
        <h3 className="feature-title">{feature.title || feature.feature_name}</h3>
        <span className="feature-tag">{feature.geography || 'All'}</span>
      </div>
      
      <p className="feature-description">
        {feature.description || feature.problem_statement?.substring(0, 150) + '...'}
      </p>
      
      <div className="feature-meta">
        <div className="meta-item">
          <span className="meta-icon">📍</span>
          <span>{feature.product_module || 'Product'}</span>
        </div>
        <div className="meta-item">
          <span className="meta-icon">✅</span>
          <span>{feature.compliance_score || '100'}% Compliance</span>
        </div>
      </div>
    </div>
  );
};

export default ZetaFeatureCard;
