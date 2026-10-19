"""Native-size contact sheets of shipped TGA exports, not engine screenshots."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "tools/data/barrad-content-icons.json").read_text())
OUTPUT = ROOT / "art/previews"
FONT = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 12)


def sheet(kind, motifs, width, height):
    columns, cell_w, cell_h = 6, 190, height + 40
    rows = (len(motifs) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell_w, rows * cell_h * 2))
    draw = ImageDraw.Draw(canvas)
    for section, (background, foreground) in enumerate((("#22272a", "#ffffff"), ("#dddeda", "#171b1d"))):
        base_y = section * rows * cell_h
        draw.rectangle((0, base_y, canvas.width, base_y + rows * cell_h), fill=background)
        for i, motif in enumerate(motifs):
            image = Image.open(ROOT / f"mod/HoISubmod/gfx/interface/{kind}/HSM_BAR_{motif}.tga").convert("RGBA")
            assert image.size == (width, height), motif
            x, y = (i % columns) * cell_w, base_y + (i // columns) * cell_h
            canvas.paste(image, (x + (cell_w - width) // 2, y + 4), image)
            label = motif.removeprefix("art_")
            draw.text((x + 6, y + height + 12), label, fill=foreground, font=FONT)
    OUTPUT.mkdir(exist_ok=True)
    canvas.save(OUTPUT / f"HSM_BAR_content_{kind}_native.png")
    print(f"{kind}: {len(motifs)} exports at {width}x{height}, dark/light sheet saved")


if __name__ == "__main__":
    all_motifs = set(DATA["ideas"].values()) | set(DATA["modifiers"].values())
    for group in DATA["focuses"].values():
        all_motifs.update(group.values())
    sheet("goals", sorted(m for m in all_motifs if m.startswith("art_")), 99, 86)
    sheet("ideas", sorted(set(DATA["ideas"].values()) | set(DATA["modifiers"].values())), 64, 64)
