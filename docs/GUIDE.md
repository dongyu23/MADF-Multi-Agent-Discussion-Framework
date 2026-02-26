# MADF 开发指南

## 1. 环境配置与快速开始

### 1.1 后端设置 (Python)

1. **创建虚拟环境**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # 或
   .venv\Scripts\activate  # Windows
   ```

2. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

3. **环境变量**:
   复制 `.env.example` 为 `.env` 并填入配置：
   ```ini
   ZHIPUAI_API_KEY=your_key_here
   DATABASE_URL=sqlite:///./sql_app.db
   SECRET_KEY=your_secret_key
   ```

4. **数据库迁移**:
   ```bash
   alembic upgrade head
   ```

5. **启动服务**:
   ```bash
   uvicorn app.main:app --reload
   ```
   API 文档地址: `http://localhost:8000/docs`

### 1.2 前端设置 (Vue 3)

1. **安装依赖**:
   ```bash
   cd frontend
   npm install
   ```

2. **启动开发服务器**:
   ```bash
   npm run dev
   ```
   访问地址: `http://localhost:5173`

## 2. API 规范

所有 API 均遵循 RESTful 风格，返回 JSON 格式。

- **基础 URL**: `/api/v1`
- **认证方式**: Bearer Token (JWT)

### 常用接口示例

- **登录**: `POST /auth/login/access-token`
- **获取当前用户**: `GET /users/me`
- **创建论坛**: `POST /forums/`
  ```json
  {
    "topic": "AI Future",
    "description": "Discussing the impact of AI."
  }
  ```

## 3. 部署流程

### Docker 部署

项目根目录包含 `Dockerfile`，可用于构建后端镜像。

```bash
# 构建镜像
docker build -t madf-backend .

# 运行容器
docker run -d -p 8000:8000 --env-file .env madf-backend
```

### 生产环境建议
- 使用 **Nginx** 作为反向代理，处理静态文件和 SSL。
- 数据库使用 **PostgreSQL** 替代 SQLite。
- 使用 **Gunicorn** 配合 Uvicorn Worker 运行 Python 服务。

## 4. 测试策略

### 后端测试
使用 `pytest` 运行测试：
```bash
pytest
```
- **单元测试**: 覆盖 `app/core` 和 `app/utils`。
- **集成测试**: 覆盖 API 端点 (`app/tests/api`).

### 前端测试
- **单元测试**: `npm run test:unit` (Vitest)
- **端到端测试**: `npm run test:e2e` (Cypress)

## 5. CI/CD 规范

项目配置了 GitHub Actions (`.github/workflows/`)：
- **Backend CI**: 推送至 `main` 分支时触发，运行 Lint (Flake8) 和 Pytest。
- **Frontend CI**: 推送时触发，运行 Build 和 Test。

确保提交前运行以下命令检查代码质量：
```bash
# 后端
flake8 app
# 前端
npm run lint
```
