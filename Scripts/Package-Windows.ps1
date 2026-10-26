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
$runUat = Join-Path $resolvedEngine 'Engine\Build\BatchFiles\RunUAT.bat'
$mapFile = Join-Path $projectRoot 'Content\Maps\M00_Bootstrap.umap'
if (-not (Test-Path -LiteralPath $mapFile -PathType Leaf)) {
    throw "Missing bootstrap map: $mapFile. Complete M00 before packaging."
}

# Each run has its own archive so a failed or older package cannot pass checks.
# Keep the archive on the real path: the temporary build drive disappears below.
$runId = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$archiveRoot = Join-Path $projectRoot "Packages\M01-Windows-Development\$runId"
$logRoot = Join-Path $projectRoot "Saved\Logs\M01-Package-Windows-$runId"
$consoleLog = Join-Path $logRoot 'console.log'
New-Item -ItemType Directory -Path $archiveRoot, $logRoot -Force | Out-Null

Invoke-MyPvZAsciiProjectRoot -BuildDrive $BuildDrive -MapParent -Action {
    param($buildRoot)
    $projectFile = Join-Path $buildRoot 'MyPvZ.uproject'
    $uatLogRoot = Join-Path $buildRoot "Saved\Logs\M01-Package-Windows-$runId\UAT"
    Invoke-MyPvZLocalEnvironment -ProjectRoot $buildRoot -Action {
        # UE 5.8 clears uebp_LogFolder when UAT starts. Isolate its files from
        # the console capture and other runs, and restore caller environment.
        $uatEnvironment = @{
            'uebp_LogFolder' = $uatLogRoot
            'uebp_FinalLogFolder' = $uatLogRoot
            'uebp_EngineSavedFolder' = (Join-Path $buildRoot 'Saved\AutomationTool')
        }
        $previous = @{}
        foreach ($name in $uatEnvironment.Keys) {
            $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
            [Environment]::SetEnvironmentVariable($name, $uatEnvironment[$name], 'Process')
        }
        Push-Location -LiteralPath $buildRoot
        try {
            $arguments = @(
                'BuildCookRun', "-project=$projectFile", '-target=MyPvZ',
                '-platform=Win64', '-clientconfig=Development',
                '-map=/Game/Maps/M00_Bootstrap',
                '-build', '-cook', '-stage', '-package', '-pak', '-iostore',
                '-archive', "-archivedirectory=$archiveRoot", '-prereqs',
                # Development uses release CRT. Exclude debug symbol files;
                # do not copy any Microsoft debug runtime into the package.
                '-nodebuginfo', '-unattended', '-nop4', '-utf8output', '-nocompileuat',
                "-ubtargs=-WaitMutex -NoHotReloadFromIDE -NoUBA -NoUBTMakefiles -MaxParallelActions=$MaxParallelActions"
            )
            Write-Host "Archive: $archiveRoot"
            Write-Host "Logs: $logRoot"
            & $runUat @arguments 2>&1 | Tee-Object -FilePath $consoleLog
            $result = $LASTEXITCODE
            if ($result -ne 0) {
                throw "Windows Development packaging failed with exit code $result. See $consoleLog and $logRoot\UAT."
            }
        }
        finally {
            Pop-Location
            foreach ($name in $previous.Keys) {
                [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
            }
        }
    }
}

$packageRoot = Join-Path $archiveRoot 'Windows'
$launcher = Join-Path $packageRoot 'MyPvZ.exe'
$gameExecutable = Join-Path $packageRoot 'MyPvZ\Binaries\Win64\MyPvZ.exe'
foreach ($requiredFile in @($launcher, $gameExecutable)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "UAT returned success but the packaged executable is missing: $requiredFile. See $consoleLog."
    }
}
$packageFiles = @(Get-ChildItem -LiteralPath $packageRoot -Recurse -File)
foreach ($extension in @('.pak', '.utoc', '.ucas')) {
    if (-not ($packageFiles | Where-Object Extension -EQ $extension)) {
        throw "UAT returned success but no $extension file was archived under $packageRoot. See $consoleLog."
    }
}
$debugRuntime = @($packageFiles | Where-Object {
    $_.Name -match '^(?:ucrtbased|(?:msvcp|vcruntime|vccorlib|concrt|vcomp)\d+(?:_\d+)?d(?:_[a-z0-9_]+)?|msvcr\d+d)\.dll$'
})
if ($debugRuntime.Count -gt 0) {
    throw "Unexpected Microsoft debug runtime in package: $($debugRuntime.FullName -join ', '). Do not distribute this archive."
}

Write-Host 'PASS: MyPvZ Win64 Development build/cook/stage/package/archive (exit code 0).'
Write-Host "Standalone launcher: $launcher"
Write-Host "Log: $consoleLog"
Write-Host 'M01 still requires standalone graphical startup and normal exit verification.'
