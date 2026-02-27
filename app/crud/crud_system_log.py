from sqlalchemy.orm import Session
from app.models.system_log import SystemLog
from app.schemas.system_log import SystemLogCreate

def create_system_log(db: Session, log: SystemLogCreate):
    db_log = SystemLog(
        forum_id=log.forum_id,
        level=log.level,
        source=log.source,
        content=log.content
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def get_system_logs(db: Session, forum_id: int, limit: int = 100):
    return db.query(SystemLog).filter(SystemLog.forum_id == forum_id).order_by(SystemLog.timestamp.asc()).limit(limit).all()
