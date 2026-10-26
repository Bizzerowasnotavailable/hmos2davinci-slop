#!/bin/bash
# Run under Linux/WSL, with the kernel checkout on a native Linux filesystem.
# Dependencies: clang/lld/llvm, make, gcc, bc, bison, flex, libssl-dev,
# libelf-dev, and AArch64/ARM32 binutils.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
KERNEL=${DAVINCI_KERNEL:-$HOME/hmos-davinci-kernel}
DEST=${DAVINCI_KERNEL_OUT:-$REPO/prebuilt/kernel/davinci}
BASE=e03e5ba22586be70673afb5d3c3f70510524e658
if [ ! -d "$KERNEL/.git" ]; then
    git clone --depth 1 --single-branch -b lineage-23.2 \
        https://github.com/LineageOS/android_kernel_xiaomi_sm6150 "$KERNEL"
fi
cd "$KERNEL"
[ "$(git rev-parse HEAD)" = "$BASE" ] || { echo "Unexpected kernel revision; expected $BASE" >&2; exit 1; }
# Only generic OHOS patches: do not enable sweet's panel, vibrator, NFC or
# charger drivers on davinci. Build an expected tree in a temporary index so
# re-running can recognize the entire stack, including patches that modify
# the same lines. Checking patches in reverse one by one cannot do that.
PATCHES=()
for number in 0001 0002 0003 0004 0005 0006 0007 0008 0009 0012 0015 0018 0019 0020; do
    patch=("$REPO"/src/kernel/patches/"$number"-*.patch)
    PATCHES+=("${patch[0]}")
done
INDEX=$(mktemp)
trap 'rm -f "$INDEX"' EXIT
GIT_INDEX_FILE=$INDEX git read-tree HEAD
for patch in "${PATCHES[@]}"; do
    GIT_INDEX_FILE=$INDEX git apply --cached "$patch"
done
if GIT_INDEX_FILE=$INDEX git diff --quiet; then
    echo "HarmonyOS patch stack already applied"
else
    git diff --quiet HEAD || { echo "Kernel checkout has unexpected changes; refusing to overwrite them" >&2; exit 1; }
    for patch in "${PATCHES[@]}"; do
        git apply --check "$patch"
        git apply "$patch"
    done
fi
if [ "${1:-}" = "--check-patches" ]; then
    exit 0
fi
M=(O=out-hmos ARCH=arm64 LLVM=1 LLVM_IAS=1 CC=clang
   CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-gnu-
   CROSS_COMPILE_ARM32=arm-linux-gnueabi-)
make "${M[@]}" vendor/sdmsteppe-perf_defconfig vendor/davinci.config vendor/ohos.config
make "${M[@]}" -j"${JOBS:-4}" Image.gz dtbs
mkdir -p "$DEST"
cp out-hmos/arch/arm64/boot/Image.gz "$DEST/Image.gz"
cp out-hmos/arch/arm64/boot/dts/qcom/xiaomi-sdmmagpie.dtb "$DEST/davinci.dtb"
cp out-hmos/.config "$DEST/kernel.config"
echo "davinci HarmonyOS kernel -> $DEST"
