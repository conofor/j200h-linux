# Linux on Samsung Galaxy J2 (SM-J200H)

Replaces Android with **Alpine Linux** on the Samsung Galaxy J2 2016
**SM-J200H** (Spreadtrum/UNISOC SC7730, S-Boot 4.0, kernel 3.10.65).

The phone boots **directly into Linux** — no Android, no chroot "on top".
Working: SSH over WiFi (auto-connect to home network), root via key.
Headless mode: no display or audio (screen stays frozen on the kernel
message — this is normal).

```
S-Boot → KERNEL partition (boot.img: kernel + initramfs + DTB)
      → initramfs /init → mount userdata → switch_root
      → Alpine Linux (OpenRC) → wpa_supplicant → dhcpcd → sshd
```

## What works / what doesn't

| Works | Doesn't work |
|---|---|
| Linux instead of Android | Display, touchscreen, sound |
| WiFi (BCM4343, nl80211/wpa_supplicant) | GSM/LTE, SMS, calls |
| SSH server, WiFi auto-connect | Camera, BT, sensors |
| eMMC storage (userdata ~5.7 GB) | Battery/charging (needs a patch) |

## Hardware and partitions

- SoC: Spreadtrum SC7730 (Cortex-A7 x4), ARMv7, 1 GB RAM
- eMMC 8 GB, partitions (PIT):
  - `KERNEL` = mmcblk0p20 — boot.img goes here (Android "boot" equivalent)
  - `RECOVERY` = mmcblk0p21 — TWRP
  - `SYSTEM` = mmcblk0p25, `CACHE` = mmcblk0p24
  - `userdata` = mmcblk0p27 — Alpine rootfs lives here under `/linuxroot`
- S-Boot bootloader **does not verify** the boot.img signature (verified
  experimentally: an unsigned image with zeroed `id` field boots the same
  as the stock one).

## Repository contents

- `scripts/mkboot.py` — pack/unpack Samsung boot.img (format: header +
  kernel + ramdisk + DTB, page=2048). Supports `pack` and `unpack`.
- `initramfs/init` — initramfs script: mounts proc/sys/dev, creates device
  nodes, **pets the hardware watchdog** (otherwise S-Boot reboots the phone
  every ~10 s), mounts userdata (p27), bind-mounts `/linuxroot` and runs
  `switch_root`.
- `scripts/build-initramfs.sh` — builds the cpio.gz initramfs.
- `rootfs-overlay/etc/local.d/` — scripts placed into Alpine
  `/etc/local.d/` (OpenRC `local` service):
  - `wifi.start` — wlan0 up + wpa_supplicant + dhcpcd
  - `00-devnodes.start` — static /dev nodes (urandom, tty, /run/sshd)
  - `05-sshd.start` — starts sshd (OpenRC service fails, binary works)
  - `01-watchdog.start` — watchdog keep-alive backup from userspace
- `docs/` — debugging notes and gotchas.

## Installation (summary)

1. **Backup**: in TWRP, dump `boot` (KERNEL p20), `efs`, `param`,
   `persistent`, `prodnv`, `hidden`, `userdata`. PIT can be downloaded via
   heimdall.
2. **Rootfs**: unpack the Alpine minirootfs (armv7) into `/data/linuxroot`
   on the userdata partition (p27). Configure `/etc/inittab` (remove getty),
   `/etc/wpa_supplicant/wpa_supplicant.conf`, `/etc/ssh/sshd_config`, copy
   the local.d scripts, generate host keys (`ssh-keygen -A`), add your SSH
   key to `/root/.ssh/authorized_keys`.
3. **Initramfs**: build the cpio.gz (see `scripts/build-initramfs.sh`),
   make sure to include **WiFi firmware** (`/system/etc/wifi/bcmdhd_sta.bin`,
   `nvram_net.txt` and `/lib/firmware/*`) — the driver reads them via
   `filp_open` at an early stage, before rootfs is mounted.
4. **boot.img**: `mkboot.py pack --kernel <stock-zImage-or-custom> --ramdisk
   initramfs.cpio.gz --dt <stock.dtb> --cmdline "console=ttyS1,115200n8"`.
   The DTB comes from the stock boot.img (`mkboot.py unpack`).
5. **Flashing**: via heimdall in download mode —
   `heimdall flash --KERNEL boot-linux.img` (or `dd` to mmcblk0p20 in TWRP).
6. Boot → ~2–3 min → `ssh -i key root@<ip>`.

## Gotchas (so you don't step on them)

- **Watchdog**: S-Boot/KERNEL requires petting the hardware watchdog.
  Without it — reboot every ~10 s. Fixed in initramfs (as early as
  possible) and in local.d.
- **No /tmp in initramfs** — logs written to `/tmp/*.log` are silently
  lost. Write to existing paths or create the directory.
- **wpa_supplicant**: the Alpine build has no `-B` and `-f` options — run
  `wpa_supplicant ... &` with output redirection. Driver uses
  `-D nl80211` (cfg80211/wlfc are in the kernel); `-D wl` is not
  supported.
- **WiFi firmware**: put it both in initramfs AND in rootfs
  (`/system/etc/wifi/` + `/lib/firmware/`). The path is compiled into
  `CONFIG_BCMDHD_FW_PATH`.
- **/dev/urandom**: mdev may not create it → wpa_supplicant/sshd crash.
  Create it manually (00-devnodes.start).
- **sshd OpenRC service**: fails with "sshd failed to start" — run the
  binary directly (05-sshd.start). `sshd -D -e -d` works.
- **sysfs**: in Alpine `/sys/class/net` may be missing at early stages —
  use `ip link` (netlink) instead of checking sysfs.
- **DHCP vs static**: dhcpcd gets an address from the router (usually .3),
  a static .250 is added before it — check both.

## Sources and authorship

Written from scratch for this project. Third-party components used
(not included in the repo, taken from upstream):

| Component | Source | License |
|---|---|---|
| Alpine Linux minirootfs | alpinelinux.org | GPL-2.0 (BusyBox), BSD/MIT (rest) |
| Linux kernel 3.10.65 (j23g/sprd) | Samsung GPL drop / TeamWin kernel trees | GPL-2.0 |
| busybox (armv7 static) | busybox.net | GPL-2.0 |
| wpa_supplicant, wpa_cli | w1.fi / Alpine | BSD-3-Clause |
| dhcpcd | dhcpcd.org / Alpine | BSD-2-Clause |
| OpenSSH | openssh.com / Alpine | BSD |
| TWRP recovery | twrp.me (j23g build) | GPL-3.0 |
| Heimdall | glassechidna.com.au | MIT |
| debootstrap/pmaports | postmarketOS | GPL-3.0/MIT |

No changes were made to third-party code — all scripts in the repo are
original.
