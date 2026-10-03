#!/usr/bin/env python3
"""把 /gki/kmi6 的 bp 分支（v8 基底之後）匯出成 patches/ 格式的檔案。

參數：輸出目錄、起始編號。每個 commit 一個檔案，檔頭寫來源、upstream、說明；
內容是相對前一個 commit 的 diff，所以照編號順序一定能套上。"""
import os, re, subprocess, sys

K = '/gki/kmi6'
out_dir, start = sys.argv[1], int(sys.argv[2])
os.makedirs(out_dir, exist_ok=True)
base = subprocess.run(['git', '-C', K, 'log', '--all', '--format=%H', '-1', '--grep=v8 patches'],
                      capture_output=True, text=True).stdout.strip()
commits = subprocess.run(['git', '-C', K, 'rev-list', '--reverse', f'{base}..bp'],
                         capture_output=True, text=True).stdout.split()
SRC = {'stable': 'linux-6.12.y stable', 'LunaKernel／stable': 'linux-6.12.y stable（LunaKernel r21 也採用）',
       'LunaKernel／mainline': 'mainline（LunaKernel r21 採用）', 'LunaKernel／ACK': 'ACK android16-6.12（LunaKernel r21 也採用）',
       'ACK android16-6.12': 'ACK android16-6.12'}
OUT = os.environ.get('KMI6_OUT', '/root/kmi6scan')
UPSTREAM, VERSION = {}, {}
if os.path.exists(f'{OUT}/stable.json'):
    import json
    for r in json.load(open(f'{OUT}/stable.json')):
        UPSTREAM[r['commit'][:12]] = (r.get('upstream') or '')[:12]
        VERSION[r['commit'][:12]] = r.get('version') or ''
for i, c in enumerate(commits):
    body = subprocess.run(['git', '-C', K, 'log', '-1', '--format=%B', c], capture_output=True, text=True).stdout
    subject = body.split('\n', 1)[0]
    meta = dict(re.findall(r'^(Source|Upstream|Version|Batch|Note|Applied|Rewrite): (.*)$', body, re.M))
    src, _, sha = meta['Source'].rpartition(' ')
    src = SRC.get(src.split('、')[0], src)
    if meta.get('Upstream', '-') in ('-', '') and UPSTREAM.get(sha):
        meta['Upstream'] = UPSTREAM[sha]
    if meta.get('Version', '-') in ('-', '') and VERSION.get(sha):
        meta['Version'] = VERSION[sha]
    extra = []
    if meta.get('Upstream', '-') != '-':
        extra.append(f"upstream {meta['Upstream']}")
    if meta.get('Version', '-') not in ('-', ''):
        extra.append(meta['Version'])
    lines = [f"# 來源：{src} {sha}" + (f"（{'，'.join(extra)}）" if extra else ''), f'# {subject}', f"# {meta['Note']}"]
    if meta.get('Rewrite'):
        lines.append(f"# 改寫：{meta['Rewrite']}")
    elif meta.get('Applied') == '3way':
        lines.append('# 以 3-way 合併套到 v8，內容與原 commit 相同，只有上下文不同')
    diff = subprocess.run(['git', '-C', K, 'diff', '--no-color', f'{c}^', c], capture_output=True, text=True).stdout
    slug = re.sub(r'[^a-z0-9]+', '-', re.sub(r'^((UPSTREAM|BACKPORT|FROMGIT|FROMLIST|ANDROID): )+', '', subject).lower()).strip('-')
    slug = '-'.join(slug.split('-')[:8])[:60].rstrip('-')
    name = f'{start + i:04d}-{slug}.patch'
    with open(os.path.join(out_dir, name), 'w') as f:
        f.write('\n'.join(lines) + '\n' + diff)
    print(name)
