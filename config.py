import os

# Use environment variables for sensitive keys, with fallbacks for local dev
# Use 'or' to handle both missing env var (None) and empty string ("")
API_KEY = os.environ.get("API_KEY") or "1a8ea1d1c38d45c38ca221b884492a46.lxGhbfNhMEPUmucZ"
MODEL_NAME = os.environ.get("MODEL_NAME") or "glm-4.6"
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY") or "7a08387f3345bff89b1fb06da40d83e724fc3ba6544c751f6fbffe5c1b7ba69a"
