#!/usr/bin/env python3
"""Pack/unpack Samsung (Android) boot images in the stock SM-J200H format.

Layout: page 0 = header, then kernel, ramdisk, second stage, DTB,
each aligned to page_size (2048).
"""
import argparse
import os
import struct
import sys

PAGE = 2048


def align(n, p=PAGE):
    return (n + p - 1) // p * p


def pack(kernel, ramdisk, dt, out, cmdline, kernel_addr=0x8000,
         ramdisk_addr=0x1000000, second_addr=0xf00000, tags_addr=0x100,
         total_size=16 * 1024 * 1024):
    k = open(kernel, 'rb').read()
    r = open(ramdisk, 'rb').read()
    d = open(dt, 'rb').read()

    header = bytearray(PAGE)
    header[0:8] = b'ANDROID!'
    struct.pack_into('<I', header, 8, len(k))
    struct.pack_into('<I', header, 12, kernel_addr)
    struct.pack_into('<I', header, 16, len(r))
    struct.pack_into('<I', header, 20, ramdisk_addr)
    struct.pack_into('<I', header, 24, 0)             # second_size
    struct.pack_into('<I', header, 28, second_addr)
    struct.pack_into('<I', header, 32, tags_addr)
    struct.pack_into('<I', header, 36, PAGE)
    struct.pack_into('<I', header, 40, len(d))
    struct.pack_into('<I', header, 44, 0)             # unused
    # name[16] at 48..63 stays zero
    cmd = cmdline.encode()[:511]
    header[64:64 + len(cmd)] = cmd
    # id[8] at 576..583 stays zero (no signature)
    # extra_cmdline[1024] at 608..1631 stays zero

    img = bytearray(header)
    img += k + b'\0' * (align(len(k)) - len(k))
    img += r + b'\0' * (align(len(r)) - len(r))
    img += d + b'\0' * (align(len(d)) - len(d))
    if total_size and len(img) < total_size:
        img += b'\0' * (total_size - len(img))

    with open(out, 'wb') as f:
        f.write(img)
    print(f'{out}: kernel={len(k)} ramdisk={len(r)} dt={len(d)} '
          f'total={len(img)}')


def unpack(path, outdir):
    data = open(path, 'rb').read()
    assert data[:8] == b'ANDROID!', 'bad magic'
    ks, ka, rs, ra, ss, sa, ta, ps = struct.unpack('<8I', data[8:40])
    ds = struct.unpack('<I', data[40:44])[0]
    cmdline = data[64:576].split(b'\0')[0].decode()
    print(f'page={ps} kernel={ks}@{hex(ka)} ramdisk={rs}@{hex(ra)} '
          f'second={ss}@{hex(sa)} tags={hex(ta)} dt={ds}')
    print(f'cmdline={cmdline!r}')

    os.makedirs(outdir, exist_ok=True)
    off = align(PAGE, ps)
    for name, size in (('kernel', ks), ('ramdisk', rs),
                       ('second', ss), ('dt', ds)):
        if size:
            with open(os.path.join(outdir, name), 'wb') as f:
                f.write(data[off:off + size])
        off += align(size, ps)
    print(f'extracted to {outdir}')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('pack')
    p.add_argument('--kernel', required=True)
    p.add_argument('--ramdisk', required=True)
    p.add_argument('--dt', required=True)
    p.add_argument('--cmdline', required=True)
    p.add_argument('--out', required=True)

    u = sub.add_parser('unpack')
    u.add_argument('image')
    u.add_argument('outdir')

    a = ap.parse_args()
    if a.cmd == 'pack':
        pack(a.kernel, a.ramdisk, a.dt, a.out, a.cmdline)
    else:
        unpack(a.image, a.outdir)


if __name__ == '__main__':
    main()
