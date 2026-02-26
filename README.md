# MADF - Multi-Agent Discussion Framework

这是一个基于大语言模型的多智能体圆桌讨论框架。项目采用前后端分离架构，后端使用 FastAPI，前端使用 Vue 3。

## 📚 开发文档索引

本项目包含详细的开发文档，请参考以下链接进行开发和维护：

- **[项目架构文档 (Architecture)](docs/ARCHITECTURE.md)**: 包含系统架构图、模块依赖关系、核心模块详细分析（输入输出、数据流）。
- **[开发指南 (Guide)](docs/GUIDE.md)**: 包含环境配置、API 规范、数据库设计、部署流程、测试策略及 CI/CD 规范。
- **[重构与路线图 (Refactoring & Roadmap)](docs/REFACTORING_AND_ROADMAP.md)**: 包含冗余模块分析、健康度评分、后续开发计划及技术债务清单。

## 1. 快速开始

### 1.1 环境准备

建议使用 Python 3.10+ 版本。

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (Linux/macOS)
source .venv/bin/activate
```

### 1.2 安装依赖

```bash
pip install -r requirements.txt
```

### 1.3 启动服务

**后端 (FastAPI)**:
```bash
uvicorn app.main:app --reload
```
API 文档地址: `http://localhost:8000/docs`

**前端 (Vue 3)**:
```bash
cd frontend
npm install
npm run dev
```
访问地址: `http://localhost:5173`

## 2. 遗留代码说明

项目根目录下的 `agent.py`, `god.py`, `memory.py`, `database.py`, `main.py` 为早期的原型验证脚本，目前已重构并迁移至 `app/` 目录下。

**推荐使用 `app/` 目录下的现代架构进行开发。**

## 3. 测试与部署

详细的测试命令和 Docker 部署流程请参考 [开发指南](docs/GUIDE.md)。

```bash
# 运行后端测试
pytest

# 运行前端测试
cd frontend && npm run test:unit
```
