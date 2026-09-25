#!/usr/bin/env node
// F24a 收紧态回归门禁（跨平台；预提交钩子与 CI 共用）。
//
// 置 F24A_STRIP_PUNCT=1 跑各书 state/dedup-check.py：
//   · 已入册章（探针内 F24A_TREATED）命中 > 存量基线 ⇒ 退出码 1（拦截）
//   · 未入册章只报告、不判失败（存量锁基线；见 books/*/state/prose-polish-plan.md §十一）
//
// 用法：
//   npm run check:f24a            # 跑各书全部已入册章（CI / 收尾）
//   npm run check:f24a -- 273 279 # 只跑指定章（须已入册）
//
// 环境缺 python 时跳过并提示，不因环境问题卡住。
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const only = process.argv.slice(2).filter((a) => a !== '--')

let py = null
for (const c of ['python3', 'python']) {
  const p = spawnSync(c, ['--version'], { stdio: 'ignore' })
  if (p.status === 0) { py = c; break }
}
if (!py) {
  console.error('[check:f24a] 未找到 python，跳过 F24a 收紧态回归门禁')
  process.exit(0)
}

const booksDir = path.join(root, 'books')
let fail = 0
let ran = 0
for (const book of fs.readdirSync(booksDir)) {
  const script = path.join(booksDir, book, 'state', 'dedup-check.py')
  if (!fs.existsSync(script)) continue

  // 已入册章清单由 dedup-check.py 的 --f24a-treated 模式给出（未启用 F24a 的书返回非零，跳过）
  const listed = spawnSync(py, [script, '--f24a-treated'], {
    encoding: 'utf8',
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
  })
  if (listed.status !== 0) continue
  const treated = (listed.stdout || '').trim().split(/\s+/).filter(Boolean)

  const nums = only.length ? only : treated
  if (!nums.length) continue
  ran++
  const r = spawnSync(py, [script, ...nums], {
    stdio: 'inherit',
    env: { ...process.env, F24A_STRIP_PUNCT: '1', PYTHONIOENCODING: 'utf-8' },
  })
  if (r.status !== 0) {
    fail = 1
    console.error(`[check:f24a] ${book}：F24a 收紧态未通过——已入册章出现超过存量基线的新重复`)
  }
}
if (!ran) console.log('[check:f24a] 无已入册章（或各书未启用 F24a），跳过')
process.exit(fail)
