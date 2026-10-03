#!/usr/bin/env python3
"""從已保留的 vendor_boot／init_boot 讀出模組，不解開其他個人資料。"""
import argparse
import gzip
import io
from pathlib import Path
import stat
import struct
import subprocess
import tarfile


def align(number, size):
    return (number + size - 1) // size * size


def ramdisks(data):
    if data.startswith(b"VNDRBOOT"):
        if len(data) < 2128:
            raise ValueError("vendor_boot 標頭不完整")
        version, page = struct.unpack_from("<2I", data, 8)
        if version != 4 or page != 4096:
            raise ValueError("預期 vendor_boot v4／4096-byte 對齊")
        size = struct.unpack_from("<I", data, 24)[0]
        header, dtb_size = struct.unpack_from("<2I", data, 2096)
        table_size, entries, entry_size = struct.unpack_from("<3I", data, 2112)
        start = align(header, page)
        table = start + align(size, page) + align(dtb_size, page)
        if entry_size < 108 or entries * entry_size != table_size or table + table_size > len(data):
            raise ValueError("vendor ramdisk table 無效")
        for index in range(entries):
            length, offset, kind = struct.unpack_from("<3I", data, table + index * entry_size)
            if offset + length > size:
                raise ValueError("vendor ramdisk 超出範圍")
            yield f"vendor-{index}-{kind}", data[start + offset:start + offset + length]
    elif data.startswith(b"ANDROID!"):
        version = struct.unpack_from("<I", data, 40)[0]
        if version not in (3, 4):
            raise ValueError("預期 boot header v3／v4")
        kernel_size, size = struct.unpack_from("<2I", data, 8)
        start = 4096 + align(kernel_size, 4096)
        if start + size > len(data):
            raise ValueError("init_boot ramdisk 不完整")
        yield "init", data[start:start + size]
    else:
        raise ValueError("無法辨識開機映像")


def cpio_members(raw):
    position = 0
    while position + 110 <= len(raw):
        header = raw[position:position + 110]
        if header[:6] not in (b"070701", b"070702"):
            raise ValueError("不支援的 cpio 格式")
        fields = [int(header[6 + i * 8:14 + i * 8], 16) for i in range(13)]
        mode, length, namesize = fields[1], fields[6], fields[11]
        name_start = position + 110
        name_end = name_start + namesize
        body = align(name_end, 4)
        end = body + length
        if namesize < 1 or end > len(raw) or raw[name_end - 1] != 0:
            raise ValueError("cpio 記錄不完整")
        name = raw[name_start:name_end - 1].decode("utf-8")
        if name == "TRAILER!!!":
            return
        if stat.S_ISREG(mode) and name.endswith(".ko"):
            yield name, raw[body:end]
        position = align(end, 4)
    raise ValueError("cpio 缺少結束記錄")


def extract(paths, output):
    count = 0
    with tarfile.open(output, "w:gz") as target:
        for path in paths:
            for label, raw in ramdisks(Path(path).read_bytes()):
                if not raw:
                    continue
                if raw.startswith(b"\x1f\x8b"):
                    raw = gzip.decompress(raw)
                elif raw[:4] in (b"\x02\x21\x4c\x18", b"\x04\x22\x4d\x18"):
                    raw = subprocess.run(["lz4", "-dc"], input=raw, capture_output=True, check=True).stdout
                for name, data in cpio_members(raw):
                    relative = Path(name)
                    if relative.is_absolute() or ".." in relative.parts:
                        raise ValueError("模組路徑不安全")
                    info = tarfile.TarInfo(f"{label}/{relative.as_posix()}")
                    info.size, info.mode = len(data), 0o644
                    target.addfile(info, io.BytesIO(data))
                    count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(f"讀出模組：{extract(args.inputs, args.output)}")


if __name__ == "__main__":
    main()
