from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication Gateway"])

@router.get("/me")
async def get_authenticated_profile(current_user: dict = Depends(get_current_user)):
    """
    Exposes the active identity profile matrix. Converts the underlying 
    BSON ObjectId into a clean string layout for frontend schema consumption.
    """
    profile_payload = dict(current_user)
    profile_payload["_id"] = str(profile_payload["_id"])
    return profile_payload