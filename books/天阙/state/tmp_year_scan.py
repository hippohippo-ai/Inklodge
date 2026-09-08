# -*- coding: utf-8 -*-
"""扫描全书 'X年前' 与 '动词+X年' 年限表述（中文数字），输出按章/行/上下文清单。"""
import re, sys
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
NOVEL = Path(__file__).resolve().parent.parent / "novel"

DIG = "一二两三四五六七八九"
CN = "一二两三四五六七八九十"


def cn2int(s):
    if not s:
        return None
    if "十" in s:
        parts = s.split("十")
        tens, ones = parts[0], parts[1] if len(parts) > 1 else ""
        t = 0
        if tens == "":
            t = 1
        elif tens == "两":
            t = 2
        elif tens in DIG:
            t = DIG.index(tens) + 1
        else:
            return None
        o = 0
        if ones:
            o = 2 if ones == "两" else (DIG.index(ones) + 1 if ones in DIG else None)
            if o is None:
                return None
        return t * 10 + o
    if s == "两":
        return 2
    if s in DIG:
        return DIG.index(s) + 1
    return None


NUMS = f"[{CN}]" + "{1,3}"
PATS = [
    (re.compile(f"({NUMS})年前"), "年前"),
    (re.compile(f"({NUMS})年以前"), "年以前"),
    (re.compile(f"({NUMS})年之前"), "年之前"),
    (re.compile(f"(?:死了|殁了|殁于|已死|走了|护了|借了|借名|辞差|查了|用了|当了|做了|干了|治了|瞒了|躲了|等了|画了|关了|押了|领了|焚了|烧了|立了|断了|认了|扛了|背了)({NUMS})年"), "动+年"),
]

# 年号前缀（匹配前的上下文含这些字则跳过该命中）
ERA = re.compile(r"(天宝|至德|乾元|上元|广德|宝应|永泰|大历|开元|贞观|开元|建中|贞元)")

hits = []
for p in sorted(NOVEL.glob("chapter-*.md")):
    ch = int(p.stem.split("-")[1])
    for ln, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        for pat, kind in PATS:
            for m in pat.finditer(line):
                n = cn2int(m.group(1))
                if n is None or n < 3:
                    continue
                pre = line[max(0, m.start() - 6):m.start()]
                if ERA.search(pre):
                    continue
                s = max(0, m.start() - 30)
                e = min(len(line), m.end() + 32)
                ctx = line[s:e].replace("\r", "").strip()
                hits.append((ch, ln, kind, n, ctx))

print(f"总命中（N≥3，排除年号）: {len(hits)}")
bych = Counter(h[0] for h in hits)
print("\n=== 各章命中数（N≥3）===")
for ch in sorted(bych):
    print(f"ch{ch}: {bych[ch]}")
print("\n=== N≥5 完整清单 ===")
for ch, ln, kind, n, ctx in hits:
    if n >= 5:
        print(f"ch{ch} L{ln} [{kind} N={n}] …{ctx}…")