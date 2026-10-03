#!/usr/bin/env python3
"""驗收 Image 與原廠模組 CRC，再產生沿用現有 boot 的 AnyKernel3 套件。"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zipfile

from inspect_kernel import inspect_path
from module_abi import compare
from validate import check_image

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def vendor_files():
    lock = json.loads((ROOT / "packaging/anykernel3.lock.json").read_text())
    paths = {}
    for name, source in lock["files"].items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("AnyKernel3 檔案路徑不符")
        path = ROOT / "packaging/anykernel3" / relative
        if digest(path) != source["sha256"]:
            raise ValueError(f"AnyKernel3 檔案 SHA-256 不符：{name}")
        if name in ("tools/busybox", "tools/magiskboot"):
            data = path.read_bytes()[:64]
            if data[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", data, 18)[0] != 183:
                raise ValueError(f"工具不是 ARM64 ELF：{name}")
        paths[name] = path
    return lock, paths


def create_package(image, symvers, system_map, builtin, output):
    source = json.loads((ROOT / "source.lock.json").read_text())
    policy = json.loads((ROOT / "config/kernel-policy.json").read_text())
    result, raw, _ = inspect_path(image)
    if errors := check_image(result, source, policy):
        raise ValueError("；".join(errors))
    required = json.loads((ROOT / "baseline/module-requirements.json").read_text())
    abi = compare(required, symvers, system_map, policy.get("abi_exceptions"),
                  builtin, policy.get("collision_exceptions"))
    if not abi["compatible"]:
        raise ValueError("原廠模組 CRC 或撞名驗收未通過，停止封裝")
    vendor, paths = vendor_files()
    manifest = {
        "schema": 1,
        "project_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "common_commit": source["common_commit"],
        "image": result,
        "symvers_sha256": digest(symvers),
        "system_map_sha256": digest(system_map),
        "module_abi": abi,
        "kernel_policy": policy,
        "root_sources": json.loads((ROOT / "root.lock.json").read_text()),
        "anykernel3": vendor,
        "device": "myron",
        "android": "16",
        "repack_existing_boot": True,
        "bundled_replacement_modules": False,
        "on_device_boot_verified": False,
    }
    payloads = {name: (path.read_bytes(), path.stat().st_mode & 0o777) for name, path in paths.items()}
    payloads["anykernel.sh"] = ((ROOT / "packaging/anykernel.sh").read_bytes(), 0o755)
    payloads["Image"] = (raw, 0o644)
    payloads["manifest.json"] = ((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode(), 0o644)
    if not output:
        output = ROOT / "out/packages" / f"myron-kmi5-{result['image_sha256'][:12]}-AnyKernel3.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, (data, mode) in sorted(payloads.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (0o100000 | mode) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
    package = {"file": output.name, "sha256": digest(output), "size": output.stat().st_size, "image_sha256": result["image_sha256"]}
    output.with_suffix(".json").write_text(json.dumps(package, indent=2) + "\n")
    print(json.dumps(package, ensure_ascii=False, indent=2))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--symvers", required=True, type=Path)
    parser.add_argument("--system-map", required=True, type=Path)
    parser.add_argument("--builtin", required=True, type=Path, help="編譯產物的 modules.builtin")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    create_package(args.image, args.symvers, args.system_map, args.builtin, args.output)


if __name__ == "__main__":
    main()
