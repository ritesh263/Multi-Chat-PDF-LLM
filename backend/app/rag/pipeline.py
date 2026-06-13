import google.generativeai as genai
from typing import List, Dict, Any
import numpy as np
from rank_bm25 import BM25Okapi

class LocalVectorRetriever:
    def __init__(self, user_id: str, chunks: List[Dict[str, Any]]):
        self.user_id = user_id
        self.chunks = chunks
        self.embeddings = []
        self.vector_matrix = None
        self.bm25_engine = None 

    def initialize_vector_space(self):
        """Compiles chunks into a numerical matrix and initializes BM25 tokenization."""
        if not self.chunks:
            return
            
        valid_chunks = []
        vectors = []
        tokenized_corpus = []
        
        for chunk in self.chunks:
            if "embedding" in chunk and chunk["embedding"]:
                vectors.append(chunk["embedding"])
                valid_chunks.append(chunk)
                tokenized_corpus.append(chunk["text"].lower().split())
                
        if vectors:
            self.chunks = valid_chunks
            self.vector_matrix = np.array(vectors, dtype=np.float32)
            norms = np.linalg.norm(self.vector_matrix, axis=1, keepdims=True)
            self.vector_matrix = np.divide(self.vector_matrix, norms, out=np.zeros_like(self.vector_matrix), where=norms!=0)
            
            self.bm25_engine = BM25Okapi(tokenized_corpus)

    def retrieve(self, search_query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Executes a Hybrid Fusion scan (Semantic Math + Exact Keywords)."""
        if not self.chunks or self.vector_matrix is None or len(self.vector_matrix) == 0:
            return []

        try:
            query_embedding_response = genai.embed_content(
                model="models/gemini-embedding-001",
                content=search_query,
                task_type="retrieval_query"
            )
            query_vector = np.array(query_embedding_response["embedding"], dtype=np.float32)
            query_norm = np.linalg.norm(query_vector)
            if query_norm > 0: query_vector /= query_norm

            vector_scores = np.dot(self.vector_matrix, query_vector)
            if np.max(vector_scores) > 0:
                vector_scores = vector_scores / np.max(vector_scores) 

            tokenized_query = search_query.lower().split()
            bm25_scores = self.bm25_engine.get_scores(tokenized_query)
            if np.max(bm25_scores) > 0:
                bm25_scores = bm25_scores / np.max(bm25_scores)

            hybrid_scores = (vector_scores * 0.7) + (bm25_scores * 0.3)
            
            top_indices = np.argsort(hybrid_scores)[::-1][:top_k]
            
            matched_chunks = []
            for idx in top_indices:
                chunk = self.chunks[idx]
                matched_chunks.append({
                    "text": chunk["text"],
                    "metadata": {
                        "filename": chunk.get("filename", "Unknown Resource"),
                        "page_number": chunk.get("page_number", 1),
                        "score": float(hybrid_scores[idx])
                    }
                })
            return matched_chunks
        except Exception as e:
            print(f"Hybrid matching engine aborted: {str(e)}")
            return []
        
        
class RAGPipelineManager:
    _active_retrievers: Dict[str, LocalVectorRetriever] = {}

    @classmethod
    def get_retriever(cls, user_id: str) -> LocalVectorRetriever:
        if user_id not in cls._active_retrievers:
            cls._active_retrievers[user_id] = LocalVectorRetriever(user_id, [])
        return cls._active_retrievers[user_id]

    @classmethod
    def clear_retriever(cls, user_id: str):
        if user_id in cls._active_retrievers:
            del cls._active_retrievers[user_id]

    @classmethod
    async def reload_user_indices(cls, user_id: str, db) -> LocalVectorRetriever:
        """Pulls text segments out of MongoDB, handles missing embeddings, and updates cache."""
        print(f"📡 Rebuilding document vector memory for profile: {user_id}")
        
        documents = await db["documents"].find({"user_id": user_id}).to_list(length=1000)
        doc_map = {doc["_id"]: doc["filename"] for doc in documents}

        if not doc_map:
            cls.clear_retriever(user_id)
            return cls.get_retriever(user_id)

        chunks_cursor = db["chunks"].find({"document_id": {"$in": list(doc_map.keys())}})
        raw_chunks = await chunks_cursor.to_list(length=10000)
        
        unembedded_texts = []
        unembedded_indices = []
        
        for idx, chunk in enumerate(raw_chunks):
            chunk["filename"] = doc_map.get(chunk["document_id"], "Unknown Resource")
            if "embedding" not in chunk or not chunk["embedding"]:
                unembedded_texts.append(chunk["text"])
                unembedded_indices.append(idx)

        if unembedded_texts:
            batch_size = 32
            for i in range(0, len(unembedded_texts), batch_size):
                batch_slice = unembedded_texts[i:i + batch_size]
                try:
                    response = genai.embed_content(
                        model="models/gemini-embedding-001",
                        content=batch_slice,
                        task_type="retrieval_document"
                    )
                    for sub_idx, embedding_vector in enumerate(response["embedding"]):
                        target_raw_idx = unembedded_indices[i + sub_idx]
                        raw_chunks[target_raw_idx]["embedding"] = embedding_vector
                        
                        await db["chunks"].update_one(
                            {"_id": raw_chunks[target_raw_idx]["_id"]},
                            {"$set": {"embedding": embedding_vector}}
                        )
                except Exception as batch_error:
                    print(f"Batch embedding failure: {str(batch_error)}")

        retriever = LocalVectorRetriever(user_id, raw_chunks)
        retriever.initialize_vector_space()
        cls._active_retrievers[user_id] = retriever
        return retriever