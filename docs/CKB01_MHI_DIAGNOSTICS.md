# CKB01：MSI 与事件环消费对照

这是一套显式触发的诊断工具。默认不开启软件轮询，不发布 modem-ready、不启动 IP_HW0，也不改变 MSI、通道、PM、MBN 或 SIM 配置。详细输出通过 `CKB01-MHI` 前缀检索。

## 使用

启动包含本补丁的同一构建 ITB/rootfs，等待开机 modem 探查结束（最长120秒）：

```sh
# 只读快照：不查询模块、不消费事件
ckb01-mhi-debug snapshot

# 一次基线 / 软件消费 / 停止后对照
ckb01-mhi-debug compare
```

也可指定一个尚不存在的结果目录作为第二参数。命令将阶段、原始响应、返回码和相关内核日志输出到 stdout；同时保存在结果目录。通过 SSH 保存完整 stdout：

```sh
ssh root@192.168.5.1 ckb01-mhi-debug compare | tee mhi-compare.txt
```

每阶段并行执行相同的管理 ping、QMI14 `probe --transport-only`、QRTR `probe --transport-only`，每个查询进程组最长15秒，随后保存 IRQ、事件、网络计数。停止轮询后再执行一组新查询，区分暂时排空与正常中断恢复。查询失败作为证据保留，不等于采集工具失败。

`ckb01-diag` 自动包含只读快照。它不会启动软件消费或 ADB。

## 接口、限制和生命周期

- `/sys/kernel/debug/mhi/mhi*/ckb01_diag`：只读上下文、四条待消费原始事件及边界计数。环0的指针为瞬时观察，不复制其原始事件；普通数据环与主线消费者共用锁。
- `ckb01_poll`：写入 `trace` 开启限量日志但不消费，`start` 开启一次消费，`stop` 停止。新 `start` 在轮询已运行时返回 EBUSY。
- 固定30秒窗口、20ms间隔，ER1/2/4/5 每轮每环最多64条原始事件，总计最多4096条。陈旧事件也计入预算；未知类型、非法指针、失链或非 M0/AMSS 状态停止实验。占用中的 PM 锁不会阻塞轮询工作。
- 复用主线完成解析、客户端回调和回收；正常 IRQ 保持运行。软件消费使用同一事件锁，以 `src=poll` 区分其事件/完成记录。
- 错误与窗口结束始终记录。每窗口普通日志最多256条、每阶段最多16条；计数不受采样限制。
- 掉电、remove、上下文释放前同步停止工作；故障回调仅设置终止标志，不等待、不复位、不读 BAR。
- `/sys/kernel/debug/ckb01-pcie/*/msi` 提供 DWC 目标地址、每 bank 的 status/mask/enable、父 IRQ/hwirq、分发与失败计数。`trace` 写 `start` / `stop` 开启或停止最长30秒限量输出。快照只读 STATUS，不做 W1C 清除；失链后不读 DBI。

诊断仅对整机 `oppo,ckb01` 及 PCI/subsystem `17cb:0306 / 17cb:010c` 的端点生效。DWC 在该板创建观察目录，但仅将匹配端点分配的向量纳入追踪。

## 如何读结果

`vector` 是端点相对 MSI index；`expected_data` 是本次 PCI 配置的 data 基值加 index。IRQ domain 的各级 `hwirq` 与 Linux IRQ 分别输出，不能互相替代。多向量 MSI 的 cached message 通常是共享基值，不是每个 index 单独的 message。

此前实机的一次映射如下，仅作示例，程序不使用这些常数：

| 事件环 | 用途 | MSI index | Linux IRQ | data（基值0x10） |
|---|---|---:|---:|---:|
| ER1 | QMI TX | 2 | 85 | 0x12 |
| ER2 | QMI RX / QRTR | 3 | 86 | 0x13 |
| ER4 | IP_SW0 TX | 5 | 88 | 0x15 |
| ER5 | IP_SW0 RX | 6 | 89 | 0x16 |

日志阶段包括 `queue`、`channel_db`、`dw_dispatch`、`irq`、`schedule`、`task`、`event`、`complete`、`event_db`、`net_rx`、`qmi_rx` 和 `refill`。`queue` / `event` 的 a 为数据指针，b 高32位是 dword0、低32位是 dword1；doorbell 的 a 为写入值、b 为 burst/DB 模式。每个 `*.rc` 保存对应命令的退出状态。

- 事件已 DMA，正常 IRQ 不增长，轮询后恢复：中断通知路径需要继续定位。
- DWC 收到目标 hwirq，但 MHI handler 没进入：检查 domain 分发和屏蔽。
- handler 已进入而 task/consumer 未前移：检查调度和消费。
- 事件已回调但 IP/QMI 失败：检查客户端收包、缓冲及模块协议服务。
- 没有新事件：检查通道状态、TRE、doorbell 和模块处理。

轮询成功本身不能证明模块没有发 MSI。DWC 未看到中断也不足以单独证明发送侧故障。

## SDX55 原厂发送路径证据

本机原厂 SDX55 `vmlinux` SHA256：`f94ac2f435a0388db04bcd153593b84800fdf0467fa22ecb893988fc26ab3a89`。

反汇编确认普通事件入口 `mhi_dev_send_event`（0xc0963f04）、异步完成入口 `mhi_dev_send_completion_event_async`（0xc0966e40）、完成批处理 `mhi_dev_flush_transfer_completion_events`（0xc0962384）及 EDMA MSI 入口 `mhi_trigger_msi_edma`（0xc09644d4）。后者在缓存为空时调用 `ep_pcie_get_msi_config`，缓存地址与 data 基值；0xc09645cc 将 vector 加到基值，随后提交4字节 EDMA 写请求。另有 `ep_pcie_trigger_msi` 发送分支。

这证明存在两条发送机制及缓存，尚不证明当前运行命中了哪一条，也不证明缓存已经过期。软件重启不能代替模块真实断电。管理路径恢复后，再读取模块已有 MHI/PCIe/EDMA debugfs、日志及导出的缓存信息，使用同一会话的地址/data 对照；无法取得的字段明确记为未观测，不用主机配置冒充模块实际发送值。

## 构建与验收状态

诊断需要重编内核及 MHI/网络模块；必须使用同一构建的 FIT 和 rootfs。CI 检查实际 initramfs 中的采集脚本与源文件一致。所有 verify 仍为 advisory，保留原始 ITB、可用 IMG 及日志。

本文件描述接口和判读方法。实机实验是否完成、控制查询和管理网络是否恢复，见对应提交后的实测报告，不能由构建成功替代。
