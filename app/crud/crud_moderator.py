from typing import List, Optional
from app.schemas import ModeratorCreate, ModeratorUpdate
from app.db.client import fetch_one, fetch_all
from datetime import datetime

def get_moderator(db, moderator_id: int):
    rs = db.execute("SELECT * FROM moderators WHERE id = ?", [moderator_id])
    return fetch_one(rs)

def get_moderators(db, skip: int = 0, limit: int = 100, creator_id: Optional[int] = None):
    params = []
    query = "SELECT * FROM moderators"
    
    if creator_id:
        query += " WHERE creator_id = ?"
        params.append(creator_id)
        
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, skip])
    
    rs = db.execute(query, params)
    return fetch_all(rs)

def create_moderator(db, moderator: ModeratorCreate, creator_id: int):
    data = moderator.model_dump()
    data['creator_id'] = creator_id
    data['created_at'] = datetime.now()
    
    columns = list(data.keys())
    placeholders = ["?"] * len(columns)
    values = list(data.values())
    
    query = f"""
    INSERT INTO moderators ({', '.join(columns)})
    VALUES ({', '.join(placeholders)})
    RETURNING *
    """
    
    rs = db.execute(query, values)
    return fetch_one(rs)

def delete_moderator(db, moderator_id: int):
    # First get it to return it (matching old behavior)
    mod = get_moderator(db, moderator_id)
    if mod:
        db.execute("DELETE FROM moderators WHERE id = ?", [moderator_id])
    return mod
