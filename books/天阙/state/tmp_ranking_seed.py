# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path

fixes = {
    "novel/chapter-07.md": [
        (
            "“我师父，太白剑宗第十二席。”\n\n“怎么死的？”",
            "“我师父，《天下宗师录》第十二席。”\n\n“宗师录？”\n\n“天下武夫认出来的十二把交椅。”公孙白抹了一把刀背上的水，“三十年前他死了，那把交椅至今空着，天下没人敢坐上去。”\n\n“怎么死的？”",
        ),
    ],
    "novel/chapter-54.md": [
        (
            "他在北仓这些天听人提过这个身形：河北来的，杀人不用刀。",
            "他在北仓这些天听人提过这个身形：河北来的，杀人不用刀。江湖上“黑榜看危，八凶看要命”——八凶里的血手屠夫，二十年只追一个人。",
        ),
    ],
    "novel/chapter-134.md": [
        (
            "“老衲鸠摩摩诃。”老僧说。\n\n灰衣人没有说话。\n\n“施主的剑，”",
            "“老衲鸠摩摩诃。”老僧说。\n\n灰衣人没有说话。\n\n“中原《宗师录》十二席。”鸠摩摩诃说，“老一辈的坐忘深山，盛世里的各归草莽。老衲居第四席，施主居第十席——天下打烂了这八年，还拔得动兵器的，就剩你我了。”\n\n“施主的剑，”",
        ),
    ],
    "novel/chapter-142.md": [
        (
            "如今那道牌，成了弹劾里的一条。”\n\n“牌已经收回了。”",
            "如今那道牌，成了弹劾里的一条。”\n\n“将军可知道，内侍省每三年核一回《黑榜》。”乔执圭说，“记天下最不受管束的十颗人头。今年重排，榜首那一栏，六部拟的都是将军。”\n\n李承洲没有说话。\n\n“本监多嘴一句。”乔执圭说，“将军在河东署过的每一道牌，本监都过过手。本监知道，那些牌没有一道是为将军自己署的——可六部不看这个。六部只看见，有人不奉诏，有人还在替人署牌。”\n\n“牌已经收回了。”",
        ),
    ],
}

total = 0
for rel, pairs in fixes.items():
    p = Path(rel)
    t = p.read_text(encoding='utf-8')
    for old, new in pairs:
        c = t.count(old)
        if c == 0:
            print(f"MISS  {rel}: {old[:36]}")
        else:
            t = t.replace(old, new)
            total += c
    p.write_text(t, encoding='utf-8')
print(f"applied {total} replacements")