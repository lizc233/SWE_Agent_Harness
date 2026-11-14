# Milestone 2 · Exercise 1：实现 `list_files`

## 为什么先做这个工具

`read_file` 要求模型提前知道文件路径，但真实 SWE Agent 面对陌生仓库时首先需要观察目录结构。`list_files` 负责“发现”，`read_file` 负责“读取”，两者职责不同。

## 你的任务

在 `src/swe_agent/tools.py` 的 `build_workspace_registry()` 中新增并注册 `list_files`。

建议接口：

```text
list_files(path=".", max_entries=200) -> str
```

第一版只需要满足：

1. `path` 必须相对当前 workspace；
2. 路径逃出 workspace 时返回受控错误；
3. 路径不存在或不是目录时返回受控错误；
4. 递归列出该目录下的文件，不列目录本身；
5. 输出使用相对 workspace 的 `/` 分隔路径，并按字母排序；
6. 最多返回 `max_entries` 条；
7. `max_entries` 必须在 1 到 1000 之间；
8. 不修改 `AgentLoop`。

## 可以使用的标准库

- `Path.resolve()`
- `Path.is_relative_to()`
- `Path.is_dir()`
- `Path.rglob("*")`
- `Path.relative_to()`
- `Path.as_posix()`

## 注册 Schema 提示

工具名为 `list_files`，参数包含：

- `path`: string，可选；
- `max_entries`: integer，可选，minimum 为 1，maximum 为 1000；
- `additionalProperties`: false。

## 完成后先自查

在聊天中告诉 AI 助手“我写完了”，并说明：

1. 为什么结果要排序？
2. 为什么输出相对路径而不是绝对路径？
3. 你把默认值放在 Schema、Python 函数，还是两者都放了？为什么？

不要复制学习仓库的现成实现。可以查看当前 `read_file` 的结构，但请亲手完成 `list_files`，不确定的地方可以随时问。

## Exercise 1 验收记录

状态：2026-11-13 已完成。

- 学习者独立完成递归遍历、工作区边界、目录校验、排序、相对路径和数量截断；
- 首次注册时混淆了 Python 参数与 JSON Schema，并把两个工具写进同一个 `Tool(...)`；
- 经 Code Review 后，由 AI 助手按学习者请求完成结构修复和正式边界测试；
- 12 个离线测试全部通过，`read_file` 与 `list_files` 均已注册。

需要记住：

1. 排序保证同一仓库得到稳定输出，使测试、缓存、轨迹对比和模型上下文更可重复；
2. 相对路径更短、可移植，不暴露本机目录，并明确以 workspace 为边界；
3. Python 函数默认值负责运行时行为，Python 不会凭 Schema 自动注入默认值；
4. Schema 的 `default` 只是可选提示，供应商未必应用，因此运行时不能依赖它；
5. 一个 `Tool(...)` 描述一个工具，每个工具需要独立注册。

