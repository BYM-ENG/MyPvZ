#include "MyPvZGridLayout.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "Misc/AutomationTest.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMyPvZGridCellsTest, "MyPvZ.M04.Grid.Cells",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FMyPvZGridCellsTest::RunTest(const FString&)
{
    const FMyPvZGridLayout Layout;
    TestTrue(TEXT("Default layout is valid"), Layout.IsValid());
    const double Epsilon = 0.000001;
    for (int32 Row = 0; Row < 3; ++Row)
    {
        for (int32 Column = 0; Column < 9; ++Column)
        {
            const FIntPoint ExpectedCell(Column, Row);
            const FString Label = FString::Printf(TEXT("Cell %d,%d"), Column, Row);
            FVector2D Center(-1.0, -1.0);
            TestTrue(Label + TEXT(" is valid"), Layout.IsValidCell(ExpectedCell));
            TestTrue(Label + TEXT(" has center"), Layout.TryCellToPixelCenter(ExpectedCell, Center));
            TestEqual(Label + TEXT(" center X"), Center.X, 300.0 + 80.0 * Column);
            TestEqual(Label + TEXT(" center Y"), Center.Y, 235.0 + 100.0 * Row);

            const FVector2D CornersAndCenter[] =
            {
                Center,
                FVector2D(260.0 + 80.0 * Column, 185.0 + 100.0 * Row),
                FVector2D(340.0 + 80.0 * Column - Epsilon, 185.0 + 100.0 * Row),
                FVector2D(260.0 + 80.0 * Column, 285.0 + 100.0 * Row - Epsilon),
                FVector2D(340.0 + 80.0 * Column - Epsilon, 285.0 + 100.0 * Row - Epsilon)
            };
            for (const FVector2D Pixel : CornersAndCenter)
            {
                FIntPoint ActualCell(INDEX_NONE, INDEX_NONE);
                TestTrue(Label + TEXT(" point maps"), Layout.TryPixelToCell(Pixel, ActualCell));
                TestEqual(Label + TEXT(" point column"), ActualCell.X, Column);
                TestEqual(Label + TEXT(" point row"), ActualCell.Y, Row);
            }
        }
    }

    const FIntPoint InvalidCells[] = { FIntPoint(-1, 0), FIntPoint(0, -1), FIntPoint(9, 0), FIntPoint(0, 3) };
    for (const FIntPoint Cell : InvalidCells)
    {
        FVector2D Output(123.0, 456.0);
        TestFalse(TEXT("Out-of-range cell is invalid"), Layout.IsValidCell(Cell));
        TestFalse(TEXT("Out-of-range cell has no center"), Layout.TryCellToPixelCenter(Cell, Output));
        TestTrue(TEXT("Failed center clears output"), Output == FVector2D::ZeroVector);
    }

    FMyPvZGridLayout Configured;
    Configured.Rows = 2;
    Configured.Columns = 2;
    Configured.ImageSize = FVector2D(200.0, 100.0);
    Configured.TopLeft = FVector2D(10.0, 20.0);
    Configured.CellSize = FVector2D(25.0, 30.0);
    FVector2D Center;
    FIntPoint Cell;
    TestTrue(TEXT("Edited configuration is valid"), Configured.IsValid());
    TestTrue(TEXT("Edited cell center exists"), Configured.TryCellToPixelCenter(FIntPoint(1, 1), Center));
    TestTrue(TEXT("Edited dimensions determine center"), Center == FVector2D(47.5, 65.0));
    TestTrue(TEXT("Edited pixel maps"), Configured.TryPixelToCell(FVector2D(59.0, 79.0), Cell));
    TestTrue(TEXT("Edited dimensions determine hit"), Cell == FIntPoint(1, 1));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMyPvZGridBoundaryTest, "MyPvZ.M04.Grid.Boundaries",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FMyPvZGridBoundaryTest::RunTest(const FString&)
{
    const FMyPvZGridLayout Layout;
    for (int32 Row = 0; Row < 3; ++Row)
    {
        for (int32 Column = 0; Column < 9; ++Column)
        {
            // Exact intersections belong to the cell on their right and below.
            FIntPoint Cell;
            TestTrue(TEXT("Exact grid intersection maps"),
                Layout.TryPixelToCell(FVector2D(260.0 + Column * 80.0, 185.0 + Row * 100.0), Cell));
            TestEqual(TEXT("Gridline chooses right column"), Cell.X, Column);
            TestEqual(TEXT("Gridline chooses lower row"), Cell.Y, Row);
        }
    }

    constexpr double Epsilon = 0.000001;
    const double NaN = std::numeric_limits<double>::quiet_NaN();
    const double Infinity = std::numeric_limits<double>::infinity();
    const FVector2D RejectedPixels[] =
    {
        FVector2D(260.0 - Epsilon, 235.0), FVector2D(300.0, 185.0 - Epsilon),
        FVector2D(980.0, 235.0), FVector2D(300.0, 485.0), FVector2D(980.0, 485.0),
        FVector2D(980.0 + Epsilon, 235.0), FVector2D(300.0, 485.0 + Epsilon),
        FVector2D(0.0, 0.0), FVector2D(1400.0, 600.0),
        FVector2D(NaN, 235.0), FVector2D(300.0, NaN),
        FVector2D(Infinity, 235.0), FVector2D(300.0, Infinity),
        FVector2D(-Infinity, 235.0), FVector2D(300.0, -Infinity)
    };
    for (const FVector2D Pixel : RejectedPixels)
    {
        FIntPoint Cell(4, 1);
        TestFalse(TEXT("Outside or nonfinite pixel is rejected"), Layout.TryPixelToCell(Pixel, Cell));
        TestEqual(TEXT("Failure clears column"), Cell.X, INDEX_NONE);
        TestEqual(TEXT("Failure clears row"), Cell.Y, INDEX_NONE);
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMyPvZGridInvalidLayoutTest, "MyPvZ.M04.Grid.InvalidLayouts",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FMyPvZGridInvalidLayoutTest::RunTest(const FString&)
{
    const double NaN = std::numeric_limits<double>::quiet_NaN();
    const double Infinity = std::numeric_limits<double>::infinity();
    TArray<FMyPvZGridLayout> InvalidLayouts;
    const auto AddInvalid = [&InvalidLayouts](auto Change)
    {
        FMyPvZGridLayout Layout;
        Change(Layout);
        InvalidLayouts.Add(Layout);
    };
    AddInvalid([](auto& L) { L.Rows = 0; });
    AddInvalid([](auto& L) { L.Columns = -1; });
    AddInvalid([](auto& L) { L.Rows = MAX_int32; L.Columns = 2; L.CellSize = FVector2D(0.000000001, 0.000000001); });
    AddInvalid([](auto& L) { L.ImageSize.X = 0.0; });
    AddInvalid([](auto& L) { L.ImageSize.Y = -1.0; });
    AddInvalid([NaN](auto& L) { L.ImageSize.X = NaN; });
    AddInvalid([Infinity](auto& L) { L.ImageSize.Y = Infinity; });
    AddInvalid([](auto& L) { L.CellSize.X = 0.0; });
    AddInvalid([](auto& L) { L.CellSize.Y = -1.0; });
    AddInvalid([NaN](auto& L) { L.CellSize.Y = NaN; });
    AddInvalid([Infinity](auto& L) { L.CellSize.X = Infinity; });
    AddInvalid([](auto& L) { L.TopLeft.X = -1.0; });
    AddInvalid([](auto& L) { L.TopLeft.Y = -1.0; });
    AddInvalid([NaN](auto& L) { L.TopLeft.X = NaN; });
    AddInvalid([Infinity](auto& L) { L.TopLeft.Y = Infinity; });
    AddInvalid([](auto& L) { L.Columns = 15; });
    AddInvalid([](auto& L) { L.Rows = 5; });
    AddInvalid([](auto& L) { L.CellSize.X = std::numeric_limits<double>::max(); });

    for (const FMyPvZGridLayout& Layout : InvalidLayouts)
    {
        FIntPoint Cell(4, 1);
        FVector2D Center(300.0, 235.0);
        TestFalse(TEXT("Invalid configuration is rejected"), Layout.IsValid());
        TestFalse(TEXT("Invalid layout has no valid cells"), Layout.IsValidCell(FIntPoint(0, 0)));
        TestFalse(TEXT("Invalid layout rejects pixel"), Layout.TryPixelToCell(FVector2D(300.0, 235.0), Cell));
        TestTrue(TEXT("Invalid layout clears cell"), Cell == FIntPoint(INDEX_NONE, INDEX_NONE));
        TestFalse(TEXT("Invalid layout rejects cell center"), Layout.TryCellToPixelCenter(FIntPoint(0, 0), Center));
        TestTrue(TEXT("Invalid layout clears center"), Center == FVector2D::ZeroVector);
    }

    FMyPvZGridLayout FitsExactly;
    FitsExactly.ImageSize = FVector2D(980.0, 485.0);
    TestTrue(TEXT("Board may fit exactly within image"), FitsExactly.IsValid());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMyPvZGridWorldTest, "MyPvZ.M04.Grid.WorldRoundTrip",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FMyPvZGridWorldTest::RunTest(const FString&)
{
    const FMyPvZGridLayout Layout;
    TestEqual(TEXT("Image top left is upper left in local X/Z"),
        Layout.PixelToLocalWorld(FVector2D::ZeroVector), FVector(-700.0, 0.0, 300.0));
    TestEqual(TEXT("Image bottom right is lower right in local X/Z"),
        Layout.PixelToLocalWorld(FVector2D(1400.0, 600.0)), FVector(700.0, 0.0, -300.0));
    TestEqual(TEXT("Image center is local origin"),
        Layout.PixelToLocalWorld(FVector2D(700.0, 300.0)), FVector::ZeroVector);

    FMyPvZGridLayout Configured;
    Configured.ImageSize = FVector2D(1600.0, 800.0);
    TestEqual(TEXT("Edited image dimensions determine local origin"),
        Configured.PixelToLocalWorld(FVector2D(800.0, 400.0)), FVector::ZeroVector);

    for (int32 Row = 0; Row < 3; ++Row)
    {
        for (int32 Column = 0; Column < 9; ++Column)
        {
            FVector2D Pixel;
            TestTrue(TEXT("Cell center exists"), Layout.TryCellToPixelCenter(FIntPoint(Column, Row), Pixel));
            FVector World = Layout.PixelToLocalWorld(Pixel);
            TestEqual(TEXT("Grid lies on local Y=0"), World.Y, 0.0);
            TestTrue(TEXT("Pixel/world conversion roundtrips"), Layout.LocalWorldToPixel(World).Equals(Pixel, 0.000000001));
            World.Y = 1234.0;
            FIntPoint Cell;
            TestTrue(TEXT("Depth does not affect pixel mapping"), Layout.TryPixelToCell(Layout.LocalWorldToPixel(World), Cell));
            TestEqual(TEXT("World roundtrip column"), Cell.X, Column);
            TestEqual(TEXT("World roundtrip row"), Cell.Y, Row);
        }
    }
    return true;
}

#endif
