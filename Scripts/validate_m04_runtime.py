"""Validate the saved M04 map in graphical PIE; never save the validation world.

SubmitGridPress exercises the same native dispatch used by the mouse binding.
It is an injected input test, not a hardware/Slate mouse-click test.
"""
import configparser
import hashlib
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

import unreal

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
MAP = "/Game/Maps/PvZ_Lawn"
BOOTSTRAP = "/Game/Maps/M00_Bootstrap"
OUTPUT = ROOT / "Saved/Diagnostics/M04/runtime.json"
SCREENSHOT = OUTPUT.with_name("lawn.png")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
result = dict(
    status="RUNNING", run_id=os.environ.get("MYPVZ_M04_RUN_ID", "standalone"),
    mode="Graphical PlayInEditor; native SubmitGridPress injection",
    hardware_mouse_validated=False, map=MAP, map_loads=[],
    counts=dict(cell_centers=0, exact_pixel_boundaries=0, projected_near_boundaries=0,
                off_viewport=0, letterbox=0, nonfinite=0, submitted=0,
                accepted=0, rejected=0),
    nonfinite_unavailable=[], exact_projected_edge_observations=[])
OUTPUT.write_text(json.dumps(result), encoding="utf-8")
started = time.monotonic()
handle = None
levels = None
finished = False
ready_at = None
config_bytes = None
map_bytes_hash = None
screenshot_task = None
capture_at = None


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def point(value):
    return [value.x, value.y]


def xyz(value):
    return [value.x, value.y, value.z]


def returned(value):
    """UE bindings may retain bool+outs or map bool failure to None."""
    if value is None:
        return False, ()
    if isinstance(value, tuple):
        if value and isinstance(value[0], bool):
            return value[0], value[1:]
        return True, value
    if isinstance(value, bool):
        return value, ()
    return True, (value,)


def one(value, description):
    success, outputs = returned(value)
    check(success and len(outputs) == 1, description + ": " + repr(value))
    return outputs[0]


def cell_result(value):
    success, outputs = returned(value)
    if not success:
        return None
    check(len(outputs) == 1, "Unexpected grid result: " + repr(value))
    return tuple(point(outputs[0]))


def config_defaults():
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.optionxform = str
    config.read_string((ROOT / "Config/DefaultEngine.ini").read_text(encoding="utf-8-sig"))
    maps = config["/Script/EngineSettings.GameMapsSettings"]
    expected = BOOTSTRAP + ".M00_Bootstrap"
    for key in ("EditorStartupMap", "GameDefaultMap"):
        check(maps[key].strip('"') in (BOOTSTRAP, expected), key + " changed from M00: " + maps[key])
    return {key: maps[key] for key in ("EditorStartupMap", "GameDefaultMap")}


def inspect_board(world):
    boards = unreal.GameplayStatics.get_all_actors_of_class(world, board_class)
    check(len(boards) == 1, "Expected exactly one native board; found " + str(len(boards)))
    board = boards[0]
    layout = board.get_editor_property("grid_layout")
    check(layout.rows == 3 and layout.columns == 9, "Saved grid dimensions changed")
    for name, expected in (("image_size", (1400, 600)), ("top_left", (260, 185)),
                           ("cell_size", (80, 100))):
        check(tuple(point(getattr(layout, name))) == expected, "Grid " + name)
    check(xyz(board.get_actor_location()) == [0, 0, 0], "Board must be at origin")
    check(xyz(board.get_actor_scale3d()) == [1, 1, 1], "Board scale must preserve source pixels")
    camera = board.get_editor_property("board_camera")
    background = board.get_editor_property("background")
    check(isinstance(camera, unreal.CameraComponent), "Missing board camera")
    check(isinstance(background, unreal.PaperSpriteComponent), "Missing background component")
    check(camera.get_editor_property("projection_mode") == unreal.CameraProjectionMode.ORTHOGRAPHIC,
          "Board camera must be orthographic")
    check(abs(camera.get_editor_property("ortho_width") - 1400) < 0.001, "Camera ortho width")
    check(abs(camera.get_editor_property("aspect_ratio") - 7 / 3) < 0.00001, "Camera aspect")
    check(camera.get_editor_property("constrain_aspect_ratio"), "Camera must constrain aspect ratio")
    sprite = background.get_sprite()
    check(sprite is not None and sprite.get_path_name() == "/Game/PvZ/Sprites/S_res_bg.S_res_bg",
          "Background sprite reference")
    texture = sprite.get_editor_property("source_texture")
    check(texture is not None and texture.get_path_name() == "/Game/PvZ/Textures/T_res_bg.T_res_bg",
          "Background texture reference")
    origin, extent, _ = unreal.SystemLibrary.get_component_bounds(background)
    check(abs(2 * extent.x - 1400) < 0.01 and abs(2 * extent.z - 600) < 0.01,
          "Background bounds must cover 1400x600 source pixels: " + repr(xyz(extent)))
    check(abs(origin.x) < 0.01 and abs(origin.z) < 0.01, "Background image is not centered")
    result["presentation"] = dict(camera=camera.get_path_name(), ortho_width=1400,
                                  aspect_ratio=camera.get_editor_property("aspect_ratio"),
                                  sprite=sprite.get_path_name(), texture=texture.get_path_name(),
                                  background_world_size=[2 * extent.x, 2 * extent.z])
    return board


def world_pixel(x, y):
    return unreal.Vector(x - 700, 0, 300 - y)


def project(pc, x, y):
    screen = one(unreal.GameplayStatics.project_world_to_screen(pc, world_pixel(x, y), False),
                 "Project source pixel")
    check(math.isfinite(screen.x) and math.isfinite(screen.y), "Nonfinite projected point")
    return screen


def state(pc, board):
    return (pc.get_editor_property("accepted_grid_presses"),
            pc.get_editor_property("rejected_grid_presses"),
            tuple(point(board.get_editor_property("selected_cell"))),
            tuple(point(pc.get_editor_property("last_accepted_cell"))))


def press(pc, board, screen, expected, group):
    before = state(pc, board)
    actual = cell_result(pc.screen_to_grid(screen))
    check(actual == expected, group + " ScreenToGrid: expected " + repr(expected) + ", got " + repr(actual))
    # The pure conversion itself must not consume the press or change selection.
    check(state(pc, board) == before, "ScreenToGrid mutated selection/counters")
    accepted = pc.submit_grid_press(screen)
    check(accepted is (expected is not None), group + " SubmitGridPress return")
    after = state(pc, board)
    if expected is None:
        check(after == (before[0], before[1] + 1, before[2], before[3]),
              group + " invalid input changed accepted count/selection or missed rejected count")
        result["counts"]["rejected"] += 1
    else:
        check(after == (before[0] + 1, before[1], expected, expected),
              group + " valid input did not select/count exactly once")
        result["counts"]["accepted"] += 1
    result["counts"]["submitted"] += 1
    result["counts"][group] += 1


def exercise(pc, board, view_rect):
    viewport = tuple(pc.get_viewport_size())
    check(len(viewport) == 2 and min(viewport) > 0, "Missing game viewport")
    lo, hi = view_rect
    result["viewport"] = list(viewport)
    result["view_rect"] = dict(min=point(lo), max=point(hi))
    check(0 <= lo.x < hi.x <= viewport[0] and 0 <= lo.y < hi.y <= viewport[1], "Invalid constrained rect")
    check(abs((hi.x - lo.x) / (hi.y - lo.y) - 7 / 3) < 0.015, "Unexpected constrained aspect")
    for pixel, corner in (((0, 0), lo), ((1400, 600), hi)):
        actual = project(pc, *pixel)
        check(abs(actual.x - corner.x) < 1.1 and abs(actual.y - corner.y) < 1.1,
              "Board image projection does not match camera view rect")
    check(state(pc, board) == (0, 0, (-1, -1), (-1, -1)), "PIE counters/selection were not initially empty")
    for row in range(3):
        for column in range(9):
            pixel = (300 + column * 80, 235 + row * 100)
            world = one(board.cell_to_world(unreal.IntPoint(column, row)), "CellToWorld")
            check(all(abs(a - b) < 0.001 for a, b in zip(xyz(world), xyz(world_pixel(*pixel)))),
                  "CellToWorld center differs from source-image contract")
            check(cell_result(board.pixel_to_cell(unreal.Vector2D(*pixel))) == (column, row), "Pixel center")
            press(pc, board, project(pc, *pixel), (column, row), "cell_centers")
    epsilon = 0.25
    result["projected_boundary_epsilon_source_pixels"] = epsilon
    result["exact_projected_edge_note"] = (
        "Exact half-open edges are asserted in PixelToCell. Screen projection/deprojection uses UE float math; "
        "screen assertions use +/-0.25 source pixels; exact projected edges below are observations only.")
    edges = (("left", 260, 235, 0), ("right", 980, 235, 0),
             ("top", 300, 185, 1), ("bottom", 300, 485, 1))
    for name, x, y, axis in edges:
        for delta in (-epsilon, 0, epsilon):
            px, py = (x + delta, y) if axis == 0 else (x, y + delta)
            inside = 260 <= px < 980 and 185 <= py < 485
            expected = (int((px - 260) // 80), int((py - 185) // 100)) if inside else None
            check(cell_result(board.pixel_to_cell(unreal.Vector2D(px, py))) == expected,
                  name + " exact pixel boundary " + str(delta))
            result["counts"]["exact_pixel_boundaries"] += 1
            screen = project(pc, px, py)
            if delta:
                press(pc, board, screen, expected, "projected_near_boundaries")
            else:
                observed = cell_result(pc.screen_to_grid(screen))
                result["exact_projected_edge_observations"].append(
                    dict(edge=name, source_pixel=[px, py], expected_pixel_cell=expected,
                         screen=point(screen), observed_screen_cell=observed))
    width, height = viewport
    for x, y in ((-1, height / 2), (width, height / 2), (width / 2, -1), (width / 2, height)):
        press(pc, board, unreal.Vector2D(x, y), None, "off_viewport")
    bars = []
    if lo.x > 0:
        bars.append((lo.x / 2, height / 2))
    if hi.x < width:
        bars.append(((hi.x + width) / 2, height / 2))
    if lo.y > 0:
        bars.append((width / 2, lo.y / 2))
    if hi.y < height:
        bars.append((width / 2, (hi.y + height) / 2))
    check(bars, "No letterbox/pillarbox pixels available; rerun with a non-7:3 viewport")
    for pixel in bars:
        press(pc, board, unreal.Vector2D(*pixel), None, "letterbox")
    for name, pixel in (("nan_x", (float("nan"), 100)), ("nan_y", (100, float("nan"))),
                         ("positive_inf_x", (float("inf"), 100)), ("negative_inf_x", (-float("inf"), 100)),
                         ("positive_inf_y", (100, float("inf"))), ("negative_inf_y", (100, -float("inf")))):
        try:
            screen = unreal.Vector2D(*pixel)
            # Conversion rejection is a binding limitation, not a native rejection.
            pc.screen_to_grid(screen)
        except (TypeError, ValueError, OverflowError) as error:
            result["nonfinite_unavailable"].append(dict(case=name, reason=str(error)))
            continue
        press(pc, board, screen, None, "nonfinite")
    final = state(pc, board)
    check(final[0] == result["counts"]["accepted"] and final[1] == result["counts"]["rejected"],
          "Final diagnostic counters differ from submitted input totals")
    result["final_state"] = dict(accepted=final[0], rejected=final[1], selected_cell=final[2],
                                 last_accepted_cell=final[3])
    check(result["counts"]["cell_centers"] == 27, "Did not test all 27 centers")
    check(result["counts"]["accepted"] == 31, "Expected 27 centers plus four near-edge accepted presses")


def finish(error=None):
    global handle, finished
    if finished:
        return
    finished = True
    if error is None:
        result["status"] = "PASS"
    else:
        result.update(status="FAIL", error=str(error), traceback=traceback.format_exc())
    try:
        check(config_bytes == (ROOT / "Config/DefaultEngine.ini").read_bytes(), "DefaultEngine.ini changed")
        check(map_bytes_hash == hashlib.sha256((ROOT / "Content/Maps/PvZ_Lawn.umap").read_bytes()).hexdigest(),
              "Validation modified the saved M04 map")
        result["default_maps"] = config_defaults()
        result["saved_map_unchanged"] = True
    except Exception as invariant_error:
        result.update(status="FAIL", invariant_error=str(invariant_error))
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    try:
        OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        unreal.log("M04 RUNTIME " + result["status"] + ": " + str(OUTPUT))
    finally:
        if handle is not None:
            # EndPlay is deferred. Exit on a later editor tick after PIE teardown.
            levels.editor_request_end_play()
        else:
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.SystemLibrary.quit_editor()


def request_screenshot(pc):
    global screenshot_task, capture_at
    try:
        SCREENSHOT.unlink(missing_ok=True)
        # Route through the player's GameViewport. AutomationLibrary captures
        # the level editor's free viewport, which is not the PIE board camera.
        capture_at = time.monotonic()
        unreal.SystemLibrary.execute_console_command(
            editor.get_game_world(), 'Shot filename="' + SCREENSHOT.as_posix() + '" -nosuffix', pc)
    except Exception as error:
        result["screenshot"] = dict(status="UNAVAILABLE", reason=str(error))
        finish()


def poll_screenshot():
    if SCREENSHOT.exists() and SCREENSHOT.stat().st_size >= 24:
        header = SCREENSHOT.read_bytes()[:24]
        if header[:8] == b"\x89PNG\r\n\x1a\n":
            result["screenshot"] = dict(status="CAPTURED", path=str(SCREENSHOT),
                                        width=int.from_bytes(header[16:20], "big"),
                                        height=int.from_bytes(header[20:24], "big"))
            finish()
            return
    if time.monotonic() - capture_at > 10:
        result["screenshot"] = dict(status="UNAVAILABLE", reason="PNG did not arrive within 10s")
        finish()


def tick(delta_seconds):
    global ready_at, handle
    try:
        if finished:
            if editor.get_game_world() is None:
                unreal.unregister_slate_post_tick_callback(handle)
                handle = None
                unreal.EditorPythonScripting.set_keep_python_script_alive(False)
                unreal.SystemLibrary.quit_editor()
            return
        check(time.monotonic() - started < 90, "Timed out waiting for graphical PIE local controller/view rect")
        if capture_at is not None:
            poll_screenshot()
            return
        world = editor.get_game_world()
        if world is None:
            return
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        if pc is None or pc.get_class() != controller_class or not pc.is_local_controller():
            return
        if pc.get_editor_property("board") is None:
            return
        success, outputs = returned(pc.get_board_view_rect())
        if not success or len(outputs) != 2 or outputs[1].x <= outputs[0].x or outputs[1].y <= outputs[0].y:
            return
        if ready_at is None:
            ready_at = time.monotonic()
            return
        if time.monotonic() - ready_at < 0.25:
            return
        if unreal.GameplayStatics.get_time_seconds(world) < 0.5:
            return
        board = inspect_board(world)
        camera = board.get_editor_property("board_camera")
        manager = unreal.GameplayStatics.get_player_camera_manager(world, 0)
        result["camera_diagnostics"] = dict(active=camera.is_active(),
            cached_location=xyz(manager.get_camera_location()),
            cached_rotation=str(manager.get_camera_rotation()),
            game_seconds=unreal.GameplayStatics.get_time_seconds(world))
        check(pc.get_editor_property("board") == board, "Controller references a different board")
        check(pc.get_view_target() == board, "Native BeginPlay did not select the board camera")
        result["controller_class"] = pc.get_class().get_path_name()
        result["view_target"] = board.get_path_name()
        exercise(pc, board, outputs)
        request_screenshot(pc)
    except Exception as error:
        finish(error)


try:
    command_line = unreal.SystemLibrary.get_command_line()
    check("-nullrhi" not in command_line.lower(), "M04 runtime validation requires a graphical renderer")
    result["renderer"] = "Graphical editor/PIE viewport; -nullrhi absent"
    config_bytes = (ROOT / "Config/DefaultEngine.ini").read_bytes()
    result["default_maps"] = config_defaults()
    map_bytes_hash = hashlib.sha256((ROOT / "Content/Maps/PvZ_Lawn.umap").read_bytes()).hexdigest()
    board_class = unreal.load_class(None, "/Script/MyPvZ.MyPvZBoard")
    controller_class = unreal.load_class(None, "/Script/MyPvZ.MyPvZPlayerController")
    check(board_class is not None and controller_class is not None, "Build M04 native editor module first")
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if levels is None:
        levels = unreal.get_default_object(unreal.LevelEditorSubsystem)
    for load in range(2):
        world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
        check(world is not None, "Could not load saved M04 map")
        board = inspect_board(world)
        check(tuple(point(board.get_editor_property("selected_cell"))) == (-1, -1), "Saved map selection")
        result["map_loads"].append(dict(load=load + 1, board=board.get_path_name()))
        if load == 0:
            check(unreal.EditorLoadingAndSavingUtils.load_map(BOOTSTRAP) is not None, "Could not unload M04")
    handle = unreal.register_slate_post_tick_callback(tick)
    # Installed 5.8.2 implementation only forwards to GUnrealEd; the CDO fallback
    # is safe when LevelEditor loaded after editor subsystem initialization.
    levels.editor_request_begin_play()
except Exception as error:
    finish(error)
