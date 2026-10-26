"""Small M02-only source verification helpers; no third-party Python packages."""
import hashlib
import json
import struct
import wave
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "SourceAssets" / "M02"
BASE = "/Game/M02"
MAP = "/Game/Maps/M02_ImportTrial"
MATERIAL = "/Paper2D/TranslucentUnlitSpriteMaterial.TranslucentUnlitSpriteMaterial"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rgba_png(path):
    """Decode the sample/exported noninterlaced RGBA8 PNGs, including all PNG filters."""
    data = Path(path).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    offset, compressed = 8, bytearray()
    while offset < len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        kind, chunk = data[offset + 4:offset + 8], data[offset + 8:offset + 8 + size]
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunk)
            assert (depth, color, compression, filtering, interlace) == (8, 6, 0, 0, 0)
        elif kind == b"IDAT":
            compressed.extend(chunk)
        offset += size + 12
    raw = zlib.decompress(compressed)
    stride, result, previous, offset = width * 4, bytearray(), bytearray(width * 4), 0
    for _ in range(height):
        filter_type = raw[offset]
        row = bytearray(raw[offset + 1:offset + 1 + stride])
        for i in range(stride):
            left, up, upper_left = (row[i - 4] if i >= 4 else 0), previous[i], (previous[i - 4] if i >= 4 else 0)
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                p = left + up - upper_left
                distances = [abs(p - left), abs(p - up), abs(p - upper_left)]
                predictor = (left, up, upper_left)[distances.index(min(distances))]
            else:
                raise AssertionError("Unexpected PNG filter")
            row[i] = (row[i] + predictor) & 255
        result.extend(row)
        previous, offset = row, offset + stride + 1
    return width, height, bytes(result)


def wav_data(path):
    with wave.open(str(path), "rb") as wav:
        return (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(),
                wav.getnframes(), wav.readframes(wav.getnframes()))


def checked_manifest():
    manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    assert [x["frame"] for x in manifest["frames"]] == list(range(1, 12))
    for item in manifest["frames"] + [manifest["audio"]]:
        assert sha256(SOURCE / item["copy"]) == item["sha256"], item["copy"]
    return manifest
