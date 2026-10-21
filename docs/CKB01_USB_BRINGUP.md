# OPPO CKB01 / SoftBank Air 5 USB bring-up

This image is an initial CKB01 board port. Compilation and FIT validation do
not establish that the physical ports or SDX55 have passed hardware tests.

## Boot and network defaults

- Keep the working OEM U-Boot. Write the complete `air5-ckb01-usb.img` to the
  **whole external USB drive**, then insert it while the Air 5 is powered off
  and power on. No interactive U-Boot command is part of this procedure.
  The image supplies an MBR partition table and a bootable primary partition 1
  containing FAT16 and `/uimage-initramfs.itb`. Check `sha256sums` after download.
- Boot and rootfs are separate: partition 1 (`AIR5BOOT`, FAT16) contains the
  FIT; partition 2 (`AIR5ROOT`, ext4) contains the writable OpenWrt rootfs.
  Settings and installed packages persist on partition 2. The FIT also carries
  a RAM recovery root for a missing/unusable persistent root.
- Physical LAN1 is intended as `wan` (DHCP client, NAT). Physical LAN2 is
  intended as `lan`, management address **192.168.5.1/24**, DHCP range
  **192.168.5.100–249**. SSH and LuCI use normal OpenWrt first-boot defaults.
- Hardware-confirmed mapping: switch port1/PHY8 = physical LAN1 (WAN);
  switch port2/PHY9 = physical LAN2 (management LAN).
- The ath11k branch provisions `Air5-2G` / `Air5-5G` after validating the
  unit's ART (WPA2 AES key `Air5-OpenWrt`, country CN, HE20/HE80).
  NSS Wi-Fi acceleration and automatic cellular sessions remain disabled.
  See [wireless implementation and evidence](CKB01_WIFI_PORTING.md).

### Complete IMG download and writing

After a successful build, download `ckb01-usb-image-<builder SHA>` from Actions
and unzip it. The file to write is **`air5-ckb01-usb.img`**, not the artifact ZIP
or the standalone ITB. A complete persistent disk image is 1281 MiB: a 1 MiB
MBR/alignment area, a 256 MiB FAT16 boot partition and a 1024 MiB ext4 root
partition. On first boot, partition 2 and its filesystem expand to use the
remaining drive capacity. A warning-marked RAM-only image is 257 MiB and has
no partition 2; consult `usb-image-report.json` rather than assuming persistence.

On Linux, identify the USB drive with `lsblk`, unmount its mounted partitions,
then write the image (this erases the target drive's previous layout):

```sh
sha256sum -c sha256sums
# Replace /dev/sdX with the USB whole disk, not /dev/sdX1.
sudo wipefs --all /dev/sdX
sudo dd if=air5-ckb01-usb.img of=/dev/sdX bs=4M status=progress conv=fsync
sync
```

A raw disk image writer can also write this IMG in its disk-image mode.
Do not format the drive again afterward. Eject it, insert it into the powered-off
Air 5, and power on. The intended path is the existing OEM `bootipq_usb`
automatic loader. The MBR layout still needs physical boot validation.

### Early boot and persistent-root recovery

The PID-1 `/init` mounts proc/sysfs, then loads `/etc/modules-boot.d/` using
OpenWrt's kmodloader before looking for the USB disk. The module-loading call
has a 20-second timeout. It then waits up to 30 seconds using integer `sleep 1`
for a unique partition 2 labeled `AIR5ROOT`; it does not assume the disk is
always `sda`. It creates block nodes from sysfs without depending on hotplug.
The explicit `blkid` package and USB boot modules are included in the firmware;
UAS storage is also loaded early for USB drives using that transport. Repairs
of an existing build without blkid can use its existing `/sbin/block info`
through the shared label helper; no replacement system libraries are required.

If the partition mounts as ext4 and contains OpenWrt init plus modules for the
running kernel, `/init` unmounts proc/sysfs and switches to that writable root.
The normal startup service mounts the same disk's `AIR5BOOT` read-only at
`/boot`. The initramfs script chooses the root partition; the DT no longer
hardcodes `root=/dev/sda2` or an indefinite kernel `rootwait`.

Missing/ambiguous labels, mount errors or an incompatible rootfs produce a
`ckb01-init:` message and select RAM recovery. Proc/sysfs are detached **before**
the RAM copy, and `/proc`, `/sys`, `/new_root` are explicitly excluded from
copy traversal. RAM recovery does not preserve configuration across reboot.

After boot, inspect the actual mounts:

```sh
cat /proc/mounts
cat /tmp/ckb01-usb-root
df -h / /boot
```

Persistent mode has an ext4 `/` and a read-only vfat `/boot`; RAM mode has a
tmpfs `/` and no managed `/boot` mount. Always deploy the FIT and rootfs from
the same build. Replacing only the FIT can leave incompatible modules on the
existing root partition. Writing a complete IMG replaces existing settings,
so back up the old rootfs before upgrading an already configured drive.

### Persistent-root ownership and wireless startup

The rootfs tarball records root:root ownership. CI must extract it and run
`mkfs.ext4 -d` inside the **same fakeroot session**; extracting as the ordinary
runner user silently stamps uid/gid 1001 onto image files. In particular,
ubusd rejects `/usr/share/acl.d/*.json` unless owned by root:root, and hostapd /
wpa_supplicant then cannot publish their ubus objects. Image inspection reads
the actual ext4 wpad ACL inode through debugfs; failure retains the IMG/GZ and
reports a warning instead of discarding the image.

`S09ckb01-caldata` re-reads and validates this machine's ART before S10boot
loads ath11k. A calibration file persists on ext4, but its `/tmp` status does
not persist; firmware hotplug alone cannot recreate that status when the file
already exists. The service restores the status on every boot without writing
ART. `S14ckb01-heartbeat` separately supervises a foreground uhttpd on TCP19888;
an exact SDX55-to-IPQ input rule allows its traffic independently of LAN/WAN.
The default configuration also keeps `169.254.10.1/32` in netifd's loopback
address list. An early `ip addr add` alone is insufficient: netifd removes
unconfigured addresses when it initializes loopback, even while uhttpd is
still listening. Preserve the normal `127.0.0.1/8` address alongside it.

An AP reaching `AP-ENABLED`, a listener accepting local HTTP, or MHI interfaces
being enumerated are separate observations. None proves the SDX55 transport
has exchanged QMI/RPC messages or that the module's restart monitor is satisfied.

The 2026-10-19 hardware log showed `** Invalid partition 1 **` only when the
previous whole-device FAT16 USB was inserted, followed by the OEM
`SBAir5, CKB01_11.B.003_291_202304012310` login. That boot did not run the new
OpenWrt system. The former image had no MBR partition entries. The U-Boot
2016 partition code emits this exact error when partition lookup fails;
the new image provides an explicit partition 1 rather than relying on whole-disk
FAT handling inferred from the SDX55 virtual disk. The FIT contents are unchanged.
Successful new-kernel boot should identify Linux 6.18.55 / OpenWrt, rather than
the OEM CLI. LTE attachment messages in the supplied log came from OEM firmware.

### Optional manual recovery

This is only for devices where the U-Boot console is accessible; it is not
required by the intended automatic startup. Enumerate `usb storage` and inspect `fatls` first.
For example, **only if the external drive is device 0, partition 1**:

```text
usb reset
fatls usb 0:1
fatload usb 0:1 0x44000000 uimage-initramfs.itb
bootm 0x44000000#config@1
```

Use the actual USB device number; the supplied IMG always has partition 1.
`config@hk09` references the same kernel
and DTB as the default `config@1`. Kernel load/entry is `0x41000000`; the
packager rejects a kernel footprint that reaches the FIT buffer at `0x44000000`.

## Board evidence and limits

- Original FDT: HK09, board-id 8, 512 MiB RAM, PCIe at `0x20000000`,
  PERST GPIO58, MDIO GPIO68/69 and PHY addresses 8/9.
- Local OEM engineering notes identify QCA807x and BMCR soft resets at PHY8/9.
  The new DTS uses the QCA807x package in PSGMII mode. The mainline driver
  identifies the actual QCA8072/QCA8075 PHY ID. Unconfirmed external PHY reset
  GPIOs are left at the OEM bootloader's state.
- CKB01 U-Boot DTS supplies reset/WPS GPIO60/15, status LEDs GPIO42/43 and
  RJ45 LED enable GPIO17. These remain subject to hardware confirmation.
- SPI NOR uses SMEM partition parsing. Locate ART by `0:ART`/`ART` label,
  never by a fixed MTD number. The OEM partition table describes ART at
  `0x2a0000`, length `0x40000` (262144 bytes).
- The original Air 5 `read_caldata_to_fs.sh` establishes ART offset `0x1000`
  and length `0x20000`; the image reads and validates this slice at runtime.
  The original Air 5 BDF is packaged as variant `OPPO-CKB01`. Actual radio
  operation remains pending hardware validation.
- Valid bootloader MACs are preserved. Otherwise MACs derive from the unit's
  ART digest, then its SoC serial; without either identity they are temporary
  random locally administered addresses. `/tmp/ckb01-mac-source` records this.

## Collect evidence after boot

```sh
ckb01-diag
ckb01-art-backup /tmp/air5-art.bin
```

`ckb01-diag` prints the path of a `/tmp/ckb01-diag-*.tar.gz` containing logs,
network/PHY/PCI/MHI state, the running DTB, partition information and ART
size/hash. It does not include the ART bytes. The separate backup command
reads the labeled partition and checks the expected 256 KiB size.

Next hardware checks, in order:

1. Three cold USB boots and at least ten minutes uptime without watchdog
   resets; record the selected FIT configuration and RAM size.
2. PCIe link/endpoint PCI ID, `mhi_pci_generic` binding, MHI execution state
   and available WWAN/QMI/QRTR ports. Absence of a session is not a dialing test.
3. Confirm physical LAN1/LAN2 placement. Check each port at 1 Gbit/s full
   duplex, LAN DHCP/SSH/LuCI, WAN DHCP, DNS and LAN-to-WAN NAT, then reconnect.
4. Read ART twice and compare size/hash, inspect MAC source and retain the
   backup for subsequent Wi-Fi calibration work.

## Build and artifacts

The dedicated **Build CKB01 USB initramfs** workflow builds one board on
`ubuntu-26.04`, from `JuliusBairaktaris/openwrt-ppe-nss` commit
`a0d3cabc052f9c3c19a0abe2b2633195f703bccc`. It uses
`COMMON=common-bringup`, `DEVICE=oppo_ckb01`, `VARIANT=ckb01` with the existing
preparation script. It does not use the general release matrix or NSS feed.

CI checks the selected profile, required ath11k packages and disabled NSS Wi-Fi, tests the FIT
packager, compiles firmware and validates both payload hashes, embedded board
identity, memory layout, port-to-PHY bindings and required initramfs contents.
The supplied compiled CPIO must occur inside the decompressed kernel bytes.
The input is the actual Linux `usr/initramfs_inc_data` file, which is embedded
by `usr/initramfs_data.S`. Its name does not acquire a compression suffix.
CI records input paths/sizes/hashes, and preserves the raw FIT and incbin file
as an explicitly unvalidated artifact if post-build verification fails.

After success, download `ckb01-usb-image-<builder SHA>` from the Actions
run. It contains `air5-ckb01-usb.img`, both FIT names, DTB/DTS,
`fit-report.json`, `usb-image-report.json`, the initramfs file list,
configuration, manifests, feed revisions and checksums. Artifacts
and build logs are retained for 30 days. Until hardware testing, the image is
explicitly **pending hardware validation**.

After FIT validation, CI generates the disk image without root using `sfdisk`,
`mkfs.fat` and `mcopy`. It verifies the MBR partition number, type, boot flag,
start/length, FAT16 sector/cluster sizes, FAT hidden-sector count and volume
length. It checks an extracted partition using `fsck.fat -n` and reads the FIT
back from the filesystem to require byte-for-byte equality with the validated
source. Persistent builds also populate partition 2 from the compiled rootfs
tarball and inspect ext4 with `e2fsck -f -n`. Verification errors remain warnings;
available raw FIT, IMG and logs are uploaded and marked accordingly.

On `ckb01-ath11k-bringup`, CI additionally checks BDF reproducibility, the
wireless helpers, and the actual initramfs/DTB using `ckb01-fit.py --wireless`.
The historical `ckb01-usb-bringup` commits contain the wired-only image.

## Verification failure investigation (2026-10-16)

Runs `38880494854` (wired) and `38884886511` (ath11k) both completed compilation
and passed the check for exactly one CKB01 initramfs FIT. They then failed
before the Python verifier because the workflow searched for the nonexistent
`usr/initramfs_data.cpio.zst` filename.

Linux 6.18's [usr/Makefile](https://github.com/torvalds/linux/blob/v6.18/usr/Makefile)
generates `usr/initramfs_data.cpio` and compresses it into
`usr/initramfs_inc_data`; [initramfs_data.S](https://github.com/torvalds/linux/blob/v6.18/usr/initramfs_data.S)
embeds that exact, suffix-free output. The corrected workflow selects
`*/linux-*/usr/initramfs_inc_data` and still requires its exact bytes to occur
in the FIT's decompressed Image before inspecting the CPIO contents.

The user-specified [upstream release](https://github.com/JuliusBairaktaris/Qualcommax_NSS_Builder/releases/tag/ppe-nss-20261013T200550Z-38460054734)
uses the same OpenWrt SHA. Its 77 uploaded assets contain sysupgrade images
and metadata, with no standalone initramfs/FIT/CPIO asset. The downloaded
TCL HH500V image is 21,227,801 bytes, SHA256
`9deea1f1bee4685b190920a0eaa7b8464dd6ecc2a750a118138a2522865fa107`.
Its tar contains a 5,996,108-byte kernel FIT and a 15,218,688-byte separate
rootfs. The gzip ARM64 kernel contains no Zstd frame. It is a sysupgrade
reference, not a CKB01 RAM-root image or a substitute calibration source.
The image was downloaded temporarily for this check, then removed after
inspection. No release mirror is stored in the project.

For an actual embedded-initramfs reference, the local temporary Haze FIT
contains an 11,725,191-byte Zstd frame at Image offset 14,884,808, decoding
to a 42,983,424-byte newc archive. Its presence confirms the byte-matching
method works with a real compressed ramdisk; its board contents differ from
CKB01 and do not satisfy CKB01's requirements.

Earlier tests exercised the Python packager but not the workflow's file
discovery. Regression tests now execute the actual workflow Bash step with
a Linux 6.18 build-directory layout and a Zstd-containing FIT. They reproduce
the old failure, pass with `initramfs_inc_data`, and reject an incbin file
whose bytes are absent from the FIT. Raw build outputs are retained on a
future verification failure so the compiled files can be inspected directly.
