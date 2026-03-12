"""
Release Notes Processor - Full Application
"""
import os
import re
import json
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from openai import AsyncOpenAI
import google.generativeai as genai

load_dotenv()

app = FastAPI(title="Release Notes Processor", version="5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Initialize clients
QUBRID_API_KEY = os.getenv("QUBRID_API_KEY")
qubrid_client = AsyncOpenAI(api_key=QUBRID_API_KEY, base_url="https://platform.qubrid.com/v1") if QUBRID_API_KEY else None

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.5-flash")
else:
    gemini_model = None

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Mount frontend - On Render, build is copied to backend folder
frontend_build = Path(__file__).parent / "build"
if not frontend_build.exists():
    # Fallback for local development
    frontend_build = Path(__file__).parent.parent / "frontend" / "build"

if frontend_build.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_build / "static")), name="static")

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "qubrid": qubrid_client is not None,
        "groq": groq_client is not None,
        "gemini": gemini_model is not None
    }

@app.get("/api/files")
async def list_files():
    if not OUTPUT_DIR.exists():
        return {"files": []}
    files = [{"name": f.name, "size": f.stat().st_size} for f in OUTPUT_DIR.iterdir() if f.is_file()]
    return {"files": files}

@app.post("/api/process")
async def process(file: UploadFile = File(...)):
    # Your processing logic here
    return {"status": "processing", "filename": file.filename}

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith("api/"):
        return {"error": "API route not found"}
    
    # Try to serve from build directory
    if frontend_build.exists():
        # Try to serve the requested file
        file_path = frontend_build / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # Serve index.html for SPA routing
        index_file = frontend_build / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
    
    return {"error": "Frontend not found - build directory missing"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
