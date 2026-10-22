# CKB01 SDX55：14槽主线 MHI 版本

2026-10-22。固定 OpenWrt `a0d3cabc052f9c3c19a0abe2b2633195f703bccc`、Linux 6.18.55。
本轮结束条件为 Actions 进入编译，**不刷写、不重启设备**。以下驱动行为已作源码检查和编译检查，新固件的实机通信及稳定性仍待验收。

## 接收、启动与故障处理

- 仅 `oppo,ckb01` + `17cb:0306 / 17cb:010c` 选用此配置，其他设备继续原有匹配。
- 保留主线 core 事件解析器、mhi_net、WWAN QMI、QRTR及libqmi。普通RX的client_managed=false；不加载QSDK NAPI消费者。
- 原厂291的14个槽位完整保留；8/12/13为零元素offload占位，主线跳过其普通缓冲及IRQ申请。4/6共享MSI5，5/7共享MSI6；沿用现有IRQ分配、IRQF_SHARED和向量数向上取整。
- 环0使用主线控制事件解析器。软件通道64元素，IP_HW0 UL512/DL1024；32位DMA、60秒控制超时、MRU16384。
- mhi_net注册接口时不prepare，ndo_open才prepare并启动RX refill；stop取消refill、unprepare并清理分片，失败回滚及remove配对。IP_SW0先开，IP_HW0后开。
- 固定no-M3，MISSION_MODE不再重新允许runtime suspend；整机suspend/hibernate返回EBUSY。
- 启动记录真实EE、MHI状态及READY。已观察到AMSS，保留上游真实READY握手；SBL/EDL/RDDM等不作正常启动，不下载SBL、不伪造状态。**尚无实测证明需要SBL专属READY入口，因此本版不启用该例外**。SSR GPIO不操作。
- 健康检查、PCI recovery、AER、reset回调、runtime resume故障汇入同一个首次故障处理；core SYS_ERR及SoC reset请求也受限制。首次故障保存PCI配置读回、缓存EE/PM、环指针和每环最多4条原始事件，再阻止进一步doorbell；不自动请求SoC/PCI功能复位。外部强制PCI复位不在驱动可阻止范围内。
- 故障快照不读取BAR，避免失联后诊断再次访问不可用MMIO。正常停止/关机仍回收资源；不要用debugfs reset恢复，保留日志后冷启动。此限制不等于停用模块自身的看门狗；管理链路失败仍须单独确认原厂心跳是否恢复。

| 通道 | 事件环 |
| --- | --- |
| DIAG4/5 | 1/3 |
| QMI14/15 | 1/2 |
| QMI1 16/17 | 3/3 |
| IPCR20/21 | 2/2 |
| IP_SW0 46/47 | 4/5 |
| IP_HW0 100/101 | 6/7 |

## 软件先行的120秒窗口

`discover.ok`仅表示合法板型、PCI和软件接口枚举；`data_present`单独记录IP_HW0是否出现。两者均不代表已经通信。

启动助手并行、分别限时执行：

1. IP_SW0配置169.254.10.1/24，管理ping及`ckb01-oem exec 'uname -r'`。
2. QMI14 `probe --transport-only`查询DMS revision及UIM。
3. QRTR动态发现服务，独立执行同样的只读查询。

SIM错误保留原始响应，但不掩盖DMS成功。三路全部通过才发布`/tmp/ckb01-modem-ready.json`；数据接口出现后由netifd打开。完整worker（包括网卡open）在timeout进程组中运行，监督进程只进行有截止时间的轮询，发布就绪前再次检查剩余时间；到期终止探查进程组。超时保留每路JSON、stderr、已完成任务的rc、管理ping和RPC结果，保持有线/Wi-Fi管理，不rescan或reset。netifd也检查该门槛，避免提前ifup绕过顺序。重复启动不重复创建会话。

本机2026-10-20实测endpoint type3/interface4。拨号前经QMI14再次WDA GET，要求raw-IP、无QoS头、双向无聚合；不符合就停止，不进行格式轮试。保留APN3gnet、蜂窝metric10、有线WAN metric20及现有LAN/Wi-Fi。无自动MBN切换、SIM解锁或NV修改。

诊断：`ckb01-diag`收集独立传输探查、管理记录、host contexts（debugfs可用时）、PCI属性、日志及接口计数。`ckb01-modem probe`完整查询仍可手动调用。

## 来源

- 本机291 FIT提取的DTB：SHA256 `11055f414882a74df936cc9559b6d6414bfe182c7b282fa95ed15369fa4f41d6`。MHI子树与原厂live DTB的43节点一致。完整14槽的元素数、moderation、MSI、doorbell、hardware/offload均来自该DTB。
- [QSDK5.4 QTI控制器](https://github.com/felix-fly/qsdk-12/blob/01a4f08eea799d81f1af9c1eceb9a1e4c20d9f51/qca/src/linux-5.4/drivers/bus/mhi/controllers/mhi_qti.c)：共享MSI、PM与启动机制参考；本地SHA256 `1300842bedb7c0315e9a4000bfc3b401b1d01f33502b9ceda450ee65cf7f337f`。
- [QSDK5.4网络客户端](https://github.com/felix-fly/qsdk-12/blob/01a4f08eea799d81f1af9c1eceb9a1e4c20d9f51/qca/src/linux-5.4/drivers/bus/mhi/clients/netdev.c)：接口open/stop与RX缓冲生命周期参考；本地SHA256 `97d8bf86842c76c1c5c8354c840473adedefcd21a7f9eccd128346fa2f7bdadd`。采用主线已有refill，未复制另一套解析器或NAPI。
- endpoint原始响应及工具摘要：[endpoint-evidence.json](../packages/ckb01-modem/files/endpoint-evidence.json)。这些是既有原厂证据，不是本版OpenWrt通信成功的证明。

## 检查与验收记录

- 本机原厂只读对照：4.4.60，AMSS/M0，M3计数0；管理ping两次成功。未刷写、未重启、未修改模块配置。
- 本地：OEM通道/14槽配置检查、部分枚举、独立探查、SIM错误隔离、重复初始化、netifd门槛、WDA格式拒绝和实际FIT内容fixtures；Linux6.18.55的MHI core/PCI、mhi_net和WWAN对象完成ARM64 clang编译。
- Actions使用既有下载、host tools、外部工具链及ccache，实际重编变更内核及固件。FIT检查实际嵌入的工具、依赖、脚本及endpoint证据；verify失败仍只警告，上传原始ITB、可用rootfs/IMG和日志。编译失败单独报告。
- **待实机验收**：同一版本三次冷启动、三次暖启动、三路控制响应、IP_HW0收发、30分钟运行，以及SIM许可后的蜂窝地址/DNS/HTTPS/客户端联网。有线及双频AP一并记录。枚举、控制、蜂窝注册、LTE和n78分别判定；不以SIM锁或缺覆盖冒充驱动结论。
