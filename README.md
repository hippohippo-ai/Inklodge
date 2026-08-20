# 说书楼 Shuoshulou · 多小说写作与阅读平台

这里是一座给长篇小说用的说书楼：楼下起稿，楼上读书；AI 负责落笔，文件负责记事，人负责定方向。

项目由两部分组成：

- **写作台**：`prompts/` 固定流程，`state/` 保存大纲、人物、伏笔、时间线和每章总结，避免写到后面忘了前文。
- **阅读台**：React + Vite 网页端，管理书库、阅读正文、查看设定和跟踪进度。
- **说书人档案**：每部书登记作者、卷首题词、卷数和创作路程；案头草稿可在网页中编辑，楼中藏书随写作台同步展示。

## 这座楼解决什么问题

长篇小说最怕两件事：写到第二十章，忘了第三章埋过的线；人物明明不知道，却替作者把答案说了出来。

说书楼把记忆交给文件保管：

1. **凡有设定，皆落成文字**：大纲、人物、矛盾、伏笔、时间线、知识矩阵和章节总结都写入 `state/`。
2. **一章一记**：每写完一章，立即总结并同步状态，下一章只按文件续写，不凭聊天记忆猜前情。
3. **人物各有耳目**：知识矩阵记录每个角色在每个阶段知道什么、不知道什么、知道一半什么，减少剧透与逻辑漏洞。

## 开一本新书

### 第一步：立题

```bash
bash scripts/new-novel.sh "你的主题"
```

例如：

```bash
bash scripts/new-novel.sh "都市悬疑·失忆法医追查连环案"
```

也可以直接编辑 `state/theme.txt`。已完成的作品放进 `books/<书名>/`，根目录继续作为当前写作台。

### 第二步：请 Agent 开讲

对 Agent 说：

```text
按 WORKFLOW.md 开始写小说，主题见 state/theme.txt
```

Agent 会依次走完：主题确认 → 大纲 → 人物 → 矛盾 → 章节 → 伏笔 → 时间线 → 知识矩阵 → 漏洞检查 → 写章节 → 章节总结 → 循环写作 → 润色 → 精校交付。

### 第三步：查看进度

```bash
bash scripts/progress.sh
```

命令会报出当前主题、所处阶段、写到哪一章以及最近的章节记录。

## 中途停笔，如何接着说

直接告诉 Agent：

```text
按 WORKFLOW.md 恢复断点继续写
```

Agent 会先读取 `state/progress.md` 与 `state/chapter-log.md`，再检查伏笔、时间线和知识矩阵，从上次停笔处接续。

## 网页阅读台

说书楼由 React + Vite 构建，可作为纯静态站点部署到 GitHub Pages。

```bash
npm install        # 安装依赖
npm run dev        # 启动本地阅读台（默认 http://localhost:5174）
npm run build      # 构建，并把当前写作台同步到 public/novels
npm run preview    # 预览构建结果
```

### 书稿从哪里来

- **楼中藏书（bundled）**：根目录 `state/` + `novel/` 的当前作品。运行构建后，自动同步到 `public/novels/<书名>/`，网页端只读展示；`state/archive.json` 会一并登记作者、题词和卷数。
- **已完稿档案**：整理到 `books/<书名>/novel/` 与 `books/<书名>/state/`；网页阅读副本仍放在 `public/novels/<书名>/`。
- **案头草稿（local）**：在网页里点击「开新书」创建，保存在浏览器 `localStorage`，可以直接编辑，也可以导入或导出 JSON。

### 部署到 GitHub Pages

1. 推送到 GitHub 仓库（例如 `shuoshulou`）。
2. 在仓库 **Settings → Pages → Source** 中选择 **GitHub Actions**。
3. 每次推送到 `main`，`.github/workflows/deploy.yml` 会自动构建并部署。
4. 访问 `https://<用户名>.github.io/shuoshulou/`。

也可以手动部署：

```bash
npm run deploy
```

手动部署需要先安装 `gh-pages`。

## 目录地图

```text
prompts/            13 个固定提示词，规定每个写作阶段怎么走
state/              所有设定与进度，长篇小说的“记忆硬盘”
  theme.txt         主题，通常只需改这一处
  archive.json       说书人档案：作者、题词和卷数
  requirements.md   用户要求的细化与全书总约束
  outline.md        总大纲
  characters.md     人物、目的、秘密与弧线
  artifacts.md      道具与场景机关
  conflicts.md      矛盾关系矩阵
  chapters.md       章节规划
  foreshadowing.md  伏笔暗线表
  timeline.md       时间线
  knowledge.md      知识矩阵，防止人物越界知情
  plot-check.md     漏洞检查
  chapter-log.md    每章总结，防止断点失忆
  progress.md       当前阶段与章节进度
  revisions.md      设定修订记录
  final-check.md    最终精校报告
novel/              当前书稿正文：chapter-01.md、chapter-02.md……
books/              已完成作品的独立写作档案
scripts/            开新书、查看进度、同步书库的脚本
WORKFLOW.md         Agent 的完整操作总纲
src/                React 网页源码
public/novels/      构建后供网页读取的书稿数据
```

## 想改设定

告诉 Agent：

```text
修改 X 设定
```

Agent 应先把改动记入 `state/revisions.md`，再同步大纲、人物、章节、伏笔、时间线和知识矩阵，并检查正文影响；不会悄悄改完就算数。

## 默认写作参数

- 每章正文通常 4000–4500 个实际 UTF-8 字符。
- 章节总数由大纲决定，当前长篇模板为 40 章。
- 视角、基调和结局方向在阶段 0 的主题确认中确定。
