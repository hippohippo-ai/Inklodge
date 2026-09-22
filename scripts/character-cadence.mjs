#!/usr/bin/env node
/**
 * 人物节奏扫描（只报不改）——为「人物可以出场少，但不要隔上百章才出现一次名字，
 * 也不要在末两卷集中出现一堆人物」这条口径提供可复核的数字。
 *
 * 用法：
 *   node scripts/character-cadence.mjs --book 天阙
 *   node scripts/character-cadence.mjs --book 天阙 --max-gap 100 --tail 100
 *   node scripts/character-cadence.mjs --book 天阙 --json
 *   node scripts/character-cadence.mjs --book 天阙 --fail-on-violation   # 需要闸门时用
 *
 * 名单来源（缺哪个就跳过哪个，不报错）：state/rankings.md（三榜单）、
 * state/characters.md（人物卡标题）、state/character-onsets.json（前移台账）。
 * 计数口径：按「名字字面」在小说正文 chapter-N.md 中出现统计——章数、段数、
 * 相邻两次出现之间的最大空窗（章）、末次出现距正文最大章号的距离（章）。
 */
import fs from 'node:fs';
import path from 'node:path';

const argv = process.argv.slice(2);
const flag = (name, def = null) => {
  const i = argv.indexOf(`--${name}`);
  if (i === -1) return def;
  const v = argv[i + 1];
  return v && !v.startsWith('--') ? v : true;
};
const BOOK = flag('book');
const MAX_GAP = Number(flag('max-gap', 100));
const TAIL = Number(flag('tail', 100));
const AS_JSON = argv.includes('--json');
const FAIL = argv.includes('--fail-on-violation');

if (!BOOK || BOOK === true) {
  console.error('用法: node scripts/character-cadence.mjs --book <书名> [--max-gap 100] [--tail 100] [--json] [--fail-on-violation]');
  process.exit(2);
}
const bookDir = path.join('books', BOOK);
const stateDir = path.join(bookDir, 'state');
const novelDir = path.join(bookDir, 'novel');
if (!fs.existsSync(novelDir)) { console.error(`找不到 ${novelDir}`); process.exit(2); }

const readIf = (p) => (fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : null);

// ---- 名单 ----
const roster = new Map();
const add = (name, group) => {
  const n = String(name || '').trim();
  if (!n || n.length < 2 || n.length > 6) return;
  if (!roster.has(n)) roster.set(n, { name: n, groups: new Set() });
  roster.get(n).groups.add(group);
};
const NOT_PERSON = /藩镇|军$|卫$|帮$|派$|传人|补档|追缉线|活人|边镇|史实人物|新增|同步纪律|群像|矩阵|规则|口径|纪律|写法|^附|^卷[一二三四五六七八九十]|共\d|势力|组织/;

const rank = readIf(path.join(stateDir, 'rankings.md'));
if (rank) {
  for (const m of rank.matchAll(/^\|\s*[一二三四五六七八九十]+\s*\|\s*([^|*]+?)\s*\|\s*\d+\s*\|/gm)) add(m[1], '宗师录');
  for (const m of rank.matchAll(/^\|\s*\*\*第[一二三四五六七八九十]+\*\*\s*\|\s*([^|]+?)\s*\|/gm)) add(m[1], '黑榜');
  const bax = rank.split('## 三、八凶')[1] || '';
  for (const m of bax.matchAll(/^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|/gm)) {
    const t = m[1].trim(); if (t === '称号' || /^-+$/.test(t)) continue;
    add(m[2].includes('·') ? m[2].split('·').pop() : m[2], '八凶');
  }
}
const cards = readIf(path.join(stateDir, 'characters.md'));
if (cards) {
  for (const m of cards.matchAll(/^#{3,4}\s+(.+)$/gm)) {
    let h = m[1].trim().replace(/^附：/, '');
    let name = h.split(/[（(——]/)[0].replace(/^[\d.、]+\s*/, '').replace(/^[a-c]\.\s*/, '').replace(/["“”]/g, '').trim();
    if (name.includes('·')) name = name.split('·').pop().trim();
    if (!name || NOT_PERSON.test(name)) continue;
    add(name, '人物卡');
  }
}
const onsetsRaw = readIf(path.join(stateDir, 'character-onsets.json'));
if (onsetsRaw) {
  try {
    const d = JSON.parse(onsetsRaw);
    const list = Array.isArray(d) ? d : (d.characters || d.list || []);
    for (const c of list) add(c.name, '前移台账');
  } catch { /* 台账坏了由别处报 */ }
}
// 别名：正文里常用简称
const ALIAS = { 明空老人: ['明空'], 守真真人: ['守真'], 重辉真人: ['重辉'], 澹台孤鹤: ['澹台'], 天鼓和尚: ['天鼓'] };
// 已知的假命中（别名撞到普通词语）：命中行含这些串时不计
const NEG = { 明空老人: ['明空栏', '写明空'], 澹台孤鹤: ['澹台山'] };

// ---- 正文 ----
const chapters = fs.readdirSync(novelDir)
  .filter((f) => /^chapter-\d+\.md$/.test(f))
  .map((f) => ({ f, n: Number(f.match(/\d+/)[0]) }))
  .sort((a, b) => a.n - b.n);
const MAXN = chapters.length ? Math.max(...chapters.map((c) => c.n)) : 0;

const rows = [];
for (const { name, groups } of roster.values()) {
  const pats = [name, ...(ALIAS[name] || [])];
  const hitCh = [];
  let paras = 0;
  for (const { f, n } of chapters) {
    const text = fs.readFileSync(path.join(novelDir, f), 'utf8');
    const lines = text.split(/\r?\n/).filter((l) => l.trim());
    const negs = NEG[name] || [];
    const hits = lines.filter((l) => pats.some((p) => l.includes(p)) && !negs.some((x) => l.includes(x))).length;
    if (hits) { hitCh.push(n); paras += hits; }
  }
  if (!hitCh.length) {
    rows.push({ name, groups: [...groups].join('/'), chapters: 0, paras: 0, first: null, last: null, maxGap: null, tailGap: null, chList: [] });
    continue;
  }
  let maxGap = hitCh[0] - (hitCh[0] === 1 ? 0 : hitCh[0] - 1); // 首现前的空窗不计入
  maxGap = 0;
  for (let i = 1; i < hitCh.length; i++) maxGap = Math.max(maxGap, hitCh[i] - hitCh[i - 1]);
  rows.push({
    name, groups: [...groups].join('/'), chapters: hitCh.length, paras,
    first: hitCh[0], last: hitCh[hitCh.length - 1],
    maxGap, tailGap: MAXN - hitCh[hitCh.length - 1], chList: hitCh,
  });
}

const gapViolations = rows.filter((r) => r.maxGap != null && r.maxGap >= MAX_GAP).sort((a, b) => b.maxGap - a.maxGap);
const tailViolations = rows.filter((r) => r.tailGap != null && r.tailGap >= TAIL).sort((a, b) => b.tailGap - a.tailGap);
const zero = rows.filter((r) => r.chapters === 0);

// ---- 棘轮基线（T-F4：闸门只紧不松）----
// 存量违规记入 state/cadence-baseline.json；此后：新出现违规、或某人空窗/断线比基线更长，都判失败。
// 用法：npm run cadence:save 一次性把当前违规面写进基线；npm run cadence:check（verify 内置）做闸门。
const SAVE_BASE = argv.includes('--save-baseline');
const BASE_PATH = path.join(stateDir, 'cadence-baseline.json');
const gapMap = Object.fromEntries(gapViolations.map((r) => [r.name, r.maxGap]));
const tailMap = Object.fromEntries(tailViolations.map((r) => [r.name, r.tailGap]));
if (SAVE_BASE) {
  const base = {
    _note: 'cadence 棘轮基线（同 F27「只紧不松」）：记录存量违规；新违规或空窗/断线变长都会被 --fail-on-violation 拦下。修好一处就重跑 --save-baseline 刷新。',
    savedAt: new Date().toISOString().slice(0, 10),
    maxGap: MAX_GAP,
    tail: TAIL,
    gaps: gapMap,
    tails: tailMap,
  };
  fs.writeFileSync(BASE_PATH, JSON.stringify(base, null, 1) + '\n');
  console.log(`\n✓ 基线已写入 ${BASE_PATH}（空窗 ${Object.keys(gapMap).length} 人／断线 ${Object.keys(tailMap).length} 人）`);
}
const newViolations = [];
if (FAIL) {
  let base = null;
  try { base = JSON.parse(fs.readFileSync(BASE_PATH, 'utf8')); } catch { base = null; }
  const hasBase = !!(base && base.gaps && base.tails);
  for (const r of gapViolations) {
    const prev = hasBase ? base.gaps[r.name] : undefined;
    if (prev === undefined) newViolations.push(`空窗·新违规：${r.name}（maxGap ${r.maxGap}${hasBase ? '，基线无记录' : '，无基线'}）`);
    else if (r.maxGap > prev) newViolations.push(`空窗·恶化：${r.name}（${prev} → ${r.maxGap}）`);
  }
  for (const r of tailViolations) {
    const prev = hasBase ? base.tails[r.name] : undefined;
    if (prev === undefined) newViolations.push(`断线·新违规：${r.name}（tailGap ${r.tailGap}${hasBase ? '，基线无记录' : '，无基线'}）`);
    else if (r.tailGap > prev) newViolations.push(`断线·恶化：${r.name}（${prev} → ${r.tailGap}）`);
  }
  if (newViolations.length) {
    console.log(`\n✗ cadence 闸门（棘轮只紧不松）：${newViolations.length} 处违规`);
    for (const s of newViolations) console.log('  - ' + s);
    console.log('  处置：存量既成事实→ npm run cadence:save 刷新基线；新稿违规→ 补落点或登记豁免。');
  } else {
    console.log('\n✓ cadence 闸门通过：无新增违规，存量均在基线内（棘轮只紧不松）。');
  }
}

if (AS_JSON) {
  console.log(JSON.stringify({ book: BOOK, maxChapter: MAXN, maxGap: MAX_GAP, tail: TAIL, rows, gapViolations, tailViolations }, null, 2));
} else {
  console.log(`════ ${BOOK}｜人物节奏（正文最大章号 ${MAXN}｜空窗阈值 ${MAX_GAP} 章｜断线阈值 ${TAIL} 章）`);
  console.log(`名单 ${rows.length} 人 · 零出场 ${zero.length} · 有空窗记录 ${rows.filter((r) => r.chapters > 1).length}`);

  console.log(`\n⚠ 相邻两次出现间隔 ≥${MAX_GAP} 章（${gapViolations.length} 人）`);
  console.log('| 人物 | 名单 | 章数 | 段数 | 首现 | 末现 | 最大空窗 | 末现距末尾 |');
  console.log('|---|---|---:|---:|---:|---:|---:|---:|');
  for (const r of gapViolations) console.log(`| ${r.name} | ${r.groups} | ${r.chapters} | ${r.paras} | ${r.first} | ${r.last} | ${r.maxGap} | ${r.tailGap} |`);

  console.log(`\n⚠ 末次出现距正文末尾 ≥${TAIL} 章（${tailViolations.length} 人）`);
  console.log('| 人物 | 名单 | 章数 | 段数 | 首现 | 末现 | 最大空窗 | 末现距末尾 |');
  console.log('|---|---|---:|---:|---:|---:|---:|---:|');
  for (const r of tailViolations) console.log(`| ${r.name} | ${r.groups} | ${r.chapters} | ${r.paras} | ${r.first} | ${r.last} | ${r.maxGap} | ${r.tailGap} |`);

  if (zero.length) console.log(`\n· 零出场（${zero.length} 人）：${zero.map((r) => r.name).join('、')}`);
  console.log('\n说明：本工具只报告、不改稿；空窗＝同一人物相邻两次具名出现之间的章数差。');
}

if (FAIL && newViolations.length) process.exit(1);
