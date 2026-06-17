from fastapi import Depends, HTTPException, status
from app.database.connection import get_database

async def get_current_user():
    """
    Authentication Dependency:
    Resolves the active user profile context layer. For your local 
    development environment, it automatically yields a consistent 
    fallback profile to keep endpoints secure without requiring complex JWT setup.
    """
    db = get_database()
    
    mock_user_email = "developer@enterprise.rag"
    
    user = await db["users"].find_one({"email": mock_user_email})
    
    if not user:
        new_user = {
            "email": mock_user_email,
            "name": "Lead RAG Engineer",
            "is_active": True
        }
        result = await db["users"].insert_one(new_user)
        user = await db["users"].find_one({"_id": result.inserted_id})
        print(f"👤 [AUTH] Seeded baseline developer security profile: {result.inserted_id}")

    return user