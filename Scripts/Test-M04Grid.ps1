param([string]$EngineRoot)
. "$PSScriptRoot\Unreal-Common.ps1"
Assert-MyPvZEditorClosed
$resolvedEngine = Resolve-MyPvZEngineRoot $EngineRoot
$root = Get-MyPvZProjectRoot
$editorCmd = Join-Path $resolvedEngine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$reportDir = Join-Path $root 'Saved/Diagnostics/M04/Automation'
$indexFile = Join-Path $reportDir 'index.json'
if (Test-Path -LiteralPath $indexFile) { Remove-Item -LiteralPath $indexFile }
Invoke-MyPvZLocalEnvironment {
    $arguments = @((Join-Path $root 'MyPvZ.uproject'), '-unattended', '-nop4', '-nosplash', '-nullrhi', '-nosound',
                  '-stdout', '-ExecCmds=Automation RunTests MyPvZ.M04.Grid',
                  '-TestExit=Automation Test Queue Empty', "-ReportExportPath=$reportDir",
                  "-abslog=$(Join-Path $root 'Saved/Logs/M04-GridTests.log')")
    & $editorCmd @arguments
    if ($LASTEXITCODE -ne 0) { throw "M04 automation process failed: $LASTEXITCODE" }
}
$report = Get-Content -Raw -LiteralPath $indexFile | ConvertFrom-Json
if ($report.succeeded -ne 4 -or $report.failed -ne 0 -or $report.notRun -ne 0) {
    throw "M04 native grid tests did not all pass: $indexFile"
}
Write-Host "PASS: all four MyPvZ.M04.Grid native automation tests. $indexFile"
