# Rebuilding the binaries

`hmos2sweet.py` uses the binaries already built in `prebuilt/` and `patches/*/files/`. Rebuilding them is only
needed if you change the sources in `src/`. All scripts are in `build/` and read their settings from
`build/env.sh`.

For `--device davinci`, pass the target LineageOS/custom ROM zip with
`--device-rom`. Its `dtbo.img` provides the davinci overlay and its vendor
block image supplies Qualcomm firmware blobs. **Do not use its stock kernel:**
the supplied LineageOS build disables both EROFS and devtmpfs and lacks the
HarmonyOS binder/access-token extensions. Build a patched davinci kernel first:

```sh
# Linux/WSL; keep the kernel checkout on the native Linux filesystem.
bash build/build_davinci_kernel.sh
# Output: prebuilt/kernel/davinci/{Image.gz,davinci.dtb,kernel.config}
```

The script pins the matching LineageOS source revision, selects
`vendor/davinci.config` (not `vendor/sweet.config`), and applies only the
generic HarmonyOS patches. Set `DAVINCI_KERNEL` to change the checkout location
and `JOBS` to change build parallelism (default 4).

Build
on Linux/WSL using a native Linux work directory because HarmonyOS contains
case-sensitive paths such as `etc/NFC` and `etc/nfc`.

| Script | Produces | Needs |
|---|---|---|
| `build_kernel.sh` | `prebuilt/kernel/{Image.gz,xiaomi-sdmmagpie.dtb,dtbo.img}` | clang/lld 15+, `aarch64-linux-gnu-` and `arm-linux-gnueabi-` binutils |
| `build_davinci_kernel.sh` | `prebuilt/kernel/davinci/{Image.gz,davinci.dtb,kernel.config}` | same kernel build tools, make, gcc, bc, bison, flex, libssl-dev, libelf-dev |
| `build_static.sh` | hmos-preinit, sweet-rproc, qrtr/rmtfs/tqftpserv/pd-mapper, sweet-oobedone, sqlite3, CameraDaemon placeholder | `aarch64-linux-gnu-gcc` (static glibc) |
| `fetch_oh_sources.sh` | OpenHarmony 5.1 sources (HDI/HDF headers, HUKS, OpenSSL) | git |
| `make_sysroot.sh <work>` | HarmonyOS sysroot for `ohos-clang` | an hmos2sweet `work` folder (`ota/system.img`, `ota/vendor.img`) |
| `build_ohos.sh` | composer + allocator, audio, user_auth, HUKS, sensors, RIL, GNSS, IR | clang/lld, llvm-strip, sysroot, OH sources |
| `build_iam.sh` | OpenHarmony REE user_auth / pin_auth HDI services (patch 46) | as above + hdi-gen output for user_auth/pin_auth |
| `build_camera_android.sh` | cambridge (bionic) + sweetcam-launch (static), patch 47 | clang/lld, AOSP headers in `$AOSP`, bionic runtime of a sweet ROM in `$ANDROID_LIBS` + crt objects in `$ANDROID_CRT` |
| `build_mesa.sh` | Mesa (EGL/GLES + gallium freedreno) | meson, ninja, python3-mako/yaml, `MESA_SRC` (Mesa 26.1-devel) |
| `build_all.sh <work>` | everything above | |

## Notes

- **`ohos-clang`** builds for `aarch64-linux-ohos` (OpenHarmony's musl). It uses libc++ with the `__h` ABI
  namespace, the same as HarmonyOS, so the binaries link against the phone's system libraries.
- **Sysroot**:
  - headers and crt objects come from `build/sysroot-base.tar.xz` (musl, libc++, Linux UAPI, libdrm, all open
    source);
  - the `.so` libraries to link against are copied from the OTA images, which is why `make_sysroot.sh` wants the
    `work` folder of a conversion.
- **Kernel**: LineageOS `android_kernel_xiaomi_sm6150`, branch `lineage-24.0`, commit `e03e5ba22`, with
  `vendor/sdmsteppe-perf_defconfig vendor/sweet.config vendor/ohos.config`.
- **Mesa**: `src/mesa/0001-mesa-ohos-platform-for-sweet.patch` was made on `mesa-for-android-container-adreno`
  26.1.0-devel. Other Mesa 26 versions may need small adjustments.
- **Camera (work in progress)**: `src/camera/bridge/cambridge.c` is built for Android (bionic) with clang
  `--target=aarch64-linux-android33`, the AOSP bionic/libhardware/system_core/system_media headers and linked
  against the bionic libraries of a sweet Android ROM; `src/camera/launcher` is a static glibc binary.

## Adding a patch

1. Create `patches/NN-name/patch.json` with:
   - `name`, `description`, `default`;
   - `requires` for dependencies;
   - the actions: `vendor_files` (`src`/`dst`/`mode`), `vendor_dirs`, `vendor_remove`, `system_remove`,
     `sweet_blobs` (`from`/`to`, trailing `/` for folders), `markers`, `ueventd`;
   - `init`, with `jobs` and `services` in the HarmonyOS init cfg format.
2. Binaries go to `patches/NN-name/files/`, sources to `src/`.
3. To modify files taken from the OTA add a `hook.py` with an `apply(ctx)` function. `ctx` provides:
   - `ctx.vendor` and `ctx.system()`: EROFS trees with `read`/`write`/`add_file`/`remove`/`exists`;
   - `ctx.image_file(partition, path)` to read a file from an untouched image;
   - `ctx.save_removed()` to keep the removed files.
4. `python3 tools/gen_patch_docs.py` updates `docs/PATCHES.md`.

The numbers decide the order in which patches are applied and the order of the commands in the init cfg.
