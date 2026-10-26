[CmdletBinding()]
param([string]$EngineRoot)

. (Join-Path $PSScriptRoot 'Unreal-Common.ps1')
Invoke-MyPvZPython -EngineRoot $EngineRoot -ScriptName 'validate_project.py' -LogName 'M00-ValidateProject'
