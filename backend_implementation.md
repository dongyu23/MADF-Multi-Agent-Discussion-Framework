# 圆桌论坛多智能体系统后端实现逻辑文档

**日期**: 2025-12-30
**状态**: 开发中/已验证核心功能
**作者**: 自动生成 (Pair Programmer)

---

## 1. 系统概述 (System Overview)

本系统模拟了一个基于大语言模型（LLM）的**圆桌论坛**场景。系统包含一个主持人（Moderator）和多位个性鲜明的参与嘉宾（Participants）。嘉宾通过上帝视角（God）根据主题自动生成，具有独立的生平、理论武库和预设立场。

系统采用**多智能体协作（Multi-Agent Collaboration）**架构，通过共享内存（Shared Memory）和私有内存（Private Memory）管理上下文，实现了基于优先级的发言权争夺机制、实时流式输出以及主持人控场功能。

---

## 2. 核心模块 (Core Modules)

系统由五个核心文件组成，各司其职：

### 2.1 主控制器 (`main.py`)
整个系统的入口与编排器，负责时间管理、循环调度和事件分发。

*   **初始化**: 接收用户输入（主题、人数、时长），调用 `God` 生成角色，初始化 `ModeratorAgent` 和 `ParticipantAgent`。
*   **主循环 (Main Loop)**:
    1.  **时间检查**: 判断是否达到预设时长，若到达则触发主持人总结（Closing）并退出。
    2.  **消息缓冲区检查**:
        *   若 `SharedMemory` 缓冲区已满（达到 n 条发言），触发**主持人阶段总结 (Periodic Summary)**。
        *   **并发申请处理**: 在总结期间，系统会检测是否有高优先级智能体申请发言。若有，记录该申请（`pending_speaker_data`），并在总结结束后立即安排其发言（无需再次思考）。
    3.  **发言权争夺**:
        *   确定当前最高优先级（Priority）。
        *   让所有最高优先级的候选人（Candidates）进行“快思考”（Think）。
        *   **决策逻辑**: 优先选择主动申请发言（`apply_to_speak`）的智能体；若多人申请则选第一个；若无人申请则随机指派。
    4.  **发言执行**: 调用胜出者的 `speak()` 方法进行流式发言。
    5.  **状态更新**:
        *   将发言存入 `SharedMemory`。
        *   将发言存入该智能体的 `PrivateMemory`（发言历史）。
        *   将未发言者的思考内容（Inner Thoughts）存入其 `PrivateMemory`（思考历史）。
        *   降低发言者的优先级（`priority -= 1`）以平衡话语权。

### 2.2 智能体系统 (`agent.py`)
定义了两种类型的智能体，均继承自 `BaseAgent`。

#### A. 主持人 (`ModeratorAgent`)
*   **职责**: 开场、阶段性总结、结束语。
*   **特点**:
    *   持有 `self.theme`（论坛主题），在所有 Prompt 中注入主题以防跑题。
    *   所有输出方法（`opening`, `periodic_summary`, `closing`）均返回 **生成器 (Generator)**，支持流式输出 (`stream=True`)。

#### B. 参与嘉宾 (`ParticipantAgent`)
*   **初始化**: 接收 `persona`（人设字典）和 `theme`。
*   **核心行为**:
    1.  **思考 (`think`)**:
        *   **输入**: 当前上下文 (`context`)、最近一次私有思考 (`my_memory`)。
        *   **输出**: JSON 格式决策，包含 `action` (apply_to_speak/listen)、`mind` (内心戏)、`previous` (对前人观点的看法) 等。
        *   **逻辑**: 基于生平（Bio）和理论武库（Theories）进行判断，而非通用逻辑。
    2.  **发言 (`speak`)**:
        *   **输入**: 思考结果 (`thought`)、上下文、私有记忆（思考历史 + 发言历史）。
        *   **输出**: 流式文本。
        *   **Prompt 优化**: 注入了“我之前的发言”历史，确保自我一致性；注入 `theme` 确保不跑题。

### 2.3 上帝系统 (`god.py`)
*   **功能**: 负责根据用户输入的主题，动态生成 `n` 位具有深度人设的专家。
*   **生成逻辑**: 调用 LLM 生成 JSON 列表，包含姓名、头衔、**300字深度生平**、7个理论武库、预设立场和系统提示词（System Prompt）。

### 2.4 内存系统 (`memory.py`)
分为两类内存，模拟人类的短期交互记忆和长期自我记忆。

#### A. 共享内存 (`SharedMemory`)
所有智能体可见的“公屏”。
*   `context_window` (deque): 滑动窗口，存储最近 `n` 条对话（原文）。
*   `summary_history` (list): 存储主持人生成的阶段性总结（摘要）。
*   `summary_buffer` (list): 临时存储待总结的消息。
*   **上下文构建**: `get_context_str()` 方法组合了“过往总结”和“近期讨论”，为智能体提供完整的语境。

#### B. 私有内存 (`PrivateMemory`)
每个智能体独享，互不可见。
*   `thoughts` (list): 存储 `think` 阶段产生的 JSON 数据（内心戏）。用于保持思维连贯性。
*   `speeches` (list): 存储自己说过的原文。用于避免重复和自我矛盾。
*   **接口**: `get_recent_thought_str()` 和 `get_speech_history_str()`。

### 2.5 工具库 (`utils.py`)
*   **LLM 交互**: 封装 `ZhipuAI` 客户端。
*   **`get_chat_completion`**: 支持普通模式、流式模式 (`stream=True`) 和 JSON 模式 (`json_mode=True`)。
*   **参数配置**: 默认 `temperature=0.8`（激发创造力），`max_tokens=4096`。

---

## 3. 关键数据流 (Data Flow)

1.  **初始化流**: User Input -> `main` -> `God` -> LLM -> Personas -> `Agent` Init.
2.  **思考流**: SharedMemory Context + PrivateMemory (Last Thought) -> `Participant.think()` -> JSON Decision.
3.  **决策流**: 所有 Candidates 的 JSON -> `main` 逻辑判断 -> 选出 Speaker -> 其他人的 Thought 存入 PrivateMemory.
4.  **发言流**: Speaker Thought + Context + PrivateMemory (Speeches) -> `Participant.speak()` -> Stream Output -> User Terminal.
5.  **记忆更新流**: Speech Content -> SharedMemory (Window & Buffer) & Speaker's PrivateMemory.

---

## 4. 特性与机制 (Key Features)

1.  **主题强一致性 (Theme Injection)**:
    *   在 `main.py` 初始化时将 `theme` 传入所有 Agent。
    *   在 `ParticipantAgent` 的 `think` 和 `speak` Prompt 中强制注入 `theme`，防止多轮对话后话题漂移。
    *   在 `ModeratorAgent` 的所有环节注入 `theme`。

2.  **全链路流式输出 (Full Streaming)**:
    *   不仅嘉宾发言是流式的，主持人的开场、总结和结束语也全部改造为流式输出，提升用户体验。

3.  **异步申请模拟 (Async Application Simulation)**:
    *   在主持人进行阶段总结（通常较长）期间，系统会检测是否有智能体急切想要发言。
    *   若有申请，系统记录该状态，待主持人总结完毕后，**跳过**下一轮的思考环节，直接让该智能体发言，模拟“举手等待”的效果。

4.  **自我一致性增强**:
    *   通过 `PrivateMemory` 记录过往发言和内心戏，智能体在发言时能“记得”自己刚才说过什么和想过什么，避免精神分裂或复读机行为。

---

## 5. 开发记录与注意事项

*   **API 依赖**: 依赖智谱 AI (GLM-4-Air)，Key 位于 `config.py` (实际在 user rules 中)。
*   **环境依赖**: `zhipuai` SDK。
*   **扩展性**:
    *   目前 `God` 生成的人设偏向于领域专家，可通过修改 `god.py` 中的 Prompt 调整人设风格。
    *   `SharedMemory` 的窗口大小默认为参会人数 `n`，可根据 Token 限制进行调整。

---
*文档生成完毕*
