using UnrealBuildTool;

public class MyPvZTarget : TargetRules
{
    public MyPvZTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("MyPvZ");
    }
}
