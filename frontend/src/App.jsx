import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { uploadDocument, sendChatMessageStream, fetchDocumentsList, deleteDocument } from './api';

function App() {
  const defaultGreeting = { role: 'assistant', content: 'Enterprise Intelligence System initialized. Ingest a document dataset to begin analysis.' };
  
  const [query, setQuery] = useState('');
  const [chatHistory, setChatHistory] = useState([defaultGreeting]);
  const [isUploading, setIsUploading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  
  const [savedSessions, setSavedSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);

  // --- NEW STATE: Document Targeting & Renaming ---
  const [selectedDocument, setSelectedDocument] = useState(''); 
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  
  const fileInputRef = useRef(null);
  const uploadAbortController = useRef(null);

  useEffect(() => {
    const loadDocs = async () => {
      try {
        const data = await fetchDocumentsList();
        setUploadedFiles(data.documents || []);
      } catch (err) {
        console.error("Could not preload document list:", err);
      }
    };
    
    const storedSessions = localStorage.getItem('rag_chat_sessions');
    if (storedSessions) {
      setSavedSessions(JSON.parse(storedSessions));
    }
    
    loadDocs();
  }, []);

  useEffect(() => {
    if (currentSessionId && chatHistory.length > 1) {
      setSavedSessions(prev => {
        const existingIndex = prev.findIndex(s => s.id === currentSessionId);
        let updated = [...prev];
        
        if (existingIndex >= 0) {
          // UPGRADE: Only update history, preserve the title if they renamed it!
          updated[existingIndex] = { ...updated[existingIndex], history: chatHistory };
        } else {
          // First time saving: auto-generate title
          const title = chatHistory[1].content.substring(0, 25) + (chatHistory[1].content.length > 25 ? '...' : '');
          updated = [{ id: currentSessionId, title, history: chatHistory }, ...updated];
        }
        
        localStorage.setItem('rag_chat_sessions', JSON.stringify(updated));
        return updated;
      });
    }
  }, [chatHistory, currentSessionId]);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsUploading(true);
    uploadAbortController.current = new AbortController(); 
    
    try {
      await uploadDocument(file, uploadAbortController.current.signal);
      
      setUploadedFiles(prev => prev.includes(file.name) ? prev : [...prev, file.name]);
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `Successfully ingested and indexed: **${file.name}**. Vector matrix updated. You may now query this document.` 
      }]);
    } catch (error) {
      if (error?.name === 'AbortError') {
        setChatHistory(prev => [...prev, { role: 'assistant', content: `⚠️ Ingestion aborted by user. ${file.name} was safely discarded.` }]);
      } else {
        setChatHistory(prev => [...prev, { role: 'assistant', content: `Ingestion failed. Ensure the backend server is running.` }]);
      }
    } finally {
      setIsUploading(false);
      uploadAbortController.current = null;
      event.target.value = null; 
    }
  };

  const cancelUpload = () => {
    if (uploadAbortController.current) {
      uploadAbortController.current.abort();
    }
  };

  const handleFileDelete = async (fileName) => {
    try {
      await deleteDocument(fileName);
      setUploadedFiles(prev => prev.filter(name => name !== fileName));
      if (selectedDocument === fileName) setSelectedDocument('');
    } catch (error) {
      alert(`Failed to delete ${fileName}`);
    }
  };

  const handleNewChat = () => {
    const newId = Date.now().toString();
    setChatHistory([defaultGreeting]);
    setCurrentSessionId(newId);
    setQuery('');

    setSavedSessions(prev => {
      if (prev.length > 0 && prev[0].title === "New Chat...") return prev;
      const newSession = { id: newId, title: "New Chat...", history: [defaultGreeting] };
      const updated = [newSession, ...prev];
      localStorage.setItem('rag_chat_sessions', JSON.stringify(updated));
      return updated;
    });
  };

  const loadSession = (id) => {
    if (editingSessionId === id) return; // Prevent loading while editing
    const session = savedSessions.find(s => s.id === id);
    if (session) {
      setChatHistory(session.history);
      setCurrentSessionId(id);
    }
  };

  const deleteSession = (e, id) => {
    e.stopPropagation(); 
    const updated = savedSessions.filter(s => s.id !== id);
    setSavedSessions(updated);
    localStorage.setItem('rag_chat_sessions', JSON.stringify(updated));
    if (currentSessionId === id) {
      setChatHistory([defaultGreeting]);
      setCurrentSessionId(null);
    }
  };

  // --- NEW: Renaming Functions ---
  const startEditingTitle = (e, session) => {
    e.stopPropagation();
    setEditingSessionId(session.id);
    setEditTitle(session.title);
  };

  const saveEditedTitle = (id) => {
    if (!editTitle.trim()) {
      setEditingSessionId(null);
      return;
    }
    setSavedSessions(prev => {
      const updated = prev.map(s => s.id === id ? { ...s, title: editTitle.trim() } : s);
      localStorage.setItem('rag_chat_sessions', JSON.stringify(updated));
      return updated;
    });
    setEditingSessionId(null);
  };

  const executeSearch = async (searchText) => {
    if (!searchText.trim()) return;
    
    let activeId = currentSessionId;
    if (!activeId) {
      activeId = Date.now().toString();
      setCurrentSessionId(activeId);
    }
    
    setQuery(''); 
    const currentHistory = [...chatHistory]; 
    
    setChatHistory(prev => [
      ...prev, 
      { role: 'user', content: searchText },
      { role: 'assistant', content: '' } 
    ]);
    setIsTyping(true); 

    try {
      // UPGRADE: Passing selectedDocument to the API
      await sendChatMessageStream(searchText, currentHistory, selectedDocument, (newChunk) => {
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
        newHistory[newHistory.length - 1].content = `⚠️ Connection Error: Unable to reach the AI routing engine.`;
        return newHistory;
      });
      setIsTyping(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    executeSearch(query);
  };

  const starterChips = [
    "Summarize the key points of my latest document.",
    "What are the main risks or warnings mentioned?",
    "Extract any important dates, names, or metrics.",
    "Explain the core concept of the document simply."
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-gray-100 font-sans overflow-hidden">
      
      {/* Sidebar */}
      <div className="w-72 bg-gray-900 border-r border-gray-800 p-6 flex flex-col h-full">
        <div className="shrink-0">
          <h2 className="text-lg font-bold text-sky-400 mb-1">Enterprise Intelligence</h2>
          <p className="text-xs text-gray-400 mb-6">Research Engine v1.5</p>
          
          <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.txt,.md,.docx" />
          
          {isUploading ? (
            <button onClick={cancelUpload} className="w-full p-3 font-bold rounded-md mb-3 transition-all bg-rose-600 hover:bg-rose-500 text-white flex justify-center items-center gap-2 shadow-lg shadow-rose-900/20">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              Cancel Indexing ✕
            </button>
          ) : (
            <button onClick={() => fileInputRef.current.click()} className="w-full p-3 font-bold rounded-md mb-3 transition-colors bg-blue-600 hover:bg-blue-500 text-white shadow-lg">
              Ingest Document ⇪
            </button>
          )}

          <button onClick={handleNewChat} disabled={isUploading || isTyping} className="w-full p-3 font-bold rounded-md mb-6 transition-colors bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex justify-center items-center gap-2">
            ＋ New Conversation
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto pr-1 space-y-8">
          <div>
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Ingested Datasets</h3>
            {uploadedFiles.length === 0 ? (
              <div className="text-sm text-gray-500 italic">No active documents.</div>
            ) : (
              <ul className="list-none p-0 m-0 text-sm text-slate-300">
                {uploadedFiles.map((fileName, i) => (
                  <li key={i} className="py-2.5 border-b border-gray-800 flex justify-between items-center group">
                    <span className="truncate max-w-[180px]" title={fileName}>📄 {fileName}</span>
                    <button onClick={() => handleFileDelete(fileName)} className="text-red-500 opacity-0 group-hover:opacity-100 hover:bg-red-950/50 px-2 py-1 rounded text-xs font-bold transition-all" title="Delete document">✕</button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Recent Chats</h3>
            {savedSessions.length === 0 ? (
              <div className="text-sm text-gray-500 italic">No previous chats.</div>
            ) : (
              <ul className="list-none p-0 m-0 text-sm text-slate-300">
                {savedSessions.map((session) => (
                  <li 
                    key={session.id} 
                    onClick={() => loadSession(session.id)}
                    className={`py-2 border-b border-gray-800 flex justify-between items-center group cursor-pointer transition-colors ${currentSessionId === session.id ? 'text-sky-400 font-medium' : 'hover:text-white'}`}
                  >
                    {/* UPGRADE: Inline Renaming Input */}
                    {editingSessionId === session.id ? (
                      <input 
                        type="text"
                        autoFocus
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onBlur={() => saveEditedTitle(session.id)}
                        onKeyDown={(e) => e.key === 'Enter' && saveEditedTitle(session.id)}
                        onClick={(e) => e.stopPropagation()}
                        className="flex-1 bg-slate-950 border border-sky-500/50 text-white px-2 py-1 rounded text-xs outline-none mr-2"
                      />
                    ) : (
                      <span className="truncate max-w-[150px]" title={session.title}>💬 {session.title}</span>
                    )}

                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {editingSessionId !== session.id && (
                        <button onClick={(e) => startEditingTitle(e, session)} className="text-gray-400 hover:text-sky-400 px-1.5 py-1 rounded text-xs font-bold transition-all" title="Rename chat">✎</button>
                      )}
                      <button onClick={(e) => deleteSession(e, session.id)} className="text-red-500 hover:bg-red-950/50 px-1.5 py-1 rounded text-xs font-bold transition-all" title="Delete chat">✕</button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="shrink-0 pt-4 mt-4 border-t border-gray-800 text-xs text-emerald-500 flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          Database Node: Connected
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        
        <div className="flex-1 p-10 overflow-y-auto flex flex-col gap-6">
          {chatHistory.map((msg, index) => (
            <div key={index} className={`flex gap-4 max-w-4xl ${msg.role === 'user' ? 'self-end flex-row-reverse' : 'self-start'}`}>
              <div className={`w-8 h-8 rounded flex items-center justify-center font-bold text-xs shrink-0 ${msg.role === 'user' ? 'bg-blue-600' : 'bg-gray-800'}`}>
                {msg.role === 'user' ? 'U' : 'AI'}
              </div>
              <div className={`p-4 rounded-lg border text-[15px] leading-relaxed max-w-full overflow-hidden ${msg.role === 'user' ? 'bg-blue-900/40 border-blue-800/50 whitespace-pre-wrap' : 'bg-gray-900 border-gray-800 text-slate-200'}`}>
                
                {msg.role === 'user' ? (
                  msg.content
                ) : (
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({node, ...props}) => <p className="mb-4 last:mb-0" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc ml-6 mb-4 space-y-1" {...props} />,
                      ol: ({node, ...props}) => <ol className="list-decimal ml-6 mb-4 space-y-1" {...props} />,
                      li: ({node, ...props}) => <li className="text-slate-300" {...props} />,
                      strong: ({node, ...props}) => <strong className="font-semibold text-white" {...props} />,
                      code({node, inline, className, children, ...props}) {
                        const match = /language-(\w+)/.exec(className || '');
                        return !inline && match ? (
                          <div className="my-4 rounded-md overflow-hidden border border-gray-700">
                            <SyntaxHighlighter {...props} children={String(children).replace(/\n$/, '')} style={vscDarkPlus} language={match[1]} PreTag="div" customStyle={{ margin: 0, padding: '1rem', fontSize: '0.875rem' }} />
                          </div>
                        ) : (
                          <code {...props} className="bg-gray-800 text-sky-300 px-1.5 py-0.5 rounded text-sm font-mono border border-gray-700">{children}</code>
                        )
                      }
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                )}

              </div>
            </div>
          ))}

          {chatHistory.length === 1 && !isTyping && uploadedFiles.length > 0 && (
            <div className="max-w-4xl pt-8 flex flex-wrap gap-3">
              {starterChips.map((chipText, i) => (
                <button key={i} onClick={() => executeSearch(chipText)} className="px-4 py-2.5 bg-slate-800/50 hover:bg-blue-900/40 border border-slate-700 hover:border-blue-500 text-sm text-slate-300 hover:text-blue-400 rounded-full transition-all text-left">
                  {chipText}
                </button>
              ))}
            </div>
          )}

          {isTyping && (
             <div className="flex gap-4 max-w-4xl self-start items-center">
               <div className="w-8 h-8 rounded bg-gray-800 flex items-center justify-center font-bold text-xs shrink-0">AI</div>
               <div className="p-4 text-[15px] text-gray-400 italic flex items-center gap-2">
                 Analyzing semantic vectors <span className="flex gap-1"><span className="w-1 h-1 bg-gray-500 rounded-full animate-bounce"></span><span className="w-1 h-1 bg-gray-500 rounded-full animate-bounce delay-100"></span><span className="w-1 h-1 bg-gray-500 rounded-full animate-bounce delay-200"></span></span>
               </div>
             </div>
          )}
        </div>

        <div className="p-6 border-t border-gray-800 bg-slate-900/50 flex flex-col gap-3">
          
          {/* UPGRADE: Target Document Selector Dropdown */}
          {uploadedFiles.length > 0 && (
            <div className="flex items-center gap-3 max-w-5xl mx-auto w-full px-1">
              <span className="text-[11px] font-bold text-gray-500 uppercase tracking-widest">Query Target:</span>
              <select 
                value={selectedDocument} 
                onChange={(e) => setSelectedDocument(e.target.value)}
                disabled={isTyping || isUploading}
                className="bg-slate-950 border border-slate-800 text-xs text-sky-400 rounded px-3 py-1.5 outline-none focus:border-sky-500 transition-colors disabled:opacity-50 cursor-pointer"
              >
                <option value="">All Active Documents</option>
                {uploadedFiles.map(f => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>
          )}

          <form onSubmit={handleSearchSubmit} className="flex gap-3 max-w-5xl mx-auto w-full">
            <input 
              type="text" value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="Query operational dataset vectors..." 
              disabled={isTyping || isUploading}
              className="flex-1 p-3.5 bg-slate-800 border border-slate-700 rounded-lg text-white text-[15px] outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all disabled:opacity-50 shadow-inner"
            />
            <button type="submit" disabled={isTyping || isUploading || !query.trim()} className={`px-7 py-3.5 font-bold rounded-lg transition-colors shadow-lg ${(isTyping || isUploading || !query.trim()) ? 'bg-gray-700 text-gray-400 cursor-not-allowed shadow-none' : 'bg-blue-600 hover:bg-blue-500 text-white'}`}>
              Execute Search
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}

export default App;