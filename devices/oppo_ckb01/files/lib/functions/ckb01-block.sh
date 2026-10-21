#!/bin/sh
# Also support already-built CKB01 initramfs images without util-linux blkid.
ckb01_block_label() {
	if command -v blkid >/dev/null 2>&1; then
		blkid -p -s LABEL -o value "$1" 2>/dev/null
	elif [ -x /sbin/block ]; then
		/sbin/block info "$1" 2>/dev/null | sed -n 's/.* LABEL="\([^"]*\)".*/\1/p'
	else
		return 1
	fi
}
