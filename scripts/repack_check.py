#!/usr/bin/env python3
"""只在手機暫存目錄重封裝 boot，取回檔案驗收；不執行安裝或刷入。"""
import argparse
import json
from pathlib import Path
import shlex
import struct
import subprocess
import tempfile

from inspect_kernel import inspect_path
from package_kernel import ROOT, digest, vendor_files
from validate import check_image

REMOTE_ROOT = "/data/local/tmp/myron-kernel-repack-check"
# 310 的原廠 boot：核心與 309 相同，只有 AVB footer 不同（docs/rom-upgrade-310.md）。
STOCK_BOOT_310 = "ecbfbf6640d45df4c6fd68686f8a9bc9be5b4c31f8f4a3f6d26cd9d6be3229f9"


def check_repacked(stock_bytes, candidate_bytes, expected_kernel):
    if len(candidate_bytes) > len(stock_bytes):
        raise ValueError("重封裝映像超過原廠分割區備份大小")
    expected_header = bytearray(stock_bytes[:4096])
    struct.pack_into("<I", expected_header, 8, len(expected_kernel))
    if candidate_bytes[:4096] != expected_header:
        raise ValueError("重封裝改變了核心大小以外的 boot 標頭")
    size = struct.unpack_from("<I", candidate_bytes, 8)[0]
    if candidate_bytes[4096:4096 + size] != expected_kernel:
        raise ValueError("重封裝的核心與候選 Image 不符")


def repack(adb, serial, stock_boot, image, output, expect_live=None):
    stock = json.loads((ROOT / "baseline/stock-image.json").read_text())
    if digest(stock_boot) not in (stock["sha256"], STOCK_BOOT_310):
        raise ValueError("原廠 boot 備份不是已收集的 309 或 310 原廠 boot")
    info, raw, _ = inspect_path(image)
    source = json.loads((ROOT / "source.lock.json").read_text())
    policy = json.loads((ROOT / "config/kernel-policy.json").read_text())
    if errors := check_image(info, source, policy):
        raise ValueError("；".join(errors))
    vendor_files()
    remote = f"{REMOTE_ROOT}/{info['image_sha256'][:12]}"
    adb_args = [adb, "-s", serial]
    logs = []

    def run(args, timeout=90):
        result = subprocess.run(adb_args + args, capture_output=True, text=True, timeout=timeout)
        logs.append(result.stdout + result.stderr)
        print(result.stdout + result.stderr, end="", flush=True)
        result.check_returncode()
        return result.stdout.strip()

    def shell(command):
        return run(["shell", "su -c " + shlex.quote(command)])

    slot = shell("getprop ro.boot.slot_suffix")
    if slot not in ("_a", "_b"):
        raise ValueError("無法辨識目前 slot")
    boot_block = f"/dev/block/bootdevice/by-name/boot{slot}"
    before = shell(f"sha256sum {boot_block}").split()[0]
    # 預設要求手機仍是原廠 boot；已刷過本專案核心時，用 --expect-live-sha 指定目前應有的雜湊。
    if before != (expect_live or stock["sha256"]):
        raise ValueError("目前手機 boot 與預期不同，停止使用既有基準")
    shell(f"test -d /data/local/tmp\nmkdir -p {remote}/unpack\nchmod 755 {remote}")
    with tempfile.TemporaryDirectory() as folder:
        extracted = Path(folder) / "Image"
        extracted.write_bytes(raw)
        for path, name in [(stock_boot, "boot-original.img"), (extracted, "Image"),
                           (ROOT / "packaging/anykernel3/tools/magiskboot", "magiskboot")]:
            run(["push", str(path), f"{remote}/{name}"])
    shell(f"set -e\ncd {remote}\nchmod 755 magiskboot\ncd unpack\n"
          "../magiskboot unpack -h ../boot-original.img\n"
          "cp ../Image kernel\n"
          "PATCHVBMETAFLAG=false ../magiskboot repack ../boot-original.img ../boot-candidate.img\n"
          "sha256sum ../boot-candidate.img")
    output.parent.mkdir(parents=True, exist_ok=True)
    run(["pull", f"{remote}/boot-candidate.img", str(output)])
    check_repacked(stock_boot.read_bytes(), output.read_bytes(), raw)
    candidate, _, _ = inspect_path(output)
    after = shell(f"sha256sum {boot_block}").split()[0]
    if after != before:
        raise ValueError("手機 boot 分割區的內容改變，停止驗收")
    report = {
        "schema": 1,
        "mode": "temporary_files_only",
        "original_boot_sha256": before,
        "live_boot_sha256_after": after,
        "live_boot_unchanged": before == after,
        "boot_header_preserved_except_kernel_size": True,
        "candidate_kernel_matches_image": True,
        "candidate": candidate,
        "magiskboot_sha256": digest(ROOT / "packaging/anykernel3/tools/magiskboot"),
        "boot_partition_written": False,
        "on_device_boot_verified": False,
        "standby": policy["standby"],
    }
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    output.with_suffix(".log").write_text("".join(logs))
    print("重封裝與核心內容驗收通過；手機 boot 分割區未改變。")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", required=True)
    parser.add_argument("--stock-boot", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expect-live-sha", help="目前 boot 分割區應有的 SHA-256；預設為原廠")
    args = parser.parse_args()
    repack(args.adb, args.serial, args.stock_boot, args.image, args.output, args.expect_live_sha)


if __name__ == "__main__":
    main()
