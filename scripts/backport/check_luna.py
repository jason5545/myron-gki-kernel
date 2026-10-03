import json,glob,os,re,subprocess,sys
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan  # noqa: E402
L='/root/luna'
rows=[]
def tsv(path, grp):
    for line in open(path):
        if line.startswith('#') or not line.strip(): continue
        f=line.rstrip('\n').split('\t')
        rows.append(dict(file=grp,order=f[0],group=f[1],action=f[2],source=f[3],ref=f[4],commit=f[5],date=f[6],paths=f[8],project_patch=f[9]))
tsv(f'{L}/selected.tsv','selected')
for p in sorted(glob.glob(f'{L}/indep/*.tsv')): tsv(p, os.path.basename(p)[:-4])
stable=json.load(open(f'{scan.OUT}/stable.json')); bycommit={r['commit']:r for r in stable}
out=[]
for r in rows:
    c=r['commit']; res=dict(r)
    pp=None
    if r['source']=='stable':
        p=scan.run('git','format-patch','-1','--stdout',c,cwd=scan.STABLE,check=False)
        if p.returncode==0 and p.stdout:
            pp=f'/root/luna/p/{c[:12]}.patch'; open(pp,'w').write(p.stdout)
            res['subject']=re.search(r'^Subject: \[PATCH\] (.*)',p.stdout,re.M).group(1)
            res['version']=bycommit.get(c,{}).get('version')
            res['apply']=scan.apply_status(pp,c)
        else: res['apply']='找不到 commit'
    elif r['source']=='mainline':
        pp=f'/root/luna/mainline/{c}.patch'
        t=open(pp).read(); res['subject']=re.search(r'^Subject: \[PATCH\] (.*)',t,re.M).group(1)
        res['apply']=scan.apply_status(pp)
    elif r['source']=='aosp':
        p=scan.run('git','format-patch','-1','--stdout',c,cwd='/gki/hist',check=False)
        if p.returncode==0 and p.stdout:
            pp=f'/root/luna/p/{c[:12]}.patch'; open(pp,'w').write(p.stdout)
            res['subject']=re.search(r'^Subject: \[PATCH\] (.*)',p.stdout,re.M).group(1)
            res['apply']=scan.apply_status(pp)
        else: res['apply']='找不到 commit：'+p.stderr[:100]
    if pp:
        pf=scan.parse_patch(open(pp).read())
        res['kmi'],res['kmi_reasons']=scan.kmi_risk(pf)
        b={}
        for path,f in pf.items():
            funcs=set()
            for h in f['hunks']: funcs.update(scan.IDENT.findall(h['ctx']))
            b[path]=scan.builtin_status(path,funcs)
        res['builtin']=b
    if r['project_patch']!='-':
        ap=f"/root/luna/patches/{os.path.basename(r['project_patch'])}"
        res['adapted_apply']=scan.apply_status(ap) if os.path.exists(ap) else '缺檔'
    out.append(res)
json.dump(out,open(f'{scan.OUT}/luna.json','w'),ensure_ascii=False,indent=1)
for x in out:
    print(x['file'][:22].ljust(22),x['order'],x['source'][:4],x['commit'][:12],x.get('version') or '-',x.get('apply'),x.get('adapted_apply','-'),x.get('kmi'),{k:v for k,v in (x.get('builtin') or {}).items()},(x.get('subject') or '')[:60],sep=' | ')
