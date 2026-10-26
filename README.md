# HarmonyOS 5 for Redmi K20 / Xiaomi Mi 9T (`davinci`)

An experimental **davinci port based on hmos2sweet**. HarmonyOS has successfully
booted on a Redmi K20 / Mi 9T after replacing the stock LineageOS kernel with an
OHOS-patched davinci kernel and fixing early-init partition mapping.

**Boot confirmed by the device owner on 26 October 2026. This is not a fully
validated daily-driver ROM.** The original scripts and many component names
still say `sweet`; always pass **`--device davinci`**. The CLI still defaults
to `sweet`, whose functionality has not been regression-tested in this fork.

> **Warning:** flashing can erase all data or leave the phone unbootable.
> An unlocked bootloader is required. AVB verification is disabled for this
> experimental build, and bring-up uses permissive/debug settings and software
> security substitutes. Do not rely on it for sensitive data. Never relock the
> bootloader with this port installed.

## Davinci status

| Item | Verified status |
|---|---|
| HarmonyOS boots on the physical phone | **Confirmed by owner** |
| Patched davinci kernel builds | Confirmed |
| EROFS, devtmpfs, OHOS binder/access-token support in boot kernel | Verified |
| Retrofit LP metadata | Checksums verified; all six HMOS partitions present |
| Flashed image contents | First/last samples of every extent matched local images |
| Preinit mapping regression test | Passed on host and phone (mocked device-mapper ioctls) |
| Touch, brightness, GPU acceleration, setup completion | Not yet individually confirmed |
| Wi-Fi | **Not working — reported by owner; deferred investigation** |
| Audio | **Not working — reported by owner; deferred investigation** |
| Bluetooth, charging, sensors, GPS | Not yet individually confirmed |
| SIM, calls, SMS, mobile data, VoLTE | Untested |
| Camera/pop-up motor, fingerprint, NFC | Untested |
| Automated fresh install/update scripts | **Not validated end-to-end on davinci** |

The inherited sweet feature table below is **not** a davinci compatibility list.
See [REPORT.MD](REPORT.MD) for the boot investigation, tested inputs, limitations,
and publication checklist.

## Build for davinci

Use Linux or WSL. Keep extracted HarmonyOS trees on a **native Linux filesystem**
(for example under your WSL home), not a case-insensitive Windows directory.
Allow tens of GB for firmware, extracted trees, kernel sources, and build output.

Required inputs, obtained separately:

- HarmonyOS Pura 70 full OTA tested here:
  `update_full_base_ADY-LGRP3-CHN_205.1.0.128_SP5_.zip`.
- Davinci LineageOS package tested here:
  `lineage-23.2-20261025-nightly-davinci-signed.zip`.
- Device-compatible Lineage recovery for fastbootd/sideload and OrangeFox for logs.
  `LOS.img` and `ofox.img` were local filenames, not recovery release identifiers.

Install the converter dependencies described in the inherited requirements below.
For the kernel, also install clang/lld/llvm, make, gcc, bc, bison, flex,
libssl-dev, libelf-dev, and AArch64/ARM32 binutils. See
[docs/BUILDING.md](docs/BUILDING.md).

```sh
bash tools/fetch_tools.sh
bash build/build_davinci_kernel.sh
python3 hmos2sweet.py --device davinci \
  --ota /path/to/update_full_base_ADY-LGRP3-CHN_205.1.0.128_SP5_.zip \
  --device-rom /path/to/lineage-23.2-20261025-nightly-davinci-signed.zip \
  --work "$HOME/hmos-davinci-work" --out "$HOME/hmos-davinci-out" \
  --patches defaults --no-setup-wizard --keep-work
```

**Do not substitute the stock LOS kernel.** It disables EROFS and devtmpfs and
lacks the OHOS extensions needed by the port. The kernel script selects davinci,
not sweet, and writes `prebuilt/kernel/davinci/`. The converter requires these
patched artifacts. A fresh full conversion using the final fixes remains to be
tested; the successful device test reused existing logical images and replaced boot.

For the original local workspace only, `python3 tools/rebuild_davinci_boot.py`
rebuilds boot and regenerates scripts using its hard-coded firmware/work/output
paths. Edit those paths for another workspace; it is not a general release tool.

## Installation: read before flashing

There is **no validated one-click davinci installation procedure yet**.
The successful bring-up followed this route:

1. Initialize the retrofit layout with `fastboot wipe-super super_empty.img`
   from **bootloader fastboot**, using the template extracted from the matching
   davinci LOS ZIP. Then install LOS through Lineage recovery; LOS booted.
2. Use **Lineage fastbootd** to create/resize and flash the HMOS logical
   partitions: `system`, `vendor`, `chip_prod`, `sys_prod`, `cust`, `patch`.
3. Use **bootloader fastboot** for davinci DTBO, the corrected `boot.img`, and
   vbmeta with `--disable-verity --disable-verification`.
4. Boot HarmonyOS. OrangeFox is retained for recovery/log collection.

This is an observed sequence, **not a complete fresh-install recipe**. Back up
data first and establish a device-specific Android restore procedure before
attempting it. Do not blindly execute the generated installer scripts.

Davinci reports `super-partition-name:system`, but physical `system` and logical
`system` are different targets depending on the fastboot environment. **Do not
directly flash `super_empty.img` as a normal system image or repeat `wipe-super`
in fastbootd.** OrangeFox was not usable for fastbootd in this test; LOS recovery
was required. The shared `lpwrite` helper is single-backing-device only and its
fallback is disabled for davinci.

## Publishing this fork

Publish source code, patches, build scripts, documentation, and license notices.
**Do not upload your entire local workspace.** `firmware/`, `out*/`, `work*/`,
logs, downloaded tools, and the generated davinci kernel are ignored.

Retain inherited attribution and licenses. Audit inherited binaries in
`prebuilt/`, `patches/*/files/`, and `build/sysroot-base.tar.xz` before publishing;
an open-source origin does not remove source/notice obligations. Never publish
private device logs or assume Huawei/Qualcomm/Xiaomi blobs can be redistributed.
Full ROM images do not belong in Git history. Use releases or external hosting
only for artifacts you are authorized to redistribute, with checksums and
corresponding source/build information where required.

See the detailed **GitHub upload checklist** in [REPORT.MD](REPORT.MD).
No repository or release has been created or pushed by these instructions.

## Credits and licenses

Based on **hmos2sweet** and its contributors, with LineageOS's
[`android_kernel_xiaomi_sm6150`](https://github.com/LineageOS/android_kernel_xiaomi_sm6150),
OpenHarmony, Mesa, linux-msm, and other components listed in [NOTICE.md](NOTICE.md).
Preserve the upstream project's attribution when creating a public fork.
The top-level [LICENSE](LICENSE) does not replace component-specific licenses.

---

<details>
<summary>Inherited hmos2sweet documentation — sweet reference, not davinci test results</summary>

## Original project: hmos2sweet

The documentation below describes the inherited sweet project. Its hardware
claims and installation commands must not be assumed valid for davinci.

`hmos2sweet` takes a **HarmonyOS full OTA package** (`update_full_base.zip`) and turns it into a ROM you can flash
on the Redmi Note 10 Pro. The userspace stays Huawei's. What changes is underneath it:

- a LineageOS 4.14 (sm6150) kernel with the patches OpenHarmony needs;
- a set of **selectable patches** that replace the Kirin drivers with Snapdragon 732G equivalents: display, GPU,
  audio, coprocessors, telephony and more.

> Experimental project. No Huawei or Xiaomi image is included in this repository: the script takes them from
> the packages you provide. Use the resulting ROM for personal use only.

## Status

| Feature | Status |
|---|---|
| Boot, boot animation, SceneBoard, launcher, setup wizard | ✅ |
| Display 1080x2400 at 120 Hz (DRM/KMS), brightness, screen off/on | ✅ |
| GPU Adreno 618 (Mesa freedreno, OpenGL ES) | ✅ |
| Touch, volume/power keys | ✅ |
| WiFi, Bluetooth, GPS, audio | ✅ (reported working on the device) |
| Lock screen, PIN/password | 🟡 OpenHarmony's REE user_auth/pin_auth without TEE (fixed in iter42: vtable mismatch with HarmonyOS's HDI) |
| Sensors for apps (accelerometer, gyroscope, compass, light, gravity/rotation) | 🟡 HAL on the Snapdragon Sensor Core over QRTR/QMI |
| Battery, charging, off-mode charging | 🟡 standard HarmonyOS HAL on sweet's power_supply; with a charger plugged in "power off" keeps the phone off and charging |
| Vibration | 🟡 aw8624 exposed as /sys/class/leds/vibrator (timed vibration; no haptic effects) |
| Telephony: SIM, network, calls, SMS, mobile data | 🟡 our own RIL library on the Qualcomm modem over QMI/QRTR (untested without a SIM) |
| Call forwarding, call waiting, call barring, CLIP/CLIR, USSD | 🟡 QMI VOICE supplementary services (untested) |
| VoLTE / VoLTE-only calls | 🟡 attempt: IMS settings, IMS PDN, PS-only voice domain (untested) |
| NFC | 🟡 NXP PN553 driven by Huawei's NXP HAL + /sys/nfc from the kernel (untested) |
| IR blaster | 🟡 IR LED through ir-spi (/dev/lirc0) |
| Thermal | 🟡 real sweet sensors, own policy |
| USB (hdc, file transfer) | 🟡 configfs gadget for the Snapdragon controller |
| Camera | 🧪 first test build (patch 47): sweet's Android camera HAL (CamX) in an isolated Android environment + an OpenHarmony camera host |
| Fingerprint, proximity sensor | 🔴 not yet (need Qualcomm's Android/TEE blobs) |

Tested with: Huawei Pura 70 HarmonyOS 5.1 full OTA (`ADY-LGRP3-CHN 205.1.0.128(SP5)`, `update_full_base.zip`).
Other HarmonyOS 5.x versions of the Pura 70 should convert as well: the patches that edit system files check what
they find and skip the step if the file is not the expected one.

## Requirements

- **Linux** (or **WSL** on Windows) with Python 3.8+, `e2fsprogs` (`debugfs`), `unzip`, `curl`.
  `pip install brotli`, or the `brotli` command, if the sweet ROM uses `vendor.new.dat.br`.
- About **25 GB free**: extracted images, temporary trees and output.
- A **HarmonyOS full OTA** of the Huawei Pura 70 (`update_full_base.zip`, the one with `update.bin` inside).
  `fetchfw` (below) can find and download one for you.
- **A ROM for the Redmi Note 10 Pro** with block images (`vendor.new.dat.br` + `vendor.transfer.list`, e.g.
  LineageOS), or an extracted `vendor.img`. It provides sweet's GPU, IPA, audio amplifier, WiFi and camera
  firmware and its audio mixer paths.
- A phone with an **unlocked bootloader**, `fastboot` and `adb` (platform-tools) in PATH, and a recovery
  (TWRP/OrangeFox) to read the logs.

## Getting the firmware: fetchfw

`fetchfw` looks for every HarmonyOS package available for the **Huawei Pura 70**, shows the list, downloads
the one you pick (resumable, sha256-checked) and then starts `hmos2sweet.py` on it:

```sh
python3 fetchfw.py                                        # search, choose, download, port
python3 fetchfw.py -- --sweet-rom ~/lineage-sweet.zip --patches defaults
python3 fetchfw.py --list                                 # only list
python3 fetchfw.py --url <package URL>                    # check and add a package you found
python3 fetchfw.py --offline                              # only the catalogs on this computer
```

On Windows `fetchfw.bat` does the same. Where the packages come from:

- the shared catalog of this repository (`lib/fetchfw_catalog.json`, also read online from GitHub, so new
  entries reach every copy of the tool);
- public pages that list Huawei full packages (their `update_full_base.zip` links are collected);
- Huawei's update services (the HarmonyOS 5 `hota/version-query` one and the older `Check.action`): they
  normally answer only requests signed by a real phone, so they rarely add anything;
- your own list (`~/.hmos2sweet_fw.json`), filled automatically with every package found or added with `--url`.

Huawei's CDN paths contain a random id, so the packages cannot be enumerated directly. **Every candidate is
verified before it is offered**: its `filelist.xml` and the headers inside the zip (`packageinfo.mbn`,
`VERSION.mbn`, read with HTTP range requests) must describe a full BASE package of a Pura 70 (`ADY-*`);
packages of other phones are skipped. To share a new Pura 70 package with everybody, add it to
`lib/fetchfw_catalog.json` with a pull request.

## Usage

```sh
git clone https://github.com/<you>/hmos2sweet && cd hmos2sweet
tools/fetch_tools.sh                     # downloads the EROFS tools into tools/bin
python3 hmos2sweet.py --ota ~/update_full_base.zip --sweet-rom ~/lineage-sweet.zip --out out
# Redmi K20 / Mi 9T: build the OHOS-patched davinci kernel first (Linux/WSL).
bash build/build_davinci_kernel.sh
# The target ROM supplies DTBO, vbmeta and Qualcomm blobs, not a stock kernel.
python3 hmos2sweet.py --device davinci --ota OTA.zip --device-rom lineage-davinci.zip --out out
```

The patch list opens:

```
  Patches to apply  (number = toggle, a = all, n = none, d = defaults,
                     i<number> = details, Enter = continue, q = quit)

     [=] Core: kernel, preinit, fstab
   1 [x] Display: DRM/KMS composer + buffer allocator
   2 [x] GPU: Mesa freedreno (Adreno 618) for OpenGL ES
   ...
```

- a number (or several, separated by spaces) toggles a patch;
- `a` enables everything, `n` disables everything, `d` goes back to the defaults;
- `i3` shows the description of patch 3;
- Enter continues.

Dependencies are handled automatically: enabling audio also enables "Modem/ADSP bring-up", disabling the
latter also disables audio and WiFi.

Without the menu (scripts, CI):

```sh
python3 hmos2sweet.py --ota OTA.zip --sweet-rom ROM.zip --patches defaults            # defaults
python3 hmos2sweet.py --ota OTA.zip --sweet-rom ROM.zip --patches all,-60             # all but debug-tools
python3 hmos2sweet.py --ota OTA.zip --sweet-rom ROM.zip --patches defaults --no-setup-wizard
python3 hmos2sweet.py --list                                                          # patch list
```

### Setup wizard

HarmonyOS's first-boot setup needs a WiFi connection. WiFi works on sweet, so the wizard is kept by default.
If you cannot get through it, enable the **"Remove the setup wizard"** patch (or pass `--no-setup-wizard`):

- it removes `HwStartupGuide` from `system.img` (the original files are saved in `out/removed/`);
- it marks the first boot as completed in the settings database (`device_provisioned`, `user_setup_complete`).

## Installation

The output folder contains:

| File | |
|---|---|
| `system.img`, `vendor.img`, `chip_prod.img`, `sys_prod.img`, `cust.img`, `patch.img` | logical partitions (in `super`) |
| `boot.img`, `dtbo.img` | kernel + HarmonyOS ramdisk with `hmos-preinit` |
| `install_clean.bat` / `.sh` | **first install**: wipes Android and ALL data, creates the HarmonyOS partitions |
| `update_keep_data.bat` / `.sh` | update from a previous hmos2sweet build, **data is kept** |
| `get_logs.bat` / `.sh` | from recovery: copies the kernel log, hilog and boot screenshots |
| `BUILD_INFO.txt` | OTA version and patches used |
| `removed/` | files taken out of the images (setup wizard) |

1. Phone in fastboot (Power + Volume down).
2. `install_clean.bat` (Windows) or `./install_clean.sh` (Linux). It asks you to type `YES`.
3. The first boot takes a few minutes.

To go back to Android, flash a sweet ROM again from recovery: the ROM recreates `super`.

### Power off and charging

With a charger or a PC connected, "power off" makes the PMIC start the phone again in charging mode
(`androidboot.mode=charger`). `hmos-preinit` recognises it and does not start HarmonyOS: the screen stays off
and the phone keeps charging. Unplugging the cable powers it off; holding the power key for 1.5 s boots
HarmonyOS.

### Logs

The ramdisk contains `hmos-preinit`, which saves to the `cache` partition on every boot:

- the kernel log;
- snapshots of hilog, processes, threads and services;
- a screenshot.

To read them: boot the recovery (Power + Volume up), then run `get_logs.bat` / `get_logs.sh`. See
[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Repository layout

```
hmos2sweet.py          converter (patch menu, OTA extraction, image build, flash scripts)
fetchfw.py             finds/downloads Pura 70 firmware and runs hmos2sweet.py (lib/fetchfw.py)
lib/                   Python modules: Huawei OTA, EROFS, boot.img, sweet ROM, patches, scripts, fetchfw
patches/NN-name/       one folder per patch: patch.json (+ hook.py) + files/ with the binaries
prebuilt/              kernel (Image.gz, dtb, dtbo.img) and hmos-preinit
src/                   sources of everything in patches/ and prebuilt/
  kernel/patches/        patches on LineageOS android_kernel_xiaomi_sm6150 (lineage-24.0)
  preinit/               hmos-preinit (/init: maps super, logs, charger mode, then HarmonyOS /bin/init_early)
  display/               DRM/KMS composer + dma-buf allocator (OpenHarmony VDI)
  mesa/                  Mesa 26.1 patches: OHOS EGL platform, YUV import
  audio/                 audio VDI HAL on tinyalsa
  userauth/ huks/ iam/   user_auth stub without TEE, software HUKS, OpenHarmony REE user_auth/pin_auth
  remoteproc/            sweet-rproc + patches to rmtfs/tqftpserv/pd-mapper (linux-msm)
  sensors/               hexagonrpcd for the ADSP + sensors HAL (SSC over QRTR/QMI)
  bluetooth/             Bluetooth vendor library for WCN3990
  ril/ gnss/ ir/         RIL over QMI (calls, SMS, data, supplementary services, USSD, IMS), GNSS over QMI LOC, IR
  camera/                camera: Android HAL bridge (cambridge), namespace launcher, OpenHarmony camera host (WIP)
  oobe/ idle/ stubs/     sweet-oobedone (skip setup), placeholders for Kirin daemons, link stubs
build/                 scripts to rebuild the kernel and the binaries (see docs/BUILDING.md)
tools/                 fetch_tools.sh (erofs-utils), gen_patch_docs.py
flash/                 log scripts
docs/                  architecture, patches, building, known issues
```

Every patch is described in [docs/PATCHES.md](docs/PATCHES.md). How the port works is explained in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); rebuilding the binaries in [docs/BUILDING.md](docs/BUILDING.md).

## Licenses

The scripts in this repository are Apache-2.0. The individual parts have different licenses:

- kernel and kernel patches, hmos-preinit: GPL-2.0;
- code derived from OpenHarmony: Apache-2.0;
- Mesa: MIT;
- tinyalsa and linux-msm: BSD-3-Clause;
- sqlite: public domain.

Details are in [NOTICE.md](NOTICE.md). HarmonyOS, Huawei, Xiaomi and Redmi are trademarks of their respective
owners. This project is not affiliated with any of them.

</details>
