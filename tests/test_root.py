"""固定來源與 root 模式的必要驗收。"""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_root import verify_sources
from validate import check_image


class RootChecks(unittest.TestCase):
    def test_vendor_uapi_and_fixed_manager_match(self):
        lock = verify_sources()
        self.assertEqual(lock["resukisu"]["uapi_version"], lock["manager"]["uapi_version"])
        self.assertEqual(lock["resukisu"]["commit"], lock["manager"]["commit"])
        self.assertTrue(lock["init_boot_migration"]["stock_init_matches_init_real"])

    def test_previous_non_root_image_is_rejected(self):
        info = json.loads((ROOT / "baseline/build-stock-modules-v2/candidate-image.json").read_text())
        policy = json.loads((ROOT / "config/kernel-policy.json").read_text())
        source = json.loads((ROOT / "source.lock.json").read_text())
        errors = check_image(info, source, policy)
        self.assertTrue(any("CONFIG_KSU=" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
