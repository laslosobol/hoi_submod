"""Rebuild the two narrow EaW selector overrides; no extra scenario or GUI logic."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod/HoISubmod"
SOURCE = Path(__file__).with_name("country-selection")
DEFAULT_EAW = Path("C:/shit/Steam/steamapps/workshop/content/394360/1826643372")
BOOKMARK = "common/bookmarks/z_scenario_main.txt"
GUI = "interface/frontendgamesetupview.gui"
TAGS = ("CYA", "ERI", "EYR", "AVI")


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Upstream changed; inspect the selector before rebuilding: {old!r}")
    return text.replace(old, new, 1)


def expected_files(eaw):
    bookmark = (eaw / BOOKMARK).read_text(encoding="utf-8-sig")
    gui = (eaw / GUI).read_text(encoding="utf-8-sig")
    for tag in TAGS:
        if f'"{tag}"' in bookmark:
            raise ValueError(f"EaW now features {tag}; reconcile its card instead of duplicating it.")
    bookmark = replace_once(
        bookmark,
        "label_order = { CSS_EquestriaFilter CSS_GriffoniaFilter CSS_ZebricaFilter }",
        "label_order = { CSS_EquestriaFilter CSS_GriffoniaFilter CSS_ZebricaFilter HSM_CSS_Filter }",
    )
    bookmark = replace_once(bookmark, "\t\teffect = {", SOURCE.joinpath("entries.txt").read_text(encoding="utf-8") + "\t\teffect = {")
    gui = replace_once(gui, '\t\tcontainerWindowType = {\n\t\t\tname ="countries_medium"', SOURCE.joinpath("tooltip.gui").read_text(encoding="utf-8") + '\t\tcontainerWindowType = {\n\t\t\tname ="countries_medium"')
    return {BOOKMARK: bookmark, GUI: gui}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eaw", type=Path, default=DEFAULT_EAW)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for relative, text in expected_files(args.eaw).items():
        target = MOD / relative
        if not target.exists() or target.read_text(encoding="utf-8-sig") != text:
            stale.append(relative)
            if not args.check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8", newline="\n")
        print(f"Upstream {relative}: {hashlib.sha256((args.eaw / relative).read_bytes()).hexdigest()}")
    print(f"Selector: four featured countries; {len(stale)} {'stale' if args.check else 'updated'} files.")
    if args.check and stale:
        raise SystemExit("Stale overrides: " + ", ".join(stale))


if __name__ == "__main__":
    main()
