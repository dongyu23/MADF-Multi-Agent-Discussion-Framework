from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Annotated

from app.db.session import get_db
from app.schemas import ForumCreate, ForumResponse, MessageCreate, MessageResponse
from app.crud import create_forum, get_forum, create_message, get_forum_messages, get_persona
from app.models import User
from app.api.deps import get_current_user
from app.core.websockets import manager

router = APIRouter()

@router.post("/", response_model=ForumResponse)
def create_new_forum(
    forum: ForumCreate, 
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    # Check participants
    for pid in forum.participant_ids:
        p = get_persona(db, pid)
        if not p:
            raise HTTPException(status_code=404, detail=f"Persona {pid} not found")
            
    return create_forum(db=db, forum=forum, creator_id=current_user.id)

@router.get("/", response_model=List[ForumResponse])
def list_forums(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    from app.models import Forum
    return db.query(Forum).order_by(Forum.start_time.desc()).offset(skip).limit(limit).all()

@router.get("/{forum_id}", response_model=ForumResponse)
def read_forum(forum_id: int, db: Session = Depends(get_db)):
    db_forum = get_forum(db, forum_id=forum_id)
    if db_forum is None:
        raise HTTPException(status_code=404, detail="Forum not found")
    return db_forum

@router.post("/{forum_id}/messages", response_model=MessageResponse)
async def post_message(
    forum_id: int, 
    message: MessageCreate, 
    db: Session = Depends(get_db)
):
    # Note: We removed current_user dependency here to allow Agents (which might call this API) 
    # or we need to implement Agent Auth. For now, we assume this endpoint can be called 
    # if it's open, or we can add optional auth.
    # To support "User" speaking in forum, we might need auth.
    
    if message.forum_id != forum_id:
        raise HTTPException(status_code=400, detail="Forum ID mismatch")
    
    db_forum = get_forum(db, forum_id=forum_id)
    if not db_forum:
        raise HTTPException(status_code=404, detail="Forum not found")
        
    if message.persona_id:
        p = get_persona(db, message.persona_id)
        if not p:
            raise HTTPException(status_code=404, detail="Persona not found")
            
    new_msg = create_message(db=db, message=message)
    
    # Broadcast to WebSocket
    await manager.broadcast(forum_id, {
        "type": "new_message",
        "data": {
            "id": new_msg.id,
            "speaker_name": new_msg.speaker_name,
            "content": new_msg.content,
            "persona_id": new_msg.persona_id,
            "timestamp": new_msg.timestamp.isoformat()
        }
    })
    
    return new_msg

@router.get("/{forum_id}/messages", response_model=List[MessageResponse])
def get_messages(forum_id: int, db: Session = Depends(get_db)):
    db_forum = get_forum(db, forum_id=forum_id)
    if not db_forum:
        raise HTTPException(status_code=404, detail="Forum not found")
    return get_forum_messages(db, forum_id=forum_id)

@router.websocket("/{forum_id}/ws")
async def websocket_endpoint(websocket: WebSocket, forum_id: int):
    await manager.connect(websocket, forum_id)
    try:
        while True:
            # Keep connection alive, maybe handle incoming client messages (user speaking)
            # For now, we just listen for disconnect
            data = await websocket.receive_text()
            # Optional: Client sends message via WS instead of POST API
            # await manager.broadcast(forum_id, f"Client says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, forum_id)
