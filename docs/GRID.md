# M04 草坪与网格合同

入口地图：`/Game/Maps/PvZ_Lawn`（`Content/Maps/PvZ_Lawn.umap`）。打开此地图后 Play；默认启动仍为 M00_Bootstrap。地图只放置一个原生 `AMyPvZBoard`，后续模块在此地图上继续。

背景使用 M03 的 `/Game/PvZ/Sprites/S_res_bg`，1400×600，1 像素 = 1 个本地 Unreal 单位。相机在本地 `(0,1000,0)`，yaw=-90，沿 -Y 观察 X/Z 平面；屏幕向右对应世界 +X。正交宽 1400，宽高比 7:3，保留黑边。背景在 Y=-10，网格命中平面为 Y=0，诊断线在 Y=2。

## 坐标

| 字段 | 约定 |
|---|---|
| 像素 | 原图左上为 (0,0)，X 向右、Y 向下 |
| 可种植矩形 | `[260,980) × [185,485)`，左/上计入，右/下排除 |
| 网格 | 3 行 × 9 列，每格 80×100 |
| 格子编号 | 从 0 开始；FIntPoint.X=列，Y=行；事件参数为 Row、Column |
| 格子中心 | 像素 `(300+80*列, 235+100*行)` |
| 本地世界坐标 | `(像素X-700, 0, 300-像素Y)`，再经过 Board 的 ActorTransform |

这是根据素材草坪校准的新工程边界，不宣称恢复了原程序坐标规则。左上、右下格子中心分别为本地 `(-400,0,65)`、`(240,0,-135)`。

## 原生接口

- `FMyPvZGridLayout` 集中维护行列、背景设计尺寸、左上角和格子尺寸；拒绝无效/非有限参数。`TryPixelToCell`、`TryCellToPixelCenter`、像素/本地世界转换共用这一合同。
- `AMyPvZBoard::PixelToCell`、`CellToWorld`、`RayToCell` 提供 Blueprint 接口。射线先转入 Board 本地坐标，再与 Y=0 平面求交；平行、反向、非法射线及网格外位置失败。
- `AMyPvZPlayerController::ScreenToGrid` 使用本地玩家实际受限投影矩形；先排除视口外和相机黑边，再反投影及调用 Board。屏幕参数是游戏视口像素，不是桌面坐标或 UMG 逻辑单位。
- 原生鼠标左键调用 `SubmitGridPress`。有效输入更新 SelectedCell/LastAcceptedCell，并广播一次 `OnGridCellPressed(Row,Column)`；无效输入不更改选择或广播有效事件。后续玩法监听此事件，不重复计算行列。
- AcceptedGridPresses / RejectedGridPresses 是诊断计数。`bShowGrid` 控制 Development 网格与黄色选择框；它不是最终 Shipping 界面。

GridLayout 的行列、原点、格子尺寸可在 Blueprint/Details 配置；ImageSize 应与背景及相机设计尺寸保持一致。M04 不提供任意背景尺寸的自动布局，也不实现占用、植物、阳光或费用。

## 验证入口

关闭编辑器后运行：

```powershell
.\Scripts\Build-Editor.ps1
.\Scripts\Create-M04Map.ps1
.\Scripts\Test-M04Grid.ps1
.\Scripts\Validate-M04.ps1
```

脚本支持 `-EngineRoot`；图形验证有超时保护，使用真实 PIE 及与鼠标相同的原生分发入口注入屏幕坐标，不宣称硬件鼠标点击验收。精确半开边界由原生数学测试覆盖，屏幕边缘测试使用 ±0.25 原图像素，避免把浮点投影误差当成格子规则。完整结果和限制见 `validation/M04.md`。
