from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.connection import connect_to_mongo, close_mongo_connection
from app.routes import auth_routes, document_routes, chat_routes
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.GOOGLE_API_KEY)

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://multi-chat-pdf-llm.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

app.include_router(auth_routes.router)
app.include_router(document_routes.router)
app.include_router(chat_routes.router, prefix="${API_BASE_URL}/api/chat", tags=["Chat"])

@app.get("/health")
def health_check():
    return {"status": "operational", "project": settings.PROJECT_NAME}