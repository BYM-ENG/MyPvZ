#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "MyPvZGameMode.generated.h"

/** Empty bootstrap game mode. Gameplay belongs to later milestones. */
UCLASS()
class MYPVZ_API AMyPvZGameMode : public AGameModeBase
{
    GENERATED_BODY()

public:
    AMyPvZGameMode();
};
