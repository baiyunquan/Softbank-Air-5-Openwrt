# CKB01：从 OpenWrt 管理原厂 SDX55 Linux

此功能由 `ckb01-oem-tools` 提供，默认随 CKB01 镜像安装。SDX55仍运行自己的原厂Linux；SSH登录OpenWrt得到的是IPQ root，下面的工具通过MHI管理网络访问模块root。

## 模块命令与文件传输

```sh
ckb01-oem status
ckb01-oem network
ckb01-oem exec 'id; uname -a; cat /sys/devices/soc0/machine'
ckb01-oem exec 'uname -a > /tmp/air5-module-info.txt'
ckb01-oem pull /tmp/air5-module-info.txt /tmp/air5-module-info.txt
ckb01-oem push /tmp/air5-module-info.txt /tmp/air5-module-info-copy.txt
```

`exec`接受**一个shell命令字符串**，返回SDX55的stdout、stderr和退出码。命令在模块root上下文执行。文件操作顺序为：`pull 远端 本地`、`push 本地 远端`。

也保留原厂兼容接口：

```sh
oatprsync -e 169.254.10.2 'uname -a > /tmp/module.txt'
oatprsync -g 169.254.10.2 /tmp/module.txt /tmp/module.txt
```

原始 `-e` 不直接取回命令输出，日常优先用 `ckb01-oem exec`。代理命令使用TCP21666/cmdagentd；文件传输使用TCP20208/oatprsyncd。

超时默认每次代理调用30秒，可显式调整：

```sh
CKB01_OEM_TIMEOUT=120 ckb01-oem exec '你的耗时命令'
```

传输超时或Ctrl-C不会保证远端命令停止；工具不会自动重放命令。未取得退出码时会报告模块 `/tmp/ckb01-oem.*` 证据位置。大文件直接用pull/push，避免通过exec生成另一份临时输出。

## ADB：启用、进入shell与恢复

```sh
ckb01-adb enable
ckb01-adb status
ckb01-adb shell
ckb01-adb shell 'id; uname -a'
ckb01-adb pull /tmp/air5-module-info.txt /tmp/adb-module-info.txt
ckb01-adb push /tmp/adb-module-info.txt /tmp/adb-module-info-copy.txt
ckb01-adb disable
```

shell/pull/push会按需调用enable。原厂adbd的TCP端点为模块管理地址 `169.254.10.2:5555`，OpenWrt上的标准adb客户端负责连接。它提供模块Linux shell，不依赖USB枚举或DIAG节点。

enable的行为：

1. 通过板型和PCI父设备发现IP_SW0，为其配置169.254.10.1/24；无需等待QMI、IP_HW0或SIM联网成功。
2. 通过原厂命令代理核对SDXPRAIRIE/ARMv7/root身份。
3. 将控制脚本和ARMv7属性库上传到模块 `/tmp/ckb01-adb`。上传采用临时文件再rename，避免截断正在被adbd映射的共享库。
4. 首次启用记录原adbd服务是否运行以及GPIO92的方向/值；暂停原服务，以LD_PRELOAD启动**原厂未修改的** `/sbin/adbd`。
5. 属性库只让service.adb.tcp.port返回5555，其余property_get保持原厂默认值行为。原厂property_set是空实现，常规adb tcpip不能据此启用TCP。
6. 连接并显示模块id/uname。重复启用复用同一进程和首次快照；若运行中的payload版本与新文件不同，要求先disable再enable。

disable只终止带有本工具LD_PRELOAD标记、PID/exe匹配的临时adbd，再按快照恢复原服务及GPIO92。原厂 `/etc/launch_adbd` 自身会将GPIO92置1，所以恢复服务后还会恢复之前记录的GPIO状态。不更改GPIO104/105，不自动改变USB composition，不修改systemd enable状态。

ADB默认**不会随OpenWrt开机自动开启**。模块重启/断电后/tmp清除，原厂启动服务照常运行；重新执行enable即可。OpenWrt单独重启、模块未重启时，模块上的首次快照仍然可用。

本功能不自动执行EDL、重启、MHI reset、SIM解锁、NV或flash修改。用户主动在root shell输入的命令按正常shell语义执行。

## 从电脑使用

交互式shell：

```sh
ssh -t root@192.168.5.1 ckb01-adb shell
```

希望使用电脑上的ADB时，先在OpenWrt执行enable，然后建立隧道：

```sh
ssh -N -L 127.0.0.1:15555:169.254.10.2:5555 root@192.168.5.1
# 在电脑另一终端
adb connect 127.0.0.1:15555
adb -s 127.0.0.1:15555 shell
```

## 运行库、来源和重建

- 原厂AArch64客户端和旧版musl/OpenSSL/C++/RPC依赖在 `/usr/lib/ckb01-oem/runtime`；`/usr/bin/oatprsync` 显式调用该私有加载器，不替换OpenWrt全局库。
- 闭包包含原厂ELF的所有DT_NEEDED依赖；另加入libconfigapi通过dlopen加载的libz.so。
- 不包含ART、SIM/NV、IMEI、密码或每台设备的配置文件。
- OpenWrt原生包依赖：ckb01-modem、adb、coreutils-timeout、jsonfilter、ip-full及其构建系统解析的依赖。coreutils-timeout的真实二进制路径为 `/usr/libexec/timeout-coreutils`，参考[上游包定义](https://github.com/openwrt/packages/blob/master/utils/coreutils/Makefile)。
- 原厂运行库SHA256清单安装在 `/usr/share/ckb01-oem/runtime-provenance.json`；ARMv7 payload清单在同目录adb-payload.json。
- 本版13个原厂运行文件取自2026-10-21当前设备的IPQ系统（Linux 4.4.60、2023-04-01固件），逐文件核对设备侧SHA256。旧本地备份的库版本存在差异，未与当前客户端混装。

重新收集本地原厂IPQ备份的依赖：

```sh
python3 scripts/ckb01-oem-bundle.py --source-root /path/to/extracted_root \
  --source-label '固件版本与提取日期'
```

重新编译ARMv7属性库需要主机clang/lld：

```sh
sh packages/ckb01-oem-tools/payload/build.sh
```

如果产物变化，应同时更新payload/provenance.json中的SHA256和size，重新记录其硬件验收状态。ARMv7库仅供SDX55加载；不能用IPQ AArch64工具链替代编译。包关闭自动strip以保留原厂哈希，并避免用AArch64 strip处理ARMv7 payload。

## 状态与排查

```sh
ckb01-modem discover
ckb01-oem status
ckb01-adb status
ckb01-oem exec 'cat /tmp/ckb01-adb/adbd.log'
ckb01-diag /tmp/air5-diag.tar.gz
```

- discovery的ok=false可能只是QMI/数据接口未就绪；只要management接口存在，本工具仍可建立模块管理路径。
- IP_SW0不存在时工具报错退出，不触发重置或为其他板型套用参数。
- 代理服务不可达时，先保留日志检查管理链路；不自动重启模块。
- 发现非本工具管理、且不属于原adbd服务的adbd进程时，不将其强行结束。
- 远端暂存恢复脚本可从原厂IPQ环境手动调用：`oatprsync -e 169.254.10.2 '/bin/sh /tmp/ckb01-adb/control.sh stop'`。模块已重启、/tmp清空时该脚本不再存在，原厂服务由正常启动恢复。

`ckb01-diag`只采集本地管理发现及payload信息，不会自动启用ADB。

## 给现有OpenWrt安装用户态覆盖包

完整新镜像会自动安装所有依赖。如果使用单独生成的 `ckb01-oem-management-overlay.tar.gz`，它包含OEM运行库、控制脚本和ARMv7 payload，**不包含OpenWrt原生adb/timeout等包**。现有系统应已包含ckb01-modem，再从与运行固件匹配的包源安装：

```sh
apk add adb coreutils-timeout jsonfilter ip-full
mkdir -p /tmp/ckb01-oem-install
tar -xzf /tmp/ckb01-oem-management-overlay.tar.gz -C /tmp/ckb01-oem-install
sh /tmp/ckb01-oem-install/install.sh
```

使用opkg的固件采用对应的 `opkg install`。安装脚本先检查CKB01板型、依赖及归档文件摘要，缺少依赖时退出，不会在缺失环境中写入半套工具。安装本身不会启用模块ADB。RAM根上的覆盖安装随主控重启丢失；持久root或包含本包的新固件可保留工具。

在构建电脑生成覆盖包：

```sh
python3 scripts/ckb01-oem-bundle.py --overlay /path/to/ckb01-oem-management-overlay.tar.gz
```

## 验收边界

属性库此前已在本机SDX55上获得TCP ADB ARMv7 root shell；该记录证明payload的可行性。新增的固件包、命令输出包装及完整启用/恢复流程仍需在包含本改动的新OpenWrt实机启动后验收，不能把先前的临时实验当成新版固件已经通过。CI会检查实际initramfs内容和不可变运行库哈希，失败只警告并继续上传原始ITB/可用IMG/日志。

## PCIe DIAG 与 EFS

新增 `ckb01-diag-efs`，默认由 S97 服务开启模块原厂 PCIe 路由；支持 `status`、`enable`、`disable` 以及只读 EFS `ls/stat/pull/backup`。具体命令、退出恢复和实测记录见 [DIAG/EFS 文档](CKB01_DIAG_EFS.md)。原有 `ckb01-diag` 仍是被动采集入口，不会因此开启 DIAG。
