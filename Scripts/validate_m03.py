"""Independent M03 reload, media roundtrip and package-reference validation."""
import array
import hashlib
import json
import math
import sys
import traceback
from pathlib import Path

import unreal

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m03_assets import (ROOT, SOURCE, BASE, MATERIAL, checked_manifest,
                        decode_png, wav_data, sha256)

OUTPUT = ROOT / "Saved" / "Diagnostics" / "M03"
OUTPUT.mkdir(parents=True, exist_ok=True)
REPORT_PATH = OUTPUT / "validation.json"
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
report = {"status": "FAIL", "textures": [], "sprites": [], "animations": [],
          "audio": [], "registry": {}, "dependencies": {}}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def object_path(path):
    return path if "." in path.rsplit("/", 1)[-1] else path + "." + path.rsplit("/", 1)[-1]


def registry_path(data):
    return str(data.package_name) + "." + str(data.asset_name)


def load(path, cls):
    asset = unreal.load_asset(path)
    require(isinstance(asset, cls), f"Missing/wrong class: {path}, expected {cls.__name__}")
    require(asset.get_path_name() == object_path(path), f"Unexpected object identity: {path}")
    return asset


def export(asset, filename, exporter):
    path = OUTPUT / "Roundtrip" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    task = unreal.AssetExportTask()
    task.set_editor_properties(dict(object=asset, filename=str(path), exporter=exporter,
                                   automated=True, prompt=False, replace_identical=True))
    require(unreal.Exporter.run_asset_export_task(task), f"Export failed: {asset.get_path_name()}")
    require(path.is_file(), f"No exported file: {path}")
    return path


def metadata(asset, item):
    for tag, expected in (("MyPvZ.SourceSHA256", item["sha256"]),
                          ("MyPvZ.SourcePath", item["source"])):
        require(assets.get_metadata_tag(asset, tag) == expected,
                f"Metadata mismatch: {asset.get_path_name()} {tag}")


def validate_material():
    material = load(MATERIAL, unreal.MaterialInterface)
    base = material.get_base_material()
    overrides = (material.get_editor_property("base_property_overrides")
                 if isinstance(material, unreal.MaterialInstance) else None)
    blend = (overrides.get_editor_property("blend_mode")
             if overrides and overrides.get_editor_property("override_blend_mode")
             else base.get_editor_property("blend_mode"))
    require(blend == unreal.BlendMode.BLEND_TRANSLUCENT, "Sprite material must be translucent")
    require(base.get_editor_property("shading_model") == unreal.MaterialShadingModel.MSM_UNLIT,
            "Sprite material must be unlit")
    return material


def validate_image(item, material):
    texture = load(item["texture"], unreal.Texture2D)
    metadata(texture, item)
    width, height = item["width"], item["height"]
    require((texture.blueprint_get_size_x(), texture.blueprint_get_size_y()) == (width, height),
            f"Texture dimensions: {item['source']}")
    settings = dict(compression_settings=unreal.TextureCompressionSettings.TC_EDITOR_ICON,
                    compression_no_alpha=False, srgb=True,
                    mip_gen_settings=unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                    filter=unreal.TextureFilter.TF_NEAREST,
                    lod_group=unreal.TextureGroup.TEXTUREGROUP_PIXELS2D, never_stream=True)
    for key, value in settings.items():
        require(texture.get_editor_property(key) == value, f"Texture setting: {item['texture']} {key}")
    filename = item["texture"][len(BASE):].strip("/") + ".png"
    ow, oh, imported = decode_png(export(texture, filename, unreal.TextureExporterPNG()))
    require((ow, oh) == (width, height), f"Exported dimensions: {item['source']}")
    result = dict(source=item["source"], texture=item["texture"], width=width, height=height)
    if Path(item["source"]).suffix.lower() == ".png":
        sw, sh, original = decode_png(SOURCE / item["source"])
        require((sw, sh) == (width, height), f"Source dimensions: {item['source']}")
        require(imported[3::4] == original[3::4], f"PNG alpha changed: {item['source']}")
        require(all(imported[i:i + 3] == original[i:i + 3]
                    for i in range(0, len(original), 4) if original[i + 3]),
                f"PNG visible RGB changed: {item['source']}")
        alpha = original[3::4]
        result.update(alpha_exact=True, visible_rgb_exact=True,
                      alpha_min=min(alpha), alpha_max=max(alpha),
                      partial_alpha=any(0 < value < 255 for value in alpha))
    else:
        require(all(value == 255 for value in imported[3::4]), f"JPEG transparency: {item['source']}")
        result.update(opaque_alpha=True, jpeg_rgb_check="not performed; lossy source")
    report["textures"].append(result)
    sprite = load(item["sprite"], unreal.PaperSprite)
    for key, expected in dict(source_texture=texture, pixels_per_unreal_unit=1.0,
                              default_material=material, pivot_mode=unreal.SpritePivotMode.CENTER_CENTER,
                              sprite_collision_domain=unreal.SpriteCollisionMode.NONE).items():
        require(sprite.get_editor_property(key) == expected, f"Sprite setting: {item['sprite']} {key}")
    for key, expected in (("source_dimension", (width, height)),
                          ("source_texture_dimension", (width, height)), ("source_uv", (0, 0))):
        vector = sprite.get_editor_property(key)
        require((vector.x, vector.y) == expected, f"Sprite dimensions/UV: {item['sprite']} {key}")
    require(sprite.get_editor_property("render_geometry").get_editor_property("geometry_type") ==
            unreal.SpritePolygonMode.SOURCE_BOUNDING_BOX, f"Sprite geometry: {item['sprite']}")
    report["sprites"].append(dict(sprite=item["sprite"], texture=item["texture"],
                                   pixels_per_unreal_unit=1.0, pivot="CENTER_CENTER", collision="NONE"))


def validate_animation(group, material):
    frames = group["frames"]
    numbers = [frame["number"] for frame in frames]
    require(numbers == list(range(1, len(frames) + 1)), f"Noncontiguous frame order: {group['id']}")
    flipbook = load(group["flipbook"], unreal.PaperFlipbook)
    require(flipbook.get_num_frames() == flipbook.get_num_key_frames() == len(frames),
            f"Flipbook frame counts: {group['id']}")
    require(flipbook.get_editor_property("frames_per_second") == group["fps"] == 8.0,
            f"Flipbook provisional FPS: {group['id']}")
    require(flipbook.get_editor_property("default_material") == material, f"Flipbook material: {group['id']}")
    require(math.isclose(flipbook.get_total_duration(), len(frames) / group["fps"], abs_tol=1e-6),
            f"Flipbook duration: {group['id']}")
    keys = flipbook.get_editor_property("key_frames")
    for index, frame in enumerate(frames):
        sprite = load(frame["sprite"], unreal.PaperSprite)
        require(flipbook.get_sprite_at_frame(index) == sprite and
                keys[index].get_editor_property("sprite") == sprite and
                keys[index].get_editor_property("frame_run") == 1,
                f"Flipbook binding/order: {group['id']} frame {frame['number']}")
    report["animations"].append(dict(id=group["id"], flipbook=group["flipbook"],
                                      frame_order=numbers, fps=group["fps"], original_fps="unknown"))


def validate_audio(item):
    sound = load(item["sound"], unreal.SoundWave)
    metadata(sound, item)
    filename = item["sound"][len(BASE):].strip("/") + ".wav"
    exported = wav_data(export(sound, filename, unreal.SoundExporterWAV()))
    channels, width, rate, count, pcm = exported
    require(channels in (1, 2) and width == 2 and rate > 0 and count > 0,
            f"Invalid decoded PCM16: {item['source']}")
    require(len(pcm) == channels * width * count and any(pcm), f"Silent/truncated PCM: {item['source']}")
    require(sound.get_editor_property("num_channels") == channels, f"Audio channels: {item['source']}")
    require(sound.get_editor_property("imported_sample_rate") == rate, f"Audio rate: {item['source']}")
    require(math.isclose(sound.get_editor_property("duration"), count / rate, abs_tol=1e-5),
            f"Audio duration: {item['source']}")
    original_wav = Path(item["source"]).suffix.lower() == ".wav"
    pcm_exact, max_error = None, None
    if original_wav:
        original = wav_data(SOURCE / item["source"])
        require(exported[:4] == original[:4], f"WAV shape changed: {item['source']}")
        pcm_exact = pcm == original[4]
        # UE 5.8.2 SoundExporterWAV requests transformed RawData, even with no
        # transformations/cues. Its libsndfile float -> PCM16 copy can round by
        # one unit; SoundFactory's original stereo PCM import is a raw clone.
        before, after = array.array("h", original[4]), array.array("h", pcm)
        max_error = max(abs(a - b) for a, b in zip(before, after))
        require(max_error <= 1, f"WAV export exceeds one PCM16 quantization unit: {item['source']}")
    report["audio"].append(dict(source=item["source"], sound=item["sound"], channels=channels,
                                sample_width_bytes=width, sample_rate=rate, frames=count,
                                duration=count / rate, pcm_sha256=hashlib.sha256(pcm).hexdigest(),
                                original_wav_pcm_exact=pcm_exact, wav_export_max_abs_error=max_error,
                                nonzero_pcm=True))


def validate_registry(manifest):
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)
    registry.scan_paths_synchronous([BASE, "/Game/M02", "/Game/Maps"], force_rescan=True)
    rows = list(registry.get_assets_by_path(BASE, recursive=True, include_only_on_disk_assets=True))
    expected = set()
    for item in manifest["items"]:
        expected.update(object_path(item[key]) for key in (("texture", "sprite")
                        if item["kind"] == "image" else ("sound",)))
    expected.update(object_path(group["flipbook"]) for group in manifest["animations"])
    actual = [registry_path(row) for row in rows]
    report["registry"] = dict(expected_count=len(expected), actual_count=len(actual),
                              missing=sorted(expected - set(actual)), extra=sorted(set(actual) - expected),
                              duplicate_rows=sorted(path for path in set(actual) if actual.count(path) > 1))
    m02_rows = list(registry.get_assets_by_path("/Game/M02", recursive=True, include_only_on_disk_assets=True))
    secondary = []
    for row in m02_rows:
        if str(row.asset_name) != str(row.package_name).rsplit("/", 1)[-1]:
            path = registry_path(row)
            loaded = unreal.load_asset(path)
            secondary.append(dict(path=path, exists=assets.does_asset_exist(path),
                                  loads=loaded is not None,
                                  loaded_path=loaded.get_path_name() if loaded else None))
    report["registry"]["m02_secondary_entries"] = secondary
    # Never discard secondary registry objects just because loading them fails.
    require(not report["registry"]["missing"] and not report["registry"]["extra"] and
            not report["registry"]["duplicate_rows"], "PvZ registry identities differ from manifest")
    require(not secondary, "M02 still contains secondary registry entries")
    map_rows = list(registry.get_assets_by_path("/Game/Maps", recursive=True, include_only_on_disk_assets=True))
    seeds = {str(row.package_name) for row in rows + m02_rows + map_rows}
    options = unreal.AssetRegistryDependencyOptions()
    options.set_editor_properties(dict(include_soft_package_references=True,
                                       include_hard_package_references=True,
                                       include_game_package_references=True,
                                       include_editor_only_package_references=True,
                                       include_searchable_names=False,
                                       include_soft_management_references=False,
                                       include_hard_management_references=False))
    pending, visited, missing, edges = list(seeds), set(), [], []
    while pending:
        package = pending.pop()
        if package in visited:
            continue
        visited.add(package)
        for dependency in registry.get_dependencies(package, options) or []:
            dependency = str(dependency)
            if not dependency.startswith(("/Game/", "/Engine/", "/Paper2D/")):
                continue
            edges.append((package, dependency))
            if not registry.get_assets_by_package_name(dependency, include_only_on_disk_assets=True):
                missing.append(dict(package=package, dependency=dependency))
            elif dependency not in visited:
                pending.append(dependency)
    report["dependencies"] = dict(seed_packages=len(seeds), checked_packages=len(visited),
                                   hard_and_soft_package_edges=len(edges), missing=missing,
                                   mounts=["/Game", "/Engine", "/Paper2D"])
    require(not missing, "Missing package dependencies")


def main():
    previous = json.loads(REPORT_PATH.read_text(encoding="utf-8")) if REPORT_PATH.is_file() else {}
    manifest = checked_manifest()
    report.update(manifest_sha256=sha256(SOURCE / "manifest.json"), source_count=len(manifest["items"]),
                  original_fps="unknown", trial_fps=8.0)
    material = validate_material()
    items = {item["source"]: item for item in manifest["items"]}
    canonical = []
    for item in manifest["items"]:
        source = items[item["canonical_source"]]
        require(source["canonical_source"] == source["source"] and item["sha256"] == source["sha256"]
                and item["kind"] == source["kind"], f"Invalid deduplication: {item['source']}")
        for key in (("texture", "sprite") if item["kind"] == "image" else ("sound",)):
            require(item[key] == source[key], f"Dedup destination differs: {item['source']} {key}")
        if item["source"] == item["canonical_source"]:
            canonical.append(item)
    report["canonical_source_count"] = len(canonical)
    require(len({(item["kind"], item["sha256"]) for item in canonical}) == len(canonical),
            "Identical source bytes have multiple canonical assets")
    for item in canonical:
        if item["kind"] == "image":
            validate_image(item, material)
        else:
            validate_audio(item)
    for group in manifest["animations"]:
        validate_animation(group, material)
    report["repeat_audio_pcm_match"] = None
    if previous.get("manifest_sha256") == report["manifest_sha256"] and previous.get("audio"):
        baseline = {row["sound"]: row["pcm_sha256"] for row in previous["audio"]}
        current = {row["sound"]: row["pcm_sha256"] for row in report["audio"]}
        require(all(current.get(path) == value for path, value in baseline.items()),
                "Audio PCM differs from previous validation of the same manifest")
        if previous.get("status") == "PASS":
            require(current.keys() == baseline.keys(), "Audio baseline asset identities changed")
        report["repeat_audio_pcm_match"] = True
        report["repeat_audio_baseline_count"] = len(baseline)
    validate_registry(manifest)
    settings = unreal.get_default_object(unreal.GameMapsSettings)
    defaults = {}
    for key in ("editor_startup_map", "game_default_map"):
        value = settings.get_editor_property(key).export_text()
        require("/Game/Maps/M00_Bootstrap.M00_Bootstrap" in value, f"Default map changed: {key}")
        defaults[key] = value
    load("/Game/Maps/M00_Bootstrap", unreal.World)
    load("/Game/Maps/M02_ImportTrial", unreal.World)
    report["default_maps"] = defaults
    report["status"] = "PASS"


try:
    main()
except Exception as error:
    report["error"] = str(error)
    report["traceback"] = traceback.format_exc()
    raise
finally:
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

unreal.log("M03 VALIDATION PASSED: full media reload/roundtrip, numeric animations, exact registry and package references.")
