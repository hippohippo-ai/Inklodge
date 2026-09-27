#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《留春信》连续性探针 continuity-scan.py（2026-09-26，源：9/25–9/26 两轮改稿的分诊项）

■ 定位（先把边界说清，勿再走回头路）
本探针把上一轮排版修复与三处连续性修复用到的「分诊项」固化成**可复跑扫描**：
  引号 / 字面转义 / 章内重复 / 数字与日期锚点。
与 `summary-camera-scan.py` 同一纪律：**只报告、不改稿；不作判定，只出候选清单**。
低噪声家族（引号、字面转义、换行风格、回归锚点）近确定性，高噪声家族（章内重复、
数量词）只作筛选——改稿仍靠人逐章通读。

■ 家族
  A 引号     A1 半角引号（正文应为 0，全书唯一一次半角事故见 revisions 2026-09-25）
             A2 全角引号配对（“ ” 与 ‘ ’；含闭合早于开启的「顺序异常」行）
  B 字面转义 B1 正文出现反斜杠（应 0；历史上出现过字面 \n\n）
  C 章内重复 C1 近似段对（同章两段 ≥35 字、4-gram containment ≥0.55）
             C2 重复句（同章同一句 ≥2 次，按去引号归一化后比对）
  D 数字锚点 D1 月日 / D2 时辰 / D2b 时辰计数 / D3 年龄 / D4 数量 / D5 时段
             按「表达 → 出现处」分组列全书，专为看**同一名目在不同章用不同数字**
             （如红结 七枚 / 五个、阿七 十二岁 / 十三岁）
  E 回归锚点 把本轮已裁定的口径写成断言；改稿后应仍成立，**有意变更须同步本表**。
             除正文字串断言（must / forbid / must_all / book_must / book_forbid）外，
             含**台账↔正文绑定**的 state_must / state_forbid / state_count / state_order
             （直接读 state/*.md，如 timeline.md 的「第9日只一行」「日程升序」）。
  F 审计清单 读 state/audit-checklist.md：`- [x]` 项的判据硬校验（失守报 ⚠），
             `- [ ]` 待裁／待办项只登记探测（○）。规则语法与 E 同源，另有 charlen_max／charlen_min。

■ 换行风格
  正文行尾不统一（ch17/19/28/33/36/39/43 为 CRLF，其余 LF）。探针只报**同一文件内混合**
  行尾（真事故），不报 CRLF/LF 之别（既有约定）。

用法：
  python state/continuity-scan.py              # 全书：概览 + 各家族候选 + 回归锚点
  python state/continuity-scan.py 39           # 单章明细（ch39）
  python state/continuity-scan.py preface      # 前言明细
  python state/continuity-scan.py --family a   # 只跑某家族 a|b|c|d|e|all
  python state/continuity-scan.py --write      # 另写 state/continuity-report.md（盖写）
"""
import sys, os, re, glob
from collections import defaultdict

# Windows 控制台默认 cp1252，会中文编码报错；统一切到 UTF-8。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.dirname(HERE)
NOVEL = os.path.join(BOOK, 'novel')
REPORT = os.path.join(HERE, 'continuity-report.md')
AUDIT = os.path.join(HERE, 'audit-checklist.md')

# ---------------- 正则 ----------------
# NUM 用「合法中文数字」而非任意数字字串，避免「阿七三个月」被当成「七三」+「个月」。
NUM = ('(?:\\d{1,4}|两|[〇零一二三四五六七八九]?十[〇零一二三四五六七八九]?|'
       '廿[〇零一二三四五六七八九]?|卅[〇零一二三四五六七八九]?|'
       '[〇零一二三四五六七八九]?百[〇零一二三四五六七八九]?十?[〇零一二三四五六七八九]?|'
       '[〇零一二三四五六七八九])')
DATE_RE = re.compile(NUM + '月(?:初?[〇零一二三四五六七八九十]{1,3}[日号])?')
TIME_RE = re.compile('[子丑寅卯辰巳午未申酉戌亥]时(?:[初正][一二三四]?刻|[一二三四]刻|初|正)?')
SHICHEN_RE = re.compile('(?:半|两|' + NUM + ')个时辰')
AGE_RE = re.compile(NUM + '岁')
# 数量：数字+量词+其后 0–3 个汉字（名词），用于「同名目不同数量」的漂移检测
QTY_RE = re.compile('(' + NUM + ')(枚|张|封|道|条|件|盏|匣|层|重|成|柄|支|根|面|页|口|袋|包|把|只|个)([\\u4e00-\\u9fa5]{0,3})')
PERIOD_RE = re.compile('(?:近|约|将近|整整)?' + NUM + '(?:个?多月|个月|多天|天|年|夜)')
H1_RE = re.compile(r'^#.*$', re.M)
PARA_SPLIT = re.compile(r'\n[ \t]*\n')
SENT_SPLIT = re.compile(r'(?<=[。！？…])')
HALFQ_RE = re.compile('["\']')          # ASCII " 与 '
REVERSE_RE = re.compile('\\\\')          # 任何反斜杠
PUB = re.compile(r'^(?:chapter-(\d+)\.md|(preface|copyright)\.md)$')


def load_all():
    items = []
    for p in glob.glob(os.path.join(NOVEL, '*.md')):
        base = os.path.basename(p)
        m = PUB.match(base)
        if not m:
            continue
        num = int(m.group(1)) if m.group(1) else 0
        with open(p, encoding='utf-8', newline='') as f:
            raw = f.read()
        crlf = raw.count('\r\n')
        items.append({
            'num': num, 'base': base, 'raw': raw,
            'text': raw.replace('\r\n', '\n').replace('\r', '\n'),
            'crlf': crlf, 'lf': raw.count('\n') - crlf, 'lonecr': raw.count('\r') - crlf,
        })
    items.sort(key=lambda x: (x['num'], x['base']))
    return items


def label(it):
    return ('ch%02d' % it['num']) if it['num'] else it['base'].replace('.md', '')


def find_by(items, key):
    key = str(key)
    num = int(key) if key.isdigit() else None
    for it in items:
        if it['num'] == num or it['base'] == (key if key.endswith('.md') else key + '.md'):
            return it
    return None


# ---------------- A 引号 / B 转义 ----------------
def fam_a(it):
    """返回 (半角引号命中列表, 配对问题列表)。"""
    text = it['text']
    half = []
    for i, ln in enumerate(text.split('\n'), 1):
        for _ in HALFQ_RE.finditer(ln):
            half.append((i, ln.strip()))
    pairs = []
    for (o, c, nm) in (('“', '”', '“ ”'), ('‘', '’', '‘ ’')):
        ko, kc = text.count(o), text.count(c)
        if ko != kc:
            pairs.append('%s 不配对：%d ／ %d（差 %+d）' % (nm, ko, kc, ko - kc))
    d = 0
    for i, ln in enumerate(text.split('\n'), 1):
        for ch in ln:
            if ch == '“':
                d += 1
            elif ch == '”':
                d -= 1
                if d < 0:
                    pairs.append('L%d 闭合早于开启：%s' % (i, ln.strip()[:40]))
                    d = 0
    return half, pairs


def fam_b(it):
    out = []
    for i, ln in enumerate(it['text'].split('\n'), 1):
        if REVERSE_RE.search(ln):
            out.append((i, ln.strip()[:52]))
    return out


# ---------------- C 章内重复 ----------------
def paragraphs(it):
    body = H1_RE.sub('', it['text'])
    return [p.strip() for p in PARA_SPLIT.split(body) if p.strip()]


def fam_c1(it):
    paras = paragraphs(it)
    grams = [set(p[i:i + 4] for i in range(len(p) - 3)) for p in paras]
    out = []
    for x in range(len(paras)):
        for y in range(x + 1, len(paras)):
            if len(paras[x]) < 35 or len(paras[y]) < 35:
                continue
            gx, gy = grams[x], grams[y]
            if not gx or not gy:
                continue
            cont = len(gx & gy) / min(len(gx), len(gy))
            if cont >= 0.55:
                out.append((x + 1, y + 1, round(cont, 2), paras[x][:26]))
    return out


def fam_c2(it):
    cnt = defaultdict(list)
    for i, ln in enumerate(it['text'].split('\n'), 1):
        for s in SENT_SPLIT.split(ln):
            s = s.strip()
            norm = re.sub(r'[\s“”‘’]', '', s)
            if len(norm) >= 12:
                cnt[norm].append(i)
    out = [(len(v), k, v) for k, v in cnt.items() if len(v) >= 2]
    out.sort(key=lambda t: (-t[0], t[1]))
    return out


# ---------------- D 数字锚点 ----------------
def collect_numeric(items):
    """D1/D2/D2b/D3/D5 按表达分组；D4 按「名词」分组看同名目数量漂移。"""
    fams = {
        'D1 日期': (DATE_RE, defaultdict(list)),
        'D2 时辰': (TIME_RE, defaultdict(list)),
        'D2b 时辰计数': (SHICHEN_RE, defaultdict(list)),
        'D3 年龄': (AGE_RE, defaultdict(list)),
        'D5 时段': (PERIOD_RE, defaultdict(list)),
    }
    qty = defaultdict(list)          # noun -> [(numeral+cls, ch, line)]
    for it in items:
        for i, ln in enumerate(it['text'].split('\n'), 1):
            for name, (rgx, store) in fams.items():
                for m in rgx.finditer(ln):
                    store[m.group(0)].append('%s:%d' % (label(it), i))
            for m in QTY_RE.finditer(ln):
                noun = m.group(3) or ('（' + m.group(2) + '）')
                qty[noun].append((m.group(1) + m.group(2), label(it), i))
    return fams, qty


def qty_drift(qty):
    """同一名词出现 ≥2 种数量表达 → 漂移候选。"""
    out = []
    for noun, hits in qty.items():
        # 单字名词（月/字/线/事…）噪声过大，D4 只留 ≥2 字的名词（如「红结」「红线」「圆点」）
        if len(noun) < 2 or noun.startswith('（'):
            continue
        forms = defaultdict(list)
        for expr, ch, ln in hits:
            forms[expr].append('%s:%d' % (ch, ln))
        if len(forms) >= 2:
            out.append((noun, forms))
    out.sort(key=lambda t: (-sum(len(v) for v in t[1].values()), t[0]))
    return out


# ---------------- E 回归锚点 ----------------
REG = [
    ('正文 0 半角引号', 'book_bad', HALFQ_RE),
    ('正文 0 字面反斜杠', 'book_bad', REVERSE_RE),
    ('每章单一换行风格（无混合行尾）', 'newline', None),
    ('ch02 开篇＝七月九日', 'must', ('ch02', '七月九日')),
    ('ch02 无「七月十四」', 'forbid', ('ch02', '七月十四')),
    ('ch02 换页案卷＝巳时初刻／卯时三刻', 'must_all', ('ch02', ['巳时初刻', '卯时三刻'])),
    ('ch02 补婚日＝七月十五', 'must', ('ch02', '七月十五')),
    ('ch09 红结＝还剩五个', 'must', ('ch09', '还剩五个红结')),
    ('ch27 阿七进茶房＝十二岁', 'must', ('ch27', '他那时十二岁')),
    ('ch43＝十二岁进沈家', 'must', ('ch43', '十二岁进沈家')),
    ('ch43 无「十三岁」', 'forbid', ('ch43', '十三岁')),
    ('preface＝从十二岁起端茶', 'must', ('preface', '从十二岁起')),
    ('preface 无「十三岁」', 'forbid', ('preface', '十三岁')),
    ('ch39 顾青禾＝十几年前', 'must', ('ch39', '十几年前')),
    ('ch39 无「二十年前」', 'forbid', ('ch39', '二十年前')),
    ('ch23 死亡时辰链＝卯时三刻', 'must', ('ch23', '卯时三刻')),
    ('ch39 死亡时辰链＝巳时初刻', 'must', ('ch39', '巳时初刻')),
    ('ch39 时辰差统一＝晚「将近两个时辰」', 'must', ('ch39', '晚将近两个时辰')),
    ('ch39 无「晚一个时辰」', 'forbid', ('ch39', '晚一个时辰')),
    ('ch39 死亡夜＝四月初八夜咽药', 'must', ('ch39', '四月初八夜里咽的药')),
    ('ch23 无「提前了一个时辰」', 'forbid', ('ch23', '提前了一个时辰')),
    ('封存期统一＝全书含「近百日封存」', 'book_must', '近百日封存'),
    ('封存期统一＝全书无「封存满百日」', 'book_forbid', '封存满百日'),
    ('封存期统一＝全书无「封存百日」', 'book_forbid', '封存百日'),
    ('ch34 无「百日一到」', 'forbid', ('ch34', '百日一到')),
    ('copyright 统一＝近百日封存期满', 'must', ('copyright', '近百日封存期满')),
    ('全书含死亡夜「四月初八」', 'book_must', '四月初八'),
    ('全书含验尸日「四月初九」', 'book_must', '四月初九'),
    # 台账↔正文绑定（2026-09-26：timeline.md 台账清理）
    ('ch26 无「陆七」（名字第40章才落字）', 'forbid', ('ch26', '陆七')),
    ('ch27 无「陆七」', 'forbid', ('ch27', '陆七')),
    ('ch40 阿七自认姓名＝陆七', 'must', ('ch40', '给我起的名字，是陆七')),
    ('ch43 落名＝亲手写下「陆七」', 'must', ('ch43', '写下两个字')),
    ('ch43 终审日＝开封第十六日', 'must', ('ch43', '开封第十六日')),
    ('ch41 离庄日＝第十日', 'must', ('ch41', '正好是第十日')),
    # 红结算术链：七枚 − ch1 挑走第七枚 − ch4/ch6 断第一枚 = ch9 剩五枚
    ('ch01 红结＝七枚', 'must', ('ch01', '边缘压着七枚极小的红结')),
    ('ch01 第七枚已被挑走', 'must', ('ch01', '第七枚的位置空了')),
    ('ch04 断＝一枚红结', 'must', ('ch04', '红结断了一枚')),
    ('ch06 断的是第一枚', 'must', ('ch06', '第一枚红结断了')),
    ('ch09 第二个绷得发白（第二枚未断）', 'must', ('ch09', '第二个已经绷得发白')),
    ('全书无「六个红结」', 'book_forbid', '六个红结'),
    # 阿七年齿链：十二岁进沈家 + 端茶十年 = 人物卡 22 岁
    ('ch30 押在沈家＝十年前', 'must', ('ch30', '十年前，你爹把你押在沈家')),
    ('ch30 端茶＝十年', 'must', ('ch30', '他在这里端过十年茶')),
    ('preface 端茶＝十年（12＋10＝22）', 'must', ('preface', '端了十年茶')),
    ('阿七人物卡＝22岁', 'state_must', ('characters.md', '22岁')),
    ('人物卡无阿七「十三岁」', 'state_forbid', ('characters.md', '十三岁')),
    ('timeline §四 第9日只一行', 'state_count', ('timeline.md', '| 第9日 |', 1)),
    ('timeline §三 第6日不写「公开陆七」', 'state_forbid', ('timeline.md', '公开“陆七”')),
    ('timeline §二 无「陶未明上司」（时辰系陶自填）', 'state_forbid', ('timeline.md', '陶未明上司')),
    ('timeline 封存口径＝近百日', 'state_must', ('timeline.md', '近百日')),
    ('timeline §二 死亡轴线升序', 'state_order', ('timeline.md', [
        '| 死亡前10年 |', '| 死亡前7年 |', '| 死亡前6个月 |', '| 死亡前5个月 |',
        '| 死亡前4个月 |', '| 死亡前3个月10日 |', '| 死亡前3个月5日 |', '| 死亡前3个月2日 |',
        '| 死亡前1日白天 |', '| 四月初八出嫁当夜 |', '| 死亡后第1日 |', '| 死亡后第3日 |',
        '| 死亡后第7日 |'])),
    ('timeline §四 日程升序', 'state_order', ('timeline.md', [
        '| 第7日正夜 |', '| 第8日拂晓至黄昏 |', '| 第9日 |', '| 第10–11日 |', '| 第12日 |',
        '| 第13–14日 |', '| 第15日 |', '| 第16日（开封第十六日） |'])),
    # 台账↔正文绑定（2026-09-26 扩面：chapter-log／plot-check／chapters／requirements）
    # 把已裁定的日期（四月初八死／四月初九验／七月十五冥婚）、数量（红结七枚、第七枚被挑走、七方）、
    # 年龄（阿七十二岁进沈家、阮孤灯十三岁传说）口径固化到 timeline.md 以外的 state 台账。
    ('chapter-log 第七枚红结被挑走', 'state_must', ('chapter-log.md', '第七枚红结被挑走')),
    ('chapter-log 第一枚断裂／第二枚未断', 'state_must', ('chapter-log.md', '第一枚红结断裂、第二枚绷紧未断')),
    ('chapter-log 无「七个红结」', 'state_forbid', ('chapter-log.md', '七个红结')),
    ('chapter-log 无「六个红结」', 'state_forbid', ('chapter-log.md', '六个红结')),
    ('chapter-log 阮孤灯＝十三岁一刀杀', 'state_must', ('chapter-log.md', '十三岁一刀杀')),
    ('chapter-log 无阿七「十三岁进沈家」', 'state_forbid', ('chapter-log.md', '十三岁进沈家')),
    ('chapter-log 封存＝近百日', 'state_must', ('chapter-log.md', '近百日')),
    ('chapter-log 第40章自认陆七', 'state_must', ('chapter-log.md', '自认“陆七”')),
    ('plot-check 死亡日＝四月初八', 'state_must', ('plot-check.md', '死亡 = 四月初八')),
    ('plot-check 冥婚日＝七月十五', 'state_must', ('plot-check.md', '冥婚 = 七月十五')),
    ('plot-check 尝药渣＝四月初九', 'state_must', ('plot-check.md', '尝药渣 = 四月初九')),
    ('plot-check 封存＝近百日', 'state_must', ('plot-check.md', '近百日')),
    ('plot-check 陆七落名边界', 'state_must', ('plot-check.md', '第40章渡厄寺下跪自认')),
    ('plot-check 无阿七「十三岁进沈家」', 'state_forbid', ('plot-check.md', '十三岁进沈家')),
    ('plot-check 无「废戏楼」', 'state_forbid', ('plot-check.md', '废戏楼')),
    ('chapters ch2 时辰＝巳时初刻改卯时三刻', 'state_must', ('chapters.md', '“巳时初刻”改成“卯时三刻”')),
    ('chapters 尝药渣＝四月初九', 'state_must', ('chapters.md', '四月初九从灵堂药碗取回的药渣')),
    ('chapters 红结＝七枚、第七枚被挑走', 'state_must', ('chapters.md', '盖头七枚红结中第七枚被人先一步挑走')),
    ('chapters 阮孤灯＝十三岁一刀杀', 'state_must', ('chapters.md', '十三岁一刀杀')),
    ('chapters 第43章落名陆七', 'state_must', ('chapters.md', '写下“陆七”')),
    ('chapters 无阿七「十三岁进沈家」', 'state_forbid', ('chapters.md', '十三岁进沈家')),
    ('requirements 死亡日＝四月初八', 'state_must', ('requirements.md', '四月初八')),
    ('requirements 冥婚日＝七月十五', 'state_must', ('requirements.md', '七月十五')),
    ('requirements 两会不得混称', 'state_must', ('requirements.md', '两个婚礼不得混称')),
    ('requirements 红结＝七枚', 'state_must', ('requirements.md', '红盖头与七枚红结')),
    ('requirements 七方＝六宾客＋明照', 'state_must', ('requirements.md', '六位作保宾客与引魂替身明照共七方')),
    ('requirements 陆七＝第27章信件爆破', 'state_must', ('requirements.md', '身份爆破必须由第 27 章信件完成')),
    ('requirements 阮孤灯＝十三岁一刀杀', 'state_must', ('requirements.md', '十三岁一刀杀')),
    ('requirements 无阿七「十三岁进沈家」', 'state_forbid', ('requirements.md', '十三岁进沈家')),
    # 戏楼命名统一（2026-09-26）：正名「旧戏楼」（章题 ch21《旧戏楼的两把刀》／ch32「旧戏楼在庄子外二里」），
    # 全面消除正文与在役台账里的「废戏楼」别名；revisions.md 属历史台账，其旧记录不回写。
    ('正文统一＝戏楼正名「旧戏楼」', 'book_must', '旧戏楼'),
    ('正文统一＝无「废戏楼」', 'book_forbid', '废戏楼'),
    ('ch19 遗留构＝半塌的旧戏楼', 'must', ('ch19', '半塌的旧戏楼')),
    ('ch21 追至＝东南的旧戏楼', 'must', ('ch21', '东南的旧戏楼')),
    ('ch22 摸到＝旧戏楼', 'must', ('ch22', '摸到旧戏楼时')),
    ('ch40 残台＝旧戏楼', 'must', ('ch40', '旧戏楼残台上')),
    # 方位统一（2026-09-26）：以 ch32「旧戏楼在庄子外二里」为基准，ch10「庄子最北面」孤例已改。
    ('ch10 方位＝旧戏楼在庄子外二里', 'must', ('ch10', '旧戏楼在庄子外二里')),
    ('ch10 无「庄子最北面」', 'forbid', ('ch10', '庄子最北面')),
    ('全书无「庄子最北面」', 'book_forbid', '庄子最北面'),
    ('theme 正名＝旧戏楼', 'state_must', ('theme.md', '旧戏楼')),
    ('theme 无「废戏楼」', 'state_forbid', ('theme.md', '废戏楼')),
    ('outline 无「废戏楼」', 'state_forbid', ('outline.md', '废戏楼')),
    ('chapter-log 无「废戏楼」', 'state_forbid', ('chapter-log.md', '废戏楼')),
    ('chapters 无「废戏楼」', 'state_forbid', ('chapters.md', '废戏楼')),
    ('requirements 无「废戏楼」', 'state_forbid', ('requirements.md', '废戏楼')),
    ('progress 无「废戏楼」', 'state_forbid', ('progress.md', '废戏楼')),
    # 篇幅口径统一（2026-09-26）：旧口径「单章 4000–4500」改为与实测均值一致（全书 43 章约 4982）。
    # 在役规范（requirements／chapters／plot-check／progress／theme）全部收口；历轮带日期的复核/进度记录保留原文。
    ('requirements 篇幅口径＝实测均值', 'state_must', ('requirements.md', '实测均值约')),
    ('requirements 无旧篇幅口径「4000–4500」', 'state_forbid', ('requirements.md', '4000–4500')),
    ('chapters 篇幅硬标准＝实测均值', 'state_must', ('chapters.md', '实测均值约')),
    ('chapters 无旧篇幅口径「4000–4500」', 'state_forbid', ('chapters.md', '4000–4500')),
    ('plot-check 篇幅口径＝实测均值', 'state_must', ('plot-check.md', '实测均值约')),
    ('progress 状态口径＝实测均值', 'state_must', ('progress.md', '实测均值约')),
    ('theme 篇幅口径＝实测均值', 'state_must', ('theme.md', '均值约 4982')),
    # ch42 去元叙述引章：不再出现「第31章」（引章号），改用「那一夜」的回指。
    ('ch42 无元叙引章「第31章」', 'forbid', ('ch42', '第31章')),
    ('ch42 白砚生旧话＝在那一夜说尽', 'must', ('ch42', '在那一夜已经说完了')),
    # 封庄／水师封锁两分（2026-09-26 裁定）：水师封锁湖口自第6日起（军防水路），
    # 官府封庄自第10日起（有司封条／查火），两者相差四日，不得混称。
    ('ch43 水师锁湖／官府封庄并写', 'must', ('ch43', '水师锁湖已十日，官府封庄已六日')),
    ('ch32 水师封锁自第六日', 'must', ('ch32', '自第六日风雪桥起')),
    ('ch38 官差封庄／水师封外口', 'must', ('ch38', '官差封的是庄门，水师封的是外口')),
    ('ch38 无「水师封的是庄门」', 'forbid', ('ch38', '水师封的是庄门')),
    ('timeline 第8日＝水师封锁第三天', 'state_must', ('timeline.md', '水师封锁湖口进入第三天')),
    ('timeline 第10日＝官府正式封庄', 'state_must', ('timeline.md', '第10日官府正式封庄')),
    ('timeline 边界＝水师第6日／官府第10日', 'state_must', ('timeline.md', '水师封锁湖口自第6日起')),
    ('timeline 无「水师封庄」', 'state_forbid', ('timeline.md', '水师封庄')),
    ('chapter-log 封庄＝第10日', 'state_must', ('chapter-log.md', '正式封庄在第10日')),
    ('plot-check 封庄锚＝第10日', 'state_must', ('plot-check.md', '10（官府封庄）')),
    ('plot-check 无旧「对峙+封庄」锚', 'state_forbid', ('plot-check.md', '对峙+封庄')),
    # 台账↔正文绑定（2026-09-26 再扩面：outline／foreshadowing／progress／knowledge／conflicts／artifacts／characters）
    # 把已裁定的日期（四月初八／七月十五／封存近百日／时辰卯→巳）、数量（红结七枚→第七枚被挑走、七方）、
    # 年龄（阿七十二岁、无「十三岁进沈家」）口径锁进其余 state 台账；戏楼正名「旧戏楼」全覆盖。
    ('outline 旧戏楼正名', 'state_must', ('outline.md', '旧戏楼')),
    ('outline 无「废戏楼」', 'state_forbid', ('outline.md', '废戏楼')),
    ('outline 无阿七「十三岁进沈家」', 'state_forbid', ('outline.md', '十三岁进沈家')),
    ('foreshadowing 死亡时辰＝卯时三刻→巳时初刻', 'state_must', ('foreshadowing.md', '卷宗写卯时三刻、真实时刻为巳时初刻')),
    ('foreshadowing 时辰差＝将近两个时辰', 'state_must', ('foreshadowing.md', '提前将近两个时辰')),
    ('foreshadowing 第七枚红结被挑走', 'state_must', ('foreshadowing.md', '第七枚红结先被人挑走')),
    ('foreshadowing 旧戏楼正名', 'state_must', ('foreshadowing.md', '旧戏楼')),
    ('foreshadowing 无「废戏楼」', 'state_forbid', ('foreshadowing.md', '废戏楼')),
    ('foreshadowing 无阿七「十三岁进沈家」', 'state_forbid', ('foreshadowing.md', '十三岁进沈家')),
    ('progress 活人出嫁夜＝四月初八', 'state_must', ('progress.md', '四月初八固定为活人出嫁')),
    ('progress 冥婚补礼日＝七月十五', 'state_must', ('progress.md', '七月十五固定为死后三个月的冥婚补礼')),
    ('progress 封存＝近百日', 'state_must', ('progress.md', '封存近百日')),
    ('progress 无「封存百日」', 'state_forbid', ('progress.md', '封存百日')),
    ('progress 时间锚＝第10日官府封庄', 'state_must', ('progress.md', '10官府封庄')),
    ('progress 无旧「对峙封庄」锚', 'state_forbid', ('progress.md', '对峙封庄')),
    ('progress 篇幅口径＝实测均值', 'state_must', ('progress.md', '实测均值约')),
    ('progress 旧戏楼正名', 'state_must', ('progress.md', '旧戏楼')),
    ('progress 无「废戏楼」', 'state_forbid', ('progress.md', '废戏楼')),
    ('progress 无阿七「十三岁进沈家」', 'state_forbid', ('progress.md', '十三岁进沈家')),
    ('knowledge 命案夜＝四月初八', 'state_must', ('knowledge.md', '四月初八')),
    ('knowledge 冥婚日＝七月十五', 'state_must', ('knowledge.md', '七月十五')),
    ('knowledge 两婚礼不得混称', 'state_must', ('knowledge.md', '不与当前冥婚场混称')),
    ('knowledge 落名边界＝第40章自认', 'state_must', ('knowledge.md', '第40章渡厄寺下跪自认“陆七”')),
    ('knowledge 旧戏楼正名', 'state_must', ('knowledge.md', '旧戏楼')),
    ('knowledge 无「废戏楼」', 'state_forbid', ('knowledge.md', '废戏楼')),
    ('knowledge 无阿七「十三岁进沈家」', 'state_forbid', ('knowledge.md', '十三岁进沈家')),
    ('conflicts 旧戏楼正名', 'state_must', ('conflicts.md', '旧戏楼')),
    ('conflicts 无「废戏楼」', 'state_forbid', ('conflicts.md', '废戏楼')),
    ('conflicts 无阿七「十三岁进沈家」', 'state_forbid', ('conflicts.md', '十三岁进沈家')),
    ('artifacts 旧戏楼正名', 'state_must', ('artifacts.md', '旧戏楼')),
    ('artifacts 无「废戏楼」', 'state_forbid', ('artifacts.md', '废戏楼')),
    ('artifacts 无阿七「十三岁进沈家」', 'state_forbid', ('artifacts.md', '十三岁进沈家')),
    ('characters 阿七真名＝陆七', 'state_must', ('characters.md', '真名：陆七')),
    ('characters 旧戏楼正名', 'state_must', ('characters.md', '旧戏楼')),
    ('characters 无「废戏楼」', 'state_forbid', ('characters.md', '废戏楼')),
    ('characters 无阿七「十三岁进沈家」', 'state_forbid', ('characters.md', '十三岁进沈家')),
]


def state_doc(name):
    """读 state/ 下的台账文件（E 家族里与正文口径绑定的那几行：改正文须同步改台账）。"""
    try:
        return open(os.path.join(HERE, name), encoding='utf-8').read()
    except OSError:
        return ''


def eval_reg(items):
    by = {label(it): it for it in items}
    book = '\n'.join(it['text'] for it in items)
    out = []
    for label_, kind, arg in REG:
        ok, note = True, ''
        if kind == 'book_bad':
            hits = sum(len(arg.findall(it['text'])) for it in items)
            ok = hits == 0
            note = '命中 %d' % hits
        elif kind == 'book_must':
            ok = arg in book
        elif kind == 'book_forbid':
            hits = book.count(arg)
            ok = hits == 0
            note = '命中 %d' % hits
        elif kind == 'newline':
            bad = ['%s(CRLF %d/LF %d)' % (label(it), it['crlf'], it['lf'])
                   for it in items if it['crlf'] > 0 and it['lf'] > 0]
            ok = not bad
            note = '；'.join(bad) if bad else '全部单一风格'
        elif kind.startswith('state_'):
            text = state_doc(arg[0])
            pat = arg[1]
            if kind == 'state_order':
                idxs = [text.find(p) for p in pat]
                ok = all(i >= 0 for i in idxs) and idxs == sorted(idxs)
                note = '升序' if ok else '缺行或乱序'
            else:
                n = text.count(pat)
                if kind == 'state_must':
                    ok = n > 0
                elif kind == 'state_forbid':
                    ok = n == 0
                else:  # state_count
                    ok = n == arg[2]
                    note = '期望 %d' % arg[2]
                note = ('命中 %d' % n) + (('；' + note) if note else '')
        else:
            which, pat = arg
            it = by.get(which)
            text = it['text'] if it else ''
            if kind == 'must':
                ok = pat in text
            elif kind == 'forbid':
                ok = pat not in text
            elif kind == 'must_all':
                missing = [p for p in pat if p not in text]
                ok = not missing
                note = ('缺 ' + '／'.join(missing)) if missing else ''
        out.append((label_, ok, note))
    return out


# ---------------- F 审计清单 ----------------
# 读 state/audit-checklist.md：`- [x]` 闭环项判据硬校验，`- [ ]` 待裁项只登记探测。
_ITEM_RE = re.compile(r'^-\s*\[( |x)\]\s+([AB]\d+)\s*[｜|]\s*(.+)$')
_RULE_RE = re.compile(r'`([^`]+)`')


def load_audit():
    """返回 [(checked, id, title, [rules])]；判据只从含「判据」的行取反引号内规则。"""
    try:
        text = open(AUDIT, encoding='utf-8').read()
    except OSError:
        return []
    items, cur = [], None
    for ln in text.split('\n'):
        m = _ITEM_RE.match(ln)
        if m:
            title = re.split(r'\s*·?\s*判据', m.group(3))[0].strip(' 。；·')
            cur = {'checked': m.group(1) == 'x', 'id': m.group(2), 'title': title, 'rules': []}
            items.append(cur)
        if cur is not None and '判据' in ln:
            cur['rules'].extend(_RULE_RE.findall(ln))
    return items


def _chars(it):
    return len(re.sub(r'\s', '', H1_RE.sub('', it['text'])))


def _resolve(items, ref):
    """ref 既可是 E 段标签（ch39）、也可是 base（chapter-39.md / preface.md）。"""
    for it in items:
        if label(it) == ref:
            return it
    return find_by(items, ref)


def eval_rule(rule, items, book):
    """规则语法：must|forbid|must_all|book_must|book_forbid|state_must|state_forbid|state_count|charlen_max。
    返回 True／False；未知规则返回 None（只提醒，不判）。"""
    kind, _, rest = rule.partition(':')
    if kind in ('must', 'forbid'):
        ref, _, text = rest.partition(':')
        it = _resolve(items, ref)
        t = it['text'] if it else ''
        return (text in t) if kind == 'must' else (text not in t)
    if kind == 'must_all':
        ref, _, texts = rest.partition(':')
        it = _resolve(items, ref)
        t = it['text'] if it else ''
        return all(x in t for x in texts.split('+'))
    if kind == 'book_must':
        return rest in book
    if kind == 'book_forbid':
        return book.count(rest) == 0
    if kind in ('state_must', 'state_forbid'):
        ref, _, text = rest.partition(':')
        n = state_doc(ref).count(text)
        return n > 0 if kind == 'state_must' else n == 0
    if kind == 'state_count':
        ref, _, tail = rest.partition(':')
        text, _, num = tail.rpartition(':')
        return state_doc(ref).count(text) == int(num)
    if kind in ('charlen_max', 'charlen_min'):
        ref, _, num = rest.partition(':')
        it = _resolve(items, ref)
        if not it:
            return None
        return _chars(it) <= int(num) if kind == 'charlen_max' else _chars(it) >= int(num)
    return None


def audit_rows(items):
    """返回 [(item, bad_rules)]；bad_rules 为判据未达的规则列表。"""
    book = '\n'.join(it['text'] for it in items)
    rows = []
    for a in load_audit():
        res = [eval_rule(r, items, book) for r in a['rules']]
        rows.append((a, [r for r, v in zip(a['rules'], res) if v is False]))
    return rows


# ---------------- 输出 ----------------
def scrub(s):
    """报告侧去中文引号，避免 state-md-lint 的 quote-imbalance 误报（例：把 “ ” 换章号括号）。"""
    return s.replace('“', '〔').replace('”', '〕').replace('‘', '‹').replace('’', '›')


def overview(items, scans):
    print('== 概览 ==')
    print('%-8s %6s %4s %4s %4s %4s %4s' % ('章', '字符', 'A1', 'A2', 'B', 'C1', 'C2'))
    tot = [0, 0, 0, 0, 0]
    for it in items:
        s = scans[label(it)]
        chars = len(re.sub(r'\s', '', H1_RE.sub('', it['text'])))
        row = [len(s['halfq']), len(s['pairs']), len(s['esc']),
               len(s['rep_para']), len(s['rep_sent'])]
        tot = [a + b for a, b in zip(tot, row)]
        print('%-8s %6d %4d %4d %4d %4d %4d' % (label(it), chars, *row))
    print('合计： A1 半角引号 %d ／ A2 配对问题 %d ／ B 反斜杠 %d ／ C1 近似段对 %d ／ C2 重复句 %d'
          % tuple(tot))
    print()


def show_family_a_b(items, scans, one=False):
    print('== A 引号 / B 字面转义 ==')
    for it in items:
        s = scans[label(it)]
        if not one and not s['halfq'] and not s['pairs'] and not s['esc']:
            continue
        tag = label(it)
        if s['halfq']:
            print('%s A1 半角引号 ×%d' % (tag, len(s['halfq'])))
            for ln, txt in s['halfq'][:6]:
                print('    L%-4d %s' % (ln, scrub(txt[:46])))
        if s['pairs']:
            print('%s A2 配对：%s' % (tag, '；'.join(s['pairs'])))
        if s['esc']:
            print('%s B1 反斜杠 ×%d' % (tag, len(s['esc'])))
            for ln, txt in s['esc'][:6]:
                print('    L%-4d %s' % (ln, scrub(txt)))
    print()


def show_family_c(items, scans, one=False):
    print('== C 章内重复（候选，需人眼判） ==')
    for it in items:
        s = scans[label(it)]
        if not one and not s['rep_para'] and not s['rep_sent']:
            continue
        tag = label(it)
        for x, y, cont, head in s['rep_para']:
            print('%s C1 段#%d ≈ 段#%d（containment %.2f） %s…' % (tag, x, y, cont, scrub(head)))
        for n, norm, locs in s['rep_sent'][:8]:
            print('%s C2 ×%d L%s 「%s」' % (tag, n, ','.join(map(str, locs[:6])), scrub(norm)))
    print()


def show_family_d(fams, qty):
    print('== D 数字与日期锚点（按表达分组；同一名目多处不同数字＝重点） ==')
    for name in ('D1 日期', 'D2 时辰', 'D2b 时辰计数', 'D3 年龄', 'D5 时段'):
        _, store = fams[name]
        print('-- %s --' % name)
        for expr, locs in sorted(store.items(), key=lambda t: (-len(t[1]), t[0])):
            show = '、'.join(locs[:8]) + ('…' if len(locs) > 8 else '')
            print('  %-8s ×%-3d %s' % (expr, len(locs), show))
        if not store:
            print('  （无）')
    print('-- D4 数量（同一名词 ≥2 种数量表达＝漂移候选） --')
    drift = qty_drift(qty)
    if not drift:
        print('  （无）')
    for noun, forms in drift[:40]:
        parts = ['%s×%d @%s' % (e, len(v), '、'.join(v[:4]) + ('…' if len(v) > 4 else ''))
                 for e, v in sorted(forms.items(), key=lambda t: -len(t[1]))]
        print('  %-10s %s' % (noun, '；'.join(parts)))
    print()


def show_family_e(items):
    print('== E 回归锚点（改稿后应仍成立；有意变更须同步本表） ==')
    bad = 0
    for label_, ok, note in eval_reg(items):
        mark = '✓' if ok else '⚠'
        if not ok:
            bad += 1
        print('  %s %s%s' % (mark, label_, ('  [' + note + ']') if note else ''))
    print('  合计：%d 项，⚠ %d 项' % (len(REG), bad))
    print()


def show_family_f(items):
    print('== F 审计清单（state/audit-checklist.md；[x] 硬校验，[ ] 只登记） ==')
    rows = audit_rows(items)
    if not rows:
        print('  （未找到 audit-checklist.md）')
        print()
        return
    closed = opened = fail = 0
    for a, bad in rows:
        if a['checked']:
            closed += 1
            mark = '⚠' if bad else '✓'
            if bad:
                fail += 1
        else:
            opened += 1
            mark = '○'
        if bad:
            note = '（判据未达：%s）' % '；'.join(bad)
        elif not a['rules']:
            note = '（无判据，待人裁定）'
        else:
            note = ''
        print('  %s %s %s%s' % (mark, a['id'], a['title'], ('  ' + note) if note else ''))
    print('  合计：共 %d 项（已闭环 %d / 待裁 %d）；闭环判据 ⚠ %d 项' % (len(rows), closed, opened, fail))
    print()


def build_report(items, scans, fams, qty):
    import io
    buf = io.StringIO()
    def w(s=''):
        buf.write(s + '\n')

    buf_scrub = scrub
    w('# 《留春信》连续性探针报告（continuity-report.md）')
    w()
    w('> 本文件由 `state/continuity-scan.py --write` 现场重算盖写；**勿手改**。')
    w('> 家族与边界见脚本头部；报告侧把中文引号换成 〔〕‹› 以免触发 state-md-lint 的配对检查。')
    w()
    # overview
    w('## 概览')
    w()
    w('```')
    w('%-8s %6s %4s %4s %4s %4s %4s' % ('章', '字符', 'A1', 'A2', 'B', 'C1', 'C2'))
    tot = [0, 0, 0, 0, 0]
    for it in items:
        s = scans[label(it)]
        chars = len(re.sub(r'\s', '', H1_RE.sub('', it['text'])))
        row = [len(s['halfq']), len(s['pairs']), len(s['esc']), len(s['rep_para']), len(s['rep_sent'])]
        tot = [a + b for a, b in zip(tot, row)]
        w('%-8s %6d %4d %4d %4d %4d %4d' % (label(it), chars, *row))
    w('合计 A1=%d A2=%d B=%d C1=%d C2=%d' % tuple(tot))
    w('```')
    w()
    # E
    w('## E 回归锚点')
    w()
    for label_, ok, note in eval_reg(items):
        w('- %s %s%s' % ('✓' if ok else '⚠', label_, ('（' + note + '）') if note else ''))
    w()
    # F
    w('## F 审计清单')
    w()
    rows = audit_rows(items)
    if not rows:
        w('- （未找到 audit-checklist.md）')
    for a, bad in rows:
        mark = ('⚠' if bad else '✓') if a['checked'] else '○'
        extra = ('（判据未达：%s）' % '；'.join(bad)) if bad else ''
        w('- %s %s %s%s' % (mark, a['id'], a['title'], extra))
    w()
    # A/B
    w('## A 引号 / B 字面转义')
    w()
    any_ab = False
    for it in items:
        s = scans[label(it)]
        if s['halfq'] or s['pairs'] or s['esc']:
            any_ab = True
            if s['halfq']:
                w('- %s A1 半角引号 ×%d：%s' % (label(it), len(s['halfq']),
                                             '；'.join('L%d %s' % (l, buf_scrub(t)[:40]) for l, t in s['halfq'][:6])))
            if s['pairs']:
                w('- %s A2：%s' % (label(it), '；'.join(s['pairs'])))
            if s['esc']:
                w('- %s B1 反斜杠 ×%d：%s' % (label(it), len(s['esc']),
                                            '；'.join('L%d %s' % (l, buf_scrub(t)) for l, t in s['esc'][:6])))
    if not any_ab:
        w('无（A1／A2／B 全部通过）')
    w()
    # C
    w('## C 章内重复（候选）')
    w()
    any_c = False
    for it in items:
        s = scans[label(it)]
        if s['rep_para'] or s['rep_sent']:
            any_c = True
            for x, y, cont, head in s['rep_para']:
                w('- %s C1 段#%d ≈ 段#%d（%.2f）%s…' % (label(it), x, y, cont, buf_scrub(head)))
            for n, norm, locs in s['rep_sent'][:8]:
                w('- %s C2 ×%d L%s 「%s」' % (label(it), n, ','.join(map(str, locs[:6])), buf_scrub(norm)))
    if not any_c:
        w('无')
    w()
    # D
    w('## D 数字与日期锚点')
    w()
    for name in ('D1 日期', 'D2 时辰', 'D2b 时辰计数', 'D3 年龄', 'D5 时段'):
        _, store = fams[name]
        w('### %s' % name)
        w()
        if not store:
            w('- （无）')
        for expr, locs in sorted(store.items(), key=lambda t: (-len(t[1]), t[0])):
            show = '、'.join(locs[:10]) + ('…' if len(locs) > 10 else '')
            w('- %s ×%d：%s' % (expr, len(locs), show))
        w()
    w('### D4 数量漂移候选（同一名词 ≥2 种数量表达）')
    w()
    drift = qty_drift(qty)
    if not drift:
        w('- （无）')
    for noun, forms in drift[:60]:
        parts = ['%s×%d @%s' % (e, len(v), '、'.join(v[:4]) + ('…' if len(v) > 4 else ''))
                 for e, v in sorted(forms.items(), key=lambda t: -len(t[1]))]
        w('- %s：%s' % (noun, '；'.join(parts)))
    w()
    return buf.getvalue()


# ---------------- main ----------------
def main():
    argv = sys.argv[1:]
    fam = 'all'
    do_write = False
    target = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--family' and i + 1 < len(argv):
            fam = argv[i + 1]; i += 2; continue
        if a == '--write':
            do_write = True; i += 1; continue
        if a == '--no-write':
            do_write = False; i += 1; continue
        if a in ('-h', '--help'):
            print(__doc__); return
        target = a; i += 1

    items = load_all()
    scans = {label(it): dict(zip(['halfq', 'pairs'], fam_a(it)),
                             esc=fam_b(it), rep_para=fam_c1(it), rep_sent=fam_c2(it))
             for it in items}
    fams, qty = collect_numeric(items)

    if target is not None:
        it = find_by(items, target.lstrip('./'))
        if it is None:
            print('找不到目标：%s' % target); return
        only = [it]
        print('=== %s（%s）单章明细 ===\n' % (label(it), it['base']))
        show_family_a_b(only, scans, one=True)
        show_family_c(only, scans, one=True)
        return

    if fam in ('all', 'a', 'b', 'ab'):
        overview(items, scans)
    if fam in ('all', 'a', 'b', 'ab'):
        show_family_a_b(items, scans)
    if fam in ('all', 'c'):
        show_family_c(items, scans)
    if fam in ('all', 'd'):
        show_family_d(fams, qty)
    if fam in ('all', 'e'):
        show_family_e(items)
    if fam in ('all', 'f'):
        show_family_f(items)

    if do_write:
        md = build_report(items, scans, fams, qty)
        with open(REPORT, 'w', encoding='utf-8', newline='\n') as f:
            f.write(md)
        print('已写 %s（%d 字节，全部现场重算）' % (os.path.relpath(REPORT, BOOK), len(md.encode('utf-8'))))


if __name__ == '__main__':
    main()
