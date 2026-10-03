#!/usr/bin/env python3
"""讀取 ARM64 ELF 模組的匯入符號 CRC，與編譯產物的 vmlinux.symvers 比對。"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct
import tarfile


def cstring(data, offset):
    if offset < 0 or offset >= len(data):
        raise ValueError("ELF 字串偏移超出範圍")
    end = data.find(b"\0", offset)
    if end < 0:
        raise ValueError("ELF 字串未結束")
    return data[offset:end].decode("ascii")


def parse_module(data):
    if len(data) < 64 or data[:6] != b"\x7fELF\x02\x01":
        raise ValueError("模組不是 little-endian ELF64")
    if struct.unpack_from("<H", data, 18)[0] != 183:
        raise ValueError("模組不是 ARM64")
    shoff = struct.unpack_from("<Q", data, 40)[0]
    shsize, shnum, shstr = struct.unpack_from("<3H", data, 58)
    if shsize != 64 or not 0 < shnum < 4096 or shstr >= shnum or shoff + shsize * shnum > len(data):
        raise ValueError("ELF section table 無效")
    headers = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * shsize) for i in range(shnum)]

    def section(index):
        h = headers[index]
        if h[4] + h[5] > len(data):
            raise ValueError("ELF section 資料不完整")
        return data[h[4]:h[4] + h[5]]

    strings = section(shstr)
    named = {cstring(strings, h[0]): i for i, h in enumerate(headers)}
    versions = {}
    if "__versions" in named:
        raw = section(named["__versions"])
        if len(raw) % 64:
            raise ValueError("__versions 記錄大小不符")
        for offset in range(0, len(raw), 64):
            crc = struct.unpack_from("<Q", raw, offset)[0]
            name = cstring(raw[offset + 8:offset + 64], 0)
            if name:
                versions[name] = f"0x{crc:08x}"
    exports = set()
    undefined = set()
    for index, h in enumerate(headers):
        if h[1] != 2:
            continue
        if h[6] >= shnum or h[9] != 24:
            raise ValueError("ELF symbol table 無效")
        raw, names = section(index), section(h[6])
        if len(raw) % 24:
            raise ValueError("ELF symbol table 長度不符")
        for offset in range(0, len(raw), 24):
            name_offset, binding, _, section_index, _, _ = struct.unpack_from("<IBBHQQ", raw, offset)
            name = cstring(names, name_offset)
            if name and section_index == 0 and binding >> 4 == 1:
                undefined.add(name)
            if name.startswith("__ksymtab_"):
                exports.add(name[len("__ksymtab_"):])
    modinfo = section(named[".modinfo"]) if ".modinfo" in named else b""
    info = dict(item.decode("utf-8", errors="replace").split("=", 1)
                for item in modinfo.split(b"\0") if b"=" in item)
    if ".note.gnu.build-id" in named:
        info["note_sha256"] = hashlib.sha256(section(named[".note.gnu.build-id"])).hexdigest()
    info["unversioned_imports"] = sorted(undefined - set(versions))
    return versions, exports, info


def inventory(archives, loaded=None):
    modules, requirements, providers = [], defaultdict(lambda: defaultdict(list)), defaultdict(list)
    found = set()
    identities = set()
    unversioned = defaultdict(list)
    for path in archives:
        with tarfile.open(path, "r:gz") as archive:
            for member in archive.getmembers():
                if not member.isfile() or not member.name.endswith(".ko"):
                    continue
                handle = archive.extractfile(member)
                if handle is None:
                    raise ValueError("無法讀取模組")
                data = handle.read()
                versions, exports, info = parse_module(data)
                module_name = info.get("name", Path(member.name).stem.replace("-", "_"))
                if loaded is not None:
                    if module_name not in loaded:
                        continue
                    if loaded[module_name] is not None and info.get("note_sha256") != loaded[module_name]:
                        continue
                    found.add(module_name)
                identity = (module_name, info.get("note_sha256") or hashlib.sha256(data).hexdigest())
                if identity in identities:
                    continue
                identities.add(identity)
                label = f"{Path(path).stem}:{member.name}"
                modules.append({"name": label, "sha256": hashlib.sha256(data).hexdigest(),
                                "vermagic": info.get("vermagic"), "imports": len(versions),
                                "exports": len(exports), "module_name": module_name,
                                "note_sha256": info.get("note_sha256"),
                                "runtime_identity_verified": loaded is not None and loaded.get(module_name) is not None,
                                "unversioned_imports": info["unversioned_imports"]})
                for name, crc in versions.items():
                    requirements[name][crc].append(label)
                for name in exports:
                    providers[name].append(label)
                for name in info["unversioned_imports"]:
                    unversioned[name].append(label)
    conflicts = {name: crcs for name, crcs in requirements.items() if len(crcs) > 1}
    if conflicts:
        raise ValueError(f"原廠模組有互相衝突的 CRC：{list(conflicts)[:20]}")
    symbols = {name: {"crc": next(iter(crcs)), "modules": next(iter(crcs.values())),
                      "prebuilt_providers": sorted(providers.get(name, []))}
               for name, crcs in sorted(requirements.items())}
    return {"schema": 1, "modules": sorted(modules, key=lambda m: m["name"]), "symbols": symbols,
            "module_count": len(modules), "symbol_count": len(symbols),
            "unmatched_loaded_modules": sorted(set(loaded or {}) - found),
            "unversioned_symbols": {name: {"modules": labels,
                                           "prebuilt_providers": sorted(providers.get(name, []))}
                                    for name, labels in sorted(unversioned.items())},
            "kernel_symbol_count": sum(not s["prebuilt_providers"] for s in symbols.values())}


def exempted(modules, exceptions):
    """符號只被列入例外的模組使用時才放行；還有其他模組使用就照樣算失敗。"""
    names = {Path(label.split(":", 1)[-1]).name for label in modules}
    return bool(names) and names <= set(exceptions)


def compare(required, symvers, system_map=None, exceptions=None):
    exceptions = exceptions or {}
    actual = {}
    for line in Path(symvers).read_text().splitlines():
        columns = line.split()
        if len(columns) >= 2:
            actual[columns[1]] = f"0x{int(columns[0], 16):08x}"
    missing, mismatched = [], []
    for name, info in required["symbols"].items():
        # 由既有模組提供的符號仍保留原模組；這一步只驗收核心本體。
        if info["prebuilt_providers"]:
            continue
        if name not in actual:
            missing.append({"symbol": name, "expected": info["crc"], "modules": info["modules"]})
        elif actual[name] != info["crc"]:
            mismatched.append({"symbol": name, "expected": info["crc"], "actual": actual[name],
                               "modules": info["modules"]})
    symbols_in_map = set()
    if system_map:
        symbols_in_map = {line.split()[2] for line in Path(system_map).read_text().splitlines()
                          if len(line.split()) >= 3}
    unversioned = required.get("unversioned_symbols", {})
    unversioned_missing = [name for name, info in unversioned.items()
                          if not info["prebuilt_providers"] and name not in actual and name not in symbols_in_map]
    excepted = ([dict(item, kind="missing") for item in missing if exempted(item["modules"], exceptions)]
                + [dict(item, kind="mismatched") for item in mismatched if exempted(item["modules"], exceptions)]
                + [{"symbol": name, "kind": "unversioned_missing", "modules": unversioned[name]["modules"]}
                   for name in unversioned_missing if exempted(unversioned[name]["modules"], exceptions)])
    missing = [item for item in missing if not exempted(item["modules"], exceptions)]
    mismatched = [item for item in mismatched if not exempted(item["modules"], exceptions)]
    unversioned_missing = [name for name in unversioned_missing
                           if not exempted(unversioned[name]["modules"], exceptions)]
    return {"compatible": not missing and not mismatched,
            "scope": "核心匯出符號 CRC；不代表模組簽章、CFI 或實機開機已通過",
            "unversioned_symbols": len(unversioned),
            "unversioned_missing": unversioned_missing,
            "root_runtime_validation_required": True,
            "checked": required["kernel_symbol_count"], "missing": missing, "mismatched": mismatched,
            "exceptions": exceptions, "excepted": excepted}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory")
    inv.add_argument("archives", nargs="+", type=Path)
    inv.add_argument("--output", required=True, type=Path)
    inv.add_argument("--loaded", type=Path, help="實際載入模組的 note SHA-256 JSON")
    check = sub.add_parser("check")
    check.add_argument("--required", required=True, type=Path)
    check.add_argument("--symvers", required=True, type=Path)
    check.add_argument("--system-map", type=Path)
    check.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "inventory":
        loaded = json.loads(args.loaded.read_text()) if args.loaded else None
        result = inventory(args.archives, loaded)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({k: result[k] for k in ("module_count", "symbol_count", "kernel_symbol_count", "unmatched_loaded_modules")}, ensure_ascii=False))
    else:
        policy = json.loads((Path(__file__).resolve().parents[1] / "config/kernel-policy.json").read_text())
        result = compare(json.loads(args.required.read_text()), args.symvers, args.system_map,
                         policy.get("abi_exceptions"))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({k: result[k] for k in ("compatible", "checked", "scope")}, ensure_ascii=False))
        print(f"缺少符號：{len(result['missing'])}；CRC 不符：{len(result['mismatched'])}")
        if result["excepted"]:
            kinds = defaultdict(int)
            for item in result["excepted"]:
                kinds[item["kind"]] += 1
            print(f"例外模組 {'、'.join(result['exceptions'])}：" + "、".join(f"{k} {v}" for k, v in kinds.items()))
        raise SystemExit(0 if result["compatible"] else 1)


if __name__ == "__main__":
    main()
