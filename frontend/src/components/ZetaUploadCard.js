import React, { useCallback } from 'react';

const ZetaUploadCard = ({ onFileSelect, isDragging, setIsDragging, processing }) => {
  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, [setIsDragging]);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, [setIsDragging]);

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
      onFileSelect(droppedFiles[0]);
    }
  }, [onFileSelect, setIsDragging]);

  const handleFileInput = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      onFileSelect(selectedFile);
    }
  };

  return (
    <div
      className={`card ${isDragging ? 'dragging' : ''} ${processing ? 'processing' : ''}`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div className="upload-icon-main">📁</div>
      
      <h3 className="card-title">
        {isDragging ? 'Drop your file here' : 'Upload Release Notes'}
      </h3>
      
      <p className="card-desc">
        {isDragging 
          ? 'Release the file to upload' 
          : 'Drag and drop your Word document here, or click to browse'}
      </p>
      
      {!processing && (
        <label className="gradient-button">
          <input
            type="file"
            accept=".docx"
            onChange={handleFileInput}
            style={{ display: 'none' }}
          />
          <span className="gradient-text">📤 Choose File</span>
        </label>
      )}
      
      <p className="card-hint">
        ✨ Supports .docx files only
      </p>
    </div>
  );
};

export default ZetaUploadCard;
