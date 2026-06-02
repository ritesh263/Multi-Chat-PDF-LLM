import asyncio
from typing import List, Dict, Any
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from app.config import settings

class AIService:
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    async def condense_query(self, query: str, chat_history: List[Dict[str, str]]) -> str:
        return query 
        
        if not chat_history:
            return query
    
            
        history_str = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in chat_history[-5:]])
        
        prompt = f"""
Given the following chat history and a new user follow-up question, rewrite the follow-up question into a single, standalone search query optimized for a vector database retrieval system.

CRITICAL OPERATIONAL RULES:
1. Do not answer the question. Only output the rewritten search phrase.
2. Maintain all core technical keywords, variables, architectures, and engineering concepts.
3. Replace pronouns like "it", "that", "this", or "the second point" with the explicit technical noun from the history.
4. If the question is already a standalone search query, return it exactly as-is.
5. Output ONLY the raw rewritten text. No markdown, no quotes, no conversational filler.

[CONVERSATIONAL CHAT HISTORY LOG]
{history_str}

[NEW USER FOLLOW-UP QUESTION]
{query}

Standalone Search Query:"""
        try:
            response = self.model.generate_content(prompt)
            cleaned_query = response.text.strip().replace('"', '').replace("'", "")
            return cleaned_query if cleaned_query else query
        except Exception:
            return query

    def _build_prompt(self, query: str, context_chunks: List[Dict[str, Any]], chat_history: List[Dict[str, str]]) -> str:
        """Internal helper to construct a standardized RAG prompt injected with source context."""
        context_str = "\n\n".join([
            f"--- START SOURCE SNIPPET (Doc: {c['metadata']['filename']}, Page: {c['metadata']['page_number']}) ---\n{c['text']}\n--- END SOURCE SNIPPET ---"
            for c in context_chunks
        ])
        
        history_str = ""
        if chat_history:
            history_str = "Conversational History:\n" + "\n".join([f"{m['role'].upper()}: {m['content']}" for m in chat_history[-6:]]) + "\n\n"
            
        return f"Answer the user query based strictly on the provided context document segments.\n\n{history_str}Context Snippets:\n{context_str}\n\nUser Query: {query}"

    async def generate_grounded_response_stream(self, query: str, context_chunks: List[Dict[str, Any]], history_messages: List[Dict[str, str]]):
        """Streams back token responses securely wrapped in rate-limit backoffs."""
        prompt = self._build_prompt(query, context_chunks, history_messages)
        
        for attempt in range(3):
            try:
                response_stream = self.model.generate_content(prompt, stream=True)
                
                for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
                return  
                
            except ResourceExhausted as e:
                if attempt == 2:
                    print(f"Chat quota fully exhausted after multiple attempts: {str(e)}")
                    raise e
                
                print(f"Chat rate limit encountered. Pacing generator track. Cooling down for 6s (Attempt {attempt + 1}/3)...")
                await asyncio.sleep(6)

    async def generate_grounded_response(self, query: str, context_chunks: List[Dict[str, Any]], chat_history: List[Dict[str, str]]) -> str:
        """Fallback non-streaming grounded response generator."""
        prompt = self._build_prompt(query, context_chunks, chat_history)
        response = self.model.generate_content(prompt)
        return response.text

    async def generate_document_summary(self, sample_texts: List[str]) -> str:
        """Generates clear high-level abstract outlines evaluating document initial processing loads."""
        combined = "\n".join(sample_texts[:5])
        prompt = f"Provide a structural summary of the text blocks below in under 4 sentences:\n\n{combined}"
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception:
            return "Summary generation unavailable for this document layout sequence."