#!/usr/bin/env node
// E1 人称 + 性别口径 收紧态回归门禁（跨平台；预提交钩子与 CI 共用）。
//
// 跑各书 state/summary-camera-scan.py：
//   · `e --gender`       性别口径门禁（每本一次，与章无关）
//                        ① GENDER_EXPECT 硬断言已裁定定向（云裳=F／守真真人=M）
//                        ② 与 gender-baseline.json 快照比对，某名字性别**翻转**即失败
//   · `e --gate [章…]`   E1 人称收紧门禁：已入册章（E1_TREATED）命中 > 存量基线 ⇒ 失败
//
// 两样都只判「已裁定的口径是否回退」；未入册章／未入表的人仍只报告
// （见 books/*/state/prose-polish-plan.md §十二／§十三）。
//
// 用法：
//   npm run check:e            # 跑各书性别口径 + 全部已入册章（CI / 收尾）
//   npm run check:e -- 273 279 # 只跑指定章（未入册章不判、只提示）
//   E_GATE_SKIP_GENDER=1 ...   # 跳过性别口径（仅调章级门禁时用）
//
// 环境缺 python 时跳过并提示，不因环境问题卡住。
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const only = process.argv.slice(2).filter((a) => a !== '--')
const skipGender = !!process.env.E_GATE_SKIP_GENDER

let py = null
for (const c of ['python3', 'python']) {
  const p = spawnSync(c, ['--version'], { stdio: 'ignore' })
  if (p.status === 0) { py = c; break }
}
if (!py) {
  console.error('[check:e] 未找到 python，跳过 E1 人称／性别口径收紧态回归门禁')
  process.exit(0)
}

const env = { ...process.env, PYTHONIOENCODING: 'utf-8' }
const booksDir = path.join(root, 'books')
let fail = 0
let ran = 0
for (const book of fs.readdirSync(booksDir)) {
  const script = path.join(booksDir, book, 'state', 'summary-camera-scan.py')
  if (!fs.existsSync(script)) continue

  // ① 性别口径门禁（与章无关）
  if (!skipGender) {
    const rg = spawnSync(py, [script, 'e', '--gender'], { stdio: 'inherit', env })
    if (rg.status !== 0) {
      fail = 1
      console.error(`[check:e] ${book}：性别口径未通过——已裁定的定向被改动或性别翻转`)
    }
  }

  // ② E1 人称章级门禁：已入册章清单由 --e-treated 枚举（未启用 E1 门禁的书返回非零，跳过）
  const listed = spawnSync(py, [script, '--e-treated'], { encoding: 'utf8', env })
  if (listed.status !== 0) continue
  const treated = (listed.stdout || '').trim().split(/\s+/).filter(Boolean)
  const nums = only.length ? only : treated
  if (!nums.length) continue
  ran++
  const r = spawnSync(py, [script, 'e', '--gate', ...nums], { stdio: 'inherit', env })
  if (r.status !== 0) {
    fail = 1
    console.error(`[check:e] ${book}：E1 收紧态未通过——已入册章出现超过存量基线的新人称离群`)
  }
}
if (!ran) console.log('[check:e] 无已入册章（或各书未启用 E1 门禁），章级门禁跳过')
process.exit(fail)
