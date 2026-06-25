from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext

from app.auth.dependencies import get_current_user
from app.database.connection import get_database
from app.config import settings

# FIX 1: Removed prefix="/api/auth" here to prevent the double URL duplication!
router = APIRouter(tags=["Authentication Gateway"])

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class RegisterRequest(BaseModel):
    username: str
    password: str

@router.post("/register")
async def register_user(request: RegisterRequest):
    db = get_database()
    
    # 1. Check if user already exists
    if await db.users.find_one({"username": request.username}):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # 2. Hash the password and save to MongoDB
    hashed_password = pwd_context.hash(request.password)
    await db.users.insert_one({
        "username": request.username,
        "hashed_password": hashed_password
    })
    return {"message": "User registered successfully"}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_database()
    user = await db.users.find_one({"username": form_data.username})
    
    # 1. Verify user exists and password matches
    if not user or not pwd_context.verify(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
        
    # 2. Generate the JWT Token (The VIP Wristband)
    secret = getattr(settings, "SECRET_KEY", "super_secret_fallback_key_123")
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    token = jwt.encode({"sub": str(user["_id"]), "exp": expire}, secret, algorithm="HS256")
    
    # React is waiting for exactly this JSON response!
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
async def get_authenticated_profile(current_user: dict = Depends(get_current_user)):
    """
    Exposes the active identity profile matrix. Converts the underlying 
    BSON ObjectId into a clean string layout for frontend schema consumption.
    """
    profile_payload = dict(current_user)
    profile_payload["_id"] = str(profile_payload["_id"])
    return profile_payload