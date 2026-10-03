#!/usr/bin/env python3
"""在固定 common 基底套用專案 patch，保留每份 patch 的 SHA-256。"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def apply(common, report):
    expected = json.loads((ROOT / "source.lock.json").read_text())["common_commit"]
    actual = subprocess.check_output(["git", "-C", str(common), "rev-parse", "HEAD"], text=True).strip()
    if actual != expected:
        raise ValueError("common 基底 commit 不符")
    if subprocess.check_output(["git", "-C", str(common), "status", "--porcelain"], text=True).strip():
        raise ValueError("套用前的 common 工作目錄必須乾淨")
    patches = []
    for line in (ROOT / "patches/series").read_text().splitlines():
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        if Path(name).name != name or not name.endswith(".patch"):
            raise ValueError("patch 檔名格式不符")
        patch = ROOT / "patches" / name
        subprocess.run(["git", "-C", str(common), "apply", "--check", str(patch)], check=True)
        subprocess.run(["git", "-C", str(common), "apply", str(patch)], check=True)
        patches.append({"name": name, "sha256": hashlib.sha256(patch.read_bytes()).hexdigest()})
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"base_commit": expected, "patches": patches}, indent=2) + "\n")
    print(f"已套用 {len(patches)} 份相容 patch；基底 commit {expected}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("common", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    apply(args.common, args.report)


if __name__ == "__main__":
    main()
