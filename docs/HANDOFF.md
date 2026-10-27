# 交接记录

## M04 本机验收通过 — 2026-10-27

起点 main/aee6924，工作区干净，与远程一致，M00–M03已验收。遵循GPT-6.1 Sol / Ultra要求，两个窄范围子代理显式使用同模型/强度；未自行切换。仅做M04，M05未开始。

交付：/Game/Maps/PvZ_Lawn（一个原生AMyPvZBoard）、FMyPvZGridLayout、Controller屏幕命中与左键分发、Development网格/黄色选择框、原生/PIE验证脚本和GRID.md。原素材及默认M00地图保持不变；不含后续玩法。

坐标必须沿用：原图1400×600，像素左上原点，X右/Y下；网格[260,980)×[185,485)，3行9列，80×100，半开边界。FIntPoint.X=列/Y=行，0起编号；中心(300+80*列,235+100*行)，本地世界(x-700,0,300-y)。相机在(0,1000,0)、yaw=-90，沿-Y看XZ平面，屏幕右=世界+X；背景Y=-10。后续详见GRID.md。

入口：打开/Game/Maps/PvZ_Lawn后Play，左键选格；有效输入更新SelectedCell/LastAcceptedCell并广播OnGridCellPressed(Row,Column)，越界不改变选择。后续使用Board.CellToWorld/PixelToCell/RayToCell和事件，不重复推导坐标。尚无占用/余额/植物。

复现（关闭编辑器，脚本支持-EngineRoot E:\develop\UE_5.8）：

~~~powershell
.\Scripts\Build-Editor.ps1
.\Scripts\Create-M04Map.ps1
.\Scripts\Test-M04Grid.ps1
.\Scripts\Validate-M04.ps1
~~~

最终构建退出0（28.09秒，4个增量动作）；4项原生测试通过。图形PIE加载地图两次，27格中心、12精确像素边界、8屏幕近边界、4视口外、2黑边、6非有限输入通过；47次提交中31接受/16拒绝，拒绝不更改选择。实际视口1023×562，画面矩形(0,62)–(1023,500)。已查看真实GameViewport截图，背景方向、网格与选择框正确；最终正常退出。

关键修正：等待游戏时间>=0.5秒再读相机缓存；相机方向避免左右镜像；不用会截断屏幕像素的引擎默认Deproject，改用实际投影矩阵保留连续坐标，修复边界外细小偏移误命中。截图取玩家GameViewport，不能把编辑器自由视口当游戏画面。

证据在忽略目录Saved/Logs/M04-*、Saved/Diagnostics/M04/runtime.json、Automation/index.json、lawn.png。详细结果见validation/M04.md。M03的资源/原FPS/坚果占位限制仍有效；本轮未重新打包。

限制：输入测试是同一原生入口注入，未做硬件鼠标/Slate人工点击；只验证当前视口，更多窗口/DPI/UMG适配留M18。网格线为Development诊断，不是最终Shipping UI。图形启动仍有既有UE UnifiedErrorTest/AutomationTest日志错误，不宣称全日志零错误；本模块测试独立通过。

额度：开始50%/38%，主要验证前62%/40%，验收整理74%/42%（五小时/周，共享账户观察）。提交后最终值见聊天报告。

下一步：仅用户发起M05时，在当前PvZ_Lawn地图继续阳光生成/掉落/收集/余额，先读STATUS/HANDOFF及PLAN的M05；使用现有网格/相机，不重建工程，不提前做M06。
