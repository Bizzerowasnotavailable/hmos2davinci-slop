# Problemi noti e log

## Leggere i log

Ogni avvio lascia nella partizione `cache` (`/log/hmos` su HarmonyOS):

| File | Contenuto |
|---|---|
| `kmsg-N.log` | log del kernel |
| `boot-N/hilog-stream-*.txt` | hilog |
| `snapN-*.txt` | processi, servizi, mount, parametri, stato GPU/display |
| `screen-*.jpeg` | screenshot |

Per scaricarli: recovery (Power + Volume su), poi `get_logs.bat` / `get_logs.sh`.

Righe utili nel kmsg:

- `sweet-rproc:`: partizione firmware, ADSP, modem, `wlan0`, scheda audio;
- `sweet-oobedone:`: chiavi del setup scritte nel database delle impostazioni;
- `sweet-sensors:`: HAL sensori (servizio SSC trovato, SUID di ogni sensore, errori).

Tag utili in hilog:

- `SWEET_AUDIO`: HAL audio;
- `composer_host`: display;
- `C04201/foundation/DMS`: schermi visti dal window manager.

## Problemi noti

| Sintomo | Stato |
|---|---|
| ADSP che si riavvia ogni ~40 s (`sensor_process ... USER-PD DOG`) | serve la patch 34 (hexagonrpcd); se continua, cerca `hexagonrpcd` e `adsprpc` nel kmsg |
| `wlan: /dev/wlan ON -> -22`, nessun `wlan0` | cerca `sweet: board id` / `BDF download` (icnss) nel kmsg: il kernel deve inviare bdwlan al firmware |
| Bluetooth che non si accende | righe `sweet-bt:` nel kmsg: versione del chip, file crbtfw/crnv, risposta all'HCI reset |
| Riavvii spontanei | `get_logs` subito dopo: `pstore/` e il `kmsg` dell'avvio precedente mostrano la causa; cerca `crashed`, `critical`, `subsys-restart`, `Kernel panic`. La patch 15 toglie i riavvii per servizi che crashano, la patch kernel 0013 quelli per un ADSP/modem lento |
| Sensori assenti nelle app | righe `sweet-sensors:` nel kmsg: se resta su "waiting for the SSC", il dominio sensori dell'ADSP non è partito (vedi `hexagonrpcd`) |
| `tqftpserv: read/write <file> -> errore` nel kmsg | file che il modem chiede al server TFTP: se manca `wlanmdsp.mbn` o una cartella readwrite il WiFi non parte |
| hdc non vede il telefono | attiva opzioni sviluppatore e debug USB; nel kmsg cerca `a600000.dwc3` / `configfs` |
| Setup bloccato sulla schermata WiFi | attiva "Remove the setup wizard" (`--no-setup-wizard`) |
| Fotocamera | non portata: su sweet richiede lo stack Qualcomm CamX (librerie Android) o un driver ISP scritto da zero |
| Impronta | non portata: il sensore è gestito da una trusted app nel TEE Qualcomm (QSEE) |
| Telefonia, GPS | non portati: serve un RIL/GNSS HarmonyOS che parli QMI con il modem |
| Prossimità | il sensore di sweet è a ultrasuoni (gestito dal DSP audio), non incluso |
| Video HEVC oltre 1920 px | limite nel servizio media, la patch 40 non basta |

## Schermo nero

- **Nero dall'inizio**: nel kmsg cerca `can not pick a crtc` / `skip connector` (connettori DRM), poi controlla
  le righe `composer_host` in hilog.
- **Nero dopo la bootanimation**: se SceneBoard si riavvia in loop con
  `GetDefaultDisplaySync: Get display info failed`, il window manager non ha ricevuto lo schermo. Controlla che il
  composer abbia creato un solo display con id 0.

## Tornare ad Android

Dalla recovery flasha una ROM per sweet. La ROM ricrea le partizioni logiche di Android nel `super`.
