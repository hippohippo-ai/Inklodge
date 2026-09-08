# -*- coding: utf-8 -*-
"""药案'忌铁器'链一致性修复：ch148 四个字→三个字；ch169 燎角页位置 最下面→最上面。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOVEL = ROOT / "novel"


def load(p):
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def save(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t)


def fix(fname, pairs):
    p = NOVEL / fname
    t = load(p)
    crlf = "\r\n" in t
    t = t.replace("\r\n", "\n")
    n = 0
    for old, new in pairs:
        c = t.count(old)
        if c == 0:
            print(f"[MISS] {fname}: {old[:30]!r}")
            continue
        t = t.replace(old, new)
        n += c
        print(f"[OK] {fname}: {old[:24]}… ×{c}")
    save(p, t.replace("\n", "\r\n") if crlf else t)
    return n


total = 0
# ch148：裴弘度读的是"忌铁器"三个字
total += fix("chapter-148.md", [
    ("忌铁器。裴弘度把这四个字又看了一遍。",
     "忌铁器。裴弘度把这三个字又看了一遍。"),
])
# ch169：燎角页与 ch169 L33/ch187/ch191 口径统一为第一页（最上面/最外面）
total += fix("chapter-169.md", [
    ("油布烧穿了一个角，最下面那页纸上，“忌铁器”三个字，被火燎去了一半。",
     "油布烧穿了一个角，最上面那页纸上，“忌铁器”三个字，被火燎去了一半。"),
    ("油布烧穿了一个角，最下面那页纸上，“忌铁器”三个字缺了半边，可上面的墨迹还认得清。",
     "油布烧穿了一个角，最上面那页纸上，“忌铁器”三个字缺了半边，可上面的墨迹还认得清。"),
])
print(f"\n总替换: {total}")