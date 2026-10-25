"""Export reviewed imagegen sources and verify their native-size game assets."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "art/verenia/batch-01.json"
BASELINE = ROOT / "art/verenia/batch-01-hashes.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    assert manifest.is_relative_to(ROOT / "art/verenia")
    baseline = manifest.with_name(manifest.stem + "-hashes.json")
    records = json.loads(manifest.read_text(encoding="utf-8"))
    hashes = {}
    sheet = Image.new("RGB", (800, 320*((len(records)+3)//4)), "#303030")
    draw = ImageDraw.Draw(sheet)
    count = 0
    for index, record in enumerate(records):
        source = ROOT / record["source"]
        hashes[record["source"]] = digest(source)
        with Image.open(source) as opened:
            original = opened.convert("RGBA")
            if not record["portrait"]:
                assert original.getchannel("A").getextrema() == (0, 255), source
            for item in record["exports"]:
                path = (ROOT / item["path"]).resolve()
                assert path.is_relative_to(ROOT / "mod/HoISubmod/gfx")
                size = (item["width"], item["height"])
                if record["portrait"]:
                    result = ImageOps.fit(original, size, Image.Resampling.LANCZOS)
                else:
                    fitted = ImageOps.contain(original, size, Image.Resampling.LANCZOS)
                    result = Image.new("RGBA", size)
                    result.alpha_composite(fitted, ((size[0]-fitted.width)//2, (size[1]-fitted.height)//2))
                if args.check:
                    with Image.open(path) as exported:
                        assert exported.size == size, path
                        assert exported.convert("RGBA").tobytes() == result.tobytes(), path
                    assert path.read_bytes()[2] == 2, f"Expected uncompressed TGA: {path}"
                else:
                    if path.exists():
                        with Image.open(path) as previous:
                            if previous.convert("RGBA").tobytes() != result.tobytes():
                                raise RuntimeError(f"Refusing to overwrite changed asset: {path}")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    result.save(path, compression=None)
                hashes[item["path"]] = digest(path)
                count += 1
            first = ROOT / record["exports"][0]["path"]
            x, y = (index % 4)*200, (index // 4)*320
            draw.text((x+8, y+8), record["id"], fill="white")
            with Image.open(first) as preview:
                sheet.paste(preview, (x+12, y+28), preview.getchannel("A"))
            if len(record["exports"]) > 1:
                with Image.open(ROOT / record["exports"][1]["path"]) as small:
                    sheet.paste(small, (x+12, y+240), small.getchannel("A"))
    if args.check:
        assert hashes == json.loads(baseline.read_text()), "Art changed since recorded export"
    else:
        sheet.save(manifest.with_name(manifest.stem + "-native-preview.png"))
        baseline.write_text(json.dumps(hashes, indent=2)+"\n", encoding="utf-8")
    print(f"{len(records)} sources, {count} exports: {'verified' if args.check else 'exported'}")


if __name__ == "__main__":
    main()
