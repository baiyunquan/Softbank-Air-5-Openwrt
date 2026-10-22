# CKB01 模块 MSI 目标对照实验，2026-10-23

## 结论

本次抓到了**当前窗口内**管理网络通道46/47的原厂IPA批量MSI发送日志。软件计划发送的地址、数据与主机硬件寄存器一致，DWC对应向量接收计数仍为零。

因此，管理网络这条路径的调查应推进到 **SDX55 IPA异步写入／PCIe出站地址转换与DWC MSI捕获之间**。已经排除本样本中发送日志所示MSI地址或base+vector算错；仍没有PCIe总线抓包，不能把软件打印值当成实际TLP字段，也不能宣布IPA高位地址必然错误。

本轮没有更改驱动、PCIe寄存器、PDC、NV或SIM设置，没有开启蜂窝数据。仅执行一次新的有界诊断窗口，结束后已关闭。DIAG实际收发仍未验收。

## 环境与执行

- 用户明确要求执行上一轮提出的目标地址/数据对照实验。
- 同一个启动实例：boot ID `4e64cdab-6fad-4cc9-964b-bc0607e8a470`；实验前uptime约34974秒，已经连续运行约9.7小时。
- M0、AMSS、dead=0；进入实验时软件消费关闭，bootstrap和其他诊断没有运行。
- 使用现有`ckb01-mhi-debug compare`；baseline为trace-only，随后一次poll，最后停用并发起新请求。
- 主机id3为baseline，id4为poll；窗口约uptime35023.84–35053.84秒，`consumed=1866 rounds=914 rc=0`。
- 上限保持30秒、20ms请求间隔、每环每轮64、总4096；正常IRQ保持启用。
- 模块RAM日志级别`mhi_msg_lvl`临时4→0，约2秒后恢复4；在模块`/tmp`先保存完整dmesg，再分别筛选发送记录与完成回调，避免上一轮过滤遗漏。
- 在同一窗口内取回完整模块日志和debugfs目录；没有增加第二个poll窗口。

## 模块发送值与主机配置

模块本次新记录（模块和主机uptime不是同一时钟）：

```text
[35035.470293] [mhi_dev_schedule_msi_ipa] Sending MSI 6 to 0x44d79000 as data = 0x16 for ch 47 msi_count 468, ereq flush_num 468
[35035.473530] [mhi_dev_schedule_msi_ipa] Sending MSI 5 to 0x44d79000 as data = 0x15 for ch 46 msi_count 509, ereq flush_num 509
```

保存的dmesg还包含上一轮uptime315秒的旧记录；分析时明确选取35035–35037秒的新记录，共28条发送日志，涉及通道46/47。**未取得本窗口通道14的同类发送打印，不能把管理网络的实测地址直接当作QMI发送抓取结果。**

| 项目 | 模块软件发送记录 | 主机期待值 |
| --- | --- | --- |
| MSI地址 | 0x44d79000 | 0x44d79000 |
| IP_SW0 TX相对向量5 | data0x15 | base0x10+5=0x15 |
| IP_SW0 RX相对向量6 | data0x16 | base0x10+6=0x16 |

这次还读回了**真正的DWC DBI寄存器**，没有只依赖内核缓存：

```text
0x820 MSI_ADDR_LO = 0x44d79000
0x824 MSI_ADDR_HI = 0x00000000
0x828 ENABLE      = 0xffffffff
0x82c MASK        = 0xfc00fffe
0x830 STATUS      = 0x00000000
```

读取方法是root port的PCI配置sysfs，偏移0x820共20字节，只读。固定内核`dw_pcie_own_conf_map_bus()`将root port配置偏移映射到`dbi_base+where`，对应寄存器定义可在仓库`ckb01-pinned-dwc`源文件fixture复查。没有创建/dev/mem，也没有写入寄存器。

## 主机事件与中断结果

| 通路 | baseline | poll期间 | 停止后的新请求 |
| --- | --- | --- | --- |
| 管理ping | 失败，退出1 | 成功，退出0 | 失败，退出1 |
| QMI14只读DMS/UIM | 超时，退出124 | 成功，退出0 | 超时，退出124 |
| QRTR只读DMS/UIM | 成功，退出0 | 成功，退出0 | 成功，退出0 |
| 模块root RPC | 未额外重试 | 成功取回日志 | 未额外重试 |

| DWC hwirq / Linux IRQ | baseline received | 最终received |
| --- | --- | --- |
| 18 / 85，QMI TX对应向量 | 0 | 0 |
| 19 / 86，QRTR/控制RX | 83 | 91 |
| 21 / 88，IP_SW TX | 0 | 0 |
| 22 / 89，IP_SW RX | 0 | 0 |

- 相关DWC位21/22和端点相对向量5/6均未屏蔽；无dispatch_failed。
- 已工作的向量19持续通过同一个parent IRQ17/GIC hwirq84。
- 模块有`mhi_dev_event_rd_offset_completion_cb`和`mhi_dev_event_msi_cb`执行记录，仍不等于主机收到了正确MSI。
- 软件消费再次恢复QMI和管理网络，停用后再次积压。不能把软件消费保留为已修复中断的证据。
- 新采集器的`logread -f`正常记录了本轮内核流，没有上一轮BusyBox dmesg选项错误。

## 新确认的实际发送路径

完整模块日志包含：

```text
[mhi_dev_write_to_host_ipa] device 0x8c4b8000 --> host 0x10044d79000, size 4
```

当前管理网络MSI实际走的是`mhi_dev_schedule_msi_ipa` → `mhi_dev_write_to_host_ipa`的批量异步路径。

原厂vmlinux中`mhi_dev_write_to_host_ipa`反汇编在`0xc0960f40`将高32位OR上0x100，即在IPA侧地址加bit40。本轮成功写入的普通事件和RP也带相同高位，例如`0x100441a2710`和`0x1004530c0cc`。因此这个高位不能直接判为“MSI发送错地址”；它需要结合模块PCIe/IPA出站映射解释，且不应把它未经验证地删掉。

下一项调查固定为：

1. 读取模块IPA/PCIe出站映射，解释`0x10044d79000`如何转换为PCIe目标。
2. 对照正常向量19的发送方式，核查批量IPA路径与直接MSI路径的差异；当前未取得向量19同粒度的发送日志。
3. 核查4字节写入的实际目标/属性及DWC捕获条件，基于具体差异再决定修复位置。

模块debugfs只找到`/sys/kernel/debug/pcie-ep/case`及IPA诊断文件；本轮未向case写入任何测试命令。主机没有现成/dev/mem或devmem命令，DBI读取通过已确认的root配置映射完成。

## 收尾状态与证据

模块日志级别已恢复4；主机`enabled=0 polling=0 dead=0`，无重启、MHI恢复或诊断error。IP_HW0仍DOWN、未产生modem-ready，双频AP和WAN192.168.1.130仍在线。未把这次实验记为蜂窝联网或DIAG成功。

本地证据位于项目根目录`research/mhi-msi-target-20261023/`：

- `preflight.txt`、`postflight.txt`
- `experiment-stdout.txt`、`experiment-result.json`、`experiment-evidence.tar.gz`、`evidence/`
- `module-msi-stdout.txt`、`module-dmesg-raw.txt`、`module-fresh-msi.txt`
- `module-debugfs-inventory.txt`、`module-write-to-host-ipa.disasm`
- `root-dbi-msi-registers.bin`及`.json`
- `uart/`、`evidence-sha256.json`

保留了此次one-shot runner和模块查询脚本供复查，已有启动标记阻止无意重复运行。
