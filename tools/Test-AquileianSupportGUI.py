"""Read-only source checks for the additive regional support GUI, not UI playtests.

Usage: python -B tools/Test-AquileianSupportGUI.py --eaw PATH [-v]
Builds strings in memory only. Does not emit production files or run the campaign.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

import aquileian_support_gui as gui

ARGS = argparse.ArgumentParser(description=__doc__)
ARGS.add_argument("--eaw", type=Path, required=True)
OPT, REST = ARGS.parse_known_args()


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.children)


def named(nodes, name):
    found = [n for n in walk(nodes) if n.get("name") == name]
    if len(found) != 1:
        raise AssertionError((name, len(found)))
    return found[0]


def signature(node, ignored=()):
    return (node.key, node.op, tuple(signature(n) for n in node.children if n.key not in ignored)
            if node.children else node.value)


class SupportGUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files, cls.loc = gui.build_support_gui(OPT.eaw)
        cls.parse = staticmethod(gui._parser()["API"]["parse"])
        cls.nodes = {p: cls.parse(text) for p, text in cls.files.items()}
        cls.native = cls.parse((OPT.eaw / "interface/eaw_jer_revolution.gui").read_text(encoding="utf-8-sig"))

    def test_additive_paths_and_pure_api(self):
        self.assertEqual(set(self.files), {
            "interface/HSM_AQR_support.gui", "common/scripted_guis/HSM_AQR_support.txt",
            "common/decisions/categories/HSM_AQR_support.txt"})
        self.assertTrue(all(isinstance(p, str) and isinstance(t, str) for p, t in self.files.items()))
        self.assertTrue(all(not (OPT.eaw / p).exists() for p in self.files))
        with patch.object(Path, "write_text", side_effect=AssertionError("unexpected write")), \
             patch.object(Path, "write_bytes", side_effect=AssertionError("unexpected write")):
            self.assertEqual(gui.build_support_gui(OPT.eaw), (self.files, self.loc))

    def test_four_categories_bind_local_country_context(self):
        categories = self.nodes[gui.CATEGORY_PATH]
        scripts = self.nodes[gui.SCRIPT_PATH][0].children
        self.assertEqual(len(categories), 4)
        self.assertEqual(len(scripts), 4)
        for tag, category in zip(("JEB", "JRR", "JFT", "VIN"), categories):
            self.assertEqual(category.get("allowed")[0].value, tag)
            self.assertEqual(category.get("allowed")[0].key, "original_tag")
            self.assertEqual(category.get("visible_when_empty"), "yes")
            script = next(n for n in scripts if n.key == category.get("scripted_gui"))
            self.assertEqual(script.get("context_type"), "decision_category")
            self.assertEqual(script.get("window_name"), gui.WINDOW)
            self.assertEqual({n.key: n.get("frame") for n in script.get("properties")}, {
                "HSM_AQR_support_bar": "monarchist_support"})

    def test_native_visibility_from_day_zero_until_revolution(self):
        phase_flags = ("JER_revolution_begun", "JER_revolution_ended", "JER_revolution_ended_2")

        def condition(node, jer_exists, flags):
            # Bounded source-condition check; reject unsupported constructs.
            if node.key == "JER":
                self.assertEqual([(n.key, n.value) for n in node.children], [("exists", "yes")])
                return jer_exists
            self.assertEqual(node.key, "NOT")
            self.assertEqual(len(node.children), 1)
            flag = node.children[0]
            self.assertEqual(flag.key, "has_global_flag")
            self.assertIn(flag.value, phase_flags)
            return flag.value not in flags

        for category in self.nodes[gui.CATEGORY_PATH]:
            visible = category.get("visible")
            self.assertEqual([n.key for n in visible], ["JER", "NOT", "NOT", "NOT"])
            self.assertEqual({n.children[0].value for n in visible if n.key == "NOT"}, set(phase_flags))
            # No completed political root, started flag, or main campaign trigger:
            # day zero and either prewar political root share this same window.
            for jer_exists in (False, True):
                for mask in range(8):
                    flags = {flag for i, flag in enumerate(phase_flags) if mask & (1 << i)}
                    with self.subTest(category=category.key, jer_exists=jer_exists, flags=flags):
                        actual = all(condition(n, jer_exists, flags) for n in visible)
                        self.assertEqual(actual, jer_exists and mask == 0)

    def test_native_visual_widgets_preserved(self):
        for old, new, ignored in (
            ("support_progbar_monarchist", "HSM_AQR_support_bar", ("name", "pdx_tooltip")),
            ("progbar_frame", "HSM_AQR_support_frame", ("name",)),
        ):
            with self.subTest(widget=old):
                self.assertEqual(signature(named(self.native, old), ignored),
                                 signature(named(self.nodes[gui.GUI_PATH], new), ignored))
        icons = [n for n in walk(self.nodes[gui.GUI_PATH]) if n.key == "icontype"]
        self.assertEqual(len(icons), 2)  # Exactly one split bar and one frame.
        self.assertEqual([n.get("quadtexturesprite") for n in icons if n.get("quadtexturesprite")],
                         ["GFX_JERrev_support_progress"])
        gfx = self.parse((OPT.eaw / "interface/eaw_jer_revolution.gfx").read_text(encoding="utf-8-sig"))
        split = named(gfx, "GFX_JERrev_support_progress")
        self.assertEqual(split.key, "progressbartype")
        self.assertEqual(split.get("texturefile1"), "gfx/interface/jer_misc/support_progress_blue.dds")
        self.assertEqual(split.get("texturefile2"), "gfx/interface/jer_misc/support_progress_red.dds")

    def test_no_influence_effects_or_foreign_selector(self):
        forbidden = {"effects", "dynamic_lists", "buttontype", "buttonType", "dirty",
                     "set_variable", "set_temp_variable", "add_to_variable", "subtract_from_variable",
                     "set_country_flag", "cost", "complete_effect", "target_root_trigger"}
        for path, nodes in self.nodes.items():
            self.assertFalse(forbidden.intersection(n.key for n in walk(nodes)), path)
        text = "\n".join(self.files.values()) + str(self.loc)
        for forbidden_text in ("JERrev_selected_country", "revolution_country", "JER:", "ROOT:",
                               "HSM_AQR_started", "HSM_AQR_active", "HSM_AQR_mechanic_active",
                               "has_completed_focus", "_click"):
            self.assertNotIn(forbidden_text, text)

    def test_localization_complete_and_local_scope(self):
        references = set(n.key for n in self.nodes[gui.CATEGORY_PATH])
        for n in walk(self.nodes[gui.GUI_PATH]):
            if n.key in ("text", "pdx_tooltip") and isinstance(n.value, str) and n.value.startswith("HSM_"):
                references.add(n.value)
        self.assertEqual(references, set(self.loc))
        for key, pair in self.loc.items():
            self.assertIsInstance(pair, tuple, key)
            self.assertEqual(len(pair), 2, key)
            self.assertTrue(all(isinstance(s, str) and s.strip() for s in pair), key)
        for text in self.loc["HSM_AQR_support_local_tt"]:
            self.assertIn("[?monarchist_support|C0]", text)
            self.assertIn("[?revolutionary_support|R0]", text)
        for camp, color in (("monarchist", "C"), ("revolutionary", "R")):
            label = named(self.nodes[gui.GUI_PATH], f"HSM_AQR_support_{camp}_label")
            self.assertEqual(label.get("text_color_code"), color)
            for text in self.loc[label.get("text")]:
                self.assertIn(f"[?{camp}_support|0]%", text)

    def test_native_art_dimensions_and_panel_fit(self):
        dimensions = {}
        for name, expected in (("support_progress_frame.dds", (420, 52)),
                               ("support_progress_blue.dds", (404, 36)),
                               ("support_progress_red.dds", (404, 36))):
            with (OPT.eaw / "gfx/interface/jer_misc" / name).open("rb") as handle:
                header = handle.read(20)
            self.assertEqual(header[:4], b"DDS ")
            height, width = struct.unpack_from("<II", header, 12)
            self.assertEqual((width, height), expected)
            dimensions[name] = (width, height)
        panel = named(self.nodes[gui.GUI_PATH], gui.WINDOW)
        height = int(next(n.value for n in panel.get("size") if n.key == "height"))
        self.assertLessEqual(height, 90)

        def pos(node, axis):
            return int(next((n.value for n in node.get("position", []) if n.key == axis), 0))

        row = named(panel.children, "HSM_AQR_support_row")
        labels = [named(panel.children, f"HSM_AQR_support_{camp}_label")
                  for camp in ("monarchist", "revolutionary")]
        self.assertLessEqual(pos(labels[0], "x") + int(labels[0].get("maxwidth")), pos(labels[1], "x"))
        for label in labels:
            self.assertGreaterEqual(pos(label, "y"), 0)
            self.assertLessEqual(pos(label, "y") + int(label.get("maxheight")), pos(row, "y"))
        for suffix, texture in (("bar", "support_progress_blue.dds"),
                                ("frame", "support_progress_frame.dds")):
            child = named(row.children, f"HSM_AQR_support_{suffix}")
            top = pos(row, "y") + pos(child, "y")
            self.assertGreaterEqual(top, pos(row, "y"))
            self.assertLessEqual(top + dimensions[texture][1], height)

    def test_tooltip_newlines_survive_main_serializer(self):
        # Extract only the production esc function, never import/run the builder.
        source = Path(__file__).with_name("Build-AquileianRegions.py").read_text(encoding="utf-8-sig")
        functions = [n for n in ast.walk(ast.parse(source))
                     if isinstance(n, ast.FunctionDef) and n.name == "esc"]
        self.assertEqual(len(functions), 1)
        namespace = {}
        exec(compile(ast.Module(body=functions, type_ignores=[]), "<main esc>", "exec"), namespace)
        for text in self.loc["HSM_AQR_support_local_tt"]:
            self.assertEqual(text.count("\n"), 2)
            self.assertNotIn("\\n", text)
            escaped = namespace["esc"](text)
            self.assertEqual(escaped.count("\\n"), 2)
            self.assertNotIn("\\\\n", escaped)
            self.assertNotIn("\n", escaped)

    def test_region_specific_titles(self):
        expected = {
            "JEB": ("Support in Rila", "Поддержка в Риле"),
            "JRR": ("Support in Westkeep", "Поддержка в Весткипе"),
            "JFT": ("Support in Pridea", "Поддержка в Придее"),
            "VIN": ("Support in Vinovia", "Поддержка в Виновии"),
        }
        for tag, title in expected.items():
            self.assertEqual(self.loc[f"HSM_AQR_support_{tag}"], title)

    def test_upstream_binding_drift_rejected(self):
        read = Path.read_text

        def changed(path, *args, **kwargs):
            text = read(path, *args, **kwargs)
            if path.name == "eaw_jer_revolution.txt":
                text = text.replace("frame = JERrev_selected_country:monarchist_support", "frame = changed_support")
            return text

        with patch.object(Path, "read_text", changed):
            with self.assertRaisesRegex(ValueError, "native monarchist variable binding changed"):
                gui.build_support_gui(OPT.eaw)


if __name__ == "__main__":
    unittest.main(argv=[__file__, *REST])
