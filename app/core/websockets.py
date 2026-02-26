from typing import List, Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # forum_id -> List[WebSocket]
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, forum_id: int):
        await websocket.accept()
        if forum_id not in self.active_connections:
            self.active_connections[forum_id] = []
        self.active_connections[forum_id].append(websocket)

    def disconnect(self, websocket: WebSocket, forum_id: int):
        if forum_id in self.active_connections:
            if websocket in self.active_connections[forum_id]:
                self.active_connections[forum_id].remove(websocket)
            if not self.active_connections[forum_id]:
                del self.active_connections[forum_id]

    async def broadcast(self, forum_id: int, message: dict):
        if forum_id in self.active_connections:
            for connection in self.active_connections[forum_id]:
                await connection.send_json(message)

manager = ConnectionManager()
