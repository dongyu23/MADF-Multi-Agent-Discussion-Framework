from sqlalchemy.orm import Session
from app.models import User, Persona, Forum, ForumParticipant, Message
from app.schemas import UserCreate, PersonaCreate, PersonaUpdate, ForumCreate, MessageCreate
from app.core.hashing import Hasher
import json

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: UserCreate):
    pwd_hash = Hasher.get_password_hash(user.password)
    db_user = User(
        username=user.username,
        password_hash=pwd_hash,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_persona(db: Session, persona: PersonaCreate, owner_id: int):
    db_persona = Persona(
        owner_id=owner_id,
        name=persona.name,
        title=persona.title,
        bio=persona.bio,
        theories=json.dumps(persona.theories),
        stance=persona.stance,
        system_prompt=persona.system_prompt,
        is_public=persona.is_public
    )
    db.add(db_persona)
    db.commit()
    db.refresh(db_persona)
    
    # Detach from session before modifying mapped attribute with incompatible type (list vs str)
    db.expunge(db_persona)
    
    # Convert JSON string back to list for Pydantic response
    if isinstance(db_persona.theories, str):
        try:
            db_persona.theories = json.loads(db_persona.theories)
        except:
            db_persona.theories = []
    return db_persona

def get_persona(db: Session, persona_id: int):
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if persona:
        # Detach before modifying
        db.expunge(persona)
        if persona.theories and isinstance(persona.theories, str):
            try:
                persona.theories = json.loads(persona.theories) 
            except:
                persona.theories = []
    return persona

def update_persona(db: Session, persona_id: int, updates: PersonaUpdate):
    db_persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not db_persona:
        return None
    
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "theories":
            setattr(db_persona, key, json.dumps(value))
        else:
            setattr(db_persona, key, value)
    
    db.commit()
    db.refresh(db_persona)
    
    db.expunge(db_persona)
    if isinstance(db_persona.theories, str):
        try:
            db_persona.theories = json.loads(db_persona.theories)
        except:
            db_persona.theories = []
    return db_persona

def delete_persona(db: Session, persona_id: int):
    db_persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if db_persona:
        db.delete(db_persona)
        db.commit()
        return True
    return False

def create_forum(db: Session, forum: ForumCreate, creator_id: int):
    db_forum = Forum(
        topic=forum.topic,
        creator_id=creator_id,
        status="active"
    )
    db.add(db_forum)
    db.commit()
    db.refresh(db_forum)
    
    # Add participants
    for pid in forum.participant_ids:
        participant = ForumParticipant(forum_id=db_forum.id, persona_id=pid)
        db.add(participant)
    
    db.commit()
    return db_forum

def get_forum(db: Session, forum_id: int):
    return db.query(Forum).filter(Forum.id == forum_id).first()

def create_message(db: Session, message: MessageCreate):
    db_message = Message(
        forum_id=message.forum_id,
        persona_id=message.persona_id,
        speaker_name=message.speaker_name,
        content=message.content,
        turn_count=message.turn_count
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_forum_messages(db: Session, forum_id: int):
    return db.query(Message).filter(Message.forum_id == forum_id).all()
