import sys, re
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

# 金句家族词表（F16 家族 + 审计报告点名句式 + 常见变体）
PHRASES = [
    # F16 家族
    "账是死的", "账是活的", "路是死的", "人是活的",
    "名在纸上", "账在纸上", "账在，人在", "账在，人就在", "人在，账在",
    "名字是死人的", "名字是死的",
    "算得清", "算不清",
    "账比人走得快", "账比命长", "账比人长",
    "我只算账", "只算账，不算命", "算账的不算命",
    # 审计报告点名
    "死人不会说话", "纸会说话", "账会说话",
    "规矩多少钱一斤",
    "咸的比亮的值钱", "咸的比",
    # 常见哲学变体
    "账不会改", "人会死", "账能走",
    "我算得清", "他算不清",
    "账是活的", "命是账", "账是命",
    "记人的账", "账记人", "人记账",
]

CH = Path("novel")
report = []
for i in range(1, 213):
    p = CH / f"chapter-{i:03d}.md"
    if not p.exists():
        continue
    lines = p.read_text(encoding='utf-8').splitlines()
    for ln, line in enumerate(lines, 1):
        for ph in PHRASES:
            if ph in line:
                # 说话人：向前找最近的“X说”或引号归属
                ctx_prev = "".join(lines[max(0, ln-4):ln-1])[-80:] if ln > 1 else ""
                speaker = ""
                m = re.search(r'([\u4e00-\u9fff]{1,6})说[：:，,]?$', ctx_prev)
                if m:
                    speaker = m.group(1)
                report.append((i, ln, ph, speaker, line.strip()[:100]))

out = []
for i, ln, ph, sp, txt in report:
    out.append(f"ch{i:03d} L{ln:4d} | {ph} | 说话人≈{sp} | {txt}")
Path("state/tmp_golden_report.txt").write_text("\n".join(out), encoding='utf-8')
print(f"总命中 {len(report)} 处, 写入 state/tmp_golden_report.txt")

# 按章节统计
from collections import Counter
per_ch = Counter(r[0] for r in report)
for ch, c in sorted(per_ch.items()):
    print(f"ch{ch:03d}: {c}")