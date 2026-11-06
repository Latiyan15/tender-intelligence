"""
Server Runner for Nikom Tender Discovery & Extraction Dashboard
Starts the FastAPI application with Uvicorn.
"""

import sys
import os
import uvicorn

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    workers = int(os.environ.get("WORKERS", "1"))
    use_reload = os.environ.get("RELOAD", "true").lower() in ("true", "1") and workers == 1

    print("=" * 70)
    print(f"[*] Starting Nikom Tender Intelligence Discovery Server (workers={workers}, reload={use_reload})...")
    print("[*] Dashboard URL: http://127.0.0.1:8000")
    print("[*] API Documentation: http://127.0.0.1:8000/docs")
    if workers > 1:
        uvicorn.run("src.api.app:app", host="127.0.0.1", port=8000, workers=workers)
    else:
        uvicorn.run("src.api.app:app", host="127.0.0.1", port=8000, reload=use_reload)
