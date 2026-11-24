# Linux на Samsung Galaxy J2 (SM-J200H)

Замена Android на **Alpine Linux** для Samsung Galaxy J2 2016 **SM-J200H**
(Spreadtrum/UNISOC SC7730, S-Boot 4.0, ядро 3.10.65).

Телефон грузится **сразу в Linux** — без Android, без chroot «поверх».
Работает: SSH по WiFi (автоподключение к домашней сети), root по ключу.
Headless-режим: экрана и звука нет (дисплей заморожен на сообщении ядра — это норма).

```
S-Boot → раздел KERNEL (boot.img: kernel + initramfs + DTB)
      → initramfs /init → mount userdata → switch_root
      → Alpine Linux (OpenRC) → wpa_supplicant → dhcpcd → sshd
```

## Что работает / что нет

| Работает | Не работает |
|---|---|
| Загрузка Linux вместо Android | Дисплей, тачскрин, звук |
| WiFi (BCM4343, nl80211/wpa_supplicant) | GSM/LTE, SMS, звонки |
| SSH-сервер, автоподключение к WiFi | Камера, BT, датчики |
| eMMC-хранилище (userdata ~5.7 ГБ) | Батарея/зарядка (нужен патч) |

## Железо и разметка

- SoC: Spreadtrum SC7730 (Cortex-A7 x4), ARMv7, 1 ГБ RAM
- eMMC 8 ГБ, разделы (PIT):
  - `KERNEL` = mmcblk0p20 — сюда шьётся boot.img (аналог "boot")
  - `RECOVERY` = mmcblk0p21 — TWRP
  - `SYSTEM` = mmcblk0p25, `CACHE` = mmcblk0p24
  - `userdata` = mmcblk0p27 — здесь живёт Alpine rootfs в `/linuxroot`
- Загрузчик S-Boot **не проверяет подпись** boot.img (проверено экспериментально:
  неподписанный образ с нуля в поле `id` грузится так же, как стоковый).

## Что в репозитории

- `scripts/mkboot.py` — упаковка/распаковка Samsung boot.img (формат: header +
  kernel + ramdisk + DTB, page=2048). Умеет `pack` и `unpack`.
- `initramfs/init` — initramfs-скрипт: монтирует proc/sys/dev, создаёт ноды,
  **питает hardware watchdog** (иначе S-Boot перезагружает телефон ~каждые 10 с),
  монтирует userdata (p27), bind-mount `/linuxroot` и делает `switch_root`.
- `scripts/build-initramfs.sh` — сборка cpio.gz initramfs.
- `rootfs-overlay/etc/local.d/` — скрипты, которые кладутся в Alpine
  `/etc/local.d/` (OpenRC `local` service):
  - `wifi.start` — wlan0 up + wpa_supplicant + dhcpcd
  - `00-devnodes.start` — статические /dev-ноды (urandom, tty, /run/sshd)
  - `05-sshd.start` — запуск sshd (OpenRC-сервис падает, бинарь работает)
  - `01-watchdog.start` — backup pet watchdog из userspace
- `docs/` — заметки по отладке и граблям.

## Установка (кратко)

1. **Бэкап**: в TWRP снять `boot`(KERNEL p20), `efs`, `param`, `persistent`,
   `prodnv`, `hidden`, `userdata`. PIT можно скачать через heimdall.
2. **Rootfs**: распаковать Alpine minirootfs (armv7) в `/data/linuxroot`
   на разделе userdata (p27). Настроить `/etc/inittab` (убрать getty),
   `/etc/wpa_supplicant/wpa_supplicant.conf`, `/etc/ssh/sshd_config`,
   положить local.d-скрипты, сгенерировать host keys (`ssh-keygen -A`),
   добавить SSH-ключ в `/root/.ssh/authorized_keys`.
3. **Initramfs**: собрать cpio.gz (см. `scripts/build-initramfs.sh`),
   обязательно включить **WiFi firmware** (`/system/etc/wifi/bcmdhd_sta.bin`,
   `nvram_net.txt` и `/lib/firmware/*`) — драйвер читает их через `filp_open`
   на ранней стадии, до монтирования rootfs.
4. **boot.img**: `mkboot.py pack --kernel <stock-zImage-or-custom> --ramdisk
   initramfs.cpio.gz --dt <stock.dtb> --cmdline "console=ttyS1,115200n8"`.
   DTB берётся из стокового boot.img (`mkboot.py unpack`).
5. **Прошивка**: через heimdall в download mode —
   `heimdall flash --KERNEL boot-linux.img` (или TWRP `dd` в mmcblk0p20).
6. Загрузка → ~2–3 мин → `ssh -i key root@<ip>`.

## Грабли (чтобы не наступать)

- **Watchdog**: S-Boot/KERNEL требует pet'а аппаратного watchdog. Без него —
  ребут каждые ~10 с. Лечится в initramfs (раньше всего) и в local.d.
- **/tmp в initramfs отсутствует** — логи в `/tmp/*.log` молча теряются.
  Пишите в существующие пути или создавайте каталог.
- **wpa_supplicant**: у alpine-сборки нет опций `-B` и `-f` — запускать
  `wpa_supplicant ... &` с редиректом вывода. Драйвер `-D nl80211`
  (cfg80211/wlfc есть в ядре); `-D wl` не поддерживается.
- **WiFi firmware**: класть в initramfs И в rootfs (`/system/etc/wifi/` +
  `/lib/firmware/`). Путь прошит в `CONFIG_BCMDHD_FW_PATH`.
- **/dev/urandom**: mdev может не создать → wpa_supplicant/sshd падают.
  Создавать вручную (00-devnodes.start).
- **sshd OpenRC service**: падает с "sshd failed to start" — запускать
  бинарь напрямую (05-sshd.start). `sshd -D -e -d` работает.
- **sysfs**: в Alpine `/sys/class/net` может отсутствовать на ранних
  этапах — использовать `ip link` (netlink) вместо проверки sysfs.
- **DHCP vs static**: dhcpcd выдаёт адрес из роутера (обычно .3),
  статический .250 добавляется до него — проверять оба.

## Источники и авторство

Написано с нуля для этого проекта. Используемые сторонние компоненты
(не входят в репозиторий, берутся из апстрима):

| Компонент | Источник | Лицензия |
|---|---|---|
| Alpine Linux minirootfs | alpinelinux.org | GPL-2.0 (BusyBox), BSD/MIT (остальное) |
| Linux kernel 3.10.65 (j23g/sprd) | Samsung GPL drop / TeamWin kernel trees | GPL-2.0 |
| busybox (armv7 static) | busybox.net | GPL-2.0 |
| wpa_supplicant, wpa_cli | w1.fi / Alpine | BSD-3-Clause |
| dhcpcd | dhcpcd.org / Alpine | BSD-2-Clause |
| OpenSSH | openssh.com / Alpine | BSD |
| TWRP recovery | twrp.me (j23g build) | GPL-3.0 |
| Heimdall | glassechidna.com.au | MIT |
| debootstrap/pmaports | postmarketOS | GPL-3.0/MIT |

Изменений в чужой код не вносилось — все скрипты в репозитории оригинальные.
