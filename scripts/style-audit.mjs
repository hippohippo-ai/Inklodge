#!/usr/bin/env node
// 文风审计探针运行器（2026-09-30）
//
// 探针本体在 books/<书名>/state/style-audit.py（卷界与词表是书内数据）。
// 本运行器只找书、挑 python、原样透传参数。
//
// 用法：
//   npm run scan:style                 # 全书：按卷指纹 + 离群章 + 逐处定位，并写 state/style-audit.md / .csv
//   npm run scan:style -- --vol 9      # 单卷
//   npm run scan:style -- --ch 130 242 # 单章
//   npm run scan:style -- --no-write   # 只上屏，不盖写报告
//   npm run scan:style -- --json       # 机读
//
// 纪律：探针**不进 verify、不判失败、不进钩子**——它只出候选，判定权在人。
import { spawnSync } from 'node:child_process'
import { existsSync, readdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const PROBE = 'state/style-audit.py'

function booksWithProbe(only) {
  const dir = join(ROOT, 'books')
  if (!existsSync(dir)) return []
  return readdirSync(dir, { withFileTypes: true })
    .filter((d) => d.isDirectory() && (!only || d.name === only))
    .map((d) => ({ name: d.name, py: join(dir, d.name, PROBE) }))
    .filter((b) => existsSync(b.py))
}

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
  const r = spawnSync(py, [PROBE, ...args], {
    cwd: join(ROOT, 'books', b.name),
    stdio: 'inherit',
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
  })
  if (r.status !== 0) failed = r.status ?? 1
}
process.exit(failed)
