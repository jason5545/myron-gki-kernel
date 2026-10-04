# KMI 6 時期修正 backport：九批實作與編譯（v9～v19）

依 [候選清單](kmi6-backport-candidates.md) 的建議，2026/10/2 晚上 Jason 確認全部做，需要改寫的也一起做。手機當時已拔掉 USB，所以當晚只做到編譯和 CRC 關卡。10/3 Jason 直接刷入 v13，實機結果見下方；之後追加批次 6 編出 v14。

## 做法

1. 在 LXC 112 的檢查 repo `/gki/kmi6` 建 `bp` 分支，以 v8 的樹（ACK `1ad7be92` 加上 0001～0008）為起點。
2. `scripts/backport/apply_chain.py` 依批次、依 stable 版本順序把 patch 疊上去，每筆一個 commit。來源、upstream、說明寫在 commit 訊息裡。套不上的再逐筆手工處理。
3. `scripts/backport/export_chain.py` 把每個 commit 匯出成 `patches/` 的檔案。內容是相對前一份的 diff，所以照 `series` 的順序一定能套上。
4. 每批一次 `remote-build.sh`，累積編譯：v9 是 v8 加批次 1，v10 再加批次 2，依此類推。

每份 patch 的檔頭依序是：來源與 upstream commit、原標題、採用理由。改寫過的會多一行「改寫：」。

## 結果

| 版本 | 內容 | patch | 版本字串 | Image SHA-256 | CRC |
| --- | --- | --- | --- | --- | --- |
| v9 | 批次 1：UFS／SCSI／block | 0009～0018（10） | `6.12.38-android16-5-g4b4d49359fd0-4k` | `166cf01ac3cd…` | 缺少 0、不符 0 |
| v10 | ＋批次 2：f2fs／erofs／fuse／binder | 0019～0042（24） | `6.12.38-android16-5-g4b4d4935ffaa-4k` | `64e02e834192…` | 缺少 0、不符 0 |
| v11 | ＋批次 3：mm／排程／核心 | 0043～0070（28） | `6.12.38-android16-5-g4b4d49354867-4k` | `0dcca2123a48…` | 缺少 0、不符 0 |
| v12 | ＋批次 4：網路／netfilter | 0071～0121（51，含前置 0076） | `6.12.38-android16-5-g4b4d4935779f-4k` | `b929f5808959…` | 缺少 0、不符 0 |
| v13 | ＋批次 5：USB／HID | 0122～0131（10） | `6.12.38-android16-5-g4b4d49357977-4k` | `3fc3f57b6209…` | 缺少 0、不符 0 |
| v14 | ＋批次 6：netlink rmem（追加） | 0132～0135（4） | `6.12.38-android16-5-g4b4d4935922a-4k` | `b246ec5eeede…` | 缺少 0、不符 0 |
| v15 | ＋0136：預設 TCP 擁塞控制改為 BBR | 0136（1） | `6.12.38-android16-5-g4b4d4935f92d-4k` | `936cf7b208f0…` | 缺少 0、不符 0 |
| v16 | ＋批次 7：Image 內的高通相關修正（Gunyah、SCMI） | 0137～0140（4） | `6.12.38-android16-5-g4b4d49350df7-4k` | `30c25089a4a2…` | 缺少 0、不符 0 |
| v18 | ＋批次 8：stable 6.12.112 補掃 | 0141～0147（7） | `6.12.38-android16-5-g4b4d4935db3b-4k` | `fdea557f4842…` | 缺少 0、不符 0 |
| v19 | ＋批次 9：參考 LunaKernel 的效能 backport | 0148～0155（8） | `6.12.38-android16-5-g4b4d49351f54-4k` | `3e58b2a92be4…` | 缺少 0、不符 0 |

每一版的 KMI 都是 `6.12-android16-5`，頁面 4096 bytes，Image 內都有 ReSukiSU（`v4.2.0-rc3-239e1e88@ReSukiSU`）、SUSFS 與 0006 的字串，Mac 上重跑映像驗收也通過。CRC 共 4,015 個符號。`rust_binder.ko` 例外和 v8 相同：不符 16、未版本化缺少 4。18 項測試通過。產物在 `out/build-2025-09-v<N>/`。

## 改寫的 7 筆

| patch | 原 commit | 為什麼套不上 | 怎麼改 |
| --- | --- | --- | --- |
| 0018 | ACK `aa134d3a4` UFS PM QoS mutex 初始化 | 上下文是 0017 之後的程式碼，行號不同 | 照原 patch：`mutex_init(&to_hba_priv(hba)->pm_qos_mutex)` 移到 `ufshcd_init()` 前段，改動與原 patch 相同 |
| 0040 | stable `cf4a9e1bc812` f2fs `write_end_io` UAF | stable 版是 page 介面，ACK 2025-09 的 f2fs 已是 folio 版 | 照 upstream `ce2739e482bc` 的 folio 寫法，把 `cp_wait` 喚醒移到 `folio_end_writeback()` 之前 |
| 0041 | stable `7be222de96c0` f2fs `nr_pages` UAF | 同上 | 改用 LunaKernel r21 的 folio 版，在 0040 之後可直接套用 |
| 0042 | stable `86ab00cf81d4` erofs `sync_decompress` UAF | ACK 的欄位是 `sbi->opt.sync_decompress`，註解也不同 | 照 upstream 的做法，把設定移到送出解壓 work 之前。和 LunaKernel 改寫版內容相同；該檔的 hunk 行數有誤，無法直接套用 |
| 0070 | stable `debfbc047196` `push_rt_task` race | ACK 2025-09 帶 proxy execution，重新驗證改由 `rt_revalidate_rq_state()` 處理 | 手機沒開 `sched_proxy_exec=`，實際走 `__rt_revalidate_rq_state()`。在這裡改用 upstream 的檢查：task 必須仍是 `pick_next_pushable_task()` 挑出的那一個。`sched.h` 的 `__revalidate_rq_state()` 由 deadline 共用，沒動 |
| 0120 | stable `38bccb927d83` af_unix `unix_stream_data_wait()` UAF | 只差 `unix_stream_read_generic()` 的區域變數宣告順序 | 其餘 6 個 hunk 原樣套用，`last_len` 宣告手動刪除 |
| 0121 | stable `ebbebf6cee95` MLD delayed work UAF | 上下文的 `mc_assert_locked()` 在 6.12.38 不存在 | 改用 LunaKernel r21 的版本，改動行與 upstream 完全相同 |

## 補上的前置 commit

第一次編譯 v12 失敗：`include/net/sock.h` 找不到 `hlist_nulls_replace_init_rcu()`。原因是 0077、0078 的 ehash race 修正需要 stable 的前置 commit `6b9cbefb73c3`（upstream `9c4609225ec1`，「rculist: Add hlist_nulls_replace_rcu() and hlist_nulls_replace_init_rcu()」）。它帶 `Stable-dep-of` 標記，篩選時被當成前置 commit 排除；第 0 步的連續套用測試只檢查文字能不能套上，抓不到編譯依賴。

補成 0076，只在 `rculist_nulls.h` 新增 static inline，不影響 KMI，原本 0076 之後的編號後移一號。之後用 `scripts/backport/dep_check.py` 對所有已採用的 stable 修正反查 `Stable-dep-of` 指向它們、又不在基底的前置 commit，共 7 個：

| 前置 commit | 對應的修正 | 處理 |
| --- | --- | --- |
| `6b9cbefb73c3` rculist helper | 0077、0078 ehash race | 補成 0076 |
| `d598eecb1615`、`5d218607febb`、`df81440519e1`（tcp） | 0113 challenge ACK | 不需要：0113 只用到 6.12 已有的 `tcp_rsk(req)->last_oow_ack_time`，編譯也通過。前者會重排 KMI 型別 `struct tcp_sock`，不能加 |
| `fbbed1834fcc`（MLD lockdep 註解） | 0121 MLD UAF | 不需要：只是上下文，已改用 LunaKernel 版 |
| `974339e126c1`、`09737c4fb106`（erofs） | 0042 sync_decompress UAF | 不需要：只是欄位改名與上下文，已改寫 |

## 實作時排除的 6 筆

改寫前先確認 6.12.38 是否真的有那個 bug：

| 原 commit | 判斷 | 依據 |
| --- | --- | --- |
| `e63032dc7150` binder `binder_thread_release()` UAF | 基底已有 | 基底已有更完整的 `2df1e89cb`：`binder_free_transaction()` 在 `t->lock` 底下讀 `to_proc`，還 pin 了 `target_thread` |
| ACK `5f93a67a7` f2fs atomic file 原子性損毀 | 基底已有 | `f2fs_inode_dirtied()` 已設定 `FI_ATOMIC_DIRTIED`，而且含後續的 `FI_ATOMIC_COMMITTED` 判斷（`70bc670f4`） |
| `db81ad20fd8a` af_unix `scc_index` 初始化 | 基底已有 | Google 已用 UPSTREAM `0de7c0db0` 補進 2025-09，四處改動都在。後續的 commit 改了上下文，所以反向套用沒偵測到 |
| `f3886f075c1f` slab `obj_exts` race | 不適用 | race 由 `f7381b911640`（無條件標記配置失敗）引入，這個 commit 不在基底。基底只在 `new_slab` 時標記，那時別人還存取不到 |
| `156cc63691c1` writeback `inode_switch_wbs_work_fn()` UAF | 不適用 | bug 來自 stable 的前置 commit `fabfc1fcd`（llist 迴圈）。基底仍是每個 isw 一個 RCU work |
| `44ddd7b1ae0b` `netlink_unicast()` 無限重試 | 不適用 | bug 由 `ae8f160e7eb2`（rmem wraparound 修正）引入，這個 commit 不在基底。基底的 `netlink_attachskb()` 還是舊寫法 |

## 批次 6：netlink rmem wraparound（2026/10/3 追加）

候選清單的「範圍外追加建議」，Jason 10/3 同意補做。`4b8e18af7bea`（upstream `ae8f160e7eb2`）修 `sk_rmem_alloc` 加上 skb 後溢位繞回、接收緩衝區限制失效的問題；標題沒有命中嚴重性關鍵字，篩選時漏掉。後三筆都是它的後續修正，包含原本判為不適用的 `44ddd7b1ae0b`：引入那個 bug 的就是 `4b8e18af7bea`，現在一起補上。四筆只改 `net/netlink/af_netlink.c`，依序直接套用，`dep_check.py` 找不到前置 commit，KMI 風險低。

## v13 實機（2026/10/3）

Jason 用無線 ADB 時，直接以 ReSukiSU 管理器刷入 v13 的 AnyKernel3 ZIP（`myron-kmi5-3fc3f57b6209-AnyKernel3.zip`，SHA-256 `6ae1e76b…`），跳過 v9～v12 與暫存重封裝驗收。開機成功，開機約 5～8 分鐘時檢查：

| 項目 | 結果 |
| --- | --- |
| 核心 | `6.12.38-android16-5-g4b4d49357977-4k`，slot `_a` |
| boot_a／init_boot_a | `73f33b78…`／`a4ed45c0…`（原廠 init_boot） |
| 模組 | 616 個，`rust_binder`、`kernelsu` 未載入 |
| 顯示 | `drmModeAtomicCommit failed` 0 次；`valid clone check ignored` 1 次 |
| UFS | 錯誤訊息 0，`ufshcd_err_handler` 未觸發 |
| dmesg WARNING | 3 個，和原廠 6.12.23、v7 完全相同（PMIC arbiter 2 次、Unprivileged eBPF 1 次）；沒有 oops、BUG、refcount、stall |
| root | ReSukiSU `v4.2.0-rc3-239e1e88@ReSukiSU`、`Work mode: Built-in`；SUSFS v2.3.0 已初始化 |
| 其他 | SELinux Enforcing；BBR 可用；開機後沒有 tombstone，crash buffer 空；`/sdcard`（FUSE）讀寫正常；zram swap 使用中 |

和 v5（約 1 小時的 dmesg）相比，v13 開機後第 57～58 秒出現一陣 `msm_vidc` 的 HEVC 解碼 session 錯誤（firmware 回報 `0x4000008`，約 690 行），之後沒有再出現。同一時間 logcat 是小米相簿（`com.miui.gallery` 的 `hi_thumb`）在產生縮圖。後來在 v14 確認是 iCloud 匯出的 HEIC 照片，不是影片，見下方 v14 段落。

無線 ADB 的備註：macOS 的區域網路權限擋住 adb 直接連手機（`No route to host`），用 Python 在 127.0.0.1 開轉送後，`adb connect 127.0.0.1:<埠>` 才連得上。手機重開機後，無線偵錯的埠號和 IP 都可能改變，要用 `dns-sd -B _adb-tls-connect._tcp` 重新找。

## v14 實機（2026/10/3）

Jason 用同樣方式刷入 v14 的 AnyKernel3 ZIP（`myron-kmi5-b246ec5eeede-AnyKernel3.zip`，SHA-256 `2a82a922…`）。開機約 3 分鐘時檢查，結果與 v13 相同：

| 項目 | 結果 |
| --- | --- |
| 核心 | `6.12.38-android16-5-g4b4d4935922a-4k`，slot `_a` |
| boot_a／init_boot_a | `b4b67c87…`／`a4ed45c0…`（原廠 init_boot） |
| 模組 | 616 個，`rust_binder`、`kernelsu` 未載入 |
| 顯示 | `drmModeAtomicCommit failed` 0 次；`valid clone check ignored` 1 次 |
| UFS | 錯誤訊息 0，`ufshcd_err_handler` 未觸發 |
| dmesg WARNING | 3 個，與原廠相同；沒有 oops、BUG、refcount、stall |
| root | ReSukiSU Built-in；SUSFS v2.3.0 已初始化 |
| 其他 | SELinux Enforcing；BBR 可用；沒有 tombstone，crash buffer 空；`/sdcard` 讀寫正常 |

HEVC 解碼的 session 錯誤（`0x4000008`）這次在開機後第 49 秒出現，共 23 行，同一時間 logcat 也是相簿的 `hi_thumb` 在活動。兩次開機都只有 HEVC session（`hevcD_56`～`58`）出錯，同次開機的 H.264 session（`avcD_27`、`avcD_28`）沒有。

追查結果與核心無關：

- 推兩支 10 秒的 HEVC 測試影片到手機（8-bit Main、10-bit Main10，1080p，ffmpeg libx265 產生），Jason 確認在相簿播放都正常。
- 開相簿時又出現約 33 個 HEVC session 錯誤。logcat 顯示這些 session 是相簿用 `HeifDecoderImpl` 解 HEIC 照片（HEVC profile 8，Main Still Picture），不是影片。
- 失敗的都是 `/storage/emulated/0/Pictures/icloud/IMG_*.HEIC`，也就是 iCloud 匯出的 iPhone 照片。該資料夾 1,189 個檔案中有 79 個 HEIC，這段時間有 29 張解碼失敗。
- 硬體解碼器 `c2.qti.hevc.decoder` 失敗後，相簿改用純軟體的 `c2.android.hevc.decoder` 也失敗，回報 `work failed to complete: 14`（`C2_CORRUPTED`）。軟體解碼在使用者空間進行，不受核心影響，所以是這批 HEIC 檔案本身或相簿對它們的支援問題。

## v15：預設 TCP 擁塞控制改為 BBR（2026/10/3）

Jason 指定預設 TCP 擁塞控制改為 BBR、開機就套用。原本 0005 只把 BBR 編進核心，預設維持 cubic。手機上沒有 init 腳本或 root 模組設定 `tcp_congestion_control`，核心預設值就是開機後的值，所以直接改核心設定：

- `0136-default-tcp-congestion-bbr.patch`：只改 0005 建立的 `myron_tuning.fragment`，`CONFIG_DEFAULT_CUBIC=y` 換成 `CONFIG_DEFAULT_BBR=y`。
- `config/kernel-policy.json` 的 `CONFIG_DEFAULT_TCP_CONG` 同步改為 `"bbr"`，映像驗收會從 Image 內嵌的設定核對。

v15 Image 讀出 `CONFIG_DEFAULT_TCP_CONG="bbr"`，cubic 仍內建可選。CRC 與其他驗收和 v14 相同。AnyKernel3 ZIP（`myron-kmi5-936cf7b208f0-AnyKernel3.zip`，SHA-256 `9ddf1795…`）已推到手機 `/sdcard/Download/`。

Jason 刷入後開機約 3 分鐘檢查：核心 `6.12.38-android16-5-g4b4d4935f92d-4k`，boot_a `c8c6b082…`，init_boot 原廠；`tcp_congestion_control` 為 `bbr`，`ss -tin` 列出的 95 條 TCP 連線全部是 bbr。616 個模組、`drmModeAtomicCommit failed` 0 次、UFS 錯誤 0、dmesg WARNING 與原廠相同、沒有 tombstone、ReSukiSU Built-in、SUSFS 已初始化、`/sdcard` 讀寫正常。

## 批次 7：Image 內的高通相關修正（2026/10/3）

先前的掃描範圍沒有涵蓋 Gunyah、SCMI、GIC ITS 與 qcom-geni。查核過程與完整分類見 [references-6.12.md 的高通段落](references-6.12.md#高通2026103-查)。Jason 同意後實作建議的 4 筆，都直接套用，沒有改寫：

| patch | 來源 | 修正 |
| --- | --- | --- |
| 0137 | ACK `6ed0366cc367` | `gunyah_vm_start()` 每次成功啟動 VM 都漏釋放 `resources` |
| 0138 | ACK `c6b71e31c280` | 分享 VM 記憶體時，binding 在計數後變多會寫出陣列範圍 |
| 0139 | ACK `f776caa5cc69` | Gunyah RM 重複回覆造成 use-after-return，記憶體損毀後卡在 `complete()` |
| 0140 | stable `96dd9e3e48ad`（6.12.110） | SCMI 的 device request 查 IDR 時加 RCU |

v16 Image `30c25089a4a2…`：KMI `6.12-android16-5`、4 KB、ReSukiSU 與 SUSFS 都在，預設擁塞控制仍是 bbr。CRC 4,015 個符號缺少 0、不符 0，`rust_binder.ko` 例外 20 個和之前相同。AnyKernel3 ZIP 是 `myron-kmi5-30c25089a4a2-AnyKernel3.zip`（SHA-256 `e8347e72…`），已推到手機 `/sdcard/Download/`，手機上核對 SHA-256 相同。

## v16 實機（2026/10/3）

Jason 用 ReSukiSU 管理器刷入，開機約 3 分鐘檢查：

| 項目 | 結果 |
| --- | --- |
| 核心 | `6.12.38-android16-5-g4b4d49350df7-4k`，boot_a `7843acd9…`，init_boot 原廠 `a4ed45c0…` |
| 模組 | 616 個 |
| 顯示 | logcat 沒有 `drmModeAtomicCommit failed` |
| UFS | 沒有錯誤，`ufshcd_err_handler` 0 次 |
| dmesg | WARNING 只有 `spmi-pmic-arb.c:352` 兩次，與 v14 相同；沒有 Oops |
| Gunyah | `gunyah_rm_rx` 143 次、`gunyah_rm_tx` 10 次、`gunyah_vcpu` 3,439 次，VM 在跑；Gunyah 相關訊息與 v14 相同 |
| SCMI | cpufreq 兩個 policy 都是 `scmi`、governor `walt`，頻率正常變動；6 個 SCMI driver 都綁定。SCMI 訊息與 v14 相同，包括韌體不支援 fastchannel 的提示 |
| root | ReSukiSU `Work mode: Built-in`，SUSFS v2.3.0 已初始化 |
| 其他 | 沒有新的 tombstone，`/sdcard` 讀寫正常，`tcp_congestion_control` 為 bbr |

dmesg 與 logcat 在 `out/v16-device/`。

## 批次 8：stable 6.12.112 補掃（2026/10/3）

6.12.112 在 10/3 發布，[候選清單](kmi6-backport-candidates.md) 只掃到 6.12.111。這次用同一套腳本與篩選條件補掃，但套用檢查改對 v16.1 的樹（基底加 0001～0140），不再對 v8。

- 6.12.112 共 850 個 commit，落在掃描子系統的 233 個。
- 自動篩選：未編進核心 85、沒有嚴重性字樣 49、只是前置 34、手機沒用到的功能 8、基底已有 2，剩 55 筆。
- 被修的 commit 是否在樹上：stable 會收，表示 bug 存在 6.12.111；再排除被修的 commit 是 6.12.39～6.12.112 才回推、而我們沒有拿的情況。55 筆中只有 dwc3 的 `5f359265f616` 屬於這種，它修的是 6.12.112 自己回推的 commit。
- 6.12.112 沒有 commit 修到我們已 backport 的 254 個 commit（`Fixes:` 與內文都比對過）。內文提到的只有 0086、0090，就是下面 0146、0147 補完的那兩份。
- 逐筆判斷：建議 7、可選 31、不建議 5、不適用 12，完整清單在 [stable-6.12.112-candidates.tsv](stable-6.12.112-candidates.tsv)。

| patch | stable commit | 修正 | 套用 |
| --- | --- | --- | --- |
| 0141 | `a500df43cde0` | arm64 上 anon_vma 發布前缺 release barrier，兩個執行緒同時在相鄰 VMA 觸發 page fault，會鎖到舊的 root 而 hung task | 改寫 |
| 0142 | `d9ae467e617c` | 多執行緒 exec 在 `de_thread()` 之後失敗，POSIX CPU timer 留在佇列裡被釋放 | 3-way |
| 0143 | `1f73253add83` | `SIOCGSTAMP` 與 `bind()` 同時改 `sk_flags`，清掉 `SOCK_RCU_FREE`，UDP socket UAF | 直接 |
| 0144 | `e3ea71cb1408` | TCP Fast Open 的 SYN-ACK 換掉 SYN skb 後，retransmit hint 指向已釋放的 skb | 直接 |
| 0145 | `3e3394a13b60` | IPv6 listener 被 `close()` 時，`tcp_v6_do_rcv()` 無鎖計入 `sk_forward_alloc` | 直接 |
| 0146 | `5045aa25f379` | 介面註銷時與 uncached route 競爭，洩漏 dst 與 net_device 參考；0086 沒修到的部分 | 直接 |
| 0147 | `fb38fb7420d5` | xfrm state 第二次刪除時經 `LIST_POISON` 寫入；0090 漏掉的 `state_cache` 兩個 list | 直接 |

0141 的改寫：6.12.38 的 `__anon_vma_prepare()` 接著呼叫 `anon_vma_chain_link()`，上游是 `anon_vma_chain_assign()`，所以 rmap.c 那段套不上。修正本身只有把 `vma->anon_vma` 的 store 換成 `smp_store_release()`，mm/vma.c 的註解照原樣。0142 以 3-way 合併，增減的行與原 commit 相同；timer 清理移到 `de_thread()` 之後、`unshare_files()` 之前，位置與上游一致。匯出的 0141～0147 從 v16.1 的樹依序套用，結果與逐筆 commit 的樹完全相同。

重跑方式（LXC 112）：

```sh
cd /src/scripts/backport
BASE=$(python3 build_tree.py)
KMI6_BASE=$BASE STABLE_RANGE=v6.12.111..v6.12.112 KMI6_OUT=/root/kmi6scan-112 python3 scan.py
KMI6_OUT=/root/kmi6scan-112 python3 filter.py
```

`build_tree.py` 只動 `/gki/kmi6` 的 detached HEAD，`bp` 分支不變。`/gki/stable` 是 shallow clone，6.12.38 以前的歷史不在裡面，不能用 `merge-base --is-ancestor` 判斷被修的 commit 在不在樹上。

這批編成 v18。v17 是 K3 把小米 cpq、kshrink_slabd 編進 Image 的版本，原廠 first stage 的 `cpq.ko` 會因此載入失敗，沒有刷過就撤回了（`29eae3a`）。

v18 Image `fdea557f4842…`，版本字串 `6.12.38-android16-5-g4b4d4935db3b-4k`：KMI `6.12-android16-5`、4 KB，設定與 v16 相同。CRC 4,015 個符號缺少 0、不符 0，`rust_binder.ko` 例外 20 個和之前相同；原廠模組撞名 0（`kernelsu` 列為例外）。vmlinux.symvers 與 v16 完全相同，System.map 只有 exec.c、sock.c 行數變動造成的 initcall 名稱與 linker veneer 不同。AnyKernel3 ZIP 是 `myron-kmi5-fdea557f4842-AnyKernel3.zip`（SHA-256 `ddf1c98c…`）。

## v18 實機（2026/10/3）

Jason 用 ReSukiSU 管理器刷入，開機約 2 分鐘檢查，對照 v16 在 310 上的紀錄（`out/v16-310-device/`）：

| 項目 | 結果 |
| --- | --- |
| 核心 | `6.12.38-android16-5-g4b4d4935db3b-4k`，310，slot a；boot_a `6fb660a8…`，init_boot 310 原廠 `0a9871f4…` |
| boot_a 內容 | 讀回比對：核心與 v18 Image 位元相同，標頭除核心大小外與刷入前的 `aa2a63e6…` 相同 |
| 模組 | 616 個，清單與 v16 完全相同；原廠 cpq（sda 排程器 `[cpq]`）與 kshrink_slabd 照常運作 |
| 顯示 | logcat 沒有 `drmModeAtomicCommit failed` |
| UFS | 沒有錯誤，`ufshcd_err_handler` 0 次 |
| dmesg | WARNING 只有 `spmi-pmic-arb.c:352` 兩次與 eBPF 提示，與 v16 相同；沒有 Oops、stall、lockup |
| Gunyah | `gunyah_rm_rx` 131 次、`gunyah_rm_tx` 4 次，vcpu 中斷在跑 |
| SCMI | 兩個 policy 都是 `scmi`、governor `walt`，頻率正常 |
| root | ReSukiSU `Work mode: Built-in`，SUSFS v2.3.0 已初始化 |
| 網路 | Wi-Fi IPv4／IPv6 ping 正常，wlan0 與 IMS（rmnet_data1）都通過驗證；xfrm 有 2 個 SA、3 條 policy 在用 |
| 其他 | 沒有新的 tombstone，`/sdcard` 讀寫正常，擁塞控制 bbr，`tcp_fastopen` 1 |

dmesg、logcat、模組清單與讀回的 boot_a 在 `out/v18-device/`。萬一要退回，fastboot 寫 `local-backup/eu310/boot-v16-on-310.img`（`aa2a63e6…`）就是 v16.1。

## 批次 9：參考 LunaKernel 的效能 backport（2026/10/4）

10/4 重讀 LunaKernel 主分支（最後推送 2026/9/1）。10/3 的查核只看了 `patches/backports/`，`patch.sh` 另有一段「Selected upstream performance backports」，6 筆沒有記到 [references-6.12.md](references-6.12.md)。兩邊合計 11 筆效能改動。設定層沒有可以參考的：它和原廠一樣是 `LTO_NONE`，預設 TCP 維持 cubic，省電 workqueue 與 tmpfs xattr 0005 已經有了。

逐筆判斷用到的實機狀態（2026/10/4，v18 開機中，adb 只讀）：

| 項目 | 手機上 |
| --- | --- |
| I/O 排程器 | sda `[cpq]`，其他 LU 是 mq-deadline；UFS 每個 CPU 一個 hw queue（`mq/0/cpu_list` 為 0） |
| /data | f2fs，`extent_cache`、`nogc_merge`、`mode=adaptive`，沒用壓縮 |
| memcg | v1 掛在 `/dev/memcg`，163 個 cgroup |
| wbt | sda `wbt_lat_usec` 2000 |
| PSI | 系統 PSI 有開，cmdline 有 `cgroup_disable=pressure` |
| MGLRU | `lru_gen/enabled` 0x0000 |

採用 6 筆，另外收 2 筆修正：

| patch | 來源 | 內容 | 手機上的依據 |
| --- | --- | --- | --- |
| 0148 | stable `a83264d8dfba`（6.12.104） | 修正：`tcp_measure_rcv_mss()` 不再隨 scaling_ratio 調低 `rcv_ssthresh` | v18 呼叫 `tcp_set_window_clamp()`，bug 在樹上；upstream 回報從 6.1 升到 6.12 後 P99 延遲約十倍。候選清單原列可選 |
| 0149 | stable `44480f7e3f83`（6.12.96） | 修正：`f2fs_balance_fs()` 前景 GC 前先送出快取的 IPU／OPU bio，避免與 truncate 互等 | /data 是 `nogc_merge`，走的正是這條路徑。候選掃描時因 Stable-dep-of 被排除 |
| 0150 | mainline `222bc257a151`（v7.2-rc1） | f2fs 覆寫 EOF 內的區塊時，extent cache 命中就不查 inode folio | /data 開了 `extent_cache`、沒用壓縮 |
| 0151 | mainline `60cada258dfe`（v6.16） | memcg 已達 flush 門檻就不再往上更新祖先 | 163 個 memcg，每次 page charge 都會進來 |
| 0152 | mainline `3ec955713d96`（v6.14） | timer base 指標只取一次 | 只改 static inline，行為不變 |
| 0153 | mainline `0ae1ac7335ca`（v6.19） | recvmsg 的 `tcp_rcv_space_adjust()` 改用快取的 `tcp_mstamp` | arm64 讀時鐘本來就便宜，收益比 x86 小 |
| 0154 | mainline `d8b96a79622e`（v6.17） | 未被節流的寫入完成時，`wbt_done()` 少一次判斷 | sda 的 wbt 有開 |
| 0155 | stable `d8d7b0043acc`（6.12.91） | hrtimer 中斷處理期間重啟本 CPU 最早到期的 timer，不立刻重設 clock event | 收益小 |

8 份依序疊在 v18 的樹上全部直接套用，增減行與 upstream 原 commit 逐份比對相同。GitHub 搜尋 mainline 沒有找到這 8 筆的後續修正或 revert（沒有逐一對 lore）。

不採用：

| commit | 內容 | 原因 |
| --- | --- | --- |
| `9cbbac29d752` | 拿掉 `__submit_bio()` 自動加的 plug | sda 有 cpq 排程器。沒有 plug 時，`blk_mq_submit_bio()` 對 `RQF_USE_SCHED` 的 request 呼叫 `blk_mq_run_hw_queue(hctx, true)`，改由 kblockd 非同步派送；有 plug 時，`blk_finish_plug()` 在送出的 CPU 上同步派送。upstream 的數字是無排程器、直接派送的情境。會改到原廠的 I/O 行為，沒有 A/B 實測不收 |
| `b0bc1c75f304` | PSI irqtime 增量為 0 時提早返回 | `cgroup_disable=pressure` 讓所有 task 都在 `psi_system`，context switch 的呼叫在計算前就因為同一個 group 返回；tick 的呼叫因上一次 tick 本身的中斷時間，增量幾乎不會是 0 |
| `ff1de90dd7a6`、`29cf3b31e8cc` | EAS 的 cpumask 判斷與 runnable boosting 算式 | 選核由 WALT 接手，governor 也是 WALT，這兩段走不到 |
| `19999e479c2a` | MGLRU 主動回收達到目標就停 | MGLRU 實機關閉 |
| `d860974a7e38` | f2fs DIO 覆寫只檢查第一段映射 | 只影響 O_DIRECT，手機上應該少見（未實測） |

`patch.sh` 另外 9 筆修正：futex requeue-PI lockup 在 ACK 基底已有；blk-cgroup rstat 是 0013，MLD query UAF 是 0099；f2fs ACL、listxattr 的邊界檢查原本就列可選；f2fs gc_merge 路徑那筆不適用（`nogc_merge`）；KVM 那筆手機用不到（dmesg：「KVM is not available」）。erofs 目錄尾項與 ext4 xattr 的越界讀取是 AOSP `android16-6.12-lts` 的 commit，這次沒有逐筆查核。

Stable-dep-of 的盲點：候選掃描依序排除的 366 筆前置 commit 中，0149 本身就是修正。這 366 筆裡有編進核心、標題或說明帶嚴重性字樣的有 90 筆（UAF 28、死鎖 15、race 12），下一輪補掃可以從這 90 筆開始。

這批編成 v19。Image `3e58b2a92be4…`，版本字串 `6.12.38-android16-5-g4b4d49351f54-4k`：KMI `6.12-android16-5`、4 KB，設定與 v18 相同。CRC 4,015 個符號缺少 0、不符 0，`rust_binder.ko` 例外 20 個和之前相同；原廠模組撞名 0。vmlinux.symvers、modules.builtin 與 v18 完全相同；System.map 多了 0149 新增的 `f2fs_submit_all_merged_ipu_writes`，其餘差異是 memcontrol.c 行數變動造成的 initcall 名稱，和 2 個 linker veneer。AnyKernel3 ZIP 是 `myron-kmi5-3e58b2a92be4-AnyKernel3.zip`（SHA-256 `db10db6b…`），已推到手機 `/sdcard/Download/`。

刷入前的暫存重封裝驗收：目前 boot_a 是 v18 的 `6fb660a8…`，用 310 原廠 boot 重封裝通過，boot_a 未改變。

## v19 實機（2026/10/4）

第一次刷入被安裝器擋下，訊息是「init_boot 與已核對的原廠基準不同」。查出 init_boot_a 在 10/3 21:27（v18 實機檢查之後）被 ReSukiSU 管理器以 LKM 方式修補，SHA-256 變成 `77db7bde…`：

- ramdisk 多了管理器內附的 `kernelsu.ko`（`v4.2.0-rc3-80c0e190@ReSukiSU`，vermagic 6.12.76）。
- `init` 換成 ksuinit，原本的改名為 `init.real`；另有 `ksu_config`（`bundled=1`）、`ksu_block_modules`、`stock_image.sha1`。
- 10/4 06:56 用它開過一次機，手機正常，跑的仍是內建 ReSukiSU（`/proc/modules` 沒有 kernelsu）。開機早期的 dmesg 已被洗掉，看不到 ksuinit 當時的訊息。

管理器修補前把原廠映像備份在 `/data/adb/ksu/ksu_backup_206b5247…`，核對 SHA-256 是 310 原廠的 `0a9871f4…`。經 Jason 同意，用 adb 把它寫回 init_boot_a，讀回確認後再刷 v19。修補過的映像存在 `local-backup/eu310/init_boot_a-lkm-20261003.img`。核心已內建 ReSukiSU，管理器的 LKM 安裝不要再用。

刷入後約 2～4 分鐘檢查，對照 v18（`out/v18-device/`）：

| 項目 | 結果 |
| --- | --- |
| 核心 | `6.12.38-android16-5-g4b4d49351f54-4k`，310，slot a；boot_a `b9a6f8c3…`，init_boot 310 原廠 `0a9871f4…` |
| boot_a 內容 | 讀回與刷入前暫存重封裝的映像位元相同 |
| 模組 | 616 個，清單與 v18 完全相同 |
| 顯示 | logcat 沒有 `drmModeAtomicCommit failed` |
| UFS | 沒有錯誤，`ufshcd_err_handler` 0 次 |
| dmesg | WARNING 只有 `spmi-pmic-arb.c:352` 兩次與 eBPF 提示，與 v18 相同；沒有 Oops、stall、lockup、hung task |
| Gunyah | `gunyah_rm_rx` 148 次、`gunyah_rm_tx` 11 次，vcpu 中斷在跑 |
| SCMI | 兩個 policy 都是 `scmi`、governor `walt`，頻率正常 |
| root | ReSukiSU `Work mode: Built-in`，SUSFS v2.3.0 已初始化 |
| 網路 | 行動網路 IPv4／IPv6 ping 正常；LTE internet 與兩張卡的 IMS（MMTEL）都通過驗證 |
| Wi-Fi | 設定裡是關的（`wifi_on` 0，開機後沒有切換紀錄），wlan0 驅動正常但沒連線；Wi-Fi、IWLAN 與 xfrm 這次沒驗到 |
| 其他 | 沒有新的 tombstone，`/sdcard` 讀寫正常，擁塞控制 bbr，`tcp_fastopen` 1 |

dmesg 有 176 次 `msm_vidc` 的 `session error 0x4000008`（heicD、hevcD 解碼 session），當時 Threads、微信、QQ 剛開機在載入媒體。v13（204 次）、v14（16）、v16（152）的實機紀錄也有同樣的錯誤，v18 與 v16-310 檢查時是 0，看起來跟開機後在跑的 app 有關，不是 v19 帶進來的。原廠核心下有沒有這些錯誤，沒有對照過。

dmesg、logcat、模組清單與讀回的 boot_a 在 `out/v19-device/`。要退回 v18，fastboot 寫 `out/v18-device/boot_a.img`（`6fb660a8…`）。

## 實機驗收（後續版本）

刷機前都要先問 Jason。只刷 `boot_a`，init_boot 維持原廠。每一版刷之前，先跑暫存重封裝驗收，指定目前 `boot_a` 的雜湊：

```sh
python3 scripts/repack_check.py --serial <adb 序號> --stock-boot local-backup/eu310/boot-stock-310.img \
  --image out/build-2025-09-v<N>/dist/Image --output out/repack-2025-09-v<N>/boot-from-stock.img \
  --expect-live-sha <目前 boot_a 的 sha256>
```

310 之後 `--stock-boot` 用 310 原廠 boot（309 的 `local-backup/device-boot_a.img` 也仍接受）。刷之前也看一下 init_boot_a 是不是原廠（310 是 `0a9871f4…`）：管理器的 LKM 安裝會改它，安裝器會以「init_boot 與已核對的原廠基準不同」拒絕，還原方式見 v19 實機。v18 刷入前的驗收：目前 boot_a `aa2a63e6…`，重封裝通過，boot_a 未改變。

每版要看的項目同 v8：

- 開機與螢幕：logcat 的 `drmModeAtomicCommit failed`，開機時出現 1 次屬正常。
- 模組數 616，只少 `rust_binder` 和舊 KernelSU。
- UFS 沒有錯誤，`ufshcd_err_handler` 沒有被觸發。
- dmesg 和 v8 相比，沒有新的 oops 或 WARN。
- ReSukiSU 是 `Work mode: Built-in`，SUSFS 有初始化。

v13 是一次跳過 v9～v12 刷上去的，日常使用若出現問題，可以依 v12 → v9 往回刷，縮小到某一批，再在那一批的 patch 裡找。用電腦回復時刷 `out/repack-2025-09-v8/boot-from-stock.img`（v8）。
