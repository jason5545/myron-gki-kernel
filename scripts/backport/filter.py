#!/usr/bin/env python3
"""從 scan.py 的 stable.json 自動篩出候選，寫入 cands.json。輸出位置同 scan.py（KMI6_OUT）。"""
import collections, json, os, re

OUT = os.environ.get('KMI6_OUT', '/root/kmi6scan')
rows = json.load(open(f'{OUT}/stable.json'))
SEVERE = {'UAF', '死鎖', 'race', '資料損毀', 'NULL', '越界', '雙重釋放／參考計數', '崩潰'}
UNUSED = re.compile(r'sched_ext|\bscx\b|lru_gen|mglru|hugetlb|\bkvm\b|\bdamon\b|\bksm\b|userfaultfd|\buffd\b|memory[- ]tier|numa|zswap|\bdax\b|mm/damon|io_uring|netkit|mptcp|sctp|tipc|rds|smc|kcm|vxlan|geneve|openvswitch|\bovs\b|mpls|seg6|ioam|batman|caif|bonding|team|macsec|macvlan|ipvlan|ipip|gre\b|sit\b|bareudp|wireguard|\bxdp\b|af_xdp|xsk|bpf_struct_ops|nf_tables|nft_|nftables|\bipvs\b|ip_vs|ebtables|arp_tables|nfnetlink_queue|conntrack.*(sip|h323|pptp|sane|irc|amanda|tftp|snmp|ftp)', re.I)


def used(r):
    code = {p: v for p, v in r['builtin'].items() if p.endswith(('.c', '.S'))}
    if not code:
        return True  # 只改 header
    return any(v == 'y' for v in code.values())


cands, why = [], collections.Counter()
for r in rows:
    if r['apply'] == '基底已有':
        why['基底已有'] += 1
        continue
    if r['is_revert'] or r['reverted_later']:
        why['revert'] += 1
        continue
    if r['stable_dep']:
        why['prep(Stable-dep-of)'] += 1
        continue
    if r['other_platform']:
        why['其他平台'] += 1
        continue
    if not used(r):
        why['未編進核心(=m/n)'] += 1
        continue
    if UNUSED.search(r['subject']) or any(UNUSED.search(p) for p in r['files'] if p.endswith('.c')):
        why['手機沒用到的功能'] += 1
        continue
    if not set(r['severity']) & SEVERE:
        why['無明確嚴重類型' + ('(效能)' if r['perf'] else '')] += 1
        if r['perf']:
            r['_perf'] = True
            cands.append(r)
        continue
    cands.append(r)
print('篩除原因', dict(why))
sev = [r for r in cands if not r.get('_perf')]
print('嚴重修正候選', len(sev), '效能字樣', len(cands) - len(sev))
print('套用', collections.Counter(r['apply'] for r in sev))
print('KMI', collections.Counter(r['kmi'] for r in sev))
json.dump(cands, open(f'{OUT}/cands.json', 'w'), ensure_ascii=False, indent=1)
