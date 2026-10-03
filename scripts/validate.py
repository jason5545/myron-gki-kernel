#!/usr/bin/env python3
"""固定來源、映像與實機基準之間的版本驗收。"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from inspect_kernel import inspect_path


def check_image(result, lock, policy=None):
    errors = []
    if result.get("kind") != "kernel":
        errors.append("映像沒有核心")
    if result.get("kmi") != lock["kmi"]:
        errors.append(f"KMI 不符：{result.get('kmi')}，預期 {lock['kmi']}")
    if result.get("page_size") != lock["page_size"]:
        errors.append("頁面大小不符或沒有可辨識的 IKCONFIG")
    for key in ("CONFIG_MODVERSIONS", "CONFIG_CFI_CLANG"):
        if result.get("config", {}).get(key) != "y":
            errors.append(f"必要設定未啟用：{key}")
    if policy:
        for key, expected in policy["required"].items():
            actual = result.get("config", {}).get(key)
            if actual != expected:
                errors.append(f"相容設定不符：{key}={actual}，預期 {expected}")
    return errors


def check_repository():
    lock = json.loads((ROOT / "source.lock.json").read_text())
    manifest = ET.parse(ROOT / "manifests/default.xml").getroot()
    projects = manifest.findall("project")
    if any(not re.fullmatch(r"[0-9a-f]{40}", p.get("revision", "")) for p in projects):
        raise ValueError("manifest 有浮動版本")
    common = next(p for p in projects if p.get("path") == "common")
    if common.get("revision") != lock["common_commit"]:
        raise ValueError("common 版本與 lock 不符")
    selected = ET.parse(ROOT / "manifests/gki.xml").getroot().findall("project")
    full = {p.get("path"): p.get("revision") for p in projects}
    if any(full.get(p.get("path")) != p.get("revision") for p in selected):
        raise ValueError("純 GKI manifest 與官方完整 snapshot 不符")
    if any(child.get("dest") == "WORKSPACE.bzlmod" for p in selected for child in p.findall("linkfile")):
        raise ValueError("純 GKI workspace 不應連結舊 GBL 依賴")
    stock = json.loads((ROOT / "baseline/stock-image.json").read_text())
    if errors := check_image(stock, lock):
        raise ValueError("原廠基準與候選規則衝突：" + "；".join(errors))
    required = json.loads((ROOT / "baseline/module-requirements.json").read_text())
    if required["unmatched_loaded_modules"]:
        raise ValueError("實機載入模組尚未完整收集")
    if not required["kernel_symbol_count"] or not required["module_count"]:
        raise ValueError("模組基準為空")
    print(f"官方來源固定：{len(projects)} 個；GKI 同步：{len(selected)} 個；實機模組：{required['module_count']}；核心 CRC：{required['kernel_symbol_count']}")
    return lock


def check_source(workspace, lock):
    common = workspace / "common"
    commit = subprocess.check_output(["git", "-C", str(common), "rev-parse", "HEAD"], text=True).strip()
    if commit != lock["common_commit"]:
        raise ValueError("同步後的 common commit 不符")
    makefile = (common / "Makefile").read_text()
    version = ".".join(re.search(rf"^{field}\s*=\s*(\d+)", makefile, re.M)[1]
                       for field in ("VERSION", "PATCHLEVEL", "SUBLEVEL"))
    constants = dict(line.split("=", 1) for line in (common / "build.config.constants").read_text().splitlines() if "=" in line)
    if version != lock["kernel_version"] or constants.get("KMI_GENERATION") != str(lock["kmi_generation"]):
        raise ValueError("原始碼的 Linux 版本或 KMI 世代不符")
    if constants.get("CLANG_VERSION") != lock["clang_version"]:
        raise ValueError("原始碼指定的 Clang 與 lock 不符")
    print(f"原始碼驗收通過：{version}／KMI {constants['KMI_GENERATION']}／{constants['CLANG_VERSION']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--image", type=Path)
    args = parser.parse_args()
    lock = check_repository()
    if args.source:
        check_source(args.source, lock)
    if args.image:
        result, _, _ = inspect_path(args.image)
        policy = json.loads((ROOT / "config/kernel-policy.json").read_text())
        if errors := check_image(result, lock, policy):
            raise ValueError("；".join(errors))
        print(f"映像版本驗收通過：{result['release']}")


if __name__ == "__main__":
    main()
