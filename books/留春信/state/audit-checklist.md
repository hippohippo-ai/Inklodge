# 《留春信》审计清单（audit-checklist.md）

> 把历轮散落在 `state/revisions.md`「仍未修」里的审计条目收敛成一张**可勾选清单**，
> 每条给出**可机械检查的判据**，由 `state/continuity-scan.py` 的 **F 段**读取并执行
> （`npm run continuity -- --book 留春信`，或 `npm run continuity -- --family f`）。
>
> - `- [x]`＝已闭环：F 段对其判据做**硬校验**，失守报 ⚠（回归即被拦）。
> - `- [ ]`＝待裁／待办：F 段只登记与探测（○），**不判失败**。
> - 判据写法：规则写在反引号内，多条用全角「｜」隔开；语法与 E 段同源——
>   must / forbid / must_all（文本用 + 连接）/ book_must / book_forbid /
>   state_must / state_forbid / state_count（末尾 :N）/ charlen_max / charlen_min。
> - 改本文件后**无需改探针代码**，重跑 F 段即可复核。

## 一、待裁／待办（F 段记为 ○）

（A1 已于 2026-09-26 裁定并落地：把「水师封锁湖口」与「官府封庄」两分，见下方 **B14**。）
（A2 已于 2026-09-26 裁定并落地：旧戏楼方位统一为「庄子外二里（庄外东南）」，见下方 **B15**。）

- [ ] A3｜第39章超长（疑两版场景拼接）
  - 现象：ch39 正文有效字符 **9211**，为全书均值（4982）的 1.85 倍、全书唯一超 7000 的章；由两段本可独立的场景合成——前半「渡口封水对峙（顾青禾现身、老张反旗）」，后半「水棺开验（甘遂、总闸铜齿）」，各约一章体量；C1／C2 章内重复探针 0 命中，故属**结构拼接**而非逐字复述。
  - 待裁：①瘦身（合并渡口对峙的重复回合）至 ≤7000；或 ②拆为两章并重编号（牵动全卷章号与 F23／F33 台账，成本高）；或 ③保留为高潮特例，并在 `state/requirements.md` 显式豁免。
  - 判据：`charlen_max:ch39:7000`（拟判据；落地前 F 段会显示「判据未达」＝尚未处理）
  - 落点：`novel/chapter-39.md`、`state/chapter-log.md`、`state/chapters.md`

## 二、已闭环（F 段硬校验；判据同时由 E 段覆盖）

- [x] B01｜ch2 开篇日期＝七月九日 · 判据：`must:ch02:七月九日`｜`forbid:ch02:七月十四`
- [x] B02｜换页案卷死亡时辰（巳时初刻／卯时三刻）· 判据：`must_all:ch02:巳时初刻+卯时三刻`
- [x] B03｜ch39 时辰差＝将近两个时辰 · 判据：`must:ch39:晚将近两个时辰`｜`forbid:ch39:晚一个时辰`｜`forbid:ch23:提前了一个时辰`
- [x] B04｜ch39 死亡夜／验尸日厘清 · 判据：`must:ch39:四月初八夜里咽的药`｜`book_must:四月初九`
- [x] B05｜ch9 红结＝还剩五个 · 判据：`must:ch09:还剩五个红结`｜`book_forbid:六个红结`
- [x] B06｜阿七入庄年龄＝十二岁（12＋10＝22）· 判据：`must:ch43:十二岁进沈家`｜`forbid:ch43:十三岁`｜`forbid:preface:十三岁`｜`state_must:characters.md:22岁`
- [x] B07｜顾青禾年限＝十几年前 · 判据：`must:ch39:十几年前`｜`forbid:ch39:二十年前`
- [x] B08｜timeline §三 第6日不提前落名「陆七」· 判据：`state_forbid:timeline.md:公开“陆七”`｜`forbid:ch26:陆七`｜`forbid:ch27:陆七`
- [x] B09｜timeline §四「第9日」只一行 · 判据：`state_count:timeline.md:| 第9日 |:1`
- [x] B10｜timeline §一 封存口径＝近百日 · 判据：`state_must:timeline.md:近百日`｜`book_forbid:封存满百日`
- [x] B11｜戏楼正名「旧戏楼」（清除「废戏楼」别名）· 判据：`book_must:旧戏楼`｜`book_forbid:废戏楼`｜`state_forbid:theme.md:废戏楼`
- [x] B12｜ch42 去元叙述引章 · 判据：`forbid:ch42:第31章`｜`must:ch42:在那一夜已经说完了`
- [x] B13｜篇幅口径＝实测均值约 4982 · 判据：`state_must:requirements.md:实测均值约`｜`state_forbid:requirements.md:4000–4500`
- [x] B14｜「水师封锁湖口」与「官府封庄」两分（相差四日）· 判据：`must:ch43:水师锁湖已十日，官府封庄已六日`｜`must:ch32:自第六日风雪桥起`｜`state_must:timeline.md:水师封锁湖口进入第三天`｜`state_must:timeline.md:第10日官府正式封庄`｜`state_must:timeline.md:水师封锁湖口自第6日起`｜`state_forbid:timeline.md:水师封庄`｜`state_must:chapter-log.md:正式封庄在第10日`｜`state_must:plot-check.md:10（官府封庄）`
- [x] B15｜旧戏楼方位＝庄子外二里（庄外东南）· 判据：`must:ch32:旧戏楼在庄子外二里`｜`must:ch10:旧戏楼在庄子外二里`｜`forbid:ch10:庄子最北面`｜`book_forbid:庄子最北面`｜`must:ch21:东南的旧戏楼`

## 三、口径与维护约定

- 本文件是**剩余审计项的单一事实源**；`state/revisions.md` 里带日期的「仍未修」清单属历史快照，不再回写。
- 闭环一项时：勾选 `- [x]`，把判据收紧为**定案口径**（而非现状探测器），重跑 F 段确认 ✓ 全绿。
- 新增审计项时：在「一、待裁」追加 `- [ ] A#`，写明现象／待裁／判据／落点；F 段自动接管。
- F 段纪律与全探针一致：只报告、不改稿；判定权在人。
