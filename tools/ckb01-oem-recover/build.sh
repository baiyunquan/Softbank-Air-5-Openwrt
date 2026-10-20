#!/usr/bin/env bash
set -euo pipefail
src=$(dirname -- "$0")/recover.c
out=${1:?output directory required}
mkdir -p "$out"
for target in aarch64-linux-gnu arm-linux-gnueabi; do
 clang --target="$target" -fuse-ld=lld -nostdlib -static -Os -fno-stack-protector \
   -fno-builtin -Wl,-e,_start -Wl,--build-id=none "$src" -o "$out/ckb01-oem-recover-$target"
done
sha256sum "$out"/ckb01-oem-recover-* > "$out/recovery-sha256sums"
