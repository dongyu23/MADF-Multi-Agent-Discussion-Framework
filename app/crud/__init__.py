from sqlalchemy.orm import Session, joinedload
from app.models import User, Persona, Forum, ForumParticipant, Message
from app.schemas import UserCreate, PersonaCreate, PersonaUpdate, ForumCreate, MessageCreate
from app.core.hashing import Hasher
import json

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: UserCreate):
    try:
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
    except Exception:
        db.rollback()
        raise

def create_persona(db: Session, persona: PersonaCreate, owner_id: int):
    try:
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
    except Exception:
        db.rollback()
        raise

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
    try:
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
    except Exception:
        db.rollback()
        raise

def delete_persona(db: Session, persona_id: int):
    try:
        db_persona = db.query(Persona).filter(Persona.id == persona_id).first()
        if db_persona:
            # Cascade delete participants/messages?
            # Normally DB foreign keys handle this if ON DELETE CASCADE is set.
            # If not, we should do it manually or ensure model definition has cascades.
            # Let's check model definition. Assuming models are set up correctly.
            # If not, SQLAlchemy relationship cascade options should be set.
            # For now, just delete the persona.
            db.delete(db_persona)
            db.commit()
            return True
        return False
    except Exception:
        db.rollback()
        raise

def create_forum(db: Session, forum: ForumCreate, creator_id: int):
    try:
        db_forum = Forum(
            topic=forum.topic,
            creator_id=creator_id,
            status="pending",
            duration_minutes=forum.duration_minutes
        )
        db.add(db_forum)
        db.flush() # Get ID before adding participants
        
        # Add participants
        for pid in forum.participant_ids:
            participant = ForumParticipant(forum_id=db_forum.id, persona_id=pid)
            db.add(participant)
        
        db.commit()
        db.refresh(db_forum)
        return db_forum
    except Exception:
        db.rollback()
        raise

def delete_forum(db: Session, forum_id: int):
    try:
        db_forum = db.query(Forum).filter(Forum.id == forum_id).first()
        if db_forum:
            # Cascade delete messages and participants
            # Again, relying on DB/ORM cascade is best practice.
            db.delete(db_forum)
            db.commit()
            return True
        return False
    except Exception:
        db.rollback()
        raise

def get_forum(db: Session, forum_id: int):
    forum = db.query(Forum).options(
        joinedload(Forum.participants).joinedload(ForumParticipant.persona)
    ).filter(Forum.id == forum_id).first()
    
    if forum:
        db.expunge(forum)
        if forum.summary_history and isinstance(forum.summary_history, str):
            try:
                forum.summary_history = json.loads(forum.summary_history)
            except:
                forum.summary_history = []
        elif forum.summary_history is None:
            forum.summary_history = []
            
        # Manually process participants to handle JSON fields if needed?
        # The Pydantic models (PersonaResponse, ForumParticipantResponse) have validators 
        # that can handle JSON string parsing.
        # But if we expunge forum, we might need to expunge participants too to be safe/consistent?
        # Actually, if we just expunge forum, accessing forum.participants returns the already loaded list.
        # Accessing properties of participants is fine.
        
    return forum

def update_forum(db: Session, forum_id: int, summary_history: list = None, status: str = None):
    try:
        db_forum = db.query(Forum).filter(Forum.id == forum_id).first()
        if not db_forum:
            return None
        
        if summary_history is not None:
            db_forum.summary_history = json.dumps(summary_history)
        
        if status is not None:
            db_forum.status = status
            
        db.commit()
        db.refresh(db_forum)
        
        db.expunge(db_forum)
        if db_forum.summary_history and isinstance(db_forum.summary_history, str):
            try:
                db_forum.summary_history = json.loads(db_forum.summary_history)
            except:
                db_forum.summary_history = []
        return db_forum
    except Exception:
        db.rollback()
        raise

def get_forum_participants(db: Session, forum_id: int):
    participants = db.query(ForumParticipant).options(joinedload(ForumParticipant.persona)).filter(ForumParticipant.forum_id == forum_id).all()
    
    results = []
    for p in participants:
        db.expunge(p)
        if p.thoughts_history and isinstance(p.thoughts_history, str):
            try:
                p.thoughts_history = json.loads(p.thoughts_history)
            except:
                p.thoughts_history = []
        elif p.thoughts_history is None:
            p.thoughts_history = []
            
        if p.persona:
            try:
                db.expunge(p.persona)
            except:
                pass
            
            if p.persona.theories and isinstance(p.persona.theories, str):
                try:
                    p.persona.theories = json.loads(p.persona.theories)
                except:
                    p.persona.theories = []
        
        results.append(p)
        
    return results

def update_forum_participant(db: Session, forum_id: int, persona_id: int, thoughts_history: list = None):
    try:
        participant = db.query(ForumParticipant).filter(
            ForumParticipant.forum_id == forum_id,
            ForumParticipant.persona_id == persona_id
        ).first()
        
        if not participant:
            return None
            
        if thoughts_history is not None:
            participant.thoughts_history = json.dumps(thoughts_history)
            
        db.commit()
        db.refresh(participant)
        
        db.expunge(participant)
        if participant.thoughts_history and isinstance(participant.thoughts_history, str):
            try:
                participant.thoughts_history = json.loads(participant.thoughts_history)
            except:
                participant.thoughts_history = []
                
        return participant
    except Exception:
        db.rollback()
        raise

def create_message(db: Session, message: MessageCreate):
    try:
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
    except Exception:
        db.rollback()
        raise

def get_forum_messages(db: Session, forum_id: int):
    return db.query(Message).filter(Message.forum_id == forum_id).all()
