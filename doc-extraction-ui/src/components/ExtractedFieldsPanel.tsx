import React, { useState } from 'react';

type ExtractedField = {
  key: string;
  value: string | null;
};

type FieldValidation = {
  validate: (value: string) => boolean;
  errorMessage: string;
  format: string;
};

// Field validation rules
const FIELD_VALIDATIONS: Record<string, FieldValidation> = {
  date_of_birth: {
    validate: (value) => {
      const date = new Date(value);
      const today = new Date();
      return !isNaN(date.getTime()) && date < today;
    },
    errorMessage: "Please enter a valid date in YYYY-MM-DD format (must be in the past)",
    format: "YYYY-MM-DD"
  },
  issue_date: {
    validate: (value) => {
      const date = new Date(value);
      return !isNaN(date.getTime());
    },
    errorMessage: "Please enter a valid date in YYYY-MM-DD format",
    format: "YYYY-MM-DD"
  },
  expiration_date: {
    validate: (value) => {
      const date = new Date(value);
      const today = new Date();
      return !isNaN(date.getTime()) && date > today;
    },
    errorMessage: "Please enter a valid date in YYYY-MM-DD format (must be in the future)",
    format: "YYYY-MM-DD"
  },
  full_name: {
    validate: (value) => value.trim().length >= 2 && /^[A-Za-z\s\-']+$/.test(value),
    errorMessage: "Please enter a valid name (letters, spaces, hyphens, and apostrophes only)",
    format: ""
  },
  country: {
    validate: (value) => value.trim().length >= 2 && /^[A-Za-z\s\-']+$/.test(value),
    errorMessage: "Please enter a valid country name (letters, spaces, and hyphens only)",
    format: ""
  }
};

type Props = {
  fields: ExtractedField[];
  onUpdateField?: (index: number, newValue: string) => void;
};

const ExtractedFieldsPanel: React.FC<Props> = ({ fields, onUpdateField }) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [tempValue, setTempValue] = useState<string>("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleEditClick = (index: number, value: string | null) => {
    setEditingIndex(index);
    setTempValue(value || "");
    setValidationError(null);
  };

  const validateField = (key: string, value: string): boolean => {
    const validation = FIELD_VALIDATIONS[key];
    if (!validation) return true; // No validation rules for this field
    return validation.validate(value);
  };

  const handleSaveClick = () => {
    if (editingIndex !== null && onUpdateField) {
      const field = fields[editingIndex];
      if (!validateField(field.key, tempValue)) {
        setValidationError(FIELD_VALIDATIONS[field.key]?.errorMessage || "Invalid value");
        return;
      }
      onUpdateField(editingIndex, tempValue);
      setValidationError(null);
    }
    setEditingIndex(null);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveClick();
    }
  };

  return (
    <div style={{
      width: '300px',
      padding: '1rem',
      background: '#fefefe',
      borderLeft: '1px solid #ccc'
    }}>
      <h2>Extracted Fields</h2>
      {fields.length === 0 ? (
        <p>No fields extracted yet.</p>
      ) : (
        <ul style={{ listStyleType: 'none', padding: 0 }}>
          {fields.map((field, index) => (
            <li key={index} style={{ 
              marginBottom: '1rem',
              padding: '0.5rem',
              borderBottom: '1px solid #eee'
            }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.5rem'
              }}>
                <div>
                  <strong>{field.key}:</strong>
                  {FIELD_VALIDATIONS[field.key] && FIELD_VALIDATIONS[field.key].format && (
                    <span style={{ fontSize: '0.8em', color: '#666', marginLeft: '0.5rem' }}>
                      {FIELD_VALIDATIONS[field.key].format}
                    </span>
                  )}
                </div>
                <button 
                  onClick={() => handleEditClick(index, field.value)}
                  style={{
                    padding: '0.25rem 0.75rem',
                    backgroundColor: editingIndex === index ? '#dc3545' : '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer',
                    fontSize: '0.9em'
                  }}
                >
                  {editingIndex === index ? 'Cancel' : 'Edit'}
                </button>
              </div>
              {editingIndex === index ? (
                <div>
                  <input
                    value={tempValue}
                    onChange={(e) => {
                      setTempValue(e.target.value);
                      setValidationError(null);
                    }}
                    onKeyPress={handleKeyPress}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      marginBottom: validationError ? '0.25rem' : '0.5rem',
                      border: validationError ? '1px solid #dc3545' : '1px solid #ced4da',
                      borderRadius: '3px',
                      fontSize: '0.9em'
                    }}
                    placeholder={FIELD_VALIDATIONS[field.key]?.format || ''}
                    autoFocus
                  />
                  {validationError && (
                    <div style={{ color: '#dc3545', fontSize: '0.8em', marginBottom: '0.5rem' }}>
                      {validationError}
                    </div>
                  )}
                  <button 
                    onClick={handleSaveClick}
                    style={{
                      padding: '0.25rem 0.75rem',
                      backgroundColor: '#28a745',
                      color: 'white',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      fontSize: '0.9em',
                      width: '100%'
                    }}
                  >
                    Save
                  </button>
                </div>
              ) : (
                <div style={{ 
                  color: field.value === null ? '#999' : 'inherit',
                  fontSize: '0.95em',
                  padding: '0.25rem 0'
                }}>
                  {field.value === null ? '' : field.value}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default ExtractedFieldsPanel;
