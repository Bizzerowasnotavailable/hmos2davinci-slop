# Componenti e licenze

| Percorso | Origine | Licenza |
|---|---|---|
| `hmos2sweet.py`, `lib/`, `patches/*/patch.json`, `patches/*/hook.py`, `tools/`, `build/*.sh`, `flash/` | questo progetto | Apache-2.0 |
| `src/kernel/patches`, `prebuilt/kernel` | LineageOS android_kernel_xiaomi_sm6150 + patch di questo progetto (parti da OpenHarmony kernel_linux_5.10) | GPL-2.0 |
| `src/preinit`, `prebuilt/ramdisk/init` | questo progetto | GPL-2.0 |
| `src/display`, `patches/10-display/files` | derivato da OpenHarmony drivers_peripheral (display) | Apache-2.0 |
| `src/display/hdi-gen` | header generati dalle IDL HDI di OpenHarmony | Apache-2.0 |
| `src/audio/vdi` | header VDI audio di OpenHarmony drivers_peripheral | Apache-2.0 |
| `src/audio/sweet_audio_vdi.cpp`, `patches/31-audio/files` | questo progetto, con tinyalsa (BSD-3-Clause) | Apache-2.0 |
| `src/huks`, `patches/21-huks-software/files` | OpenHarmony security_huks, OpenSSL 3 | Apache-2.0 |
| `src/userauth`, `src/oobe`, `src/idle`, `src/remoteproc/sweet-rproc.c` | questo progetto | Apache-2.0 |
| `src/remoteproc/patches`, `patches/30-remoteproc/files` | linux-msm qrtr, rmtfs, tqftpserv, pd-mapper | BSD-3-Clause |
| `src/mesa`, `patches/11-gpu-mesa/files` | Mesa 3D | MIT |
| `src/sensors/compat`, `src/sensors/sweet_fastrpc.c`, `patches/34-sensors-pd/files` | linux-msm hexagonrpc + shim per il driver adsprpc downstream | GPL-3.0 |
| `src/sensors/sweet_sensors_vdi.cpp`, `patches/39-sensors-hal/files` | questo progetto | Apache-2.0 |
| `src/sensors/vdi` | header VDI sensori di OpenHarmony drivers_peripheral | Apache-2.0 |
| `src/bluetooth`, `patches/35-bluetooth/files` | questo progetto (sequenza WCN3990 come in Linux btqca/hci_qca) | Apache-2.0 |
| `patches/50-remove-setup-wizard/files`, `patches/60-debug-tools/files` | sqlite | pubblico dominio |
| `build/sysroot-base.tar.xz` | musl (MIT), LLVM libc++ (Apache-2.0 with LLVM exception), Linux UAPI (GPL-2.0 WITH Linux-syscall-note), libdrm (MIT) | varie |
| `tools/bin` (scaricato) | sekaiacg/erofs-utils | GPL-2.0 / Apache-2.0 |

Nessuna immagine o libreria Huawei o Xiaomi è inclusa: `hmos2sweet.py` le legge dai pacchetti forniti dall'utente
al momento della conversione.
