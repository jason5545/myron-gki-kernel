#!/usr/bin/env bash
# 在 PC 的 Proxmox LXC（原生 x86_64）同步固定來源並編譯，產物拉回 out/<名稱>/。
# GKI 原始碼與 Bazel 快取留在遠端 /gki，之後可增量重編。
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${BUILD_HOST:-root@10.0.0.182}"
KEY="${BUILD_KEY:-$HOME/.ssh/id_ed25519}"
JOBS="${BUILD_JOBS:-24}"
NAME="${1:-build-$(git -C "$PROJECT_ROOT" rev-parse --short HEAD)}"
SSH=(ssh -o BatchMode=yes -o IdentitiesOnly=yes -o ServerAliveInterval=30 -i "$KEY" "$HOST")
DEST="$PROJECT_ROOT/out/$NAME"

cd "$PROJECT_ROOT"
if [[ -n "$(git status --porcelain -- config manifests patches scripts tests source.lock.json root.lock.json)" ]]; then
  printf '有未 commit 的修改；repo 與封裝只讀取已 commit 的內容。\n' >&2
  exit 1
fi
{ git ls-files; find .git -type f; } | COPYFILE_DISABLE=1 tar --no-mac-metadata --no-xattrs -cf - -T - \
  | "${SSH[@]}" 'rm -rf /src.new && mkdir /src.new && tar -xf - -C /src.new && rm -rf /src && mv /src.new /src'
# 上次套過的 patch 與 root 來源先還原，apply_patches.py 要求乾淨的 common。
"${SSH[@]}" "set -euo pipefail; cd /src; mkdir -p out
  base=\$(python3 -c 'import json; print(json.load(open(\"source.lock.json\"))[\"common_commit\"])')
  if [[ -d /gki/common/.git ]]; then git -C /gki/common reset -q --hard \"\$base\" 2>/dev/null || git -C /gki/common reset -q --hard; git -C /gki/common clean -qfdx; fi
  bash scripts/sync.sh /gki
  BUILD_JOBS=$JOBS bash scripts/build.sh /gki" 2>&1 | tee "$PROJECT_ROOT/out/$NAME.log"
mkdir -p "$DEST"
"${SSH[@]}" 'cd /src/out && cp /src/work/resolved-manifest.xml reports/ && tar -cf - dist/Image dist/vmlinux.symvers dist/System.map reports packages build.log' \
  | tar -xf - -C "$DEST"
python3 - "$DEST" <<'PY'
import hashlib, json, pathlib, sys
dest = pathlib.Path(sys.argv[1])
expected = json.loads((dest / "reports/sha256.json").read_text())
for name in ("dist/Image", "dist/vmlinux.symvers", "dist/System.map"):
    if hashlib.sha256((dest / name).read_bytes()).hexdigest() != expected[name]:
        raise SystemExit(f"{name} 傳回 Mac 後 SHA-256 不符")
print(f"產物已取回並核對：{dest}")
PY
