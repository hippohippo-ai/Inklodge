#!/usr/bin/env node
// 全探针总控（2026-09-25）
//
// 一条命令跑完各家族探针与收紧门禁，输出汇总表与失败退出码——本地与 CI 共用。
//
// 纪律（与 books/*/state/prose-polish-plan.md 同源）：
//   · **报告类**（家族 A/B/C/D、G·旧稿形态、E）只出候选、不判失败——表里标「报告」，
//     不影响退出码（它们是探针，判定权在人）。默认 **不盖写 report 文件**，加 `--write` 才写。
//   · **判失败类**（F·跨文件一致性＋全书规则含 dedup、F24a 收紧门禁、E1 收紧门禁）
//     任一失败即退出码 1。
//   · `--full` 追加 cadence（角色节奏）与 style（文风漂移）两项判失败检查。
//
// 用法：
//   npm run probes                     # 跑默认 7 步（F/F24a/E1/S/D/G/E）
//   npm run probes -- --full           # 再追加 cadence／style
//   npm run probes -- --write          # 报告类探针盖写 report 文件（默认只上屏）
//   npm run probes -- --only F,E1      # 只跑指定步（id 逗号分隔；F 最慢，约 3—4 分钟）
//   npm run probes -- --json           # 机读输出（CI 解析用）
//   npm run probes -- --list           # 只列步骤与 id（不跑）
//   npm run probes -- -v               # 失败时也打印完整输出
//
// 耗时：F 步（全书 dedup-check）占大头（约 3—4 分钟/书），其余每步 1—2 秒。
// 环境缺 python 时，报告类步骤以 ⚠ 标出（不影响退出码），判失败类步骤如常报错。
import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const argv = process.argv.slice(2)
const has = (f) => argv.includes(f)
const write = has('--write')
const asJson = has('--json')
const verbose = has('-v') || has('--verbose')
const full = has('--full')
const onlyIdx = argv.indexOf('--only')
const only = onlyIdx >= 0 ? new Set((argv[onlyIdx + 1] || '').split(',').filter(Boolean)) : null

const node = process.execPath
const probeArgs = write ? [] : ['--no-write']

// kind: 'fail' 判失败并计入退出码 ／ 'report' 只报告、不影响退出码
const STEPS = [
  { id: 'F', kind: 'fail', label: 'F 家族·跨文件一致性＋全书规则（含 dedup：各书 dedup-check.py 全书）',
    cmd: [node, 'scripts/consistency-check.mjs', '--dedup'],
    hit: /一致性终检[^\n]*|[^\n]*存量报告 [0-9]+ 处[^\n]*/ },
  { id: 'F24a', kind: 'fail', label: 'F24a 章内重复·收紧门禁（已入册章）',
    cmd: [node, 'scripts/f24a-gate.mjs'],
    hit: /\[F24a·[^\n]*|无已入册章[^\n]*/ },
  { id: 'E1', kind: 'fail', label: 'E1 人称·收紧门禁（已入册章）',
    cmd: [node, 'scripts/e-gate.mjs'],
    hit: /ch[0-9]+: E1 [^\n]*|无已入册章[^\n]*/ },
  { id: 'S', kind: 'report', label: '家族 A/B/C/D·按卷汇总（summary-camera-scan.py）',
    cmd: [node, 'scripts/prose-scan.mjs', ...probeArgs],
    hit: /全书候选[^\n]*/ },
  { id: 'D', kind: 'report', label: '家族 D·解释腔报告（d-family-report.md）',
    cmd: [node, 'scripts/prose-scan.mjs', 'd', ...probeArgs],
    hit: /全书：待裁可[^\n]*/ },
  { id: 'G', kind: 'report', label: '家族 G·旧稿形态／oldform 报告（oldform-report.md）',
    cmd: [node, 'scripts/prose-scan.mjs', 'old', ...probeArgs],
    hit: /全书 [0-9]+ 章，命中[^\n]*/ },
  { id: 'E', kind: 'report', label: '家族 E·人称／归属／在场报告（e-family-report.md）',
    cmd: [node, 'scripts/prose-scan.mjs', 'e', ...probeArgs],
    hit: /全书 [0-9]+ 章，命中[^\n]*/ },
  { id: 'LX', kind: 'report', label: '留春信·连续性探针（引号／字面转义／章内重复／数字与日期锚点／回归锚点／审计清单）',
    cmd: [node, 'scripts/continuity-scan.mjs', ...probeArgs],
    hit: /合计：[0-9]+ 项[^\n]*/ },
]
if (full) {
  STEPS.push(
    { id: 'cadence', kind: 'fail', label: 'F·角色节奏（character-cadence --fail-on-violation）',
      cmd: [node, 'scripts/character-cadence.mjs', '--book', '天阙', '--max-gap', '100', '--tail', '100', '--fail-on-violation'],
      hit: /[^\n]*违[^\n]*|[^\n]*零出场[^\n]*/ },
    { id: 'style', kind: 'fail', label: 'F·文风漂移（style-fingerprint --diff --fail-on-drift）',
      cmd: [node, 'scripts/style-fingerprint.mjs', '--diff', '--fail-on-drift'],
      hit: /文风指纹[^\n]*/ },
  )
}

if (has('--list')) {
  console.log('可用步骤（id ｜ 类型 ｜ 名称）：')
  for (const s of STEPS) console.log(`  ${s.id.padEnd(8)} ${s.kind.padEnd(7)} ${s.label}`)
  if (!full) console.log('  （--full 还会追加 cadence／style；见下）')
  process.exit(0)
}

const steps = STEPS.filter((s) => !only || only.has(s.id))
if (!steps.length) {
  console.error(`[probes] --only 没有匹配到任何步骤：${[...(only || [])].join(',')}`)
  process.exit(2)
}

const run = (s) => {
  const r = spawnSync(s.cmd[0], s.cmd.slice(1), {
    cwd: ROOT, encoding: 'utf8',
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
    maxBuffer: 64 * 1024 * 1024,
  })
  const out = `${r.stdout || ''}${r.stderr || ''}`
  const status = r.error ? -1 : (r.status ?? 1)
  const ok = status === 0
  const hits = out.split('\n').filter((l) => s.hit.test(l))
  // 失败时优先挑带 ✗／× 的那行（正则首行可能是不出问题的那章）
  const pick = ok ? hits[0] : (hits.find((l) => /(✗|失败|未通过|未达标)/.test(l)) || hits[hits.length - 1])
  const summary = (pick || out.split('\n').find((l) => l.trim()) || '').trim().slice(0, 100)
  return { id: s.id, kind: s.kind, label: s.label, out, summary, status, ok }
}

const results = steps.map(run)
const failed = results.some((r) => r.kind === 'fail' && !r.ok) ? 1 : 0

// 中文按 2 列宽计算，让表格在等宽终端里对齐
const dw = (s) => [...s].reduce((n, ch) => n
  + (/[\u1100-\u115F\u2E80-\uA4CF\uAC00-\uD7A3\uF900-\uFAFF\uFE30-\uFE6F\uFF00-\uFF60\uFFE0-\uFFE6]/.test(ch) ? 2 : 1), 0)
const pad = (s, n) => s + ' '.repeat(Math.max(0, n - dw(s)))

if (asJson) {
  console.log(JSON.stringify({
    failed: !!failed,
    steps: results.map((r) => ({ id: r.id, kind: r.kind, label: r.label,
      status: r.status, ok: r.ok, summary: r.summary })),
  }, null, 2))
} else {
  const w = Math.max(...results.map((r) => dw(r.id)))
  const lw = Math.max(...results.map((r) => dw(r.label)))
  const line = '-'.repeat(w + lw + 30)
  console.log('\n全探针总控（probes）')
  console.log(line)
  console.log(`${pad('ID', w)}  ${pad('结果', 4)}  ${pad('退出', 4)}  ${pad('步骤', lw)}  摘要`)
  console.log(line)
  for (const r of results) {
    const mark = r.ok ? '✓' : (r.kind === 'fail' ? '✗' : '⚠')
    console.log(`${pad(r.id, w)}  ${pad(mark, 4)}  ${pad(String(r.status), 4)}  ` +
      `${pad(r.label, lw)}  ${r.summary}`)
    if (verbose && !r.ok) {
      for (const l of r.out.split('\n').slice(-40)) console.log(`      │ ${l}`)
    }
  }
  console.log(line)
  const nFail = results.filter((r) => r.kind === 'fail').length
  const nWarn = results.filter((r) => r.kind === 'report').length
  console.log(`共 ${results.length} 步：判失败类 ${nFail} 步（✗ ${results.filter((r) => r.kind === 'fail' && !r.ok).length}）`
    + `／报告类 ${nWarn} 步（⚠ ${results.filter((r) => r.kind === 'report' && !r.ok).length}，不影响退出码）`)
  console.log('说明：报告类＝探针候选，判定权在人（默认不盖写 report；`--write` 才写）；'
    + '判失败类＝机械规则与收紧门禁。' + (full ? '' : '（`--full` 另跑 cadence／style）'))
  if (failed) {
    console.log('\n失败详情（判失败类）：')
    for (const r of results.filter((x) => x.kind === 'fail' && !x.ok)) {
      console.log(`\n── ${r.id} ${r.label} ──`)
      for (const l of r.out.split('\n').slice(-25)) console.log(`   ${l}`)
    }
  }
}

process.exit(failed)
