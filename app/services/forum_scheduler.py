import asyncio
import logging
import time
import random
import traceback
import uuid
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

    async def _broadcast_system_log(self, forum_id: int, message: str, level: str = "info", source: str = "System", db: Session = None):
        """Broadcast system log to frontend for 'terminal-like' view and optionally persist"""
        
        # Persist if DB session provided
        if db:
            from app.crud.crud_system_log import create_system_log
            from app.schemas.system_log import SystemLogCreate
            try:
                create_system_log(db, SystemLogCreate(
                    forum_id=forum_id,
                    level=level,
                    source=source,
                    content=message
                ))
            except Exception as e:
                logger.error(f"Failed to persist system log: {e}")

        await manager.broadcast(forum_id, {
            "type": "system_log",
            "data": {
                "timestamp": get_beijing_time_iso(),
                "level": level,
                "content": message,
                "source": source
            }
        })

    async def _run_forum_loop(self, forum_id: int):
        logger.info(f"Starting forum loop for {forum_id}")
        await self._broadcast_system_log(forum_id, "论坛主循环启动...")
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

            moderator_db = forum.moderator
            if moderator_db:
                moderator = ModeratorAgent(
                    theme=forum.topic, 
                    name=moderator_db.name, 
                    system_prompt=moderator_db.system_prompt
                )
                await self._broadcast_system_log(forum_id, f"主持人 [{moderator.name}] 已就位")
            else:
                moderator = ModeratorAgent(theme=forum.topic)
                await self._broadcast_system_log(forum_id, "系统默认主持人已就位")
            
            # Speaker Queue for multi-speaker management
            speaker_queue = []
            # Track agents who have spoken in the current "batch" (until queue is cleared)
            batch_spoken_agents = set()
            
            # Opening
            await self._broadcast_system_message(forum_id, "论坛开始，主持人正在开场...")
            await self._broadcast_system_log(forum_id, "主持人正在进行开场白...")
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
                # Requirement #4: Sliding Window Summary
                # "When N messages exceeded... Moderator summarizes... Append to shared summary... Clear shared memory"
                # Here "Clear shared memory" implies that subsequent contexts should NOT include the summarized messages.
                # SharedMemory.get_context_str() builds context from summaries + messages.
                # So if we clear `messages` (in memory list, not DB), the next context will be Summary + New Messages.
                # BUT, we re-fetch `messages` from DB every loop: `messages = get_forum_messages(db, forum_id)`.
                # So we need a way to filter out summarized messages.
                # We can use `forum.summary_history` length or some metadata to know where to start.
                # Or simpler: store "last_summarized_msg_id" in Forum? 
                # Or just rely on the fact that we only feed the last N messages to the periodic_summary prompt,
                # AND we assume `SharedMemory` should only hold the last N messages + All Summaries.
                
                # Let's adjust the logic to strictly follow "Sliding Window":
                # 1. Fetch ALL messages (or just last N+buffer).
                # 2. Check if len(unsummarized_messages) > N.
                # 3. If so, summarize them, add to summary_history, and effectively "archive" them.
                
                # To support this statelessly with DB:
                # We can check `turn_count`. Or just keep the simple heuristic but ensure context is built correctly.
                # The prompt requirement says: "maintain a global shared memory list... only retain recent N".
                # In `_run_forum_loop`, we do:
                # `messages = get_forum_messages(db, forum_id)` -> This gets ALL.
                # `shared_memory = SharedMemory(n_participants)`
                # `for m in messages: shared_memory.add_message(...)` -> This adds ALL.
                # `SharedMemory` internal deque handles the "retain recent N" for *context generation*.
                
                # BUT the Summary Trigger should probably be based on *new* messages since last summary.
                # Let's use a persistent counter or check message count vs stored state?
                # For now, `msg_count % 10 == 0` is a rough proxy for "every 10 messages".
                # To be precise:
                # If we have 20 messages, and we summarized at 10.
                # At 20, we summarize 11-20.
                # This works if we assume the loop runs frequently enough.
                
                msg_count = len(messages)
                N_WINDOW = 20 # Configurable default
                
                if msg_count > 0 and msg_count % N_WINDOW == 0:
                    last_msg = messages[-1]
                    if last_msg.speaker_name != moderator.name:
                         logger.info(f"Forum {forum_id} triggering summary (msg count {msg_count}).")
                         # Summarize the last N messages
                         msgs_to_summarize = messages[-N_WINDOW:]
                         await self._moderator_speak(db, forum_id, moderator, "periodic_summary", messages=msgs_to_summarize)
                         # Note: `_moderator_speak` appends to `forum.summary_history`.
                         # Next loop, `SharedMemory` will load the new summary.
                         # And `SharedMemory` (via deque) will only keep last N messages in context context_str.
                         # So "Clear shared memory" effect is achieved by the deque + summary addition.

                # 4. Select Speaker (Queue Based)
                context_str = shared_memory.get_context_str()
                speaker = None
                thoughts_map = {}
                
                # Everyone thinks
                await self._broadcast_system_log(forum_id, "所有参与者正在思考中...", "info")
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
                            # Add to queue if not already there AND hasn't spoken in current batch
                            if agent not in speaker_queue:
                                if agent in batch_spoken_agents and speaker_queue:
                                    # If queue is not empty, and agent already spoke in this batch, deny entry.
                                    logger.info(f"Agent {agent.name} denied queue entry (already spoke in current batch).")
                                else:
                                    speaker_queue.append(agent)
                        
                        # Save thought to DB (Private History)
                        p_db = next((p for p in participants_db if p.persona.name == agent.name), None)
                        if p_db:
                             new_thoughts = (p_db.thoughts_history or []) + [thought]
                             update_forum_participant(db, forum_id, p_db.persona_id, thoughts_history=new_thoughts)

                # Pop from queue
                if speaker_queue:
                    speaker = speaker_queue.pop(0)
                    batch_spoken_agents.add(speaker)
                    # Requirement: Queue should NOT be cleared automatically.
                    # It persists until empty.
                        
                elif participants and random.random() < 0.2: # 20% chance to random speak if quiet
                    speaker = random.choice(participants)
                
                # Check if queue is now empty
                if not speaker_queue:
                    if batch_spoken_agents:
                        logger.info(f"Queue empty. Clearing batch history ({len(batch_spoken_agents)} agents).")
                        batch_spoken_agents.clear()
                
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
        stream_id = str(uuid.uuid4())
        
        forum = get_forum(db, forum_id)
        moderator_id = forum.moderator_id
        
        try:
            if action == "opening":
                guest_list = [{"name": g.name, "title": g.title, "stance": g.stance} for g in guests]
                gen = await asyncio.to_thread(moderator.opening, guest_list)
            elif action == "closing":
                forum = get_forum(db, forum_id)
                gen = await asyncio.to_thread(moderator.closing, forum.summary_history or [])
            elif action == "periodic_summary":
                msgs_text = [{"speaker": m.speaker_name, "content": m.content} for m in messages[-20:]]
                gen = await asyncio.to_thread(moderator.periodic_summary, msgs_text)

            if gen:
                for chunk in gen:
                     if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        content += token
                        await self._broadcast_chunk(forum_id, moderator.name, token, None, moderator_id, stream_id)
        except Exception as e:
            logger.error(f"Moderator speak failed: {e}")
            logger.error(traceback.format_exc())
            return

        if content:
            msg = create_message(db, MessageCreate(
                forum_id=forum_id,
                moderator_id=moderator_id,
                speaker_name=moderator.name,
                content=content,
                turn_count=0 
            ))
            
            if action == "periodic_summary":
                forum = get_forum(db, forum_id)
                new_history = (forum.summary_history or []) + [content]
                update_forum(db, forum_id, summary_history=new_history)

            await self._broadcast_message(forum_id, moderator.name, content, None, moderator_id, stream_id, msg.id)
            
            # Log full speech
            await self._broadcast_system_log(forum_id, content, "speech", moderator.name, db=db)

    async def _agent_speak(self, db: Session, forum_id: int, agent: ParticipantAgent, thought: dict, context: str):
        content = ""
        stream_id = str(uuid.uuid4())
        participants = get_forum_participants(db, forum_id)
        p_db = next((p for p in participants if p.persona.name == agent.name), None)
        persona_id = p_db.persona_id if p_db else None

        try:
            gen = await asyncio.to_thread(agent.speak, thought, context)
            if gen:
                for chunk in gen:
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        content += token
                        await self._broadcast_chunk(forum_id, agent.name, token, persona_id, None, stream_id)
        except Exception as e:
            logger.error(f"Agent {agent.name} speak failed: {e}")
            return

        if content:
            msg = create_message(db, MessageCreate(
                forum_id=forum_id,
                persona_id=persona_id,
                speaker_name=agent.name,
                content=content,
                turn_count=0
            ))
            
            await self._broadcast_message(forum_id, agent.name, content, persona_id, None, stream_id, msg.id)
            
            # Log full speech to system log
            await self._broadcast_system_log(forum_id, content, "speech", agent.name, db=db)

    async def _broadcast_chunk(self, forum_id: int, speaker: str, chunk: str, persona_id: int = None, moderator_id: int = None, stream_id: str = None):
        if not chunk:
            return
            
        await manager.broadcast(forum_id, {
            "type": "message_chunk",
            "data": {
                "speaker_name": speaker,
                "content": chunk,
                "persona_id": persona_id,
                "moderator_id": moderator_id,
                "stream_id": stream_id,
                "timestamp": get_beijing_time_iso()
            }
        })

    async def _broadcast_message(self, forum_id: int, speaker: str, content: str, persona_id: int = None, moderator_id: int = None, stream_id: str = None, msg_id: int = None):
        await manager.broadcast(forum_id, {
            "type": "new_message",
            "data": {
                "id": msg_id,
                "speaker_name": speaker,
                "content": content,
                "persona_id": persona_id,
                "moderator_id": moderator_id,
                "stream_id": stream_id,
                "timestamp": get_beijing_time_iso()
            }
        })

    async def _broadcast_system_message(self, forum_id: int, content: str):
        await manager.broadcast(forum_id, {
            "type": "system",
            "content": content
        })

scheduler = ForumScheduler()
