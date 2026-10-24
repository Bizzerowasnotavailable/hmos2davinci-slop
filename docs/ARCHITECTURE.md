# Come funziona il port

## Partenza

- **Donatore**: Huawei Pura 70 (Kirin 9010), HarmonyOS 5.1 = OpenHarmony 5.0/5.1 + servizi Huawei.
- **Destinazione**: Redmi Note 10 Pro *sweet* (Snapdragon 732G / sm6150, Adreno 618, WCN3990, codec Bolero +
  2× Awinic aw882xx, pannello AMOLED 1080x2400 120 Hz).

Lo userspace HarmonyOS (system, sys_prod, chip_prod, cust, patch) gira quasi intatto. Tutto quello che parla con
l'hardware Kirin vive in `/vendor` ed è sostituito o neutralizzato dalle patch.

## Avvio

```
ABL Xiaomi ─► boot.img (header v2)
               ├─ kernel LineageOS 4.14 + patch OpenHarmony (src/kernel/patches)
               ├─ dtb sdmmagpie + dtbo di sweet
               └─ ramdisk HarmonyOS dall'OTA + /init = hmos-preinit
hmos-preinit (src/preinit)
  1. legge i metadati LP della partizione super e crea un dm-linear per ogni partizione logica
  2. scrive /etc/fstab.required (system, vendor, sys_prod, chip_prod, cust, patch → dm-N, erofs)
  3. monta cache e avvia un logger: kmsg, istantanee di hilog/processi/servizi, screenshot
  4. exec /bin/init_early (init originale di HarmonyOS)
init HarmonyOS
  ├─ /vendor/etc/fstab.sweet: data f2fs, cache come /log, dsp
  └─ /vendor/etc/init/hmos2sweet.cfg: comandi e servizi delle patch scelte
```

Riga di comando del kernel (`lib/builder.py`): `hardware=sweet` (sceglie `fstab.sweet`), `hmos.permissive=1`
(SELinux permissive anche se init chiede enforcing), `hmos.noreboot=1` (un servizio critico che crasha non riavvia
il telefono), `firmware_class.path=/vendor/firmware`, `service_locator.enable=1`.

## Kernel (src/kernel/patches)

| Patch | Perché |
|---|---|
| 0001 userspace bring-up | driver `/dev/access_token_id`, ioctl binder `BINDER_GET_SENDER_INFO`/`ACCESS_TOKEN`, opzioni `hmos.*` |
| 0002 binderfs off, sysrq/noreboot, DRM | init di HarmonyOS crea i nodi binder da uevent |
| 0003 DRM auth per i HAL | composer, allocatore e Mesa condividono `/dev/dri/card0` senza essere DRM master |
| 0004/0005 hmdfs/sharefs emulati | storage_daemon monta hmdfs/sharefs: emulati con tmpfs + bind |
| 0006/0007 fs-verity stub | installd attiva la firma del codice: accettata su un kernel senza fs-verity |
| 0008 percorsi firmware | firmware di modem/ADSP da `/vendor/firmware_mnt/image` e `/vendor/dsp` |
| 0009 binder one-way sender pid | OpenHarmony usa il pid del mittente anche per le transazioni asincrone |
| 0010 log icnss | messaggi di debug del WiFi nel kmsg (bring-up) |
| 0011 BDF WLAN | il kernel invia bdwlan al firmware WLAN (su Android lo fa cnss-daemon) |
| 0012 reboot panic | `hmos.noreboot=1` rifiuta anche i riavvii `panic:<motivo>` |
| 0013 SSR senza panic | un riavvio lento di ADSP/modem non manda più in panic il kernel |

## Display e GPU

- **Composer** (`src/display/composer`, VDI OpenHarmony): DRM/KMS atomico sul driver SDE di sweet.
  - Usa solo il connettore DSI. Il writeback "Virtual" non va considerato, altrimenti lo schermo resta nero.
  - Gestisce piani hardware, eventi vblank (con vsync software di riserva) e DPMS + backlight sysfs.
  - Il pannello ha un solo modo a 120 Hz; il composer espone anche un modo virtuale a 60 Hz per il gestore
    del refresh (HGM).
- **Allocatore** (`src/display/buffer`): buffer dma-buf tramite dumb buffer DRM, import YUV.
- **Mesa 26** (`src/mesa`): freedreno su kgsl, piattaforma EGL OHOS (NativeWindow/NativeBuffer, import NV12/NV21).
  Sostituisce `libEGL_impl.so`/`libGLESv*_impl.so` in `/vendor/lib64/chipsetsdk`.
- dpi/cutout e politica HGM sono riscritti dai file dell'OTA e montati con bind sopra `/sys_prod` al boot.

## TEE assente

sweet non ha iTrustee. Due librerie "CA" Huawei aspetterebbero per sempre il TEE:

- `libuserauth_daemon.z.so` → stub: nessuna credenziale, quindi lock screen senza PIN;
- `libhuks_ca_hdi.z.so` → core HUKS di OpenHarmony su OpenSSL, con chiave radice software.

## Coprocessori Qualcomm

Su Android ci pensano i demoni vendor. Qui ci sono le versioni libere di linux-msm, patchate per il kernel downstream:

- `qrtr-ns`: name service QRTR, che sul 4.14 non è nel kernel;
- `rmtfs`: memoria condivisa via UIO;
- `tqftpserv`: file letti dalla partizione firmware;
- `pd-mapper`: legge i `.jsn`.

A questi si aggiunge `sweet-rproc`, che:

1. monta la partizione firmware (vfat, che l'fstab di HarmonyOS non supporta);
2. avvia `pd-mapper` e `tqftpserv`;
3. accende l'ADSP se c'è `/vendor/etc/sweet/feature_audio`;
4. accende il modem e chiede `wlan0` se c'è `feature_wifi`;
5. apre i nodi ALSA all'host audio.

## Audio

`src/audio/sweet_audio_vdi.cpp` implementa l'interfaccia VDI che l'host audio di HarmonyOS carica da
`/vendor/lib64/libaudio_primary_impl.z.so`. È basato su tinyalsa:

- PCM 0 (deep buffer) e 13 (low latency) in riproduzione, PCM 0 in cattura;
- percorsi del mixer letti dai `mixer_paths_*.xml` originali di sweet: `speaker`, `headphones`, `handset`,
  `handset-mic`;
- senza scheda audio i frame vengono consumati in tempo reale, così il server audio non si blocca mai.

## Setup wizard

Il wizard (`HwStartupGuide`) richiede WiFi. La patch 50:

- lo toglie da `system.img` e dalla lista di preinstallazione;
- fa partire `sweet-oobedone`, che scrive `device_provisioned`, `user_setup_complete` e `basic_statement_agreed`
  nel database settingsdata.

Senza queste chiavi SceneBoard cercherebbe di avviare il wizard a ogni boot.

## Riavvii

Su un port un driver mancante basta per far crashare un servizio, e HarmonyOS reagisce riavviando:

- AMS riavvia il telefono se SceneBoard crasha 4 volte in 4 minuti (`supportSCBCrashReboot`);
- init, quando un servizio "critical" (render_service, foundation, samgr, ...) crasha troppe volte, esegue il
  job `reboot` (ferma tutti i servizi, smonta /data) e poi manda in panic il kernel.

La patch 15 spegne il primo e toglie il flag critical: nei cfg di vendor direttamente, per quelli di system
dichiarando di nuovo il servizio in `/vendor/etc/init/hmos2sweet_nocritical.cfg` (init, build musl, aggiorna
un servizio già definito). Il kernel (0013) non va più in panic se un coprocessore ci mette più di 20 s a
ripartire.

## Sensori

I sensori di sm6150 sono nello Snapdragon Sensor Core, sull'ADSP. Due pezzi:

- `hexagonrpcd` (patch 34) serve al dominio sensori dell'ADSP i file di configurazione e il registro;
- `libhdi_sensor_impl.z.so` (patch 39, `src/sensors`) è il VDI che l'host sensori di HarmonyOS carica. Parla
  con il servizio QMI "SNS client" (400) su QRTR come l'HAL Android: cerca il SUID di `accel`, `gyro`, `mag`,
  `ambient_light`, `gravity`, `rotv`, `game_rv`, invia le richieste di configurazione in protobuf e
  inoltra gli eventi. Se l'SSC non ha `gravity` la calcola dall'accelerometro (serve alla rotazione).

## Termica, USB, demoni Kirin

- Patch 36: l'HDI termico legge le thermal zone reali (CPU, GPU, batteria, retro, connettore USB) e il
  servizio termico usa una politica per sweet. La limitazione di CPU/GPU resta al kernel.
- Patch 38: `/system/etc/init.usb.cfg` importa `/vendor/etc/init.${ohos.boot.hardware}.usb.cfg`; la patch
  scrive `init.sweet.usb.cfg` dal file Kirin dell'OTA con il controller `a600000.dwc3`.
- Patch 37: i demoni Huawei che parlano solo con hardware Kirin (THP, sensorhub, Balong, NPU, TEE, ...) non
  vengono avviati.

## Mount nel job pre-init

init crea le sandbox dei servizi (`mksandbox system`, `mksandbox chipset` nel job `init`) con bind `rec` +
`private`: un mount fatto dopo non è visibile ai servizi in sandbox (foundation/DMS, render_service, host HDF
come Bluetooth). Per questo tutti i mount delle patch (partizioni modem, bluetooth e persist, file di
configurazione sostituiti in /sys_prod e /system/etc) stanno nel job `pre-init`, prima delle sandbox.

## Telefonia, GPS, infrarossi (iter31)

- **RIL** (`src/ril`, patch `42-ril`): sostituisce `libril_msgtransfer.z.so` (il RIL Balong di Huawei)
  con una libreria che implementa `RilInitOps` di `telephony_ril_adapter` (OpenHarmony 5.1, stesse
  tabelle di funzioni del `libhril.z.so` Huawei) e parla con i servizi QMI del modem via QRTR:
  DMS (radio, IMEI, baseband), UIM (stato SIM, PIN/PUK, lettura/scrittura file, IMSI, ICCID, APDU),
  NAS (registrazione, segnale, operatore, selezione rete, tipo di rete, ora di rete), VOICE (chiamate
  CS), WMS (SMS 3GPP) e WDS/WDA (dati). Un `ServiceWatcher` segue il name service QRTR e
  ricollega i client quando il modem riparte.
- **Dati mobili**: `sweet-rproc` configura `rmnet_ipa0` (formato QMAP in/out) e crea `rmnet_data0..3`
  (mux id 1..4) via rtnetlink; il RIL imposta il formato dati sul modem (WDA, endpoint IPA
  "embedded"), lega un client WDS per chiamata dati al mux e restituisce indirizzi/DNS al
  telephony stack, che configura l'interfaccia.
- **Audio in chiamata**: lo scene `AUDIO_IN_CALL` sul render primario avvia il front end
  `VoiceMMode1` (PCM hostless) con i mixer path stock `voicemmode1-call <dispositivo>`.
- **GPS** (`src/gnss`, patch `44-gnss`): `vendorGnssAdapter.so` per il servizio GNSS HDI di
  OpenHarmony, su QMI LOC (posizioni, satelliti, NMEA).
- **Infrarossi** (`src/ir`, patch `43-consumer-ir`): `libconsumerir.so` caricata dal servizio IR di
  Huawei, trasmette tramite `/dev/lirc0`.
- **Vibrazione**: patch kernel 0016, l'aw8624 compare anche come `/sys/class/leds/vibrator`.
