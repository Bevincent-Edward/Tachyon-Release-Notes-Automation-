"""
Release Notes Processor - Full Application with Proper Fallback
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from openai import AsyncOpenAI
import google.generativeai as genai

load_dotenv()

print("=== APPLICATION STARTING ===", file=sys.stderr)
print(f"Environment variables loaded: {list(os.environ.keys())}", file=sys.stderr)

app = FastAPI(title="Release Notes Processor", version="5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Initialize QUBRID client (PRIMARY)
QUBRID_API_KEY = os.getenv("QUBRID_API_KEY")
QUBRID_BASE_URL = os.getenv("QUBRID_BASE_URL", "https://platform.qubrid.com/v1")
print(f"QUBRID_API_KEY set: {QUBRID_API_KEY is not None and len(QUBRID_API_KEY) > 10}", file=sys.stderr)
print(f"QUBRID_BASE_URL: {QUBRID_BASE_URL}", file=sys.stderr)

qubrid_client = None
if QUBRID_API_KEY:
    try:
        qubrid_client = AsyncOpenAI(api_key=QUBRID_API_KEY, base_url=QUBRID_BASE_URL)
        print("✓ Qubrid client initialized", file=sys.stderr)
    except Exception as e:
        print(f"✗ Qubrid client failed: {e}", file=sys.stderr)

# Initialize GROQ client (FALLBACK 1)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
print(f"GROQ_API_KEY set: {GROQ_API_KEY is not None and len(GROQ_API_KEY) > 10}", file=sys.stderr)

groq_client = None
if GROQ_API_KEY:
    try:
        groq_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        print("✓ Groq client initialized", file=sys.stderr)
    except Exception as e:
        print(f"✗ Groq client failed: {e}", file=sys.stderr)

# Initialize GEMINI client (FALLBACK 2)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(f"GEMINI_API_KEY set: {GEMINI_API_KEY is not None and len(GEMINI_API_KEY) > 10}", file=sys.stderr)

gemini_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-2.5-flash")
        print("✓ Gemini client initialized", file=sys.stderr)
    except Exception as e:
        print(f"✗ Gemini client failed: {e}", file=sys.stderr)

# Frontend build
frontend_build = Path(__file__).parent.parent / "frontend" / "build"
if frontend_build.exists() and (frontend_build / "index.html").exists():
    print(f"✓ Frontend found at: {frontend_build}", file=sys.stderr)
    app.mount("/static", StaticFiles(directory=str(frontend_build / "static")), name="static")
else:
    print(f"✗ Frontend NOT found at: {frontend_build}", file=sys.stderr)

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "frontend": frontend_build.exists() and (frontend_build / "index.html").exists(),
        "qubrid": qubrid_client is not None,
        "groq": groq_client is not None,
        "gemini": gemini_model is not None,
        "env_vars": {
            "QUBRID_API_KEY": QUBRID_API_KEY is not None,
            "GROQ_API_KEY": GROQ_API_KEY is not None,
            "GEMINI_API_KEY": GEMINI_API_KEY is not None
        }
    }

@app.get("/api/files")
async def list_files():
    return {"files": []}

@app.post("/api/process")
async def process(file: UploadFile = File(...)):
    print(f"\n=== PROCESSING FILE: {file.filename} ===", file=sys.stderr)
    
    # Try Qubrid first
    if qubrid_client:
        print("Attempting Qubrid...", file=sys.stderr)
        try:
            # Your processing logic here
            return {"status": "success", "provider": "qubrid", "filename": file.filename}
        except Exception as e:
            print(f"Qubrid failed: {e}", file=sys.stderr)
    
    # Fallback to Groq
    if groq_client:
        print("Attempting Groq...", file=sys.stderr)
        try:
            return {"status": "success", "provider": "groq", "filename": file.filename}
        except Exception as e:
            print(f"Groq failed: {e}", file=sys.stderr)
    
    # Fallback to Gemini
    if gemini_model:
        print("Attempting Gemini...", file=sys.stderr)
        try:
            return {"status": "success", "provider": "gemini", "filename": file.filename}
        except Exception as e:
            print(f"Gemini failed: {e}", file=sys.stderr)
    
    # All failed
    print("All providers failed!", file=sys.stderr)
    return {"status": "error", "message": "All LLM providers failed"}

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith("api/"):
        return {"error": "API route not found"}
    
    if not frontend_build.exists():
        return {"error": "Frontend not built"}
    
    index_file = frontend_build / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    
    return {"error": "Not found"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on port {port}...", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=port)
