#!/usr/bin/env python3
"""Render real MTC GUI assets/fonts and fixture-resolved text; not a live HOI4 capture."""
import importlib.util
import json
from functools import lru_cache
from pathlib import Path
import subprocess

from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("archive_preview", ROOT / "tools/Preview-BarradArchive.py")
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


def main():
    fixtures = json.loads(subprocess.run(
        ["node", "tools/Test-BarradCollegiumMenu.cjs", "--fixtures"], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    assets = {lang: archive.Assets(lang) for lang in ("english", "russian")}
    for instance in assets.values():
        for nodes in archive.parse_files([ROOT / "mod/HoISubmod/interface/HSM_BAR_mtk.gfx"]):
            instance.ingest(nodes)
        instance.sprite = lru_cache(maxsize=96)(instance.sprite)
    output = ROOT / "art/previews"
    output.mkdir(parents=True, exist_ok=True)
    errors, reports = [], []
    previews = {}
    for scene in fixtures:
        a = assets[scene["language"]]
        canvas = Image.new("RGBA", (scene["width"], scene["height"]))
        scroll = []
        for w in scene["widgets"]:
            if w["kind"] == "buttonType":
                bitmap = a.sprite(w["sprite"], disabled=not w["enabled"])
                assert bitmap.size == (w["w"], w["h"]), w["name"]
                canvas.alpha_composite(bitmap, (w["x"], w["y"]))
            if not w.get("text"):
                continue
            is_button = w["kind"] == "buttonType"
            # Reserve the metal rim and optional department glyph, rather than letting labels touch it.
            inset = 8 if is_button else 0
            width = w["w"] - 2 * inset
            bitmap, full_height = archive.text_image(
                w["text"], a.font(w["font"]), a, width, w["h"], "center" if is_button else "left")
            if full_height > w["h"]:
                if w.get("scroll"):
                    scroll.append({"name": w["name"], "content_height": full_height, "viewport": w["h"]})
                else:
                    errors.append(f"{scene['language']}/{scene['project']}/{scene['document']}: {w['name']} {full_height}px > {w['h']}px")
            y = w["y"] + max(0, (w["h"] - full_height) // 2) if is_button else w["y"]
            canvas.alpha_composite(bitmap, (w["x"] + inset, y))
        reports.append({k: scene[k] for k in ("language", "project", "stage", "document")} | {"scrolling": scroll})
        opening = scene["project"] in ("field_atlas", "prosthetics", "necrotic_suture", "ritual_brake")
        opus = scene["project"] in ("chorus", "manufactory", "last_minute", "contact")
        joint = scene["project"] in ("sensate_prosthesis", "interrupt_notation")
        key = None
        if opus and scene["document"] == 4 or opening and scene["stage"] == "proposal" and scene["document"] == 1:
            key = f"{scene['department']}_{scene['stage']}"
        elif scene["document"] in (5, 7) and (opening or joint or scene["project"] == "revolver_howitzer"):
            key = f"{scene['project']}_{'laboratory' if scene['document'] == 5 else 'ledger'}_{scene['stage']}"
        elif scene["document"] == 3 and scene["project"] == "revolver_howitzer":
            key = f"{scene['project']}_report_{scene['stage']}"
        elif opus and scene["document"] == 6:
            key = f"{scene['project']}_origins_{scene['stage']}"
        elif joint and scene["document"] == 4 or scene["stage"] == "instrumented":
            key = f"{scene['project']}_{scene['stage']}"
        if key:
            previews[f"HSM_BAR_mtk_{key}_{scene['language']}"] = canvas
    if errors:
        raise ValueError("\n".join(sorted(set(errors))))
    for name, canvas in previews.items():
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Description", "Static source-based preview; not an HOI4 screenshot. Scroll position zero.")
        canvas.save(output / (name + ".png"), pnginfo=metadata)
    (output / "HSM_BAR_mtk_layout-report.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print(f"MTC preview: {len(fixtures)} bilingual states checked; {len(previews)} previews saved; no clipped non-scrolling text.")
    print(f"{sum(bool(r['scrolling']) for r in reports)} states use the native text scrollbar; in-game rendering remains unverified.")


if __name__ == "__main__":
    main()
