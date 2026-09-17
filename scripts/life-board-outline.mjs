#!/usr/bin/env node
// 开卷必读·在世窗口压力段（数据源：state/life-windows.json，与 F35 / life-window-board.mjs 同源）
//
// 功能：把逐卷压力表（⚠卒年在卷内 / △卒年紧贴卷端 / □planned 待落 / ◇零落点）写进每卷卷纲
// 头部的『开卷必读』段。**由脚本生成并自动维护**：
//   · 段落整体包在 `<!-- LIFE-BOARD:BEGIN … LIFE-BOARD:END -->` 标记里，重跑即整段替换；
//   · 标记外的卷纲内容一个字节都不动；
//   · 已写卷生成的段落标「已写卷·存档」，未写卷标「开写前核对」，内容侧重不同；
//   · 明细入口指向 `npm run life:board -- --vol N`，避免把整张明细表灌进卷纲。
//
// 用法：
//   node scripts/life-board-outline.mjs                       # 全部卷纲
//   node scripts/life-board-outline.mjs --vol 13              # 只写卷十三
//   npm run life:board:outline
//
// 判据与 F35 / 看板完全一致（ceil = min(卒年, 书末年)；L0 载体不受卒年上限约束）。

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
const OPT = {
  book: flag('book', '天阙'),
  vol: flag('vol') != null ? Number(flag('vol')) : null,
  slack: Number(flag('slack', 1)),
}

const file = path.join(BOOKS_DIR, OPT.book, 'state', 'life-windows.json')
if (!fs.existsSync(file)) { console.error(`找不到 ${file}`); process.exit(1) }
const data = JSON.parse(fs.readFileSync(file, 'utf8'))
const endYear = Number(data.book_end_year ?? 779)

const stateDir = path.join(BOOKS_DIR, OPT.book, 'state')
const novelDir = path.join(BOOKS_DIR, OPT.book, 'novel')
const written = new Set(
  fs.existsSync(novelDir)
    ? fs.readdirSync(novelDir).map((f) => Number(/^chapter-(\d+)\.md$/.exec(f)?.[1])).filter((n) => !Number.isNaN(n))
    : [],
)

const people = (data.people || []).map((p) => ({
  ...p,
  ceil: p.death_year != null ? Math.min(Number(p.death_year), endYear) : endYear,
}))

const volOf = (data.volume_years || []).map((v) => {
  const m = /^(\d+)\s*[-—–]\s*(\d+)$/.exec(String(v.chapters || '').trim())
  const first = m ? Number(m[1]) : null
  const last = m ? Number(m[2]) : null
  const missing = first != null ? [...Array(last - first + 1).keys()].map((i) => first + i).filter((n) => !written.has(n)) : []
  return {
    vol: Number(v.vol), from: Number(v.from), to: Number(v.to ?? v.from),
    first, last, missing,
  }
})

function bucketFor(p, v) {
  const lastChance = p.ceil >= v.from && p.ceil <= v.to
  const nearEnd = !lastChance && p.ceil >= v.from && p.ceil <= v.to + OPT.slack
  const inCh = (n) => v.first != null && n >= v.first && n <= v.last
  const pendingHere = (p.planned || []).filter((x) => x.chapter != null && inCh(Number(x.chapter)))
  const nodePending = !(p.landed || []).length && (p.planned || []).length > 0
  return { lastChance, nearEnd, pendingHere, nodePending }
}

const BEGIN = '<!-- LIFE-BOARD:BEGIN（本段由 scripts/life-board-outline.mjs 自动生成并维护；手工改动会被下次运行覆盖。明细：npm run life:board -- --vol N）'
const END = 'LIFE-BOARD:END -->'

function buildSegment(v) {
  const rows = people.map((p) => ({ p, ...bucketFor(p, v) }))
  const dead = rows.filter((r) => r.lastChance)
  const near = rows.filter((r) => r.nearEnd)
  const pend = rows.filter((r) => r.pendingHere.length)
  const zero = rows.filter((r) => r.nodePending)
  const isWritten = v.first != null && v.missing.length === 0
  const partial = v.first != null && !isWritten && v.missing.length < v.last - v.first + 1
  const status = isWritten ? '已写卷·存档' : partial ? `部分已写（缺 ${v.missing.length} 章：ch${v.missing[0]}${v.missing.length > 1 ? `—${v.missing[v.missing.length - 1]}` : ''}）` : '未写·开写前核对'
  const lines = []
  lines.push(`${BEGIN} v${v.vol} ${status}`)
  lines.push('')
  lines.push(`> ### 开卷必读·在世窗口压力（卷${v.vol}，ch${v.first ?? '?'}—${v.last ?? '?'}，${v.from}—${v.to} 年；${status}）`)
  lines.push('>')
  lines.push(`> 判据与 F35 同源：ceil = min(卒年, ${endYear})；L0 载体（文书／口述）死后可续现。**动笔前先看四行，明细 \`npm run life:board -- --vol ${v.vol}\`。**`)
  lines.push('>')
  lines.push(`> ⚠ **卒年落在本卷内（${dead.length}）——本卷是最后窗口：** ${dead.length ? dead.map((r) => `${r.p.name}（${r.p.death_year == null ? `无卒，末年 ${endYear}` : `卒 ${r.p.ceil}`}）`).join('、') : '无'}　→ 这些人的退场／终局只能落在本卷或之前，开写时逐个安排。`)
  lines.push(`> △ 卒年紧贴本卷（±${OPT.slack} 年，${near.length}）：${near.length ? near.map((r) => `${r.p.name}（${r.p.ceil}）`).join('、') : '无'}　→ 只登记，不强制本卷交代；但卷十四前的收束计划里必须有他们。`)
  lines.push(`> □ planned 待落（${pend.reduce((s, r) => s + r.pendingHere.length, 0)}）：${pend.length ? pend.flatMap((r) => r.pendingHere.map((x) => `${r.p.name} ch${x.chapter}`)).join('、') : '无'}　→ 台账已排的章号，开写别漏（落位见各章补注与 §9.8a 类登记）。`)
  lines.push(`> ◇ 零落点（${zero.length}）：${zero.length ? zero.map((r) => `${r.p.name}`).join('、') : '无'}　→ 档案有节点、正文无任何落点的人。`)
  lines.push('')
  lines.push(END)
  return lines.join('\r\n')
}

// —— 写入 ——
const targets = OPT.vol != null ? volOf.filter((v) => v.vol === OPT.vol) : volOf
if (!targets.length) { console.error(`volume_years 里没有卷${OPT.vol}`); process.exit(1) }
let changed = 0
for (const v of targets) {
  if (v.first == null) continue
  const f = path.join(stateDir, `outline-vol${v.vol}.md`)
  if (!fs.existsSync(f)) { console.log(`· 卷${v.vol}：无 outline-vol${v.vol}.md，跳过`); continue }
  const raw = fs.readFileSync(f, 'utf8')
  // 按原文的多数行尾约定选择 eol（防止 LF 文件被插入 CRLF 段造成混合行尾）
  const crlfN = (raw.match(/\r\n/g) || []).length
  const eol = crlfN * 2 >= (raw.match(/\n/g) || []).length ? '\r\n' : '\n'
  const seg = buildSegment(v).replace(/\r\n/g, eol)
  const re = new RegExp(`${BEGIN.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[\\s\\S]*?${END.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`)
  let out
  if (re.test(raw)) {
    out = raw.replace(re, seg)
  } else {
    // 插在标题行（首个 # 开头行）之后的空行处；无标题则置顶
    const m = /^#.*$/m.exec(raw)
    if (m) {
      const at = m.index + m[0].length
      out = raw.slice(0, at) + eol + eol + seg + raw.slice(at)
    } else {
      out = seg + eol + eol + raw
    }
  }
  if (out !== raw) { fs.writeFileSync(f, out, 'utf8'); changed += 1; console.log(`✓ 卷${v.vol} 开卷必读已写入（${path.basename(f)}）`) }
  else console.log(`· 卷${v.vol} 无变化`)
}
console.log(`\n完成：${changed} 个卷纲更新（书末年 ${endYear}，临近阈值 ±${OPT.slack}）。重跑 \`npm run life:board:outline\` 即整段刷新。`)
