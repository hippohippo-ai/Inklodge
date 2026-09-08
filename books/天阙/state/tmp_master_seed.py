# -*- coding: utf-8 -*-
"""宗师预埋补种：萧寒山(ch19)/李清微(ch122)/澹台孤鹤(ch201) + 回归修复(ch201 十五年后)。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOVEL = ROOT / "novel"


def load(p):
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def save(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t)


def swap(s):
    out = []
    oc = True
    for ch in s:
        if ch == '"':
            out.append("\u201c" if oc else "\u201d")
            oc = not oc
        elif ch in "\u201c\u201d":
            out.append('"')
        else:
            out.append(ch)
    return "".join(out)


def fix(fname, pairs):
    p = NOVEL / fname
    t = load(p)
    crlf = "\r\n" in t
    t = t.replace("\r\n", "\n")
    n = 0
    for old, new in pairs:
        if old in t:
            t = t.replace(old, new, 1)
            n += 1
            continue
        alt = swap(old)
        if alt in t:
            t = t.replace(alt, swap(new), 1)
            n += 1
            continue
        print(f"[MISS] {fname}: {old[:34]!r}")
    save(p, t.replace("\n", "\r\n") if crlf else t)
    return n


total = 0

# ── 回归修复：ch201 观察档口径（上轮改"十五年前"漏了"十二年后"）──
total += fix("chapter-201.md", [
    ("他十五年前被人记进档案，十二年后的今夜",
     "他十五年前被人记进档案，十五年后的今夜"),
])

# ── 补种 A：萧寒山 + 四十三斤铁脊枪（ch19 握枪段）──
total += fix("chapter-19.md", [
    ("李承洲没有答。他的手从枪杆上移开，又握紧。",
     "李承洲没有答。他的手从枪杆上移开，又握紧。\n\n枪是旧枪，四十三斤铁脊，当年老帅萧寒山交到他手里时，只说了一句：“兵阵里的枪，不挑力气，挑阵位。”这句话，他记了十年。"),
])

# ── 补种 B：李清微 + 太白山门（ch122 断喉式·三支）──
total += fix("chapter-122.md", [
    ("宁红叶站在晒场边，没有说话。风从竹林里穿过来，把药草的苦味送到她鼻子里。她忽然想起她爹教她练剑时说的那句话：",
     "宁红叶站在晒场边，没有说话。风从竹林里穿过来，把药草的苦味送到她鼻子里。\n\n北支散了，西支走了——可太白山上还有一个人没走。玄都观的李清微师伯，在雪峰上枯坐了三十年，锁着山门；散出去的人她不管，山里的剑，她看着。剑宗分家那年，她只做了一件事：把山门上的锁，换成了新的。\n\n她忽然想起她爹教她练剑时说的那句话："),
])

# ── 补种 C：澹台孤鹤 + 终南山（ch201 炭客第三道盘查）──
total += fix("chapter-201.md", [
    ("汉子把炭扔回篓里，没有再问。他让开路，眼睛却一直跟着沈广农的背影，直到他转过山弯。",
     "汉子把炭扔回篓里，没有再问。他朝山深处抬了抬下巴：“后生，知道这山里住着谁吗？”\n\n沈广农摇头。\n\n“住着一位老道爷。”汉子说，“楼观台后头，南五台顶上，坐忘了几十年没下山。山下的年号换了好几个，他连眼皮都不抬。炭客窑工拜神拜不到他头上——可我们守山的人知道，这山，是他在看着。”\n\n沈广农没有接话。汉子让开路，眼睛却一直跟着他的背影，直到他转过山弯。"),
])

print(f"\n总替换: {total}")