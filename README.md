# Multi-Chat-PDF-LLM: Enterprise RAG Assistant

A high-performance, asynchronous Enterprise Retrieval-Augmented Generation (RAG) backend architecture engineered with **FastAPI**, **MongoDB Atlas**, **PyMuPDF**, and the **Google Gemini Pro SDK**. This platform supports multi-tenant document ingestion, automatic semantic splitting, query condensation for multi-turn chats, and low-latency Server-Sent Events (SSE) streaming with adaptive rate-limit recovery loops.

## Key Architectural Highlights

* **Asynchronous Background Task Ingestion Matrix:** Utilizes FastAPI’s non-blocking `BackgroundTasks` thread-pool mapping to offload CPU-bound vector index hot-reloads (`RAGPipelineManager.reload_user_indices`), enabling instantaneous `200 OK` API responses during file processing and deletion.
* **Idempotent Ingestion Shields:** Implements an atomic MongoDB data-integrity pipeline that checks file identity profiles, preventing duplicate database nodes by executing targeted overwrites (`upsert`) on modified assets.
* **Contextual Query Condensation:** Features a history-tracking middleware that evaluates conversational history arrays using a sliding window algorithm, condensing pronoun shifts into precise, self-contained keyword vectors before execution.
* **Fault-Tolerant SSE Stream Engineering:** Delivers a resilient chunked token delivery channel utilizing Server-Sent Events (SSE) wrapped in adaptive exponential backoff interceptors to recover gracefully from upstream AI quota caps (`ResourceExhausted`).
* **Path-Agnostic Environment Pipeline:** Employs absolute resolution file-tree traversals (`Path(__file__).resolve()`) within Pydantic settings base targets, eliminating runtime directory context dependency bugs.

---

## Current Directory Manifest

The project repository currently exposes the operational core gateway, data normalization models, and custom asynchronous delivery channels:

```text
Multi-Chat-PDF-LLM/
└── backend/
    └── app/
        ├── database/       # MongoDB connection pools & active cluster clients
        ├── models/         # Pydantic schema constraints & ODM validation models
        ├── routes/
        │   ├── chat_routes.py      # SSE response streams & session delete endpoints
        │   └── document_routes.py  # Ingestion pipelines & background task workers
        ├── config.py       # Path-resolved global configuration management
        └── main.py         # App entry-point gateway, CORS setup, and SDK hooks
