\## 1. 为什么 CI 要在干净环境重新运行？



CI 每次启动都是\*\*全新、无历史残留的虚拟机\*\*，跑完直接销毁，不保留任何上一次的缓存、全局包、本地配置：



\- 规避「本地遗留状态」：你本机装过很多全局依赖、旧版本包、编译缓存、环境变量；这些 “隐性依赖” 会让代码在你机器刚好能跑，换环境就炸。干净环境强制\*\*从 0 开始安装依赖、构建\*\*，保证流程可复现。

\- 标准化基线：所有开发者、所有 PR 都跑在一模一样的基础镜像（ubuntu-latest /windows-latest），评判标准统一，不会出现 “环境因人而异”。

\- 验证构建脚本本身：验证你的构建步骤、安装命令是不是写完整了；如果构建脚本缺步骤，在干净环境会直接失败，本地有缓存是发现不了的。



> 

> 一句话：CI 干净环境的目标是\*\*保证可复现性（reproducible）\*\*。



\## 2. 为什么本地测试通过仍然需要 CI？



经典的「在我机器上能跑（works on my machine）」问题：



1\. \*\*操作系统差异\*\*：你本地可能是 macOS，CI 是 Ubuntu/Windows；路径分隔符、文件大小写、系统库、权限行为不一样。

2\. \*\*Python 版本差异\*\*：你本地是 3.12，CI 还要验证 3.11；不同小版本标准库行为、编译逻辑有区别。

3\. \*\*依赖版本浮动\*\*：本地依赖已经固定缓存；CI 会重新拉取依赖，有概率出现依赖新版本引入 bug、依赖冲突。

4\. \*\*缺少隔离\*\*：本地有全局包污染；CI 是独立环境，能发现代码\*\*缺少声明依赖\*\*的问题。

5\. \*\*统一准入门禁\*\*：团队协作，每个人环境五花八门，CI 是统一的验收标准；代码合并前必须过 CI，而不是靠人本地自测。

6\. \*\*自动化，防遗忘\*\*：人很容易忘记换版本、换系统自测；提交 PR 自动触发。



\## 3. 为什么一个 PR 最好只做一个主题？



你截图这个 PR 标题：`Bump actions/upload-artifact from 4 to 7 #3`，它就只做一件事：\*\*升级 upload-artifact 这个 GitHub Action 版本\*\*，这就是典型单主题 PR。

好处：



\- \*\*容易 review\*\*：改动范围小， reviewer 一眼看懂目的，不容易漏掉风险点；如果一个 PR 同时改依赖、改业务逻辑、修复 bug，review 成本指数上升。

\- \*\*出错容易回滚 / 定位\*\*：CI 一旦变红，你立刻知道：问题就是这次升级 action 导致的；如果 PR 混了很多无关修改，你根本不知道是哪一处代码搞崩 CI。

\- \*\*历史干净、便于追溯\*\*：以后看 git 历史，这条提交记录含义清晰；混在一起的大 PR，以后查问题非常痛苦。

\- \*\*降低合并风险\*\*：小 PR 更容易通过，出问题影响面很小。



> 

> 反例：一个 PR 同时：升级 upload-artifact + 修改打包脚本 + 修复代码 bug，一旦 CI 失败，排查成本很高。



\## 4. 截图里 5 个 CI job 分别验证什么
ubuntu-latest / Python 3.11

ubuntu-latest / Python 3.12

windows-latest / Python 3.11

windows-latest / Python 3.12

Build wheel

（这里`Build wheel`是其中一个 job 的名称，矩阵一共 4 个组合，合计 5 行展示）

整体目标：\*\*验证 Python 包能不能正常打包生成 wheel 分发包\*\*



1\. \*\*ubuntu-latest / Python3.11\*\*：Linux 系统 + Python3.11，验证在 Linux 下，用 3.11 版本可以正常构建 wheel 包

2\. \*\*ubuntu-latest / Python3.12\*\*：Linux 系统 + Python3.12，验证高一点的 Python3.12 版本打包正常

3\. \*\*windows-latest / Python3.11\*\*：Windows 系统 + Python3.11，验证 Windows 环境打包（Windows 编译、路径、系统 API 坑很多）

4\. \*\*windows-latest / Python3.12\*\*：Windows 系统 + Python3.12

5\. \*\*Build wheel\*\*：是这个 job 的显示名称，job 内部步骤：

&#x20;  - checkout：拉取源码

&#x20;  - setup-python：安装指定 Python 版本

&#x20;  - 更新 pip

&#x20;  - `python -m pip wheel . --no-deps --wheel-dir dist`：\*\*构建 wheel 包，--no-deps 意思是只构建当前项目，不构建它的依赖包\*\*，产物放到 dist 目录pip

&#x20;  - upload-artifact@v7：把打好的 wheel 包上传成 CI 产物，后面可以下载、发布到 PyPI

