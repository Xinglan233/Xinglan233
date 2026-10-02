# 使用说明

这是一套为 `Xinglan233` 写好的 GitHub 主页实现，不是独立网站，也不是只有截图的模板。个人介绍、项目说明和链接已经填写。统计面板由仓库自己的 Actions 更新。

## 当前交付状态

已经生成 README、四个主题/尺寸的 SVG、统计脚本、测试和工作流。本地离线测试及预览结果见 `docs/VERIFICATION.md`。

本次没有修改远程仓库，也没有完成真实 GitHub API / Actions 的端到端运行。当前连接读取 `Xinglan233/Xinglan233` 返回 404；这既可能是仓库尚未创建，也可能是连接未获得访问权限，不能据此断言仓库不存在。

包内「—」表示首次同步尚未运行，不是你的实际得分为零。不要为了填满画面而手动编造 commit、语言占比或评级。

## 一、放到正确的仓库

GitHub 个人主页读取 **公开同名仓库 `Xinglan233/Xinglan233` 根目录的 `README.md`**。它不会读取普通项目里的 README 来替换个人主页。

如果还没有同名仓库：在 GitHub 创建公开仓库，名称填 `Xinglan233`。把本包文件放到仓库根目录，注意是文件夹里面的内容，不是再套一层 `Xinglan233-profile` 文件夹。`.github/workflows/profile.yml` 也必须上传；它在 macOS Finder 中可能被隐藏。

如果同名仓库已经存在：先保存旧 README 和现有工作流，在新分支应用本方案，检查差异后合并。不要删除无关文件，也不要改动头像、置顶项目或账户设置。不要将私有仓库为了装主页直接改成公开。

包里的 `README.md` 是对外主页正文；`SETUP.md` 等文件是维护文档，不会出现在主页正文里。

## 二、第一次同步

进入该仓库的 `Actions`，选择 **Update profile stats**，点击 **Run workflow**，选择默认分支并运行。

若上传主分支已自动触发成功，则不必重复运行。工作流先运行离线测试，再请求公开统计，最后提交四个 SVG 和 README 的统计明细。

不需要新建 Personal Access Token，也不需要设置 Vercel、WakaTime 或任何第三方服务。`secrets.GITHUB_TOKEN` 是 GitHub 在每次工作流运行时自动提供的临时令牌。

如果写入步骤提示权限不足，检查仓库的 Actions 权限及组织策略。工作流已显式申请更新任务的 `contents: write`。如果默认分支被规则保护，可能需要走 PR 流程；不要直接关闭分支保护来掩盖问题。权限限制下旧数据仍保留。

## 三、检查主页

打开个人主页，确认介绍、「同野·游」项目链接和统计面板显示正常。页面下方原生 Popular/Pinned repositories 和贡献日历不由本仓库生成，不会因为替换 README 被删除。

项目区不必另装插件。可手动将承载「同野·游」的 `coukong` 仓库置顶；GitHub 原生最多支持六个置顶项目，但这里保持只展示这一个即可。

浅/深色图片根据浏览器报告的 `prefers-color-scheme` 选择，窄屏阈值为 650px。GitHub 的账户主题若强制设成与系统不同，图片选图可能不跟随；这是 README 媒体查询的边界，不是能靠自定义 CSS 控制的完整网站。

## 定期更新

默认每天 UTC 02:17，即北京时间 10:17 尝试运行，也支持手动运行。GitHub 的定时任务可能延迟，不应把它视为精确定时服务。公开仓库长期无活动时，定时任务可能被自动禁用；届时在 Actions 重新启用。

生成器会显示数据日期。接口失败时工作流报错，保留上次发布的内容，不会把数据清空成 0。GitHub 的图片缓存也可能使刚更新的图片暂时仍显示旧版本。

机器人使用 `github-actions[bot]` 身份提交更新，不伪装成你的个人提交来刷贡献图。

## 统计含义

- Commits、Reviews：从当年 1 月 1 日 UTC 到获取时刻的贡献统计。它不是逐个扫描所有 Git 仓库对象得到的“终身 commit 总量”。
- Pull requests、Issues：作者为本人、公开可见的累计数量。
- Stars received：本人公开、非 fork 仓库获得的 Star 总和，保留归档仓库，排除同名主页仓库。
- Languages：本人公开、非 fork、未归档仓库中 GitHub 识别的语言字节数占比，排除同名主页仓库。最多展示五种语言，其余并为 Other。百分比合计 100.0%；这不是熟练度或编码时间。
- GRS rank：采用 GitHub Readme Stats 的默认活动评级公式，输入是上述计数及 Followers。不是 GitHub 官方评分，也不是实测的全球排名。由于筛选口径明确排除了主页仓库等内容，数值不保证和所有第三方卡片相同。
- 自动令牌默认用于公开统计；不要随意替换成权限更广的个人令牌。更广权限可能改变提交/评审等数据的可见范围。
- 绿色原生贡献日历还可能包括提交以外的活动；日历总贡献数与面板 commits 不必相等。

数据源只使用 GitHub API。语言仓库列表处理分页，不会只计算前 100 个仓库。单个仓库若出现超过 100 种语言，生成器明确报错而不是默默截断。

## 交给已授权的 agent 安装

将 `AGENT_TASK.md` 的内容连同本包交给已经能操作同名仓库的 agent。`AGENTS.md` 会约束后续维护，不让它越改越花。

## 本地验证

仅需要 Python 3.10 或更高版本，运行代码只依赖标准库。

```bash
python3 -m unittest discover -s tests -v
```

离线生成空状态（会重置四张图和统计明细，所以仅在临时副本中使用）：

```bash
python3 scripts/update_profile.py --init
```

不要把 `.env`、个人访问令牌、仓库 API 原始响应或私有信息提交到公开主页仓库。

## 官方依据

- Profile README：https://docs.github.com/en/account-and-profile/how-tos/profile-customization/managing-your-profile-readme
- Pinning：https://docs.github.com/en/account-and-profile/how-tos/profile-customization/pinning-items-to-your-profile
- Picture：https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github
- Workflow events：https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- GITHUB_TOKEN：https://docs.github.com/en/actions/concepts/security/github_token
- GraphQL users：https://docs.github.com/en/graphql/reference/users
- GRS：https://github.com/anuraghazra/github-readme-stats
