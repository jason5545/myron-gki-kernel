#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GKI_WORKSPACE="${1:-$PROJECT_ROOT/work/gki}"
mkdir -p "$GKI_WORKSPACE" "$PROJECT_ROOT/work/bin"
GKI_WORKSPACE="$(cd "$GKI_WORKSPACE" && pwd)"
python3 "$PROJECT_ROOT/scripts/validate.py"
REPO_COMMIT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["repo_tool_commit"])' "$PROJECT_ROOT/source.lock.json")"
REPO_LAUNCHER="$PROJECT_ROOT/work/bin/repo"
curl --fail --silent --show-error --retry 3 --max-time 60 \
  "https://gerrit.googlesource.com/git-repo/+/$REPO_COMMIT/repo?format=TEXT" \
  | base64 --decode > "$REPO_LAUNCHER"
python3 - "$PROJECT_ROOT/source.lock.json" "$REPO_LAUNCHER" <<'PY'
import hashlib,json,pathlib,sys
expected=json.load(open(sys.argv[1]))["repo_launcher_sha256"]
if hashlib.sha256(pathlib.Path(sys.argv[2]).read_bytes()).hexdigest()!=expected:
    raise SystemExit("repo 啟動檔 SHA-256 不符")
PY
chmod +x "$REPO_LAUNCHER"
cd "$GKI_WORKSPACE"
"$REPO_LAUNCHER" init -u "$PROJECT_ROOT" -b main -m manifests/gki.xml \
  --depth=1 --repo-url=https://gerrit.googlesource.com/git-repo --repo-rev="$REPO_COMMIT" \
  --no-clone-bundle --no-use-superproject
"$REPO_LAUNCHER" sync -c -j2 --no-tags --no-clone-bundle --fail-fast
"$REPO_LAUNCHER" manifest -r -o "$PROJECT_ROOT/work/resolved-manifest.xml"
python3 "$PROJECT_ROOT/scripts/validate.py" --source "$GKI_WORKSPACE"
