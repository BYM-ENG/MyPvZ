using UnrealBuildTool;

public class MyPvZEditorTarget : TargetRules
{
    public MyPvZEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("MyPvZ");
    }
}
