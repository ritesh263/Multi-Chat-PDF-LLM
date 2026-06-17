# Multi-Chat-PDF-LLM: Enterprise RAG Assistant

A high-performance, full-stack Enterprise Hybrid Retrieval-Augmented Generation (RAG) architecture engineered with **FastAPI**, **React**, **MongoDB Atlas**, and the **Google Gemini Pro SDK**. 

This platform supports multi-tenant document ingestion, real-time Markdown-rendered chat streaming, and automatic semantic splitting. By utilizing a custom-built hybrid search pipeline, it avoids heavy abstraction layers to deliver a stateless, horizontally scalable, and highly optimized AI research tool.

## Key Architectural Highlights

### Custom Hybrid Search Engine (Zero LangChain / Zero FAISS)
Bypasses the abstraction bloat of LangChain and the stateless constraints of local FAISS indexes. Instead, this system utilizes a native, granular pipeline combining **Rank-BM25** (lexical exact-matching) with **Gemini Embeddings** (semantic vector search) directly coupled with MongoDB. This guarantees horizontally scalable infrastructure and airtight real-time database mutations.

### Asynchronous Background Task Ingestion Matrix
Utilizes FastAPI’s non-blocking `BackgroundTasks` thread-pool mapping to offload CPU-bound vector index hot-reloads. This enables instantaneous `200 OK` API responses during complex file parsing, chunking, and database syncing.

### Stream-Interrupted Upload Aborts
Client-side `AbortController` integrations wired directly to backend asynchronous cancellation hooks. If a user halts a multi-megabyte PDF ingestion mid-stream, the backend instantly intercepts the disconnect, drops the active pipeline, and purges temporary OS files to prevent memory leaks.

### Zero-Ghost Cascading Deletes
Features a comprehensive data-integrity pipeline. When a document is removed, the system executes a cascading purge of all orphaned vector chunks in MongoDB and triggers a synchronized RAM index rebuild. This prevents "Ghost Vectors" and ensures absolute data privacy.

### Fault-Tolerant SSE Stream Engineering & Query Condensation
Delivers resilient chunked token delivery utilizing Server-Sent Events (SSE) wrapped in adaptive exponential backoff interceptors to recover gracefully from upstream AI quota caps (`ResourceExhausted`). A history-tracking middleware evaluates conversation arrays, condensing pronoun shifts into precise keyword vectors before execution.

### Markdown-Native Enterprise UI
A highly responsive React and Tailwind CSS frontend interface featuring dynamic Markdown rendering (`react-markdown`), ChatGPT-style syntax highlighting (`react-syntax-highlighter`), persistent `localStorage` session caching, and pre-computed prompt starter chips.

---

## Technology Stack

* **Frontend:** React.js, Tailwind CSS v4, Vite, React Markdown
* **Backend:** Python 3, FastAPI, Uvicorn, Server-Sent Events (SSE)
* **Database & Storage:** MongoDB Atlas, Motor (Async MongoDB Driver)
* **AI & Processing:** Google Gemini 1.5 Flash / Pro, Rank-BM25, NLTK, PyMuPDF
* **Deployment:** Render (Cloud Native Web Services)

---

## System Architecture Manifest

```text
Multi-Chat-PDF-LLM/
├── frontend/                 # Client-Side Application
│   ├── src/
│   │   ├── api.js            # Fetch interceptors and SSE stream handling
│   │   ├── App.jsx           # Main UI, chat logic, and Markdown rendering
│   │   └── index.css         # Tailwind v4 configuration
│   └── package.json
│
└── backend/                  # Server-Side Application
    ├── app/
    │   ├── auth/             # Multi-tenant user validation and dependencies
    │   ├── database/         # MongoDB connection pools & active cluster clients
    │   ├── models/           # Pydantic schema constraints & ODM validation models
    │   ├── rag/              # Core AI Pipeline
    │   │   ├── hybrid_retriever.py # BM25 + Vector fusion algorithm
    │   │   ├── pipeline.py         # RAG pipeline manager and index loader
    │   │   └── text_processor.py   # NLTK sentence boundary chunking
    │   ├── routes/
    │   │   ├── chat_routes.py      # SSE response streams
    │   │   └── document_routes.py  # Ingestion pipelines & background tasks
    │   ├── services/
    │   │   └── ai_service.py       # Gemini SDK API wrappers
    │   ├── config.py         # Path-resolved global configuration management
    │   └── main.py           # App entry-point gateway and CORS setup
    └── requirements.txt
