"""Prepare scoped portrait bindings; default is read-only, --apply is explicit.

The manifest owns approval: approved=true plus source_sha256 and export.sha256
must match existing assets. This tool never exports art or defines shared sprites.
--inventory prints a fresh, unapproved reference register to stdout.
--self-test exercises byte preservation and AST guards without writing files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod/HoISubmod"
API = runpy.run_path(str(ROOT / "tools/Build-VereniaSpirit.py"))
spans, parse, TOKEN = API["spans"], API["API"]["parse"], API["API"]["TOKEN"]
CHARACTERS = {f"common/characters/{tag}.txt" for tag in ("ERI", "EYR", "AVI")}
GROVER = {"common/scripted_effects/HSM_VER_grover.txt",
          "common/scripted_effects/HSM_VER_regency.txt"}
MANIFEST = ROOT / "art/verenia/portrait-bindings.json"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(base, relative):
    path = (base / relative).resolve()
    require(not Path(relative).is_absolute() and path.is_relative_to(base.resolve()),
            f"Path escapes {base}: {relative}")
    return path


def visit(nodes, prefix=()):
    counts = {}
    for node in nodes:
        index = counts.get(node.key, 0)
        counts[node.key] = index + 1
        path = prefix + ((node.key, index),)
        yield path, node
        yield from visit(node.children, path)


def select(nodes, selector):
    for key, index in selector:
        matches = [node for node in nodes if node.key == key]
        require(isinstance(index, int) and 0 <= index < len(matches),
                f"Missing selector: {selector}")
        node = matches[index]
        nodes = node.children
    return node


def ast_signature(text, ignored):
    def block(nodes, prefix=()):
        counts, result = {}, []
        for node in nodes:
            index = counts.get(node.key, 0)
            counts[node.key] = index + 1
            path = prefix + ((node.key, index),)
            value = (block(node.value, path) if isinstance(node.value, list)
                     else "<approved portrait>" if path in ignored else node.value)
            result.append((node.key, node.op, value))
        return result
    return block(parse(text.lstrip("\ufeff")))


def replace_values(raw, bindings):
    text = raw.decode("utf-8")
    nodes = spans(text.lstrip("\ufeff"))
    offset = int(text.startswith("\ufeff"))
    edits, ignored = [], set()
    for binding, value in bindings:
        selector = tuple(tuple(p) for p in binding["selector"])
        require(selector not in ignored, f"Duplicate binding: {selector}")
        ignored.add(selector)
        node = select(nodes, selector)
        require(not node.children and node.value in (binding["original"], value),
                f"Changed original portrait: {selector}: {node.value}")
        tokens = [m for m in TOKEN.finditer(text, node.start + offset, node.end + offset)
                  if not m[0].isspace() and not m[0].startswith("#")]
        require(len(tokens) == 3 and tokens[1][0] == "=", "Not a scalar assignment")
        token = tokens[-1]
        replacement = '"' + value + '"' if token[0].startswith('"') else value
        edits.append((token.start(), token.end(), replacement))
    result = text
    for start, end, value in sorted(edits, reverse=True):
        result = result[:start] + value + result[end:]
    require(ast_signature(text, ignored) == ast_signature(result, ignored),
            "Gameplay AST changed")
    return result.encode("utf-8")


def inventory(eaw, game):
    loc, sprites = {}, {}
    for base in (game, eaw):
        for path in sorted((base / "localisation/english").rglob("*.yml")):
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                match = re.match(r'\s*([^\s#:]+):\d*\s*"(.*)"', line)
                if match:
                    loc[match[1]] = match[2]
        for path in sorted((base / "interface").rglob("*.gfx")):
            text = path.read_text(encoding="utf-8-sig")
            # Some upstream GUI files use syntax outside the script parser.
            if "spriteType" not in text:
                continue
            for match in re.finditer(r'\bspriteType\s*=\s*\{([^{}]*)\}', text, re.I):
                fields = {n.key.lower(): n.value for n in parse(match[1])}
                if "name" in fields and "texturefile" in fields:
                    sprites[fields["name"]] = (fields["texturefile"], path.relative_to(base).as_posix())

    def reference(value):
        texture, definition = sprites.get(value, (value if value.startswith("gfx/") else None, None))
        owner = next((label for label, base in (("EaW", eaw), ("game", game))
                      if texture and (base / texture).is_file()), None)
        return {"alias": value if value.startswith("GFX_") else None,
                "path": texture, "root": owner, "sprite_definition": definition}

    done = {r["target"]: r for r in json.loads((ROOT / "art/verenia/batch-01.json").read_text())}
    records = []
    for file in sorted(CHARACTERS):
        text = (eaw / file).read_text(encoding="utf-8-sig")
        for character in spans(text)[0].children:
            flat = list(visit(character.children))
            name_key = next(n.value for _, n in flat if n.key == "name")
            institution = "chamberofcommerce" in character.key or "tripartite" in character.key
            advisor = any(n.key == "advisor" for _, n in flat)
            record = {"id": character.key, "name": loc.get(name_key, name_key),
                      "name_key": name_key,
                      "kind": "institution" if institution else "advisor" if advisor else "leader_or_commander",
                      "source": f"art/verenia/{character.key}.png", "approved": False,
                      "source_sha256": None, "bindable": character.key not in done,
                      "status": "batch01_native_override" if character.key in done else "pending",
                      "bindings": []}
            record["reference_note"] = ("Shared generic appearance reference, not a unique canonical character design."
                                         if advisor and not institution else
                                         "Institution emblem, not an individual portrait." if institution else
                                         "Use the original appearance reference; unknown silhouettes do not establish identity.")
            if character.key in done:
                record["source"] = done[character.key]["source"]
            for selector, node in flat:
                if node.key not in ("large", "small") or not any(k == "portraits" for k, _ in selector):
                    continue
                role = selector[-2][0]
                width, height = (156, 210) if node.key == "large" else (65, 67)
                export = f"mod/HoISubmod/gfx/portraits/HSM_VER/{character.key}_{role}_{node.key}.tga"
                if character.key in done:
                    export = "mod/HoISubmod/" + node.value
                record["bindings"].append({"file": file,
                    "selector": [("characters", 0), (character.key, 0)] + list(selector),
                    "original": node.value, "reference": reference(node.value),
                    "export": {"path": export, "width": width, "height": height, "sha256": None}})
            records.append(record)
    categories = {"tank_manufacturer", "naval_manufacturer", "aircraft_manufacturer",
                  "industrial_concern", "materiel_manufacturer"}
    for file in ("common/ideas/zzz_AVI_ideas.txt", "common/ideas/zzz_generic.txt"):
        for selector, node in visit(spans((eaw / file).read_text(encoding="utf-8-sig"))):
            if node.key != "picture" or len(selector) != 4 or selector[1][0] not in categories:
                continue
            key = selector[-2][0]
            records.append({"id": key, "name": loc.get(key, key), "kind": "manufacturer",
                "source": done[key]["source"] if key in done else f"art/verenia/{key}.png",
                "approved": False, "source_sha256": None, "bindable": False,
                "status": "batch01_native_override" if key in done else "blocked_shared_definition",
                "note": "Shared manufacturers need a separately reviewed country-scoped design; never override their sprites or definitions globally." if key not in done else "Native unique texture already integrated.",
                "bindings": [{"file": file, "selector": list(selector), "original": node.value,
                    "reference": reference("GFX_idea_" + node.value),
                    "export": {"path": done[key]["exports"][0]["path"] if key in done else f"mod/HoISubmod/gfx/portraits/HSM_VER/{key}.tga",
                               "width": 64, "height": 64, "sha256": None}}]})
    grover = {"id": "GRI_emperor_grover_vi_verenia_story", "name": "Grover VI (Verenian story)",
              "kind": "story_portrait", "source": "art/verenia/grover-story.png",
              "approved": False, "source_sha256": None, "bindable": True,
              "status": "pending", "bindings": []}
    for file in sorted(GROVER):
        for selector, node in visit(spans((MOD / file).read_text(encoding="utf-8-sig"))):
            if node.key == "set_portraits" and any(n.key == "character" and n.value == "GRI_emperor_grover_vi" for n in node.children):
                for sub, leaf in visit(node.children):
                    if sub == (("civilian", 0), ("large", 0)):
                        grover["bindings"].append({"file": file, "selector": list(selector + sub),
                            "original": leaf.value, "reference": reference(leaf.value),
                            "export": {"path": "mod/HoISubmod/gfx/portraits/HSM_VER/grover_story.tga",
                                       "width": 156, "height": 210, "sha256": None}})
    records.append(grover)
    return {"schema_version": 1, "approval_policy": "Explicit approved=true and matching SHA256 for source and each existing native-size TGA. Pending/missing assets are skipped. No exports or sprite overrides are created.",
            "reference_roots": {"EaW": "EaW", "game": str(game)},
            "records": records}


def validate_scope(record, binding, text):
    file, selector = binding["file"], tuple(tuple(p) for p in binding["selector"])
    keys = tuple(k for k, _ in selector)
    if file in CHARACTERS:
        require(len(keys) in (5, 6) and keys[:2] == ("characters", record["id"])
                and keys[-3] == "portraits" and keys[-2] in ("army", "civilian", "navy")
                and keys[-1] in ("large", "small")
                and (len(keys) == 5 or keys[2] == "instance"), "Non-portrait character selector")
        require(record["id"].startswith(Path(file).stem + "_"), "Wrong country character")
    else:
        require(file in GROVER and record["id"] == "GRI_emperor_grover_vi_verenia_story"
                and keys[-3:] == ("set_portraits", "civilian", "large"), "Out-of-scope script binding")
        parent = select(spans(text.lstrip("\ufeff")), selector[:-2])
        require(any(n.key == "character" and n.value == "GRI_emperor_grover_vi" for n in parent.children),
                "Grover selector targets another character")


def plan(manifest, eaw, mod=MOD):
    require(manifest["schema_version"] == 1, "Unknown manifest schema")
    pending, originals, skipped = {}, {}, []
    for record in manifest["records"]:
        if record.get("approved") is not True:
            skipped.append(record["id"])
            continue
        require(record.get("bindable") is True, f"Blocked record approved: {record['id']}")
        source = inside(ROOT, record["source"])
        exports = [inside(ROOT, b["export"]["path"]) for b in record["bindings"]]
        if not source.is_file():
            skipped.append(record["id"])
            continue
        require(digest(source) == record["source_sha256"], f"Unreviewed source: {source}")
        for binding, asset in zip(record["bindings"], exports):
            if not asset.is_file():
                skipped.append(record["id"] + ":" + binding["export"]["path"])
                continue
            require(asset.is_relative_to((MOD / "gfx/portraits/HSM_VER").resolve()), "Export is not a unique scoped texture")
            require(digest(asset) == binding["export"]["sha256"], f"Unreviewed export: {asset}")
            data = asset.read_bytes()
            size = (binding["export"]["width"], binding["export"]["height"])
            expected = (156, 210) if binding["selector"][-1][0] == "large" else (65, 67)
            require(size == expected and len(data) >= 18 and data[1:3] == bytes((0, 2))
                    and int.from_bytes(data[12:14], "little") == size[0]
                    and int.from_bytes(data[14:16], "little") == size[1] and data[16] == 32
                    and len(data) >= 18 + data[0] + size[0] * size[1] * 4,
                    f"Expected native-size uncompressed RGBA TGA: {asset}")
            file = binding["file"]
            target = inside(mod, file)
            require(file in CHARACTERS | GROVER, f"Out-of-scope file: {file}")
            if target not in originals:
                baseline = target if target.exists() else inside(eaw, file)
                require(file not in GROVER or target.exists(), "Story script override must already exist")
                originals[target] = baseline.read_bytes()
            validate_scope(record, binding, originals[target].decode("utf-8"))
            value = asset.relative_to(MOD.resolve()).as_posix()
            pending.setdefault(target, []).append((binding, value))
    outputs = {path: replace_values(originals[path], edits) for path, edits in pending.items()}
    return {p: raw for p, raw in outputs.items() if raw != originals[p]}, originals, skipped


def self_test(eaw):
    raw = b'\xef\xbb\xbfcharacters={\r\n X={ portraits={ civilian={ small = "GFX_old" # keep\r\n } } cost=100 }\r\n}\r\n'
    selector = [["characters", 0], ["X", 0], ["portraits", 0], ["civilian", 0], ["small", 0]]
    binding = {"selector": selector, "original": "GFX_old"}
    result = replace_values(raw, [(binding, "gfx/portraits/HSM_VER/x.tga")])
    require(result == raw.replace(b'GFX_old', b'gfx/portraits/HSM_VER/x.tga'), "Byte preservation failed")
    require(replace_values(result, [(binding, "gfx/portraits/HSM_VER/x.tga")]) == result, "Not idempotent")
    ignored = {tuple(tuple(p) for p in selector)}
    require(ast_signature(raw.decode(), ignored) != ast_signature(raw.decode().replace("cost=100", "cost=101"), ignored), "Gameplay guard failed")
    for bad in (raw.replace(b'GFX_old', b'GFX_other'), raw[:-4]):
        try:
            replace_values(bad, [(binding, "new")])
        except (ValueError, AssertionError):
            pass
        else:
            raise ValueError("Invalid input accepted")
    import copy
    from unittest.mock import patch

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    count = 0
    for record in manifest["records"]:
        for binding in record["bindings"]:
            file = binding["file"]
            path = MOD / file if (MOD / file).exists() else eaw / file
            original = path.read_bytes()
            node = select(spans(original.decode("utf-8-sig")), binding["selector"])
            require(node.value == binding["original"], f"Stale inventory: {record['id']}")
            if record["bindable"]:
                validate_scope(record, binding, original.decode("utf-8"))
                value = "gfx/portraits/HSM_VER/test.tga"
                changed = replace_values(original, [(binding, value)])
                require(replace_values(changed, [(binding, value)]) == changed, "Selector not idempotent")
            count += 1

    # Exercise the approval path entirely in memory; no fixture/game files written.
    record = copy.deepcopy(next(r for r in manifest["records"] if r["id"] == "AVI_aaron_redtail"))
    record["approved"] = True
    record["source_sha256"] = "reviewed"
    record["bindings"][0]["export"]["sha256"] = "reviewed"
    asset = inside(ROOT, record["bindings"][0]["export"]["path"])
    source = inside(ROOT, record["source"])
    tga = bytearray(18 + 156 * 210 * 4)
    tga[2], tga[16] = 2, 32
    tga[12:14], tga[14:16] = (156).to_bytes(2, "little"), (210).to_bytes(2, "little")
    real_read, real_file = Path.read_bytes, Path.is_file
    def fake_read(path):
        return bytes(tga) if path == asset else real_read(path)
    def fake_file(path):
        return True if path in (asset, source) else real_file(path)
    with patch.object(Path, "read_bytes", fake_read), patch.object(Path, "is_file", fake_file), \
            patch.dict(plan.__globals__, digest=lambda path: "reviewed"):
        fixture = {"schema_version": 1, "records": [record]}
        outputs, originals, skipped = plan(fixture, eaw)
        require(len(outputs) == 1 and not skipped, "Approved asset was not planned")
        for path, changed in outputs.items():
            binding = record["bindings"][0]
            require(changed == originals[path].replace(binding["original"].encode(),
                    asset.relative_to(MOD.resolve()).as_posix().encode()), "Unexpected file changes")
        record["source_sha256"] = "wrong"
        try:
            plan(fixture, eaw)
        except ValueError:
            pass
        else:
            raise ValueError("Unreviewed source accepted")
        record["source_sha256"] = "reviewed"
        record["bindings"][0]["export"]["sha256"] = "wrong"
        try:
            plan(fixture, eaw)
        except ValueError:
            pass
        else:
            raise ValueError("Unreviewed export accepted")
        record["bindings"][0]["export"]["sha256"] = "reviewed"
        with patch.object(Path, "is_file", lambda path: False if path == asset else fake_file(path)):
            require(not plan(fixture, eaw)[0], "Missing export was not skipped")
        for bad_file in ("common/characters/GRI.txt", "../outside.txt"):
            bad = copy.deepcopy(record["bindings"][0])
            bad["file"] = bad_file
            try:
                validate_scope(record, bad, "")
            except ValueError:
                pass
            else:
                raise ValueError("Out-of-scope binding accepted")
    print(f"Self-test passed: {count} reference selectors, byte preservation, AST guard, approval hashes, drift rejection, idempotence")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eaw", type=Path, default=ROOT / "EaW")
    parser.add_argument("--game", type=Path, default=API["API"]["OPT"].game)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--inventory", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.eaw)
        return
    if args.inventory:
        print(json.dumps(inventory(args.eaw, args.game), indent=2, ensure_ascii=True))
        return
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    outputs, originals, skipped = plan(manifest, args.eaw)
    # Preflight all files before the first write, including concurrent edits.
    for path in outputs:
        require(not path.exists() or path.read_bytes() == originals[path], f"Concurrent edit: {path}")
    for path, raw in outputs.items():
        print(path.relative_to(ROOT).as_posix())
        if args.apply:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    print(f"{len(outputs)} {'updated' if args.apply else 'planned'} files; {len(skipped)} unapproved/missing records skipped")
    if args.check and outputs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
