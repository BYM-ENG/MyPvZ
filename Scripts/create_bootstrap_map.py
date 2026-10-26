"""Create the M00 empty map once; preserve an existing map for later milestones."""
from pathlib import Path

import unreal

MAP_PACKAGE = "/Game/Maps/M00_Bootstrap"
map_file = Path(unreal.Paths.project_content_dir()) / "Maps" / "M00_Bootstrap.umap"
if map_file.exists():
    unreal.log("M00: bootstrap map already exists; leaving it unchanged.")
else:
    map_file.parent.mkdir(parents=True, exist_ok=True)
    world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    if world is None:
        raise RuntimeError("M00: could not create an empty world")
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, MAP_PACKAGE):
        raise RuntimeError("M00: could not save the bootstrap map")
    if not map_file.is_file():
        raise RuntimeError("M00: map save returned success without a .umap file")
    unreal.log("M00: created " + MAP_PACKAGE)
