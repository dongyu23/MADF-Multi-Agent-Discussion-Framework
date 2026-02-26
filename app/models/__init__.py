from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import json

from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False) # 'user', 'admin', 'god'
    created_at = Column(DateTime, default=datetime.utcnow)

    personas = relationship("Persona", back_populates="owner", cascade="all, delete-orphan")
    created_forums = relationship("Forum", back_populates="creator", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="user", cascade="all, delete-orphan")
    god_logs = relationship("GodLog", back_populates="god_user", cascade="all, delete-orphan")

class Persona(Base):
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    title = Column(String)
    bio = Column(Text)
    theories = Column(Text) # JSON string
    stance = Column(Text)
    system_prompt = Column(Text)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="personas")
    participated_forums = relationship("ForumParticipant", back_populates="persona", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="persona")

class Forum(Base):
    __tablename__ = "forums"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="active") # 'active', 'finished'
    summary_history = Column(Text, default="[]")
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)

    creator = relationship("User", back_populates="created_forums")
    participants = relationship("ForumParticipant", back_populates="forum", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="forum", cascade="all, delete-orphan")
    observers = relationship("Observation", back_populates="forum", cascade="all, delete-orphan")

class ForumParticipant(Base):
    __tablename__ = "forum_participants"

    forum_id = Column(Integer, ForeignKey("forums.id"), primary_key=True)
    persona_id = Column(Integer, ForeignKey("personas.id"), primary_key=True)
    thoughts_history = Column(Text, default="[]")

    forum = relationship("Forum", back_populates="participants")
    persona = relationship("Persona", back_populates="participated_forums")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    forum_id = Column(Integer, ForeignKey("forums.id"), nullable=False)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=True) # Null for Moderator
    speaker_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    turn_count = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    forum = relationship("Forum", back_populates="messages")
    persona = relationship("Persona", back_populates="messages")

class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    forum_id = Column(Integer, ForeignKey("forums.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    left_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="observations")
    forum = relationship("Forum", back_populates="observers")

class GodLog(Base):
    __tablename__ = "god_logs"

    id = Column(Integer, primary_key=True, index=True)
    god_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    details = Column(Text) # JSON string
    timestamp = Column(DateTime, default=datetime.utcnow)

    god_user = relationship("User", back_populates="god_logs")
