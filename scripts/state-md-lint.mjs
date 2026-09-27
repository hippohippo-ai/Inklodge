#!/usr/bin/env node
// state/*.md 结构校验（2026-09-25）
//
// 扫每本书 state/ 下的 .md 台账，报告**结构问题**，只报告、不改稿：
//   ① 结构错误  glued-heading（标题粘连）／level-jump（层级跳跃）／dup-card（重复卡名）
//               dup-field（同卡字段重复）／field-halfwidth-colon（字段半角冒号）
//               table-columns（表格列数与表头不符）
//   ② 文本体例  quote-imbalance（中文双引号不配对）
//   ③ 建议      field-alias（核心字段的非规范写法，建议统一）
//
// 「卡片文件」（卡名／字段类检查只在这些文件跑）：见 CARD_FILES 白名单——人物的「卡」长在
// characters.md 里（各书同名），其余台账的 `###` 多是分节标题，扫卡名会满屏假阳。
//
// 用法：
//   npm run lint:state                 # 全量报告（只上屏）
//   npm run lint:state -- --fail       # 有「结构错误」时退出码 1（CI 用）
//   npm run lint:state -- --json       # 机读输出
//   npm run lint:state -- --book 天阙   # 只看某本书
//   npm run lint:state -- --only glued-heading,dup-card   # 只看某些检查
//
// 纪律：默认只报告、不判失败（台账是手写文档，判定权在人）；--fail 才拦。
import { readdirSync, readFileSync, existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const argv = process.argv.slice(2)
const has = (f) => argv.includes(f)
const asJson = has('--json')
const failOnError = has('--fail')
const bookIdx = argv.indexOf('--book')
const onlyBook = bookIdx >= 0 ? argv[bookIdx + 1] : null
const chkIdx = argv.indexOf('--only')
const onlyChecks = chkIdx >= 0 ? new Set((argv[chkIdx + 1] || '').split(',').filter(Boolean)) : null

const CARD_FILES = new Set(['characters.md'])  // 「卡」文件白名单（dup-card／dup-field／field-alias 只在此类文件生效）
const CORE_FIELDS = ['年龄', '身份', '外貌', '境界', '性格', '命运', '说话风格', '核心台词', '定位', '命名纪律']
const TIER = {
  'glued-heading': 1, 'level-jump': 1, 'dup-card': 1, 'dup-field': 1,
  'field-halfwidth-colon': 1, 'table-columns': 1,
  'quote-imbalance': 2,
  'field-alias': 3,
}

const HEAD = /^(#{1,6})\s+(.*)$/
const FIELD = /^-\s+\*\*([^*]+?)([:：])\*\*/
const isTableRow = (l) => /^\s*\|.*\|\s*$/.test(l)
const isTableSep = (l) => /^\s*\|[\s:|-]+\|\s*$/.test(l)
const stripCode = (l) => l.replace(/`[^`]*`/g, '')

/** 规范化标题名：去序号、去括注与分隔符后缀，用于判重 */
function cardName(h) {
  let t = h.replace(/^[0-9]+[a-z]?[.\u3001]\s*/, '').trim()
  t = t.split(/[\uFF08(\uFF5C|\u00B7\s\u2014/]/)[0].trim()
  return t
}
const isPersonName = (t) => /^[\u4e00-\u9fa5]{2,}$/.test(t)

function lintFile(rel, text) {
  const lines = text.split(/\r?\n/)
  const out = []
  const add = (check, line, msg) => {
    if (onlyChecks && !onlyChecks.has(check)) return
    out.push({ check, tier: TIER[check], line, msg })
  }

  // 卡片识别 + 卡片文件判定
  const headings = []
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(HEAD)
    if (m) headings.push({ i, lvl: m[1].length, name: m[2].trim() })
  }
  const cardHasField = new Map()
  for (let hi = 0; hi < headings.length; hi++) {
    const end = hi + 1 < headings.length ? headings[hi + 1].i : lines.length
    for (let j = headings[hi].i + 1; j < end; j++) {
      if (FIELD.test(lines[j])) { cardHasField.set(headings[hi].i, true); break }
    }
  }
  const cards = headings.filter((h) => h.lvl >= 3 && cardHasField.get(h.i))
  const isCardFile = CARD_FILES.has(rel.split('/').pop())

  // ① 标题粘连 / 层级跳跃
  let prevLvl = 0
  for (const h of headings) {
    const raw = lines[h.i]
    const after = raw.replace(/^#{1,6}\s*/, '')
    if (/[^\s#]#{2,6}[^\s#\u4e00-\u9fa5A-Za-z]/.test(after) || /[^\s#]#{2,6}[\u4e00-\u9fa5A-Za-z]/.test(after)
        || /^.*\s#{2,6}\s/.test(after)) {
      add('glued-heading', h.i + 1, `标题里还嵌着另一个标题：${raw.trim().slice(0, 48)}`)
    }
    if (prevLvl && h.lvl > prevLvl + 1) {
      add('level-jump', h.i + 1, `${'#'.repeat(prevLvl)} → ${'#'.repeat(h.lvl)}：${h.name.slice(0, 40)}`)
    }
    prevLvl = h.lvl
  }

  // ① 重复卡名（仅卡片文件，同层级、纯中文 ≥2 字）
  if (isCardFile) {
    const seen = new Map()
    for (const h of cards) {
      const nm = cardName(h.name)
      if (!isPersonName(nm)) continue
      const key = `${h.lvl}:${nm}`
      if (seen.has(key)) add('dup-card', h.i + 1, `重复卡名「${nm}」（首见 ${seen.get(key)}）`)
      else seen.set(key, h.i + 1)
    }
  }

  // ① 同卡字段重复 / 字段半角冒号 / ③ 核心字段口径不统一
  const variants = new Map()   // core → Map（字段名 → 首见行号），仅卡片文件
  for (let hi = 0; hi < headings.length; hi++) {
    const end = hi + 1 < headings.length ? headings[hi + 1].i : lines.length
    const seenField = new Map()
    for (let j = headings[hi].i + 1; j < end; j++) {
      const m = lines[j].match(FIELD)
      if (!m) continue
      const [, key, colon] = m
      if (colon === ':') add('field-halfwidth-colon', j + 1, `字段「${key}」用了半角冒号`)
      if (!isCardFile) continue
      if (seenField.has(key)) add('dup-field', j + 1, `卡「${headings[hi].name.slice(0, 24)}」字段「${key}」重复（早见 ${seenField.get(key)}）`)
      else seenField.set(key, j + 1)
      if (key.length <= 8 && !/[（(]/.test(key)) {
        for (const core of CORE_FIELDS) {
          if (key.includes(core)) {
            if (!variants.has(core)) variants.set(core, new Map())
            const vm = variants.get(core)
            if (!vm.has(key)) vm.set(key, j + 1)
            break
          }
        }
      }
    }
  }
  // 只有「同一核心词在本文件用了 ≥种写法」才报（单一写法可能是有意约定，不报）
  for (const [core, vm] of variants) {
    if (vm.size < 2) continue
    const list = [...vm.entries()].map(([k, l]) => `「${k}」(L${l})`).join('、')
    add('field-alias', vm.get([...vm.keys()].find((k) => k !== core)) || 0,
      `核心字段「${core}」在本文件有 ${vm.size} 种写法：${list}——建议统一`)
  }

  // ① 表格列数与表头不符
  let headerCols = null
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i]
    if (isTableRow(l)) {
      const cells = stripCode(l).split('|').length - 2
      if (headerCols === null) headerCols = cells
      else if (isTableSep(l)) headerCols = cells
      else if (cells !== headerCols) add('table-columns', i + 1, `表格列数 ${cells} ≠ 表头 ${headerCols}`)
    } else headerCols = null
  }

  // ② 中文双引号不配对（代码段 `…` 内的引号不计，与行内扫描一致）
  const scanText = lines.map(stripCode).join('\n')
  const open = (scanText.match(/\u201C/g) || []).length
  const close = (scanText.match(/\u201D/g) || []).length
  if (open !== close) {
    // 用栈扫出第一个未闭合的 “（或先出现的多余 ”）行号
    const stack = []
    let orphan = 0
    for (let i = 0; i < lines.length; i++) {
      for (const ch of stripCode(lines[i]).replace(/[^\u201C\u201D]/g, '')) {
        if (ch === '\u201C') stack.push(i + 1)
        else if (stack.length) stack.pop()
        else if (!orphan) orphan = i + 1
      }
    }
    const line = orphan || stack[0] || 0
    const where = stack.length ? `未闭合的 “ 起于 L${stack[0]}` : (orphan ? `多余的 ” 在 L${orphan}` : '')
    add('quote-imbalance', line, `中文引号不配对：“ ${open} ／ ” ${close}（差 ${open - close}）${where}`)
  }

  return out
}

// ── 扫描 ─────────────────────────────────────────────────────────────
const booksDir = path.join(ROOT, 'books')
if (!existsSync(booksDir)) {
  console.error('找不到 books/ 目录——请在仓库根运行。')
  process.exit(2)
}
const reports = []
let nErr = 0, nBody = 0, nAdvisory = 0, nFiles = 0
for (const book of readdirSync(booksDir)) {
  const stateDir = path.join(booksDir, book, 'state')
  if (!existsSync(stateDir) || (onlyBook && book !== onlyBook)) continue
  for (const f of readdirSync(stateDir).filter((x) => x.endsWith('.md')).sort()) {
    nFiles++
    const text = readFileSync(path.join(stateDir, f), 'utf8')
    const items = lintFile(`${book}/state/${f}`, text)
    for (const it of items) {
      if (it.tier === 1) nErr++
      else if (it.tier === 2) nBody++
      else if (it.tier === 3) nAdvisory++
    }
    if (items.length) reports.push({ book, file: f, items })
  }
}

if (asJson) {
  console.log(JSON.stringify({
    files: nFiles, errors: nErr, body: nBody, advisory: nAdvisory, reports,
  }, null, 2))
} else {
  const TIER_NAME = { 1: '结构错误', 2: '文本体例', 3: '建议（advisory）' }
  console.log(`\nstate 结构校验（${nFiles} 个 .md 文件）`)
  console.log('='.repeat(72))
  if (!reports.length) {
    console.log('✓ 未发现任何问题。')
  }
  for (const tier of [1, 2, 3]) {
    const rows = []
    for (const r of reports) for (const it of r.items) if (it.tier === tier) rows.push({ ...it, file: `${r.book}/state/${r.file}` })
    if (!rows.length) continue
    console.log(`\n── ${TIER_NAME[tier]}（${rows.length} 项）`)
    const cw = Math.max(...rows.map((r) => r.check.length))
    let lastFile = ''
    for (const r of rows) {
      if (r.file !== lastFile) { console.log(`  ${r.file}`); lastFile = r.file }
      console.log(`    L${String(r.line).padEnd(5)} ${r.check.padEnd(cw)}  ${r.msg}`)
    }
  }
  console.log('\n' + '='.repeat(72))
  console.log(`合计：${reports.length} 文件有项 ｜ 结构错误 ${nErr} ／ 文本体例 ${nBody} ／ 建议 ${nAdvisory}`)
  console.log('说明：只报告、不改稿（台账手写，判定权在人）；`--fail` 可让「结构错误」拦 CI。')
}

process.exit(failOnError && nErr ? 1 : 0)
