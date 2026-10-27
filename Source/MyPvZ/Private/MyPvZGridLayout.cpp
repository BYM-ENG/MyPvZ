#include "MyPvZGridLayout.h"

namespace
{
bool IsFiniteVector(FVector2D Value)
{
    return FMath::IsFinite(Value.X) && FMath::IsFinite(Value.Y);
}
}

bool FMyPvZGridLayout::IsValid() const
{
    if (Rows <= 0 || Columns <= 0 || static_cast<int64>(Rows) * Columns > MAX_int32
        || !IsFiniteVector(ImageSize) || ImageSize.X <= 0.0 || ImageSize.Y <= 0.0
        || !IsFiniteVector(CellSize) || CellSize.X <= 0.0 || CellSize.Y <= 0.0
        || !IsFiniteVector(TopLeft) || TopLeft.X < 0.0 || TopLeft.Y < 0.0)
    {
        return false;
    }

    const FVector2D BottomRight = TopLeft + FVector2D(Columns * CellSize.X, Rows * CellSize.Y);
    return IsFiniteVector(BottomRight)
        && BottomRight.X <= ImageSize.X && BottomRight.Y <= ImageSize.Y;
}

bool FMyPvZGridLayout::IsValidCell(FIntPoint Cell) const
{
    return IsValid() && Cell.X >= 0 && Cell.X < Columns && Cell.Y >= 0 && Cell.Y < Rows;
}

bool FMyPvZGridLayout::TryPixelToCell(FVector2D Pixel, FIntPoint& OutCell) const
{
    OutCell = FIntPoint(INDEX_NONE, INDEX_NONE);
    if (!IsValid() || !IsFiniteVector(Pixel))
    {
        return false;
    }

    const FVector2D BottomRight = TopLeft + FVector2D(Columns * CellSize.X, Rows * CellSize.Y);
    if (Pixel.X < TopLeft.X || Pixel.Y < TopLeft.Y || Pixel.X >= BottomRight.X || Pixel.Y >= BottomRight.Y)
    {
        return false;
    }

    // Keep a value just inside the far edge in the last cell if division rounds upward.
    OutCell.X = FMath::Min(FMath::FloorToInt32((Pixel.X - TopLeft.X) / CellSize.X), Columns - 1);
    OutCell.Y = FMath::Min(FMath::FloorToInt32((Pixel.Y - TopLeft.Y) / CellSize.Y), Rows - 1);
    return true;
}

bool FMyPvZGridLayout::TryCellToPixelCenter(FIntPoint Cell, FVector2D& OutPixel) const
{
    OutPixel = FVector2D::ZeroVector;
    if (!IsValidCell(Cell))
    {
        return false;
    }

    OutPixel = TopLeft + FVector2D((Cell.X + 0.5) * CellSize.X, (Cell.Y + 0.5) * CellSize.Y);
    return true;
}

FVector FMyPvZGridLayout::PixelToLocalWorld(FVector2D Pixel) const
{
    return FVector(Pixel.X - ImageSize.X * 0.5, 0.0, ImageSize.Y * 0.5 - Pixel.Y);
}

FVector2D FMyPvZGridLayout::LocalWorldToPixel(FVector LocalWorld) const
{
    return FVector2D(LocalWorld.X + ImageSize.X * 0.5, ImageSize.Y * 0.5 - LocalWorld.Z);
}
