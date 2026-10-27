#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MyPvZGridLayout.h"
#include "MyPvZBoard.generated.h"

class UCameraComponent;
class UPaperSpriteComponent;

/** M04 board presentation and coordinate boundary. No occupancy/economy/gameplay yet. */
UCLASS()
class MYPVZ_API AMyPvZBoard : public AActor
{
    GENERATED_BODY()

public:
    AMyPvZBoard();
    virtual void Tick(float DeltaSeconds) override;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Board")
    FMyPvZGridLayout GridLayout;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Board")
    TObjectPtr<UPaperSpriteComponent> Background;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Board")
    TObjectPtr<UCameraComponent> BoardCamera;

    /** Development overlay only; the later planting/UI modules own their presentation. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Board|Diagnostics")
    bool bShowGrid = true;

    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Board")
    FIntPoint SelectedCell = FIntPoint(INDEX_NONE, INDEX_NONE);

    UFUNCTION(BlueprintPure, Category = "Board")
    bool PixelToCell(FVector2D Pixel, FIntPoint& OutCell) const;

    UFUNCTION(BlueprintPure, Category = "Board")
    bool CellToWorld(FIntPoint Cell, FVector& OutWorld) const;

    UFUNCTION(BlueprintPure, Category = "Board")
    bool RayToCell(FVector RayOrigin, FVector RayDirection, FIntPoint& OutCell) const;

    UFUNCTION(BlueprintCallable, Category = "Board")
    bool SelectCell(FIntPoint Cell);
};
