"""Run all seven imported Flipbooks in an unsaved editor simulation, then exit.

Use the graphical editor with -ExecutePythonScript, without -nullrhi. No asset,
map or default configuration is saved. Results go to Saved/Diagnostics/M03.
"""
import json
import sys
import time
import traceback
from pathlib import Path

import unreal

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m03_assets import ROOT, checked_manifest

output = ROOT / "Saved/Diagnostics/M03/runtime.json"
output.parent.mkdir(parents=True, exist_ok=True)
result = dict(status="RUNNING", mode="Editor simulation; unsaved transient world", animations={})
output.write_text(json.dumps(result), encoding="utf-8")
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
# This minimal project may load LevelEditor after editor subsystem discovery.
# These two methods only forward requests to GUnrealEd (installed 5.8.2 source).
if levels is None:
    levels = unreal.get_default_object(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
started = time.monotonic()
handle, game_started = None, None
samples = {}


def finish(error=None):
    global handle
    if error is not None:
        result.update(status="FAIL", error=str(error), traceback=traceback.format_exc())
    else:
        result["status"] = "PASS"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    unreal.log("M03 RUNTIME " + result["status"] + ": " + str(result))
    if handle is not None:
        unreal.unregister_slate_post_tick_callback(handle)
    try:
        levels.editor_request_end_play()
    finally:
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()


def tick(delta_seconds):
    global game_started
    try:
        assert time.monotonic() - started < 90, "Timed out starting/sampling simulation"
        world = editor.get_game_world()
        if world is None:
            return
        runtime_actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PaperFlipbookActor)
        if len(runtime_actors) != len(groups):
            return
        if game_started is None:
            game_started = time.monotonic()
        for actor in runtime_actors:
            component = actor.get_component_by_class(unreal.PaperFlipbookComponent)
            path = component.get_flipbook().get_path_name()
            assert path in samples and component.is_playing() and component.is_looping(), path
            samples[path].add(component.get_playback_position_in_frames())
        if time.monotonic() - game_started >= 0.75:
            for path, positions in samples.items():
                assert len(positions) >= 2, "Animation did not advance: " + path
                result["animations"][path] = dict(observed_frames=sorted(positions), playing=True, looping=True)
            result["runtime_actor_count"] = len(runtime_actors)
            result["sample_seconds"] = time.monotonic() - game_started
            finish()
    except Exception as error:
        finish(error)


try:
    groups = checked_manifest()["animations"]
    unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    for index, group in enumerate(groups):
        flipbook = unreal.load_asset(group["flipbook"])
        assert isinstance(flipbook, unreal.PaperFlipbook), group["id"]
        actor = actors.spawn_actor_from_class(unreal.PaperFlipbookActor, unreal.Vector(-450 + index * 150, 0, 0))
        actor.set_actor_label("M03_Smoke_" + group["id"])
        component = actor.get_component_by_class(unreal.PaperFlipbookComponent)
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        assert component.set_flipbook(flipbook)
        component.set_looping(True)
        component.play_from_start()
        samples[flipbook.get_path_name()] = set()
    editor.set_level_viewport_camera_info(
        unreal.Vector(0, -1000, 0), unreal.Rotator(pitch=0, yaw=90, roll=0))
    handle = unreal.register_slate_post_tick_callback(tick)
    levels.editor_play_simulate()
except Exception as error:
    finish(error)
