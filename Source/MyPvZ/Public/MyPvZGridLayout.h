#pragma once

#include "CoreMinimal.h"
#include "MyPvZGridLayout.generated.h"

/** Pixel coordinates start at the image's top left; cells use X = column, Y = row. */
USTRUCT(BlueprintType)
struct MYPVZ_API FMyPvZGridLayout
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Grid", meta = (ClampMin = "1"))
    int32 Rows = 3;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Grid", meta = (ClampMin = "1"))
    int32 Columns = 9;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Grid")
    FVector2D ImageSize = FVector2D(1400.0, 600.0);

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Grid")
    FVector2D TopLeft = FVector2D(260.0, 185.0);

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Grid")
    FVector2D CellSize = FVector2D(80.0, 100.0);

    bool IsValid() const;
    bool IsValidCell(FIntPoint Cell) const;

    /** The playable rectangle is half open. Failure always writes (INDEX_NONE, INDEX_NONE). */
    bool TryPixelToCell(FVector2D Pixel, FIntPoint& OutCell) const;

    /** Failure writes ZeroVector. */
    bool TryCellToPixelCenter(FIntPoint Cell, FVector2D& OutPixel) const;

    /** One pixel is one local Unreal unit on the X/Z plane, centered on the image. */
    FVector PixelToLocalWorld(FVector2D Pixel) const;
    FVector2D LocalWorldToPixel(FVector LocalWorld) const;
};
