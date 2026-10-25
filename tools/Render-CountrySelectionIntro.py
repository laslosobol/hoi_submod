"""Package the generated illustration in EaW's native inline-tooltip dimensions."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "art/source/HSM_country_selection_intro.png"
TARGET = ROOT / "mod/HoISubmod/gfx/interface/country_selection_screen/HSM_stories_intro.tga"
PREVIEW = ROOT / "outputs/country-selection/HSM_stories_intro.png"


def render():
    with Image.open(SOURCE) as source:
        illustration = source.convert("RGBA").resize((310, 175), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (325, 207))
    canvas.paste(illustration, (0, 16))
    return canvas


if __name__ == "__main__":
    image = render()
    for target in (TARGET, PREVIEW):
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target)
    print("Illustrated tooltip: 325x207; generated source retained in art/source.")
