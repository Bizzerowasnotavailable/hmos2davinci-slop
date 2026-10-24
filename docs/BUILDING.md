# Ricompilare i binari

`hmos2sweet.py` usa i binari già compilati in `prebuilt/` e `patches/*/files/`. Ricompilarli serve solo se
modifichi i sorgenti in `src/`. Tutti gli script stanno in `build/` e leggono le impostazioni da `build/env.sh`.

| Script | Produce | Serve |
|---|---|---|
| `build_kernel.sh` | `prebuilt/kernel/{Image.gz,xiaomi-sdmmagpie.dtb,dtbo.img}` | clang/lld 15+, binutils `aarch64-linux-gnu-` e `arm-linux-gnueabi-` |
| `build_static.sh` | hmos-preinit, sweet-rproc, qrtr/rmtfs/tqftpserv/pd-mapper, sweet-oobedone, sqlite3, CameraDaemon | `aarch64-linux-gnu-gcc` (glibc statico) |
| `fetch_oh_sources.sh` | sorgenti OpenHarmony 5.1 (header HDI/HDF, HUKS, OpenSSL) | git |
| `make_sysroot.sh <work>` | sysroot HarmonyOS per `ohos-clang` | una cartella `work` di hmos2sweet (`ota/system.img`, `ota/vendor.img`) |
| `build_ohos.sh` | composer + allocatore, audio, user_auth, HUKS | clang/lld, llvm-strip, sysroot, sorgenti OH |
| `build_mesa.sh` | Mesa (EGL/GLES + gallium freedreno) | meson, ninja, python3-mako/yaml, `MESA_SRC` (Mesa 26.1-devel) |
| `build_all.sh <work>` | tutto quanto sopra | |

## Note

- **`ohos-clang`** compila per `aarch64-linux-ohos` (musl di OpenHarmony). Usa la libc++ con namespace ABI `__h`,
  la stessa di HarmonyOS, quindi i binari si linkano contro le librerie di sistema del telefono.
- **Sysroot**:
  - header e oggetti crt vengono da `build/sysroot-base.tar.xz` (musl, libc++, UAPI Linux, libdrm, tutto open
    source);
  - le librerie `.so` contro cui linkare vengono copiate dalle immagini dell'OTA, per questo `make_sysroot.sh`
    vuole la cartella `work` di una conversione.
- **Kernel**: base LineageOS `android_kernel_xiaomi_sm6150`, ramo `lineage-24.0`, commit `e03e5ba22`, con
  configurazione `vendor/sdmsteppe-perf_defconfig vendor/sweet.config vendor/ohos.config`.
- **Mesa**: la patch `src/mesa/0001-mesa-ohos-platform-for-sweet.patch` è stata fatta su
  `mesa-for-android-container-adreno` 26.1.0-devel. Su altre versioni di Mesa 26 potrebbe servire qualche
  ritocco.

## Aggiungere una patch

1. Crea `patches/NN-nome/patch.json` con questi campi:
   - `name`, `description`, `default`;
   - `requires` per le dipendenze;
   - le azioni: `vendor_files` (`src`/`dst`/`mode`), `vendor_dirs`, `vendor_remove`, `system_remove`,
     `sweet_blobs` (`from`/`to`, con la `/` finale per le cartelle), `markers`, `ueventd`;
   - `init`, con `jobs` e `services` nel formato cfg di init HarmonyOS.
2. I binari vanno in `patches/NN-nome/files/` e i sorgenti in `src/`.
3. Per modificare file presi dall'OTA aggiungi `hook.py` con una funzione `apply(ctx)`. Da `ctx` hai:
   - `ctx.vendor` e `ctx.system()`: alberi EROFS, con `read`/`write`/`add_file`/`remove`/`exists`;
   - `ctx.image_file(partizione, percorso)` per leggere un file da un'immagine intatta;
   - `ctx.save_removed()` per salvare i file tolti.
4. `python3 tools/gen_patch_docs.py` aggiorna `docs/PATCHES.md`.

I numeri decidono l'ordine di applicazione e l'ordine dei comandi nel cfg di init.
