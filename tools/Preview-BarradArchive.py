#!/usr/bin/env python3
"""Deterministic native-asset fixtures, NOT an HOI4 capture or engine emulator.

Run with Python + Pillow and Node already installed; no browser or new packages.
HOI4_PATH / EAW_PATH override the installed dependency roots. Only writes
art/previews/HSM_BAR_archive_skin_*.png. Scroll position is zero; shader idle
and disabled states only. Bitmap metrics, glyphs, colours, sprites, visibility,
image selectors, and text keys come from the real source files.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from functools import lru_cache

from PIL import Image, ImageChops, PngImagePlugin


REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "mod/HoISubmod"
GAME = Path(os.environ.get("HOI4_PATH", "C:/shit/Steam/steamapps/common/Hearts of Iron IV"))
EAW = Path(os.environ.get("EAW_PATH", "C:/shit/Steam/steamapps/workshop/content/394360/1826643372"))
PREFIX = "HSM_BAR_archive_"
FIXTURES = (
    ("investigated", "russian", "reactor", 5, 2, 2, ("reactor", "echo", "compass", "plants"), None),
    ("results", "english", "rock", 1, 1, 4, ("rock", "titan", "entity", "amulet"), None),
    ("photo", "russian", "titan", 2, 1, 5, ("rock", "titan", "entity", "amulet"), None),
    *(("copy_" + str(copy), "english", "reactor", 5, 2, 2,
       ("reactor", "echo", "compass", "plants"), copy) for copy in (1, 2, 3)),
    ("region_equus", "english", "sombra", 13, 1, 1, ("sombra", "darkheart", "crown"), None),
    ("region_griffonia", "russian", "grover", 10, 1, 1, ("grover", "herald", "crown"), None),
    ("region_north", "russian", "rosa", 11, 1, 1, ("rosa", "chalice", "phylactery"), None),
    ("region_riverlands", "english", "marsh", 15, 1, 2, ("marsh",), None),
    ("region_zebrica", "russian", "zebrica", 18, 1, 1, ("zebrica", "crown"), None),
    ("crown_crossref", "english", "crown", 6, 1, 1, ("sombra", "darkheart", "crown"), None),
)
REGIONS = (("rock", "titan", "entity", "amulet", "reactor", "echo", "compass", "plants"),
           ("sombra", "darkheart", "crown"), ("grover", "herald"), ("rosa", "chalice", "phylactery"),
           ("marsh",), ("zebrica",))
SOURCES = {}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    data = path.read_bytes()
    SOURCES[str(path)] = hashlib.sha256(data).hexdigest()
    return data.decode("utf-8-sig")


def parse_files(paths):
    # Reuse the repository parser without running its test suite.
    source = """
const fs = require('node:fs');
const {parse} = require('./tools/Test-BarradCases.cjs');
const paths = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(paths.map(p => parse(fs.readFileSync(p, 'utf8')))));
"""
    paths = list(paths)
    for path in paths:
        read(path)
    result = subprocess.run(["node", "-e", source], cwd=REPO,
                            input=json.dumps([str(p) for p in paths]),
                            capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(result.stdout)


def prop(nodes, key, default=None):
    return next((n["value"] for n in nodes if n["key"].lower() == key.lower()), default)


def literals(nodes):
    return [n["key"].strip('"') for n in nodes]


def walk(nodes):
    for node in nodes:
        yield node
        if isinstance(node["value"], list):
            yield from walk(node["value"])


def resolve(relative):
    for root in (MOD, EAW, GAME):
        path = root / relative.replace("\\", "/")
        if path.is_file():
            return path
    raise ValueError("Missing asset: " + relative)


@lru_cache(None)
def bitmap(path):
    SOURCES[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    with Image.open(path) as image:
        return image.convert("RGBA")


class Assets:
    def __init__(self, language):
        self.language = language
        self.sprites, self.fonts = {}, {}
        self.overrides = []
        files = [GAME / "interface/core.gfx", EAW / "interface/eaw_fonts.gfx"]
        files += sorted((MOD / "interface").glob("HSM_BAR_archive*.gfx"))
        for nodes in parse_files(files):
            self.ingest(nodes)

    def ingest(self, nodes):
        for n in walk(nodes):
            if not isinstance(n["value"], list):
                continue
            name = prop(n["value"], "name")
            if n["key"].lower() in ("spritetype", "textspritetype", "corneredtilespritetype"):
                self.sprites[name] = (n["key"].lower(), n["value"])
            elif n["key"] == "bitmapfont":
                self.fonts[name] = n["value"]
            elif n["key"] == "bitmapfont_override":
                self.overrides.append(n["value"])

    def sprite(self, name, frame=1, disabled=False):
        if name not in self.sprites:
            # Only parse dependency files actually defining a requested sprite.
            files = []
            pattern = re.compile(r'\bname\s*=\s*"?' + re.escape(name) + r'(?:"|\s)')
            for root in (GAME, EAW, MOD):
                for path in sorted((root / "interface").rglob("*.gfx")):
                    if pattern.search(path.read_text(encoding="utf-8-sig", errors="replace")):
                        files.append(path)
            for nodes in parse_files(files):
                self.ingest(nodes)
        require(name in self.sprites, "Missing sprite definition: " + name)
        kind, definition = self.sprites[name]
        require(kind in ("spritetype", "textspritetype"), "Unsupported tiled sprite: " + name)
        image = bitmap(resolve(prop(definition, "texturefile")))
        frames = int(prop(definition, "noOfFrames", 1))
        require(image.width % frames == 0 and 1 <= frame <= frames,
                "Invalid sprite frame: " + name)
        width = image.width // frames
        image = image.crop(((frame - 1) * width, 0, frame * width, image.height))
        effect = prop(definition, "effectFile", "")
        if disabled and effect.lower() == "gfx/fx/buttonstate.lua":
            # PixelShaderDisable in the installed buttonstate.shader.
            shader = read(GAME / "gfx/FX/buttonstate.shader")
            require("0.212671f, 0.715160f, 0.072169f" in shader,
                    "Native disabled shader changed; review renderer")
            grey = image.convert("RGB").convert("L", (0.212671, 0.715160, 0.072169, 0))
            image = Image.merge("RGBA", (grey, grey, grey, image.getchannel("A")))
        return image

    @lru_cache(None)
    def font(self, name):
        require(name in self.fonts, "Missing native font: " + name)
        definition = self.fonts[name]
        paths = literals(prop(definition, "fontfiles", []))
        if not paths:
            paths = [prop(definition, "path")]
        for override in self.overrides:
            if prop(override, "name") == name and "l_" + self.language in literals(prop(override, "languages", [])):
                paths = literals(prop(override, "fontfiles"))
        return NativeFont(definition, paths)


class NativeFont:
    def __init__(self, definition, paths):
        value = int(prop(definition, "color", "0xffffffff"), 16)
        self.color = ((value >> 16) & 255, (value >> 8) & 255, value & 255, (value >> 24) & 255)
        self.colors = {n["key"]: tuple(map(int, literals(n["value"]))) + (255,)
                       for n in prop(definition, "textcolors", [])}
        self.glyphs, self.kern, owners = {}, {}, {}
        self.line_height = None
        for base in paths:
            path = resolve(base + ".fnt")
            rows = []
            for line in read(path).splitlines():
                values = dict(re.findall(r'(\w+)=("[^"]*"|[^\s]+)', line))
                rows.append((line.split()[0], {k: v.strip('"') for k, v in values.items()}))
            common = next(v for kind, v in rows if kind == "common")
            if self.line_height is None:
                self.line_height = int(common["lineHeight"])
            pages = {}
            if not any(kind == "page" for kind, _ in rows):
                require(int(common["pages"]) == 1, "Missing multi-page font declaration: " + str(path))
                rows.append(("page", {"id": "0", "file": path.with_suffix(".dds").name}))
            for kind, v in rows:
                if kind != "page":
                    continue
                atlas = path.parent / v["file"]
                # HOI4 ships single pages as stem.dds, although BMFont records stem_0.dds.
                if not atlas.exists() and int(common["pages"]) == 1:
                    atlas = path.with_suffix(".dds")
                page = bitmap(atlas)
                require(page.size == (int(common["scaleW"]), int(common["scaleH"])),
                        "Font atlas dimensions disagree: " + str(path))
                pages[int(v["id"])] = page
            for kind, values in rows:
                if kind not in ("char", "kerning"):
                    continue
                v = {k: int(value) for k, value in values.items()}
                if kind == "kerning":
                    if owners.get(v["first"]) == base and owners.get(v["second"]) == base:
                        self.kern.setdefault((v["first"], v["second"]), v["amount"])
                else:
                    crop = pages[v["page"]].crop((v["x"], v["y"], v["x"] + v["width"], v["y"] + v["height"]))
                    self.glyphs.setdefault(v["id"], (crop, v))
                    owners.setdefault(v["id"], base)

    @lru_cache(None)
    def glyph(self, char, color):
        require(ord(char) in self.glyphs, "Missing native glyph U+%04X" % ord(char))
        image, metrics = self.glyphs[ord(char)]
        return ImageChops.multiply(image, Image.new("RGBA", image.size, color)), metrics


class Fixture:
    def __init__(self, fixture, language, texts, script, helpers):
        self.name, default_language, self.case, case_id, page, document, page_cases, copy = fixture
        self.page_cases = page_cases
        self.language = language or default_language
        self.vars = {PREFIX + k: v for k, v in
                     (("open", 1), ("case", case_id), ("page", page), ("document", document))}
        self.vars[PREFIX + "region"] = next(i + 1 for i, cases in enumerate(REGIONS) if self.case in cases)
        if copy is not None:
            self.vars[PREFIX + "copy"] = copy
        self.flags = {"HSM_BAR_" + k for k in ("active", "directorate", "service_founded", "region_local_open")}
        self.flags.update("HSM_BAR_case_" + c + "_known" for c in page_cases)
        if self.case != "zebrica":
            self.flags.add("HSM_BAR_case_" + self.case + "_investigated")
        if self.name == "results":
            self.flags.update(("HSM_BAR_study_rock_done", "HSM_BAR_study_rock_applied", "HSM_BAR_outcome_rock_recorded"))
        self.texts, self.script, self.helpers, self.selected = texts, script, helpers, {}
        self.locale = {}
        for path in sorted((MOD / "localisation" / self.language).glob("HSM_BAR*_l_*.yml")):
            for key, value in re.findall(r'^\s*(\w+):\d*\s+"(.*)"\s*$', read(path), re.M):
                self.locale[key] = value.replace(r'\n', '\n').replace(r'\"', '"')

    def condition(self, nodes):
        self.validate_condition(nodes)
        def test(n):
            k, v = n["key"], n["value"]
            if k == "AND": return self.condition(v)
            if k == "OR": return any(test(child) for child in v)
            if k == "NOT": return not any(test(child) for child in v)
            if k == "tag": return v == "BAR"
            if k in ("is_ai", "has_capitulated", "is_subject"): return v == "no"
            if k == "controls_state": return v == "624"
            if k == "has_country_flag": return v in self.flags
            if k == "has_variable": return v in self.vars
            if k in self.helpers:
                return self.condition(self.helpers[k]) == (v == "yes")
            if k == "check_variable":
                require(len(v) == 1, "Unsupported multi-variable condition")
                a, b, op = self.vars.get(v[0]["key"], 0), float(v[0]["value"]), v[0]["op"]
                require(op in ("=", ">", "<", ">=", "<="), "Unsupported comparison: " + op)
                return {"=": a == b, ">": a > b, "<": a < b, ">=": a >= b, "<=": a <= b}[op]
            if re.fullmatch(r"HSM_BAR_cases_\w+_access", k):
                # Explicit fixture fact, not a simulation of territorial control.
                return (k == "HSM_BAR_cases_" + self.case + "_access") == (v == "yes")
            raise ValueError("Unsupported fixture predicate: " + k)
        return all(test(n) for n in nodes)

    def validate_condition(self, nodes, stack=()):
        require(isinstance(nodes, list), "Missing fixture predicate block")
        for n in nodes:
            k, v = n["key"], n["value"]
            require(n["op"] == "=", "Unsupported predicate operator: " + k)
            if k in ("AND", "OR", "NOT"):
                self.validate_condition(v, stack)
            elif k in self.helpers:
                require(v in ("yes", "no"), "Invalid scripted predicate value")
                require(k not in stack and k in self.helpers, "Missing/recursive scripted predicate: " + k)
                self.validate_condition(self.helpers[k], stack + (k,))
            elif k == "check_variable":
                require(len(v) == 1 and v[0]["key"] in {PREFIX + key for key in ("open", "region", "page", "case", "document", "copy")},
                        "Unsupported fixture variable")
                require(v[0]["op"] in ("=", ">", "<", ">=", "<="), "Unsupported fixture comparison")
                float(v[0]["value"])
            elif k == "has_variable":
                require(v in {PREFIX + key for key in ("open", "region", "page", "case", "document", "copy")},
                        "Unsupported fixture variable")
            elif k in ("is_ai", "has_capitulated", "is_subject") or re.fullmatch(r"HSM_BAR_cases_\w+_access", k):
                require(v in ("yes", "no"), "Invalid boolean fixture predicate")
            elif k == "controls_state":
                require(v == "624", "Unsupported fixture control scope")
            else:
                require(k in ("tag", "has_country_flag") and isinstance(v, str),
                        "Unsupported fixture predicate: " + k)

    def getter(self, name):
        name = name.removeprefix("ROOT.")
        require(name in self.texts, "Missing scripted getter: " + name)
        for block in self.texts[name]:
            if self.condition(prop(block, "trigger", [])):
                key = prop(block, "localization_key")
                self.selected[name] = key
                return key
        raise ValueError("No matching scripted text: " + name)

    def expand(self, value, depth=0):
        require(depth < 24, "Recursive localization: " + value)
        if value.startswith("GFX_"):
            return value
        if value in self.locale:
            return self.expand(self.locale[value], depth + 1)
        value = re.sub(r'\[([\w.]+)\]', lambda m: self.expand(self.getter(m[1]), depth + 1), value)
        value = re.sub(r'\$(\w+)\$', lambda m: self.expand(m[1], depth + 1), value)
        require(not re.search(r'\bHSM_BAR_\w+\b', re.sub(r'\xa3[^\xa3]+\xa3', '', value)),
                "Unresolved localization: " + value)
        return value

    def visible(self, name):
        return self.condition(prop(prop(self.script, "triggers", []), name + "_visible", []))


def text_image(text, font, assets, width, height, align="left"):
    # Atoms carry the original atlas glyph, offsets, advances and kerning.
    atoms, color, index = [], font.color, 0
    while index < len(text):
        char = text[index]
        if char == "\xa7":
            code = text[index + 1]
            require(code == "!" or code in font.colors, "Unknown native text color: " + code)
            color = font.color if code == "!" else font.colors[code]
            index += 2
            continue
        if char == "\xa3":
            end = text.index("\xa3", index + 1)
            icon = assets.sprite("GFX_" + text[index + 1:end])
            atoms.append((icon, icon.width, 0, (font.line_height - icon.height) // 2, None, False))
            index = end + 1
            continue
        if char == "\n":
            atoms.append(None)
        else:
            image, m = font.glyph(char, color)
            atoms.append((image, m["xadvance"], m["xoffset"], m["yoffset"], ord(char), char.isspace()))
        index += 1

    def measure(line):
        total, previous = 0, None
        for atom in line:
            total += font.kern.get((previous, atom[4]), 0) + atom[1]
            previous = atom[4]
        return total

    lines, line, word = [], [], []
    def flush_word():
        nonlocal line, word
        if line and measure(line + word) > width:
            while line and line[-1][5]: line.pop()
            lines.append(line)
            line = []
        for atom in word:
            if line and measure(line + [atom]) > width:
                lines.append(line)
                line = []
            require(atom[1] <= width, "Inline sprite or glyph wider than text box")
            line.append(atom)
        word = []

    for atom in atoms:
        if atom is None or atom[5]:
            flush_word()
            if atom is None:
                lines.append(line)
                line = []
            elif line:
                line.append(atom)
        else:
            word.append(atom)
    flush_word()
    lines.append(line)
    image = Image.new("RGBA", (width, height))
    for row, line in enumerate(lines):
        x = (width - measure(line)) // 2 if align == "centre" or align == "center" else 0
        previous = None
        for glyph, advance, dx, dy, code, _space in line:
            x += font.kern.get((previous, code), 0)
            image.alpha_composite(glyph, (x + dx, row * font.line_height + dy))
            x += advance
            previous = code
    return image, len(lines) * font.line_height


def render(fixture, window, assets):
    size = prop(window, "size")
    dimensions = (int(prop(size, "width")), int(prop(size, "height")))
    require(dimensions == (1000, 700), "Archive window contract changed")
    canvas = Image.new("RGBA", dimensions)
    visible_cases, report = [], []
    properties = prop(fixture.script, "properties", [])
    for node in window:
        kind, widget = node["key"], node["value"]
        if kind not in ("background", "buttonType", "iconType", "instantTextboxType"):
            continue
        name = prop(widget, "name")
        if not fixture.visible(name):
            continue
        position = prop(widget, "position", [])
        x, y = int(prop(position, "x", 0)), int(prop(position, "y", 0))
        if kind == "instantTextboxType":
            width, height = int(prop(widget, "maxWidth")), int(prop(widget, "maxHeight"))
            text = fixture.expand(prop(widget, "text"))
            text_bitmap, full_height = text_image(text, assets.font(prop(widget, "font")), assets,
                                                   width, height, prop(widget, "format", "left"))
            canvas.alpha_composite(text_bitmap, (x, y))
            report.append({"widget": name, "text_height": full_height, "clip_height": height})
            continue
        sprite = prop(widget, "quadTextureSprite", prop(widget, "spriteType"))
        selector = prop(prop(properties, name, []), "image")
        if selector:
            sprite = fixture.expand(selector)
        if kind == "buttonType" and re.fullmatch(PREFIX + r"(?:case_\w+|doc_[1-5]|copy_[1-3])", name):
            require(selector is not None, "Missing actual scripted image selector: " + name)
            if "_case_" in name:
                visible_cases.append(name)
        enabled = fixture.condition(prop(prop(fixture.script, "triggers", []), name + "_click_enabled", []))
        image = assets.sprite(sprite, int(prop(widget, "frame", 1)), not enabled)
        if kind == "buttonType":
            require(x >= 0 and y >= 0 and x + image.width <= dimensions[0] and y + image.height <= dimensions[1],
                    "Button hitbox extends beyond window: " + name)
            require(image.getchannel("A").getbbox() is not None, "Invisible button texture: " + name)
            if name in (PREFIX + "prev", PREFIX + "next", PREFIX + "back", PREFIX + "close", PREFIX + "doc_5") or name.startswith(PREFIX + "audio_"):
                require(len(image.getcolors(image.width * image.height) or []) > 16,
                        "Archive control failed to decode or lost its shaded artwork: " + name)
        definition = assets.sprites[sprite][1]
        if sprite.startswith("GFX_HSM_BAR_archive_") and kind == "buttonType":
            require(int(prop(definition, "noOfFrames", 1)) == 1, "Button states must not be frames: " + sprite)
            effect = prop(definition, "effectFile", "").lower()
            expected = "static_button.lua" if "input_" in name else "buttonstate.lua"
            require(effect == "gfx/fx/" + expected, "Missing native button shader contract: " + sprite)
        explicit_size = prop(widget, "size")
        if explicit_size:
            target = (int(prop(explicit_size, "x", prop(explicit_size, "width"))),
                      int(prop(explicit_size, "y", prop(explicit_size, "height"))))
            require(image.size == target, "Sprite and explicit GUI size disagree: " + name)
        canvas.alpha_composite(image, (x, y))
        label = prop(widget, "buttonText")
        if label:
            font = assets.font(prop(widget, "buttonFont"))
            text_bitmap, full_height = text_image(fixture.expand(label), font, assets,
                                                   image.width, image.height, "center")
            require(full_height <= image.height, "Button text exceeds native bounds: " + name)
            canvas.alpha_composite(text_bitmap, (x, y + (image.height - full_height) // 2))
    require(set(visible_cases) == {PREFIX + "case_" + c for c in fixture.page_cases},
            "Fixture regional index differs from its historical case set")
    return canvas, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("russian", "english"), help="Override the fixtures' default languages")
    args = parser.parse_args()
    skin = MOD / "interface/HSM_BAR_archive_skin.gfx"
    selectors = MOD / "common/scripted_localisation/HSM_BAR_archive_skin.txt"
    helper_path = MOD / "common/scripted_triggers/HSM_BAR_archive_copies.txt"
    for path in (skin, selectors, helper_path):
        require(path.is_file(), "Missing production contract; waiting for main integration: " + str(path))
    # State changes are shaders; selected controls are separate scripted images.
    for filename, states in (("static_button.shader", {"Up": "Up", "Down": "Up", "Disable": "Up", "Over": "Up"}),
                             ("buttonstate.shader", {"Up": "Up", "Down": "Down", "Disable": "Disable", "Over": "Over"})):
        shader = read(GAME / "gfx/FX" / filename)
        for state, pixel_shader in states.items():
            require(re.search(r'Effect\s+' + state + r'\s*\{[^}]*PixelShader\s*=\s*"PixelShader' + pixel_shader + '"', shader),
                    "Native shader state contract changed: " + filename + "/" + state)
    require("OutColor = OutColor * v.vColor;" in read(GAME / "gfx/FX/text.shader"),
            "Native font tint shader changed; review renderer")
    gui, script, helper_nodes, region_nodes, service_nodes, *localizations = parse_files([
        MOD / "interface/HSM_BAR_archive.gui",
        MOD / "common/scripted_guis/HSM_BAR_archive.txt",
        helper_path,
        MOD / "common/scripted_triggers/HSM_BAR_archive_regions.txt",
        MOD / "common/scripted_triggers/HSM_BAR_service_gui.txt",
        MOD / "common/scripted_localisation/HSM_BAR_archive.txt",
        MOD / "common/scripted_localisation/HSM_BAR_case_outcomes.txt", selectors])
    window = next(n["value"] for n in prop(gui, "guiTypes") if prop(n["value"], "name") == PREFIX + "window")
    script = prop(prop(script, "scripted_gui"), PREFIX + "window")
    controls = {prop(n["value"], "name") for n in window if n["key"] == "buttonType"
                and re.fullmatch(PREFIX + r"(?:case_\w+|doc_[1-5]|copy_[1-3]|region_[1-6])", prop(n["value"], "name"))}
    properties = prop(script, "properties", [])
    require(len(controls) == 32 and len(properties) == 32 and {n["key"] for n in properties} == controls,
            "Expected 18 case, five document, three copy and six region image selectors")
    require(all(len(n["value"]) == 1 and prop(n["value"], "image") for n in properties),
            "Only read-only image properties are supported")
    texts = {prop(n["value"], "name"): [entry["value"] for entry in n["value"] if entry["key"] == "text"]
             for nodes in localizations for n in nodes if n["key"] == "defined_text"}
    require(len(helper_nodes) == 1 and helper_nodes[0]["key"] == "HSM_BAR_archive_copies_available",
            "Unexpected archive scripted helper contract")
    helpers = {n["key"]: n["value"] for n in helper_nodes + region_nodes
               + [n for n in service_nodes if n["key"] in ("HSM_BAR_service_gui_actor", "HSM_BAR_service_gui_available")]}
    outputs = []
    for spec in FIXTURES:
        fixture = Fixture(spec, args.language, texts, script, helpers)
        require(fixture.condition(prop(script, "visible")), "Fixture does not open archive")
        for trigger in prop(script, "triggers", []):
            fixture.validate_condition(trigger["value"])
        for choices in texts.values():
            for choice in choices:
                fixture.validate_condition(prop(choice, "trigger", []))
        canvas, report = render(fixture, window, Assets(fixture.language))
        if fixture.name.startswith("copy_"):
            copy = fixture.vars[PREFIX + "copy"]
            suffix = {1: "", 2: "_restricted", 3: "_sealed"}[copy]
            require(fixture.selected.get("GetHSMBARArchiveBody") == PREFIX + "reactor_field" + suffix,
                    "Copy fixture selected the wrong document")
            require(all(fixture.visible(PREFIX + "copy_" + str(i)) for i in (1, 2, 3))
                    and not fixture.visible(PREFIX + "document_title"), "Copy fixture has wrong heading visibility")
            for i in (1, 2, 3):
                require(fixture.selected.get("GetHSMBARArchiveCopy" + str(i) + "Skin")
                        == "GFX_" + PREFIX + "edition" + ("_selected" if copy == i else ""),
                        "Copy fixture has wrong selected control")
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Description", "Static native-asset fixture preview, not a game capture. Idle/disabled buttons; scroll position zero.")
        metadata.add_text("Fixture", json.dumps({"case": fixture.case, "vars": fixture.vars, "flags": sorted(fixture.flags),
                                                "access": ["HSM_BAR_cases_" + fixture.case + "_access"],
                                                "language": fixture.language, "getters": fixture.selected}, sort_keys=True))
        metadata.add_text("Sources", json.dumps(SOURCES, sort_keys=True))
        metadata.add_text("TextBounds", json.dumps(report, sort_keys=True))
        output = REPO / "art/previews" / (PREFIX + "skin_" + fixture.name + "_" + fixture.language + ".png")
        outputs.append((output, canvas, metadata, report))
    for output, canvas, metadata, report in outputs:
        output.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output, pnginfo=metadata)
        clipped = [r["widget"] for r in report if r["text_height"] > r["clip_height"]]
        print(str(output))
        print("  1000x700 static preview; clipped text: " + (", ".join(clipped) or "none"))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as error:
        print("Preview contract error: " + str(error), file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr, file=sys.stderr)
        sys.exit(1)
