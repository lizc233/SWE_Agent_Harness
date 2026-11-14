# Engineering Portfolio Case Study

## 项目问题

普通 LLM 对话只能生成代码文本，无法可靠完成仓库级任务。SWE Agent Harness 为模型提供受约束的观察和行动接口，并解决四类工程问题：工具执行安全、长任务预算、失败可诊断性、修复结果可验证性。

## 核心链路

```text
Task
  → model chooses a tool
  → permission policy allows / denies / asks
  → workspace or command handler executes
  → bounded result returns with tool_call_id
  → model edits, tests, inspects diff, or stops
  → JSONL trace records the decision path
```

## 关键工程决策

### 模型与 Harness 解耦

`ModelClient` 协议隔离供应商，Agent Loop 只依赖标准化的文本、工具调用和 token usage。HTTP、鉴权和响应解析留在 provider 层。

### 注册不等于授权

工具池公开可用能力，权限策略单独决定每次调用。只读观察自动允许，编辑根据模式允许或询问，命令始终询问，破坏性能力默认拒绝。

### 写入必须可验证

`edit_file` 要求精确匹配预期次数，先写同目录临时文件，再 `fsync + os.replace`；替换前比较文件摘要，检测并发变化，失败时不覆盖原文件。

### 命令不经过 Shell

命令使用参数数组与 `shell=False`，限制 cwd、超时和输出。退出码被原样返回，trace 将非零退出和超时记录为失败。

### 上下文压缩不能破坏协议

只裁剪旧工具输出，不删除 assistant tool call 或 tool result，确保 `tool_call_id` 配对完整。无法安全压缩时明确停止。

## 可复现证据

- 51 个离线自动化测试通过；
- Python 3.11 / 3.12 CI；
- `offline-repair-v1` 版本化评测：1/1 通过；
- 基准案例 6 个模型步骤、5 次工具调用；
- 临时 Git 仓库中真实完成读取、编辑、测试和 diff；
- 0.1.0 wheel 构建通过，约 20 KB（不含依赖）；
- 最大运行时模块 188 行，工具系统拆分为装配、治理、工作区和进程四层。

这些数字证明 Harness 行为，不代表真实模型在 SWE-bench 或任意仓库上的成功率。

## 简历候选表述

只有在能够独立解释对应模块后再使用：

> 独立构建 Python SWE Agent Harness，基于 OpenAI-compatible Tool Calling 实现“仓库发现—代码搜索—原子编辑—测试执行—Git diff”闭环；设计 allow/deny/ask 分级权限、`shell=False` 命令执行与多维硬预算，并通过 51 项离线测试和版本化临时 Git 仓库评测验证失败语义与修复流程。

更短版本：

> 实现可审计 SWE Agent Harness，支持多步工具调用、安全编辑、测试/Git 闭环、上下文预算和 JSONL 轨迹；构建 51 项离线测试及版本化修复评测。

## 面试追问边界

必须主动说明：

- 项目构建的是 Harness，不训练基础模型；
- 当前命令审批不是操作系统沙箱；
- 离线 Scripted Model 评测验证执行链，不代表模型智能；
- 尚未形成真实模型多任务成功率，不能宣称达到 SWE-bench 水平；
- 当前上下文管理是工具输出压缩，不是完整语义摘要与恢复系统。

## 下一份有效证据

配置真实模型后，在 5–10 个固定缺陷任务上记录成功率、平均步骤、token、审批次数和失败分类。这比继续增加多 Agent 或 MCP 名词更能提升项目可信度。

