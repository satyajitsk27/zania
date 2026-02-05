import { useState } from 'react';

export default function App() {
  const [questionsFile, setQuestionsFile] = useState(null);
  const [documentFile, setDocumentFile] = useState(null);
  const [qaPairs, setQaPairs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!questionsFile || !documentFile) {
      setError('Please upload both a questions file and a document file.');
      return;
    }

    const formData = new FormData();
    formData.append('questions_file', questionsFile);
    formData.append('document_file', documentFile);

    setLoading(true);
    setQaPairs([]);
    setError('');

    try {
      const res = await fetch('http://localhost:3000/answer', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      
      // Check for errors in response
      if (data.error) {
        setError(data.error);
      } else if (data.qa_pairs && Array.isArray(data.qa_pairs)) {
        setQaPairs(data.qa_pairs);
      } else {
        setError('Unexpected response format from server.');
      }
    } catch (error) {
      setError(`Network error: ${error.message}. Please make sure the backend server is running.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      padding: '40px', 
      maxWidth: '800px', 
      margin: '0 auto',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      <h1 style={{ marginBottom: '12px', color: '#333' }}>Document Q&A System</h1>
      <p style={{ marginBottom: '32px', color: '#666' }}>
        Upload a questions file (JSON) and a document file (PDF or JSON) to get answers grounded in your document.
      </p>
      
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '20px' }}>
          <label style={{ 
            display: 'block', 
            marginBottom: '8px',
            fontWeight: '500',
            color: '#555'
          }}>
            1. Upload Questions File (JSON):
          </label>
          <input
            type="file"
            accept=".json"
            onChange={(e) => {
              setQuestionsFile(e.target.files[0]);
              setError('');
            }}
            style={{
              padding: '10px',
              border: '2px solid #ddd',
              borderRadius: '6px',
              width: '100%',
              cursor: 'pointer'
            }}
          />
          <p style={{ fontSize: '13px', color: '#888', marginTop: '4px' }}>
            Format: ["Question 1?", "Question 2?"] or {'{'}questions: ["Q1?", "Q2?"]{'}'}
          </p>
        </div>
        
        <div style={{ marginBottom: '20px' }}>
          <label style={{ 
            display: 'block', 
            marginBottom: '8px',
            fontWeight: '500',
            color: '#555'
          }}>
            2. Upload Document File (PDF or JSON):
          </label>
          <input
            type="file"
            accept=".pdf,.json"
            onChange={(e) => {
              setDocumentFile(e.target.files[0]);
              setError('');
            }}
            style={{
              padding: '10px',
              border: '2px solid #ddd',
              borderRadius: '6px',
              width: '100%',
              cursor: 'pointer'
            }}
          />
          <p style={{ fontSize: '13px', color: '#888', marginTop: '4px' }}>
            The document that contains the information to answer your questions
          </p>
        </div>
        
        <button 
          type="submit" 
          disabled={(!questionsFile || !documentFile) || loading}
          style={{
            padding: '12px 24px',
            backgroundColor: (!questionsFile || !documentFile) || loading ? '#ccc' : '#4A90E2',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontSize: '16px',
            fontWeight: '500',
            cursor: (!questionsFile || !documentFile) || loading ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.2s'
          }}
          onMouseOver={(e) => {
            if (questionsFile && documentFile && !loading) e.target.style.backgroundColor = '#357ABD';
          }}
          onMouseOut={(e) => {
            if (questionsFile && documentFile && !loading) e.target.style.backgroundColor = '#4A90E2';
          }}
        >
          {loading ? 'Processing...' : 'Get Answers'}
        </button>
      </form>

      {/* Display Error Message */}
      {error && (
        <div style={{
          marginTop: '24px',
          padding: '16px',
          backgroundColor: '#fee',
          border: '2px solid #fcc',
          borderRadius: '6px',
          color: '#c33'
        }}>
          <strong>⚠️ Error:</strong>
          <p style={{ margin: '8px 0 0 0' }}>{error}</p>
        </div>
      )}

      {/* Display Q&A Pairs */}
      {qaPairs.length > 0 && (
        <div style={{ marginTop: '32px' }}>
          <h2 style={{ color: '#333', marginBottom: '16px' }}>
            Questions & Answers ({qaPairs.length} found)
          </h2>
          {qaPairs.map((qa, index) => (
            <div 
              key={index}
              style={{
                marginBottom: '20px',
                padding: '16px',
                border: '2px solid #ddd',
                borderRadius: '6px',
                backgroundColor: '#f9f9f9'
              }}
            >
              <div style={{ marginBottom: '12px' }}>
                <strong style={{ color: '#4A90E2', fontSize: '16px' }}>Q{index + 1}:</strong>
                <p style={{ margin: '8px 0 0 0', color: '#333' }}>{qa.question}</p>
              </div>
              <div style={{ marginBottom: qa.source ? '12px' : '0' }}>
                <strong style={{ color: '#27ae60', fontSize: '16px' }}>Answer:</strong>
                <p style={{ margin: '8px 0 0 0', color: '#555' }}>{qa.answer}</p>
              </div>
              {qa.source && qa.source.trim() !== '' && (
                <div style={{
                  marginTop: '8px',
                  padding: '12px',
                  backgroundColor: '#f0f7ff',
                  borderLeft: '4px solid #4A90E2',
                  borderRadius: '4px'
                }}>
                  <strong style={{ color: '#666', fontSize: '14px' }}>📄 Source:</strong>
                  <p style={{ 
                    margin: '4px 0 0 0', 
                    color: '#555',
                    fontSize: '14px',
                    fontStyle: 'italic'
                  }}>"{qa.source}"</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}