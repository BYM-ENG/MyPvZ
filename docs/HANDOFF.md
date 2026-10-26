# 交接记录

## M01 — 已完成并通过本机验收（2026-10-26）

- 用户授权：仅执行 M01，更新交接、提交并推送到 BYM-ENG/MyPvZ，之后结束。M02 未开始。
- 模型要求：GPT-6.1 Sol / Ultra，不更换；打包脚本子代理显式指定此模型与强度。
- 起点：`main` / `cc7fb7f`，工作区干净；fetch 后与远程一致。M00 已验收，地图哈希保持不变。
- 技术基线：UE 5.8.2 / CL56702186，VS2022，MSVC 14.44.35228（目录 14.44.35207），Windows SDK 10.0.26100.0，NETFXSDK 4.8。

## 本轮交付

- `Scripts/Package-Windows.ps1`：Development Win64 BuildCookRun，显式 Cook 空地图，Stage / Pak / IoStore / Archive / Prereqs；每次独立输出目录和日志。
- Common 新增可选 `-MapParent`，供打包使用 `P:\UE5Migration`；既有 M00 构建脚本默认行为保留，盘符占用保护和 finally 清理保留。
- 脚本核对 UAT 退出码、启动器及 Game EXE、pak / utoc / ucas，并拒绝微软 debug CRT DLL；打包成功后仍需实际图形启动验收。
- 更新状态、环境、README、继续提示词和 `validation/M01.md`。源码、地图、玩法和原型资源未修改。

## 实际验收与复现

关闭编辑器，在仓库根目录执行：

```powershell
.\Scripts\Package-Windows.ps1 -EngineRoot 'E:\develop\UE_5.8'
```

- 成功运行编号 `20261026-233956-779`：Editor + Game 构建 83.89 秒，Cook 60.50 秒，BuildCookRun 199.46 秒；UAT 退出码 0。
- 本机完整包：`Packages/M01-Windows-Development/20261026-233956-779/Windows`。从根目录运行 `MyPvZ.exe`，分发时保留整个 Windows 目录。
- 父代理实际查看 `MyPvZ (64-bit Development PCD3D_SM5)` 空黑窗口；日志确认 D3D12、M00_Bootstrap 和 MyPvZGameMode。启动时编辑器未运行，P: 已移除。
- Alt+F4 后窗口消失；ViewportClosed 退出状态 0，启动器退出码 0，游戏/编辑器进程均已退出。
- 包内微软 debug CRT / PDB / UnrealEditor / PythonScriptPlugin 文件均为 0，包含引擎随附的 x64 / ARM64 VC Redist。
- 完整日志位于忽略目录 `Saved/Logs/M01-Package-Windows-20261026-233956-779`；GUI 日志为 `Saved/Logs/M01-Standalone-GUI-20261026-2343.log`。详细证据和 Game EXE 哈希见 `validation/M01.md`。

## 已处理问题与限制

- 初次 UAT 退出 8：根目录 `P:\` 的 `-remoteini` 嵌套引号解析错误；改用父目录映射后的完整重试已通过。失败日志保留于 `Saved/Logs/M01-Package-Windows-20261026-233726-331`。
- Cook 有 1 条主机名解析警告；运行有空 HUD 的 SpawnActor 警告、NVIDIA TSR 回退和渲染线程变量警告。无 Error / Fatal / Assertion，正常启动退出；细节见验证记录，不宣称日志零警告。
- 只验收现有本机环境的空场景 Development 包；干净 Windows 机器依赖安装、素材效果、玩法、最终 Shipping 包尚未验收。
- 本轮没有安装软件、修改引擎或修改原型。完整运行包、缓存、原始日志和安装程序均不进入 Git。

## 用量观察

开始（约 23:32）：五小时已用 45%，周已用 22%。主要验证前（23:36）：49% / 22%。图形验收后（约 23:46）：56% / 23%。交付前结束快照（23:49）：58% / 24%，同一窗口未重置，观察增幅为 13 / 2 个百分点。账户及子代理共享额度，观察差值不能精确归因。

本文件随 M01 检查点提交，最终提交标识以 Git 历史和远程 main 为准。

## 下一入口

只在用户明确发起后执行 **M02：少量图片/动画/音频导入试验**，验收透明度、帧序、缩放和音频。先核对当前 Git 状态和包记录，按需读取 RULES、ARCHITECTURE 与 M01 验证记录；不要重建工程或提前进行 M03 全量导入。新聊天提示词见 `CONTINUE.md`。

M00 环境修复与完整证据仍保留在 `ENVIRONMENT.md`、`validation/M00.md` 和 Git 历史。
