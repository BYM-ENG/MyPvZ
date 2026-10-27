param([string]$EngineRoot)
. "$PSScriptRoot\Unreal-Common.ps1"
Invoke-MyPvZPython -EngineRoot $EngineRoot -ScriptName 'create_m04_map.py' -LogName 'M04-CreateMap'
