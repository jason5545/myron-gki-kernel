#!/usr/bin/env python3
"""把一批 backport 依序疊到 /gki/kmi6 的 bp 分支，每筆一個 commit。

參數：清單 JSON（[{commit, source, batch, note, subject, upstream, version}]）。
衝突需改寫的項目跳過，列出來由人工處理。commit 訊息帶 Source／Upstream／Note，
export_chain.py 會據此產生 patches/ 底下的檔頭。"""
import json, os, subprocess, sys

K = '/gki/kmi6'
OUT = os.environ.get('KMI6_OUT', '/root/kmi6scan')


def git(*a, check=True, **kw):
    r = subprocess.run(['git', '-C', K, *a], capture_output=True, text=True, **kw)
    if check and r.returncode:
        raise SystemExit(f'git {a}: {r.stderr}')
    return r


def patch_for(c):
    for p in (f'{OUT}/patches/{c}.patch', f'/root/luna/p/{c}.patch', f'{OUT}/ack-{c}.patch'):
        if os.path.exists(p):
            return p
    for f in os.listdir('/root/luna/mainline'):
        if f.startswith(c):
            return '/root/luna/mainline/' + f


def commit(e, how):
    msg = (f"{e['subject']}\n\nSource: {e['source']} {e['commit']}\n"
           f"Upstream: {e.get('upstream') or '-'}\nVersion: {e.get('version') or '-'}\n"
           f"Batch: {e['batch']}\nNote: {e['note']}\nApplied: {how}\n")
    git('-c', 'user.name=myron-gki', '-c', 'user.email=myron-gki@users.noreply.github.com', 'commit', '-q', '-F', '-', input=msg)


def main():
    entries = json.load(open(sys.argv[1]))
    done = set(git('log', '--format=%B', 'bp').stdout.split())
    manual = []
    for e in entries:
        if e['commit'] in done:
            continue
        if e.get('manual'):
            manual.append(e)
            continue
        p = patch_for(e['commit'])
        r = git('apply', '--index', p, check=False)
        how = 'clean'
        if r.returncode:
            r = git('apply', '--index', '--3way', p, check=False)
            how = '3way'
            if r.returncode:
                git('reset', '-q', '--hard', 'HEAD')
                manual.append(e)
                print('FAIL', e['commit'], r.stderr.strip().splitlines()[-1:])
                continue
        commit(e, how)
        print('ok  ', how.ljust(5), e['commit'], e['subject'][:70])
    print('需人工改寫：', ' '.join(e['commit'] for e in manual))


if __name__ == '__main__':
    main()
