# Inklodge · 墨庐
https://hippohippo-ai.github.io/Inklodge/

古典武侠与当代叙事的沉浸式阅读空间。

这里是一座给长篇小说用的书房：案头起稿，屏前读书；AI 负责落笔，文件负责记事，人负责定方向。

项目由两部分组成：

- **写作台**：`prompts/` 固定流程，`state/` 保存大纲、人物、伏笔、时间线和每章总结，避免写到后面忘了前文。
- **阅读台**：React + Vite 网页端，管理书库、阅读正文、查看设定和跟踪进度。
- **说书人档案**：每部书登记作者、卷首题词、卷数和创作路程；案头草稿可在网页中编辑，墨庐藏书随写作台同步展示。

## 这座书房解决什么问题

长篇小说最怕两件事：写到第二十章，忘了第三章埋过的线；人物明明不知道，却替作者把答案说了出来。

墨庐把记忆交给文件保管：

1. **凡有设定，皆落成文字**：大纲、人物、矛盾、伏笔、时间线、知识矩阵和章节总结都写入 `state/`。
2. **一章一记**：每写完一章，立即总结并同步状态，下一章只按文件续写，不凭聊天记忆猜前情。
3. **人物各有耳目**：知识矩阵记录每个角色在每个阶段知道什么、不知道什么、知道一半什么，减少剧透与逻辑漏洞。

## 开一本新书

### 第一步：立题

```bash
bash scripts/new-novel.sh "书名" "你的主题"
```

例如：

```bash
bash scripts/new-novel.sh "失忆法医" "都市悬疑·失忆法医追查连环案"
```

也可以直接编辑 `books/<书名>/state/theme.txt`。每本小说从创建起就是 `books/<书名>/` 下的独立项目，根目录只保存通用流程、模板和脚本。

### 第二步：请 Agent 开讲

对 Agent 说：

```text
按 WORKFLOW.md 开始写小说，主题见 books/<书名>/state/theme.txt
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

Agent 会先读取对应项目的 `state/progress.md` 与 `state/chapter-log.md`，再检查伏笔、时间线和知识矩阵，从上次停笔处接续。

## 网页阅读台

墨庐由 React + Vite 构建，可作为纯静态站点部署到 GitHub Pages。

```bash
npm install        # 安装依赖
npm run dev        # 启动本地阅读台（默认 http://localhost:5174）
npm run build      # 构建，并把当前写作台同步到 public/novels
npm run preview    # 预览构建结果
```

### 书稿从哪里来

- **墨庐藏书（bundled）**：`books/<书名>/` 下的独立项目。运行构建后，自动同步到 `public/novels/<书名>/`，网页端只读展示；项目内 `state/archive.json` 会一并登记作者、题词和卷数。
- **已完稿档案**：仍保存在 `books/<书名>/`，与进行中的项目采用相同结构；网页阅读副本仍放在 `public/novels/<书名>/`。
- **案头草稿（local）**：在网页里点击「开新书」创建，保存在浏览器 `localStorage`，可以直接编辑，也可以导入或导出 JSON。

### 部署到 GitHub Pages

1. 推送到 GitHub 仓库（例如 `inklodge`）。
2. 在仓库 **Settings → Pages → Source** 中选择 **GitHub Actions**。
3. 每次推送到 `main`，`.github/workflows/deploy.yml` 会自动构建并部署。
4. 访问 `https://<用户名>.github.io/inklodge/`。

也可以手动部署：

```bash
npm run deploy
```

手动部署需要先安装 `gh-pages`。

## 目录地图

```text
prompts/            13 个固定提示词，规定每个写作阶段怎么走
books/              每部小说一个独立项目
  <书名>/novel/      该书正文
  <书名>/state/      该书设定、总结与进度
  <书名>/README.md   项目说明
prompts/             所有小说共享的 13 个提示词
 templates/state/    新项目使用的状态文件模板
scripts/             开新书、查看进度、同步书库的脚本
WORKFLOW.md         Agent 的完整操作总纲
src/                React 网页源码
public/novels/      构建后供网页读取的所有小说数据
```

## 想改设定

告诉 Agent：

```text
修改 books/<书名>/state/ 中的 X 设定
```

Agent 应先把改动记入 `state/revisions.md`，再同步大纲、人物、章节、伏笔、时间线和知识矩阵，并检查正文影响；不会悄悄改完就算数。

## 默认写作参数

- 每章正文通常 4000–4500 个实际 UTF-8 字符。
- 章节总数由大纲决定，当前长篇模板为 40 章。
- 视角、基调和结局方向在阶段 0 的主题确认中确定。
