import asyncio
import websockets
import sys
import json

# Configuration
FORUM_ID = 1
WS_URL = f"ws://localhost:8001/api/v1/forums/{FORUM_ID}/ws"

async def test_ws_client():
    print(f"Attempting to connect to {WS_URL}...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            print(f"[SUCCESS] Connected to {WS_URL}")
            
            # Send a ping
            print("[INFO] Sending 'ping'...")
            await websocket.send("ping")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"[INFO] Received: {response}")
                if response == "pong":
                    print("[SUCCESS] Heartbeat verified (ping -> pong)")
                else:
                    print(f"[WARN] Unexpected response: {response}")
            except asyncio.TimeoutError:
                print("[WARN] No pong received within 5 seconds")
            
            print("[INFO] Keeping connection open for 10 seconds...")
            await asyncio.sleep(10)
            print("[INFO] Closing connection normally.")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"[ERROR] Server rejected connection with status code: {e.status_code}")
        if e.status_code == 404:
            print(" -> Suggestion: Check if backend is running and route path is correct.")
            print(" -> Suggestion: Check 'debug_routes.py' to verify registered routes.")
        elif e.status_code == 403:
            print(" -> Suggestion: Check authentication/permissions.")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(test_ws_client())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
