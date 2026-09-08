# -*- coding: utf-8 -*-
"""已核实审计项批量修复。运行于 books/天阙 目录。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # books/天阙
NOVEL = ROOT / "novel"


def load(p):
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def save(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t)


def has_crlf(t):
    return "\r\n" in t


def norm(t):
    return t.replace("\r\n", "\n")


def denorm(t, crlf):
    return t.replace("\n", "\r\n") if crlf else t


def swap_quotes(s):
    """把弯引号换成直引号（或反向），用于锚点兜底匹配。"""
    m = {
        "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
        '"': "\u201c", "'": "\u2018",
    }
    # 成对替换直引号时按出现次序轮流给左右引号
    out = []
    open_curly = True
    for ch in s:
        if ch == '"':
            out.append("\u201c" if open_curly else "\u201d")
            open_curly = not open_curly
        elif ch == "'":
            out.append("\u2018" if open_curly else "\u2019")
            open_curly = not open_curly
        elif ch in m:
            out.append(m[ch])
        else:
            out.append(ch)
    return "".join(out)


def apply_fixes(fname, pairs):
    p = NOVEL / fname
    if not p.exists():
        print(f"[MISS-FILE] {fname}")
        return 0
    t = load(p)
    crlf = has_crlf(t)
    t = norm(t)
    n = 0
    for old, new in pairs:
        if old in t:
            t = t.replace(old, new)
            n += 1
            continue
        alt = swap_quotes(old)
        if alt in t:
            t = t.replace(alt, swap_quotes(new) if alt != old else new)
            n += 1
            continue
        print(f"[MISS] {fname}: {old[:40]!r}")
    save(p, denorm(t, crlf))
    return n


total = 0

# ── P0 逻辑硬伤 ──────────────────────────────
# 1) ch31 桑葚开口说话 → 肢体动作
total += apply_fixes("chapter-31.md", [
    ("桑葚忽然问：“他会死吗？”",
     "桑葚忽然拉了拉宁红叶的衣角，指了指沈念，又用两手比划了一个阖眼的动作，仰头看着她。"),
])

# 2) ch177 重复粘贴段
total += apply_fixes("chapter-177.md", [
    ("他上了楼，推开铺门。\n\n如今，他又看见那片红了。\n\n他上了楼，推开铺门。",
     "他上了楼，推开铺门。\n\n如今，他又看见那片红了。"),
])

# 3) ch185 李承恩死期 十年→八年（763−755=8）
total += apply_fixes("chapter-185.md", [
    ("他死了十年的弟弟", "他死了八年的弟弟"),
])

# 4) ch191 十九年→十五年（764−749=15）；ch211/212 →十七年（766−749=17）
total += apply_fixes("chapter-191.md", [("十九年", "十五年")])
total += apply_fixes("chapter-211.md", [("走了十九年", "走了十七年")])
total += apply_fixes("chapter-212.md", [("走了十九年", "走了十七年")])

# 5) ch92 公文被行台收回尾巴（解决卷七朝堂不知情的矛盾）
total += apply_fixes("chapter-92.md", [(
    "远处，营火连成一线，在雪夜里亮着，一直亮到天边。",
    "远处，营火连成一线，在雪夜里亮着，一直亮到天边。\n\n"
    "可三天之后，官道上来了一匹快马。马上的文吏跳下来，看了墙上一眼，伸手把公文揭下来，卷进袖里，换上一张新告示：“军籍核销属河东军务，可‘限十日内自首’一条，牵动转运司名下的存粮、存盐、存钱——须先核，后销。李承恩名下签押，由河东军府自行封存核销。各粮站、卡口、转运司，不再受理。”\n\n"
    "文吏钉完告示，翻身上马走了。雪很快落满新告示的纸面。沈广农站在告示前，把“自行封存”四个字念了一遍，又念了一遍。他知道，公文贴出去的那三天里，有人自首，有人逃走，有人连夜把名字从册上抹掉——可三天一过，名字重新沉回水里。名字有人管了三天。三天之后，名字又没有人管了。\n\n"
    "他伸出手，把告示上落的雪拂掉，露出底下那行字，看了很久。雪原上，他的脚印重新往北延伸，一直延伸到看不见的地方。",
)])

# 6) ch169 沈念台词（遗孤，无“以前记事”前提）
total += apply_fixes("chapter-169.md", [
    ("“他病的时候烧得厉害，烧退了，以前的事记不大清了。”温守朴在门口说，“他娘的事，他爹的事，都记不得了。他只知道温家是他的家。”",
     "“他小的时候烧得太凶，身子亏得厉害。”温守朴在门口说，“他落地就没了爹娘，是温家捡回来养的。除了温家，别处的事他一概不知，胆子也小。”"),
])

# ── 语流衔接 ────────────────────────────────
# 7) ch103 补过渡提问
total += apply_fixes("chapter-103.md", [
    ("柳直沉默了一会儿，才说：\"你查的是李承恩。李将军查的，也是李承恩。\"",
     "柳直沉默了一会儿，才说：\"你查的是李承恩。李将军查的，也是李承恩。\"\n\n\"那他专程南下？\"沈广农问。"),
])

# ── P1 文字错漏 ─────────────────────────────
total += apply_fixes("chapter-04.md", [("半昼", "半晌")])
total += apply_fixes("chapter-11.md", [("半昼", "半晌"), ("管事捾起布包掂了掂", "管事拎起布包掂了掂")])
total += apply_fixes("chapter-08.md", [("沈广农一怕", "沈广农一怔")])
total += apply_fixes("chapter-18.md", [("血痪", "血痂")])
total += apply_fixes("chapter-39.md", [("摩拳", "摩挲"), ("跸脚", "跛脚")])
total += apply_fixes("chapter-217.md", [("批注只有四个字", "批注只有三个字"), ("留下这四个字", "留下这三个字")])

# ── P3 F16 金句家族降频（保留核心章眼 ch86/87/88/146/152/193）──
total += apply_fixes("chapter-08.md", [
    ("“罐子是死的，人是活的。等你哪天能听出我换重心，就不用板了。”",
     "“罐子不会自己换重心，人会。等你哪天能听出我换重心，就不用板了。”"),
])
total += apply_fixes("chapter-12.md", [
    ("“牌是死的，人是活的。活人才欠账。”", "“牌抵不了账，活人才欠账。”"),
])
total += apply_fixes("chapter-18.md", [
    ("“米是死的，人是活的。”高个的蹲下去又翻了一遍尸体口袋，“活人才知道还有没有第二封。”",
     "高个的蹲下去又翻了一遍尸体口袋：“死人身上搜不出第二封，活人才知道还有没有。”"),
])
total += apply_fixes("chapter-78.md", [
    ("“法子是死的，人是活的。”韩魁说，", "韩魁说："),
])
total += apply_fixes("chapter-100.md", [
    ("锁换了，可锁是死的，人是活的——总有开锁的人。", "锁换了，可换锁的是人，开锁的也是人——总有开锁的人。"),
])
total += apply_fixes("chapter-124.md", [
    ("——路是死的，画下来，不会踢人。", "——路画下来，不会踢人。"),
])
total += apply_fixes("chapter-139.md", [
    ("名单是死的，账是活的——名单上的名字会核完", "名单上的名字会核完"),
])
total += apply_fixes("chapter-167.md", [
    ("减不掉的是这三年走出来的路。路是死的，人是活的。河东缺粮的那几年", "减不掉的是这三年走出来的路。河东缺粮的那几年"),
])

# ── F18 单字回声（ch205/208；ch100/105/111 带增量判定保留）──
total += apply_fixes("chapter-205.md", [
    ("“样本？”", "“一本空账底册，算什么样本？”"),
])
total += apply_fixes("chapter-208.md", [
    ("“夹墙？”", "“那面墙，是什么时候砌的？”"),
    ("裴令仪愣了一下：“天阙？”\n\n“是天阙。”顾琰说，“你爹的暗格钥匙上，刻的就是这两个字。”",
     "裴令仪愣了一下：“天阙？钥匙上刻的，是这两个字？”\n\n“是。”顾琰说，“你爹的暗格钥匙上，刻的就是这两个字。”"),
])

print(f"\n总替换数: {total}")