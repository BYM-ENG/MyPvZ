param([string]$EngineRoot)
. "$PSScriptRoot\Unreal-Common.ps1"
Invoke-MyPvZPython -EngineRoot $EngineRoot -ScriptName 'validate_m02.py' -LogName 'M02-Validate'
