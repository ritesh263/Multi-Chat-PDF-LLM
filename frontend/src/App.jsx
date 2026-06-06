import React, { useState, useRef } from 'react';
import { uploadDocument, sendChatMessage } from './api';

function App() {
  const [query, setQuery] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { role: 'assistant', content: 'Enterprise Intelligence System initialized. Ingest a document dataset to begin analysis.' }
  ]);
  const [isUploading, setIsUploading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  
  const fileInputRef = useRef(null);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const result = await uploadDocument(file);
      setUploadedFiles(prev => [...prev, file.name]);
      
      
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `Successfully ingested and indexed: ${file.name}. Vector matrix updated. You may now query this document.` 
      }]);
    } catch (error) {
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `Ingestion failed: Could not process ${file.name}. Ensure the backend server is running.` 
      }]);
    } finally {
      setIsUploading(false);
      event.target.value = null; 
    }
  };

  
  const handleSearchSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    const userText = query;
    setQuery('');
    setChatHistory(prev => [...prev, { role: 'user', content: userText }]);
    setIsTyping(true);

    try {
      
      const response = await sendChatMessage(userText);
      setChatHistory(prev => [...prev, { role: 'assistant', content: response.answer || response.response }]);
    } catch (error) {
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `⚠️ Connection Error: Unable to reach the AI routing engine. Please verify the backend is active on port 8000.` 
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: '#0b0f19', color: '#f3f4f6', fontFamily: 'sans-serif' }}>
      
      
      <div style={{ width: '280px', backgroundColor: '#111827', borderRight: '1px solid #1f2937', padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#38bdf8', marginBottom: '4px' }}>Enterprise Intelligence</h2>
          <p style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '24px' }}>Research Engine v1.5</p>
          
          
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            style={{ display: 'none' }} 
            accept=".pdf,.txt,.md"
          />
          
          <button 
            onClick={() => fileInputRef.current.click()}
            disabled={isUploading}
            style={{ width: '100%', padding: '12px', backgroundColor: isUploading ? '#374151' : '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: isUploading ? 'not-allowed' : 'pointer', marginBottom: '32px', transition: 'background-color 0.2s' }}
          >
            {isUploading ? 'Indexing Vectors...' : 'Ingest Document ⇪'}
          </button>
          
          <h3 style={{ fontSize: '12px', fontWeight: 'bold', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>Ingested Datasets</h3>
          
          {uploadedFiles.length === 0 ? (
            <div style={{ fontSize: '14px', color: '#6b7280', fontStyle: 'italic' }}>No active documents loaded.</div>
          ) : (
            <ul style={{ listStyleType: 'none', padding: 0, margin: 0, fontSize: '14px', color: '#cbd5e1' }}>
              {uploadedFiles.map((fileName, i) => (
                <li key={i} style={{ padding: '8px 0', borderBottom: '1px solid #1f2937' }}>📄 {fileName}</li>
              ))}
            </ul>
          )}
        </div>
        
        <div style={{ borderTop: '1px dotted #374151', paddingTop: '16px', fontSize: '12px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }}></div>
          Database Node: Connected
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
        
        <div style={{ flex: 1, padding: '40px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {chatHistory.map((msg, index) => (
            <div key={index} style={{ display: 'flex', gap: '16px', maxWidth: '800px', alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '4px', backgroundColor: msg.role === 'user' ? '#2563eb' : '#1f2937', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '12px', flexShrink: 0 }}>
                {msg.role === 'user' ? 'U' : 'AI'}
              </div>
              <div style={{ backgroundColor: msg.role === 'user' ? '#1e3a8a' : '#111827', padding: '16px', borderRadius: '8px', border: '1px solid #1f2937', fontSize: '15px', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                {msg.content}
              </div>
            </div>
          ))}
          {isTyping && (
             <div style={{ display: 'flex', gap: '16px', maxWidth: '800px', alignSelf: 'flex-start' }}>
               <div style={{ width: '32px', height: '32px', borderRadius: '4px', backgroundColor: '#1f2937', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '12px', flexShrink: 0 }}>AI</div>
               <div style={{ padding: '16px', fontSize: '15px', color: '#9ca3af', fontStyle: 'italic' }}>Analyzing semantic vectors...</div>
             </div>
          )}
        </div>

        
        <div style={{ padding: '24px 40px', borderTop: '1px solid #1f2937', backgroundColor: '#0f172a' }}>
          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '12px', maxWidth: '1000px', margin: '0 auto' }}>
            <input 
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Query operational dataset vectors..." 
              disabled={isTyping || isUploading}
              style={{ flex: 1, padding: '14px 20px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#fff', fontSize: '15px', outline: 'none' }}
            />
            <button type="submit" disabled={isTyping || isUploading || !query.trim()} style={{ padding: '14px 28px', backgroundColor: (isTyping || isUploading || !query.trim()) ? '#374151' : '#2563eb', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: (isTyping || isUploading || !query.trim()) ? 'not-allowed' : 'pointer', transition: 'background-color 0.2s' }}>
              Execute Search
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}

export default App;