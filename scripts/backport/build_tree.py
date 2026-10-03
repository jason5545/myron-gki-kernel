#!/usr/bin/env python3
"""在 /gki/kmi6 建出目前的樹（ACK 基底加 /src/patches/series），印出 commit 給 scan.py 的 KMI6_BASE 用。
只動 /gki/kmi6 的 detached HEAD，bp 分支不變。"""
import subprocess

K = '/gki/kmi6'
BASE = '1ad7be92b3ed2e7d9c39f9b6d96bb91f1220c76d'


def git(*a):
    return subprocess.run(['git', *a], cwd=K, check=True, capture_output=True, text=True).stdout.strip()


git('checkout', '-q', '-f', '--detach', BASE)
git('clean', '-qfdx')
names = [l.strip() for l in open('/src/patches/series') if l.strip() and not l.startswith('#')]
for name in names:
    git('apply', '--index', '/src/patches/' + name)
git('-c', 'user.name=check', '-c', 'user.email=check@local', 'commit', '-q', '-m', f'{len(names)} patches')
print(git('rev-parse', 'HEAD'))
