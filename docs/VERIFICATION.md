# 交付验证

验证日期：2026-09-30。

## 已通过

- `python3 -m unittest discover -s tests -v`：22 项测试通过。
- Python 编译检查通过。
- 工作流 YAML 已解析并检查：定时/手动触发、PR 只测试、默认分支更新、分任务最小权限、固定 checkout 提交版本。
- 四个正式 SVG 均可解析，没有 script、foreignObject 或外部字体依赖。
- 本地 Chromium 对 320、390、768、960px 四个视口，浅色/深色、初始/示例状态共 16 组渲染检查通过：无横向溢出，正确选用窄/宽版图片，项目链接存在，折叠明细可展开。
- 四个带测试数据的 SVG 完成文本边界检查；桌面浅色与手机深色已人工查看截图。
- 初始正式资产保持「Awaiting first sync」和「—」。示例数字仅存在于明确标注的预览和离线测试中。

## 未验证的环境

- 未在真实 `Xinglan233/Xinglan233` 仓库运行 GitHub Actions。
- 未用真实运行令牌完成账户 GraphQL 查询。
- 未验证 GitHub 线上 Markdown 清洗、图片缓存和账号主题的最终组合效果。本地预览使用 Markdown 渲染和近似 GitHub 样式，不等同于 GitHub 官方截图。
- 未执行远程推送、创建仓库或修改现有主页、置顶项目、头像和账户设置。

## 阅读预览

根目录 `preview.html`：交付时的真实初始状态。  
根目录 `preview-example.html`：**仅使用测试数字的排版演示**。页面顶部有明确提示，不代表实际账户数据。

这两个 HTML 是独立的离线快照，不是 GitHub 主页的运行入口，不会被工作流自动刷新；实际运行入口是 README 和 assets 下的四张 SVG。
