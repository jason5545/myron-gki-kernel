#!/usr/bin/env python3
"""掃描 linux-6.12.y 6.12.39..111，對 ACK 1ad7be92（6.12.38，KMI 5）做套用、反向套用、
3-way 檢查，並估計是否編進核心與 KMI 風險。在 LXC 112 執行。

STABLE_RANGE 改掃描範圍（例如 v6.12.111..v6.12.112），KMI6_BASE 改比對的樹
（build_tree.py 建出的目前 patch 狀態）。"""
import collections, json, os, re, subprocess, sys

STABLE = '/gki/stable'
KMI = '/gki/kmi6'
BASE = os.environ.get('KMI6_BASE', '1ad7be92b3ed2e7d9c39f9b6d96bb91f1220c76d')
RANGE = os.environ.get('STABLE_RANGE', 'v6.12.111')
CONFIG_PATH = '/src/out/reports/candidate.config'
SYSMAP_PATH = '/src/out/dist/System.map'
OUT = os.environ.get('KMI6_OUT', '/root/kmi6scan')
os.makedirs(OUT + '/patches', exist_ok=True)

# (前綴, 子系統, 層級) 層級 A = Jason 點名，B = 手機用到的核心子系統
SUBSYS = [
    ('fs/f2fs/', 'f2fs', 'A'), ('include/linux/f2fs_fs.h', 'f2fs', 'A'),
    ('fs/erofs/', 'erofs', 'A'),
    ('block/', 'block', 'A'), ('include/linux/blk', 'block', 'A'), ('include/linux/bio.h', 'block', 'A'),
    ('drivers/ufs/core/', 'ufs', 'A'), ('include/ufs/', 'ufs', 'A'),
    ('mm/', 'mm', 'A'), ('include/linux/mm', 'mm', 'A'), ('include/linux/huge_mm.h', 'mm', 'A'),
    ('include/linux/swap', 'mm', 'A'), ('include/linux/page', 'mm', 'A'), ('include/linux/memcontrol.h', 'mm', 'A'),
    ('kernel/sched/', 'sched', 'A'), ('include/linux/sched', 'sched', 'A'),
    ('drivers/android/', 'binder', 'A'),
    ('net/core/', 'net', 'A'), ('net/ipv4/', 'net', 'A'), ('net/ipv6/', 'net', 'A'),
    ('net/unix/', 'net', 'A'), ('net/xfrm/', 'net', 'A'), ('net/netlink/', 'net', 'A'),
    ('net/packet/', 'net', 'A'), ('net/sched/', 'net', 'A'), ('net/key/', 'net', 'A'),
    ('include/net/', 'net', 'A'), ('include/linux/skbuff.h', 'net', 'A'), ('include/linux/netdevice.h', 'net', 'A'),
    ('net/netfilter/', 'netfilter', 'A'), ('net/ipv4/netfilter/', 'netfilter', 'A'),
    ('net/ipv6/netfilter/', 'netfilter', 'A'), ('include/linux/netfilter', 'netfilter', 'A'),
    ('include/net/netfilter/', 'netfilter', 'A'),
    ('fs/crypto/', 'fscrypt', 'A'), ('include/linux/fscrypt.h', 'fscrypt', 'A'),
    ('fs/fuse/', 'fuse', 'A'),
    ('drivers/usb/host/xhci', 'xhci', 'A'),
    ('drivers/scsi/scsi', 'scsi', 'B'), ('drivers/scsi/sd.c', 'scsi', 'B'),
    ('fs/ext4/', 'ext4', 'B'), ('fs/jbd2/', 'ext4', 'B'),
    ('fs/overlayfs/', 'overlayfs', 'B'),
    ('drivers/block/loop.c', 'loop', 'B'),
    ('drivers/md/dm', 'dm', 'B'),
    ('drivers/usb/core/', 'usb-core', 'B'), ('drivers/usb/gadget/', 'usb-gadget', 'B'),
    ('drivers/usb/dwc3/', 'dwc3', 'B'), ('drivers/usb/typec/', 'typec', 'B'),
    ('kernel/time/', 'time', 'B'), ('kernel/futex/', 'futex', 'B'), ('kernel/locking/', 'locking', 'B'),
    ('kernel/rcu/', 'rcu', 'B'), ('kernel/workqueue.c', 'workqueue', 'B'), ('kernel/cgroup/', 'cgroup', 'B'),
    ('kernel/bpf/', 'bpf', 'B'), ('kernel/irq/', 'irq', 'B'), ('kernel/power/', 'pm', 'B'),
    ('drivers/base/power/', 'pm', 'B'), ('kernel/exit.c', 'kernel', 'B'), ('kernel/fork.c', 'kernel', 'B'),
    ('kernel/signal.c', 'kernel', 'B'), ('kernel/sys.c', 'kernel', 'B'), ('kernel/pid', 'kernel', 'B'),
    ('kernel/kthread.c', 'kernel', 'B'), ('kernel/cpu.c', 'kernel', 'B'), ('kernel/softirq.c', 'kernel', 'B'),
    ('kernel/smp.c', 'kernel', 'B'), ('kernel/events/', 'perf', 'B'), ('kernel/printk/', 'printk', 'B'),
    ('drivers/cpufreq/cpufreq.c', 'cpufreq', 'B'), ('drivers/cpuidle/', 'cpuidle', 'B'),
    ('drivers/thermal/thermal_', 'thermal', 'B'), ('drivers/dma-buf/', 'dma-buf', 'B'),
    ('fs/proc/', 'vfs', 'B'), ('fs/kernfs/', 'vfs', 'B'), ('fs/sysfs/', 'vfs', 'B'), ('fs/exfat/', 'exfat', 'B'),
    ('fs/fat/', 'fat', 'B'), ('fs/iomap/', 'vfs', 'B'), ('fs/notify/', 'vfs', 'B'),
    ('security/selinux/', 'selinux', 'B'), ('security/', 'security', 'B'),
    ('arch/arm64/mm/', 'arm64', 'B'), ('arch/arm64/kernel/', 'arm64', 'B'), ('arch/arm64/include/', 'arm64', 'B'),
    ('arch/arm64/lib/', 'arm64', 'B'), ('arch/arm64/crypto/', 'arm64', 'B'),
    ('crypto/', 'crypto', 'B'), ('lib/', 'lib', 'B'), ('io_uring/', 'io_uring', 'B'),
    ('drivers/hid/hid-core.c', 'hid', 'B'), ('drivers/input/input.c', 'input', 'B'),
    ('drivers/tty/', 'tty', 'B'), ('net/bluetooth/', 'bluetooth', 'B'), ('net/wireless/', 'wireless', 'B'),
    ('net/mac80211/', 'mac80211', 'B'), ('net/tls/', 'net', 'B'), ('net/l2tp/', 'net', 'B'),
    ('net/bridge/', 'net', 'B'), ('net/8021q/', 'net', 'B'), ('net/qrtr/', 'net', 'B'),
    ('drivers/net/tun.c', 'net', 'B'), ('drivers/net/ppp/', 'net', 'B'),
    ('fs/', 'vfs', 'B'),  # fs/ 根目錄的 VFS 檔案；fs/<其他檔案系統>/ 會在下面排除
]
FS_SKIP = re.compile(r'^fs/(?!f2fs/|erofs/|ext4/|jbd2/|fuse/|crypto/|overlayfs/|proc/|kernfs/|sysfs/|exfat/|fat/|iomap/|notify/)[^/]+/')
SKIP = re.compile(r'^(Documentation/|tools/|samples/|scripts/|LICENSES/|MAINTAINERS|.*selftests?/|.*/kunit|.*_test\.c$|.*-test\.c$)')
OTHER_PLATFORM = re.compile(r'mediatek|\bmtk\b|exynos|samsung|intel|tegra|nvidia|amd|x86|imx|rockchip|allwinner|sunxi|renesas|ti[- ]k3|stm32|meson|amlogic|broadcom|bcm|marvell|hisilicon|kirin|unisoc|loongarch|riscv|powerpc|s390|mips', re.I)

SEVERITY = [
    ('UAF', r'use[- ]after[- ]free|\bUAF\b|slab-use-after'),
    ('死鎖', r'dead[- ]?lock|circular locking|hung[- ]task|\bhang|livelock|soft lockup|hard lockup|\bstall'),
    ('race', r'\brac(e|es|y|ing)\b|data-race|TOCTOU'),
    ('資料損毀', r'corrupt|data loss|lose data|lost data|silent(ly)? (data )?loss'),
    ('NULL', r'null[- ]ptr|null[- ]pointer|NULL (pointer )?deref'),
    ('越界', r'out[- ]of[- ]bounds|\bOOB\b|overflow|underflow|overrun|overread'),
    ('雙重釋放／參考計數', r'double[- ]free|refcount|reference count|ref leak|refcnt|imbalance'),
    ('崩潰', r'\bBUG_ON\b|\bBUG:|kernel panic|\bpanic\b|\bcrash|\boops\b|general protection'),
    ('工具回報', r'syzbot|syzkaller|KASAN|KMSAN|KCSAN|UBSAN'),
    ('洩漏', r'\bleak'),
    ('CVE', r'CVE-\d{4}-\d+'),
]
PERF = re.compile(r'\b(optimi[sz]e|speed ?up|performance|faster|reduce (the )?(overhead|latency|contention)|avoid unnecessary|scalab)', re.I)


def run(*cmd, cwd=None, check=True, input=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors='replace', input=input)
    if check and r.returncode != 0:
        raise RuntimeError(f'{cmd}: {r.stderr[:500]}')
    return r


def load_config():
    cfg = {}
    for line in open(CONFIG_PATH):
        m = re.match(r'^(CONFIG_\w+)=(.*)$', line)
        if m:
            cfg[m.group(1)] = m.group(2)
    return cfg


CFG = load_config()
SYSMAP = set()
for line in open(SYSMAP_PATH):
    parts = line.split()
    if len(parts) >= 3:
        SYSMAP.add(parts[2])


def subsystem(path):
    if FS_SKIP.match(path) and not path.startswith(('fs/f2fs', 'fs/erofs')):
        return None
    for prefix, name, tier in SUBSYS:
        if path.startswith(prefix):
            return name, tier
    return None


MAKEFILE_CACHE = {}


def makefile_text(d):
    if d in MAKEFILE_CACHE:
        return MAKEFILE_CACHE[d]
    text = ''
    for name in ('Makefile', 'Kbuild'):
        p = os.path.join(KMI, d, name)
        if os.path.exists(p):
            text += open(p, errors='replace').read() + '\n'
    text = text.replace('\\\n', ' ')
    MAKEFILE_CACHE[d] = text
    return text


def cond_value(var):
    """$(CONFIG_X) → y／m／n；y 直接回 y。"""
    if var == 'y':
        return 'y'
    m = re.fullmatch(r'\$\((CONFIG_\w+)\)', var)
    if not m:
        return '?'
    return CFG.get(m.group(1), 'n')


def dir_builtin(d, depth=0):
    """往上找父目錄的 obj-$(CONFIG_X) += d/。"""
    if depth > 6 or d in ('', '.') or '/' not in d:
        return 'y'
    parent, name = d.rsplit('/', 1)
    text = makefile_text(parent)
    vals = []
    for m in re.finditer(r'^\s*obj-(\S+?)\s*[:+]?=\s*(.*)$', text, re.M):
        if re.search(r'(^|\s)' + re.escape(name) + r'/(\s|$)', m.group(2)):
            vals.append(cond_value(m.group(1)))
    if not vals:
        return dir_builtin(parent, depth + 1) if depth < 2 else '?'
    v = 'y' if 'y' in vals else ('m' if 'm' in vals else ('?' if '?' in vals else 'n'))
    if v == 'y':
        up = dir_builtin(parent, depth + 1)
        return 'y' if up in ('y', '?') else up
    return v


def obj_builtin(d, objname, depth=0):
    text = makefile_text(d)
    vals = []
    for m in re.finditer(r'^\s*([\w-]+)-(\S+?)\s*[:+]?=\s*(.*)$', text, re.M):
        lhs, cond, rhs = m.group(1), m.group(2), m.group(3)
        if not re.search(r'(^|\s)' + re.escape(objname) + r'\.o(\s|$)', rhs):
            continue
        c = cond_value(cond) if cond.startswith('$(') or cond == 'y' else ('y' if cond in ('objs',) else '?')
        if lhs == 'obj':
            vals.append(c)
        elif lhs in ('lib', 'core', 'ccflags', 'ldflags'):
            vals.append(c if lhs == 'lib' else '?')
        else:
            if c == 'n':
                vals.append('n')
                continue
            if depth < 3:
                parent = obj_builtin(d, lhs, depth + 1)
                vals.append(parent if c in ('y', '?') else ('m' if parent in ('y', 'm') else parent))
    if not vals:
        return '?'
    if 'y' in vals:
        return 'y'
    if 'm' in vals:
        return 'm'
    if '?' in vals:
        return '?'
    return 'n'


def builtin_status(path, funcs):
    if not path.endswith(('.c', '.S')):
        return 'header'
    d, base = os.path.split(path)
    base = re.sub(r'\.[cS]$', '', base)
    v = obj_builtin(d, base)
    if v == 'y':
        dv = dir_builtin(d)
        v = 'y' if dv in ('y', '?') else dv
    if v == '?':
        if any(f in SYSMAP for f in funcs):
            return 'y'
    return v


HUNK_FUNC = re.compile(r'^@@ [^@]+ @@\s*(.*)$')
IDENT = re.compile(r'\b([A-Za-z_]\w*)\s*\(')


def parse_patch(text):
    files = collections.OrderedDict()
    cur = None
    for line in text.splitlines():
        if line.startswith('diff --git '):
            m = re.match(r'diff --git a/(\S+) b/(\S+)', line)
            cur = m.group(2)
            files[cur] = {'hunks': [], 'plus': [], 'minus': []}
        elif cur is None:
            continue
        elif line.startswith('@@'):
            m = HUNK_FUNC.match(line)
            files[cur]['hunks'].append({'ctx': m.group(1) if m else '', 'plus': [], 'minus': []})
        elif line.startswith('+') and not line.startswith('+++'):
            files[cur]['plus'].append(line[1:])
            if files[cur]['hunks']:
                files[cur]['hunks'][-1]['plus'].append(line[1:])
        elif line.startswith('-') and not line.startswith('---'):
            files[cur]['minus'].append(line[1:])
            if files[cur]['hunks']:
                files[cur]['hunks'][-1]['minus'].append(line[1:])
    return files


EXPORTS_CACHE = {}


def exported_in(path):
    if path in EXPORTS_CACHE:
        return EXPORTS_CACHE[path]
    p = os.path.join(KMI, path)
    s = set()
    if os.path.exists(p):
        s = set(re.findall(r'EXPORT_SYMBOL(?:_GPL)?(?:_NS(?:_GPL)?)?\(\s*(\w+)', open(p, errors='replace').read()))
    EXPORTS_CACHE[path] = s
    return s


PROTO = re.compile(r'^\s*(extern\s+)?(const\s+|unsigned\s+|signed\s+|struct\s+|enum\s+)*[A-Za-z_][\w\s\*]*?\b([A-Za-z_]\w*)\s*\([^;{]*\)?\s*;?\s*$')


def kmi_risk(files):
    """回傳 (等級, 理由)。高：匯出結構／enum／函式簽名可能變動；中：header 有改；低：只改 .c 內部。"""
    reasons = []
    level = '低'
    for path, f in files.items():
        changed = f['plus'] + f['minus']
        if not changed:
            continue
        if path.endswith('.h'):
            for h in f['hunks']:
                ctx = h['ctx']
                lines = [l for l in h['plus'] + h['minus'] if l.strip() and not l.strip().startswith(('//', '/*', '*', '*/'))]
                if not lines:
                    continue
                if re.match(r'\s*(struct|union)\s+\w+\s*\{', ctx) or any(re.match(r'^\s*(struct|union)\s+\w+\s*\{', l) for l in lines):
                    if any(re.search(r'[;,]\s*(/\*.*)?$', l) for l in lines) or any('ANDROID_KABI' in l for l in lines):
                        level = '高'
                        reasons.append(f'{path}: 結構成員')
                        continue
                if re.match(r'\s*enum\s+\w+\s*\{', ctx) and any(re.search(r',\s*$|^\s*\w+\s*=', l) for l in lines):
                    level = '高'
                    reasons.append(f'{path}: enum')
                    continue
                if any(PROTO.match(l) and not l.startswith((' ', '\t')) and not l.lstrip().startswith(('static', '#', 'return', 'if', '}', 'DECLARE', 'DEFINE', 'TRACE', 'EXPORT')) for l in lines):
                    level = '高'
                    reasons.append(f'{path}: 函式宣告')
                    continue
                if level == '低':
                    level = '中'
                reasons.append(f'{path}: header 內容')
        else:
            exp = exported_in(path)
            for l in changed:
                if l.startswith((' ', '\t')):
                    continue
                for name in IDENT.findall(l)[:1]:
                    if name in exp:
                        level = '高'
                        reasons.append(f'{path}: 匯出函式 {name} 簽名')
            for h in f['hunks']:
                if re.match(r'\s*(struct|union)\s+\w+\s*\{', h['ctx']) and any(re.search(r';\s*$', l) for l in h['plus'] + h['minus'] if l.startswith('\t') and not l.startswith('\t\t')):
                    if level == '低':
                        level = '中'
                    reasons.append(f'{path}: .c 內的結構（{h["ctx"].strip()[:40]}）')
    return level, sorted(set(reasons))


def severity(text):
    tags = []
    for name, pat in SEVERITY:
        if re.search(pat, text, re.I):
            tags.append(name)
    return tags


def apply_status(patch_path, commit=None):
    fwd = run('git', 'apply', '--check', patch_path, cwd=KMI, check=False)
    if fwd.returncode == 0:
        return '可套用'
    rev = run('git', 'apply', '--check', '-R', patch_path, cwd=KMI, check=False)
    if rev.returncode == 0:
        return '基底已有'
    if commit:
        mt = run('git', 'merge-tree', '--write-tree', f'--merge-base={commit}^', BASE, commit, cwd=KMI, check=False)
        if mt.returncode == 0:
            tree = mt.stdout.split('\n')[0].strip()
            base_tree = run('git', 'rev-parse', BASE + '^{tree}', cwd=KMI).stdout.strip()
            return '基底已有' if tree == base_tree else '3-way 可合併'
        if mt.returncode == 1:
            return '衝突需改寫'
    fuzzy = run('git', 'apply', '--check', '-C1', patch_path, cwd=KMI, check=False)
    if fuzzy.returncode == 0:
        return '3-way 可合併'
    return '衝突需改寫'


def stable_commits():
    shallow = set(open(STABLE + '/.git/shallow').read().split())
    fmt = '%x1e%H%x1f%s%x1f%b%x1f'
    out = run('git', 'log', '--no-merges', '--name-only', f'--format={fmt}', RANGE, cwd=STABLE).stdout
    version = None
    commits = []
    for chunk in out.split('\x1e')[1:]:
        h, s, b, rest = chunk.split('\x1f', 3)
        files = [l for l in rest.strip().splitlines() if l.strip()]
        m = re.fullmatch(r'Linux 6\.12\.(\d+)', s.strip())
        if m:
            version = int(m.group(1))
            continue
        commits.append({'commit': h, 'subject': s.strip(), 'body': b, 'files': files,
                        'version': f'6.12.{version}' if version else '?', 'boundary': h in shallow})
    return commits


def main():
    commits = stable_commits()
    reverted = collections.Counter()
    for c in commits:
        m = re.match(r'Revert "(.*)"$', c['subject'])
        if m:
            reverted[m.group(1)] += 1
    rows = []
    for c in commits:
        if c['boundary']:
            continue
        files = [f for f in c['files'] if not SKIP.match(f)]
        subs = [subsystem(f) for f in files]
        subs = [s for s in subs if s]
        if not subs:
            continue
        text = c['subject'] + '\n' + c['body']
        up = re.search(r'\[ Upstream commit ([0-9a-f]{40}) \]|commit ([0-9a-f]{40}) upstream', c['body'])
        tier = 'A' if any(t == 'A' for _, t in subs) else 'B'
        names = sorted({n for n, _ in subs})
        row = {
            'commit': c['commit'], 'version': c['version'], 'subject': c['subject'],
            'upstream': (up.group(1) or up.group(2)) if up else None,
            'subsystems': names, 'tier': tier, 'files': c['files'],
            'stable_dep': bool(re.search(r'^Stable-dep-of:', c['body'], re.M)),
            'is_revert': c['subject'].startswith('Revert "'),
            'reverted_later': reverted.get(c['subject'], 0) > 0,
            'severity': severity(text), 'perf': bool(PERF.search(c['subject'])),
            'other_platform': bool(OTHER_PLATFORM.search(c['subject'])),
            'fixes': re.findall(r'^Fixes: ([0-9a-f]{8,40}) \("(.*)"\)', c['body'], re.M),
        }
        patch = run('git', 'format-patch', '-1', '--stdout', c['commit'], cwd=STABLE).stdout
        pp = f"{OUT}/patches/{c['commit'][:12]}.patch"
        open(pp, 'w').write(patch)
        pf = parse_patch(patch)
        row['kmi'], row['kmi_reasons'] = kmi_risk(pf)
        bstat = {}
        for path, f in pf.items():
            funcs = set()
            for h in f['hunks']:
                funcs.update(IDENT.findall(h['ctx']))
            bstat[path] = builtin_status(path, funcs)
        row['builtin'] = bstat
        row['apply'] = apply_status(pp, c['commit'])
        row['lines'] = sum(len(f['plus']) + len(f['minus']) for f in pf.values())
        rows.append(row)
        if len(rows) % 100 == 0:
            print(len(rows), file=sys.stderr, flush=True)
    json.dump(rows, open(OUT + '/stable.json', 'w'), ensure_ascii=False, indent=1)
    print('rows', len(rows))


if __name__ == '__main__':
    main()
