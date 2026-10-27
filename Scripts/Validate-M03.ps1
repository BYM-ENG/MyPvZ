param([string]$EngineRoot)
. "$PSScriptRoot\Unreal-Common.ps1"
Invoke-MyPvZPython -EngineRoot $EngineRoot -ScriptName 'validate_m03.py' -LogName 'M03-Validate'
