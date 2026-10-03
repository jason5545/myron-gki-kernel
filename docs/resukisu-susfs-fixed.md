# 固定 ReSukiSU／SUSFS 與管理器配套

## LK v1.3 的警告

LK v1.3 的 Image 內讀出 root 版本 `v4.1.0-0b4f56fd@Lunar612`。對應 ReSukiSU 提交 `0b4f56fd92bcc47a24bd4add8d7125239531c4f5` 的 `uapi/supercall.h` 定義 UAPI 2；目前官方 main `3a2745f78ab68e61c02a0681463021952083ec8c` 與固定 rc3 的管理器則使用 UAPI 4。

管理器 `Natives.isFullFeatured()` 要求它已被核心辨識為 manager，且核心與管理器 UAPI 完全相同。`KernelRepository` 另要求 root 可用。`HomePage` 在 manager 已辨識但功能不完整時，比較兩端 UAPI；核心端較舊便顯示「Kernel update required」，多個頁面也會按完整功能狀態限制操作。

因此這個訊息指向 root 驅動與管理器的介面版本，不是要求把 Linux 6.12 換成更大的版本。改 uname 或只提高版本碼不能補上 scoped su-session driver fd、bundled flags 等新介面。

LK 的 runtime UAPI 尚未直接查詢；以上依據是映像中標示的 root 提交、該提交原始碼與管理器的實際判斷條件，與 Jason 提供的警告行為一致。

## 本專案固定版本

| 元件 | 固定來源 |
| --- | --- |
| ReSukiSU | 官方 `v4.2.0-rc3`，commit `239e1e8871b8fcd51a6e5b3002e0ba522fdd99fb` |
| root 版本碼／UAPI | 35171／4，與同一提交的官方發行管理器一致 |
| SUSFS | `v2.3.0`，`gki-android16-6.12` commit `b213c54126fb243595ce7876e91d84d6e0861fec` |
| 管理器 | `ReSukiSU_v4.2.0-rc3_35171-arm64-v8a-release.apk` |
| APK SHA-256 | `25657bc449439687608fffa04b4b586de90fc405e3dc6217bd997fc71ba0a0a1` |
| APK 簽署憑證 | 887 bytes，SHA-256 `d3469712b6214462764a1d8d3e5cbe1d6819a0b629791b9f4101867821f1df64`，符合核心內建的 ReSukiSU 憑證清單 |

rc3 是官方預發行版本。這次固定它的來源與配套 APK，不追蹤浮動 nightly；未來管理器更改 UAPI，仍需同時更新並驗收核心。

`root.lock.json` 保存提交、版本、APK 與每個上游來源檔案的 SHA 或連結資訊。`vendor/` 保存原始 ReSukiSU 核心／UAPI 和 SUSFS 檔案；不執行上游會拉取 main 的 setup.sh。Kleaf 將來源實體化到 `drivers/kernelsu`，建置資料由固定提交產生，避免編譯中依賴 sandbox 外的 Git 資料或網路。版本碼屬於該來源的真實版本；UAPI 定義與驅動實作一併更新。

SUSFS patch 調整到固定 ACK 的 SELinux 前後文；read hook 依 rc3 實作使用 `int ksu_handle_sys_read(unsigned int, char __user **, size_t *)`，不採用型別不一致的宣告。KSU 與 SUSFS 啟用、選用 inline hooks；保留原有 KMI 5、4 KB、CFI、MODVERSIONS 與原廠模組 CRC 驗收。LK 待機調校仍依 Jason 指示跳過。

## init_boot 遷移

目前手機 init_boot 有 `init` loader、`init.real`、`kernelsu.ko`、`ksu_block_modules`、`ksu_config`，會載入現有 KernelSU LKM。改成核心內建 root 時應使用原廠 init_boot，避免舊後端與新核心同時存在。

MiShare 的原廠 init_boot 已核對：`init` 與目前映像的 `init.real` 位元組完全相同；其餘原廠 ramdisk 項目的資料與模式均一致。配套檔案保存在本機 `out/root-migration/init_boot-stock.img`，SHA-256 `a4ed45c0af246068212b899a3f7e003b396d45b77af59b7f37acca0495ffe4b3`。原始備份都保留。

候選 AnyKernel3 安裝器只接受這份已驗證原廠 init_boot 的 SHA；遇到舊 LKM 或其他未驗證映像會在寫 boot 前停止。ZIP 不附替換驅動，也不自動寫 init_boot。實際遷移和開機測試另行執行；本次只準備來源、編譯與封裝，不安裝管理器、不刷入、不重新啟動手機。

參考：[官方 root 提交](https://github.com/ReSukiSU/ReSukiSU/tree/239e1e8871b8fcd51a6e5b3002e0ba522fdd99fb)、[LK 標示的舊 root 提交](https://github.com/ReSukiSU/ReSukiSU/tree/0b4f56fd92bcc47a24bd4add8d7125239531c4f5)、[官方 SUSFS 提交](https://gitlab.com/simonpunk/susfs4ksu/-/tree/b213c54126fb243595ce7876e91d84d6e0861fec)。
