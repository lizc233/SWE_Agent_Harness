# 项目进度

## 当前状态

核心 MVP 已形成：Agent 可以在权限和预算约束下完成“发现—搜索—读取—编辑—测试—查看 diff—结束”的修复闭环。

## 已完成

### Agent Runtime

- 模型无关的 Agent Loop 与 OpenAI-compatible 适配器；
- 结构化 `tool_call_id` 配对与多步工具循环；
- 步骤数、工具调用数、墙上时间和上下文字符硬预算；
- token usage 汇总；
- 工具输出压缩且不破坏 assistant/tool 消息配对。

### Workspace Tools

- `list_files`：稳定排序、相对路径、数量上限、生成目录过滤；
- `read_file`：带行号的分段 UTF-8 读取；
- `search_text`：字面量搜索、Glob、大小写、文件/输出预算；
- `edit_file`：精确次数、原子替换、并发变化检测、符号链接拒绝；
- `run_command`：参数数组、`shell=False`、cwd 边界、超时、退出码与输出上限；
- `git_status` / `git_diff`：固定只读 Git 观察。

### Governance and Observability

- `observe / write / execute / destructive` 风险分类；
- `allow / deny / ask` 三态决策；
- `read-only / ask / auto-edit` 三种运行模式；
- JSONL 轨迹记录权限、工具、耗时、输出规模和结束状态，不保存原始工具参数；
- 独立 `SECURITY.md` 明确非 OS 沙箱及进程隔离限制。

### Quality

- 51 个离线自动化测试通过，1 个 Windows 符号链接测试按环境跳过；
- 语法检查通过；
- 独立离线评测通过：6 步、5 次工具调用，真实完成编辑、测试和 Git diff；
- GitHub Actions 覆盖 Python 3.11 / 3.12；
- Python wheel 构建验证通过（0.1.0，约 20 KB，不含依赖）；
- TOML 运行配置已覆盖模型、预算、轨迹和权限模式，并拒绝未知配置项；
- 版本化 `offline-repair-v1` 评测套件支持 JSON 报告输出；
- GitHub PR 模板、CODEOWNERS、Issue 模板、Dependabot 和跨平台 CI 已配置；
- 将 500+ 行工具模块拆分为 `tooling / workspace / execution / tools` 四层，并修正非零退出在轨迹中的成功判定；
- 项目已初始化独立 `main` 分支 Git 仓库并绑定 GitHub 远程仓库，尚未建立首次基线提交。

## 学习验收

- Milestone 1：已通过 Agent Loop、tool call/result 和终止语义；
- Milestone 2：学习者实现 `list_files` 核心遍历，理解 Registry、Schema 和稳定输出；
- `search_text`、`edit_file`、权限、命令、Git、预算与轨迹均有对应 `docs/learning/` 讲义；
- 后续需要进行一次架构口述和真实模型运行复盘，才能形成最终简历描述。

## 当前限制

- 尚未使用真实模型 API 完成联网修复评测；
- 命令执行不是 OS 沙箱，获批进程可以访问当前系统用户可访问的资源；
- Windows 下超时会终止直接进程，但不保证清理所有后代进程；
- 搜索不支持正则、`.gitignore` 语义、AST 或 LSP；
- 上下文只压缩工具输出，尚未生成历史摘要或恢复中断会话；
- Skills、MCP、后台任务和子 Agent 尚未实现；
- 离线 Scripted Model 评测验证的是 Harness，不代表真实模型成功率。

## 下一步

1. 配置真实 API，在专用演示仓库运行一次 `ask` 模式修复并复盘轨迹；
2. 将评测套件扩展到 5–10 个版本化缺陷任务，测量真实模型成功率、步骤、token 和失败原因；
3. 根据评测瓶颈决定是否加入摘要、Skills、MCP 或任务分解，而不是为功能数量盲目堆叠。

