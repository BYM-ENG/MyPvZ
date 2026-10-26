"""Repeatable M02 import from tracked copies; recreates only the independent M02 map."""
import sys
from pathlib import Path

import unreal

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m02_sample import BASE, MAP, MATERIAL, SOURCE, checked_manifest, rgba_png

manifest = checked_manifest()
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)


def create(name, directory, asset_class, factory):
    path = directory + "/" + name
    asset = unreal.load_asset(path) if assets.does_asset_exist(path) else None
    return asset or tools.create_asset(name, directory, asset_class, factory)


def import_file(item, name, directory, factory):
    task = unreal.AssetImportTask()
    task.set_editor_properties(dict(filename=str(SOURCE / item["copy"]), destination_name=name,
                                   destination_path=directory, automated=True, replace_existing=True,
                                   replace_existing_settings=True, save=False, factory=factory))
    tools.import_asset_tasks([task])
    paths = list(task.get_editor_property("imported_object_paths"))
    assert len(paths) == 1, paths
    return unreal.load_asset(paths[0])


material = unreal.load_asset(MATERIAL)
assert material is not None
sprites = []
for item in manifest["frames"]:
    frame = item["frame"]
    texture = import_file(item, f"T_ZombieStand_{frame:02d}", BASE + "/Textures", unreal.TextureFactory())
    texture.set_editor_properties(dict(compression_settings=unreal.TextureCompressionSettings.TC_EDITOR_ICON,
                                      compression_no_alpha=False, srgb=True,
                                      mip_gen_settings=unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                                      filter=unreal.TextureFilter.TF_NEAREST,
                                      lod_group=unreal.TextureGroup.TEXTUREGROUP_PIXELS2D,
                                      never_stream=True))
    width, height, _ = rgba_png(SOURCE / item["copy"])
    sprite = create(f"S_ZombieStand_{frame:02d}", BASE + "/Sprites", unreal.PaperSprite, unreal.PaperSpriteFactory())
    sprite.set_editor_property("source_texture", texture)
    sprite.set_editor_properties(dict(source_uv=unreal.Vector2D(0, 0),
                                     source_dimension=unreal.Vector2D(width, height),
                                     source_texture_dimension=unreal.Vector2D(width, height),
                                     pixels_per_unreal_unit=1.0, pivot_mode=unreal.SpritePivotMode.CENTER_CENTER,
                                     sprite_collision_domain=unreal.SpriteCollisionMode.NONE,
                                     default_material=material))
    geometry = sprite.get_editor_property("render_geometry")
    geometry.set_editor_property("geometry_type", unreal.SpritePolygonMode.SOURCE_BOUNDING_BOX)
    sprite.set_editor_property("render_geometry", geometry)
    sprites.append(sprite)

flipbook = create("FB_ZombieStand_Trial8fps", BASE + "/Flipbooks", unreal.PaperFlipbook, unreal.PaperFlipbookFactory())
frames = []
for sprite in sprites:
    key = unreal.PaperFlipbookKeyFrame()
    key.set_editor_properties(dict(sprite=sprite, frame_run=1))
    frames.append(key)
flipbook.set_editor_properties(dict(key_frames=frames, frames_per_second=manifest["trial_fps"], default_material=material))
# The checked source snapshot is immutable; reuse its existing trial wave.
# Fresh-process validation checks its full exported PCM against that snapshot.
sound_path = BASE + "/Audio/SW_SeedTrial"
sound = unreal.load_asset(sound_path) if assets.does_asset_exist(sound_path) else None
if sound is None:
    sound = import_file(manifest["audio"], "SW_SeedTrial", BASE + "/Audio", unreal.SoundFactory())
sound.set_editor_properties(dict(looping=True, volume=1.0, pitch=1.0))


def spawn(cls, label, location, rotation=unreal.Rotator(pitch=0, yaw=0, roll=0)):
    actor = actors.spawn_actor_from_class(cls, unreal.Vector(*location), rotation)
    assert actor is not None, label
    actor.set_actor_label(label)
    return actor


# Unlit checkerboard makes transparent image margins visible without lights.
checker_materials = []
for name, value in (("M_CheckerDark", 0.055), ("M_CheckerLight", 0.13)):
    mat = create(name, BASE + "/Diagnostics", unreal.Material, unreal.MaterialFactoryNew())
    unreal.MaterialEditingLibrary.delete_all_material_expressions(mat)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    constant = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector)
    constant.set_editor_property("constant", unreal.LinearColor(value, value, value, 1.0))
    unreal.MaterialEditingLibrary.connect_material_property(constant, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    checker_materials.append(mat)
plane = unreal.load_asset("/Engine/BasicShapes/Plane")
for col in range(11):
    for row in range(6):
        panel = spawn(unreal.StaticMeshActor, f"M02_Checker_{col}_{row}", (-500 + col * 100, 30, -250 + row * 100),
                      unreal.Rotator(pitch=0, yaw=0, roll=90))
        component = panel.get_component_by_class(unreal.StaticMeshComponent)
        component.set_editor_property("static_mesh", plane)
        component.set_material(0, checker_materials[(col + row) % 2])
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        component.set_cast_shadow(False)

for label, x, scale in (("M02_Static_1x", -350, 1), ("M02_Static_2x", -50, 2)):
    actor = spawn(unreal.PaperSpriteActor, label, (x, 0, 0))
    component = actor.get_component_by_class(unreal.PaperSpriteComponent)
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    assert component.set_sprite(sprites[0])
    component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
animated = spawn(unreal.PaperFlipbookActor, "M02_Loop_1x_8fps", (350, 0, 0))
animated_component = animated.get_component_by_class(unreal.PaperFlipbookComponent)
animated_component.set_mobility(unreal.ComponentMobility.MOVABLE)
assert animated_component.set_flipbook(flipbook)
animated_component.set_looping(True)
animated_component.play_from_start()

camera = spawn(unreal.CameraActor, "M02_TrialCamera", (0, -1000, 0), unreal.Rotator(pitch=0, yaw=90, roll=0))
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
camera_component = camera.get_component_by_class(unreal.CameraComponent)
camera_component.set_editor_properties(dict(projection_mode=unreal.CameraProjectionMode.ORTHOGRAPHIC,
                                          ortho_width=1100.0, aspect_ratio=16 / 9,
                                          constrain_aspect_ratio=True, post_process_blend_weight=0.0))
audio = spawn(unreal.AmbientSound, "M02_SeedAudio_Looping", (0, 0, 0))
audio_component = audio.get_component_by_class(unreal.AudioComponent)
audio_component.set_sound(sound)
audio_component.set_editor_properties(dict(auto_activate=True, allow_spatialization=False,
                                           volume_multiplier=0.6, pitch_multiplier=1.0))


def text(label, value, x, z, size):
    actor = spawn(unreal.TextRenderActor, label, (x, -10, z), unreal.Rotator(pitch=0, yaw=-90, roll=0))
    component = actor.get_component_by_class(unreal.TextRenderComponent)
    component.set_text(value)
    component.set_world_size(size)
    component.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    component.set_text_render_color(unreal.Color(240, 245, 250, 255))


text("M02_Title", "M02 | Import trial", 0, 255, 30)
for x, value in ((-350, "Static 1x"), (-50, "Static 2x"), (350, "Loop 1x / 8 fps")):
    text("M02_Label_" + str(x), value, x, 195, 23)
text("M02_SourceNote", "11 frames: 1, 2, ... 10, 11 | trial 8 fps (source FPS unknown)", 0, -205, 19)
text("M02_AudioNote", "seed.wav | stereo 22050 Hz | looping import sample", 0, -245, 19)

assert unreal.EditorLoadingAndSavingUtils.save_map(world, MAP)
assert assets.save_directory(BASE, only_if_is_dirty=False, recursive=True)
unreal.log("M02 IMPORT PASSED: 11 textures + sprites, numeric 8fps trial flipbook, SoundWave and " + MAP)
