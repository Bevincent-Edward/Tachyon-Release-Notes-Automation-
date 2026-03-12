"""
Release Notes Processor - Production Ready (Serves Frontend + Backend)
"""

import os
import re
import json
import csv
import io
import typing_extensions as typing
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from docx import Document
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
import aiofiles
from datetime import datetime
import zipfile
import asyncio

# Groq imports (FALLBACK 1 - Fastest LPU)
from openai import AsyncOpenAI

# Gemini imports (FALLBACK 2 - Token Efficient)
import google.generativeai as genai

load_dotenv()

app = FastAPI(title="Release Notes Processor", version="5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Initialize QUBRID client (PRIMARY - Fast & Cheap)
QUBRID_API_KEY = os.getenv("QUBRID_API_KEY")
if QUBRID_API_KEY:
    qubrid_client = AsyncOpenAI(
        api_key=QUBRID_API_KEY,
        base_url=os.getenv("QUBRID_BASE_URL", "https://platform.qubrid.com/v1"),
        max_retries=0,
        timeout=45.0
    )
    qubrid_model_name = os.getenv("QUBRID_MODEL", "openai/gpt-oss-20b")
else:
    qubrid_client = None
    qubrid_model_name = None

# Initialize GROQ client (FALLBACK 1 - Fastest LPU)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    groq_client = AsyncOpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        max_retries=0,
        timeout=30.0
    )
    groq_model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
else:
    groq_client = None
    groq_model_name = None

# Initialize GEMINI client (FALLBACK 2 - Token Efficient)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
else:
    gemini_model = None

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Mount frontend build directory (for production)
frontend_build_path = Path(__file__).parent.parent / "frontend" / "build"
if frontend_build_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_build_path / "static")), name="static")
    
    # Serve React app for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        if full_path.startswith("api/"):
            return await api_routes(full_path)
        
        index_path = frontend_build_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404, detail="Frontend not found")

# ============================================================================
# Your existing API routes here...
# (Keep all your existing API endpoint code)
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check."""
    return {
        "status": "healthy",
        "gemini_available": gemini_model is not None,
        "groq_available": groq_client is not None,
        "qubrid_available": qubrid_client is not None,
        "version": "5.0"
    }

@app.get("/api/files")
async def list_files():
    """List generated files."""
    if not OUTPUT_DIR.exists():
        return {"files": []}
    
    files = []
    for file_path in OUTPUT_DIR.iterdir():
        if file_path.is_file():
            files.append({
                "filename": file_path.name,
                "type": "release_notes" if file_path.suffix == ".md" else "validation_csv",
                "size": file_path.stat().st_size,
                "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
            })
    
    return {"files": files}
