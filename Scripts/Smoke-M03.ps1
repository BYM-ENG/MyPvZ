param([string]$EngineRoot)
. "$PSScriptRoot\Unreal-Common.ps1"
Assert-MyPvZEditorClosed
$resolvedEngine = Resolve-MyPvZEngineRoot $EngineRoot
$root = Get-MyPvZProjectRoot
$reportFile = Join-Path $root 'Saved/Diagnostics/M03/runtime.json'
$editorExe = Join-Path $resolvedEngine 'Engine/Binaries/Win64/UnrealEditor.exe'
New-Item -ItemType Directory -Path (Split-Path -Parent $reportFile) -Force | Out-Null
'{"status":"NOT_RUN"}' | Set-Content -LiteralPath $reportFile -Encoding utf8
Invoke-MyPvZLocalEnvironment {
    $arguments = @(('"' + (Join-Path $root 'MyPvZ.uproject') + '"'), '-unattended', '-nop4', '-nosplash',
                  '-RenderOffscreen', '-nosound', '-stdout',
                  ('-ExecutePythonScript="' + (Join-Path $PSScriptRoot 'smoke_m03_runtime.py') + '"'),
                  ('-abslog="' + (Join-Path $root 'Saved/Logs/M03-Runtime.log') + '"'))
    $process = Start-Process -FilePath $editorExe -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "M03 graphical editor exited $($process.ExitCode)" }
}
$report = Get-Content -Raw -LiteralPath $reportFile | ConvertFrom-Json
if ($report.status -ne 'PASS') { throw "M03 runtime failed: $reportFile" }
Write-Host "PASS: seven Flipbooks advanced in editor simulation. $reportFile"
