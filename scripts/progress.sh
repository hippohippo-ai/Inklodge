#!/usr/bin/env bash
# 查看小说项目进度。用法: bash scripts/progress.sh "书名"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TITLE="${1:-}"
if [ -z "$TITLE" ]; then
  echo '用法: bash scripts/progress.sh "书名"'
  echo '可用项目:'
  find "$ROOT/books" -mindepth 1 -maxdepth 1 -type d -printf '  %f\n' 2>/dev/null || true
  exit 1
fi
PROJECT="$ROOT/books/$TITLE"
if [ ! -d "$PROJECT" ]; then
  echo ">>> 未找到项目: books/$TITLE" >&2
  exit 1
fi

echo "===== 项目 ====="
echo "books/$TITLE"
echo "===== 主题 ====="
cat "$PROJECT/state/theme.txt"
echo
echo "===== 进度 ====="
cat "$PROJECT/state/progress.md"
echo
echo "===== 已写章节 ====="
find "$PROJECT/novel" -maxdepth 1 -type f -name '*.md' -print | sort || echo '（暂无）'
echo
echo "===== 最近章节总结 ====="
tail -n 40 "$PROJECT/state/chapter-log.md" 2>/dev/null || echo '（暂无）'
