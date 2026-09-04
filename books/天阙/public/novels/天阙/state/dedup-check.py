#!/usr/bin/env python
"""《天阙》防重复基线检查器
用法:  python state/dedup-check.py 45 [46 47 ...]   (章号，可为多个)
比对:  ① 冻结短语(F类, dedup-baseline-vol3.md) 逐字匹配
       ② 跨卷 14字非重叠滑窗 (ch≤92 vs 第二卷44章; ch117-140 vs 前五卷116章+卷内已写章)
       ③ 章内 12字非重叠滑窗
       ④ 高频意象词降频检查(F3: 单章≤1次)
       ⑤ 句式/身份词密度上限(F7: 精确词+正则模板, 全书通用)
       ⑥ F8 卷五标志性短语(F8, dedup-baseline-vol6.md: 冷金笺/第三支笔/竹简/销名/收笔带钩/归位/缺角)
       ⑦ F9 卷六"岸"意象落点(117/119/124/126/138 必含岸; 非落点章单章≤3)
       ⑧ 卷六B类词密度上限(待核销≤3/编号册≤2/凸点≤2/分名≤2/军道图≤1/盐账≤4)
       ⑨ F10 章题声明与旧题禁引 (自 ch141 起): 新章题必须先声明于卷纲(outline-vol7.md 管 141-164, outline-vol8.md 管 165-188, 随卷演进);
          正文禁回引卷六旧题(粮行的一笔/船坞的三十年等, 源: chapter-title-index.md);
          卷三—卷六现有章另做卷纲声明与实际章题一致性复核(仅报告漂移, 不算失败)
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
# F3 high-density imagery words: <=1 occurrence per new chapter (ch45+; ch1-44 存量仅报告)
F3 = ["水纹", "驿站", "门洞", "公验", "押运", "盐霜", "军功牌", "铁牌", "淮口"]
# FROZEN 短语的登记豁免 (章→该章允许次数): B类刻意呼应/存量通用短语。
# 你问得太快/你答得太慢 → 顾琰一系说话习惯 (ch6/13); 还能抬 → 宁红叶左臂 (ch31/44);
# 记什么 → 李承洲登记执念 (ch19/20 各2, ch41 1); 一个抱孩子的妇人 → 存量通用短语 (ch3/15/21/26);
# 东门收路引/西门收粮牌 → 世界规则口诀 (ch26/43/44); 溃兵两句 → ch26 单章存量。
FROZEN_ALLOW = {
    "你问得太快": {6: 1, 13: 1},
    "你答得太慢": {6: 1, 13: 1},
    "还能抬": {31: 1, 44: 1},
    "记什么": {19: 2, 20: 2, 41: 1},
    "一个抱孩子的妇人": {3: 1, 15: 1, 21: 1, 26: 1},
    "东门收路引": {26: 1, 43: 1, 44: 1},
    "西门收粮牌": {26: 1, 43: 1, 44: 1},
    "到了马嵬再想办法": {26: 1},
    "把布条塞回怀里": {26: 1},
    "记人的账": {44: 1},  # ch44 卷末收束预言, 正典呼应 ch53 章题
    "药方上的名字已经被汗浸开": {24: 1},  # ch24 单章源句, 禁他章复用
    "改账的人在改命": {25: 1},  # ch25 单章源句(章眼), 禁他章复用
}
# F4 vol3 frozen collocations: <=1 occurrence per chapter (per baseline section 5)
F4 = ["泥按纸算钱", "闸下之货", "我救市，不救人", "欲寻印者", "灯下无名", "我记灯，不记人"]
F4_MAX = {"泥按纸算钱": 0, "闸下之货": 1, "我救市，不救人": 1, "欲寻印者": 0, "灯下无名": 1, "我记灯，不记人": 1}
# F6 vol3 high-density new words: <=1 occurrence per chapter
F6 = ["调拨单", "堂票", "窝棚区", "点验", "粮卡巡役", "活结环"]
# F7 sentence/identity-word density caps (universal, every chapter).
# Exact-string caps: 模板反馈句式（“你怎么知道”“哪里不对”）单章≤1；身份词（账房先生/识数）
# 以章为上限防止“全员账房化”。新章写作时若需超限，须先改写为指代/具体问法。
F7_EXACT = {"你怎么知道": 1, "哪里不对": 1, "账房先生": 4, "识数": 3}
# Regex caps: 模板句式变体（“你是个……的”评价句；“X不对”问答模板的变体问法）。
# 每项 (标签, 正则, 单章上限)。正则与正文同用 UTF-8，捕获组一律用 (?: ) 以免干扰 findall。
F7_REGEX = [
    ("你是个…的/你才是个…的", r"你(?:是|才是|才)个[^，。！？\n]{1,12}的", 1),
    ("怎么个不对法", r"怎么个不对法", 1),
    ("哪儿不对", r"哪儿不对", 1),
    ("不对在哪里", r"不对在哪里", 1),
]
# B-class controlled echoes: allowed, report only
CONTROLLED = ["黑布线", "缺角铁牌", "军道图", "盐账", "半份盐账", "冷金笺", "照夜", "霜梅", "贝壳砂", "盐砖"]
# === 第六卷 (117–140) 规则, dedup-baseline-vol6.md ===
# F8 vol5 signature phrases: {短语: {章号: 该章允许次数}} 或 {短语: None}=每章≤1 (None cap=1)
# 默认其余卷六章节允许 0 次; "缺角"以负向断言排除"缺角铁牌"(B类既有词, 不属卷五意象)
F8 = {
    "第三支笔": {125: 1},
    "冷金笺": {130: 1},
    "竹简": None,
    "销名": None,
    "收笔带钩": None,
    "归位": None,
    "缺角": {131: 1, 140: 1},  # 全卷合计≤2 额外校验
}
# F9 卷六"岸"意象: 落点章必含≥1; 其余卷六章≤3 (用 渡口/埠头/船缆/堤 等器物替代)
VOL6_LANDING = {117, 119, 124, 126, 138}
# 卷六 B 类词密度上限 (单章超过即失败)
VOL6_CAPS = {"待核销": 3, "编号册": 2, "凸点": 2, "分名": 2, "军道图": 1, "盐账": 4}
# === 第七卷起 (141+) 章题纪律: F10 ===
# 新章必须先声明于 state/outline-volN.md (声明的章题与 novel/ 首行章题一致), 正文禁回引旧题。
VOL_START = 141
# 卷纲文件与章号范围: (start, end, outline文件名)。卷一二无逐章卷纲, 跳过低卷号段。
OUTLINE_SPANS = [(45, 68, "outline-vol3.md"), (69, 92, "outline-vol4.md"),
                 (93, 116, "outline-vol5.md"), (117, 140, "outline-vol6.md")]
# 弃用旧题全集 (40, 据 chapter-title-index.md 一轮+二轮清洗): ch141+ 正文禁现(指代/概念语可豁免需登记)。
# 与 chapter-title-index.md 保持同步: 新增改名批次必须在此登记。
DEPRECATED = [
    # 卷六 11 (二轮)
    "粮行的一笔", "船坞的三十年", "岸上的袁五", "南支的老人", "虹县的图", "出关的册",
    "马市的编号", "地窖的药案", "寺的供养册", "雪线之前", "军线的回响",
    # 卷五 11 (一轮)
    "常平仓的灯", "北上的漕船", "押运的册子", "宁红叶的剑南", "漕港的账房",
    "崔玉真与李承洲的账", "总漕册的背面", "一页纸的缺口", "病休的誊录官", "销名的手", "名单的最后一行",
    # 卷四 3
    "张孝忠的门", "军报里的墨圈", "借名者的手",
    # 卷三 3
    "段九的算盘", "南来的药", "桑葚的信",
    # 卷二 1
    "宁红叶的选择",
    # 卷一 11
    "茶摊后面的账本", "清江浦的潮声", "废仓里的秤", "观察者的目光", "运河上的第一次交手",
    "黑水盟的边缘", "失明的边缘", "观察者的眼泪", "运河上的刀声", "驿站的北方来客", "信使的尸体",
]
# 弃用旧题中仍以普通叙述短语在正文合法出现的豁免项 (人物指代/概念语, 防误伤; 仍禁止作为章题引用)。
DEPRECATED_EXEMPT_BODY = {"岸上的袁五", "名单的最后一行", "宁红叶的剑南"}
# === F15·卷七回收链机械校验 (ch141-164, 与 foreshadowing「卷七回收规划区」同步) ===
# F15A: 弃用旧题禁引已由 DEPRECATED/EXEMPT 覆盖(见 F10 块); F15B: 回收章必备意象表。
# 每章至少命中任一组 token 之一(任何一组内任意词出现即满足该组), 防止写 ch141-164 时漏掉回收章眼。
# 维护约定: 改 foreshadowing 卷七回收规划区或 outline-vol7 章眼, 必须先同步本表。
VOL7_REQ = {
    141: [["通牌"]], 142: [["行军簿"]], 143: [["无铁"]], 144: [["名下人数"]],
    145: [["冷金笺"]], 146: [["半本账"]], 147: [["白身"]], 148: [["药案"]],
    149: [["周衡之"]], 150: [["三份"]], 151: [["私印"]], 152: [["回纥"]],
    153: [["十二年"]], 154: [["凹"]], 155: [["药案"]], 156: [["马册"]],
    157: [["名单"]], 158: [["待查"]], 159: [["灰烬", "余烬"]], 160: [["沈念"]],
    161: [["新墨"]], 162: [["阿青"]], 163: [["行军簿"]], 164: [["袁五"]],
}
# === F15·卷八回收链机械校验 (ch165-188, 与 outline-vol8 章眼/器物锚点同步) ===
# 每章至少命中任一组 token 之一(任何一组内任意词出现即满足该组), 防止写 ch165-188 时漏掉必备意象。
# 维护约定: 改 outline-vol8 章眼或器物锚点清单, 必须先同步本表。
VOL8_REQ = {
    165: [["底本", "抄本"]], 166: [["回禀"]], 167: [["名分"]], 168: [["划掉", "划名"]],
    169: [["照夜"]], 170: [["第四封"]], 171: [["第三次入城", "三入长安", "第三次走进"], ["画影"]],
    172: [["凸点", "抹痕"]], 173: [["报数"]], 174: [["三页"]], 175: [["逃潮"]],
    176: [["先走的车"]], 177: [["城门又开了"], ["数人"]], 178: [["火外头"], ["三页"]],
    179: [["无档"]], 180: [["空架"]], 181: [["两封旨"], ["勤王"]], 182: [["轮换"]],
    183: [["水关"]], 184: [["清洗令"], ["清算"]], 185: [["官吏版"]], 186: [["簿外"]],
    187: [["别再一个人走了"]], 188: [["灯灭"]],
}
# === 第七卷起 (141+) 反内卷机械规则: F11-F13 (requirements.md 律五) ===
# F11 微型交易禁令: "恶钱"单章≤1 (ch141+); 全书按卷做签名词报告(不判失败)
F11_CAP_WORDS = ["恶钱"]
F11_SIG = ["恶钱", "过塘钱", "买路钱", "编丁"]
# F12 纸张版本学降频: 鉴定词表单章命中总数 ch141+ ≤4 (≈150字代理); 全书按章报告
F12_WORDS = ["纤维", "毛边", "撕口", "入纸", "浮红", "沉墨", "帘纹", "水纹", "收笔带钩"]
F12_CAP = 4
# F13 桑葚符号化冻结: ch141+ 禁止"桑葚+炭枝/画圈/画小人"组合
F13_BAN = ["炭枝", "画圈", "画小人"]

def load_outline_declared(outline_file: str) -> dict[int, str]:
    """返回卷纲中声明过的 {章号: 章题}, 卷纲缺失或未声明返回空。"""
    p = ROOT / "state" / outline_file
    if not p.exists():
        return {}
    t = norm(p.read_text(encoding="utf-8"))
    out = {}
    for m in re.finditer(r"第(\d+)章《([^》]*)》", t):
        out[int(m.group(1))] = m.group(2).strip()
    return out

def chapter_title(n: int) -> str:
    """从 novel/chapter-N.md 首行提取章题。"""
    p = NOVEL / f"chapter-{n:02d}.md"
    if not p.exists():
        return ""
    m = re.search(r"《([^》]*)》", p.read_text(encoding="utf-8").split("\n", 1)[0])
    return m.group(1).strip() if m else ""

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
    # vol6: base = 前五卷全116章 + 已写卷六章(比 n 小), 用于跨卷 14字滑窗
    vol6_base = [load_ch(i) for i in range(1, 117)] if any(a >= 117 for a in args) else []
    fail = 0
    for n in args:
        text = load_ch(n)
        body = re.sub(r"^#.*$", "", text, flags=re.M)
        print(f"\n=== 第{n}章 ===")
        # ① frozen (body only: chapter titles are sanctioned by outline-vol3, e.g. ch53 《记人的账》)
        # ch63/68 sanctioned: the "第七" cross-volume loop (第七袋/第七仓/第七灯) may appear ONLY there
        sanctioned = {"第七袋", "第七仓"} if n in (27, 63, 68) else set()  # ch27 埋线, ch63/68 卷三回环
        f_hits = []
        for ph in FROZEN:
            cnt = body.count(ph)
            allow = FROZEN_ALLOW.get(ph, {})
            if cnt and ph not in sanctioned and not (n in allow and cnt <= allow[n]):
                f_hits.append((ph, cnt))
        if f_hits:
            fail += 1
            print("  [F类·冻结短语]")
            for ph, c in f_hits:
                print(f"    × {ph}  ×{c}")
        # ④ F3 density (ch1-44 为规则前存量, 仅报告不判失败)
        d_hits = [(w, body.count(w)) for w in F3 if body.count(w) > 1]
        if d_hits:
            if n >= 45:
                fail += 1
            print("  [F3·高频意象超频(单章>1)]" + ("" if n >= 45 else " (存量, 仅报告)"))
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
        # ⑦ F7 sentence/identity-word density (exact + regex)
        f7_hits = [(w, body.count(w), m) for w, m in F7_EXACT.items() if body.count(w) > m]
        f7_hits += [(lab, len(re.findall(p, body)), m) for lab, p, m in F7_REGEX if len(re.findall(p, body)) > m]
        if f7_hits:
            fail += 1
            print("  [F7·句式/身份词超频]")
            for w, c, m in f7_hits:
                print(f"    × {w}  ×{c} (上限{m})")
        # ② cross-volume 14-char windows (exclude title line already)
        if n >= 117:
            # base: 前五卷116章 + 卷内已写章(章号<n)
            base_list = vol6_base + [load_ch(m) for m in range(117, n) if (NOVEL / f"chapter-{m:02d}.md").exists()]
            punct = set(chr(c) for c in (0xFF0C,0x3002,0xFF1A,0xFF1B,0xFF01,0xFF1F,0x000A,0x201C,0x201D,0x0022,0x0027,0x2014,0x2026,0x3001,0x300A,0x300B,0xFF08,0xFF09))
            idx = set()
            for o in base_list:
                for k in range(0, len(o) - 13):
                    w = o[k:k+14]
                    if not any(p in w for p in punct):
                        idx.add(w)
            seen = set(); x_hits = []
            for i in range(0, len(body) - 13):
                if any(i <= s < i + 14 for s in seen):
                    continue
                w = body[i:i+14]
                if any(p in w for p in punct):
                    continue
                if w in idx:
                    x_hits.append((i, w)); seen.update(range(i, i + 14))
        else:
            # 排除自身章 (vol2 列表含 ch1-44, 若含当前章会产生自比对误报)
            others = [load_ch(i) for i in range(1, 45) if i != n]
            x_hits = dedup_windows(body, others, 14)
        if x_hits:
            fail += 1
            print("  [跨卷 14字滑窗]" if n < 117 else "  [跨卷 14字滑窗 vs 前五卷+卷内]")
            for i, w, *rest in x_hits[:20]:
                print(f"    × “{w}”  偏移{i}" if n >= 117 else f"    × “{w}”  ← 第{rest[0]+1:02d}章 偏移{rest[1]}")
        # F8 vol5 signature phrases (vol6 chapters only)
        v6_issue = False
        if 117 <= n <= 140:
            f8_hits = []
            for ph, allow in F8.items():
                cnt = body.count(ph)
                if ph == "缺角":
                    cnt = len(re.findall(r"缺角(?!铁牌)", body))
                cap = (allow.get(n, 0) if isinstance(allow, dict) else (1 if allow is None else 0))
                if cnt > cap:
                    f8_hits.append((ph, cnt, cap))
            if f8_hits:
                fail += 1; v6_issue = True
                print("  [F8·卷五标志性短语超限]")
                for ph, c, m in f8_hits:
                    print(f"    × {ph}  ×{c} (本章上限{m})")
            # 缺角 全卷合计≤2
            total_jq = 0
            for m in range(117, 141):
                p = NOVEL / f"chapter-{m:02d}.md"
                if p.exists():
                    total_jq += len(re.findall(r"缺角(?!铁牌)", re.sub(r"^#.*$", "", norm(p.read_text(encoding="utf-8")), flags=re.M)))
            if total_jq > 2:
                fail += 1; v6_issue = True
                print(f"  [F8·缺角 全卷合计超限]  ×{total_jq} (上限2)")
            # F9 岸 意象
            shore_cnt = body.count("岸")
            if n in VOL6_LANDING and shore_cnt < 1:
                fail += 1; v6_issue = True
                print("  [F9·岸意象落点缺失]  (本章须含“岸”)")
            elif n not in VOL6_LANDING and shore_cnt > 3:
                fail += 1; v6_issue = True
                print(f"  [F9·岸意象超频]  ×{shore_cnt} (非落点章上限3)")
            # 卷六 B 类词密度
            v6_hits = [(w, body.count(w), m) for w, m in VOL6_CAPS.items() if body.count(w) > m]
            if v6_hits:
                fail += 1; v6_issue = True
                print("  [卷六·B类词超频]")
                for w, c, m in v6_hits:
                    print(f"    × {w}  ×{c} (上限{m})")
            print(f"  [卷六·岸意象计数]  {shore_cnt} 处" + ("  ✓ 落点章达标" if n in VOL6_LANDING and shore_cnt >= 1 else ""))
        # F11-F13 反内卷机械规则 (ch141+ 判失败; 存量按卷/章报告)
        if n >= 141:
            f11_hits = [(w, body.count(w)) for w in F11_CAP_WORDS if body.count(w) > 1]
            f12_cnt = sum(body.count(w) for w in F12_WORDS)
            f13_hits = [w for w in F13_BAN if w in body]
            f13_hits += ["桑葚画"] if re.search(r"桑葚[^。！？\n]{0,25}(?:画|比划)", body) else []
            if f11_hits or f12_cnt > F12_CAP or f13_hits:
                fail += 1; v6_issue = True
                print("  [F11-F13·反内卷机械规则]")
                if f11_hits:
                    for w, c in f11_hits:
                        print(f"    × F11 微型交易词「{w}」×{c} (单章上限1)")
                if f12_cnt > F12_CAP:
                    print(f"    × F12 纸张鉴定词命中 {f12_cnt} 次 (上限{F12_CAP}, 约等于150字鉴定描写)")
                if f13_hits:
                    for w in f13_hits:
                        print(f"    × F13 桑葚符号化: 「{w}」出现 (ch141+ 禁止炭枝/画圈/画小人)")
            else:
                print(f"  [F11-F13·反内卷] F12鉴定词×{f12_cnt} (上限{F12_CAP}) ✓")
        else:
            f12_cnt = sum(body.count(w) for w in F12_WORDS)
            if f12_cnt > 6:
                print(f"  [F12·存量报告] 纸张鉴定词命中 {f12_cnt} 次 (仅报告, 供后续批次清理)")
        # F10 章题纪律: ①卷三—卷六 卷纲声明 vs 正典一致性(报告); ②自 ch141 起, 新章必须先声明于卷纲
        f10_hits = []
        if n < 141:
            for (a, b, of) in OUTLINE_SPANS:
                if a <= n <= b:
                    declared = load_outline_declared(of)
                    if n in declared and declared[n] != chapter_title(n):
                        f10_hits.append(f"卷纲{of}声明《{declared[n]}》≠ 正典《{chapter_title(n)}》(请在卷纲同步正典章题)")
        else:
            # 141-164 → outline-vol7.md; 165-188 → outline-vol8.md (新卷章题声明文件随卷演进)
            decl_file = "outline-vol7.md" if n <= 164 else "outline-vol8.md"
            decl_all = load_outline_declared(decl_file)
            if not decl_all:
                f10_hits.append(f"{decl_file} 缺失或未声明任何章题——ch141+ 章题必须先声明于 state/{decl_file}（声明章题后再跑查重）")
            elif n not in decl_all:
                f10_hits.append(f"第{n}章未在 {decl_file} 中声明——先补声明（`第{n}章《…》`）再跑查重")
            elif decl_all[n] != chapter_title(n):
                f10_hits.append(f"卷纲声明《{decl_all[n]}》≠ 正典《{chapter_title(n)}》——先统一章题")
            # 新章题不得与既有章重名 (标题行不入滑窗, 需单查)
            cur = chapter_title(n)
            if cur:
                dup = [m for m in range(1, n) if chapter_title(m) == cur]
                if dup:
                    f10_hits.append(f"章题《{cur}》与 ch{dup[0]} 重名——章题须全书唯一")
            # 弃用旧题禁引: 旧章题字符串不得在正文章题以外的正文出现(豁免项除外)
            for old in DEPRECATED:
                if old in DEPRECATED_EXEMPT_BODY:
                    continue
                c = body.count(old)
                if c:
                    f10_hits.append(f"正文回引弃用旧题「{old}」×{c}——以现行章题或指代替换")
        if f10_hits:
            fail += 1
            v6_issue = True
            print("  [F10·章题声明/旧题禁引]")
            for h in f10_hits:
                print(f"    × {h}")
        # F15·卷七/卷八回收链必备意象 (ch141-188): 每章须命中 REQ 表各组 token 至少一次
        # 卷七表= VOL7_REQ(foreshadowing「卷七回收规划区」), 卷八表= VOL8_REQ(outline-vol8 章眼/器物锚点)
        req_tbl = VOL8_REQ if 165 <= n <= 188 else VOL7_REQ
        if n in req_tbl:
            miss = []
            for grp in req_tbl[n]:
                if not any(w in body for w in grp):
                    miss.append("或".join(grp))
            if miss:
                fail += 1
                v6_issue = True
                print("  [F15·回收章必备意象缺失]")
                for m in miss:
                    print(f"    × 缺「{m}」——本章回收章眼未落位(同步见 foreshadowing 卷七回收规划区 / outline-vol8)")
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
        # (F8/F9/卷六词 命中已在各自块内 fail+=1 并打印; v6_issue 抑制误报 ✓)
        if not v6_issue and not (f_hits or d_hits or f4_hits or f6_hits or f7_hits or x_hits or i_hits):
            print("  ✓ 基线比对通过")
    # 卷级微型交易签名词报告 (每卷一次, 仅报告)
    if args and min(args) <= 140:
        vol_sig = {}
        for vn, (a, b) in enumerate([(1, 20), (21, 44), (45, 68), (69, 92), (93, 116), (117, 140)], 1):
            s = 0
            for m in range(a, b + 1):
                p = NOVEL / f"chapter-{m:02d}.md"
                if p.exists():
                    t = re.sub(r"^#.*$", "", norm(p.read_text(encoding="utf-8")), flags=re.M)
                    s += sum(t.count(w) for w in F11_SIG)
            vol_sig[vn] = s
        print("\n[F11·微型交易签名词按卷报告(仅报告)] " + " | ".join(f"卷{vn}:{s}" for vn, s in vol_sig.items()))
    sys.exit(1 if fail else 0)

if __name__ == "__main__":
    main()
