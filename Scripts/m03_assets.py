"""Frozen M03 inventory contract; usable by stock Python 3.11 and Unreal Python."""
import hashlib
import json
import struct
import wave
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "SourceAssets" / "M03"
BASE = "/Game/PvZ"
MATERIAL = "/Paper2D/TranslucentUnlitSpriteMaterial.TranslucentUnlitSpriteMaterial"
EXTENSIONS = {".png", ".jpg", ".wav", ".mp3"}
SEQUENCES = {
    "res/zhiwu/0": ("Peashooter", 13),
    "res/zhiwu/1": ("Sunflower", 18),
    "res/zhiwu/2": ("WallnutCardPlaceholder", 9),
    "res/zm": ("ZombieWalk", 22),
    "res/zm_eat": ("ZombieEat", 21),
    "res/zm_stand": ("ZombieStand", 11),
    "res/sunshine": ("Sun", 29),
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def media_files(root):
    return sorted((p for d in ("res", "resx") for p in (root / d).rglob("*")
                   if p.is_file() and p.suffix.lower() in EXTENSIONS),
                  key=lambda p: p.relative_to(root).as_posix())


def decode_png(path):
    """Decode the inventory's noninterlaced RGB/RGBA8 PNGs with all PNG filters."""
    data = Path(path).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", str(path)
    offset, compressed = 8, bytearray()
    while offset < len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        kind, chunk = data[offset + 4:offset + 8], data[offset + 8:offset + 8 + size]
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunk)
            assert depth == 8 and color in (2, 6) and (compression, filtering, interlace) == (0, 0, 0), str(path)
            channels = 4 if color == 6 else 3
        elif kind == b"IDAT":
            compressed.extend(chunk)
        offset += size + 12
    raw = zlib.decompress(compressed)
    stride = width * channels
    result, previous, offset = bytearray(), bytearray(stride), 0
    assert len(raw) == height * (stride + 1), str(path)
    for _ in range(height):
        filter_type = raw[offset]
        row = bytearray(raw[offset + 1:offset + 1 + stride])
        assert filter_type in range(5), str(path)
        for i in range(stride):
            left = row[i - channels] if i >= channels else 0
            up, upper_left = previous[i], previous[i - channels] if i >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            else:
                p = left + up - upper_left
                distances = [abs(p - left), abs(p - up), abs(p - upper_left)]
                predictor = (left, up, upper_left)[distances.index(min(distances))]
            row[i] = (row[i] + predictor) & 255
        if channels == 4:
            result.extend(row)
        else:
            for i in range(0, len(row), 3):
                result.extend(row[i:i + 3])
                result.append(255)
        previous, offset = row, offset + stride + 1
    return width, height, bytes(result)


def image_size(path):
    if path.suffix.lower() == ".png":
        data = path.read_bytes()
        return struct.unpack_from(">II", data, 16)
    data, offset = path.read_bytes(), 2
    assert data[:2] == b"\xff\xd8", str(path)
    while offset < len(data):
        assert data[offset] == 255, str(path)
        while data[offset] == 255:
            offset += 1
        marker, offset = data[offset], offset + 1
        length = struct.unpack_from(">H", data, offset)[0]
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack_from(">HH", data, offset + 3)
            return width, height
        offset += length
    raise AssertionError("JPEG dimensions missing: " + str(path))


def wav_data(path):
    with wave.open(str(path), "rb") as wav:
        return (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(),
                wav.getnframes(), wav.readframes(wav.getnframes()))


def checked_manifest():
    manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1 and manifest["base"] == BASE
    actual = {p.relative_to(SOURCE).as_posix() for p in media_files(SOURCE)}
    assert actual == {x["source"] for x in manifest["items"]}, "Source inventory changed"
    assert len(actual) == len(manifest["items"]) == 150
    by_source = {x["source"]: x for x in manifest["items"]}
    for item in manifest["items"]:
        path = SOURCE / item["source"]
        assert sha256(path) == item["sha256"] and path.stat().st_size == item["bytes"], str(path)
        canonical = by_source[item["canonical_source"]]
        assert canonical["sha256"] == item["sha256"] and canonical["kind"] == item["kind"]
        for key in (("texture", "sprite") if item["kind"] == "image" else ("sound",)):
            assert item[key] == canonical[key] and item[key].startswith(BASE + "/")
    assert len(manifest["animations"]) == len(SEQUENCES)
    for group in manifest["animations"]:
        identity, count = SEQUENCES[group["source_directory"]]
        assert group["id"] == identity and group["fps"] == 8.0
        assert [f["number"] for f in group["frames"]] == list(range(1, count + 1))
        for frame in group["frames"]:
            assert frame["source"] == f'{group["source_directory"]}/{frame["number"]}.png'
            assert frame["sprite"] == by_source[frame["source"]]["sprite"]
    return manifest
