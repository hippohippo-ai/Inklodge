#!/usr/bin/env node
// 写作前在世窗口看板（数据源：books/<书名>/state/life-windows.json，与 F35 同源）
//
// 用途：开写某一卷之前跑一次，回答一个问题——**这一卷里谁"必须"被交代**。
// F35（consistency-check.mjs）管"写完之后对不对"；本看板管"动笔之前看得见"：
//   ①卒年临近／已在窗口末端  —— 本卷结束年距卒年 ≤ N 年的人，本卷是最后的机会章；
//   ②命运节点未落        —— 档案 node 里写了卒年／事件、正文与计划都还没落的那批；
//   ③本卷待落计划        —— planned 登记在本卷章号的落点（开写时别漏）；
//   ④ L0 待落            —— status=待落 的载体型人物（血手／无影一类）。
// 全部只读，不改任何文件；--vol 不给时给出全书概览＋"最近未写卷"。
//
// 用法：
//   node scripts/life-window-board.mjs                       # 全书概览＋下一卷
//   node scripts/life-window-board.mjs --book 天阙 --vol 13  # 只看卷十三
//   npm run life:board -- --vol 13
//
// 判据口径：
//   ceil      = min(卒年, book_end_year)（与 F35 一致，卒年越界按书末年计）
//   临近      = 本卷起 ≤ ceil ≤ 本卷止 + SLACK（默认 1 年）→「本卷是最后窗口」
//   窗口末端  = ceil − 本卷起 ≤ SLACK（卒年落在卷内或紧贴卷首）
//   未落节点  = status ≠ 已落地，或 node 声明的节点年 > 已有落点最大年（简判：landed 为空）

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const BOOKS_DIR = path.join(ROOT, 'books')

const argv = process.argv.slice(2)
function flag(name, def = null) {
  const i = argv.indexOf(`--${name}`)
  return i >= 0 ? (argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : true) : def
}
const OPT = { book: flag('book', '天阙'), vol: flag('vol') != null ? Number(flag('vol')) : null, slack: Number(flag('slack', 1)) }

const file = path.join(BOOKS_DIR, OPT.book, 'state', 'life-windows.json')
if (!fs.existsSync(file)) {
  console.error(`找不到 ${file}（先按 F35 落台账）`)
  process.exit(1)
}
const data = JSON.parse(fs.readFileSync(file, 'utf8'))
const endYear = Number(data.book_end_year ?? 779)
const volOf = (data.volume_years || []).map((v) => ({
  vol: Number(v.vol), from: Number(v.from), to: Number(v.to ?? v.from),
  ch: String(v.chapters || ''), written: false,
}))
// 卷是否已写：看正文目录里该卷首章是否在（用 volume_years 的章范围首章判断）
const novelDir = path.join(BOOKS_DIR, OPT.book, 'novel')
const written = new Set(
  fs.existsSync(novelDir)
    ? fs.readdirSync(novelDir).map((f) => Number(/^chapter-(\d+)\.md$/.exec(f)?.[1])).filter((n) => !Number.isNaN(n))
    : [],
)
for (const v of volOf) {
  const m = /^(\d+)\s*[-—–]\s*(\d+)$/.exec(v.ch)
  const first = m ? Number(m[1]) : null
  const lastN = m ? Number(m[2]) : null
  v.missing = []
  if (m) {
    for (let n = Number(m[1]); n <= Number(m[2]); n++) if (!written.has(n)) v.missing.push(n)
  }
  v.written = m ? v.missing.length === 0 : false
}
const writtenChapters = [...written].sort((a, b) => a - b)
const lastWritten = writtenChapters.length ? writtenChapters[writtenChapters.length - 1] : 0

const people = (data.people || []).map((p) => ({
  ...p,
  ceil: p.death_year != null ? Math.min(Number(p.death_year), endYear) : endYear,
  floor: p.birth_year != null ? Number(p.birth_year) : null,
}))

const yearTag = (y) => (y == null ? '—' : String(y))
const kindTag = (k) => (k === 'document' ? '文书' : k === 'reported' ? '口述/遗物' : '在场')
const chLabel = (x) => (x.chapter != null ? `ch${x.chapter}` : x.vol != null ? `卷${x.vol}` : String(x.note || x.chapter || '未定'))

function bucketFor(p, v) {
  const inVolWindow = p.ceil >= v.from && p.ceil <= v.to + OPT.slack
  const lastChance = p.ceil >= v.from && p.ceil <= v.to // 卒年落在卷内
  const nearEnd = !lastChance && inVolWindow
  const pendingHere = (p.planned || []).filter((x) => x.chapter != null && volOf.find((w) => w.vol === v.vol && inCh(w, x.chapter)))
  const landedMax = (p.landed || []).reduce((m, x) => Math.max(m, Number(x.year ?? v.from)), 0)
  const nodePending = (p.landed || []).length === 0 && (p.planned || []).length > 0
  return { lastChance, nearEnd, pendingHere, nodePending, landedMax }
}
function inCh(v, n) {
  const m = /^(\d+)\s*[-—–]\s*(\d+)$/.exec(v.ch)
  return m ? n >= Number(m[1]) && n <= Number(m[2]) : false
}

function render(v, isOverview = false) {
  const rows = people.map((p) => ({ p, ...bucketFor(p, v) })).filter((r) => r.lastChance || r.nearEnd || r.pendingHere.length || r.nodePending)
  const missNote = v.missing?.length ? `；缺 ${v.missing[0]}${v.missing.length > 1 ? `—${v.missing[v.missing.length - 1]}` : ''} 共 ${v.missing.length} 章` : ''
  const out = []
  const head = `${isOverview ? '【全书概览】' : ''}卷${v.vol}（ch${v.ch}，${v.from}—${v.to} 年，${v.written ? '已写' : '未写'}${missNote}）`
  out.push(head)
  out.push('─'.repeat(Math.min(head.length + 8, 72)))
  if (!rows.length) { out.push('  · 无卒年临近、无未落节点——本卷无"必须交代"压力'); return out }
  const show = (title, list, fmt) => {
    if (!list.length) return
    out.push(`  ${title}（${list.length}）`)
    for (const r of list) out.push(`    · ${fmt(r)}`)
  }
  show('⚠ 卒年落在本卷内——本卷是最后窗口', rows.filter((r) => r.lastChance),
    (r) => `${r.p.name}（${r.p.death_year == null ? '无卒，末年 779' : `卒 ${r.p.ceil}${r.p.death_year > endYear ? `，档案卒 ${r.p.death_year} 越界按 ${endYear} 计` : ''}`}）｜节点：${r.p.node || '—'}｜已落 ${(r.p.landed || []).length} 处${(r.p.landed || []).length ? `（末 ${chLabel((r.p.landed || []).sort((a, b) => (a.chapter ?? 1e9) - (b.chapter ?? 1e9)).slice(-1)[0])}）` : ''}`)
  show('△ 窗口末端（卒年紧贴本卷）', rows.filter((r) => r.nearEnd),
    (r) => `${r.p.name}（卒 ${yearTag(r.p.ceil)}）｜${r.p.node || '—'}`)
  show('□ 本卷待落计划（planned 登记在本卷）', rows.filter((r) => r.pendingHere.length),
    (r) => `${r.p.name} → ${r.pendingHere.map((x) => `${chLabel(x)}${x.note ? `（${String(x.note).slice(0, 40)}）` : ''}`).join('、')}`)
  show('◇ 档案声明节点但零落点（landed 为空）', rows.filter((r) => r.nodePending),
    (r) => `${r.p.name}｜${r.p.node || '—'}｜计划：${(r.p.planned || []).map(chLabel).join('、') || '无'}`)
  return out
}

// ── 输出 ────────────────────────────────────────────────────────────
console.log(`在世窗口看板 · ${OPT.book}（书末年 ${endYear}；已写至 ch${lastWritten}；临近阈值 ±${OPT.slack} 年）`)
console.log(`数据源：state/life-windows.json（${people.length} 人，与 F35 同源）\n`)

if (OPT.vol != null) {
  const v = volOf.find((x) => x.vol === OPT.vol)
  if (!v) { console.error(`volume_years 里没有卷${OPT.vol}`); process.exit(1) }
  console.log(render(v, false).join('\n'))
} else {
  // 概览：逐卷压力分布表
  console.log('卷   | 年份      | 状态                      | ⚠卒年内 | △贴近 | □待落 | ◇零落')
  console.log('-'.repeat(78))
  for (const v of volOf) {
    const rows = people.map((p) => ({ p, ...bucketFor(p, v) }))
    const a = rows.filter((r) => r.lastChance).length
    const b = rows.filter((r) => r.nearEnd).length
    const c = rows.filter((r) => r.pendingHere.length).length
    const d = rows.filter((r) => r.nodePending).length
    const total = Number(v.ch.split(/[-—–]/)[1]) - Number(v.ch.split(/[-—–]/)[0]) + 1
    const st = v.missing.length === 0 ? '全部已写' : v.missing.length === total ? '未开写' : `缺 ${v.missing.length} 章（${v.missing[0]}${v.missing.length > 1 ? `—${v.missing[v.missing.length - 1]}` : ''}）`
    console.log(
      `${`卷${v.vol}`.padEnd(5, '　')} | ${`${v.from}—${v.to}`.padEnd(7, '　')} | ${String(st).padEnd(22, '　')} | ${String(a).padStart(5)}  | ${String(b).padStart(4)}  | ${String(c).padStart(4)}  | ${String(d).padStart(4)}`,
    )
  }
  // 全书级清单
  const landedEmpty = people.filter((p) => !(p.landed || []).length && (p.landed_range || (p.planned || []).length))
  const l0Pending = people.filter((p) => p.status === '待落')
  const next = volOf.find((v) => v.missing.length)
  const deadlines = next
    ? people.filter((p) => (p.landed || []).length === 0 && p.death_year != null && p.ceil <= next.from)
    : []
  console.log(`\n  ◇ 零落点（档案有节点、正文无任何落点）：${landedEmpty.length ? landedEmpty.map((p) => `${p.name}（${p.node || '—'}）`).join('；') : '无'}`)
  console.log(`  ◇ L0 待落（status=待落，只许载体出现）：${l0Pending.length ? l0Pending.map((p) => p.name).join('、') : '无'}`)
  if (deadlines.length) {
    console.log(`  ⚠ 已过卒年仍零落点（只剩 L0 载体可用）：${deadlines.map((p) => `${p.name}（卒 ${p.ceil}）`).join('、')}`)
  }
  if (next) {
    console.log(`\n【下一卷】卷${next.vol}（ch${next.ch}，${next.from}—${next.to} 年；缺 ${next.missing.length} 章）`)
    console.log(render(next, false).slice(1).join('\n'))
  }
}
console.log('\n（只读看板：不改任何文件；判据与 F35 一致——ceil = min(卒年, 书末年)，L0 载体不受卒年上限约束）')
