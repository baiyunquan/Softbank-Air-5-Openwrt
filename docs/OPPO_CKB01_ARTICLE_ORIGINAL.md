<!--
Source URL: https://memo205.hatenablog.jp/entry/2025/07/31/234645
Fetched: 2026-10-16
The page itself did not expose an MIT/Creative Commons licence in the fetched HTML.
-->

# OPPO CKB01

原文来源：https://memo205.hatenablog.jp/entry/2025/07/31/234645  
发布日期：2025-07-31

<div class="entry-content hatenablog-entry">

OpenWrtでサポートできそうなデ<a href="https://d.hatena.ne.jp/keyword/%A5%D0%A5%A4%A5%B9" class="keyword">バイス</a>が無いか、インターネットを徘徊していて見つけたもの。

中国語の情報が先行情報としていくらか出ているので、中古がかなり安いしとりあえず確保してみることにした。

弄っていくのでメモ。

### Switch, PHY

未確認

<table style="display:none">
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<thead>
<tr>
<th><em>zone</em></th>
<th colspan="2" style="text-align: center; border-left: 1px solid #ddd;">LAN</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong><em>port<br />
(CKB01)</em></strong></td>
<td>LAN1</td>
<td>LAN2</td>
</tr>
<tr>
<td><strong><em>port</em></strong></td>
<td>port2</td>
<td>port1</td>
</tr>
</tbody>
</table>

### <a href="https://d.hatena.ne.jp/keyword/MAC" class="keyword">MAC</a>

未確認

### Bootloader

- #### `help`

  ```
    IPQ807x# help           
    ?       - alias for 'help'
    aes_256 - AES 256 CBC/ECB encryption/decryption
    aq_load_fw- LOAD aq-fw-binary
    aq_phy_restart- Restart Aquantia phy
    base    - print or set address offset
    bdinfo  - print Board Info structure
    bootipq - bootipq from flash device
    bootipq_usb- bootipq from usb device
    bootm   - boot application image from memory
    bootp   - boot image via network using BOOTP/TFTP protocol
    bootz   - boot Linux zImage image from memory
    canary  - test stack canary
    chpart  - change active partition
    cmp     - memory compare
    cp      - memory copy
    crc32   - checksum calculation
    dcache  - enable or disable data cache
    dhcp    - boot image via network using DHCP/TFTP protocol
    dm      - Driver model low level access
    echo    - echo args to console
    env     - environment handling commands
    erase   - erase FLASH memory
    exectzt - execute TZT

    exit    - exit script
    ext4load- load binary file from a Ext4 filesystem
    ext4ls  - list files in a directory (default /)
    ext4size- determine a file's size
    false   - do nothing, unsuccessfully
    fatinfo - print information about filesystem
    fatload - load binary file from a dos filesystem
    fatls   - list files in a directory (default /)
    fatsize - determine a file's size
    fdt     - flattened device tree utility commands
    flash   - flash part_name 
            flash part_name load_addr file_size 

    flasherase- flerase part_name 

    flinfo  - print FLASH memory information
    fuseipq - fuse QFPROM registers from memory

    go      - start application at address 'addr'
    help    - print command description/usage
    i2c     - I2C sub-system
    icache  - enable or disable instruction cache
    imxtract- extract a part of a multi-image
    ipq_mdio- IPQ mdio utility commands
    is_sec_boot_enabled- check secure boot fuse is enabled or not

    itest   - return true/false on integer compare
    loop    - infinite loop on address range
    md      - memory display
    mii     - MII utility commands
    mm      - memory modify (auto-incrementing address)
    mmc     - MMC sub system
    mmcinfo - display MMC info
    mtdparts- define flash/nand partitions
    mtest   - simple RAM read/write test
    mw      - memory write (fill)
    nand    - NAND sub-system
    nboot   - boot from NAND device
    nm      - memory modify (constant address)
    pci     - list and access PCI Configuration Space
    ping    - send ICMP ECHO_REQUEST to network host
    printenv- print environment variables
    protect - enable or disable FLASH write protection
    reset   - Perform RESET of the CPU
    run     - run commands in an environment variable
    runmulticore- Enable and schedule secondary cores
    saveenv - save environment variables to persistent storage
    secure_authenticate- authenticate the signed image

    setenv  - set environment variables
    sf      - SPI flash sub-system
    showvar - print local hushshell variables
    sleep   - delay execution for some time
    smeminfo- print SMEM FLASH information
    source  - run script from memory
    test    - minimal test like /bin/sh
    tftpboot- boot image via network using TFTP protocol
    tftpput - TFTP put command, for uploading files to a server
    true    - do nothing, successfully
    uart    - UART sub-system
    ubi     - ubi commands
    usb     - USB sub-system
    usbboot - boot from USB device
    version - print monitor, compiler and linker version
  ```

- #### `version`

  ```
    IPQ807x# version

    U-Boot 2016.01 (Oct 26 2021 - 17:26:18 +0800)
    arm-openwrt-linux-muslgnueabi-gcc (OpenWrt GCC 5.2.0 fa2f68a+r49254) 5.2.0
    GNU ld (GNU Binutils) 2.24.0
  ```

- #### `bdinfo`

  ```
    IPQ807x# bdinfo
    arch_number = 0x08010008
    boot_params = 0x40000100
    DRAM bank   = 0x00000000
    -> start    = 0x40000000
    -> size     = 0x20000000
    eth0name    = eth0
    ethaddr     = 00:03:7f:ba:db:ad
    current eth = eth0
    ip_addr     = 192.168.10.10
    baudrate    = 115200 bps
    TLB addr    = 0x4A9D0000
    relocaddr   = 0x4A900000
    reloc off   = 0x00000000
    irq_sp      = 0x4A77FA90
    sp start    = 0x4A77FA80
  ```

- #### `smeminfo`

  ```
    IPQ807x# smeminfo
    flash_type:             0x6
    flash_index:            0x0
    flash_chip_select:      0x0
    flash_block_size:       0x10000
    flash_density:          0x1000000
    partition table offset  0x0
    No.: Name             Attributes            Start             Size
      0: 0:SBL1           0x0000ffff              0x0          0x40000
      1: 0:MIBIB          0x001040ff          0x40000          0x10000
      2: 0:QSEE           0x0000ffff          0x50000         0x160000
      3: 0:DEVCFG         0x0000ffff         0x1b0000          0x10000
      4: 0:RPM            0x0000ffff         0x1c0000          0x20000
      5: 0:CDT            0x0000ffff         0x1e0000          0x10000
      6: 0:APPSBLENV      0x0000ffff         0x1f0000          0x10000
      7: 0:APPSBL         0x0000ffff         0x200000          0xa0000
      8: 0:ART            0x0000ffff         0x2a0000          0x40000
      9: 0:OEM            0x0000ffff         0x2e0000          0x10000
     10: 0:CRASH          0x0000ffff         0x2f0000          0x20000
  ```

- #### `nand info`

  ```
    IPQ807x# nand info

    Device 1: 17x nand1, sector size 4 KiB
      Page size        256 b
      OOB size           0 b
      Erase size      4096 b
      subpagesize 1251414100 b
      options     0x65746172
      bbt options 0x       0
  ```

- #### `printenv`

  ```
    IPQ807x# printenv
    baudrate=115200
    bootargs=console=ttyMSM0,115200n8 loglevel=0
    bootcmd=bootipq_usb
    bootdelay=2
    ethact=eth0
    ethaddr=00:03:7f:ba:db:ad
    fdt_high=0x4A400000
    fdtcontroladdr=4a976500
    fileaddr=44000000
    filesize=18d45bc
    flash_type=8
    ipaddr=192.168.10.10
    machid=8010008
    mtdids=nand1=spi0.0
    nand_erasesize=1000
    nand_oobsize=0
    nand_writesize=100
    netmask=255.255.255.0
    serverip=192.168.10.1
    soc_hw_version=200d0200
    soc_version_major=2
    soc_version_minor=0
    stderr=serial@78B3000
    stdin=serial@78B3000
    stdout=serial@78B3000

    Environment size: 557/65532 bytes
  ```

- #### `tftpboot`

  ```
    IPQ807x# tftpboot
    ipq807x_eth_halt: done
    eth0 PHY0 Down Speed :10 Half duplex
    eth0 PHY1 Down Speed :10 Half duplex
    eth0 PHY2 Down Speed :10 Half duplex
    eth0 PHY3 Down Speed :10 Half duplex
    eth0 PHY4 up Speed :10 Full duplex
    eth0 PHY5 up Speed :10 Full duplex
    ipq807x_eth_init: done
    *** Warning: no boot file name; using 'C0A80A0A.img'
    Using eth0 device
    TFTP from server 192.168.10.1; our IP address is 192.168.10.10
    Filename 'C0A80A0A.img'.
    Load address: 0x44000000
    Loading: 
  ```

- #### `is_sec_boot_enabled`

  ```
    IPQ807x# is_sec_boot_enabled
    secure boot fuse is not enabled
  ```

- #### `usb *`

  KernelはUSBで接続されているストレージから読み出しているようである

  このストレージは、名前<a href="https://d.hatena.ne.jp/keyword/%A4%AB%A4%E9%A4%B7" class="keyword">からし</a>てどうもSDX55側のMTPモードを利用している雰囲気がある。ただし、コマンド操作でアクセスしようとするとタイミングが悪いのか `usb info` で検出しないことが度々ある（`bootipq_usb` 内では一定時間ディレイを挟んでいるかも）

  ```
    IPQ807x# usb start
    IPQ807x# usb reset
    resetting USB...
    IPQ807x# usb info
    1: Hub,  USB Revision 3.0
     - U-Boot XHCI Host Controller 
     - Class: Hub
     - PacketSize: 9  Configurations: 1
     - Vendor: 0x0000  Product 0x0000 Version 1.0
       Configuration: 1
       - Interfaces: 1 Self Powered 0mA
         Interface: 0
         - Alternate Setting 0, Endpoints: 1
         - Class Hub
         - Endpoint 1 In Interrupt MaxPacket 8 Interval 255ms

    1: Hub,  USB Revision 3.0
     - U-Boot XHCI Host Controller 
     - Class: Hub
     - PacketSize: 9  Configurations: 1
     - Vendor: 0x0000  Product 0x0000 Version 1.0
       Configuration: 1
       - Interfaces: 1 Self Powered 0mA
         Interface: 0
         - Alternate Setting 0, Endpoints: 1
         - Class Hub
         - Endpoint 1 In Interrupt MaxPacket 8 Interval 255ms

    2: Mass Storage,  USB Revision 2.10
     - QCOM SDXPRAIRIE-MTP _SN:436B307A 436b307a
     - Class: (from Interface) Mass Storage
     - PacketSize: 64  Configurations: 1
     - Vendor: 0x05c6  Product 0xf000 Version 4.20
       Configuration: 1
       - Interfaces: 1 Bus Powered 500mA
       - String: "MS"
         Interface: 0
         - Alternate Setting 0, Endpoints: 2
         - Class Mass Storage, Transp. SCSI, Bulk only
         - String: "Mass Storage"
         - Endpoint 1 In Bulk MaxPacket 512
         - Endpoint 1 Out Bulk MaxPacket 512

    IPQ807x# usb tree
    USB device tree:
      1  Hub (5 Gb/s, 0mA)
         U-Boot XHCI Host Controller 

      1  Hub (5 Gb/s, 0mA)
      |  U-Boot XHCI Host Controller 
      |
      +-2  Mass Storage (480 Mb/s, 500mA)
           QCOM SDXPRAIRIE-MTP _SN:436B307A 436b307a

    IPQ807x# usb dev

    USB device -1: device type unknown
    IPQ807x# usb part

    Partition Map for USB device 0  --   Partition Type: DOS

    Part    Start Sector    Num Sectors     UUID            Type
    IPQ807x# usb storage
      Device 0: Vendor: Linux    Rev: 0414 Prod: File-Stor Gadget
                Type: Removable Hard Disk
                Capacity: 29.0 MB = 0.0 GB (59392 x 512)
  ```

- #### `fat* usb 0:0`

  ```
    IPQ807x# fatinfo usb 0:0
    Interface:  USB
      Device 0: Vendor: Linux    Rev: 0414 Prod: File-Stor Gadget
                Type: Removable Hard Disk
                Capacity: 29.0 MB = 0.0 GB (59392 x 512)
    Filesystem: FAT16 "NO NAME    "
    IPQ807x# fatls usb 0:0
     28071196   uimage-initramfs.itb 

    1 file(s), 0 dir(s)
  ```

### Kernel

パスワードが設定されているから代わりにfailsafe

ただしWDTの影響か3分前後で勝手にリセットが掛かり、再起動される

- #### `uname -a`

  ```
    root@(none):/# uname -a
    Linux (none) 4.4.60 #2 SMP PREEMPT Wed Aug 2 18:42:52 CST 2023 aarch64 GNU/Linux
  ```

- #### `cat /proc/version`

  ```
    root@(none):/# cat /proc/version
    Linux version 4.4.60 (cpebuild@ubuntu-45-11) (gcc version 5.2.0 (OpenWrt GCC 5.2.0 9af9c46+r49254) ) #2 SMP PREEMPT Wed Aug 2 18:42:52 CST 2023
  ```

- #### `cat /proc/cmdline`

  ```
    root@(none):/# cat /proc/cmdline
    console=ttyMSM0,115200n8 loglevel=0 swiotlb=1 coherent_pool=2M
  ```

- #### `cat /proc/cpuinfo`

  ```
    root@(none):/# cat /proc/cpuinfo
    processor       : 0
    BogoMIPS        : 38.40
    Features        : fp asimd evtstrm aes pmull sha1 sha2 crc32
    CPU implementer : 0x41
    CPU architecture: 8
    CPU variant     : 0x0
    CPU part        : 0xd03
    CPU revision    : 4

    processor       : 1
    BogoMIPS        : 38.40
    Features        : fp asimd evtstrm aes pmull sha1 sha2 crc32
    CPU implementer : 0x41
    CPU architecture: 8
    CPU variant     : 0x0
    CPU part        : 0xd03
    CPU revision    : 4

    processor       : 2
    BogoMIPS        : 38.40
    Features        : fp asimd evtstrm aes pmull sha1 sha2 crc32
    CPU implementer : 0x41
    CPU architecture: 8
    CPU variant     : 0x0
    CPU part        : 0xd03
    CPU revision    : 4

    processor       : 3
    BogoMIPS        : 38.40
    Features        : fp asimd evtstrm aes pmull sha1 sha2 crc32
    CPU implementer : 0x41
    CPU architecture: 8
    CPU variant     : 0x0
    CPU part        : 0xd03
    CPU revision    : 4

    Hardware        : Qualcomm Technologies, Inc. IPQ807x/AP-HK09
  ```

- #### `cat /proc/meminfo`

  ```
    root@(none):/# cat /proc/meminfo
    MemTotal:         408668 kB
    MemFree:          256560 kB
    MemAvailable:     336880 kB
    Buffers:               0 kB
    Cached:            84120 kB
    SwapCached:            0 kB
    Active:            10540 kB
    Inactive:          74124 kB
    Active(anon):        548 kB
    Inactive(anon):       16 kB
    Active(file):       9992 kB
    Inactive(file):    74108 kB
    Unevictable:           0 kB
    Mlocked:               0 kB
    SwapTotal:             0 kB
    SwapFree:              0 kB
    Dirty:                 0 kB
    Writeback:             0 kB
    AnonPages:           568 kB
    Mapped:             1312 kB
    Shmem:                20 kB
    Slab:              13960 kB
    SReclaimable:       4920 kB
    SUnreclaim:         9040 kB
    KernelStack:        1568 kB
    PageTables:           88 kB
    NFS_Unstable:          0 kB
    Bounce:                0 kB
    WritebackTmp:          0 kB
    CommitLimit:      204332 kB
    Committed_AS:        628 kB
    VmallocTotal:   258998208 kB
    VmallocUsed:           0 kB
    VmallocChunk:          0 kB
  ```

- #### `cat /proc/mtd`

  ```
    root@(none):/# cat /proc/mtd
    dev:    size   erasesize  name
    mtd0: 00040000 00010000 "0:SBL1"
    mtd1: 00010000 00010000 "0:MIBIB"
    mtd2: 00160000 00010000 "0:QSEE"
    mtd3: 00010000 00010000 "0:DEVCFG"
    mtd4: 00020000 00010000 "0:RPM"
    mtd5: 00010000 00010000 "0:CDT"
    mtd6: 00010000 00010000 "0:APPSBLENV"
    mtd7: 000a0000 00010000 "0:APPSBL"
    mtd8: 00040000 00010000 "0:ART"
    mtd9: 00010000 00010000 "0:OEM"
    mtd10: 00020000 00010000 "0:CRASH"
  ```

- #### `cat /proc/partitions`

  ```
    root@(none):/# cat /proc/partitions
    major minor  #blocks  name

       1        0       4096 ram0
       1        1       4096 ram1
       1        2       4096 ram2
       1        3       4096 ram3
       1        4       4096 ram4
       1        5       4096 ram5
       1        6       4096 ram6
       1        7       4096 ram7
       1        8       4096 ram8
       1        9       4096 ram9
       1       10       4096 ram10
       1       11       4096 ram11
       1       12       4096 ram12
       1       13       4096 ram13
       1       14       4096 ram14
       1       15       4096 ram15
      31        0        256 mtdblock0
      31        1         64 mtdblock1
      31        2       1408 mtdblock2
      31        3         64 mtdblock3
      31        4        128 mtdblock4
      31        5         64 mtdblock5
      31        6         64 mtdblock6
      31        7        640 mtdblock7
      31        8        256 mtdblock8
      31        9         64 mtdblock9
      31       10        128 mtdblock10
  ```

- #### `ubinfo -a`

  ```
    root@(none):/# ubinfo -a
    UBI version:                    1
    Count of UBI devices:           0
    UBI control device major/minor: 10:56
  ```

- #### `strings /dev/mtdblock6`

  ```
    root@(none):/# strings /dev/mtdblock6
    @baudrate=115200
    bootdelay=2
    ethact=eth0
    ethaddr=00:03:7f:ba:db:ad
    fdt_high=0x4A400000
    fdtcontroladdr=4a976480
    fileaddr=44000000
    filesize=18d45bc
    flash_type=8
    ipaddr=192.168.10.10
    machid=8010008
    mtdids=nand1=spi0.0
    netmask=255.255.255.0
    serverip=192.168.10.1
    soc_hw_version=200d0200
    soc_version_major=2
    soc_version_minor=0
    stderr=serial@78B3000
    stdin=serial@78B3000
    stdout=serial@78B3000
    bootcmd=bootipq_usb
    bootargs=console=ttyMSM0,115200n8 loglevel=0
    ok_image=17bda96be656cfd633539c226b68039d.itb
    =ttyMSM0,115200n8
    otipq_usb
  ```

- #### `hexdump -n 1024 -C /dev/mtdblock6`

  ```
    root@(none):/# hexdump -n 1024 -C /dev/mtdblock6
    00000000  31 5f 0e 40 62 61 75 64  72 61 74 65 3d 31 31 35  |1_.@baudrate=115|
    00000010  32 30 30 00 62 6f 6f 74  64 65 6c 61 79 3d 32 00  |200.bootdelay=2.|
    00000020  65 74 68 61 63 74 3d 65  74 68 30 00 65 74 68 61  |ethact=eth0.etha|
    00000030  64 64 72 3d 30 30 3a 30  33 3a 37 66 3a 62 61 3a  |ddr=00:03:7f:ba:|
    00000040  64 62 3a 61 64 00 66 64  74 5f 68 69 67 68 3d 30  |db:ad.fdt_high=0|
    00000050  78 34 41 34 30 30 30 30  30 00 66 64 74 63 6f 6e  |x4A400000.fdtcon|
    00000060  74 72 6f 6c 61 64 64 72  3d 34 61 39 37 36 34 38  |troladdr=4a97648|
    00000070  30 00 66 69 6c 65 61 64  64 72 3d 34 34 30 30 30  |0.fileaddr=44000|
    00000080  30 30 30 00 66 69 6c 65  73 69 7a 65 3d 31 38 64  |000.filesize=18d|
    00000090  34 35 62 63 00 66 6c 61  73 68 5f 74 79 70 65 3d  |45bc.flash_type=|
    000000a0  38 00 69 70 61 64 64 72  3d 31 39 32 2e 31 36 38  |8.ipaddr=192.168|
    000000b0  2e 31 30 2e 31 30 00 6d  61 63 68 69 64 3d 38 30  |.10.10.machid=80|
    000000c0  31 30 30 30 38 00 6d 74  64 69 64 73 3d 6e 61 6e  |10008.mtdids=nan|
    000000d0  64 31 3d 73 70 69 30 2e  30 00 6e 65 74 6d 61 73  |d1=spi0.0.netmas|
    000000e0  6b 3d 32 35 35 2e 32 35  35 2e 32 35 35 2e 30 00  |k=255.255.255.0.|
    000000f0  73 65 72 76 65 72 69 70  3d 31 39 32 2e 31 36 38  |serverip=192.168|
    00000100  2e 31 30 2e 31 00 73 6f  63 5f 68 77 5f 76 65 72  |.10.1.soc_hw_ver|
    00000110  73 69 6f 6e 3d 32 30 30  64 30 32 30 30 00 73 6f  |sion=200d0200.so|
    00000120  63 5f 76 65 72 73 69 6f  6e 5f 6d 61 6a 6f 72 3d  |c_version_major=|
    00000130  32 00 73 6f 63 5f 76 65  72 73 69 6f 6e 5f 6d 69  |2.soc_version_mi|
    00000140  6e 6f 72 3d 30 00 73 74  64 65 72 72 3d 73 65 72  |nor=0.stderr=ser|
    00000150  69 61 6c 40 37 38 42 33  30 30 30 00 73 74 64 69  |ial@78B3000.stdi|
    00000160  6e 3d 73 65 72 69 61 6c  40 37 38 42 33 30 30 30  |n=serial@78B3000|
    00000170  00 73 74 64 6f 75 74 3d  73 65 72 69 61 6c 40 37  |.stdout=serial@7|
    00000180  38 42 33 30 30 30 00 62  6f 6f 74 63 6d 64 3d 62  |8B3000.bootcmd=b|
    00000190  6f 6f 74 69 70 71 5f 75  73 62 00 62 6f 6f 74 61  |ootipq_usb.boota|
    000001a0  72 67 73 3d 63 6f 6e 73  6f 6c 65 3d 74 74 79 4d  |rgs=console=ttyM|
    000001b0  53 4d 30 2c 31 31 35 32  30 30 6e 38 20 6c 6f 67  |SM0,115200n8 log|
    000001c0  6c 65 76 65 6c 3d 30 00  00 00 6f 6b 5f 69 6d 61  |level=0...ok_ima|
    000001d0  67 65 3d 31 37 62 64 61  39 36 62 65 36 35 36 63  |ge=17bda96be656c|
    000001e0  66 64 36 33 33 35 33 39  63 32 32 36 62 36 38 30  |fd633539c226b680|
    000001f0  33 39 64 2e 69 74 62 00  00 3d 74 74 79 4d 53 4d  |39d.itb..=ttyMSM|
    00000200  30 2c 31 31 35 32 30 30  6e 38 00 00 6f 74 69 70  |0,115200n8..otip|
    00000210  71 5f 75 73 62 00 00 00  00 00 00 00 00 00 00 00  |q_usb...........|
    00000220  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
    *
    00000400
  ```

<!-- -->

- #### bootlog (`loglevel=0`)

  ```
    Press the [f] key and hit [enter] to enter failsafe mode
    Press the [1], [2], [3] or [4] key and hit [enter] to select the debug level
    Sending udev events over mhi-uci WIFI FW mount is successful
    /lib/firmware/qca-nss0.bin 33
    /lib/firmware/qca-nss1.bin 33
    acfg_tool: Issuing blocking call to wait for events
    **** Platform Name: ap-hk09 *****
    Copy ART caldata from /dev/mtdblock8 to /tmp/virtual_art.bin
    qcawifi configuration is disable


    --------------------------------------------------------------------
    ---------------------------Welcome To Cli---------------------------
    --SBAir5, CKB01_11.B.003_293_202308021758, 10:71:FA:69:F0:5B--
    --------------------------------------------------------------------
    Login: Mode Switch:LTE Only mode attached flag = <FALSE>
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 1
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 2
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 3
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 4
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 5
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 6
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 7
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 8
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 9
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 10
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:RSRP Check Start
    Mode Switch:5G RSRP check count 1.<->,<-110>
    Mode Switch:Current RSRP check count 1.<->,<-128>
    Mode Switch:wait 1 minute(s)
  ```

- #### bootlog (`loglevel` 無し)

  ```

    PCI Link Intialized

    ** Invalid partition 1 **
    [    0.000000] Booting Linux on physical CPU 0x0
    [    0.000000] Initializing cgroup subsys cpuset
    [    0.000000] Initializing cgroup subsys cpu
    [    0.000000] Initializing cgroup subsys cpuacct
    [    0.000000] Linux version 4.4.60 (cpebuild@ubuntu-45-11) (gcc version 5.2.0 (OpenWrt GCC 5.2.0 9af9c46+r49254) ) #2 SMP PREEMPT Wed Aug 2 18:42:52 CST 2023
    [    0.000000] Boot CPU: AArch64 Processor [410fd034]
    [    0.000000] Ignoring memory range 0x40000000 - 0x41000000
    [    0.000000] Machine: Qualcomm Technologies, Inc. IPQ807x/AP-HK09
    [    0.000000] efi: Getting EFI parameters from FDT:
    [    0.000000] efi: UEFI not found.
    [    0.000000] psci: probing for conduit method from DT.
    [    0.000000] psci: PSCIv1.0 detected in firmware.
    [    0.000000] psci: Using standard PSCI v0.2 function IDs
    [    0.000000] psci: MIGRATE_INFO_TYPE not supported.
    [    0.000000] PERCPU: Embedded 15 pages/cpu @ffffffc01ef46000 s20992 r8192 d32256 u61440
    [    0.000000] Detected VIPT I-cache on CPU0
    [    0.000000] CPU features: enabling workaround for ARM erratum 845719
    [    0.000000] Built 1 zonelists in Zone order, mobility grouping on.  Total pages: 107352
    [    0.000000] Kernel command line: console=ttyMSM0,115200n8 swiotlb=1 coherent_pool=2M
    [    0.000000] PID hash table entries: 2048 (order: 2, 16384 bytes)
    [    0.000000] Dentry cache hash table entries: 65536 (order: 7, 524288 bytes)
    [    0.000000] Inode-cache hash table entries: 32768 (order: 6, 262144 bytes)
    [    0.000000] software IO TLB [mem 0x5fe41000-0x5fe81000] (0MB) mapped at [ffffffc01ee41000-ffffffc01ee80fff]
    [    0.000000] Memory: 390044K/436224K available (5644K kernel code, 643K rwdata, 2388K rodata, 18580K init, 519K bss, 46180K reserved, 0K cma-reserved)
    [    0.000000] Virtual kernel memory layout:
    [    0.000000]     vmalloc : 0xffffff8000000000 - 0xffffffbdbfff0000   (   246 GB)
    [    0.000000]     vmemmap : 0xffffffbdc0000000 - 0xffffffbfc0000000   (     8 GB maximum)
    [    0.000000]               0xffffffbdc0040000 - 0xffffffbdc0800000   (     7 MB actual)
    [    0.000000]     fixed   : 0xffffffbffa7fd000 - 0xffffffbffac00000   (  4108 KB)
    [    0.000000]     PCI I/O : 0xffffffbffae00000 - 0xffffffbffbe00000   (    16 MB)
    [    0.000000]     modules : 0xffffffbffc000000 - 0xffffffc000000000   (    64 MB)
    [    0.000000]     memory  : 0xffffffc000000000 - 0xffffffc01f000000   (   496 MB)
    [    0.000000]       .init : 0xffffffc00085a000 - 0xffffffc001a7f000   ( 18580 KB)
    [    0.000000]       .text : 0xffffffc000080000 - 0xffffffc00085a000   (  8040 KB)
    [    0.000000]       .data : 0xffffffc001a8e000 - 0xffffffc001b2ee00   (   644 KB)
    [    0.000000] SLUB: HWalign=64, Order=0-3, MinObjects=0, CPUs=4, Nodes=1
    [    0.000000] Preemptible hierarchical RCU implementation.
    [    0.000000]  Build-time adjustment of leaf fanout to 64.
    [    0.000000] NR_IRQS:64 nr_irqs:64 0
    [    0.000000] Architected cp15 timer(s) running at 19.20MHz (virt).
    [    0.000000] clocksource: arch_sys_counter: mask: 0xffffffffffffff max_cycles: 0x46d987e47, max_idle_ns: 440795202767 ns
    [    0.000005] sched_clock: 56 bits at 19MHz, resolution 52ns, wraps every 4398046511078ns
    [    0.000468] Calibrating delay loop (skipped), value calculated using timer frequency.. 38.40 BogoMIPS (lpj=192000)
    [    0.000479] pid_max: default: 32768 minimum: 301
    [    0.000581] Mount-cache hash table entries: 1024 (order: 1, 8192 bytes)
    [    0.000591] Mountpoint-cache hash table entries: 1024 (order: 1, 8192 bytes)
    [    0.001158] Initializing cgroup subsys io
    [    0.001176] Initializing cgroup subsys memory
    [    0.001203] Initializing cgroup subsys devices
    [    0.001215] Initializing cgroup subsys freezer
    [    0.001227] Initializing cgroup subsys net_cls
    [    0.001236] Initializing cgroup subsys pids
    [    0.001491] EFI services will not be available.
    [    0.001517] ASID allocator initialised with 65536 entries
    [    0.052136] MSM Memory Dump base table set up
    [    0.052163] MSM Memory Dump apps data table set up
    [    0.090066] Detected VIPT I-cache on CPU1
    [    0.090114] CPU1: Booted secondary processor [410fd034]
    [    0.120048] Detected VIPT I-cache on CPU2
    [    0.120077] CPU2: Booted secondary processor [410fd034]
    [    0.150078] Detected VIPT I-cache on CPU3
    [    0.150106] CPU3: Booted secondary processor [410fd034]
    [    0.150160] Brought up 4 CPUs
    [    0.150187] SMP: Total of 4 processors activated.
    [    0.150197] CPU: All CPU(s) started at EL1
    [    0.150220] alternatives: patching kernel code
    [    0.169445] clocksource: jiffies: mask: 0xffffffff max_cycles: 0xffffffff, max_idle_ns: 19112604462750000 ns
    [    0.169474] futex hash table entries: 1024 (order: 5, 131072 bytes)
    [    0.169829] pinctrl core: initialized pinctrl subsystem
    [    0.171006] NET: Registered protocol family 16
    [    0.200026] cpuidle: using governor ladder
    [    0.230043] cpuidle: using governor menu
    [    0.230252] NET: Registered protocol family 42
    [    0.230315] vdso: 2 pages (1 code @ ffffffc001a95000, 1 data @ ffffffc001a94000)
    [    0.230345] hw-breakpoint: found 6 breakpoint and 4 watchpoint registers.
    [    0.231245] DMA: preallocated 2048 KiB pool for atomic allocations
    [    0.231377] CPU: IPQ8072A, SoC Version: 2.0
    [    0.231798] IPC logging disabled
    [    0.231804] IPC logging disabled
    [    0.231809] IPC logging disabled
    [    0.231814] IPC logging disabled
    [    0.231818] IPC logging disabled
    [    0.234370] Soc version is not 1, changing clock offsets
    [    0.243342] irq: no irq domain found for /soc/smp2p-wcss/slave-kernel !
    [    0.245714] irq: no irq domain found for /soc/smp2p-wcss/slave-kernel !
    [    0.248990] sps:sps is ready.
    [    0.254749] spmi spmi-0: PMIC Arb Version-2 (0x20010000)
    [    0.261585] qcom,cpr4-apss-regulator b018000.cpr4-ctrl: CPR valid fuse count: 4
    [    0.261899] qcom,cpr3-npu-regulator a4000.npu-cpr: NPU CPR valid fuse count: 2
    [    0.292125] pps_core: LinuxPPS API ver. 1 registered
    [    0.292133] pps_core: Software ver. 5.3.6 - Copyright 2005-2007 Rodolfo Giometti <giometti@linux.it>
    [    0.292156] PTP clock support registered
    [    0.293595] Advanced Linux Sound Architecture Driver Initialized.
    [    0.294226] clocksource: Switched to clocksource arch_sys_counter
    [    0.297454] NET: Registered protocol family 2
    [    0.298234] default registered
    [    0.298242] default registered
    [    0.298248] MPTCP: Stable release v0.92
    [    0.298288] TCP established hash table entries: 4096 (order: 3, 32768 bytes)
    [    0.298352] TCP bind hash table entries: 4096 (order: 4, 65536 bytes)
    [    0.298449] TCP: Hash tables configured (established 4096 bind 4096)
    [    0.298499] UDP hash table entries: 256 (order: 1, 8192 bytes)
    [    0.298522] UDP-Lite hash table entries: 256 (order: 1, 8192 bytes)
    [    0.298692] NET: Registered protocol family 1
    [   14.046364] hw perfevents: enabled with armv8_cortex_a53 PMU driver, 7 counters available
    [   14.054754] squashfs: version 4.0 (2009/01/31) Phillip Lougher
    [   14.054773] jffs2: version 2.2 (NAND) (SUMMARY) (LZMA) (RTIME) (CMODE_PRIORITY) (c) 2001-2006 Red Hat, Inc.
    [   14.058269] Key type asymmetric registered
    [   14.058285] Asymmetric key parser 'x509' registered
    [   14.058316] io scheduler noop registered
    [   14.058330] io scheduler deadline registered (default)
    [   14.060542] 20000000.pci supply vdda not found, using dummy regulator
    [   14.060589] 20000000.pci supply vdda_phy not found, using dummy regulator
    [   14.060625] 20000000.pci supply vdda_refclk not found, using dummy regulator
    [   14.061343] PCI host bridge /soc/pci@20000000 ranges:
    [   14.061369]    IO 0x20200000..0x2020ffff -> 0x20200000
    [   14.061384]   MEM 0x20220000..0x2fffffff -> 0x20220000
    [   14.315767] qcom-pcie 20000000.pci: link up
    [   14.315940] qcom-pcie 20000000.pci: PCI host bridge to bus 0000:00
    [   14.315955] pci_bus 0000:00: root bus resource [bus 00-ff]
    [   14.315969] pci_bus 0000:00: root bus resource [io  0x0000-0xffff] (bus address [0x20200000-0x2020ffff])
    [   14.315979] pci_bus 0000:00: root bus resource [mem 0x20220000-0x2fffffff]
    [   14.316302] pci 0000:00:00.0: bridge configuration invalid ([bus 00-00]), reconfiguring
    [   14.317281] pci 0000:00:00.0: BAR 8: assigned [mem 0x20300000-0x204fffff]
    [   14.317296] pci 0000:00:00.0: BAR 9: assigned [mem 0x20500000-0x206fffff 64bit pref]
    [   14.317309] pci 0000:00:00.0: BAR 0: assigned [mem 0x20220000-0x20220fff 64bit]
    [   14.317325] pci 0000:00:00.0: BAR 7: assigned [io  0x1000-0x1fff]
    [   14.317341] pci 0000:01:00.0: BAR 0: assigned [mem 0x20300000-0x20300fff 64bit]
    [   14.317392] pci 0000:01:00.0: BAR 2: assigned [mem 0x20301000-0x20301fff 64bit]
    [   14.317440] pci 0000:00:00.0: PCI bridge to [bus 01]
    [   14.317451] pci 0000:00:00.0:   bridge window [io  0x1000-0x1fff]
    [   14.317462] pci 0000:00:00.0:   bridge window [mem 0x20300000-0x204fffff]
    [   14.317473] pci 0000:00:00.0:   bridge window [mem 0x20500000-0x206fffff 64bit pref]
    [   14.317964] [E][of_register_mhi_controller] mhi coherent pool is not reserved
    [   14.318083] mhi 0000:01:00.0: BAR 0: assigned [mem 0x20300000-0x20300fff 64bit]
    [   14.318150] mhi 0000:01:00.0: enabling device (0000 -> 0002)
    [   14.319218] PCIe: RC0 enabled during bootup
    [   14.323688] msm_rpm_log_probe: OK
    [   14.324019] msm-dcc b3000.dcc: DCC XPU is not specified
    [   14.324311] msm-dcc b3000.dcc: jiffies_64: 0xffff9068, cntvct_64: 0x2586ebb9
    [   14.324324] msm-dcc b3000.dcc: gcnt_hi: 0x00000000(0xffffff80005f8004)
    [   14.324334] msm-dcc b3000.dcc: gcnt_lo: 0x2586ed99(0xffffff80005f8000)
    [   14.324905] TZ SMMU State: SMMU Stage2 Enabled
    [   14.324966] TZ Log : Will warn on Access Violation, as paniconaccessviolation is not set
    [   14.326531] msm_serial 78b3000.serial: msm_serial: detected port #0
    [   14.326573] msm_serial 78b3000.serial: uartclk = 3686400
    [   14.326610] 78b3000.serial: ttyMSM0 at MMIO 0x78b3000 (irq = 78, base_baud = 230400) is a MSM
    [   14.326632] msm_serial: console setup on port #0
    [   14.561729] rmnet_ctl driver probed
    [   15.193627] console [ttyMSM0] enabled
    [   15.197164] msm_serial 78b1000.serial: msm_serial: detected port #1
    [   15.200698] msm_serial 78b1000.serial: uartclk = 19200000
    [   15.206783] 78b1000.serial: ttyMSM1 at MMIO 0x78b1000 (irq = 79, base_baud = 1200000) is a MSM
    [   15.212737] msm_serial: driver initialized
    [   15.221145] msm_serial_hsl_init: driver initialized
    [   15.263726] brd: module loaded
    [   15.298165] loop: module loaded
    [   15.298806] spi_qup 78b5000.spi: IN:block:16, fifo:64, OUT:block:16, fifo:64
    [   15.301568] m25p80 spi32766.0: found gd25lq32, expected n25q128a11
    [   15.307429] m25p80 spi32766.0: gd25lq32 (4096 Kbytes)
    [   15.313437] 11 ofpart partitions found on MTD device spi32766.0
    [   15.318527] Creating 11 MTD partitions on "spi32766.0":
    [   15.324256] 0x000000000000-0x000000040000 : "0:SBL1"
    [   15.330113] 0x000000040000-0x000000050000 : "0:MIBIB"
    [   15.345292] 0x000000050000-0x0000001b0000 : "0:QSEE"
    [   15.345907] 0x0000001b0000-0x0000001c0000 : "0:DEVCFG"
    [   15.359925] 0x0000001c0000-0x0000001e0000 : "0:RPM"
    [   15.370564] 0x0000001e0000-0x0000001f0000 : "0:CDT"
    [   15.371181] 0x0000001f0000-0x000000200000 : "0:APPSBLENV"
    [   15.374894] 0x000000200000-0x0000002a0000 : "0:APPSBL"
    [   15.380398] 0x0000002a0000-0x0000002e0000 : "0:ART"
    [   15.385492] 0x0000002e0000-0x0000002f0000 : "0:OEM"
    [   15.390208] 0x0000002f0000-0x000000310000 : "0:CRASH"
    [   15.396091] libphy: Fixed MDIO Bus: probed
    [   15.400281] qca-mdio 90000.mdio: Could not find phy-enable-0-85v
    [   15.403678] qca-mdio 90000.mdio: Could not find phy-enable-1-2v
    [   15.409868] qca-mdio 90000.mdio: Could not find phy-enable-2-1v
    [   15.415497] qca-mdio 90000.mdio: Could not find phy-enable-1-8v
    [   16.081675] libphy: qca_mdio: probed
    [   16.082457] qca-mdio 90000.mdio: qca-mdio driver was registered
    [   16.084530] Unable to create IPC log context!
    [   16.090221] Skip QCA8074V1 in V2 platform
    [   16.094745] cnss[2]: INFO: Platform driver probed successfully. plat ffffffc0155d8018 tgt 0xfffe
    [   16.098703] i2c /dev entries driver
    [   16.154708] device-mapper: ioctl: 4.34.0-ioctl (2015-10-28) initialised: dm-devel@redhat.com
    [   16.155204] sdhci: Secure Digital Host Controller Interface driver
    [   16.162206] sdhci: Copyright(c) Pierre Ossman
    [   16.168220] sdhci-pltfm: SDHCI platform and OF driver helper
    [   16.173332] qcom_ice_get_device_tree_data: No vdd-hba-supply regulator, assuming not needed
    [   16.178431] ICE IRQ = 82
    [   16.186950] 
    [   16.186950] Version Rollback Feature Disabled
    [   16.189717] sps_register_bam_device : unable to create IPC Logging 0 for bam 0x0000000008b04000
    [   16.194872] sps_register_bam_device : unable to create IPC Logging 1 for bam 0x0000000008b04000sps_register_bam_device : unable to create IPC Logging 2 for bam 0x0000000008b04000
    [   16.212136] sps_register_bam_device : unable to create IPC Logging 3 for bam 0x0000000008b04000sps_register_bam_device : unable to create IPC Logging 4 for bam 0x0000000008b04000
    [   16.228021] sps:BAM 0x0000000008b04000 is registered.[   16.237172] remoteproc remoteproc0: releasing cd00000.qcom_q6v5_wcss
    [   16.240867] SPMI VADC - Min ch: 0 Max ch: 15
    [   16.248440] of_graph_get_next_endpoint(): no port node found in /soc/csr@6001000
    [   16.251011] coresight-csr 6001000.csr: CSR initialized
    [   16.258473] of_graph_get_next_endpoint(): no port node found in /soc/cti@6010000
    [   16.263410] of_graph_get_next_endpoint(): no port node found in /soc/cti@6011000
    [   16.270967] of_graph_get_next_endpoint(): no port node found in /soc/cti@6012000
    [   16.278345] of_graph_get_next_endpoint(): no port node found in /soc/cti@6013000
    [   16.285723] of_graph_get_next_endpoint(): no port node found in /soc/cti@6014000
    [   16.293085] of_graph_get_next_endpoint(): no port node found in /soc/cti@6015000
    [   16.300480] of_graph_get_next_endpoint(): no port node found in /soc/cti@6016000
    [   16.307867] of_graph_get_next_endpoint(): no port node found in /soc/cti@6017000
    [   16.315230] of_graph_get_next_endpoint(): no port node found in /soc/cti@6018000
    [   16.322601] of_graph_get_next_endpoint(): no port node found in /soc/cti@6019000
    [   16.329992] of_graph_get_next_endpoint(): no port node found in /soc/cti@601a000
    [   16.337372] of_graph_get_next_endpoint(): no port node found in /soc/cti@601b000
    [   16.344748] of_graph_get_next_endpoint(): no port node found in /soc/cti@601c000
    [   16.352112] of_graph_get_next_endpoint(): no port node found in /soc/cti@601d000
    [   16.359512] of_graph_get_next_endpoint(): no port node found in /soc/cti@601e000
    [   16.366890] of_graph_get_next_endpoint(): no port node found in /soc/cti@601f000
    [   16.374267] of_graph_get_next_endpoint(): no port node found in /soc/cti@6198000
    [   16.381631] of_graph_get_next_endpoint(): no port node found in /soc/cti@6199000
    [   16.389030] of_graph_get_next_endpoint(): no port node found in /soc/cti@619a000
    [   16.396415] of_graph_get_next_endpoint(): no port node found in /soc/cti@619b000
    [   16.403779] of_graph_get_next_endpoint(): no port node found in /soc/cti@610c000
    [   16.411339] sps_register_bam_device : unable to create IPC Logging 0 for bam 0x0000000006044000
    [   16.418400] sps_register_bam_device : unable to create IPC Logging 1 for bam 0x0000000006044000sps_register_bam_device : unable to create IPC Logging 2 for bam 0x0000000006044000
    [   16.435485] sps_register_bam_device : unable to create IPC Logging 3 for bam 0x0000000006044000sps_register_bam_device : unable to create IPC Logging 4 for bam 0x0000000006044000
    [   16.451372] sps:BAM 0x0000000006044000 is registered.[   16.459172] coresight-tmc 6028000.tmc: TMC initialized
    [   16.463835] coresight-tmc 6027000.tmc: TMC initialized
    [   16.468987] coresight-funnel 6021000.funnel: FUNNEL initialized
    [   16.473987] coresight-funnel 6100000.funnel: FUNNEL initialized
    [   16.479832] coresight-funnel 6120000.funnel: FUNNEL initialized
    [   16.485724] coresight-funnel 6130000.funnel: FUNNEL initialized
    [   16.491629] coresight-funnel 61a1000.funnel: FUNNEL initialized
    [   16.498060] coresight-etm4x 619c000.etm: ETM 4.0 initialized
    [   16.503665] coresight-etm4x 619d000.etm: ETM 4.0 initialized
    [   16.509569] coresight-etm4x 619e000.etm: ETM 4.0 initialized
    [   16.515219] coresight-etm4x 619f000.etm: ETM 4.0 initialized
    [   16.520638] coresight-replicator-qcom 6026000.replicator: REPLICATOR 1.0 initialized
    [   16.526398] coresight-stm 6002000.stm: STM initialized
    [   16.534988] of_graph_get_next_endpoint(): no port node found in /soc/hwevent@6101000
    [   16.538786] coresight-hwevent 6101000.hwevent: Hardware Event driver initialized
    [   16.549992] NET: Registered protocol family 10
    [   16.554908] fullmesh registered
    [   16.558213] ndiffports registered
    [   16.561257] binder registered
    [   16.564744] roundrobin registered
    [   16.567676] redundant registered
    [   16.570974] NET: Registered protocol family 17
    [   16.574322] bridge: automatic filtering via arp/ip/ip6tables has been deprecated. Update your scripts to load br_netfilter if you need this.
    [   16.578566] Bridge firewalling registered
    [   16.591306] 8021q: 802.1Q VLAN Support v1.8
    [   16.612251] qcom,cpr4-apss-regulator b018000.cpr4-ctrl: CPR valid fuse count: 4
    [   16.612512] pmd9655_s3: supplied by e-smps1-reg
    [   16.618540] cpr4_ipq807x_apss_read_fuse_data: apc_corner: speed bin = 0
    [   16.622916] cpr4_ipq807x_apss_read_fuse_data: apc_corner: CPR fusing revision = 1
    [   16.629490] cpr4_ipq807x_apss_read_fuse_data: apc_corner: CPR misc fuse value = 0
    [   16.637149] cpr4_ipq807x_apss_read_fuse_data: apc_corner: Voltage boost fuse config = 0 boost = disable
    [   16.644664] cpr3_mem_acc_init: apc: not using memory accelerator regulator
    [   16.653780] cpr4_ipq807x_apss_calculate_open_loop_voltages: apc_corner: fused      SVS: open-loop= 704000 uV
    [   16.660742] cpr4_ipq807x_apss_calculate_open_loop_voltages: apc_corner: fused      NOM: open-loop= 808000 uV
    [   16.670723] cpr4_ipq807x_apss_calculate_open_loop_voltages: apc_corner: fused    TURBO: open-loop= 864000 uV
    [   16.680613] cpr4_ipq807x_apss_calculate_open_loop_voltages: apc_corner: fused   STURBO: open-loop= 944000 uV
    [   16.690402] cpr4_ipq807x_apss_calculate_target_quotients: apc_corner: fused      SVS: quot[ 7]= 756, quot_offset[ 7]=   0
    [   16.700154] cpr4_ipq807x_apss_calculate_target_quotients: apc_corner: fused      NOM: quot[ 7]= 958, quot_offset[ 7]= 200
    [   16.711003] cpr4_ipq807x_apss_calculate_target_quotients: apc_corner: fused    TURBO: quot[ 7]=1056, quot_offset[ 7]=  95
    [   16.721941] cpr4_ipq807x_apss_calculate_target_quotients: apc_corner: fused   STURBO: quot[ 7]=1206, quot_offset[ 7]= 150
    [   16.733009] cpr3_regulator_init_ctrl: apc: Default CPR mode = closed-loop
    [   16.744399] qcom,cpr3-npu-regulator a4000.npu-cpr: NPU CPR valid fuse count: 2
    [   16.750688] pmd9655_s4: supplied by e-smps1-reg
    [   16.757848] cpr3_mem_acc_init: npu: not using memory accelerator regulator
    [   16.762113] npu_corner: fused      NOM: open-loop= 760000 uV
    [   16.769067] npu_corner: fused    TURBO: open-loop= 824000 uV
    [   16.774923] npu_corner: fused      NOM: open-loop= 760000 uV
    [   16.780510] npu_corner: fused    TURBO: open-loop= 824000 uV
    [   16.786187] npu_corner: Normal and Cold condition init done. Default to normal.
    [   16.792776] cpufreq: cpufreq_online: CPU0: Running at unlisted freq: 800000 KHz
    [   16.799010] cpufreq: cpufreq_online: CPU0: Unlisted initial frequency changed to: 1017600 KHz
    [   16.807374] qcom-q6v5-wcss-pil cd00000.qcom_q6v5_wcss: ssr registeration success qcom_q6v5_wcss
    [   16.814910] remoteproc remoteproc0: cd00000.qcom_q6v5_wcss is available
    [   16.823534] hctosys: unable to open rtc device (rtc0)
    [   16.835180] pmd9655_ldo11: disabling
    [   16.835657] ALSA device list:
    [   16.838750]   No soundcards found.
    [   16.849414] Freeing unused kernel memory: 18580K (ffffffc00085a000 - ffffffc001a7f000)
    [   16.849458] Freeing alternatives memory: 44K (ffffffc001a7f000 - ffffffc001a8a000)
    [   16.860598] init: Console is alive
    [   16.863839] init: - watchdog -
    [   16.876553] usbcore: registered new interface driver usbfs
    [   16.876599] usbcore: registered new interface driver hub
    [   16.881002] usbcore: registered new device driver usb
    [   16.887443] Button Hotplug driver version 0.4.1
    [   16.893684] SCSI subsystem initialized
    [   16.910380] ehci_hcd: USB 2.0 'Enhanced' Host Controller (EHCI) Driver
    [   16.910667] ehci-platform: EHCI generic platform driver
    [   16.922269] msm-usb-ssphy-qmp 78000.ssphy: Initializing QMP phy
    [   16.929204] msm-usb-ssphy-qmp 78000.ssphy: QMP PHY initialization timeout
    [   16.929225] msm-usb-ssphy-qmp 78000.ssphy: USB3_PHY_PCS_STATUS:68686868
    [   17.136108] msm-usb-ssphy-qmp 58000.ssphy: Initializing QMP phy
    [   17.143708] msm-usb-ssphy-qmp 58000.ssphy: QMP PHY initialization timeout
    [   17.143729] msm-usb-ssphy-qmp 58000.ssphy: USB3_PHY_PCS_STATUS:68686868
    [   17.351964] xhci-hcd xhci-hcd.0.auto: xHCI Host Controller
    [   17.351999] xhci-hcd xhci-hcd.0.auto: new USB bus registered, assigned bus number 1
    [   17.356536] xhci-hcd xhci-hcd.0.auto: hcc params 0x0220fe65 hci version 0x110 quirks 0x00010010
    [   17.363923] xhci-hcd xhci-hcd.0.auto: irq 193, io mem 0x08a00000
    [   17.372876] hub 1-0:1.0: USB hub found
    [   17.378834] hub 1-0:1.0: 1 port detected
    [   17.382524] xhci-hcd xhci-hcd.0.auto: xHCI Host Controller
    [   17.386483] xhci-hcd xhci-hcd.0.auto: new USB bus registered, assigned bus number 2
    [   17.391781] usb usb2: We don't know the algorithms for LPM for this host, disabling LPM.
    [   17.399515] hub 2-0:1.0: USB hub found
    [   17.407647] hub 2-0:1.0: 1 port detected
    [   17.411340] xhci-hcd xhci-hcd.1.auto: xHCI Host Controller
    [   17.415286] xhci-hcd xhci-hcd.1.auto: new USB bus registered, assigned bus number 3
    [   17.420699] xhci-hcd xhci-hcd.1.auto: hcc params 0x0220fe65 hci version 0x110 quirks 0x00010010
    [   17.428157] xhci-hcd xhci-hcd.1.auto: irq 194, io mem 0x08c00000
    [   17.437013] hub 3-0:1.0: USB hub found
    [   17.443058] hub 3-0:1.0: 1 port detected
    [   17.446721] xhci-hcd xhci-hcd.1.auto: xHCI Host Controller
    [   17.450697] xhci-hcd xhci-hcd.1.auto: new USB bus registered, assigned bus number 4
    [   17.456019] usb usb4: We don't know the algorithms for LPM for this host, disabling LPM.
    [   17.463736] hub 4-0:1.0: USB hub found
    [   17.471882] hub 4-0:1.0: 1 port detected
    [   17.477040] gpio_buttons initialized
    [   17.479709] gpio-led init driver
    [   17.483544] gpio_led_probe:gpio device register
    [   17.486676] hw_version_init
    [   17.490844] usb_protect initialized
    [   17.493537] Init module OPANIC v2.0 
    [   17.497840] usbcore: registered new interface driver usb-storage
    [   17.501088] usbcore: registered new interface driver uas
    [   17.867512] init: - preinit -
    Press the [f] key and hit [enter] to enter failsafe mode
    Press the [1], [2], [3] or [4] key and hit [enter] to select the debug level
    [   19.899386] procd: - early -
    [   19.899428] procd: - watchdog -
    Sending udev events over mhi-uci[   20.478687] procd: - ubus -
    [   21.480238] random: ubusd: uninitialized urandom read (4 bytes read, 7 bits of entropy available)
    [   21.494245] random: ubusd: uninitialized urandom read (4 bytes read, 7 bits of entropy available)
    [   21.494275] random: ubusd: uninitialized urandom read (4 bytes read, 7 bits of entropy available)
    [   21.504241] random: ubusd: uninitialized urandom read (4 bytes read, 7 bits of entropy available)
    [   21.510945] random: ubusd: uninitialized urandom read (4 bytes read, 7 bits of entropy available)
    [   21.519834] random: ubusd: uninitialized urandom read (4 bytes read, 7 bits of entropy available)
    [   21.528683] random: ubusd: uninitialized urandom read (4 bytes read, 7 bits of entropy available)
    [   21.537579] procd: - init -
     WIFI FW mount is successful
    [   22.147058] ntfs: driver 2.1.32 [Flags: R/O MODULE].
    [   22.150441] Initializing XFRM netlink socket
    [   22.151691] NET: Registered protocol family 15
    [   22.163376] ssdk_switch_device_num_init[1159]:INFO:ess-switch dts node number: 1
    [   22.163437] ssdk_dt_get_switch_node[970]:INFO:ess-switch DT exist!
    [   22.169942] ssdk_dt_parse_access_mode[856]:INFO:switch_access_mode: local bus
    [   22.175921] ssdk_dt_parse_access_mode[869]:INFO:switchreg_base_addr: 0x3a000000
    [   22.183037] ssdk_dt_parse_access_mode[870]:INFO:switchreg_size: 0x1000000
    [   22.190171] ssdk_dt_parse_mac_mode[295]:INFO:mac mode = 0x0
    [   22.197123] ssdk_dt_parse_mac_mode[304]:INFO:mac mode1 = 0xf
    [   22.202470] ssdk_dt_parse_mac_mode[313]:INFO:mac mode2 = 0xf
    [   22.208409] ssdk_dt_parse_phy_info[659]:INFO:[PORT 5] port_mac_sel = QGMAC_PORT
    [   22.214030] ssdk_dt_parse_phy_info[659]:INFO:[PORT 6] port_mac_sel = QGMAC_PORT
    [   22.221101] ssdk_dt_parse_uniphy[332]:INFO:ess-uniphy DT exist!
    [   22.228466] ssdk_dt_parse_intf_mac[801]:INFO:dp1 MAC 00:03:7f:ba:db:ad
    [   22.234369] ssdk_plat_init start
    [   22.316236] ssdk_gcc_clock_init[1011]:INFO:SSDK gcc clock init successfully!
    [   22.316992] HPPE initializing...
    [   22.322458] ssdk_phy_driver_init[328]:INFO:dev_id = 0, phy_adress = 2, phy_id = 0xffffffff phytype doesn't match
    [   22.325661] ssdk_phy_driver_init[328]:INFO:dev_id = 0, phy_adress = 3, phy_id = 0xffffffff phytype doesn't match
    [   22.335782] ssdk_phy_driver_init[328]:INFO:dev_id = 0, phy_adress = 24, phy_id = 0xffffffff phytype doesn't match
    [   22.345921] ssdk_phy_driver_init[328]:INFO:dev_id = 0, phy_adress = 28, phy_id = 0xffffffff phytype doesn't match
    [   22.356065] malibu_phy_api_ops_init[2875]:INFO:qca probe malibu phy driver succeeded!
    [   22.367775] regi_init[3526]:INFO:Initializing HPPE!!
    [   22.584219] ssdk_ppe_reset_init[1243]:INFO:ppe reset successfully!
    [   22.587219] qca_hppe_tdm_hw_init[674]:INFO:tdm setup num=96
    [   22.589558] qca_hppe_portctrl_hw_init[105]:INFO:Hawkeye PPE port initializing
    [   25.071277] ssdk_switch_register[1691]:INFO:Chip version 0x1500
    [   25.071310] qca_link_polling_select[1307]:INFO:link-polling-required node does not exist
    [   25.075998] ssdk_switch_register[1717]:INFO:polling is selected
    [   25.084327] regi_init[3530]:INFO:Initializing HPPE Done!!
    [   25.090019] regi_init[3590]:INFO:qca-ssdk module init succeeded!
    [   25.098991] tun: Universal TUN/TAP device driver, 1.6
    [   25.101594] tun: (C) 1999-2004 Max Krasnyansky <maxk@qualcomm.com>
    [   25.108873] EDMA ver 1 hw init
    [   25.112839] EDMA HW Reset completed succesfully
    [   25.115760] Num rings - TxDesc:1 (23-23) TxCmpl:1 (7-7)
    [   25.120084] RxDesc:1 (15-15) RxFill:1 (7-7)
    [   25.126653] GMAC2(ffffffc001169880) Invalid MAC@ - using 7e:1d:91:66:32:3b
    [   25.130379] GMAC3(ffffffc00116d880) Invalid MAC@ - using 3a:45:3c:2c:60:86
    [   25.136642] libphy: PHY 90000.mdio:02 not found
    [   25.143300] nss-dp: probe of 3a001400.dp3 failed with error -14
    [   25.147835] GMAC4(ffffffc00116d880) Invalid MAC@ - using c6:95:f5:6a:eb:de
    [   25.153696] libphy: PHY 90000.mdio:03 not found
    [   25.160560] nss-dp: probe of 3a001600.dp4 failed with error -14
    [   25.165006] GMAC5(ffffffc00116d880) Invalid MAC@ - using ce:29:d7:59:4b:40
    [   25.170903] libphy: PHY 90000.mdio:18 not found
    [   25.177824] nss-dp: probe of 3a001800.dp5 failed with error -14
    [   25.182260] GMAC6(ffffffc00116d880) Invalid MAC@ - using 42:5c:da:54:95:cc
    [   25.188180] libphy: PHY 90000.mdio:1c not found
    [   25.195097] nss-dp: probe of 3a001a00.dp6 failed with error -14
    [   25.199579] **********************************************************
    [   25.205428] * NSS Data Plane driver
    [   25.212006] **********************************************************
    [   25.222203] l2tp_core: L2TP core driver, V2.0
    [   25.222984] l2tp_netlink: L2TP netlink interface
    [   25.258280] qca-nss 39000000.nss: Direct firmware load for qca-nss0.bin failed with error -2
    [   25.258311] qca-nss 39000000.nss: Falling back to user helper
    /lib/firmware/qca-nss0.bin 33
    [   25.282572] nss_driver - fw of size 779896  bytes copied to load addr: 40000000, nss_id : 0
    [   25.284497] Supported Frequencies - 
    [   25.289717] 748.8 MHz 1.4976 GHz 
    [   25.295709] 1.6896 GHz [   25.296744] 
    [   25.299130] ffffffbffc659d00: set sdma ffffffc0016dc800
    [   25.300650] ffffffbffc659d00: meminfo init succeed
    [   25.323146] qca-nss 39400000.nss: Direct firmware load for qca-nss1.bin failed with error -2
    [   25.323177] qca-nss 39400000.nss: Falling back to user helper
    [   25.337418] node size 2 # items 4
    [   25.337441] memory: 40000000 536870912 (avl 505061376) items 4 active_cores 2
    [   25.339712] addr/size storage words 2 2 # words 4 in DTS, ddr size 1000000
    [   25.346843] ffffffbffc659d00: nss core 0 booted successfully
    /lib/firmware/qca-nss1.bin 33
    [   25.367223] nss_driver - fw of size 291644  bytes copied to load addr: 40800000, nss_id : 1
    [   25.368061] Supported Frequencies - 
    [   25.374424] 748.8 MHz 1.4976 GHz 
    [   25.380394] 1.6896 GHz [   25.381395] 
    [   25.383794] ffffffbffc660c80: set sdma ffffffc0135f1e00
    [   25.385306] ffffffbffc660c80: meminfo init succeed
    [   25.391852] sit: IPv6 over IPv4 tunneling driver
    [   25.395082] node size 2 # items 4
    [   25.395085] memory: 40000000 536870912 (avl 505061376) items 4 active_cores 2
    [   25.395091] addr/size storage words 2 2 # words 4 in DTS, ddr size 1000000
    [   25.395100] ffffffbffc660c80: nss core 1 booted successfully
    [   25.419319] nat46: module (version 8ff2ae59ec9840a7b8b45f976c51cae80abe0226) loaded.
    [   25.425124] gre: GRE over IPv4 demultiplexor driver
    [   25.431521] ip_gre: GRE over IPv4 tunneling driver
    [   25.436753] ip6_gre: GRE over IPv6 tunneling driver
    [   25.442411] Ethernet Channel Bonding Driver: v3.7.1 (April 27, 2011)
    [   25.450233] ip6_tables: (C) 2000-2006 Netfilter Core Team
    [   25.454729] rmnet_nss_init(): initializing rmnet_nss
    [   25.460028] nf_conntrack version 0.5.0 (3192 buckets, 12768 max)
    [   25.468916] QCA Hy-Fi multicast installation successfully
    [   25.475110] PPP generic driver version 2.4.2
    [   25.476925] nss_lag_init[352]:LAG Manager Installed
    [   25.479691] NET: Registered protocol family 24
    [   25.484940] PPTP driver version 0.8.5
    [   25.491313] diag: IPC Logging disabled
    [   25.491800] TRACK: P[0]      PMask[4]
    [   25.495027] TRACK: P[1]      PMask[4]
    [   25.498408] TRACK: P[2]      PMask[4]
    [   25.501679] TRACK: P[3]      PMask[4]
    [   25.504856] nik 4097 info->svc_id
    [   25.530180] QCA multicast snooping installed successfully
    [   25.531473] <NSS-CRYPTO>:module loaded Build_ID - 08/02/23, 18:31:36 SoC=ipq807x_64
    [   25.536322] nss-macsec0 DT exist!
    [   25.542117] nss-macsec1 DT exist!
    [   25.545594] cannot find nss-macsec2 node
    [   25.548793] nss_macsec init success
    [   25.568617] u32 classifier
    [   25.568636]     input device check on
    [   25.570234]     Actions configured
    [   25.574855] Mirror/redirect action on
    [   25.585339] fuse init (API version 7.23)
    [   25.587714] arp_tables: (C) 2002 David S. Miller
    [   25.595552] Ebtables v2.0 registered
    [   25.596832] ip_tables: (C) 2000-2006 Netfilter Core Team
    [   25.600816] l2tp_ppp: PPPoL2TP kernel driver, V2.0
    [   25.699588] nf_conntrack_rtsp v0.6.21 loading
    [   25.837147] nf_nat_rtsp v0.6.21 loading
    [   25.840055] Netfilter messages via NETLINK v0.30.
    [   25.842167] PPP MPPE Compression module registered
    [   25.861323] xt_time: kernel timezone is -0000
    [   25.868436] ctnetlink v0.93: registering with nfnetlink.
    [   26.100957] random: jshn: uninitialized urandom read (4 bytes read, 41 bits of entropy available)
    [   26.103117] random: ubusd: uninitialized urandom read (4 bytes read, 41 bits of entropy available)
    [   26.108933] random: ubus: uninitialized urandom read (4 bytes read, 42 bits of entropy available)
    acfg_tool: Issuing blocking call to wait for events
    [   26.320441] ECM init
    [   26.320496] ECM database jhash random seed: 0x1e5d8765
    [   26.322789] ECM init complete
    [   26.714508] sh (1650): drop_caches: 3
    **** Platform Name: ap-hk09 *****
    Copy ART caldata from /dev/mtdblock8 to /tmp/virtual_art.bin
    qcawifi configuration is disable
    [   27.026431] random: nonblocking pool is initialized
    [   27.053948] main[3266] IPQCM:IPQCM Quitting!!!
    [   27.229422] ECM exit
    [   27.339646] DFC QMAP init
    [   27.364868] Connection established with the WDA Service, DL Marker disabled
    [   27.494651] ECM exit complete
    [   27.642729] sh (2337): /proc/1972/oom_adj is deprecated, please use /proc/1972/oom_score_adj instead.
    [   27.644099] [RMNET:HI] rmnet_vnd_create_dev(): NSS context for rmnet_data3 created
    [   29.491438] device eth0 entered promiscuous mode
    [   29.495352] device eth1 entered promiscuous mode
    [   29.498125] bridge0: port 2(eth1) entered forwarding state
    [   29.499758] bridge0: port 2(eth1) entered forwarding state
    [   30.283411] mem_manager: module license 'Proprietary' taints kernel.
    [   30.283438] Disabling lock debugging due to kernel taint
    [   30.454301] bridge0: port 2(eth1) entered disabled state
    [   30.525579] wlan: [3159:I:RPTR] qca_multi_link_init_module: 
    [   30.525579] ******QCA Repeater Initialization Done***********
    [   30.525579] 
    [   30.604699] wlan: [3171:I:ANY] =======ol_if_register_wifi3_0==========
    [   30.604699] 
    [   30.604736] wlan: [3171:I:ANY] osif_nss_register_module: NSS wifi ops registered for target_type:1 with soc_ops:ffffffbffd6289d8
    [   30.612031] wlan: [3171:I:ANY] ol_ath_wifi_ssr: ol_ath_wifi_ssr: SSR event 2 bus_type 1
    [   30.624171] remoteproc remoteproc0: powering up cd00000.qcom_q6v5_wcss
    [   30.631796] remoteproc remoteproc0: Booting fw image IPQ8074/q6_fw.mdt, size 668
    [   30.760523] ECM init
    [   30.760589] ECM database jhash random seed: 0x128026d5
    [   30.890799] ECM init complete
    [   30.999878] Subsystem error monitoring/handling services are up
    [   31.000251] remoteproc remoteproc0: remote processor cd00000.qcom_q6v5_wcss is now up
    [   31.000651] rpmsg_dev_probe: No pm domain
    [   31.000842] rpmsg_dev_probe: No pm domain
    [   31.004406] cnss[2]: INFO: QMI WLFW service connected, state: 0x1
    [   31.011587] cnss[2]: INFO: device_id : 65534 mem mode : [1]
    [   31.011632] cnss[2]: INFO: platform name: Qualcomm Technologies, Inc. IPQ807x/AP-HK09
    [   31.011632] diag: In diag_send_feature_mask_update, control channel is not open, p: 2, ffffffbffc8a8248
    [   31.012692] cnss[2]: INFO: Target capability: chip_id: 0x0, chip_family: 0x0, board_id: 0xff, soc_id: 0xffffffff, fw_version: 0x240804a5, fw_build_timestamp: 2021-04-16 05:26, otp_version: 0x0 eeprom_caldata_read_timeout 0s
    [   31.012702] cnss[2]: INFO: No board_id entry in device tree
    [   31.012932] cnss[2]: INFO: BDF location : 0x4b0c0000
    [   31.012934] cnss[2]: INFO: BDF IPQ8074/bdwlan.bin size 131072
    [   31.013347] cnss[2]: INFO: per device BDF location : 0x4b0e0000
    [   31.013410] cnss[2]: INFO: CALDATA IPQ8074/caldata.bin size 131072 offset 0x20000
    [   31.091212] wlan: [3171:I:ANY] ol_ath_wifi_ssr: ol_ath_wifi_ssr: SSR event 3 bus_type 1
    [   31.098825] cnss[2]: INFO: Waiting for FW ready. Device: 0xfffe, FW ready timeout: 15 seconds
    [   31.106632] cnss[2]: INFO: FW ready received for device 0xfffe
    [   31.115712] wlan: [3171:I:ANY] pld_ahb_wlan_enable: cnss_mode: Mission mode 
    [   31.121252] cnss[2]: INFO: Sending mode message, mode: MISSION(0), state: 0x7
    [   31.138328] wlan: [3171:I:ANY] qca_napi_create: qca_napi_create: napi instance 0 created on pipe 4
    [   31.138643] wlan: [3171:I:ANY] __ol_ath_attach: Allocated soc ffffffc00ef80880
    [   31.146267] wlan: [3171:D:dfs] WLAN_DEBUG_DFS1 : dfs_psoc_obj_create_notification: DFS obj attach to psoc successfully
    [   31.153740] wlan: [3171:E:CONFIG] cfg_uint_item_handler: num_vdevs_pdev0=16 - Out of range [1, 9]; Using 9
    [   31.164096] wlan: [3171:E:CONFIG] cfg_uint_item_handler: num_vdevs_pdev1=16 - Out of range [1, 9]; Using 9
    [   31.173725] wlan: [3171:E:CONFIG] cfg_uint_item_handler: num_vdevs_pdev2=16 - Out of range [1, 9]; Using 9
    [   31.183353] wlan: [3171:E:CONFIG] cfg_uint_item_handler: num_peers_pdev0=512 - Out of range [1, 128]; Using 128
    [   31.193005] wlan: [3171:E:CONFIG] cfg_uint_item_handler: num_peers_pdev1=512 - Out of range [1, 128]; Using 128
    [   31.202979] wlan: [3171:E:CONFIG] cfg_uint_item_handler: num_peers_pdev2=512 - Out of range [1, 128]; Using 128
    [   31.213044] wlan: [3171:E:CONFIG] cfg_uint_item_handler: num_monitor_pdev0=1 - Out of range [0, 0]; Using 0
    [   31.223113] wlan: [3171:E:CONFIG] cfg_uint_item_handler: num_monitor_pdev1=1 - Out of range [0, 0]; Using 0
    [   31.232829] wlan: [3171:E:CONFIG] cfg_uint_item_handler: num_monitor_pdev2=1 - Out of range [0, 0]; Using 0
    [   31.242693] wlan: [3171:I:ANY] osif_nss_wifi_soc_setup: nss register id -1 nss config 0 Target Type 18 
    [   31.252303] wlan: [3171:I:ANY] __ol_ath_attach: dev name soc0
    [   31.261849] wlan: [3171:I:ANY] ol_ath_soc_attach: WMI attached. wmi_handle ffffffc012237000 
    [   31.279818] wlan: [3171:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   31.279856] wlan: [3171:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   31.288763] wlan: [3171:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   31.298803] wlan: [3171:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   31.308873] wlan: [3171:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   31.318938] wlan: [3171:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   31.329005] wlan: [3171:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   31.339079] wlan: [3171:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   31.349178] wlan: [3171:I:ANY] htc_wmi_init: HT Create . ffffffc008191000
    [   31.359392] wlan: [3171:I:ANY] htc_wmi_init: Skipping BMI Done
    [   31.366183] wlan: [3171:I:ANY] htc_wmi_init: host_enable 0 nss_nwifi_offload 0
    [   31.394446] wlan: [3171:I:ANY] ol_target_init_complete: CDP soc attach success
    [   31.394478] wlan: [3171:I:ANY] ol_target_init_complete: Soc attach success NSS config 0 
    [   31.400663] wlan: [3171:I:ANY] htc_set_async_ep: htc_set_async_ep: htc_handle ffffffc008191000, ep 2, value 1
    [   31.408895] wlan: [3171:I:ANY] htc_set_async_ep: htc_set_async_ep: htc_handle ffffffc008191000, ep 3, value 1
    [   31.418712] wlan: [3171:I:ANY] htc_set_async_ep: htc_set_async_ep: htc_handle ffffffc008191000, ep 4, value 1
    [   31.429009] wlan: [1185:I:TIF] init_deinit_populate_hw_mode_capability: Preferred mode is not set, use mode id 1
    [   31.429009] 
    [   31.438538] wlan: [1185:I:TIF] HE_CAP Info = 9a18010d
    [   31.450141] wlan: [1185:I:TIF] Num HW modes = 1
    [   31.455105] wlan: [1185:I:TIF] Num PHY = 2
    [   31.459424] wlan: [1185:I:TIF] FW Build Version (Ext.) = 0
    [   31.463575] wlan: [1185:I:TIF] HDL Version: MajorVersion.MinorVersion = 0.0
    [   31.470140] wlan: [1185:I:TIF] Preferred HW Mode = 1 Num Radios = 2
    [   31.476048] wlan: [1185:I:TIF] init_deinit_add_11ax_modes: hw_mode_id = 1 phy_id = 0 wireless modes = f97f9001
    [   31.482523] wlan: [1185:I:TIF] init_deinit_add_11ax_modes: hw_mode_id = 1 phy_id = 1 wireless modes = 680688c
    [   31.493464] wlan: [1185:I:TIF] init_deinit_alloc_pdevs: CDP PDEV ATTACH success
    [   31.504348] wlan: [1185:I:TIF] init_deinit_alloc_pdevs: CDP PDEV ATTACH success
    [   31.509986] wlan: [1185:I:TIF] init_deinit_get_total_num_ema_vaps: num_radios: 2
    [   31.517116] wlan: [1185:I:TIF] init_deinit_get_total_num_ema_vaps: ema_max_vap_cnt: 0
    [   31.524713] wlan: [1185:I:TIF] init_deinit_get_total_num_vdevs_for_soc: num_vdevs: 18
    [   31.532359] wlan: [1185:I:TIF] init_deinit_get_total_num_ema_vaps: num_radios: 2
    [   31.539896] wlan: [1185:I:TIF] init_deinit_get_total_num_ema_vaps: ema_max_vap_cnt: 0
    [   31.547321] wlan: [1185:I:TIF] init_deinit_get_total_num_vdevs_for_soc: num_vdevs: 18
    [   31.555020] wlan: [1185:I:TIF] init_deinit_get_total_beaconing_vdevs_for_soc: beacon_tx_offload_max_vdev: 18
    [   31.562808] wlan: [1185:I:TIF] init_deinit_get_total_num_ema_vaps: num_radios: 2
    [   31.572739] wlan: [1185:I:TIF] init_deinit_get_total_num_ema_vaps: ema_max_vap_cnt: 0
    [   31.580093] wlan: [1185:I:TIF] init_deinit_get_total_num_vdevs_for_soc: num_vdevs: 18
    [   31.588265] wlan: [1185:I:TIF] init_deinit_get_total_num_ema_vaps: num_radios: 1
    [   31.595690] wlan: [1185:I:TIF] init_deinit_get_total_num_ema_vaps: ema_max_vap_cnt: 0
    [   31.603128] wlan: [1185:I:TIF] init_deinit_get_total_num_vdevs_for_soc: num_vdevs: 9
    [   31.611095] wlan: [1185:I:ANY] init_deinit_update_pdev_tgt_info: pdev id:0 wmi_handle:ffffffc012237000
    [   31.619395] wlan: [1185:F:DP] dp_rx_enable_mon_dest_frag: Feature DP_RX_MON_MEM_FRAG for mon_dest is enabled
    [   31.639764] wlan: [1185:I:ANY] init_deinit_update_pdev_tgt_info: Pdev = 0 Number of peers = 137 vdevs = 9
    [   31.639804] wlan: [1185:I:TIF] init_deinit_update_pdev_tgt_info: CDP PDEV INIT success
    [   31.648572] wlan: [1185:I:ANY] init_deinit_update_pdev_tgt_info: pdev id:1 wmi_handle:ffffffc014ecb800
    [   31.656969] wlan: [1185:F:DP] dp_rx_enable_mon_dest_frag: Feature DP_RX_MON_MEM_FRAG for mon_dest is enabled
    [   31.674934] wlan: [1185:I:ANY] init_deinit_update_pdev_tgt_info: Pdev = 1 Number of peers = 137 vdevs = 9
    [   31.675399] wlan: [1185:I:TIF] init_deinit_update_pdev_tgt_info: CDP PDEV INIT success
    [   31.785695] wlan: [1185:I:ANY] copy_fw_abi_version_tlv: copy_fw_abi_version_tlv: INIT_CMD version: 1, 0, 0x5f414351, 0x4c4d, 0x0, 0x0
    [   31.905103] wlan: [1775:I:ANY] ready_extract_init_status_tlv: ready_extract_init_status_tlv:0
    [   31.905140] wlan: [1775:I:ANY] dp_peer_map_attach_wifi3: dp_peer_map_attach_wifi3 max_peers 309, max_ast_index: 1040
    [   31.905140] 
    [   31.912709] wlan: [3171:I:ANY] ol_ath_connect_htc: WMI is ready
    [   31.924790] wlan: [3171:I:ANY] ol_ath_soc_attach: connect HTC
    [   31.943125] wlan: [3171:I:ANY] ol_ath_soc_attach: bypasswmi : 0
    [   31.943183] wlan: [3171:I:MSCS] qca_mscs_module_init: 
    [   31.943183] ****QCA MSCS Initialization Done**** SoC ffffffc00ef80880
    [   31.948189] wlan: [3171:I:ANY] ol_ath_soc_attach: UMAC attach
    [   31.959785] wlan: [3171:I:ANY] __ol_ath_attach: pdev_netdev name wifi0
    [   31.965331] wlan: [3171:I:ANY] __ol_ath_attach: Skip txrx_pdev_attach_target
    [   31.971722] wlan: [3171:I:ANY] __ol_ath_attach: BURSTING enabled by default
    [   31.979009] wlan: [3171:I:ANY] ol_ath_pdev_attach: interface_id 0
    [   31.985625] wlan: [3171:I:TIF] ol_ath_pdev_regdmn_init:  phy id = 0 Modes supported
    [   31.991861] wlan: [3171:I:TIF] ol_ath_pdev_regdmn_init:  11b = 0 11g = 0 11a = 1 11n = 1 11ac = 1 11ax = 1
    [   31.999344] wlan: [3171:I:TIF] ol_ath_pdev_regdmn_init:  Reg cap - phy_id = 0 supp_bnd = 2, modes = f97f9001, lo_2g = 0, hi_2g = 0 lo_g5 = 4900, hi_5g = 5920
    [   32.009067] wlan: [3171:I:ANY] ol_ath_update_wireless_modes: wireless_modes = f97f9001 before update
    [   32.023236] wlan: [3171:I:ANY] ol_ath_update_wireless_modes: Wireless_modes = f97f9001 after update
    [   32.032411] wlan: [3171:I:ANY] ol_ath_update_ext_caps: 11ax 5G supported case
    [   32.041260] wlan: [3171:I:MBSSIE] ol_ath_assign_mbssid_ref_bssid: MBSSID reference bssid is 02:03:7f:12:e3:bf soc: soc0 pdev: wifi0
    [   32.048571] wlan: [3171:I:MBSSIE] ieee80211_mbss_attach: :>
    [   32.060094] wlan: [3171:I:MBSSIE] ieee80211_mbss_attach: :<
    [   32.065647] wlan: [3171:I:ANY] ol_resmgr_create: OL Resmgr Init-ed
    [   32.071387] wlan: [3171:I:ANY] acfg_attach: acfg_attach: 3290: Netlink socket created:ffffffc014f3bc00
    [   32.077466] wlan: [3171:I:ANY] ol_ath_stats_attach: periodic_chan_stats: 1
    [   32.087754] wlan: [3171:I:ANY] wlan_scan_update_channel_list: num_chan: 25
    [   32.093633] wlan: [0:I:ANY] ol_ath_pdev_attach: Set global_ic[1], ptr:ffffffbffd2d8fe0
    [   32.100472] wlan: [0:I:ANY] dp_lag_soc_enable: pdev(ffffffc0015a6008) Enabling DBDC Repeater 0  soc_lag ffffffc007debc80
    [   32.108377] wlan: [0:I:ANY] dp_lag_pdev_set_primary_radio: pdev(ffffffc0015a6008) is_primary 0 
    [   32.119682] wlan: [0:I:ANY] ol_ath_twt_enable_complete_event_handler: twt enabled
    [   32.121383] wlan: [3171:I:ANY] ol_ath_ucfg_set_rx_pkt_protocol_tagging: Set RX packet type TAG, opcode : 0, pkt_type : 18, metadata : 0xca0,pdev_id = 0, REO dest ring = 5
    [   32.121383] 
    [   32.121421] wlan: [3171:I:ANY] ol_ath_pri20_cfg_blockchanlist_parse: cfg block channel list is empty
    [   32.121432] wlan: [3171:I:ANY] ol_ath_configure_cong_ctrl_max_msdus: pdev_idx = 0 tx_desc_limit = 32768
    [   32.121446] wlan: [3171:I:ANY] osif_wrap_attach: osif wrap attached
    [   32.121446] 
    [   32.121448] wlan: [3171:I:ANY] osif_wrap_devt_init: osif wrap dev table init done
    [   32.121448] 
    [   32.121452] wlan: [3171:I:ANY] osif_wrap_attach:  Wrap Attached: Wrap_com =ffffffc014f3b400 ic->ic_wrap_com=ffffffc014f3b400 &wrap_com->wc_devt=ffffffc014f3b400 
    [   32.121452] 
    [   32.121475] wlan: [3171:I:ANY] __ol_ath_attach: needed_headroom reservation 60
    [   32.121692] wlan: [3171:I:ANY] ieee80211_cfg80211_radio_attach: ic: 0xffffffc007f40880, wdev: 0xffffffc007f58ad0, wiphy: 0xffffffc014c632a0, netdev: 0xffffffc007f40000 
    [   32.122379] wlan: [3171:I:ANY] __ol_ath_attach: pdev_netdev name wifi1
    [   32.122394] wlan: [3171:I:ANY] __ol_ath_attach: Skip txrx_pdev_attach_target
    [   32.122397] wlan: [3171:I:ANY] __ol_ath_attach: BURSTING enabled by default
    [   32.122442] wlan: [3171:I:ANY] ol_ath_pdev_attach: interface_id 1
    [   32.122453] wlan: [3171:I:TIF] ol_ath_pdev_regdmn_init:  phy id = 1 Modes supported
    [   32.122457] wlan: [3171:I:TIF] ol_ath_pdev_regdmn_init:  11b = 1 11g = 1 11a = 0 11n = 1 11ac = 1 11ax = 1
    [   32.122461] wlan: [3171:I:TIF] ol_ath_pdev_regdmn_init:  Reg cap - phy_id = 1 supp_bnd = 1, modes = 680680c, lo_2g = 2312, hi_2g = 2732 lo_g5 = 0, hi_5g = 0
    [   32.122463] wlan: [3171:I:ANY] ol_ath_update_wireless_modes: wireless_modes = 680680c before update
    [   32.122466] wlan: [3171:I:ANY] ol_ath_update_wireless_modes: Wireless_modes = 680680c after update
    [   32.122471] wlan: [3171:I:ANY] ol_ath_update_ext_caps: 11ax 2G supported case
    [   32.122499] wlan: [3171:I:ANY] ol_ath_pdev_regdmn_init: LDPC not supported in 5G HE CAP
    [   32.122520] wlan: [3171:I:MBSSIE] ol_ath_assign_mbssid_ref_bssid: MBSSID reference bssid is 02:03:7f:12:db:73 soc: soc0 pdev: wifi1
    [   32.122576] wlan: [3171:I:MBSSIE] ieee80211_mbss_attach: :>
    [   32.122579] wlan: [3171:I:MBSSIE] ieee80211_mbss_attach: :<
    [   32.122583] wlan: [3171:I:ANY] ol_resmgr_create: OL Resmgr Init-ed
    [   32.122754] wlan: [3171:I:ANY] acfg_attach: Offload using existing sock ffffffc014f3bc00
    [   32.122760] wlan: [3171:I:ANY] ol_ath_stats_attach: periodic_chan_stats: 1
    [   32.122943] wlan: [3171:I:ANY] wlan_scan_update_channel_list: num_chan: 11
    [   32.122972] wlan: [0:I:ANY] ol_ath_pdev_attach: Set global_ic[2], ptr:ffffffbffd2d8fe0
    [   32.122978] wlan: [0:I:ANY] dp_lag_soc_enable: pdev(ffffffc004f78008) Enabling DBDC Repeater 0  soc_lag ffffffc007debc80
    [   32.122982] wlan: [0:I:ANY] dp_lag_pdev_set_primary_radio: pdev(ffffffc004f78008) is_primary 0 
    [   32.125203] wlan: [3171:I:ANY] ol_ath_ucfg_set_rx_pkt_protocol_tagging: Set RX packet type TAG, opcode : 0, pkt_type : 18, metadata : 0xca0,pdev_id = 1, REO dest ring = 5
    [   32.125203] 
    [   32.125232] wlan: [3171:I:ANY] ol_ath_pri20_cfg_blockchanlist_parse: cfg block channel list is empty
    [   32.125237] wlan: [3171:I:ANY] ol_ath_configure_cong_ctrl_max_msdus: pdev_idx = 1 tx_desc_limit = 32768
    [   32.125253] wlan: [3171:I:ANY] osif_wrap_attach: osif wrap attached
    [   32.125253] 
    [   32.125256] wlan: [3171:I:ANY] osif_wrap_devt_init: osif wrap dev table init done
    [   32.125256] 
    [   32.125260] wlan: [3171:I:ANY] osif_wrap_attach:  Wrap Attached: Wrap_com =ffffffc0044ea400 ic->ic_wrap_com=ffffffc0044ea400 &wrap_com->wc_devt=ffffffc0044ea400 
    [   32.125260] 
    [   32.125282] wlan: [3171:I:ANY] __ol_ath_attach: needed_headroom reservation 60
    [   32.125298] wlan: [3171:I:ANY] wlan_cfg80211_init: Number of 2G channels: 11 
    [   32.125434] wlan: [3171:I:ANY] ieee80211_cfg80211_radio_attach: ic: 0xffffffc007880880, wdev: 0xffffffc007898ad0, wiphy: 0xffffffc0044f22a0, netdev: 0xffffffc007880000 
    [   32.126059] wlan: [3171:I:Dynamic Mode Change] ol_ath_check_and_reconfig_hw_mode: Running with HW mode = 1
    [   32.126381] wlan: [3171:E:QLD] qld_register: Handle or address is NULL
    [   32.126405] wlan: [3171:I:ANY] wlan_pdev_operation: num_radios=1, wifi_radios[0].sc = ffffffc007f40880_radio_type = 2
    [   32.126409] wlan: [3171:I:ANY] wlan_pdev_operation: num_radios=2, wifi_radios[1].sc = ffffffc007880880_radio_type = 2
    [   32.126435] wlan: [3171:I:ANY] init_ath_pci_3_0: 6ath_ol_pci_wifi3.0 :  (Atheros/multi-bss)
    [   32.148112] wlan: [3308:I:ANY] osif_nss_register_module: NSS wifi ops registered for target_type:0 with soc_ops:ffffffbffd6d1fd0
    [   32.148418] wlan: [3308:I:ANY] init_ath_pci_2_0: 6ath_ol_pci_2_0:  (Atheros/multi-bss)
    [   32.549865] wlan: [0:I:ANY] ol_ath_twt_enable_complete_event_handler: twt enabled
    [   35.554348] nss-dp 3a001000.dp1 eth0: PHY Link up speed: 1000
    [   35.554527] bridge0: port 1(eth0) entered forwarding state
    [   35.559113] bridge0: port 1(eth0) entered forwarding state
    [   36.207376] wlan: [3840:I:ANY] ol_ath_wifi_ssr: ol_ath_wifi_ssr: SSR event 0 bus_type 1
    [   36.207430] wlan: [3840:I:ANY] ol_ath_ahb_remove: Suspending Target - with disable_intr set :soc0 (sc ffffffc010288000) soc=ffffffc00ef80880
    [   36.214283] wlan: [3840:I:ANY] wlan_pdev_operation: disable_target_intr val is 1
    [   36.227313] wlan: [3840:I:ANY] wlan_pdev_operation: disable_target_intr val is 1
    [   36.234491] wlan: [3840:I:ANY] ol_ath_ahb_remove: waiting for target paused event from target :soc0 (sc ffffffc010288000)
    [   36.241847] wlan: [3840:I:ANY] ol_ath_ahb_remove: AHB Call to nss detach 
    [   36.252723] wlan: [3840:I:ANY] ol_ath_ahb_remove: Call to nss detach ops 0000000000000000 
    [   36.259476] wlan: [3840:E:QLD] qld_register: Handle or address is NULL
    [   36.267658] wlan: [3840:I:ANY] osif_wrap_devt_detach: osif wrap dev table detached
    [   36.267658] 
    [   36.274135] wlan: [3840:I:ANY] osif_wrap_detach: osif wrap detached
    [   36.274135] 
    [   36.312168] wlan: [3840:E:CFR] tgt_cfr_deinit_pdev: Error occurred with exit code 16
    [   36.312168] 
    [   36.312204] wlan: [3840:E:CFR] cfr_deinitialize_pdev: cfr_deinitialize_pdev status=16
    [   36.312204] 
    [   36.320581] wlan: [3840:I:ANY] wlan_pdev_operation: soc_txrx_handle ffffffc00e804000 dp_pdev id 0
    [   36.329718] wlan: [3840:I:ANY] wlan_pdev_operation: soc_txrx_handle ffffffc00e804000 dp_pdev id 1
    [   36.338705] wlan: [3840:I:MBSSIE] ieee80211_mbss_detach: :>
    [   36.347454] wlan: [3840:I:MBSSIE] ieee80211_mbss_detach: :<
    [   36.352865] wlan: [3840:I:ANY] acfg_detach: acfg_detach Netlink socket released
    [   36.358346] wlan: [3840:E:CFR] tgt_cfr_deinit_pdev: Error occurred with exit code 16
    [   36.358346] 
    [   36.365626] wlan: [3840:E:CFR] cfr_deinitialize_pdev: cfr_deinitialize_pdev status=16
    [   36.365626] 
    [   36.375050] wlan: [0:I:ANY] ol_ath_pdev_detach: remove global_ic[1]..gloabl_ic ptr:ffffffbffd2d8fe0
    [   36.384202] wlan: [3840:I:ANY] ieee80211_cfg80211_radio_detach: ieee80211_cfg80211_radio_detach: ic: 0xffffffc007f40880, wdev: 0xffffffc007f58ad0, netdev: 0xffffffc007f40000 
    [   36.684338] PCIe: User of event deregistration is NULL
    [   36.734373] wlan: [3840:E:QLD] qld_register: Handle or address is NULL
    [   36.734513] wlan: [3840:I:ANY] osif_wrap_devt_detach: osif wrap dev table detached
    [   36.734513] 
    [   36.739860] wlan: [3840:I:ANY] osif_wrap_detach: osif wrap detached
    [   36.739860] 
    [   36.748858] wlan: [3840:E:CFR] tgt_cfr_deinit_pdev: Error occurred with exit code 16
    [   36.748858] 
    [   36.756765] wlan: [3840:E:CFR] cfr_deinitialize_pdev: cfr_deinitialize_pdev status=16
    [   36.756765] 
    [   36.765894] wlan: [3840:I:ANY] wlan_pdev_operation: soc_txrx_handle ffffffc00e804000 dp_pdev id 1
    [   36.775217] wlan: [3840:I:MBSSIE] ieee80211_mbss_detach: :>
    [   36.784017] wlan: [3840:I:MBSSIE] ieee80211_mbss_detach: :<
    [   36.789414] wlan: [3840:E:CFR] tgt_cfr_deinit_pdev: Error occurred with exit code 16
    [   36.789414] 
    [   36.795012] wlan: [3840:E:CFR] cfr_deinitialize_pdev: cfr_deinitialize_pdev status=16
    [   36.795012] 
    [   36.804401] wlan: [0:I:ANY] ol_ath_pdev_detach: remove global_ic[0]..gloabl_ic ptr:ffffffbffd2d8fe0
    [   36.813533] wlan: [3840:I:ANY] ieee80211_cfg80211_radio_detach: ieee80211_cfg80211_radio_detach: ic: 0xffffffc007880880, wdev: 0xffffffc007898ad0, netdev: 0xffffffc007880000 
    [   36.964370] PCIe: User of event deregistration is NULL
    [   37.054380] wlan: [3840:I:ANY] ol_ath_phyerr_detach: 6ol_ath_phyerr_detach: called
    [   37.054421] wlan: [3840:E:WMI] wmi_unified_unregister_event_handler: Event id 55 is unavailable
    [   37.060874] wlan: [3840:I:MSCS] qca_mscs_module_deinit: 
    [   37.060874] ****QCA MSCS De-Initialization Done**** SoC ffffffc00ef80880
    [   37.069947] wlan: [3840:E:WMI] wmi_unified_unregister_event_handler: Event id 141 is unavailable
    [   37.081850] wlan: [3840:E:WMI] wmi_unified_unregister_event_handler: Event id 137 is unavailable
    [   37.097467] cnss[2]: INFO: Sending mode message, mode: OFF(4), state: 0x7
    [   37.101605] wlan: [3840:I:ANY] 6ath_ahb_remove
    [   37.101605] 
    [   37.106404] cnss[2]: INFO: QMI WLFW service disconnected, state: 0x6
    [   37.138255] remoteproc remoteproc0: stopped remote processor cd00000.qcom_q6v5_wcss
    [   37.138320] wlan: [3840:I:ANY] ol_ath_wifi_ssr: ol_ath_wifi_ssr: SSR event 1 bus_type 1
    [   37.407080] wlan: [3883:I:RPTR] qca_multi_link_deinit_module: 
    [   37.407080] ******QCA RPtr De-Init Done***********
    [   37.407080] 
    [   37.797437] configuring additional NSS pbufs
    [   37.806793] additional pbufs of size 3100672 got added to NSS
    [   37.980374] wlan: [3993:I:RPTR] qca_multi_link_init_module: 
    [   37.980374] ******QCA Repeater Initialization Done***********
    [   37.980374] 
    [   38.061117] wlan: [3998:I:ANY] =======ol_if_register_wifi3_0==========
    [   38.061117] 
    [   38.061153] wlan: [3998:I:ANY] osif_nss_register_module: NSS wifi ops registered for target_type:1 with soc_ops:ffffffbffdcea9d8
    [   38.068276] wlan: [3998:I:ANY] ol_ath_wifi_ssr: ol_ath_wifi_ssr: SSR event 2 bus_type 1
    [   38.079843] remoteproc remoteproc0: powering up cd00000.qcom_q6v5_wcss
    [   38.088196] remoteproc remoteproc0: Booting fw image IPQ8074/q6_fw.mdt, size 668
    [   38.453954] Subsystem error monitoring/handling services are up
    [   38.454864] remoteproc remoteproc0: remote processor cd00000.qcom_q6v5_wcss is now up
    [   38.455076] rpmsg_dev_probe: No pm domain
    [   38.455791] rpmsg_dev_probe: No pm domain
    [   38.461217] cnss[2]: INFO: QMI WLFW service connected, state: 0x1
    [   38.467211] cnss[2]: INFO: device_id : 65534 mem mode : [1]
    [   38.468111] cnss[2]: INFO: platform name: Qualcomm Technologies, Inc. IPQ807x/AP-HK09
    [   38.468111] cnss[2]: INFO: Target capability: chip_id: 0x0, chip_family: 0x0, board_id: 0xff, soc_id: 0xffffffff, fw_version: 0x240804a5, fw_build_timestamp: 2021-04-16 05:26, otp_version: 0x0 eeprom_caldata_read_timeout 0s
    [   38.468121] cnss[2]: INFO: No board_id entry in device tree
    [   38.468564] cnss[2]: INFO: BDF location : 0x4b0c0000
    [   38.468567] cnss[2]: INFO: BDF IPQ8074/bdwlan.bin size 131072
    [   38.469138] cnss[2]: INFO: per device BDF location : 0x4b0e0000
    [   38.469184] cnss[2]: INFO: CALDATA IPQ8074/caldata.bin size 131072 offset 0x20000
    [   38.535902] wlan: [3998:I:ANY] ol_ath_wifi_ssr: ol_ath_wifi_ssr: SSR event 3 bus_type 1
    [   38.543504] cnss[2]: INFO: Waiting for FW ready. Device: 0xfffe, FW ready timeout: 15 seconds
    [   38.552024] cnss[2]: INFO: FW ready received for device 0xfffe
    [   38.560680] wlan: [3998:I:ANY] pld_ahb_wlan_enable: cnss_mode: Mission mode 
    [   38.566055] cnss[2]: INFO: Sending mode message, mode: MISSION(0), state: 0x7
    [   38.583139] wlan: [3998:I:ANY] qca_napi_create: qca_napi_create: napi instance 0 created on pipe 4
    [   38.583446] wlan: [3998:I:ANY] __ol_ath_attach: Allocated soc ffffffc00ed00880
    [   38.591267] wlan: [3998:D:dfs] WLAN_DEBUG_DFS1 : dfs_psoc_obj_create_notification: DFS obj attach to psoc successfully
    [   38.598729] wlan: [3998:I:ANY] osif_nss_wifi_soc_setup: nss-wifili:#1 register wifili function for soc 
    [   38.609008] wlan: [3998:I:ANY] osif_nss_wifi_soc_setup: nss register id -1 nss config 3 Target Type 18 
    [   38.618335] wlan: [3998:I:ANY] __ol_ath_attach: dev name soc0
    [   38.627994] wlan: [3998:I:ANY] ol_ath_soc_attach: WMI attached. wmi_handle ffffffc0041e3400 
    [   38.636739] wlan: [3998:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   38.642456] wlan: [3998:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   38.652024] wlan: [3998:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   38.661947] wlan: [3998:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   38.671986] wlan: [3998:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   38.682120] wlan: [3998:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   38.692140] wlan: [3998:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   38.702177] wlan: [3998:I:MBSSIE] ol_ath_sanitize_ema_vendor_ie_config: vendor_ie_size: 0 ven_ie_size_nibble: 3
    [   38.712274] wlan: [3998:I:ANY] htc_wmi_init: HT Create . ffffffc004702000
    [   38.722311] wlan: [3998:I:ANY] htc_wmi_init: Skipping BMI Done
    [   38.729242] wlan: [3998:I:ANY] htc_wmi_init: host_enable 0 nss_nwifi_offload 0
    [   38.741005] wlan: [3998:I:ANY] ol_target_init_complete: CDP soc attach success
    [   38.742112] wlan: [3998:I:ANY] ol_target_init_complete: Soc attach success NSS config 0 
    [   38.749711] wlan: [3998:I:ANY] htc_set_async_ep: htc_set_async_ep: htc_handle ffffffc004702000, ep 2, value 1
    [   38.757916] wlan: [3998:I:ANY] htc_set_async_ep: htc_set_async_ep: htc_handle ffffffc004702000, ep 3, value 1
    [   38.767904] wlan: [1775:I:TIF] HE_CAP Info = 9a18010d
    [   38.777622] wlan: [1775:I:TIF] Num HW modes = 1
    [   38.782322] wlan: [1775:I:TIF] Num PHY = 2
    [   38.786774] wlan: [1775:I:TIF] FW Build Version (Ext.) = 0
    [   38.790841] wlan: [1775:I:TIF] HDL Version: MajorVersion.MinorVersion = 0.0
    [   38.796432] wlan: [1775:I:TIF] Preferred HW Mode = 1 Num Radios = 2
    [   38.803227] wlan: [1775:I:TIF] init_deinit_add_11ax_modes: hw_mode_id = 1 phy_id = 0 wireless modes = f97f9001
    [   38.809587] wlan: [1775:I:TIF] init_deinit_add_11ax_modes: hw_mode_id = 1 phy_id = 1 wireless modes = 680688c
    [   38.820814] wlan: [1775:I:TIF] init_deinit_alloc_pdevs: CDP PDEV ATTACH success
    [   38.830755] wlan: [1775:I:TIF] init_deinit_alloc_pdevs: CDP PDEV ATTACH success
    [   38.836775] wlan: [1775:I:TIF] init_deinit_get_total_num_ema_vaps: num_radios: 2
    [   38.843893] wlan: [1775:I:TIF] init_deinit_get_total_num_ema_vaps: ema_max_vap_cnt: 0
    [   38.851788] wlan: [1775:I:TIF] init_deinit_get_total_num_vdevs_for_soc: num_vdevs: 18
    [   38.859344] wlan: [1775:I:TIF] init_deinit_get_total_num_ema_vaps: num_radios: 2
    [   38.867127] wlan: [1775:I:TIF] init_deinit_get_total_num_ema_vaps: ema_max_vap_cnt: 0
    [   38.874637] wlan: [1775:I:TIF] init_deinit_get_total_num_vdevs_for_soc: num_vdevs: 18
    [   38.882250] wlan: [1775:I:TIF] init_deinit_get_total_beaconing_vdevs_for_soc: beacon_tx_offload_max_vdev: 18
    [   38.890085] wlan: [1775:I:TIF] init_deinit_get_total_num_ema_vaps: num_radios: 2
    [   38.900011] wlan: [1775:I:TIF] init_deinit_get_total_num_ema_vaps: ema_max_vap_cnt: 0
    [   38.907387] wlan: [1775:I:TIF] init_deinit_get_total_num_vdevs_for_soc: num_vdevs: 18
    [   38.915056] wlan: [1775:I:TIF] init_deinit_get_total_num_ema_vaps: num_radios: 1
    [   38.922865] wlan: [1775:I:TIF] init_deinit_get_total_num_ema_vaps: ema_max_vap_cnt: 0
    [   38.930359] wlan: [1775:I:TIF] init_deinit_get_total_num_vdevs_for_soc: num_vdevs: 9
    [   38.938061] wlan: [1775:I:ANY] init_deinit_update_pdev_tgt_info: pdev id:0 wmi_handle:ffffffc0041e3400
    [   38.946234] wlan: [1775:F:DP] dp_rx_enable_mon_dest_frag: Feature DP_RX_MON_MEM_FRAG for mon_dest is enabled
    [   38.956177] wlan: [1775:I:ANY] init_deinit_update_pdev_tgt_info: Pdev = 0 Number of peers = 137 vdevs = 9
    [   38.965004] wlan: [1775:I:TIF] init_deinit_update_pdev_tgt_info: CDP PDEV INIT success
    [   38.974662] wlan: [1775:I:ANY] init_deinit_update_pdev_tgt_info: pdev id:1 wmi_handle:ffffffc01cd38000
    [   38.982591] wlan: [1775:F:DP] dp_rx_enable_mon_dest_frag: Feature DP_RX_MON_MEM_FRAG for mon_dest is enabled
    [   38.992695] wlan: [1775:I:ANY] init_deinit_update_pdev_tgt_info: Pdev = 1 Number of peers = 137 vdevs = 9
    [   39.001583] wlan: [1775:I:TIF] init_deinit_update_pdev_tgt_info: CDP PDEV INIT success
    [   39.111480] wlan: [1775:I:ANY] copy_fw_abi_version_tlv: copy_fw_abi_version_tlv: INIT_CMD version: 1, 0, 0x5f414351, 0x4c4d, 0x0, 0x0
    [   39.230544] wlan: [1775:I:ANY] ready_extract_init_status_tlv: ready_extract_init_status_tlv:0
    [   39.230580] wlan: [1775:I:ANY] dp_peer_map_attach_wifi3: dp_peer_map_attach_wifi3 max_peers 309, max_ast_index: 1040
    [   39.230580] 
    [   39.238174] wlan: [3998:I:ANY] ol_ath_connect_htc: WMI is ready
    [   39.265301] wlan: [3998:I:ANY] ath_get_radio_index: Error: Could not match the device name : wifi%d
    [   39.265334] wlan: [3998:E:NSS] [nss-wifili]: pdev:ffffffc00dc20880 radio_ifnum:29 scheme_id:0 radio_priority:1 
    [   39.277727] wlan: [3998:E:TIF] target_if_lro_hash_config: pdev with id 0 is NULL
    [   39.283306] wlan: [3998:I:ANY] ath_get_radio_index: Error: Could not match the device name : wifi%d
    [   39.290875] wlan: [3998:E:NSS] [nss-wifili]: pdev:ffffffc0080a0880 radio_ifnum:30 scheme_id:1 radio_priority:0 
    [   39.304102] wlan: [3998:E:TIF] target_if_lro_hash_config: pdev with id 1 is NULL
    [   39.310030] wlan: [3998:I:ANY] ol_ath_soc_attach: connect HTC
    [   39.317337] wlan: [3998:I:ANY] ol_ath_soc_attach: bypasswmi : 0
    [   39.322986] wlan: [3998:I:MSCS] qca_mscs_module_init: 
    [   39.322986] ****QCA MSCS Initialization Done**** SoC ffffffc00ed00880
    [   39.328717] wlan: [3998:I:ANY] ol_ath_soc_attach: UMAC attach
    [   39.340577] wlan: [3998:I:ANY] __ol_ath_attach: pdev_netdev name wifi0
    [   39.346219] wlan: [3998:I:ANY] __ol_ath_attach: Skip txrx_pdev_attach_target
    [   39.352571] wlan: [3998:I:ANY] __ol_ath_attach: BURSTING enabled by default
    [   39.359847] wlan: [3998:I:ANY] ol_ath_pdev_attach: interface_id 0
    [   39.366472] wlan: [3998:I:TIF] ol_ath_pdev_regdmn_init:  phy id = 0 Modes supported
    [   39.372712] wlan: [3998:I:TIF] ol_ath_pdev_regdmn_init:  11b = 0 11g = 0 11a = 1 11n = 1 11ac = 1 11ax = 1
    [   39.380188] wlan: [3998:I:TIF] ol_ath_pdev_regdmn_init:  Reg cap - phy_id = 0 supp_bnd = 2, modes = f97f9001, lo_2g = 0, hi_2g = 0 lo_g5 = 4900, hi_5g = 5920
    [   39.389917] wlan: [3998:I:ANY] ol_ath_update_wireless_modes: wireless_modes = f97f9001 before update
    [   39.404057] wlan: [3998:I:ANY] ol_ath_update_wireless_modes: Wireless_modes = f97f9001 after update
    [   39.413268] wlan: [3998:I:ANY] ol_ath_update_ext_caps: 11ax 5G supported case
    [   39.422104] wlan: [3998:I:MBSSIE] ol_ath_assign_mbssid_ref_bssid: MBSSID reference bssid is 02:03:7f:12:d2:e7 soc: soc0 pdev: wifi0
    [   39.429404] wlan: [3998:I:MBSSIE] ieee80211_mbss_attach: :>
    [   39.440943] wlan: [3998:I:MBSSIE] ieee80211_mbss_attach: :<
    [   39.446499] wlan: [3998:I:ANY] ol_resmgr_create: OL Resmgr Init-ed
    [   39.452233] wlan: [3998:I:ANY] acfg_attach: acfg_attach: 3290: Netlink socket created:ffffffc012446800
    [   39.458371] wlan: [3998:I:ANY] ol_ath_stats_attach: periodic_chan_stats: 1
    [   39.468680] wlan: [3998:I:ANY] wlan_scan_update_channel_list: num_chan: 25
    [   39.474543] wlan: [0:I:ANY] ol_ath_pdev_attach: Set global_ic[1], ptr:ffffffbffda10fe0
    [   39.481313] wlan: [0:I:ANY] dp_lag_soc_enable: pdev(ffffffc01cd3a808) Enabling DBDC Repeater 0  soc_lag ffffffc013368c80
    [   39.489266] wlan: [0:I:ANY] dp_lag_pdev_set_primary_radio: pdev(ffffffc01cd3a808) is_primary 0 
    [   39.489328] wlan: [0:E:NSS] [nss-wifili]: NSS Wifili DBDC Repeater enable message passed
    [   39.508902] wlan: [0:I:ANY] ol_ath_twt_enable_complete_event_handler: twt enabled
    [   39.510880] wlan: [3998:I:ANY] ol_ath_ucfg_set_rx_pkt_protocol_tagging: Set RX packet type TAG, opcode : 0, pkt_type : 18, metadata : 0xca0,pdev_id = 0, REO dest ring = 5
    [   39.510880] 
    [   39.510911] wlan: [3998:I:ANY] ol_ath_pri20_cfg_blockchanlist_parse: cfg block channel list is empty
    [   39.510925] wlan: [3998:I:ANY] ol_ath_configure_cong_ctrl_max_msdus: pdev_idx = 0 tx_desc_limit = 8192
    [   39.510943] wlan: [3998:I:ANY] osif_wrap_attach: osif wrap attached
    [   39.510943] 
    [   39.510945] wlan: [3998:I:ANY] osif_wrap_devt_init: osif wrap dev table init done
    [   39.510945] 
    [   39.510949] wlan: [3998:I:ANY] osif_wrap_attach:  Wrap Attached: Wrap_com =ffffffc0126d6c00 ic->ic_wrap_com=ffffffc0126d6c00 &wrap_com->wc_devt=ffffffc0126d6c00 
    [   39.510949] 
    [   39.510975] wlan: [3998:I:ANY] __ol_ath_attach: needed_headroom reservation 60
    [   39.510978] wlan: [3998:I:ANY] ol_ath_enable_fraglist: Enabled Fraglist bit for the radio wifi0 features 41 
    [   39.511196] wlan: [3998:I:ANY] ieee80211_cfg80211_radio_attach: ic: 0xffffffc00dc20880, wdev: 0xffffffc00dc38ad0, wiphy: 0xffffffc0058882a0, netdev: 0xffffffc00dc20000 
    [   39.511881] wlan: [3998:I:ANY] __ol_ath_attach: pdev_netdev name wifi1
    [   39.511896] wlan: [3998:I:ANY] __ol_ath_attach: Skip txrx_pdev_attach_target
    [   39.511900] wlan: [3998:I:ANY] __ol_ath_attach: BURSTING enabled by default
    [   39.511943] wlan: [3998:I:ANY] ol_ath_pdev_attach: interface_id 1
    [   39.511954] wlan: [3998:I:TIF] ol_ath_pdev_regdmn_init:  phy id = 1 Modes supported
    [   39.511957] wlan: [3998:I:TIF] ol_ath_pdev_regdmn_init:  11b = 1 11g = 1 11a = 0 11n = 1 11ac = 1 11ax = 1
    [   39.511961] wlan: [3998:I:TIF] ol_ath_pdev_regdmn_init:  Reg cap - phy_id = 1 supp_bnd = 1, modes = 680680c, lo_2g = 2312, hi_2g = 2732 lo_g5 = 0, hi_5g = 0
    [   39.511964] wlan: [3998:I:ANY] ol_ath_update_wireless_modes: wireless_modes = 680680c before update
    [   39.511966] wlan: [3998:I:ANY] ol_ath_update_wireless_modes: Wireless_modes = 680680c after update
    [   39.511971] wlan: [3998:I:ANY] ol_ath_update_ext_caps: 11ax 2G supported case
    [   39.511999] wlan: [3998:I:ANY] ol_ath_pdev_regdmn_init: LDPC not supported in 5G HE CAP
    [   39.512022] wlan: [3998:I:MBSSIE] ol_ath_assign_mbssid_ref_bssid: MBSSID reference bssid is 02:03:7f:12:86:ec soc: soc0 pdev: wifi1
    [   39.512080] wlan: [3998:I:MBSSIE] ieee80211_mbss_attach: :>
    [   39.512082] wlan: [3998:I:MBSSIE] ieee80211_mbss_attach: :<
    [   39.512086] wlan: [3998:I:ANY] ol_resmgr_create: OL Resmgr Init-ed
    [   39.512250] wlan: [3998:I:ANY] acfg_attach: Offload using existing sock ffffffc012446800
    [   39.512257] wlan: [3998:I:ANY] ol_ath_stats_attach: periodic_chan_stats: 1
    [   39.512439] wlan: [3998:I:ANY] wlan_scan_update_channel_list: num_chan: 11
    [   39.512465] wlan: [0:I:ANY] ol_ath_pdev_attach: Set global_ic[2], ptr:ffffffbffda10fe0
    [   39.512470] wlan: [0:I:ANY] dp_lag_soc_enable: pdev(ffffffc01d4dac08) Enabling DBDC Repeater 0  soc_lag ffffffc013368c80
    [   39.512499] wlan: [0:I:ANY] dp_lag_pdev_set_primary_radio: pdev(ffffffc01d4dac08) is_primary 0 
    [   39.514724] wlan: [3998:I:ANY] ol_ath_ucfg_set_rx_pkt_protocol_tagging: Set RX packet type TAG, opcode : 0, pkt_type : 18, metadata : 0xca0,pdev_id = 1, REO dest ring = 5
    [   39.514724] 
    [   39.514754] wlan: [3998:I:ANY] ol_ath_pri20_cfg_blockchanlist_parse: cfg block channel list is empty
    [   39.514759] wlan: [3998:I:ANY] ol_ath_configure_cong_ctrl_max_msdus: pdev_idx = 1 tx_desc_limit = 8192
    [   39.514776] wlan: [3998:I:ANY] osif_wrap_attach: osif wrap attached
    [   39.514776] 
    [   39.514778] wlan: [3998:I:ANY] osif_wrap_devt_init: osif wrap dev table init done
    [   39.514778] 
    [   39.514782] wlan: [3998:I:ANY] osif_wrap_attach:  Wrap Attached: Wrap_com =ffffffc014ecb800 ic->ic_wrap_com=ffffffc014ecb800 &wrap_com->wc_devt=ffffffc014ecb800 
    [   39.514782] 
    [   39.514805] wlan: [3998:I:ANY] __ol_ath_attach: needed_headroom reservation 60
    [   39.514808] wlan: [3998:I:ANY] ol_ath_enable_fraglist: Enabled Fraglist bit for the radio wifi1 features 41 
    [   39.514825] wlan: [3998:I:ANY] wlan_cfg80211_init: Number of 2G channels: 11 
    [   39.514962] wlan: [3998:I:ANY] ieee80211_cfg80211_radio_attach: ic: 0xffffffc0080a0880, wdev: 0xffffffc0080b8ad0, wiphy: 0xffffffc00588baa0, netdev: 0xffffffc0080a0000 
    [   39.515603] wlan: [3998:I:Dynamic Mode Change] ol_ath_check_and_reconfig_hw_mode: Running with HW mode = 1
    [   39.515943] wlan: [3998:E:QLD] qld_register: Handle or address is NULL
    [   39.515966] wlan: [3998:I:ANY] wlan_pdev_operation: num_radios=1, wifi_radios[0].sc = ffffffc00dc20880_radio_type = 2
    [   39.515970] wlan: [3998:I:ANY] wlan_pdev_operation: num_radios=2, wifi_radios[1].sc = ffffffc0080a0880_radio_type = 2
    [   39.515996] wlan: [3998:I:ANY] init_ath_pci_3_0: 6ath_ol_pci_wifi3.0 :  (Atheros/multi-bss)
    [   39.937611] wlan: [0:E:NSS] [nss-wifili]: NSS Wifili DBDC Repeater enable message passed
    [   39.946597] wlan: [0:I:ANY] ol_ath_twt_enable_complete_event_handler: twt enabled
    [   39.983602] wlan: [4019:I:ANY] osif_nss_register_module: NSS wifi ops registered for target_type:0 with soc_ops:ffffffbffdd84fd0
    [   39.984018] wlan: [4019:I:ANY] init_ath_pci_2_0: 6ath_ol_pci_2_0:  (Atheros/multi-bss)
    [   40.760018] wlan: [4106:I:ANY] wlan_cfg80211_set_hwaddr: wlan_cfg80211_set_hwaddr :10:71:fa:69:f0:59 ret: 0 
    [   40.777899] wlan: [4110:I:ANY] wlan_cfg80211_set_hwaddr: wlan_cfg80211_set_hwaddr :10:71:fa:69:f0:58 ret: 0 
    [   40.982621] wlan: [4165:I:ANY] wlan_cfg80211_set_hwaddr: wlan_cfg80211_set_hwaddr :10:71:fa:69:f0:59 ret: -16 
    [   40.999405] wlan: [4168:I:ANY] ol_ath_set_config_param: set TXBF_SND_PERIOD: val 100 stat 0
    [   41.052189] wlan: [0:I:ANY] ol_ath_set_config_param: Disconnect_timeout value: 10
    [   41.069865] wlan: [0:I:ANY] ol_ath_set_config_param: Reconfiguration_timeout value:60
    [   41.117727] wlan: [4200:I:ANY] wlan_cfg80211_add_virtual_intf: proprietary mode 6 for interface: ath0 : clone params: 0x00000001 
    [   41.117793] wlan: [4200:I:MBSSIE] osif_mbssid_sanity_check: mbssid_sanity_ok: YES
    [   41.128544] wlan: [4200:I:ANY] osifp_create_wlan_vap: VDEV Create 10:71:fa:69:f0:59
    [   41.135898] wlan: [4200:I:ANY] wlan_vap_create: devhandle=0xffffffc00dc20880, opmode=IEEE80211_M_HOSTAP, flags=0x1
    [   41.135898] 
    [   41.143660] wlan: [4200:I:ANY] ol_ath_vap_set_param: Setting SGI value: 1
    [   41.155283] wlan: [4200:I:ANY] ol_ath_vap_set_param: VDEV params:HE su_bfee:1|su_bfer:1|mu_bfee:0|mu_bfer:1|dl_muofdma:1|ul_muofdma:1|ul_mumimo:1|dl_muofdma_bfer:0
    [   41.162088] wlan: [4200:I:ANY] ol_ath_vap_set_param: he_bf_cap=0x7b
    [   41.176609] wlan: [4200:I:ANY] ol_ath_vap_set_param: VDEV params: AC/VHT sounding mode:HE|SU/MU sounding mode:SU|Trig/Non-Trig sounding mode:Non-Trigged
    [   41.182774] wlan: [4200:I:ANY] MBO Initialized
    [   41.196723] wlan: [4200:I:ANY] OCE Initialized
    [   41.200885] wlan: [4200:I:ANY] osif_nss_ol_vap_create: NSS wifi offload VAP create IF 31 nss_id -1 
    [   41.205292] wlan: [4200:I:ANY] NSS radio_if 29
    [   41.214539] wlan: [0:I:ANY] osif_nss_vdev_cfg_callback: VDEV configuration success: 0
    [   41.218743] wlan: [4200:I:ANY] osif_nss_ol_vap_create: vap create ffffffc00dc18880 : if_num 31 
    [   41.226728] wlan: [4200:F:DP] dp_vdev_register_tx_handler: Configure tx_vdev_id_chk_handler Feature Flag: 0 and mode:1 for vdev_id:0
    [   41.235170] wlan: [4200:E:ANY] wlan_create_attach_vdev_rawsim_ctxt: simulation module not registerd
    [   41.264238] wlan: [4200:I:ANY] osif_create_vap_complete: TX Checksum:1|SG:1|TSO:1|LRO:0
    [   41.264264] wlan: [4200:I:ANY] WLAN-NSS: VAP NSS ops initialized 
    [   41.272551] wlan: [4200:I:ANY] VAP device ath0 created osifp: (ffffffc00dc18880) os_if: (ffffffc001768000)
    [   41.552490] wlan: [4255:I:ANY] wlan_cfg80211_add_virtual_intf: proprietary mode 6 for interface: ath01 : clone params: 0x00000001 
    [   41.552555] wlan: [4255:I:MBSSIE] osif_mbssid_sanity_check: mbssid_sanity_ok: YES
    [   41.563233] wlan: [4255:I:ANY] osifp_create_wlan_vap: VDEV Create 16:71:fa:69:f0:59
    [   41.570785] wlan: [4255:I:ANY] wlan_vap_create: devhandle=0xffffffc00dc20880, opmode=IEEE80211_M_HOSTAP, flags=0x1
    [   41.570785] 
    [   41.578517] wlan: [4255:I:ANY] ol_ath_vap_set_param: Setting SGI value: 1
    [   41.590074] wlan: [4255:I:ANY] ol_ath_vap_set_param: VDEV params:HE su_bfee:1|su_bfer:1|mu_bfee:0|mu_bfer:1|dl_muofdma:1|ul_muofdma:1|ul_mumimo:1|dl_muofdma_bfer:0
    [   41.597009] wlan: [4255:I:ANY] ol_ath_vap_set_param: he_bf_cap=0x7b
    [   41.611523] wlan: [4255:I:ANY] ol_ath_vap_set_param: VDEV params: AC/VHT sounding mode:HE|SU/MU sounding mode:SU|Trig/Non-Trig sounding mode:Non-Trigged
    [   41.617644] wlan: [4255:I:ANY] MBO Initialized
    [   41.631525] wlan: [4255:I:ANY] OCE Initialized
    [   41.635777] wlan: [4255:I:ANY] osif_nss_ol_vap_create: NSS wifi offload VAP create IF 32 nss_id -1 
    [   41.640181] wlan: [4255:I:ANY] NSS radio_if 29
    [   41.649278] wlan: [0:I:ANY] osif_nss_vdev_cfg_callback: VDEV configuration success: 0
    [   41.653605] wlan: [4255:I:ANY] osif_nss_ol_vap_create: vap create ffffffc00ef06880 : if_num 32 
    [   41.661549] wlan: [4255:F:DP] dp_vdev_register_tx_handler: Configure tx_vdev_id_chk_handler Feature Flag: 0 and mode:1 for vdev_id:1
    [   41.670034] wlan: [4255:E:ANY] wlan_create_attach_vdev_rawsim_ctxt: simulation module not registerd
    [   41.694246] wlan: [4255:I:ANY] osif_create_vap_complete: TX Checksum:1|SG:1|TSO:1|LRO:0
    [   41.694276] wlan: [4255:I:ANY] WLAN-NSS: VAP NSS ops initialized 
    [   41.702703] wlan: [4255:I:ANY] VAP device ath01 created osifp: (ffffffc00ef06880) os_if: (ffffffc00ebf8000)
    [   42.077197] wlan: [4331:I:ANY] wlan_cfg80211_set_hwaddr: wlan_cfg80211_set_hwaddr :10:71:fa:69:f0:58 ret: -16 
    [   42.093913] wlan: [4334:I:ANY] ol_ath_set_config_param: set TXBF_SND_PERIOD: val 100 stat 0
    [   42.143941] wlan: [0:I:ANY] ol_ath_set_config_param: Disconnect_timeout value: 10
    [   42.160849] wlan: [0:I:ANY] ol_ath_set_config_param: Reconfiguration_timeout value:60
    [   42.206806] wlan: [4365:I:ANY] wlan_cfg80211_add_virtual_intf: proprietary mode 6 for interface: ath1 : clone params: 0x00000001 
    [   42.206872] wlan: [4365:I:MBSSIE] osif_mbssid_sanity_check: mbssid_sanity_ok: YES
    [   42.217502] wlan: [4365:I:ANY] osifp_create_wlan_vap: VDEV Create 10:71:fa:69:f0:58
    [   42.224961] wlan: [4365:I:ANY] wlan_vap_create: devhandle=0xffffffc0080a0880, opmode=IEEE80211_M_HOSTAP, flags=0x1
    [   42.224961] 
    [   42.232643] wlan: [4365:I:ANY] ol_ath_vap_set_param: Setting SGI value: 1
    [   42.244327] wlan: [4365:I:ANY] ol_ath_vap_set_param: VDEV params:HE su_bfee:1|su_bfer:1|mu_bfee:0|mu_bfer:1|dl_muofdma:1|ul_muofdma:1|ul_mumimo:1|dl_muofdma_bfer:0
    [   42.251137] wlan: [4365:I:ANY] ol_ath_vap_set_param: he_bf_cap=0x7b
    [   42.265632] wlan: [4365:I:ANY] ol_ath_vap_set_param: VDEV params: AC/VHT sounding mode:HE|SU/MU sounding mode:SU|Trig/Non-Trig sounding mode:Non-Trigged
    [   42.271835] wlan: [4365:I:ANY] MBO Initialized
    [   42.285674] wlan: [4365:I:ANY] OCE Initialized
    [   42.289927] wlan: [4365:I:ANY] osif_nss_ol_vap_create: NSS wifi offload VAP create IF 33 nss_id -1 
    [   42.294374] wlan: [4365:I:ANY] NSS radio_if 30
    [   42.303388] wlan: [0:I:ANY] osif_nss_vdev_cfg_callback: VDEV configuration success: 0
    [   42.307808] wlan: [4365:I:ANY] osif_nss_ol_vap_create: vap create ffffffc010a6a880 : if_num 33 
    [   42.315729] wlan: [4365:F:DP] dp_vdev_register_tx_handler: Configure tx_vdev_id_chk_handler Feature Flag: 0 and mode:1 for vdev_id:2
    [   42.324238] wlan: [4365:E:ANY] wlan_create_attach_vdev_rawsim_ctxt: simulation module not registerd
    [   42.354273] wlan: [4365:I:ANY] osif_create_vap_complete: TX Checksum:1|SG:1|TSO:1|LRO:0
    [   42.354306] wlan: [4365:I:ANY] WLAN-NSS: VAP NSS ops initialized 
    [   42.362092] wlan: [4365:I:ANY] VAP device ath1 created osifp: (ffffffc010a6a880) os_if: (ffffffc01192c000)
    [   42.616210] wlan: [4405:W:ANY] wlan_get_wlan_band_id_chan_to_freq: Invalid freq: 0, wlan_band: 0, reg_wifi_band: 3, chan: 12
    [   42.616249] wlan: [4405:F:ANY] ieee80211dbg_ioctl_acs_block_channel: ieee80211dbg_ioctl_acs_block_channel Invalid input chan: 12, band: 0
    [   42.616249] 
    [   42.656393] wlan: [4425:I:ANY] wlan_cfg80211_add_virtual_intf: proprietary mode 6 for interface: ath11 : clone params: 0x00000001 
    [   42.656456] wlan: [4425:I:MBSSIE] osif_mbssid_sanity_check: mbssid_sanity_ok: YES
    [   42.667485] wlan: [4425:I:ANY] osifp_create_wlan_vap: VDEV Create 16:71:fa:69:f0:58
    [   42.674876] wlan: [4425:I:ANY] wlan_vap_create: devhandle=0xffffffc0080a0880, opmode=IEEE80211_M_HOSTAP, flags=0x1
    [   42.674876] 
    [   42.683091] wlan: [4425:I:ANY] ol_ath_vap_set_param: Setting SGI value: 1
    [   42.694329] wlan: [4425:I:ANY] ol_ath_vap_set_param: VDEV params:HE su_bfee:1|su_bfer:1|mu_bfee:0|mu_bfer:1|dl_muofdma:1|ul_muofdma:1|ul_mumimo:1|dl_muofdma_bfer:0
    [   42.700822] wlan: [4425:I:ANY] ol_ath_vap_set_param: he_bf_cap=0x7b
    [   42.715308] wlan: [4425:I:ANY] ol_ath_vap_set_param: VDEV params: AC/VHT sounding mode:HE|SU/MU sounding mode:SU|Trig/Non-Trig sounding mode:Non-Trigged
    [   42.721515] wlan: [4425:I:ANY] MBO Initialized
    [   42.735498] wlan: [4425:I:ANY] OCE Initialized
    [   42.739608] wlan: [4425:I:ANY] osif_nss_ol_vap_create: NSS wifi offload VAP create IF 34 nss_id -1 
    [   42.744026] wlan: [4425:I:ANY] NSS radio_if 30
    [   42.753096] wlan: [0:I:ANY] osif_nss_vdev_cfg_callback: VDEV configuration success: 0
    [   42.757485] wlan: [4425:I:ANY] osif_nss_ol_vap_create: vap create ffffffc010a46880 : if_num 34 
    [   42.765434] wlan: [4425:F:DP] dp_vdev_register_tx_handler: Configure tx_vdev_id_chk_handler Feature Flag: 0 and mode:1 for vdev_id:3
    [   42.773898] wlan: [4425:E:ANY] wlan_create_attach_vdev_rawsim_ctxt: simulation module not registerd
    [   42.804257] wlan: [4425:I:ANY] osif_create_vap_complete: TX Checksum:1|SG:1|TSO:1|LRO:0
    [   42.804289] wlan: [4425:I:ANY] WLAN-NSS: VAP NSS ops initialized 
    [   42.812080] wlan: [4425:I:ANY] VAP device ath11 created osifp: (ffffffc010a46880) os_if: (ffffffc00ebd0000)
    [   43.064895] wlan: [4465:W:ANY] wlan_get_wlan_band_id_chan_to_freq: Invalid freq: 0, wlan_band: 0, reg_wifi_band: 3, chan: 12
    [   43.064935] wlan: [4465:F:ANY] ieee80211dbg_ioctl_acs_block_channel: ieee80211dbg_ioctl_acs_block_channel Invalid input chan: 12, band: 0
    [   43.064935] 
    [   43.179772] wlan: [4498:I:ANY] wlan_scan_update_channel_list: num_chan: 19
    [   43.180884] wlan: [4498:I:ANY] wlan_scan_update_channel_list: num_chan: 19
    [   43.185798] wlan: [4498:I:ANY] ieee80211_setctry_tryretaining_curchan: [431] Skipping current channel retention during set_country operation
    [   43.192452] wlan: [4498:I:ANY] number of channels: 2G = 0 5G = 19, 6G = 0
    [   43.226590] wlan: [4501:I:ANY] wlan_scan_update_channel_list: num_chan: 19
    [   43.227062] wlan: [4501:I:ANY] number of channels: 2G = 0 5G = 19, 6G = 0
    [   43.233045] wlan: [4501:I:ANY] wlan_scan_update_channel_list: num_chan: 19
    [   43.261132] wlan: [4504:I:ANY] wlan_scan_update_channel_list: num_chan: 20
    [   43.261261] wlan: [4504:I:ANY] number of channels: 2G = 0 5G = 20, 6G = 0
    [   44.353411] wlan: [4534:I:ANY] wlan_scan_update_channel_list: num_chan: 19
    [   44.353543] wlan: [4534:I:ANY] number of channels: 2G = 0 5G = 19, 6G = 0
    [   44.388910] wlan: [0:D:dfs] WLAN_DEBUG_DFS_AGILE : dfs_agile_sm_print_state_event: [DFS_AGILE]INIT, EV_AGILE_STOP
    [   44.388951] wlan: [0:D:dfs] WLAN_DEBUG_DFS_AGILE : dfs_agile_sm_print_state_event: [DFS_AGILE]INIT, EV_AGILE_START
    [   44.398177] wlan: [0:I:ANY] dfs_set_agilecac_chan_for_freq: Cannot start Agile CAC as a valid agile channel width could not be found
    [   44.398177] 
    [   44.447414] wlan: [4549:I:ANY] wlan_scan_update_channel_list: num_chan: 13
    [   44.447503] wlan: [4549:I:ANY] ieee80211_setctry_tryretaining_curchan: [431] Skipping current channel retention during set_country operation
    [   44.453204] wlan: [4549:I:ANY] number of channels: 2G = 13 5G = 0, 6G = 0
    [   44.634583] wlan: [4586:I:ANY] ol_ath_vap_set_param: Setting SGI value: 1
    [   44.865550] wlan: [4621:E:ANY] ieee80211_ucfg_setparam: Invalid value
    [   44.896984] 8021q: adding VLAN 0 to HW filter on device ath0
    [   44.944764] wlan: [1455:I:ANY] wlan_cfg80211_do_acs: vap-0(ath0):ACS Params
    [   44.944793] wlan: [1455:I:ANY] wlan_cfg80211_do_acs: ht_enabled:1|ht40_enabled:0|vht_enabled:1|hw_mode:31|chwidth:20|
    [   44.950611] wlan: [1455:I:ANY] ieee80211_autoselect_infra_bss_channel: ACS started: vap:0xffffffc001768000
    [   44.962971] wlan: [1455:I:ANY] ACS channel list: 
    [   44.971039] wlan: [1455:I:ANY] [36] <---> [5180]
    [   44.975688] wlan: [1455:I:ANY] [40] <---> [5200]
    [   44.980306] wlan: [1455:I:ANY] [44] <---> [5220]
    [   44.985008] wlan: [1455:I:ANY] [48] <---> [5240]
    [   44.989513] wlan: [1455:I:ANY] [52] <---> [5260]
    [   44.994104] wlan: [1455:I:ANY] [56] <---> [5280]
    [   44.998841] wlan: [1455:I:ANY] [60] <---> [5300]
    [   45.003307] wlan: [1455:I:ANY] [64] <---> [5320]
    [   45.008011] wlan: [1455:I:ANY] [100] <---> [5500]
    [   45.012509] wlan: [1455:I:ANY] [104] <---> [5520]
    [   45.017206] wlan: [1455:I:ANY] [108] <---> [5540]
    [   45.021806] wlan: [1455:I:ANY] [112] <---> [5560]
    [   45.026613] wlan: [1455:I:ANY] [116] <---> [5580]
    [   45.031174] wlan: [1455:I:ANY] [120] <---> [5600]
    [   45.035957] wlan: [1455:I:ANY] [124] <---> [5620]
    [   45.040547] wlan: [1455:I:ANY] [128] <---> [5640]
    [   45.097083] device ath0 entered promiscuous mode
    [   45.097404] bridge0: port 3(ath0) entered forwarding state
    [   45.100817] bridge0: port 3(ath0) entered forwarding state
    [   45.172087] wlan: [4665:I:ANY] ol_ath_vap_set_param: Setting SGI value: 1
    [   45.438745] 8021q: adding VLAN 0 to HW filter on device ath1
    [   45.504783] wlan: [1455:I:ANY] wlan_cfg80211_do_acs: vap-2(ath1):ACS Params
    [   45.504817] wlan: [1455:I:ANY] wlan_cfg80211_do_acs: ht_enabled:1|ht40_enabled:0|vht_enabled:1|hw_mode:29|chwidth:20|
    [   45.510562] wlan: [1455:I:ANY] ieee80211_autoselect_infra_bss_channel: ACS started: vap:0xffffffc01192c000
    [   45.521392] wlan: [1455:I:ANY] ACS channel list: 
    [   45.530894] wlan: [1455:I:ANY] [1] <---> [2412]
    [   45.535642] wlan: [1455:I:ANY] [2] <---> [2417]
    [   45.539977] wlan: [1455:I:ANY] [3] <---> [2422]
    [   45.544498] wlan: [1455:I:ANY] [4] <---> [2427]
    [   45.549005] wlan: [1455:I:ANY] [5] <---> [2432]
    [   45.553517] wlan: [1455:I:ANY] [5] <---> [2432]
    [   45.558039] wlan: [1455:I:ANY] [6] <---> [2437]
    [   45.562551] wlan: [1455:I:ANY] [6] <---> [2437]
    [   45.567067] wlan: [1455:I:ANY] [7] <---> [2442]
    [   45.571574] wlan: [1455:I:ANY] [7] <---> [2442]
    [   45.576106] wlan: [1455:I:ANY] [8] <---> [2447]
    [   45.580602] wlan: [1455:I:ANY] [8] <---> [2447]
    [   45.585124] wlan: [1455:I:ANY] [9] <---> [2452]
    [   45.589635] wlan: [1455:I:ANY] [9] <---> [2452]
    [   45.594143] wlan: [1455:I:ANY] [10] <---> [2457]
    [   45.598663] wlan: [1455:I:ANY] [11] <---> [2462]
    [   45.821425] wlan: [4765:I:ANY] ol_ath_ucfg_setparam: set acs_nf_threshold to -85 
    [   45.821425] 
    [   45.827942] wlan: [4767:I:ANY] ol_ath_ucfg_setparam: set acs_nf_threshold to -85 
    [   45.827942] 
    [   46.185847] device ath1 entered promiscuous mode
    [   46.186093] bridge0: port 4(ath1) entered forwarding state
    [   46.189546] bridge0: port 4(ath1) entered forwarding state
    [   49.613784] wlan: [3995:I:ANY] vap-2(ath1): ACS result PCH 2 freq 2417, SCH 6 freq 2437, hw_mode 1 chwidth 40, vht_seg0 4 freq 2427, vht_seg1 0 freq 0
    [   49.613843] wlan: [3995:I:ANY] ieee80211_acs_scan_evhandler: lock held duration: 0(ms)
    [   49.638794] wlan: [1455:I:ANY] DES SSID SET=1071FA69F05B-2G
    [   49.638821] wlan: [1455:I:ANY] desired hw mode: 29
    [   49.643270] wlan: [1455:I:ANY] ieee80211_ucfg_set_freq_internal: 
    [   49.643270]  Channel is configured already!!
    [   49.648413] wlan: [1455:E:MBSSIE] ieee80211_ucfg_set_txvap: MBSSID is not enabled
    [   49.659595] wlan: [1455:I:ANY] [ASSOC] vap-2(ath1):ieee80211_try_mark_node_for_delayed_cleanup: ni: 0xffffffc00ebda000, mac: 10:71:fa:69:f0:58, marked:0, vapid: 2
    [   49.659595] 
    [   49.667585] wlan: [1455:I:ANY] [ASSOC] vap-2(ath1):ieee80211_try_mark_node_for_delayed_cleanup: ni: 0xffffffc00ebda000, mac: 10:71:fa:69:f0:58, marked:0, vapid: 2
    [   49.667585] 
    [   49.819570] wlan: [0:I:ANY] [ASSOC] vap-2(ath1):ieee80211_mlme_frame_complete_handler: frame 192 send to ff:ff:ff:ff:ff:ff, delayed_clean: 0, leve_ongoing: 0
    [   49.819570] 
    [   49.820497] wlan: [0:I:ANY] [ASSOC] vap-2(ath1):ieee80211_mlme_frame_complete_handler: frame 192 send to ff:ff:ff:ff:ff:ff, delayed_clean: 0, leve_ongoing: 0
    [   49.820497] 
    [   50.564240] bridge0: port 1(eth0) entered forwarding state


    --------------------------------------------------------------------
    ---------------------------Welcome To Cli---------------------------
    --SBAir5, CKB01_11.B.003_293_202308021758, 10:71:FA:69:F0:5B--
    --------------------------------------------------------------------
    Login: [   50.940528] wlan: [3995:I:ANY] vap-0(ath0): ACS result PCH 128 freq 5640, SCH 108 freq 5540, hw_mode 2 chwidth 160, vht_seg0 114 freq 5570, vht_seg1 0 freq 0
    [   50.940589] wlan: [3995:I:ANY] ieee80211_acs_scan_evhandler: lock held duration: 0(ms)
    [   50.963307] wlan: [1455:I:ANY] DES SSID SET=1071FA69F05B-5G
    [   50.963335] wlan: [1455:I:ANY] desired hw mode: 31
    [   50.967952] wlan: [1455:I:ANY] ieee80211_ucfg_set_freq_internal: 
    [   50.967952]  Channel is configured already!!
    [   50.972694] wlan: [1455:E:MBSSIE] ieee80211_ucfg_set_txvap: MBSSID is not enabled
    [   50.983182] wlan: [0:D:dfs] WLAN_DEBUG_DFS_AGILE : dfs_agile_sm_print_state_event: [DFS_AGILE]INIT, EV_AGILE_STOP
    [   50.990938] wlan: [1455:I:ANY] [ASSOC] vap-0(ath0):ieee80211_try_mark_node_for_delayed_cleanup: ni: 0xffffffc00ea11000, mac: 10:71:fa:69:f0:59, marked:0, vapid: 0
    [   50.990938] 
    [   51.002127] wlan: [1455:I:ANY] [ASSOC] vap-0(ath0):ieee80211_try_mark_node_for_delayed_cleanup: ni: 0xffffffc00ea11000, mac: 10:71:fa:69:f0:59, marked:0, vapid: 0
    [   51.002127] 
    [   51.017591] wlan: [0:D:dfs] WLAN_DEBUG_DFS_AGILE : dfs_agile_sm_print_state_event: [DFS_AGILE]INIT, EV_AGILE_START
    [   51.032471] wlan: [0:I:ANY] dfs_set_agilecac_chan_for_freq: Cannot start Agile CAC as a valid agile channel width could not be found
    [   51.032471] 
    Mode Switch:LTE Only mode attached flag = <FALSE>
    [   53.179922] wlan: [0:I:ANY] [ASSOC] vap-0(ath0):ieee80211_mlme_frame_complete_handler: frame 192 send to ff:ff:ff:ff:ff:ff, delayed_clean: 0, leve_ongoing: 0
    [   53.179922] 
    [   53.180018] wlan: [0:I:ANY] [ASSOC] vap-0(ath0):ieee80211_mlme_frame_complete_handler: frame 192 send to ff:ff:ff:ff:ff:ff, delayed_clean: 0, leve_ongoing: 0
    [   53.180018] 
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 1
    [   60.124225] bridge0: port 3(ath0) entered forwarding state
    [   61.204225] bridge0: port 4(ath1) entered forwarding state
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 2
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 3
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 4
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 5
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 6
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 7
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 8
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 9
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:attach retry 10
    Mode Switch:Mode <LTE Only> Attach Fail
    Mode Switch:RSRP Check Start
    Mode Switch:5G RSRP check count 1.<-119>,<-110>
    Mode Switch:Current RSRP check count 1.<->,<-128>
    Mode Switch:wait 1 minute(s)
    Mode Switch:Current RSRP check count 2.<->,<-128>
    Mode Switch:wait 1 minute(s)
  ```

</div>

