# OPPO CKB01 / SoftBank Air 5 USB bring-up

This image is an initial CKB01 board port. Compilation and FIT validation do
not establish that the physical ports or SDX55 have passed hardware tests.

## Boot and network defaults

- Keep the working OEM U-Boot. Copy `uimage-initramfs.itb` into the root of the
  external USB drive's already verified FAT boot filesystem. The long OpenWrt
  image filename is an identical copy; check `sha256sums` after download.
- The FIT contains its own root filesystem. Configuration lives in RAM and
  resets to the image defaults after reboot. There is no flash installation or
  persistent USB-root procedure in this version.
- Physical LAN1 is intended as `wan` (DHCP client, NAT). Physical LAN2 is
  intended as `lan`, management address **192.168.5.1/24**, DHCP range
  **192.168.5.100–249**. SSH and LuCI use normal OpenWrt first-boot defaults.
- Port placement is an initial hypothesis: switch port1/PHY8 = LAN2;
  switch port2/PHY9 = LAN1. Confirm this with cable insertion/carrier tests.
  If management does not appear on LAN2, inspect both ports from serial.
- Wi-Fi, NSS Wi-Fi acceleration and automatic cellular sessions are disabled.
  PCIe/MHI and USB storage modules are included for investigation.

For manual recovery boot, enumerate `usb storage` and inspect `fatls` first.
For example, **only if the external drive is device 0, partition 1**:

```text
usb reset
fatls usb 0:1
fatload usb 0:1 0x44000000 uimage-initramfs.itb
bootm 0x44000000#config@1
```

Use the actual device/partition from the working setup; it may be `0:0` on a
filesystem without a partition table. `config@hk09` references the same kernel
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
- No Haze/Deco BDF, caldata offsets or modem power/reset GPIOs are reused.
  Wi-Fi stays disabled until Air 5 calibration layout is established.
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

CI checks the selected profile and disabled wireless packages, tests the FIT
packager, compiles firmware and validates both payload hashes, embedded board
identity, memory layout, port-to-PHY bindings and required initramfs contents.
The supplied compiled CPIO must occur inside the decompressed kernel bytes.

After success, download `ckb01-usb-initramfs-<builder SHA>` from the Actions
run. It contains both image names, DTB/DTS, `fit-report.json`, the initramfs
file list, configuration, manifests, feed revisions and checksums. Artifacts
and build logs are retained for 30 days. Until hardware testing, the image is
explicitly **pending hardware validation**.
