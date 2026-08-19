# 话本 Huaben · 多小说写作与阅读平台

用 AI（Codebuff）写长篇小说的通用流水线 + React 网页阅读/管理端。**提示词全部固定**，换一个主题就能开一本新书；支持多本小说同时管理、写作与阅读。

- 写作：`prompts/` 固定提示词 + `state/` 落盘（防 AI 记性差）——见下方「生成器」说明。
- 阅读/管理：React 网页（书库 / 阅读器 / 写作页 / 设定页 / 进度页），可部署到 GitHub Pages。

## 它解决什么问题

AI 写长文最大的问题是**记性差**：写到第 20 章，忘了第 3 章的伏笔，人物说出不该知道的话。本系统靠三点解决：

1. **一切落盘**：大纲、人物、矛盾、伏笔、时间线、知识矩阵、每章总结全部写入 `state/` 文件。
2. **一章一总结**：每写完一章立刻同步所有状态文件，下一章只读文件，不靠对话记忆。
3. **知识矩阵**：记录每个角色在时间线上「知道 / 不知道 / 知道一半 / 错误认知」，从源头杜绝剧透和漏洞。

## 怎么用（两步）

### 第一步：定主题

```bash
bash scripts/new-novel.sh "你的主题"
```

例如：

```bash
bash scripts/new-novel.sh "都市悬疑·失忆法医追查连环案"
```

> 也可以直接改 `state/theme.txt`。已完成的作品可整理到 `books/<书名>/`，新书继续使用根目录工作区。

### 第二步：让 AI 开写

对 Agent 说一句：

```
按 WORKFLOW.md 开始写小说，主题见 state/theme.txt
```

Agent 会严格按 13 个阶段推进：主题确认 → 大纲 → 人物 → 矛盾 → 章节 → 伏笔 → 时间线 → 知识矩阵 → 漏洞检查 → 写章节 → 总结 → 循环 → 润色 → 精校。

## 随时查看进度

```bash
bash scripts/progress.sh
```

会显示：当前主题、当前阶段、写到第几章、最近总结。

## 中途打断 / 换会话怎么办

直接说：

```
按 WORKFLOW.md 恢复断点继续写
```

Agent 会读 `state/progress.md` 和 `state/chapter-log.md`，从断点接着写，不会失忆。

## 网页端（话本）

React + Vite 构建，纯静态，可部署到 GitHub Pages。

```bash
npm install        # 安装依赖
npm run dev        # 本地开发（http://localhost:5174）
npm run build      # 构建（prebuild 自动把根目录当前小说同步进 public/novels）
npm run preview    # 本地预览构建产物
```

**多小说**：书库支持任意多本小说。
- 仓库内置（bundled）：AI 生成器写在根目录 `state/` + `novel/` 的当前小说，构建时自动同步进 `public/novels/<书名>/`，网页只读展示。
- 已完成作品：整理在 `books/<书名>/novel/` 与 `books/<书名>/state/`，作为写作档案保存；网页阅读副本仍在 `public/novels/<书名>/`。
- 本地草稿（local）：网页里「新建小说」创建的，存在浏览器 localStorage，可编辑、可导出/导入 JSON。

**部署到 GitHub Pages**：
1. 推到 GitHub 仓库（如 `huaben`）。
2. 仓库 Settings → Pages → Source 选 **GitHub Actions**。
3. 每次 push 到 `main`，`.github/workflows/deploy.yml` 会自动构建部署。
4. 访问 `https://<用户名>.github.io/huaben/`。

（也可手动：`npm run deploy`，需先安装 `gh-pages`。）

## 目录结构

```
prompts/            13 个固定提示词（每个阶段一个，一般不用动）
state/              所有设定与进度（记忆的"硬盘"）
  theme.txt         主题（你唯一要改的文件）
  requirements.md   你口述要求的细化与固化（全书总约束）
  outline.md        大纲
  characters.md     人物：性格/目的/秘密/弧线
  artifacts.md      道具/法宝：金箍棒、钉耙、紧箍咒、生死簿……
  conflicts.md      矛盾关系矩阵
  chapters.md       章节规划
  foreshadowing.md  伏笔暗线表
  timeline.md       时间线
  knowledge.md      知识矩阵（防剧透核心）
  plot-check.md     漏洞检查报告
  chapter-log.md    每章总结（防记忆丢失核心）
  progress.md       当前阶段/章节
  revisions.md      设定修订记录
  final-check.md    精校报告
novel/              当前新书正文 chapter-01.md、chapter-02.md……
books/              已完成小说的独立档案（如 `books/高太公造反/`）
scripts/            new-novel.sh（开新书）、progress.sh（看进度）、sync.mjs（同步进网页）
WORKFLOW.md         Agent 的操作总纲
（网页端）
  package.json / vite.config.js / index.html
  src/              React 源码（书库/阅读器/写作/设定/进度）
  public/novels/    同步后的小说数据（网页只读加载）
  .github/workflows/deploy.yml   GitHub Pages 自动部署
```

## 想改设定？

告诉 Agent：「修改 X 设定」，Agent 会走修订记录流程（`state/revisions.md`），并全篇同步检查，不会悄悄改。

## 默认参数（可在 `state/theme.md` 阶段 0 调整）

- 每章 3000–5000 字
- 章节数由大纲规模决定（进度文件可调）
- 视角 / 基调 / 结局方向在阶段 0 确定
