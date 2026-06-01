from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.connection import connect_to_mongo, close_mongo_connection
from app.routes import auth_routes, document_routes, chat_routes
import google.generativeai as genai
from app.config import settings

# Configure the global Google SDK state instantly on boot sequence
genai.configure(api_key=settings.GOOGLE_API_KEY)

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

# Explicitly list permitted client origins to support secure credentialed handshakes
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Replaced "*" with explicit list
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
app.include_router(chat_routes.router)

@app.get("/health")
def health_check():
    return {"status": "operational", "project": settings.PROJECT_NAME}