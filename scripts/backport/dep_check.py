#!/usr/bin/env python3
"""列出 Stable-dep-of 指向已採用修正的 stable 前置 commit。

第 0 步的連續套用只檢查文字能不能套上，抓不到編譯依賴；backport 前先跑這支，
逐一判斷前置 commit 是否需要（v12 第一次編譯就是缺了 rculist 的前置 commit）。
讀 /gki/kmi6 bp 分支的 commit 訊息與 KMI6_OUT/stable.json，在 LXC 112 執行。"""
import json, os, re, subprocess

OUT = os.environ.get('KMI6_OUT', '/root/kmi6scan')
V8 = subprocess.run(['git', '-C', '/gki/kmi6', 'log', '--all', '--format=%H', '-1', '--grep=v8 patches'],
                    capture_output=True, text=True).stdout.strip()
rows = json.load(open(f'{OUT}/stable.json'))
# 已採用的 stable commit：bp 分支 commit 訊息裡的 Source
log = subprocess.run(['git','-C','/gki/kmi6','log','--format=%B',f'{V8}..bp'],capture_output=True,text=True).stdout
applied = set(re.findall(r'^Source: \S+ ([0-9a-f]{12})$', log, re.M))
by = {r['commit'][:12]: r for r in rows}
up_applied = {}
for c in applied:
    r = by.get(c)
    if r and r.get('upstream'): up_applied[r['upstream'][:12]] = c
# 前置 commit 的 Stable-dep-of 指向已採用 commit 的 upstream
body = subprocess.run(['git','-C','/gki/stable','log','--no-merges','--format=%x1e%H%x1f%s%x1f%b','v6.12.111'],capture_output=True,text=True).stdout
for chunk in body.split('\x1e')[1:]:
    h, s, b = chunk.split('\x1f', 2)
    for dep in re.findall(r'^Stable-dep-of: ([0-9a-f]{8,40})', b, re.M):
        tgt = up_applied.get(dep[:12])
        if tgt:
            r = by.get(h[:12], {})
            print(h[:12], '->', tgt, '|', r.get('apply_v8', '範圍外'), '|', s[:80])
