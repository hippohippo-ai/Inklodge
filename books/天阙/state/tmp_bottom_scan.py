import sys, re
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

# 底层小人物的说话人词根（车夫/老妇/守门/匪盗/小贩/脚夫/流民等）
BOTTOM = re.compile(
    r'(老妇|老婆子|婆子|老妪|老太婆|老丈|老汉|老头|老人|老儿|老大娘|大娘|婶子|'
    r'妇人|女子|姑娘|丫头|孩子|小儿|小童|孩童|少年|小子|'
    r'车夫|赶车的|船夫|艄公|渡夫|挑夫|脚夫|纤夫|苦力|'
    r'守门|门卒|门军|门吏|城门官|军士|士卒|小卒|兵丁|乱兵|溃兵|'
    r'匪|盗|贼|劫道的|响马|山贼|马贼|'
    r'小贩|货郎|摊主|摊贩|卖水的|卖姜的|卖饼的|卖粥的|卖柴的|卖炭的|'
    r'店家|掌柜|店伙|伙计|跑堂|厨子|屠户|屠夫|匠人|木匠|铁匠|补伞|'
    r'乞丐|叫花子|流民|难民|乡民|村民|农人|佃户|渔夫|猎人|采药|'
    r'尼姑|和尚|僧人|老僧|道士|道姑|盲人|瞎子|瘸子|驼子|哑巴|疯子|傻|'
    r'守门人|差役|皂隶|狱卒|更夫|打更|'
    r'妇人|民妇|村妇|贫妇)'
)

APHOR = re.compile(r'(比\S+值钱|比\S+长|比\S+久|是死的|是活的|活人|死人|'
                   r'不会说话|会说话|算得清|算不清|认得\S+不认|认\S+不认|'
                   r'值钱|金贵|贱|命|天理|世道|乱世|年头|人心|良心|'
                   r'才活得|才走得|才过得|躲不过|逃不过|躲得|'
                   r'吃人|怕人|欺软|敬酒|规矩|道理|'
                   r'活着|死着|往\S+走|往\S+去)')

out = []
for i in range(1, 213):
    p = Path("novel") / f"chapter-{i:03d}.md"
    if not p.exists():
        continue
    lines = p.read_text(encoding='utf-8').splitlines()
    for ln, line in enumerate(lines, 1):
        # 说话人判定：本行内 "…说" 或 上一行尾部
        s = line
        speaker = ""
        m = re.search(r'^(.{0,30}?)[说]道?[：，:]', s)
        if m:
            cand = m.group(1).strip('“”"\' ')
            # 去掉引号内残留
            cand = cand.split('”')[-1].split('"')[-1]
            speaker = cand
        else:
            prev = lines[ln-2] if ln >= 2 else ""
            m2 = re.search(r'([\u4e00-\u9fff]{1,8})说[：，:]?$', prev)
            if m2:
                speaker = m2.group(1)
        if not speaker or not BOTTOM.search(speaker):
            continue
        # 提取引号内对白
        quoted = re.findall(r'[“"]([^”"]{12,})[”"]', line)
        if not quoted:
            continue
        for q in quoted:
            if q.count('。') >= 2 and APHOR.search(q):
                out.append((i, ln, speaker, q))
        # 裸对白（无引号但整行是台词，如直引号章节）
        if '"' in line or '“' in line:
            continue
        body = line.strip()
        if body.count('。') >= 2 and APHOR.search(body) and '说' in body:
            out.append((i, ln, speaker + '?', body[:120]))

print(f"候选 {len(out)} 处")
seen = set()
for i, ln, sp, q in out:
    key = (i, q[:20])
    if key in seen:
        continue
    seen.add(key)
    print(f"ch{i:03d} L{ln:4d} [{sp}] {q[:110]}")