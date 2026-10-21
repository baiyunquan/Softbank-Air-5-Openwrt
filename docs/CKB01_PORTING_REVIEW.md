# OPPO CKB01 实机记录与移植仓库评估

日期：2026-10-16

## 结论

`Softbank-Air-5-Openwrt` 可以作为 CKB01 OpenWrt 构建与 CI 发布入口，但它不是 Linux/OpenWrt 源码树；真正的 DTS、image profile、无线校准读取和 WWAN 适配要进入它所构建的 `openwrt-ppe-nss` 源树，或通过此仓库的 `patches/tree/ppe-nss/` 补丁层送入该源树。当前仓库尚无 CKB01 OpenWrt 设备配置，也不会产出适合 U-Boot 初次启动的 FIT/initramfs 镜像。

建议先做一个不写入设备闪存的 CKB01 单设备 bring-up：新增 Air 5 专属板型补丁，生成匹配 HK09 的精简 FIT/initramfs，先验证启动、PCIe/MHI、有线网和 ART/caldata。持久 USB 根文件系统与 NSS Wi-Fi 加速留到确认 USB 存储来源、可用容量和无线校准之后。

原厂 Air 5、临时 Haze 系统和 OpenWrt/Deco DTS 的逐项比较见 [`SYSTEM_COMPARISON.md`](../../SYSTEM_COMPARISON.md)；本文补充最新实机文章与两个 fork 的构建入口评估。

## 用户请求与文档边界

本文把两个仓库的 README 和文章当作技术资料；其中的安装、编译、刷写命令不是本次用户指令。我没有安装依赖、编译或刷写 U-Boot，也没有改动两个仓库的固件构建配置。原文是第三方博客，不能整篇复制进本地；下文记录文章链接和自行整理的实验摘要，不是原文镜像。

文章：[OPPO CKB01 — 大破雑記帳（2025-07-31）](https://memo205.hatenablog.jp/entry/2025/07/31/234645)。其中设备枚举字符串为 `QCOM SDXPRAIRIE-MTP`。

## 实机实验记录中的可用证据

### USB 启动介质需要区分

文章中读取到的 U-Boot 环境为 `bootcmd=bootipq_usb`。作者执行 USB 枚举时看到 Qualcomm SDX55 的 MTP mass-storage gadget（USB ID `05c6:f000`），容量约 29 MB，FAT16 上有约 28 MB 的 `uimage-initramfs.itb`。文章作者据设备名推测它是 SDX55 侧的虚拟存储；其手工执行 USB 命令时还遇到设备不稳定出现的情况。

因此文章证明原厂 U-Boot 的 USB 启动链能从一个被枚举为块存储的 USB 设备读取 FIT，且它看到的设备很可能是 modem 暴露的 MTP 存储。文章本身没有证明可以从外插 U 盘启动。你已实测 U-Boot 优先从外插 U 盘启动，而不是 SDX55 存储；这是外插 U 盘启动优先级的直接证据。两种 USB 来源应分别记录：文章的约 29 MB 容量只约束 MTP 路径，不应套用到外插 U 盘。仍需记录外插盘实际装载的 FIT、可用容量和重复启动稳定性。

### 板级身份、内存与闪存

- 文章记录的机型为 `Qualcomm Technologies, Inc. IPQ807x/AP-HK09`，machine id 为 `0x08010008`，与项目原厂 FDT 的 HK09/board-id 8 信息吻合。
- U-Boot `bdinfo` 与 Linux FDT/日志都指向 512 MiB DRAM；Linux 运行时可用内存约 390 MiB。
- `/proc/mtd` 列出的分区是 SBL1、MIBIB、QSEE、DEVCFG、RPM、CDT、APPSBLENV、APPSBL、ART、OEM、CRASH，未看到普通 OpenWrt 根文件系统分区。日志显示原厂启动镜像包含 initramfs；结合文章中从 MTP 设备读取 FIT 的结果，可以推测该路径使用了随 FIT 提供的 initramfs。
- 原厂启动过程从 ART 读取校准数据到 `/tmp/virtual_art.bin`。这能证明 ART 是校准链的一部分，但尚未给出 ath11k 所需 BDF/caldata 的映射偏移。

文章中的固件标识为 `CKB01_11.B.003_293`（2023-08）；项目本地分析记录的是 `.251`。应把文章当作同机型的硬件实验参考，不要认为其固件细节与本地镜像版本完全一致。

### PCIe、MHI 与无线

- Linux 4.4.60 日志显示 `20000000.pci` 链路建立，根桥下出现 `0000:01:00.0` endpoint；紧接着有 MHI coherent pool 未保留的告警和 MHI 设备启用日志。此证据确认 PCIe modem 设备实际枚举，也说明 stock QSDK 的 MHI 初始化中有内存池告警；文章没有提供 endpoint 的 PCI vendor/device ID、完整 MHI channel 状态或拨号成功证据。
- 启动日志显示平台名 `ap-hk09`，并从 ART 读取 Wi-Fi 校准；后续 QSDK WLAN 驱动创建 2.4/5 GHz VAP，日志还出现 NSS Wi-Fi offload 初始化。作者在文章开头仍将交换机、PHY、MAC 映射记为未确认，不能仅凭驱动日志认定端口映射和 OpenWrt ath11k 校准已就绪。
- 蜂窝日志多次显示 LTE attach fail。文章没有联通 SIM、n78 band query 或中国网络驻网结果；它不能作为 n78/联通兼容性的实测证明。
- 文章报告 failsafe 会在约三分钟后因看门狗重启。该现象提示实机调试时应区分 watchdog 超时与内核 panic；串口日志和 pstore 对第一次 bring-up 很有价值。

## 两个 fork 的状态

### `Softbank-Air-5-Openwrt`

本地 `main` 位于 `b61f6650e37d814f96a27810e5a6d8611e782838`（2026-10-11），工作树干净。README 标题是 Qualcommax NSS Builder；仓库约 912 KiB，是 CI/配置/补丁/overlay 仓库，不含可直接改动的完整 OpenWrt 内核和 target 树。

当前 workflow 从 `JuliusBairaktaris/openwrt-ppe-nss` 的 `ppe-nss` 分支构建，并使用 `nss-packages` 的 `edma-nss` feed。`scripts/prepare-build.sh` 会先更新 feeds，再应用 `patches/tree/ppe-nss/*.patch`，然后拼接 `.config` 并叠加 `devices/<group>/files*`。这给 CKB01 提供了明确入口：用一组 OpenWrt target 补丁定义板型，builder 仓库保存补丁、设备构建配置和运行时 overlay。

当前 builder 缺少 CKB01：README 的构建设备表没有 `oppo_ckb01`；`devices/ipq807x-512m/config` 只列 6 个 512 MiB IPQ807x 板型；没有 CKB01 补丁或专用 overlay。

现有 release 面向已安装 OpenWrt 的用户，只产出 `squashfs-sysupgrade.bin`，没有 factory image。故不能把当前默认 release 当作 U-Boot USB 初次启动镜像。另一个容易漏掉的点是 `.github/workflows/build.yml` 的 push path filter 没有包含 `patches/**`：只改 DTS 补丁不会自动触发主构建 workflow；开发时要手动 dispatch，或把补丁路径加入触发条件。

CI 一次构建 6 个设备内存组、default/mesh 两个 flavor，合计 12 个矩阵任务。第一次 CKB01 bring-up 用专用工作流/单设备 config 更省时间，也能避免把 mesh 和 NSS 选项引入早期启动问题。现有 `devices/common/config` 打开 NSS Wi-Fi offload，并包含 USB storage/UAS 包；这不等于已有 USB-root FIT、initramfs 早期模块加载或 CKB01 无线校准支持。

### `uboot-qsdk12.5-build`

本地 `main` 位于 `9ce315735ac88fd0a7c7697bc527a8616ed0a972`（2026-08-18），外层和内嵌 U-Boot 源树工作区干净。`build.sh` 和 `configs/ipq807x_oppo_ckb01_defconfig` 已列出 OPPO CKB01；[`ipq807x-oppo_ckb01.dts`](../../uboot-qsdk12.5-build/u-boot-2016/arch/arm/dts/ipq807x-oppo_ckb01.dts) 标识 `qca,ipq807x-hk09`、machid `0x08010008`，并列出 `config@ckb01`/`config@hk09` 等配置别名。

这个 DTS 是 2016 QSDK U-Boot 的板级描述，重点在按键、LED、交换机和 U-Boot 配置识别；它不是 Linux 设备树，不能代替 Air 5 的 PCIe/MHI/ath11k Linux DTS。该仓库适合日后研究 CKB01 的 U-Boot 恢复能力。当前源树 `include/configs/ipq807x.h` 的默认命令是 `bootipq`，源树中未找到 `bootipq_usb` 实现；因此不能假设重新编译/替换后仍保留实机已有的 USB 启动行为。

## 在 `Softbank-Air-5-Openwrt` 开始移植的建议

### 适合的第一步

1. 在 builder fork 建立 `patches/tree/ppe-nss/0001-qualcommax-add-oppo-ckb01.patch`，目标修改由其构建的 OpenWrt 树：新增 CKB01 DTS/image profile、board compatible/config、Wi-Fi caldata 读取规则、MAC/端口映射和 per-device 包选择。以原厂 FDT 为资源来源；U-Boot DTS 只作为板型别名和 GPIO 候选资料。
2. 以 512 MiB、HK09 的 OpenWrt 设备配置为起点。先产出只给这块板用的 FIT/initramfs，FIT configuration name 应与 U-Boot 实际匹配行为相符；`config@hk09` 是合理候选，但须以 U-Boot 串口实际选中记录确认。
3. 首轮用常规 ath11k/firmware 路径建立 Wi-Fi 基线，保留 CKB01 的 ART/MAC 数据，不套用 Haze 或 Deco 的校准变体；NSS Wi-Fi offload 可在基线 Wi-Fi 稳定后再启用比较。
4. modem 先加入当前内核可用的 MHI PCI、WWAN control、MHI net/QRTR 包，核对实机 PCI ID、MHI ports、QMI 控制和 `IP_HW0` 数据面。原厂数据面是 QMI/RMNET，因此不能只以 MBIM 包成功加载作为移植完成条件。
5. 独立制作 USB 启动的 FIT/initramfs artifact，并在已验证优先级的外插 U 盘上确认 U-Boot 能稳定读取它。只有计划使用 SDX55 MTP 路径时，才需要按约 29 MB 的文章实测容量限制 FIT；这不是外插 U 盘的容量上限。再确认 Linux 启动后外插盘是否可见、可写且容量足够，然后决定持久根文件系统方案。
6. 将 CKB01 构建配置与其他 512 MiB 设备隔离，或在专门的 bring-up workflow 中只构建此设备；把 `patches/**` 纳入 CI push path。成功启动并验证基础功能后，再接入完整 release 矩阵和 NSS 优化。

### 开始写板级 DTS 前的现场记录

- 记录 U-Boot `usb info`、`usb tree`、`usb storage`、`usb part` 和外插 U 盘上实际加载的 FIT 路径；重复冷启动，确认设备编号和优先级稳定，并记录另一个 MTP 设备是否同时出现。
- 记录外插盘的 FIT 可读大小与分区格式；只有使用 MTP 启动时，才以文章中约 29 MB 的 MTP 容量评估 FIT 空间。
- 从串口保存 PCIe link、endpoint 的 `lspci -nn`/配置空间 ID、GPIO58 PERST 时序、MHI 初始化和 channel bind 情况；不要将文章的 MHI coherent-pool 告警误判为“整个 MHI 不工作”。
- 保存 ART 原始数据和 `/proc/mtd`/SMEM 映射，确定校准区、BDF、MAC 和外部闪存可写区域；文章仅证明原厂会读 ART，未提供足够偏移供 OpenWrt 直接复制。
- 收集 lan/wan 逐口连通、PHY ID、交换机端口、MAC 地址来源；文章作者也没有确认这部分。
- 确认设备上的实际 SoC SKU；本地原厂资料为通用 `IPQ807x/AP-HK09` 和 `IPQ8074` 软件 baseline，用户识别为 IPQ8072A。HK09 与 512 MiB 可以先用于构建初版，不应据此锁死 Silicon SKU 或射频能力。

## 建议的移植阶段与完成判据

| 阶段 | 工作 | 完成判据 |
|---|---|---|
| 0. USB 启动路径 | 记录已实测的外插 U 盘优先级、容量、FIT config 匹配 | 不改闪存即可稳定从外插 U 盘加载 initramfs；若切换到 MTP 路径，再单独验证其容量限制。 |
| 1. 基础板型 | DTS、UART/LED/按钮、RAM、以太网/PHY、ART 读取 | OpenWrt 启动稳定；串口可登录；有线端口映射和 MAC 可重复。 |
| 2. Wi-Fi | Air 5 专属校准包/variant、ath11k 基线 | 两频段注册并稳定发射/接收，校准数据和 MAC 来源确认。 |
| 3. SDX55 | PCIe/MHI、QMI control、RMNET/IP_HW0 数据面 | modem 重启、SIM 查询、QMI 会话、路由和掉线恢复都可重复。 |
| 4. 联通与 n78 | modem capability/NV、网络注册和流量测试 | 联通 SIM 实际注册到目标 NR band 并通过数据面测试；仅识别 SIM 不算完成。 |
| 5. 完整发行版 | USB 持久 root、NSS/PPE 性能配置、升级/恢复策略 | FIT 与 rootfs 可重复启动，主要硬件功能通过重启/升级验证。 |

**结论：可以从 `Softbank-Air-5-Openwrt` 开始做移植工程，但应先把它当作 OpenWrt 补丁与构建编排层。第一件代码交付应是“单板型补丁 + 精简 USB FIT/initramfs”，不是把当前 sysupgrade release 直接刷到设备。**
