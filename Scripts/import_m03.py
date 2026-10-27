"""Import the frozen catalog at stable paths; unchanged inputs never replace SoundWaves."""
import json
import sys
from pathlib import Path

import unreal

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m03_assets import BASE, MATERIAL, ROOT, SOURCE, checked_manifest, sha256

manifest = checked_manifest()
tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
material = unreal.load_asset(MATERIAL)
assert material is not None
created, reused = [], []


def import_media(item, key, cls, factory):
    path = item[key]
    asset = unreal.load_asset(path) if assets.does_asset_exist(path) else None
    if asset is not None:
        assert isinstance(asset, cls), path
        assert assets.get_metadata_tag(asset, "MyPvZ.SourceSHA256") == item["sha256"], \
            "Refusing to replace an unrecognized or changed frozen asset: " + path
        reused.append(path)
        return asset, False
    directory, name = path.rsplit("/", 1)
    task = unreal.AssetImportTask()
    task.set_editor_properties(dict(filename=str(SOURCE / item["source"]), destination_path=directory,
                                   destination_name=name, automated=True, replace_existing=False,
                                   save=False, factory=factory))
    tools.import_asset_tasks([task])
    imported = list(task.get_editor_property("imported_object_paths"))
    assert imported == [path + "." + name], (path, imported)
    asset = unreal.load_asset(path)
    assert isinstance(asset, cls), path
    assets.set_metadata_tag(asset, "MyPvZ.SourceSHA256", item["sha256"])
    assets.set_metadata_tag(asset, "MyPvZ.SourcePath", item["source"])
    created.append(path)
    return asset, True


def create(path, cls, factory):
    if assets.does_asset_exist(path):
        asset = unreal.load_asset(path)
        assert isinstance(asset, cls), path
        reused.append(path)
        return asset, False
    directory, name = path.rsplit("/", 1)
    asset = tools.create_asset(name, directory, cls, factory)
    assert isinstance(asset, cls), path
    created.append(path)
    return asset, True


for item in manifest["items"]:
    if item["canonical_source"] != item["source"]:
        continue
    if item["kind"] == "image":
        texture, is_new = import_media(item, "texture", unreal.Texture2D, unreal.TextureFactory())
        if is_new:
            texture.set_editor_properties(dict(compression_settings=unreal.TextureCompressionSettings.TC_EDITOR_ICON,
                                              compression_no_alpha=False, srgb=True,
                                              mip_gen_settings=unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                                              filter=unreal.TextureFilter.TF_NEAREST,
                                              lod_group=unreal.TextureGroup.TEXTUREGROUP_PIXELS2D, never_stream=True))
            assert assets.save_loaded_asset(texture, only_if_is_dirty=False)
        sprite, is_new = create(item["sprite"], unreal.PaperSprite, unreal.PaperSpriteFactory())
        if is_new:
            sprite.set_editor_properties(dict(source_texture=texture, source_uv=unreal.Vector2D(0, 0),
                                             source_dimension=unreal.Vector2D(item["width"], item["height"]),
                                             source_texture_dimension=unreal.Vector2D(item["width"], item["height"]),
                                             pixels_per_unreal_unit=1.0, pivot_mode=unreal.SpritePivotMode.CENTER_CENTER,
                                             sprite_collision_domain=unreal.SpriteCollisionMode.NONE,
                                             default_material=material))
            geometry = sprite.get_editor_property("render_geometry")
            geometry.set_editor_property("geometry_type", unreal.SpritePolygonMode.SOURCE_BOUNDING_BOX)
            sprite.set_editor_property("render_geometry", geometry)
            assert assets.save_loaded_asset(sprite, only_if_is_dirty=False)
    else:
        sound, is_new = import_media(item, "sound", unreal.SoundWave, unreal.SoundFactory())
        if is_new:
            # M16 owns event bindings and looping policy, including music.
            sound.set_editor_properties(dict(looping=False, volume=1.0, pitch=1.0))
            assert assets.save_loaded_asset(sound, only_if_is_dirty=False)

for group in manifest["animations"]:
    flipbook, is_new = create(group["flipbook"], unreal.PaperFlipbook, unreal.PaperFlipbookFactory())
    if is_new:
        frames = []
        for item in group["frames"]:
            sprite = unreal.load_asset(item["sprite"])
            assert sprite is not None
            key = unreal.PaperFlipbookKeyFrame()
            key.set_editor_properties(dict(sprite=sprite, frame_run=1))
            frames.append(key)
        flipbook.set_editor_properties(dict(key_frames=frames, frames_per_second=group["fps"], default_material=material))
        assert assets.save_loaded_asset(flipbook, only_if_is_dirty=False)

output = ROOT / "Saved/Diagnostics/M03"
output.mkdir(parents=True, exist_ok=True)
report = dict(status="PASS", manifest_sha256=sha256(SOURCE / "manifest.json"),
              created=sorted(created), reused=sorted(reused), source_count=len(manifest["items"]))
(output / "import.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log(f"M03 IMPORT PASSED: {len(created)} created, {len(reused)} reused; 150 original source mappings")
