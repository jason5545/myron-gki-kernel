#!/system/bin/sh
# 使用固定版本的官方 AnyKernel3，只替換目前 slot 的 boot 核心。

properties() { '
kernel.string=myron HyperOS 3 KMI 5 自編核心
do.devicecheck=1
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=0
device.name1=myron
supported.versions=16
supported.patchlevels=
supported.vendorpatchlevels=
'; }

BLOCK=boot
IS_SLOT_DEVICE=auto
RAMDISK_COMPRESSION=auto
PATCH_VBMETA_FLAG=0
NO_VBMETA_PARTITION_PATCH=1
NO_MAGISK_CHECK=1

. tools/ak3-core.sh

# 從實際 boot 擷取版本，避免 uname 顯示偽裝造成誤判。
split_boot
header_version=$(od -An -tu4 -j40 -N4 "$BOOTIMG" | tr -d '[:space:]')
[ "$header_version" = 4 ] || abort '需要現有的 boot v4 映像。'
[ -s "$SPLITIMG/kernel" ] || abort '沒有取得原有核心。'
release=$(strings "$SPLITIMG/kernel" | sed -n 's/^Linux version \([^ ]*\) .*/\1/p' | head -n1)
case "$release" in
  6.12.*-android16-5-*-4k) ;;
  *) abort "實際 boot 核心不符 KMI 5／4 KB：$release" ;;
esac
[ ! -s "$SPLITIMG/kernel_dtb" ] || abort 'boot 核心有附加 DTB，需另行核對封裝。'

# 內建 root 不能再透過 init_boot 載入舊 LKM；只接受已核對的原廠映像。
init_boot_block="$(dirname "$BLOCK")/init_boot$SLOT"
[ -e "$init_boot_block" ] || abort '找不到對應 slot 的 init_boot，停止安裝。'
init_boot_sha=$(sha256sum "$init_boot_block" | awk '{print $1}')
case "$init_boot_sha" in
  a4ed45c0af246068212b899a3f7e003b396d45b77af59b7f37acca0495ffe4b3) ;;
  5dee4a6da2e6c6718ccec7c6570ff90371a94468103a54fc53a37fa629406f7f)
    abort 'init_boot 仍有舊 KernelSU LKM；請先遷移至配套原廠 init_boot。' ;;
  *) abort 'init_boot 與已核對的原廠基準不同，停止安裝。' ;;
esac

ui_print "沿用現有 boot v4，替換核心；原有版本：$release"
flash_boot
