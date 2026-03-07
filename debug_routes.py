import sys
import os

# Add the project root directory to the Python path
sys.path.append(os.getcwd())

from app.main import app

def print_routes():
    print("Registered Routes:")
    print("-" * 50)
    for route in app.routes:
        methods = ", ".join(route.methods) if hasattr(route, "methods") else "WS"
        print(f"{methods:<10} {route.path}")
    print("-" * 50)

if __name__ == "__main__":
    print_routes()
