"""Pure builder for four local, display-only EaW revolution support panels.

API: build_support_gui(eaw_path) -> (files, localization). File keys are relative
to the playable mod; localization values are (English, Russian). The caller owns
headers, encoding and emission. This module never writes files or changes EaW.

Prototype: interface/eaw_jer_revolution.gui and its decision-category scripted GUI.
Only the native progress widgets are copied; country selection and influence
actions are deliberately absent. Panels use the native pre-revolution window:
JER exists, and no revolution-begun or either revolution-ended global flag is set.
They are available from day zero, without a political-root or campaign-tracking
requirement. Each category's country context reads its own native variables.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import runpy
import sys

TAGS = ("JEB", "JRR", "JFT", "VIN")
REGION_TITLES = {
    "JEB": ("Support in Rila", "Поддержка в Риле"),
    "JRR": ("Support in Westkeep", "Поддержка в Весткипе"),
    "JFT": ("Support in Pridea", "Поддержка в Придее"),
    "VIN": ("Support in Vinovia", "Поддержка в Виновии"),
}
WINDOW = "HSM_AQR_support_window"
GUI_PATH = "interface/HSM_AQR_support.gui"
SCRIPT_PATH = "common/scripted_guis/HSM_AQR_support.txt"
CATEGORY_PATH = "common/decisions/categories/HSM_AQR_support.txt"


@lru_cache(maxsize=1)
def _parser():
    # Reuse existing token spans without feeding the embedding builder's CLI to
    # the historical Test-Verenia argument parser imported by this utility.
    old = sys.argv
    try:
        sys.argv = [__file__]
        return runpy.run_path(str(Path(__file__).with_name("Build-VereniaSpirit.py")))
    finally:
        sys.argv = old


def _require(condition, message):
    if not condition:
        raise ValueError("Aquileian support GUI: " + message)


def _one(nodes, key):
    found = [node for node in nodes if node.key == key]
    _require(len(found) == 1, f"expected one {key}, found {len(found)}")
    return found[0]


def _named(nodes, name):
    found = [node for node in nodes if any(
        child.key == "name" and child.value == name for child in node.children)]
    _require(len(found) == 1, f"missing or ambiguous native widget/sprite {name}")
    return found[0]


def _copy_widget(source, node, fields):
    """Patch only selected scalar fields; preserve the native widget geometry."""
    result = source[node.start:node.end]
    edits = []
    for key, value in fields.items():
        field = _one(node.children, key)
        _require(not field.children, f"unexpected block field {key}")
        edits.append((field.start - node.start, field.end - node.start,
                      f'{key} = "{value}"'))
    for start, end, replacement in sorted(edits, reverse=True):
        result = result[:start] + replacement + result[end:]
    return result


def build_support_gui(eaw_path):
    """Return additive source and EN/RU entries, without mutating any file."""
    eaw = Path(eaw_path)
    api = _parser()
    spans = api["spans"]
    source = (eaw / "interface/eaw_jer_revolution.gui").read_text(encoding="utf-8-sig")
    native = _named(_one(spans(source), "guitypes").children,
                    "EaW_JER_revolution_deccat")
    progress = _named(native.children, "progressbar_container")
    script = spans((eaw / "common/scripted_guis/eaw_jer_revolution.txt").read_text(
        encoding="utf-8-sig"))
    definition = _one(_one(script, "scripted_gui").children, "eaw_JER_revolution_deccat")
    _require(_one(definition.children, "context_type").value == "decision_category",
             "native scripted GUI no longer uses the decision-category context")
    properties = _one(definition.children, "properties")
    gfx = _one(spans((eaw / "interface/eaw_jer_revolution.gfx").read_text(
        encoding="utf-8-sig")), "spritetypes").children
    frame = _named(progress.children, "progbar_frame")
    _require(_one(frame.children, "spritetype").value == "GFX_JERrev_progress_frame",
             "native frame sprite changed")
    loc = {
        "HSM_AQR_support_monarchist_label": (
            "Monarchists: [?monarchist_support|0]%", "Монархисты: [?monarchist_support|0]%"),
        "HSM_AQR_support_revolutionary_label": (
            "Revolutionaries: [?revolutionary_support|0]%", "Революционеры: [?revolutionary_support|0]%"),
        "HSM_AQR_support_local_tt": (
            "Local support:\n§CMonarchists§!: [?monarchist_support|C0]%\n"
            "§RRevolutionaries§!: [?revolutionary_support|R0]%",
            "Поддержка в нашем регионе:\n§CМонархисты§!: [?monarchist_support|C0]%\n"
            "§RРеволюционеры§!: [?revolutionary_support|R0]%"),
    }
    # This native sprite already combines blue and red. A second reverse bar
    # would repeat the same split; show both local values in its two labels.
    icon = _named(progress.children, "support_progbar_monarchist")
    binding = _one(properties.children, "support_progbar_monarchist")
    _require(_one(binding.children, "frame").value == "JERrev_selected_country:monarchist_support",
             "native monarchist variable binding changed")
    _require(_one(icon.children, "quadtexturesprite").value == "GFX_JERrev_support_progress",
             "native monarchist progress sprite changed")
    bar = _copy_widget(source, icon, {"name": "HSM_AQR_support_bar", "pdx_tooltip": "HSM_AQR_support_local_tt"})
    border = _copy_widget(source, frame, {"name": "HSM_AQR_support_frame"})
    labels = []
    for camp, x, color, align in (
        ("monarchist", 5, "C", "left"),
        ("revolutionary", 217, "R", "right"),
    ):
        name = f"HSM_AQR_support_{camp}"
        labels.append(f'''instantTextBoxType = {{
 name = "{name}_label"
 text = {name}_label
 position = {{ x = {x} y = 2 }}
 font = "hoi_16mbs"
 maxwidth = 200
 maxheight = 23
 format = {align}
 text_color_code = {color}
 pdx_tooltip = HSM_AQR_support_local_tt
}}''')

    # Depend on existing native sprites, never clone/redefine their art. Fail on
    # missing textures instead of silently emitting an invisible substitute.
    for sprite in ("GFX_JERrev_support_progress", "GFX_JERrev_progress_frame"):
        definition = _named(gfx, sprite)
        for field in definition.children:
            if field.key in ("texturefile", "texturefile1", "texturefile2"):
                _require((eaw / field.value).is_file(), f"missing native texture {field.value}")

    guis, categories = [], []
    for tag in TAGS:
        category = f"HSM_AQR_support_{tag}"
        guis.append(f'''{category}_gui = {{
 window_name = "{WINDOW}"
 context_type = decision_category
 properties = {{
  HSM_AQR_support_bar = {{ frame = monarchist_support }}
 }}
}}''')
        categories.append(f'''{category} = {{
 icon = generic_democracy
 allowed = {{ original_tag = {tag} }}
 priority = {{ base = 105 }}
 visible_when_empty = yes
 visible = {{
  JER = {{ exists = yes }}
  NOT = {{ has_global_flag = JER_revolution_begun }}
  NOT = {{ has_global_flag = JER_revolution_ended }}
  NOT = {{ has_global_flag = JER_revolution_ended_2 }}
 }}
 scripted_gui = {category}_gui
}}''')
        loc[category] = REGION_TITLES[tag]

    labels_text = "\n".join(labels)
    guis_text = "\n".join(guis)
    files = {
        GUI_PATH: f'''guitypes = {{
 containerwindowtype = {{
  name = "{WINDOW}"
  size = {{ width = 100%% height = 86 }}
  {labels_text}
  containerwindowtype = {{
   name = "HSM_AQR_support_row"
   position = {{ x = -3 y = 28 }}
   {bar}
   {border}
  }}
 }}
}}
''',
        SCRIPT_PATH: f"scripted_gui = {{\n{guis_text}\n}}\n",
        CATEGORY_PATH: "\n\n".join(categories) + "\n",
    }
    for text in files.values():
        api["API"]["parse"](text)
    return files, loc
