# MADF - Multi-Agent Discussion Framework

这是一个基于大语言模型的多智能体圆桌讨论框架。

## 1. 依赖配置与安装

本项目使用 Python 开发，依赖管理通过 `requirements.txt` 进行。

### 1.1 环境准备

建议使用 Python 3.10+ 版本。
请在项目根目录下创建并激活虚拟环境：

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (Linux/macOS)
source .venv/bin/activate
```

### 1.2 配置镜像源

为确保下载速度和稳定性，建议配置国内镜像源（如清华源）：

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### 1.3 安装依赖

执行以下命令安装所有依赖（包括开发和生产环境）：

```bash
pip install -r requirements.txt
```

### 1.4 依赖完整性校验

项目依赖已锁定版本。你可以通过以下命令生成依赖树报告以进行审计：

```bash
pipdeptree > dependency_tree_report.txt
```

## 2. 项目架构与结构

详细的架构说明、文件角色定义及依赖关系图谱，请参考：
👉 **[架构说明文档 (Architecture Readme)](docs/architecture_readme.md)**

## 3. API 服务 (FastAPI)

本项目已重构为基于 FastAPI 的 RESTful 服务。

### 2.1 启动服务

```bash
python app/main.py
# 或
uvicorn app.main:app --reload
```

服务启动后，访问 `http://localhost:8000/docs` 查看交互式 API 文档。

### 2.2 数据库迁移 (Alembic)

项目使用 Alembic 进行数据库版本管理。

```bash
# 生成新的迁移脚本（修改模型后执行）
alembic revision --autogenerate -m "description"

# 应用迁移到数据库
alembic upgrade head
```

### 2.3 运行 API 测试

```bash
python -m pytest app/tests/test_api.py
```

## 3. 命令行工具 (Legacy)

原有的命令行工具仍然保留，可用于快速演示。

```bash
python main.py "讨论主题" 3 5
```

## 4. 构建与测试流程

自动化构建脚本 `build_and_test.py` 已更新，涵盖 API 测试。

```bash
python build_and_test.py
```

## 5. 容器化部署

```bash
docker build -t madf-agent .
docker run -p 8000:8000 madf-agent uvicorn app.main:app --host 0.0.0.0 --port 8000
```
