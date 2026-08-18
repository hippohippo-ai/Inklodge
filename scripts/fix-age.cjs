const fs = require('fs');
const path = require('path');

// 高太公 73 岁。ch5-12 的「我活了六十年」是早期笔误，改为「我活了七十多年」。
// ch20 的「俺活了六十年」是别的鬼王二柱，保留（用「我活了」精确匹配）。
const files = [5, 6, 7, 9, 12];
let total = 0;
for (const n of files) {
  const p = path.join('novel', `chapter-${String(n).padStart(2, '0')}.md`);
  let s = fs.readFileSync(p, 'utf8');
  let c = 0;
  const re = /我活了六十年/g;
  const m = s.match(re);
  if (m) { c = m.length; s = s.replace(re, '我活了七十多年'); }
  // ch7 特例：后面「觉得六十年，已经很长了」也要跟着变
  s = s.replace(/觉得六十年，已经很长了/g, '觉得七十多年，已经很长了');
  if (c > 0) {
    fs.writeFileSync(p, s);
    console.log(`chapter-${n}.md :`, c, '处');
    total += c;
  }
}
console.log('共', total, '处');
