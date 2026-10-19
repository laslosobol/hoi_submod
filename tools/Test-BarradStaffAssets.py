"""Decode resolved native staff art and optionally render a contact sheet; no source edits."""
import argparse
import json
import struct
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument("--preview", action="store_true")
args = parser.parse_args()
sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
items = json.load(sys.stdin)
tiles = []
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 13)


def decode(file):
    try:
        with Image.open(file) as source:
            source.load()
            return source.convert("RGBA")
    except NotImplementedError:
        # EaW's original advisor DDS files include uncompressed DX10 BGRA8.
        # Pillow does not implement DXGI 87; decode that exact 2D layout only.
        data = Path(file).read_bytes()
        assert len(data) >= 148 and data[:4] == b"DDS " and data[84:88] == b"DX10", file
        size, flags, height, width, pitch = struct.unpack_from("<5I", data, 4)
        fmt, dimension, misc, array_size, _ = struct.unpack_from("<5I", data, 128)
        assert size == 124 and fmt == 87 and dimension == 3 and array_size == 1 and not misc & 4, file
        assert width > 0 and height > 0, file
        stride = pitch if flags & 8 else width * 4
        assert stride >= width * 4 and len(data) >= 148 + stride * height, file
        return Image.frombytes("RGBA", (width, height), data[148:148 + stride * height], "raw", "BGRA", stride)


for item in items:
    with decode(item["path"]) as source:
        source.load()
        assert source.width > 0 and source.height > 0, item
        image = source.convert("RGBA")
        assert image.getbbox(), item
        assert any(low != high for low, high in image.getextrema()[:3]), item
        tile = Image.new("RGB", (220, 160), (37, 42, 42))
        image.thumbnail((160, 96))
        tile.paste(image, ((220 - image.width) // 2, 5), image)
        draw = ImageDraw.Draw(tile)
        draw.text((8, 110), item["label"], font=font, fill="white")
        draw.text((8, 130), item["kind"], font=font, fill=(175, 192, 194))
        tiles.append(tile)
if args.preview:
    sheet = Image.new("RGB", (1100, ((len(tiles) + 4) // 5) * 160), (37, 42, 42))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % 5) * 220, (i // 5) * 160))
    output = Path(__file__).resolve().parent.parent / "art/previews/HSM_BAR_staff_native.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    print(output)
print(f"Decoded {len(items)} staff/company images; no missing, blank or undecodable textures.")
