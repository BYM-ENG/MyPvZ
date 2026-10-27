# 资源目录合同（M03）

完整逐文件清单为 `SourceAssets/M03/manifest.json`：保留 150 个原始媒体路径、大小、SHA256、源副本、目标 UE 路径和动画帧映射。PNG 为 134 张，JPG 为 2 张，WAV 为 6 段，MP3 为 8 段。原型 EXE 和 3 个调试 DLL 不属于导入素材，不入库。

生产资源根目录为 `/Game/PvZ`：127 个 Texture2D、127 个 PaperSprite、14 个 SoundWave、7 个 PaperFlipbook，共 275 个包。原本字节相同的坚果卡牌及 9 张占位帧共用一个 Texture/Sprite；全部 150 个源文件仍各自保留映射。`/Game/M02` 是独立的历史导入试验，后续玩法使用 PvZ 目录。

## 动画

| 原始目录 | 帧号 | Flipbook |
|---|---|---|
| res/zhiwu/0 | 1–13 | /Game/PvZ/Flipbooks/FB_Peashooter |
| res/zhiwu/1 | 1–18 | /Game/PvZ/Flipbooks/FB_Sunflower |
| res/zhiwu/2 | 1–9 | /Game/PvZ/Flipbooks/FB_WallnutCardPlaceholder |
| res/zm | 1–22 | /Game/PvZ/Flipbooks/FB_ZombieWalk |
| res/zm_eat | 1–21 | /Game/PvZ/Flipbooks/FB_ZombieEat |
| res/zm_stand | 1–11 | /Game/PvZ/Flipbooks/FB_ZombieStand |
| res/sunshine | 1–29 | /Game/PvZ/Flipbooks/FB_Sun |

共 123 个帧槽，按整数帧号排序，每槽 frame_run=1；初始配置统一为 8 fps，原型 FPS 未知。坚果组是卡牌占位，M11 才补真正场上图，不应当作已完成的坚果动画。

动画 Texture/Sprite 名采用 `T_<组名>_<两位帧号>` / `S_<组名>_<两位帧号>`，位于 Textures / Sprites 子目录。坚果帧引用卡牌的 `S_res_Cards_card_3`，不是九个重复资源。

## 静态图与声音

静态图片为 res 下的 `1.jpg`、`bg.jpg`、`bar5.png`、`fail.png`、`menu.png`、`menu1.png`、`menu2.png`、`win.png`，以及 bullets 的两张图、Cards 的三张图。目标名为 `T_res_<文件名>` / `S_res_<文件名>`；子目录转换成下划线，例如 `T_res_bullets_bullet_normal`。草坪背景 `T_res_bg` 为 1400×600，菜单/结算图为 900×600；实际网格和布局由 M04/M18 校准。

WAV 包括 `bong`、`eatplant`、`hitZB`、`seed`、`showZB`、`sunshine`，目标名为 `/Game/PvZ/Audio/SW_res_<名称>`。MP3 包括 `begin`、`eat`、`game`、`lose`、`menu`、`seedlift`、`splat`、`win`，目标名为 `SW_resx_<名称>`。引擎 5.8.2 SoundFactory 直接导入 MP3，未额外转码生成源文件；`menu.MP3` 原始大小写保留在清单中。全部音频初始 looping=false，事件触发与音乐循环由 M16 实施。

## 导入与校验

关闭编辑器后运行：

```powershell
.\Scripts\Import-M03.ps1
.\Scripts\Validate-M03.ps1
```

以上命令只依赖库内 SourceAssets，不需要原型目录，也不需要外部 Python 包。`Prepare-M03.ps1` 仅用于首次从原型建立源快照及再次核对；默认读取 `../protptype`，可通过 `-PrototypeRoot` 指定。所有脚本支持 `-EngineRoot`，默认 `E:\develop\UE_5.8`。

导入以固定路径和 `MyPvZ.SourceSHA256` / `MyPvZ.SourcePath` 元数据辨认冻结快照。未变化媒体及已有 Sprite/Flipbook 直接复用，不再次覆盖 SoundWave；校验脚本独立验证全部实际设置和绑定。源文件或已有资源身份不符时失败，要求显式审查更新，不静默覆盖。此流程验证相同源快照的重复导入，不提供任意变化素材的自动更新工具。

图片为 1 pixel / Unreal unit，中心 pivot、无碰撞、完整源矩形、透明 Unlit 材质，sRGB、Nearest、Pixels2D、无 mip。PNG 导出回读验证每个 alpha 字节及可见 RGB；透明像素底下的 RGB 可由 UE 填充。JPG 检查尺寸和不透明 alpha，未独立比较有损 JPEG 的颜色解码结果。

声音导出检查 PCM16 声道/长度/采样率与非静音；WAV 与原 PCM 比较，允许引擎导出路径带来的最多 1 个量化单位误差，并明确记录是否逐字节相同。MP3 检查引擎解码后的 PCM，不宣称与独立解码器位级一致。重复验证比较全部 14 段导出 PCM 的哈希。

`Smoke-M03.ps1` 以图形编辑器在未保存的临时世界中模拟 7 组 Flipbook，验证实际帧号推进并自动退出；使用 RenderOffscreen / nosound，不创建玩法地图，不代替听辨或逐帧人工视觉验收。结果及完整日志在忽略目录 `Saved/Diagnostics/M03`、`Saved/Logs`。本模块实际证据见 `validation/M03.md`。
