"""
Server Runner for Nikom Tender Discovery & Extraction Dashboard
Starts the FastAPI application with Uvicorn.
"""

import sys
import os
import uvicorn

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print("=" * 70)
    print("[*] Starting Nikom Tender Intelligence Discovery Server...")
    print("[*] Dashboard URL: http://127.0.0.1:8000")
    print("[*] API Documentation: http://127.0.0.1:8000/docs")
    uvicorn.run("src.api.app:app", host="127.0.0.1", port=8000, reload=True)
