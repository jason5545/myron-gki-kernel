# myron GKI kernel

POCO F8 Ultra（`myron`）HyperOS `OS3.0.309.0.WPMCNXM` 用的自編 GKI 核心。

基底是 Android 官方 ACK `android16-6.12-2025-09`（Linux 6.12.38，KMI 5），補上 6.12.38 之後的穩定性與安全修正，內建 ReSukiSU 與 SUSFS。方向是只做修正與最佳化，盡量維持小米官方核心的行為；不改 KMI，不加新的排程器或功能。

## 目前版本

v15：`6.12.38-android16-5-g4b4d4935f92d-4k`。

- 2026/10/3 起在作者的手機上使用：開機、顯示、616 個原廠模組、UFS、ReSukiSU 與 SUSFS 都正常，dmesg 的 WARNING 與原廠相同。
- 原廠模組需要的 4,015 個核心符號，CRC 全部一致。
- 版本字串中 commit 的開頭固定為 `4b4d4935`，是 "KMI5" 的 ASCII hex。

只在這一台手機、這一個韌體版本驗證過。

## 內容

所有改動都在 [`patches/`](patches/)，依 [`series`](patches/series) 的順序套用。

| patch | 內容 |
| --- | --- |
| 0001～0002 | 原廠模組相容：保留原廠 `rust_binder.ko` 需要的兩個符號；允許原廠 GKI 模組搭配自編核心（清空保護清單、停用匯出裁切） |
| 0003～0004 | 內建 SUSFS v2.3.0 與 ReSukiSU v4.2.0-rc3，來源固定在 [`root.lock.json`](root.lock.json) |
| 0005 | 取自 LunarKernel v1.8.1 的三項設定：內建 BBR、tmpfs xattr、省電 workqueue |
| 0006 | 6.12.38 的 DRM valid clones 檢查會拒絕原廠顯示驅動，造成面板無法點亮；改成只記錄 |
| 0007～0008 | UFS runtime PM 錯誤復原、suspend 時 RTC work 造成的 SError |
| 0009～0135 | 6.12.38 之後（KMI 6 時期）的 stable、ACK 與 LunaKernel 修正，共 127 份，分 6 批：UFS／SCSI／block、f2fs／erofs／fuse／binder、mm／排程、網路、USB／HID、netlink |
| 0136 | 預設 TCP 擁塞控制改為 BBR |

每份 backport 的檔頭寫著來源、upstream commit 和採用理由。挑選過程與排除項目見 [候選清單](docs/kmi6-backport-candidates.md) 和 [實作紀錄](docs/kmi6-backport-batches.md)。

原廠 Image 另有 7 個小米私有選項（例如 `SCSI_FASTDISCARD`、`XIAOMI_ENHANCED_IOSTAT`），小米沒有公開原始碼，這個核心沒有這些功能。查核過程見 [references-6.12.md](docs/references-6.12.md)。

## 安裝

條件：

- myron，HyperOS `OS3.0.309.0.WPMCNXM`（Android 16），bootloader 已解鎖。
- 目前 boot 的核心是 KMI 5、4 KB 頁面（`6.12.*-android16-5-*-4k`）。
- init_boot 必須是原廠映像（SHA-256 `a4ed45c0…`）。root 若是靠 init_boot 的 KernelSU LKM 或 Magisk 修補，安裝器會拒絕，要先換回原廠 init_boot。

安裝包是 AnyKernel3 ZIP，只替換 boot 裡的核心，不動 ramdisk、DTB、init_boot 與模組。可以用 ReSukiSU 管理器或其他能刷 AnyKernel3 的工具刷入。編譯好的 ZIP 在 [Releases](https://github.com/jason5545/myron-gki-kernel/releases)，也可以自己編譯。

手機上沒有內建 root 的核心時，只能用 fastboot 寫入。[`scripts/repack_check.py`](scripts/repack_check.py) 可以用原廠 boot 加新的 Image 重封裝出 boot 映像並驗收；它只在手機暫存目錄操作，不寫分割區。

root 管理器請用 ReSukiSU v4.2.0-rc3（UAPI 4），下載連結在 `root.lock.json`。舊版或 UAPI 2 的管理器不相容。

刷入前先備份目前的 boot 分割區；開不了機時，用 fastboot 寫回備份。

## 編譯

需要 Linux x86_64。

```sh
bash scripts/sync.sh
BUILD_JOBS=24 bash scripts/build.sh
```

`sync.sh` 依 [`manifests/`](manifests/) 與 [`source.lock.json`](source.lock.json) 同步 50 個固定 commit 的官方 project，包含 Kleaf 與 Clang r536225。`build.sh` 套用 patch、編譯 4 KB GKI target，再依 [`config/kernel-policy.json`](config/kernel-policy.json) 核對設定、檢查 CRC，產生 AnyKernel3 ZIP。輸出在 `out/dist/`、`out/reports/`、`out/packages/`。

GitHub Actions 的「編譯 HyperOS 3 核心基底」可以手動啟動完整編譯；push 時只跑快速驗收。Actions 最後一次完整編譯是 v3，v4 之後都在下面的 Linux 主機上編譯。

作者平常在 Mac 上執行 `bash scripts/remote-build.sh <名稱>`，到另一台 Linux 主機（預設是作者的 LXC，可用 `BUILD_HOST` 指定）同步、增量編譯，再取回 `out/<名稱>/`。Apple container 的 Rosetta 跑不了 AOSP 的 relinterp 工具，不能用來編譯。

只讀的分析與檢查在 Mac 和 Linux 都能跑：

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
python3 scripts/inspect_kernel.py /path/to/boot.img
python3 scripts/inspect_kernel.py /path/to/AnyKernel3.zip
```

## 驗收

每次編譯：

- Image 的 KMI 是 `6.12-android16-5`，頁面 4096 bytes，設定與 `kernel-policy.json` 一致。
- 對照原廠 boot、vendor_boot、vendor_dlkm、system_dlkm 的模組（[`baseline/module-requirements.json`](baseline/module-requirements.json)），4,015 個符號 CRC 缺少 0、不符 0。唯一例外是原廠 `rust_binder.ko`：手機用 C binder，不會載入它。

每次刷入：

- 開機、螢幕正常，logcat 沒有持續的 `drmModeAtomicCommit failed`。
- 616 個模組載入，只少 `rust_binder` 和舊 KernelSU。
- UFS 沒有錯誤，`ufshcd_err_handler` 沒有被觸發。
- dmesg 沒有新的 oops 或 WARN。
- ReSukiSU 為 Built-in 模式，SUSFS 有初始化。

## 原廠基準

| 項目 | 原廠 |
| --- | --- |
| 裝置／系統 | myron／Android 16／HyperOS `OS3.0.309.0.WPMCNXM` |
| 核心 | `6.12.23-android16-5-g16e473de48a3-abogki462654244-4k` |
| KMI／頁面 | `6.12-android16-5`／4096 bytes |
| boot | header v4，ramdisk 為 0，分割區 100663296 bytes |

原廠設定在 [`baseline/stock.config`](baseline/stock.config)。原廠的 common commit `16e473de48a3` 在公開的 Android common 查不到，所以這個專案是官方 ACK 的相容版本，不是重現小米的原始碼。

原廠映像、第三方核心 ZIP 與手機備份只留在作者本機的 `local-backup/`，不在這個 repo 裡；`baseline/` 只放從中讀出的設定、雜湊與符號清單。

## 版本紀錄

| 版本 | 內容 | 實機 |
| --- | --- | --- |
| v1 | 基底 `android16-6.12-2025-06`（6.12.23），4,015 個 CRC 全部通過（[紀錄](docs/baseline-v1.md)） | — |
| v2 | 原廠模組相容設定與 AnyKernel3 封裝（[紀錄](docs/module-policy-build-v2.md)） | — |
| v3 | 內建 ReSukiSU 與 SUSFS（[紀錄](docs/root-build-v3.md)） | — |
| v4 | 基底換成 `android16-6.12-2025-09`（6.12.38），加入 0005（[紀錄](docs/build-2025-09-v4.md)） | 面板無法點亮，已還原 |
| v5 | 0006 修正面板（[紀錄](docs/build-2025-09-v5.md)） | 正常 |
| v6～v7 | 版本字串改為 `-g<commit>`，commit 開頭固定為 `4b4d4935` | — |
| v8 | 0007～0008 UFS 修正 | 正常 |
| v9～v13 | KMI 6 時期修正批次 1～5（[紀錄](docs/kmi6-backport-batches.md)） | v13 正常 |
| v14 | 批次 6：netlink | 正常 |
| v15 | 預設 TCP 擁塞控制改為 BBR | 正常 |

公開時把開發歷史合併成單一 commit，v15 是第一個公開版本。`docs/` 與 `baseline/` 提到的專案 commit（例如 `7868bf2`）屬於公開前的歷史，在這個 repo 裡已經找不到。

## 文件

- [backport 候選清單](docs/kmi6-backport-candidates.md)：936 筆候選的來源、篩選與判斷，完整表格在 [TSV](docs/kmi6-backport-candidates.tsv)。
- [backport 實作紀錄](docs/kmi6-backport-batches.md)：v9～v15 的做法、改寫、排除項目與實機結果。
- [可參考的 6.12 開源核心](docs/references-6.12.md)：LokumKernel、LunaKernel、小米官方釋出，以及原廠私有修改的查核。
- [ReSukiSU／SUSFS 的固定版本](docs/resukisu-susfs-fixed.md)、[模組相容與封裝](docs/module-policy-and-packaging.md)、[LunarKernel v1.3 套件查核](docs/lk-v1.3-audit.md)。

## 授權

本專案的 patch 與腳本以 [GPL-2.0-only](LICENSE) 釋出。取自 Linux stable、ACK 與 LunaKernel 的 backport 保留原作者與 `Signed-off-by`。

隨附的第三方元件維持各自的授權：

| 元件 | 位置 | 授權 |
| --- | --- | --- |
| [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) | `vendor/resukisu/` | 核心部分 GPL-2.0，其餘 GPL-3.0 |
| [SUSFS](https://gitlab.com/simonpunk/susfs4ksu) | `vendor/susfs/`、`patches/0003` | GPL-3.0 |
| [AnyKernel3](https://github.com/osm0sis/AnyKernel3) | `packaging/anykernel3/` | AnyKernel3 授權；`busybox`（GPL-2.0）與 `magiskboot`（GPL-3.0）取自 AnyKernel3 固定 commit，見 [`anykernel3.lock.json`](packaging/anykernel3.lock.json) |

## 免責

刷入自編核心可能讓手機無法開機。這個專案只在作者自己的手機上驗證過，使用風險自負。
