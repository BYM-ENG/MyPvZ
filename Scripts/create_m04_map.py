"""Create the M04 board once; never overwrite an existing edited level."""
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
package = "/Game/Maps/PvZ_Lawn"
filename = root / "Content/Maps/PvZ_Lawn.umap"
if filename.exists():
    world = unreal.EditorLoadingAndSavingUtils.load_map(str(filename))
    assert world and len(unreal.GameplayStatics.get_all_actors_of_class(
        world, unreal.load_class(None, "/Script/MyPvZ.MyPvZBoard"))) == 1
    unreal.log("M04 map already exists; preserving saved level.")
else:
    world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    cls = unreal.load_class(None, "/Script/MyPvZ.MyPvZBoard")
    assert cls is not None
    actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
        cls, unreal.Vector(0, 0, 0))
    assert actor is not None
    actor.set_actor_label("PvZ_Board")
    assert unreal.EditorLoadingAndSavingUtils.save_map(world, package)
    unreal.log("M04 MAP PASSED: " + package)
