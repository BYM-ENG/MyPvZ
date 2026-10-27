param(
    [string]$EngineRoot,
    [ValidateRange(60, 600)][int]$TimeoutSeconds = 180
)
. "$PSScriptRoot\Unreal-Common.ps1"
Assert-MyPvZEditorClosed
$resolvedEngine = Resolve-MyPvZEngineRoot $EngineRoot
$root = Get-MyPvZProjectRoot
$reportFile = Join-Path $root 'Saved/Diagnostics/M04/runtime.json'
$logFile = Join-Path $root 'Saved/Logs/M04-Runtime.log'
$editorExe = Join-Path $resolvedEngine 'Engine/Binaries/Win64/UnrealEditor.exe'
$runId = [guid]::NewGuid().ToString('N')
New-Item -ItemType Directory -Path (Split-Path -Parent $reportFile) -Force | Out-Null
@{ status = 'NOT_RUN'; run_id = $runId } | ConvertTo-Json | Set-Content -LiteralPath $reportFile -Encoding utf8
Invoke-MyPvZLocalEnvironment {
    $previousRunId = [Environment]::GetEnvironmentVariable('MYPVZ_M04_RUN_ID', 'Process')
    [Environment]::SetEnvironmentVariable('MYPVZ_M04_RUN_ID', $runId, 'Process')
    try {
        $arguments = @(('"' + (Join-Path $root 'MyPvZ.uproject') + '"'), '-unattended', '-nop4', '-nosplash',
                      '-RenderOffscreen', '-nosound', '-stdout', '-ResX=1280', '-ResY=900',
                      ('-ExecutePythonScript="' + (Join-Path $PSScriptRoot 'validate_m04_runtime.py') + '"'),
                      ('-abslog="' + $logFile + '"'))
        $process = Start-Process -FilePath $editorExe -ArgumentList $arguments -WindowStyle Hidden -PassThru
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            $partial = Get-Content -Raw -LiteralPath $reportFile | ConvertFrom-Json
            $partial.status = 'FAIL'
            $partial | Add-Member -NotePropertyName wrapper_error -NotePropertyValue "Editor exceeded ${TimeoutSeconds}s watchdog" -Force
            $partial | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $reportFile -Encoding utf8
            throw "M04 graphical editor timed out. Report: $reportFile; log: $logFile"
        }
        $process.Refresh()
        if ($process.ExitCode -ne 0) { throw "M04 graphical editor exited $($process.ExitCode). See $logFile" }
    }
    finally {
        [Environment]::SetEnvironmentVariable('MYPVZ_M04_RUN_ID', $previousRunId, 'Process')
    }
}
$report = Get-Content -Raw -LiteralPath $reportFile | ConvertFrom-Json
if ($report.status -ne 'PASS' -or $report.run_id -ne $runId) {
    throw "M04 runtime failed or report does not belong to this launch: $reportFile. See $logFile"
}
Write-Host "PASS: $($report.counts.cell_centers) cell centers, $($report.counts.exact_pixel_boundaries) exact pixel-edge cases, $($report.counts.submitted) native-dispatch presses. $reportFile"
Write-Host 'Input evidence uses SubmitGridPress injection; hardware/Slate mouse clicks were not validated.'
