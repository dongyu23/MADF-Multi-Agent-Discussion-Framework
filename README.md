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

`dependency_tree_report.txt` 文件包含了详细的依赖关系树、版本号及来源信息。

## 2. 构建与测试流程

本项目提供了一个自动化的构建脚本 `build_and_test.py`，用于执行完整的构建流程，包括依赖检查、代码风格检查、单元测试和容器构建。

### 2.1 执行完整构建

在本地环境运行以下命令：

```bash
python build_and_test.py
```

该脚本将依次执行：
1. **依赖安装**：确保环境一致。
2. **依赖报告生成**：输出 `dependency_tree_report.txt`。
3. **代码检查 (Lint)**：使用 `flake8` 检查代码风格。
4. **单元测试 (Smoke Test)**：使用 `pytest` 运行 `tests/test_smoke.py`，验证核心类实例化和 API 连通性。
5. **容器构建 (Docker)**：尝试构建 Docker 镜像（如果已安装 Docker）。
6. **端到端测试 (E2E)**：模拟运行应用程序 (`python main.py`) 1 分钟，确保无运行时错误。

### 2.2 手动运行测试

你也可以手动运行测试：

```bash
# 运行单元/冒烟测试
python -m pytest tests/test_smoke.py

# 运行端到端测试 (主题="测试", 人数=3, 时长=1分钟)
python main.py "测试主题" 3 1
```

## 3. 容器化部署

本项目支持 Docker 容器化部署。

### 3.1 构建镜像

```bash
docker build -t madf-agent .
```

### 3.2 运行容器

```bash
# 交互式运行 (默认配置)
docker run -it --rm madf-agent

# 指定参数运行 (主题="AI未来", 人数=3, 时长=5分钟)
docker run -it --rm madf-agent python main.py "AI未来" 3 5
```

## 4. CI/CD 集成建议

在 CI 环境（如 Jenkins, GitLab CI, GitHub Actions）中，可以直接复用 `build_and_test.py` 脚本作为构建步骤。确保 CI Runner 已安装 Python 3.10+ 和 Docker（可选）。

## 5. 依赖清单

核心依赖包括：
- `zhipuai`: 智谱 AI 大模型 SDK
- `pytest`: 测试框架
- `flake8`: 代码检查工具
- `pipdeptree`: 依赖树分析工具

详细列表请参考 `requirements.txt` 和 `dependency_tree_report.txt`。
