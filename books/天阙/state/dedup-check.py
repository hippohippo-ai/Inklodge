#!/usr/bin/env python
"""第三卷防重复基线检查器
用法:  python state/dedup-check.py 45 [46 47 ...]   (章号，可为多个)
比对:  ① 冻结短语(F类, dedup-baseline-vol3.md) 逐字匹配
       ② 跨卷 14字非重叠滑窗 vs 第二卷44章
       ③ 章内 12字非重叠滑窗
       ④ 高频意象词降频检查(F3: 单章≤1次)
退出码: 0=全部通过, 1=有命中
"""
import sys, re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent      # books/天阙
NOVEL = ROOT / "novel"
# F1/F2 frozen phrases (exact match)
FROZEN = [
    "记人的账", "东门收路引", "西门收粮牌", "改账的人在改命",
    "到了马嵬再想办法", "把布条塞回怀里", "第七袋", "第七仓",
    "你问得太快", "你答得太慢", "还能抬", "一个抱孩子的妇人",
    "姓名籍贯", "药方上的名字已经被汗浸开", "记什么",
]
# F3 high-density imagery words: <=1 occurrence per new chapter
F3 = ["水纹", "驿站", "门洞", "公验", "押运", "盐霜", "军功牌", "铁牌", "淮口"]
# F4 vol3 frozen collocations: <=1 occurrence per chapter (per baseline section 5)
F4 = ["泥按纸算钱", "闸下之货", "我救市，不救人", "欲寻印者", "灯下无名", "我记灯，不记人"]
F4_MAX = {"泥按纸算钱": 0, "闸下之货": 1, "我救市，不救人": 1, "欲寻印者": 0, "灯下无名": 1, "我记灯，不记人": 1}
# F6 vol3 high-density new words: <=1 occurrence per chapter
F6 = ["调拨单", "堂票", "窝棚区", "点验", "粮卡巡役", "活结环"]
# B-class controlled echoes: allowed, report only
CONTROLLED = ["黑布线", "缺角铁牌", "军道图", "盐账", "半份盐账", "冷金笺", "照夜", "霜梅", "贝壳砂", "盐砖"]

def norm(t: str) -> str:
    t = unicodedata.normalize("NFC", t)
    return t

def load_ch(n: int) -> str:
    p = NOVEL / f"chapter-{n:02d}.md"
    return norm(p.read_text(encoding="utf-8"))

def dedup_windows(text: str, others: list[str], width: int, self_idx=None):
    """Non-overlapping sliding windows of `text` found in any of `others`.
    self_idx: index in `others` that IS this text (intra-chapter mode);
    occurrences at the window's own position are excluded (anti self-overlap)."""
    seen_spans = set()
    hits = []
    punct = set(chr(c) for c in (0xFF0C,0x3002,0xFF1A,0xFF1B,0xFF01,0xFF1F,0x000A,0x201C,0x201D,0x0022,0x0027,0x2014,0x2026,0x3001,0x300A,0x300B,0xFF08,0xFF09))
    for i in range(0, len(text) - width + 1):
        if any(i <= s < i + width for s in seen_spans):
            continue
        w = text[i:i+width]
        if any(p in w for p in punct):
            continue
        for o_idx, o in enumerate(others):
            j = o.find(w)
            while o_idx == self_idx and j >= 0 and j <= i < j + width:
                j = o.find(w, j + 1)
            if j >= 0:
                hits.append((i, w, o_idx, j))
                for k in range(i, i + width):
                    seen_spans.add(k)
                break
    return hits

def main():
    args = [int(a) for a in sys.argv[1:]]
    if not args:
        print(__doc__); sys.exit(2)
    vol2 = [load_ch(i) for i in range(1, 45)]
    fail = 0
    for n in args:
        text = load_ch(n)
        body = re.sub(r"^#.*$", "", text, flags=re.M)
        print(f"\n=== 第{n}章 ===")
        # ① frozen (body only: chapter titles are sanctioned by outline-vol3, e.g. ch53 《记人的账》)
        # ch63/68 sanctioned: the "第七" cross-volume loop (第七袋/第七仓/第七灯) may appear ONLY there
        sanctioned = {"第七袋", "第七仓"} if n in (63, 68) else set()
        f_hits = [(ph, body.count(ph)) for ph in FROZEN if body.count(ph) and ph not in sanctioned]
        if f_hits:
            fail += 1
            print("  [F类·冻结短语]")
            for ph, c in f_hits:
                print(f"    × {ph}  ×{c}")
        # ④ F3 density
        d_hits = [(w, body.count(w)) for w in F3 if body.count(w) > 1]
        if d_hits:
            fail += 1
            print("  [F3·高频意象超频(单章>1)]")
            for w, c in d_hits:
                print(f"    × {w}  ×{c}")
        # F4 vol3 collocations (apply from ch53 onward per baseline section 5)
        f4_hits = [(w, body.count(w), F4_MAX.get(w, 0)) for w in F4 if n >= 53 and body.count(w) > F4_MAX.get(w, 0)]
        if f4_hits:
            fail += 1
            print("  [F4·卷三冻结搭配超限]")
            for w, c, m in f4_hits:
                print(f"    × {w}  ×{c} (上限{m})")
        # F6 vol3 density
        f6_hits = [(w, body.count(w)) for w in F6 if n >= 53 and body.count(w) > 1]
        if f6_hits:
            fail += 1
            print("  [F6·卷三新词超频(单章>1)]")
            for w, c in f6_hits:
                print(f"    × {w}  ×{c}")
        # ② cross-volume 14-char windows (exclude title line already)
        x_hits = dedup_windows(body, vol2, 14)
        if x_hits:
            fail += 1
            print("  [跨卷 14字滑窗]")
            for i, w, oi, j in x_hits[:20]:
                print(f"    × “{w}”  ← 第{oi+1:02d}章 偏移{j}")
        # ③ intra-chapter 12-char windows
        i_hits = dedup_windows(body, [body], 12, self_idx=0)
        if i_hits:
            fail += 1
            print("  [章内 12字滑窗]")
            for i, w, _, _ in i_hits[:20]:
                print(f"    × “{w}”  偏移{i}")
        # B-class report (no fail)
        b_hits = [(w, body.count(w)) for w in CONTROLLED if body.count(w)]
        if b_hits:
            print("  [B类·受控呼应（需登记）]")
            for w, c in b_hits:
                print(f"    • {w}  ×{c}")
        if not (f_hits or d_hits or f4_hits or f6_hits or x_hits or i_hits):
            print("  ✓ 基线比对通过")
    sys.exit(1 if fail else 0)

if __name__ == "__main__":
    main()
