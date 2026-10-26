# MyPvZ — UE5 二维塔防迁移

基于现有 Windows 原型及素材，在 Unreal Engine 5.8.2 中重建二维塔防游戏。采用 C++、Paper 2D、UMG，目标平台为 Windows x64。

当前阶段：**M01 空场景 Windows Development 打包已完成并通过本机启动、退出验收**。M00 已完成，下一阶段为 M02（未开始）；当前工程不含原版素材或玩法。

## 从这里继续

1. 阅读 [当前状态](docs/STATUS.md)。
2. 阅读 [最新交接记录](docs/HANDOFF.md)。
3. 根据 [模块计划](docs/PLAN.md) 只执行用户指定的模块。
4. 对照 [规则基线](docs/RULES.md)、[架构约定](docs/ARCHITECTURE.md) 和对应验证记录开展工作。

每个模块允许在新聊天中继续；磁盘和 Git 记录是进度依据，不依赖完整聊天历史。[继续提示词](docs/CONTINUE.md) 可直接复制。用户要求使用 **GPT-6.1 Sol / Ultra**，不可自行切换模型。

## 环境与构建

- Unreal Engine **5.8.2**，此机安装在 `E:\develop\UE_5.8`。
- Visual Studio 2022，安装 C++ 编译工具、Windows SDK 和 .NET Framework 4.8 SDK（Developer Pack）。
- 关闭本工程的 Unreal Editor 后执行：

```powershell
.\Scripts\Build-Editor.ps1 -EngineRoot 'E:\develop\UE_5.8'
```

中文工作目录请使用此脚本构建。它会临时将本项目映射到空闲的 `P:`，避开 MSVC 的响应文件路径编码问题，结束后自动移除映射。如果 `P:` 已被占用，可追加 `-BuildDrive R` 指定其他空闲盘符；不会覆盖已有盘符。

然后使用上述引擎打开 `MyPvZ.uproject`。具体自检命令与结果见 [M00 验证记录](docs/validation/M00.md)，本机依赖与环境变更见 [环境记录](docs/ENVIRONMENT.md)。

关闭编辑器后，可创建空场景的 Windows Development 包：

```powershell
.\Scripts\Package-Windows.ps1 -EngineRoot 'E:\develop\UE_5.8'
```

成功输出位于 `Packages/M01-Windows-Development/<时间戳>/Windows`，运行其中的 `MyPvZ.exe`；分发时需要完整 Windows 目录。空黑场景是当前阶段的预期结果，用 Alt+F4 正常退出。此脚本使用 `P:\UE5Migration` 形式的临时路径，支持 `-BuildDrive`，结束后清理映射。完整包不进入 Git；本机实际结果与限制见 [M01 验证记录](docs/validation/M01.md)。

## 仓库约定

- `Source`、`Config`、`Content`、`Scripts` 和 `docs` 是交付内容。
- 不提交 `Binaries`、`Intermediate`、`Saved`、派生缓存或原版调试运行库。
- 本机旧原型位于仓库外的同级 `..\protptype`。它不是构建依赖，M00 不修改它。
- 后续资源导入在 M02 / M03 开展；旧原型没有源码，无法承诺逐行恢复原代码。
