const fs = require('fs');
const path = require('path');

const rules = [
  ['十年里', '七年里'],
  ['躺了十年', '躺了七年'],
  ['埋十年', '埋七年'],
  ['被锁了十年', '被锁了七年'],
  ['等了她男人十年', '等了她男人七年'],
  ['等了那个人十年', '等了那个人七年'],
  ['十年，不算长', '七年，不算长'],
  ['查了十年', '查了七年'],
  ['住了十年', '住了七年'],
  ['这十年', '这七年'],
  ['她等了她男人十年', '她等了她男人七年'],
];

const skip = new Set(['chapter-09.md', 'chapter-16.md']);
const files = fs.readdirSync('novel').filter(f => /^chapter-\d+\.md$/.test(f));
let total = 0;
for (const f of files) {
  if (skip.has(f)) continue;
  const p = path.join('novel', f);
  let s = fs.readFileSync(p, 'utf8');
  let count = 0;
  for (const [a, b] of rules) {
    if (s.includes(a)) {
      const re = new RegExp(a.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
      const m = s.match(re);
      count += m ? m.length : 0;
      s = s.replace(re, b);
    }
  }
  if (count > 0) {
    fs.writeFileSync(p, s);
    console.log(f, ':', count, '处');
    total += count;
  }
}
console.log('共', total, '处');
