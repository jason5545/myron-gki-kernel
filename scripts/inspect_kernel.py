#!/usr/bin/env python3
"""只讀分析 boot／init_boot／AnyKernel3／ARM64 Image，不執行套件腳本。"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile
import zlib

MAX_IMAGE = 256 * 1024 * 1024


def inspect(data):
    result = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    image = data
    if data.startswith(b"ANDROID!"):
        if len(data) < 1584:
            raise ValueError("boot 標頭不完整")
        version = struct.unpack_from("<I", data, 40)[0]
        if version not in (3, 4):
            raise ValueError(f"尚未支援 boot header v{version}")
        kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from("<4I", data, 8)
        if header_size != (1584 if version == 4 else 1580):
            raise ValueError("boot 標頭大小不符")
        if 4096 + kernel_size > len(data):
            raise ValueError("boot 的核心資料不完整")
        signature_size = struct.unpack_from("<I", data, 1580)[0] if version == 4 else 0
        result["boot"] = {"header_version": version, "kernel_size": kernel_size,
                          "ramdisk_size": ramdisk_size, "os_version": os_version,
                          "signature_size": signature_size}
        image = data[4096:4096 + kernel_size]
        if not image:
            result["kind"] = "init_boot"
            return result, None, None
    if image.startswith(b"\x1f\x8b"):
        image = gzip.decompress(image)
    if len(image) > MAX_IMAGE or len(image) < 64 or image[56:60] != b"ARM\x64":
        raise ValueError("輸入不是可辨識的未壓縮 ARM64 Image")
    result["kind"] = "kernel"
    result["image_sha256"] = hashlib.sha256(image).hexdigest()
    result["image_size"] = len(image)
    releases = sorted(set(x.decode("ascii") for x in re.findall(rb"Linux version ([^\s\x00]+)", image)))
    if len(releases) != 1:
        raise ValueError(f"無法唯一辨識核心版本：{releases}")
    result["release"] = releases[0]
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)-(android\d+)-(\d+)(?:-|$)", releases[0])
    result["kmi"] = f"{match[1]}.{match[2]}-{match[4]}-{match[5]}" if match else None
    config = None
    offset = image.find(b"IKCFG_ST")
    if offset >= 0:
        config = zlib.decompress(image[offset + 8:], 31).decode("utf-8")
        options = dict(line.split("=", 1) for line in config.splitlines() if line.startswith("CONFIG_"))
        sizes = [size for key, size in (("CONFIG_ARM64_4K_PAGES", 4096),
                                      ("CONFIG_ARM64_16K_PAGES", 16384),
                                      ("CONFIG_ARM64_64K_PAGES", 65536)) if options.get(key) == "y"]
        result["page_size"] = sizes[0] if len(sizes) == 1 else None
        keys = ("CONFIG_MODVERSIONS", "CONFIG_CFI_CLANG", "CONFIG_MODULE_SIG",
                "CONFIG_MODULE_SIG_ALL", "CONFIG_MODULE_SIG_FORCE",
                "CONFIG_MODULE_SIG_PROTECT_LIST", "CONFIG_MODULE_SIG_PROTECT",
                "CONFIG_TRIM_UNUSED_KSYMS", "CONFIG_MODULE_FORCE_LOAD",
                "CONFIG_ANDROID_BINDER_IPC_RUST", "CONFIG_ZRAM", "CONFIG_ZSMALLOC", "CONFIG_KSU",
                "CONFIG_KSU_SUSFS", "CONFIG_KSU_MULTI_MANAGER_SUPPORT", "CONFIG_KALLSYMS_ALL",
                "CONFIG_KSU_DISABLE_MANAGER", "CONFIG_KSU_DISABLE_POLICY", "CONFIG_KSU_DEBUG",
                "CONFIG_KSU_TOOLKIT_SUPPORT", "CONFIG_TCP_CONG_BBR", "CONFIG_DEFAULT_TCP_CONG",
                "CONFIG_WQ_POWER_EFFICIENT_DEFAULT", "CONFIG_TMPFS_XATTR", "CONFIG_TMPFS_POSIX_ACL")
        result["config"] = {key: options.get(key, "n") for key in keys}
    return result, image, config


def inspect_path(path):
    path = Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names = [entry for entry in archive.infolist() if entry.filename == "Image"]
            if len(names) != 1 or names[0].file_size > MAX_IMAGE:
                raise ValueError("ZIP 必須包含唯一且大小合理的根目錄 Image")
            result, image, config = inspect(archive.read(names[0]))
            result["package_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            for name in ("version", "anykernel.sh"):
                if name in archive.namelist():
                    info = archive.getinfo(name)
                    if info.file_size > 65536:
                        raise ValueError("套件中繼資料過大")
                    text = archive.read(name).decode("utf-8", errors="replace")
                    if name == "version":
                        result["package_version"] = text.strip()
                    else:
                        match = re.search(r"^supported\.versions=(.*)$", text, re.M)
                        result["supported_android_versions"] = match[1].strip() if match else None
    else:
        result, image, config = inspect(path.read_bytes())
    result["file"] = path.name
    return result, image, config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--config-out", type=Path)
    parser.add_argument("--kernel-out", type=Path)
    args = parser.parse_args()
    result, image, config = inspect_path(args.input)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text)
    if args.config_out and config:
        args.config_out.write_text(config)
    if args.kernel_out and image:
        args.kernel_out.write_bytes(image)
    print(text, end="")


if __name__ == "__main__":
    main()
