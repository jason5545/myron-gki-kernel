# 升級到 OS3.0.310（2026/10/3）

第一次在自編核心上升級韌體，而且保留資料：Xiaomi.eu `OS3.0.309.0.WPMCNXM` 升到 `OS3.0.310.0.WPMCNXM`，升級後繼續用 v16。

## 310 與 309 的開機映像

| 項目 | 309 | 310 |
| --- | --- | --- |
| boot 裡的核心 Image | `670c8285…`，`6.12.23-android16-5-g16e473de48a3-abogki462654244-4k` | 相同 |
| boot 的 AVB `security_patch` | 2026-02-01 | 2026-09-01 |
| init_boot | `a4ed45c0…` | `0a9871f4…` |
| vendor_boot | `cc7e2691…` | `b5229289…`，419 個模組有 404 個重新編譯 |

boot 的標頭與核心逐位元相同，只差 AVB vbmeta 所在的那一個 4 KB 區塊。原廠核心沒有變，所以 v16 的相容性基準不變；變的是 boot 的 AVB footer 和 vendor 模組。

## 用 310 的原廠 boot 重封裝 v16

手機上的 v16 是 309 原廠 boot 換掉核心，footer 是 309 的（`security_patch` 2026-02-01）。如果先用 310 原廠 boot 開過機，再刷回這顆，boot 的修補等級會倒退，KeyMint 的金鑰可能因此失效。所以改用 310 原廠 boot 換上 v16 Image，修補等級跟著變成 2026-09-01。

步驟和 [`repack_check.py`](../scripts/repack_check.py) 相同：同一顆 magiskboot，在手機的 `/data/local/tmp` 執行 `unpack -h`、替換 `kernel`、`PATCHVBMETAFLAG=false repack`。`repack_check.py` 只接受 309 的原廠 boot，這次手動執行。

- 對照組：同樣的步驟套在 309 原廠 boot，結果是 `7843acd9…`，與當時手機上的 boot_a 位元完全相同。
- 310 成品 `aa2a63e6…`：標頭只有核心大小改變，核心等於 v16 Image `30c25089…`，footer 是 310 的指紋與 2026-09-01。
- 封裝前後，手機的 boot_a 都是 `7843acd9…`，沒有寫入分割區。

## 模組

310 vendor_boot 的 419 個模組對 v16 的 `vmlinux.symvers`：2,764 個核心符號，CRC 不符 0。缺少的 9 個（`rfkill_*`、`arc4_*`）由 system_dlkm 的模組提供，309 的 vendor_boot 也一樣缺這 9 個。

vendor_dlkm 與 system_dlkm 在 super 裡，刷入前沒有檢查，改在開機後看模組數量。

## 刷入

用 Xiaomi.eu 的不清資料升級腳本，腳本寫入 310 原廠 boot 之後、重開機之前，把 boot_a 換成上面重封裝的 v16（`aa2a63e6…`）。

boot_b 保留 310 原廠 boot（`ecbfbf66…`）。v16 在 310 上出問題時，把這顆寫回 boot_a，修補等級相同，不會倒退。309 封裝的那顆 v16 不能再刷回去。

## 實機

| 項目 | 結果 |
| --- | --- |
| 系統 | `OS3.0.310.0.WPMCNXM`，slot a |
| 核心 | `6.12.38-android16-5-g4b4d49350df7-4k`，boot_a `aa2a63e6…`，init_boot 是 310 原廠 `0a9871f4…` |
| 模組 | 616 個，與 309 相同；`Unknown symbol` 只有 `rust_binder` |
| 顯示 | logcat 沒有 `drmModeAtomicCommit failed` |
| UFS | `ufshcd_err_handler` 0 次 |
| dmesg | WARNING 只有 `spmi-pmic-arb.c:352` 兩次和 eBPF 提示，與 v16 在 309 上相同；沒有 Oops |
| root | ReSukiSU `Work mode: Built-in`，SUSFS v2.3.0 已初始化 |
| 網路 | `tcp_congestion_control` 為 bbr |

dmesg、logcat 與模組清單在 `out/v16-310-device/`。

## 安裝器（v16.1）

v16 的 AnyKernel3 安裝器只接受 309 的原廠 init_boot（`a4ed45c0…`），在 310 上會拒絕安裝。v16.1 把 310 的 `0a9871f4…` 加進去，核心 Image 不變（`30c25089…`）。

AnyKernel3 沿用手機目前的 boot，只換核心，所以在 310 上用 v16.1 刷入時，boot 的 AVB footer 仍是 310 的，不會有上面修補等級倒退的問題。
