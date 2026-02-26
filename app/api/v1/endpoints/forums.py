from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Annotated

from app.db.session import get_db
from app.schemas import (
    ForumCreate, 
    ForumResponse, 
    MessageCreate, 
    MessageResponse, 
    TriggerAgentRequest, 
    TriggerModeratorRequest
)
from app.crud import (
    create_forum, 
    get_forum, 
    create_message, 
    get_forum_messages, 
    get_persona,
    get_forum_participants,
    update_forum_participant,
    update_forum
)
from app.agent.agent import ParticipantAgent, ModeratorAgent
from app.agent.memory import SharedMemory
import json
from app.api.deps import get_current_user
from app.core.websockets import manager
from app.models import User

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

@router.post("/{forum_id}/trigger_agent")
async def trigger_agent(
    forum_id: int,
    request: TriggerAgentRequest,
    db: Session = Depends(get_db)
):
    # 1. Get Forum
    forum = get_forum(db, forum_id)
    if not forum:
        raise HTTPException(status_code=404, detail="Forum not found")
        
    if not request.persona_id:
        raise HTTPException(status_code=400, detail="Persona ID is required for participant agent")
        
    # 2. Get Participant
    participants = get_forum_participants(db, forum_id)
    target_participant = next((p for p in participants if p.persona_id == request.persona_id), None)
    
    if not target_participant:
         raise HTTPException(status_code=404, detail="Participant not found in this forum")
         
    # 3. Get Messages
    messages = get_forum_messages(db, forum_id)
    
    # 4. Reconstruct Shared Memory (Context)
    n_participants = len(participants)
    shared_memory = SharedMemory(n_participants)
    
    # Load summaries
    if forum.summary_history:
        for s in forum.summary_history:
            shared_memory.add_summary(s)
            
    # Load messages
    for m in messages:
        shared_memory.add_message(m.speaker_name, m.content)
        
    context = shared_memory.get_context_str()
    
    # 5. Initialize Agent
    persona = target_participant.persona
    if not persona:
        raise HTTPException(status_code=404, detail="Persona data missing for participant")

    # Convert persona model to dict for Agent init
    persona_dict = {
        "name": persona.name,
        "title": persona.title,
        "bio": persona.bio,
        "theories": persona.theories,
        "stance": persona.stance,
        "system_prompt": persona.system_prompt
    }
    
    agent = ParticipantAgent(
        name=persona.name,
        persona=persona_dict,
        n_participants=n_participants,
        theme=forum.topic
    )
    
    # 6. Reconstruct Private Memory
    # Load thoughts
    if target_participant.thoughts_history:
        for t in target_participant.thoughts_history:
            agent.private_memory.add_thought(t)
            
    # Load speeches (filter messages by this persona)
    my_messages = [m for m in messages if m.persona_id == request.persona_id]
    for m in my_messages:
        agent.private_memory.add_speech(m.content)
        
    # 7. Think
    # Note: think() calls LLM, might be slow.
    thought = agent.think(context)
    if not thought:
        raise HTTPException(status_code=500, detail="Agent failed to think")

    # Update thoughts history in DB
    new_thoughts = (target_participant.thoughts_history or []) + [thought]
    update_forum_participant(db, forum_id, request.persona_id, thoughts_history=new_thoughts)
    
    response_data = {
        "thought": thought,
        "action": thought.get("action"),
        "message": None
    }
    
    # 8. Speak if needed
    if thought.get("action") == "apply_to_speak":
        # Generate speech
        speech_generator = agent.speak(thought, context)
        
        if speech_generator:
            # Consume generator
            full_speech = ""
            # The generator yields chunks from OpenAI/Compatible API
            # We need to handle potential errors or empty chunks
            try:
                for chunk in speech_generator:
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        full_speech += chunk.choices[0].delta.content
            except Exception as e:
                print(f"Error generating speech: {e}")
                # If streaming fails, we might still have partial speech or just fail
                # For now, let's continue if we have something
                
            if full_speech:
                # Save message
                new_msg = create_message(db, MessageCreate(
                    forum_id=forum_id,
                    persona_id=request.persona_id,
                    speaker_name=persona.name,
                    content=full_speech,
                    turn_count=len(messages) + 1
                ))
                
                # Broadcast
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
                
                response_data["message"] = full_speech
        
    return response_data

@router.post("/{forum_id}/trigger_moderator")
async def trigger_moderator(
    forum_id: int,
    request: TriggerModeratorRequest,
    db: Session = Depends(get_db)
):
    # 1. Get Forum
    forum = get_forum(db, forum_id)
    if not forum:
        raise HTTPException(status_code=404, detail="Forum not found")
        
    # 2. Get Messages & Participants
    messages = get_forum_messages(db, forum_id)
    participants = get_forum_participants(db, forum_id)
    
    # 3. Init Moderator
    moderator = ModeratorAgent(theme=forum.topic)
    
    # 4. Determine Action
    action = request.action
    if action == "auto":
        if not messages:
            action = "opening"
        elif forum.status == "closing":
            action = "closing"
        else:
            # Default to summary if there are messages
            action = "periodic_summary"
    
    response_content = ""
    
    if action == "opening":
        # Prepare guests list
        guests = []
        for p in participants:
            if p.persona:
                guests.append({
                    "name": p.persona.name,
                    "title": p.persona.title,
                    "stance": p.persona.stance
                })
            
        gen = moderator.opening(guests)
        if gen:
            try:
                for chunk in gen:
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        response_content += chunk.choices[0].delta.content
            except Exception as e:
                print(f"Error generating opening: {e}")
                
    elif action == "periodic_summary":
        # Use last 20 messages for summary context
        recent_msgs = [{"speaker": m.speaker_name, "content": m.content} for m in messages[-20:]]
        
        if not recent_msgs:
             return {"action": action, "content": "No messages to summarize."}

        gen = moderator.periodic_summary(recent_msgs)
        if gen:
            try:
                for chunk in gen:
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        response_content += chunk.choices[0].delta.content
            except Exception as e:
                print(f"Error generating summary: {e}")
                
        # Update summary history
        if response_content:
            new_history = (forum.summary_history or []) + [response_content]
            update_forum(db, forum_id, summary_history=new_history)
        
    elif action == "closing":
        history = forum.summary_history or []
        gen = moderator.closing(history)
        if gen:
            try:
                for chunk in gen:
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        response_content += chunk.choices[0].delta.content
            except Exception as e:
                print(f"Error generating closing: {e}")
                
        if response_content:
            update_forum(db, forum_id, status="closed")
        
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    # Save as message
    if response_content:
        new_msg = create_message(db, MessageCreate(
            forum_id=forum_id,
            persona_id=None, 
            speaker_name="主持人",
            content=response_content,
            turn_count=len(messages) + 1
        ))
        
        await manager.broadcast(forum_id, {
            "type": "new_message",
            "data": {
                "id": new_msg.id,
                "speaker_name": new_msg.speaker_name,
                "content": new_msg.content,
                "persona_id": None,
                "timestamp": new_msg.timestamp.isoformat()
            }
        })
        
    return {"action": action, "content": response_content}
