#include "MyPvZGameMode.h"
#include "MyPvZPlayerController.h"

AMyPvZGameMode::AMyPvZGameMode()
{
    PlayerControllerClass = AMyPvZPlayerController::StaticClass();
    DefaultPawnClass = nullptr;
    HUDClass = nullptr;
}
