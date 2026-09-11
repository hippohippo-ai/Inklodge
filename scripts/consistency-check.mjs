#!/usr/bin/env node
// 一致性终检：源（books/<书名>/novel|state/）↔ 站点镜像（public/novels/<书名>/）↔ 台账（卷纲声明/字数口径）
//
// 用途：每卷收尾一键跑，替代此前手工做的三向比对。
// 检查项：
//   ① 章节源↔镜像 md5 逐字节一致（缺文件/内容不同即失败）
//   ② state/*.md 源↔镜像一致，镜像多余文件单列警告
//   ③ index.json 覆盖（chapters 列全、stateFiles 列全、与源数量一致）
//   ④ 卷纲章题声明 vs 正文 H1 章题一致（声明章缺正文、章题不符即失败）
//   ⑤ 字数口径台账（去章题行与 Unicode 空白，与 state/dedup-check.py 同口径），
//      单章低于 --min 默认只登记警告；加 --strict 升为失败（卷收尾用）
//   ⑥ F23 跨章物件持有链（台账 state/custody-chains.json）：同一件物证在两次出现的章节间
//      交接/分拆是否自洽——A 每步须命中持有锚点；B 易主须有交接词；C 分拆/归档后再以整体出现即报错。
//      （编号说明：state/dedup-check.py 的 F21 = 同章物件去向互斥、F22 = 单章字数口径；
//        跨章这一层在一致脚本里编为 F23，避免与既有编号冲突。）
//
// 用法：
//   node scripts/consistency-check.mjs                              # 全部书目、全部卷
//   node scripts/consistency-check.mjs --book 天阙 --vol 11          # 只查天阙卷十一（ch237—260）
//   node scripts/consistency-check.mjs --book 天阙 --vol 12 --strict # 卷收尾：字数也判失败
//   node scripts/consistency-check.mjs --book 天阙 --vol 11 --dedup  # 顺带跑 state/dedup-check.py
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
  python: flag('python', 'python'),
  json: argv.includes('--json'),
  quiet: argv.includes('--quiet'),
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

function checkCustodyChains({ stateDir, novelDir, targets, allMap, fail, warn, notes }) {
  const { chains, error } = loadCustodyChains(stateDir)
  if (!chains.length && !error) return null
  if (error) { fail(error); return null }

  const allSet = new Set(allMap.keys())
  const textOf = (n) => (allMap.has(n) ? read(path.join(novelDir, allMap.get(n))) || '' : '')
  const inRange = new Set(targets)
  let steps = 0
  const skipped = []

  for (const chain of chains) {
    const id = chain.id || '(未命名链)'
    const list = Array.isArray(chain.steps) ? chain.steps : []
    const active = []
    for (const st of list) {
      const n = Number(st.ch)
      if (!Number.isFinite(n)) { fail(`F23 链「${id}」有非法章号：${st.ch}`); continue }
      if (!allSet.has(n)) { fail(`F23 链「${id}」登记的章不存在：ch${n}`); continue }
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
  return { chains: chains.length, steps }
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
  const checkedVols = OPT.vol != null ? volumes.filter((v) => v.vol === OPT.vol) : volumes
  for (const v of checkedVols) {
    for (const [nStr, declTitle] of Object.entries(v.declared)) {
      const n = Number(nStr)
      const srcText = read(path.join(novelDir, `chapter-${n}.md`))
      if (srcText == null) { fail(`卷纲 ${v.file} 声明第${n}章《${declTitle}》，正文文件不存在`); continue }
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

  // —— ⑥ F23 跨章物件持有链（state/custody-chains.json）——
  const custody = checkCustodyChains({
    stateDir, novelDir, targets, allMap, fail, warn, notes,
  }) || { chains: 0, steps: 0 }

  const wordTotal = chapters.reduce((s, c) => s + c.chars, 0)
  return { name, title, mirror, failures, warnings, notes, chapters, volumes, wordTotal, custody }
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
    const ok = res.status === 0
    report.dedup.push({ book: r.name, chapters: nums.length, ok, status: res.status })
    if (!ok) report.failures += 1
    if (!OPT.json && !OPT.quiet) {
      console.log(`\n════ ${r.name}｜dedup-check.py（${nums.length} 章）`)
      const lines = (res.stdout || '').trim().split('\n')
      const hits = lines.filter((l) => /^\s*[×✗]|失败|未声明/.test(l))
      console.log(hits.length ? hits.map((l) => '  ' + l.trim()).join('\n') : '  ✓ 全部通过')
      if (res.error) console.log(`  ✗ 无法调用 ${OPT.python}：${res.error.message}`)
    }
  }
}

if (OPT.json) console.log(JSON.stringify(report, null, 2))
else {
  const pass = report.failures === 0
  console.log(`\n──────────────────────────────────────────`)
  console.log(pass
    ? `✓ 一致性终检通过：${report.books.length} 本，${report.books.reduce((s, b) => s + b.chapters.length, 0)} 章`
    : `✗ 一致性终检失败：${report.failures} 项失败，${report.warnings} 项警告`)
}
process.exit(report.failures === 0 ? 0 : 1)
