from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.user import PyObjectId
from bson import ObjectId

class DocumentMetadata(BaseModel):
    filename: str
    file_size: int
    content_type: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: PyObjectId

class DocumentInDB(DocumentMetadata):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    summary: Optional[str] = None
    chunk_ids: List[str] = []

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}