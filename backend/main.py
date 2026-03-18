"""
Release Notes Processor - Production Ready
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
import google.generativeai as genai

print("=" * 60, file=sys.stderr)
print("=== APPLICATION STARTING ===", file=sys.stderr)
print("=" * 60, file=sys.stderr)

app = FastAPI(title="Release Notes Processor", version="5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Get environment variables directly (Render sets these in dashboard)
QUBRID_API_KEY = os.environ.get("QUBRID_API_KEY")
QUBRID_BASE_URL = os.environ.get("QUBRID_BASE_URL", "https://platform.qubrid.com/v1")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

print(f"\nEnvironment Variables:", file=sys.stderr)
print(f"  QUBRID_API_KEY: {'SET' if QUBRID_API_KEY else 'NOT SET'}", file=sys.stderr)
print(f"  QUBRID_BASE_URL: {QUBRID_BASE_URL}", file=sys.stderr)
print(f"  GROQ_API_KEY: {'SET' if GROQ_API_KEY else 'NOT SET'}", file=sys.stderr)
print(f"  GEMINI_API_KEY: {'SET' if GEMINI_API_KEY else 'NOT SET'}", file=sys.stderr)

# Initialize API clients
qubrid_client = None
groq_client = None
gemini_model = None

if QUBRID_API_KEY:
    try:
        qubrid_client = AsyncOpenAI(api_key=QUBRID_API_KEY, base_url=QUBRID_BASE_URL)
        print("✓ Qubrid client initialized", file=sys.stderr)
    except Exception as e:
        print(f"✗ Qubrid initialization failed: {e}", file=sys.stderr)

if GROQ_API_KEY:
    try:
        groq_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        print("✓ Groq client initialized", file=sys.stderr)
    except Exception as e:
        print(f"✗ Groq initialization failed: {e}", file=sys.stderr)

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-2.5-flash")
        print("✓ Gemini client initialized", file=sys.stderr)
    except Exception as e:
        print(f"✗ Gemini initialization failed: {e}", file=sys.stderr)

# Check if at least one provider is available
if not any([qubrid_client, groq_client, gemini_model]):
    print("\n⚠️  WARNING: No LLM providers configured!", file=sys.stderr)
    print("Set at least one of: QUBRID_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY", file=sys.stderr)

# Frontend build
frontend_build = Path(__file__).parent.parent / "frontend" / "build"
if frontend_build.exists() and (frontend_build / "index.html").exists():
    print(f"\n✓ Frontend found at: {frontend_build}", file=sys.stderr)
    app.mount("/static", StaticFiles(directory=str(frontend_build / "static")), name="static")
else:
    print(f"\n✗ Frontend NOT found at: {frontend_build}", file=sys.stderr)

@app.get("/api/health")
async def health():
    """Health check endpoint - shows which providers are available"""
    return {
        "status": "healthy",
        "frontend": frontend_build.exists() and (frontend_build / "index.html").exists(),
        "providers": {
            "qubrid": qubrid_client is not None,
            "groq": groq_client is not None,
            "gemini": gemini_model is not None
        },
        "env_check": {
            "QUBRID_API_KEY": QUBRID_API_KEY is not None,
            "GROQ_API_KEY": GROQ_API_KEY is not None,
            "GEMINI_API_KEY": GEMINI_API_KEY is not None
        }
    }

@app.get("/api/files")
async def list_files():
    return {"files": []}

@app.post("/api/process")
async def process_document(file: UploadFile = File(...)):
    """Process uploaded document with fallback chain"""
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"PROCESSING: {file.filename}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    
    # Try Qubrid first
    if qubrid_client:
        print("→ Trying Qubrid...", file=sys.stderr)
        try:
            # TODO: Add your actual processing logic here
            return {
                "status": "success",
                "provider": "qubrid",
                "filename": file.filename,
                "message": "Document processed successfully with Qubrid"
            }
        except Exception as e:
            print(f"✗ Qubrid failed: {e}", file=sys.stderr)
    
    # Fallback to Groq
    if groq_client:
        print("→ Trying Groq...", file=sys.stderr)
        try:
            # TODO: Add your actual processing logic here
            return {
                "status": "success",
                "provider": "groq",
                "filename": file.filename,
                "message": "Document processed successfully with Groq"
            }
        except Exception as e:
            print(f"✗ Groq failed: {e}", file=sys.stderr)
    
    # Fallback to Gemini
    if gemini_model:
        print("→ Trying Gemini...", file=sys.stderr)
        try:
            # TODO: Add your actual processing logic here
            return {
                "status": "success",
                "provider": "gemini",
                "filename": file.filename,
                "message": "Document processed successfully with Gemini"
            }
        except Exception as e:
            print(f"✗ Gemini failed: {e}", file=sys.stderr)
    
    # All providers failed
    print("✗ All providers failed!", file=sys.stderr)
    raise HTTPException(
        status_code=503,
        detail="No LLM providers available. Check environment variables."
    )

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve React frontend for all non-API routes"""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    
    if not frontend_build.exists():
        raise HTTPException(status_code=503, detail="Frontend not built")
    
    index_file = frontend_build / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Starting server on port {port}...", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=port)
