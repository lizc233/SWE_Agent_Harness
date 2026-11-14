# Phase 1：最小 Agent Loop

## 本阶段要学会什么

最重要的不是 API，而是下面这个循环：

```text
用户任务
  ↓
模型判断下一步
  ├─ 没有工具调用 → 返回最终答案
  └─ 请求工具调用 → Harness 校验并执行
                         ↓
                    工具结果写回 messages
                         ↓
                      再问模型
```

模型负责选择动作，Harness 负责提供动作空间、执行动作并守住边界。

## 四个关键对象

### `ModelClient`

只有一个职责：接收消息和工具定义，返回文本及工具调用。Agent Loop 不应该知道 DeepSeek URL 或 HTTP 细节。

### `ToolCall`

它是模型提出的结构化动作，包括调用 ID、工具名称和参数。调用 ID 用来把工具结果对应回原请求。

### `ToolRegistry`

它同时保存给模型看的工具说明和本地真正执行工具的 handler。模型只能调用注册过的工具。

### `AgentLoop`

它反复调用模型、执行工具、追加结果，直到模型不再请求工具。`max_steps` 是防止失控循环的硬上限。

## 一次完整消息顺序

```text
system: 你是只读 SWE Agent
user: 读取 buggy_math.py 并分析
assistant: tool_call(read_file, {path: "buggy_math.py"})
tool: 文件内容和行号
assistant: 最终分析文本
```

缺少 `tool` 消息时，模型不知道工具执行结果；缺少后续模型调用时，工具结果也不会自动变成答案。

## 为什么暂时没有 Shell

Shell 会把模型的文本变成真实系统行为。只有字符串黑名单远远不够，因此必须先学习工作区边界和审批流程，再增加 Shell。

## 面试表达基础版

“第一阶段我没有使用复杂编排框架，而是实现了一个模型无关的 Agent Loop。模型返回结构化工具调用，Harness 从白名单注册表执行工具，把结果按 tool_call_id 写回消息，再由模型决定继续行动或结束。循环有最大步骤上限，单元测试使用 Fake Model，不依赖真实 API。”

这段话只有在你能解释每一句时才算通过。

