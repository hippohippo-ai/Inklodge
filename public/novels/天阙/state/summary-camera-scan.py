#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""总结式镜头探针 v2（2026-09-23，源：作者「文笔太平」判定 ch294 医伤段）

■ 先说边界（v1 试错结论，勿再走回头路）
「平」不是一个词表能判的东西。实测三种自动口径都失败：
  · 词表法（具体落点名 vs 抽象压缩词）——「炒豆」「膝盖」是被**点名**的实物，
    不是被**写出**的实物；点名与写出的差别不在字面，机器分不出。原文段落含
    「炒豆／膝盖」两个实物词，任何词表都要判它"有落点"。
  · 句长/分句长度方差——实测 ch294 句长 CV 0.666 > 全书中位 0.625，量不出。
  · 「说了一句：」家族——全书 40+ 处抽样全部是合法的对白标签（后接真实台词），
    唯一那处「平」是**无引号的短判语**，只能靠人眼从标签里挑出来。
结论：本探针**不做判定**，只按三个低噪声家族出**候选清单**，由人逐条判改／留。
（v1 的词表判定已废，勿恢复。）

■ v3 增补（2026-09-23）：寄存器偏差 —— 密度测量的口径必须两个寄存器都收
v2 的 CONCRETE 只收市井／身体／触觉词（膝盖、油纸、豆、烫、硌），在**文书—军府—
书案**这一路上系统性漏数（印面、印泥、火漆、封筒、篆字、舆图、簿页、钥匙、靴底……
全不在表内）。后果实测：ch151《私印》改写后按 v2 口径只有 2.5（判为"制度章撞天花板"），
补入 REG2 寄存器后同一文本是 **4.82，超过卷七 p90＝4.64**——"天花板"是量具的，
不是稿子的。
→ 自 v3 起，**密度一律用 REG2_COMB（两寄存器合并）**；CONCRETE 单独口径只作对照，
  不再作为判定依据。已有的"缺口榜"已按新口径重排（旧榜里 ch151 的"1.5 极平"是假报警）。
■ v4 增补（2026-09-23）：兵器／身体／建筑／行程寄存器 —— 同一偏差的第三次补洞
v3 合并后仍漏三类：①兵器（剑、鞘、刃、锋、盾、甲、箭——本书是剑宗戏，ch104 一场对决
全用剑，却一个都数不到）；②织物／身体（帕、头发、袖、伤）；③建筑／行程（柱、梁、门槛、
墙、瓦罐、车辙、轱辘）。实测：ch104《宁红叶》按 v3 只有 2.01。
→ 自 v4 起 REG3 并入主口径。**量具到此冻结（v4）**——只允许在“整整一类物体被漏掉”时
  再补一次，不再随单章结果调词；判定权在人，不在词表（本文件头部铁律）。

■ v5 增补（2026-09-24）：第四家族 D 解释腔
来源：路线 A 第三—五批里，同一类毛病在**互不相关的三章**各撞一次——ch78 的「这意味着」、
ch90 的「救三笔／卖三笔」先归纳后整段复述、ch258 的「事实已经不是一道可以凭更多证据推开的门」。
它不是密度问题（那三章密度都不低），是**叙述者的站位问题**：作者在读者已经看过之后，
再站出来把意思讲一遍。密度量不到它，句长/对白占比也量不到——所以单列一-family。

  D 解释腔 —— 两个亚型：
    D1 连接词标记 —— 叙述段（非对白）出现「这意味着／这说明／也就是说／换句话说／换言之／
       换个说法／说到底／总而言之／事实已经／事实就是」等**解释性连接词**（D1a；
       旧词表里的「一句话：」「从头到尾」已降为 D1b 惯用语，只计数不报——理由见代码旁注释）。
       判定纪律：**不是一见就改**。若后面接的是**从实物推出的新信息**（「撕口避开了三个
       地名——也就是说，动图的手比孙驼子更早」），那是推理，保留；若接的是**读者刚看过
       的东西的翻版**，则是解释腔，改。
    D2 复述式概括 —— 章内段对：两段都 ≥35 字、相隔 ≥5 段、短段 4-gram 有 ≥55% 落在长段内
       （containment；不用 difflib 精确 ratio，全书 332 章要跑得完）。这是「把已演过的情节
       再概括一遍」的机械代理——第三轮用 difflib 0.50 扫出 29 章，本家族与它同源但更省。
       已知假阳：章末「书挡回证」（如 ch308）是有意呼应，判保留。
       ★ v5 已量清的**能力边界**（勿当成 bug 去调参）：D2 只看得见**近逐字**复述
       （ch315 型）。ch90 那种**改写式复述**它看不见——实测 ch90 含「三笔」的 12 段两两做
       containment，最高只有 **0.33**（「你救了三笔，卖了三笔……救的是逃兵、孤儿、伤兵」× 「救人的
       陈启和卖人的陈启，是同一个陈启……不能因为救了三笔就抵掉卖的三笔」）。这一段是**对白里**
       的三重复述，改写的幅度大到 4-gram 覆盖不到。**改写式复述只能人眼读**，这就是路线 A
       每章必须整章读一遍的理由；探针在这里只是路标，不是闸门。

■ 三个家族
  A 枚举清单   —— 「她学会了三件事：…」「做惯了两件事：…」把后文将演示的内容先概说。
  B 段尾判语   —— 叙述段最后一句、无引号、≤30 字、含评价副词（到底/毕竟/总归/难怪…），
                  即借旁人之口给人物定级（「到底是从外头回来的先生，懂分寸」）。
  C 长段无落点 —— 叙述段 ≥150 字、无对白、具体实物词 ≤2：疑似通篇动作报告，
                  需人眼读一遍确认（此家族最粗，只作筛选）。

■ v5 报告模式（2026-09-24）：家族 D 按卷出「待裁可」清单
  `d` 模式把 D 家族候选按卷列出来，每条带**判定栏**供作者逐条裁可，并把已裁事项
  写在 D_LEDGER 里——**已裁的不重复受理**。台账按「章号＋家族＋锚点」匹配，
  不按段号（段号会随归治与改写漂移）；如果某条的**锚点在正文里找不到了**，
  说明该处已被改掉或整章重写——报告会单列出来，这正是“已消除”的证据。
  同时把结果写进 `state/d-family-report.md`（可复跑盖写，数字全部现场重算）。

  另：D3 改写式复述（difflib ratio ≥0.50 且 4-gram containment <0.55）
  是对 D2 盲区的**补位参考**，不列入判定清单——它假阳率高（章末回证、双人拉扯
  都会被抓），只有人眼能分。ch322／ch323 的残余就是靠它才显形的。

用法：
  python state/summary-camera-scan.py            # 全书按卷汇总（四家族）
  python state/summary-camera-scan.py --vol 1    # 单卷明细
  python state/summary-camera-scan.py 294        # 单章明细
  python state/summary-camera-scan.py d          # 家族 D 报告（按卷待裁可清单）
  python state/summary-camera-scan.py d --no-write   # 同上，不写 md
只报告、不改稿。
"""
import sys, os, re, glob

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.dirname(HERE)

# ---- A 枚举清单 ----
ENUM_RE = re.compile(r"[两三四五]件事[：:]|[两三四五]样[东西][：:]|[两三四五]种[：:]")

# ---- B 段尾判语 ----
# 评价副词/定性词（借旁人之口给人物定级）
# 只收“给人物/事情定级”的词。
# 已剔除的假阳源（实测）：不像（“水声不像流水，倒像拖动铁链”是比喻，好句）、
# 懂（“老人看懂了，手停在半空”是动作）、像样、才是。
VERDICT = ("到底|毕竟|总归|终究|难怪|怪不得|果然|才算是|体面|分寸|"
           "难得|了不起|长脸|有脸|识相|知趣|会做人|不是白给|这才叫|委实|"
           "怪道|也算是个|不枉|白长了|白在")
VERDICT_RE = re.compile(VERDICT)

# ---- C 长段无落点 ----
# 具体实物/身体/触感/量词（只用不歧义词；不收单字与颜色字，避免「宁红叶」误中「红」）
CONCRETE = re.compile(
    "纸包|纸张|纸|布|木|铁|铜|石头|石子|泥|沙|水|油|烟|灰|绳|线|瓦|砖|竹|皮|骨头|血|"
    "膝盖|手指|巴掌|掌心|手腕|肩头|后背|眼眶|喉咙|脚|额头|脖子|腰间|眉头|嘴唇|指尖|指节|虎口|"
    "烛|灯|月光|日头|影|刀|秤|筐|匣|册|牌|铜钱|银|米|盐|茶|酒|豆|饼|肉|药|膏|"
    "汗|泪|雨|雪|风|火|烫|凉|湿|黏|扎|硌|疼|痛|麻|腥|酸|苦|甜|咸|哗啦|咔|嗤|吱|咚|"
    "[一二三四五六七八九十]+[个步斤尺寸斗石升碗张页册坛包封口]")

# ---- 器物／文书／军器寄存器（v3 增补：与 CONCRETE 合并成密度主口径）----
REG2 = ("火漆|封筒|封皮|封泥|印面|印章|印泥|印文|私章|官印|篆字|篆|字缝|朱色|朱印|"
        "墨色|笔划|笔画|刻痕|折痕|纸背|纸角|纸沿|边口|毛边|骑缝|拓|押签|"
        "灯芯|灯花|烛芯|更鼓|香炉|铜鹤|炭盆|炭|砚沿|砚台|砚|笔架|镇纸|笔尖|笔|"
        "钥匙|锁孔|匣盖|箱底|蓝布|铜丝|水囊|靴底|靴|袖口|左襟|腰间|药囊|"
        "舆图|簿页|页码|驿马|马队|烽|营|粮道|兵册|粮册|马册|行簿|行军簿")
# ---- 兵器／身体／建筑／行程寄存器（v4 增补）----
REG3 = ("剑|刀|鞘|刃|锋|盾|甲|弓|箭|枪|杖|杵|帕|头发|尘|蛛网|神像|柱|梁|门槛|"
        "墙|屋脊|瓦罐|炭枝|车辙|轱辘|伞|灯笼|火把|井|桥")

REG2_COMB = re.compile("(?:" + CONCRETE.pattern + ")|(?:" + REG2 + ")|(?:" + REG3 + ")")
REG2_COMB_STR = REG2_COMB.pattern

# 制度／文书腔（章型分档用：令奏诏敕簿册印……）
INST_RE = re.compile("令|奏|诏|敕|簿|册|印|制|度|衙|司|廷|军府|案|文|报|符|勘|覆|驳|例|式")


SPLIT_PARA = re.compile(r"\n\s*\n")
SPLIT_SENT = re.compile(r"(?<=[。！？])")


def paragraphs(text):
    t = re.sub(r"^#.*$", "", text, flags=re.M)
    return [p.strip() for p in SPLIT_PARA.split(t) if p.strip()]


def nows(s):
    return re.sub(r"\s", "", s)


def is_narr(p):
    return not p.startswith("“")


def has_dialogue(p):
    return any(len(q) >= 8 for q in re.findall(r"“([^”]*)”", p))


def fam_a(p):
    m = ENUM_RE.search(p)
    if m and is_narr(p):
        return f"A 枚举清单：…{nows(p[max(0, m.start()-14):m.end()+10])}…"
    return None


def fam_b(p):
    if not is_narr(p):
        return None
    sents = [s for s in SPLIT_SENT.split(p) if nows(s)]
    if len(sents) < 2:
        return None
    last = nows(sents[-1])
    if "“" in last or "”" in last:
        return None
    if len(last) > 30:
        return None
    if not VERDICT_RE.search(last):
        return None
    return f"B 段尾判语：{last}"


# ---- D 解释腔 ----
# D1 连接词标记：只收**解释性**连接词。刻意不收「其实／当然／显然」这类高频且多为正常行文语气的词。
# ★ v5 实测（第一次口径就吃了大亏，写下来）：首版词表里放了「一句话：」「一句话，」「从头到尾」，
#   报出 104 处，其中 70 处（43+23+27……）全是**惯用语**，零处是解释腔：
#     「从头到尾看了一遍」＝把册子读一遍（动线，该留）；
#     「他留下一句话：」＝留话（引语，该留）；「一句话，就是……」才是解释腔。
#   所以 D1 分两层：**D1a 进候选**（真解释连接词，全书 11 处）；
#   **D1b 惯用语只计数备查、不进候选**（不列入清单，避免淹没真信号）。
#   ★ 另一个实测假阳：「归总之前」被「总之」子串命中（ch148）——加否定回顾，
#     这条只挡「归/汇/共总」，不碰真正的句首「总之」。
EXPLAIN = ("这意味着|这说明|这即是说|这代表着|也就是说|换句话说|换个说法|换言之|"
           "事实已经|事实就是|说白了|说到底|归根到底|总而言之|(?<![归汇共])总之")
EXPLAIN_RE = re.compile(EXPLAIN)
# D1b 惯用语（测试过，零真阳；只统计，不报候选）
IDIOM = ("一句话[，,：:]|从头到尾|前文说过|前面已经说过")
IDIOM_RE = re.compile(IDIOM)
# ★ v5 教训（勿重走）：曾给 D1 加过一个「后接推理落点→倾向保留」的自动提示，
#   词的清单是（说明|等于|所以|因此|已经|不再…）。拿已知的两个坏样本一测——
#   ch78「这意味着」与 ch258「事实已经」——**两个都被它标成「倾向保留」**。
#   因为坏样本里接的确实是**一句推理**；病不在那一句，在它后面又把同一意思说了两遍。
#   所以不再输出“该留/该改”的机器意见，只输出两个**事实性**信号，由人判：
#     · 「含推理词」——标记后 40 字内有没有推理连接词（不代表可留）；
#     · 「段内复诵×N」——本段最高频 2-gram 的出现次数（≥3 报），这才是 ch78 那种
#       “一句推理＋两遍翻版”与 ch50 那种干净推理的**分水岭**。
INFER = ("说明|等于|可以推出|所以|因此|只能|必然|至少|已经|不再|反而")


def _top_2gram_rep(p):
    s = nows(p)
    cnt = {}
    for i in range(len(s) - 1):
        g = s[i:i + 2]
        cnt[g] = cnt.get(g, 0) + 1
    if not cnt:
        return 0, ""
    g, c = max(cnt.items(), key=lambda kv: kv[1])
    return c, g


def fam_d1(p):
    if not is_narr(p):
        return None
    m = EXPLAIN_RE.search(p)
    if not m:
        return None
    if len(nows(p)) < 40:
        return None
    tail = p[m.end():m.end() + 40]
    rep, g = _top_2gram_rep(p)
    flags = []
    if any(w in tail for w in INFER):
        flags.append("含推理词")
    if rep >= 3:
        flags.append(f"段内复诵×{rep}（「{g}」）")
    return (f"D1 解释腔标记：「{m.group(0)}」→ {nows(tail)[:28]}…"
            + ("（" + "；".join(flags) + "）" if flags else ""))


# D2 复述式概括：章内段对 containment（4-gram）
NGRAM = 4

def _grams(s):
    s = nows(s)
    return {s[i:i + NGRAM] for i in range(max(0, len(s) - NGRAM + 1))}


def recap_pairs(paras):
    """返回章内疑似复述段对 [(i, j, ratio)]；i<j，相隔 >=5 段，两段 >=35 字"""
    idx = [(i, _grams(p), len(nows(p))) for i, p in enumerate(paras)
           if is_narr(p) and len(nows(p)) >= 35]
    out = []
    for a in range(len(idx)):
        i, gi, li = idx[a]
        for b in range(a + 1, len(idx)):
            j, gj, lj = idx[b]
            if j - i < 5:
                continue
            if abs(li - lj) > max(li, lj) * 0.8:   # 长度悬殊过大不成对
                continue
            small = gi if len(gi) <= len(gj) else gj
            if not small:
                continue
            c = len(small & (gi & gj)) / len(small)
            if c >= 0.55:
                out.append((i, j, c))
    return out


def fam_c(p):
    if not is_narr(p) or has_dialogue(p):
        return None
    n = len(nows(p))
    if n < 150:
        return None
    hits = len(CONCRETE.findall(p))
    if hits <= 2:
        return f"C 长段无落点：{n} 字，实物词 {hits} 个｜{nows(p)[:30]}…"
    return None


FAMS = (("A", fam_a), ("B", fam_b), ("C", fam_c), ("D1", fam_d1))

VOLS = [(1, 1, 20), (2, 21, 44), (3, 45, 68), (4, 69, 92), (5, 93, 116),
        (6, 117, 140), (7, 141, 164), (8, 165, 188), (9, 189, 212),
        (10, 213, 236), (11, 237, 260), (12, 261, 284), (13, 285, 308),
        (14, 309, 332)]


def vol_of(n):
    for v, a, b in VOLS:
        if a <= n <= b:
            return v
    return 0


def collect(sel=None, vol=None):
    out = {}
    for path in sorted(glob.glob(os.path.join(BOOK, "novel", "chapter-*.md"))):
        n = int(re.search(r"(\d+)", os.path.basename(path)).group(1))
        if sel and n not in sel:
            continue
        if vol and vol_of(n) != vol:
            continue
        paras = paragraphs(open(path, encoding="utf-8").read())
        found = []
        for i, p in enumerate(paras):
            for tag, fn in FAMS:
                r = fn(p)
                if r:
                    found.append((i, tag, r))
        for i, j, c in recap_pairs(paras):
            found.append((i, "D2", f"D2 复述式概括：段{i} × 段{j}（containment {c:.2f}）｜"
                               f"{nows(paras[i])[:34]}…"))
        found.sort()
        if found:
            out[n] = found
    return out


def density(text, combined=True):
    """每百字落点密度（默认 v3 主口径：两寄存器合并）"""
    t = re.sub(r"^#.*$", "", text, flags=re.M)
    L = len(nows(t))
    if not L:
        return 0.0
    rx = REG2_COMB if combined else CONCRETE
    return len(rx.findall(t)) / L * 100


def main_density(sel=None, vol=None):
    """密度主口径报表：全卷 p50/p90 + 缺口榜 + 章型分档"""
    import statistics as st
    rows = []
    for path in sorted(glob.glob(os.path.join(BOOK, "novel", "chapter-*.md"))):
        n = int(re.search(r"(\d+)", os.path.basename(path)).group(1))
        if sel and n not in sel:
            continue
        if vol and vol_of(n) != vol:
            continue
        t = open(path, encoding="utf-8").read()
        body = re.sub(r"^#.*$", "", t, flags=re.M)
        rows.append((n, density(t, True), density(t, False),
                     len(INST_RE.findall(body)) / max(1, len(nows(body))) * 100))
    if sel or vol:
        # 同型带（按对白占比分档）：目标取本档 p50，并报字数余额
        allrows = []
        for path in sorted(glob.glob(os.path.join(BOOK, "novel", "chapter-*.md"))):
            tt = open(path, encoding="utf-8").read()
            bb = re.sub(r"^#.*$", "", tt, flags=re.M)
            L = max(1, len(nows(bb)))
            dlg = sum(len(nows(q)) for q in re.findall(r"“([^”]*)”", tt)) / L
            allrows.append((density(tt, True), dlg))
        bands = {}
        for lab, lo, hi in (("叙述型", -1, .15), ("混合", .15, .40), ("对白驱动", .40, 1e9)):
            ds = sorted(d for d, g in allrows if lo <= g < hi)
            q = st.quantiles(ds, n=10)
            bands[lab] = (q[1], q[4], q[6])
        print("同型带（对白占比分档，p25/p50/p75）: " +
              " ｜ ".join(f"{k} {v[0]:.2f}/{v[1]:.2f}/{v[2]:.2f}" for k, v in bands.items()))
        for n, d, d0, inst in rows:
            t = open(os.path.join(BOOK, "novel", f"chapter-{n}.md"), encoding="utf-8").read()
            body = nows(re.sub(r"^#.*$", "", t, flags=re.M))
            dlg = sum(len(nows(q)) for q in re.findall(r"“([^”]*)”", t)) / max(1, len(body))
            lab = "叙述型" if dlg < .15 else ("混合" if dlg < .40 else "对白驱动")
            sents = [len(s) for s in re.split(r"(?<=[。！？])", body) if s]
            cv = st.pstdev(sents) / st.mean(sents) if len(sents) > 1 else 0
            print(f"ch{n:<4} 字数{len(body):>5} 余额{5000-len(body):>4} 密度{d:.2f} "
                  f"CV{cv:.3f} 对白占比{dlg:.2f} → {lab}带 目标p50={bands[lab][1]:.2f}"
                  + (" 未达" if d < bands[lab][1] else " 已达"))
        return
    print("卷 | p50 | p90")
    p90 = {}
    for v, a, b in VOLS:
        ds = sorted(x[1] for x in rows if a <= x[0] <= b)
        q = st.quantiles(ds, n=10)
        p90[v] = q[8]
        print(f"卷{v:>2} | {q[4]:.2f} | {q[8]:.2f}")
    print("\n章型分档（按制度词占比三分）：")
    iq = st.quantiles([x[3] for x in rows], n=3)
    for lab, lo, hi in (("低制度", -1, iq[0]), ("中制度", iq[0], iq[1]), ("高制度", iq[1], 1e9)):
        ds = sorted(x[1] for x in rows if lo <= x[3] < hi)
        q = st.quantiles(ds, n=10)
        print(f"  {lab} {len(ds)} 章  p50={q[4]:.2f} p75={q[6]:.2f} p90={q[8]:.2f}")
    print("\n缺口榜 top20（卷内 p90 − 章密度）：")
    gap = sorted(((p90[vol_of(n)] - d, n, d, vol_of(n)) for n, d, _, _ in rows), reverse=True)
    for g, n, d, v in gap[:20]:
        print(f"  ch{n:<4} 卷{v:<2} 密度{d:.2f} 缺口{g:.2f}")


# ==== D 家族已裁台账（2026-09-24 首批）====
# 纪律：已裁事项不重复受理。锚点取正文里能唯一定位到该处的短句；
# 锚点找不到＝该处已消除（改掉或整章重写），报告会在「已消除」栏列出。
D_LEDGER = [
    {"ch": 47, "tag": "D1", "anchor": "谁拿了牌", "verdict": "已改",
     "action": "删连接词「也就是说」（认牌不认人。谁拿了牌，谁就是货主。）"},
    {"ch": 52, "tag": "D1", "anchor": "六把都一样", "verdict": "已改",
     "action": "删「这说明」——六把椅子的亮是现场可见的，让读者自己连"},
    {"ch": 53, "tag": "D1", "anchor": "库册上却没有出册", "verdict": "已改",
     "action": "删连接词与三重排比（与下段「三本册子」重复）→「库册第三排那一格，是空的」"},
    {"ch": 229, "tag": "D2", "anchor": "他把麻线和废纸并排放在桌上", "verdict": "已改",
     "action": "删段56 两处逐字回述（F24a 漏检的「短段被长段吞掉」），补纸套实物"},
    {"ch": 315, "tag": "D2", "anchor": "顾琰离山前又核了一次锁", "verdict": "已改",
     "action": "删等文的离山段（留带新增内容的那一段，删后时间线也更顺）"},
    {"ch": 321, "tag": "D2", "anchor": "九十七步", "verdict": "已改",
     "action": "整章重写：五拍各只一次，「冬至评资质」调回冬至前；4,032→4,193 字／密度 3.67→4.65"},
    {"ch": 43, "tag": "D1", "anchor": "另一半此刻在什么人手里", "verdict": "保留",
     "action": "后接从符牌断口推出的新信息，属本书「推账腔」"},
    {"ch": 48, "tag": "D1", "anchor": "白皮册上都要多一行数", "verdict": "保留",
     "action": "后接从印与账推出的新信息"},
    {"ch": 50, "tag": "D1", "anchor": "动图的手", "verdict": "保留",
     "action": "后接从撕口避名与注文推出的新信息"},
    {"ch": 99, "tag": "D1", "anchor": "没有说一句实话", "verdict": "保留",
     "action": "假阳：此处「说到底」是副词（终究），不是归纳标记"},
    {"ch": 159, "tag": "D1", "anchor": "不再有纸面上的凭证", "verdict": "保留",
     "action": "人物内景，后接新后果"},
    {"ch": 251, "tag": "D1", "anchor": "改路的人可能早在药队出发前", "verdict": "保留",
     "action": "后接从折痕推出的新信息，并自限「折痕只能证明预先准备」"},
    {"ch": 253, "tag": "D1", "anchor": "删去了断后者的结果", "verdict": "保留",
     "action": "后接从时辰与改写痕迹推出的新信息"},
    {"ch": 107, "tag": "D2", "anchor": "路的尽头，是长安", "verdict": "保留",
     "action": "章首×章末书挡（同句式回证），有意"},
    {"ch": 231, "tag": "D2", "anchor": "红线仍指向那座没有名字的城", "verdict": "保留",
     "action": "章末地图红线回证，有意"},
    {"ch": 232, "tag": "D2", "anchor": "还有地方活着", "verdict": "保留",
     "action": "章末主题句回证（末段独立成章眼句），有意"},
]


def ledger_lookup(ch, tag, texts):
    for e in D_LEDGER:
        if e["ch"] == ch and e["tag"] == tag \
                and any(e["anchor"] in t for t in texts):
            return e
    return None


def _bigrams(s):
    s = nows(s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def paraphrase_pairs(paras, gap=5, minlen=35, ratio=0.50, contain_max=0.55):
    """D3 参考：改写式复述（difflib 口径，第三轮同款；已由 D2 覆盖的不重复报）
    先过一道 2-gram 预筛再跑 difflib——全 332 章跑 difflib 要半分钟，预筛后秒级。"""
    import difflib
    idx = [(i, nows(p), _grams(p), _bigrams(p)) for i, p in enumerate(paras)
           if len(nows(p)) >= minlen]
    out = []
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            i, si, gi, bi = idx[a]
            j, sj, gj, bj = idx[b]
            if j - i < gap:
                continue
            small = gi if len(gi) <= len(gj) else gj
            c = len(small & (gi & gj)) / len(small) if small else 0
            if c >= contain_max:          # 近逐字，已由 D2 报过
                continue
            sb = bi if len(bi) <= len(bj) else bj
            if not sb or len(sb & (bi & bj)) / len(sb) < 0.42:   # 预筛
                continue
            r = difflib.SequenceMatcher(None, si, sj).ratio()
            if r >= ratio:
                out.append((i, j, round(r, 2)))
    return out


def collect_d(with_d3=True):
    """家族 D 明细：{ch: [dict(tag, para, texts, ev, fact, verdict, action)]} + D3 参考"""
    rows = {}
    for path in sorted(glob.glob(os.path.join(BOOK, "novel", "chapter-*.md"))):
        n = int(re.search(r"(\d+)", os.path.basename(path)).group(1))
        paras = paragraphs(open(path, encoding="utf-8").read())
        items = []
        for i, p in enumerate(paras):
            r = fam_d1(p)
            if r:
                items.append({"tag": "D1", "para": i, "texts": [p], "ev": r})
        for i, j, c in recap_pairs(paras):
            items.append({"tag": "D2", "para": i,
                          "texts": [paras[i], paras[j]],
                          "ev": f"段{i} × 段{j}（containment {c:.2f}）"})
        for it in items:
            e = ledger_lookup(n, it["tag"], it["texts"])
            it["verdict"] = e["verdict"] if e else "▢待裁可"
            it["action"] = e["action"] if e else ""
        d3 = []
        if with_d3:
            for i, j, r in paraphrase_pairs(paras):
                d3.append((i, j, r))
        if items or d3:
            rows[n] = (items, d3)
    return rows


def main_d(write=True):
    import datetime
    rows = collect_d()
    # 台账锚点现状
    plain = []
    for n, (items, d3) in sorted(rows.items()):
        for it in items:
            plain.append((n, it))
    hit_anchors = set()
    alltext = {}
    for n in set([n for n, _ in plain]):
        alltext[n] = "".join(nows(p) for p in
                             paragraphs(open(os.path.join(BOOK, "novel", f"chapter-{n}.md"),
                                             encoding="utf-8").read()))
    for e in D_LEDGER:
        if e["anchor"] in alltext.get(e["ch"], ""):
            hit_anchors.add(id(e))
    # 按卷汇总（D1/D2 进判定清单；D3 单列人眼线索）
    per_vol = {}
    d3_vol = {}
    for v, a, b in VOLS:
        items_all = []
        d3_all = []
        for n in sorted(rows):
            if a <= n <= b:
                items_all += [(n, it) for it in rows[n][0]]
                for i, j, r in rows[n][1]:
                    d3_all.append((n, i, j, r))
        per_vol[v] = items_all
        d3_vol[v] = d3_all
    todo = [(v, n, it) for v in per_vol for n, it in per_vol[v]
            if it["verdict"].startswith("▢")]

    def key(x):
        return (x[0], x[1]["para"])

    print("家族 D（解释腔）— 按卷待裁可清单")
    print("口径: D1 解释性连接词 / D2 近逐字复述（4-gram containment ≥0.55, 隔 ≥5 段）/ "
          "D3 改写式复述（difflib ≥0.50, 仅参考）")
    for v, a, b in VOLS:
        itemsv = per_vol[v]
        td = sorted([x for x in itemsv if x[1]["verdict"].startswith("▢")], key=key)
        led = [e for e in D_LEDGER if a <= e["ch"] <= b]
        led_gone = [e for e in led if id(e) not in hit_anchors]
        print(f"\n卷{v:>2}（ch{a}—{b}）：待裁可 {len(td)} ｜ 本卷已裁 {len(led)} 项"
              f"（其中已消除 {len(led_gone)}）｜ D3 人眼线索 {len(d3_vol[v])}")
        for e in led:
            print(f"  ✓ ch{e['ch']} {e['tag']} {e['verdict']}" +
                  ("（锚点已消失）" if id(e) not in hit_anchors else ""))
        for n, it in td:
            print(f"  ch{n:<4} 段{it['para']:<4} [{it['tag']}] {it['ev']}")
        if not td:
            print("  ✓ 无待裁可项")
        for n, i, j, r in d3_vol[v][:6]:
            print(f"  ch{n:<4} 段{i:<4} [D3] 段{i} × 段{j}（{r:.2f}，人眼读）")
        if len(d3_vol[v]) > 6:
            print(f"  …（另 {len(d3_vol[v]) - 6} 对 D3 线索略，见报告文件）")
    gone = [e for e in D_LEDGER if id(e) not in hit_anchors]
    print(f"\n全书：待裁可 {len(todo)} ｜ 已裁台账 {len(D_LEDGER)} 项"
          f"（其中锚点已消失＝已消除 {len(gone)} 项）")
    for e in gone:
        print(f"  ch{e['ch']} [{e['tag']}] 已消除：{e['action'][:28]}…")
    tot_d3 = sum(len(d3_vol[v]) for v in d3_vol)
    print(f"D3 改写式复述线索全书 {tot_d3} 对（参考，不入判定清单）。")
    print("纪律：候选≠违规；D3 假阳率高（章末回证／双人拉扯）只作人眼线索；"
          "探针不进 verify、不判失败（见 state/prose-polish-plan.md §八）。")

    if not write:
        return
    out = os.path.join(HERE, "d-family-report.md")
    today = datetime.date.today().isoformat()
    L = []
    L.append("<!-- 本文件由 `python state/summary-camera-scan.py d` 生成（npm run scan:d）。")
    L.append("     数字现场重算，勿手改；判定栏由作者裁可，裁完请登进脚本的 D_LEDGER，不要改本文件。 -->")
    L.append("")
    L.append("# 家族 D（解释腔）待处置清单")
    L.append("")
    L.append(f"**生成**：{today}（可复跑：`npm run scan:d`）｜ **范围**：全书 332 章 ｜ "
             "**口径**：v5（D1 标记／D2 近逐字复述；D3 改写式复述仅参考）")
    L.append("")
    L.append("## 一、怎么读这张清单")
    L.append("")
    L.append("- **候选≠违规**：探针不做判定，只把「像」的地方挑出来。")
    L.append("- 判定三档：**改**（连接词后接的是读者刚看过的东西的翻版）／**保留**"
             "（后接从实物推出的新信息、章末回证、假阳）／**人眼读**（D3）。")
    L.append("- **已裁不重复受理**：见 §四 台账；台账按「章号＋家族＋锚点」匹配（段号会随归治漂移）。"
             "**锚点消失＝该处已消除**（改掉或整章重写）。")
    L.append("- D2 的能力边界（已量清）：只看得见近逐字复述；**改写式复述只能人眼读**"
             "——ch90 那种 12 段各说一遍的复述，containment 最高只有 0.33。")
    L.append("")
    L.append("## 二、按卷待裁可清单（D1／D2）")
    L.append("")
    for v, a, b in VOLS:
        itemsv = per_vol[v]
        td = sorted([x for x in itemsv if x[1]["verdict"].startswith("▢")], key=key)
        done = len(itemsv) - len(td)
        led = [e for e in D_LEDGER if a <= e["ch"] <= b]
        led_gone = [e for e in led if id(e) not in hit_anchors]
        L.append(f"### 卷{v}（ch{a}—{b}）｜待裁可 {len(td)} ｜本卷已裁 {len(led)} 项"
                 f"（其中已消除 {len(led_gone)}）｜D3 线索 {len(d3_vol[v])}")
        L.append("")
        if led:
            L.append("- 本卷已裁：" + "；".join(
                f"ch{e['ch']} {e['tag']} {e['verdict']}" +
                ("（锚点已消失）" if id(e) not in hit_anchors else "") for e in led))
        if not td:
            L.append("- ✓ 本卷无待裁可项（已裁项见 §四）。")
            L.append("")
            continue
        L.append("| 章 | 段 | 家族 | 证据 | 机器事实信号 | 判定（圈一个） |")
        L.append("|---|---|---|---|---|---|")
        for n, it in td:
            ev = nows(it["ev"]).replace("|", "／")
            L.append(f"| ch{n} | {it['para']} | {it['tag']} | {ev} | | ▢改 ▢保留 |")
        L.append("")
    L.append("## 二之二、D3 改写式复述人眼线索（参考，不入判定清单）")
    L.append("")
    L.append("D2 只看得到近逐字复述；以下是用第三轮 difflib 口径（ratio ≥0.50、段 ≥35 字、"
             "隔 ≥5 段，且 4-gram containment <0.55）补位抓到的**改写式**复述。"
             "假阳率高（章末回证、双人拉扯对峙都会被抓），只作人眼线索。")
    L.append("")
    for v, a, b in VOLS:
        if not d3_vol[v]:
            continue
        L.append(f"**卷{v}（{len(d3_vol[v])} 对）**")
        L.append("")
        L.append("| 章 | 段对 | difflib | 段首 |")
        L.append("|---|---|---|---|")
        for n, i, j, r in d3_vol[v]:
            ps = paragraphs(open(os.path.join(BOOK, "novel", f"chapter-{n}.md"),
                                 encoding="utf-8").read())
            head = nows(ps[i])[:26].replace("|", "／")
            L.append(f"| ch{n} | {i} × {j} | {r:.2f} | {head}… |")
        L.append("")
    L.append("## 三、全书统计")
    L.append("")
    L.append("| 卷 | D1 | D2 | 待裁可 | 已裁（台账） | 其中已消除 | D3（参考） |")
    L.append("|---|---|---|---|---|---|---|")
    for v, a, b in VOLS:
        iv = per_vol[v]
        c = {t: sum(1 for _, it in iv if it["tag"] == t) for t in ("D1", "D2")}
        td = sum(1 for _, it in iv if it["verdict"].startswith("▢"))
        led = [e for e in D_LEDGER if a <= e["ch"] <= b]
        gonev = sum(1 for e in led if id(e) not in hit_anchors)
        L.append(f"| 卷{v} | {c['D1']} | {c['D2']} | {td} | {len(led)} | {gonev} | "
                 f"{len(d3_vol[v])} |")
    allc = {t: sum(1 for v in per_vol for _, it in per_vol[v] if it["tag"] == t)
            for t in ("D1", "D2")}
    tot_d3 = sum(len(d3_vol[v]) for v in d3_vol)
    L.append(f"| **合计** | {allc['D1']} | {allc['D2']} | {len(todo)} | {len(D_LEDGER)} | "
             f"{len(gone)} | {tot_d3} |")
    L.append("")
    L.append(f"另：D1b 口语惯用语（「一句话：」「从头到尾」）全书 105 处，已实测**零真阳**，"
             "只计数不进候选。")
    L.append("")
    L.append("## 四、已裁台账（不重复受理）")
    L.append("")
    L.append("| 章 | 家族 | 判定 | 处置／理由 | 锚点现状 |")
    L.append("|---|---|---|---|---|")
    for e in sorted(D_LEDGER, key=lambda x: (x["ch"], x["tag"])):
        state = "锚点在正文（候选仍在）" if id(e) in hit_anchors else "**锚点已消失＝已消除**"
        L.append(f"| ch{e['ch']} | {e['tag']} | {e['verdict']} | {e['action']} | {state} |")
    L.append("")
    L.append("## 五、复跑与纪律")
    L.append("")
    L.append("```bash")
    L.append("npm run scan:d                              # 本报告（写回 state/d-family-report.md）")
    L.append("npm run scan:d -- --no-write               # 只看终端")
    L.append("python state/summary-camera-scan.py d --vol 13   # 单卷")
    L.append("```")
    L.append("")
    L.append("- 探针**不进 verify**、不判失败、不进钩子（见 `prose-polish-plan.md` §八）；"
             "改稿仍按路线 A 逐章通读。")
    L.append("- 已裁事项请登进脚本的 `D_LEDGER`（章号＋家族＋锚点＋判定＋处置），"
             "**不要手改本文件**——下次复跑会盖写。")
    L.append("")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))
    print(f"\n已写报告：state/{os.path.basename(out)}")


def main():
    args = sys.argv[1:]
    if args and args[0] == "d":
        rest = args[1:]
        if "--vol" in rest:
            vol = int(rest[rest.index("--vol") + 1])
            rows = collect_d()
            saved = {n: h for n, h in rows.items() if vol_of(n) == vol}
            for n, (items, d3) in sorted(saved.items()):
                print(f"=== ch{n} ===")
                for it in items:
                    print(f"  段{it['para']:<4} [{it['tag']}] {it['ev']} → {it['verdict']} {it['action']}")
                for i, j, r in d3:
                    print(f"  段{i:<4} [D3] 段{i} × 段{j}（{r:.2f}，人眼读）")
            return
        main_d(write="--no-write" not in rest)
        return
    if args and args[0] == "density":
        rest = args[1:]
        if rest and rest[0] == "--vol":
            main_density(vol=int(rest[1]))
        elif rest:
            main_density(sel=[int(x) for x in rest if x.isdigit()])
        else:
            main_density()
        return
    sel = None
    vol = None
    if args and args[0] == "--vol":
        vol = int(args[1])
    elif args:
        sel = [int(x) for x in args if x.isdigit()]

    res = collect(sel, vol)
    if sel or vol:
        for n in sorted(res):
            print(f"\n=== ch{n} === {len(res[n])} 处候选")
            for i, tag, txt in res[n]:
                print(f"  段{i:>3} [{tag}] {txt}")
    else:
        print("卷 | 命中章/卷章数 | A枚举 | B判语 | C长段 | D1解释腔 | D2复述 | 合计 | 最密章")
        for v, a, b in VOLS:
            rows = {n: h for n, h in res.items() if vol_of(n) == v}
            cnt = {t: 0 for t in ("A", "B", "C", "D1", "D2")}
            for n, hs in rows.items():
                for _, t, _ in hs:
                    cnt[t] += 1
            tot = sum(cnt.values())
            top = sorted(((n, len(h)) for n, h in rows.items()), key=lambda r: -r[1])[:3]
            print(f"卷{v:>2} | {len(rows):>3}/{b-a+1:<3} | {cnt['A']:>5} | {cnt['B']:>5} |"
                  f" {cnt['C']:>5} | {cnt['D1']:>7} | {cnt['D2']:>6} | {tot:>5} | {top}")
        allh = sum(len(h) for h in res.values())
        print(f"\n全书候选：{len(res)} 章 / {allh} 处")
        # D1b 惯用语：只计数，不进候选（避免淹没真信号）
        ib = sum(1 for path in glob.glob(os.path.join(BOOK, "novel", "chapter-*.md"))
                 for p in paragraphs(open(path, encoding="utf-8").read())
                 if is_narr(p) and IDIOM_RE.search(p))
        print(f"（另：D1b 口语惯用语「一句话：／从头到尾」全书 {ib} 处，实测零真阳，不计入候选）")
    print("\n说明：候选≠违规。四个家族都要人眼判「改写／保留」——详见文件头「边界」节。")


if __name__ == "__main__":
    main()
