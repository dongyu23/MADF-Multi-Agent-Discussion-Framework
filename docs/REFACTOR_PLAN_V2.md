# MADF 系统重构与架构优化计划

## 1. 核心目标
遵循“大道至简”原则，消除冗余，实现前后端职责分离，提升系统的可维护性、可扩展性与稳定性。

## 2. 现状分析 (Phase 1)

### 后端 (Backend)
- **API 层臃肿**: `endpoints/forums.py` 包含了过多的业务逻辑（WebSocket 广播、消息创建、权限校验、Agent 触发）。
- **Service 层缺失**: 虽然引入了 `forum_scheduler.py`，但大部分同步业务逻辑仍耦合在 API 路由中。
- **Agent 逻辑**: `app/agent` 模块独立性尚可，但与 API 交互较为生硬。

### 前端 (Frontend)
- **组件巨石化**: `ForumDetailView.vue` 包含了大量的内联样式、逻辑和 UI 结构，缺乏组件拆分。
- **Store 职责不清**: `forum.ts` 同时处理了 API 调用、WebSocket 连接和状态管理，容易导致逻辑混乱。
- **类型定义重复**: 前后端数据模型定义在多处（Store interface vs API Schema），需统一。

## 3. 重构执行路线图

### Phase 2: 后端架构分层 (Service Layer Extraction)
- [ ] **创建 Service 层**: 建立 `app/services/forum_service.py`。
- [ ] **迁移逻辑**: 将 `endpoints/forums.py` 中的 `create_forum`, `post_message`, `trigger_agent` 等核心逻辑迁移至 Service。
- [ ] **统一响应**: 引入 `app/core/response.py`，定义标准的 API 响应格式 `{ code, message, data }`。
- [ ] **异常处理**: 优化 `app/main.py` 中的全局异常处理器，确保所有错误返回统一 JSON 结构。

### Phase 3: 前端组件化与规范化 (Frontend Modularization)
- [ ] **组件拆分**:
    - `components/forum/ChatBubble.vue`: 消息气泡组件。
    - `components/forum/MessageList.vue`: 消息列表容器。
    - `components/forum/ControlPanel.vue`: 底部输入与控制区。
- [ ] **Store 优化**: 将 `forum.ts` 中的 WebSocket 逻辑抽离为 `composables/useForumWebSocket.ts`。
- [ ] **样式统一**: 移除内联 CSS，使用 scoped CSS 或工具类。

### Phase 4: 稳定性与测试 (Testing & Verification)
- [ ] **后端测试**: 为 `ForumService` 编写单元测试。
- [ ] **前端测试**: 修复 `HomeView` 和 `LoginView` 的断言错误。
- [ ] **文档更新**: 更新 `ARCHITECTURE.md` 反映新的分层架构。

## 4. 架构变更预览

### Old Architecture
`API Endpoint` -> `CRUD` -> `DB` (Logic mixed in API)

### New Architecture
`API Endpoint` (Controller) -> `Service Layer` (Business Logic) -> `CRUD Layer` (Data Access) -> `DB`
