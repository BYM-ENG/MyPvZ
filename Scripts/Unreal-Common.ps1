Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-MyPvZProjectRoot {
    return (Split-Path -Parent $PSScriptRoot)
}

function Resolve-MyPvZEngineRoot {
    param([string]$EngineRoot)

    if ([string]::IsNullOrWhiteSpace($EngineRoot)) { $EngineRoot = $env:UE_ENGINE_ROOT }
    if ([string]::IsNullOrWhiteSpace($EngineRoot)) { $EngineRoot = 'E:\develop\UE_5.8' }
    $resolved = (Resolve-Path -LiteralPath $EngineRoot).Path
    $versionFile = Join-Path $resolved 'Engine\Build\Build.version'
    $version = Get-Content -Raw -LiteralPath $versionFile | ConvertFrom-Json
    if ($version.MajorVersion -ne 5 -or $version.MinorVersion -ne 8 -or $version.PatchVersion -ne 2) {
        throw "M00 requires UE 5.8.2. Engine version at '$resolved' is $($version.MajorVersion).$($version.MinorVersion).$($version.PatchVersion)."
    }
    Write-Host "UE $($version.MajorVersion).$($version.MinorVersion).$($version.PatchVersion): $resolved"
    return $resolved
}

function Assert-MyPvZEditorClosed {
    $editors = Get-Process -Name UnrealEditor, UnrealEditor-Cmd -ErrorAction SilentlyContinue
    if ($editors) { throw 'Close UnrealEditor and UnrealEditor-Cmd before running this script.' }
}

function Invoke-MyPvZLocalEnvironment {
    param(
        [scriptblock]$Action,
        [string]$ProjectRoot = (Get-MyPvZProjectRoot)
    )

    $savedRoot = Join-Path $ProjectRoot 'Saved'
    $overrides = @{
        'TEMP' = (Join-Path $savedRoot 'Temp')
        'TMP' = (Join-Path $savedRoot 'Temp')
        'DOTNET_CLI_HOME' = (Join-Path $savedRoot 'DotNetHome')
        'DOTNET_SKIP_FIRST_TIME_EXPERIENCE' = '1'
        'DOTNET_NOLOGO' = '1'
        'UE-LocalDataCachePath' = (Join-Path $ProjectRoot 'DerivedDataCache')
    }
    $previous = @{}
    foreach ($directory in @('Logs', 'Temp', 'DotNetHome')) {
        New-Item -ItemType Directory -Path (Join-Path $savedRoot $directory) -Force | Out-Null
    }
    foreach ($name in $overrides.Keys) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $overrides[$name], 'Process')
    }
    try { & $Action }
    finally {
        foreach ($name in $previous.Keys) {
            [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
        }
    }
}

function Invoke-MyPvZAsciiProjectRoot {
    param(
        [scriptblock]$Action,
        [ValidatePattern('^[A-Za-z]$')][string]$BuildDrive = 'P',
        [switch]$MapParent
    )

    $projectRoot = Get-MyPvZProjectRoot
    if ($projectRoot -notmatch '[^\x00-\x7F]') {
        & $Action $projectRoot
        return
    }

    # MSVC cannot decode this UE version's UTF-8 response paths on every
    # Windows locale. Map a directory without moving or copying files.
    $driveName = $BuildDrive.ToUpperInvariant()
    $drive = "${driveName}:"
    $driveRoot = "${drive}\"
    $aliasRoot = $driveRoot
    $mappingRoot = $projectRoot
    if ($MapParent) {
        # UAT nests a quoted -remoteini in its UBT target argument. A project
        # at P:\ ends that value with a backslash and breaks nested quoting.
        # Retain the project folder name so it becomes P:\UE5Migration.
        $mappingRoot = Split-Path -Parent $projectRoot
        $aliasRoot = [System.IO.Path]::Combine($driveRoot, (Split-Path -Leaf $projectRoot))
    }
    if ($aliasRoot -match '[^\x00-\x7F]') {
        throw "Temporary build path '$aliasRoot' is not ASCII. Use an ASCII project folder name with -MapParent."
    }
    if ((Get-PSDrive -Name $driveName -ErrorAction SilentlyContinue) -or
        ([System.IO.DriveInfo]::GetDrives().Name -contains $driveRoot)) {
        throw "Build drive $drive is already occupied. Choose another -BuildDrive letter."
    }
    $subst = Join-Path $env:SystemRoot 'System32\subst.exe'
    & $subst $drive $mappingRoot
    if ($LASTEXITCODE -ne 0) { throw "Could not create temporary build mapping $drive -> $mappingRoot" }
    try {
        Write-Host "Temporary ASCII build path: $aliasRoot -> $projectRoot"
        & $Action $aliasRoot
    }
    finally {
        & $subst $drive /D
        if ($LASTEXITCODE -ne 0) { Write-Warning "Could not remove this run's temporary mapping $drive" }
        else { Write-Host "Removed temporary build mapping $drive" }
    }
}

function Invoke-MyPvZPython {
    param([string]$EngineRoot, [string]$ScriptName, [string]$LogName)

    Assert-MyPvZEditorClosed
    $resolvedEngine = Resolve-MyPvZEngineRoot $EngineRoot
    $projectRoot = Get-MyPvZProjectRoot
    $editorCmd = Join-Path $resolvedEngine 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
    $pythonScript = Join-Path $PSScriptRoot $ScriptName
    $projectFile = Join-Path $projectRoot 'MyPvZ.uproject'
    $logFile = Join-Path $projectRoot "Saved\Logs\$LogName.log"
    Invoke-MyPvZLocalEnvironment {
        $arguments = @(
            $projectFile, '-run=pythonscript', "-script=$pythonScript",
            '-unattended', '-nop4', '-nosplash', '-nullrhi', '-nosound',
            '-stdout', "-abslog=$logFile"
        )
        & $editorCmd @arguments
        $result = $LASTEXITCODE
        if ($result -ne 0) { throw "UnrealEditor-Cmd failed with exit code $result. See $logFile" }
    }
    Write-Host "PASS: $LogName (exit code 0). Log: $logFile"
}
