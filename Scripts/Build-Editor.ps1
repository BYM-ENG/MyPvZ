[CmdletBinding()]
param(
    [string]$EngineRoot,
    [ValidateRange(1, 64)][int]$MaxParallelActions = 4,
    [ValidatePattern('^[A-Za-z]$')][string]$BuildDrive = 'P'
)

. (Join-Path $PSScriptRoot 'Unreal-Common.ps1')
Assert-MyPvZEditorClosed
$resolvedEngine = Resolve-MyPvZEngineRoot $EngineRoot
$projectRoot = Get-MyPvZProjectRoot
$buildScript = Join-Path $resolvedEngine 'Engine\Build\BatchFiles\Build.bat'
$logFile = Join-Path $projectRoot 'Saved\Logs\M00-Build-Editor.log'

Invoke-MyPvZAsciiProjectRoot -BuildDrive $BuildDrive -Action {
    param($buildRoot)
    $projectFile = Join-Path $buildRoot 'MyPvZ.uproject'
    $buildLog = Join-Path $buildRoot 'Saved\Logs\M00-Build-Editor.log'
    Invoke-MyPvZLocalEnvironment -ProjectRoot $buildRoot -Action {
        $arguments = @(
            'MyPvZEditor', 'Win64', 'Development', "-Project=$projectFile",
            '-WaitMutex', '-NoHotReloadFromIDE', '-NoUBA',
            # Recreate response files if a prior build used the Unicode path.
            '-NoUBTMakefiles', "-MaxParallelActions=$MaxParallelActions", "-Log=$buildLog"
        )
        Push-Location -LiteralPath $buildRoot
        try {
            & $buildScript @arguments
            $result = $LASTEXITCODE
            if ($result -ne 0) { throw "Editor build failed with exit code $result. See $logFile" }
        }
        finally { Pop-Location }
    }
}
Write-Host "PASS: MyPvZEditor Win64 Development (exit code 0). Log: $logFile"
