"""Independent fresh-process reload and source/export roundtrip checks for M02."""
import hashlib
import json
import math
import sys
from pathlib import Path

import unreal

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m02_sample import ROOT, SOURCE, BASE, MAP, MATERIAL, checked_manifest, rgba_png, wav_data

manifest = checked_manifest()
output = ROOT / "Saved" / "Diagnostics" / "M02"
output.mkdir(parents=True, exist_ok=True)
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)


def load(path, cls):
    asset = unreal.load_asset(path)
    assert isinstance(asset, cls), path
    return asset


def export(asset, filename, exporter):
    path = output / filename
    task = unreal.AssetExportTask()
    task.set_editor_properties(dict(object=asset, filename=str(path), exporter=exporter,
                                   automated=True, prompt=False, replace_identical=True))
    assert unreal.Exporter.run_asset_export_task(task), filename
    assert path.is_file(), filename
    return path


material = load(MATERIAL, unreal.MaterialInterface)
base_material = material.get_base_material()
overrides = material.get_editor_property("base_property_overrides") if isinstance(material, unreal.MaterialInstance) else None
blend = (overrides.get_editor_property("blend_mode") if overrides and overrides.get_editor_property("override_blend_mode")
         else base_material.get_editor_property("blend_mode"))
assert blend == unreal.BlendMode.BLEND_TRANSLUCENT, str(blend)
assert base_material.get_editor_property("shading_model") == unreal.MaterialShadingModel.MSM_UNLIT
sprites, texture_results = [], []
for item in manifest["frames"]:
    frame = item["frame"]
    texture = load(f"{BASE}/Textures/T_ZombieStand_{frame:02d}", unreal.Texture2D)
    expected_settings = dict(compression_settings=unreal.TextureCompressionSettings.TC_EDITOR_ICON,
                             compression_no_alpha=False, srgb=True,
                             mip_gen_settings=unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                             filter=unreal.TextureFilter.TF_NEAREST,
                             lod_group=unreal.TextureGroup.TEXTUREGROUP_PIXELS2D, never_stream=True)
    for key, value in expected_settings.items():
        assert texture.get_editor_property(key) == value, (texture.get_name(), key)
    width, height, original = rgba_png(SOURCE / item["copy"])
    assert (texture.blueprint_get_size_x(), texture.blueprint_get_size_y()) == (width, height)
    exported_path = export(texture, f"roundtrip_{frame:02d}.png", unreal.TextureExporterPNG())
    out_width, out_height, imported = rgba_png(exported_path)
    assert (out_width, out_height) == (width, height)
    assert imported[3::4] == original[3::4], f"Frame {frame} alpha changed"
    # UE fills RGB beneath zero-alpha pixels during PNG import. Those pixels
    # have no visible color; preserve all nonzero-alpha RGB and every alpha byte.
    assert all(imported[i:i + 3] == original[i:i + 3]
               for i in range(0, len(original), 4) if original[i + 3]), f"Frame {frame} visible RGB changed"
    sprite = load(f"{BASE}/Sprites/S_ZombieStand_{frame:02d}", unreal.PaperSprite)
    assert sprite.get_editor_property("source_texture") == texture
    assert sprite.get_editor_property("pixels_per_unreal_unit") == 1.0
    assert sprite.get_editor_property("default_material") == material
    dimension = sprite.get_editor_property("source_dimension")
    assert (dimension.x, dimension.y) == (width, height)
    assert sprite.get_editor_property("render_geometry").get_editor_property("geometry_type") == unreal.SpritePolygonMode.SOURCE_BOUNDING_BOX
    sprites.append(sprite)
    texture_results.append(dict(frame=frame, width=width, height=height,
                                alpha_min=min(original[3::4]), alpha_max=max(original[3::4]),
                                alpha_roundtrip_exact=True, visible_rgb_roundtrip_exact=True))

flipbook = load(BASE + "/Flipbooks/FB_ZombieStand_Trial8fps", unreal.PaperFlipbook)
assert flipbook.get_num_frames() == flipbook.get_num_key_frames() == 11
assert flipbook.get_editor_property("frames_per_second") == manifest["trial_fps"] == 8.0
assert math.isclose(flipbook.get_total_duration(), 11 / 8, abs_tol=1e-6)
assert [flipbook.get_sprite_at_frame(i) for i in range(11)] == sprites
assert [key.get_editor_property("frame_run") for key in flipbook.get_editor_property("key_frames")] == [1] * 11

sound = load(BASE + "/Audio/SW_SeedTrial", unreal.SoundWave)
channels, sample_width, sample_rate, sample_count, original_pcm = wav_data(SOURCE / manifest["audio"]["copy"])
assert sound.get_editor_property("num_channels") == channels
assert sound.get_editor_property("imported_sample_rate") == sample_rate
assert math.isclose(sound.get_editor_property("duration"), sample_count / sample_rate, abs_tol=1e-6)
assert sound.get_editor_property("looping")
exported_wav = export(sound, "roundtrip_seed.wav", unreal.SoundExporterWAV())
assert wav_data(exported_wav) == (channels, sample_width, sample_rate, sample_count, original_pcm), "WAV PCM roundtrip differs"

world = unreal.EditorLoadingAndSavingUtils.load_map(str(ROOT / "Content/Maps/M02_ImportTrial.umap"))
assert world and world.get_path_name() == MAP + ".M02_ImportTrial"
actor_list = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
actors = {actor.get_actor_label(): actor for actor in actor_list}
bounds_report = {}
for label, scale in (("M02_Static_1x", 1), ("M02_Static_2x", 2)):
    actor = actors[label]
    assert actor.get_component_by_class(unreal.PaperSpriteComponent).get_sprite() == sprites[0]
    bounds = actor.get_actor_bounds(False)[1]
    assert math.isclose(bounds.x * 2, 166 * scale, abs_tol=0.01), label
    assert math.isclose(bounds.z * 2, 144 * scale, abs_tol=0.01), label
    bounds_report[label] = [bounds.x * 2, bounds.z * 2]
animated = actors["M02_Loop_1x_8fps"].get_component_by_class(unreal.PaperFlipbookComponent)
assert animated.get_flipbook() == flipbook and animated.is_looping() and animated.is_playing()
camera = actors["M02_TrialCamera"]
assert camera.get_auto_activate_player_index() == 0
rotation = camera.get_actor_rotation()
assert all(math.isclose(actual, expected, abs_tol=1e-4) for actual, expected in
           ((rotation.pitch, 0), (rotation.yaw, 90), (rotation.roll, 0))), str(rotation)
forward = camera.get_actor_forward_vector()
assert all(math.isclose(actual, expected, abs_tol=1e-4) for actual, expected in
           ((forward.x, 0), (forward.y, 1), (forward.z, 0))), str(forward)
for label, actor in actors.items():
    if label.startswith("M02_Checker_"):
        rotation = actor.get_actor_rotation()
        assert all(math.isclose(actual, expected, abs_tol=1e-4) for actual, expected in
                   ((rotation.pitch, 0), (rotation.yaw, 0), (rotation.roll, 90))), label
assert camera.get_component_by_class(unreal.CameraComponent).get_editor_property("ortho_width") == 1100
audio = actors["M02_SeedAudio_Looping"].get_component_by_class(unreal.AudioComponent)
assert audio.get_editor_property("sound") == sound and audio.get_editor_property("auto_activate")
assert not audio.get_editor_property("allow_spatialization")
assert len([a for a in actor_list if a.get_actor_label().startswith("M02_Checker_")]) == 66
all_asset_paths = list(assets.list_assets(BASE, recursive=True, include_folder=False))
# Count each package's primary asset. SoundFactory replacement may retain an
# old SoundWave_0 registry entry; M03 owns full-import deduplication behavior.
asset_paths = [path for path in all_asset_paths if path.rsplit("/", 1)[1].split(".")[0] == path.rsplit(".", 1)[1]]
assert len(asset_paths) == 26, asset_paths
settings = unreal.get_default_object(unreal.GameMapsSettings)
for key in ("editor_startup_map", "game_default_map"):
    assert "M00_Bootstrap" in settings.get_editor_property(key).export_text()

report = dict(status="PASS", map=MAP, asset_count=len(asset_paths), textures=texture_results,
              secondary_registry_entries=[path for path in all_asset_paths if path not in asset_paths],
              frame_order=list(range(1, 12)), trial_fps=8.0, original_fps="unknown",
              pixels_per_unreal_unit=1.0, sprite_world_bounds=bounds_report,
              audio=dict(channels=channels, sample_width_bytes=sample_width, sample_rate=sample_rate,
                         frames=sample_count, duration=sample_count / sample_rate,
                         pcm_sha256=hashlib.sha256(original_pcm).hexdigest(), pcm_roundtrip_exact=True),
              visual_and_audible_runtime_check="Requires separate actual GUI/audio inspection")
(output / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("M02 VALIDATION PASSED: reload, 11 numeric frames, exact alpha/visible RGB, 1x/2x bounds and exact WAV PCM roundtrip.")
