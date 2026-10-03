"""用 gki/aarch64/abi.stg 重新判斷 KMI 風險。"""
import collections, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan  # noqa: E402
STRUCTS=set(); ENUMS=set(); SYMS=set()
cur=None
for line in open('/gki/kmi6/gki/aarch64/abi.stg'):
    if not line.startswith(' '):
        cur=line.split(' ')[0]
        continue
    m=re.match(r'  name: "([^"]+)"',line)
    if m:
        if cur=='struct_union': STRUCTS.add(m.group(1))
        elif cur=='enumeration': ENUMS.add(m.group(1))
        elif cur=='elf_symbol': SYMS.add(m.group(1))
DECL=re.compile(r'^(?:extern\s+)?(?:[\w\*]+\s+)+\**([A-Za-z_]\w*)\s*\(')
def kmi_risk2(files):
    level='低'; reasons=[]
    def bump(l,r):
        nonlocal level
        order={'低':0,'中':1,'高':2}
        if order[l]>order[level]: level=l
        reasons.append(r)
    for path,f in files.items():
        if not (f['plus'] or f['minus']): continue
        for h in f['hunks']:
            lines=[l for l in h['plus']+h['minus'] if l.strip() and not l.strip().startswith(('//','/*','*','*/'))]
            if not lines: continue
            ctx=h['ctx']
            m=re.match(r'\s*(?:typedef\s+)?(struct|union|enum)\s+(\w+)\s*\{',ctx)
            if m and any(re.search(r'[;,]\s*(/\*.*)?$',l) or re.match(r'^\s*\w+\s*(=.*)?$',l) for l in lines):
                kind,name=m.group(1),m.group(2)
                kmi = name in (ENUMS if kind=='enum' else STRUCTS)
                if path.endswith('.h') or kmi:
                    bump('高' if kmi else '低', f'{path}: {kind} {name}' + ('（KMI 型別）' if kmi else '（非 KMI）'))
                continue
            # 函式簽名：只有被移除或修改的宣告才算；新增宣告不影響既有 CRC
            removed={DECL.match(l).group(1) for l in h['minus'] if not l.startswith((' ','\t')) and DECL.match(l)}
            added={DECL.match(l).group(1) for l in h['plus'] if not l.startswith((' ','\t')) and DECL.match(l)}
            for name in removed:
                if name in SYMS: bump('高', f'{path}: KMI 符號 {name} 的宣告／簽名')
                elif path.endswith('.h') and not name.startswith('__'): bump('中', f'{path}: 宣告 {name} 有改')
            if path.endswith('.h') and not removed:
                if added: reasons.append(f'{path}: 新增宣告 {",".join(sorted(added))[:60]}')
                elif any(l.lstrip().startswith('#define') for l in lines): reasons.append(f'{path}: 巨集')
                else: reasons.append(f'{path}: inline／header 內容')
    return level, sorted(set(reasons))
if __name__=='__main__':
    print(len(STRUCTS),len(ENUMS),len(SYMS))
    for fn in ['stable.json','cands.json','luna.json','ack.json']:
        rows=json.load(open(f'{scan.OUT}/{fn}'))
        for r in rows:
            pp=None
            c=r['commit'][:12]
            for cand in (f'{scan.OUT}/patches/{c}.patch', f'/root/luna/p/{c}.patch', f'/root/luna/mainline/{r["commit"]}.patch', f'{scan.OUT}/ack-{r["commit"]}.patch'):
                if os.path.exists(cand): pp=cand; break
            if not pp: continue
            r['kmi'],r['kmi_reasons']=kmi_risk2(scan.parse_patch(open(pp).read()))
        json.dump(rows,open(f'{scan.OUT}/{fn}','w'),ensure_ascii=False,indent=1)
        print(fn, collections.Counter(r.get('kmi') for r in rows))
    for r in json.load(open(f'{scan.OUT}/luna.json')):
        if r.get('kmi')!='低': print(r['commit'][:12], r.get('kmi'), r.get('kmi_reasons'))
