"""
Release Notes Processor - Full Stack Deployment
Serves both API and React frontend from single Render service
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
from fastapi.middleware.trustedhost import TrustedHostMiddleware
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
# Qubrid provides access to multiple models at low cost
QUBRID_API_KEY = os.getenv("QUBRID_API_KEY")
if QUBRID_API_KEY:
    qubrid_client = AsyncOpenAI(
        api_key=QUBRID_API_KEY,
        base_url=os.getenv("QUBRID_BASE_URL", "https://platform.qubrid.com/v1"),
        max_retries=0,
        timeout=45.0  # Reduced timeout for faster fallback
    )
    qubrid_model_name = os.getenv("QUBRID_MODEL", "openai/gpt-oss-20b")  # Working model
else:
    qubrid_client = None
    qubrid_model_name = None

# Initialize GROQ client (FALLBACK 1 - Fastest LPU Infrastructure)
# Groq uses dedicated LPU for 800+ tokens/second
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
# Gemini 2.5 Flash is fast and consumes fewer tokens
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
else:
    gemini_model = None

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Mount frontend static files (for production deployment)
frontend_build_dir = Path(__file__).parent.parent / "frontend" / "build"
if frontend_build_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_build_dir / "static")), name="static")
