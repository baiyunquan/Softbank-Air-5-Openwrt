# CKB01 SDX55 / 中国联通适配

## 当前状态

这是驱动和拨号候选版本。构建、OpenWrt 控制链路、LTE 数据、n78 数据四项验收分别记录；不能用编译成功或 CU XML 中存在 n78 代替实机驻网证据。

- 固定 OpenWrt：`a0d3cabc052f9c3c19a0abe2b2633195f703bccc`。
- 板型 `oppo,ckb01` + PCI `17cb:0306/17cb:010c` 才选择 `ckb01-sdx55`。
- DIAG 4/5、QMI 14/15、QMI1 16/17、IPCR 20/21、IP_SW0 46/47、IP_HW0 100/101。
- 主线六事件环，软件64元素，HW UL512 / DL1024，32位DMA，控制超时60秒；不从主机下载基带/SBL，不主动进入EDL。
- 按PCI父设备和通道发现接口，120秒异步等待。IP_SW0管理地址169.254.10.1/24；模块169.254.10.2。
- LAN1有线WAN(metric20)，LAN2及Wi-Fi为LAN192.168.5.1。蜂窝metric10、APN3gnet、无认证。
- `network.cellular.auto=0` 避免通道未发现时抢先拨号；启动助手就绪后显式ifup。endpoint确认前不会设置WDA或尝试拨号。

## 查询及数据

```
ckb01-modem discover
ckb01-modem status
ckb01-modem probe > /tmp/baseline.json
# QRTR动态发现节点，供交叉验证或原厂调试环境使用：
ckb01-modem --device qrtr probe
```

控制默认通道14/15，经qmi-proxy协调；WDS由netifd前台子进程持有，诊断使用独立客户端，写操作使用互斥锁。原始响应、libqmi解码和具体错误保存在`/tmp/ckb01-modem.jsonl`；不支持某条消息不代表整个模块故障。`ckb01-diag`一起收集。

**必须先取得本机IP_HW0 endpoint/interface证据**。不能因为PCI ID相同而套用Quectel编号。确认后配置：

```
uci set network.cellular.endpoint='<实测PCIe interface编号>'
uci commit network
ifup cellular
```

`ckb01_qmi`协议先执行带endpoint的WDA GET，再设置raw-IP/关闭聚合并读回。raw-IP不被接受时尝试普通QMAP，mux1及内核rmnet；只接受读回一致的数据格式。IPv4/IPv6使用独立WDS客户端，客户端及数据handle由同一进程持有，退出时Stop Network并释放CID。IPv6失败只在明确的IP族不支持/3GPP IPv4-only响应时允许IPv4回退。其他错误保留日志并退避重试，不触发MHI reset。

## CU切换和恢复

本机原厂查询（2026-10-20）：

- MPSS.HI.2.0.3-00217-SDX55_CPEALL_PACK-1.576560.2.578897.2，2023-03-31。
- 当前SBM：`bff8740b8ba4a579e5c21499b9e4f88d0773cd6f`，Commercial-SBM，0x0a011c0b。
- 预装CU：`3b6df21a5b1e34bf2b66357780ba035bd65d1ea3`，OpenMkt-Commercial-CU，0x0a011502，26180字节。
- SBM时DMS仅报告LTE B1/B8/B41/B42、NR n3/n77；NAS LTE only、手动选网。SIM存在且USIM ready；尚非成功注册/联网证明。
- CU XML包含n41/n78；是否真正可用须切换后查询和实测。

先将U盘挂在`/mnt/usb`，把本机MBN备份及其SHA256保存到U盘。参考摘要已随工具记录，来源是此前这台设备的只读提取。停止数据后：

```
ifdown cellular
CKB01_BACKUP_DIR=/mnt/usb/air5-backup/cu ckb01-modem profile cu
```

工具先核对CU ID/描述/版本/大小，保存active/pending、NAS偏好、DMS版本与能力及参考MBN摘要；原备份不覆盖。PDC选择及激活都等待匹配CID、消息及token的indication，并读回active ID。响应成功本身不算激活成功。通信中断或indication缺失时先完整断电冷启动，再读状态；不要运行MHI debugfs reset。

```
ifdown cellular
CKB01_BACKUP_DIR=/mnt/usb/air5-backup/cu ckb01-modem profile restore
```

恢复保存的原PDC ID及NAS偏好，读回确认。原厂IPQ系统可使用打包的独立ARM恢复工具（USB内`ckb01-oem-recover-aarch64-linux-gnu`（IPQ）或`ckb01-oem-recover-arm-linux-gnueabi`（模块）及`original-profile.json`）；工具只允许恢复备份中的原PDC ID，不写NV/基带。用法：`./ckb01-oem-recover-aarch64-linux-gnu /mnt/usb/air5-backup/cu/original-profile.json`。QRTR服务须已可用；NAS偏好在完整OpenWrt工具中恢复，独立工具只恢复PDC并核对active ID。

## n78与验收

CU正常后先记录DMS/NAS/UIM/PDC。只有DMS报告n78时才运行：

```
ckb01-n78-test 300 > /mnt/usb/air5-backup/cu/n78-test.log 2>&1
```

临时限制NR SA/NSA为n78，保留LTE支持NSA锚点；测试结束恢复原频段掩码与LTE/NR自动选网。必须同时记录实际NR服务小区/频段及同一会话流量。LTE回落单独标记。

实机清单：3次冷启动、3次暖启动；管理ping和只读查询；蜂窝IP、DNS、HTTPS；Wi-Fi客户端经蜂窝上网；有线备用；至少30分钟联网及复位/MHI/AP/端口检查。缺覆盖或证据的项目标为待验收。

## 构建

本地包使用libqmi、libqrtr-glib、libjson-c和完整QMI消息集。沿用下载与ccache缓存；驱动变化仍需重新编译内核。FIT验证检查实际嵌入initramfs中的工具、协议、模块和依赖，以及既有哈希与内存边界；所有验证失败只警告，保留原始ITB、可用IMG及日志上传。实际编译错误单独失败。
