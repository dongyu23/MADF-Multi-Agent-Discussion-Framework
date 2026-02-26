# 项目审计与现状文档

## 1. 技术栈构成

### 前端模块 (Frontend)
- **核心框架**: Vue 3 (v3.5.25)
- **构建工具**: Vite (v6.x)
- **语言**: TypeScript (v5.6.2)
- **UI 组件库**: Ant Design Vue (v4.2.6)
- **状态管理**: Pinia (v3.0.4)
- **路由管理**: Vue Router (v4.x)
- **HTTP 客户端**: Axios (v1.13.5)
- **国际化**: Vue I18n (v11.2.8)
- **CSS 预处理**: Sass (v1.97.3)
- **测试**: Vitest (单元测试), Cypress (E2E 测试)
- **Linting**: ESLint (v8.57) + Flat Config

### 后端服务 (Backend)
- **语言**: Python 3.10
- **Web 框架**: FastAPI
- **ORM**: SQLAlchemy
- **数据库**: SQLite (当前开发环境)
- **数据库迁移**: Alembic
- **数据验证**: Pydantic
- **AI SDK**: ZhipuAI (v2.1.5.20250825)
- **服务器**: Uvicorn

### 中间件与工具
- **CORS**: FastAPI CORSMiddleware (已配置允许所有源 `*`)
- **CI/CD**: GitHub Actions (前端: `frontend-ci.yml`, 后端: `backend-ci.yml`)

## 2. 后端 API 现状

### 接口概览
目前共开发 **16** 个 RESTful API 接口，分布在 `app/api/v1/endpoints/` 下：

| 模块 | 路径 | 方法 | 功能描述 |
| :--- | :--- | :--- | :--- |
| **Auth** | `/auth/register` | POST | 用户注册 |
| **Auth** | `/auth/login` | POST | 用户登录 (JWT) |
| **Users** | `/users/me` | GET | 获取当前用户信息 |
| **Personas** | `/personas/` | POST | 创建角色 (需 owner_id) |
| **Personas** | `/personas/batch/preset` | POST | 批量创建预设角色 |
| **Personas** | `/personas/{persona_id}` | GET | 获取角色详情 |
| **Personas** | `/personas/{persona_id}` | PUT | 更新角色信息 |
| **Personas** | `/personas/{persona_id}` | DELETE | 删除角色 |
| **Forums** | `/forums/` | POST | 创建论坛 (需 creator_id) |
| **Forums** | `/forums/{forum_id}` | GET | 获取论坛详情 |
| **Forums** | `/forums/{forum_id}/messages` | POST | 发送消息 |
| **Forums** | `/forums/{forum_id}/messages` | GET | 获取消息列表 |
| **Forums** | `/forums/{forum_id}/trigger_agent` | POST | 触发 Agent 思考并发言 |
| **Forums** | `/forums/{forum_id}/trigger_moderator` | POST | 触发主持人控场 |
| **Agents** | `/agents/chat` | POST | 智能体对话 (Stateless) |
| **God** | `/god/generate` | POST | 上帝模式：自然语言生成智能体 |

### 质量指标
- **接口文档**: FastAPI 自动生成的 Swagger UI (`/docs`) 完整覆盖所有接口，包含请求/响应 Schema。
- **测试覆盖率**: 后端整体测试覆盖率达到 **90%** (基于 `pytest-cov` 报告)。
- **错误处理**: 全局异常捕获机制已上线，杜绝 500 页面直接暴露堆栈。

## 3. 前端完成度现状

### 页面开发
- **HomeView (`/dashboard`)**: 系统概览页，展示核心指标。
- **GodAgentView (`/god`)**: **新增** 上帝智能体对话界面，支持自然语言创建角色。
- **PersonaView (`/personas`)**: 智能体工坊。支持查看、编辑、删除角色，展示深度生平、理论武库等富文本信息。
- **ForumListView (`/forums`)**: 论坛列表与创建。
- **ForumDetailView (`/forums/:id`)**: 圆桌论坛详情。支持实时消息展示、主持人控场工具栏、Agent 手动触发。
- **TestView (`/test`)**: API 测试面板。

### 交互与优化
- **状态管理**: Pinia Store (`auth`, `forum`, `persona`, `god`) 全面接管数据流。
- **错误处理**: 统一的 Axios 拦截器，处理 401 (自动登出)、500 (友好提示) 及网络异常。
- **加载状态**: 所有异步操作均绑定 `loading` 状态，防止重复提交和 UI 卡顿。
- **WebSocket**: 论坛消息支持 WebSocket 实时推送 (基础实现)。

## 4. 冗余组件分析

随着项目从单脚本原型向 FastAPI 架构迁移，根目录下遗留了大量不再需要的代码文件：

| 文件名 | 功能描述 | 冗余原因 | 建议操作 |
| :--- | :--- | :--- | :--- |
| `agent.py` | 原 Agent 类定义 | 已迁移至 `app/agent/agent.py` | 删除 |
| `god.py` | 原上帝视角逻辑 | 已迁移至 `app/agent/god.py` | 删除 |
| `memory.py` | 原记忆模块 | 已迁移至 `app/agent/memory.py` | 删除 |
| `database.py` | 原数据库连接 | 已重构为 `app/db/` 和 `app/models/` | 删除 |
| `utils.py` | 原工具函数 | 功能分散至 `app/` 或需迁移至 `app/core/utils.py` | 迁移后删除 |
| `main.py` (根目录) | 原 CLI 入口 | 已由 `app/main.py` (Web 入口) 取代 | 删除 |

## 5. 前后端适配问题与挑战

### 已解决问题
- **认证 (Auth)**: 实现了基于 JWT 的完整认证流程 (`/auth/login`)，前端自动附加 Token。
- **错误处理**: 前后端均实现了健壮的错误捕获与提示机制。
- **数据一致性**: 修复了 JSON 字段 (`theories`, `summary_history`) 在数据库存储与前端展示之间的解析问题。
- **Linting**: 修复了 ESLint 配置，支持 Vue 3 + TypeScript Flat Config。

### 潜在/现有问题
1.  **WebSocket 稳定性**: 目前 WebSocket 连接在网络波动下可能断开，需增加心跳和自动重连机制。
2.  **类型同步**: 前端 TypeScript 类型定义仍需手动维护，建议引入 `openapi-typescript` 自动生成。
