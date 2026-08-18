const fs = require('fs');
const path = require('path');

// 安全规则：翠兰死后至今的时长 = 7 年（14 年前取经 → 等满七年 → 7 年前死）
const rules = [
  ['十年前死', '七年前死'],
  ['十年前走', '七年前走'],
  ['十年前添', '七年前添'],
  ['十年前下葬', '七年前下葬'],
  ['十年前的事', '七年前的事'],
  ['十年前', '七年前'],
  ['等了十年', '等了七年'],
  ['等了他十年', '等了他七年'],
  ['等了你十年', '等了你七年'],
  ['等了我十年', '等了我七年'],
  ['死了十年', '死了七年'],
  ['走了十年', '走了七年'],
  ['埋了十年', '埋了七年'],
  ['困了十年', '困了七年'],
  ['住了十年', '住了七年'],
  ['转了十年', '转了七年'],
  ['记了十年', '记了七年'],
  ['扛了十年', '扛了七年'],
  ['想了十年', '想了七年'],
  ['等了十年', '等了七年'],
  ['待了十年', '待了七年'],
  ['看了十年', '看了七年'],
  ['拿着它十年', '拿着它七年'],
  ['喊了十年', '喊了七年'],
  ['当了十年', '当了七年'],
  ['画了十年', '画了七年'],
  ['信了十年', '信了七年'],
  ['留了十年', '留了七年'],
  ['欠了十年', '欠了七年'],
  ['我的十年', '我的七年'],
  ['这十年', '这七年'],
  ['十年了', '七年了'],
];

// ch9 排除（死期改动相隔十年/在十年前是正典，需人工），ch16 需人工（六十三→七十三），ch1 需人工（十二年）
const skip = new Set(['chapter-09.md', 'chapter-16.md', 'chapter-01.md']);

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
