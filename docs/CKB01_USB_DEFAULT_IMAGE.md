# CKB01 默认 USB 启动镜像 v2

`Package CKB01 default-boot USB` 是独立的打包工作流。它复用成功编译的 FIT，不下载 OpenWrt 源码、不安装编译工具链，也不运行固件编译。

## 下载和使用

下载该打包工作流的 `ckb01-usb-default-v2-<commit>` artifact 并解压。

- 镜像文件：`air5-ckb01-usb-default-v2.img`。
- 大小：256MiB（268435456 字节）。
- 写入对象：整个 U 盘设备；镜像从 LBA 0 开始就是 FAT16，不先创建分区。
- 文件系统：512 字节扇区、4096 字节簇、两份 FAT、隐藏扇区数 0。
- 根目录仅有 `uImage-initramfs.itb`，内容与成功编译的 FIT 完全相同。
- `sha256sums`、`usb-image-report.json` 和 `source-provenance.json` 记录校验与来源。

现有系统仍是 initramfs RAM root；重启后配置不持久保存。LAN1 是 DHCP WAN，LAN2 管理地址为 `192.168.5.1`。无线沿用源固件的 Air5-2G / Air5-5G、密码 `Air5-OpenWrt`，启动时读取本机 ART，校准失败时保留有线管理。网口映射、无线和本机启动均待实机验收。

## 严格对应的 U-Boot 默认路径

依据 [oldcat618/ckb01 固定提交](https://github.com/oldcat618/ckb01/tree/f989e6f5752d856c805081a1d2f6610a79372a9a) 中的 SPI 备份，已核对 U-Boot 命令表、加载分支和 FAT 分区解析。该备份的环境 CRC 有效，版本为 `U-Boot 2016.01 (Mar 06 2021 - 18:24:41 +0800)`。

```text
bootcmd=bootipq_usb
bootargs=console=ttyMSM0,115200n8
bootdelay=2
```

正常加载路径为：

```text
usb start
fatload usb 0:0 0x44000000 uImage-initramfs.itb
bootm 0x44000000
```

`0:0` 在该二进制中明确选择 USB 设备 0 的整个磁盘，并从 LBA 0 探测 FAT。本版本因此移除 MBR 和 LBA 2048 的第一分区偏移。U 盘必须成为该路径访问的 USB 设备 0。

镜像提供启动文件，不修改机器保存的 `bootargs`、`bootcmd` 或 `hook_image`，也不写入 SPI。它没有 U-Boot、第三方 ART、`uEnv.txt` 或 `boot.scr`。内核、设备树、无线包和校准助手全部沿用源 FIT。

这份备份与后期包含 `hook_image` 的 U-Boot 有差异。用户本机版本尚未读出；v2 是针对上面已分析的默认 `0:0` 路径制作的镜像，不能把打包成功写成实机启动成功。此前 MBR 版针对第一分区访问，不能与本版混用。

## 固定复用的编译成果

| 项目 | 固定值 |
|---|---|
| 编译 run | [38924263239](https://github.com/baiyunquan/Softbank-Air-5-Openwrt/actions/runs/38924263239) |
| 编译提交 | `6e6cd66997956dd5ff10e66e2c01221a93f6106c` |
| artifact ID | `12061105888` |
| artifact 名称 | `ckb01-usb-initramfs-6e6cd66997956dd5ff10e66e2c01221a93f6106c` |
| FIT SHA256 | `7279e8676979c2d075eabef01d89bfe7940716d7b75cbf6ccd7b90334d701f49` |
| 内置 initramfs SHA256 | `3b36bc2ec0997a42271f0c65e4714a2a05c86cb7642a701edd86c2239cf129d9` |

工作流检查源 run 成功、提交一致、artifact 未过期、artifact 所属 run 和摘要一致。artifact 过期时直接失败，不会自动改成重新编译。

打包时还会从现有 FIT 内提取原始 zstd initramfs，按已知摘要确认其身份，并复用现有 `ckb01-fit.py` 的只读校验：FIT 哈希、ARM64 内存范围、CKB01 DTS、无线模块、固件、BDF、校准助手和 AP 配置。不会重新生成或编辑 FIT。

完成 FAT 后执行 `fsck.fat -n`，检查 LBA 0 的 BPB、零隐藏扇区、无 MBR 条目、FAT16 簇数、根目录文件名，并从 FAT 回读 FIT 逐字节比较。

## 工作流触发

推送 `ckb01-usb-default-packaging` 分支上的本工作流、打包脚本或本文档时触发。也提供 `workflow_dispatch`，是否显示手动按钮取决于 GitHub 默认分支是否包含该工作流。

该分支不在原 `Build CKB01 USB initramfs` 工作流的编译触发分支中；本次推送只执行打包。
