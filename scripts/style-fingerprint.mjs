#!/usr/bin/env node
// 文风指纹看板：按卷输出段落体例 / 否定矫正句密度 / 会话话术与解释腔密度 / 引号体例 / 字数口径，
// 并可与上一次保存的快照逐项对比——让文风漂移在累积成「卷十—十二解释腔回潮」之前就被看见。
//
// 指标口径（与既有机械规则同源，避免两套数字）：
//   段落体例  叙述段/引号段/全段的均段长与 <20 字占比（state/dedup-check.py 的 F26 口径）
//   否定矫正句 `不是…(而是|是)` 单章密度（dedup-check.py 的 F24b 口径）
//   重复话术  全书范围内出现 ≥N 次的整句（≥8 字）在每卷的密度 + 该卷高频句；另有固定解释腔词表
//   引号体例  半角双引号（应为 0）、中文引号配对（开引号数 == 闭引号数）、引号段占比
//   字数口径  去章题行与 Unicode 空白，单章 ≥4000、≤5000（F22 口径）
//             【回改/新章豁免】豁免区与豁免上限读 `books/<书>/state/word-budget.json`
//             （与 dedup-check.py 同一张表）：豁免章计入 exemptN，不受 5000 约束；
//             overCeil 只统计「非豁免」章，另外单列 overExempt（豁免章超豁免上限，也应拦截）。
//
// 用法：
//   node scripts/style-fingerprint.mjs                          # 全部书目、全部卷，打印看板
//   node scripts/style-fingerprint.mjs --book 天阙 --vol 12      # 只看天阙卷十二
//   node scripts/style-fingerprint.mjs --book 天阙 --save        # 写快照 state/style-fingerprint.json
//   node scripts/style-fingerprint.mjs --book 天阙 --diff        # 与快照逐项对比，标出漂移
//   node scripts/style-fingerprint.mjs --diff --fail-on-drift    # 有漂移则退出码 1（可接入检查）
//   node scripts/style-fingerprint.mjs --json                   # 机器可读
//   node scripts/style-fingerprint.mjs --ranges 1-44,45-68      # 覆盖卷段（无卷纲文件的书目用）
//   选项：--repeat-min N（重复整句阈值，默认 3）--repeat-len N（整句最短字数，默认 8）
//
// 卷段来源（按序回退，不需要另维护章段表）：
//   ① state/outline-volN.md 的「正文第A—B章」声明；② state/outline.md 的「第N卷：M章（第A—B章）」；
//   ③ --ranges；④ 都没有则整本作为一卷（全书）。
//
// 退出码：0=正常（--fail-on-drift 时无漂移）；1=--fail-on-drift 且检到漂移。
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const BOOKS_DIR = path.join(ROOT, 'books')

// ── 参数 ────────────────────────────────────────────────────────────
const argv = process.argv.slice(2)
const has = (n) => argv.includes(`--${n}`)
function opt(name, def = null) {
  const i = argv.indexOf(`--${name}`)
  return i >= 0 ? (argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : true) : def
}
if (has('help') || has('h')) {
  const src = fs.readFileSync(fileURLToPath(import.meta.url), 'utf8')
  console.log(src.split('\n').filter((l) => l.startsWith('//')).map((l) => l.replace(/^\/\/ ?/, '')).join('\n'))
  process.exit(0)
}
const OPT = {
  book: opt('book'),
  vol: opt('vol') != null ? Number(opt('vol')) : null,
  ranges: opt('ranges'),
  repeatMin: Number(opt('repeat-min', 3)),
  repeatLen: Number(opt('repeat-len', 8)),
  save: has('save'),
  diff: has('diff'),
  json: has('json'),
  failOnDrift: has('fail-on-drift'),
}

// ── 工具 ────────────────────────────────────────────────────────────
const read = (p) => { try { return fs.readFileSync(p, 'utf8') } catch { return null } }
const readJson = (p) => { try { return JSON.parse(read(p)) } catch { return null } }
const wc = (s) => [...s.replace(/\s/g, '')].length          // 与 dedup-check.py 同口径：去全部 Unicode 空白
const per10k = (n, chars) => (chars ? +(n * 10000 / chars).toFixed(2) : 0)
const mean = (xs) => (xs.length ? +(xs.reduce((a, b) => a + b, 0) / xs.length).toFixed(1) : 0)
const pct = (a, b) => (b ? Math.round(100 * a / b) : 0)

// 段落：非空、非章题行（^#）的行各算一段——与 dedup-check.py 的 f26_stats 完全一致
function paragraphs(text) {
  return text.split('\n').map((l) => l.trim()).filter((l) => l && !l.startsWith('#'))
}
const isQuotePara = (p) => p.startsWith('“')

// ── 指标 ────────────────────────────────────────────────────────────
const F24B_RE = /不是[^，。！？\n]{1,22}[，]?(?:而是|是)/g          // F24b 否定矫正句（与 dedup-check.py 同式）
// 解释腔／对冲话术：与 F24b 互补的“再解释一遍”标记词
const TICS = ['至少', '其实', '反而', '也就是说', '换句话说', '更重要的是', '值得注意的是',
  '归根到底', '事实上', '这意味着', '不难看出', '某种意义上', '恰恰', '无非', '终究', '本来', '并不']

function analyzeChapter(n, text, dupSentences) {
  const body = text.split('\n').filter((l) => !l.startsWith('#')).join('\n')
  const paras = paragraphs(text)
  const q = paras.filter(isQuotePara)
  const nar = paras.filter((p) => !isQuotePara(p))
  const chars = wc(body)
  const ql = q.map(wc), nl = nar.map(wc), al = paras.map(wc)
  // 引号体例
  const open = (text.match(/“/g) || []).length
  const close = (text.match(/”/g) || []).length
  const half = (text.match(/"/g) || []).length
  // 重复话术：命中本书“全局重复整句表”的次数 + 解释腔词表
  const sentences = text.split(/[。！？；!?;\n]/).map((s) => s.replace(/\s/g, '')).filter((s) => s.length >= OPT.repeatLen)
  let dupHits = 0
  const dupSeen = []
  for (const s of sentences) {
    if (dupSentences.has(s)) { dupHits++; if (dupSeen.length < 40) dupSeen.push(s) }
  }
  const ticHits = {}
  for (const t of TICS) { const c = text.split(t).length - 1; if (c) ticHits[t] = c }
  const negation = (body.match(F24B_RE) || []).length
  return {
    chapter: n, chars,
    paraN: paras.length, paraMean: mean(al), paraLt20: pct(al.filter((x) => x < 20).length, al.length),
    narN: nar.length, narMean: mean(nl), narLt20: pct(nl.filter((x) => x < 20).length, nl.length),
    quoteN: q.length, quoteMean: mean(ql), quoteLt20: pct(ql.filter((x) => x < 20).length, ql.length),
    quoteShare: pct(q.length, paras.length),
    negation, dupHits, dupSeen, ticHits,
    open, close, half,
  }
}

function rollup(chapters, budget) {
  const chars = chapters.reduce((s, c) => s + c.chars, 0)
  const sum = (k) => chapters.reduce((s, c) => s + c[k], 0)
  const wmean = (num, den) => (den ? +(num / den).toFixed(1) : 0)
  const narW = sum('narN') ? chapters.reduce((s, c) => s + c.narN * c.narMean, 0) : 0
  const quoW = sum('quoteN') ? chapters.reduce((s, c) => s + c.quoteN * c.quoteMean, 0) : 0
  const tics = {}
  for (const c of chapters) for (const [k, v] of Object.entries(c.ticHits)) tics[k] = (tics[k] || 0) + v
  const dupCount = {}
  for (const c of chapters) for (const s of c.dupSeen) dupCount[s] = (dupCount[s] || 0) + 1
  const topDup = Object.entries(dupCount).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 5)
  const topTics = Object.entries(tics).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 4)
  return {
    chapters: chapters.length, chars, mean: mean(chapters.map((c) => c.chars)),
    minChars: chapters.length ? Math.min(...chapters.map((c) => c.chars)) : 0,
    maxChars: chapters.length ? Math.max(...chapters.map((c) => c.chars)) : 0,
    underFloor: chapters.filter((c) => c.chars < budget.floor).length,
    overCeil: chapters.filter((c) => !c.exempt && c.chars > budget.ceilingDefault).length,
    exemptN: chapters.filter((c) => c.exempt).length,
    overExempt: chapters.filter((c) => c.exempt && c.chars > budget.ceilingExempt).length,
    paraN: sum('paraN'), paraMean: wmean(chapters.reduce((s, c) => s + c.paraN * c.paraMean, 0), sum('paraN')),
    paraLt20: pct(sum('paraLt20') && sum('paraN') ? chapters.reduce((s, c) => s + c.paraN * c.paraLt20, 0) / 100 : 0, sum('paraN')),
    narN: sum('narN'), narMean: wmean(narW, sum('narN')),
    narLt20: pct(sum('narN') ? chapters.reduce((s, c) => s + c.narN * c.narLt20, 0) / 100 : 0, sum('narN')),
    quoteN: sum('quoteN'), quoteMean: wmean(quoW, sum('quoteN')),
    quoteLt20: pct(sum('quoteN') ? chapters.reduce((s, c) => s + c.quoteN * c.quoteLt20, 0) / 100 : 0, sum('quoteN')),
    quoteShare: pct(sum('quoteN'), sum('paraN')),
    negation: sum('negation'), negationPer10k: per10k(sum('negation'), chars),
    negationPerChapter: chapters.length ? +(sum('negation') / chapters.length).toFixed(2) : 0,
    dupHits: sum('dupHits'), dupPer10k: per10k(sum('dupHits'), chars), topDup,
    ticHits: sum(Object.values(tics).reduce((a, b) => a + b, 0)), ticPer10k: per10k(Object.values(tics).reduce((a, b) => a + b, 0), chars), topTics,
    halfwidth: sum('half'),
    unpaired: Math.abs(sum('open') - sum('close')),
    open: sum('open'), close: sum('close'),
  }
}

// ── 卷段解析 ────────────────────────────────────────────────────────
const CN = { 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9, 十: 10 }
const cnNum = (s) => {
  if (/^\d+$/.test(s)) return Number(s)
  if (s === '十') return 10
  const m = /^(.)?十(.)?$/.exec(s)
  if (m) return (m[1] ? CN[m[1]] : 1) * 10 + (m[2] ? CN[m[2]] : 0)
  return CN[s] || 0
}
function volumeMap(stateDir) {
  const map = []
  for (const f of fs.readdirSync(stateDir).filter((x) => /^outline-vol\d+\.md$/.test(x)).sort()) {
    const n = Number(/^outline-vol(\d+)\.md$/.exec(f)[1])
    const text = read(path.join(stateDir, f)) || ''
    const m = /正文\s*第\s*(\d+)\s*[—\-~]\s*(\d+)\s*章/.exec(text) || /(\d+)\s*[—\-~]\s*(\d+)\s*章/.exec(text)
    if (m) map.push({ vol: n, from: Number(m[1]), to: Number(m[2]), src: f })
  }
  const outline = read(path.join(stateDir, 'outline.md')) || ''
  for (const m of outline.matchAll(/第([一二三四五六七八九十\d]+)卷[：:]\s*(\d+)\s*章（第\s*(\d+)\s*[—\-~]\s*(\d+)\s*章）/g)) {
    const v = cnNum(m[1])
    if (v && !map.some((x) => x.vol === v)) map.push({ vol: v, from: Number(m[3]), to: Number(m[4]), src: 'outline.md' })
  }
  return map.sort((a, b) => a.from - b.from)
}
// F22 字数豁免区（源：state/word-budget.json，与 dedup-check.py 同读一表）
function wordBudget(stateDir) {
  const j = readJson(path.join(stateDir, 'word-budget.json'))
  const floor = j?.floor ?? 4000
  const ceilingDefault = j?.ceilingDefault ?? 5000
  const ceilingExempt = j?.ceilingExempt ?? ceilingDefault
  const from = j?.newChaptersFrom ?? Number.POSITIVE_INFINITY
  const ranges = (j?.exemptRanges || []).map((r) => r.range).filter((r) => Array.isArray(r) && r.length === 2)
  return {
    floor, ceilingDefault, ceilingExempt, ranges: ranges.length, from,
    isExempt: (n) => n >= from || ranges.some(([a, b]) => n >= a && n <= b),
  }
}
function f26Treated(stateDir) {
  const src = read(path.join(stateDir, 'dedup-check.py'))
  if (!src) return null
  const m = /F26_TREATED\s*=\s*\[([^\]]*)\]/.exec(src)
  if (!m) return null
  return [...m[1].matchAll(/\(\s*(\d+)\s*,\s*(\d+)\s*\)/g)].map((x) => [Number(x[1]), Number(x[2])])
}

// ── 主流程 ──────────────────────────────────────────────────────────
const projects = fs.readdirSync(BOOKS_DIR).sort()
  .map((name) => ({ name, novel: path.join(BOOKS_DIR, name, 'novel'), state: path.join(BOOKS_DIR, name, 'state') }))
  .filter((p) => fs.existsSync(p.novel) && fs.existsSync(p.state))
  .filter((p) => !OPT.book || p.name === OPT.book)

if (!projects.length) { console.error(`未找到书目${OPT.book ? `：${OPT.book}` : ''}`); process.exit(2) }

const report = { generatedAt: new Date().toISOString(), repeatMin: OPT.repeatMin, repeatLen: OPT.repeatLen, books: {} }
let driftTotal = 0
const lines = []

for (const proj of projects) {
  const chapters = fs.readdirSync(proj.novel).filter((f) => /^chapter-\d+\.md$/.test(f)).sort()
    .map((f) => ({ n: Number(/chapter-(\d+)\.md/.exec(f)[1]), file: path.join(proj.novel, f) }))
  if (!chapters.length) continue
  const texts = new Map(chapters.map(({ n, file }) => [n, read(file) || '']))

  // 全书重复整句表（先全书统计，再按卷归集——「重复」是全书尺度的概念）
  const sentenceCount = new Map()
  for (const [, text] of texts) {
    for (const s of text.split(/[。！？；!?;\n]/).map((x) => x.replace(/\s/g, ''))) {
      if (s.length >= OPT.repeatLen && !s.startsWith('#') && !/^[“”‘’"'（）()《》、，—…\-.]+$/.test(s)) {
        sentenceCount.set(s, (sentenceCount.get(s) || 0) + 1)
      }
    }
  }
  const dupSentences = new Set([...sentenceCount].filter(([, c]) => c >= OPT.repeatMin).map(([s]) => s))

  const budget = wordBudget(proj.state)
  const per = new Map()
  for (const [n, text] of texts) {
    const c = analyzeChapter(n, text, dupSentences)
    c.exempt = budget.isExempt(n)
    per.set(n, c)
  }

  // 卷段
  let ranges = volumeMap(proj.state)
  if (!ranges.length && OPT.ranges) {
    ranges = String(OPT.ranges).split(',').map((r) => {
      const [a, b] = r.split('-').map(Number)
      return { vol: null, from: a, to: b, src: '--ranges' }
    })
  }
  if (!ranges.length) ranges = [{ vol: null, from: chapters[0].n, to: chapters[chapters.length - 1].n, src: '全书' }]
  const treated = f26Treated(proj.state)

  const vols = []
  let seg = 0
  for (const r of ranges) {
    if (OPT.vol != null && r.vol !== OPT.vol) continue
    const cs = [...per.values()].filter((c) => c.chapter >= r.from && c.chapter <= r.to)
    if (!cs.length) continue
    seg++
    const enforced = treated ? cs.some((c) => treated.some(([a, b]) => c.chapter >= a && c.chapter <= b)) : null
    vols.push({
      label: r.vol ? `卷${r.vol}` : ranges.length > 1 ? `段${seg}` : '全书', vol: r.vol, from: r.from, to: r.to,
      range: `ch${r.from}—${r.to}`, src: r.src, f26: enforced, ...rollup(cs, budget),
    })
  }
  const all = rollup([...per.values()], budget)
  // 有多个卷段时补一行整本汇总；整本一卷就不重复第二遍
  if (OPT.vol == null && ranges.length > 1) vols.push({ label: '全卷', vol: null, from: chapters[0].n, to: chapters[chapters.length - 1].n, range: `ch${chapters[0].n}—${chapters[chapters.length - 1].n}`, src: '全书', f26: null, ...all })

  if (!vols.length) continue
  report.books[proj.name] = { volumes: vols }
  if (OPT.json) continue

  const prior = OPT.diff ? (readJson(path.join(proj.state, 'style-fingerprint.json')) || null) : null
  const priorBy = new Map((prior?.books?.[proj.name]?.volumes || []).map((v) => [v.label, v]))

  const srcs = [...new Set(vols.map((v) => v.src).filter((s) => s !== '全书'))]
  lines.push('', `════ ${proj.name}｜文风指纹（${chapters.length} 章${srcs.length ? '，卷段来自 ' + (srcs.length > 3 ? `${srcs.length} 处声明` : srcs.join('／')) : '，整本一卷'}）`)
  lines.push('  卷段        章  字数/章  段/均段/<20字      叙述均段/<20字   引号均段/<20字/占比   否定句/万字  重复话术/万字  半角/未配对  字数越界')
  for (const v of vols) {
    // 漂移口径表：[指标, 变差方向, 容差, 是否在行内标 ▲▼]。计数与标记同用一张表，避免两套数字。
    const DEG = [
      ['paraLt20', 'up', 2, true], ['narMean', 'down', 3, true], ['narLt20', 'up', 3, false],
      ['quoteMean', 'down', 2, true], ['negationPer10k', 'up', 2, true], ['dupPer10k', 'up', 2, true],
      ['halfwidth', 'up', 0, true], ['unpaired', 'up', 0, true], ['underFloor', 'up', 0, true], ['overCeil', 'up', 0, true], ['overExempt', 'up', 0, true],
    ]
    const drift = new Map()
    for (const [k, worse, tol] of DEG) {
      const p = priorBy.get(v.label)
      if (!p || !(k in p)) continue
      const d = +(v[k] - p[k]).toFixed(2)
      const bad = worse === 'up' ? d > tol : -d > tol
      if (bad) driftTotal++
      drift.set(k, { d, bad })
    }
    const mark = (k) => {
      const r = drift.get(k)
      const show = DEG.find(([n]) => n === k)?.[3]
      if (!r || !r.d || !show) return ''
      return ` ${r.d > 0 ? '▲' : '▼'}${Math.abs(r.d).toFixed(1)}${r.bad ? '⚠' : ''}`
    }
    // f26=true 表示本章段落在 F26_TREATED 内（该区间受机械判失败约束），否则只报告
    const f26 = v.f26 === null ? '' : v.f26 ? '  F26严格' : '  F26仅报告'
    lines.push(`  ${v.label.padEnd(6)} ${String(v.chapters).padStart(4)}  ${String(v.mean).padStart(6)}  ` +
      `${String(v.paraN).padStart(5)}/${String(v.paraMean).padStart(5)}/${String(v.paraLt20).padStart(2)}%${mark('paraLt20')}` +
      `   ${String(v.narMean).padStart(5)}/${String(v.narLt20).padStart(2)}%${mark('narMean')}` +
      `      ${String(v.quoteMean).padStart(5)}/${String(v.quoteLt20).padStart(2)}%/${String(v.quoteShare).padStart(2)}%${mark('quoteMean')}` +
      `     ${String(v.negationPer10k).padStart(5)}${mark('negationPer10k')}` +
      `        ${String(v.dupPer10k).padStart(5)}${mark('dupPer10k')}` +
      `      ${String(v.halfwidth).padStart(2)}/${String(v.unpaired).padStart(2)}${mark('halfwidth')}${mark('unpaired')}` +
      `   ${v.underFloor}/${v.overCeil}${mark('underFloor')}${mark('overCeil')}${v.exemptN ? `（豁免${v.exemptN}章${v.overExempt ? `，超限${v.overExempt}${mark('overExempt')}` : ''}）` : ''}${f26}`)
  }
  // 明细：最长/最短章、重复话术与解释腔 top
  const byChars = [...per.values()].sort((a, b) => a.chars - b.chars || a.chapter - b.chapter)
  lines.push(`  · 字数：最短 ch${byChars[0].chapter}（${byChars[0].chars} 字）／最长 ch${byChars[byChars.length - 1].chapter}（${byChars[byChars.length - 1].chars} 字）／低于下限 ${all.underFloor} 章／超上限 ${all.overCeil} 章${all.exemptN ? `（另有回改/新章豁免 ${all.exemptN} 章，豁免上限 ${budget.ceilingExempt}，超豁免上限 ${all.overExempt} 章）` : ''}`)
  const bookDup = new Map()
  for (const c of per.values()) for (const s of c.dupSeen) bookDup.set(s, (bookDup.get(s) || 0) + 1)
  const topDupBook = [...bookDup].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 6)
  if (topDupBook.length) lines.push(`  · 全书高频重复句（≥${OPT.repeatMin} 次，跨章数）：` + topDupBook.map(([s, c]) => `${c}章“${s.length > 18 ? s.slice(0, 18) + '…' : s}”`).join('　'))
  const bookTics = {}
  for (const c of per.values()) for (const [k, v] of Object.entries(c.ticHits)) bookTics[k] = (bookTics[k] || 0) + v
  lines.push(`  · 解释腔词表（全书）：` + Object.entries(bookTics).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k, v]) => `${k}×${v}`).join('　'))

  if (OPT.save) {
    const out = path.join(proj.state, 'style-fingerprint.json')
    const prev = readJson(out)
    const payload = { ...report, books: { ...(prev?.books || {}), ...report.books } }
    if (prev?.books) for (const [b, d] of Object.entries(prev.books)) if (!report.books[b] && !payload.books[b]) payload.books[b] = d
    // 只保留本次跑到的书目 + 快照里已有的其他书目
    payload.books = { ...(prev?.books || {}), ...report.books }
    const tmp = { generatedAt: payload.generatedAt, repeatMin: OPT.repeatMin, repeatLen: OPT.repeatLen, books: payload.books }
    fs.writeFileSync(out, JSON.stringify(tmp, null, 2) + '\n')
    lines.push(`  · 已写快照：${path.relative(ROOT, out)}`)
  }
}

if (OPT.json) {
  console.log(JSON.stringify(report, null, 2))
} else {
  lines.push('')
  lines.push('说明：字数口径的「回改/新章豁免区」读 state/word-budget.json（与 dedup-check.py 同源）：豁免章不计入 overCeil，另计 overExempt（超过豁免上限）。')
  lines.push('说明：段落体例与字数口径与 state/dedup-check.py（F26／F22）同源；「重复话术」按全书尺度统计整句（≥' + OPT.repeatLen + ' 字）出现 ≥' + OPT.repeatMin + ' 次者；▲▼ 为与 state/style-fingerprint.json 的差值，⚠ 表示超过漂移阈值（<20字占比 +2pp、叙述均段 −3 字、引号均段 −2 字、否定句/万字 +2、重复话术/万字 +2、半角或未配对引号 +1、越界章 +1）。')
  console.log(lines.join('\n'))
}

if (OPT.failOnDrift && driftTotal) {
  console.error(`✗ 文风漂移：${driftTotal} 项超过阈值（--fail-on-drift）`)
  process.exit(1)
}
