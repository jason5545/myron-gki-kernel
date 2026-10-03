import gzip
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from inspect_kernel import inspect, inspect_path
from module_abi import collisions, compare, parse_module
from validate import check_image


def image(release="6.12.23-android16-5-test", pages="4K"):
    header = bytearray(64)
    header[56:60] = b"ARM\x64"
    config = f"CONFIG_ARM64_{pages}_PAGES=y\nCONFIG_MODVERSIONS=y\nCONFIG_CFI_CLANG=y\n"
    return bytes(header) + f"Linux version {release}\0".encode() + b"IKCFG_ST" + gzip.compress(config.encode()) + b"IKCFG_ED"


class KernelChecks(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads((ROOT / "source.lock.json").read_text())

    def test_same_kmi_allows_new_sublevel(self):
        result, _, _ = inspect(image("6.12.69-android16-5-test"))
        self.assertEqual(check_image(result, self.lock), [])

    def test_generation_change_is_rejected(self):
        result, _, _ = inspect(image("6.12.69-android16-6-test"))
        self.assertTrue(any("KMI" in error for error in check_image(result, self.lock)))

    def test_wrong_page_size_is_rejected(self):
        result, _, _ = inspect(image(pages="16K"))
        self.assertTrue(check_image(result, self.lock))

    def test_init_boot_is_not_a_kernel(self):
        data = bytearray(4096)
        data[:8] = b"ANDROID!"
        struct.pack_into("<I", data, 20, 1584)
        struct.pack_into("<I", data, 40, 4)
        result, raw, _ = inspect(bytes(data))
        self.assertEqual(result["kind"], "init_boot")
        self.assertIsNone(raw)
        self.assertTrue(check_image(result, self.lock))

    def test_truncated_boot_is_rejected(self):
        data = bytearray(4096)
        data[:8] = b"ANDROID!"
        struct.pack_into("<I", data, 8, 100)
        struct.pack_into("<I", data, 20, 1584)
        struct.pack_into("<I", data, 40, 4)
        with self.assertRaises(ValueError):
            inspect(bytes(data))

    def test_zip_scripts_are_not_executed(self):
        with tempfile.TemporaryDirectory() as folder:
            path, marker = Path(folder) / "kernel.zip", Path(folder) / "marker"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("Image", image())
                archive.writestr("anykernel.sh", f"touch '{marker}'\nsupported.versions=17\n")
            result, _, _ = inspect_path(path)
            self.assertFalse(marker.exists())
            self.assertEqual(result["supported_android_versions"], "17")

    def test_invalid_elf_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_module(b"\x7fELF" + b"\0" * 100)

    def test_real_crc_mismatch_and_missing_symbol_are_detected(self):
        baseline = json.loads((ROOT / "baseline/module-requirements.json").read_text())
        imports = [(name, value) for name, value in baseline["symbols"].items() if not value["prebuilt_providers"]][:3]
        required = {"symbols": dict(imports), "kernel_symbol_count": len(imports)}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "vmlinux.symvers"
            path.write_text("".join(f"{info['crc']}\t{name}\tvmlinux\tEXPORT_SYMBOL\n" for name, info in imports))
            self.assertTrue(compare(required, path)["compatible"])
            first, info = imports[0]
            path.write_text(path.read_text().replace(info["crc"], f"0x{int(info['crc'], 16) ^ 1:08x}", 1))
            result = compare(required, path)
            self.assertFalse(result["compatible"])
            self.assertEqual(result["mismatched"][0]["symbol"], first)
            path.write_text("")
            self.assertEqual(len(compare(required, path)["missing"]), 3)

    def test_abi_exception_only_covers_symbols_used_by_exempt_modules(self):
        required = {"kernel_symbol_count": 2, "symbols": {
            "only_rust": {"crc": "0x00000001", "modules": ["system-modules.tar:./rust_binder.ko"], "prebuilt_providers": []},
            "shared": {"crc": "0x00000002", "modules": ["system-modules.tar:./rust_binder.ko", "vendor-modules.tar:./qcom.ko"], "prebuilt_providers": []}}}
        exceptions = {"rust_binder.ko": "測試"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "vmlinux.symvers"
            path.write_text("0x00000009\tonly_rust\tvmlinux\tEXPORT_SYMBOL\n0x00000002\tshared\tvmlinux\tEXPORT_SYMBOL\n")
            result = compare(required, path, exceptions=exceptions)
            self.assertTrue(result["compatible"])
            self.assertEqual([item["symbol"] for item in result["excepted"]], ["only_rust"])
            path.write_text("0x00000001\tonly_rust\tvmlinux\tEXPORT_SYMBOL\n0x00000009\tshared\tvmlinux\tEXPORT_SYMBOL\n")
            result = compare(required, path, exceptions=exceptions)
            self.assertFalse(result["compatible"])
            self.assertEqual(result["mismatched"][0]["symbol"], "shared")

    def test_builtin_or_export_named_like_stock_module_is_rejected(self):
        # v17 把 cpq、kshrink_slabd 編進 Image；原廠 first stage 的 cpq.ko 會因 -EBUSY 載入失敗。
        baseline = json.loads((ROOT / "baseline/module-requirements.json").read_text())
        allowed = json.loads((ROOT / "config/kernel-policy.json").read_text())["collision_exceptions"]
        stock_export = next(iter(baseline["exports"]))
        with tempfile.TemporaryDirectory() as folder:
            builtin = Path(folder) / "modules.builtin"
            builtin.write_text("kernel/drivers/kernelsu/kernelsu.ko\nkernel/fs/ext4/ext4.ko\n")
            collided, excepted = collisions(baseline, set(), builtin, allowed)
            self.assertEqual(collided, [])
            self.assertEqual([item["name"] for item in excepted], ["kernelsu"])
            builtin.write_text(builtin.read_text() + "kernel/block/cpq.ko\nkernel/mm/kshrink_slabd.ko\n")
            collided, _ = collisions(baseline, {stock_export}, builtin, allowed)
            self.assertEqual([(item["kind"], item["name"]) for item in collided],
                             [("module", "cpq"), ("module", "kshrink_slabd"), ("export", stock_export)])

    def test_collision_fails_compare(self):
        required = {"kernel_symbol_count": 0, "symbols": {}, "exports": {"stock_fn": ["vendor-modules.tar:./qcom.ko"]},
                    "modules": [{"module_name": "cpq", "name": "ramdisk-modules.tar:vendor-0-1/lib/modules/cpq.ko"}]}
        with tempfile.TemporaryDirectory() as folder:
            symvers, builtin = Path(folder) / "vmlinux.symvers", Path(folder) / "modules.builtin"
            symvers.write_text("")
            builtin.write_text("kernel/block/mq-deadline.ko\n")
            result = compare(required, symvers, builtin=builtin)
            self.assertTrue(result["compatible"])
            self.assertTrue(result["builtin_checked"])
            builtin.write_text("kernel/block/cpq.ko\n")
            self.assertFalse(compare(required, symvers, builtin=builtin)["compatible"])
            builtin.write_text("")
            symvers.write_text("0x00000001\tstock_fn\tvmlinux\tEXPORT_SYMBOL_GPL\n")
            self.assertEqual(compare(required, symvers, builtin=builtin)["collisions"][0]["name"], "stock_fn")


if __name__ == "__main__":
    unittest.main()
