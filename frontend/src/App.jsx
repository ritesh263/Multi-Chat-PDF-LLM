import React, { useState, useRef, useEffect } from 'react';
import { uploadDocument, sendChatMessageStream, fetchDocumentsList, deleteDocument } from './api';

function App() {
  const [query, setQuery] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { role: 'assistant', content: 'Enterprise Intelligence System initialized. Ingest a document dataset to begin analysis.' }
  ]);
  const [isUploading, setIsUploading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  
  const fileInputRef = useRef(null);
 
  useEffect(() => {
    const loadDocs = async () => {
      try {
        const data = await fetchDocumentsList();
        setUploadedFiles(data.documents || []);
      } catch (err) {
        console.error("Could not preload document list:", err);
      }
    };
    loadDocs();
  }, []);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsUploading(true);
    try {
      await uploadDocument(file);
      setUploadedFiles(prev => prev.includes(file.name) ? prev : [...prev, file.name]);
      
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

  const handleFileDelete = async (fileName) => {
    try {
      await deleteDocument(fileName);
      setUploadedFiles(prev => prev.filter(name => name !== fileName));
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `Purged index: ${fileName} has been completely removed from the vector matrix.` 
      }]);
    } catch (error) {
      alert(`Failed to delete ${fileName}`);
    }
  };


  const handleSearchSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    const userText = query;
    setQuery('');
    
    setChatHistory(prev => [
      ...prev, 
      { role: 'user', content: userText },
      { role: 'assistant', content: '' } 
    ]);
    setIsTyping(true); 

    try {
      await sendChatMessageStream(userText, chatHistory, (newChunk) => {
        setIsTyping(false); 
        setChatHistory(prev => {
          const newHistory = [...prev];
          const lastIndex = newHistory.length - 1;
          newHistory[lastIndex] = {
            ...newHistory[lastIndex],
            content: newHistory[lastIndex].content + newChunk
          };
          return newHistory;
        });
      });
    } catch (error) {
      setChatHistory(prev => {
        const newHistory = [...prev];
        newHistory[newHistory.length - 1].content = `Connection Error: Unable to reach the AI routing engine.`;
        return newHistory;
      });
      setIsTyping(false);
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-gray-100 font-sans">
      
      <div className="w-72 bg-gray-900 border-r border-gray-800 p-6 flex flex-col justify-between">
        <div>
          <h2 className="text-lg font-bold text-sky-400 mb-1">Enterprise Intelligence</h2>
          <p className="text-xs text-gray-400 mb-6">Research Engine v1.5</p>
          
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            className="hidden" 
            accept=".pdf,.txt,.md,.docx"
          />
          
          <button 
            onClick={() => fileInputRef.current.click()}
            disabled={isUploading}
            className={`w-full p-3 font-bold rounded-md mb-8 transition-colors ${
              isUploading ? 'bg-gray-700 cursor-not-allowed text-gray-300' : 'bg-blue-600 hover:bg-blue-500 text-white'
            }`}
          >
            {isUploading ? 'Indexing Vectors...' : 'Ingest Document ⇪'}
          </button>
          
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Ingested Datasets</h3>
          
          {uploadedFiles.length === 0 ? (
            <div className="text-sm text-gray-500 italic">No active documents loaded.</div>
          ) : (
            <ul className="list-none p-0 m-0 text-sm text-slate-300">
              {uploadedFiles.map((fileName, i) => (
                <li key={i} className="py-2.5 border-b border-gray-800 flex justify-between items-center group">
                  <span className="truncate max-w-[180px]" title={fileName}>📄 {fileName}</span>
                  <button 
                    onClick={() => handleFileDelete(fileName)}
                    className="text-red-500 opacity-0 group-hover:opacity-100 hover:bg-red-950/50 px-2 py-1 rounded text-xs font-bold transition-all"
                    title="Delete document"
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        
        <div className="pt-4 border-t border-gray-800 text-xs text-emerald-500 flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          Database Node: Connected
        </div>
      </div>

      
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        
       
        <div className="flex-1 p-10 overflow-y-auto flex flex-col gap-6">
          {chatHistory.map((msg, index) => (
            <div 
              key={index} 
              className={`flex gap-4 max-w-4xl ${msg.role === 'user' ? 'self-end flex-row-reverse' : 'self-start'}`}
            >
              <div className={`w-8 h-8 rounded flex items-center justify-center font-bold text-xs shrink-0 ${
                msg.role === 'user' ? 'bg-blue-600' : 'bg-gray-800'
              }`}>
                {msg.role === 'user' ? 'U' : 'AI'}
              </div>
              <div className={`p-4 rounded-lg border text-[15px] leading-relaxed whitespace-pre-wrap ${
                msg.role === 'user' ? 'bg-blue-900/40 border-blue-800/50' : 'bg-gray-900 border-gray-800'
              }`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isTyping && (
             <div className="flex gap-4 max-w-4xl self-start items-center">
               <div className="w-8 h-8 rounded bg-gray-800 flex items-center justify-center font-bold text-xs shrink-0">AI</div>
               <div className="p-4 text-[15px] text-gray-400 italic">Analyzing semantic vectors...</div>
             </div>
          )}
        </div>

        <div className="p-6 border-t border-gray-800 bg-slate-900/50">
          <form onSubmit={handleSearchSubmit} className="flex gap-3 max-w-5xl mx-auto">
            <input 
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Query operational dataset vectors..." 
              disabled={isTyping || isUploading}
              className="flex-1 p-3.5 bg-slate-800 border border-slate-700 rounded-lg text-white text-[15px] outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all disabled:opacity-50"
            />
            <button 
              type="submit" 
              disabled={isTyping || isUploading || !query.trim()} 
              className={`px-7 py-3.5 font-bold rounded-lg transition-colors ${
                (isTyping || isUploading || !query.trim()) ? 'bg-gray-700 text-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500 text-white'
              }`}
            >
              Execute Search
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}

export default App;