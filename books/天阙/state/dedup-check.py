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
       ⑨ F10 章题声明与旧题禁引 (自 ch141 起): 新章题必须先声明于卷纲(outline-vol7.md 管 141-164, outline-vol8.md 管 165-188, outline-vol9.md 管 189-212, outline-vol10.md 管 213-236, 随卷演进);
          正文禁回引卷六旧题(粮行的一笔/船坞的三十年等, 源: chapter-title-index.md);
          卷三—卷六现有章另做卷纲声明与实际章题一致性复核(仅报告漂移, 不算失败)
       ⑩ F14 回声式对话纪律 (ch141+ 判失败; 存量仅报告): 机械回声(重复且无新信息)禁止,
          戏剧节拍(重复后接展开)允许; F14A 相邻整句回声问答对, F14B 标记式重复密度≤2
       ⑪ F16 金句家族纪律 (ch189+ 判失败; ch1-188 存量仅报告): 同一金句家族(语义同源变体)
          单章合计≤2; 同一成员短语连续6段内≥2 或整章≥3 视为逐字连发, 禁止(书挡须相隔>6段)
       ⑫ F17 卷九洛阳段器物锚点 (ch189-212, dedup-baseline-vol9.md): 两套编号/核销卷/折色/船耗/
       ⑬ F18 裸回声问句纪律 (ch189+, 卷九对白语气审计): ≤3字引号问句单章≤2, 防全员审讯腔
          死引/燎角/虚额/回禀稿/冷金笺/油布/底册 仅在落点章作章眼, 其余卷九章 0 次(指代改写)
       ⑭ F20 榜单引用核验 (全书): 正文出现 宗师录/黑榜/八凶/第X席 时自动比对 state/rankings.md
          席位与 state/chronology.md 生年×正文年份——F20S 台账自审(席位年龄↔生年)/F20a 席位配对
          (裴十三=第十二席空缺)/F20b 年龄换算(生年+当前年)/F20c 黑榜榜首年份/F20d 八凶称号/
          F20e 单章单榜≤2; 数据源运行时解析, 改 rankings.md/chronology.md 即生效, 无需同步本文件
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
    "记人的账": {44: 1, 45: 1},  # ch44 卷末收束预言, ch45 开卷回响(与 ch53 章题同族), 正典呼应
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
# === F15·卷九回收链机械校验 (ch189-212, 与 outline-vol9 章眼/意象链检查表同步) ===
# 每章至少命中任一组 token 之一(任何一组内任意词出现即满足该组), 防止写 ch189-212 时漏掉章眼意象。
# 维护约定: 改 outline-vol9 章眼、意象链检查表或 foreshadowing 卷九回收规划区, 必须先同步本表。
VOL9_REQ = {
    189: [["两套编号"], ["旧档库"]], 190: [["折色"], ["船耗"]], 191: [["药案"], ["忌铁器"]],
    192: [["暗桩"], ["在记他"]], 193: [["虚额"], ["缺口"]], 194: [["冷金笺"], ["不点了"]],
    195: [["抄经房"], ["待抄"]], 196: [["天阙有后"], ["实验"]], 197: [["阿青"], ["缝衣裳"]],
    198: [["永不核销"], ["裴令仪"]], 199: [["铁链"], ["错本", "抄错"]], 200: [["簿外"], ["替簿子活着"]],
    201: [["凌虚"], ["三道盘查"]], 202: [["蒋默"], ["十二份"]], 203: [["两户"], ["三百年前"]],
    204: [["保奴"], ["括户"]], 205: [["底册"], ["样本"]], 206: [["铁碰铁"], ["食盒"]],
    207: [["凌虚"], ["让开"]], 208: [["裴令仪"], ["竹简"]], 209: [["夹墙"], ["暗格"]],
    210: [["抄页"], ["烧不掉"]], 211: [["火盆"], ["干饼"]], 212: [["灰烬"], ["无碑坟"], ["立碑"]],
}
# === F17 卷九洛阳段器物锚点 (ch189-212, 与 dedup-baseline-vol9.md 同步) ===
# 语义: dict {短语: {落点章: 允许次数}} 或 int(全卷每章统一上限)。
#   dict 值: None=该落点章不限(章眼铺陈章); int=该章允许次数; 未列出的卷九章节一律 0 次。
# 防的是锚点器物跨章连发/串用——"两套编号/折色/船耗/冷金笺"等只在落点章作章眼, 其余卷九章须指代改写。
# 维护约定: 改 outline-vol9 洛阳段章眼或 dedup-baseline-vol9.md, 必须先同步本表。
VOL9_ANCHORS = {
    "两套编号": {189: None, 194: 1},   # ch189 物证(分署号vs总署号) / ch194 抄本留档
    "核销卷": {189: None, 192: 1},     # ch189 袁五核销卷 / ch192 夜里对档
    "折色": {190: None},               # ch190 章眼
    "船耗": {190: None},               # ch190 章眼伴器
    "死引": {190: None},               # ch190 套话核心
    "燎角": {191: 1},                  # ch191 药案缺三字处
    "虚额": {193: 1},                  # ch193 虚额田册
    "回禀稿": {193: 1},                # ch193 卷库角落新页
    "冷金笺": {194: 1},                # ch194 约信纸(ch112 同源纸)
    "油布": 1,                         # 全卷每章≤1 (ch191 药案交接包装)
    "底册": {194: None, 198: None, 205: None, 209: None, 211: None, 212: None},
}  # 底册=活档三件主线词: 落点章(194首现/198裴度判断/205章眼/209取回/211入火盆/212随身)不限, 其余卷九章 0 次
# === F15·卷十回收链机械校验 (ch213-236, 与 outline-vol10 意象链检查表同步) ===
# 每章至少命中任一组 token 之一, 防止写 ch213-236 时漏掉章眼意象。
# 维护约定: 改 outline-vol10 意象链检查表或 foreshadowing 卷十区, 必须先同步本表。
VOL10_REQ = {
    213: [["秤"], ["分路"], ["碑"]], 214: [["行台"], ["朱印"]], 215: [["盲校"], ["太干净"]],
    216: [["浮数"], ["仓里无"]], 217: [["一斗米"]], 218: [["九成仓"], ["官斛", "斛"]],
    219: [["对粮"], ["底册"]], 220: [["样本"], ["空账"]], 221: [["算稿"], ["裴十三"]],
    222: [["天阙有后"], ["一分为三"]], 223: [["忌铁器"], ["吃人的账"]], 224: [["空灶"], ["编"]],
    225: [["假数"], ["闭环"]], 226: [["永不核销"], ["吃册"]], 227: [["牺牲一城"], ["大阵"]],
    228: [["算得出天下"], ["竹简"]], 229: [["朱批"], ["抄副"]], 230: [["崩仓"], ["叫出名字", "名字"]],
    231: [["十万"], ["没有名字"]], 232: [["十个"], ["名字"]], 233: [["断秤"], ["第一笔假数"]],
    234: [["自首"], ["永不核销"]], 235: [["还账"], ["划回"]], 236: [["收秤"]],
}
# === F19 卷十器物/词频锚点 (ch213-236, 与 outline-vol10 意象密度硬约束12同步) ===
# 语义: {词: {unlimited: 不限章集合, cap: 其余卷十章单章上限}}。
# 防的是"天阙"作感叹词滥用、"永不核销"跨章连发。
VOL10_CAPS = {
    "天阙": {"unlimited": {222}, "cap": 1},       # ch222 正题揭晓章不限; 其余单章≤1
    "永不核销": {"unlimited": {226, 234}, "cap": 0},  # 全卷≤2 (ch226/234 各一次); 其余 0(指代改写)
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
# === F14 回声式对话纪律 (ch141+ 判失败; 存量仅报告) ===
# 判定标准 —— 机械回声 vs 戏剧节拍 (源: 卷五 ch90-115 回声清洗审计 + 卷六 ch117-140 密度审计):
#   · 机械回声(禁止) = 后一句原样复读前一句的尾词/整句, 且不含任何新信息, 纯复读:
#       例: "反向的账？""反向的账。" / "全对上了。""全对上了。" / 短问答 "X？""X。"
#   · 戏剧节拍(允许) = 重复之后紧跟展开(新信息/解释/行动), 或重复本身承担节奏功能:
#       例: "一整槽。""一整槽。养马的人把槽扩了——" (重复+展开)
#            "回来了。""回来了。" (戍卒归来的沉默留白, 属刻意节拍)
#   判断口诀: 重复后接"新信息增量"=戏剧节拍, 可留; 重复后无任何增量=机械回声, 必改。
# F14A 相邻整句回声: 相邻两段引号内正文完全相同(允许中间夹"XX说"式归属行) → 判失败(ch141+)。
#     刻意留白的重复节拍须登记于 F14_ECHO_ALLOW {章号: [短语]}, 每章限1次。
# F14B 标记式重复: "重复了一遍/又念了一遍/重复道" 单章≤2 (卷六实测密度 0.6/章);
#     命中后段内须有新信息增量(重复词之外的续句), 否则按机械回声报告。
#     写作纪律: 需要"重复+强调"时, 优先用变体(换人称/换标点/加修饰), 不要原字复读。
F14_ECHO_ALLOW: dict[int, list[str]] = {
    # 存量章已核验的"问答确认+紧跟展开"或"名称回指+新信息"节拍 (F14 判定口诀: 重复后接增量=戏剧节拍, 可留):
    144: ["办完了"],     # “办完了？”/“办完了。”主事说，回报二月廿四递的… (确认+展开)
    155: ["就这一页"],   # “就这一页？”/“就这一页。”宁红叶说，“别的不在草垛底下。” (确认+展开)
    158: ["保奴", "待查"],  # 章眼名被裴弘度/书吏念出后展开评述 (名称回指+增量)
    160: ["随军查账的", "不问来路"],  # 门岗问答确认 (前者纯确认属自然门岗对话; 后者接“牌上不写名字…”展开)
    161: ["不明"],       # 门房写"不明"→裴弘度未见那道"不明", 同一物证笔迹回指(第二段带新信息展开)
    166: ["能看清规律的人"],  # 段A尾旧档引语 → 段B“观天台从来不放过…” (叙事书挡+增量)
    167: ["兵在河东"],   # “兵在河东。”她重复了一遍，“河东北边是回纥…” (显式重复标记+展开)
}  # {章号: [允许整句重复的短语]}, 同章多处须逐条登记
F14_MARKERS = ["重复了一遍", "又念了一遍", "重复道"]
F14_MARKER_CAP = 2
# === F16 金句家族纪律 (ch189+ 判失败; ch1-188 存量仅报告) ===
# 判定标准 (源: 全库金句家族扫描审计 —— 卷四/五/六 1.3-1.4次/章热点, ch92 16行三锤链):
#   · 家族密度: 同一金句家族(语义同源变体)单章合计 ≤2 次。金句只允许以三种形态存活:
#     章题背书的主旨句 / 信件首尾书挡 / 单次人物台词。超过即"金句复读"(全员账房化来源)。
#   · 逐字连发: 同一成员短语在连续 F16_CHAIN_WIN 段内原样出现 ≥2 次 → 机械连发, 禁止;
#     同一成员短语整章 ≥3 次 → 无论距离一律判为锤句链(如 ch92 原 "名在纸上…就有人能查" 三锤)。
#     例外: 恰 2 次且相距 >F16_CHAIN_WIN 段(信件首尾书挡, 如 ch146 严平信) = 戏剧节拍, 允许。
#   · 写作纪律: 需要强调时用变体(换主语/换说法/换句式), 不要原字复读;
#     确需超限须登记 F16_FAMILY_ALLOW {章号: {家族: 允许次数}}。
F16_START = 189
F16_FAMILIES = {
    "账理生死": ["账是死的", "账是活的", "路是死的", "人是活的"],
    "纸上落名": ["名在纸上", "账在纸上", "账在，人在", "账在，人就在", "人在，账在"],
    "名字是死人的": ["名字是死人的", "名字是死的"],
    "算得清否": ["算得清", "算不清"],
    "账比人长": ["账比人走得快", "账比命长", "账比人长"],
    "只算账": ["我只算账", "只算账，不算命", "算账的不算命"],
}
F16_FAMILY_CAP = 2
F16_CHAIN_WIN = 6
F16_FAMILY_ALLOW: dict[int, dict[str, int]] = {}  # {章号: {家族: 允许次数}} 超限登记

# === F18 裸回声问句纪律 (ch189+ 判失败): 沈广农式"X？"回声问句是主角审讯签名,
# 但 顾琰( ch208 对裴令仪)、老人( ch203 ) 同型连用会全员同质化。
# 判定: 独立成行的引号问句, 正文≤3字, 且非通用问词 → 裸回声。单章 ≤F18_CAP 次。
# 通用问词(什么/谁/哪儿/后来呢/嗯等)不计数。变体写法: 扩成"十万户的活人？""那它在哪里？"。
F18_START = 189
F18_CAP = 2
F18_GENERIC = {"什么", "为什么", "怎么", "谁", "哪儿", "哪里", "几时", "何时", "多久", "哪个",
              "干什么", "后来呢", "什么字", "什么话", "那", "这", "何处", "如何"}
LQ, RQ, QM = "\u201c", "\u201d", "\uff1f"
# === F20 榜单引用核验 (全书生效, 2026-09-09): 每章正文出现 宗师录/黑榜/八凶/第X席 引用时,
# 自动比对 state/rankings.md 席位与 state/chronology.md 生年×正文年份的年龄换算
# (宗师补种闭环核验机械化, 防写作时临时查表出错)。数据源运行时解析两份台账:
# 改 rankings.md / chronology.md 即自动生效, 无需同步本文件。
#   F20S 台账自审: rankings 宗师录各席 755 年龄 ↔ chronology 表三生年 (生年带"约"±1) 逐席验算
#   F20a 席位配对: 「第X席」同句±邻窗出现榜单人物名 → X 必须等于其 rankings 席位;
#       席号>12 或「宗师录…≠十二席」判失败; 裴十三=第十二席(空缺, 无人敢补)正典
#   F20b 年龄换算: 榜单人物名紧邻「…岁」→ 数值必须落在本章候选年份(chronology 卷表)的
#       生年+当前年(±1, 生年带约); 卷纲未登记章退化为 755—779 全域可行域(仅拦不可能年龄);
#       回溯年龄(「十七岁那年」)须句内自带年份锚, 特例登记 RANK_AGE_ALLOW
#   F20c 黑榜榜首年份: 黑榜+榜首/第一 同句具名 → 人名必须属于候选年份正典榜首
#       (rankings 黑榜变化时间线: 755—762 慕容荒 / 763—775 李承洲 / 776—778 沈广农)
#   F20d 八凶称号张冠李戴: 八凶姓名与他人称号同句(单称号句)判失败
#   F20e 每章单榜提及 ≤2 (foreshadowing「榜单体系植入区」纪律机械化)
RANK_VOL_YEARS = {1: (755, 755), 2: (756, 757), 3: (757, 757), 4: (757, 760), 5: (759, 760),
                  6: (760, 761), 7: (762, 763), 8: (763, 763), 9: (764, 766), 10: (766, 770),
                  11: (770, 772)}  # 与 chronology.md「卷一—卷十时间范围」表同步; 卷十一暂据 foreshadowing(770—772), chronology 卷表登记后校对
RANK_FIRST = (("慕容荒", 755, 762), ("李承洲", 763, 775), ("沈广农", 776, 778))  # rankings「黑榜变化时间线」正典; 改 rankings 须同步
RANK_AGE_ALLOW: dict[int, set[str]] = {}            # {章号: {"人名:岁值"}} 回溯年龄等特例豁免
RANK_MENTION_ALLOW: dict[int, dict[str, int]] = {}  # {章号: {"宗师录"/"黑榜"/"八凶": 允许次数}} 存量超限豁免
_AGE_RE = re.compile(r"(?:一百[零一二三四五六七八九十]{1,3}|\d{1,3}|[一二三四五六七八九十]{1,4})多?岁")
_F20_CACHE: dict = {}

def cn2num(s: str):
    """中文数字→整数 (一~一百九十九 及阿拉伯数字); 解析失败返回 None。"""
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if s.startswith("十"):
        s = "一" + s
    total = 0
    for seg in re.findall(r"[一二三四五六七八九]?百|零|[一二三四五六七八九]?十|[一二三四五六七八九]", s):
        if seg == "零":
            continue
        if seg.endswith("百"):
            total += ("一二三四五六七八九".index(seg[0]) + 1) * 100 if len(seg) == 2 else 100
        elif seg.endswith("十"):
            total += ("一二三四五六七八九".index(seg[0]) + 1) * 10 if len(seg) == 2 else 10
        else:
            total += "一二三四五六七八九".index(seg) + 1
    return total or None

def _rank_data():
    """解析 state/rankings.md: (宗师录[(席词,人名,755岁)], 黑榜{人名:席词}, 八凶{人名:称号})。"""
    if "seats" in _F20_CACHE:
        return _F20_CACHE["seats"], _F20_CACHE["black"], _F20_CACHE["bafeng"]
    seats, black, bafeng = [], {}, {}
    p = ROOT / "state" / "rankings.md"
    if p.exists():
        for sec in re.split(r"^## ", norm(p.read_text(encoding="utf-8")), flags=re.M):
            head = sec.split("\n", 1)[0]
            if head.startswith("一、《天下宗师录》"):
                for m in re.finditer(r"^\|\s*([一二三四五六七八九十]{1,2})\s*\|\s*([^|]+?)\s*\|\s*(\d{1,3})\s*\|", sec, flags=re.M):
                    seats.append((m.group(1), m.group(2).replace("*", "").strip(), int(m.group(3))))
            elif head.startswith("二、黑榜"):
                for m in re.finditer(r"^\|\s*\*\*(第一|第二|第三|第四|第五|第六|第七|第八|第九|第十)\*\*\s*\|\s*([^|]+?)\s*\|", sec, flags=re.M):
                    black[m.group(2).replace("*", "").strip()] = m.group(1)
            elif head.startswith("三、八凶"):
                for m in re.finditer(r"^\|\s*([^|*]+?)\s*\|\s*([^|*]+?)\s*\|", sec, flags=re.M):
                    t, nm = m.group(1).strip(), m.group(2).strip()
                    if t and nm and t != "称号" and nm != "姓名" and not set(t) <= set("-:： "):
                        bafeng[nm] = t
    _F20_CACHE.update(seats=seats, black=black, bafeng=bafeng)
    return seats, black, bafeng

def _birth_years():
    """解析 state/chronology.md 表三: {人名: (生年, 是否约数)}。"""
    if "births" in _F20_CACHE:
        return _F20_CACHE["births"]
    out = {}
    p = ROOT / "state" / "chronology.md"
    if p.exists():
        for m in re.finditer(r"^\|\s*\*{0,2}([^|*]+?)\*{0,2}(?:（[^）]*）)?\s*\|\s*(约)?(\d{3})\s*\|", norm(p.read_text(encoding="utf-8")), flags=re.M):
            out[m.group(1).strip()] = (int(m.group(3)), bool(m.group(2)))
    _F20_CACHE["births"] = out
    return out

def _vol_year_cands(n: int) -> list:
    """本章候选年份: chronology 卷表区间展开; 卷纲未登记章(卷十二+)退化为 755—779 全域。"""
    for a, b, v in ((1, 20, 1), (21, 44, 2), (45, 68, 3), (69, 92, 4), (93, 116, 5), (117, 140, 6),
                    (141, 164, 7), (165, 188, 8), (189, 212, 9), (213, 236, 10), (237, 260, 11)):
        if a <= n <= b:
            lo, hi = RANK_VOL_YEARS[v]
            return list(range(lo, hi + 1))
    return list(range(755, 780))

def f20_selfaudit() -> list:
    """F20S: rankings 宗师录各席 755 年龄 ↔ chronology 表三生年 逐席验算。"""
    seats, _, _ = _rank_data()
    births = _birth_years()
    out = []
    for seatw, nm, age in seats:
        b = births.get(nm)
        if not b:
            out.append(f"「{nm}」(第{seatw}席) 在 chronology.md 表三无生年行——补台账后 F20b 年龄换算才可校验")
            continue
        by, approx = b
        if abs((755 - by) - age) > (1 if approx else 0):
            out.append(f"「{nm}」rankings.md 755年 {age} 岁 ≠ chronology 生年{by}{'(约)' if approx else ''}推算 {755 - by} 岁")
    return out

def f20_check(n: int, body: str):
    """F20 单章核验, 返回 (fails, notes, used)。used=本章含榜单引用。"""
    fails, notes = [], []
    if not (("宗师录" in body) or ("黑榜" in body) or ("八凶" in body)
            or re.search(r"第[一二三四五六七八九十]{1,2}席", body)):
        return fails, notes, False
    seats, black, bafeng = _rank_data()
    births = _birth_years()
    seat_of = {nm: cn2num(w) for w, nm, _ in seats}
    seat_of["裴十三"] = 12  # 第十二席空缺正典: 裴十三殁后无人敢补
    names = sorted({*seat_of, *black, *bafeng, "沈广农", "裴弘度"}, key=len, reverse=True)
    cands = _vol_year_cands(n)
    allow_age = RANK_AGE_ALLOW.get(n, set())
    yr_span = f"{min(cands)}—{max(cands)}" if len(cands) > 1 else str(cands[0])
    for w in ("宗师录", "黑榜", "八凶"):  # F20e 单章单榜≤2
        c = body.count(w)
        if c > RANK_MENTION_ALLOW.get(n, {}).get(w, 2):
            fails.append(f"F20e 单章「{w}」提及 ×{c} (上限2——foreshadowing 榜单植入区纪律)")
    for sent in [s for s in re.split(r"[。！？；…\n]+", body) if s.strip()]:
        for m in re.finditer(r"第([一二三四五六七八九十]{1,2})席", sent):  # F20a 席位配对
            x = cn2num(m.group(1))
            if x is None:
                continue
            if x > 12:
                fails.append(f"F20a 席位越界「第{m.group(1)}席」(宗师录只有十二席)——句:{sent.strip()[:26]}")
                continue
            win = sent[max(0, m.start() - 12): m.start()] + sent[m.end(): m.end() + 10]
            for nm in names:
                if nm in win and seat_of.get(nm) and seat_of[nm] != x:
                    fails.append(f"F20a 席位配对冲突:「{nm}」rankings.md 第{seat_of[nm]}席, 正文作「第{m.group(1)}席」——句:{sent.strip()[:26]}")
        for m in re.finditer(r"宗师录[^。！？\n]{0,10}?(十[一二三四五六七八九]?|二十|三十)席", sent):
            if m.group(1) != "十二":
                fails.append(f"F20a 宗师录席数「{m.group(1)}席」≠ 正典十二席——句:{sent.strip()[:26]}")
        for nm in names:  # F20b 年龄换算
            if nm not in sent or not births.get(nm):
                continue
            by, approx = births[nm]
            lo, hi = min(y - by for y in cands), max(y - by for y in cands)
            for occ in re.finditer(re.escape(nm), sent):
                seg = sent[max(0, occ.start() - 6): occ.start()] + "|" + sent[occ.end(): occ.end() + 7]
                for am in _AGE_RE.finditer(seg):
                    v = cn2num(am.group(0)[:-1])  # 整段匹配(如"十六岁"/"70岁"/"八十多岁")剥尾字"岁"
                    if v is None or not (3 <= v <= 150) or f"{nm}:{v}" in allow_age:
                        continue
                    if not (lo - (1 if approx else 0) <= v <= hi + (1 if approx else 0)):
                        fails.append(f"F20b 年龄换算冲突:「{nm}」正文 {v} 岁 vs 生年{by}{'(约)' if approx else ''}→本章 {yr_span} 年应为 {lo}—{hi} 岁——句:{sent.strip()[:26]}")
        if "黑榜" in sent and re.search(r"榜首|黑榜[^。！？\n]{0,6}第一|第一[^。！？\n]{0,4}黑榜", sent):  # F20c
            named = False
            for nm in names:
                if nm in sent:
                    named = True
                    if not any(h == nm and a <= y <= b for h, a, b in RANK_FIRST for y in cands):
                        canon = "/".join(f"{h}({a}—{b})" for h, a, b in RANK_FIRST)
                        fails.append(f"F20c 黑榜榜首年份冲突: 正文将「{nm}」置于榜首, 本章 {yr_span} 年正典榜首 {canon}——句:{sent.strip()[:26]}")
            if not named:
                notes.append(f"F20c 黑榜榜首陈述未具名(机械核验仅拦具名冲突), 请自查与 rankings.md 正典一致——句:{sent.strip()[:26]}")
        clauses = re.split(r"[，、：；—…（）()]+", sent)  # F20d 八凶称号: 分句级+相邻搭配判定(同句跨逗号不算, 防"韩魁往南去了，鬼算的折子…"误报)
        for cl in clauses:
            titles_in = [t for t in {t for t in bafeng.values()} if t in cl]
            if len(titles_in) != 1:
                continue
            holder = next((nm for nm, t0 in bafeng.items() if t0 == titles_in[0]), "")
            for nm in names:
                if nm == holder or nm not in cl:
                    continue
                pair = re.escape(nm) + r"[^\u4e00-\u9fff]{0,2}" + re.escape(titles_in[0]) + r"|" + re.escape(titles_in[0]) + r"[^\u4e00-\u9fff]{0,2}" + re.escape(nm)
                if re.search(pair, cl):
                    tag = f"(称号={bafeng[nm]})" if nm in bafeng else "(非八凶人物)"
                    fails.append(f"F20d 称号串名:「{titles_in[0]}」与「{nm}」{tag}相邻成搭配——句:{cl.strip()[:26]}")
    return fails, notes, True

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

def _echo_core(s: str) -> str:
    """F14A 提取段落用于回声判定的核心正文: 取引号内正文(若有), 去首尾引号/空白/尾标点。"""
    m = re.search(r"[“\"]([^”\"]*)[”\"]", s)
    t = m.group(1) if m else s
    return t.strip().strip("“”‘’\"'。！？!?，,、")

def _family_counts(text: str) -> dict[str, int]:
    """合并重叠 span 后统计各金句家族命中次数(子串重叠不重复计, 防"账是死的"嵌套于长句时双算)。"""
    out = {}
    for fam, phrases in F16_FAMILIES.items():
        spans = []
        for ph in phrases:
            for m in re.finditer(re.escape(ph), text):
                spans.append((m.start(), m.end()))
        if not spans:
            continue
        spans.sort()
        merged, cur = 0, None
        for s, e in spans:
            if cur is None or s >= cur:
                merged += 1
                cur = e
            else:
                cur = max(cur, e)
        out[fam] = merged
    return out

def main():
    args = [int(a) for a in sys.argv[1:]]
    if not args:
        print(__doc__); sys.exit(2)
    vol2 = [load_ch(i) for i in range(1, 45)]
    # vol6: base = 前五卷全116章 + 已写卷六章(比 n 小), 用于跨卷 14字滑窗
    vol6_base = [load_ch(i) for i in range(1, 117)] if any(a >= 117 for a in args) else []
    fail = 0
    # F20S 榜单台账自审 (rankings.md 席位年龄 ↔ chronology.md 生年, 每次运行一次)
    f20s = f20_selfaudit()
    if f20s:
        fail += 1
        print("[F20S·榜单台账自审]")
        for h in f20s:
            print(f"  × {h}")
    else:
        print("[F20S·榜单台账自审] ✓ (rankings 席位年龄 ↔ chronology 生年逐席一致)")
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
        # F14 回声式对话纪律: F14A 相邻整句回声问答对; F14B 标记式重复密度 (ch141+ 判失败)
        f14_hits = []
        paras = [p.strip() for p in body.split("\n") if p.strip()]
        allow = F14_ECHO_ALLOW.get(n, [])
        for i in range(len(paras) - 1):
            core_a = _echo_core(paras[i])
            core_b = _echo_core(paras[i + 1])
            if core_a and core_b and len(core_a) >= 2 and core_b == core_a and not any(
                    core_a == c for c in allow):
                f14_hits.append(f"F14A 相邻整句回声「{core_a}」 (第{i+1}/{i+2}段)")
        m_cnt = sum(body.count(m) for m in F14_MARKERS)
        if m_cnt > F14_MARKER_CAP:
            f14_hits.append(f"F14B 标记式重复×{m_cnt} (上限{F14_MARKER_CAP})")
        if f14_hits:
            if n >= 141:
                fail += 1
            print("  [F14·回声式对话]" + ("" if n >= 141 else " (存量, 仅报告)"))
            for h in f14_hits[:10]:
                print(f"    × {h}")
        elif n >= 141:
            print(f"  [F14·回声式对话] ✓ (标记式重复×{m_cnt} ≤ {F14_MARKER_CAP})")
        # F16 金句家族纪律: 家族合计≤2; 逐字连发(连续6段内≥2 或 整章≥3) (ch189+ 判失败; 存量仅报告)
        f16_hits = []
        for fam, c in _family_counts(body).items():
            allow = F16_FAMILY_ALLOW.get(n, {}).get(fam, F16_FAMILY_CAP)
            if c > allow:
                f16_hits.append(f"家族「{fam}」×{c} (上限{allow})")
        paras2 = [p.strip() for p in body.split("\n") if p.strip()]
        for fam, phrases in F16_FAMILIES.items():
            for ph in phrases:
                per = [p.count(ph) for p in paras2]
                tot = sum(per)
                if tot >= 3:
                    f16_hits.append(f"逐字连发「{ph}」整章×{tot} (≥3 即锤句链)")
                elif tot == 2 and any(sum(per[i:i + F16_CHAIN_WIN]) >= 2 for i in range(len(per))):
                    f16_hits.append(f"逐字连发「{ph}」×2 落在连续{F16_CHAIN_WIN}段内 (书挡须相距>{F16_CHAIN_WIN}段)")
        if f16_hits:
            if n >= F16_START:
                fail += 1
            print("  [F16·金句家族]" + ("" if n >= F16_START else " (存量, 仅报告)"))
            for h in f16_hits[:10]:
                print(f"    × {h}")
        elif n >= F16_START:
            print("  [F16·金句家族] ✓")
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
            decl_file = ("outline-vol7.md" if n <= 164 else ("outline-vol8.md" if n <= 188
                         else ("outline-vol9.md" if n <= 212 else "outline-vol10.md")))
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
        req_tbl = (VOL10_REQ if 213 <= n <= 236 else
                   (VOL9_REQ if 189 <= n <= 212 else (VOL8_REQ if 165 <= n <= 188 else VOL7_REQ)))
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
                    print(f"    × 缺「{m}」——本章回收章眼未落位(同步见各卷 outline 章眼/意象链检查表)")
        # F17 卷九洛阳段器物锚点 (ch189-212, 与 dedup-baseline-vol9.md 同步): 锚点器物只在落点章出现
        if 189 <= n <= 212:
            f17_hits = []
            for ph, spec in VOL9_ANCHORS.items():
                cnt = body.count(ph)
                if isinstance(spec, dict):
                    if n in spec:
                        cap = spec[n]  # None=该落点章不限
                        if cap is not None and cnt > cap:
                            f17_hits.append((ph, cnt, cap))
                    elif cnt > 0:
                        f17_hits.append((ph, cnt, 0))
                elif cnt > spec:
                    f17_hits.append((ph, cnt, spec))
            if f17_hits:
                fail += 1
                v6_issue = True
                print("  [F17·卷九洛阳段器物锚点超限]")
                for ph, c, m in f17_hits:
                    print(f"    × {ph}  ×{c} (本章上限{m})——锚点器物仅在落点章作章眼, 其余卷九章须指代改写(见 dedup-baseline-vol9.md)")
        # F19 卷十器物/词频锚点 (ch213-236, 与 outline-vol10 意象密度硬约束12同步)
        if 213 <= n <= 236:
            f19_hits = []
            for ph, spec in VOL10_CAPS.items():
                if n in spec["unlimited"]:
                    continue
                cnt = body.count(ph)
                if cnt > spec["cap"]:
                    f19_hits.append((ph, cnt, spec["cap"]))
            if f19_hits:
                fail += 1
                v6_issue = True
                print("  [F19·卷十器物/词频锚点超限]")
                for ph, c, m in f19_hits:
                    print(f"    × {ph} ×{c} (本章上限 {m})——见 outline-vol10 意象密度硬约束12 (指代改写)")
        # F18 裸回声问句纪律 (ch189+, 与卷九对白语气审计同步): 独立成行的 ≤3字 引号问句
        if n >= F18_START:
            f18_hits = []
            for l in paras:
                l = l.strip()
                if len(l) >= 4 and l.startswith(LQ) and l.endswith(RQ) and l[-2] == QM:
                    body = l[1:-2]
                    if 2 <= len(body) <= 3 and body not in F18_GENERIC:
                        f18_hits.append(body)
            if len(f18_hits) > F18_CAP:
                fail += 1
                v6_issue = True
                print(f"  [F18·裸回声问句] ×{len(f18_hits)} (上限{F18_CAP}) {f18_hits}")
                print("    × 短回声问句(如「记法？」「样本？」)是审讯签名, 单章≤2; 其余改为完整问句(见审计: 活人→十万户的活人)")
        # F20 榜单引用核验 (全书; 数据源=rankings.md/chronology.md 运行时解析)
        f20_f, f20_notes, f20_used = f20_check(n, body)
        if f20_f:
            fail += 1
            print("  [F20·榜单引用核验]")
            for h in f20_f:
                print(f"    × {h}")
        if f20_notes:
            print("  [F20·榜单引用·报告]")
            for h in f20_notes:
                print(f"    • {h}")
        elif f20_used and not f20_f:
            print("  [F20·榜单引用核验] ✓")
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
        if not v6_issue and not (f_hits or d_hits or f4_hits or f6_hits or f7_hits or x_hits or i_hits or f16_hits or f20_f):
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
