import asyncio
import logging
import time
import traceback
import uuid
from typing import Any
from app.db.session import db_manager
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
# Removed SQLAlchemy models import as we use schemas/dicts
from app.core.time_utils import get_beijing_time, get_beijing_time_iso
from app.core.async_utils import async_generator_wrapper

logger = logging.getLogger(__name__)

class ForumScheduler:
    def __init__(self):
        self.running_tasks = {}

    async def start_forum(self, forum_id: int, ablation_flags: dict = None):
        if forum_id in self.running_tasks:
            logger.warning(f"Forum {forum_id} is already running.")
            return

        task = asyncio.create_task(self._run_forum_loop(forum_id, ablation_flags))
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

    async def _broadcast_system_log(self, forum_id: int, message: str, level: str = "info", source: str = "System", db: Any = None):
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

    async def _run_forum_loop(self, forum_id: int, ablation_flags: dict = None):
        ablation_flags = ablation_flags or {}
        logger.info(f"Starting forum loop for {forum_id} with flags: {ablation_flags}")
        await self._broadcast_system_log(forum_id, f"论坛主循环启动... (配置: {ablation_flags})")
        
        # Use new DB client
        db = db_manager.get_connection()
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
                    theme=forum.topic,
                    ablation_flags=ablation_flags
                )
                
                # Restore memory only if private memory is NOT ablated
                if not ablation_flags.get("no_private_memory"):
                    if hasattr(p_db, 'thoughts_history') and p_db.thoughts_history:
                        # thoughts_history is a JSON string from DB (via RowObject)
                        # Wait, CRUD handles JSON dumping, but fetching?
                        # RowObject just has the raw value. 
                        # In crud.__init__.py: get_forum_participants doesn't decode JSON.
                        # Wait, I missed decoding JSON in get_forum_participants!
                        # I should fix that in crud. Or handle it here.
                        # Let's check crud.
                        import json
                        history = []
                        if isinstance(p_db.thoughts_history, str):
                            try:
                                history = json.loads(p_db.thoughts_history)
                            except:
                                history = []
                        elif isinstance(p_db.thoughts_history, list):
                            history = p_db.thoughts_history
                            
                        for t in history:
                            agent.private_memory.add_thought(t)
                
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
            fallback_speaker_idx = 0
            
            while True:
                # Reload forum to check for external stop signals or status changes
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
                    # Parse summary history if string
                    summaries = forum.summary_history
                    if isinstance(summaries, str):
                        import json
                        try:
                            summaries = json.loads(summaries)
                        except:
                            summaries = []
                    
                    for s in summaries:
                        shared_memory.add_summary(s)
                        
                for m in messages:
                    shared_memory.add_message(m.speaker_name, m.content)
                
                # Sync private memories with recent speeches (if allowed)
                if not ablation_flags.get("no_private_memory"):
                    for agent in participants:
                        agent.private_memory.speech_history = []
                        my_msgs = [m for m in messages if m.speaker_name == agent.name]
                        for m in my_msgs:
                            agent.private_memory.add_speech(m.content)

                # 3. Check Summary (If not ablated)
                msg_count = len(messages)
                N_WINDOW = 20 # Configurable default
                
                if not ablation_flags.get("no_summary"):
                    if msg_count > 0 and msg_count % N_WINDOW == 0:
                        last_msg = messages[-1]
                        if last_msg.speaker_name != moderator.name:
                            logger.info(f"Forum {forum_id} triggering summary (msg count {msg_count}).")
                            # Summarize the last N messages
                            msgs_to_summarize = messages[-N_WINDOW:]
                            await self._moderator_speak(db, forum_id, moderator, "periodic_summary", messages=msgs_to_summarize)

                # 4. Select Speaker (Queue Based)
                if ablation_flags.get("no_shared_memory"):
                    # Ablation: Minimal context (only last message)
                    if messages:
                        last_m = messages[-1]
                        context_str = f"【最新发言】\n{last_m.speaker_name}: {last_m.content}"
                    else:
                        context_str = "(暂无发言)"
                else:
                    context_str = shared_memory.get_context_str()

                speaker = None
                thoughts_map = {}
                
                # Everyone thinks
                await self._broadcast_system_log(forum_id, "所有参与者正在思考中 (分步处理)...", "info")
                logger.info(f"Forum {forum_id}: Agents start thinking...")
                
                async def agent_think(ag):
                    try:
                        # Log individual agent thinking
                        await self._broadcast_system_log(forum_id, f"嘉宾 [{ag.name}] 正在思考...", "thought")
                        thought = await asyncio.wait_for(
                            asyncio.to_thread(ag.think, context_str),
                            timeout=30 # Increased timeout for slow API
                        )
                        return ag, thought
                    except asyncio.TimeoutError:
                        logger.warning(f"Agent {ag.name} think timeout")
                        return ag, None
                    except Exception as e:
                        logger.error(f"Agent {ag.name} think failed: {e}")
                        return ag, None

                think_results = []
                for p in participants:
                    res = await agent_think(p)
                    think_results.append(res)
                    # Small delay between thinking calls to avoid rate limits (429)
                    await asyncio.sleep(1.0)
                    
                logger.info(f"Forum {forum_id}: Agents finished thinking.")
                
                for agent, thought in think_results:
                    if thought:
                        thoughts_map[agent] = thought
                        if thought.get('action') == 'apply_to_speak':
                            # Add to queue if not already there AND hasn't spoken in current batch
                            if agent not in speaker_queue:
                                if agent in batch_spoken_agents and speaker_queue:
                                    pass
                                else:
                                    speaker_queue.append(agent)
                        
                        # Save thought to DB (Private History)
                        p_db = next((p for p in participants_db if p.persona.name == agent.name), None)
                        if p_db:
                             # Need to parse current history if string
                             current_hist = []
                             if hasattr(p_db, 'thoughts_history'):
                                 if isinstance(p_db.thoughts_history, str):
                                     import json
                                     try:
                                         current_hist = json.loads(p_db.thoughts_history)
                                     except:
                                         pass
                                 elif isinstance(p_db.thoughts_history, list):
                                     current_hist = p_db.thoughts_history
                                     
                             new_thoughts = current_hist + [thought]
                             update_forum_participant(db, forum_id, p_db.persona_id, thoughts_history=new_thoughts)

                # Pop from queue
                if speaker_queue:
                    speaker = speaker_queue.pop(0)
                    batch_spoken_agents.add(speaker)
                elif participants:
                    speaker = participants[fallback_speaker_idx % len(participants)]
                    fallback_speaker_idx += 1
                
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
            # Broadcast the error to the system log so user can see it
            try:
                await self._broadcast_system_log(forum_id, f"论坛异常终止: {str(e)}", "error")
            except:
                pass
        finally:
            db.close()

    async def _moderator_speak(self, db: Any, forum_id: int, moderator: ModeratorAgent, action: str, guests=None, messages=None):
        content = ""
        gen = None
        stream_id = str(uuid.uuid4())
        
        forum = get_forum(db, forum_id)
        moderator_id = forum.moderator_id
        
        await self._broadcast_system_log(forum_id, f"主持人 [{moderator.name}] 正在构思...", "info")
        try:
            if action == "opening":
                guest_list = [{"name": g.name, "title": g.title, "stance": g.stance} for g in guests]
                gen = await asyncio.to_thread(moderator.opening, guest_list)
            elif action == "closing":
                forum = get_forum(db, forum_id)
                # Parse summary history
                summaries = forum.summary_history or []
                if isinstance(summaries, str):
                    import json
                    try:
                        summaries = json.loads(summaries)
                    except:
                        summaries = []
                        
                gen = await asyncio.to_thread(moderator.closing, summaries)
            elif action == "periodic_summary":
                msgs_text = [{"speaker": m.speaker_name, "content": m.content} for m in messages[-20:]]
                gen = await asyncio.to_thread(moderator.periodic_summary, msgs_text)

            if gen:
                try:
                    # Mark that streaming started
                    await self._broadcast_system_log(forum_id, f"主持人 [{moderator.name}] 开始发言...", "info")
                    
                    async for chunk in async_generator_wrapper(gen):
                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                            token = chunk.choices[0].delta.content
                            content += token
                            await self._broadcast_chunk(forum_id, moderator.name, token, None, moderator_id, stream_id)
                except Exception as e:
                     logger.error(f"Error consuming generator: {e}")
            else:
                logger.warning("Moderator speak returned None generator")
                
        except Exception as e:
            logger.error(f"Moderator speak failed: {e}")
            logger.error(traceback.format_exc())
            await self._broadcast_system_log(forum_id, f"主持人发言生成失败: {str(e)}", "error")
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
                current = forum.summary_history or []
                if isinstance(current, str):
                    import json
                    try:
                        current = json.loads(current)
                    except:
                        current = []
                new_history = current + [content]
                update_forum(db, forum_id, summary_history=new_history)

            await self._broadcast_message(forum_id, moderator.name, content, None, moderator_id, stream_id, msg.id)
            
            # Log full speech
            await self._broadcast_system_log(forum_id, content, "speech", moderator.name, db=db)

    async def _agent_speak(self, db: Any, forum_id: int, agent: ParticipantAgent, thought: dict, context: str):
        content = ""
        stream_id = str(uuid.uuid4())
        participants = get_forum_participants(db, forum_id)
        p_db = next((p for p in participants if p.persona.name == agent.name), None)
        persona_id = p_db.persona_id if p_db else None

        await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 正在构思中...", "info")
        try:
            gen = await asyncio.to_thread(agent.speak, thought, context)
            if gen:
                try:
                    await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 开始发言...", "info")
                    async for chunk in async_generator_wrapper(gen):
                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                            token = chunk.choices[0].delta.content
                            content += token
                            await self._broadcast_chunk(forum_id, agent.name, token, persona_id, None, stream_id)
                except Exception as e:
                    logger.error(f"Error consuming agent generator: {e}")
            else:
                logger.warning(f"Agent {agent.name} speak returned None")
                content = "(沉默)"
        except Exception as e:
            logger.error(f"Agent {agent.name} speak failed: {e}")
            await self._broadcast_system_log(forum_id, f"嘉宾 [{agent.name}] 发言生成失败: {str(e)}", "error")
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
                "forum_id": forum_id,
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
