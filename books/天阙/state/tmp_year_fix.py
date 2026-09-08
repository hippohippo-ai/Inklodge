# -*- coding: utf-8 -*-
"""年限对账修复：三岔路口分手=759、长安陷=756、沈母殁=754、分家=732、观察始=751。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOVEL = ROOT / "novel"


def load(p):
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def save(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t)


def swap_quotes(s):
    out = []
    open_curly = True
    for ch in s:
        if ch == '"':
            out.append("\u201c" if open_curly else "\u201d")
            open_curly = not open_curly
        elif ch == "'":
            out.append("\u2018" if open_curly else "\u2019")
            open_curly = not open_curly
        elif ch == "\u201c" or ch == "\u201d":
            out.append('"')
        elif ch == "\u2018" or ch == "\u2019":
            out.append("'")
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
            t = t.replace(old, new)
            n += 1
            continue
        alt = swap_quotes(old)
        if alt in t:
            t = t.replace(alt, swap_quotes(new))
            n += 1
            continue
        print(f"[MISS] {fname}: {old[:32]!r}")
    save(p, t.replace("\n", "\r\n") if crlf else t)
    return n


total = 0

# ── 三岔路口分手 = 759（ch95 卷五初）───────────
total += fix("chapter-141.md", [("记得八年前的长安城门", "记得七年前的长安城门")])  # 762−755=7
total += fix("chapter-159.md", [("一场他等了六年、", "一场他等了三年、")])  # 762−759=3
total += fix("chapter-160.md", [
    ("六年了——六年前，在三岔路口分手", "三年了——三年前，在三岔路口分手"),
    ("他忽然想起六年前那个决定——", "他忽然想起三年前那个决定——"),
    ("他忽然想起六年前那个三岔路口", "他忽然想起三年前那个三岔路口"),
    ("忽然想起六年前在三岔路口，他蹲下来替桑葚包脚的那个下午", "忽然想起三年前在三岔路口，他蹲下来替桑葚包脚的那个下午"),
    ("一转眼，六年了。", "一转眼，三年了。"),
])
total += fix("chapter-169.md", [("六年前在三岔路口", "四年前在三岔路口")])  # 763−759=4
total += fix("chapter-187.md", [
    ("六年前，她用小鞋、石子、沙，摆给他看", "四年前，她用小鞋、石子、沙，摆给他看"),
    ("他忽然想起，六年前分别的时候", "他忽然想起，四年前分别的时候"),
    ("这话是六年前在废仓里说的", "这话是四年前在废仓里说的"),
    ("六年前，她摆小鞋、石子、沙，告诉他", "四年前，她摆小鞋、石子、沙，告诉他"),
    ("他忽然想，六年前，也是这双手", "他忽然想，四年前，也是这双手"),
])

# ── 沈母殁 = 754（ch166/179 正典）─────────────
total += fix("chapter-175.md", [("忽然想：八年前，他娘也是这样", "忽然想：九年前，他娘也是这样")])  # 763−754=9
total += fix("chapter-177.md", [
    ("那时候他娘抱着他，混在人堆里", "那时候他娘刚死，他一个人混在人堆里"),
    ("他忽然想起八年前的自己，也是这么大", "他忽然想起九年前的自己，也是这么大"),
])

# ── 长安陷 = 756（ch26/ch141 正典）───────────
total += fix("chapter-182.md", [
    ("沈广农看着他们，忽然想起八年前。", "沈广农看着他们，忽然想起七年前。"),
    ("八年前，长安也破过一回。", "七年前，长安也破过一回。"),
])

# ── 观察档始 = 751（ch166 顾琰 5岁/10岁兵祸 自洽）──
total += fix("chapter-192.md", [
    ("他等了十二年，等的就是一个人看东西的方式", "他等了十三年，等的就是一个人看东西的方式"),  # 764−751=13
    ("“等了十二年。”记缝的人说，“十二年前，上头让人在扬州码头留了一双眼睛", "“等了十三年。”记缝的人说，“十三年前，上头让人在扬州码头留了一双眼睛"),
])
total += fix("chapter-195.md", [("二十年前，她五岁，她的第一份回禀", "她五岁那年，她的第一份回禀")])
total += fix("chapter-201.md", [("十二年了——他十二年前被人记进档案", "十五年了——他十五年前被人记进档案")])  # 766−751=15

# ── 分家 = 732（ch153/161 恒等式）─────────────
total += fix("chapter-205.md", [
    ("三十年前，他离开观天台的时候", "三十多年前，他离开观天台的时候"),  # 765/766−732=33/34
    ("三十年前，裴弘度离开的时候", "三十多年前，裴弘度离开的时候"),
])

# ── 楚归藏刺目 = 723（ch166 恒等式）───────────
total += fix("chapter-210.md", [("四十年前", "四十多年前")])  # 766−723=43

print(f"\n总替换: {total}")