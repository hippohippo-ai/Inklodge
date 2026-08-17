# Freebuff 小说生成器 · 操作手册

本文件是**执行 Agent 的总纲**。所有阶段严格按此推进，禁止跳步、禁止凭对话记忆写正文。

## 一、核心原则（防「AI 记性差」）

1. **一切落盘**：所有设定、进度、总结都写入 `state/` 文件，正文写入 `novel/`。
2. **只信文件**：写任何内容前，先读取对应状态文件；**不依赖对话历史记忆**。
3. **一章一总结**：每写完一章立刻更新所有状态文件，再写下一章。
4. **断点续写**：任何时刻被打断，只需读 `state/progress.md` + `state/chapter-log.md` 即可恢复。
5. **固定提示词**：每个阶段对应 `prompts/` 下一个固定模板，换主题只改 `state/theme.txt`，流程不变。

## 二、阶段总览

| 阶段 | 提示词 | 输出文件 | 目的 |
|------|--------|----------|------|
| 前置 | 用户口述 | `state/requirements.md` | 细化并固化用户对这本书的全部要求（总约束） |
| 00 | `prompts/00-theme.md` | `state/theme.md` | 定题材、基调、视角、规模 |
| 01 | `prompts/01-outline.md` | `state/outline.md` | 立大纲（三幕/起承转合） |
| 02 | `prompts/02-characters.md` | `state/characters.md` | 列人物：性格/目的/秘密/弧线 |
| 03 | `prompts/03-conflicts.md` | `state/conflicts.md` | 列矛盾关系矩阵 |
| 04 | `prompts/04-chapters.md` | `state/chapters.md` | 列章节规划 |
| 05 | `prompts/05-foreshadowing.md` | `state/foreshadowing.md` | 列伏笔暗线 |
| 06 | `prompts/06-timeline.md` | `state/timeline.md` | 列时间线 |
| 07 | `prompts/07-knowledge.md` | `state/knowledge.md` | 人物在时间线上知道/不知道/错误认知 |
| 08 | `prompts/08-plot-check.md` | `state/plot-check.md` | 全盘漏洞检查（动笔前必过） |
| 09 | `prompts/09-write-chapter.md` | `novel/chapter-N.md` | 写一章正文 |
| 10 | `prompts/10-summary.md` | `state/chapter-log.md` 等 | 章节总结 + 状态同步 |
| 11 | `prompts/11-continue.md` | — | 循环 09→10 直到写完 |
| 12 | `prompts/12-polish.md` | `novel/*.md` | 润色与衔接 |
| 13 | `prompts/13-final-proof.md` | `state/final-check.md` | 精校交付 |

## 三、主循环（阶段 09 → 10 → 11）

```
while 当前章节 < 总章节数:
    执行 阶段09（写一章）
    执行 阶段10（总结 + 同步全部状态文件）
    当前章节 += 1
```

**禁止**：连续写多章再补总结；跳过状态同步；凭记忆写下一章。

## 四、断点恢复（换会话 / 被打断时）

1. 读取 `state/progress.md`。
2. 若「当前阶段」≤ 08：从对应阶段提示词继续。
3. 若「当前阶段」= 09/10：读取 `state/chapter-log.md` 最后一篇，确认当前章节，从阶段 09 继续。
4. 若「当前阶段」= 12/13：从对应阶段继续。
5. 恢复后**先检查**：`state/foreshadowing.md`、`state/knowledge.md`、`state/timeline.md` 是否与已写章节一致，不一致先修正再继续。

## 五、修订记录（改设定的唯一合法途径）

任何设定改动（人物、大纲、章节、伏笔）必须：

1. 在 `state/revisions.md` 追加一条：日期 / 改了什么 / 为什么 / 影响哪些章节。
2. 同步修改对应状态文件。
3. 在 `state/plot-check.md` 记录一次局部复检。
4. **禁止**在写正文时悄悄改设定。

## 六、状态文件清单

| 文件 | 内容 | 何时更新 |
|------|------|----------|
| `state/theme.txt` | 用户填的主题（唯一需要用户改的文件） | 用户 |
| `state/requirements.md` | 用户要求的细化与固化（全书总约束，高于一切） | 开书时 |
| `state/theme.md` | 题材/基调/视角/规模 | 阶段 00 |
| `state/outline.md` | 大纲 | 阶段 01 |
| `state/characters.md` | 人物 + 状态备注 | 阶段 02 / 每章后 |
| `state/conflicts.md` | 矛盾矩阵 | 阶段 03 |
| `state/chapters.md` | 章节规划 | 阶段 04 |
| `state/foreshadowing.md` | 伏笔暗线表 | 阶段 05 / 每章后 |
| `state/timeline.md` | 时间线 | 阶段 06 / 每章后 |
| `state/knowledge.md` | 知识矩阵 | 阶段 07 / 每章后 |
| `state/plot-check.md` | 漏洞检查报告 | 阶段 08 / 修订时 |
| `state/chapter-log.md` | 每章总结（防记忆丢失核心） | 每章后 |
| `state/progress.md` | 当前阶段 / 当前章节 / 总章节数 | 每阶段后 |
| `state/revisions.md` | 修订记录 | 任何设定改动时 |
| `state/final-check.md` | 精校报告 | 阶段 13 |

## 七、进度文件格式（`state/progress.md`）

```markdown
# 进度

- 当前阶段：09
- 当前章节：1
- 总章节数：20
- 状态：写作中
- 上次更新时间：YYYY-MM-DD
```

「状态」取值：初始化 / 规划中 / 写作中 / 润色中 / 已完成。
