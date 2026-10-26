"""Reload the committed M00 map and check the native bootstrap types."""
import json
from pathlib import Path

import unreal

MAP_PACKAGE = "/Game/Maps/M00_Bootstrap"
project_root = Path(unreal.Paths.project_dir()).resolve()
map_file = project_root / "Content" / "Maps" / "M00_Bootstrap.umap"
if not map_file.is_file():
    raise RuntimeError("M00: missing bootstrap map: " + str(map_file))

descriptor = json.loads((project_root / "MyPvZ.uproject").read_text(encoding="utf-8-sig"))
plugins = {item["Name"]: item for item in descriptor["Plugins"]}
if not plugins["Paper2D"]["Enabled"]:
    raise RuntimeError("M00: Paper2D must be enabled")
if plugins["PythonScriptPlugin"].get("TargetAllowList") != ["Editor"]:
    raise RuntimeError("M00: PythonScriptPlugin must be restricted to Editor")

for class_path in ("/Script/Paper2D.PaperSprite", "/Script/UMG.UserWidget"):
    if unreal.load_class(None, class_path) is None:
        raise RuntimeError("M00: required presentation module is unavailable: " + class_path)

map_settings = unreal.get_default_object(unreal.GameMapsSettings)
for setting in ("editor_startup_map", "game_default_map"):
    actual = map_settings.get_editor_property(setting).export_text().strip('"')
    if actual != MAP_PACKAGE + ".M00_Bootstrap":
        raise RuntimeError("M00: incorrect " + setting + ": " + actual)

game_mode = unreal.load_class(None, "/Script/MyPvZ.MyPvZGameMode")
controller = unreal.load_class(None, "/Script/MyPvZ.MyPvZPlayerController")
if game_mode is None or controller is None:
    raise RuntimeError("M00: native bootstrap classes failed to load")
defaults = unreal.get_default_object(game_mode)
if defaults.get_editor_property("player_controller_class") != controller:
    raise RuntimeError("M00: GameMode does not select the MyPvZ controller")
if defaults.get_editor_property("default_pawn_class") is not None:
    raise RuntimeError("M00: bootstrap must not spawn a gameplay pawn")

world = unreal.EditorLoadingAndSavingUtils.load_map(str(map_file))
if world is None or world.get_path_name() != MAP_PACKAGE + ".M00_Bootstrap":
    raise RuntimeError("M00: failed to reload the bootstrap map")

# UE 5.8 creates these bookkeeping actors while loading an empty editor world.
actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
allowed_classes = {
    "WorldSettings", "Brush", "DefaultPhysicsVolume",
    "GameplayDebuggerPlayerManager", "AbstractNavData",
}
unexpected = [actor.get_class().get_name() for actor in actors
              if actor.get_class().get_name() not in allowed_classes]
if unexpected:
    raise RuntimeError("M00: unexpected content in empty map: " + repr(unexpected))

unreal.log("M00 VALIDATION PASSED: Paper2D/UMG and native classes loaded; " + MAP_PACKAGE
           + " reloaded; only empty-world bookkeeping actors exist.")
