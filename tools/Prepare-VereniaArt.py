"""Lossless reference conversion and engine-format export, not art generation."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--size", nargs=2, type=int, metavar=("WIDTH", "HEIGHT"))
    parser.add_argument("--portrait", action="store_true")
    args = parser.parse_args()
    destination = args.destination.resolve()
    if not destination.is_relative_to(ROOT):
        parser.error("Output must stay within the project")
    if destination.exists():
        parser.error("Output exists; use a new versioned path")
    with Image.open(args.source) as original:
        result = original.convert("RGBA")
        if args.size:
            size = tuple(args.size)
            if min(size) < 1:
                parser.error("Dimensions must be positive")
            if args.portrait:
                result = ImageOps.fit(result, size, Image.Resampling.LANCZOS)
            else:
                fitted = ImageOps.contain(result, size, Image.Resampling.LANCZOS)
                result = Image.new("RGBA", size)
                result.alpha_composite(fitted, ((size[0]-fitted.width)//2, (size[1]-fitted.height)//2))
        destination.parent.mkdir(parents=True, exist_ok=True)
        result.save(destination)
        print(f"{destination}: {result.width}x{result.height}, {result.mode}")


if __name__ == "__main__":
    main()
