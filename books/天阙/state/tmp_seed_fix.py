# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path

fixes = {
    "novel/chapter-201.md": [
        ("十五年了——他十五年前被人记进档案，十五年后的今夜", "十四年了——他十四年前被人记进档案，十四年后的今夜"),
        ("你们记了我十二年", "你们记了我十四年"),
        ("十二年，你长高了", "十四年，你长高了"),
        ("记你十二年的是台主", "记你十四年的是台主"),
        ("台里记了你十二年", "台里记了你十四年"),
        ("他记了我十二年", "他记了我十四年"),
        ("是你这十二年怎么活过来的", "是你这十四年怎么活过来的"),
        ("“住着一位老道爷。”汉子说，“楼观台后头", "“住着一位老道爷，叫澹台孤鹤。”汉子说，“楼观台后头"),
    ],
    "novel/chapter-192.md": [
        ("等了他十二年", "等了他十三年"),
        ("被记了十二年", "被记了十三年"),
    ],
}

total = 0
for rel, pairs in fixes.items():
    p = Path(rel)
    t = p.read_text(encoding='utf-8')
    for old, new in pairs:
        c = t.count(old)
        if c == 0:
            print(f"MISS  {rel}: {old[:30]}")
        else:
            t = t.replace(old, new)
            total += c
    p.write_text(t, encoding='utf-8')
print(f"applied {total} replacements")