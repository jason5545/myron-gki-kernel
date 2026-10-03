#!/usr/bin/env python3
"""合併掃描結果與人工判斷，輸出候選清單（TSV）與統計（JSON）。"""
import collections, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from decisions import D  # noqa: E402

DATA = os.environ.get('KMI6_DATA', f'{HERE}/data')
data = {n: json.load(open(f'{DATA}/{n}.json')) for n in ('stable', 'cands', 'luna', 'ack')}
OUT_TSV = sys.argv[1]
OUT_JSON = sys.argv[2]

DUP = {  # ACK commit → 已列入的同一個修正
    'abdb3eb9a': 'c301ec61ce6f', '1ac5be05b': 'e63032dc7150', 'f222c1f72': '56038756aae6',
    'ec806d3e1': '25d2dc669f2a', '64d481b3e': '58a5deb220bc', 'a3d06921c': 'a3d06921ce75',
    '7ee04de32': '7ee04de323f7', 'abcdfdd5e': '2dda0930fb79', '2d9c4a4ed': '7be222de96c0',
}
UNUSED_NET = re.compile(r'^net/(sched/(?!cls_bpf|act_bpf|sch_ingress|cls_api|sch_api|sch_generic|act_api)|bridge/|key/|l2tp/|8021q/|mpls/|tipc/|sctp/|rds/)|^net/ipv4/(ip_tunnel|ipip|ip_gre|ip_vti|udp_tunnel|fou|gre)|^net/ipv6/(ip6_tunnel|ip6_gre|ip6_vti|sit|seg6|rpl|ioam|ila|mip6)|^net/core/(page_pool|devmem|netdev-genl|xdp)|^net/ipv4/nexthop|^net/xdp/')
DEBUG = re.compile(r'kasan|kmsan|kcsan|lockdep|false alarm|codetag|ptdump|debugobjects|kernel-doc|comment', re.I)


def status(r):
    s = r.get('apply_v8') or r.get('apply') or '?'
    return {'3-way 可合併': '可套用（3-way）'}.get(s, s)


def kind(r):
    t = r.get('subject', '')
    if r.get('perf') or r.get('_perf') or re.search(r'\b(optimi[sz]e|speed up|avoid unnecessary|redundant plug|pointless|skip .* lookup|skip irqtime|mitigate overhead|flush_bypasses_map)', t, re.I):
        return '效能'
    return '修正'


def default_decision(r):
    files = [f for f in r.get('files', []) if f.endswith('.c')]
    subj = r['subject']
    sev = set(r.get('severity', []))
    if r.get('kmi') == '高':
        return '不建議', '改到 KMI 型別：' + '；'.join(x for x in r.get('kmi_reasons', []) if 'KMI 型別' in x)[:120]
    if DEBUG.search(subj):
        return '不適用', '除錯或標註用途，正式核心不會走到'
    if re.search(r'annotate|data-race', subj, re.I) and not (sev - {'race', '工具回報'}):
        return '不建議', '只是 KCSAN 標註'
    if files and all(UNUSED_NET.search(f) for f in files):
        return '不適用', '實機沒用到（qdisc 只有 pfifo_fast／mq／clsact，沒有 bridge、pfkey、tunnel、nexthop、XDP）'
    if any(s in r.get('subsystems', []) for s in ('ext4',)):
        return '可選', 'ext4 只用在唯讀的 apex loop 映像'
    if any(s in r.get('subsystems', []) for s in ('exfat', 'fat')):
        return '可選', '外接儲存才會用到'
    if 'bpf' in r.get('subsystems', []):
        return '可選', '只有特權程序能載入 BPF'
    if re.search(r'sockmap|skmsg|sk_psock|tcp_bpf|udp_bpf', subj + ' '.join(files), re.I):
        return '可選', 'sockmap 實機未使用'
    if re.search(r'gadget: (f_uvc|uvc|f_midi|f_hid|f_acm|f_ecm|f_mass_storage|f_printer|u_audio|f_uac)', subj):
        return '可選', '這個 USB gadget function 平常不會啟用'
    if re.search(r'tcpm', subj):
        return '不適用', '高通用 ucsi_glink，不走 tcpm'
    return '可選', '自動篩出，未逐項審'


def subsystem_of(r):
    if r.get('subsystems'):
        return ','.join(r['subsystems'])
    paths = r.get('paths') or ','.join(r.get('builtin', {}).keys())
    for key, name in (('f2fs', 'f2fs'), ('erofs', 'erofs'), ('ufs', 'ufs'), ('scsi', 'scsi'), ('block', 'block'),
                      ('fuse', 'fuse'), ('fs/crypto', 'fscrypt'), ('android', 'binder'), ('xhci', 'xhci'),
                      ('usb/core', 'usb-core'), ('gadget', 'usb-gadget'), ('mm/', 'mm'), ('sched', 'sched'),
                      ('netfilter', 'netfilter'), ('net/', 'net'), ('dm-', 'dm'), ('dma-buf', 'dma-buf'),
                      ('hid', 'hid'), ('time', 'time'), ('futex', 'futex'), ('crypto', 'crypto'), ('bpf', 'bpf')):
        if key in paths:
            return name
    return '?'


rows = {}


def add(r, source):
    c = r['commit']
    key = c[:12]
    if key in rows:
        rows[key]['source'] += '、' + source
        return
    dec = D.get(c[:12]) or D.get(c[:9])
    if c[:9] in DUP and DUP[c[:9]] != c[:12]:
        dec = ('重複', 0, f'同一個修正已列為 {DUP[c[:9]]}')
    if dec:
        level, batch, note = dec
    else:
        (level, note), batch = default_decision(r), 0
    if level in ('建議', '可選') and status(r) == '基底已有':
        level, note = '基底已有', note
    up = r.get('upstream')
    if isinstance(up, list):
        up = up[0] if up else None
    rows[key] = {
        'commit': c[:12], 'source': source, 'version': r.get('version') or '', 'upstream': (up or '')[:12],
        'subsystem': subsystem_of(r), 'kind': kind(r), 'status': status(r), 'kmi': r.get('kmi', '?'),
        'decision': level, 'batch': batch, 'note': note, 'subject': r.get('subject', ''),
        'kmi_reasons': '；'.join(r.get('kmi_reasons', [])),
    }


for r in data['luna']:
    src = {'stable': 'LunaKernel／stable', 'mainline': 'LunaKernel／mainline', 'aosp': 'LunaKernel／ACK'}[r['source']]
    r.setdefault('subject', '')
    add(r, src)
    if r.get('adapted_apply_v8'):
        rows[r['commit'][:12]]['status'] += f"（LunaKernel 改寫版：{r['adapted_apply_v8'].replace('3-way 可合併', '可套用（3-way）')}）"
for r in data['cands']:
    add(r, 'stable')
for r in data['ack']:
    r['subject'] = r['subject'].replace('  ', ' ')
    add(r, 'ACK android16-6.12')

# 人工判斷涵蓋到、但自動篩選沒選進 cands 的 stable commit（例如沒有嚴重性關鍵字）
stable_by = {r['commit'][:12]: r for r in data['stable']}
for k in D:
    if len(k) == 12 and k not in rows and k in stable_by:
        add(stable_by[k], 'stable')

cols = ['decision', 'batch', 'commit', 'source', 'version', 'subsystem', 'kind', 'status', 'kmi', 'note', 'subject', 'upstream', 'kmi_reasons']
order = {'建議': 0, '可選': 1, '不建議': 2, '不適用': 3, '基底已有': 4, '重複': 5}
with open(OUT_TSV, 'w') as f:
    f.write('\t'.join(['建議', '批次', 'commit', '來源', 'stable 版本', '子系統', '類型', '狀態（對 v8）', 'KMI 風險', '說明', '標題', 'upstream commit', 'KMI 判斷依據']) + '\n')
    for r in sorted(rows.values(), key=lambda r: (order.get(r['decision'], 9), r['batch'] or 9, r['subsystem'], r['commit'])):
        f.write('\t'.join(str(r[c]).replace('\t', ' ') for c in cols) + '\n')

# 篩選漏斗
stable = data['stable']
why = collections.Counter()
stats = {
    'stable_total_commits': 16411,
    'stable_relevant': len(stable),
    'cands': len(data['cands']),
    'luna_rows': len(data['luna']),
    'ack_rows': len(data['ack']),
    'unique_rows': len(rows),
    'decision': collections.Counter(r['decision'] for r in rows.values()),
    'by_batch': collections.Counter((r['batch'], r['decision']) for r in rows.values() if r['decision'] in ('建議', '可選')),
    'rec_status': collections.Counter(r['status'].split('（')[0] for r in rows.values() if r['decision'] == '建議'),
    'rec_kmi': collections.Counter(r['kmi'] for r in rows.values() if r['decision'] == '建議'),
    'stable_apply_v8': collections.Counter(r.get('apply_v8') for r in stable),
}
stats['by_batch'] = {f'{b}:{d}': n for (b, d), n in sorted(stats['by_batch'].items())}
json.dump({'stats': stats, 'rows': list(rows.values())}, open(OUT_JSON, 'w'), ensure_ascii=False, indent=1, default=dict)
print(json.dumps(stats, ensure_ascii=False, indent=1, default=dict))
