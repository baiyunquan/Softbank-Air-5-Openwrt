# CKB01 PCIe EDL / EFS maintenance

This image is built for manual maintenance. Programmer authentication, EDL/FP
transition and actual NAND reads on CKB01 remain **pending hardware acceptance**.
No device was contacted during this build. USB PID 9008 is not a PCIe success criterion.

## Boot and access

Write the complete `air5-ckb01-usb.img` to a USB drive. Keep the boot FIT and
AIR5ROOT from the same build. The existing OEM boot filename remains
`uimage-initramfs.itb`. LAN2 and Wi-Fi provide management at `192.168.5.1`;
LAN1 remains wired WAN. APs remain Air5-2G/Air5-5G, key Air5-OpenWrt.
Normal USB-root expansion, per-unit ART calibration and heartbeat remain enabled.
Maintenance initializes IP_SW0 and PCIe DIAG, without cellular auto-dial.

## Manual commands

```sh
ckb01-edl status
ckb01-edl enter
ckb01-edl backup-efs --output /root/efs-backups
```

`enter` sends the OEM-compatible DIAG request once. Explicit alternative:
`ckb01-edl enter --method mhi` uses the mainline MHI EDL doorbell mechanism.
There is no automatic fallback between entry methods and no reset retry loop.
The kernel arm/attach/cancel ABI is described in the kernel patch. Attach loads
only the pinned RAM programmer via BHI and binds FP FIREHOSE channels 34/35.
A module already in EDL/FP waits for manual attachment; boot alone uploads nothing.

Backup never enters EDL implicitly. Its destination must be persistent storage;
when booted in RAM fallback, supply a mounted external storage directory.
Each run has a unique directory, programmer provenance, kernel and protocol logs,
MIBIB/geometry, and two reads. Incomplete reads retain `.partial` files. A short
read, timeout or NAK ends the pass without automatic sector resume. Only two
complete ACK-terminated reads with equal length/hash establish transport completion.

The CKB01 reference geometry is NAND 512 MiB, page 4096, eraseblock 262144;
`efs2` starts at 0x500000 and is 0xb00000 bytes (11 MiB). Actual storage information
and the MIBIB table must agree. This differs from the T99W175 partition layout.
The backup is programmer/ECC main data; OOB, bad-block semantics and restore
suitability require separate evidence. Unreported properties remain unknown.

After success or a failed EDL transition, retain logs and fully remove/reconnect
power to return the module to normal NAND boot. Do not repeatedly invoke reset.
An interrupted command may retain `/tmp/ckb01-edl-active` and locks intentionally;
inspect the cached kernel state before manual cleanup. No internal startup files
are changed by this maintenance package, and the reader exposes no NAND write command.

## Build and evidence

`Build CKB01 PCIe EDL maintenance` calls the pinned existing build with the
maintenance fragment. Toolchain/download/compiler caches are reused. Kernel changes
are compiled. Validation is advisory: failures warn and retain raw FIT, available
IMG and logs. Genuine compilation errors are reported separately. The package
preserves the signed ARM programmer byte-for-byte, including during AArch64 packaging.
See the installed `/usr/share/ckb01-edl/provenance.json` for hash and source.

Build success does not establish programmer authentication, EDL/FP or NAND-read
success. Those hardware items remain pending in the uploaded status reports.
