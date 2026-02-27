from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Annotated

from app.db.session import get_db
from app.schemas import (
    ForumCreate, 
    ForumResponse, 
    MessageCreate, 
    MessageResponse,
    SystemLogResponse
)
from app.crud import get_forum, get_forum_messages
from app.crud.crud_system_log import get_system_logs
from app.api.deps import get_current_user
from app.core.websockets import manager
from app.models import User
from app.services.forum_service import ForumService

router = APIRouter()

def get_forum_service(db: Session = Depends(get_db)) -> ForumService:
    return ForumService(db)

@router.post("/", response_model=ForumResponse)
def create_new_forum(
    forum: ForumCreate, 
    current_user: Annotated[User, Depends(get_current_user)],
    service: ForumService = Depends(get_forum_service)
):
    return service.create_new_forum(forum, current_user.id)

@router.get("/", response_model=List[ForumResponse])
def list_forums(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    from app.models import Forum
    return db.query(Forum).filter(Forum.creator_id == current_user.id).order_by(Forum.start_time.desc()).offset(skip).limit(limit).all()

@router.get("/{forum_id}", response_model=ForumResponse)
def read_forum(forum_id: int, db: Session = Depends(get_db)):
    db_forum = get_forum(db, forum_id=forum_id)
    if db_forum is None:
        raise HTTPException(status_code=404, detail="Forum not found")
    return db_forum

@router.delete("/{forum_id}")
def delete_forum_endpoint(
    forum_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: ForumService = Depends(get_forum_service)
):
    is_admin = current_user.role == 'admin'
    success = service.delete_forum(forum_id, current_user.id, is_admin)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete forum")
    return {"message": "Forum deleted successfully"}

@router.post("/{forum_id}/start")
async def start_forum_endpoint(
    forum_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: ForumService = Depends(get_forum_service)
):
    is_admin = current_user.role == 'admin'
    return await service.start_forum(forum_id, current_user.id, is_admin)

@router.post("/{forum_id}/messages", response_model=MessageResponse)
async def post_message(
    forum_id: int, 
    message: MessageCreate, 
    service: ForumService = Depends(get_forum_service)
):
    return await service.post_message(forum_id, message)

@router.get("/{forum_id}/messages", response_model=List[MessageResponse])
def get_messages(forum_id: int, db: Session = Depends(get_db)):
    db_forum = get_forum(db, forum_id=forum_id)
    if not db_forum:
        raise HTTPException(status_code=404, detail="Forum not found")
    return get_forum_messages(db, forum_id=forum_id)

@router.get("/{forum_id}/logs", response_model=List[SystemLogResponse])
def get_forum_logs(forum_id: int, db: Session = Depends(get_db)):
    db_forum = get_forum(db, forum_id=forum_id)
    if not db_forum:
        raise HTTPException(status_code=404, detail="Forum not found")
    return get_system_logs(db, forum_id=forum_id)

@router.websocket("/{forum_id}/ws")
async def websocket_endpoint(websocket: WebSocket, forum_id: int):
    await manager.connect(websocket, forum_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, forum_id)
