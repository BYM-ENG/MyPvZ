# 交接记录

## M03 本机验收通过 — 2026-10-27

起点 main/10c965c，工作区干净，与远程一致；前置 M00–M02 已验收。遵循 GPT-6.1 Sol / Ultra 要求，窄范围子代理显式指定相同模型及强度，未自行切换模型。只做 M03，M04 未开始。

交付 SourceAssets/M03 的 150 原媒体及 manifest.json、/Game/PvZ 下 275 个 uasset（127 Texture、127 Sprite、14 SoundWave、7 Flipbook）、导入/校验/模拟脚本和 docs/ASSETS.md。9 张坚果占位帧与卡牌共用资源。源快照约 8.6MB，UE 包约 36.6MB，最大单包约 18.7MB；原型 EXE/DLL 不入库，原型未修改。

复现（先关闭编辑器；均支持 -EngineRoot E:\develop\UE_5.8）：

~~~powershell
.\Scripts\Build-Editor.ps1
.\Scripts\Import-M03.ps1
.\Scripts\Validate-M03.ps1
.\Scripts\Import-M03.ps1
.\Scripts\Validate-M03.ps1
.\Scripts\Smoke-M03.ps1
~~~

本轮以上最终全部退出 0。首次导入创建 275，第二次新增 0 / 复用 275，全部包 SHA256 不变。两次新进程验证 150 源映射、127 图像/Sprite、7 组 123 帧槽、14 段解码音频、275 注册身份及 424 条硬/软包依赖边，无缺失或额外资源。图形编辑器临时模拟的 7 Actor 均从帧 0 推进至 1，正常退出；未保存临时地图或改默认地图。

M02 的 SoundWave_0 在新进程强制磁盘重扫后不存在。安装源码显示 WAV 导出会在原 outer 创建临时 SoundWave 副本，可能留下临时注册/缓存项；本轮未删除/重建原音频包。校验不再过滤次级项；不要在 WAV 导出后把整个资产目录另行全部保存。相同源快照重复导入直接复用，源身份变化则拒绝静默覆盖。

音频：6 WAV / 8 MP3 直接导入 UE 并回读非静音 PCM16。4 WAV 导出逐字节一致，bong/hitZB 最大误差 1；安装源码已确认 SoundExporterWAV 经浮点缓冲区重写 PCM16，不能声称所有导入 PCM 位级精确。两轮 14 段导出 PCM 哈希一致。细节见 validation/M03.md。

环境：首次沙箱内 .NET 启动失败，沙箱外实际完整构建通过（9 动作，78.21秒）。图形脚本改用 UnrealEditorSubsystem 相机接口；最小项目 LevelEditorSubsystem 未实例化时，其默认对象的无状态方法转发 GUnrealEd 播放请求，已核对本机实现并实际通过。初次失败的临时编辑器已关闭，最终无残留编辑器进程。

原始证据在忽略目录 Saved/Logs/M03-*、Saved/Diagnostics/M03（含 import-first.json、import.json、validation-first.json、validation.json、packages-first.csv、packages-repeat.csv、runtime.json）。提交只含源副本、必需 uasset、脚本及简明文档。

限制：原 FPS 未知，暂配 8fps；坚果仍是卡牌占位，M11 再补；2 JPG 只检查尺寸/不透明 alpha；未逐帧人工视觉验收、未全音频听辨，模拟使用 nosound；未 cook/打包。工厂默认材质导入警告存在，但已保存的显式材质全部验证通过；图形 Editor 仍有 UE UnifiedErrorTest/AutomationTest 启动错误，不声称全日志零错误。

额度：开始 19% / 33%，主要验证前 35% / 36%，验收整理时 44% / 37%（五小时/周，共享账户，仅观察值）；提交后最终读数见聊天报告。

下一步：仅用户指定 M04 时，先读 STATUS/HANDOFF 和 PLAN 的 M04，按 ASSETS.md 的 /Game/PvZ 稳定路径开始摄像机、草坪和网格命中，不重建工程。Prepare-M03.ps1 只用于快照建立/核对；日常导入及校验不依赖原型目录。
