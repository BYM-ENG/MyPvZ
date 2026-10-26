# 本机环境与 M00 环境变更

记录日期：2026-10-26，Asia/Hong_Kong。其他机器仍需自行检查，不能直接沿用本机路径。

| 项目 | 已观察到的值 |
|---|---|
| 引擎 | UE 5.8.2，Changelist 56702186 |
| 安装目录 | `E:\develop\UE_5.8` |
| Visual Studio | Community 2022 / 17.14.35 |
| MSVC | 14.44.35207 |
| Windows SDK | 10.0.26100.0 |
| NETFXSDK | M00 补齐 4.8，目录 `C:\Program Files (x86)\Windows Kits\NETFXSDK\4.8` |

## 已执行的环境修复

首次受限环境中的 dotnet 启动停顿，没有进入编译，也没有生成 UBT 日志。停止本次构建启动的进程后，以普通本机权限（脱离工具沙箱）执行，UBT 正常运行，报告缺失 NetFxSDK：

```text
Unable to instantiate module 'SwarmInterface': Could not find NetFxSDK install dir
```

检查本机 Windows Kits、SDK 注册表和现有安装目录后确认缺失。随后补齐微软官方 .NET Framework 4.8 Developer Pack：

- 官方入口：https://dotnet.microsoft.com/en-us/download/dotnet-framework/net48
- 官方安装文件：https://download.microsoft.com/download/6/4/2/642ec242-448b-49a1-8371-5d9c202eaa46/NDP48-DevPack-ENU.exe
- 文件大小：147605328 bytes。
- Authenticode：Valid，签名机构 Microsoft Corporation。
- SHA-256：`B37882CDA5610B291B2A984E4C2270F67A448F79D6B1F78337736C95B35C5A7F`。
- 安装参数：`/q /norestart /log <本地日志路径>`；退出码 0，未重启机器。
- 安装包与原始安装日志位于仓库忽略目录 `Local/Dependencies`，不上传 Git。
- 未修改引擎源码、证书、安全策略或注册表检测逻辑。

## 缓存与构建

检查时 C 盘可用空间约 5.8 GB，E 盘约 59 GB。脚本将临时目录和 .NET 用户目录限定到本项目 `Saved`，派生数据缓存限定到项目 `DerivedDataCache`；不修改系统环境变量。

构建工具可能仍需访问系统工具链和用户级 UBT 配置，因此在限制进程权限的自动化环境中，可能需要批准本机构建命令。不要靠禁用 SDK 检查来伪造通过。

## 中文路径兼容处理

补齐 SDK 后，MSVC 在读取无 BOM UTF-8 响应文件时错误解析中文项目路径，产生 `C1083`，无法创建 PCH。UE 默认的 `/utf-8` 源码选项没有解决响应文件路径编码。

`Build-Editor.ps1` 因此在非 ASCII 项目路径下临时使用 `subst` 创建本项目的 ASCII 盘符别名，默认 `P:`，可用 `-BuildDrive` 指定其他未占用盘符。构建参数、临时目录和缓存路径使用该别名，正常完成或异常退出后由 `finally` 清理本次映射；不移动仓库，不修改引擎，不关闭 PCH。

首次切换别名前，旧 Unicode 路径已写入中间产物缓存。M00 将这些生成文件保存在忽略目录 `Saved/Diagnostics/Intermediate-BeforeAscii`，然后干净生成。后续请使用脚本构建，避免重新混入中文根路径的编译缓存；不要在编辑器内直接触发源码构建。

## M01 打包路径与依赖

M01 实际发现 UAT 的 `-remoteini` 嵌套引号无法正确处理工程位于 `P:\` 盘符根目录的情况。`Package-Windows.ps1` 因此启用 Common 的可选 `-MapParent`：临时映射父目录，工程使用 `P:\UE5Migration`，归档仍写入真实中文路径。M00 构建脚本的默认行为保留；不要直接复用根盘符路径调用 BuildCookRun。打包结束后清理本次盘符映射，不移动或复制原型。

本机 VS 实际目录为 `E:\Microsoft Visual Studio\2022\Community`。引擎本版 `-prereqs` 归档 `vc_redist.x64.exe` 和 `vc_redist.arm64.exe`；旧版 `UEPrereqSetup_x64.exe` 不存在是此版本的布局，不能据此判定缺依赖。M01 没有安装额外软件；干净机器上的依赖安装尚未验收。

Cook / IoStore 阶段自动使用 Zen package store，数据位于项目 `DerivedDataCache/Zen`，引擎同时写入用户 AppData 下的 Zen 程序/版本元数据；这与 M00 配置的文件系统 DDC 是不同用途。独立游戏从已归档的 pak / IoStore 容器加载，本次启动时 P: 已不存在。
