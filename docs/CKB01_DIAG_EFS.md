# CKB01 蜂窝管理与 DIAG EFS

## 已固化的通信路径

- PCIe0 使用现有 SoC GICv2m 接收 MSI；源码修复提交 `afc8fcf3`。同一内核的 DWC/GICv2m 回切已证明这会恢复 OEM IPA 完成中断，详见 [MSI 实验](CKB01_MHI_GICV2M_20261023.md)。软件事件消费默认关闭。
- `ckb01-modem` 通过 QMI14 / QRTR 查询模块；`ckb01-oem` 通过 IP_SW0 命令/文件代理操作 SDX55 Linux。DIAG 与这些入口独立。
- `ckb01-modem discover` 新增 `diag` 字段，按匹配 CKB01 的 PCI 父设备发现 `qcdm` 端口；不固定 `wwan0`。DIAG 缺失不会使原有管理发现失败。

## 默认开机开启 PCIe DIAG

`ckb01-oem-tools` 安装 `S97ckb01-diag-route`。服务在 IPQ 上异步运行，每30秒尝试连接模块：

1. 检查 `oppo,ckb01` 和 `17cb:0306 / 17cb:010c` 对应的设备。
2. 通过已有命令代理检查模块为 root / ARMv7 / SDXPRAIRIE。
3. 在 SDX55 `/tmp` 部署路由控制脚本，核对原厂 `test_diag` 的已验证 SHA256。
4. 启动原厂 `/usr/bin/test_diag -p 7`，保持其 `/dev/diag` 会话；这是原厂 `pcie-diag` 脚本的机制。
5. IPQ 对实际 DIAG 节点执行 EFS HELLO 成功后，写入 `/tmp/ckb01-diag-efs.status` 的 `ready` 状态。

仅发现节点、仅存在进程都不标记成功。失败保留有线和 Wi-Fi 管理，写日志并重试；不执行 MHI reset、NV 写入或 PDC 切换。

模块 `/data/debug_transport.conf`、启动服务、GPIO和基带保持原样。路由进程退出后，内核恢复原厂默认路由；本机已验证默认 USB -> 临时 PCIe -> USB。进程退出或管理链路故障的恢复结果，以实机查询为准，不以本地状态文件替代验证。

### 命令

```sh
ckb01-modem status
ckb01-modem --device qrtr probe --transport-only
ckb01-oem exec 'id; ls -la /data /usr/lib/oppo'

ckb01-diag-efs status
ckb01-diag-efs hello
ckb01-diag-efs ls /
ckb01-diag-efs ls /policyman
ckb01-diag-efs ls /nv/item_files
ckb01-diag-efs stat /policyman/hardware_band_filtering.xml
ckb01-diag-efs pull /policyman/hardware_band_filtering.xml /tmp/hardware_band_filtering.xml
```

`pull` 的本地目标必须尚不存在；读取器不会覆盖已有最终文件或 `.partial`。`backup PATH LOCAL` 导出可访问的逻辑 EFS 文件树，不能当作 NAND 原始镜像或原子快照。保护路径的拒绝会作为错误记录。

```sh
# 当前开机周期停用；后台重试与服务 restart 均保留这个状态
ckb01-diag-efs disable

# 显式重新启用
ckb01-diag-efs enable

# 后续开机也不自动启用
/etc/init.d/ckb01-diag-route disable
/etc/init.d/ckb01-diag-route stop

# 恢复默认开机行为；若本次已手工 disable，另执行 enable
/etc/init.d/ckb01-diag-route enable
/etc/init.d/ckb01-diag-route start
ckb01-diag-efs enable
```

本地锁串行化本工具的读取、启停和后台 HELLO；重复 enable 复用同一模块 PID。PID、启动时间和命令行同时核对，不能因 PID 复用误杀其他进程。原厂进程命令行可能没有末尾 NUL，已实机验证并覆盖回归测试。模块程序摘要不匹配或已有非本工具管理的 `test_diag` 时拒绝接管。

停止需要管理代理可达。服务停止会先设置停止标记，最多等待30秒让已在执行的后台步骤释放锁，再停止其模块进程。若失联或锁等待超时，停止会报告未确认，不通过复位模块掩盖错误。直接用其他程序并行读取同一 DIAG 节点会绕过本工具锁，应先协调关闭已有会话。

## 包与校验

- `/usr/sbin/ckb01-diag-efs`：主控上的启停、查询与 EFS 客户端。
- `/usr/libexec/ckb01-diag-reader`：随 OpenWrt 目标编译的 C 读取器，支持 HDLC CRC、匹配响应、目录和文件读取检查。协议实现取自本项目已有 `tools/diag_efs_read.c`，参考 `qcdm-efs2` 提交 `309997a175f895f44908b6d2878c9c4813044f89`。
- `/usr/lib/ckb01-oem/diag-route-control.sh`：发送至模块 RAM 的路由进程控制器。
- `/etc/init.d/ckb01-diag-route`：procd 服务；关机时在网络拆除前尝试停止模块进程。

读取器仅实现 DIAG 版本、HELLO、STAT、READLINK、OPENDIR/READDIR/CLOSEDIR、只读 OPEN/READ/CLOSE。没有 EFS/NV 写入、重启或 EDL 操作。

FIT verify 检查实际安装路径并比较脚本内容，fixture 同步更新。校验仍是 advisory，不影响原始 ITB/可用 IMG/日志上传。原有 `ckb01-diag` 仅收集本地 DIAG 状态，不因此开启路由或更改管理网口。

## 2026-10-23 实测

通过 SSH `root@192.168.5.1` 完成，未使用串口、软件消费或 MHI reset：

- 蜂窝管理器10类查询成功：DMS版本/频段、UIM、NAS偏好/驻网/RF/系统/信号、PDC当前配置及列表。
- 原厂代理返回 SDX55 uid0 / ARMv7 / 4.14.206-perf，能列 Linux 文件。
- 模块本机 `/dev/diag`：EFS HELLO、35个根目录条目，39帧，CRC错误0。
- IPQ MHI DIAG：PCIe路由启用后列出35个根条目、8个 policyman 条目、15个 nv/item_files 条目，CRC错误0；DIAG RX ER3中断从0增加至39。
- 实际读取741字节 `hardware_band_filtering.xml`，SHA256：`8213e7d173cebf44feda35da3d251b06c66743366a59092a2d7e759a2a260f00`。
- 关闭临时原厂路由进程后，MHI EFS HELLO恢复为超时，证明路由条件；持久配置摘要未变化。
- 新打包脚本已经在当前系统验证 enable、重复 enable、ls、disable 和 procd 运行；仍需新完整镜像的冷启动验收。

完整原始现场数据保存在本机项目 `research/ckb01-control-diag-20261023/`。蜂窝通信成功不等于驻网成功；本轮未改变 SBM/CU、SIM锁、频段或拨号配置，未把 n78/蜂窝联网标为通过。

曾在读取模块诊断 debugfs 文件期间发生原厂命令/文件服务中断；具体原因尚未证明，冷启动后恢复。新服务不读取该组文件。

提交前还验证了：手动 disable 后 restart 仍保持停用；显式 enable 后恢复；重复 enable 使用同一 PID；停用后 `_step` 不重新启动；procd 服务在运行，S97/K10 链接存在；新客户端读取741字节文件与前述摘要一致。模块持久配置摘要保持 `aa58088040b7de83054e3dcc50b4770fa4bd3af58dafc44835d812acab910edc`。当前设备的服务已重新启用。提交前自动测试101项全部通过，覆盖停止时已有后台步骤持锁、控制器升级、手动停用、PID复用、HDLC HELLO 和实际安装路径。新整包固件尚未重编译或进行冷启动验收。
