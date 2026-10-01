#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《天阙》文风审计探针（2026-09-30 立）

用途：把「文风是否统一、是否滑向现代网络小说（人物拽、对话龙傲天）」从
印象变成可复跑的清单。只报告，不判定、不改稿、不进 verify。

口径（按章统计，按卷汇总）：

  M1 感叹号密度      ！／万字            —— >0 即接近网文腔
  M2 破折号金句        ——（段末判语）／章  —— 判语腔主力信号
  M3 傲语标记          冷笑/哼/不屑/区区/找死/竟敢/蝼蚁… 命中
  M4 冷高人设标记      淡淡道/嘴角/不动声色/面无表情/莫测…
  M5 解释腔标记        也就是说/换句话说/这说明/说到底…
  M6 现代理性词        系统/数据/逻辑/机制/流程/标准/概率/成本/维度…
  M7 声纹账房化        含「账|算|数|名|册|簿」的台词占全部台词的比例
  M8 长台词            单条台词 >40 字的条数（说教／独白风险）
  M9 对话占比          引号内字数／全章字数

文笔级待修信号（2026-10-01 加，启发式·**只报告**，供逐章重写前先出清单）：
  M10 同章段落近重复    R4 待修：两叙述段 2-gram 容器相似度过高（同一场戏疑似写两遍）
  M11 章内复句          ≥6 字整句在**同章**出现 ≥2 次（同一动作拍重复）
  M12 段末金句/打分     叙述段末短句疑似金句或叙述打分（R3）
  M13 对白对仗收尾      台词末句疑似对仗／金句收尾（R5）
  M14 闪前提叙         叙述句含「…的时候/之后，…已经/已/是第一个」类前瞻＋已然（时序倒置候选）
  M15 昏倒后又发言      同一主体在致昏/离场标记后 ≤4 句内又发声（同一场戏里“先倒后说”候选）

章段来源：016 起的卷段沿用仓库既有口径（卷一 1—20，卷二 21—44，
卷三—卷十四各 24 章）。可 --vol N 单卷、--ch N 单章、--json 机读。

用法：`--todo` 只打印 R3/R4/R5 待修清单（配 --ch/--vol 选章），供逐章重写前
先出病灶位置；`--worklist` 写回炉工单 state/style-worklist.md（全 332 章按脏度排名
＋逐章可点链接＋前 40 勾选清单）；`--ledger` 写逐章台账；`--selftest` 跑 M13/M14/M15
判据回归用例；不带上述参数则照旧出九指标报告并写 state/style-audit.md／.csv。
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

try:  # Windows 控制台默认 cp1252，中文报告会崩
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)          # books/天阙
NOVEL = os.path.join(ROOT, "novel")
PROGRESS = os.path.join(HERE, "style-progress.json")
LEDGER = os.path.join(HERE, "style-revision-ledger.md")
WORKLIST = os.path.join(HERE, "style-worklist.md")
ONSETS = os.path.join(HERE, "character-onsets.json")   # 正典人物名+别名（M15 主体识别用）

# 记体白话目标带（见 style-spec.md §五）；用于标「待改信号」
TARGET = {"excl": 2.0, "mdash": 45.0, "jud": 3.5, "acct": 0.22,
          "quote_lo": 0.18, "quote_hi": 0.30}

# 与仓库既有卷段口径一致（outline.md 卷表 + F22 口径）
VOLS = [
    (1, 1, 20), (2, 21, 44), (3, 45, 68), (4, 69, 92), (5, 93, 116),
    (6, 117, 140), (7, 141, 164), (8, 165, 188), (9, 189, 212),
    (10, 213, 236), (11, 237, 260), (12, 261, 284), (13, 285, 308),
    (14, 309, 332),
]
VOLNAME = {
    1: "乱世初鸣", 2: "长安劫", 3: "洛阳龙蛇", 4: "河北三镇", 5: "名在纸上",
    6: "两命一名", 7: "灯下长安", 8: "长安烬", 9: "观天台", 10: "天衡",
    11: "三王天下", 12: "记危", 13: "登顶", 14: "放手",
}

W_傲语 = ["冷笑", "哼", "呵呵", "不屑", "区区", "找死", "竟敢", "蝼蚁",
          "雕虫小技", "不过如此", "狂妄", "配吗", "凭你", "放肆", "大胆",
          "跪下", "有眼无珠", "不知死活", "自不量力", "不自量力", "插翅难飞",
          "识相的", "你也配", "算什么东西"]
W_冷高 = ["淡淡道", "淡淡地", "淡淡的一", "冷冷地", "嘴角", "高深莫测", "深不可测",
          "莫测", "意味深长", "不动声色", "面无表情", "轻描淡写", "似笑非笑",
          "玩味", "深意", "定定地"]
W_解释 = ["也就是说", "换句话说", "换言之", "这说明", "这意味着", "说到底",
          "总而言之", "事实已经", "事实证明"]
W_判语 = ["毕竟", "本来", "其实", "总归", "终究", "这才是", "从来不是", "无非",
          "所谓的", "早已不是", "并不", "反而", "至少"]
W_现代 = ["系统", "数据", "逻辑", "效率", "机制", "流程", "标准", "概率", "成本",
          "维度", "价值观", "底线", "结构", "状态", "目标", "计划", "分析",
          "判断力", "心理", "空间", "信息", "资源", "环节", "层面", "属性",
          "能量", "实力", "级别", "团队", "项目", "方案", "策略"]

# ── 文笔级机械信号（R3 段末金句/打分、R4 同章重复、R5 对白对仗；2026-10-01 立）──
W_金句 = ["这世道", "到头来", "说到底", "终归", "无非", "不过如此", "从来都是",
          "活着的人都", "认得的人", "值几个钱"]
PAT_打分 = re.compile(r"(比[^，。！？；]{1,8}更|怎么[^，。！？；]{0,6}都|才[^，。！？；]{0,4}(?:算|是)|早[^，。！？；]{0,4}不是|不值|白搭)")
NARR_TAIL = re.compile(r"^(?P<a>[^，。！？；]{2,8})[，,](?P<b>[^，。！？；]{2,8})[。！？]?$")


def _clean(s):
    return re.sub(r"[\s“”‘’\"'（）()《》…—]", "", s)


def _parallel(a, b):
    """对仗度：**严格等长**是对仗的基本外形（否则 0）；共字≥2 记 2.0；
    共字 1 且含否定对立记 1.5；共字 1 其余记 1.0。≥1.5 视为对仗。"""
    if len(a) < 3 or len(b) < 3 or len(a) != len(b):
        return 0.0
    common = len(set(a) & set(b))
    if common == 0:
        return 0.0
    if common >= 2:
        return 2.0
    neg = lambda x: ("不" in x) or ("没" in x) or ("无" in x) or ("莫" in x)
    return 1.5 if neg(a) != neg(b) else 1.0


def _last_sent(seg):
    ps = [p for p in re.split(r"[。！？!?…]", seg) if p.strip()]
    return ps[-1].strip() if ps else ""


def sig_r4_dup(txt):
    """同章段落近重复：对 2-gram 取容器相似度，返回 (最高相似, 命中对数, 样例)。
    只比**清洗后 ≥20 字**的叙述段，且交集 ≥6 才算命中（防短段共字虚高）。"""
    narr = []
    for p in re.split(r"\n\s*\n", txt):
        p = p.strip()
        if p.startswith("“"):
            continue
        c = _clean(p)
        if len(c) >= 20:
            narr.append((c, p))
    sh = [({c[i:i + 2] for i in range(len(c) - 1)}, c) for c, _ in narr]
    best, hits, sample = 0.0, 0, ""
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            a, b = sh[i][0], sh[j][0]
            if not a or not b:
                continue
            inter = len(a & b)
            if inter < 6:
                continue
            cont = inter / min(len(a), len(b))
            best = max(best, cont)
            if cont >= 0.42:
                hits += 1
                if not sample:
                    sample = narr[i][1][:24] + " ／ " + narr[j][1][:24]
    return round(best, 2), hits, sample


def sig_r4_sent(txt):
    """章内复句：≥6 字整句在同章出现 ≥2 次。返回 (重复余数, 样例)。"""
    sents = [s.strip() for s in re.split(r"[。！？!?…\n]", txt)]
    c = defaultdict(int)
    for s in sents:
        k = _clean(s)
        if len(k) >= 6:
            c[k] += 1
    rep = {k: v for k, v in c.items() if v >= 2}
    return sum(v - 1 for v in rep.values()), list(rep)[:3]


def sig_r3_judge(txt):
    """叙述段末短句疑似金句/叙述打分（R3）。返回命中末句列表。"""
    paras = [p.strip() for p in re.split(r"\n\s*\n", txt) if p.strip()]
    hits = []
    for p in paras:
        if p.startswith("“"):
            continue
        last = _last_sent(p)
        if not last or len(_clean(last)) > 18:
            continue
        m = NARR_TAIL.match(last)
        if m and _parallel(m.group("a"), m.group("b")) >= 1.5:
            hits.append(last)
            continue
        if PAT_打分.search(last) or any(w in last for w in W_金句):
            hits.append(last)
    return hits


def sig_r5_dui(txt):
    """台词末句疑似对仗/金句收尾（R5）。返回命中末句列表。"""
    quotes = [q.strip() for q in QUOTE_RE.findall(txt) if q.strip()]
    hits = []
    for q in quotes:
        last = _last_sent(q)
        if not last:
            continue
        m = NARR_TAIL.match(last)
        if m and _parallel(m.group("a"), m.group("b")) >= 1.5:
            hits.append(last)
            continue
        if any(w in last for w in W_金句):
            hits.append(last)
    return hits


# ── 连续性信号（M14 闪前提叙、M15 昏倒/离场后又发言；2026-10-01 加，启发式·只报告）──
# 「…的时候/之后，…」多数是同时态（正常），故只认**已然＋人物动作**（不是状态“挂着/亮着/死了”）才算闪前。
FLASH_ACT = (r"(?:是第一个|是头一个|头一个|已经走|已走|已经退|已退|已经离|已离|"
             r"已经出|已出|已经进|已进|已经跑|已跑|已经冲|已冲|已经动手|"
             r"已经拔|已拔|已经掀|已掀|已经踢|已踢|已经丢下|已经不见了)")
FLASH_RE1 = re.compile(r"[^，。！？；]{2,14}(?:的时候|之时|之后)[，,][^，。！？；]{0,20}" + FLASH_ACT)
FLASH_RE2 = re.compile(r"^(?:后来|随后|事后|不久之后|这之后)[^，。！？；]{0,30}" + FLASH_ACT)

COLLAPSE = ["昏过去", "昏倒", "昏迷", "晕过去", "不省人事", "人事不省", "没了声息",
            "没了动静", "断了气", "气绝", "咽气", "软下去", "软了半边", "软倒",
            "栽倒", "合上眼", "闭上眼", "没了气息"]
EXIT_STRONG = ["端着钱走了", "转身走了", "转身离开", "头也不回",
               "抬了出去", "退到门外", "被抬出去", "拖了出去"]
REACT = ["又笑", "忽然笑", "又开口", "又说话", "又咳", "又喊", "又叫道",
         "忽然开口", "忽然说", "忽然又问", "又问道", "又答", "又骂",
         "笑出了声", "又笑了", "又叹"]
_NAME_RE = re.compile(r"([\u4e00-\u9fa5]{2,3})(?:说|道|问|喊|笑|答|吼|骂|劝|叹)")


def _sentences(txt):
    out = []
    for p in re.split(r"\n\s*\n", txt):
        for s in re.split(r"(?<=[。！？!?…])", p.strip()):
            s = s.strip()
            if s:
                out.append(s)
    return out


_CHARNAMES = None


def char_names():
    """正典人物名＋别名（读 state/character-onsets.json；缺失时返回空集）。"""
    global _CHARNAMES
    if _CHARNAMES is None:
        ns = set()
        try:
            with open(ONSETS, encoding="utf-8") as f:
                d = json.load(f)
            for c in d.get("characters", []):
                if c.get("name"):
                    ns.add(c["name"])
                for a in (c.get("aliases") or []):
                    ns.add(a)
        except Exception:
            pass
        _CHARNAMES = ns
    return _CHARNAMES


def _names(txt):
    """本章出现的人物名：正典名/别名 ∪ 「名字+说/道/问…」抽取，滤掉代词/虚字。"""
    ns = set(char_names())
    for n in _NAME_RE.findall(txt):
        if 2 <= len(n) <= 3 and not any(c in n for c in "他她你我它人这那"):
            ns.add(n)
    return {n for n in ns if n in txt}


def sig_flash(txt):
    """M14 闪前提叙候选：叙述句含「…的时候/之后，…已经/已/是第一个」类前瞻＋已然。"""
    hits = []
    for s in _sentences(txt):
        if s.startswith("“"):
            continue
        if FLASH_RE1.search(s) or FLASH_RE2.match(s):
            hits.append(s[:34])
    return hits


def sig_recollapse(txt):
    """M15 昏倒/离场后又发言候选：同一主体在致昏/离场标记后 ≤4 句内又发声。"""
    sents = _sentences(txt)
    names = _names(txt)
    hits = []
    for i, s in enumerate(sents):
        if s.startswith("“"):
            continue
        marker = next((m for m in COLLAPSE + EXIT_STRONG if m in s), None)
        if not marker:
            continue
        subj = None
        for k in range(i, max(-1, i - 3), -1):
            found = sorted((n for n in names if n in sents[k]), key=len, reverse=True)
            if found:
                subj = found[0]
                break
        if not subj:
            continue
        for j in range(i, min(i + 5, len(sents))):
            t = sents[j]
            if subj in t and any(r in t for r in REACT):
                hits.append("%s：%s → %s" % (subj, marker, t[:28]))
                break
    return hits

QUOTE_RE = re.compile(r"[“](.*?)[”]", re.S)
SPLIT_SENT = re.compile(r"[。！？!?…]+")
# 对话段：以 “ 开头的段落
DIALOG_SEG = re.compile(r"^[“](.*)$", re.S)


def vol_of(ch):
    for v, a, b in VOLS:
        if a <= ch <= b:
            return v
    return 0


def read_chapter(ch):
    p = os.path.join(NOVEL, "chapter-%02d.md" % ch)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        txt = f.read()
    # 去 H1 章题行
    txt = re.sub(r"(?m)^#\s.*$", "", txt)
    return txt


def count_hits(txt, words):
    n = 0
    hit_chars = 0
    for w in words:
        c = txt.count(w)
        if c:
            n += c
            hit_chars += c * len(w)
    return n


def audit_chapter(ch):
    txt = read_chapter(ch)
    if txt is None:
        return None
    body = re.sub(r"\s+", "", txt)          # 与 F22 同口径：去空白
    nchar = len(body)
    if nchar == 0:
        return None

    # 台词
    quotes = [q.strip() for q in QUOTE_RE.findall(txt) if q.strip()]
    quote_chars = sum(len(re.sub(r"\s+", "", q)) for q in quotes)
    nq = len(quotes)
    long_q = sum(1 for q in quotes if len(re.sub(r"\s+", "", q)) > 40)
    max_q = max((len(re.sub(r"\s+", "", q)) for q in quotes), default=0)

    # 段落切分（保留引号段落归属判断）
    paras = [p.strip() for p in re.split(r"\n\s*\n", txt) if p.strip()]
    dialogue_paras = [p for p in paras if p.startswith("“")]

    # M7 声纹账房化：含账目词的台词占比
    acct_q = sum(1 for q in quotes if re.search(r"[账算数名册簿条例籍]", q))
    m7 = acct_q / nq if nq else 0.0

    # M2 破折号：统计「——」且在段末/句末的判语用法（粗略：全部 —— 计数）
    mdash = txt.count("——")

    # ── 文笔级信号（R3/R4/R5；2026-10-01 加，启发式·只报告）──
    r4_best, r4_hits, r4_sample = sig_r4_dup(txt)
    r4_sent, r4_sent_samp = sig_r4_sent(txt)
    r3_hits = sig_r3_judge(txt)
    r5_hits = sig_r5_dui(txt)
    r6_hits = sig_flash(txt)
    r7_hits = sig_recollapse(txt)

    per_wan = lambda n: round(n * 10000.0 / nchar, 2)

    return {
        "ch": ch,
        "vol": vol_of(ch),
        "chars": nchar,
        "quote_n": nq,
        "quote_share": round(quote_chars / nchar, 3),
        "quote_mean": round(quote_chars / nq, 1) if nq else 0.0,
        "long_q": long_q,
        "max_q": max_q,
        "excl": txt.count("！") + txt.count("!"),
        "excl_per_wan": per_wan(txt.count("！") + txt.count("!")),
        "mdash": mdash,
        "mdash_per_wan": per_wan(mdash),
        "w1": count_hits(txt, W_傲语),
        "w2": count_hits(txt, W_冷高),
        "w5": count_hits(txt, W_解释),
        "w6": count_hits(txt, W_判语),
        "w7": count_hits(txt, W_现代),
        "acct_share": round(m7, 3),
        "w1_per_wan": per_wan(count_hits(txt, W_傲语)),
        "w2_per_wan": per_wan(count_hits(txt, W_冷高)),
        "w5_per_wan": per_wan(count_hits(txt, W_解释)),
        "w6_per_wan": per_wan(count_hits(txt, W_判语)),
        "w7_per_wan": per_wan(count_hits(txt, W_现代)),
        "r4_dup": r4_best,
        "r4_dup_hits": r4_hits,
        "r4_sent": r4_sent,
        "r3_judge": len(r3_hits),
        "r5_dui": len(r5_hits),
        "r4_dup_sample": r4_sample,
        "r4_sent_samples": r4_sent_samp,
        "r3_samples": r3_hits[:6],
        "r5_samples": r5_hits[:6],
        "r6_flash": len(r6_hits),
        "r7_recollapse": len(r7_hits),
        "r6_samples": r6_hits[:6],
        "r7_samples": r7_hits[:6],
    }


# ── 自测用例（`--selftest`）：回归三个易调错信号的判据，防调参把探针调死 ──
SELFTEST = [
    ("M13 对白对仗·真", lambda: bool(sig_r5_dui("“牌抵不了账，活人才欠账。”"))),
    ("M13 对白对仗·假", lambda: not sig_r5_dui("“你吃饭了吗。”")),
    ("M14 闪前·真", lambda: bool(sig_flash("火起的时候，那个第三个人是第一个退到门外的。"))),
    ("M14 闪前·假(同时态)", lambda: not sig_flash("沈广农到的时候，铺子外的白幡已经挂起来了。")),
    ("M15 昏后又言·真", lambda: bool(sig_recollapse("席横的嘴唇动了动。人软了半边。沈广农把头扶正。半刻之后，席横忽然又笑，笑到一半变成咳。"))),
    ("M15 昏后又言·假", lambda: not sig_recollapse("沈广农倒下。他闭着眼。李承洲说：“撤。”")),
]


def run_selftest():
    ok = 0
    for name, fn in SELFTEST:
        try:
            good = bool(fn())
        except Exception:
            good = False
        print("  %s %s" % ("✓" if good else "✗", name))
        ok += 1 if good else 0
    print("自测：%d/%d 通过" % (ok, len(SELFTEST)))
    return 0 if ok == len(SELFTEST) else 1


def pct(vals, p):
    vals = sorted(vals)
    if not vals:
        return 0
    i = int(round((len(vals) - 1) * p))
    return vals[i]


def build(vol_filter=None, ch_filter=None):
    rows = []
    for ch in range(1, 333):
        if ch_filter and ch not in ch_filter:
            continue
        if vol_filter and vol_of(ch) != vol_filter:
            continue
        r = audit_chapter(ch)
        if r:
            rows.append(r)
    return rows


def summarize(rows):
    byvol = defaultdict(list)
    for r in rows:
        byvol[r["vol"]].append(r)
    out = []
    for v in sorted(byvol):
        rs = byvol[v]
        m = lambda k: round(sum(r[k] for r in rs) / len(rs), 3)
        out.append({
            "vol": v, "name": VOLNAME.get(v, ""), "n": len(rs),
            "chars": int(m("chars")),
            "quote_share": m("quote_share"),
            "quote_mean": m("quote_mean"),
            "long_q": round(m("long_q"), 2),
            "excl_per_wan": round(m("excl_per_wan"), 2),
            "mdash_per_wan": round(m("mdash_per_wan"), 2),
            "w1_per_wan": round(m("w1_per_wan"), 3),
            "w2_per_wan": round(m("w2_per_wan"), 3),
            "w5_per_wan": round(m("w5_per_wan"), 3),
            "w6_per_wan": round(m("w6_per_wan"), 3),
            "w7_per_wan": round(m("w7_per_wan"), 3),
            "acct_share": m("acct_share"),
            "w1_total": sum(r["w1"] for r in rs),
            "w2_total": sum(r["w2"] for r in rs),
            "w5_total": sum(r["w5"] for r in rs),
            "w6_total": sum(r["w6"] for r in rs),
            "w7_total": sum(r["w7"] for r in rs),
        })
    return out


def write_csv(rows, path):
    # 跳过列表/字典/样例字段，CSV 只存数值列
    cols = [k for k, v in rows[0].items()
            if not isinstance(v, (list, dict)) and not k.endswith("_samples") and not k.endswith("_sample")]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def top(rows, key, n=12, reverse=True):
    return sorted(rows, key=lambda r: r[key], reverse=reverse)[:n]


def fmt_report(rows, summ):
    L = []
    L.append("# 《天阙》文风审计报告（生成物·勿手改）\n")
    L.append("> 探针：`state/style-audit.py`　复跑：`python state/style-audit.py`（或 `npm run scan:style`）")
    L.append("> 口径：按章统计九项（见脚本头）。**只报告，不判定，不改稿**；判定权在人。")
    L.append("> 生成时间口径：以当前 `novel/` 正文为准。\n")

    L.append("## 一、按卷指纹（统一性一眼表）\n")
    L.append("| 卷 | 卷名 | 章 | 均字 | 对话占比 | 均台词长 | ！/万 | ——/万 | 傲语/万 | 冷高/万 | 解释/万 | 判语/万 | 现代词/万 | 台词账房化 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for s in summ:
        L.append("| %d | %s | %d | %d | %.2f | %.1f | %.2f | %.2f | %.3f | %.3f | %.3f | %.3f | %.3f | %.2f |" % (
            s["vol"], s["name"], s["n"], s["chars"], s["quote_share"], s["quote_mean"],
            s["excl_per_wan"], s["mdash_per_wan"], s["w1_per_wan"], s["w2_per_wan"],
            s["w5_per_wan"], s["w6_per_wan"], s["w7_per_wan"], s["acct_share"]))
    L.append("")

    L.append("## 二、全库分布（本书自己的内标）\n")
    for k, label in [("quote_share", "对话占比"), ("quote_mean", "均台词长"),
                     ("mdash_per_wan", "——密度/万"), ("excl_per_wan", "感叹号/万"),
                     ("w6_per_wan", "判语/万"), ("w7_per_wan", "现代词/万"),
                     ("acct_share", "台词账房化")]:
        vals = [r[k] for r in rows]
        L.append("- **%s**：p10 %.3f／p50 %.3f／p90 %.3f／max %.3f" % (
            label, pct(vals, .10), pct(vals, .50), pct(vals, .90), max(vals)))
    L.append("")

    L.append("## 三、离群章（逐章修正的优先名单）\n")

    def block(title, key, note, rev=True, n=10):
        L.append("### %s\n" % title)
        L.append("| 章 | 卷 | 值 | %s |" % note)
        L.append("|---|---|---|---|")
        for r in top(rows, key, n, rev):
            L.append("| ch%d | %d | %s | |" % (r["ch"], r["vol"], r[key]))
        L.append("")

    block("A · 台词最长（说教/独白风险）", "max_q", "最长台词字数")
    block("B · 长台词最多", "long_q", ">40 字台词条数")
    block("C · 破折号判语最密", "mdash_per_wan", "——/万字")
    block("D · 判语词最密", "w6_per_wan", "判语/万字")
    block("E · 现代理性词最密", "w7_per_wan", "现代词/万字")
    block("F · 傲语标记（龙傲天安检）", "w1", "傲语命中")
    block("G · 冷高人设标记", "w2", "冷高命中")
    block("H · 感叹号最多（网文腔安检）", "excl_per_wan", "！/万字")
    block("I · 台词账房化最重", "acct_share", "账目词台词占比")

    L.append("## 三之二、文笔级待修信号（R3/R4/R5＋连续性·机械清单）\n")
    L.append("> 2026-10-01 加。**启发式，只报告**：逐章重写前先读这份清单定位病灶；命中不等于有病，须人读上下文。")
    L.append("> R4 近重复对 = 两叙述段 2-gram 容器相似度 ≥0.42 的对数（同场戏疑似写两遍）；R4 复句 = ≥6 字整句在同章重复的次数；")
    L.append("> R3 金句 = 叙述段末短句疑似金句/叙述打分；R5 对白对仗 = 台词末句疑似对仗/金句收尾；")
    L.append("> 闪前 = 叙述句含「…的时候/之后，…已经/已/是第一个」（时序倒置候选）；复言 = 同一主体致昏/离场后 ≤4 句内又发声。\n")
    flagged = [r for r in rows if r["r3_judge"] or r["r4_dup_hits"] or r["r4_sent"]
               or r["r5_dui"] or r["r6_flash"] or r["r7_recollapse"]]
    if not flagged:
        L.append("- （全库无命中）")
    for r in flagged:
        L.append("- **ch%d**(卷%d)：R3 金句 %d／R4 近重复对 %d（最高相似 %.2f）／R4 复句 %d／R5 对白对仗 %d／闪前 %d／复言 %d"
                 % (r["ch"], r["vol"], r["r3_judge"], r["r4_dup_hits"],
                    r["r4_dup"], r["r4_sent"], r["r5_dui"], r["r6_flash"], r["r7_recollapse"]))
        for s in (r["r3_samples"] + r["r5_samples"] + r["r6_samples"] + r["r7_samples"])[:3]:
            L.append("  - 例：「%s」" % s)
    L.append("")

    L.append("## 四、傲语／冷高逐处定位（全库命中章）\n")
    L.append("> 供逐章修正时直接检索。傲语（w1）与冷高（w2）是「拽」的两条最直观信号。\n")
    for r in rows:
        if r["w1"] or r["w2"]:
            L.append("- **ch%d**(卷%d)：傲语 %d／冷高 %d" % (r["ch"], r["vol"], r["w1"], r["w2"]))
    if not any(r["w1"] or r["w2"] for r in rows):
        L.append("- （全库无命中）")
    L.append("")

    L.append("## 五、纪律\n")
    L.append("1. 本探针**只报告**：不进 `verify`、不进预提交钩子、不判失败。")
    L.append("2. 「傲语命中」多为叙述里的「冷笑／哼」，不等于台词有病——**必须人读上下文**再判。")
    L.append("3. 「现代词」按字面统计，制度语境（如「名册／标准／流程」）可能合法，逐处人判。")
    L.append("4. 逐章修正后重跑本探针，看的是**同章前后 delta**，不是绝对带（另见 `style-spec.md`）。")
    return "\n".join(L)


def load_progress():
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def signals(r):
    """返回本章当前未达标的信号列表（空 = 已在带内）。"""
    f = []
    if r["excl_per_wan"] > TARGET["excl"]:
        f.append("！%g" % r["excl_per_wan"])
    if r["mdash_per_wan"] > TARGET["mdash"]:
        f.append("——%g" % r["mdash_per_wan"])
    if r["w6_per_wan"] > TARGET["jud"]:
        f.append("判语%g" % r["w6_per_wan"])
    if r["acct_share"] > TARGET["acct"]:
        f.append("账房%.2f" % r["acct_share"])
    if r["quote_share"] < TARGET["quote_lo"]:
        f.append("对白少%.2f" % r["quote_share"])
    elif r["quote_share"] > TARGET["quote_hi"]:
        f.append("对白多%.2f" % r["quote_share"])
    # 文笔级待修信号（R3/R4/R5；0 不列）
    if r.get("r4_dup_hits"):
        f.append("R4近重复%d" % r["r4_dup_hits"])
    if r.get("r4_sent"):
        f.append("R4复句%d" % r["r4_sent"])
    if r.get("r3_judge"):
        f.append("R3金句%d" % r["r3_judge"])
    if r.get("r5_dui"):
        f.append("R5对仗%d" % r["r5_dui"])
    if r.get("r6_flash"):
        f.append("闪前%d" % r["r6_flash"])
    if r.get("r7_recollapse"):
        f.append("复言%d" % r["r7_recollapse"])
    return f


def work_score(r):
    """回炉脏度：R3/R4/R5 为主，兼记连续性（权重可调）。"""
    return (3 * r["r3_judge"] + 4 * r["r4_dup_hits"] + 2 * r["r4_sent"]
            + 3 * r["r5_dui"] + 2 * r["r6_flash"] + 4 * r["r7_recollapse"])


def write_worklist(rows, prog):
    """回炉工单：全章按脏度排名＋可点击链接＋优先清单（生成物）。"""
    wroot = "books/" + os.path.basename(ROOT)          # 工作区根相对路径（应用内可点）
    link = lambda ch: "[ch%d](%s/novel/chapter-%02d.md)" % (ch, wroot, ch)
    scored = sorted(rows, key=lambda r: (-work_score(r), -r["r4_dup_hits"],
                                          -r["r5_dui"], -r["r3_judge"], r["ch"]))
    nz = [r for r in scored if work_score(r) > 0]
    done = [r for r in rows if "已改" in str(prog.get(str(r["ch"]), {}).get("status", ""))]
    full = [r for r in rows if "文笔级" in str(prog.get(str(r["ch"]), {}).get("status", ""))]
    L = ["# 《天阙》回炉工单（R3/R4/R5＋连续性·生成物）\n",
         "> 生成：`python state/style-audit.py --worklist`。**全 332 章排名，不抽样、不漏章。**",
         "> 脏度 = R3金句×3 ＋ R4近重复对×4 ＋ R4复句×2 ＋ R5对仗×3 ＋ 闪前×2 ＋ 复言×4（权重可调）。",
         "> 信号只报**候选**，命中不等于有病；已「文笔级已改」的章排次仅供参考（大多已洗过 R3/R4/R5）。",
         "> 章名可点击（工作区根相对路径）：`%s/novel/chapter-NN.md`。\n" % wroot,
         "进度：**已改 %d / %d 章**（文笔级 %d 章）；有命中的章 %d 章。\n"
         % (len(done), len(rows), len(full), len(nz)),
         "| 序 | 章 | 卷 | 字 | R3金句 | R4近重复 | R4复句 | R5对仗 | 闪前 | 复言 | 脏度 | 状态 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(scored, 1):
        st = prog.get(str(r["ch"]), {}).get("status", "未过")
        L.append("| %d | %s | %d | %d | %d | %d | %d | %d | %d | %d | **%d** | %s |" % (
            i, link(r["ch"]), r["vol"], r["chars"], r["r3_judge"], r["r4_dup_hits"],
            r["r4_sent"], r["r5_dui"], r["r6_flash"], r["r7_recollapse"],
            work_score(r), st))
    L.append("")
    L.append("## 优先清单（脏度前 40 · 勾选即开工）\n")
    for r in scored[:40]:
        st = prog.get(str(r["ch"]), {}).get("status", "未过")
        marks = []
        if r["r4_dup_hits"]:
            marks.append("近重复%d" % r["r4_dup_hits"])
        if r["r3_judge"]:
            marks.append("金句%d" % r["r3_judge"])
        if r["r5_dui"]:
            marks.append("对仗%d" % r["r5_dui"])
        if r["r4_sent"]:
            marks.append("复句%d" % r["r4_sent"])
        if r["r6_flash"]:
            marks.append("闪前%d" % r["r6_flash"])
        if r["r7_recollapse"]:
            marks.append("复言%d" % r["r7_recollapse"])
        L.append("- [ ] %s（卷%d·脏度 **%d**）：%s　—　%s" % (
            link(r["ch"]), r["vol"], work_score(r), "、".join(marks) or "—", st))
    L.append("")
    with open(WORKLIST, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return len(nz)


def write_ledger(rows, prog):
    L = []
    done = [r for r in rows if "已改" in str(prog.get(str(r["ch"]), {}).get("status", ""))]
    full = [r for r in rows if "文笔级" in str(prog.get(str(r["ch"]), {}).get("status", ""))]
    L.append("# 《天阙》文风精修台账（逐章·生成物）\n")
    L.append("> 生成：`python state/style-audit.py --ledger`。**全 332 章逐章登记，不抽样、不漏章。**")
    L.append("> 状态源：`state/style-progress.json`（人工登记，探针不代写）；指标读当前正文实时值。")
    L.append("> 「待改信号」为空 = 本章已在记体白话目标带内（见 `style-spec.md` §五）。已改章仍列信号，便于回查。\n")
    L.append("进度：**已改 %d / %d 章**（其中**文笔级已改 %d 章**；其余为「表层已改」，待文笔级复修）。\n"
             % (len(done), len(rows), len(full)))
    L.append("| 章 | 卷 | 字 | ！/万 | ——/万 | 判语/万 | 账房化 | 对白 | 待改信号 | 状态 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        p = prog.get(str(r["ch"]), {})
        st = p.get("status", "未过")
        sig = "、".join(signals(r)) or "✓"
        L.append("| ch%d | %d | %d | %.2f | %.2f | %.2f | %.2f | %.2f | %s | %s |" % (
            r["ch"], r["vol"], r["chars"], r["excl_per_wan"], r["mdash_per_wan"],
            r["w6_per_wan"], r["acct_share"], r["quote_share"], sig, st))
    with open(LEDGER, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return len(done)


def main():
    ap = argparse.ArgumentParser(description="《天阙》文风审计探针（只报告）")
    ap.add_argument("--vol", type=int, help="只跑某卷")
    ap.add_argument("--ch", type=int, nargs="*", help="只跑某几章")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write", action="store_true", help="只上屏，不写报告/csv")
    ap.add_argument("--ledger", action="store_true", help="写逐章精修台账 style-revision-ledger.md")
    ap.add_argument("--todo", action="store_true", help="只打印 R3/R4/R5 待修清单（配 --ch/--vol 选章）")
    ap.add_argument("--selftest", action="store_true", help="跑内置判据回归用例（M13/M14/M15）")
    ap.add_argument("--worklist", action="store_true", help="写回炉工单 style-worklist.md（全章排名＋可点链接）")
    args = ap.parse_args()

    if args.selftest:
        return run_selftest()

    if args.ledger:
        rws = build(None, None)
        n = write_ledger(rws, load_progress())
        print("已写 state/style-revision-ledger.md（已改 %d / %d 章）" % (n, len(rws)))
        return 0

    if args.worklist:
        rws = build(None, None)
        n = write_worklist(rws, load_progress())
        print("已写 state/style-worklist.md（有命中 %d / %d 章）" % (n, len(rws)))
        return 0

    rows = build(args.vol, set(args.ch) if args.ch else None)
    if not rows:
        print("没有命中任何章。", file=sys.stderr)
        return 1

    if args.todo:
        for r in rows:
            print("ch%d（卷%d）" % (r["ch"], r["vol"]))
            dup = r["r4_dup_sample"] or "—"
            print("  R4 同场近重复 %d 对（最高相似 %.2f）：%s" % (r["r4_dup_hits"], r["r4_dup"], dup))
            print("  R4 章内复句 %d：%s" % (r["r4_sent"], "；".join(r["r4_sent_samples"]) or "—"))
            print("  R3 段末金句/打分 %d：%s" % (r["r3_judge"], "；".join("「%s」" % s for s in r["r3_samples"]) or "—"))
            print("  R5 对白对仗收尾 %d：%s" % (r["r5_dui"], "；".join("「%s」" % s for s in r["r5_samples"]) or "—"))
            print("  M14 闪前提叙 %d：%s" % (r["r6_flash"], "；".join("「%s」" % s for s in r["r6_samples"]) or "—"))
            print("  M15 昏后又言 %d：%s" % (r["r7_recollapse"], "；".join("「%s」" % s for s in r["r7_samples"]) or "—"))
        return 0

    summ = summarize(rows)

    if args.json:
        import json
        print(json.dumps({"summary": summ, "chapters": rows}, ensure_ascii=False, indent=2))
    else:
        rep = fmt_report(rows, summ)
        print(rep)
        if not args.no_write:
            with open(os.path.join(HERE, "style-audit.md"), "w", encoding="utf-8") as f:
                f.write(rep + "\n")
            write_csv(rows, os.path.join(HERE, "style-audit.csv"))
            print("\n[已写] state/style-audit.md / state/style-audit.csv", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
