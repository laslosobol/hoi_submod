"""Package reviewed atlas artwork in EaW's native country-selection template.

Atlas artwork: Deer (lunar_explorator); selector layout: Scars and Egil / EaW.
Selection highlights were edited with image generation, not drawn by this tool.
The retained PNG sources are authoritative; this exporter only sizes and packs.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "art/source"
OUT = ROOT / "mod/HoISubmod/gfx/interface/country_selection_screen"
PREVIEW = ROOT / "outputs/country-selection"
DEFAULT_EAW = Path("C:/shit/Steam/steamapps/workshop/content/394360/1826643372")
TAGS = ("CYA", "ERI", "EYR", "AVI")
MAP_BOX = (104, 21, 464, 322)
TEMPLATE = "gfx/interface/country_selection_screen/country_map/template.png"
# Viewports use the 860x710 atlas-reference coordinate system.
VIEWS = {
    "CYA": (0, 0, 860, 710),
    "ERI": (160, 180, 620, 565),
    "EYR": (400, 130, 840, 498),
    "AVI": (125, 55, 605, 457),
}


def render_maps(eaw):
    with Image.open(eaw / TEMPLATE) as source:
        frame = source.convert("RGBA")
    if frame.size != (485, 344):
        raise ValueError("EaW changed its map template; reconcile the inline slot before exporting.")
    x0, y0, x1, y1 = MAP_BOX
    result = {}
    for tag in TAGS:
        with Image.open(SOURCE / f"HSM_CSS_{tag}_atlas.png") as source:
            vx0, vy0, vx1, vy1 = VIEWS[tag]
            crop = (round(vx0 * source.width / 860), round(vy0 * source.height / 710),
                    round(vx1 * source.width / 860), round(vy1 * source.height / 710))
            tile = source.convert("RGBA").crop(crop).resize((x1 - x0, y1 - y0), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", frame.size)
        canvas.paste(tile, (x0, y0))
        result[tag] = Image.alpha_composite(canvas, frame)
    return result


def render_icon():
    with Image.open(SOURCE / "HSM_country_selection_icon.png") as source:
        icon = source.convert("RGBA")
    bounds = icon.getchannel("A").getbbox()
    if not bounds:
        raise ValueError("The generated tab icon is empty.")
    icon = ImageOps.contain(icon.crop(bounds), (72, 64), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (78, 70))
    canvas.paste(icon, ((78 - icon.width) // 2, (70 - icon.height) // 2))
    return canvas


def export(eaw):
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    maps = render_maps(eaw)
    for tag, image in maps.items():
        image.save(OUT / f"HSM_{tag}.tga")
        image.save(PREVIEW / f"{tag}.png")
        print(f"{tag}: 485x344; native EaW atlas and frame, retained selection artwork")
    icon = render_icon()
    icon.save(OUT / "HSM_stories_icon.tga")
    icon.save(PREVIEW / "HSM_stories_icon.png")
    # An asset contact sheet at native size, not a simulated in-game screenshot.
    sheet = Image.new("RGBA", (970, 758), (28, 29, 27, 255))
    for index, image in enumerate(maps.values()):
        sheet.alpha_composite(image, ((index % 2) * 485, (index // 2) * 344))
    sheet.alpha_composite(icon, (446, 688))
    sheet.save(PREVIEW / "atlas-contact-sheet.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eaw", type=Path, default=DEFAULT_EAW)
    export(parser.parse_args().eaw)
