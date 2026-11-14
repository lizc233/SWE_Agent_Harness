# SWE Agent Harness

[![CI](https://github.com/lizc233/SWE_Agent_Harness/actions/workflows/ci.yml/badge.svg)](https://github.com/lizc233/SWE_Agent_Harness/actions/workflows/ci.yml)

一个面向真实代码仓库的、可审计且逐步增强的 Python SWE Agent Harness。

项目目标不是复刻某个聊天界面，而是构建模型执行软件工程任务所需的运行环境：工具、观察、权限、执行预算、轨迹和评测。

> 当前版本已经形成可运行的修复闭环：发现、搜索、读取、精确编辑、运行测试、查看 Git diff，并以权限、预算和 JSONL 轨迹约束全过程。

## 当前能力

- OpenAI-compatible Chat Completions 模型适配层；
- 与模型供应商解耦的 Agent Loop；
- 结构化工具调用与 `tool_call_id` 结果关联；
- 工具注册、白名单分发和错误隔离；
- 限制在工作区内、带行号和读取上限的 `read_file`；
- 稳定排序的递归 `list_files` 和受输出预算约束的 `search_text`；
- 通过精确匹配、期望次数和原子替换保护的 `edit_file`；
- `shell=False` 的受控命令执行，以及固定只读 `git_status` / `git_diff`；
- `allow / deny / ask` 权限决策与三种运行模式；
- 步骤、工具调用、墙上时间和上下文硬预算；
- 保持 tool-call/result 配对的工具输出压缩；
- token 汇总和不记录原始参数的 JSONL 轨迹；
- 完全离线、可重复的 Fake Model 单元测试；
- 临时 Git 仓库中的端到端修复评测；
- GitHub Actions 多 Python 版本 CI。

## 架构

```text
User Task
    ↓
AgentLoop ←────────────── Tool Result
    ↓                          ↑
ModelClient → ToolCall → ToolRegistry → Workspace Tool
    │
    └─ no tool call → Final Answer
```

详细边界和模块职责见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

## 安装

```powershell
git clone <your-repository-url>
cd SWE_Agent_Harness
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

配置兼容接口：

```powershell
$env:OPENAI_COMPATIBLE_API_KEY="your-key"
$env:OPENAI_COMPATIBLE_BASE_URL="https://api.deepseek.com"
$env:MODEL_ID="deepseek-chat"
```

或者复制 `.env.example` 为不会上传 Git 的 `.env`，然后显式加载：

```powershell
Copy-Item .env.example .env
swe-agent --env-file .env --workspace . "分析并修复失败测试"
```

也可以复制 `swe-agent.toml.example` 为 `swe-agent.toml`，通过 `--config swe-agent.toml` 固化模型、预算和权限模式。

运行 Agent（默认逐次审批写入和命令）：

```powershell
swe-agent --workspace .\examples\demo_repo "修复 total 为 0 时的失败并运行测试"
```

权限模式：

```powershell
# 只观察，拒绝写入和命令
swe-agent --approval-mode read-only --workspace . "分析项目"

# 写入和命令逐次询问（默认）
swe-agent --approval-mode ask --workspace . "修复失败测试"

# 自动允许精确文件编辑，命令仍询问
swe-agent --approval-mode auto-edit --workspace . "修复失败测试"
```

## 验证

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
python -m compileall -q src tests
python scripts\evaluate_offline.py
python scripts\run_evaluation.py --output .swe-agent\reports\latest.json
# 与 GitHub Actions 使用相同入口
python scripts\check.py
```

测试与离线评测不访问真实模型 API，不消耗 token。当前基线为 51 个测试通过；版本化 `offline-repair-v1` 套件会输出可归档 JSON 报告。

## 工程路线

1. 可审计的最小工具循环；
2. 文件发现、搜索和原子编辑；
3. 分级权限、审批与受控 Shell；
4. Git diff、测试执行和自动修复闭环；
5. 上下文预算、成本、轨迹和恢复；
6. Skills、MCP、任务分解与可选子 Agent；
7. 基于真实缺陷集的质量、安全和成本评测。

详细准入标准见 [`docs/ROADMAP.md`](docs/ROADMAP.md)，明确不做的内容见 [`docs/PRODUCT_SCOPE.md`](docs/PRODUCT_SCOPE.md)。

## 安全状态

当前版本不是操作系统级沙箱。命令即使从 workspace 启动，仍拥有当前系统用户的权限；因此命令在所有模式下都需要审批。完整边界见 [`SECURITY.md`](SECURITY.md)。

## 开发与学习

核心代码按生产仓库标准组织；个人学习记录单独放在 `docs/learning/`，不会作为产品运行时依赖。架构决策保存在 [`docs/DECISIONS.md`](docs/DECISIONS.md)。

项目工程案例、量化证据和面试边界见 [`docs/PORTFOLIO.md`](docs/PORTFOLIO.md)。

第一次参与 PR/CI 请阅读 [`docs/GITHUB_WORKFLOW.md`](docs/GITHUB_WORKFLOW.md)。

按主链路、安全边界和工程闭环阅读代码，请使用 [`docs/LEARNING_PATH.md`](docs/LEARNING_PATH.md)。

## License

MIT

