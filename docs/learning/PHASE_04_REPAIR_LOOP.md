# Milestone 4：修复闭环

完整闭环不是“模型输出了一段代码”，而是：

```text
list/search → read → edit → run tests → inspect failure/diff → retry or finish
```

`run_command` 返回真实退出码，非零退出不能包装成成功。`git_status` 和 `git_diff` 只能执行固定只读 Git 子命令，不允许模型自由拼接 Git 参数。

离线端到端评测使用 Scripted Model 控制动作序列，在临时 Git 仓库中真实编辑文件、执行测试并检查 diff。它验证 Harness，不声称衡量真实模型智能。

