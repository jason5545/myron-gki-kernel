#!/usr/bin/env python3
"""核對固定 root 來源，將 ReSukiSU／SUSFS 放入 common，不執行上游 setup。"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def verify_sources():
    lock = json.loads((ROOT / "root.lock.json").read_text())
    vendor = ROOT / "vendor"
    actual = {p.relative_to(vendor).as_posix() for p in vendor.rglob("*") if p.is_file() or p.is_symlink()}
    if actual != set(lock["files"]):
        raise ValueError("root 來源檔案清單改變")
    for name, expected in lock["files"].items():
        path = vendor / name
        if expected["type"] == "symlink":
            if not path.is_symlink() or str(path.readlink()) != expected["target"]:
                raise ValueError(f"root 來源連結不符：{name}")
        elif path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
            raise ValueError(f"root 來源 SHA-256 不符：{name}")
    uapi = (vendor / "resukisu/uapi/supercall.h").read_text()
    if f"KERNEL_SU_UAPI_VERSION = {lock['resukisu']['uapi_version']};" not in uapi:
        raise ValueError("ReSukiSU UAPI 與固定版本不符")
    if f'SUSFS_VERSION "{lock["susfs"]["version"]}"' not in (vendor / "susfs/kernel_patches/include/linux/susfs.h").read_text():
        raise ValueError("SUSFS 版本與固定來源不符")
    return lock


def prepare(common, report):
    lock = verify_sources()
    source = json.loads((ROOT / "source.lock.json").read_text())
    head = subprocess.check_output(["git", "-C", str(common), "rev-parse", "HEAD"], text=True).strip()
    if head != source["common_commit"]:
        raise ValueError("root 整合的 common 基底不符")
    target = common / "drivers/kernelsu"
    if target.exists():
        raise ValueError("drivers/kernelsu 已存在，停止覆蓋")
    shutil.copytree(ROOT / "vendor/resukisu/kernel", target, symlinks=False)
    r = lock["resukisu"]
    (target / "pinned-version.mk").write_text(
        "# 版本碼來自同一提交的官方發行 APK；只固定建置資料，不偽裝 UAPI。\n"
        f"KSU_LOCAL_VERSION := {r['commit_count']}\n"
        f"KSU_VERSION := {r['version_code']}\n"
        f"KSU_TAG_NAME := {r['tag']}\n"
        f"KSU_COMMIT_SHA := {r['commit'][:8]}\n"
        f"KSU_BRANCH_NAME := pinned-{r['tag']}\n"
    )
    patch = ROOT / "root-patches/0001-pin-resukisu-version-for-kleaf.patch"
    subprocess.run(["git", "apply", "--directory=drivers/kernelsu", "--check", str(patch)], cwd=common, check=True)
    subprocess.run(["git", "apply", "--directory=drivers/kernelsu", str(patch)], cwd=common, check=True)
    if "include $(KSU_SRC)/pinned-version.mk" not in (target / "Kbuild").read_text():
        raise ValueError("ReSukiSU 建置資料配套未生效")
    copied = {}
    for name in ("fs/susfs.c", "include/linux/susfs.h", "include/linux/susfs_def.h"):
        src = ROOT / "vendor/susfs/kernel_patches" / name
        dest = common / name
        if dest.exists():
            raise ValueError(f"SUSFS 檔案已存在：{name}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        copied[name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    data = {"resukisu": r, "susfs": lock["susfs"], "manager": lock["manager"],
            "root_adapter_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(), "copied": copied}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"固定 ReSukiSU {r['tag']}／{r['version_code']}／UAPI {r['uapi_version']}；SUSFS {lock['susfs']['version']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("common", type=Path, nargs="?")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.common:
        if not args.report:
            parser.error("整合來源時需要 --report")
        prepare(args.common, args.report)
    else:
        lock = verify_sources()
        print(f"root 固定來源驗收通過：{len(lock['files'])} 個檔案與連結")


if __name__ == "__main__":
    main()
