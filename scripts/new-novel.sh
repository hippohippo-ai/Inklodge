#!/usr/bin/env bash
# 开新书 / 换主题：备份旧作品，写入新主题，重置状态。
# 用法: bash scripts/new-novel.sh "你的主题"
set -euo pipefail

THEME="${1:-}"

if [ -z "$THEME" ]; then
  echo "用法: bash scripts/new-novel.sh \"你的主题\""
  echo "示例: bash scripts/new-novel.sh \"都市悬疑·失忆法医追查连环案\""
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# 1. 备份旧作品（如果有）
if ls novel/*.md >/dev/null 2>&1; then
  BACKUP="backup/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$BACKUP"
  cp -r novel "$BACKUP/novel"
  cp -r state "$BACKUP/state"
  echo ">>> 已备份旧作品到 $BACKUP"
fi

# 2. 写入主题
echo "$THEME" > state/theme.txt
echo ">>> 主题已写入: $THEME"

# 3. 清空正文
rm -f novel/*.md

# 4. 重置状态文件（保留 theme.txt / revisions.md / final-check.md 之外的内容）
reset_file() {
  local f="$1"; local header="$2"
  printf '%s\n\n> 由 new-novel.sh 重置，等待对应阶段生成。\n' "$header" > "state/$f"
}

reset_file requirements.md "# 要求文件
\n> 由 new-novel.sh 重置。把用户对这本书的全部要求细化写在这里（主题/视角/规模/文笔/剧情纪律等）。\n> 主题：$THEME"
reset_file progress.md "# 进度
- 当前阶段：00
- 当前章节：0
- 总章节数：0
- 状态：初始化
- 上次更新时间：$(date +%Y-%m-%d)"
reset_file outline.md "# 大纲"
reset_file characters.md "# 人物"
reset_file artifacts.md "# 道具"
reset_file conflicts.md "# 矛盾关系"
reset_file chapters.md "# 章节规划"
reset_file foreshadowing.md "# 伏笔暗线"
reset_file timeline.md "# 时间线"
reset_file knowledge.md "# 知识矩阵"
reset_file plot-check.md "# 漏洞检查"
reset_file chapter-log.md "# 章节总结日志"
reset_file revisions.md "# 修订记录"
reset_file final-check.md "# 精校报告"

echo ">>> 状态已重置。现在可以对 Agent 说：开始写《$THEME》"
