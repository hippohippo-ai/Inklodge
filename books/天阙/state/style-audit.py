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

章段来源：016 起的卷段沿用仓库既有口径（卷一 1—20，卷二 21—44，
卷三—卷十四各 24 章）。可 --vol N 单卷、--ch N 单章、--json 机读。
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
    }


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
    cols = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
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
    return f


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
    args = ap.parse_args()

    if args.ledger:
        rws = build(None, None)
        n = write_ledger(rws, load_progress())
        print("已写 state/style-revision-ledger.md（已改 %d / %d 章）" % (n, len(rws)))
        return 0

    rows = build(args.vol, set(args.ch) if args.ch else None)
    if not rows:
        print("没有命中任何章。", file=sys.stderr)
        return 1
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
