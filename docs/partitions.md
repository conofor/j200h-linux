# SM-J200H partition map (PIT, 31 entries)

Key partitions (by-name → mmcblk0pN):
- SBOOT p1, SBOOT2 p2 — bootloaders
- KERNEL p20 — Android boot.img goes here (kernel+ramdisk+dtb)
- RECOVERY p21 — TWRP
- CACHE p24 — used for debug logs (raw dd at offset ~199MB)
- SYSTEM p25 — Android /system (left intact)
- HIDDEN p26
- userdata p27 — Linux rootfs at /linuxroot

Flash via heimdall (download mode):
  heimdall flash --KERNEL boot.img --no-reboot
  heimdall flash --RECOVERY twrp.img --no-reboot
  heimdall download-pit --output device.pit
