import React from 'react';

interface DocumentListItemProps {
  id: string;
  name: string;
  onSelect: (id: string) => void;
}

const DocumentListItem: React.FC<DocumentListItemProps> = ({ id, name, onSelect }) => {
  const containerStyle: React.CSSProperties = {
    padding: '0.75rem',
    marginBottom: '0.5rem',
    backgroundColor: 'white',
    border: '1px solid #dee2e6',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  };

  const textStyle: React.CSSProperties = {
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    display: 'block',
    width: '100%'
  };

  return (
    <div
      onClick={() => onSelect(id)}
      style={containerStyle}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = '#f8f9fa';
        e.currentTarget.style.borderColor = '#ced4da';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'white';
        e.currentTarget.style.borderColor = '#dee2e6';
      }}
      title={name} // Shows full name on hover
    >
      <span style={textStyle}>{name}</span>
    </div>
  );
};

export default DocumentListItem; 