import React, { useRef } from 'react';
import { buttonStyle } from '../styles'; // adjust path if needed

type DocumentViewerProps = {
  documentUrl: string | null;
  onUpload: (file: File) => void;
};

const DocumentViewer: React.FC<DocumentViewerProps> = ({ documentUrl, onUpload }) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUpload(e.target.files[0]);
    }
  };

  return (
    <div style={{ textAlign: 'center', padding: '1rem' }}>
      {documentUrl ? (
        <img
          src={documentUrl}
          alt="Uploaded Document"
          style={{ width: '80%', maxHeight: '400px', objectFit: 'contain' }}
        />
      ) : (
        <p>No document uploaded yet.</p>
      )}
      <br />
      <button style={buttonStyle} onClick={() => fileInputRef.current?.click()}>
        📁 Upload Document
      </button>


      <input
        type="file"
        accept="image/*"
        ref={fileInputRef}
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
    </div>
  );
};

export default DocumentViewer;
