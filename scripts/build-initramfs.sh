#!/bin/sh
# build-initramfs.sh — assemble the boot initramfs (stage3) and pack boot.img.
#
# Layout produced:
#   initramfs.cpio.gz  — cpio.gz with /init, busybox, WiFi firmware
#
# Usage:
#   ./build-initramfs.sh /path/to/workdir
# Expects in workdir:
#   busybox-arm        — static ARM busybox binary
#   firmware/          — bcmdhd_sta.bin, nvram_net.txt, ...
#
set -e
WD="$1"
[ -d "$WD" ] || { echo "usage: $0 workdir"; exit 1; }

RD=$(mktemp -d)
trap 'rm -rf "$RD"' EXIT

mkdir -p "$RD"/{bin,dev,proc,sys,tmp,newroot,newroot2,system/etc/wifi,lib/firmware}
cp "$WD/busybox-arm" "$RD/bin/busybox"
cp init/init "$RD/init" 2>/dev/null || cp "$(dirname "$0")/../initramfs/init" "$RD/init"
chmod +x "$RD/init"
cp "$WD"/firmware/* "$RD/system/etc/wifi/" 2>/dev/null || true
cp "$WD"/firmware/* "$RD/lib/firmware/" 2>/dev/null || true

cd "$RD"
find . | cpio -o -H newc 2>/dev/null | gzip -9 > "$WD/initramfs.cpio.gz"
echo "built $WD/initramfs.cpio.gz ($(stat -c%s "$WD/initramfs.cpio.gz") bytes)"
