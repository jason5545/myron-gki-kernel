# KMI 5 基底第一版

來源：Android 官方 `android16-6.12-2025-06`，common `13ff069897df965d9039dca208b2f39dacf81957`，Clang `r536225`。保持 Linux 6.12.23、Android 16 KMI 世代 5、4 KB 頁面、MODVERSIONS、CFI。

唯一相容 patch 是保留 `list_lru_add_obj`／`list_lru_del_obj`。固定來源已有實作與 GPL 匯出宣告，原廠 `rust_binder.ko` 需要它們；修正只加入小米 KMI 清單，避免裁剪。

## 實際驗收

| 項目 | 結果 |
| --- | --- |
| CI | run 36940172667 成功 |
| Image release | 6.12.23-android16-5-maybe-dirty-4k |
| Image bytes | 39954944 |
| Image SHA-256 | 0721b909ec6f287b176c8f15d9107d35ecec79aae26a4418e3572611fb64173f |
| 核心 CRC | 4015 個通過 |
| 缺少符號／CRC 不符 | 0／0 |
| unversioned imports 的符號存在性 | 沒有缺少；不代表布局與實機驗證 |
| 核心內建 KernelSU | 無；現有手機使用 LKM |
| MODULE_SIG_PROTECT | 仍啟用 |

可重現的 patch SHA、Image 資訊與完整 ABI 結果保存在 `baseline/build-kmi5-v1/`。來源與 patch 的 provenance 比 `maybe-dirty` 字串更精確；此字串尚未整理成最終發行版本名稱。

## 還沒完成的部分

新核心的簽章金鑰與原廠 protected GKI 模組不同，仍要決定配套新編模組或保留原廠模組的相容方案。一般 hardware vendor 模組的 CRC 已通過，CFI callback 與實際功能還要上機測試。KernelSU 的 LKM 沒有 CRC、runtime identity 也無法核對，另做載入與 root 驗證。

目前 CI 產物是候選基底。原廠 boot／vendor_boot／init_boot、完整模組和 SHA-256 已保留在本機 `local-backup/`；手機未寫入新核心。下一階段完成簽章與 root 配套後，再產生符合現有 boot v4 格式的測試映像。
