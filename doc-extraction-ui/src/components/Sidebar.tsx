import React from 'react';

type Document = {
  id: string;
  name: string;
  fields: any[];
};

type Props = {
  documents: Document[];
  onSelect: (id: string) => void;
  onExtractNew: () => void;
};

const Sidebar: React.FC<Props> = ({ documents, onSelect, onExtractNew }) => {
  return (
    <div style={{
      width: '250px',
      padding: '1rem',
      background: '#f5f5f5',
      borderRight: '1px solid #ccc',
      display: 'flex',
      flexDirection: 'column'
    }}>
      
      <button
        onClick={onExtractNew}
        style={{
          padding: '0.5rem',
          marginBottom: '1rem',
          backgroundColor: '#007BFF',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        Extract Fields
      </button>
      <h2>Recent Documents</h2>
      {documents.length === 0 ? (
        <p>No documents processed yet.</p>
      ) : (
        <ul style={{ listStyleType: 'none', padding: 0 }}>
          {documents.map((doc) => (
            <li
              key={doc.id}
              onClick={() => onSelect(doc.id)}
              style={{
                padding: '0.5rem',
                marginBottom: '0.5rem',
                cursor: 'pointer',
                backgroundColor: 'white',
                border: '1px solid #ddd',
                borderRadius: '4px',
                transition: 'background-color 0.2s'
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.backgroundColor = '#f0f0f0';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.backgroundColor = 'white';
              }}
            >
              {doc.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default Sidebar;
