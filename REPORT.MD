# Davinci HarmonyOS bring-up report

## Outcome

On **26 October 2026**, the device owner confirmed that HarmonyOS booted on a
**Redmi K20/Xiaomi Mi 9T (`davinci`, Snapdragon 730)**. The confirmation came
after flashing the OHOS-patched davinci kernel and corrected preinit in a new
boot image, plus vbmeta with verification disabled.

This confirms boot, **not complete hardware support or release readiness**.
No subsequent per-feature validation was recorded. The inherited sweet status
table must not be advertised as davinci results.

## Tested inputs and final artifact

| Component | Input / identifier |
|---|---|
| HarmonyOS OTA | `update_full_base_ADY-LGRP3-CHN_205.1.0.128_SP5_.zip` |
| OTA identifier in local build summary | `ADY-AL10 20510128` |
| Davinci Android base | `lineage-23.2-20261025-nightly-davinci-signed.zip` |
| Kernel repository | `https://github.com/LineageOS/android_kernel_xiaomi_sm6150` |
| Kernel base commit | `e03e5ba22586be70673afb5d3c3f70510524e658` |
| Kernel selection | `vendor/sdmsteppe-perf_defconfig vendor/davinci.config vendor/ohos.config` |
| Final compiler used | Ubuntu Clang 21.1.8; LLVM linker/tools |
| Final boot image | Local `out-davinci-built/boot.img` |
| Final boot SHA-256 | `0aa260be3d1544cc9e5db688177f649628841f54538505663f1cbafe9e817568` |

Recovery images were supplied locally as `LOS.img` and `ofox.img`; exact upstream
recovery release identifiers were not recorded. Obtain compatible recoveries
from their maintainers instead of treating these filenames as version guarantees.

The logical image build summary predates the final kernel/preinit rebuild.
`BUILD_INFO.txt` records selected patch names, including inherited sweet names,
but does not on its own identify the final working boot image. The hash above
identifies the tested boot artifact, not future reproducible builds.

## Diagnosis

### 1. Stock LineageOS kernel was not a suitable OHOS kernel

The initial port extracted the kernel/DTB from LOS and combined them with the
HarmonyOS ramdisk. The kernel booted LOS, but its embedded configuration showed:

```text
# CONFIG_DEVTMPFS is not set
# CONFIG_EROFS_FS is not set
```

Preinit assumed devtmpfs would populate `/dev`, and the logical images used
EROFS. Missing device nodes could prevent both block access and persistent
logging; without EROFS the kernel could not mount the port's images. The stock
kernel also lacked the OHOS binder/access-token extensions included by the
original project's kernel patches.

**Fix:** build the matching LOS kernel source with davinci's device config and
the generic OHOS patch subset. Do not apply sweet-specific vibrator/NFC/panel
changes indiscriminately. `build/build_davinci_kernel.sh` pins the source base
and selects the patch subset. `lib/sweetrom.py` now requires the patched davinci
kernel/DTB instead of silently using the stock LOS kernel.

Clang 21 exposed legacy WLAN enum conversions under the driver's `-Werror`.
Patches `0019` and `0020` correct one return value and demote only that enum
diagnostic within WLAN, retaining other compiler error checks.

### 2. Preinit did not handle retrofit backing devices

Davinci reports `super-partition-name:system`. Its LP metadata describes physical
backing devices `system`, `cust`, and `vendor`; each extent's `target_source`
selects one of them. The original mapper used the metadata device for every
extent, which is incorrect for this layout.

**Fixes in `src/preinit/preinit.c`:**

- Prefer physical `super`, with physical `system` as the retrofit fallback.
- Create block nodes using sysfs major/minor numbers when needed.
- Fall back to tmpfs if devtmpfs cannot be mounted; create essential char nodes.
- Resolve LP block-device names and honor each extent's `target_source`.
- Reject invalid table bounds, unsupported targets, unavailable sources, and
  oversized extent lists rather than silently truncating mappings.
- Start persistent logging before LP mapping so mapping failures can be captured.

### 3. Fastboot environment mattered

Earlier attempts repeatedly reset/flashed partitions without establishing a
working baseline. Some commands reported success while later metadata reads
were empty. Those observations did **not** prove that fastbootd could never
persist metadata, and missing `/cache/hmos` did **not** establish a metadata-only
failure.

The owner subsequently initialized the layout with `wipe-super`, installed LOS,
and confirmed LOS boot. After port flashing, OrangeFox inspection found valid
metadata with correct header/table checksums and all six HMOS partitions.
This ruled out another blind wipe as the next repair step.

`wipe-super` must not be confused with flashing a complete filesystem image.
Bootloader fastboot and userspace fastbootd can resolve `system` differently.
Lineage recovery supplied usable fastbootd; the supplied OrangeFox did not.

## Successful device test sequence

This records the observed sequence, **not a complete, validated installer**:

1. Owner initialized the layout using bootloader `wipe-super`, installed LOS via
   recovery, and confirmed LOS boot.
2. Owner flashed the port; the device still bootlooped with the stock kernel.
3. OrangeFox inspection verified LP checksums and sampled the beginning/end of
   every extent against the corresponding local image. All samples matched.
4. A patched davinci kernel and corrected static AArch64 preinit were built.
5. `tools/rebuild_davinci_boot.py` rebuilt boot using the existing HarmonyOS
   ramdisk/logical images and regenerated the flashing scripts.
6. The new boot image was checked for davinci, EROFS, devtmpfs, access-token and
   binder configuration, and for an exact match to the rebuilt preinit binary.
7. From bootloader fastboot, boot was flashed and vbmeta flashed with
   `--disable-verity --disable-verification`. Logical images, data, DTBO, and
   recovery were not reflashed during this final test.
8. The owner confirmed that HarmonyOS booted.

## Verification and limits

- Kernel compilation completed and the required embedded configuration was checked.
- Boot payloads matched the intended kernel and preinit before flashing.
- LP metadata checksums were checked on the captured physical metadata.
- All extent endpoint samples matched local logical images. This was **not** a
  full hash comparison of every flashed partition.
- `src/preinit/test_lp.c` passed on the host and as a static AArch64 executable
  on the phone in OrangeFox. It mocks device-mapper ioctls; it tests target
  construction, source selection, zero extents and invalid-source rejection,
  not actual kernel mapping/mounting in isolation.
- Installer-generation checks passed for both profiles, including disabled
  single-device `lpwrite` fallback and AVB-disable flags on davinci. No complete
  automated clean-install or keep-data upgrade was tested.

## Remaining work before a public ROM release

- Validate a fresh conversion and clean install with the final source changes.
- Record exact recovery versions, all input checksums and final image checksums.
- Test touch, display modes, brightness, suspend/resume and GPU acceleration.
- Test Wi-Fi, Bluetooth, audio, sensors, GPS, battery/charging and USB.
- Test SIM/data/calls/SMS/VoLTE; do not assume emergency calling works.
- Test cameras/pop-up motor, fingerprint and NFC.
- Audit remaining sweet-specific defaults: the inherited fixed-120-Hz policy,
  thermal/performance policy, IR, audio, haptics, NFC and camera assumptions.
  Davinci has a 60-Hz 1080x2340 panel; inherited patch labels do not prove that
  those settings are appropriate. The tested build also skipped setup wizard.
- Review permissive/debug settings, software key storage and security stubs;
  this is not a security-hardened production system.
- Validate Android restoration and update/rollback procedures before publishing
  an installation guide as reliable.

## GitHub upload checklist

### Include in the source fork

- `README.md`, `REPORT.MD`, `LICENSE`, `NOTICE.md`, `.gitignore`, `.gitattributes`.
- `hmos2sweet.py`, `fetchfw.py`, `fetchfw.bat`, and `lib/`.
- `src/`, especially all kernel patches, preinit changes and regression tests.
- `build/` scripts, `tools/` source/scripts, `flash/`, `docs/`.
- `patches/` manifests/hooks and only binary payloads whose licensing and
  provenance have been checked. Preserve inherited author/license notices.
- Existing required `prebuilt/` helpers only after the same review. Generated
  davinci kernel output is ignored by default and can be rebuilt from source.

**Create a real fork of the upstream repository on GitHub**, clone that fork,
and apply these changes so upstream history/attribution is preserved. This
workspace was supplied without `.git`; no commit, remote, fork or push has been
created here. Do not blindly run `git add .` on an unaudited copy.

### Exclude from Git history

- `firmware/`: Huawei/LOS input ZIPs and supplied recovery images.
- Every `out*/` and `work*/` folder: ROM images, extracted proprietary trees,
  `removed/`, raw dumps, logs and bundled platform-tools.
- `tools/bin/`, `build/work/`, WSL kernel checkouts/toolchains, caches and venvs.
- Device logs/screenshots with serials, identifiers, account/network details or
  other personal data. Review all diagnostic material before sharing it.
- Generated `prebuilt/kernel/davinci/` artifacts unless deliberately distributed
  separately with the applicable source/license obligations satisfied.

The updated `.gitignore` covers the main local paths. Ignore rules do **not**
remove files already tracked in an existing Git repository; inspect the index
before committing. GitHub normally blocks ordinary Git files over 100 MiB;
ROM images should not be put in Git history or used as a reason to add firmware
to Git LFS.

### Source versus release downloads

Source publication does not authorize redistribution of Huawei userspace,
Qualcomm/Xiaomi firmware, recoveries, or other third-party binaries. Check
permissions and applicable licenses before hosting any binary release. Releases
or external hosting are suitable only for artifacts you may redistribute.

For any permitted kernel/helper binary release, publish corresponding source
and build instructions as required by its license, retain notices, and include
SHA-256 checksums and clear experimental-device/install warnings. For a ROM
release, also include a dated hardware test matrix and a genuinely tested
installation/restore guide; neither is complete yet.
