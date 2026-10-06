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

### 收尾自检

每卷（或改完一批章节）收尾时跑一次三向一致性终检——源 `books/<书名>/` ↔ 镜像 `public/novels/<书名>/` ↔ 台账（卷纲声明与字数口径）：

```bash
npm run check                                    # 全部书目：章节 md5、state 镜像、index.json 覆盖、卷纲章题声明、字数台账、F23 跨章持有链
npm run check -- --book 天阙 --vol 12            # 只查某书某卷（章范围取自 state/outline-volN.md 的章题声明）
npm run check -- --book 天阙 --vol 12 --strict   # 卷收尾：单章低于 4000 字也判失败
npm run verify                                   # 再顺带跑各书 state/dedup-check.py
```

> 卷纲先声明、正文未开写的章按**警告**处理（outline-vol12 等预登记是合法状态）；已写正文的章题不符才是失败。`--predecl` 可把「声明未开写」升为失败。

镜像（`public/novels/`）由 `npm run build` 的 prebuild（`node scripts/sync.mjs`）生成，**不要手改镜像文件**；正文唯一可编辑源是 `books/<书名>/novel/` 与 `books/<书名>/state/`。

### 文笔探针（只出清单，判在人在）

逐章精校用的家族探针本体在**每本书自己的** `state/summary-camera-scan.py`（卷界、寄存器、已裁台账都是书内数据），跑法：

```bash
npm run scan                 # 家族按卷汇总（A 枚举清单／B 段尾判语／C 长段无落点／D 解释腔）
npm run scan -- --vol 13     # 单卷明细
npm run scan:d               # 家族 D（解释腔）报告：按卷待裁可清单，并写回 state/d-family-report.md
npm run scan:d -- --no-write # 只上屏，不盖写报告
npm run scan:old             # 家族 G（旧稿形态·F24a 盲区补位）报告：state/oldform-report.md
npm run scan:e               # 家族 E（人称／归属／在场）报告：state/e-family-report.md
npm run check:e              # E1 人称 + 性别口径 收紧态回归门禁（CI / 收尾）
npm run probes               # 全探针总控：一命令跑完 F/F24a/E1/S/D/G/E，汇总表 + 失败退出码
npm run lint:state           # 各书 state/*.md 结构校验（标题粘连／重复卡名／字段口径／表格列数…）
```

**全探针总控（2026-09-25）**：`npm run probes` 把各家族探针与收紧门禁串成一步，输出汇总表与失败退出码（本地与 CI 共用）。文风 R3/R4/R5 新增候选另由独立步骤 `npm run check:style-signals -- --base <before-sha> --head <after-sha>` 报告（本地预提交自动比较暂存区与 HEAD，CI push 比较 before/head）；它只打印新候选、不判失败，也不并入 `dedup-check.py`。表里**报告类**（家族 A/B/C/D、G·旧稿形态、E）只出候选、不影响退出码（默认不盖写 report，`--write` 才写）；**判失败类**（F·跨文件一致性+全书规则含 dedup、F24a 与 E1 收紧门禁）任一失败即退出码 1。`--full` 再追加 cadence／style；`--only F,E1` 只跑指定步；`--json` 机读；`--list` 列步骤。F 步（全书 dedup-check）占大头（约 3—4 分钟）。

**state 台账结构校验（2026-09-25）**：`npm run lint:state` 扫各书 `state/*.md`，报告标题粘连（一行嵌两个标题）、标题层级跳跃、重复卡名、同卡字段重复、字段半角冒号、表格列数与表头不符、中文引号不配对，以及核心字段口径不统一（建议）。**只报告、不改稿**；`--fail` 可让「结构错误」拦 CI，`--json` 机读，`--book`／`--only` 可缩小范围。

**家族 E 的能力边界（务必先读再信它的输出）**：E3（在场性断裂）可靠，已用旧 ch78 校准；**E1（人称离群）与 E2（同段双重归属）只是线索**——E1 的假阳机制已查明（本书「他想起谢沉璧写字的样子：她从不抬头…」这类句式会把在场者的代词计入），E2 的 20 处逐条读全是正常问答往来。**按 E1 改稿前必须先人读该章上下文。**

两条纪律：①**探针主体不进 verify、不判失败**——它一天里被迫补过三次寄存器，每次都让「最平的章」换人，判定权必须在人；**但已裁定的真阳／口径项可就那几章加一道收紧门禁**（E1_TREATED，仿 F24a，接入预提交钩子与 CI），未入册章仍只报告（详见下节）；②家族 D 的**已裁事项登记在探针的 `D_LEDGER`**（章号＋家族＋锚点＋判定），已裁不重复受理；台账按锚点而非段号匹配，**锚点消失＝该处已消除**。报告文件是生成物，勿手改（下次复跑盖写）。

**E1 人称 + 性别口径收紧门禁（2026-09-25）**：E1 全书 60 处逐条裁定后，真阳／口径项已处置归零（真阳 17 段：ch273／279／284 谢沉璧他→她；口径 2 处：ch184 云裳＝女、ch305 守真真人＝男）。探针新增 **`E1_TREATED={章号: 存量基线}`**（棘轮只增不减）——**已入册 5 章 E1 命中 > 基线即判失败**，未入册章仍只报告；与之配对的是**性别口径门禁**：`GENDER_EXPECT` 硬断言已裁定定向，`gender-baseline.json` 快照检测性别**翻转**（新增／减少只报告）。已接进 `scripts/pre-commit`（正文章节跑 `e --gate`；改了 characters.md 跑 `e --gender`）与 CI：手动跑 `npm run check:e`（或 `python state/summary-camera-scan.py e --gate [章…]`／`e --gender`）。

**F24a 标点剥离收紧模式（2026-09-25，默认关闭）**：`dedup-check.py` 的章内重复检出**默认沿用**「12 字滑窗、跳过含标点窗口」的宽松口径（`npm run verify` 与此一致）；要收紧（补跨标点盲区）显式开——`F24A_STRIP_PUNCT=1 python state/dedup-check.py <章…>`（先剥标点再取 ≥16 字非重叠窗，`F24A_STRIP_WIDTH` 可换宽度）。收紧态判定**仿 F26 棘轮**：探针内 `F24A_TREATED={章号: 存量基线}`，已入册章超基线才判失败。**该开关不进 `npm run verify`**（verify 保持默认宽松），但**已接进预提交钩子**（treated 章回归门禁）与 **`npm run check:f24a`**（CI）——已入册章出现超基线的新重复即拦截，未入册章仍只报告、不判失败。手动跑：`npm run check:f24a`。

### F23 跨章物件持有链（台账 `state/custody-chains.json`）

同一件物证（木牌、民夫名单、簿外页、抄页、三册、出库单副联……）在**相邻几次出现的章节间**交接与分拆是否自洽，原先只能靠人工抽读；现在由一致脚本机械校验：

```jsonc
// books/<书名>/state/custody-chains.json
{
  "chains": [{
    "id": "行军簿抄页",
    "steps": [                                             // 按章号升序
      { "ch": 253, "holder": "沈广农", "anchors": ["封进原来的油布套"], "handover": ["送回扬州"] },
      { "ch": 258, "holder": "顾琰",   "anchors": ["抄页也已经沿水路南返"], "handover": ["沿水路南返"] },
      { "ch": 260, "holder": "蒋默",   "anchors": ["抄页早已归蒋默"],       "handover": ["托船脚送来"] }
    ],
    "terminal": { "ch": 260, "why": "抄页归蒋默，只寄回空封皮", "forbid_after": ["抄页又回到沈广农"] }
  }]
}
```

三条规则：**F23A** 每步在所登记章内须命中 `anchors` 之一（否则“未落位”）；**F23B** 相邻两步持有者不同时，须在两步章内命中 `handover` 之一（否则“易主无交接”）；**F23C** 登记了 `terminal` 的链，终局章之后的章节不得命中 `forbid_after`（分拆/归档后又以整体出现）。登记了不存在的章号、台账非合法 JSON 均直接报错。编号互补：`dedup-check.py` 的 **F21** 管同章物件去向互斥、**F22** 管单章字数，跨章这一层为 **F23**。

改链时必须同步这份台账；只改正文不改表，F23 会直接报错。按书启用：没有该文件的书自动跳过。**《留春信》**（该书没有 `dedup-check.py`）于 2026-09-25 一并建了 `state/character-onsets.json`（31 人）与 `state/custody-chains.json`（11 条链／45 步），F23 与 F33 自此对它生效；`sync.mjs` 会把这两份 JSON 连同 `dedup-check.py` 一起镜像。

**F33 现为双向规则（2026-09-25）**：①**前置**——早于 `first_appearance` 出现姓名或别名、或早于 `first_speech` 出现台词归属即**判失败**（`first_appearance: null` ＝ 台账声明“尚未登场”，一出现即失败）；②**反向**——声明的首现章必须真查得到其人（只警告），并统计仍挤在末两卷／未定的人数。①与 `dedup-check.py` 的 **F30** 正则、排除词、口径逐字同源：有该脚本的书会得到两遍同样的判定（都过才过），**没有该脚本的书只剩这一道“不得提前出现”的闸门**——这正是给《留春信》建台账的目的（第 1—3 章不得再写“阿七”）。负向探针已验证：把阿七首现声明改成 ch5 → 报「ch4 已出现姓名／别名」；改错一条锚点 → 报「F23A ch9 未落位」。

各书的 `state/dedup-check.py` 已加入 **F22 单章字数口径**：每章打印一行 `[F22·字数]` 台账，单章低于 4000 字即拦截（新规则自 ch237 起判失败，更早的存量章仅报告；需全书拦截时用 `WORD_ENFORCE_FROM=1`）。全卷跑完另出一行合计/均值。

```bash
python books/天阙/state/dedup-check.py 237 238                    # 逐章台账 + 字数拦截
WORD_ENFORCE_FROM=1 python books/天阙/state/dedup-check.py 219     # 连存量章一起拦截
```

### 预提交钩子

```bash
npm run hooks:install     # 安装（复制 scripts/pre-commit → .git/hooks/pre-commit）
npm run hooks:uninstall   # 卸载
```

安装后每次提交会先跑两关：①三向一致性 + F23 跨章持有链（镜像过期／章题不符／索引漏列／持有链断裂即中止）；②本次提交涉及的正文章节的 `dedup-check.py`（含 F22 字数拦截）。跳过单次检查：`git commit --no-verify`。

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
scripts/             开新书、查看进度、同步书库、一致性终检的脚本
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
