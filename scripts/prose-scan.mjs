#!/usr/bin/env node
// 文笔探针运行器（2026-09-24）
//
// 探针本体在每本书自己的 state/summary-camera-scan.py 里（卷界、寄存器、D 台账都是
// 书内数据，不往公共脚本里搬）。本运行器只做两件事：找到哪本书有探针、用哪个 python，
// 然后把参数原样透传过去——所以探针加新模式时**不用改这里**。
//
// 用法：
//   npm run scan                       # 四家族按卷汇总（默认模式）
//   npm run scan:d                     # 家族 D 报告：按卷待裁可清单 + 写 state/d-family-report.md
//   npm run scan -- --vol 13           # 单卷明细
//   npm run scan:d -- --no-write       # 只看终端，不盖写报告
//   npm run scan -- --book 天阙 294     # 指定书／单章（多书时）
//
// 纪律（与 state/prose-polish-plan.md §八 同源）：探针**不进 verify、不判失败、不进钩子**，
// 它只出候选，判定权在人。
import { spawnSync } from 'node:child_process'
import { existsSync, readdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const PROBE = 'state/summary-camera-scan.py'

/** 找到带探针的书（books/<书名>/state/summary-camera-scan.py） */
function booksWithProbe(only) {
  const dir = join(ROOT, 'books')
  if (!existsSync(dir)) return []
  return readdirSync(dir, { withFileTypes: true })
    .filter((d) => d.isDirectory() && (!only || d.name === only))
    .map((d) => ({ name: d.name, py: join(dir, d.name, PROBE) }))
    .filter((b) => existsSync(b.py))
}

/** 挑一个能用的 python：环境变量 PYTHON 优先，其次按平台惯例 */
function pickPython() {
  const cands = [process.env.PYTHON, process.platform === 'win32' ? 'python' : 'python3',
    'python3', 'python'].filter(Boolean)
  for (const c of cands) {
    const r = spawnSync(c, ['--version'], { encoding: 'utf8' })
    if (!r.error && r.status === 0) return c
  }
  return null
}

const argv = process.argv.slice(2)
const bookIdx = argv.indexOf('--book')
const only = bookIdx >= 0 ? argv[bookIdx + 1] : null
const args = bookIdx >= 0 ? [...argv.slice(0, bookIdx), ...argv.slice(bookIdx + 2)] : argv

const books = booksWithProbe(only)
if (!books.length) {
  console.error(only ? `没有找到 ${only} 的探针（books/${only}/${PROBE}）`
    : `没有找到任何探针（books/*/${PROBE}）`)
  process.exit(1)
}
const py = pickPython()
if (!py) {
  console.error('找不到可用的 python（可设环境变量 PYTHON=/path/to/python）')
  process.exit(1)
}

let failed = 0
for (const b of books) {
  console.log(`\n════ ${b.name} ════`)
  // 探针里所有 print 都是中文，Windows 控制台默认 cp1252 会炸，统一强制 utf-8 输出
  const r = spawnSync(py, [PROBE, ...args], {
    cwd: join(ROOT, 'books', b.name),
    stdio: 'inherit',
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
  })
  if (r.status !== 0) failed = r.status ?? 1
}
console.log('\n说明：候选≠违规。探针只出清单，判定权在人（见各书 state/prose-polish-plan.md）。')
process.exit(failed)
