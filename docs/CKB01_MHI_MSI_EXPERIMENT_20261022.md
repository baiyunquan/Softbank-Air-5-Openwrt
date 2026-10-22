# CKB01 MSI 实机对照，2026-10-22

## 结论

已经复现并隔离 **QMI/IP_SW0 的完成事件存在、对应 MSI 未进入 DWC 分发**。
使用同一主线解析器主动消费事件后，管理 ping、模块 root RPC、QMI14 DMS/UIM 全部恢复；停止消费后，管理 ping 和 QMI14 再次失败。QRTR 在三个阶段均正常。

这证明本轮所测通道的事件内容、DMA 数据和主线完成解析能够协同工作，不能再把故障整体归因于 QMI 消息不兼容、管理地址错误或 netdev 未启动。也不代表 IP_HW0 数据通路已验证。

故障边界目前在目标向量被 DWC 捕获/分发之前，而非已经进入 MHI handler 后未调度 tasklet。尚不能把它进一步等同于“模块从未发送 MSI”：模块发送到错误地址/数据、发送通路或主机捕获条件仍需区分。

## 本次环境与边界

- 用户自行烧录修正版成果；本轮通过 SSH `192.168.5.1` 调试，并记录串口。
- 固件源码：`dd30146bae08790c81c9fe91a812c187673faa27`，Linux 6.18.55。
- `/boot/uimage-initramfs.itb` SHA256：`6080451297442871ff8132b86ef340d65fab5360f3101c310c34de3cdb7cbfe0`。
- 根文件系统 `/dev/sda2`；诊断入口存在；安装的采集脚本与该提交字节一致。
- boot ID：`4e64cdab-6fad-4cc9-964b-bc0607e8a470`，实验前后未变。
- 模块自启动 AMSS/M0；未执行 MHI reset、重启、PDC、NV、SIM 解锁或拨号。
- 仅执行一次软件消费窗口。基线 id1 为 trace-only，id2 为 poll；ER1/2/4/5，正常 IRQ 保持开启。
- IP_HW0 保持 DOWN；未伪造 modem-ready，也未绕过启动就绪条件。

## 三阶段结果

| 操作 | 基线，无软件消费 | 软件消费窗口 | 停止后新请求 |
| --- | --- | --- | --- |
| 主机 ping 169.254.10.2 | 0/3 | 3/3 | 0/3 |
| QMI14 DMS/UIM | CTL CID 超时，退出124 | 成功，退出0 | CTL CID 超时，退出124 |
| QRTR DMS/UIM | 成功，退出0 | 成功，退出0 | 成功，退出0 |
| 原厂 root RPC | 本轮基线未额外调用 | 成功执行模块只读日志查询 | 未以新窗口重试 |

QMI 和 QRTR 读到相同基带版本：

```text
MPSS.HI.2.0.3-00217-SDX55_CPEALL_PACK-1.576560.2.578897.2  1  [Mar 31 2023 10:00:00]
```

UIM 主 USIM 为 `state=ready`、`personalization_state=ready`。本轮没有解锁操作；不能从这里的零个性化重试字段推导锁死。

窗口从主机 uptime 300.38s 到330.38s，自行结束，`consumed=1055 rounds=916 rc=0`，未达到4096总预算。20ms为请求调度间隔，非硬实时周期。初次管理 ping 延迟1228ms/228ms/22ms，包含清理积压、诊断输出与并发 RPC 开销，不作为网络性能结论。

## 中断与事件证据

主机配置 MSI 地址 `0x44d79000`、data base `0x10`。父 bank0 为 Linux IRQ17/GIC hwirq84。端点相对向量与 DWC 硬件号不能混用：

| 事件/用途 | 相对向量 | DWC hwirq | Linux IRQ | 实验前 DWC received | 实验后 DWC received |
| --- | --- | --- | --- | --- | --- |
| ER1 / QMI TX | 2 | 18 | 85 | 0 | 0 |
| ER2 / QRTR、控制 RX | 3 | 19 | 86 | 77 | 83 |
| ER4 / IP_SW TX | 5 | 21 | 88 | 0 | 0 |
| ER5 / IP_SW RX | 6 | 22 | 89 | 0 | 0 |

- bank0 enable=`0xffffffff`、mask=`0xfc00fffe`，目标18/21/22未屏蔽；端点 MSI mask=`0xfffffc00`，相对2/5/6未屏蔽。
- 实验前后 snapshot 的 bank0 status=0，DWC observer 对18/21/22的 received/dispatch_failed始终为0。
- 正常 QRTR 的hwirq19持续经过DWC及MHI handler；同一个父IRQ能够工作。
- 软件消费期间，ER1 event/complete从0变成22；ER4变成504；ER5变成515，而这三个环的 irq/schedule/task始终为0。
- net_rx从0变成515；停止后事件device RP继续前进，host RP停住，新的管理/QMI请求再次超时。
- 全程 M0/AMSS，dead=0，未出现诊断error、设备自动恢复或复位。

这些证据支持修复**中断发送/目标捕获兼容性**；不支持继续更换完成事件解析格式。当前数据不足以直接判定是EP发错地址、发错数据，还是主机侧未捕获正确写入。

## 模块侧证据及下一步

在同一个窗口中，通过恢复的原厂 root RPC 读取模块 Linux4.14.206-perf 日志。临时将 RAM 参数 `/sys/module/mhi/parameters/mhi_msg_lvl` 从4设为0，约4秒后恢复4。日志包含连续的：

```text
[mhi_dev_event_rd_offset_completion_cb] Rd offset dma completed for flush req ...
[mhi_dev_event_msi_cb] MSI completed for flush req ...
```

这是模块异步传输回调执行证据，不是主机已收到正确MSI的证据。模块反向ping主机未收到应答，与主机窗口内3/3成功分开记录，未据此改防火墙。

此次过滤器主要捕获完成回调，未保留发送地址/数据。随后对原厂vmlinux继续核对，批量路径实际使用另一条日志：

```text
[mhi_dev_schedule_msi_ipa] Sending MSI %d to 0x%llx as data = 0x%x for ch %d ...
```

下一次应优先取得该日志，与主机地址`0x44d79000`及data`0x12/0x15/0x16`对齐，再核对eDMA/IPA的目标地址转换和DWC捕获。已修正本地模块采集模板，将发送记录单独保留，避免被大量完成记录挤出。**本轮没有开启第二个软件消费窗口。**

另有一处重要限制：`mhi_trigger_msi_edma`有缓存MSI目标的路径，但原厂批量flush分支在`0xc0962a2c`调用`ep_pcie_get_msi_config`，在`0xc0962ab8..0xc0962ae4`使用配置地址和base+msivec。不能仅凭另一个函数的缓存就宣布此次故障由旧地址缓存造成。

## 采集脚本修复与当前状态

实机 BusyBox 不支持`dmesg -w`，导致原始kernel-stream文件只有用法错误。前后完整dmesg及阶段快照仍保留关键日志。采集器现自动检测follow支持，缺失时改用`logread -f`；相关回归测试先失败后通过，完整86项检查通过。实机已更新此用户态脚本，原脚本保存在`/root/ckb01-mhi-debug-dd30146b`；新脚本仅执行只读snapshot，没有重复窗口。logread follow冒烟测试按1秒超时返回124，无选项错误。

双频AP在运行，Wi-Fi SSH在实验期间保持；WAN192.168.1.130，网关192.168.1.1 ping2/2。未执行完整双频流量稳定性测试；HTTPS探测因未安装curl而未完成，不记为联网故障。蜂窝数据、LTE/n78仍未验收。

## 原始证据

保存在本机项目根目录下 `research/mhi-msi-diagnostics-20261022/`：

- `new-firmware-preflight.txt`：更新后的启动、网络、中断及日志。
- `experiment-stdout.txt`、`experiment-result.json`：三阶段输出与返回状态。
- `experiment-evidence.tar.gz`及同名解压目录：每阶段完整快照、QMI响应和命令返回码。
- `module-msi-stdout.txt`、`module-msi-full-filtered.txt`：模块回调及参数恢复证据。
- `sdx55-msi-path.disasm`、`sdx55-async-msi.disasm`：原厂模块发送路径。
- `post-experiment-health.txt`、`firmware-and-logreader.txt`、`collector-fixed-snapshot.txt`。
- `uart-experiment/serial.raw`、`events.jsonl`；串口记录不含主动控制命令。
- `collector-busybox-red.log`及`collector-busybox-green.log`；日志摘要见`evidence-sha256.json`。
