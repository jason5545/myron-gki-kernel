# 固定 ReSukiSU／SUSFS 與管理器配套

## LK v1.3 的警告

LK v1.3 的 Image 內讀出 root 版本 `v4.1.0-0b4f56fd@Lunar612`。對應 ReSukiSU 提交 `0b4f56fd92bcc47a24bd4add8d7125239531c4f5` 的 `uapi/supercall.h` 定義 UAPI 2；目前官方 main `3a2745f78ab68e61c02a0681463021952083ec8c` 與固定 rc3 的管理器則使用 UAPI 4。

管理器 `Natives.isFullFeatured()` 要求它已被核心辨識為 manager，且核心與管理器 UAPI 完全相同。`KernelRepository` 另要求 root 可用。`HomePage` 在 manager 已辨識但功能不完整時，比較兩端 UAPI；核心端較舊便顯示「Kernel update required」，多個頁面也會按完整功能狀態限制操作。

因此這個訊息指向 root 驅動與管理器的介面版本，不是要求把 Linux 6.12 換成更大的版本。改 uname 或只提高版本碼不能補上 scoped su-session driver fd、bundled flags 等新介面。

LK 的 runtime UAPI 尚未直接查詢；以上依據是映像中標示的 root 提交、該提交原始碼與管理器的實際判斷條件，與 Jason 提供的警告行為一致。

## 本專案固定版本

| 元件 | 固定來源 |
| --- | --- |
| ReSukiSU | 官方 `main` commit `8770c7e324a22895703c4916b8a16520e0b81c79`（`v4.2.0-rc3-32-g8770c7e3`），v20 起；v19 以前是 `v4.2.0-rc3`（`239e1e8871b8fcd51a6e5b3002e0ba522fdd99fb`） |
| root 版本碼／UAPI | 35203／5，與同一提交的 CI 管理器一致；rc3 是 35171／4 |
| SUSFS | `v2.3.0`，`gki-android16-6.12` commit `b213c54126fb243595ce7876e91d84d6e0861fec` |
| 管理器 | CI run [`37180105212`](https://github.com/ReSukiSU/ReSukiSU/actions/runs/37180105212) 的 `Spoofed-Manager-release`，arm64 APK，套件名稱 `ntaxru.tzihjp.gpckog` |
| APK SHA-256 | `365789335c025d0cc2971baded864b9d1481416c21a1d40a947f02bf2743c4b1`（本機 `out/manager/ReSukiSU_v4.2.0-rc3_35203-arm64-v8a-spoofed-release.apk`） |
| APK 簽署憑證 | 887 bytes，SHA-256 `d3469712b6214462764a1d8d3e5cbe1d6819a0b629791b9f4101867821f1df64`，符合核心內建的 ReSukiSU 憑證清單 |

rc3 是官方預發行版本，v15～v19 固定它的來源與配套 APK。v20 改固定 main 的一個提交，原因見下一節；仍然不追蹤浮動 nightly，管理器更改 UAPI 時要同時更新並驗收核心。

## 2026/10/5：升到 main `8770c7e3`（v20）

main 在 `8770c7e3`（「Avoid repeatedly triggering service stage」，上游 tiann/KernelSU#3800）把 UAPI 從 4 升到 5：新增 `EVENT_SERVICES`，核心回傳 1 表示執行 service 階段，回傳 0 表示已經執行過。

手機上的管理器一直跟著 main 的 CI 版本（10/5 時是 35199，`80c0e190`，UAPI 4）。管理器更新到 `8770c7e3` 之後，會把 `/data/adb/ksud` 換成新版。新 ksud 在 service 階段先問核心，rc3 的核心對不認得的事件一律回 0，ksud 就當成已經執行過而跳過：`/data/adb/service.d` 與模組的 `service.sh` 都不會跑。管理器也會顯示「Kernel update required」。所以核心跟著升。

rc3 之後 32 個提交，改到 `kernel/` 與 `uapi/` 的有 6 個：

| 提交 | 內容 | 對這支手機 |
| --- | --- | --- |
| `f397410c` | sepolicy：移除規則時 `db->len` 少算；已存在的 allowxperm 規則，新的權限位元不會加上去 | 有影響 |
| `b0fa24df` | 讀 allowlist 時改用 KernelSU 自己的 cred | 有影響 |
| `f6513993` | `packages.list` 變動時同步執行 `track_throne` | 有影響 |
| `8770c7e3` | service 階段只觸發一次，UAPI 5 | 有影響 |
| `325265c5` | riscv64 支援；系統呼叫第一個參數改用 `PT_REGS_SYSCALL_PARM1` | arm64 上它仍是 `regs[0]`，行為不變 |
| `c4bdcaae` | 3.6 以前核心的 `dentry_open` | 不適用 |

上游 `kernel/Kbuild` 新增的 riscv64 段落少一個右括號（`else ifeq ($(CONFIG_RISCV),y`）。arm64 在前一個分支就成立，make 不會解析那一行；這個核心也沒有開 `CONFIG_KSU_TRACEPOINT_HOOK`，整段都跳過。GNU make 3.81 模擬：arm64 與關閉 tracepoint hook 都正常，只有走到 riscv 那條才會出錯。

`vendor/resukisu` 換成 `8770c7e3` 的 `kernel/`、`uapi/`、`LICENSE`（`git archive`，換之前確認舊的內容與 rc3 的 archive 完全相同），`root.lock.json` 從 119 項變成 123 項：16 個檔案改變，多 4 個 riscv64 檔案，SUSFS 的項目不變。`root-patches/0001` 直接套用。版本碼依上游公式 30000＋4503＋700＝35203，與 CI 管理器的 versionCode 相同。

管理器改用 Jason 指定的 Spoofed 版，取代手機上的舊管理器（`dultqo.utgklb.okvfdx`，35199）。舊 APK 備份在 `local-backup/eu310/manager-35199-80c0e190-dultqo.apk`。CI artifact 有保存期限，以本機那份為準。

順序是先刷 v20，再裝新管理器、移除舊的。反過來做的話，新管理器配 v19 會顯示「Kernel update required」，可能擋住管理器的刷入功能，ksud 也已經被換掉。退回 v19 時，管理器也要換回舊的。

`root.lock.json` 保存提交、版本、APK 與每個上游來源檔案的 SHA 或連結資訊。`vendor/` 保存原始 ReSukiSU 核心／UAPI 和 SUSFS 檔案；不執行上游會拉取 main 的 setup.sh。Kleaf 將來源實體化到 `drivers/kernelsu`，建置資料由固定提交產生，避免編譯中依賴 sandbox 外的 Git 資料或網路。版本碼屬於該來源的真實版本；UAPI 定義與驅動實作一併更新。

SUSFS patch 調整到固定 ACK 的 SELinux 前後文；read hook 依 rc3 實作使用 `int ksu_handle_sys_read(unsigned int, char __user **, size_t *)`，不採用型別不一致的宣告。KSU 與 SUSFS 啟用、選用 inline hooks；保留原有 KMI 5、4 KB、CFI、MODVERSIONS 與原廠模組 CRC 驗收。LK 待機調校仍依 Jason 指示跳過。

## init_boot 遷移

目前手機 init_boot 有 `init` loader、`init.real`、`kernelsu.ko`、`ksu_block_modules`、`ksu_config`，會載入現有 KernelSU LKM。改成核心內建 root 時應使用原廠 init_boot，避免舊後端與新核心同時存在。

MiShare 的原廠 init_boot 已核對：`init` 與目前映像的 `init.real` 位元組完全相同；其餘原廠 ramdisk 項目的資料與模式均一致。配套檔案保存在本機 `out/root-migration/init_boot-stock.img`，SHA-256 `a4ed45c0af246068212b899a3f7e003b396d45b77af59b7f37acca0495ffe4b3`。原始備份都保留。

候選 AnyKernel3 安裝器只接受這份已驗證原廠 init_boot 的 SHA；遇到舊 LKM 或其他未驗證映像會在寫 boot 前停止。ZIP 不附替換驅動，也不自動寫 init_boot。實際遷移和開機測試另行執行；本次只準備來源、編譯與封裝，不安裝管理器、不刷入、不重新啟動手機。

參考：[官方 root 提交](https://github.com/ReSukiSU/ReSukiSU/tree/239e1e8871b8fcd51a6e5b3002e0ba522fdd99fb)、[LK 標示的舊 root 提交](https://github.com/ReSukiSU/ReSukiSU/tree/0b4f56fd92bcc47a24bd4add8d7125239531c4f5)、[官方 SUSFS 提交](https://gitlab.com/simonpunk/susfs4ksu/-/tree/b213c54126fb243595ce7876e91d84d6e0861fec)。
