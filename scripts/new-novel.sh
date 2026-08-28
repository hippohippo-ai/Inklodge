#!/usr/bin/env bash
# 创建独立小说项目。用法: bash scripts/new-novel.sh "书名" [主题]
set -euo pipefail

TITLE="${1:-}"
THEME="${2:-$TITLE}"
if [ -z "$TITLE" ]; then
  echo '用法: bash scripts/new-novel.sh "书名" [主题]'
  exit 1
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="$ROOT/books/$TITLE"
TEMPLATE="$ROOT/templates/state"
if [ -e "$PROJECT" ]; then
  echo ">>> 项目已存在: books/$TITLE" >&2
  exit 1
fi
mkdir -p "$PROJECT/novel" "$PROJECT/state"
printf '%s\n' "$THEME" > "$PROJECT/state/theme.txt"
printf '%s\n' '{"author":"咸鱼散翁","epigraph":"","volumes":1}' > "$PROJECT/state/archive.json"
for f in "$TEMPLATE"/*.md; do
  [ -e "$f" ] || continue
  cp "$f" "$PROJECT/state/$(basename "$f")"
done
cat > "$PROJECT/state/progress.md" <<EOF
# 进度｜《$TITLE》

- 当前阶段：00
- 当前章节：0
- 总章节数：0
- 状态：初始化
- 上次更新时间：$(date +%Y-%m-%d)
EOF
cat > "$PROJECT/README.md" <<EOF
# 《$TITLE》

独立小说项目。正文位于 \\`novel/\\`，设定与进度位于 \\`state/\\`；通用流程和提示词位于根目录 \\`WORKFLOW.md\\` 与 \\`prompts/\\`。
EOF
echo ">>> 已创建项目: books/$TITLE"
echo ">>> 开始编辑 books/$TITLE/state/theme.txt"
