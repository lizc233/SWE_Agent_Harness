# 代码学习与面试准备路线

这不是要求你重写整个项目。目标是让你能沿着一次真实任务，解释关键设计、定位代码，并完成小范围修改和验证。

## 第一遍：先看懂主链路

按以下顺序阅读，每个阶段先看实现，再看对应测试：

1. `src/swe_agent/models.py`：理解 `ToolCall`、`ModelResponse` 和 token usage 是模型层与运行时之间的协议；
2. `src/swe_agent/agent.py`：跟踪“模型调用 → 装填 assistant 消息 → 执行工具 → 装填 tool result → 下一轮或结束”；
3. `tests/test_agent_loop.py`：看 Fake Model 如何精确控制每一轮响应，以及如何验证 `tool_call_id` 配对、预算和终止；
4. `src/swe_agent/tooling.py`：理解工具注册、JSON Schema、权限判断、异常隔离与统一结果；
5. `src/swe_agent/tools.py`：看各类工具如何组装成 Agent 可见的工具池。

完成标准：不看文档也能画出 Agent Loop，并解释为什么不能丢失 `tool_call_id`、为什么 Fake Model 适合单元测试。

## 第二遍：理解安全边界

1. `src/swe_agent/workspace.py`：重点读路径解析、工作区逃逸防护、符号链接处理和原子编辑；
2. `src/swe_agent/permissions.py`：理解“注册能力”与“授权执行”为什么必须分离；
3. `src/swe_agent/execution.py`：理解参数数组、`shell=False`、cwd、超时、退出码和输出限制；
4. `tests/test_tools.py`、`tests/test_permissions.py`、`tests/test_execution_tools.py`：把每个边界测试对应回风险。

完成标准：能解释读取、写入、命令和破坏性操作分别应属于什么风险等级，并主动说明当前实现不是 OS 沙箱。

## 第三遍：理解可观测性和工程闭环

1. `src/swe_agent/context.py`：理解为何只能裁剪工具输出，不能破坏 assistant/tool 协议消息；
2. `src/swe_agent/trace.py`：理解如何记录运行证据，同时避免把原始工具参数写进日志；
3. `src/swe_agent/provider.py`：理解 OpenAI-compatible 响应如何转换为内部模型；
4. `src/swe_agent/config.py`、`src/swe_agent/cli.py`：理解配置优先级、显式 `.env` 和运行时装配；
5. `scripts/run_evaluation.py`：理解版本化缺陷案例如何在临时 Git 仓库中完成编辑、测试和 diff；
6. `.github/workflows/ci.yml`：理解为什么 CI 要在多个干净环境重跑同一个本地检查入口。

完成标准：能区分单元测试、端到端评测和真实模型评测各自证明了什么，也能说明它们不能证明什么。

## 你亲手完成的两个改动

### 第一次 PR：CI 学习记录

按 `docs/GITHUB_WORKFLOW.md` 创建 `docs/learning/CI_NOTES.md`。这次 PR 的重点不是代码难度，而是完整走一遍 branch、commit、push、PR、CI、review 和 squash merge。

### 第二次 PR：增加一个离线缺陷案例

在 `evaluations/cases/` 增加一个小型失败仓库，在 `evaluations/suite.json` 注册它，并扩展 `scripts/run_evaluation.py` 的 Scripted Model。要求评测能证明 Agent 读取、修改、运行测试并检查 diff，而不是直接改最终答案。

这次 PR 会让你真正接触评测设计、可复现输入和失败证据，也是面试中比“接了一个 API”更有价值的经历。

## 面试前自测

你应能独立回答：

1. Agent Loop 在什么条件下继续、成功、失败或被预算终止？
2. 工具注册、JSON Schema、权限策略和 handler 分别负责什么？
3. 为什么编辑工具需要精确匹配、摘要校验和原子替换？
4. 为什么命令使用 `shell=False` 仍不等于安全沙箱？
5. 上下文压缩为什么必须保留 tool call/result 配对？
6. 51 个测试和离线评测证明了什么，为什么不能宣称真实模型成功率？
7. 什么证据出现后，才值得加入 MCP 或多 Agent？

如果其中任何一题只能背结论，就回到对应实现和测试，亲手改一个断言或补一个边界用例，再运行 `python scripts/check.py`。
