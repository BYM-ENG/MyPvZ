#include "MyPvZBoard.h"

#include "Camera/CameraComponent.h"
#include "Components/SceneComponent.h"
#include "DrawDebugHelpers.h"
#include "PaperSprite.h"
#include "PaperSpriteComponent.h"
#include "UObject/ConstructorHelpers.h"

AMyPvZBoard::AMyPvZBoard()
{
    PrimaryActorTick.bCanEverTick = true;
    bFindCameraComponentWhenViewTarget = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("BoardRoot"));

    Background = CreateDefaultSubobject<UPaperSpriteComponent>(TEXT("Background"));
    Background->SetupAttachment(RootComponent);
    Background->SetRelativeLocation(FVector(0.0, -10.0, 0.0));
    Background->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Background->SetCastShadow(false);
    static ConstructorHelpers::FObjectFinder<UPaperSprite> LawnSprite(
        TEXT("/Game/PvZ/Sprites/S_res_bg.S_res_bg"));
    if (LawnSprite.Succeeded())
    {
        Background->SetSprite(LawnSprite.Object);
    }

    BoardCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("BoardCamera"));
    BoardCamera->SetupAttachment(RootComponent);
    BoardCamera->SetRelativeLocation(FVector(0.0, 1000.0, 0.0));
    BoardCamera->SetRelativeRotation(FRotator(0.0, -90.0, 0.0));
    BoardCamera->ProjectionMode = ECameraProjectionMode::Orthographic;
    BoardCamera->OrthoWidth = 1400.0f;
    BoardCamera->AspectRatio = 1400.0f / 600.0f;
    BoardCamera->bConstrainAspectRatio = true;
    BoardCamera->bAutoCalculateOrthoPlanes = false;
    BoardCamera->OrthoNearClipPlane = 1.0f;
    BoardCamera->OrthoFarClipPlane = 5000.0f;
    BoardCamera->PostProcessBlendWeight = 0.0f;
}

bool AMyPvZBoard::PixelToCell(FVector2D Pixel, FIntPoint& OutCell) const
{
    return GridLayout.TryPixelToCell(Pixel, OutCell);
}

bool AMyPvZBoard::CellToWorld(FIntPoint Cell, FVector& OutWorld) const
{
    OutWorld = FVector::ZeroVector;
    FVector2D Pixel;
    if (!GridLayout.TryCellToPixelCenter(Cell, Pixel) || GetActorTransform().ContainsNaN())
    {
        return false;
    }
    OutWorld = GetActorTransform().TransformPosition(GridLayout.PixelToLocalWorld(Pixel));
    return true;
}

bool AMyPvZBoard::RayToCell(FVector RayOrigin, FVector RayDirection, FIntPoint& OutCell) const
{
    OutCell = FIntPoint(INDEX_NONE, INDEX_NONE);
    const FTransform Transform = GetActorTransform();
    const FVector Scale = Transform.GetScale3D();
    if (!GridLayout.IsValid() || RayOrigin.ContainsNaN() || RayDirection.ContainsNaN()
        || Transform.ContainsNaN() || FMath::IsNearlyZero(Scale.X)
        || FMath::IsNearlyZero(Scale.Y) || FMath::IsNearlyZero(Scale.Z))
    {
        return false;
    }
    const FVector Origin = Transform.InverseTransformPosition(RayOrigin);
    const FVector Direction = Transform.InverseTransformVector(RayDirection);
    if (FMath::IsNearlyZero(Direction.Y))
    {
        return false;
    }
    const double Distance = -Origin.Y / Direction.Y;
    if (!FMath::IsFinite(Distance) || Distance < 0.0)
    {
        return false;
    }
    return GridLayout.TryPixelToCell(GridLayout.LocalWorldToPixel(Origin + Direction * Distance), OutCell);
}

bool AMyPvZBoard::SelectCell(FIntPoint Cell)
{
    if (!GridLayout.IsValidCell(Cell))
    {
        return false;
    }
    SelectedCell = Cell;
    return true;
}

void AMyPvZBoard::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
#if ENABLE_DRAW_DEBUG
    if (!bShowGrid || !GridLayout.IsValid())
    {
        return;
    }
    auto Line = [this](FVector2D A, FVector2D B, FColor Color, float Thickness)
    {
        FVector Start = GridLayout.PixelToLocalWorld(A);
        FVector End = GridLayout.PixelToLocalWorld(B);
        Start.Y = End.Y = 2.0;
        DrawDebugLine(GetWorld(), GetActorTransform().TransformPosition(Start),
            GetActorTransform().TransformPosition(End), Color, false, 0.0f, 0, Thickness);
    };
    const FVector2D End = GridLayout.TopLeft + FVector2D(
        GridLayout.Columns * GridLayout.CellSize.X, GridLayout.Rows * GridLayout.CellSize.Y);
    for (int32 Column = 0; Column <= GridLayout.Columns; ++Column)
    {
        const double X = GridLayout.TopLeft.X + Column * GridLayout.CellSize.X;
        Line(FVector2D(X, GridLayout.TopLeft.Y), FVector2D(X, End.Y), FColor(210, 245, 220), 1.0f);
    }
    for (int32 Row = 0; Row <= GridLayout.Rows; ++Row)
    {
        const double Y = GridLayout.TopLeft.Y + Row * GridLayout.CellSize.Y;
        Line(FVector2D(GridLayout.TopLeft.X, Y), FVector2D(End.X, Y), FColor(210, 245, 220), 1.0f);
    }
    if (GridLayout.IsValidCell(SelectedCell))
    {
        const FVector2D A = GridLayout.TopLeft + FVector2D(
            SelectedCell.X * GridLayout.CellSize.X, SelectedCell.Y * GridLayout.CellSize.Y);
        const FVector2D B = A + GridLayout.CellSize;
        Line(A, FVector2D(B.X, A.Y), FColor::Yellow, 4.0f);
        Line(FVector2D(B.X, A.Y), B, FColor::Yellow, 4.0f);
        Line(B, FVector2D(A.X, B.Y), FColor::Yellow, 4.0f);
        Line(FVector2D(A.X, B.Y), A, FColor::Yellow, 4.0f);
    }
#endif
}
