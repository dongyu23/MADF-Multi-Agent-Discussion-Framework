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
- **Linting**: ESLint, Prettier, Flake8
- **CI/CD**: GitHub Actions (前端: `frontend-ci.yml`, 后端: `backend-ci.yml`)

## 2. 后端 API 现状

### 接口概览
目前共开发 **11** 个 RESTful API 接口，分布在 `app/api/v1/endpoints/` 下：

| 模块 | 路径 | 方法 | 功能描述 |
| :--- | :--- | :--- | :--- |
| **Users** | `/users/` | POST | 创建用户 |
| **Users** | `/users/{username}` | GET | 获取用户信息 |
| **Personas** | `/personas/` | POST | 创建角色 (需 owner_id) |
| **Personas** | `/personas/{persona_id}` | GET | 获取角色详情 |
| **Personas** | `/personas/{persona_id}` | PUT | 更新角色信息 |
| **Personas** | `/personas/{persona_id}` | DELETE | 删除角色 |
| **Forums** | `/forums/` | POST | 创建论坛 (需 creator_id) |
| **Forums** | `/forums/{forum_id}` | GET | 获取论坛详情 |
| **Forums** | `/forums/{forum_id}/messages` | POST | 发送消息 |
| **Forums** | `/forums/{forum_id}/messages` | GET | 获取消息列表 |
| **Agents** | `/agents/chat` | POST | 智能体对话 (Stateless) |

### 质量指标
- **接口文档**: FastAPI 自动生成的 Swagger UI (`/docs`) 完整覆盖所有接口，包含请求/响应 Schema。
- **测试覆盖率**: 后端整体测试覆盖率达到 **90%** (基于 `pytest-cov` 报告)。
- **性能**: 目前使用 SQLite，适合开发和测试。生产环境需评估是否迁移至 PostgreSQL/MySQL。

## 3. 前端完成度现状

### 页面开发
- **HomeView (`/`)**: 智能体对话主界面。已实现聊天气泡显示、输入框、侧边栏配置（Agent 设定）及思维链展示。
- **TestView (`/test`)**: API 测试面板。已实现用户注册、角色创建、论坛创建的表单交互，直接对接后端 API。

### 交互与优化
- **交互逻辑**: 基于 Pinia 的状态管理已打通，支持实时对话流。
- **静态资源**: Vite 默认配置，支持按需加载。
- **国际化**: 已实现中英文切换基础框架。
- **暗黑模式**: 已集成 Ant Design 的暗黑主题切换。

## 4. 冗余组件分析

随着项目从单脚本原型向 FastAPI 架构迁移，根目录下遗留了大量不再需要的代码文件：

| 文件名 | 功能描述 | 冗余原因 | 建议操作 |
| :--- | :--- | :--- | :--- |
| `agent.py` | 原 Agent 类定义 | 已迁移至 `app/agent/agent.py` | 删除 |
| `god.py` | 原上帝视角逻辑 | 已迁移至 `app/agent/god.py` (如有) 或需确认迁移 | 删除/归档 |
| `memory.py` | 原记忆模块 | 已迁移至 `app/agent/memory.py` | 删除 |
| `database.py` | 原数据库连接 | 已重构为 `app/db/` 和 `app/models/` | 删除 |
| `utils.py` | 原工具函数 | 功能分散至 `app/` 或需迁移至 `app/core/utils.py` | 迁移后删除 |
| `main.py` (根目录) | 原 CLI 入口 | 已由 `app/main.py` (Web 入口) 取代 | 删除/归档 |

## 5. 前后端适配问题与挑战

### 已解决问题
- **跨域 (CORS)**: 后端已配置 `allow_origins=["*"]`，前端 Vite 配置了 `/api` 代理，开发环境通信正常。
- **数据格式**: 前端 TypeScript 接口定义 (`frontend/src/stores/agent.ts`) 与后端 Pydantic Schema (`app/schemas/__init__.py`) 基本一致。

### 潜在/现有问题
1.  **认证缺失**: 目前 API 仅依赖 ID (如 `owner_id`, `creator_id`) 进行操作，**没有任何身份验证 (JWT/OAuth)**。前端可以直接伪造请求操作任意用户数据。
2.  **错误处理**: 前端对后端错误的展示较为原始（直接显示 error message），缺乏统一的错误码处理机制。
3.  **类型同步**: 前端 TypeScript 类型定义是手写的，未与后端 Pydantic 模型自动同步（如使用 `openapi-typescript`），后端模型变更可能导致前端类型错误。
4.  **状态同步**: 论坛消息目前采用轮询或单次获取 (`GET`), 缺乏 WebSocket 或 SSE 实现实时聊天体验。
