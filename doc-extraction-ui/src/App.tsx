import React, { useState, useEffect } from 'react';
import DocumentViewer from './components/DocumentViewer';
import ExtractedFieldsPanel from './components/ExtractedFieldsPanel';
import Sidebar from './components/Sidebar';
import { v4 as uuidv4 } from 'uuid';

// Add type definitions at the top
type Field = {
  key: string;
  value: string | null;
};

type Document = {
  id: string;
  name: string;
  url: string;
  fields: Field[];
};

// Add passport field definitions at the top
const PASSPORT_FIELDS = [
  'full_name',
  'date_of_birth',
  'country',
  'issue_date',
  'expiration_date'
];

function App() {
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [fields, setFields] = useState<Field[]>([]);
  const [recentDocs, setRecentDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingDocument, setLoadingDocument] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRecentDocuments = async () => {
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/documents');
      if (!response.ok) {
        throw new Error('Failed to fetch recent documents');
      }
      const data = await response.json();
      
      // Transform the backend data to match our frontend Document type
      const transformedDocs = data.map((doc: any) => ({
        id: String(doc.id),
        name: doc.filename,
        url: null, // We'll load this when the document is selected
        fields: doc.fields.map((field: any) => ({
          key: field.key,
          value: field.value
        }))
      }));
      
      setRecentDocs(transformedDocs);
    } catch (error) {
      console.error('Error fetching recent documents:', error);
      setError('Failed to load recent documents. Please try again later.');
    }
  };

  useEffect(() => {
    fetchRecentDocuments();
  }, []);

  const handleUpload = (file: File) => {
    const url = URL.createObjectURL(file);
    setDocumentUrl(url);
    setSelectedFile(file);
    setFields([]);
    setUploadSuccess(true); 
    setTimeout(() => setUploadSuccess(false), 5000);
  };

  const handleExtractNew = async () => {
    if (!selectedFile) {
      alert("Please upload a document first.");
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("http://localhost:8000/classify-document", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Extraction failed");

      const data = await response.json();
      let parsedFields: any;

      if ('raw_output' in data.fields) {
        // Clean ```json ... ``` wrapping
        const raw = data.fields.raw_output;
        const cleaned = raw.replace(/```json|```/g, '').trim();

        try {
          const parsed = JSON.parse(cleaned);
          parsedFields = parsed.document_content ?? parsed;
        } catch (e) {
          console.error("JSON parse error:", e);
          parsedFields = { raw_output: raw }; // fallback
        }
      } else {
        parsedFields = data.fields.document_content ?? data.fields;
      }

      // Create a complete set of fields with all expected fields
      const existingFields = Object.entries(parsedFields).reduce((acc, [key, value]) => {
        acc[key] = value === null ? null : String(value);
        return acc;
      }, {} as Record<string, string | null>);

      const completeFields = PASSPORT_FIELDS.map(key => ({
        key,
        value: existingFields[key] || null
      }));

      const newDoc = {
        id: String(data.document_id),
        name: data.filename || `Document ${recentDocs.length + 1}`,
        url: documentUrl!,
        fields: completeFields,
      };

      setFields(completeFields);
      setRecentDocs([newDoc, ...recentDocs]);
    } catch (err) {
      console.error(err);
      setError("Failed to extract fields.");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateField = async (index: number, newValue: string) => {
    try {
      const field = fields[index];
      const currentDoc = recentDocs[0]; // Get the current document
      
      if (!currentDoc) {
        throw new Error("No document selected");
      }

      const response = await fetch("http://localhost:8000/update-field", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          document_id: currentDoc.id,
          key: field.key,
          value: newValue,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to update field");
      }

      // Update local state after successful backend update
      setFields((prevFields) => {
        const updated = [...prevFields];
        updated[index] = { ...updated[index], value: newValue };
        return updated;
      });

      // Also update the field in recentDocs
      setRecentDocs((prevDocs) => {
        const updated = [...prevDocs];
        const docIndex = updated.findIndex(doc => doc.id === currentDoc.id);
        if (docIndex !== -1) {
          updated[docIndex] = {
            ...updated[docIndex],
            fields: updated[docIndex].fields.map((f, i) => 
              i === index ? { ...f, value: newValue } : f
            )
          };
        }
        return updated;
      });
    } catch (error) {
      console.error("Error updating field:", error);
      alert("Failed to update field. Please try again.");
    }
  };

  const handleSelectRecent = async (id: string) => {
    setError(null);
    setLoadingDocument(true);
    try {
      // First find the document in our local state to get its fields
      const doc = recentDocs.find((d) => d.id === id);
      if (!doc) return;

      // Create a complete set of fields, including empty ones
      const existingFields = doc.fields.reduce((acc, field) => {
        acc[field.key] = field.value;
        return acc;
      }, {} as Record<string, string | null>);

      // Create the complete fields array with all expected fields
      const completeFields = PASSPORT_FIELDS.map(key => ({
        key,
        value: existingFields[key] || null
      }));

      // Set the complete fields
      setFields(completeFields);

      // Fetch the actual document content from the backend
      const response = await fetch(`http://localhost:8000/documents/${id}`);
      if (!response.ok) {
        throw new Error('Failed to fetch document content');
      }
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setDocumentUrl(url);

      // Update the document URL in recentDocs
      setRecentDocs(prevDocs => 
        prevDocs.map(d => 
          d.id === id ? { ...d, url } : d
        )
      );
    } catch (error) {
      console.error('Error fetching document:', error);
      setError('Failed to load document content. Please try again.');
      setDocumentUrl(null);
    } finally {
      setLoadingDocument(false);
    }
  };

  const buttonStyle: React.CSSProperties = {
    padding: '0.5rem 1rem',
    margin: '0.5rem',
    backgroundColor: '#007BFF',
    color: 'white',
    border: 'none',
    borderRadius: '5px',
    cursor: 'pointer',
    fontSize: '14px',
    transition: 'background-color 0.2s ease'
  };

  const buttonHoverStyle: React.CSSProperties = {
    ...buttonStyle,
    backgroundColor: '#0056b3'
  };

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      fontFamily: 'Arial, sans-serif',
      overflow: 'hidden'
    }}>
      <Sidebar
        documents={recentDocs}
        onSelect={handleSelectRecent}
        onExtractNew={handleExtractNew}
      />
      <div style={{
        flex: 1,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '1rem'
      }}>
        <h1 style={{ textAlign: "center" }}>Document Viewer</h1>
        {error && (
          <p style={{ color: 'red', textAlign: 'center', margin: '1rem 0' }}>
            {error}
          </p>
        )}
        <DocumentViewer documentUrl={documentUrl} onUpload={handleUpload} />
        {uploadSuccess && (
          <p style={{ textAlign: "center", color: "black", marginTop: "0.5rem" }}>
            ✅ Document uploaded successfully
          </p>
        )}
        {(loading || loadingDocument) && (
          <p style={{ textAlign: 'center' }}>
            {loading ? 'Extracting fields...' : 'Loading document...'}
          </p>
        )}
      </div>
      <ExtractedFieldsPanel fields={fields} onUpdateField={handleUpdateField} />
    </div>
  );
}

export default App;
