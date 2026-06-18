const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export const fetchUserProfile = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`);
    if (!response.ok) throw new Error('Failed to load user profile');
    return await response.json();
  } catch (error) {
    console.error("Auth Error:", error);
    return null;
  }
};

export const uploadDocument = async (file, signal) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
    method: 'POST',
    body: formData,
    signal: signal 
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`);
  }

  return await response.json();
};

// UPGRADED: Added selectedDocument to parameters and payload
export const sendChatMessageStream = async (query, chatHistory, selectedDocument, onChunkReceived) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        query: query, 
        history: chatHistory,
        target_document: selectedDocument || "all" // Pass the target to the backend
      }), 
    });
    
    if (!response.ok) throw new Error('Chat generation failed');
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let done = false;
    
    while (!done) {
      const { value, done: readerDone } = await reader.read();
      done = readerDone;
      if (value) {
        const chunkText = decoder.decode(value, { stream: true });
        onChunkReceived(chunkText); 
      }
    }
  } catch (error) {
    console.error("Chat Streaming Error:", error);
    throw error;
  }
};

export const fetchDocumentsList = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/documents/list`)
    if (!response.ok) throw new Error('Failed to fetch document list');
    return await response.json();
  } catch (error) {
    console.error("Fetch Docs Error:", error);
    throw error;
  }
};

export const deleteDocument = async (filename) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/documents/${encodeURIComponent(filename)}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete document');
    return await response.json();
  } catch (error) {
    console.error("Delete Doc Error:", error);
    throw error;
  }
};