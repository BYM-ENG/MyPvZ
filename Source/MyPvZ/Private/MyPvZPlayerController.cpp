#include "MyPvZPlayerController.h"

#include "MyPvZBoard.h"
#include "Components/InputComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "EngineUtils.h"
#include "InputCoreTypes.h"
#include "SceneView.h"

AMyPvZPlayerController::AMyPvZPlayerController()
{
    bShowMouseCursor = true;
}

void AMyPvZPlayerController::BeginPlay()
{
    Super::BeginPlay();
    if (!IsLocalController())
    {
        return;
    }
    for (TActorIterator<AMyPvZBoard> It(GetWorld()); It; ++It)
    {
        if (Board)
        {
            UE_LOG(LogTemp, Error, TEXT("MyPvZ: multiple boards; grid input disabled."));
            Board = nullptr;
            return;
        }
        Board = *It;
    }
    if (Board)
    {
        SetViewTarget(Board);
        FInputModeGameAndUI Mode;
        Mode.SetHideCursorDuringCapture(false);
        Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
        SetInputMode(Mode);
        if (ULocalPlayer* LocalPlayer = GetLocalPlayer())
        {
            if (LocalPlayer->ViewportClient)
            {
                LocalPlayer->ViewportClient->SetMouseCaptureMode(EMouseCaptureMode::NoCapture);
                LocalPlayer->ViewportClient->SetMouseLockMode(EMouseLockMode::DoNotLock);
            }
        }
    }
}

void AMyPvZPlayerController::SetupInputComponent()
{
    Super::SetupInputComponent();
    InputComponent->BindKey(EKeys::LeftMouseButton, IE_Pressed, this, &AMyPvZPlayerController::OnPrimaryPressed);
}

bool AMyPvZPlayerController::GetBoardViewRect(FVector2D& OutMin, FVector2D& OutMax) const
{
    OutMin = OutMax = FVector2D::ZeroVector;
    const ULocalPlayer* LocalPlayer = GetLocalPlayer();
    if (!IsValid(Board) || !LocalPlayer || !LocalPlayer->ViewportClient || !LocalPlayer->ViewportClient->Viewport)
    {
        return false;
    }
    FSceneViewProjectionData Projection;
    if (!LocalPlayer->GetProjectionData(LocalPlayer->ViewportClient->Viewport, Projection))
    {
        return false;
    }
    const FIntRect Rect = Projection.GetConstrainedViewRect();
    OutMin = FVector2D(Rect.Min.X, Rect.Min.Y);
    OutMax = FVector2D(Rect.Max.X, Rect.Max.Y);
    return Rect.Width() > 0 && Rect.Height() > 0;
}

bool AMyPvZPlayerController::ScreenToGrid(FVector2D ScreenPosition, FIntPoint& OutCell) const
{
    OutCell = FIntPoint(INDEX_NONE, INDEX_NONE);
    FVector2D Min, Max;
    if (!FMath::IsFinite(ScreenPosition.X) || !FMath::IsFinite(ScreenPosition.Y)
        || !GetBoardViewRect(Min, Max)
        || ScreenPosition.X < Min.X || ScreenPosition.Y < Min.Y
        || ScreenPosition.X >= Max.X || ScreenPosition.Y >= Max.Y)
    {
        return false;
    }
    FSceneViewProjectionData Projection;
    const ULocalPlayer* LocalPlayer = GetLocalPlayer();
    if (!LocalPlayer->GetProjectionData(LocalPlayer->ViewportClient->Viewport, Projection))
    {
        return false;
    }
    // UE 5.8's DeprojectScreenPositionToWorld truncates to integer pixels.
    // Keep continuous input so a point just outside an edge stays outside.
    const double X = 2.0 * (ScreenPosition.X - Min.X) / (Max.X - Min.X) - 1.0;
    const double Y = 1.0 - 2.0 * (ScreenPosition.Y - Min.Y) / (Max.Y - Min.Y);
    const FMatrix Inverse = Projection.ComputeViewProjectionMatrix().Inverse();
    const FVector4 Start = Inverse.TransformFVector4(FVector4(X, Y, 1.0, 1.0));
    const FVector4 End = Inverse.TransformFVector4(FVector4(X, Y, 0.01, 1.0));
    if (Start.W == 0.0 || End.W == 0.0)
    {
        return false;
    }
    const FVector Origin = FVector(Start.X, Start.Y, Start.Z) / Start.W;
    const FVector Far = FVector(End.X, End.Y, End.Z) / End.W;
    return Board->RayToCell(Origin, (Far - Origin).GetSafeNormal(), OutCell);
}

bool AMyPvZPlayerController::SubmitGridPress(FVector2D ScreenPosition)
{
    FIntPoint Cell;
    if (!ScreenToGrid(ScreenPosition, Cell) || !Board->SelectCell(Cell))
    {
        if (RejectedGridPresses < MAX_int32)
        {
            ++RejectedGridPresses;
        }
        return false;
    }
    LastAcceptedCell = Cell;
    if (AcceptedGridPresses < MAX_int32)
    {
        ++AcceptedGridPresses;
    }
    OnGridCellPressed.Broadcast(Cell.Y, Cell.X);
    UE_LOG(LogTemp, Display, TEXT("MyPvZ grid press: row=%d column=%d"), Cell.Y, Cell.X);
    return true;
}

void AMyPvZPlayerController::OnPrimaryPressed()
{
    float X = 0.0f;
    float Y = 0.0f;
    if (GetMousePosition(X, Y))
    {
        SubmitGridPress(FVector2D(X, Y));
    }
}
