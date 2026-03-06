import os

# Use environment variables for sensitive keys, with fallbacks for local dev
API_KEY = os.environ.get("API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME")
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY")
