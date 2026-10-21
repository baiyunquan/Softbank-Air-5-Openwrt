# OPPO CKB01 实机文章：来源与实验摘要

> 本文件是对原文的技术摘要，不是原文逐字副本。

## 原文

- 标题：OPPO CKB01
- 作者站点：大破雑記帳
- 发布日期：2025-07-31
- 原文链接：https://memo205.hatenablog.jp/entry/2025/07/31/234645
- 本地抓取的网页源文件：[OPPO_CKB01_ARTICLE_SOURCE.html](OPPO_CKB01_ARTICLE_SOURCE.html)
- 本地 Markdown 版本：[OPPO_CKB01_ARTICLE_ORIGINAL.md](OPPO_CKB01_ARTICLE_ORIGINAL.md)

## 文章记录的实机信息

### 启动器与存储

- 设备使用 U-Boot 2016.01。环境变量里的启动命令为 `bootipq_usb`，帮助信息也列出了从 USB 设备启动的命令。
- 板级编号为 `0x08010008`，U-Boot 识别为 IPQ807x/AP-HK09。`bdinfo` 显示 DRAM 从 `0x40000000` 开始，大小为 `0x20000000`（512 MiB）。
- U-Boot USB 枚举结果里有 Qualcomm SDXPRAIRIE-MTP mass-storage gadget，USB ID 为 `05c6:f000`。作者推测这是 SDX55 侧的 MTP 存储设备，并提到手动枚举时设备并非每次都出现。
- 该存储设备约 29 MB，FAT16 分区中有约 28 MB 的 `uimage-initramfs.itb`。这描述的是文章中的 MTP 路径；文章没有验证外插 U 盘启动。
- SMEM 分区表列出 SBL1、MIBIB、QSEE、DEVCFG、RPM、CDT、APPSBLENV、APPSBL、ART、OEM 和 CRASH，未显示常规 Linux rootfs 分区。

### Linux 与板级信息

- 原厂系统运行 Linux 4.4.60。启动记录将平台标为 `ap-hk09`，并能对应到 IPQ807x/HK09 板型。
- 文章中的固件版本为 `CKB01_11.B.003_293`（2023 年 8 月）。本地项目资料中的原厂版本为 `.251`，所以文章与本地镜像不是同一个固件构建。
- 设备有 512 MiB RAM，文章报告 Linux 运行时可用内存约 390 MiB。
- 作者通过 failsafe 进入系统时观察到设备约三分钟后被 watchdog 重启；调试时应保存串口日志以区分 watchdog 重启和内核故障。

### PCIe 与 SDX55

- Linux 日志显示 `20000000.pci` PCIe 控制器链路建立，根桥下面出现一个 endpoint。
- 随后的日志包含 MHI coherent pool 未预留的告警，也包含 MHI 设备启用记录。文章没有列出 endpoint 的 PCI vendor/device ID、完整 MHI 通道状态或成功拨号结果。
- 文章没有给出可复现的 QMI 会话或蜂窝数据测试，因此不能据此断言 QMI/RMNET 数据面在 OpenWrt 下已具备适配条件。

### Wi-Fi、ART 与有线接口

- 原厂启动过程从 ART 读取数据，并在系统中生成 `/tmp/virtual_art.bin`。这说明 ART 参与无线校准流程，但文章没有提供可直接用于 ath11k 的校准偏移、BDF 对应关系或 MAC 映射。
- 后续日志能看到 QSDK WLAN VAP 和 NSS Wi-Fi offload 初始化。它们证明原厂软件启动了无线相关组件，不等于 OpenWrt 所需的 ath11k 校准和板级参数已确认。
- 文章把交换机、PHY、MAC 与 LAN 端口映射标为尚未确认，因此端口定义仍需本机测试。

### SIM、频段与网络注册

- 文章中的蜂窝日志多次出现 LTE attach 失败。
- 没有中国联通 SIM 的测试结果，没有 n78 查询结果，也没有证明 modem 实际注册到中国联通网络。

## 对 Air 5 移植的参考价值

1. HK09 板型、board id 8、512 MiB RAM 与本地原厂 FDT 分析相互印证，可用于确定初始板级身份。
2. 文章展示了 U-Boot 经 USB 读取 FIT 的实际路径，但枚举到的是 SDX55 MTP gadget。用户另行实测外插 U 盘优先级，因此文章中 MTP 的约 29 MB 容量不能当成外插 U 盘限制。
3. PCIe/MHI 的启动证据足以支持继续调查 SDX55，但不足以证明 QMI/RMNET 或中国联通网络已打通。
4. ART 是无线校准链的一部分；在拿到 Air 5 自己的 ART/caldata 布局前，不应照搬 Haze 或 Deco 的校准配置。
5. 文章未确认 LAN/PHY 映射，也未验证 n78；这两项仍需用本机资料和实测补齐。

## 与项目内其他分析

- [三套系统与设备树比较](../../SYSTEM_COMPARISON.md)
- [CKB01 移植仓库评估](CKB01_PORTING_REVIEW.md)
