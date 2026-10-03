# LK v1.3 套件查核

2026/10/2，直接讀取手機提供的 `LunarKernel-v1.3.zip`、Image 內嵌設定與安裝腳本；沒有執行套件程式、刷入或重新啟動手機。

LK v1.3 維持 Linux 6.12.23 與 4 KB 分頁，保留 MODVERSIONS／CFI。它清空 GKI 模組匯出保護清單、停用符號裁切，將 KernelSU／SUSFS、Rust Binder、zram 和 zsmalloc 編入核心，再附加遊戲與待機服務。這能說明它採用的相容策略，但不能從 ZIP 重建每個程式碼修改，也尚未證明它能在目前 HyperOS 開機。

完整設定差異在 [`../baseline/lk-v1.3-audit/config-comparison.json`](../baseline/lk-v1.3-audit/config-comparison.json)。比較將缺少的設定視為未啟用；LK 與原廠有 41 個不同項目。

## 輸入與來源

| 項目 | 讀取結果 |
| --- | --- |
| ZIP SHA-256 | `ba41a8560ab2af1f419f83718f97ef513fe5c19a17cecb800b612842f50d1728` |
| Image SHA-256 | `65412d32d3d9fdb3a8e0865528198a582cf7902d53cbddaaec4eafead2b4e4b0` |
| Image 大小 | 41,110,016 bytes |
| Image 真實 release | `6.12.23-gb050bfa1f91e-LunarKernel-V1.3` |
| 套件標示的 Source | `b050bfa1f91e740de561ea118b36106d72ed6ff8` |
| 套件標示的工作目錄 | Dirty files: 3 |
| 套件標示的建置時間 | 2026/7/25 21:35:49 UTC |

上述 Source 提交在公開 Android common Gitiles 回傳 HTTP 404。尚未取得作者對應的完整原始碼、三個 dirty 檔案或 Module.symvers，因此不能確認全部 backport、KernelSU 分支版本或 LK 的完整模組 CRC。非標準 release 無法直接讀出真正的 KMI 世代。

下列載入規則以我們固定的 ACK commit `13ff069897df965d9039dca208b2f39dacf81957` 查核，屬於解釋設定效果的依據；不代表已確認 LK 沒有額外修改載入程式碼。

## 模組相容策略

| 設定 | 原廠 | LK v1.3 | 我們已編譯的第一版 |
| --- | --- | --- | --- |
| ARM64 分頁 | 4 KB | 4 KB | 4 KB |
| `CONFIG_MODVERSIONS` | y | y | y |
| `CONFIG_CFI_CLANG` | y | y | y |
| `CONFIG_LTO_NONE` | y | y | y |
| `CONFIG_MODULE_SIG` | y | y | y |
| `CONFIG_MODULE_SIG_ALL` | y | y | y |
| `CONFIG_MODULE_SIG_FORCE` | n | n | n |
| `CONFIG_MODULE_SIG_PROTECT_LIST` | `"protected_module_names_list"` | `""` | `"protected_module_names_list"` |
| `CONFIG_MODULE_SIG_PROTECT` | y | n | y |
| `CONFIG_TRIM_UNUSED_KSYMS` | y | n | y |
| `CONFIG_MODULE_FORCE_LOAD` | n | n | n |
| `CONFIG_ANDROID_BINDER_IPC_RUST` | m | y | m |
| `CONFIG_ZRAM`／`CONFIG_ZSMALLOC` | m／m | y／y | m／m |
| `CONFIG_KSU` | n | y | n |

**GKI 簽章保護：** LK 仍啟用簽章驗證與編譯時簽章，沒有要求所有模組都必須由受信任金鑰簽署。清空 `MODULE_SIG_PROTECT_LIST` 使衍生設定 `MODULE_SIG_PROTECT` 停用。依 ACK 的 `verify_exported_symbols()`，這會移除「未受信任模組不得匯出 protected 符號」的限制，能避開原廠 system_dlkm 模組的金鑰與新核心不同所造成的一類拒載。簽章格式錯誤、驗證失敗或 runtime 強制簽章仍可能拒載；清單清空不等於所有簽章檢查停用。

**符號裁切與匯入限制：** LK 的 `TRIM_UNUSED_KSYMS=n` 不只保留更多已有匯出，依 ACK 的 `resolve_symbol()`，也停用未受信任模組必須使用允許清單內核心符號的限制。我們第一版仍採用裁切，僅將原廠 Rust Binder 需要的 `list_lru_add_obj`／`list_lru_del_obj` 加入小米保留清單；它們已有實作與 GPL 匯出。4015 個 CRC 通過屬於我們的第一版結果，沒有套用到 LK。

**內建與模組的差異：** LK 把原本的 Rust Binder、zram、zsmalloc 模組改為內建。原廠模組若再匯出同名符號，依 ACK 載入器仍可能因重複匯出被拒；關掉保護清單不會取消重複符號檢查。這些設定需要與原廠載入順序一起核對，不能整份照抄。

LK 將 zram 預設壓縮改成 LZ4，加入 ZSTD backend，以及 `KCOMPRESSD`、`XRING_ZRAM_MEMCG`、`XRING_ZRAM_MEMCG_WRITEBACK`、`XRING_ZRAM_XSWAPD`、`XRING_SMART_CACHE` 等設定。它也加入 `XIAOMI_SFI`、tmpfs ACL／xattr，將 ADIOS I/O scheduler 設為模組，但 ZIP 沒有附該模組。這些是內嵌設定可證實的差異；效能與實際初始化方式未驗證。

## KernelSU 與版本顯示

`CONFIG_KSU=y`、`CONFIG_KSU_MULTI_MANAGER_SUPPORT=y`、`CONFIG_KSU_SUSFS=y`，另啟用 SUSFS 的 path／mount／kstat／map／open redirect／uname／cmdline 功能。這是核心內建 root；我們目前手機原廠 Image 沒有 KSU，使用 init_boot 的 KernelSU LKM。ZIP 的安裝腳本未見清理或修改既有 init_boot 的 LKM 載入流程，兩者配套仍要另驗。

版本偽裝實際由 `post-fs-data.sh` 呼叫 `apply_uname_spoof()`，寫入：

```text
/sys/module/InfoManager/parameters/kernel_name
/sys/module/InfoManager/parameters/kernel_build_time
```

預設顯示 `6.12.23-android16-5-g75e9b1c7ae7c-abogki463945075-4k` 與 `#1 SMP PREEMPT Thu Nov 27 08:45:40 UTC 2025`，都不同於 Image 中的真實版本資訊，也不同於目前手機原廠 release。

這是顯示偽裝，不能證明 ABI 相容。依 ACK 的 `same_magic()`，有 CRC 的模組比較 vermagic 時會略過 release 部分，其餘旗標仍要一致，CRC 仍需吻合；未帶 CRC 的 LKM 不適用這個略過規則。也不能由 InfoManager 的 sysfs 寫入，推定它改寫載入器編譯時的 vermagic。

## 安裝包與附加服務

套件沒有 `.ko`、獨立 `.img`／`.dtb`／`.dtbo`，`do.modules=0`。安裝腳本以 `block=boot` 自動選 slot，讀取現有 boot，透過內附 magiskboot 用新 Image 重新封裝，再寫回 boot。原廠 boot v4 的 ramdisk 大小為 0，腳本會採用 `flash_boot` 路徑；沒有這個 ZIP 提供的 vendor_boot、system_dlkm 或 vendor_dlkm 替換映像。

腳本刪除拆出的 `kernel_dtb`，註解宣稱新 Image 已附相符 DTB。對未壓縮 Image 掃描 FDT 標頭與尺寸，只找到與原廠同樣的 72-byte 空根節點 FDT，位於 Image 內部；未找到可支持「已附手機硬體 DTB」宣稱的資料。目前手機硬體 DTB 位於 vendor_boot，應保留原廠內容。

安裝檢查只接受當前版本以 `6.12` 開頭；裝置檢查關閉、Android 版本欄位空白。這不是 myron／目前 HyperOS 的完整相容驗收。

此外，安裝腳本會將附加套件複製到 `/data/adb/modules/lunarkernelmodule`，清除舊 Lunar 模組位置，建立 `/data/adb/lunar/setting.prop`。這是 root 管理器附加套件，不是 `.ko` 驅動替換。

| 功能 | 此 ZIP 的實際預設與腳本行為 |
| --- | --- |
| VFAS／render hint | 核心設定啟用；遊戲調頻與 boost 預設關閉，可由 WebUI 開啟 |
| 遊戲 SCX／LSE | 能力清單 `lse=0`，沒有 `lunar_bsp_ext_sched.ko`；不可由服務腳本中的 optional insmod 推定已提供 |
| 待機最佳化 | `standby_opt=1`，存在介面時寫 `deep_idle_enable=1`，並啟動 kernel-daemon |
| I/O 前台最佳化 | 設定檔寫 `io_unfair=1`，但能力清單 `io_priority=0`／`dynamic_readahead=0`，`apply_state()` 會將這項視為不支援 |
| 小米服務 | 開機後嘗試使 `/data/system/mcd/df` 不可存取且 immutable；存在介面時將 `perfmgr_enable` 寫成 0 |
| 場景配合 | 預設與 Scene 共存；啟用接管功能時可修改 Scene 的遊戲白名單，腳本也會移除 `/data/powercfg.json`／`powercfg.sh` |
| 使用者空間 daemon | 內附 ARM64 程式與 SM8850 遊戲設定；依功能啟用狀態啟動，並移入 system cgroup |

daemon 內部演算法與核心 VFAS／render hint 實作沒有由這次靜態檢查重建。套件文件的省電與效能宣稱，也不算實機測量。

## 對我們基底的判斷

下一步可參考 LK 的 GKI 模組保護設定與沿用原廠 boot 重新封裝方式；要同時核對剩餘匯入限制。第一版可保持原廠的 Binder／zram 模組配置，用明確符號清單處理相容需求。KernelSU 要取得可追溯且相容的來源，並處理現有 init_boot 的 LKM 流程；效能 daemon、小米服務停用與版本偽裝不屬於完成可開機基底的必要條件。

本次僅保存分析，沒有修改建置設定、核心 patch 或手機。

規則來源：[ACK Kconfig](https://android.googlesource.com/kernel/common/+/13ff069897df965d9039dca208b2f39dacf81957/kernel/module/Kconfig)、[ACK main.c](https://android.googlesource.com/kernel/common/+/13ff069897df965d9039dca208b2f39dacf81957/kernel/module/main.c)、[ACK signing.c](https://android.googlesource.com/kernel/common/+/13ff069897df965d9039dca208b2f39dacf81957/kernel/module/signing.c)、[ACK version.c](https://android.googlesource.com/kernel/common/+/13ff069897df965d9039dca208b2f39dacf81957/kernel/module/version.c)。
