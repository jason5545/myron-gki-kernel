# KMI 6 時期修正的 backport 候選（2026/10/2）

目標是把 6.12.38 之後的穩定性與安全修正補進 myron 的 KMI 5 核心（v8：ACK `android16-6.12-2025-09` `1ad7be92` 加上 0001～0008），不改 KMI、不加功能、不改預設行為。

2026/10/2 Jason 確認範圍：建議清單全部做，需要改寫的也一起做。實作與編譯結果在 [kmi6-backport-batches.md](kmi6-backport-batches.md)。

## 結論

- 三個來源合併、去重後共 936 筆。整理時建議 128 筆，其中 115 筆可以直接套到 v8、13 筆需要改寫。
- 實作改寫時逐筆確認 6.12.38 是否真的有那個 bug，排除 6 筆：3 筆基底已有等效或更新的修正，3 筆的 bug 是由不在基底的 commit 引入。**最後建議 122 筆**：115 筆直接套用、7 筆改寫。
- 改寫前的 KMI 風險都是低，只有 1 筆是中（f2fs 內部函式宣告）。編譯後的 CRC 結果見批次文件。
- 115 筆可套用的 patch 依批次、依版本順序連續套在 v8 上全部成功；五批全部疊在一起也成功。只有 1 筆需要 3-way（`5e7ece24c5cb`）。
- 其餘：可選 561、不建議 58（其中 33 筆會改到 KMI 型別）、不適用 151、基底已有 35、重複 9。完整清單在 [`kmi6-backport-candidates.tsv`](kmi6-backport-candidates.tsv)。

| 批次 | 範圍 | 整理時建議 | 直接套用 | 改寫 | 實作時排除 |
| --- | --- | --- | --- | --- | --- |
| 1 | UFS／SCSI／block | 10 | 9 | 1 | 0 |
| 2 | f2fs／erofs／fuse／binder | 26 | 21 | 3 | 2 |
| 3 | mm／排程／核心 | 30 | 27 | 1 | 2 |
| 4 | 網路／netfilter | 52 | 48 | 2 | 2 |
| 5 | USB／HID | 10 | 10 | 0 | 0 |

## 範圍外的追加建議

netlink 的 rmem wraparound 修正 `4b8e18af7bea`（6.12.39，upstream `ae8f160e7eb2`）單獨試套用可以直接套上，但標題沒有命中嚴重性關鍵字而被篩掉。它和後續的 `f98c4cec7`、`42baf9977`、`44ddd7b1ae0b` 是同一組。下一輪可以一起補。

## 來源與篩選

| 來源 | 範圍 | 數量 |
| --- | --- | --- |
| linux-6.12.y stable | 6.12.39～6.12.111，16,411 個 commit（含 73 個版本號 commit） | 子系統範圍內 3,540 → 自動篩選後 824 |
| LunaKernel r21 | `r21-selected-backports.tsv` 29 列、`r21-independent/*.tsv` 43 列 | 72 |
| ACK `android16-6.12` | 基底之後的 ANDROID／UPSTREAM／FROMGIT commit 3,709 個，挑出 fuse-bpf、UFS、binder、f2fs、fscrypt、xhci 等修正 | 81 |
| ACK `android16-6.12-2025-09` | `1ad7be92` 之後只有 `4a49f9f60`（pKVM），手機 KVM 不可用（dmesg：「KVM is not available」），不適用 | 1 |

stable 的自動篩選依序排除：

| 排除原因 | 數量 |
| --- | --- |
| 基底已有（反向套用成功，或 3-way 結果與基底相同） | 72 |
| revert，或之後被 revert | 19 |
| 只是其他修正的前置（`Stable-dep-of:`） | 366 |
| 其他平台（聯發科、Exynos、Intel、Tegra 等） | 30 |
| 改的程式碼沒編進核心（模組或未啟用；只換 Image，原廠 `.ko` 不變） | 1,024 |
| 手機沒用到的功能（sched_ext、MGLRU、hugetlb、KVM、io_uring、MPTCP、nf_tables 等） | 195 |
| 標題與說明沒有 UAF、死鎖、race、資料損毀、NULL、越界、雙重釋放、崩潰等字樣 | 1,010 |
| 剩下（另保留 5 筆效能字樣） | 819 + 5 |

「是否編進核心」用 Makefile 加 v8 的 `.config` 判斷，Makefile 找不到時用 System.map 的函式名補判。KMI 風險對照 ACK 樹的 `gki/aarch64/abi.stg`：改到 STG 裡的結構、enum 或 KMI 符號簽名算高；新增宣告、static inline、內部結構算低。

## 依實機狀態判斷

篩選與人工判斷用到的實機資訊（2026/10/2 從手機讀取，v8 開機中）：

| 項目 | 實機 | 影響 |
| --- | --- | --- |
| `/data` | f2fs，`mode=adaptive`、`atgc`、`nogc_merge`、`inlinecrypt`，壓縮寫入 0 | 壓縮、lfs、gc_merge 修正不適用；atomic write、extent cache、GC 修正有用 |
| 系統分割區 | erofs（dm-verity），apex 是 ext4 loop 唯讀 | erofs 執行期修正有用；損毀映像防護價值低；ext4 寫入路徑幾乎不會走 |
| swap | 16 GB zram，沒有 swapfile | swap 修正有用，swapfile 修正不適用 |
| MGLRU／THP | `lru_gen/enabled` 0x0000；THP `always`，shmem THP `never` | MGLRU 不適用；匿名 THP 修正有用 |
| cpufreq | governor 是高通 WALT（`sched_walt` 模組） | schedutil 修正不適用；EAS 選核由 WALT 接手 |
| UFS | MCQ 模式，`rpm_lvl=1`、`spm_lvl=3` | MCQ 修正有用；`rpm_lvl=0` 才有用的修正不適用 |
| 網路 | qdisc 只有 pfifo_fast、mq、clsact；沒有 pfkey socket；沒有 bridge | 大部分 net/sched、af_key、bridge 修正不適用 |
| 核心參數 | `kasan=off`、`cgroup_disable=pressure`、`panic_on_rcu_stall=1`、`kvm-arm.mode=protected`（但 KVM 不可用） | KASAN、cgroup PSI、pKVM 修正不適用；RCU stall 修正價值高 |
| 核心設定 | 沒有 `IP_SET`、`IP6_NF_MATCH_EUI64`、`BLK_DEV_THROTTLING` | LunaKernel 的 ipset 系列不適用 |

## 第 0 步：對資料模擬驗收

- v8 的 CRC 基準在 Mac 重跑：4,015 個符號，缺少 0、不符 0；`rust_binder.ko` 例外為不符 16、未版本化缺少 4，與 v8 相同。18 項測試通過。
- 所有候選都在 v8 的樹上重跑過套用、反向套用與 3-way，不是只對 ACK 原始基底。這次重跑抓到兩件事：
  - stable `2fcc2fc21cae` 就是 0008，判定為基底已有。
  - v8 的 0007 等於 upstream `f966e02ae521`、`e23ef4f22db3`、`14be351e5cd0` 三個 patch 合併後的結果。ACK 的 `7ef00d345`、`459c818f8`、`a460b437a` 都已涵蓋。接在後面的 `79bb460d3` 可以直接套用，列在批次 1。
- 115 筆可套用的建議 patch 分批連續套用，0 失敗。
- 沒有發現與驗收條件互斥的項目。

## 限制

- 「可選」裡有 434 筆是自動篩出、沒有逐項審的修正，判斷依據寫在 TSV 的「說明」欄。
- 篩掉的 1,010 筆沒有嚴重性字樣，裡面可能還有實際的錯誤修正。
- KMI 判斷是靜態比對，最後以編譯後的 CRC 為準。出現新的 CRC 不符，就拿掉那份 patch 或改寫。
- 能套用不代表語意正確（上下文相同但前提可能不同）。每批都要實機驗收，項目同 v8：`drmModeAtomicCommit failed`、616 個模組、UFS 錯誤與 `ufshcd_err_handler`、dmesg 的新 oops／WARN、ReSukiSU 與 SUSFS。

## 重跑方式

掃描腳本在 [`scripts/backport/`](../scripts/backport/)，在 LXC 112 上執行。用到 `/gki/stable`（stable blobless clone）、`/gki/hist`（ACK blobless clone），以及獨立的檢查 repo `/gki/kmi6`。`/gki/kmi6` 透過 alternates 借用前兩者的物件，不動 `/gki/common`。

| 腳本 | 用途 |
| --- | --- |
| `scan.py` | 掃 stable、產生 patch、判斷套用狀態與是否編進核心 |
| `kmi_stg.py` | 依 `abi.stg` 重算 KMI 風險 |
| `check_luna.py`、`check_ack.py` | LunaKernel 清單與 ACK commit 的套用檢查 |
| `recheck_v8.py` | 在 `/gki/kmi6` 建 v8 樹（基底加 `patches/series`），全部重跑 |
| `seq_check.py` | 建議清單分批連續套用 |
| `decisions.py`、`gen_candidates.py`、`make_doc.py` | 人工判斷、產生 TSV 與這份文件的表格 |
| `apply_chain.py`、`export_chain.py` | 實作時依序疊到 `/gki/kmi6` 的 `bp` 分支，再匯出成 `patches/` 的檔案 |

## 建議清單（122 筆）

「狀態」是對 v8 的樹（ACK `1ad7be92` 加上 0001～0008）實際試套用的結果。「來源」寫 LunaKernel 的，表示 LunaKernel r21 也採用了。

### 批次 1：UFS／SCSI／block（10 筆）

| commit | 子系統 | 類型 | 狀態 | KMI 風險 | 建議理由 | 標題 |
| --- | --- | --- | --- | --- | --- | --- |
| `3baeec23a82e` | block | 修正 | 可套用 | 低 | UFS 錯誤處理會 quiesce tagset；改用 RCU 避免死鎖 | block: Use RCU in blk_mq_[un]quiesce_tagset() instead of set->tag_list_lock |
| `5b029dd854f8`（LunaKernel） | block | 修正 | 可套用 | 低 | blk_time_get_ns() 被搶占時回傳 0（LunaKernel 已採用） | block: fix race in blk_time_get_ns() returning 0 |
| `a09280c39ea5` | block | 修正 | 可套用 | 低 | Android init 開機時會寫 queue sysfs；store 期間 GFP_NOIO 避免回收遞迴死鎖 | block: mark GFP_NOIO around sysfs ->store() |
| `bbebd9425cad` | block | 修正 | 可套用 | 低 | blk-cgroup rstat flush UAF | blk-cgroup: fix UAF in __blkcg_rstat_flush() |
| `dfc8292a1d67`（LunaKernel） | mm | 修正 | 可套用 | 低 | cgroup writeback（CGROUP_WRITEBACK=y）釋放時 UAF（LunaKernel 已採用） | mm: blk-cgroup: fix use-after-free in cgwb_release_workfn() |
| `64ae21b9c4f0` | scsi | 修正 | 可套用 | 低 | SCSI 錯誤處理在最後一個完成與 EH 競爭時沒被喚醒，UFS 走這條路 | scsi: core: Wake up the error handler when final completions race against each other |
| `6557af8245c0` | ufs | 修正 | 可套用 | 低 | MCQ 模式（實機 use_mcq_mode=Y）下 MAXQ=32 的位移越界 | scsi: ufs: core: Fix shift out of bounds when MAXQ=32 |
| `79bb460d3`（ACK） | ufs | 修正 | 可套用 | 低 | W-LUN resume 失敗後 EH 無法把裝置設回 active；接在 0007 之後 | FROMGIT: scsi: ufs: core: Fix EH failure after W-LUN resume error |
| `e6f3cb873`（ACK） | ufs | 修正 | 可套用 | 低 | 高通提交的 UFS CPU latency PM QoS race，會造成 list 損毀；用 ufs_hba_priv 保持 KMI | BACKPORT: FROMLIST: scsi: ufs: core: Fix data race in CPU latency PM QoS request handling |
| `aa134d3a4`（ACK） | ufs | 修正 | 衝突需改寫 | 低 | 上一項的 mutex 初始化順序修正；上下文不同，手工套用相同改動：mutex_init 移到 ufshcd_init() 前段 | BACKPORT: scsi: ufs: core: Fix PM QoS mutex initialization |

### 批次 2：f2fs／erofs／fuse／binder（24 筆）

| commit | 子系統 | 類型 | 狀態 | KMI 風險 | 建議理由 | 標題 |
| --- | --- | --- | --- | --- | --- | --- |
| `c301ec61ce6f` | binder | 修正 | 可套用 | 低 | binder dbitmap double free | binder: fix double-free in dbitmap |
| `378949f46e89` | erofs | 修正 | 可套用 | 低 | bio 完成時需要 GFP_NOIO，避免回收遞迴死鎖 | erofs: add GFP_NOIO in the bio completion if needed |
| `ad07ea069f92` | erofs | 修正 | 可套用 | 低 | ztailpacking pcluster 的 inline 資料讀取失敗 | erofs: fix inline data read failure for ztailpacking pclusters |
| `cc2ec79a6cb1` | erofs | 修正 | 可套用 | 低 | 非 DEBUG_LOCK_ALLOC 的正式核心誤判 atomic context，可能在不能睡眠時同步解壓 | erofs: fix atomic context detection when !CONFIG_DEBUG_LOCK_ALLOC |
| `86ab00cf81d4`（LunaKernel） | erofs | 修正 | 衝突需改寫（LunaKernel 版：衝突需改寫） | 低 | sync_decompress UAF；衝突需改寫（LunaKernel 改寫版也衝突） | erofs: fix use-after-free on sbi->sync_decompress |
| `19d7ac99e101` | f2fs | 修正 | 可套用 | 低 | age extent cache 計數溢位（實機掛載 atgc） | f2fs: fix age extent cache insertion skip on counter overflow |
| `25d2dc669f2a` | f2fs | 修正 | 可套用 | 低 | GC 不搬空 section | f2fs: fix to avoid migrating empty section |
| `473550e71565` | f2fs | 修正 | 可套用 | 低 | fsync 復原回傳值錯誤 | f2fs: fix return value of f2fs_recover_fsync_data() |
| `4f244c64efe6` | f2fs | 修正 | 可套用 | 低 | extent cache 寫入零長度 extent | f2fs: fix to avoid updating zero-sized extent in extent cache |
| `56038756aae6` | f2fs | 修正 | 可套用 | 低 | atomic write 的 atomic_inode UAF；SQLite 依賴 f2fs atomic write | f2fs: atomic: fix UAF issue on f2fs_inode_info.atomic_inode |
| `603c55e992f8`（LunaKernel） | f2fs | 修正 | 可套用 | 低 | atomic write 重試時把原始資料清成 0（LunaKernel 已採用） | f2fs: keep atomic write retry from zeroing original data |
| `6c3bab5c6261` | f2fs | 修正 | 可套用 | 中 | 潛在死鎖（f2fs_handle_error_async 宣告有改，需確認 KMI） | f2fs: fix to avoid potential deadlock |
| `97df495d7541` | f2fs | 修正 | 可套用 | 低 | evict_inode 時的 panic | f2fs: fix to avoid panic in f2fs_evict_inode |
| `a7b7ebdd7045` | f2fs | 修正 | 可套用 | 低 | f2fs_truncate() 錯誤路徑沒截掉第一頁 | f2fs: fix to truncate first page in error path of f2fs_truncate() |
| `ab1eaf9d5c99` | f2fs | 修正 | 可套用 | 低 | extent node 銷毀與 writeback 的 node_cnt race | f2fs: fix node_cnt race between extent node destroy and writeback |
| `c78206dcb912`（LunaKernel） | f2fs | 修正 | 可套用 | 低 | rename 的記憶體洩漏（LunaKernel 已採用） | f2fs: fix to avoid memory leak in f2fs_rename() |
| `58a5deb220bc` | f2fs | 修正 | 可套用（3-way） | 低 | FI_NO_EXTENT 處理錯誤（3-way） | f2fs: fix incorrect FI_NO_EXTENT handling in __destroy_extent_node() |
| `7be222de96c0`（LunaKernel） | f2fs | 修正 | 衝突需改寫（LunaKernel 版：衝突需改寫） | 低 | f2fs_write_end_io() 遞減 nr_pages 的 UAF；衝突需改寫（LunaKernel 也改寫過） | f2fs: fix UAF caused by decrementing sbi->nr_pages[] in |
| `cf4a9e1bc812` | f2fs | 修正 | 衝突需改寫 | 低 | f2fs_write_end_io() UAF；6.12.38 衝突需改寫 | f2fs: fix to avoid UAF in f2fs_write_end_io() |
| `46473ddccdc5` | fuse | 修正 | 可套用 | 低 | FUSE 替換 page cache folio 前沒重新上鎖，UAF；/sdcard 走 FUSE | fuse: re-lock request before replacing page cache folio |
| `a3d06921ce75`（LunaKernel） | fuse | 修正 | 可套用 | 低 | fuse-bpf verifier 繞過（LunaKernel 已採用） | ANDROID: fuse-bpf: fix verifier bypass in |
| `af1823716`（ACK） | fuse | 修正 | 可套用 | 低 | fuse-bpf read backing 邏輯錯誤 | ANDROID: fuse-bpf: fix wrong logic in read backing |
| `aff1917ea`（ACK） | fuse | 修正 | 可套用 | 低 | FUSE 等待回應改用 freezable wait，避免 suspend 卡住 | ANDROID: fuse: Use freezable wait in request_wait_answer to avoid suspend deadlock |
| `e6aa539720c3` | fuse | 修正 | 可套用 | 低 | FUSE 替換 page cache folio 前沒重新上鎖，UAF；/sdcard 走 FUSE | fuse: re-lock request before returning from fuse_ref_folio() |

### 批次 3：mm／排程／核心（28 筆）

| commit | 子系統 | 類型 | 狀態 | KMI 風險 | 建議理由 | 標題 |
| --- | --- | --- | --- | --- | --- | --- |
| `708fd522b86d` | arm64 | 修正 | 可套用 | 低 | arm64 cpu_switch_to()、call_on_irq_stack() 沒遮 DAIF | arm64/entry: Mask DAIF in cpu_switch_to(), call_on_irq_stack() |
| `71ddb7defc44` | bpf | 修正 | 可套用 | 低 | RCU stall 會 panic（panic_on_rcu_stall=1）：fd array map 清除時的 stall | bpf: Fix RCU stall in bpf_fd_array_map_clear() |
| `993047031c9f` | cgroup | 修正 | 可套用 | 低 | cgroup 釋放與遷移的 UAF、race、死鎖；Android 每個 app 都建 cgroup | cgroup: Fix kernfs_node UAF in css_free_rwork_fn |
| `9cca530c7cc1` | cgroup | 修正 | 可套用 | 低 | cgroup 釋放與遷移的 UAF、race、死鎖；Android 每個 app 都建 cgroup | cgroup: fix race between task migration and iteration |
| `ded4d207a320` | cgroup | 修正 | 可套用 | 低 | cgroup 釋放與遷移的 UAF、race、死鎖；Android 每個 app 都建 cgroup | cgroup: split cgroup_destroy_wq into 3 workqueues |
| `244f301759fd` | futex | 修正 | 可套用 | 低 | futex PI／robust list 的 UAF 與 race | futex: Prevent rcuwait use-after-free during requeue PI |
| `3b4222494489` | futex | 修正 | 可套用 | 低 | futex PI／robust list 的 UAF 與 race | futex: Don't leak robust_list pointer on exec race |
| `7475dfad10a0` | futex | 修正 | 可套用 | 低 | futex PI／robust list 的 UAF 與 race | futex: Clear stale exiting pointer in futex_lock_pi() retry path |
| `925628656b73`（LunaKernel） | futex | 修正 | 可套用 | 低 | futex PI／robust list 的 UAF 與 race | futex: Prevent robust futex exit race some more |
| `a170b9c0dde8` | futex | 修正 | 可套用 | 低 | futex PI／robust list 的 UAF 與 race | futex: Prevent use-after-free during requeue-PI |
| `6024f6d0d9b9`（LunaKernel） | mm | 修正 | 可套用 | 低 | huge_zero_pfn race；實機 THP=always（LunaKernel 已採用） | mm/huge_memory: fix huge_zero_pfn race |
| `60cbe67d1342` | mm | 修正 | 可套用 | 低 | swap 回收全滿 cluster 時缺 cond_resched，16 GB zram 可能 soft lockup | mm/swap: add cond_resched() in swap_reclaim_full_clusters to prevent softlockup |
| `b9a280a9a454` | mm | 修正 | 可套用 | 低 | memcg shrinker_info 釋放與擴充的 race | mm: shrinker: fix shrinker_info teardown race with expansion |
| `c0c21293d0c2` | mm | 修正 | 可套用 | 低 | khugepaged 對匿名 VMA 誤走檔案掃描；READ_ONLY_THP_FOR_FS=y | mm: khugepaged: fix call hpage_collapse_scan_file() for anonymous vma |
| `c15ff206ba78` | mm | 修正 | 可套用 | 低 | vmalloc shrinker 沒拿 vmap_purge_lock | mm/vmalloc: take vmap_purge_lock in shrinker |
| `c7af5300d784` | mm | 修正 | 可套用 | 低 | slab obj_exts race 導致 NULL deref；MEMCG kmem 會用到 | slab: Avoid race on slab->obj_exts in alloc_slab_obj_exts |
| `7cc237e3bc17` | sched | 修正 | 可套用 | 低 | task group 的 runnable 溢位；Android 用 cpu cgroup | sched/fair: Fix overflow in update_tg_cfs_runnable() |
| `c71bf35caba1` | sched | 修正 | 可套用 | 低 | EEVDF：fork 出的 entity 沒清 rel_deadline | sched/fair: Clear rel_deadline when initializing forked entities |
| `debfbc047196` | sched | 修正 | 衝突需改寫 | 低 | push_rt_task race；音訊、SurfaceFlinger 使用 RT；衝突需改寫 | sched/rt: Fix race in push_rt_task |
| `07b3b83587fb`（LunaKernel） | time | 修正 | 可套用 | 低 | timer migration livelock（LunaKernel 已採用） | timers/migration: Fix livelock in tmigr_handle_remote_up() |
| `176725f48483` | time | 修正 | 可套用 | 低 | timer_shutdown_sync() 的 NULL 函式指標 race | timers: Fix NULL function pointer race in timer_shutdown_sync() |
| `6d37ec779d56` | time | 修正 | 可套用 | 低 | alarm_timer_forward() 參數順序錯；Android 大量使用 alarmtimer | alarmtimer: Fix argument order in alarm_timer_forward() |
| `0d8cd9537c64` | vfs | 修正 | 可套用 | 低 | eventpoll 釋放延到 RCU、反向路徑檢查時 pin 檔案 | eventpoll: pin files while checking reverse paths |
| `5b1173b16542` | vfs | 修正 | 可套用 | 低 | eventpoll 釋放延到 RCU、反向路徑檢查時 pin 檔案 | eventpoll: defer struct eventpoll free to RCU grace period |
| `623bb26127fb` | vfs | 修正 | 可套用 | 低 | proc_readdir_de() UAF | fs/proc: fix uaf in proc_readdir_de() |
| `73ec7c96601d` | vfs | 修正 | 可套用 | 低 | do_task_stat() 讀 real_parent 缺 RCU | procfs: fix missing RCU protection when reading real_parent in do_task_stat() |
| `7e64474aba78` | vfs | 修正 | 可套用 | 低 | kernfs poll UAF；sysfs poll 很常用 | kernfs: Fix UAF in polling when open file is released |
| `e63052921f1b` | vfs | 修正 | 可套用 | 低 | writeback __mark_inode_dirty() UAF | fs: writeback: fix use-after-free in __mark_inode_dirty() |

### 批次 4：網路／netfilter（50 筆）

| commit | 子系統 | 類型 | 狀態 | KMI 風險 | 建議理由 | 標題 |
| --- | --- | --- | --- | --- | --- | --- |
| `005671c60fcf` | net | 修正 | 可套用 | 低 | sock_recv_errqueue() 觸發 hardened usercopy panic | net: sock: fix hardened usercopy panic in sock_recv_errqueue |
| `059efb48dd74` | net | 修正 | 可套用 | 低 | ICMP、in6_dev、fib6 walk 的 NULL deref | ipv6: fib6: fix NULL deref in fib6_walk_continue() on multi-batch dump |
| `0630bfc773d8` | net | 修正 | 可套用 | 低 | af_unix OOB 與 GC 修正 | af_unix: Update last skb marker in manage_oob(). |
| `0c699035b7ba`（LunaKernel） | net | 修正 | 可套用 | 低 | TCP 修正（LunaKernel 已採用） | tcp: make probe0 timer handle expired user timeout |
| `0fe4636665d1`（LunaKernel） | net | 修正 | 可套用 | 低 | TCP 修正（LunaKernel 已採用） | tcp: challenge ACK for non-exact RST in SYN-RECEIVED |
| `145e9afa5b90`（LunaKernel） | net | 修正 | 可套用 | 低 | 分片與 MTU 檢查（LunaKernel 已採用） | ipv4: raw: reject IP_HDRINCL packets with ihl < 5 |
| `165258303357`（LunaKernel） | net | 修正 | 可套用 | 低 | IGMP 計時器 UAF（LunaKernel 已採用） | ipv4: igmp: Fix potential UAF in igmp_gq_start_timer() |
| `192df376a05c`（LunaKernel） | net | 修正 | 可套用 | 低 | IPv6 路徑上可從網路觸發的 UAF／NULL／越界（LunaKernel 已採用） | ipv6: Fix a potential NPD in cleanup_prefix_route() |
| `1c206d461c68`（LunaKernel） | net | 修正 | 可套用 | 低 | IPv6 路徑上可從網路觸發的 UAF／NULL／越界（LunaKernel 已採用） | ipv6: prevent in6_dev_get() from resurrecting inet6_dev |
| `1e1f0f89ee46`（LunaKernel） | net | 修正 | 可套用 | 低 | IPv6 路徑上可從網路觸發的 UAF／NULL／越界（LunaKernel 已採用） | ipv6: fix possible UAF in icmpv6_rcv() |
| `21e235a36cfb` | net | 修正 | 可套用 | 低 | xfrm 介面註銷時清除、MIGRATE 參考計數、刪除時解 hash、state_ptrs 初始化、xfrm6 saddr | xfrm: fix refcount leak in xfrm_migrate_policy_find |
| `25357b670afb` | net | 修正 | 可套用 | 低 | IPv6 位址、MLD、IGMP 的 UAF | ipv6: prevent possible UaF in addrconf_permanent_addr() |
| `2684610a9c9c` | net | 修正 | 可套用 | 低 | IPv6 位址、MLD、IGMP 的 UAF | ipv6: Fix use-after-free in inet6_addr_del(). |
| `26edb0a3c99f` | net | 修正 | 可套用 | 低 | xfrm 介面註銷時清除、MIGRATE 參考計數、刪除時解 hash、state_ptrs 初始化、xfrm6 saddr | xfrm: defensively unhash xfrm_state lists in __xfrm_state_delete |
| `3310fc11fc47` | net | 修正 | 可套用 | 低 | ICMP、in6_dev、fib6 walk 的 NULL deref | ipv6: fix NULL pointer deref in ip6_rt_get_dev_rcu() |
| `36e0741833bd`（LunaKernel） | net | 修正 | 可套用 | 低 | 分片與 MTU 檢查（LunaKernel 已採用） | ipv4: reject undersized MTUs in ip_do_fragment() |
| `3c770ac4e6f0` | net | 修正 | 可套用 | 低 | IPv6 輸出、dst 快取、fnhe 的 UAF 與 race | ipv6: fix use-after-free in ip6_finish_output2() |
| `43de8a49335e`（LunaKernel） | net | 修正 | 可套用 | 低 | xfrm 修正；IWLAN／VPN 會用到（LunaKernel 已採用） | xfrm6: clear dst.dev on error to avoid double netdev_put in |
| `46f201f8b4c3` | net | 修正 | 可套用 | 低 | IPv6 paged 配置漏算 fraggap，資料錯誤 | ipv6: account for fraggap on the paged allocation path |
| `5a28a4b22dde`（LunaKernel） | net | 修正 | 可套用 | 低 | IPv4 fnhe PMTU UAF（LunaKernel 已採用；新增的宣告不影響 KMI） | ipv4: fix use-after-free in fib_nhc_update_mtu() |
| `62c719203cb5`（LunaKernel） | net | 修正 | 可套用 | 低 | IPv6 路徑上可從網路觸發的 UAF／NULL／越界（LunaKernel 已採用） | ipv6: ndisc: fix NULL deref in accept_untracked_na() |
| `62e6160cfb55` | net | 修正 | 可套用 | 低 | TCP 接收佇列計數、剩餘空間計算、ehash 查找 race | tcp: Correct signedness in skb remaining space calculation |
| `63fda7488555` | net | 修正 | 可套用 | 低 | ip6_datagram_send_ctl() 溢位，一般 app 可觸發 | ipv6: avoid overflows in ip6_datagram_send_ctl() |
| `645b1ed3259a` | net | 修正 | 可套用 | 低 | af_unix OOB 與 GC 修正 | af_unix: Reject SIOCATMARK on non-stream sockets |
| `6bf2daafc51b` | net | 修正 | 可套用 | 低 | xfrm 介面註銷時清除、MIGRATE 參考計數、刪除時解 hash、state_ptrs 初始化、xfrm6 saddr | xfrm: state: initialize state_ptrs earlier in xfrm_state_find |
| `6dab4dec9a49`（LunaKernel） | net | 修正 | 可套用 | 低 | xfrm 修正；IWLAN／VPN 會用到（LunaKernel 已採用） | xfrm: Fix xfrm state cache insertion race |
| `80600b5d0f3e`（LunaKernel） | net | 修正 | 可套用 | 低 | IPv6 路徑上可從網路觸發的 UAF／NULL／越界（LunaKernel 已採用） | ipv6: Fix null-ptr-deref in fib6_nh_mtu_change(). |
| `820e501be8ae`（LunaKernel） | net | 修正 | 可套用 | 低 | xfrm 修正；IWLAN／VPN 會用到（LunaKernel 已採用） | xfrm: Check for underflow in xfrm_state_mtu |
| `8820b530cb23` | net | 修正 | 可套用 | 低 | IPv6 位址、MLD、IGMP 的 UAF | ipv4: igmp: remove multicast group from hash table on device destruction |
| `8dd8929b71c4`（LunaKernel） | net | 修正 | 可套用 | 低 | xfrm 修正；IWLAN／VPN 會用到（LunaKernel 已採用） | xfrm: fix sk_dst_cache double-free in xfrm_user_policy() |
| `952426a83ca7` | net | 修正 | 可套用 | 低 | ICMP、in6_dev、fib6 walk 的 NULL deref | ipv6: guard against possible NULL deref in __in6_dev_stats_get() |
| `9647e99d2a61` | net | 修正 | 可套用 | 低 | ICMP、in6_dev、fib6 walk 的 NULL deref | icmp: fix NULL pointer dereference in icmp_tag_validation() |
| `a3c8fede034f` | net | 修正 | 可套用 | 低 | xfrm 介面註銷時清除、MIGRATE 參考計數、刪除時解 hash、state_ptrs 初始化、xfrm6 saddr | xfrm: always flush state and policy upon NETDEV_UNREGISTER event |
| `b2eb8886200b` | net | 修正 | 可套用 | 低 | IPv6 位址、MLD、IGMP 的 UAF | ipv6: mcast: Fix use-after-free when processing MLD queries |
| `b84f083f50ec` | net | 修正 | 可套用 | 低 | IPv6 輸出、dst 快取、fnhe 的 UAF 與 race | ipv4: route: Prevent rt_bind_exception() from rebinding stale fnhe |
| `dc0abce05513` | net | 修正 | 可套用 | 低 | xfrm 介面註銷時清除、MIGRATE 參考計數、刪除時解 hash、state_ptrs 初始化、xfrm6 saddr | xfrm6: fix uninitialized saddr in xfrm6_get_saddr() |
| `dec2edb7aaf1`（LunaKernel） | net | 修正 | 可套用 | 低 | 分片與 MTU 檢查（LunaKernel 已採用） | inet: frags: strip GSO state from fragments before reassembly |
| `df50875c208a`（LunaKernel） | net | 修正 | 可套用 | 低 | TCP 修正（LunaKernel 已採用） | tcp: fix icsk_ack.ato bitfield overflow |
| `df8060ca14ac` | net | 修正 | 可套用 | 低 | TCP 接收佇列計數、剩餘空間計算、ehash 查找 race | tcp: Fix imbalanced icsk_accept_queue count. |
| `e1480cc48d41` | net | 修正 | 可套用 | 低 | TCP 接收佇列計數、剩餘空間計算、ehash 查找 race | inet: Avoid ehash lookup race in inet_ehash_insert() |
| `f24a52948c95` | net | 修正 | 可套用 | 低 | IPv6 輸出、dst 快取、fnhe 的 UAF 與 race | dst: fix races in rt6_uncached_list_del() and rt_del_uncached_list() |
| `fe89feb2bdce` | net | 修正 | 可套用 | 低 | TCP 接收佇列計數、剩餘空間計算、ehash 查找 race | inet: Avoid ehash lookup race in inet_twsk_hashdance_schedule() |
| `ff3cb05289b8`（LunaKernel） | net | 修正 | 可套用 | 低 | IPv6 路徑上可從網路觸發的 UAF／NULL／越界（LunaKernel 已採用） | ipv6: fix Route Information option length validation |
| `38bccb927d83`（LunaKernel） | net | 修正 | 衝突需改寫 | 低 | af_unix peek UAF；衝突需改寫（LunaKernel 已採用） | af_unix: Fix UAF read of tail->len in unix_stream_data_wait() |
| `ebbebf6cee95` | net | 修正 | 衝突需改寫 | 低 | IPv6 位址、MLD、IGMP 的 UAF | ipv6: mcast: Fix potential UAF in MLD delayed work |
| `fc38c249c622` | net,netfilter | 修正 | 可套用 | 低 | conntrack 移除未初始化項目時 crash、ctnetlink dump 參考計數洩漏 | netfilter: nf_conntrack: fix crash due to removal of uninitialised entry |
| `53ef70a31542`（LunaKernel） | netfilter | 修正 | 可套用 | 低 | conntrack 修正（LunaKernel 已採用） | netfilter: nf_conntrack_reasm: guard mac_header adjustment |
| `a2cb4df7872d` | netfilter | 修正 | 可套用 | 低 | conntrack 移除未初始化項目時 crash、ctnetlink dump 參考計數洩漏 | netfilter: ctnetlink: fix refcount leak on table dump |
| `f206def4e86d`（LunaKernel） | netfilter | 修正 | 可套用 | 低 | conntrack 修正（LunaKernel 已採用） | netfilter: conntrack: tcp: do not force CLOSE on invalid-seq |
| `5e7ece24c5cb` | netfilter | 修正 | 可套用（3-way） | 低 | xt_IDLETIMER 重用 ALARM 標籤；Android 用它追蹤網路介面閒置 | netfilter: xt_IDLETIMER: reject rev0 reuse of ALARM timer labels |

### 批次 5：USB／HID（10 筆）

| commit | 子系統 | 類型 | 狀態 | KMI 風險 | 建議理由 | 標題 |
| --- | --- | --- | --- | --- | --- | --- |
| `7cfb62888eba` | dwc3 | 修正 | 可套用 | 低 | dwc3 並行 remove_requests 的 race | usb: dwc3: Fix race condition between concurrent dwc3_remove_requests() call paths |
| `02246d8b462f` | hid | 修正 | 可套用 | 低 | HID 報告欄位越界與停止時的 UAF（前者 LunaKernel 已採用） | HID: core: quiesce input in hid_hw_stop() to prevent use-after-free |
| `a38212687519`（LunaKernel） | hid | 修正 | 可套用 | 低 | HID 報告欄位越界與停止時的 UAF（前者 LunaKernel 已採用） | HID: core: fix OOB read of field->usage in hid_set_field() |
| `0aeda584554e` | usb-gadget | 修正 | 可套用 | 低 | f_fs（adb 使用）的 NULL、短讀、read_buffer 生命週期、ep0 死鎖 | usb: gadget: f_fs: Tie read_buffer lifetime to ffs_epfile |
| `1c91f3784`（ACK） | usb-gadget | 修正 | 可套用 | 低 | f_fs 提早設定 epfile->in，修正端點方向檢查（adb 使用 f_fs） | UPSTREAM: usb: gadget: f_fs: Initialize epfile->in early to fix endpoint direction checks |
| `5f06ee9f9a36` | usb-gadget | 修正 | 可套用 | 低 | composite_dev_cleanup() UAF | usb: gadget : fix use-after-free in composite_dev_cleanup() |
| `88874a19b2b0` | usb-gadget | 修正 | 可套用 | 低 | f_fs（adb 使用）的 NULL、短讀、read_buffer 生命週期、ep0 死鎖 | usb: gadget: f_fs: copy only received bytes on short ep0 read |
| `d62b808d5c68` | usb-gadget | 修正 | 可套用 | 低 | f_fs（adb 使用）的 NULL、短讀、read_buffer 生命週期、ep0 死鎖 | usb: gadget: f_fs: Fix epfile null pointer access after ep enable. |
| `fd20cc68bbdb` | usb-gadget | 修正 | 可套用 | 低 | f_fs（adb 使用）的 NULL、短讀、read_buffer 生命週期、ep0 死鎖 | usb: gadget: f_fs: Prevent deadlock during ep0 read loop |
| `521591170206` | xhci | 修正 | 可套用 | 低 | xhci endpoint_disable 後 hcpriv 被釋放的 UAF | usb: xhci: Make usb_host_endpoint.hcpriv survive endpoint_disable() |

## LunaKernel r21 清單逐項結果（72 筆）

來源是 LunaKernel 主分支的 `patches/backports/r21-selected-backports.tsv` 與 `r21-independent/*.tsv`（2026/10/2 讀取）。同一個修正若同時出現在 stable 掃描，只算一次。

| commit | 來源 | 子系統 | 狀態 | KMI 風險 | 建議 | 說明 |
| --- | --- | --- | --- | --- | --- | --- |
| `5b029dd854f8` | stable | block | 可套用 | 低 | 建議 | blk_time_get_ns() 被搶占時回傳 0（LunaKernel 已採用） |
| `86ab00cf81d4` | stable | erofs | 衝突需改寫（LunaKernel 版：衝突需改寫） | 低 | 建議 | sync_decompress UAF；衝突需改寫（LunaKernel 改寫版也衝突） |
| `603c55e992f8` | stable | f2fs | 可套用 | 低 | 建議 | atomic write 重試時把原始資料清成 0（LunaKernel 已採用） |
| `7be222de96c0` | stable | f2fs | 衝突需改寫（LunaKernel 版：衝突需改寫） | 低 | 建議 | f2fs_write_end_io() 遞減 nr_pages 的 UAF；衝突需改寫（LunaKernel 也改寫過） |
| `c78206dcb912` | stable | f2fs | 可套用 | 低 | 建議 | rename 的記憶體洩漏（LunaKernel 已採用） |
| `a3d06921ce75` | ACK | fuse | 可套用 | 低 | 建議 | fuse-bpf verifier 繞過（LunaKernel 已採用） |
| `925628656b73` | stable | futex | 可套用 | 低 | 建議 | futex PI／robust list 的 UAF 與 race |
| `a38212687519` | stable | hid | 可套用 | 低 | 建議 | HID 報告欄位越界與停止時的 UAF（前者 LunaKernel 已採用） |
| `6024f6d0d9b9` | stable | mm | 可套用 | 低 | 建議 | huge_zero_pfn race；實機 THP=always（LunaKernel 已採用） |
| `dfc8292a1d67` | stable | mm | 可套用 | 低 | 建議 | cgroup writeback（CGROUP_WRITEBACK=y）釋放時 UAF（LunaKernel 已採用） |
| `0c699035b7ba` | stable | net | 可套用 | 低 | 建議 | TCP 修正（LunaKernel 已採用） |
| `0fe4636665d1` | stable | net | 可套用 | 低 | 建議 | TCP 修正（LunaKernel 已採用） |
| `145e9afa5b90` | stable | net | 可套用 | 低 | 建議 | 分片與 MTU 檢查（LunaKernel 已採用） |
| `165258303357` | stable | net | 可套用 | 低 | 建議 | IGMP 計時器 UAF（LunaKernel 已採用） |
| `192df376a05c` | stable | net | 可套用 | 低 | 建議 | IPv6 路徑上可從網路觸發的 UAF／NULL／越界（LunaKernel 已採用） |
| `1c206d461c68` | stable | net | 可套用 | 低 | 建議 | IPv6 路徑上可從網路觸發的 UAF／NULL／越界（LunaKernel 已採用） |
| `1e1f0f89ee46` | stable | net | 可套用 | 低 | 建議 | IPv6 路徑上可從網路觸發的 UAF／NULL／越界（LunaKernel 已採用） |
| `36e0741833bd` | stable | net | 可套用 | 低 | 建議 | 分片與 MTU 檢查（LunaKernel 已採用） |
| `38bccb927d83` | stable | net | 衝突需改寫 | 低 | 建議 | af_unix peek UAF；衝突需改寫（LunaKernel 已採用） |
| `43de8a49335e` | stable | net | 可套用 | 低 | 建議 | xfrm 修正；IWLAN／VPN 會用到（LunaKernel 已採用） |
| `5a28a4b22dde` | stable | net | 可套用 | 低 | 建議 | IPv4 fnhe PMTU UAF（LunaKernel 已採用；新增的宣告不影響 KMI） |
| `62c719203cb5` | stable | net | 可套用 | 低 | 建議 | IPv6 路徑上可從網路觸發的 UAF／NULL／越界（LunaKernel 已採用） |
| `6dab4dec9a49` | stable | net | 可套用 | 低 | 建議 | xfrm 修正；IWLAN／VPN 會用到（LunaKernel 已採用） |
| `80600b5d0f3e` | stable | net | 可套用 | 低 | 建議 | IPv6 路徑上可從網路觸發的 UAF／NULL／越界（LunaKernel 已採用） |
| `820e501be8ae` | stable | net | 可套用 | 低 | 建議 | xfrm 修正；IWLAN／VPN 會用到（LunaKernel 已採用） |
| `8dd8929b71c4` | stable | net | 可套用 | 低 | 建議 | xfrm 修正；IWLAN／VPN 會用到（LunaKernel 已採用） |
| `dec2edb7aaf1` | stable | net | 可套用 | 低 | 建議 | 分片與 MTU 檢查（LunaKernel 已採用） |
| `df50875c208a` | stable | net | 可套用 | 低 | 建議 | TCP 修正（LunaKernel 已採用） |
| `ff3cb05289b8` | stable | net | 可套用 | 低 | 建議 | IPv6 路徑上可從網路觸發的 UAF／NULL／越界（LunaKernel 已採用） |
| `53ef70a31542` | stable | netfilter | 可套用 | 低 | 建議 | conntrack 修正（LunaKernel 已採用） |
| `f206def4e86d` | stable | netfilter | 可套用 | 低 | 建議 | conntrack 修正（LunaKernel 已採用） |
| `07b3b83587fb` | stable | time | 可套用 | 低 | 建議 | timer migration livelock（LunaKernel 已採用） |
| `23d8ea1e303b` | stable | block | 衝突需改寫 | 低 | 可選 | LunaKernel 的 blk-mq cached request 系列；6.12.38 衝突，需先確認 bug 是否存在 |
| `44e41381591d` | mainline | block | 可套用（3-way） | 低 | 可選 | LunaKernel 的 blk-mq cached request 系列；6.12.38 衝突，需先確認 bug 是否存在 |
| `8e23114b89e2` | stable | block | 衝突需改寫 | 低 | 可選 | LunaKernel 的 blk-mq cached request 系列；6.12.38 衝突，需先確認 bug 是否存在 |
| `9cbbac29d752` | mainline | block | 衝突需改寫（LunaKernel 版：可套用） | 低 | 可選 | 效能：移除多餘的 plug（LunaKernel 改寫版可套用） |
| `1509c1ae9185` | stable | bpf | 可套用 | 低 | 可選 | 自動篩出，未逐項審 |
| `6321ebf2a105` | stable | bpf | 可套用 | 低 | 可選 | 自動篩出，未逐項審 |
| `d0d59a35ac0b` | stable | crypto | 可套用 | 低 | 可選 | crypto arm64 aes mac 參數寬度（LunaKernel 已採用） |
| `16161444c30d` | stable | f2fs | 可套用（LunaKernel 改寫版：可套用（3-way）） | 低 | 可選 | 損毀映像的防護；/data 由手機自己建立，價值較低 |
| `222bc257a151` | mainline | f2fs | 可套用 | 低 | 可選 | 效能：cached overwrite 略過 inode folio 查找（mainline） |
| `2a9f9791653b` | stable | f2fs | 衝突需改寫（LunaKernel 版：可套用） | 低 | 可選 | 損毀映像的防護；/data 由手機自己建立，價值較低 |
| `550511a2470f` | stable | f2fs | 可套用 | 低 | 可選 | 損毀映像的防護；/data 由手機自己建立，價值較低 |
| `03cb8cc2961f` | stable | net | 可套用 | 低 | 可選 | BIG TCP、UDP tunnel GSO、bridge、sockmap 實機未使用（LunaKernel 已採用） |
| `4c9d9aa809c2` | stable | net | 可套用 | 低 | 可選 | BIG TCP、UDP tunnel GSO、bridge、sockmap 實機未使用（LunaKernel 已採用） |
| `5161e67c561c` | stable | net | 可套用 | 低 | 可選 | BIG TCP、UDP tunnel GSO、bridge、sockmap 實機未使用（LunaKernel 已採用） |
| `a83264d8dfba` | stable | net | 可套用 | 低 | 可選 | TCP rcv_ssthresh 行為調整（LunaKernel 已採用） |
| `367abcacc13a` | stable | netfilter | 衝突需改寫 | 低 | 可選 | 同時改 ipset（未編進）與 xt_mac、nf_log；衝突，需拆出有編進的部分 |
| `f2e6596d1078` | stable | netfilter | 可套用 | 低 | 可選 | BIG TCP、UDP tunnel GSO、bridge、sockmap 實機未使用（LunaKernel 已採用） |
| `29cf3b31e8cc` | stable | sched | 可套用 | 低 | 可選 | EAS cpu_util 計算；選核由 WALT 接手（LunaKernel 已採用） |
| `b0bc1c75f304` | mainline | sched | 可套用 | 低 | 可選 | 效能：沒有新的 irq 時間時略過計算（mainline） |
| `d8d7b0043acc` | stable | time | 可套用 | 低 | 可選 | 效能：避免多餘的 hrtimer 重新設定（LunaKernel 已採用） |
| `7ee04de323f7` | ACK | xhci | 可套用 | 中 | 可選 | LunaKernel 採用的 ACK revert；需確認與原廠 USB 音訊 offload 的關係 |
| `ed9f54727ab3` | ACK | f2fs | 可套用 | 高 | 不建議 | 改到 KMI 型別 struct fscrypt_operations |
| `f5154cf3ce1c` | stable | f2fs | 可套用 | 低 | 不適用 | f2fs 壓縮未使用（實機 compr_written_block=0） |
| `19999e479c2a` | mainline | mm | 衝突需改寫（LunaKernel 版：衝突需改寫） | 低 | 不適用 | MGLRU 實機關閉（lru_gen/enabled=0x0000） |
| `02f75f041a93` | stable | netfilter | 可套用 | 低 | 不適用 | ipset、ip6t_eui64 未編進核心（IP_SET、IP6_NF_MATCH_EUI64 未設定） |
| `157c0a896127` | stable | netfilter | 衝突需改寫 | 低 | 不適用 | ipset、ip6t_eui64 未編進核心（IP_SET、IP6_NF_MATCH_EUI64 未設定） |
| `20cb13a523f0` | stable | netfilter | 可套用 | 低 | 不適用 | ipset、ip6t_eui64 未編進核心（IP_SET、IP6_NF_MATCH_EUI64 未設定） |
| `7445fe965b7d` | stable | netfilter | 衝突需改寫 | 低 | 不適用 | ipset、ip6t_eui64 未編進核心（IP_SET、IP6_NF_MATCH_EUI64 未設定） |
| `7e06a41b3663` | stable | netfilter | 可套用 | 低 | 不適用 | ipset、ip6t_eui64 未編進核心（IP_SET、IP6_NF_MATCH_EUI64 未設定） |
| `9eda5478746e` | stable | netfilter | 可套用 | 低 | 不適用 | ipset、ip6t_eui64 未編進核心（IP_SET、IP6_NF_MATCH_EUI64 未設定） |
| `a12c0025080e` | stable | netfilter | 可套用 | 低 | 不適用 | ipset、ip6t_eui64 未編進核心（IP_SET、IP6_NF_MATCH_EUI64 未設定） |
| `c710e9bf38e4` | stable | netfilter | 可套用 | 低 | 不適用 | ipset、ip6t_eui64 未編進核心（IP_SET、IP6_NF_MATCH_EUI64 未設定） |
| `c940d1b96248` | stable | netfilter | 可套用 | 低 | 不適用 | ipset、ip6t_eui64 未編進核心（IP_SET、IP6_NF_MATCH_EUI64 未設定） |
| `fcb565966534` | stable | netfilter | 可套用 | 低 | 不適用 | ipset、ip6t_eui64 未編進核心（IP_SET、IP6_NF_MATCH_EUI64 未設定） |
| `ff86ea9b7fdf` | stable | netfilter | 可套用 | 低 | 不適用 | ipset、ip6t_eui64 未編進核心（IP_SET、IP6_NF_MATCH_EUI64 未設定） |
| `0504d52d0529` | stable | sched | 可套用 | 低 | 不適用 | governor 是 WALT，schedutil 不會執行 |
| `806fcff98c1d` | stable | sched | 可套用 | 低 | 不適用 | cgroup PSI 已停用（cgroup_disable=pressure） |
| `0267a9417dfe` | stable | ufs | 衝突需改寫 | 低 | 不適用 | active-active suspend 分支在 6.12.38 不存在（v8 已確認） |
| `e74443f5db00` | stable | time | 基底已有 | 低 | 基底已有 | 自動篩出，未逐項審 |
| `2d9c4a4ed4ee` | mainline | f2fs | 衝突需改寫 | 低 | 重複 | 同一個修正已列為 7be222de96c0 |

## 因 KMI 排除（33 筆）

這些修正本身有價值，但會改到 STG 裡的 KMI 型別。除非能改寫成不動結構（例如像 e6f3cb873 改用私有結構），否則不採用。

| commit | 子系統 | 改到的型別 | 標題 |
| --- | --- | --- | --- |
| `dc518afa8eb7` | arm64 | kernel/trace/ring_buffer.c: struct trace_buffer（KMI 型別） | ring-buffer: Flush and stop persistent ring buffer on panic |
| `397209d78` | binder | binder per-VMA lock 系列是效能改動，衝突且改到 KMI 型別 struct binder_lru_page | UPSTREAM: binder: use per-vma lock in page installation |
| `3fb6436fa` | binder | binder per-VMA lock 系列是效能改動，衝突且改到 KMI 型別 struct binder_lru_page | BACKPORT: Revert "binder: switch alloc->mutex to spinlock_t" |
| `658b9fc00` | binder | binder per-VMA lock 系列是效能改動，衝突且改到 KMI 型別 struct binder_lru_page | BACKPORT: binder: concurrent page installation |
| `ee25d80f0` | binder | binder per-VMA lock 系列是效能改動，衝突且改到 KMI 型別 struct binder_lru_page | UPSTREAM: binder: use per-vma lock in page reclaiming |
| `656d40d1ca22` | bpf | include/linux/bpf.h: enum bpf_arg_type（KMI 型別） | bpf: Reject non-scalar bpf_loop iteration counts |
| `e422b32e6a57` | cgroup | struct cpuset | cgroup/cpuset: Make nr_deadline_tasks an atomic_t |
| `1eb0b130196b` | f2fs | struct f2fs_sb_info | f2fs: use global inline_xattr_slab instead of per-sb slab cache |
| `67c51f025` | f2fs | struct f2fs_bio_info／f2fs_sb_info | BACKPORT: UPSTREAM: f2fs: fix lock priority inversion issue |
| `85e0019c0` | f2fs | fs/f2fs/f2fs.h: struct f2fs_sb_info（KMI 型別） | UPSTREAM: f2fs: quota: fix to avoid warning in dquot_writeback_dquots() |
| `ac7e7d18816e` | f2fs | struct f2fs_sb_info | f2fs: fix false alarm of lockdep on cp_global_sem lock |
| `d762e881e` | f2fs | struct f2fs_bio_info／f2fs_sb_info | UPSTREAM: f2fs: fix to avoid out-of-boundary access in devs.path |
| `ed9f54727ab3` | f2fs | struct fscrypt_operations | BACKPORT: fscrypt: Avoid dynamic allocation in |
| `97a688563be7` | f2fs,fscrypt | struct fscrypt_operations | fscrypt: Avoid dynamic allocation in fscrypt_get_devices() |
| `6a379f037` | fscrypt | struct fscrypt_master_key／fscrypt_prepared_key | BACKPORT: fscrypt: Fix key setup in edge case with multiple data unit sizes |
| `16852eccbdfa` | net | 改到 KMI 型別（struct ip_mc_socklist、net_device、softnet_data、in_device、tc_action、enum skb_drop_reason 等） | Bluetooth: hci_sync: fix double free in 'hci_discovery_filter_clear()' |
| `5dd51e09020c` | net | 改到 KMI 型別（struct ip_mc_socklist、net_device、softnet_data、in_device、tc_action、enum skb_drop_reason 等） | net/sched: act_api: use RCU with deferred freeing for action lifecycle |
| `70debb2b34a2` | net | 改到 KMI 型別（struct ip_mc_socklist、net_device、softnet_data、in_device、tc_action、enum skb_drop_reason 等） | ipv4: igmp: annotate data-races around idev->mr_maxdelay |
| `834c4f645726` | net | 改到 KMI 型別（struct ip_mc_socklist、net_device、softnet_data、in_device、tc_action、enum skb_drop_reason 等） | net: add xmit recursion limit to tunnel xmit functions |
| `b1fcc7888035` | net | 改到 KMI 型別（struct ip_mc_socklist、net_device、softnet_data、in_device、tc_action、enum skb_drop_reason 等） | af_unix: Set drop reason in unix_release_sock(). |
| `b712da45bd9b` | net | 改到 KMI 型別（struct ip_mc_socklist、net_device、softnet_data、in_device、tc_action、enum skb_drop_reason 等） | net: udp_tunnel: fix memory leak in udp_tunnel_nic_unregister() |
| `cc8ddf303397` | net | 改到 KMI 型別（struct ip_mc_socklist、net_device、softnet_data、in_device、tc_action、enum skb_drop_reason 等） | af_unix: Set drop reason in manage_oob(). |
| `e40e2d11ced8` | net | 改到 KMI 型別（struct ip_mc_socklist、net_device、softnet_data、in_device、tc_action、enum skb_drop_reason 等） | ip_tunnel: adapt iptunnel_xmit_stats() to NETDEV_PCPU_STAT_DSTATS |
| `f5182dfad542` | net | 改到 KMI 型別（struct ip_mc_socklist、net_device、softnet_data、in_device、tc_action、enum skb_drop_reason 等） | igmp: convert struct ip_sf_list to RCU |
| `7fc808d98215` | sched | struct rq | sched: Change nr_uninterruptible type to unsigned long |
| `c1cbee3aae2a` | sched | enum psi_aggregators | sched/psi: Optimize psi_group_change() cpu_clock() usage |
| `dbfc1413a` | sched | psi 最佳化改到 KMI 型別 enum psi_aggregators | UPSTREAM: sched/psi: Optimize psi_group_change() cpu_clock() usage |
| `866efe8ae8b8` | scsi | struct Scsi_Host | scsi: core: wake eh reliably when using scsi_schedule_eh |
| `778fdda45307` | selinux | security/selinux/ss/policydb.h: struct user_datum（KMI 型別） | selinux: avoid unnecessary indirection in struct level_datum |
| `10014310193c` | usb-gadget | struct usb_gadget | usb: gadget: udc: fix use-after-free in usb_gadget_state_work |
| `15ea8dc42a02` | vfs | struct mount | fhandle: fix UAF due to unlocked ->mnt_ns read in may_decode_fh() |
| `f08c80af3c9a` | vfs | 改到 KMI 型別（struct ip_mc_socklist、net_device、softnet_data、in_device、tc_action、enum skb_drop_reason 等） | netfs: Fix unbuffered write error handling |
| `74bd9a178` | xhci | struct usb_device | BACKPORT: usb: core: use dedicated spinlock for offload state |
