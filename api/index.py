import os
import sys

# Add project root to sys.path to allow imports from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Vercel Serverless Function entry point
# This file is located at /api/index.py to map to Vercel's /api route
