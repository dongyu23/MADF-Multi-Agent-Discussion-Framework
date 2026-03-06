import os
import sys
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Add project root to sys.path to allow imports from app
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.main import app
except Exception as e:
    # Fallback app to report initialization errors instead of 500 crash
    logging.error(f"Failed to initialize app: {e}", exc_info=True)
    app = FastAPI()
    
    @app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
    async def catch_all(path_name: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Application Initialization Failed",
                "detail": str(e),
                "path": path_name
            }
        )

# Vercel Serverless Function entry point
# This file is located at /api/index.py to map to Vercel's /api route
