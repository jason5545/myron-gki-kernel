# 原廠模組相容設定與 boot 封裝

Jason 指定加入 LK v1.3 的模組保護設定、完整匯出、沿用現有 boot 封裝，以及預設開啟待機調校。

## 核心設定

`0002-allow-stock-gki-modules-with-custom-kernel.patch` 僅修改 4 KB 的 `kernel_aarch64` Kleaf 目標：

- `protected_module_names_list = None`，使 `MODULE_SIG_PROTECT_LIST` 回到空字串，衍生 `MODULE_SIG_PROTECT=n`。
- `trim_nonlisted_kmi = False`，使 `TRIM_UNUSED_KSYMS=n`；依 ACK 同時停用未受信任模組的匯入允許清單限制。
- `kmi_symbol_list_strict_mode = False`，允許產物保留清單以外的匯出。`kmi_enforced=True` 保留，實機模組 CRC 驗收也繼續執行。

MODVERSIONS、CFI、模組簽章驗證與編譯時簽章維持啟用；不強制簽章、不強制忽略模組版本。Rust Binder、zram、zsmalloc 維持原廠模組配置。第一份符號保留 patch 保留於套用歷史；不裁切後，它不再是保留那兩個匯出的必要條件。

`config/kernel-policy.json` 定義驗收值，編譯後從實際 Image 擷取設定再核對。舊版保護與裁切仍啟用的 Image 不能被新封裝流程接受。

## AnyKernel3 套件

`scripts/package_kernel.py` 先驗證 KMI 5、4 KB、核心設定與現有原廠模組 CRC，再產生 `out/packages/myron-kmi5-<Image SHA 前 12 碼>-AnyKernel3.zip`。

官方 AnyKernel3 腳本固定於 `020dfeccf9d7e962a48400fc94d3e451df92eead`；ARM64 工具固定於 `f1a6f5ec47749252d30cc5e26f71f06b14cba617`。來源、每個檔案的 SHA-256 與 LICENSE 保存在 `packaging/`，工具架構也會核對。

安裝器檢查 myron、Android 16，讀取當前 slot 的 boot；從實際 boot 的核心讀取 release，要求 `6.12.*-android16-5-*-4k`，不採用可能偽裝的 uname。需要 boot v4，遇到附加 kernel DTB 時停止，避免混入來源不明的硬體 DTB。

安裝器透過官方 `split_boot`／`flash_boot` 直接沿用現有映像封裝。套件只帶 Image、必要工具與驗收 manifest，不附 boot.img、vendor_boot、init_boot、system_dlkm、vendor_dlkm、dtbo 或替換 `.ko`。實際安裝時才會寫入 boot；本次工作不執行安裝器或刷入。

如需確認官方工具的解包與重封裝，在已存在的 `/data/local/tmp` 下建立本專案專用的 `/data/local/tmp/myron-kernel-repack-check`。只放備份映像、候選 Image 與官方 magiskboot；只執行檔案的 unpack／repack，不傳入分割區路徑、不呼叫 flash_boot。測試後保留可核對的輸出至本機。這是封裝驗證，不是實機開機驗證。

`scripts/repack_check.py` 自動執行這個檔案測試，驗收標頭只改變核心大小、核心內容與 Image 一致、手機 boot 分割區前後 SHA-256 不變。手機暫存檔案不會作為刷入來源自動執行。

## 待機功能

Jason 原先要求預設開啟，確認沒有來源後已指示跳過。LK 的 `standby_opt=1` 需要 `lunar_render_hint` 核心程式碼、`deep_idle_enable` 等 sysfs 介面及對應協作邏輯。官方 ACK 沒有這個功能，複製設定檔或寫入不存在的介面不會生效。

已查核作者的 `LunarKernel-Dev/lunarkernel_vendor_opensource`，目前為空；公開的 `lunarkernel_sched_extention` 與第三方 builder 提供排程擴充，沒有查到這套待機實作。政策檔記錄 `requested_default=false`、`implemented=false`、`status=skipped_by_user`。本版不包含 LK 待機功能。

KernelSU LKM、原廠模組實際載入、CFI callback、硬體功能與開機仍須上機驗證。
