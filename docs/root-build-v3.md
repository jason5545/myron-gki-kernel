# ReSukiSU／SUSFS 內建版的實際驗收

2026/10/2，[CI run 36965637116](https://github.com/jason5545/myron-gki-kernel/actions/runs/36965637116) 成功完成。核心建置與 CI 封裝都使用專案 commit `7868bf2`，固定 ACK common `13ff069897df965d9039dca208b2f39dacf81957`，套用四份 patch：沿用 v2 的 Rust Binder 符號保留與原廠模組相容設定，加上 `0003-susfs-v2.3.0-android16-6.12.patch` 與 `0004-integrate-pinned-resukisu-susfs.patch`。

| 驗收項目 | 實際結果 |
| --- | --- |
| release | `6.12.23-android16-5-maybe-dirty-4k` |
| KMI／分頁 | `6.12-android16-5`／4096 bytes |
| Image 大小 | 40,614,400 bytes |
| Image SHA-256 | `6c5d676bbab21995bc0056e36c2572efe9499ef3940025ca89cd29d39be7839b` |
| `KSU`／`KSU_SUSFS`／`KSU_MULTI_MANAGER_SUPPORT` | y／y／y |
| `KSU_DISABLE_MANAGER`／`KSU_DISABLE_POLICY`／`KSU_DEBUG` | n／n／n |
| Image 內的 root 標記 | `v4.2.0-rc3-239e1e88@ReSukiSU` |
| Image 內的 SUSFS 標記 | `susfs is initialized! version: v2.3.0` |
| `MODULE_SIG_PROTECT_LIST` | 空字串 |
| `MODULE_SIG_PROTECT`／`TRIM_UNUSED_KSYMS` | n／n |
| MODVERSIONS／CFI／模組簽章驗證／自動簽章 | y／y／y／y |
| 強制簽章／強制載入模組 | n／n |
| 原廠模組核心 CRC | 4015 個通過 |
| 缺少匯出／CRC 不符 | 0／0 |
| Binder Rust／zram／zsmalloc | 維持 m／m／m |
| 待機調校 | 依 Jason 指示跳過 |

Image、vmlinux.symvers、System.map 下載後全部重新核對 CI 的 SHA-256，並在本機重跑 `validate.py --image`、`prepare_root.py` 與 CRC 驗收；本機 `inspect_kernel.py` 的結果與 CI 的 `candidate-image.json` 完全一致。17 項測試通過。資料保存於 `baseline/build-root-v3/`。

root 標記中的 `239e1e88` 對應固定的 ReSukiSU `v4.2.0-rc3` 提交；LK v1.3 的標記是 `v4.1.0-0b4f56fd@Lunar612`。UAPI 4 是編譯期常數，Image 裡沒有可直接讀出的字串，依據是固定提交的原始碼與 `root-source.json`；實際 UAPI 要等開機後由管理器確認。

## 候選套件

AnyKernel3 ZIP：`out/baseline-run16/packages/myron-kmi5-6c5d676bbab2-AnyKernel3.zip`，17,628,115 bytes，SHA-256 `7ee207862f69a669acb5076b0f6c4992b0f6f69fa767bbd4303f3d6fc12df67d`。

這次 CI 建置與封裝使用同一個 commit，直接採用 CI 產生的 ZIP，不在本機重新封裝。內嵌 manifest 的 `project_commit` 為 `7868bf2`，ZIP 內 Image 的 SHA 與上表相同。內容只有 Image、官方 ARM64 工具、安裝腳本、LICENSE 與 manifest，沒有 `.ko`、分割區 `.img` 或 DTB。

安裝腳本在寫 boot 前會讀取同 slot 的 init_boot，只接受已核對的原廠 init_boot（SHA-256 `a4ed45c0af246068212b899a3f7e003b396d45b77af59b7f37acca0495ffe4b3`）。目前手機的 init_boot 仍會載入舊 KernelSU LKM，直接安裝會在寫入前停止；需先依 [init_boot 遷移](resukisu-susfs-fixed.md#init_boot-遷移) 換回 `out/root-migration/init_boot-stock.img`。

## 原廠 boot 重封裝

已執行 `scripts/repack_check.py`，只在手機 `/data/local/tmp/myron-kernel-repack-check/6c5d676bbab2` 操作暫存檔案，以官方 ARM64 magiskboot 重新封裝原廠 boot 備份與新 Image。

- boot v4、ramdisk 0、page size 4096 均保留。
- 4096-byte 標頭僅修改 kernel_size；核心內容與候選 Image 完全一致。
- 封裝檔保留原廠 100,663,296-byte 分割區大小，SHA-256 `4e931383e39966b200caf6732fc1600295b5bb0498d7d51ad89e5e952a3e48be`，已取回本機 `out/repack-run16/boot-from-stock.img`。
- 手機 boot_a 前後 SHA-256 同為 `e4a6fea84769a450c26550f07ca4dc2967f03541f2a6716ad995065f1fa7a19d`。

完整結果在 `baseline/build-root-v3/repack-check.json`。

本次沒有刷入、遷移 init_boot、安裝管理器或重新啟動手機。以上證明編譯、設定、root 來源、CRC 與封裝檔案通過驗收；實機開機、原廠模組實際載入、CFI callback、ReSukiSU 管理器辨識與 UAPI、SUSFS 功能仍須另驗。
