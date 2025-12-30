import time
import random
from god import God
from agent import ModeratorAgent, ParticipantAgent
from memory import SharedMemory
import sys

def main():
    print("=== 圆桌论坛系统启动 ===")
    
    # 1. User Inputs
    if len(sys.argv) > 1:
        # Command line mode (Non-interactive)
        theme = sys.argv[1]
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        duration_min = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    else:
        # Interactive mode
        try:
            theme = input("请输入论坛主题 (默认: AI对未来的影响): ") or "AI对未来的影响"
            n_str = input("请输入参会人数 (默认: 3): ") or "3"
            n = int(n_str)
            duration_str = input("请输入论坛时长(分钟) (默认: 5): ") or "5"
            duration_min = int(duration_str)
        except ValueError:
            print("输入无效，使用默认值。")
            theme = "AI对未来的影响"
            n = 3
            duration_min = 5

    # 2. Initialization
    god = God()
    personas = god.generate_personas(theme, n)
    if not personas:
        print("无法生成角色，系统退出。")
        return

    participants = [ParticipantAgent(p['name'], p, n, theme) for p in personas]
    moderator = ModeratorAgent(theme)
    shared_memory = SharedMemory(n)
    
    start_time = time.time()
    end_time = start_time + duration_min * 60
    
    # 3. Opening
    print("\n--- 主持人开场 ---")
    opening_stream = moderator.opening(personas)
    print(f"{moderator.name}: ", end="", flush=True)
    
    opening_speech = ""
    for chunk in opening_stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end='', flush=True)
            opening_speech += content
    print("\n")
    
    # 4. Main Loop
    turn_count = 0
    pending_speaker_data = None # Store (speaker, thought) if applied during summary
    
    while True:
        current_time = time.time()
        
        # Check Time Limit
        if current_time > end_time:
            print("\n--- 时间到，主持人总结 ---")
            closing_stream = moderator.closing(shared_memory.get_summaries())
            print(f"{moderator.name}: ", end="", flush=True)
            
            closing_speech = ""
            for chunk in closing_stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    closing_speech += content
            print()
            break
            
        # Check Shared Memory Summary Buffer
        if shared_memory.is_ready_for_summary():
            print("\n--- 消息窗口已满 (到达上限 n)，主持人进行阶段总结 ---")
            
            # --- REQUIREMENT: "During summary, respond to first application but ignore it." ---
            # Simulate agents wanting to speak while moderator is busy
            print(">>> (主持人总结期间，检测智能体发言申请...)")
            max_priority = max(p.priority for p in participants)
            candidates = [p for p in participants if p.priority == max_priority]
            context = shared_memory.get_context_str()
            
            # Check for application during summary
            for agent in candidates:
                thought = agent.think(context)
                if thought and thought.get('action') == 'apply_to_speak':
                    print(f"检测到 {agent.name} 请求发言 (已记录，总结后立即发言)。")
                    pending_speaker_data = {'speaker': agent, 'thought': thought}
                    break # Only accept one
            
            if not pending_speaker_data:
                print(">>> (无智能体在总结期间申请发言)")
            # -------------------------------------------------------------------------------

            msgs_to_summarize = shared_memory.get_messages_for_summary()
            summary_stream = moderator.periodic_summary(msgs_to_summarize)
            print(f"{moderator.name} (总结): ", end="", flush=True)
            
            summary = ""
            for chunk in summary_stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    summary += content
            print() # Newline
            
            shared_memory.add_summary(summary)
            shared_memory.clear_summary_buffer()
            # Note: The context_window (original message queue) continues sliding, not cleared.
            
            continue

        # Determine Candidates (Max Priority)
        max_priority = max(p.priority for p in participants)
        candidates = [p for p in participants if p.priority == max_priority]
        
        print(f"\n--- 第 {turn_count + 1} 轮 (最高优先级: {max_priority}, 候选人: {[c.name for c in candidates]}) ---")
        
        speaker = None
        thoughts_map = {}
        context = shared_memory.get_context_str()

        # Check if we have a pending speaker from summary phase
        if pending_speaker_data:
            speaker = pending_speaker_data['speaker']
            thought = pending_speaker_data['thought']
            thoughts_map[speaker] = thought # Ensure thought is in map for later logic
            print(f"-> {speaker.name} 在总结期间申请通过，直接发言。")
            pending_speaker_data = None # Reset
            
            # Others didn't think in this turn (skipped), so thoughts_map only has speaker
        else:
            # Agents Think
            applicants = []
            
            print("智能体正在思考...")
            for agent in candidates:
                thought = agent.think(context)
                if thought:
                    thoughts_map[agent] = thought
                    if thought.get('action') == 'apply_to_speak':
                        applicants.append(agent)
            
            if applicants:
                speaker = applicants[0] # Pick first applicant
                print(f"-> {speaker.name} 申请发言成功。")
            else:
                # If no one applied (or all said 'listen'), force one from candidates (Random Start / Fallback)
                if candidates:
                    speaker = random.choice(candidates)
                    print(f"-> 无人主动申请，系统指定 {speaker.name} 发言。")
                else:
                    print("Error: No candidates.")
                    break
        
        # Save thoughts for non-speakers
        for agent in candidates:
            if agent != speaker and agent in thoughts_map:
                agent.private_memory.add_thought(thoughts_map[agent])

        # Speaker Speaks
        if speaker:
            # Check if we have a thought for the speaker
            thought = thoughts_map.get(speaker)
            if not thought:
                # If think failed or forced, create dummy thought with 'analysis'
                thought = {
                    "focus": "系统指派", 
                    "attitude": "中立", 
                    "analysis": "无（思考过程解析失败或被系统强制发言）",
                    "action": "listen"
                }
            
            print(f"\n{speaker.name} ({speaker.title}) 正在发言...")
            response_stream = speaker.speak(thought, context)
            
            full_content = ""
            if response_stream:
                for chunk in response_stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        print(content, end='', flush=True)
                        full_content += content
                print() # Newline
            
            # Update State
            shared_memory.add_message(speaker.name, full_content)
            speaker.private_memory.add_speech(full_content)
            speaker.priority -= 1
            turn_count += 1
            
            time.sleep(1)

if __name__ == "__main__":
    main()
