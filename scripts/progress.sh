#!/usr/bin/env bash
# 查看当前进度。用法: bash scripts/progress.sh
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "===== 主题 ====="
cat state/theme.txt
echo
echo "===== 进度 ====="
cat state/progress.md
echo
echo "===== 已写章节 ====="
if ls novel/*.md >/dev/null 2>&1; then
  ls -1 novel/*.md | sort
else
  echo "（暂无）"
fi
echo
echo "===== 最近章节总结 ====="
tail -n 40 state/chapter-log.md 2>/dev/null || echo "（暂无）"
