#!/usr/bin/env python3
"""Rebuild only the davinci boot image after changing hmos-preinit."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import bootimg, devices, flashgen, sweetrom

OUT = "out-davinci-built"
WORK = "work-davinci-full"
ROM = "firmware/lineage-23.2-20261025-nightly-davinci-signed.zip"

d = devices.get("davinci")
a = sweetrom.davinci_hmos_boot_artifacts(ROM, WORK)
rd = bootimg.build_ramdisk(os.path.join(WORK, "ota", "ramdisk.img"), "prebuilt/ramdisk/init")
cmd = ("hardware=%s default_boot_device=%s console=ttyMSM0,115200n8 "
       "earlycon=msm_geni_serial,0x880000 service_locator.enable=1 "
       "lpm_levels.sleep_disabled=1 loop.max_part=7 buildvariant=user "
       "enforcing=0 hmos.permissive=1 hmos.noreboot=1 printk.devkmsg=on "
       "audit=0 firmware_class.path=/vendor/firmware") % (d.hardware, d.default_boot_device)
bootimg.build_boot(a["kernel"], rd, a["dtb"], cmd, os.path.join(OUT, "boot.img"))
for name in ("dtbo", "vbmeta"):
    import shutil
    shutil.copyfile(a[name], os.path.join(OUT, name + ".img"))
parts = [p for p in flashgen.HMOS_LOGICAL if os.path.isfile(os.path.join(OUT, p + ".img"))]
flashgen.write(OUT, parts, open(os.path.join(OUT, "BUILD_INFO.txt")).read(), d)
