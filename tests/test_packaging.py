"""驗證誤用舊設定、ABI 不符與錯誤 boot 不會進入封裝或寫入。"""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from package_kernel import create_package, vendor_files
from repack_check import check_repacked
from validate import check_image


class PackageChecks(unittest.TestCase):
    def test_previous_image_policy_is_rejected(self):
        previous = json.loads((ROOT / "baseline/build-kmi5-v1/candidate-image.json").read_text())
        lock = json.loads((ROOT / "source.lock.json").read_text())
        policy = json.loads((ROOT / "config/kernel-policy.json").read_text())
        errors = check_image(previous, lock, policy)
        self.assertTrue(any("MODULE_SIG_PROTECT" in item for item in errors))

    def test_pinned_tools_are_arm64(self):
        _, paths = vendor_files()
        self.assertIn("LICENSE", paths)
        for name in ("tools/magiskboot", "tools/busybox"):
            data = paths[name].read_bytes()
            self.assertEqual(struct.unpack_from("<H", data, 18)[0], 183)

    def test_crc_failure_stops_package_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "rejected.zip"
            with patch("package_kernel.inspect_path", return_value=({}, b"", "")), \
                    patch("package_kernel.check_image", return_value=[]), \
                    patch("package_kernel.compare", return_value={"compatible": False}):
                with self.assertRaisesRegex(ValueError, "CRC"):
                    create_package(Path("unused"), Path("unused"), Path("unused"), Path("unused"), out)
            self.assertFalse(out.exists())

    def test_repack_rejects_changed_header_or_kernel(self):
        original = bytearray(8192)
        original[:8] = b"ANDROID!"
        struct.pack_into("<I", original, 40, 4)
        kernel = b"test-kernel"
        candidate = bytearray(original)
        struct.pack_into("<I", candidate, 8, len(kernel))
        candidate[4096:4096 + len(kernel)] = kernel
        check_repacked(original, candidate, kernel)
        candidate[44] = 1
        with self.assertRaisesRegex(ValueError, "標頭"):
            check_repacked(original, candidate, kernel)
        candidate[44] = 0
        candidate[4096] ^= 1
        with self.assertRaisesRegex(ValueError, "核心"):
            check_repacked(original, candidate, kernel)

    def run_installer(self, release, header=4, dtb=False, init_sha="a4ed45c0af246068212b899a3f7e003b396d45b77af59b7f37acca0495ffe4b3"):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tools = root / "tools"
            tools.mkdir()
            split = root / "split_img"
            split.mkdir()
            boot = bytearray(4096)
            boot[:8] = b"ANDROID!"
            struct.pack_into("<I", boot, 40, header)
            (root / "boot.img").write_bytes(boot)
            (root / "init_boot_a").write_bytes(b"fixture")
            (split / "kernel").write_text(f"Linux version {release} test compiler #1\n")
            if dtb:
                (split / "kernel_dtb").write_bytes(b"test-dtb")
            # 使用假的 core；測試不載入第三方腳本，也沒有手機或分割區操作。
            (tools / "ak3-core.sh").write_text(
                'BOOTIMG="$PWD/boot.img"\nSPLITIMG="$PWD/split_img"\n'
                'BLOCK="$PWD/boot_a"\nSLOT=_a\n'
                'split_boot() { :; }\nabort() { echo "$*" >&2; exit 1; }\n'
                'ui_print() { :; }\nflash_boot() { echo flashed > "$PWD/marker"; }\n'
                f'sha256sum() {{ printf "%s  %s\\n" "{init_sha}" "$1"; }}\n'
            )
            result = subprocess.run(["sh", str(ROOT / "packaging/anykernel.sh")], cwd=root, capture_output=True, text=True, env=os.environ.copy())
            return result.returncode, (root / "marker").exists()

    def test_correct_boot_reaches_repack(self):
        self.assertEqual(self.run_installer("6.12.23-android16-5-stock-4k"), (0, True))

    def test_310_stock_init_boot_reaches_repack(self):
        sha = "0a9871f49b19840af13485feea6baa37ea0db4beffedc057f020bccc6b93e550"
        self.assertEqual(self.run_installer("6.12.38-android16-5-g4b4d49350df7-4k", init_sha=sha), (0, True))

    def test_old_lkm_or_unknown_init_boot_never_flashes(self):
        for sha in ("5dee4a6da2e6c6718ccec7c6570ff90371a94468103a54fc53a37fa629406f7f", "0" * 64):
            code, wrote = self.run_installer("6.12.23-android16-5-stock-4k", init_sha=sha)
            self.assertNotEqual(code, 0)
            self.assertFalse(wrote)

    def test_wrong_kmi_header_or_appended_dtb_never_flashes(self):
        for release, header, dtb in [
            ("6.12.69-android16-6-stock-4k", 4, False),
            ("6.12.23-android16-5-stock-16k", 4, False),
            ("6.12.23-android16-5-stock-4k", 3, False),
            ("6.12.23-android16-5-stock-4k", 4, True),
        ]:
            with self.subTest(release=release, header=header, dtb=dtb):
                code, wrote = self.run_installer(release, header, dtb)
                self.assertNotEqual(code, 0)
                self.assertFalse(wrote)


if __name__ == "__main__":
    unittest.main()
