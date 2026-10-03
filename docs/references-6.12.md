# 可參考的 6.12 開源核心

2026/10/2 用 `gh` 搜尋整理，日期是查詢當時各 repo 最近一次推送或 commit。這裡只列實際打開看過的內容；沒有驗證過的說明不寫成事實。

LunarKernel 6.12 的核心原始碼沒有找到：[`4532sde/LunarKernel6.12-backup`](https://github.com/4532sde/LunarKernel6.12-backup) 與 [`LunarKernel-Dev/lunarkernel_vendor_opensource`](https://github.com/LunarKernel-Dev/lunarkernel_vendor_opensource) 都是空 repo；[`NEURAX-FX/LunarKernel-GKI-Builder`](https://github.com/NEURAX-FX/LunarKernel-GKI-Builder) 只建置 `android14-6.1`、`android15-6.6`。

## 同基底、可直接對照

### LokumKernel SM8850

[`LokumKernel-SM8850/android_kernel_xiaomi_sm8850`](https://github.com/LokumKernel-SM8850/android_kernel_xiaomi_sm8850)，對象是小米 SM8850（README 寫 Pandora）。分支有 `6.12.23-android16-5-…` 與 `6.12.38-android16-5-lokumkernel-ksun-susfs-exp1`，後者從 `android16-6.12-2025-09` 匯入，與本專案 v5 同一條分支。

- [`1909baed87`](https://github.com/LokumKernel-SM8850/android_kernel_xiaomi_sm8850/commit/1909baed87)「bypass strict DRM clone validation for Xiaomi SM8850」：把 `drm_atomic_check_valid_clones()` 的 `-EINVAL` 改成 `drm_warn_once` 後 `continue`，與本專案 `0006` 做法相同。兩邊各自查到同一個問題。
- [`59a69d12bb`](https://github.com/LokumKernel-SM8850/android_kernel_xiaomi_sm8850/commit/59a69d12bb)「add Xiaomi DMV debug vendor hooks for 6.12.38」：補 dm-verity 除錯用的 `android_vh_handle_*` hooks。myron 目前載入的模組沒有用到（`baseline/module-requirements.json` 查無這些符號），本專案未採用。
- KernelSU Next 與 SUSFS v2.1.0。

### LunaKernel

[`LunaKernel/android_kernel_xiaomi_sm8850`](https://github.com/LunaKernel/android_kernel_xiaomi_sm8850)（名稱是 Luna，不是 Lunar）。主分支給小米 17（pudding）HyperOS 4，ACK `android16-6.12-2026-06_r21`（6.12.81）。另有 `os3-android16-6.12.23`，README 稱為 HyperOS 3 歷史分支，最後更新 2026/8/29。

- 每個 backport 單獨記錄在 `patches/backports/`，可以個別稽核與回退；之後從 6.12.38 再往上補修正時可以照這個方式。
- 內建 KernelSU v3.3.0、SUSFS v2.3.0、Baseband Guard、IPSet。
- README 記錄的小米公開基線是 MiCode `popsicle-w-oss` @ `45705be1220b`。

2026/10/3 讀過 `main` 與 `os3-android16-6.12.23` 的腳本與文件，它處理小米部分的方式和本專案相同：

- GKI Image 只從 AOSP common 編。MiCode 的 `popsicle-w-oss` 只拿來核對 `android/ACK_SHA`。`AGENTS.md` 明文規定不准用小米 repo 的同名目錄覆蓋 common。
- 原廠的小米私有選項（`XIAOMI_*`、`SCSI_FASTDISCARD` 等）在兩個分支都找不到，它也沒有這些功能。
- 相容性靠比對原廠 OTA：從 boot、vendor_boot、vendor_dlkm、system_dlkm 抽出模組實際依賴的 4,083 個符號，核對 CRC、provider 與 namespace。`rust_binder.ko` 是唯一例外，和本專案一樣。
- `main` 能用 KMI 6（r21，6.12.81），是因為小米 17 HyperOS 4 的原廠核心本來就是 `6.12.69-android16-6`。myron OS3 的原廠是 KMI 5，不能照搬。
- `os3` 分支的兩個 backport（binder `binder_free_transaction` 生命週期、UFS runtime PM 錯誤復原）在本專案的 6.12.38 基底裡已經有了。unicode 相容 patch 改的是 ext4 casefold，手機 `/data` 是 f2fs，而 f2fs 的部分基底也已經有了。ADIOS、TCP Brutal 是新功能，不在本專案範圍。

## 小米官方釋出

| repo／分支 | 內容 |
| --- | --- |
| [`MiCode/Xiaomi_Kernel_OpenSource`](https://github.com/MiCode/Xiaomi_Kernel_OpenSource) `popsicle-w-oss` | 「Xiaomi kernel changes for Xiaomi 17, Xiaomi 17 Pro AND Xiaomi 17 Pro Max for Android W」（2026/3/9）。高通 msm-kernel（vendor 模組）樹，含 `build.config.msm.canoe`。`android/ACK_SHA` 記錄 GKI 基底為 `android16-6.12-2025-06_r8`（`f1bdb13583da`）。 |
| [`MiCode/vendor_opensource_display-drivers`](https://github.com/MiCode/vendor_opensource_display-drivers) `popsicle-w-oss` | 小米 17 系列的顯示驅動，只釋出部分檔案（約 359 KB），找不到設定 `possible_clones` 的程式碼。 |
| `MiCode/kernel_devicetree`、`vendor_qcom_proprietary_display-devicetree`、`vendor_qcom_opensource_*` | device tree 與其他高通 vendor 模組。 |

這些都不是 GKI Image 的原始碼；原廠 `g16e473de48a3` 仍查不到。

### 原廠 Image 帶有小米私有的 GKI 修改（2026/10/3 查）

`popsicle-w-oss` 是高通 msm-kernel 的 overlay 樹，`mm/`、`kernel/`、`net/` 只放 vendor 模組（例如小米自己的 `zsmalloc.c`、`kernel/sched`、`net/qrtr`），會另外編成 `.ko`，手機本來就在用原廠版本。MiCode 在 2026/9 更新的 Android 16（`-w-oss`）分支中，只有 `popsicle-w-oss` 是 SM8850，沒有 myron 分支；組織底下也沒有 GKI common 的 repo，`kernel_build` 只有各機型的建置設定。

比對原廠 Image 的設定（`baseline/stock.config`）和 v15，原廠有 7 個 ACK 不存在的選項：`CONFIG_XIAOMI_DEVICE_XCOPY`、`CONFIG_XIAOMI_DMABUF_HUGETLB`、`CONFIG_XIAOMI_ENHANCED_IOSTAT`、`CONFIG_XIAOMI_EROFS_IOSTAT`、`CONFIG_F2FS_FAULT_REPORT`、`CONFIG_SCSI_DISCARD`、`CONFIG_SCSI_FASTDISCARD`。也就是說原廠 Image 是從帶小米修改的 common 編出來的。用 GitHub 程式碼搜尋這些名稱，只找到其他人 dump 出來的 ikconfig（例如 `xt0032rus/poco_myron_dump`），沒有原始碼，所以無法合入。本專案從第一版起就沒有這些功能；原廠模組的 CRC 驗收沒有缺少符號，表示 vendor 模組不依賴它們的匯出符號。

其餘設定差異是本專案刻意的（KernelSU／SUSFS、模組保護與匯出裁切、BBR、tmpfs xattr、省電 workqueue）或 ACK 基底不同造成的（例如 2025-06 的 gki_defconfig 有 `CONFIG_TLS=m`，連帶 `STREAM_PARSER=y`；2025-09 拿掉了）。MiCode 的 6.12.38 分支 `bsp-prague-w-oss`（Redmi K90 Max）與 `yili-w-oss`（REDMI K Pad 2）是聯發科平台，對 myron 參考價值低。

## myron 與 ReSukiSU 整合

- [`Geeeeeker/android_kernel_xiaomi_sm8850`](https://github.com/Geeeeeker/android_kernel_xiaomi_sm8850)（`lineage-23.2`，6.12.23）：commit「arch: arm64: add support for Poco F8 Ultra (myron)」只加 3 個檔案，含 `arch/arm64/configs/vendor/myron_GKI.config`，可以和原廠 config 對照。
- [`MYSK-QC/android_kernel_xiaomi_sm8850`](https://github.com/MYSK-QC/android_kernel_xiaomi_sm8850)（Kokuban，小米 17 系列，6.12.23）：分支 `ksu`、`mksu`、`resukisu`；有「Add empty protected lists to fix modpost」，與本專案 `0002` 同方向。
- [`0oiiiiiippqqw-star/android_kernel_xiaomi_sm8850-extra`](https://github.com/0oiiiiiippqqw-star/android_kernel_xiaomi_sm8850-extra)（Picters，小米 17，6.12.23）：ReSukiSU、SUSFS 與外接 USB Wi-Fi。

## LK 唯一公開的部分：LSE 排程器

[`LunarKernel-Dev/lunarkernel_sched_extention`](https://github.com/LunarKernel-Dev/lunarkernel_sched_extention)（`dev` 分支）：把 Oplus 風馳遊戲核心（`hmbird_gki`）的 Slim WALT 負載追蹤移植到小米裝置的排程器，檔案為 `lse_*.c`、`cpufreq_lse.c`。LK v1.8.1 套件裡的 `scheddata/SM8850.toml` 推測是給它用的（未驗證）。裡面沒有 `render_hint`，LK 的待機調校仍沒有來源。移植會牽涉排程與 vendor hooks，需要另外評估與實機驗證。

## 其他

- [`travismills82/oneplus15-sm8850-oos-kernel`](https://github.com/travismills82/oneplus15-sm8850-oos-kernel)：OnePlus 15 OxygenOS 16 的完整 SM8850 `kernel_platform`（約 2.4 GB），可作為高通 vendor 程式碼與 Oplus `hmbird` 的參考。
- [`Mi-SM8850/android_kernel_xiaomi_sm8850`](https://github.com/Mi-SM8850/android_kernel_xiaomi_sm8850)：6.17、LineageOS，來自 CodeLinaro；不是 GKI，參考價值低。
- [`lolipuru/android_kernel_xiaomi_sm8850-devicetrees`](https://github.com/lolipuru/android_kernel_xiaomi_sm8850-devicetrees)：LineageOS 用的 SM8850 device tree。
