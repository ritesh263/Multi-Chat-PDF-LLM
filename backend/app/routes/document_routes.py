from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request, BackgroundTasks  # 🟢 Added BackgroundTasks
from app.auth.dependencies import get_current_user
from app.database.connection import get_database
from app.models.document import DocumentInDB
from app.config import settings
from app.rag.text_processor import DocumentProcessor
from app.rag.pipeline import RAGPipelineManager
from app.services.ai_service import AIService
from bson import ObjectId
import os
import shutil
import asyncio

router = APIRouter(prefix="/api/documents", tags=["Documents"])
ai_service = AIService()

@router.post("/upload")
async def upload_documents(
    request: Request, 
    background_tasks: BackgroundTasks,  
    file: UploadFile = File(...), 
    current_user: dict = Depends(get_current_user)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only standard PDF files are supported.")
        
    db = get_database()
    user_id = current_user["_id"]
    
    file_path = os.path.join(settings.UPLOAD_DIR, f"{user_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    doc_id = ObjectId()
    
    try:
        pages_data = DocumentProcessor.extract_text_from_pdf(file_path)
        chunks = DocumentProcessor.split_documents(pages_data)
        
        await asyncio.sleep(0.1)
        if await request.is_disconnected():
            if os.path.exists(file_path): os.remove(file_path)
            print(f"[CANCELLATION VERIFIED] Ingestion safely aborted during parsing for: {file.filename}")
            return {"message": "Pipeline execution aborted safely."}
            
        
        sample_texts = [c["text"] for c in chunks[:4]]
        summary = await ai_service.generate_document_summary(sample_texts)
        
        await asyncio.sleep(0.1)
        if await request.is_disconnected():
            if os.path.exists(file_path): os.remove(file_path)
            print(f"[CANCELLATION VERIFIED] Ingestion safely aborted before database commit for: {file.filename}")
            return {"message": "Pipeline execution aborted safely."}

        
        existing_doc = await db["documents"].find_one({"filename": file.filename, "user_id": user_id})
        
        if existing_doc:
            doc_id = existing_doc["_id"]
            await db["chunks"].delete_many({"document_id": doc_id})
            print(f"[UPSERT OVERWRITE] Updating existing asset matrix for ID: {doc_id}")

        doc_meta = {
            "filename": file.filename,
            "file_size": os.path.getsize(file_path),
            "content_type": file.content_type,
            "user_id": user_id,
            "summary": summary
        }
        
        await db["documents"].update_one({"_id": doc_id}, {"$set": doc_meta}, upsert=True)
        
        db_chunks = []
        for chunk in chunks:
            db_chunks.append({
                "document_id": doc_id,
                "user_id": user_id,
                "text": chunk["text"],
                "page_number": chunk["page_number"]
            })
            
        if db_chunks:
            await db["chunks"].insert_many(db_chunks)
            
        background_tasks.add_task(RAGPipelineManager.reload_user_indices, str(user_id), db)
        
        return {"message": "Document ingested and database records initialized. Vector index rebuilding in background.", "document_id": str(doc_id)}
        
    except asyncio.CancelledError:
        print(f"[CANCELLATION VERIFIED] Ingestion safely aborted via async core hook for: {file.filename}")
        if os.path.exists(file_path):
            os.remove(file_path)
        await db["documents"].delete_one({"_id": doc_id})
        await db["chunks"].delete_many({"document_id": doc_id})
        return {"message": "Pipeline execution cancelled safely."}
        
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        await db["documents"].delete_one({"_id": doc_id})
        await db["chunks"].delete_many({"document_id": doc_id})
        raise HTTPException(status_code=500, detail=f"Pipeline Processing Internal Failure: {str(e)}")
        
@router.get("/")
async def list_documents(current_user: dict = Depends(get_current_user)):
    db = get_database()
    docs = await db["documents"].find({"user_id": current_user["_id"]}).to_list(length=100)
    for d in docs:
        d["_id"] = str(d["_id"])
        d["user_id"] = str(d["user_id"])
    return docs

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str, 
    background_tasks: BackgroundTasks, 
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    user_id = current_user["_id"]
    
    doc = await db["documents"].find_one({"_id": ObjectId(doc_id), "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document asset target context profile not found.")
        
    await db["documents"].delete_one({"_id": ObjectId(doc_id)})
    await db["chunks"].delete_many({"document_id": ObjectId(doc_id)})
    
    file_path = os.path.join(settings.UPLOAD_DIR, f"{user_id}_{doc['filename']}")
    if os.path.exists(file_path):
        os.remove(file_path)
        
    background_tasks.add_task(RAGPipelineManager.reload_user_indices, str(user_id), db)
    return {"message": "Document metadata structures successfully removed from active vector indexes."}