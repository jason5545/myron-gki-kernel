"""在 /gki/kmi6 建 v8 基底（1ad7be92 + patches/series），對所有候選重跑套用檢查。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan  # noqa: E402
K='/gki/kmi6'
def git(*a, check=True): return scan.run('git',*a,cwd=K,check=check)
git('checkout','-q','-f','--detach',scan.BASE); git('clean','-qfdx')
for name in [l.strip() for l in open('/src/patches/series') if l.strip() and not l.startswith('#')]:
    git('apply','--index','/src/patches/'+name)
git('-c','user.name=check','-c','user.email=check@local','commit','-q','-m','v8 patches')
V8=git('rev-parse','HEAD').stdout.strip()
print('v8 base', V8)
scan.BASE=V8
def find_patch(r):
    c=r['commit']
    for p in (f'{scan.OUT}/patches/{c[:12]}.patch', f'/root/luna/p/{c[:12]}.patch', f'/root/luna/mainline/{c}.patch', f'{scan.OUT}/ack-{c}.patch'):
        if os.path.exists(p): return p
for fn in ('stable.json','luna.json','ack.json'):
    rows=json.load(open(f'{scan.OUT}/{fn}'))
    for r in rows:
        p=find_patch(r)
        if not p: continue
        stable_commit = r['commit'] if (fn=='stable.json' or r.get('source')=='stable') else None
        r['apply_v8']=scan.apply_status(p, stable_commit)
        if r.get('project_patch','-') not in ('-',None):
            ap='/root/luna/patches/'+os.path.basename(r['project_patch'])
            if os.path.exists(ap): r['adapted_apply_v8']=scan.apply_status(ap)
    json.dump(rows,open(f'{scan.OUT}/{fn}','w'),ensure_ascii=False,indent=1)
    import collections
    print(fn, collections.Counter((r.get('apply'),r.get('apply_v8')) for r in rows if r.get('apply')!=r.get('apply_v8')))
