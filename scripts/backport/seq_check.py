import json, os, subprocess, sys  # 參數：分批清單 JSON
K='/gki/kmi6'
OUT=os.environ.get('KMI6_OUT', '/root/kmi6scan')
V8=subprocess.run(['git','-C',K,'log','--format=%H','-1','--grep=v8 patches'],capture_output=True,text=True).stdout.strip()
def patch_for(c, src):
    for p in (f'{OUT}/patches/{c}.patch', f'/root/luna/p/{c}.patch', f'{OUT}/ack-{c}.patch'):
        if os.path.exists(p): return p
    for f in os.listdir('/root/luna/mainline'):
        if f.startswith(c): return '/root/luna/mainline/'+f
seq=json.load(open(sys.argv[1] if len(sys.argv) > 1 else '/root/kmi6seq.json'))
allres={}
for batch in sorted(seq):
    subprocess.run(['git','-C',K,'checkout','-q','-f','--detach',V8]); subprocess.run(['git','-C',K,'clean','-qfdx'])
    ok=[];bad=[]
    for v,c,src in seq[batch]:
        p=patch_for(c,src)
        r=subprocess.run(['git','-C',K,'apply','--index',p],capture_output=True,text=True)
        if r.returncode!=0:
            r=subprocess.run(['git','-C',K,'apply','--index','--3way',p],capture_output=True,text=True)
            (ok if r.returncode==0 else bad).append((c,'3way' if r.returncode==0 else r.stderr.strip().splitlines()[-1][:120]))
            if r.returncode!=0: subprocess.run(['git','-C',K,'reset','-q','--hard','HEAD'])
        else: ok.append((c,'ok'))
        subprocess.run(['git','-C',K,'-c','user.name=c','-c','user.email=c@l','commit','-qm',c],capture_output=True)
    allres[batch]={'ok':ok,'bad':bad}
    print('batch',batch,'ok',len(ok),'3way',sum(1 for x in ok if x[1]=='3way'),'fail',len(bad),bad)
# 全部批次依序疊在一起
subprocess.run(['git','-C',K,'checkout','-q','-f','--detach',V8])
n=0;fails=[]
for batch in sorted(seq):
    for v,c,src in seq[batch]:
        p=patch_for(c,src)
        r=subprocess.run(['git','-C',K,'apply','--index','--3way',p],capture_output=True,text=True)
        if r.returncode==0:
            n+=1; subprocess.run(['git','-C',K,'-c','user.name=c','-c','user.email=c@l','commit','-qm',c],capture_output=True)
        else:
            fails.append(c); subprocess.run(['git','-C',K,'reset','-q','--hard','HEAD'])
print('all batches stacked: ok',n,'fail',fails)
subprocess.run(['git','-C',K,'checkout','-q','-f','--detach',V8])
json.dump(allres,open(f'{OUT}/seq-result.json','w'),indent=1)
