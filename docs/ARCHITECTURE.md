# Architecture

## 设计目标

- 模型供应商可替换；
- 工具能力显式注册；
- 模型提出动作，Harness 决定能否执行；
- 每次调用可关联、可限制、最终可追踪；
- 核心循环可使用 Fake Model 完全离线测试。

## 当前模块

### `models.py`

定义 `ModelClient` 协议、`ModelResponse` 和 `ToolCall`。这一层是模型协议与运行时之间的防腐层。

### `provider.py`

实现 OpenAI-compatible HTTP 适配器。供应商鉴权、URL 和响应解析不进入 Agent Loop。

### `agent.py`

维护消息历史并执行循环。它不读取文件、不发 HTTP 请求，也不包含具体工具策略；同时执行步骤、工具调用、时间和上下文预算。

### `tools.py`

负责组装工具 Schema 与 handler，保持公开工具池集中可读。

### `tooling.py`

维护 `Tool`、`ToolRegistry`、权限闸门、执行审计和统一错误边界。

### `workspace.py`

封装路径边界、读取、发现、搜索和原子编辑，不依赖模型协议。

### `execution.py`

封装 `shell=False` 命令执行、超时、输出预算与固定只读 Git 观察。

### `permissions.py`

定义风险类别、权限决策和运行模式。工具注册表示“存在这种能力”，策略决定“本次是否执行”。

### `context.py`

计算上下文预算并压缩旧工具输出，保留所有协议消息和 `tool_call_id` 对应关系。

### `trace.py`

追加写 JSONL 事件。记录元数据而非原始工具参数，降低代码和密钥泄漏风险。

### `cli.py`

负责参数、环境配置和依赖组装，不承载业务逻辑。

## 信任边界

```text
Untrusted: user input, model text, model tool arguments, repository content
Trusted: validated configuration, ToolRegistry, permission policy, tool handlers
```

模型生成的工具名和参数始终是不可信输入。工具被注册不代表每次调用都获准执行；权限层按风险、运行模式和用户决定给出 allow、deny 或 ask。

## 终止语义

- 模型不请求工具：正常结束；
- 达到 `max_steps`：以明确异常停止；
- 工具失败：结果作为工具消息返回，由模型决定修正或结束；
- 未知工具：不会动态查找 Python 对象，而是返回受控错误。
- 达到工具、时间或上下文预算：明确失败并保留轨迹；
- 命令退出非零：保留真实退出码，由模型决定修正或停止。

## 后续扩展点

- 历史摘要和中断恢复；
- 版本化真实缺陷评测集；
- Skills 与 MCP 按需扩展；
- 有评测收益时再加入任务分解或子 Agent；
- 可选容器/系统沙箱执行后端。

