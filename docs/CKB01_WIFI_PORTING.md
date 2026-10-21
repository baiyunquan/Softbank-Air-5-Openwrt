# CKB01 / SoftBank Air 5 ath11k 双频适配

## 2026-10-21 持久化 rootfs 修复

实机已确认：CI 普通用户解压 rootfs 后直接 mkfs.ext4，会使 ACL 文件归属变成
1001:1001。ubusd 跳过这些 ACL，hostapd/wpa_supplicant 虽有进程却不能注册
ubus 对象，netifd 因此反复等待。恢复归属并重载 ACL、重启 wpad 后对象出现。
重新验证本机 ART、恢复 `/tmp/ckb01-caldata.status` 后，2.4GHz 信道1及5GHz
信道149/80MHz均到达 AP-ENABLED。源码改为同一 fakeroot 会话保留打包所有权，
并在每次启动的 S09 阶段校验 ART，避免持久化文件与临时状态不一致。
本轮结果覆盖 AP 启动；终端关联和新启动服务的重启验收另行记录。

## 交付状态与默认配置

这是 USB FIT/initramfs 无线适配首版。2026-10-20 已在一台 CKB01 实机上
验证 ART 校准读取、双频 AP、AX211 关联和重复本地链路测试。用户决定不再做
额外 30 分钟稳定性测试；采样时设备 uptime 为 1 小时 44 分钟，AX211 当前关联
时长约 12 分钟。结果只覆盖本机与 30 cm 测点，不等同量产或远距离验证。
保留原厂 U-Boot，将 Actions 产物 `air5-ckb01-usb.img` 整盘写入外插 U 盘，
再插入断电的设备并通电。镜像提供 MBR、第 1 主分区 FAT16 及根目录的
`uimage-initramfs.itb`，供原厂 USB 启动流程自动加载，无需进入 U-Boot。
新分区布局的自动启动仍待实机确认。配置位于 RAM，重启恢复镜像默认值。

| 项目 | 2.4GHz | 5GHz |
|---|---|---|
| SSID | Air5-2G | Air5-5G |
| 加密 / 密码 | WPA2 AES / Air5-OpenWrt | WPA2 AES / Air5-OpenWrt |
| 地区 / 带宽 | CN / HE20 | CN / HE80 |
| 首选信道 | 1 | 149，36 作为可用性回退 |
| 接入网络 | lan，192.168.5.1/24 | lan，192.168.5.1/24 |

无线运行于普通 ath11k 数据路径。实际空间流和天线能力由 BDF、校准和固件报告。
本次无线测量不用于判定物理网口映射。

## 原厂证据

- 本地 `extracted_root` 与 `extracted_kernel/rootfs` 中的
  `lib/read_caldata_to_fs.sh` 对 `ap-hk*` 使用 `0:ART`，`skip=4096`，
  `count=131072`，生成 `/tmp/IPQ8074/caldata.bin`。
- 两份原厂 `lib/firmware/IPQ8074/WIFI_FW/bdwlan.bin` 均为 131072 字节，
  SHA256 为 `9fdaff50396c03e097f713067df149be3c9b1d36689e4d20eff455f00c886944`，
  内容与原厂 `bdwlan.b290` 相同。原厂版本文本为
  `WLAN.HK.2.4-02142-QCAHKSWPL_SILICONZ-1.395212.1 v2`。
- 实机文章日志显示 chip_id=0、board_id=0xff，加载 `IPQ8074/bdwlan.bin`；
  BDF 地址 `0x4b0c0000`，每机校准地址 `0x4b0e0000`。日志中的
  `offset 0x20000` 是两者的目标内存偏移；ART 的源偏移为脚本确认的 `0x1000`。
- 原厂 FDT 的 WCSS 保留区为 `0x4b000000 + 0x3700000`，ETR/M3 位于
  `0x4e700000` / `0x4e800000`。因此使用 OpenWrt `ipq8074-512m.dtsi`
  和 `qcom,ath11k-fw-memory-mode = <1>`。
- 本机 `0:art` 已实读两次并与本地原始备份一致；按 `0x1000` 提取的
  131072 字节校准片段 SHA256 为
  `6d177df460b50e8dbe24cfbefddef9d1f58e9d2c61a3d5d888fa8b70d3e7372a`，
  XOR16 校验为 `0xffff`。完整 ART 与逐机校准数据不放入仓库。
- 实机 ath11k 接受 board_id `0xff` 和仓库中的原厂 BDF；无线固件成功启动，
  2.4/5 GHz PHY 分别报告四条可配置链。BDF 是板级数据，仍不能替代每机校准。

来源中的出厂校准、工厂模式和闪存写入脚本仅作为调查资料。

## BDF 与固件

使用固定版本 Qualcomm `ath11k-bdencoder`：
`qca/qca-swiss-army-knife@6209ad4248f73a3d4ba6a9647ce062a1f8aecde2`。
原工具及版权声明位于 `tools/ath11k-bdencoder`。

```sh
python3 scripts/ckb01-bdf.py          # 重新生成
python3 scripts/ckb01-bdf.py --check  # 校验可重复性
```

映射只包含 `bus=ahb,qmi-chip-id=0,qmi-board-id=255,variant=OPPO-CKB01`；
生成 `QCA-ATH11K-BOARD` 格式的 `board-2.bin`。
原始 BDF、映射、来源及全部摘要见 `devices/oppo_ckb01/firmware/`。
板级数据安装到 `/lib/firmware/ath11k/IPQ8074/hw2.0/board-2.bin`。

运行固件沿用固定 OpenWrt 源码的 `ath11k-firmware-ipq8074`（linux-firmware
20260910），安装在 `/lib/firmware/IPQ8074/`，供 secure WCSS remoteproc 加载。
原厂 QSDK 运行固件未与现代 ath11k 混用。

## 启动数据流及失败处理

1. ath11k 请求 `ath11k/IPQ8074/hw2.0/cal-ahb-c000000.wifi.bin`。
2. `10-ckb01-caldata` 按 `0:ART` / `ART` / `0:art` / `art` 标签定位 MTD 字符设备，要求分区为
   262144 字节；完整读取两次并比较，提取 `0x1000 + 0x20000`，检查 XOR16=0xffff。
3. 校准通过后原样、原子发布到固件请求路径。全过程只读 ART，临时副本退出时删除。
   来源、偏移、大小、ART/caldata SHA256 写入 `/tmp/ckb01-caldata.status`。
   失败时保留原因，校准文件不发布。
4. `S95ckb01-wifi` 通过 procd 启动一次性助手，由 BusyBox timeout 限制为 120 秒。
   助手等待有效校准和两个频段的上游 UCI 检测结果，按 band 匹配设备。
5. 确认 HE AP 能力及可用信道后写入 `ckb01_2g` / `ckb01_5g` AP，禁用上游生成的
   默认 VIF，然后请求 netifd reload。2.4GHz 优先 1，再选其他可用信道；5GHz
   优先 149，再选 36，且相应 80MHz 块的四个信道均须允许 AP、无 DFS/no-IR/no-80MHz 限制。
6. 无线 MAC 优先保留有效驱动地址；样例、无效或重复地址使用本机 ART 摘要按频段
   派生的稳定本地地址。校准字节不作 MAC 或区域修改。
7. 以设备初始化标志保证重复运行不会覆盖本次启动中 LuCI 已修改的配置。

`/tmp/ckb01-wifi.status` 的 `configured` 仅表示已提交 AP 配置和 reload 请求，
实际启动结果查看 hostapd / `ubus call network.wireless status`。
缺失校准、仅一个频段或无可用信道时记录失败，有线网络独立工作。

## 诊断与后续实机验收

```sh
cat /tmp/ckb01-caldata.status /tmp/ckb01-wifi.status
ubus call network.wireless status
iw phy
iw dev
ckb01-diag
ckb01-art-backup /tmp/air5-art.bin
```

修复问题后可执行 `/etc/init.d/ckb01-wifi restart` 重试。
`ckb01-diag` 收集无线配置、PHY/信道/区域、站点关联、hostapd、remoteproc 和固件日志，
以及 BDF/caldata 摘要；完整 ART 仍使用独立备份命令导出。

2026-10-20 实机测试摘要：AX211 距设备约 30 cm，2.4 GHz 信道 1 / HE20，5 GHz
信道 149 / HE80；5 GHz 三轮各 250 Mbps UDP 上下行对照中，上传延迟 p99 中位数
12.4 ms，下载 11.3 ms，空闲 5.8 ms，未见 Wi-Fi ping 丢包。完整方法、各轮数据、
温度和设备最终状态见工作目录 `research/CKB01_WIFI_20261020.md` 及 `raw/`。
原计划的额外 30 分钟 soak 已按用户要求取消；`soak-*` 子目录是中止前的部分采样，
不作为完整稳定性结论。AX211 在 5 GHz 信道 36 的两条接收链曾相差约 20 dB；
切到信道 149 后，多次测量差值约 7–11 dB，聚合 RSSI 约 -46 至 -51 dBm，
当前读数为 -50 dBm。信道 36 的 RSSI 更强，但本次同负载 p99 较差；因此选择
149 是按测得的延迟和重传表现，不是信号强度提升。该单点结果不能区分客户端
天线方向、近场摆放或设备链路本身，不能据此改写 ART。

仍需后续确认冷启动后的校准一致性、多个位置和终端的链路表现；用户可用
`ckb01-art-backup` 导出 ART，但导出内容仅留在设备本地并妥善保存。

## 构建检查

固定源码仍为 `JuliusBairaktaris/openwrt-ppe-nss@a0d3cabc052f9c3c19a0abe2b2633195f703bccc`。
补丁按 `0001` 板型、`0002` 无线顺序应用；CI 检查解析后的无线/MHI 包选择。
`ckb01-fit.py --wireless` 对实际嵌入的 initramfs 校验无线模块、固件、助手、启动链接
和精确 BDF 摘要，并检查 DT 的 variant、memory mode 和 512MB 保留区。
保留 FIT 哈希、CPIO 嵌入和 `0x41000000` 内核至 `0x44000000` FIT 缓冲区的边界检查。
产物包含来源记录和本说明，实机状态统一标为待验证。

参考：

- [Linux ath11k 板名与变体匹配](https://github.com/torvalds/linux/blob/v6.18/drivers/net/wireless/ath/ath11k/core.c)
- [Linux ath11k BDF/caldata 加载](https://github.com/torvalds/linux/blob/v6.18/drivers/net/wireless/ath/ath11k/qmi.c)
- [Qualcomm ath11k-bdencoder 固定版本](https://github.com/qca/qca-swiss-army-knife/blob/6209ad4248f73a3d4ba6a9647ce062a1f8aecde2/tools/scripts/ath11k/ath11k-bdencoder)
- [实机文章](https://memo205.hatenablog.jp/entry/2025/07/31/234645)
