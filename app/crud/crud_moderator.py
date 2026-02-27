from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Moderator
from app.schemas import ModeratorCreate, ModeratorUpdate

def get_moderator(db: Session, moderator_id: int):
    return db.query(Moderator).filter(Moderator.id == moderator_id).first()

def get_moderators(db: Session, skip: int = 0, limit: int = 100, creator_id: Optional[int] = None):
    query = db.query(Moderator)
    if creator_id:
        query = query.filter(Moderator.creator_id == creator_id)
    return query.offset(skip).limit(limit).all()

def create_moderator(db: Session, moderator: ModeratorCreate, creator_id: int):
    db_obj = Moderator(
        **moderator.model_dump(),
        creator_id=creator_id
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_moderator(db: Session, moderator_id: int):
    db_obj = db.query(Moderator).filter(Moderator.id == moderator_id).first()
    if db_obj:
        db.delete(db_obj)
        db.commit()
    return db_obj
