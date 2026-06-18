from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from fastapi.responses import StreamingResponse
import asyncio

from app.auth.dependencies import get_current_user
from app.rag.pipeline import RAGPipelineManager
from app.database.connection import get_database

router = APIRouter()

# UPGRADE 1: Add target_document to the allowed schema
class ChatRequest(BaseModel):
    query: str
    history: list = []
    target_document: str = "all" 

@router.post("")
async def chat_with_agent(request: ChatRequest, current_user = Depends(get_current_user)):
    raw_user_id = current_user["_id"]
    
    retriever = RAGPipelineManager.get_retriever(raw_user_id)
    
    if not retriever.chunks:
        db = get_database()
        retriever = await RAGPipelineManager.reload_user_indices(raw_user_id, db)
        
    if not retriever.chunks:
        return {"answer": "My vector matrix is currently empty. Please ingest a document before querying."}

    try:
        # UPGRADE 2: Pass the target_document down to your retrieval engine
        matched_chunks = retriever.retrieve(
            request.query, 
            top_k=5, 
            target_document=request.target_document
        )
        
        if not matched_chunks:
            async def empty_stream():
                yield f"I couldn't find any relevant information in '{request.target_document}' to answer that."
            return StreamingResponse(empty_stream(), media_type="text/plain")

        context_block = "\n\n---\n\n".join(
            [f"Source: {c['metadata']['filename']} (Page {c['metadata']['page_number']})\n{c['text']}" for c in matched_chunks]
        )

        history_text = "\n".join(
            [f"{msg.get('role', 'Unknown').capitalize()}: {msg.get('content', '')}" 
             for msg in request.history[-4:] 
             if "Enterprise Intelligence System initialized" not in msg.get('content', '')]
        )
        if not history_text:
            history_text = "No previous conversation."

        prompt = f"""You are a precise Enterprise Intelligence Assistant. 
        Answer the user's query using ONLY the provided context excerpts below. 
        If the answer is not contained within the context, state clearly that you do not have enough information.
        
        Use the Conversation History to understand pronouns or follow-up questions.

        CONVERSATION HISTORY:
        {history_text}
        
        CONTEXT EXCERPTS:
        {context_block}
        
        USER QUERY: 
        {request.query}
        """

        valid_model_name = None
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                valid_model_name = m.name
                break
        
        if not valid_model_name:
            raise Exception("No text generation models found for this API key.")

        print(f"Auto-selected authorized model: {valid_model_name}")
        
        model = genai.GenerativeModel(valid_model_name)
        response_stream = model.generate_content(prompt, stream=True)
        
        async def generate_stream():
            try:
                for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
                        await asyncio.sleep(0.01) 
            except Exception as stream_err:
                print(f"Streaming Error: {str(stream_err)}")
                if "429" in str(stream_err) or "quota" in str(stream_err).lower():
                    yield "\n\n[System Notice: Generation paused due to API rate limits. Please wait 30 seconds.]"
                else:
                    yield "\n\n[Error: Connection interrupted during streaming.]"

        return StreamingResponse(generate_stream(), media_type="text/plain")

    except Exception as e:
        error_str = str(e)
        print(f"Chat Generation Error: {error_str}")
        
        if "429" in error_str or "quota" in error_str.lower():
            async def rate_limit_stream():
                yield "**System Notice:** The AI routing engine has temporarily paused to prevent server overload (API rate limit reached). Please wait about 30 seconds and try your query again!"
            return StreamingResponse(rate_limit_stream(), media_type="text/plain")
            
        raise HTTPException(status_code=500, detail="Failed to synthesize AI response.")