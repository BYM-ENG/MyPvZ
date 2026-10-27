param([string]$EngineRoot, [string]$PrototypeRoot)
. "$PSScriptRoot\Unreal-Common.ps1"
$resolvedEngine = Resolve-MyPvZEngineRoot $EngineRoot
$python = Join-Path $resolvedEngine 'Engine\Binaries\ThirdParty\Python3\Win64\python.exe'
$arguments = @('-B', (Join-Path $PSScriptRoot 'prepare_m03.py'))
if ($PrototypeRoot) { $arguments += @('--prototype', $PrototypeRoot) }
& $python @arguments
if ($LASTEXITCODE -ne 0) { throw 'M03 source preparation failed.' }
