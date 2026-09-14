#!/usr/bin/env node
/**
 * coalesce-paragraphs.mjs —— 段落合并（治「一句一段」的碎片化）
 *
 * 背景：2026-09-14 全书审阅发现卷十—十二段落碎片化回到开卷水平
 * （卷十一均段 29 字 / <20字段落占 61%，卷十二均段 25 字 / 64%，
 *   而卷三—卷九叙述段均段 48—69 字 / <20字 13—32%）。
 * 本工具把相邻段落合并回长段，**只动段落边界，不改一个字**：
 * 合并后的段落文本 = 相邻段落原文直接相接。
 *
 * 安全规则（三条，均为「不可能改变说话人归属」的判据）：
 *   M1 叙述段 + 叙述段：缓冲未达 --target 时合并。无歧义。
 *   M2 引号段 + 叙述段：仅当 ①引号段自带归属（收尾引号后有文字，如
 *      「…」某某说。），且 ②后续叙述段不含归属动词（说/道/问/答/喊/
 *      叫/喝/应/念）时才合并——两条同时成立，后句才不可能被读成
 *      「给前一句对白指派了说话人」。
 *   M3 引号段 + 引号段：一律不合并（无法机械判定是否同一说话人，
 *      误并会把 A 的台词挂到 B 名下）。这是本工具的能力边界：
 *      单行对白的碎片化属文本层面，须逐章改写，不能靠脚本。
 * 另有 M0：叙述段以「：」结尾 + 紧跟引号段 → 合并（冒号已明确引入对白）。
 *
 * 护栏 D1（文档式引文块）：跨段引文（某段以「“」开头、段内无收尾「”」，
 *   直到后面某段才出现收尾）整块不参与合并——书信／公文／名单在本项目里
 *   是逐行排版的实物，合并会把行结构抹掉（例：ch18 裴弘度军令三行）。
 *
 * 用法：
 *   node scripts/coalesce-paragraphs.mjs --book 天阙 --from 219 --to 284 --dry
 *   node scripts/coalesce-paragraphs.mjs --book 天阙 --from 219 --to 284
 * 选项：
 *   --dry            只统计与抽样，不写文件
 *   --target N       叙述段合并目标长度（默认 110）
 *   --sample N       抽样打印 N 个合并结果（默认 8）
 */
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const has = (k) => args.includes(k);

const BOOK = opt('--book', '天阙');
const FROM = Number(opt('--from', 219));
const TO = Number(opt('--to', 284));
const TARGET = Number(opt('--target', 110));
const DRY = has('--dry');
const SAMPLE = Number(opt('--sample', 8));

const ROOT = path.resolve(import.meta.dirname, '..');
const NOVEL = path.join(ROOT, 'books', BOOK, 'novel');

const wc = (s) => s.replace(/\s/g, '').length;
const isQuote = (p) => p.startsWith('“');
const ATTR_VERB = /[说道问答喊叫喝应念]/;
/** 引号段自带归属：收尾引号后仍有文字（“…”某某说。 / “…”他点了一下头。） */
const hasOwnAttribution = (p) => {
  const last = p.lastIndexOf('”');
  return last >= 0 && p.slice(last + 1).trim().length > 0;
};

/** 场景跳行：短且为时间/地点转换标记，保留独立段（合并会抹掉转场拍） */
const SCENE_SHIFT = /^(?:同一夜|次日|第二天|当夜|夜裏|夜里|入夜|天亮|天明|后半夜|半月|数日后|三日后|晌午|午后|清晨|傍晚|[一二三四五六七八九十]{1,3}月|[0-9]{3,4}年)/;
const isProtected = (p) => wc(p) <= 16 && SCENE_SHIFT.test(p);

/** D1 护栏：跨段引文块的段落下标集合（含开引号段、中间段与收尾段）。
 *  判据：某段以「“」开头且段内无「”」，后续直到出现「”」的段落全部属于同块。 */
function quoteBlockIdx(paras) {
  const inBlock = new Set();
  let i = 0;
  while (i < paras.length) {
    const p = paras[i];
    if (p.startsWith('“') && !p.includes('”')) {
      let j = i + 1;
      while (j < paras.length && !paras[j].includes('”')) j++;
      if (j < paras.length) {           // 只有真正闭合的跨段引文才成块
        for (let k = i; k <= j; k++) inBlock.add(k);
        i = j + 1;
        continue;
      }
    }
    i++;
  }
  return inBlock;
}

function coalesce(paras, target) {
  const out = [];
  const merges = [];
  const last = paras.length - 1;
  const dqBlock = quoteBlockIdx(paras);
  for (let i = 0; i < paras.length; i++) {
    const p = paras[i];
    // D1: i 或 i-1 落在跨段引文块内 → 不合并（out[-1] 恒以原文第 i-1 段结尾）
    if (out.length && i !== last && !isProtected(p) && !dqBlock.has(i) && !dqBlock.has(i - 1)) {
      const prev = out[out.length - 1];
      const pq = isQuote(prev), cq = isQuote(p);
      const pl = wc(prev);
      // 护栏：待并入的段里含无归属动词的引语时，前一段的主语可能被读成该引语的说话人
      // （例：『老吏把册子推回去。』⧺『他停了一下。“我不知道。”』→ “他”被回指成老吏）。此类不并。
      const riskyTail = p.includes('“') && !ATTR_VERB.test(p);
      let rule = null;
      if (!pq && !cq && pl < target && !riskyTail) rule = 'M1';                             // 叙述+叙述
      else if (!pq && cq && prev.endsWith('：')) rule = 'M0';                               // 冒号引入对白
      else if (pq && !cq && pl < target && hasOwnAttribution(prev) && !ATTR_VERB.test(p)) rule = 'M2';
      if (rule) {
        merges.push({ ch: 0, rule, a: prev, b: p });
        out[out.length - 1] = prev + p;
        continue;
      }
    }
    out.push(p);
  }
  return { out, merges };
}

function stats(paras) {
  const q = paras.filter(isQuote), nar = paras.filter((p) => !isQuote(p));
  const one = (xs) => {
    if (!xs.length) return { n: 0, mean: 0, lt20: 0 };
    const ls = xs.map(wc);
    return {
      n: xs.length,
      mean: +(ls.reduce((a, b) => a + b, 0) / ls.length).toFixed(1),
      lt20: Math.round((100 * ls.filter((x) => x < 20).length) / ls.length),
    };
  };
  return { all: one(paras), nar: one(nar), dq: one(q), qShare: Math.round((100 * q.length) / paras.length) };
}

let sum = { all: [], nar: [], dq: [] };
const samples = [];
let changedFiles = 0;

for (let n = FROM; n <= TO; n++) {
  const file = path.join(NOVEL, `chapter-${String(n).padStart(2, '0')}.md`);
  if (!fs.existsSync(file)) continue;
  const raw = fs.readFileSync(file, 'utf8');
  const lines = raw.split('\n');
  const head = lines.filter((l) => l.startsWith('#')).join('\n');
  const paras = lines.map((l) => l.trim()).filter((l) => l && !l.startsWith('#'));
  const { out, merges } = coalesce(paras, TARGET);
  if (out.length === paras.length) continue;
  if (!DRY) {
    fs.writeFileSync(file, (head ? head + '\n\n' : '') + out.join('\n\n') + '\n', 'utf8');
  }
  changedFiles++;
  const b = stats(paras), a = stats(out);
  sum.all.push([b.all, a.all]); sum.nar.push([b.nar, a.nar]); sum.dq.push([b.dq, a.dq]);
  for (const m of merges) {
    if (samples.length < SAMPLE) samples.push(`ch${n} ${m.rule}: ${m.a} ⧺ ${m.b}   ⇒   ${m.a + m.b}`);
  }
}

const combine = (pairs, side) => {
  const xs = pairs.map((p) => p[side]);
  const n = xs.reduce((s, x) => s + x.n, 0);
  return {
    n,
    mean: n ? +(xs.reduce((s, x) => s + x.n * x.mean, 0) / n).toFixed(1) : 0,
    lt20: n ? Math.round(xs.reduce((s, x) => s + x.n * x.lt20, 0) / n) : 0,
  };
};

for (const [label, pairs] of [['全部段', sum.all], ['叙述段', sum.nar], ['引号段', sum.dq]]) {
  const b = combine(pairs, 0), a = combine(pairs, 1);
  console.log(`${label}: ${b.n} → ${a.n} 段 | 均段 ${b.mean} → ${a.mean} | <20字 ${b.lt20}% → ${a.lt20}%`);
}
console.log(`改动 ${changedFiles} 章${DRY ? '（dry-run，未写盘）' : ''}，target=${TARGET}`);
if (samples.length) {
  console.log('\n抽样：');
  for (const s of samples) console.log('  ' + s);
}
