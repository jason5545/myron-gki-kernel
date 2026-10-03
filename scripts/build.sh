#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GKI_WORKSPACE="${1:-$PROJECT_ROOT/work/gki}"
DIST_DIR="$PROJECT_ROOT/out/dist"
if [[ "$(uname -s)" != Linux ]]; then
  printf '核心編譯使用 Linux x86_64；Mac 可執行映像與模組分析。\n' >&2
  exit 1
fi
if [[ "$(uname -m)" != x86_64 ]]; then
  printf '固定工具鏈需要 Linux x86_64。\n' >&2
  exit 1
fi
python3 "$PROJECT_ROOT/scripts/validate.py" --source "$GKI_WORKSPACE"
mkdir -p "$DIST_DIR" "$PROJECT_ROOT/out/reports"
python3 "$PROJECT_ROOT/scripts/apply_patches.py" "$GKI_WORKSPACE/common" \
  --report "$PROJECT_ROOT/out/reports/applied-patches.json"
python3 "$PROJECT_ROOT/scripts/prepare_root.py" "$GKI_WORKSPACE/common" \
  --report "$PROJECT_ROOT/out/reports/root-source.json"
# 把 patch 提交成 commit，版本字串才會是 -g<commit>，不會因為工作目錄有修改變成 -dirty。
# 日期沿用基底 commit，同樣的 patch 會得到同樣的 commit。
base_date="$(git -C "$GKI_WORKSPACE/common" log -1 --format=%cI HEAD)"
git -C "$GKI_WORKSPACE/common" add -A
GIT_AUTHOR_DATE="$base_date" GIT_COMMITTER_DATE="$base_date" \
  git -C "$GKI_WORKSPACE/common" -c user.name=myron-gki -c user.email=myron-gki@users.noreply.github.com \
  commit -q -m "myron: 套用專案 patch 與固定 root 來源"
# 版本字串的 commit 開頭固定為 4b4d4935，也就是 "KMI5" 的 ASCII hex。在 commit 訊息尾端
# 找最小的 vanity-nonce，結果仍是真實存在、可重現的 git commit。SCM_PREFIX= 可關閉。
SCM_PREFIX="${SCM_PREFIX-4b4d4935}"
if [[ -n "$SCM_PREFIX" ]]; then
  mkdir -p "$PROJECT_ROOT/work/bin"
  cc -O2 -pthread -o "$PROJECT_ROOT/work/bin/vanity_commit" "$PROJECT_ROOT/scripts/vanity_commit.c" -lcrypto
  vanity_body="$(mktemp)"
  git -C "$GKI_WORKSPACE/common" cat-file commit HEAD \
    | "$PROJECT_ROOT/work/bin/vanity_commit" "$SCM_PREFIX" > "$vanity_body"
  vanity_commit="$(git -C "$GKI_WORKSPACE/common" hash-object -t commit -w "$vanity_body")"
  rm -f "$vanity_body"
  if [[ "$vanity_commit" != "$SCM_PREFIX"* ]]; then
    printf 'vanity commit 前綴不符：%s\n' "$vanity_commit" >&2
    exit 1
  fi
  git -C "$GKI_WORKSPACE/common" reset -q --soft "$vanity_commit"
  printf 'commit 前綴 %s：%s\n' "$SCM_PREFIX" "$vanity_commit"
fi
cd "$GKI_WORKSPACE"
# --config=stamp 讓 Kleaf 嵌入實際的 git commit；不加時 Kleaf 固定填 -maybe-dirty。
tools/bazel run --enable_workspace=false --config=stamp \
  --repo_manifest="$GKI_WORKSPACE:$PROJECT_ROOT/work/resolved-manifest.xml" \
  --jobs="${BUILD_JOBS:-2}" --lto=none //common:kernel_aarch64_dist -- --destdir="$DIST_DIR" \
  2>&1 | tee "$PROJECT_ROOT/out/build.log"
python3 "$PROJECT_ROOT/scripts/inspect_kernel.py" "$DIST_DIR/Image" \
  --json "$PROJECT_ROOT/out/reports/candidate-image.json" \
  --config-out "$PROJECT_ROOT/out/reports/candidate.config"
python3 "$PROJECT_ROOT/scripts/validate.py" --image "$DIST_DIR/Image"
python3 "$PROJECT_ROOT/scripts/module_abi.py" check \
  --required "$PROJECT_ROOT/baseline/module-requirements.json" \
  --symvers "$DIST_DIR/vmlinux.symvers" --system-map "$DIST_DIR/System.map" \
  --output "$PROJECT_ROOT/out/reports/module-abi.json"
python3 "$PROJECT_ROOT/scripts/package_kernel.py" --image "$DIST_DIR/Image" \
  --symvers "$DIST_DIR/vmlinux.symvers" --system-map "$DIST_DIR/System.map"
python3 - "$PROJECT_ROOT/out" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);files={}
for p in (root/'dist').glob('*'):
    if p.is_file():
        with p.open('rb') as f:
            files[str(p.relative_to(root))]=hashlib.file_digest(f,'sha256').hexdigest()
(root/'reports/sha256.json').write_text(json.dumps(files,indent=2)+'\n')
print('候選核心完成；模組簽章、KernelSU 與實機開機仍待驗證。')
PY
