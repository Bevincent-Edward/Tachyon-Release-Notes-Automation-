#!/usr/bin/env python3
"""
Entry point for Render deployment
"""
import os
import uvicorn

if __name__ == "__main__":
    # Render sets PORT environment variable, default to 10000
    port = int(os.environ.get("PORT", 10000))
    
    print(f"Starting server on port {port}...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        workers=1
    )
