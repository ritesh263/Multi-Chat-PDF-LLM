from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from app.auth.dependencies import get_current_user
from app.database.connection import get_database
from app.rag.pipeline import RAGPipelineManager
from app.services.ai_service import AIService
from google.api_core.exceptions import ResourceExhausted
from bson import ObjectId
from datetime import datetime, timezone
import json
import asyncio

router = APIRouter(prefix="/api/chats", tags=["Conversations Pipeline"])
ai_service = AIService()

@router.post("/")
async def create_chat_session(title: str = "New Knowledge Exploration", current_user: dict = Depends(get_current_user)):
    db = get_database()
    session = {
        "user_id": current_user["_id"],
        "title": title,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "messages": []
    }
    result = await db["chats"].insert_one(session)
    return {"chat_id": str(result.inserted_id), "title": title}

@router.get("/")
async def get_user_chats(current_user: dict = Depends(get_current_user)):
    db = get_database()
    chats = await db["chats"].find({"user_id": current_user["_id"]}).sort("updated_at", -1).to_list(length=100)
    for c in chats:
        c["_id"] = str(c["_id"])
        c["user_id"] = str(c["user_id"])
    return chats

@router.post("/{chat_id}/message")
async def send_message(chat_id: str, query: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    user_id = current_user["_id"]
    
    chat = await db["chats"].find_one({"_id": ObjectId(chat_id), "user_id": user_id})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat conversation context log target missing.")
        
    retriever = RAGPipelineManager.get_retriever(str(user_id))
    
    if not retriever.chunks:
        await RAGPipelineManager.reload_user_indices(str(user_id), db)
        retriever = RAGPipelineManager.get_retriever(str(user_id))
        
    history_messages = chat.get("messages", [])
    
    # 🔍 OPTIMIZATION: Condense multi-turn chat statements into a standalone search vector
    search_query = await ai_service.condense_query(query, history_messages)
    print(f"\n🔍 [QUERY CONDENSER] Original: '{query}' -> Optimized Search: '{search_query}'\n")
    
    context_chunks = retriever.retrieve(search_query, top_k=8)
    
    citations = []
    for c in context_chunks:
        citation = {
            "filename": c["metadata"]["filename"],
            "page_number": c["metadata"]["page_number"],
            "snippet": c["text"]
        }
        if citation not in citations:
            citations.append(citation)

    # Return persistent server-sent events stream back to the UI interface
    return StreamingResponse(
        sse_response_generator(query, context_chunks, history_messages, citations, db, chat_id),
        media_type="text/event-stream"
    )

@router.delete("/{chat_id}")
async def delete_chat_session(chat_id: str, current_user: dict = Depends(get_current_user)):
    """Atomic Chat Purge Route: Eliminates 404 errors during tracking lifecycle."""
    db = get_database()
    user_id = current_user["_id"]
    
    result = await db["chats"].delete_one({"_id": ObjectId(chat_id), "user_id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chat session target context log missing or unauthorized."
        )
        
    print(f"扫 [CHAT PURGE] Successfully removed conversation track: {chat_id}")
    return {"message": "Chat session context successfully purged from database layers."}

async def sse_response_generator(query, context_chunks, history_messages, citations, db, chat_id):
    """GLOBAL STREAM GENERATOR WORKER: Safely feeds tokens and manages quota ceilings."""
    full_response = ""
    try:
        # First send citation mappings straight to frontend layouts
        yield f"data: {json.dumps({'citations': citations})}\n\n"
        
        async for text_chunk in ai_service.generate_grounded_response_stream(query, context_chunks, history_messages):
            full_response += text_chunk
            yield f"data: {json.dumps({'text': text_chunk})}\n\n"
            
        user_msg = {"role": "user", "content": query, "timestamp": datetime.now(timezone.utc)}
        ai_msg = {"role": "assistant", "content": full_response, "citations": citations, "timestamp": datetime.now(timezone.utc)}
        
        await db["chats"].update_one(
            {"_id": ObjectId(chat_id)},
            {
                "$push": {"messages": {"$each": [user_msg, ai_msg]}},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
            
    except ResourceExhausted:
        print("⚠️ [QUOTA EXHAUSTED] Gemini API tier limits hit. Yielding clean feedback notification.")
        error_msg = "⚠️ Core processing engine quota limit reached. Please pause for a moment before issuing further queries."
        yield f"data: {json.dumps({'text': error_msg, 'error': 'quota_exceeded'})}\n\n"
        
    except Exception as e:
        print(f"💥 [STREAM ERROR] Execution path interrupted: {str(e)}")
        error_msg = "⚠️ An unexpected interruption occurred within the core synchronization channel."
        yield f"data: {json.dumps({'text': error_msg, 'error': 'internal_failure'})}\n\n"