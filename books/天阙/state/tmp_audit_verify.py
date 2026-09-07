import sys, re
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

def wc(n):
    t = Path(f'novel/chapter-{n:02d}.md').read_text(encoding='utf-8')
    body = re.sub(r'^#.*$', '', t, flags=re.M)
    return len(body.replace('\n', '').replace('\r', '').replace(' ', '').replace('\t', ''))

print('== 单章字数 <4000 的章节 ==')
under = []
for n in range(1, 213):
    p = Path(f'novel/chapter-{n:02d}.md')
    if not p.exists():
        print(f'ch{n}: 缺失!')
        continue
    c = wc(n)
    if c < 4000:
        under.append((n, c))
for n, c in under:
    print(f'ch{n:03d}: {c}')
print(f'\n共 {len(under)} 章 <4000')

print('\n== 报告具体指控核查 ==')
checks = {
    'ch88 七年/五年': None, 'ch90 七年/五年': None, 'ch91 七年/五年': None,
    'ch122 十四年前': None, 'ch129 十四年前': None, 'ch98 榻上': None,
}
for n in [88, 90, 91]:
    t = Path(f'novel/chapter-{n:02d}.md').read_text(encoding='utf-8')
    hits = [l.strip()[:100] for l in t.splitlines() if ('七年' in l or '五年' in l or '三年' in l or '借名' in l or '辞差' in l or '征发' in l)]
    print(f'--- ch{n} 年限/借名相关 ---')
    for h in hits:
        print(' ', h)
for n in [122, 129]:
    t = Path(f'novel/chapter-{n:02d}.md').read_text(encoding='utf-8')
    hits = [l.strip()[:100] for l in t.splitlines() if '十四' in l or '十二年' in l or '收你爹' in l]
    print(f'--- ch{n} 十四年相关 ---')
    for h in hits:
        print(' ', h)
t = Path('novel/chapter-98.md').read_text(encoding='utf-8')
print('--- ch98 榻/死地 ---')
for l in t.splitlines():
    if '榻' in l or '饿死' in l or '码头' in l or '草' in l:
        print(' ', l.strip()[:100])