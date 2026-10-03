# 原廠模組相容設定版的實際驗收

2026/10/2，[CI run 36955312429](https://github.com/jason5545/myron-gki-kernel/actions/runs/36955312429) 成功完成。核心建置使用專案 commit `762e693`，固定 ACK common `13ff069897df965d9039dca208b2f39dacf81957`，套用兩份 patch。後續只修改待機跳過的狀態、文件與檔案驗收工具；目前 main 的核心 patch SHA-256 與成功建置完全一致。

| 驗收項目 | 實際結果 |
| --- | --- |
| release | `6.12.23-android16-5-maybe-dirty-4k` |
| KMI／分頁 | `6.12-android16-5`／4096 bytes |
| Image 大小 | 40,413,696 bytes |
| Image SHA-256 | `06d41b575a6e67f8103cc1b0e4e1c512479b4e71b606996746f568d5a81f10f2` |
| `MODULE_SIG_PROTECT_LIST` | 空字串 |
| `MODULE_SIG_PROTECT`／`TRIM_UNUSED_KSYMS` | n／n |
| MODVERSIONS／CFI／模組簽章驗證／自動簽章 | y／y／y／y |
| 強制簽章／強制載入模組 | n／n |
| 原廠模組核心 CRC | 4015 個通過 |
| 缺少匯出／CRC 不符 | 0／0 |
| Binder Rust／zram／zsmalloc | 維持 m／m／m |
| KernelSU | 核心未內建；既有 LKM 的實際載入仍待驗證 |
| 待機調校 | 依 Jason 指示跳過 |

Image、vmlinux.symvers、System.map 下載後全部重新核對 CI 的 SHA-256，並在本機重跑設定與 CRC 驗收。資料保存於 `baseline/build-stock-modules-v2/`。

## 候選套件

AnyKernel3 ZIP：`out/packages/myron-kmi5-06d41b575a6e-AnyKernel3.zip`，17,522,296 bytes，SHA-256 `fdec9e5e22619fce5bb13b09ffae5da133178bf69eba37a996a01d19d78a4122`。

此 ZIP 在本機依最新的待機跳過政策重新產生。實際檢查 ZIP 的 CRC、Image SHA 與內嵌 manifest 均通過；只包含 Image、官方 ARM64 工具、安裝腳本、LICENSE 與 manifest，沒有 `.ko`、分割區 `.img` 或 DTB。安裝時讀取當前 boot 再封裝，保留原廠驅動。

CI 建置時的 ZIP 是較早的政策狀態快照；它也沒有實作待機功能。本機上述 ZIP 的 manifest 已明確記錄 `skipped_by_user`，核心 Image 與 CI 相同。

## 原廠 boot 重封裝

已執行 `scripts/repack_check.py`，只在手機 `/data/local/tmp/myron-kernel-repack-check/06d41b575a6e` 操作暫存檔案，以官方 ARM64 magiskboot 重新封裝原廠 boot 備份與新 Image。

- boot v4、ramdisk 0、OS version 0、signature size 0 均保留。
- 4096-byte 標頭僅修改 kernel_size；核心內容與候選 Image 完全一致。
- 封裝檔保留原廠 100,663,296-byte 分割區大小，已取回本機 `out/repack-run11/boot-from-stock.img`。
- 手機 boot_a 前後 SHA-256 同為 `e4a6fea84769a450c26550f07ca4dc2967f03541f2a6716ad995065f1fa7a19d`。

重封裝結果 SHA、完整候選資訊與驗收狀態在 `baseline/build-stock-modules-v2/repack-check.json`。程式、安裝前檢查與封裝檔案驗收的 14 項測試通過。

本次沒有刷入或重新啟動手機。以上證明編譯、設定、CRC 與封裝檔案通過驗收；原廠模組實際載入、CFI callback、KernelSU LKM、硬體功能與實機開機仍須另驗。
