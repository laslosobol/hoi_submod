#!/usr/bin/env python3
"""Render source-driven native-bitmap fixtures, not live HOI4 screenshots.

Defaults to ignored dist/barrad-investigations-20261010/previews: 56 PNGs and the
full JSON report. Also exports six rock EN/RU evidence/expedition/returned-2
PNGs to art/previews for user links. Requires authored JSON and generated native
GUI/localization. Does not invoke or edit the builder, or delete existing files.
The report also checks all four compact register labels in EN/RU against the
native Service GUI row font and 490x20 bounds; it does not render that whole GUI.

Options: --output-dir dist/<run>/previews changes the exhaustive output folder;
--all-images saves all 224 fixture states; --no-representatives skips the six
art/previews exports. Output directories are resolved relative to the repo and
must remain under its dist directory. All output names use HSM_BAR_investigation_.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

from PIL import Image, PngImagePlugin

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("archive_preview", Path(__file__).with_name("Preview-BarradArchive.py"))
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
P = "HSM_BAR_investigation_"
OUT = A.REPO / "dist/barrad-investigations-20261010/previews"
REPRESENTATIVES = A.REPO / "art/previews"
REPRESENTATIVE_STATES = (("evidence", 1), ("expedition", 1), ("returned", 2))
TEXTURE_ALIASES = {}
_resolve = A.resolve


def resolve_native(relative):
    try:
        return _resolve(relative)
    except ValueError:
        # Installed core.gfx names checkbox_small.tga; the shipped bitmap is DDS.
        # Keep this native basename alias explicit in the report, not a fake sprite.
        A.require(Path(relative).suffix.lower() == ".tga", "Missing native asset: " + relative)
        alternate = str(Path(relative).with_suffix(".dds"))
        resolved = _resolve(alternate)
        TEXTURE_ALIASES[relative] = str(resolved)
        return resolved


A.resolve = resolve_native


def dimensions(body, default=(1000, 700)):
    size = A.prop(body, "size", [])
    return tuple(int(A.prop(size, name, A.prop(size, alternate, fallback)))
                 for name, alternate, fallback in zip(("width", "height"), ("x", "y"), default))


def position(body):
    pos = A.prop(body, "position", [])
    return int(A.prop(pos, "x", 0)), int(A.prop(pos, "y", 0))


def locale(language):
    result = {}
    for file in sorted((A.MOD / "localisation" / language).glob("HSM_BAR*.yml")):
        for key, value in re.findall(r'^\s*(\w+):\d*\s+"(.*)"\s*$', A.read(file), re.M):
            result[key] = value.replace(r"\n", "\n").replace(r'\"', '"').replace("\\\\", "\\")
    return result


def compare(a, op, b):
    A.require(op in ("=", ">", "<", ">=", "<="), "Unknown comparison: " + op)
    return {"=": a == b, ">": a > b, "<": a < b, ">=": a >= b, "<=": a <= b}[op]


class Fixture:
    """Explicit UI state; territorial access is a declared fixture fact."""
    def __init__(self, case, state, method, texts, helpers, script, loc):
        self.case, self.state, self.method = case, state, method
        self.name = f"{case['id']}_{state}_{method}"
        self.texts, self.helpers, self.script, self.loc = texts, helpers, script, loc
        self.selected, self.used_frames = {}, {}
        self.flags = {"HSM_BAR_" + k for k in (
            "active", "directorate", "service_founded", "field_research_open", "region_local_open")}
        self.flags.add("HSM_BAR_case_" + case["id"] + "_known")
        self.missions = set()
        self.pp = 100 if state != "unfunded" else 0
        page = 1 if state in ("evidence", "mismatch", "unmatched") else 3 if state in ("returned", "empty", "historical") else 2
        self.vars = {P + "open": 1, P + "case": case["subject"], P + "page": page,
                     P + "method": method, P + "report": method, P + "a": case["pair"][0], P + "b": case["pair"][1]}
        for side, selected in (("a", case["pair"][0]), ("b", case["pair"][1]), ("method", method)):
            for number in (1, 2, 3):
                self.vars[P + "frame_" + side + str(number)] = 2 if selected == number else 1
        key = P + case["id"]
        if state not in ("unmatched", "mismatch"):
            self.flags.add(key + "_matched")
        if state == "mismatch":
            self.vars[P + "feedback"] = 2
            self.vars[P + "b"] = case["pair"][1] % 3 + 1
            for number in (1, 2, 3):
                self.vars[P + "frame_b" + str(number)] = 2 if number == self.vars[P + "b"] else 1
        if state == "unmatched":
            self.vars[P + "a"] = self.vars[P + "b"] = 0
            for side in ("a", "b"):
                for number in (1, 2, 3):
                    self.vars[P + "frame_" + side + str(number)] = 1
        if state == "running":
            self.flags.update((key + "_running", key + f"_{method}_running"))
            self.missions.add(key + f"_{method}_mission")
        if state == "returned":
            self.flags.add(key + f"_{method}_reported")
        if state == "historical" or state == "returned" and case["methods"][method - 1]["qualifies"]:
            self.flags.add("HSM_BAR_case_" + case["id"] + "_investigated")
        if state == "cancelled":
            self.flags.add(key + "_cancelled")

    def condition(self, nodes, stack=()):
        def test(n):
            key, value, op = n["key"], n["value"], n["op"]
            if key in ("AND", "hidden_trigger"):
                return self.condition(value, stack)
            if key == "OR":
                return any(test(child) for child in value)
            if key == "NOT":
                return not any(test(child) for child in value)
            if key == "check_variable":
                A.require(len(value) == 1, "Unsupported variable comparison")
                return compare(self.vars.get(value[0]["key"], 0), value[0]["op"], float(value[0]["value"]))
            if key == "has_political_power":
                return compare(self.pp, op, float(value))
            if key == "has_country_flag":
                A.require(isinstance(value, str), "Timed flag is not a UI fixture predicate")
                return value in self.flags
            if key == "has_active_mission":
                return value in self.missions
            if key == "has_variable":
                return value in self.vars
            if key in ("tag", "original_tag"):
                return value == "BAR"
            if key in ("is_ai", "has_capitulated", "is_subject"):
                return value == "no"
            if key == "controls_state":
                return value == "624"
            if key == "always":
                return value == "yes"
            if key in self.helpers:
                A.require(key not in stack, "Recursive fixture predicate: " + key)
                return self.condition(self.helpers[key], stack + (key,)) == (value == "yes")
            raise ValueError("Unknown investigation UI predicate: " + key)
        return all(test(n) for n in nodes)

    def getter(self, name):
        name = name.removeprefix("ROOT.")
        A.require(name in self.texts, "Missing scripted localization: " + name)
        for entry in self.texts[name]:
            if self.condition(A.prop(entry, "trigger", [])):
                result = A.prop(entry, "localization_key")
                self.selected[name] = result
                return result
        raise ValueError("No localization selection for " + name)

    def expand(self, value, depth=0):
        A.require(depth < 24, "Recursive localization: " + value)
        if value.startswith("GFX_"):
            return value
        if value in self.loc:
            return self.expand(self.loc[value], depth + 1)
        value = re.sub(r"\[([\w.]+)\]", lambda m: self.expand(self.getter(m[1]), depth + 1), value)
        value = re.sub(r"\$(\w+)\$", lambda m: self.expand(m[1], depth + 1), value)
        value = re.sub(r"\[\?days_mission_timeout@\w+\|0\]", "14", value)
        A.require(not re.search(r"\bHSM_BAR_\w+\b|\[Get|\[\?|\$\w+\$", re.sub(r"£[^£]+£", "", value)), "Unresolved text: " + value)
        return value

    def gate(self, name, suffix):
        return self.condition(A.prop(A.prop(self.script, "triggers", []), name + suffix, []))


class Renderer:
    def __init__(self, assets, fixture, language):
        self.assets, self.fixture, self.language = assets, fixture, language
        self.checks, self.issues, self.scrolls, self.geometry = [], [], [], []

    def issue(self, kind, name, **details):
        self.issues.append({"kind": kind, "widget": name, **details})

    def text(self, body, text, width, height, align="left", scroll=None):
        name = A.prop(body, "name")
        font_name = A.prop(body, "font", A.prop(body, "buttonFont"))
        image, used = A.text_image(text, self.assets.font(font_name), self.assets, width, height, align)
        self.checks.append({"widget": name, "text": text, "font": font_name,
                            "width": width, "height": height, "used_height": used, "scrolling": scroll is not None})
        if used > height:
            self.issue("text_clipped", name, text=text, used_height=used, available_height=height, width=width)
        if scroll and used > scroll[1]:
            self.scrolls.append({"widget": name, "content_height": used, "viewport_height": scroll[1], "viewport_width": scroll[0]})
        return image, used

    def bounds(self, name, rect, kind, parent, scroll):
        if scroll:
            return
        self.geometry.append({"name": name, "rect": rect, "kind": kind})
        x, y, w, h = rect
        if x < 0 or y < 0 or x + w > 1000 or y + h > 700:
            self.issue("outside_window", name, rect=rect, parent=parent)

    def container(self, body, absolute=(0, 0), in_scroll=None):
        size = dimensions(body)
        canvas = Image.new("RGBA", size)
        for node in body:
            kind, child = node["key"], node["value"]
            if not isinstance(child, list):
                continue
            name = A.prop(child, "name", "")
            if not self.fixture.gate(name, "_visible"):
                continue
            x, y = position(child)
            ax, ay = absolute[0] + x, absolute[1] + y
            if kind == "containerWindowType":
                scroll = dimensions(child) if A.prop(child, "verticalScrollbar") else in_scroll
                if A.prop(child, "verticalScrollbar"):
                    A.require(A.prop(child, "clipping") == "yes", "Scrollable text must have a clipping viewport")
                    self.bounds(name, (ax, ay, *dimensions(child)), "scroll", A.prop(body, "name"), in_scroll)
                image = self.container(child, (ax, ay), scroll)
            elif kind == "instantTextboxType":
                width, height = int(A.prop(child, "maxWidth")), int(A.prop(child, "maxHeight"))
                text = self.fixture.expand(A.prop(child, "text"))
                image, used = self.text(child, text, width, height, A.prop(child, "format", "left"), in_scroll)
                self.bounds(name, (ax, ay, width, min(height, used)), "text", A.prop(body, "name"), in_scroll)
            elif kind in ("background", "buttonType", "iconType"):
                if name.endswith(("input_floor", "input_shield")):
                    continue
                properties = A.prop(A.prop(self.fixture.script, "properties", []), name, [])
                sprite = self.fixture.expand(A.prop(properties, "image", A.prop(child, "quadTextureSprite", A.prop(child, "spriteType", ""))))
                frame = A.prop(properties, "frame", A.prop(child, "frame", "1"))
                frame = int(frame) if str(frame).isdigit() else int(self.fixture.vars[frame])
                enabled = self.fixture.gate(name, "_click_enabled")
                image = self.assets.sprite(sprite, frame=frame, disabled=not enabled).copy()
                if A.prop(properties, "frame"):
                    self.fixture.used_frames[name] = {"frame": frame, "enabled": enabled, "sprite": sprite}
                explicit = A.prop(child, "size")
                if explicit:
                    A.require(dimensions(child) == image.size, "Unexpected widget scaling: " + name)
                if kind != "background":
                    self.bounds(name, (ax, ay, *image.size), "button", A.prop(body, "name"), in_scroll)
                label = A.prop(child, "buttonText")
                if label:
                    # Full physical bounds plus a separate conservative paper-control inset.
                    text = self.fixture.expand(label)
                    layer, used = self.text(child, text, image.width, image.height, "center")
                    _, inset_height = A.text_image(text, self.assets.font(A.prop(child, "buttonFont")), self.assets,
                                                   image.width - 14, image.height, "center")
                    if inset_height > image.height - 6:
                        self.issue("button_padding", name, text=text, width=image.width - 14,
                                   used_height=inset_height, available_height=image.height - 6)
                    image.alpha_composite(layer, (0, max(0, (image.height - used) // 2)))
            else:
                continue
            canvas.alpha_composite(image, (x, y))
        return canvas

    def overlaps(self):
        for i, a in enumerate(self.geometry):
            x, y, w, h = a["rect"]
            for b in self.geometry[i + 1:]:
                bx, by, bw, bh = b["rect"]
                overlap = (min(x + w, bx + bw) - max(x, bx), min(y + h, by + bh) - max(y, by))
                if min(overlap) > 0:
                    self.issue("overlap", a["name"], other=b["name"], overlap=list(overlap), rect=a["rect"], other_rect=b["rect"])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all-images", action="store_true", help="Save all fixture states, not only the 42 principal pages and selected edge cases")
    parser.add_argument("--output-dir", type=Path, default=OUT, help="Full PNG/report destination, restricted to repo/dist")
    parser.add_argument("--no-representatives", action="store_true", help="Do not export the six representative rock PNGs to art/previews")
    args = parser.parse_args()
    repo = A.REPO.resolve()
    dist = (repo / "dist").resolve()
    output = (repo / args.output_dir).resolve()
    representatives = REPRESENTATIVES.resolve()
    A.require(dist.is_relative_to(repo), "dist resolves outside the workspace")
    A.require(output.is_relative_to(dist), "Preview output must remain under workspace dist")
    A.require(representatives.is_relative_to(repo), "Representative preview folder resolves outside the workspace")
    for source in (Path(__file__).resolve(), Path(A.__file__).resolve(), repo / "tools/Test-BarradCases.cjs"):
        A.read(source)
    data_file = A.REPO / "tools/data/barrad-investigations.json"
    paths = [A.MOD / "interface/HSM_BAR_investigation.gui", A.MOD / "common/scripted_guis/HSM_BAR_investigation.txt",
             A.MOD / "common/scripted_localisation/HSM_BAR_investigation.txt"]
    paths += [A.MOD / "common/scripted_triggers" / file for file in (
        "HSM_BAR_investigation.txt", "HSM_BAR_service_gui.txt", "HSM_BAR_anomalies.txt", "HSM_BAR_cases.txt")]
    for file in [data_file, *paths]:
        A.require(file.is_file(), "Waiting for authored/generated source: " + str(file))
    cases = json.loads(A.read(data_file))
    A.require(len(cases) == 7, "Expected all seven authored cases")
    gui, scripts, text_nodes, *helper_nodes = A.parse_files(paths)
    register_gui, = A.parse_files([A.MOD / "interface/HSM_BAR_service_gui.gui"])
    register_rows = [n["value"] for n in A.walk(register_gui) if n["key"] == "instantTextboxType"
                     and A.prop(n["value"], "name") == "HSM_BAR_service_gui_action_state"]
    A.require(len(register_rows) == 1, "Expected one native Service register status template")
    register_row = register_rows[0]
    register_width, register_height = (int(A.prop(register_row, key)) for key in ("maxWidth", "maxHeight"))
    A.require((register_width, register_height) == (490, 20), "Native register status dimensions changed")
    window = next(n["value"] for n in A.prop(gui, "guiTypes") if A.prop(n["value"], "name") == P + "window")
    A.require(dimensions(window) == (1000, 700), "Native folder size changed")
    script = A.prop(A.prop(scripts, "scripted_gui"), P + "window")
    texts = {A.prop(n["value"], "name"): [entry["value"] for entry in n["value"] if entry["key"] == "text"]
             for n in text_nodes if n["key"] == "defined_text"}
    helpers = {n["key"]: n["value"] for nodes in helper_nodes for n in nodes}
    report = {"kind": "static-native-bitmap-fixtures", "live_game": False,
              "limitations": ["Idle/disabled sprites only; no engine hover/input/save-load verification.",
                              "Scroll position zero; text is clipped by actual container viewports.",
                              "Native automatic scrollbar tracks/thumb geometry is not simulated; reserved scrollbar gutters remain clear.",
                              "Territorial/political eligibility is explicit fixture state, not a world simulation."],
              "fixtures": [], "register_row_checks": [], "sources": {}, "issues": []}
    output.mkdir(parents=True, exist_ok=True)
    if not args.no_representatives:
        representatives.mkdir(parents=True, exist_ok=True)
    for language in ("english", "russian"):
        assets, loc = A.Assets(language), locale(language)
        row_renderer = Renderer(assets, None, language)
        for state in ("pending", "ready", "accepted", "limited"):
            key = P + "row_" + state
            A.require(key in loc, "Missing compact register localization: " + key + "/" + language)
            image, used = row_renderer.text(register_row, loc[key], register_width, register_height,
                                            A.prop(register_row, "format", "left"))
            report["register_row_checks"].append({"key": key, "language": language, **row_renderer.checks[-1],
                                                   "ink_bounds": image.getchannel("A").getbbox(),
                                                   "fits": used <= register_height})
        report["issues"].extend({"fixture": "register_row", "language": language, **issue}
                                for issue in row_renderer.issues)
        for c in cases:
            states = [("evidence", 1), ("unmatched", 1), ("mismatch", 1), ("empty", 1), ("historical", 1),
                      ("unfunded", 1), ("cancelled", 1)]
            states += [(state, number) for state in ("expedition", "running", "returned") for number in (1, 2, 3)]
            for state, number in states:
                f = Fixture(c, state, number, texts, helpers, script, loc)
                A.require(f.condition(A.prop(script, "visible")), "Fixture cannot open window: " + f.name)
                renderer = Renderer(assets, f, language)
                canvas = renderer.container(window)
                renderer.overlaps()
                primary = (state, number) in (("evidence", 1), ("expedition", 1), ("returned", 1))
                save = args.all_images or primary or c["id"] == "rock" and (state, number) in (("unmatched", 1), ("mismatch", 1), ("running", 2), ("returned", 2), ("returned", 3), ("unfunded", 1), ("historical", 1))
                file = output / f"{P}{c['id']}_{state}_{number}_{language}.png"
                representative = not args.no_representatives and c["id"] == "rock" and (state, number) in REPRESENTATIVE_STATES
                meta = {"case": c["id"], "state": state, "method": number, "language": language,
                        "vars": f.vars, "flags": sorted(f.flags), "getters": f.selected, "frames": f.used_frames,
                        "checks": renderer.checks, "scrolls": renderer.scrolls, "issues": renderer.issues}
                if save:
                    png = PngImagePlugin.PngInfo()
                    png.add_text("Description", "Source-driven native bitmap fixture; not an HOI4 capture. Scroll offset zero; automatic scrollbars omitted.")
                    png.add_text("Fixture", json.dumps(meta, ensure_ascii=False))
                    canvas.save(file, pnginfo=png)
                    if representative:
                        canvas.save(representatives / file.name, pnginfo=png)
                report["fixtures"].append({**meta, "image": str(file) if save else None,
                                           "representative_image": str(representatives / file.name) if representative else None})
                report["issues"].extend({"fixture": f.name, "language": language, **issue} for issue in renderer.issues)
            print(f"Checked {language}/{c['id']}: {len(states)} exact-text native-font states")
    report["sources"] = A.SOURCES
    changed_sources = [path for path, digest in A.SOURCES.items()
                       if not Path(path).is_file() or hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest]
    report["source_checks"] = {"hashed_sources": len(A.SOURCES), "unchanged_during_render": not changed_sources,
                               "changed_sources": changed_sources,
                               "contracts": ["Seven authored cases; native 1000x700 folder geometry",
                                             "Parsed GUI positions, sprite selectors and numeric checkbox frames",
                                             "Scripted localization resolved against explicit EN/RU fixture states",
                                             "Physical texture/font atlas existence, native glyphs and frame bounds",
                                             "Four compact register labels in each language against the native 490x20 row/font",
                                             "Fixed text bounds, button padding and sibling overlap checks"]}
    report["issues"].extend({"kind": "source_changed_during_render", "widget": path, "language": "source"}
                            for path in changed_sources)
    title_widgets = {P + name for name in ("title", "hypothesis_title", "case_title", "doc_1", "doc_2",
                                           "method_title_1", "method_title_2", "method_title_3")}
    fixed_titles = {}
    for fixture in report["fixtures"]:
        for check in fixture["checks"]:
            if check["widget"] in title_widgets:
                key = (fixture["case"], fixture["language"], check["widget"], check["text"])
                fixed_titles.setdefault(key, {"case": fixture["case"], "language": fixture["language"], **check,
                                              "fits": check["used_height"] <= check["height"]})
    report["fixed_title_fits"] = list(fixed_titles.values())
    report["native_texture_aliases"] = TEXTURE_ALIASES
    report["summary"] = {"cases": len(cases), "fixtures": len(report["fixtures"]),
                         "images": sum(bool(f["image"]) for f in report["fixtures"]),
                         "representative_images": sum(bool(f["representative_image"]) for f in report["fixtures"]),
                         "text_checks": sum(len(f["checks"]) for f in report["fixtures"]) + len(report["register_row_checks"]),
                         "register_row_checks": len(report["register_row_checks"]),
                         "register_row_failures": sum(not c["fits"] for c in report["register_row_checks"]),
                         "fixed_title_checks": len(fixed_titles),
                         "fixed_title_failures": sum(not f["fits"] for f in fixed_titles.values()),
                         "source_checks": len(A.SOURCES), "source_changes": len(changed_sources),
                         "issues": len(report["issues"])}
    target = output / f"{P}layout_report.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"]))
    unique = {}
    for issue in report["issues"]:
        key = (issue["kind"], issue["widget"], issue.get("other"), issue.get("text"), issue["language"])
        unique.setdefault(key, issue)
    for issue in unique.values():
        print("QA: " + json.dumps(issue, ensure_ascii=False))
    print("Report: " + str(target))
    return 1 if report["issues"] else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.exit(main())
    except (ValueError, FileNotFoundError, KeyError) as error:
        print("Preview contract error: " + str(error), file=sys.stderr)
        sys.exit(2)
