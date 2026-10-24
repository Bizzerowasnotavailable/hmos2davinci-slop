# hmos2sweet

**HarmonyOS 5 (OpenHarmony) per Redmi Note 10 Pro (sweet).**

`hmos2sweet` prende un **pacchetto OTA completo di HarmonyOS** (`update_full_base.zip`) e lo trasforma in una ROM
flashabile sul Redmi Note 10 Pro. Lo userspace resta quello Huawei. A sostituirlo ci pensano:

- un kernel LineageOS 4.14 (sm6150) con le patch per OpenHarmony;
- una serie di **patch selezionabili** che sostituiscono i driver Kirin con equivalenti per Snapdragon 732G:
  display, GPU, audio, coprocessori e altro.

> Progetto sperimentale. Nessuna immagine Huawei o Xiaomi è inclusa in questo repository: lo script le prende
> dai pacchetti che fornisci tu. Usa la ROM risultante solo per uso personale.

## Stato

| Funzione | Stato |
|---|---|
| Avvio, bootanimation, SceneBoard, launcher | ✅ |
| Display 1080x2400 a 120 Hz (DRM/KMS), luminosità, spegnimento/accensione | ✅ |
| GPU Adreno 618 (Mesa freedreno, OpenGL ES) | ✅ |
| Touch, tasti volume/accensione | ✅ |
| Lock screen senza PIN (niente TEE) | ✅ |
| Audio (altoparlanti, microfono) | 🟡 funziona; dominio sensori dell'ADSP servito da hexagonrpcd (da verificare) |
| WiFi | 🟡 BDF inviato dal kernel come faceva cnss-daemon (da verificare) |
| Bluetooth | 🟡 libreria vendor per WCN3990 (da verificare) |
| Sensori per le app (accelerometro, giroscopio, bussola, luce, gravità/rotazione) | 🟡 HAL su Snapdragon Sensor Core via QRTR/QMI (da verificare) |
| Batteria, ricarica | 🟡 HAL HarmonyOS standard su power_supply di sweet (da verificare) |
| Vibrazione | 🟡 aw8624 esposto come /sys/class/leds/vibrator (vibrazioni a tempo; effetti haptic no) |
| Telefonia: SIM, rete, chiamate, SMS, dati mobili | 🟡 libreria RIL nostra sul modem Qualcomm via QMI/QRTR; SIM 2 senza rete, niente VoLTE (da verificare) |
| GPS | 🟡 motore GNSS del modem via QMI LOC, senza A-GPS (da verificare) |
| Infrarossi | 🟡 LED IR via ir-spi (/dev/lirc0) (da verificare) |
| Termica | 🟡 sensori reali di sweet, politica propria (da verificare) |
| USB (hdc, trasferimento file) | 🟡 gadget configfs per il controller Snapdragon (da verificare) |
| Fotocamera, impronta, NFC, sensore di prossimità, VoLTE | 🔴 non ancora: richiedono i blob Android/TEE di Qualcomm (vedi docs/TROUBLESHOOTING.md) |

Testato con: HarmonyOS 5.1 OTA completo del Huawei Pura 70 (`update_full_base.zip`, luglio 2025).
Altre versioni di HarmonyOS 5.x dovrebbero convertirsi. Le patch che modificano file di sistema verificano cosa
trovano e saltano il passaggio se il file è diverso da quello atteso.

## Cosa serve

- **Linux** (oppure **WSL** su Windows) con Python 3.8+, `e2fsprogs` (`debugfs`), `unzip`, `curl`.
  `pip install brotli`, oppure il comando `brotli`, se la ROM sweet usa `vendor.new.dat.br`.
- Circa **25 GB liberi**: immagini estratte, alberi temporanei e output.
- **OTA HarmonyOS completo** (`update_full_base.zip`, quello con `update.bin` dentro).
- **Una ROM per Redmi Note 10 Pro** con immagini a blocchi (`vendor.new.dat.br` + `vendor.transfer.list`, per esempio
  LineageOS), oppure un `vendor.img` estratto. Da qui vengono il firmware di GPU, IPA, amplificatori audio, WiFi
  e i mixer audio di sweet.
- Telefono con **bootloader sbloccato**, `fastboot` e `adb` (platform-tools) nel PATH, una recovery (TWRP/OrangeFox)
  per leggere i log.

## Uso

```sh
git clone https://github.com/<tu>/hmos2sweet && cd hmos2sweet
tools/fetch_tools.sh                     # scarica gli strumenti EROFS in tools/bin
python3 hmos2sweet.py --ota ~/update_full_base.zip --sweet-rom ~/lineage-22-sweet.zip --out out
```

Si apre la lista delle patch:

```
  Patches to apply  (number = toggle, a = all, n = none, d = defaults,
                     i<number> = details, Enter = continue, q = quit)

     [=] Core: kernel, preinit, fstab
   1 [x] Display: DRM/KMS composer + buffer allocator
   2 [x] GPU: Mesa freedreno (Adreno 618) for OpenGL ES
   ...
  ...
  23 [x] Remove the setup wizard (skip first-boot setup)
  24 [ ] Debug tools (sqlite3)
```

- numero (o più numeri separati da spazio): attiva/disattiva;
- `a` attiva tutto, `n` disattiva tutto, `d` torna ai predefiniti;
- `i3` mostra la descrizione della patch 3;
- Invio per continuare.

Le dipendenze si gestiscono da sole. Se attivi l'audio si attiva anche "Modem/ADSP bring-up"; se spegni
quest'ultimo si spengono anche audio e WiFi.

Senza menu (script, CI):

```sh
python3 hmos2sweet.py --ota OTA.zip --sweet-rom ROM.zip --patches defaults            # predefiniti
python3 hmos2sweet.py --ota OTA.zip --sweet-rom ROM.zip --patches all,-60             # tutto tranne debug-tools
python3 hmos2sweet.py --ota OTA.zip --sweet-rom ROM.zip --patches defaults --keep-setup-wizard
python3 hmos2sweet.py --list                                                          # elenco patch
```

### Setup wizard e WiFi

Il setup iniziale di HarmonyOS non si può completare senza connettersi a una rete WiFi, e il WiFi su sweet è
ancora sperimentale. Per questo la patch **"Remove the setup wizard"** è attiva di default:

- rimuove `HwStartupGuide` da `system.img`. I file originali vengono salvati in `out/removed/`, così li puoi
  rimettere quando il WiFi funzionerà;
- segna il primo avvio come completato nel database delle impostazioni (`device_provisioned`,
  `user_setup_complete`).

Si controlla dal menu, oppure con `--no-setup-wizard` (forza la rimozione) e `--keep-setup-wizard` (lo tiene).

## Installazione

Nella cartella di output trovi:

| File | |
|---|---|
| `system.img`, `vendor.img`, `chip_prod.img`, `sys_prod.img`, `cust.img`, `patch.img` | partizioni logiche (in `super`) |
| `boot.img`, `dtbo.img` | kernel + ramdisk HarmonyOS con `hmos-preinit` |
| `install_clean.bat` / `.sh` | **prima installazione**: cancella Android e TUTTI i dati, crea le partizioni HarmonyOS |
| `update_keep_data.bat` / `.sh` | aggiornamento da una build hmos2sweet precedente, **i dati restano** |
| `get_logs.bat` / `.sh` | dalla recovery: copia log del kernel, hilog e screenshot del boot |
| `BUILD_INFO.txt` | versione OTA e patch usate |
| `removed/` | file tolti dalle immagini (setup wizard) |

1. Telefono in fastboot (Power + Volume giù).
2. `install_clean.bat` (Windows) oppure `./install_clean.sh` (Linux). Chiede di scrivere `YES`.
3. Il primo avvio dura alcuni minuti.

Per tornare ad Android basta flashare di nuovo una ROM sweet dalla recovery: il `super` viene ricreato dalla ROM.

### Log

Il ramdisk contiene `hmos-preinit`, che a ogni avvio salva nella partizione `cache`:

- il log del kernel;
- istantanee di hilog, processi e servizi;
- uno screenshot.

Per leggerli: avvia la recovery (Power + Volume su), poi lancia `get_logs.bat` / `get_logs.sh`.

## Struttura del repository

```
hmos2sweet.py          convertitore (menu patch, estrazione OTA, build immagini, script di flash)
lib/                   moduli Python: OTA Huawei, EROFS, boot.img, ROM sweet, patch, script
patches/NN-nome/       una cartella per patch: patch.json (+ hook.py) + files/ con i binari
prebuilt/              kernel (Image.gz, dtb, dtbo.img) e hmos-preinit
src/                   sorgenti di tutto quello che è in patches/ e prebuilt/
  kernel/patches/        patch sul kernel LineageOS android_kernel_xiaomi_sm6150 (lineage-24.0)
  preinit/               hmos-preinit (/init: mappa super, log, poi /bin/init_early di HarmonyOS)
  display/               composer DRM/KMS + allocatore dma-buf (VDI OpenHarmony)
  mesa/                  patch Mesa 26.1: piattaforma EGL OHOS, import YUV
  audio/                 HAL audio VDI su tinyalsa
  userauth/ huks/        stub user_auth senza TEE, HUKS software
  remoteproc/            sweet-rproc + patch a rmtfs/tqftpserv/pd-mapper (linux-msm)
  sensors/               hexagonrpcd per l'ADSP + HAL sensori (SSC via QRTR/QMI)
  bluetooth/             libreria vendor Bluetooth per WCN3990
  oobe/ idle/            sweet-oobedone (salta setup), segnaposto per demoni Kirin
build/                 script per ricompilare kernel e binari (vedi docs/BUILDING.md)
tools/                 fetch_tools.sh (erofs-utils)
flash/                 script per i log
docs/                  architettura, patch, compilazione, problemi noti
```

Ogni patch è descritta in [docs/PATCHES.md](docs/PATCHES.md). Come funziona il port è spiegato in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), e per ricompilare i binari c'è [docs/BUILDING.md](docs/BUILDING.md).

## Licenze

Gli script di questo repository sono sotto Apache-2.0. Le singole parti hanno licenze diverse:

- kernel e patch kernel: GPL-2.0;
- codice derivato da OpenHarmony: Apache-2.0;
- Mesa: MIT;
- tinyalsa e linux-msm: BSD-3-Clause;
- sqlite: pubblico dominio.

I dettagli sono in [NOTICE.md](NOTICE.md). HarmonyOS, Huawei, Xiaomi e Redmi sono marchi dei rispettivi
proprietari. Questo progetto non è affiliato con nessuno di loro.
