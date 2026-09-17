#!/usr/bin/env node
// 一致性终检：源（books/<书名>/novel|state/）↔ 站点镜像（public/novels/<书名>/）↔ 台账（卷纲声明/字数口径）
//
// 用途：每卷收尾一键跑，替代此前手工做的三向比对。
// 检查项：
//   ① 章节源↔镜像 md5 逐字节一致（缺文件/内容不同即失败）
//   ② state/*.md 源↔镜像一致，镜像多余文件单列警告；脚本直接读的结构化台账（life-windows/custody-chains/
//      character-onsets/word-budget）也按字节比对——否则脚本核的是旧账
//   ③ index.json 覆盖（chapters 列全、stateFiles 列全、与源数量一致） //   ④ 卷纲章题声明 vs 正文 H1 章题一致（章题不符即失败；「声明章缺正文」按警告处理——卷纲先声明后开写是本仓惯例，--predecl 时对回填范围内缺章升为失败）
//   ⑤ 字数口径台账（去章题行与 Unicode 空白，与 state/dedup-check.py 同口径），
//      单章低于 --min 默认只登记警告；加 --strict 升为失败（卷收尾用）
//   ⑥ F23 跨章物件持有链（台账 state/custody-chains.json）：同一件物证在两次出现的章节间
//      交接/分拆是否自洽——A 每步须命中持有锚点；B 易主须有交接词；C 分拆/归档后再以整体出现即报错。
//   ⑩ F33 人物首现台账闭环（state/character-onsets.json × 正文）：
//      ①台账声明的首现章必须真的查得到其人（防“台账先行、正文空转”）；
//      ②首次具名仍在末两卷的人数超阈值即警告（作者口径：不要都挤在卷十三／十四）。
//      与 F30 分工：F30 管“不得早于台账出现”，F33 管“不得晚于／落空台账声明”。
//   ⑧ F31 人物卡排期闭环（state/characters.md × outline-vol13/14 × appearance-plan.md §十二）：
//      每张人物卡必须回答“排入哪一卷”或“为什么不回”（不回需登记豁免/已故/待裁决），否则判失败。
//   ⑪ F35 在世窗口闭环（state/life-windows.json × 卷→年表 × chronology.md §一）：
//      档案声明了卒年／命运节点的角色，其落点章换算出的年份必须在在世窗口内（本人出场不得晚于卒年；
//      文书/口述类 L0 载体只受生年约束），并逐卷比对 volume_years 与 chronology.md 卷表。
//   ⑦ progress 台账语义：state/progress.md 的「当前阶段/当前章节/总章节数」↔ 正文实际章数
//      （以及镜像 index.json 的 progress 是否与源同步）。字节比对拦不住语义漂移（如 ch284 已写、
//       台账仍写 260），故单列一项；字段缺失时只警告、不判失败。
//      （编号说明：state/dedup-check.py 的 F21 = 同章物件去向互斥、F22 = 单章字数口径；
//        跨章这一层在一致脚本里编为 F23，避免与既有编号冲突。）
//
// 用法：
//   node scripts/consistency-check.mjs                              # 全部书目、全部卷
//   node scripts/consistency-check.mjs --book 天阙 --vol 11          # 只查天阙卷十一（ch237—260）
//   node scripts/consistency-check.mjs --book 天阙 --vol 12 --strict # 卷收尾：字数也判失败
//   node scripts/consistency-check.mjs --book 天阙 --vol 11 --dedup  # 顺带跑 state/dedup-check.py
//   node scripts/consistency-check.mjs --dedup --legacy             # 另列出「存量·仅报告」的逐条详单
//      dedup 输出分两档：判失败项逐条打印（带章号）；各规则「某章起才判失败」之前的存量命中只给
//      按规则 / 按章号的计数摘要——它们在某些书里可达上百处（如天阙 140 处），与失败项混在一起打印
//      会让「通过」的一跑看起来像「失败」。存量是历史存稿、非本轮改动引入，故只报告不判失败。
//   node scripts/consistency-check.mjs --min 0                      # 只看一致性，不看字数
//   node scripts/consistency-check.mjs --json                       # 机器可读输出
//
// 退出码：0=通过（字数仅警告），1=有失败项（含 --strict 下的字数不足）。

import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const BOOKS_DIR = path.join(ROOT, 'books')
const PUBLIC_NOVELS = path.join(ROOT, 'public', 'novels')

// ── 参数 ────────────────────────────────────────────────────────────
const argv = process.argv.slice(2)
function flag(name, def = null) {
  const i = argv.indexOf(`--${name}`)
  return i >= 0 ? (argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : true) : def
}
const OPT = {
  book: flag('book'),
  vol: flag('vol') != null ? Number(flag('vol')) : null,
  min: flag('min') != null ? Number(flag('min')) : 4000,
  strict: argv.includes('--strict'),
  dedup: argv.includes('--dedup'),
  legacy: argv.includes('--legacy'),
  python: flag('python', 'python'),
  json: argv.includes('--json'),
  quiet: argv.includes('--quiet'),
  predecl: argv.includes('--predecl'),
  help: argv.includes('--help') || argv.includes('-h'),
}

if (OPT.help) {
  const src = fs.readFileSync(fileURLToPath(import.meta.url), 'utf8')
  console.log(src.split('\n').filter((l) => l.startsWith('//')).map((l) => l.replace(/^\/\/ ?/, '')).join('\n'))
  process.exit(0)
}

// ── 工具 ────────────────────────────────────────────────────────────
const read = (p) => {
  try { return fs.readFileSync(p, 'utf8') } catch { return null }
}
const md5 = (p) => crypto.createHash('md5').update(fs.readFileSync(p)).digest('hex')
const isFile = (p) => { try { return fs.statSync(p).isFile() } catch { return false } }
const isDir = (p) => { try { return fs.statSync(p).isDirectory() } catch { return false } }

/** 正文 H1 章题：`# 第二百三十七章《换榜》` → 《换榜》 */
function chapterTitle(text) {
  const m = /第[零一二三四五六七八九十百千\d]+章[《【]([^》】]+)[》】]/.exec(text || '')
  return m ? m[1] : null
}
/** 卷纲声明：`第237章《换榜》〔公文·追缉〕` → {237: '换榜'} */
function outlineDeclared(text) {
  const out = {}
  for (const m of (text || '').matchAll(/第(\d+)章[《【]([^》】]+)[》】]/g)) {
    const n = Number(m[1])
    if (!(n in out)) out[n] = m[2] // 首现为准，避免正文提及覆盖声明
  }
  return out
}
/** 统一字数口径：去章题行（^#…）后删全部空白（含全角空格等 Unicode 空白，与 state/dedup-check.py 口径一致） */
const WS = /[\s\u00a0\u1680\u180e\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]/g
function wordCount(text) {
  const body = (text || '').replace(/^#.*$/gm, '')
  return body.replace(WS, '').length
}
/** 返回 [{n, file}]，保留零填充文件名（如 chapter-01.md） */
function chapterFiles(novelDir) {
  if (!isDir(novelDir)) return []
  return fs.readdirSync(novelDir)
    .map((f) => {
      const m = /^chapter-(\d+)\.md$/.exec(f)
      return m ? { n: Number(m[1]), file: f } : null
    })
    .filter(Boolean)
    .sort((a, b) => a.n - b.n)
}
function bookTitle(bookDir) {
  const theme = (read(path.join(bookDir, 'state', 'theme.txt')) || '').split('\n')[0].trim()
  return theme || path.basename(bookDir)
}

// ── ⑥ F23 跨章物件持有链 ───────────────────────────────────────────
// 台账：books/<书名>/state/custody-chains.json
//   { "chains": [ { "id": "行军簿抄页", "steps": [ { "ch": 253, "holder": "沈广农",
//       "anchors": ["封进原来的油布套"], "handover": ["送回扬州"] }, … ],
//       "terminal": { "ch": 260, "why": "…", "forbid_after": ["抄页在沈广农手里"] } } ] }
// 规则：
//   F23A 每步在所登记章内须命中 anchors 之一（否则“未落位”）；登记的章号必须存在。
//   F23B 相邻两步持有者不同时，两步各自列表里须至少有一处命中 handover（否则“易主无交接”）。
//   F23C 登记 terminal 的链，terminal 章之后的章节不得命中 forbid_after（分拆/归档后又以整体出现）。
function loadCustodyChains(stateDir) {
  const p = path.join(stateDir, 'custody-chains.json')
  if (!isFile(p)) return { file: null, chains: [], error: null }
  try {
    const data = JSON.parse(read(p))
    const chains = Array.isArray(data?.chains) ? data.chains : []
    return { file: p, chains, error: null }
  } catch (e) {
    return { file: p, chains: [], error: `custody-chains.json 不是合法 JSON：${e.message}` }
  }
}

function checkCustodyChains({ stateDir, novelDir, targets, allMap, declaredChapterNumbers = new Set(), fail, warn, notes }) {
  const { chains, error } = loadCustodyChains(stateDir)
  if (!chains.length && !error) return null
  if (error) { fail(error); return null }

  const allSet = new Set(allMap.keys())
  const textOf = (n) => (allMap.has(n) ? read(path.join(novelDir, allMap.get(n))) || '' : '')
  const inRange = new Set(targets)
  let steps = 0
  const skipped = []
  const pending = []

  for (const chain of chains) {
    const id = chain.id || '(未命名链)'
    const list = Array.isArray(chain.steps) ? chain.steps : []
    const active = []
    for (const st of list) {
      const n = Number(st.ch)
      if (!Number.isFinite(n)) { fail(`F23 链「${id}」有非法章号：${st.ch}`); continue }
      if (!allSet.has(n)) {
        if (declaredChapterNumbers.has(n)) {
          pending.push(`ch${n}`)
          continue
        }
        fail(`F23 链「${id}」登记的章不存在：ch${n}`)
        continue
      }
      if (!inRange.has(n)) { skipped.push(`ch${n}`); continue }
      if (!Array.isArray(st.anchors) || !st.anchors.length) {
        fail(`F23 链「${id}」ch${n} 未登记持有锚点`)
        continue
      }
      active.push({ ...st, n, text: textOf(n) })
      steps += 1
    }

    // F23A 落位
    for (const st of active) {
      if (!st.anchors.some((a) => st.text.includes(a))) {
        fail(`F23A 链「${id}」ch${st.n} 未落位：持有者「${st.holder}」的锚点 ${st.anchors.map((a) => `「${a}」`).join('、')} 一个也未出现`)
      }
    }

    // F23B 易主须有交接
    for (let i = 1; i < active.length; i += 1) {
      const prev = active[i - 1]
      const cur = active[i]
      if (prev.holder === cur.holder) continue
      const words = [...(prev.handover || []), ...(cur.handover || [])]
      if (!words.length) {
        fail(`F23B 链「${id}」ch${prev.n}（${prev.holder}）→ ch${cur.n}（${cur.holder}）易主，但两步都未登记交接词`)
        continue
      }
      if (!words.some((w) => prev.text.includes(w) || cur.text.includes(w))) {
        fail(`F23B 链「${id}」ch${prev.n}（${prev.holder}）→ ch${cur.n}（${cur.holder}）易主无交接：${words.map((w) => `「${w}」`).join('、')} 均未出现`)
      }
    }

    // F23C 终局后复现
    const term = chain.terminal
    if (term && Number.isFinite(Number(term.ch))) {
      const t = Number(term.ch)
      const forbid = Array.isArray(term.forbid_after) ? term.forbid_after : []
      if (!forbid.length) {
        warn(`F23 链「${id}」登记了 terminal ch${t}，但未列 forbid_after，终局后复现无法机械校验`)
      }
      const after = targets.filter((n) => n > t)
      for (const n of after) {
        const t2 = textOf(n)
        const hit = forbid.find((w) => t2.includes(w))
        if (hit) {
          fail(`F23C 链「${id}」ch${t} 已终局（${term.why || '分拆/归档'}），ch${n} 又以整体出现：「${hit}」`)
        }
      }
    }
  }

  if (skipped.length) {
    const uniq = [...new Set(skipped)].sort((a, b) => Number(a.slice(2)) - Number(b.slice(2)))
    notes.push(`跨章持有链：${uniq.join('、')} 不在本次范围内（--vol 限定），相关链未全量校验`)
  }
  if (pending.length) {
    const uniq = [...new Set(pending)].sort((a, b) => Number(a.slice(2)) - Number(b.slice(2)))
    notes.push(`跨章持有链：${uniq.join('、')} 已在卷纲声明但正文尚未开写，待对应章落地后校验`)
  }
  return { chains: chains.length, steps }
}

// ── ⑧ F31 人物卡排期闭环 ───────────────────────────────────────────
// 台账：books/<书名>/state/characters.md 的人物卡（### / #### 小标题里的姓名）
//   规则：每张人物卡必须"已分类"——姓名（或该小标题内的同一人名变体）出现在
//     · outline-vol13.md / outline-vol14.md（＝已排期），或
//     · state/appearance-plan.md（含 §十二 终审表：不回／已故／真缺口／待裁决）
//   未分类 ⇒ 新増了人物卡却没有回答"他出现在哪一卷、或为什么不出现" → 判失败。
//   标题里含下列词的属分类性/群组标题，不是人卡；说明性词组（已故/岁出场…）不计。
const CARD_GROUP_RE = /(人物|纪律|关系网|补档|谱系|姓名考|矩阵|圈层|首领|传人|四卫|藩镇|附：|第[一二三]代|丐帮|青城派|崆峒派|海沙帮|河东军|剑南军|夜行司|观天台|烛微阁|八凶|宗师录|朝堂|市井|名单|军中|本节|传说)/
const CARD_TOKEN_SKIP = new Set(['已故', '新増', '随卷更新', '校订条', '岁出场', '双主角'])
function characterCards(text) {
  const out = []
  // 注意：必须按 CRLF 切行——JS 的 `$` 在非多行模式下不匹行尾的 \r，
  // 直接 split('\n') 会让 CRLF 版 characters.md（本书即如此）一张卡也拓不到。
  for (const raw of String(text || '').split(/\r?\n/)) {
    const m = /^#{3,4}\s+(.*)$/.exec(raw)
    if (!m) continue
    const head = m[1].trim().replace(/^\d+[a-z]?[.、]\s*/, '')
    if (head.includes('：') || CARD_GROUP_RE.test(head)) continue
    const toks = [...head.matchAll(/[\u4e00-\u9fff]{2,6}/g)].map((x) => x[0])
      .filter((t) => !CARD_TOKEN_SKIP.has(t))
    if (!toks.length || out.some((c) => c.head === head)) continue
    out.push({ head, toks })
  }
  return out
}
function checkCharacterCards({ stateDir, fail, warn, notes }) {
  const cardsText = read(path.join(stateDir, 'characters.md'))
  const plan = read(path.join(stateDir, 'appearance-plan.md'))
  if (!cardsText) { notes.push('F31 人物卡排期闭环：本书无 state/characters.md，不适用'); return { cards: 0, unclassified: 0 } }
  if (plan == null) {
    // 排期闭环只在维护「出场编排表」的书里生效（当前为《天阙》）；其余书目不能用该规则拦。
    notes.push('F31 人物卡排期闭环：本书无 state/appearance-plan.md，规则不适用（先建立编排表再启用）')
    return { cards: 0, unclassified: 0 }
  }
  const scheduled = ['outline-vol13.md', 'outline-vol14.md']
    .map((f) => read(path.join(stateDir, f)) || '').join('\n')
  const cards = characterCards(cardsText)
  const unclassified = cards
    .filter((c) => !c.toks.some((t) => scheduled.includes(t) || (plan || '').includes(t)))
    .map((c) => c.head)
  if (unclassified.length) {
    fail(`F31 人物卡未分类（${unclassified.length} 张）：${unclassified.join('、')}`
      + '　→ 每张人物卡必须排入卷十三/十四卷纲，或在 state/appearance-plan.md §十二 终审表登记"不回／已故／待裁决"')
  }
  return { cards: cards.length, unclassified: unclassified.length }
}

// ── ⑨ F32 双榜席位首现闭环 ────────────────────────────────────
// 台账：state/rankings.md（《天下宗师录》十二席 / 黑榜十人 / 八凶八人）
//   规则：每一位席位人物必须"首现闭环"——
//     · 正文 ch1—285 内实际出现（按章计数，不看台账声明），或
//     · 在 appearance-plan.md §14.3「前置植入表」内一行，且该行的前置锚点落在已写卷。
//   另报均衡比：正文 ≤1 章的席位数（＝"只能靠末两卷首次出现"的那一批），>6 仅警告。
//   背景：名单在台账里是满的，在正文里可能是空的——而这类故障不在任何一张表里。
const SEAT_NAME_SKIP = new Set(['姓名', '空缺', '代号', '—', '-'])
const SEAT_HEAD_SKIP = new Set(['席位', '排名', '称号', '年份', '人物', '姓名'])
const CN_NUM = { 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9, 十: 10,
  十一: 11, 十二: 12, 十三: 13, 十四: 14 }
function seatHolders(rankingsText) {
  const cut = String(rankingsText || '').indexOf('## 四、白玉京')
  const lines = (cut > 0 ? String(rankingsText).slice(0, cut) : String(rankingsText || '')).split(/\r?\n/)
  const out = []
  let inTable = false
  for (const raw of lines) {
    const tr = raw.trim()
    if (!tr || tr.startsWith('#')) { inTable = false; continue } // 空行或新小节：表格结束
    if (!tr.startsWith('|')) continue // 说明行、引用块（三个名单的表头与数据行之间都有注释行）
    const cells = raw.split('|').slice(1, -1).map((c) => c.replace(/\*\*/g, '').trim())
    if (cells.length < 2) continue
    if (cells[1] === '姓名') { inTable = true; continue } // 表头：三个名单同构，第 2 格是姓名
    if (SEAT_HEAD_SKIP.has(cells[0])) continue
    if (!inTable) continue
    const nm = cells[1]
    if (!nm || SEAT_NAME_SKIP.has(nm) || !/^[\u4e00-\u9fff]{2,5}$/.test(nm)) continue
    if (!out.includes(nm)) out.push(nm)
  }
  return out
}
function plantedSeatNames(plan) {
  const t = String(plan || '')
  const i = t.indexOf('### 14.3')
  if (i < 0) return new Set()
  const j = t.indexOf('### 14.4', i)
  const sec = t.slice(i, j > 0 ? j : undefined)
  const ok = new Set()
  for (const raw of sec.split(/\r?\n/)) {
    if (!/^\s*\|/.test(raw)) continue
    const cells = raw.split('|').slice(1, -1).map((c) => c.replace(/\*\*/g, '').trim())
    if (cells.length < 7) continue // 档|人物|席位|现计划|前置锚点|依据|后段
    const anchor = cells[4]
    if (!anchor) continue
    let qualified = /已在案|已落地|已排|已就位/.test(anchor)
    if ([...anchor.matchAll(/ch\s*(\d+)/g)].some((m) => Number(m[1]) <= 285)) qualified = true
    for (const m of anchor.matchAll(/卷([一二三四五六七八九十]+)/g)) {
      const v = CN_NUM[m[1]]
      if (v && v <= 12) qualified = true
    }
    if (!qualified) continue
    for (const nm of (cells[1].match(/[\u4e00-\u9fff]{2,5}/g) || [])) ok.add(nm)
  }
  return ok
}
function checkSeatOnsets({ stateDir, novelDir, allMap, fail, warn, notes }) {
  const rank = read(path.join(stateDir, 'rankings.md'))
  if (!rank) { notes.push('F32 双榜席位首现闭环：本书无 state/rankings.md，不适用'); return { seats: 0, unclosed: [], thin: 0 } }
  const plan = read(path.join(stateDir, 'appearance-plan.md'))
  if (plan == null) {
    notes.push('F32 双榜席位首现闭环：本书无 state/appearance-plan.md，规则不适用')
    return { seats: 0, unclosed: [], thin: 0 }
  }
  const seats = seatHolders(rank)
  const planted = plantedSeatNames(plan)
  const text = new Map()
  for (const [n, file] of allMap) {
    if (n > 285) continue
    text.set(n, read(path.join(novelDir, file)) || '')
  }
  const unclosed = []
  let thin = 0
  for (const nm of seats) {
    const hits = [...text.entries()].filter(([, s]) => s.includes(nm)).map(([n]) => n)
    if (hits.length <= 1) thin += 1
    if (!hits.length && !planted.has(nm)) unclosed.push(nm)
  }
  if (unclosed.length) {
    fail(`F32 双榜席位未闭环（${unclosed.length} 位）：${unclosed.join('、')}`
      + '　→ 每位席位人物要么在正文 ch1—285 内出现，要么在 appearance-plan.md §14.3 登记带已写卷锚点的前置植入行')
  }
  if (thin > 6) {
    warn(`F32 双榜席位首现均衡：${seats.length} 席中正文 ≤1 章者 ${thin} 位（目标 ≤6）——其余只能靠末两卷首次具名`)
  }
  return { seats: seats.length, unclosed, thin }
}

// ── ⑩ F33 人物首现台账闭环（state/character-onsets.json × 正文）──────
//   台账（F30 读它做“不得提前出现”的校验）里写下的 first_appearance，本项做两件反向校验：
//     a) 声明落在已写章的，该章正文必须真的查得到这个人——否则是“台账上写了、正文里没落”
//        的假闭环（声明而未落者单列警告，不判失败：如李虎 ch279 属已裁决待回改）；
//     b) 统计首次具名仍在末两卷（≥ ch286）的人数——作者口径是“不要都挤在卷十三／十四卷纲”，
//        超阈值即警告（首现本身可以晚，但全堆在末尾必须看得见）。
//   与 F30 分工：F30 管“不得早于台账出现”，F33 管“不得晚于/落空台账声明”。
const ONSET_LATE_FROM = 286
const ONSET_LATE_MAX = 10
function checkOnsetLedger({ stateDir, novelDir, allMap, fail, warn, notes }) {
  const raw = read(path.join(stateDir, 'character-onsets.json'))
  if (!raw) { notes.push('F33 人物首现台账：本书无 state/character-onsets.json，规则不适用'); return null }
  let list = []
  try { list = JSON.parse(raw).characters || [] } catch (e) {
    fail(`F33 人物首现台账解析失败：${e.message}`)
    return null
  }
  const late = []      // 首现仍在末两卷（或未定）
  const pending = []   // 声明了已写章，但该章正文查无其名
  let verified = 0
  for (const c of list) {
    const n = c.first_appearance
    const toks = [c.name, ...(c.aliases || [])]
    if (n == null || n >= ONSET_LATE_FROM) { late.push(`${c.name}(${n == null ? '未定' : `ch${n}`})`); continue }
    const file = allMap.get(n)
    if (!file) continue                       // 该章不在本次检查范围内（--vol 限定）
    const t = read(path.join(novelDir, file)) || ''
    if (toks.some((x) => t.includes(x))) verified += 1
    else pending.push(`${c.name}(声明 ch${n})`)
  }
  if (pending.length) {
    warn(`F33 台账声明首现章查无其名（${pending.length} 人）：${pending.join('、')}`
      + '　→ 要么把名字落进该章，要么改 first_appearance（含已裁决待回改项时属预期）')
  }
  if (late.length > ONSET_LATE_MAX) {
    warn(`F33 人物首现前移：${list.length} 人中 ${late.length} 人首次具名仍在末两卷（目标 ≤${ONSET_LATE_MAX}）：${late.join('、')}`)
  }
  notes.push(`F33 人物首现台账：${list.length} 人 · 末两卷首现 ${late.length}（目标 ≤${ONSET_LATE_MAX}）· 声明章已核 ${verified} · 待落 ${pending.length}`)
  return { entries: list.length, late: late.length, pending: pending.length, verified }
}

// ── ⑪ F35 在世窗口闭环（state/life-windows.json × 卷→年表 × 正文落点）──
//   凡档案声明了生年／卒年／命运节点的角色，其落点章换算出的年份必须落在在世窗口内：
//     ①落点年 < 生年 → 失败（任何载体）；
//     ②本人出场（kind 缺省 / in_person）而落点年 > min(卒年, 书末年) → 失败；
//     ③文书·名册·军报（document）与口述·转述·尸首（reported）＝ L0 载体，死后可续现，只受①约束；
//     ④跨年卷的落点建议自带 year；未标 year 时按“卷首年 > 卒年”判失败、卷末年越界仅警告；
//     ⑤volume_years 与 chronology.md §一 的卷表逐卷比对（年号或章范围不符即失败，该表未收录的卷只登记）。
//   与既有项分工：F32/F33 管“有没有出现”，F35 管“出现得是不是时候”。
const LIFE_L0 = new Set(['document', 'reported'])
function checkLifeWindows({ stateDir, targets, volumes, fail, warn, notes }) {
  const raw = read(path.join(stateDir, 'life-windows.json'))
  if (!raw) { notes.push('F35 在世窗口闭环：本书无 state/life-windows.json，规则不适用'); return null }
  let data
  try { data = JSON.parse(raw) } catch (e) {
    fail(`F35 在世窗口台账解析失败：${e.message}`)
    return null
  }
  const endYear = Number(data.book_end_year ?? 779)
  // 卷→年：chapters 形如 "237-260"
  const span = new Map()
  for (const v of data.volume_years || []) {
    const m = /^(\d+)\s*[-—–]\s*(\d+)$/.exec(String(v.chapters || '').trim())
    if (!m) continue
    const fy = Number(v.from); const ty = Number(v.to ?? v.from)
    for (let n = Number(m[1]); n <= Number(m[2]); n++) span.set(n, { from: fy, to: ty, vol: v.vol })
  }
  const ov = new Map(Object.entries(data.chapter_year_overrides || {}).map(([k, x]) => [Number(k), Number(x)]))
  const targetSet = new Set(targets)
  let judged = 0; let undated = 0; let upper = 0
  const lowerBad = []; const overBad = []; const softBad = []; const noSpan = []
  for (const p of data.people || []) {
    const ceil = p.death_year != null ? Math.min(Number(p.death_year), endYear) : endYear
    const floor = p.birth_year != null ? Number(p.birth_year) : null
    const steps = [
      ...(p.landed || []).map((x) => ({ ...x, phase: '已落' })),
      ...(p.planned || []).map((x) => ({ ...x, phase: '计划' })),
    ]
    // land_range：只登记“首现—末现”跨度的（无逐年落点）
    if (p.landed_range) {
      for (const k of ['first', 'last']) {
        if (p.landed_range[k] != null) steps.push({ chapter: p.landed_range[k], phase: `跨度·${k === 'first' ? '首' : '末'}` })
      }
    }
    for (const st of steps) {
      if (st.chapter == null) { upper += 1; continue }   // 只写卷次、未定章：由卷表另判
      const ch = Number(st.chapter)
      if (!targetSet.has(ch)) continue
      const s = span.get(ch)
      if (!s) { noSpan.push(`ch${ch}（${p.name}）`); continue }
      judged += 1
      const declared = st.year != null ? Number(st.year) : null
      const lo = declared ?? s.from
      const hi = declared ?? s.to
      const l0 = LIFE_L0.has(String(st.kind || 'in_person'))
      if (floor != null && lo < floor) {
        lowerBad.push(`${p.name} ch${ch}（${st.phase}${l0 ? '·载体' : ''}）→ ${lo} 年 < 生年 ${floor}`)
      } else if (!l0) {
        if (lo > ceil) {
          overBad.push(`${p.name} ch${ch}（${st.phase}）→ ${hi === lo ? `${lo} 年` : `${lo}—${hi} 年`} > 在世上限 ${ceil}`
            + `${p.death_year == null ? '（书末年）' : '（卒年）'}`)
        } else if (hi > ceil) {
          softBad.push(`${p.name} ch${ch}（${st.phase}）→ 卷末年 ${hi} 越上限 ${ceil}（跨年卷未标 year，仅警告）`)
        }
      }
    }
  }
  if (lowerBad.length) fail(`F35 落点早于生年（${lowerBad.length} 处）：${lowerBad.join('；')}`)
  if (overBad.length) fail(`F35 在世窗口越上限——本人在卒年之后仍被写成在场（${overBad.length} 处）：${overBad.join('；')}`
    + '　→ 要么改落点，要么把该处改成 document／reported 载体')
  if (softBad.length) warn(`F35 跨年卷落点未标 year（${softBad.length} 处，仅警告）：${softBad.join('；')}`)
  if (noSpan.length) {
    warn(`F35 落点章不在 volume_years 覆盖范围内，无法换算年份（${noSpan.length} 处）：${noSpan.join('、')}`)
  }
  // ⑤ volume_years ↔ chronology.md §一 卷表
  const chrono = read(path.join(stateDir, 'chronology.md'))
  let chronoVols = 0
  const mismatch = []
  const covered = new Set((data.volume_years || []).map((x) => Number(x.vol)))
  if (chrono) {
    for (const line of String(chrono).split(/\r?\n/)) {
      const m = /^\|\s*(十[一二三四]|[一二三四五六七八九十])\s*\|\s*ch(\d+)\s*[—–\-]\s*(\d+)\s*\|([^|]*)\|/.exec(line)
      if (!m) continue
      const vol = CN_NUM[m[1]]
      const v = (data.volume_years || []).find((x) => Number(x.vol) === vol)
      if (!v) { mismatch.push(`卷${vol} 见于 chronology 卷表、life-windows 未收录`); continue }
      chronoVols += 1
      const range = `${m[2]}-${m[3]}`
      if (String(v.chapters).replace(/\s/g, '') !== range) {
        mismatch.push(`卷${vol} 章范围不一致：chronology ch${m[2]}—${m[3]} vs life-windows ${v.chapters}`)
      }
      const ys = [...m[4].matchAll(/\d{3}/g)].map((x) => Number(x[0]))
      if (ys.length) {
        const cf = Math.min(...ys); const ct = Math.max(...ys)
        if (Number(v.from) !== cf || Number(v.to ?? v.from) !== ct) {
          mismatch.push(`卷${vol} 年号不一致：chronology ${cf}—${ct} vs life-windows ${v.from}—${v.to ?? v.from}`)
        }
      }
    }
    if (mismatch.length) fail(`F35 卷→年表与 chronology.md §一 不一致（${mismatch.length} 处）：${mismatch.join('；')}`)
  }
  const uncovered = (volumes || []).map((v) => v.vol).filter((vol) => !covered.has(vol))
  notes.push(`F35 在世窗口：${(data.people || []).length} 人 · 落点已判 ${judged} · 未来卷未定章 ${upper}`
    + ` · 窗口越界 ${overBad.length} · chronology 卷表比对 ${chronoVols} 卷`
    + (uncovered.length ? ` · 未覆盖卷：${uncovered.join('、')}` : ''))
  return { people: (data.people || []).length, judged, lowerBad: lowerBad.length,
    overBad: overBad.length, softBad: softBad.length, undated: upper, mismatch: mismatch.length }
}

// ── 单本检查 ────────────────────────────────────────────────────────
function checkBook(name) {
  const bookDir = path.join(BOOKS_DIR, name)
  const novelDir = path.join(bookDir, 'novel')
  const stateDir = path.join(bookDir, 'state')
  const title = bookTitle(bookDir)
  const mirror = path.join(PUBLIC_NOVELS, title)
  const failures = []
  const warnings = []
  const notes = []
  const fail = (m) => failures.push(m)
  const warn = (m) => warnings.push(m)

  if (!isDir(novelDir) || !isDir(stateDir)) return null
  if (!isDir(mirror)) {
    fail(`规范镜像缺失：public/novels/${title}/（先跑 npm run build 或 node scripts/sync.mjs）`)
    return { name, title, mirror, failures, warnings, notes, chapters: [], volumes: [], wordTotal: 0 }
  }

  const all = chapterFiles(novelDir)
  const allSet = new Set(all.map((c) => c.n))
  const allMap = new Map(all.map((c) => [c.n, c.file]))

  // —— ④ 卷纲声明（顺便得到卷/章范围）——
  const outlineFiles = fs.readdirSync(stateDir)
    .filter((f) => /^outline-vol(\d+)\.md$/.test(f))
    .sort((a, b) => Number(a.match(/\d+/)[0]) - Number(b.match(/\d+/)[0]))
  const volumes = [] // {vol, file, declared: {n:title}, min, max}
  for (const f of outlineFiles) {
    const vol = Number(f.match(/\d+/)[0])
    const declared = outlineDeclared(read(path.join(stateDir, f)))
    const ns = Object.keys(declared).map(Number)
    if (!ns.length) continue
    volumes.push({ vol, file: f, declared, min: Math.min(...ns), max: Math.max(...ns) })
  }
  const inVol = (n) => volumes.find((v) => n >= v.min && n <= v.max)

  // 章范围：--vol 指定时按其声明范围，否则全部
  let targets = all
  if (OPT.vol != null) {
    const v = volumes.find((x) => x.vol === OPT.vol)
    if (!v) {
      fail(`找不到 outline-vol${OPT.vol}.md 或其内无「第N章《…》」声明`)
      return { name, title, mirror, failures, warnings, notes, chapters: [], volumes, wordTotal: 0 }
    }
    targets = all.filter((c) => c.n >= v.min && c.n <= v.max).map((c) => c.n)
  } else {
    targets = all.map((c) => c.n)
  }

  // —— ④ 声明 ↔ 正文章题 ——
  // 「声明章缺正文」按警告处理：卷纲先声明后开写是本仓惯例（outline-vol12 等），只对已存在的正文校验章题
  const checkedVols = OPT.vol != null ? volumes.filter((v) => v.vol === OPT.vol) : volumes
  for (const v of checkedVols) {
    for (const [nStr, declTitle] of Object.entries(v.declared)) {
      const n = Number(nStr)
      const srcText = read(path.join(novelDir, `chapter-${n}.md`))
      if (srcText == null) {
        if (n <= allSet.size && !OPT.predecl) fail(`卷纲 ${v.file} 声明第${n}章《${declTitle}》，正文文件不存在`)
        else warn(`卷纲 ${v.file} 已声明第${n}章《${declTitle}》（正文未开写）`)
        continue
      }
      const actual = chapterTitle(srcText)
      if (actual == null) { fail(`第${n}章 正文首行缺「第N章《…》」章题`); continue }
      if (actual !== declTitle) fail(`第${n}章 章题不符：卷纲《${declTitle}》 vs 正文《${actual}》`)
    }
    const undeclared = targets.filter((n) => n >= v.min && n <= v.max && !(n in v.declared))
    if (undeclared.length) warn(`${v.file} 范围内未声明章：${undeclared.join('、')}`)
  }

  // —— ① 章节源 ↔ 镜像 md5 ——
  const chapters = []
  for (const n of targets) {
    if (!allSet.has(n)) { fail(`源缺 chapter-${n}.md`); continue }
    const file = allMap.get(n)
    const src = path.join(novelDir, file)
    const dst = path.join(mirror, 'chapters', file)
    if (!isFile(dst)) { fail(`镜像缺 ${file}`); continue }
    if (md5(src) !== md5(dst)) fail(`${file} 源↔镜像 md5 不一致`)
    const text = read(src) || ''
    const wc = wordCount(text)
    const vol = inVol(n)?.vol ?? null
    chapters.push({ n, title: chapterTitle(text), vol, chars: wc, under: OPT.min > 0 && wc < OPT.min })
  }
  // 字数口径台账：默认只登记警告；--strict 时升为失败
  const unders = chapters.filter((c) => c.under)
  if (unders.length) {
    const list = unders.slice(0, 24).map((c) => `ch${c.n}(${c.chars})`).join('、')
    const more = unders.length > 24 ? ` 等${unders.length}章` : ''
    const msg = `字数低于 ${OPT.min}：${list}${more}`
    if (OPT.strict) fail(msg)
    else warn(msg)
  }

  // —— ② state 源 ↔ 镜像 ——
  const stateFiles = fs.readdirSync(stateDir).filter((f) => f.endsWith('.md')).sort()
  for (const f of stateFiles) {
    const dst = path.join(mirror, 'state', f)
    if (!isFile(dst)) { fail(`state 镜像缺 ${f}`); continue }
    if (md5(path.join(stateDir, f)) !== md5(dst)) fail(`state/${f} 源↔镜像 md5 不一致`)
  }
  if (isDir(path.join(mirror, 'state'))) {
    const extra = fs.readdirSync(path.join(mirror, 'state'))
      .filter((f) => f.endsWith('.md') && !stateFiles.includes(f))
    if (extra.length) warn(`镜像 state 有源端已无的文件：${extra.join('、')}`)
  }
  // 结构化台账（脚本直接读的几份）同样按字节比对：改了台账忘了同步镜像，
  // 会让 F23/F33/F35 读的是旧账——这类漂移 .md 比对拦不住。
  const jsonLedgers = ['life-windows.json', 'custody-chains.json', 'character-onsets.json', 'word-budget.json']
  for (const f of jsonLedgers) {
    const src = path.join(stateDir, f)
    if (!isFile(src)) continue
    const dst = path.join(mirror, 'state', f)
    if (!isFile(dst)) { fail(`state 镜像缺 ${f}（重跑 node scripts/sync.mjs）`); continue }
    if (md5(src) !== md5(dst)) fail(`state/${f} 源↔镜像 md5 不一致`)
  }

  // —— ③ index.json 覆盖 ——
  const idxPath = path.join(mirror, 'index.json')
  if (!isFile(idxPath)) {
    fail('镜像缺 index.json')
  } else {
    let idx = null
    try { idx = JSON.parse(read(idxPath)) } catch { fail('index.json 不是合法 JSON') }
    if (idx) {
      const ids = new Set(idx.chapters || [])
      const missCh = all.filter((c) => !ids.has(c.file.replace(/\.md$/, ''))).map((c) => c.n)
      if (missCh.length) fail(`index.json 未列章：${missCh.join('、')}`)
      const idChapters = (idx.chapters || []).filter((c) => /^chapter-\d+$/.test(c))
      if (idChapters.length !== all.length) {
        warn(`index.json 章节数 ${idChapters.length} ≠ 源章数 ${all.length}`)
      }
      const extraIds = (idx.chapters || []).filter((c) => !/^chapter-\d+$/.test(c))
      if (extraIds.length) notes.push(`index.json 另含非正文章节：${extraIds.join('、')}（sync 按 publishable 收录 copyright/preface）`)
      const sf = new Set((idx.stateFiles || []).map((s) => `${s}.md`))
      const missSf = stateFiles.filter((f) => !sf.has(f))
      if (missSf.length) fail(`index.json stateFiles 未列：${missSf.join('、')}`)
      notes.push(`progress: stage=${idx.progress?.stage} currentChapter=${idx.progress?.currentChapter}/${idx.progress?.totalChapters}`)
    }
  }

  // —— ⑤ 卷纲声明 vs 镜像 index（台账台账对齐）——
  // 声明章若超出源范围（如卷纲先行），仅提示
  for (const v of checkedVols) {
    const beyond = Object.keys(v.declared).map(Number).filter((n) => !allSet.has(n) && n <= v.max)
    if (beyond.length) warn(`${v.file} 声明了尚无正文的章：${beyond.join('、')}`)
  }

  // —— ⑦ progress 台账语义（state/progress.md ↔ 实际章数；口径与 scripts/sync.mjs 一致）——
  // ①—⑤ 只比字节与覆盖，所以「ch284 写完而 progress.md 仍写当前章节 260」这类语义漂移
  // 以前拦不住（镜像 index.json 只是照抄 progress.md，抄错也“一致”）。此处补语义校验。
  {
    const progRaw = read(path.join(stateDir, 'progress.md'))
    if (progRaw == null) {
      warn('state/progress.md 不存在，跳过 progress 语义校验')
    } else {
      const pick = (re) => { const m = re.exec(progRaw); return m ? Number(m[1]) : null }
      const pStage = pick(/当前阶段[：:]\s*(\d+)/)
      const pCur = pick(/当前章节[：:]\s*(\d+)/)
      const pTotal = pick(/总章节数[：:]\s*(\d+)/)
      const actualMax = all.length ? Math.max(...all.map((c) => c.n)) : 0
      const actualCount = all.length
      if (pCur == null) {
        warn('progress.md 无「当前章节：N」字段，跳过 progress 语义校验（sync.mjs 同样读不到该字段）')
      } else {
        if (pCur !== actualMax) {
          fail(`progress.md 当前章节=${pCur} ≠ 正文实际最大章号 ${actualMax}（台账滞后：改 progress.md 后重跑 npm run build）`)
        }
        if (pTotal != null && pCur > pTotal) {
          fail(`progress.md 当前章节=${pCur} 超过总章节数=${pTotal}`)
        }
        if (actualCount !== actualMax) {
          warn(`正文章号不连续：${actualCount} 个章节文件，最大章号 ${actualMax}`)
        }
        let idxCur = null
        try { idxCur = JSON.parse(read(idxPath))?.progress?.currentChapter ?? null } catch { /* ③ 已报 */ }
        if (idxCur != null && idxCur !== pCur) {
          fail(`镜像 index.json 当前章节=${idxCur} ≠ progress.md 当前章节=${pCur}（重跑 npm run build）`)
        }
        notes.push(`progress 语义: 当前章节 ${pCur}/${pTotal ?? '?'} · 阶段 ${pStage ?? '?'} · 实际章数 ${actualCount}`)
      }
    }
  }

  // —— ⑥ F23 跨章物件持有链（state/custody-chains.json）——
  const declaredChapterNumbers = new Set(volumes.flatMap((v) => Object.keys(v.declared).map(Number)))
  const custody = checkCustodyChains({
    stateDir, novelDir, targets, allMap, declaredChapterNumbers, fail, warn, notes,
  }) || { chains: 0, steps: 0 }

  // —— ⑧ F31 人物卡排期闭环（state/characters.md × 卷十三/十四卷纲 × appearance-plan.md）——
  const cards = checkCharacterCards({ stateDir, fail, warn, notes })

  // —— ⑨ F32 双榜席位首现闭环（state/rankings.md × 正文 × appearance-plan.md §14.3）——
  const seats = checkSeatOnsets({ stateDir, novelDir, allMap, fail, warn, notes })

  // —— ⑩ F33 人物首现台账闭环（state/character-onsets.json × 正文）——
  const onsets = checkOnsetLedger({ stateDir, novelDir, allMap, fail, warn, notes })

  // —— ⑪ F35 在世窗口闭环（state/life-windows.json × 卷→年表 × 正文落点）——
  const windows = checkLifeWindows({ stateDir, targets, volumes, fail, warn, notes })

  const wordTotal = chapters.reduce((s, c) => s + c.chars, 0)
  return { name, title, mirror, failures, warnings, notes, chapters, volumes, wordTotal, custody, cards, seats, onsets, windows }
}

// ── dedup 输出解析：判失败项 / 存量报告 / 信息项 三档 ──────────────
// dedup-check.py 对「新规则自某章起」的历史章节打 `  [F3·…] (存量, 仅报告)` + `    × …`。
// 只看以 × 开头的行会同时丢掉 section 头（丢了「存量」标签与章号），故按 section 头分类：
//   缩进 4 空格的 × / • 行归属其上方最近的 section 头：
//     section 含「存量」        → 存量报告（历史存稿的规则命中，按设计不判失败）
//     section 含「仅报告」或 • 行 → 信息项（如 B类「受控呼应（需登记）」清单、卷级词频报告）
//     其余（顶层 F20S 自审块、带 ✗ 的 F22 字数行）→ 判失败
function parseDedupOutput(stdout) {
  const failures = []
  const legacy = []
  const info = []
  let ch = null
  let sec = ''
  let mode = 'fail'   // 'fail' | 'legacy' | 'info'
  for (const raw of String(stdout || '').split('\n')) {
    const line = raw.replace(/\s+$/, '')
    if (!line.trim()) continue
    const mCh = /^===\s*第(\d+)章\s*===/.exec(line.trim())
    if (mCh) { ch = Number(mCh[1]); sec = ''; mode = 'fail'; continue }
    const mSec = /^\s*\[([^\]]+)\]\s*(.*)$/.exec(line)
    if (mSec) {
      sec = mSec[1].trim()
      const rest = (mSec[2] || '').trim()
      const hasLegacy = /存量/.test(sec) || /存量/.test(rest)
      const hasInfo = /仅报告/.test(sec) || /仅报告/.test(rest)
      mode = hasLegacy ? 'legacy' : (hasInfo ? 'info' : 'fail')
      // section 头自带正文（如 [F12·存量报告] 命中 7 次）才算一条记录；
      // 纯标签型（rest 只剩「(存量, 仅报告)」）不计，由随后的 × 行计数。
      const restClean = rest
        .replace(/[（(][^）)]*(?:存量|仅报告)[^）)]*[）)]/g, '')
        .replace(/存量|仅报告/g, '')
        .replace(/[，,、\s]/g, '')
      const rec = { ch, rule: sec.split('·')[0], sec, text: `${sec} ${rest}` }
      if (restClean && mode === 'legacy') legacy.push(rec)
      else if (restClean && mode === 'info') info.push(rec)
      else if (mode === 'fail' && /✗|失败|未声明/.test(rest)) failures.push(rec)
      continue
    }
    const mHit = /^\s*([×✗•])\s*(.*)$/.exec(line)
    if (!mHit) continue
    const rec = { ch, rule: sec.split('·')[0] || '未归类', sec, text: mHit[2].trim() }
    if (mHit[1] === '•' || mode === 'info') info.push(rec)
    else if (mode === 'legacy') legacy.push(rec)
    else failures.push(rec)
  }
  return { failures, legacy, info }
}

/** 按规则标签归组，多的在前（标签取 section 头「·」前一段，如 F3·高频意象超频 → F3）。 */
function groupByRule(records) {
  const m = new Map()
  for (const x of records) {
    if (!m.has(x.rule)) m.set(x.rule, [])
    m.get(x.rule).push(x)
  }
  return [...m].sort((a, b) => b[1].length - a[1].length)
}

/** [1,2,3,5] → "ch1—3、ch5"；连续段数超过 max 时截断。 */
function fmtRanges(nums, max = 10) {
  const a = [...new Set(nums)].filter((n) => n != null).sort((x, y) => x - y)
  const segs = []
  for (let i = 0; i < a.length;) {
    let j = i
    while (j + 1 < a.length && a[j + 1] === a[j] + 1) j += 1
    segs.push(i === j ? `ch${a[i]}` : `ch${a[i]}—${a[j]}`)
    i = j + 1
  }
  return segs.length <= max ? segs.join('、') : `${segs.slice(0, max).join('、')}…（另 ${segs.length - max} 段）`
}

// ── 主流程 ──────────────────────────────────────────────────────────
const allBooks = fs.existsSync(BOOKS_DIR)
  ? fs.readdirSync(BOOKS_DIR).filter((d) => {
      const p = path.join(BOOKS_DIR, d)
      return isDir(p) && isDir(path.join(p, 'novel')) && isDir(path.join(p, 'state'))
    })
  : []
const books = OPT.book ? allBooks.filter((b) => b === OPT.book) : allBooks
if (OPT.book && !books.length) {
  console.error(`找不到书目：${OPT.book}`)
  process.exit(1)
}

const report = { root: ROOT, min: OPT.min, vol: OPT.vol, books: [], failures: 0, warnings: 0, dedup: [] }

for (const b of books) {
  const r = checkBook(b)
  if (!r) continue
  report.books.push(r)
  report.failures += r.failures.length
  report.warnings += r.warnings.length

  if (!OPT.json && !OPT.quiet) {
    console.log(`\n════ ${r.name}（镜像 public/novels/${r.title}/）`)
    // 字数台账
    const vols = OPT.vol != null ? [OPT.vol] : [...new Set(r.volumes.map((v) => v.vol))]
    if (r.chapters.length) {
      if (vols.length) {
        for (const v of vols) {
          const cs = r.chapters.filter((c) => c.vol === v)
          if (!cs.length) continue
          const sum = cs.reduce((s, c) => s + c.chars, 0)
          console.log(`\n  卷${v}｜${cs.length} 章，合计 ${sum} 字，均 ${Math.round(sum / cs.length)} 字/章`)
          for (let i = 0; i < cs.length; i += 8) {
            console.log('    ' + cs.slice(i, i + 8)
              .map((c) => `ch${c.n} ${c.chars}${c.under ? ' ✗' : ''}`).join('  '))
          }
        }
      }
      console.log(`\n  全书已检 ${r.chapters.length} 章，合计 ${r.wordTotal} 字，均 ${Math.round(r.wordTotal / r.chapters.length)} 字/章`)
    }
    if (r.custody?.chains) {
      const ok = r.failures.every((f) => !f.startsWith('F23'))
      console.log(`\n  F23 跨章持有链：${r.custody.chains} 条 / ${r.custody.steps} 步 ${ok ? '✓' : '✗'}`)
    }
    if (r.cards) {
      console.log(`  F31 人物卡排期闭环：${r.cards.cards} 张 / 未分类 ${r.cards.unclassified} ${r.cards.unclassified ? '✗' : '✓'}`)
      if (r.seats && r.seats.seats) {
        console.log(`  F32 双榜席位首现闭环：${r.seats.seats} 席 / 未闭环 ${r.seats.unclosed.length} ${r.seats.unclosed.length ? '✗' : '✓'}　· 正文 ≤1 章者 ${r.seats.thin}（目标 ≤6）`)
      }
      if (r.onsets) {
        console.log(`  F33 人物首现台账：${r.onsets.entries} 人 · 末两卷首现 ${r.onsets.late}（目标 ≤10）${r.onsets.late > 10 ? ' ✗' : ' ✓'} · 声明章已核 ${r.onsets.verified} · 待落 ${r.onsets.pending}`)
      }
    }
    if (r.windows) {
      const bad = r.windows.overBad + r.windows.lowerBad + r.windows.mismatch
      console.log(`  F35 在世窗口闭环：${r.windows.people} 人 / 落点已判 ${r.windows.judged} ${bad ? '✗' : '✓'}`
        + `　· 越上限 ${r.windows.overBad} · 早于生年 ${r.windows.lowerBad} · 卷表不符 ${r.windows.mismatch}`)
    }
    for (const n of r.notes) console.log(`  · ${n}`)
    for (const w of r.warnings) console.log(`  ! 警告 ${w}`)
    for (const f of r.failures) console.log(`  ✗ ${f}`)
    if (!r.failures.length) console.log('  ✓ 源／镜像／台账 一致')
  }
}

// ── 可选：调用各书 dedup-check ──────────────────────────────────────
if (OPT.dedup) {
  for (const r of report.books) {
    const bookDir = path.join(BOOKS_DIR, r.name)
    const script = path.join(bookDir, 'state', 'dedup-check.py')
    if (!isFile(script)) continue
    const nums = r.chapters.map((c) => c.n)
    if (!nums.length) continue
    const res = spawnSync(OPT.python, [script, ...nums.map(String)], {
      cwd: ROOT, encoding: 'utf8', env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    })
    const { failures, legacy, info } = parseDedupOutput(res.stdout)
    const ok = res.status === 0 && failures.length === 0
    report.dedup.push({ book: r.name, chapters: nums.length, ok, status: res.status,
      failures: failures.length, legacy: legacy.length, info: info.length })
    if (!ok) report.failures += 1
    if (!OPT.json && !OPT.quiet) {
      console.log(`\n════ ${r.name}｜dedup-check.py（${nums.length} 章）`)
      if (res.error) {
        console.log(`  ✗ 无法调用 ${OPT.python}：${res.error.message}`)
      } else if (failures.length) {
        for (const f of failures) console.log(`  ✗ ${f.ch != null ? `ch${f.ch} ` : ''}${f.text}`)
      } else if (!ok) {
        console.log(`  ✗ dedup-check.py 退出码 ${res.status}，但未解析出失败行——请单独跑该脚本看原始输出`)
      } else {
        console.log('  ✓ 无判失败项')
      }
      if (legacy.length) {
        const legacyChs = legacy.map((x) => x.ch).filter((n) => n != null)
        console.log(`  · 存量报告 ${legacy.length} 处 · ${new Set(legacyChs).size} 章`
          + '——规则前章段，按设计仅报告、不判失败')
        for (const [rule, list] of groupByRule(legacy)) {
          const chs = list.map((x) => x.ch)
          console.log(`      ${rule}｜${new Set(chs.filter((n) => n != null)).size} 章 / ${list.length} 处`
            + `　${fmtRanges(chs)}`)
        }
        if (OPT.legacy) {
          for (const x of legacy) console.log(`      ch${x.ch != null ? x.ch : '-'} ${x.sec} → ${x.text}`)
        } else {
          console.log('      逐条详单：npm run verify -- --legacy')
        }
      }
      if (info.length) {
        const chs = info.map((x) => x.ch).filter((n) => n != null)
        console.log(`  · 信息项（非命中、不计失败）：${info.length} 处 · ${new Set(chs).size} 章　`
          + groupByRule(info).map(([r, l]) => `${r} ${l.length}`).join('、'))
      }
    }
  }
}

if (OPT.json) console.log(JSON.stringify(report, null, 2))
else {
  const pass = report.failures === 0
  const legacyTotal = report.dedup.reduce((s, d) => s + (d.legacy || 0), 0)
  console.log(`\n──────────────────────────────────────────`)
  console.log(pass
    ? `✓ 一致性终检通过：${report.books.length} 本，${report.books.reduce((s, b) => s + b.chapters.length, 0)} 章`
    : `✗ 一致性终检失败：${report.failures} 项失败，${report.warnings} 项警告`)
  if (pass && legacyTotal) {
    console.log(`  （另有 ${legacyTotal} 处 dedup 存量报告，全在各规则判失败起点之前的章段，不影响通过；`
      + '逐条详单：npm run verify -- --legacy）')
  }
}
process.exit(report.failures === 0 ? 0 : 1)
