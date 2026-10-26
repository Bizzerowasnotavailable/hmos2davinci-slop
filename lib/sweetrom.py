"""Get the Redmi Note 10 Pro (sweet) vendor blobs the port needs.

Accepted sources:
  * a flashable sweet ROM zip with block images (vendor.new.dat.br or
    vendor.new.dat + vendor.transfer.list), e.g. LineageOS or most custom ROMs;
  * a raw ext4 vendor.img dumped from a sweet ROM.

Only firmware and audio configuration files are taken (list in each patch's
"sweet_blobs"); they stay on your computer and are never part of the repo.
"""
import os
import re
import shutil
import subprocess
import zipfile
import struct

from .util import die, info, tool, run, mkdirs

BLOCK = 4096


def _brotli_decompress(src, dst):
    try:
        import brotli  # pip install brotli
        d = brotli.Decompressor()
        with open(src, "rb") as i, open(dst, "wb") as o:
            while True:
                b = i.read(1 << 20)
                if not b:
                    break
                o.write(d.process(b))
        return
    except ImportError:
        pass
    exe = shutil.which("brotli")
    if not exe:
        die("vendor.new.dat.br needs brotli: 'pip install brotli' or install the brotli tool")
    args = [exe, "-d", "-f", "-o", dst, src]
    # When the Linux build is run from WSL, a Windows brotli.exe can be on
    # PATH but it cannot consume /mnt/c paths.  Give it native Windows paths.
    if os.name != "nt" and (exe.lower().endswith(".exe") or os.path.realpath(exe).lower().endswith(".exe")):
        def winpath(p):
            return subprocess.check_output(["wslpath", "-w", p]).decode().strip()
        args = [exe, "-d", "-f", "-o", winpath(dst), winpath(src)]
    run(args)


def _rangeset(s):
    v = [int(x) for x in s.split(",")]
    return list(zip(v[1::2], v[2::2]))


def _sdat2img(transfer_list, new_dat, out_img):
    """Rebuild an image from a block-based OTA transfer list (versions 1-4)."""
    with open(transfer_list) as f:
        lines = [l.strip() for l in f if l.strip()]
    version = int(lines[0])
    cmds = lines[2:] if version == 1 else lines[4:]
    max_block = 0
    ops = []
    for line in cmds:
        parts = line.split(" ")
        if parts[0] in ("new", "zero", "erase"):
            rs = _rangeset(parts[1])
            ops.append((parts[0], rs))
            for _, e in rs:
                max_block = max(max_block, e)
    with open(new_dat, "rb") as src, open(out_img, "wb") as dst:
        dst.truncate(max_block * BLOCK)
        for op, rs in ops:
            if op != "new":
                continue
            for b, e in rs:
                dst.seek(b * BLOCK)
                left = (e - b) * BLOCK
                while left:
                    chunk = src.read(min(left, 16 << 20))
                    if not chunk:
                        die("vendor.new.dat shorter than its transfer list")
                    dst.write(chunk)
                    left -= len(chunk)


def vendor_image(source, workdir):
    """Return the path of an ext4 sweet vendor image built from 'source'."""
    if not os.path.exists(source):
        die("sweet ROM not found: %s" % source)
    if not zipfile.is_zipfile(source):
        return source  # raw vendor.img
    out = os.path.join(workdir, "sweet_vendor.img")
    if os.path.isfile(out):
        info("sweet vendor image already unpacked")
        return out
    z = zipfile.ZipFile(source)
    names = z.namelist()
    if "vendor.transfer.list" not in names:
        if "payload.bin" in names:
            die("payload.bin ROMs are not supported yet: extract vendor.img with "
                "payload-dumper and pass it with --sweet-rom vendor.img")
        die("%s has no vendor.transfer.list / vendor.new.dat(.br)" % source)
    tmp = mkdirs(os.path.join(workdir, "sweet_rom"))
    z.extract("vendor.transfer.list", tmp)
    tl = os.path.join(tmp, "vendor.transfer.list")
    if "vendor.new.dat.br" in names:
        info("unpacking vendor.new.dat.br")
        z.extract("vendor.new.dat.br", tmp)
        dat = os.path.join(tmp, "vendor.new.dat")
        _brotli_decompress(os.path.join(tmp, "vendor.new.dat.br"), dat)
        os.remove(os.path.join(tmp, "vendor.new.dat.br"))
    elif "vendor.new.dat" in names:
        z.extract("vendor.new.dat", tmp)
        dat = os.path.join(tmp, "vendor.new.dat")
    else:
        die("%s has no vendor.new.dat(.br)" % source)
    info("rebuilding vendor.img from the transfer list")
    _sdat2img(tl, dat, out + ".part")
    os.replace(out + ".part", out)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def _debugfs(img, cmd):
    p = subprocess.run([tool("debugfs"), "-R", cmd, img], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.stdout.decode(errors="replace"), p.stderr.decode(errors="replace")


def check_vendor(img):
    out, err = _debugfs(img, "ls -p /firmware")
    if "a630_sqe.fw" not in out:
        die("%s does not look like a sweet vendor image (no /firmware/a630_sqe.fw)\n%s" % (img, err[-500:]))


def android_boot_artifacts(source, workdir):
    """Extract the kernel, DTB and DTBO from a Lineage Android boot package."""
    if not source or not zipfile.is_zipfile(source):
        die("davinci needs a Lineage/custom ROM zip containing boot.img and dtbo.img")
    out = mkdirs(os.path.join(workdir, "device_boot"))
    z = zipfile.ZipFile(source)
    for n in ("boot.img", "dtbo.img", "vbmeta.img"):
        if n not in z.namelist():
            die("%s has no %s" % (source, n))
    info("extracting davinci kernel and device trees from %s" % os.path.basename(source))
    boot = z.read("boot.img")
    # Android boot header v2/v3-compatible fields used by davinci's current
    # Lineage build.  The supplied package is v2 and carries a separate DTB.
    if boot[:8] != b"ANDROID!":
        die("unsupported Android boot header in %s" % source)
    h = struct.unpack("<8s10I16s512s32s1024sIQIIQ", boot[:1660])
    page, ksize, rsize, dtb_size = h[8], h[1], h[3], h[18]
    def span(size, pos):
        return pos + ((size + page - 1) // page) * page
    kpos = page
    rpos = span(ksize, kpos)
    dtbpos = span(rsize, rpos)
    if not dtb_size or len(boot) < dtbpos + dtb_size:
        die("davinci boot.img has no separate DTB")
    paths = {"kernel": os.path.join(out, "Image"), "dtb": os.path.join(out, "davinci.dtb"),
             "dtbo": os.path.join(out, "dtbo.img"), "vbmeta": os.path.join(out, "vbmeta.img")}
    open(paths["kernel"], "wb").write(boot[kpos:kpos + ksize])
    open(paths["dtb"], "wb").write(boot[dtbpos:dtbpos + dtb_size])
    open(paths["dtbo"], "wb").write(z.read("dtbo.img"))
    open(paths["vbmeta"], "wb").write(z.read("vbmeta.img"))
    return paths


def super_empty(source, out):
    """Extract Lineage's retrofit dynamic-partition metadata template."""
    if not source or not zipfile.is_zipfile(source):
        die("davinci needs a Lineage ROM zip containing unsparse_super_empty.img")
    with zipfile.ZipFile(source) as z:
        name = "unsparse_super_empty.img"
        if name not in z.namelist():
            die("%s has no %s" % (source, name))
        with open(out, "wb") as fh:
            fh.write(z.read(name))
    return out


def davinci_hmos_boot_artifacts(source, workdir):
    """Use davinci device trees/AVB from LOS, but a patched OHOS kernel.

    Stock LOS kernels lack EROFS, devtmpfs and the OHOS binder/token ABI.
    Never silently build another unbootable image using the stock kernel.
    """
    from .util import REPO
    paths = android_boot_artifacts(source, workdir)
    kernel_dir = os.path.join(REPO, "prebuilt", "kernel", "davinci")
    for key, filename in (("kernel", "Image.gz"), ("dtb", "davinci.dtb")):
        path = os.path.join(kernel_dir, filename)
        if not os.path.isfile(path):
            die("missing %s; run build/build_davinci_kernel.sh under Linux/WSL first" % path)
        paths[key] = path
    return paths


def fetch(img, blobs, outdir):
    """Copy blobs ([{"from": "firmware/x", "to": "firmware/x"}], trailing / = directory)."""
    got = []
    for b in blobs:
        src, dst = b["from"], os.path.join(outdir, b["to"])
        probe, probe_err = _debugfs(img, "stat /%s" % src.rstrip("/"))
        if "not found" in (probe + probe_err).lower() or "no such file" in (probe + probe_err).lower():
            # Device ROMs often omit sweet-only amplifier/camera files.  They
            # must not prevent a bootable davinci base image being produced;
            # the corresponding optional patch component is skipped below.
            info("  optional blob missing on target ROM: /%s" % src)
            continue
        if src.endswith("/"):
            mkdirs(dst)
            # a fresh folder for every directory blob: the previous one may not be removable
            n = 0
            while os.path.exists(os.path.join(outdir, ".rdump%d" % n)):
                n += 1
            tmp = mkdirs(os.path.join(outdir, ".rdump%d" % n))
            _debugfs(img, "rdump /%s %s" % (src.rstrip("/"), tmp))
            name = os.path.basename(src.rstrip("/"))
            if not os.path.isdir(os.path.join(tmp, name)):
                die("blob directory /%s not found in the sweet vendor image" % src)
            for f in sorted(os.listdir(os.path.join(tmp, name))):
                shutil.move(os.path.join(tmp, name, f), os.path.join(dst, f))
                got.append(os.path.join(b["to"], f))
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            mkdirs(os.path.dirname(dst))
            path = "/" + src
            for _ in range(4):  # follow (vendor-relative) symlinks
                st, _ = _debugfs(img, "stat %s" % path)
                m = re.search(r'Fast link dest: "([^"]+)"', st)
                if not m:
                    break
                tgt = m.group(1)
                path = tgt[len("/vendor"):] if tgt.startswith("/vendor/") else \
                    os.path.normpath(os.path.join(os.path.dirname(path), tgt))
            _debugfs(img, "dump %s %s" % (path, dst))
            if not os.path.isfile(dst) or os.path.getsize(dst) == 0:
                die("blob /%s not found in the sweet vendor image" % src)
            got.append(b["to"])
    return got
