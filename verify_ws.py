import asyncio
import websockets
import sys

async def test_ws():
    uri = "ws://localhost:8000/api/v1/forums/1/ws"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            await websocket.send("ping")
            print("Sent ping")
            # Wait a bit for potential response or just confirm connection stays open
            await asyncio.sleep(1)
            print("Connection stable.")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_ws())
