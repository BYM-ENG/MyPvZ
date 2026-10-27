#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "MyPvZPlayerController.generated.h"

class AMyPvZBoard;
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FMyPvZGridCellPressed, int32, Row, int32, Column);

/** Native pointer -> projection -> board intent boundary. */
UCLASS()
class MYPVZ_API AMyPvZPlayerController : public APlayerController
{
    GENERATED_BODY()

public:
    AMyPvZPlayerController();
    virtual void BeginPlay() override;
    virtual void SetupInputComponent() override;

    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Grid")
    TObjectPtr<AMyPvZBoard> Board;

    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Grid|Diagnostics")
    int32 AcceptedGridPresses = 0;

    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Grid|Diagnostics")
    int32 RejectedGridPresses = 0;

    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Grid")
    FIntPoint LastAcceptedCell = FIntPoint(INDEX_NONE, INDEX_NONE);

    UPROPERTY(BlueprintAssignable, Category = "Grid")
    FMyPvZGridCellPressed OnGridCellPressed;

    /** Local game viewport pixels, excluding the camera's letterbox/pillarbox area. */
    UFUNCTION(BlueprintPure, Category = "Grid")
    bool GetBoardViewRect(FVector2D& OutMin, FVector2D& OutMax) const;

    UFUNCTION(BlueprintPure, Category = "Grid")
    bool ScreenToGrid(FVector2D ScreenPosition, FIntPoint& OutCell) const;

    /** Same dispatch for the native mouse binding and scripted verification. */
    UFUNCTION(BlueprintCallable, Category = "Grid")
    bool SubmitGridPress(FVector2D ScreenPosition);

private:
    void OnPrimaryPressed();
};
