# 第一次 GitHub PR / CI 实操

## 你要掌握的概念

- **commit**：一次可解释、可回滚的本地变更快照；
- **branch**：隔离一组开发变更，不直接污染 `main`；
- **push**：把本地分支上传到 GitHub；
- **Pull Request**：请求把功能分支合并到 `main`，也是讨论和审查入口；
- **CI**：PR 或 main 更新时，由 GitHub Actions 在干净机器重新安装并验证；
- **required check**：分支保护要求必须通过的 CI job。

## 第一次上传基线

当前本地仓库已经绑定：

```text
origin = https://github.com/lizc233/SWE_Agent_Harness.git
```

首次基线需要直接建立 `main`：

```powershell
cd D:\AAA_learn_claude_code\SWE_Agent_Harness
python scripts\check.py
git add .
git status
git commit -m "feat: establish auditable SWE agent harness"
git push -u origin main
```

执行 `git add .` 后，先确认 `.env` 没有出现在 `git status` 中。如果出现，立即停止，不要 commit。

## 你的第一个 PR 练习

基线 push 成功后：

```powershell
git switch -c docs/first-pr
```

亲手在 `docs/learning/` 新建 `CI_NOTES.md`，用自己的话写下：

1. CI 为什么必须在干净环境重跑；
2. 为什么本地测试通过仍然需要 CI；
3. 为什么 PR 应只做一个主题；
4. 这次 CI 的 5 个 job 分别验证什么。

然后：

```powershell
python scripts\check.py
git add docs/learning/CI_NOTES.md
git commit -m "docs: record CI learning notes"
git push -u origin docs/first-pr
```

打开 GitHub 仓库，点击 **Compare & pull request**，填写模板并创建 PR。观察 Actions：四个系统/Python 测试 job，加一个 wheel job。

## Review 与合并

在 PR 的 **Files changed** 检查是否只有学习笔记；在 **Checks** 查看失败日志。如果全部通过，使用 **Squash and merge**，然后本地同步：

```powershell
git switch main
git pull --ff-only
git branch -d docs/first-pr
```

## 建议的分支保护

GitHub：Settings → Branches → Add branch protection rule：

- Branch name pattern：`main`
- Require a pull request before merging
- Require status checks to pass
- 选择四个测试 job 和 `Build wheel`
- Require conversation resolution
- Do not allow force pushes

个人仓库如果“一人无法批准自己的 PR”，可以暂时不勾选 required approvals，但仍要求 PR 和 CI。

## 如何读 CI 失败

1. 看失败的是安装、测试、评测还是打包；
2. 展开第一个失败步骤，不要只看最后一行；
3. 在本地运行同一个入口：`python scripts/check.py`；
4. 修复后追加 commit 并 push，同一个 PR 会自动重新触发 CI；
5. 不要通过删除测试或降低断言来“修绿”。

