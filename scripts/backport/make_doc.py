#!/usr/bin/env python3
"""從 gen.py 的結果產生 docs/kmi6-backport-candidates.md 的表格部分。"""
import json, sys

d = json.load(open(sys.argv[1]))
rows = d['rows']
head_path, out_path = sys.argv[2], sys.argv[3]
BATCH = {1: '批次 1：UFS／SCSI／block', 2: '批次 2：f2fs／erofs／fuse／binder', 3: '批次 3：mm／排程／核心',
         4: '批次 4：網路／netfilter', 5: '批次 5：USB／HID', 6: '批次 6：netlink rmem（追加）'}


def esc(s):
    return s.replace('|', '\\|')


def status(r):
    return r['status'].replace('衝突需改寫（LunaKernel 改寫版：', '衝突需改寫（LunaKernel 版：')


out = [open(head_path).read().rstrip('\n'), '']
out.append(f"## 建議清單（{sum(1 for r in rows if r['decision'] == '建議')} 筆）")
out.append('')
out.append('「狀態」是對 v8 的樹（ACK `1ad7be92` 加上 0001～0008）實際試套用的結果。「來源」寫 LunaKernel 的，表示 LunaKernel r21 也採用了。')
for b in range(1, 7):
    sel = [r for r in rows if r['decision'] == '建議' and r['batch'] == b]
    sel.sort(key=lambda r: (r['subsystem'], r['status'] != '可套用', r['commit']))
    out += ['', f'### {BATCH[b]}（{len(sel)} 筆）', '',
            '| commit | 子系統 | 類型 | 狀態 | KMI 風險 | 建議理由 | 標題 |', '| --- | --- | --- | --- | --- | --- | --- |']
    for r in sel:
        src = '（LunaKernel）' if 'LunaKernel' in r['source'] else ('（ACK）' if r['source'].startswith('ACK') else '')
        out.append(f"| `{r['commit']}`{src} | {r['subsystem']} | {r['kind']} | {status(r)} | {r['kmi']} | {esc(r['note'])} | {esc(r['subject'][:90])} |")

luna = [r for r in rows if 'LunaKernel' in r['source']]
out += ['', f'## LunaKernel r21 清單逐項結果（{len(luna)} 筆）', '',
        '來源是 LunaKernel 主分支的 `patches/backports/r21-selected-backports.tsv` 與 `r21-independent/*.tsv`（2026/10/2 讀取）。同一個修正若同時出現在 stable 掃描，只算一次。', '',
        '| commit | 來源 | 子系統 | 狀態 | KMI 風險 | 建議 | 說明 |', '| --- | --- | --- | --- | --- | --- | --- |']
order = {'建議': 0, '可選': 1, '不建議': 2, '不適用': 3, '基底已有': 4, '重複': 5}
for r in sorted(luna, key=lambda r: (order[r['decision']], r['subsystem'], r['commit'])):
    out.append(f"| `{r['commit']}` | {r['source'].split('、')[0].replace('LunaKernel／', '')} | {r['subsystem']} | {status(r)} | {r['kmi']} | {r['decision']} | {esc(r['note'])} |")

kmi = [r for r in rows if r['decision'] == '不建議' and 'KMI' in r['note']]
out += ['', f'## 因 KMI 排除（{len(kmi)} 筆）', '',
        '這些修正本身有價值，但會改到 STG 裡的 KMI 型別。除非能改寫成不動結構（例如像 e6f3cb873 改用私有結構），否則不採用。', '',
        '| commit | 子系統 | 改到的型別 | 標題 |', '| --- | --- | --- | --- |']
for r in sorted(kmi, key=lambda r: (r['subsystem'], r['commit'])):
    types = r['note']
    for prefix in ('改到 KMI 型別：', '改到 KMI 型別 '):
        if types.startswith(prefix):
            types = types[len(prefix):]
    out.append(f"| `{r['commit']}` | {r['subsystem']} | {esc(types[:110])} | {esc(r['subject'][:80])} |")
open(out_path, 'w').write('\n'.join(out) + '\n')
print('written', out_path)
