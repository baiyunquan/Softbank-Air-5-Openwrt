#!/bin/sh
# Rebuild the ARMv7 payload on an LLVM host, not with the IPQ AArch64 toolchain.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
clang --target=arm-linux-gnueabihf -march=armv7-a -mfpu=neon -mfloat-abi=hard \
 -fuse-ld=lld -shared -nostdlib -fPIC -O2 -fno-builtin -fno-stack-protector \
 -Wl,-soname,air5-adb-tcp.so "$here/adb-tcp-property.c" -o "$here/adb-tcp-property.so"
sha256sum "$here/adb-tcp-property.so"
