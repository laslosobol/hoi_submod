"""Prepare opt-in, hash-verified Verenian clones of eleven shared companies.

Default/--check are read-only; --apply writes a planned override, unique sprites,
and name aliases. No art is exported. --inventory prints an unapproved manifest.
Only original_tag ERI/EYR/AVI receives the clones; original eligibility remains
mandatory. Existing generic hires remain active until normally dismissed.
Dynamic available/visible guards prevent duplicate hiring; no save migration,
cancel, do_effect, removal-cost, or on_add/on_remove changes are introduced.
Runtime validation on a disposable existing save is still required.
The full native file is byte-pinned. Existing overrides must exactly match this
tool's previous output or the native file; foreign edits fail rather than merge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = runpy.run_path(str(ROOT / "tools/Bind-VereniaIcons.py"))
parse, spans, walk = API["parse"], API["spans"], API["walk"]
require, Files, read_json = API["require"], API["Files"], API["read_json"]
SOURCE = "EaW/common/ideas/zzz_generic.txt"
OUTPUT = "mod/HoISubmod/common/ideas/zzz_generic.txt"
MANIFEST = "art/verenia/company-bindings.json"
GFX = "mod/HoISubmod/interface/HSM_VER_company_art.gfx"
TAGS = ("ERI", "EYR", "AVI")
SCOPE = "OR = { original_tag = ERI original_tag = EYR original_tag = AVI }"
POLICY = "preserve-hired-v2"
RUNTIME_CHECKS = [
    "Load a disposable pre-binding save for ERI/EYR/AVI with an original generic hired; verify it remains selected with unchanged bonuses and removal cost.",
    "While the original is held, confirm the matching clone cannot be selected by player or AI; the original remains inspectable and dismissible under native rules.",
    "Dismiss the original normally; confirm only its eligible clone can be newly hired, with native price, conditions and bonuses and no replayed/refunded effects.",
    "Reload after dismissal and after clone hiring; test a dynamic-tag civil-war country retaining an ERI/EYR/AVI original_tag.",
    "Check a non-Verenian country and a native excluded/custom-designer country; eligibility must remain native. Existing corrupted saves with both IDs are not automatically repaired.",
]
CATEGORIES = {
    "generic_tank_manufacturer": "tank_manufacturer",
    "generic_naval_manufacturer": "naval_manufacturer",
    "generic_light_aircraft_manufacturer": "aircraft_manufacturer",
    "generic_medium_aircraft_manufacturer": "aircraft_manufacturer",
    "generic_heavy_aircraft_manufacturer": "aircraft_manufacturer",
    "generic_naval_aircraft_manufacturer": "aircraft_manufacturer",
    "generic_industrial_concern": "industrial_concern",
    "generic_electronics_concern": "industrial_concern",
    "generic_infantry_equipment_manufacturer": "materiel_manufacturer",
    "generic_artillery_manufacturer": "materiel_manufacturer",
    "generic_motorized_equipment_manufacturer": "materiel_manufacturer",
}


class CompanyFiles(Files):
    def __init__(self, root):
        super().__init__(root)
        self.idea_files = self.list_ideas()

    def list_ideas(self):
        return sorted(p.relative_to(self.root).as_posix()
                      for p in (self.root / "mod/HoISubmod/common/ideas").rglob("*.txt"))

    def verify(self):
        super().verify()
        require(self.idea_files == self.list_ideas(), "Idea files changed during planning")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def clone_id(target):
    return "HSM_VER_COMP_" + target


def definition(raw, target):
    text = raw.decode("utf-8")
    offset = int(text.startswith("\ufeff"))
    parse(text.lstrip("\ufeff"))
    matches = [node for selector, node in walk(spans(text.lstrip("\ufeff")))
               if tuple(k for k, _ in selector) == ("ideas", CATEGORIES[target], target)]
    require(len(matches) == 1, f"Expected one company definition: {target}")
    node = matches[0]
    for key in ("allowed", "picture"):
        require(len([n for n in node.children if n.key == key]) == 1, f"Missing/duplicate {key}: {target}")
    return node, offset


def guards(target, cloned):
    if cloned:
        return {"allowed": SCOPE,
                "available": f"NOT = {{ has_idea = {target} }}",
                "visible": f"NOT = {{ has_idea = {target} }}"}
    return {"available": "NOT = { " + SCOPE + " }",
            "visible": "OR = { NOT = { " + SCOPE + " } has_idea = " + target + " }"}


def add_guards(text, additions, newline):
    """Extend native trigger blocks by conjunction, preserving their exact text."""
    node = spans(text)[0]
    edits = []
    missing = []
    for key, guard in additions.items():
        matches = [n for n in node.children if n.key == key]
        require(len(matches) <= 1, f"Duplicate company {key} block")
        if matches:
            field = matches[0]
            require(text[field.end - 1] == "}", f"Expected trigger block: {key}")
            edits.append((field.end - 1, newline + "\t\t\t\t" + guard + newline + "\t\t\t"))
        else:
            missing.append("\t\t\t" + key + " = { " + guard + " }")
    if missing:
        edits.append((node.end - 1, newline + newline.join(missing) + newline + "\t\t"))
    for position, insertion in sorted(edits, reverse=True):
        text = text[:position] + insertion + text[position:]
    return text


def transformed(raw, selected):
    """Preserve hired originals; alter only selection guards, clone ID/picture."""
    text = raw.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    edits = []
    for target in sorted(selected):
        node, offset = definition(raw, target)
        start, end = node.start + offset, node.end + offset
        original = text[start:end]
        generic = add_guards(original, guards(target, False), newline)
        copy = add_guards(original, guards(target, True), newline)
        # Replace the clone's picture using the same parsed scalar span mechanism.
        clone_nodes = spans(copy)[0]
        picture = next(n for n in clone_nodes.children if n.key == "picture")
        tokens = [m for m in API["TOKEN"].finditer(copy, picture.start, picture.end)
                  if not m[0].isspace() and not m[0].startswith("#")]
        require(len(tokens) == 3 and tokens[1][0] == "=", "Expected scalar company picture")
        value = clone_id(target)
        if tokens[2][0].startswith('"'):
            value = '"' + value + '"'
        copy = copy[:tokens[2].start()] + value + copy[tokens[2].end():]
        copy = clone_id(target) + copy[len(target):]
        edits.append((start, end, generic + newline + "\t\t" + copy))
    changed = text
    for start, end, replacement in sorted(edits, reverse=True):
        changed = changed[:start] + replacement + changed[end:]
    verify_ast(raw, changed.encode("utf-8"), selected)
    return changed.encode("utf-8")


def verify_ast(before, after, selected):
    import copy

    old = parse(before.decode("utf-8-sig"))
    new = parse(after.decode("utf-8-sig"))
    for target in selected:
        def find(nodes, key):
            matches = [(parent, n) for _, parent in walk(nodes) if parent.key == CATEGORIES[target]
                       for n in parent.children if n.key == key]
            require(len(matches) == 1, f"Duplicate/missing company: {key}")
            return matches[0]
        _, original = find(old, target)
        _, generic = find(new, target)
        parent, cloned = find(new, clone_id(target))
        for definition_node, is_clone in ((generic, False), (cloned, True)):
            for key, expression in guards(target, is_clone).items():
                fields = definition_node.all(key)
                require(len(fields) == 1 and fields[0].children
                        and fields[0].children[-1] == parse(expression)[0],
                        f"Company selection guard changed: {target}/{key}")
                fields[0].children.pop()
                if not original.all(key):
                    require(not fields[0].children, f"Unexpected added {key} conditions: {target}")
                    definition_node.children.remove(fields[0])
        require(cloned.get("picture") == clone_id(target), f"Wrong scoped picture: {target}")
        cloned.key = target
        cloned.all("picture")[0].value = copy.deepcopy(original.get("picture"))
        require(cloned == original and generic == original,
                f"Company bonuses/conditions changed: {target}")
        parent.children[:] = [n for n in parent.children if n is not cloned]
    require(new == old, "Non-company content or category metadata changed")


def inventory():
    rows = json.loads((ROOT / "art/verenia/portrait-bindings.json").read_text())["records"]
    by_id = {r["id"]: r for r in rows}
    raw = (ROOT / SOURCE).read_bytes()
    records = []
    for target, category in CATEGORIES.items():
        old = by_id[target]
        node, _ = definition(raw, target)
        picture = next(n.value for n in node.children if n.key == "picture")
        records.append(dict(id=target, target=target, clone=clone_id(target), name=old["name"],
                            kind="manufacturer", category=category, file=SOURCE,
                            original_picture=picture, reference=old["bindings"][0]["reference"],
                            source=old["source"], approved=False, source_sha256=None,
                            exports=[dict(path=f"mod/HoISubmod/gfx/interface/ideas/HSM_VER_COMP/{target}.tga",
                                          width=64, height=64, sha256=None)],
                            review="Pending source and native-size QA", runtime_verified=False))
    return dict(schema_version=1, binding_policy=POLICY, source_file=SOURCE, source_file_sha256=sha(raw),
                countries=list(TAGS), strategy="Original allowed remains exact. Originals keep native available/visible conditions plus dynamic guards: no new Verenian hire, visible while held. Clones keep native conditions plus original_tag scope in allowed and NOT has_idea original in available/visible. No global sprite override.",
                no_clone_assessment="Existing pictures are static; country graphical cultures are shared with other countries. A new graphical culture would require auditing other culture-dependent art. No verified country-tag-only picture override is available in the inspected content.",
                save_compatibility="Preserve original hired idea and bonuses until normal dismissal. Its corresponding clone cannot be hired while the original is held. After dismissal only the eligible scoped clone is selectable. No automatic swap, repayment, removal or effect replay. No repair of saves already containing both IDs. Runtime existing-save UI/loading validation remains pending.",
                condition_semantics="allowed is load-time eligibility and stays unchanged on originals; do not put has_idea there. available/visible are dynamic selection gates, not cancellation or modifier gates. Native blocks are retained as conjunctions, including each original NOT exclusion. cancel, do_effect, allowed_to_remove, costs, category metadata, bonuses and effects remain exact.",
                runtime_validation={"verified": False, "pending_checks": RUNTIME_CHECKS},
                records=records)


def plan(files, manifest):
    data = read_json(files, manifest)
    require(data["schema_version"] == 1 and data.get("binding_policy") == POLICY and data["source_file"] == SOURCE
            and data["countries"] == list(TAGS), "Company scope mismatch")
    raw = files.read(SOURCE)
    require(raw is not None and sha(raw) == data["source_file_sha256"], "Native company file changed; re-audit required")
    rows = data["records"]
    require(len(rows) == len(CATEGORIES) and {r["id"] for r in rows} == set(CATEGORIES), "Expected eleven unique company records")
    selected, exports = set(), {}
    for row in rows:
        target = row["id"]
        require(row["target"] == target and row["clone"] == clone_id(target)
                and row["category"] == CATEGORIES[target] and row["file"] == SOURCE
                and row["kind"] == "manufacturer", f"Company identity mismatch: {target}")
        node, _ = definition(raw, target)
        require(next(n.value for n in node.children if n.key == "picture") == row["original_picture"], "Picture pin mismatch")
        if row.get("approved") is not True:
            continue
        require(len(row["exports"]) == 1, "Expected one company export")
        export = row["exports"][0]
        expected = f"mod/HoISubmod/gfx/interface/ideas/HSM_VER_COMP/{target}.tga"
        require(export["path"] == expected and (export["width"], export["height"]) == (64, 64), "Company export path/size mismatch")
        API["relative"](row["source"], "art/verenia")
        for path, digest in ((row["source"], row["source_sha256"]), (expected, export["sha256"])):
            asset = files.read(path)
            require(asset is not None and sha(asset) == digest, f"Missing/unreviewed company asset: {path}")
        API["native_tga"](files.read(expected), (64, 64))
        selected.add(target)
        exports[target] = expected.removeprefix("mod/HoISubmod/")
    previous = files.read(OUTPUT)
    previous_selected = set()
    if previous is not None:
        keys = [n.key for _, n in walk(parse(previous.decode("utf-8-sig")))]
        previous_selected = {t for t in CATEGORIES if clone_id(t) in keys}
        require(previous == transformed(raw, previous_selected), "Existing generic override has foreign edits; refusing to replace it")
        require(previous_selected <= selected, "Previously bound companies cannot be unapproved/removed")
    if not selected:
        return {}, 0
    outputs = {OUTPUT: transformed(raw, selected)}
    clones = {clone_id(t) for t in selected}
    for file in files.idea_files:
        if file != OUTPUT:
            require(not any(n.key in clones for _, n in walk(parse(files.read(file).decode("utf-8-sig")))),
                    f"Company clone already defined in {file}")
    def gfx_text(targets):
        return ("# Generated by Bind-VereniaCompanies.py\nspriteTypes = {\n" + "".join(
            f'\tspriteType = {{ name = GFX_idea_{clone_id(t)} textureFile = "{exports[t]}" }}\n'
            for t in sorted(targets)) + "}\n").encode()
    outputs[GFX] = gfx_text(selected)
    owned_names = {"GFX_idea_" + clone_id(t) for t in selected}
    for file in files.interfaces:
        if file != GFX:
            for _, node in walk(parse(files.read(file).decode("utf-8-sig"))):
                require(not (node.key.lower() == "spritetype" and node.get("name") in owned_names), f"Company sprite collision: {file}")
    old_gfx = files.read(GFX)
    require(old_gfx is None or old_gfx == gfx_text(previous_selected), "Existing company sprites changed")
    for lang in ("english", "russian"):
        path = f"mod/HoISubmod/localisation/{lang}/HSM_VER_companies_l_{lang}.yml"
        def localisation(targets):
            return ("\ufeffl_" + lang + ":\n" + "".join(
                f' {clone_id(t)}:0 "${t}$"\n' for t in sorted(targets))).encode("utf-8")
        old = files.read(path)
        require(old is None or old == localisation(previous_selected), f"Existing company localisation changed: {path}")
        outputs[path] = localisation(selected)
    return {p: b for p, b in outputs.items() if files.read(p) != b}, len(selected)


def self_test():
    import copy
    import unittest

    class Memory:
        def __init__(self, data):
            self.data = data
            self.interfaces = [p for p in data if p.endswith(".gfx")]
            self.idea_files = [p for p in data if p.startswith("mod/HoISubmod/common/ideas/") and p.endswith(".txt")]

        def read(self, name):
            return self.data.get(name)

    class Tests(unittest.TestCase):
        def test_existing_hire_selection_semantics(self):
            raw = (ROOT / SOURCE).read_bytes()
            original_nodes = parse(raw.decode("utf-8-sig"))
            changed_nodes = parse(transformed(raw, set(CATEGORIES)).decode("utf-8-sig"))
            def idea(nodes, key):
                return next(n for _, n in walk(nodes) if n.key == key and n.all("allowed"))

            def evaluate(nodes, original_tag, held, custom=False, flags=frozenset()):
                def condition(node):
                    if node.key == "OR":
                        return any(condition(n) for n in node.children)
                    if node.key == "NOT":
                        return not any(condition(n) for n in node.children)
                    if node.key == "AND":
                        return all(condition(n) for n in node.children)
                    if node.key == "original_tag":
                        return original_tag == node.value
                    if node.key == "has_idea":
                        return node.value in held
                    if node.key == "country_with_custom_designers":
                        return custom == (node.value == "yes")
                    if node.key == "has_country_flag":
                        return node.value in flags
                    raise AssertionError(f"Unmodelled trigger: {node.key}")
                return all(condition(n) for n in nodes)

            for target in CATEGORIES:
                native = idea(original_nodes, target)
                generic = idea(changed_nodes, target)
                cloned = idea(changed_nodes, clone_id(target))
                self.assertEqual(generic.all("allowed"), native.all("allowed"))
                self.assertFalse(any(n.key == "has_idea" for _, n in walk(cloned.get("allowed"))))
                exclusions = {n.value for _, n in walk(native.get("allowed")) if n.key == "original_tag"}
                for tag in sorted(set(TAGS) | exclusions | {"GRI", "JER", "D01"}):
                    for custom in (False, True):
                        eligible = not custom and tag not in exclusions
                        self.assertEqual(evaluate(native.get("allowed"), tag, set(), custom), eligible)
                        for held in (set(), {target}, {clone_id(target)}, {target, clone_id(target)}):
                            with self.subTest(company=target, original_tag=tag, custom=custom, held=held):
                                def gate(node, key):
                                    return evaluate(node.get(key, []), tag, held, custom)
                                self.assertEqual(gate(generic, "allowed"), eligible)
                                self.assertEqual(gate(cloned, "allowed"), eligible and tag in TAGS)
                                self.assertEqual(gate(generic, "available"), tag not in TAGS)
                                self.assertEqual(gate(generic, "visible"), tag not in TAGS or target in held)
                                self.assertEqual(gate(cloned, "available"), target not in held)
                                self.assertEqual(gate(cloned, "visible"), target not in held)
                                can_hire = [all(gate(n, k) for k in ("allowed", "visible", "available"))
                                            for n in (generic, cloned)]
                                self.assertLessEqual(sum(can_hire), 1)
                                if tag in TAGS and target in held:
                                    self.assertEqual(can_hire, [False, False])
                                elif eligible:
                                    self.assertEqual(sum(can_hire), 1)
                # Non-selection fields are byte-independent AST equivalents.
                for key in ("cancel", "do_effect", "allowed_to_remove", "on_add", "on_remove",
                            "cost", "removal_cost", "research_bonus", "traits"):
                    self.assertEqual(generic.all(key), native.all(key))
                    self.assertEqual(cloned.all(key), native.all(key))

        def test_native_available_visible_conditions_are_not_bypassed(self):
            raw = (ROOT / SOURCE).read_bytes()
            # Test existing AND conditions, including an empty block, rather than
            # assuming these eleven definitions will always omit both fields.
            target = "generic_tank_manufacturer"
            for extra in (b' available = { has_country_flag = ready } visible = { has_country_flag = shown }',
                          b' available = {} visible = {}'):
                fixture = raw.replace(b"picture = generic_tank_manufacturer_1",
                                      b"picture = generic_tank_manufacturer_1" + extra, 1)
                changed = transformed(fixture, {target})
                verify_ast(fixture, changed, {target})
                for _, node in walk(parse(changed.decode("utf-8-sig"))):
                    if node.key in (target, clone_id(target)):
                        for key, flag in (("available", "ready"), ("visible", "shown")):
                            fields = node.all(key)
                            self.assertEqual(len(fields), 1)
                            children = fields[0].children
                            if b"has_country_flag" in extra:
                                self.assertEqual(children[0], parse("has_country_flag = " + flag)[0])
                                self.assertEqual(len(children), 2)
                            else:
                                self.assertEqual(len(children), 1)
            for extra in (b' available = yes', b' available = {} available = {}'):
                fixture = raw.replace(b"picture = generic_tank_manufacturer_1",
                                      b"picture = generic_tank_manufacturer_1" + extra, 1)
                with self.assertRaises(ValueError):
                    transformed(fixture, {target})

        def test_all_native_companies_and_partition(self):
            raw = (ROOT / SOURCE).read_bytes()
            changed = transformed(raw, set(CATEGORIES))
            verify_ast(raw, changed, set(CATEGORIES))
            self.assertEqual(transformed(raw, set()), raw)
            for old, new in ((b"armor = 0.15", b"armor = 0.16"),
                             (b"country_with_custom_designers = yes", b"country_with_custom_designers = no"),
                             (b"designer = yes", b"designer = no"),
                             (b"original_tag = ERI", b"original_tag = GRI")):
                with self.subTest(change=old), self.assertRaises(ValueError):
                    verify_ast(raw, changed.replace(old, new), set(CATEGORIES))

        def test_pipeline_and_incremental_approval(self):
            manifest = inventory()
            data = {MANIFEST: json.dumps(manifest).encode(), SOURCE: (ROOT / SOURCE).read_bytes()}
            self.assertEqual(plan(Memory(data), MANIFEST), ({}, 0))
            native = data[SOURCE]
            for index in (0, 1):
                row = manifest["records"][index]
                tga = bytearray(18 + 64 * 64 * 4)
                tga[2], tga[12], tga[14], tga[16], tga[17] = 2, 64, 64, 32, 8
                data[row["source"]] = b"reviewed source"
                data[row["exports"][0]["path"]] = bytes(tga)
                row["approved"] = True
                row["source_sha256"] = sha(data[row["source"]])
                row["exports"][0]["sha256"] = sha(bytes(tga))
                data[MANIFEST] = json.dumps(manifest).encode()
                outputs, count = plan(Memory(data), MANIFEST)
                self.assertEqual(count, index + 1)
                self.assertNotIn(SOURCE, outputs)
                self.assertTrue(set(outputs) <= {OUTPUT, GFX,
                    "mod/HoISubmod/localisation/english/HSM_VER_companies_l_english.yml",
                    "mod/HoISubmod/localisation/russian/HSM_VER_companies_l_russian.yml"})
                data.update(outputs)
                self.assertEqual(plan(Memory(data), MANIFEST)[0], {})
                self.assertEqual(data[SOURCE], native)
            for name in (SOURCE, OUTPUT, manifest["records"][0]["source"], manifest["records"][0]["exports"][0]["path"], GFX):
                bad = copy.deepcopy(data)
                bad[name] += b"unexpected"
                with self.subTest(path=name), self.assertRaises(ValueError):
                    plan(Memory(bad), MANIFEST)
            for file, value in (("mod/HoISubmod/common/ideas/collision.txt",
                                  b"ideas={ tank_manufacturer={ HSM_VER_COMP_generic_tank_manufacturer={} } }"),
                                 ("mod/HoISubmod/interface/collision.gfx",
                                  b"spriteTypes={ spriteType={ name=GFX_idea_HSM_VER_COMP_generic_tank_manufacturer } }")):
                bad = copy.deepcopy(data)
                bad[file] = value
                with self.subTest(collision=file), self.assertRaises(ValueError):
                    plan(Memory(bad), MANIFEST)
            for field_name, wrong in (("source", "../outside.png"), ("category", "country"),
                                      ("clone", "generic_tank_manufacturer"), ("file", "EaW/common/ideas/other.txt")):
                bad = copy.deepcopy(data)
                bad_manifest = copy.deepcopy(manifest)
                bad_manifest["records"][0][field_name] = wrong
                bad[MANIFEST] = json.dumps(bad_manifest).encode()
                with self.subTest(field=field_name), self.assertRaises(ValueError):
                    plan(Memory(bad), MANIFEST)
            outdated = copy.deepcopy(data)
            old_manifest = copy.deepcopy(manifest)
            old_manifest.pop("binding_policy")
            outdated[MANIFEST] = json.dumps(old_manifest).encode()
            with self.assertRaises(ValueError):
                plan(Memory(outdated), MANIFEST)
            manifest["records"][0]["approved"] = False
            data[MANIFEST] = json.dumps(manifest).encode()
            with self.assertRaises(ValueError):
                plan(Memory(data), MANIFEST)

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    require(result.wasSuccessful(), "Company self-tests failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=MANIFEST)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--inventory", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.inventory:
        print(json.dumps(inventory(), indent=2))
        return
    API["relative"](args.manifest, "art/verenia")
    files = CompanyFiles(ROOT)
    outputs, count = plan(files, args.manifest)
    if args.apply:
        API["apply"](files, outputs)
    for path in sorted(outputs):
        print(path)
    print(f"{count}/11 approved companies; {len(outputs)} {'updated' if args.apply else 'pending'} files")
    if args.check and outputs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
