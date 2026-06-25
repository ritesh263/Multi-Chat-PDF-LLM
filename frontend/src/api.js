// Base URL for your FastAPI backend
const API_BASE = 'http://127.0.0.1:8000';

// Helper function to grab the token and format the Authorization header
const getAuthHeaders = () => {
  const token = localStorage.getItem('rag_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

export const fetchDocumentsList = async () => {
  const response = await fetch(`${API_BASE}/api/documents`, {
    method: 'GET',
    headers: {
      ...getAuthHeaders()
    }
  });

  if (!response.ok) {
    if (response.status === 401) throw new Error("Unauthorized");
    throw new Error("Failed to fetch documents");
  }

  return response.json();
};

export const uploadDocument = async (file, signal) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/api/documents/upload`, {
    method: 'POST',
    // Note: Do NOT set 'Content-Type' when sending FormData. 
    // The browser sets it automatically with the correct boundary.
    headers: {
      ...getAuthHeaders()
    },
    body: formData,
    signal: signal
  });

  if (!response.ok) throw new Error("Upload failed");
  return response.json();
};

export const deleteDocument = async (fileName) => {
  const response = await fetch(`${API_BASE}/api/documents/${fileName}`, {
    method: 'DELETE',
    headers: {
      ...getAuthHeaders()
    }
  });

  if (!response.ok) throw new Error("Delete failed");
  return response.json();
};

export const sendChatMessageStream = async (text, history, targetDoc, onChunk) => {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders() // Show the bouncer our token!
    },
    body: JSON.stringify({
      query: text,
      history: history,
      target_document: targetDoc || "all"
    })
  });

  if (!response.ok) {
    throw new Error(`Chat request failed with status ${response.status}`);
  }

  // Read the streaming response from FastAPI
  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    // Decode the binary chunk into text and pass it to React
    const chunkText = decoder.decode(value, { stream: true });
    onChunk(chunkText);
  }
};