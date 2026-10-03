import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan  # noqa: E402
ids="""aff1917ea a56cf2e25 a1ffef555 88680fe19 af1823716 da324a107 39bb8df5b a3d06921c
7ef00d345 459c818f8 a460b437a 79bb460d3 32d79853e e6f3cb873 aa134d3a4 8ff877aa6 12cbb992b
2df1e89cb 1ac5be05b 1c8fffa12 abdb3eb9a e7a034a56 ee25d80f0 397209d78 658b9fc00 3fb6436fa
6a379f037 030ed2af4 d75e1f837
e4b70b22d f222c1f72 84b5a9e56 eb95d43ef fc2f50b65 ea4956ef3 c5148581b 7ccce76f8 78ce33690 285c84322 67c51f025 d73a8ddf4 9719875a2 64d481b3e ec806d3e1 e6a38c6e0 74a46084d fe3859bd3 d762e881e 5161413c6 63352a68f afb757a93 44c66f24d 03dc06797 4205e8fd7 74d87b5fd 104059752 5f93a67a7 afaedae56 c5033f81e 91fe72852 ad5197b05 a1bbe89ff abcdfdd5e 46cffed3c 5f937a44f 85e0019c0 6ffe70953 0a08bd027 f0db034d6
b93d53f5d 1fc1975ac 7ee04de32 74bd9a178 503a5365f 21ed84930 1c91f3784 f0b4e777b dbfc1413a acaecb734 a9fce61d1 f118039cc""".split()
out=[]
for i in ids:
    p=scan.run('git','format-patch','-1','--stdout',i,cwd='/gki/hist',check=False)
    if p.returncode or not p.stdout:
        print(i,'FAIL',p.stderr[:120]); continue
    pp=f'{scan.OUT}/ack-{i}.patch'; open(pp,'w').write(p.stdout)
    subj=re.search(r'^Subject: \[PATCH\] (.*(?:\n [^\n]+)*)',p.stdout,re.M).group(1).replace('\n','')
    pick=re.findall(r'cherry picked from commit ([0-9a-f]{12,40})',p.stdout)
    st=scan.apply_status(pp)
    pf=scan.parse_patch(p.stdout); k,kr=scan.kmi_risk(pf)
    b={path:scan.builtin_status(path,set(sum([scan.IDENT.findall(h['ctx']) for h in f['hunks']],[]))) for path,f in pf.items()}
    date=re.search(r'^Date: (.*)',p.stdout,re.M).group(1)
    out.append(dict(commit=i,subject=subj,apply=st,kmi=k,kmi_reasons=kr,builtin=b,upstream=pick,date=date))
    print(i,st,k,{k2:v for k2,v in b.items() if v!='y'} or '',subj[:95])
json.dump(out,open(f'{scan.OUT}/ack.json','w'),ensure_ascii=False,indent=1)
