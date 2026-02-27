from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    forum_id = Column(Integer, ForeignKey("forums.id"), nullable=False)
    level = Column(String, default="info") # info, warning, error, thought, speech
    source = Column(String, nullable=True) # Agent Name or 'System'
    content = Column(Text, nullable=False) # Detailed text or JSON
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    forum = relationship("Forum", back_populates="system_logs")
