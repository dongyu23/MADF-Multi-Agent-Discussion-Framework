import asyncio
import logging
import time
import random
import traceback
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.crud import (
    get_forum, 
    get_forum_participants, 
    create_message, 
    get_forum_messages,
    update_forum,
    update_forum_participant,
    get_persona
)
from app.schemas import MessageCreate
from app.agent.agent import ModeratorAgent, ParticipantAgent
from app.agent.memory import SharedMemory
from app.core.websockets import manager
from app.models import Forum, Message
from app.core.time_utils import get_beijing_time, get_beijing_time_iso

logger = logging.getLogger(__name__)

class ForumScheduler:
    def __init__(self):
        self.running_tasks = {}

    async def start_forum(self, forum_id: int):
        if forum_id in self.running_tasks:
            logger.warning(f"Forum {forum_id} is already running.")
            return

        task = asyncio.create_task(self._run_forum_loop(forum_id))
        self.running_tasks[forum_id] = task
        
        # Remove task from dict when done
        task.add_done_callback(lambda t: self.running_tasks.pop(forum_id, None))

    async def stop_forum(self, forum_id: int):
        if forum_id in self.running_tasks:
            self.running_tasks[forum_id].cancel()
            try:
                await self.running_tasks[forum_id]
            except asyncio.CancelledError:
                pass
            logger.info(f"Forum {forum_id} stopped.")

    async def _run_forum_loop(self, forum_id: int):
        logger.info(f"Starting forum loop for {forum_id}")
        db = SessionLocal()
        try:
            forum = get_forum(db, forum_id)
            if not forum:
                logger.error(f"Forum {forum_id} not found.")
                return

            # Update status to Running
            update_forum(db, forum_id, status="running")
            
            # Initialize Agents
            participants_db = get_forum_participants(db, forum_id)
            participants = []
            n_participants = len(participants_db)
            
            for p_db in participants_db:
                persona = p_db.persona
                if not persona:
                    continue
                
                # Convert persona model to dict
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
                
                # Restore memory
                if p_db.thoughts_history:
                    for t in p_db.thoughts_history:
                        agent.private_memory.add_thought(t)
                
                # We need to load speech history too, but that requires querying messages
                # Optimization: Load messages once
                participants.append(agent)

            moderator = ModeratorAgent(theme=forum.topic)
            
            # Speaker Queue for multi-speaker management
            speaker_queue = []
            
            # Opening
            await self._broadcast_system_message(forum_id, "论坛开始，主持人正在开场...")
            await self._moderator_speak(db, forum_id, moderator, "opening", participants)

            # Main Loop
            start_time = time.time()
            duration_sec = (forum.duration_minutes or 30) * 60
            end_time = start_time + duration_sec
            
            turn_count = 0
            
            while True:
                # Reload forum to check for external stop signals or status changes
                # db.refresh(forum) -> This fails because get_forum detaches the object
                # We need to re-fetch it
                forum = get_forum(db, forum_id)
                if not forum:
                    logger.error(f"Forum {forum_id} disappeared during loop.")
                    break
                    
                if forum.status != "running":
                    logger.info(f"Forum {forum_id} status changed to {forum.status}, stopping loop.")
                    break
                
                current_time = time.time()
                
                # 1. Check Time -> Closing
                if current_time > end_time:
                    logger.info(f"Forum {forum_id} time up. Closing.")
                    await self._moderator_speak(db, forum_id, moderator, "closing")
                    update_forum(db, forum_id, status="closed")
                    break

                # 2. Reconstruct Context (Shared Memory)
                messages = get_forum_messages(db, forum_id)
                shared_memory = SharedMemory(n_participants)
                if forum.summary_history:
                    for s in forum.summary_history:
                        shared_memory.add_summary(s)
                for m in messages:
                    shared_memory.add_message(m.speaker_name, m.content)
                
                # Sync private memories with recent speeches
                for agent in participants:
                    agent.private_memory.speech_history = []
                    my_msgs = [m for m in messages if m.speaker_name == agent.name]
                    for m in my_msgs:
                        agent.private_memory.add_speech(m.content)

                # 3. Check Summary
                msg_count = len(messages)
                if msg_count > 0 and msg_count % 10 == 0:
                    last_msg = messages[-1]
                    if last_msg.speaker_name != moderator.name:
                         logger.info(f"Forum {forum_id} triggering summary (msg count {msg_count}).")
                         await self._moderator_speak(db, forum_id, moderator, "periodic_summary", messages=messages)

                # 4. Select Speaker (Queue Based)
                context_str = shared_memory.get_context_str()
                speaker = None
                thoughts_map = {}
                
                # Everyone thinks
                async def agent_think(ag):
                    try:
                        thought = await asyncio.to_thread(ag.think, context_str)
                        return ag, thought
                    except Exception as e:
                        logger.error(f"Agent {ag.name} think failed: {e}")
                        return ag, None

                think_results = await asyncio.gather(*[agent_think(p) for p in participants])
                
                for agent, thought in think_results:
                    if thought:
                        thoughts_map[agent] = thought
                        if thought.get('action') == 'apply_to_speak':
                            # Add to queue if not already there
                            if agent not in speaker_queue:
                                speaker_queue.append(agent)
                        
                        # Save thought to DB (Private History)
                        p_db = next((p for p in participants_db if p.persona.name == agent.name), None)
                        if p_db:
                             new_thoughts = (p_db.thoughts_history or []) + [thought]
                             update_forum_participant(db, forum_id, p_db.persona_id, thoughts_history=new_thoughts)

                # Pop from queue
                if speaker_queue:
                    speaker = speaker_queue.pop(0)
                elif participants and random.random() < 0.2: # 20% chance to random speak if quiet
                    speaker = random.choice(participants)
                
                if speaker:
                    thought = thoughts_map.get(speaker)
                    if not thought:
                         thought = {
                            "focus": "系统指派", 
                            "attitude": "中立", 
                            "analysis": "无（思考过程解析失败或被系统强制发言）",
                            "action": "listen",
                            "previous": "无",
                            "mind": "无",
                            "benefit": "无"
                        }
                    
                    await self._agent_speak(db, forum_id, speaker, thought, context_str)
                
                turn_count += 1
                await asyncio.sleep(2) # Pace the forum

        except Exception as e:
            logger.error(f"Forum loop crashed: {e}")
            logger.error(traceback.format_exc())
        finally:
            db.close()

    async def _moderator_speak(self, db: Session, forum_id: int, moderator: ModeratorAgent, action: str, guests=None, messages=None):
        content = ""
        gen = None
        
        try:
            if action == "opening":
                guest_list = [{"name": g.name, "title": g.title, "stance": g.stance} for g in guests]
                gen = await asyncio.to_thread(moderator.opening, guest_list)
            elif action == "closing":
                # Get summary history
                forum = get_forum(db, forum_id)
                gen = await asyncio.to_thread(moderator.closing, forum.summary_history or [])
            elif action == "periodic_summary":
                # Get recent messages
                msgs_text = [{"speaker": m.speaker_name, "content": m.content} for m in messages[-20:]]
                gen = await asyncio.to_thread(moderator.periodic_summary, msgs_text)

            if gen:
                # Stream consumption
                for chunk in gen:
                     if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        content += token
                        # Stream to WebSocket in real-time
                        await self._broadcast_chunk(forum_id, moderator.name, token, None)
        except Exception as e:
            logger.error(f"Moderator speak failed: {e}")
            return

        if content:
            # Save message
            msg = create_message(db, MessageCreate(
                forum_id=forum_id,
                speaker_name=moderator.name,
                content=content,
                turn_count=0 
            ))
            
            if action == "periodic_summary":
                # Update history
                forum = get_forum(db, forum_id)
                new_history = (forum.summary_history or []) + [content]
                update_forum(db, forum_id, summary_history=new_history)

            # Broadcast full message
            # We must use the content we accumulated, NOT empty string
            await self._broadcast_message(forum_id, moderator.name, content)

    async def _agent_speak(self, db: Session, forum_id: int, agent: ParticipantAgent, thought: dict, context: str):
        content = ""
        # Find persona_id
        participants = get_forum_participants(db, forum_id)
        p_db = next((p for p in participants if p.persona.name == agent.name), None)
        persona_id = p_db.persona_id if p_db else None

        try:
            # Run speak in thread
            gen = await asyncio.to_thread(agent.speak, thought, context)
            if gen:
                for chunk in gen:
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        content += token
                        # Stream to WebSocket in real-time
                        await self._broadcast_chunk(forum_id, agent.name, token, persona_id)
        except Exception as e:
            logger.error(f"Agent {agent.name} speak failed: {e}")
            return

        if content:
            create_message(db, MessageCreate(
                forum_id=forum_id,
                persona_id=persona_id,
                speaker_name=agent.name,
                content=content,
                turn_count=0
            ))
            
            await self._broadcast_message(forum_id, agent.name, content, persona_id)

    async def _broadcast_chunk(self, forum_id: int, speaker: str, chunk: str, persona_id: int = None):
        if not chunk:
            return
            
        await manager.broadcast(forum_id, {
            "type": "message_chunk",
            "data": {
                "speaker_name": speaker,
                "content": chunk,
                "persona_id": persona_id,
                "timestamp": get_beijing_time_iso()
            }
        })

    async def _broadcast_message(self, forum_id: int, speaker: str, content: str, persona_id: int = None):
        await manager.broadcast(forum_id, {
            "type": "new_message",
            "data": {
                "speaker_name": speaker,
                "content": content,
                "persona_id": persona_id,
                "timestamp": get_beijing_time_iso()
            }
        })

    async def _broadcast_system_message(self, forum_id: int, content: str):
        await manager.broadcast(forum_id, {
            "type": "system",
            "content": content
        })

scheduler = ForumScheduler()
