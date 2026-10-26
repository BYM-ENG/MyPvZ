[CmdletBinding()]
param([string]$EngineRoot)

. (Join-Path $PSScriptRoot 'Unreal-Common.ps1')
Invoke-MyPvZPython -EngineRoot $EngineRoot -ScriptName 'create_bootstrap_map.py' -LogName 'M00-CreateMap'
