# MADF 重构计划与路线图

## 1. 冗余模块与重构分析

### 1.1 冗余识别
经过代码审计，发现根目录下存在大量遗留代码，与 `app/` 目录下的现代架构严重重叠。

| 冗余文件 (Root) | 对应现代模块 (`app/`) | 重复程度 | 建议操作 |
| :--- | :--- | :--- | :--- |
| `agent.py` | `app/agent/agent.py` | 高 (90%+) | **删除**，逻辑已迁移。 |
| `god.py` | `app/agent/god.py` | 中 (60%) | **删除**，`app` 版本功能更强。 |
| `memory.py` | `app/agent/memory.py` | 高 (95%) | **删除**。 |
| `database.py` | `app/db/session.py` | 完全不同技术栈 | **删除**，根目录使用 SQLite 原生接口，`app` 使用 SQLAlchemy。 |
| `main.py` (CLI) | `app/main.py` (FastAPI) | 功能重叠 | **保留并重命名**为 `cli_runner.py` 或移至 `scripts/`，作为离线测试工具。 |

### 1.2 模块健康度评分

| 模块 | 复杂度 | 测试覆盖率 | 维护成本 | 评分 (0-10) | 备注 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Agent Core** | 高 | 低 | 中 | 6.5 | 核心逻辑复杂，缺乏单元测试，依赖 LLM 稳定性。 |
| **API Layer** | 中 | 中 | 低 | 8.0 | 标准 FastAPI 结构，清晰易维护。 |
| **Database** | 低 | 高 | 低 | 9.0 | 使用 Alembic 管理，结构清晰。 |
| **Frontend** | 中 | 低 | 中 | 7.0 | Vue 3 组件化良好，但缺乏 E2E 测试覆盖。 |
| **Legacy Scripts** | 低 | 0% | 高 | 2.0 | 根目录脚本不仅冗余，且可能误导新开发者。 |

## 2. 开发路线图 (Roadmap)

### Phase 1: 清理与标准化 (立即执行)
- [ ] **移除遗留代码**: 删除根目录下的 `agent.py`, `god.py`, `memory.py`, `database.py`。
- [ ] **统一入口**: 确保所有启动脚本都通过 `app.main` 或 `manage.py` 类型的入口进行。
- [ ] **依赖锁定**: 更新 `requirements.txt`，移除未使用的库，锁定版本。

### Phase 2: 稳定性与测试 (1-2 周)
- [ ] **后端测试**: 为 `app/agent` 添加 Mock LLM 测试，确保逻辑不依赖外部 API。
- [ ] **前端测试**: 完善 Vue 组件测试，增加 Cypress E2E 流程测试（注册 -> 创建论坛 -> 聊天）。
- [ ] **错误处理**: 增强全局异常捕获，规范化 API 错误码。

### Phase 3: 功能增强 (1 个月)
- [ ] **实时性优化**: 完善 WebSocket 连接管理，增加心跳检测和断线重连。
- 

### Phase 4: 运维与监控 (持续进行)
- [ ] **Docker 优化**: 编写多阶段构建 Dockerfile，减小镜像体积。
- [ ] **CI/CD**: 配置 GitHub Actions 自动运行测试和 Lint。
- [ ] **日志监控**: 接入 ELK 或 Prometheus + Grafana。

## 3. 技术债务清单
2. **缺乏类型提示**: 部分 Python 代码缺乏 Type Hints，影响静态分析。
3. **前端状态管理**: Pinia Store 部分逻辑过于臃肿，需拆分 Action 和 Getter。
