"""Supported phone profiles.

The original project was written for sweet.  Keep that profile as the
default, but keep device-specific boot details out of the image builder so a
different SM7150 phone can supply its own kernel and device tree.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    hardware: str
    default_boot_device: str
    kernel_zip_entry: Optional[str] = None
    dtbo_zip_entry: Optional[str] = None
    panel_width: int = 1080
    panel_height: int = 2400
    panel_dpi: int = 460
    # None means that the device has no display cutout (davinci has a
    # motorised pop-up camera).
    cutout: Optional[Tuple[int, int, int, int]] = (444, 26, 192, 52)


DEVICES = {
    "sweet": Device("sweet", "Redmi Note 10 Pro", "sweet", "soc/1d84000.ufshc"),
    "davinci": Device(
        "davinci", "Redmi K20 / Xiaomi Mi 9T", "davinci", "soc/1d84000.ufshc",
        kernel_zip_entry="boot.img", dtbo_zip_entry="dtbo.img",
        panel_width=1080, panel_height=2340, panel_dpi=403, cutout=None,
    ),
}


def get(name):
    try:
        return DEVICES[name.lower()]
    except KeyError:
        raise ValueError("unknown device %r (choose: %s)" % (name, ", ".join(DEVICES)))
