#!/usr/bin/env python3
"""Render fielddesk fixture snapshots with existing native assets; not a game capture."""
import importlib.util
import json
from pathlib import Path
import subprocess

from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("archive_preview", ROOT / "tools/Preview-BarradArchive.py")
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


def main():
    result = subprocess.run(
        ["node", "tools/Test-BarradFielddesk.cjs", "--preview-json"], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", check=True)
    fixtures = json.loads(result.stdout)
    output = ROOT / "art/previews"
    output.mkdir(parents=True, exist_ok=True)
    report = []
    for fixture in fixtures:
        assets = archive.Assets(fixture["language"])
        canvas = assets.sprite("GFX_HSM_BAR_archive_folder").copy()
        assert canvas.size == (1000, 700)
        for item in fixture["items"]:
            x, y = item["x"], item["y"]
            if item["kind"] == "buttonType":
                sprite = assets.sprite(item["sprite"], disabled=item["disabled"])
                canvas.alpha_composite(sprite, (x, y))
                if item["text"]:
                    font = assets.font(item["font"])
                    image, height = archive.text_image(item["text"], font, assets, sprite.width - 16, sprite.height, "center")
                    assert height <= sprite.height, item["name"]
                    canvas.alpha_composite(image, (x + 8, y + (sprite.height - height) // 2))
            else:
                image, height = archive.text_image(item["text"], assets.font(item["font"]), assets, item["width"], item["height"])
                assert height <= item["height"], item["name"]
                canvas.alpha_composite(image, (x, y))
        name = f'HSM_BAR_fielddesk_{fixture["state"]}_{fixture["language"]}.png'
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Description", "Native-asset layout fixture, not an HOI4 screenshot.")
        canvas.save(output / name, pnginfo=metadata)
        report.append({"file": name, "size": canvas.size, "widgets": len(fixture["items"])})
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
