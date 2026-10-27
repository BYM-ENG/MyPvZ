"""Copy the complete original media snapshot without replacing differing local files."""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from m03_assets import (BASE, ROOT, SOURCE, SEQUENCES, checked_manifest, decode_png,
                        image_size, media_files, sha256, wav_data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prototype", type=Path, default=ROOT.parent / "protptype")
    args = parser.parse_args()
    original = args.prototype.resolve(strict=True)
    files = media_files(original)
    assert len(files) == 150, "Unexpected prototype inventory; review before changing the frozen contract"
    # Preflight every existing copy before copying anything.
    for path in files:
        target = SOURCE / path.relative_to(original)
        if target.exists():
            assert sha256(target) == sha256(path), "Refusing to overwrite modified source: " + str(target)
    items, canonical = [], {}
    for path in files:
        relative = path.relative_to(original).as_posix()
        target = SOURCE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(path, target)
        kind = "image" if path.suffix.lower() in (".png", ".jpg") else "audio"
        digest = sha256(target)
        item = dict(source=relative, kind=kind, sha256=digest, bytes=target.stat().st_size)
        if (kind, digest) in canonical:
            first = canonical[kind, digest]
            item["canonical_source"] = first["source"]
            for key in (("texture", "sprite") if kind == "image" else ("sound",)):
                item[key] = first[key]
        else:
            item["canonical_source"] = relative
            parent = path.relative_to(original).parent.as_posix()
            if parent in SEQUENCES:
                stem = f"{SEQUENCES[parent][0]}_{int(path.stem):02d}"
            else:
                stem = re.sub(r"[^A-Za-z0-9_]", "_", str(Path(relative).with_suffix("")).replace("\\", "/"))
            if kind == "image":
                item.update(texture=f"{BASE}/Textures/T_{stem}", sprite=f"{BASE}/Sprites/S_{stem}")
            else:
                item["sound"] = f"{BASE}/Audio/SW_{stem}"
            canonical[kind, digest] = item
        if kind == "image":
            item["width"], item["height"] = image_size(target)
            if path.suffix.lower() == ".png":
                width, height, rgba = decode_png(target)
                alpha = rgba[3::4]
                item["alpha"] = dict(zero=alpha.count(0), full=alpha.count(255),
                                     partial=sum(0 < a < 255 for a in alpha))
        elif path.suffix.lower() == ".wav":
            channels, width, rate, count, pcm = wav_data(target)
            item["wav"] = dict(channels=channels, sample_width_bytes=width, sample_rate=rate, frames=count)
        items.append(item)
    by_source = {x["source"]: x for x in items}
    animations = []
    for directory, (identity, count) in SEQUENCES.items():
        numbers = sorted(int(p.stem) for p in (SOURCE / directory).glob("*.png"))
        assert numbers == list(range(1, count + 1)), directory
        animations.append(dict(id=identity, source_directory=directory, fps=8.0,
                               original_fps="unknown", placeholder=(identity == "WallnutCardPlaceholder"),
                               flipbook=f"{BASE}/Flipbooks/FB_{identity}",
                               frames=[dict(number=n, source=f"{directory}/{n}.png",
                                            sprite=by_source[f"{directory}/{n}.png"]["sprite"]) for n in numbers]))
    manifest = dict(schema_version=1, base=BASE, items=items, animations=animations,
                    notes=["All original media included, including potentially unused files.",
                           "Exact byte duplicates share canonical UE assets; every original path is retained.",
                           "Original FPS unknown; 8 fps is provisional import configuration.",
                           "Wallnut frames are duplicates of the card, not a field character; M11 owns replacement.",
                           "Original menu.MP3 case preserved; destination uses a stable case-independent identity."])
    encoded = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    manifest_file = SOURCE / "manifest.json"
    if manifest_file.exists():
        assert manifest_file.read_text(encoding="utf-8") == encoded, "Frozen manifest differs; review explicitly"
    else:
        manifest_file.write_text(encoded, encoding="utf-8", newline="\n")
    checked_manifest()
    print(f"PASS: {len(items)} source files; {len(canonical)} canonical media; {len(animations)} animations; original hashes match")


if __name__ == "__main__":
    main()
