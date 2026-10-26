using UnrealBuildTool;

public class MyPvZ : ModuleRules
{
    public MyPvZ(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[]
        {
            "Core", "CoreUObject", "Engine", "InputCore", "Paper2D", "UMG"
        });
    }
}
