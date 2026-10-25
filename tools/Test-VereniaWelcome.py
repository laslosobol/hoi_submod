"""Check the native welcome-screen adapters and both language packs.

Uses production dispatch tables and the existing trigger fixture. This checks
source wiring and fallbacks, not engine localization precedence or pixel layout.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "verenia_welcome_base", Path(__file__).with_name("Test-Verenia.py")
)
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)
LOC = BASE.MOD / "localisation"
SCRIPT = BASE.MOD / "common/scripted_localisation/HSM_VER_welcome.txt"
TABLES = {n.get("name"): n for n in BASE.read(SCRIPT)}
LANGUAGES = ("english", "russian")
NATIVE = {
    "EAW_WS_TAB_1_HEADER": "GetNiceCountryName",
    "EAW_WS_TAB_1_TXT": "GetCountryIntro",
    "EAW_WS_TAB_2_HEADER": "GetRegionName",
    "EAW_WS_TAB_2_TXT": "GetRegionDesc",
}
GETTER = re.compile(r"^\[Root\.(\w+)\]$")
ENTRY = re.compile(r'\s*([^#\s:]+):\d*\s+"(.*)"\s*$')


def locale(path):
    entries = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = ENTRY.fullmatch(line)
        if not match or match[1] in entries:
            raise AssertionError(f"Malformed/duplicate localization in {path}: {line}")
        entries[match[1]] = match[2]
    return entries


def paths(language):
    return (
        LOC / language / f"HSM_VER_welcome_l_{language}.yml",
        LOC / "replace" / language / f"HSM_VER_welcome_dispatch_l_{language}.yml",
    )


def select(getter, world, tag):
    for text in TABLES[getter].all("text"):
        if world.check(text.get("trigger", []), tag):
            return text.get("localization_key")
    raise AssertionError(f"No fallback for {getter}/{tag}")


class Welcome(unittest.TestCase):
    def test_bilingual_packs_are_valid_and_complete(self):
        inventories = []
        for language in LANGUAGES:
            content_path, dispatch_path = paths(language)
            for path in (content_path, dispatch_path):
                self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"), path)
                self.assertTrue(path.read_text(encoding="utf-8-sig").startswith(f"l_{language}:\n"))
            content, dispatch = locale(content_path), locale(dispatch_path)
            self.assertEqual(set(dispatch), set(NATIVE))
            for table in TABLES.values():
                for text in table.all("text"):
                    self.assertIn(text.get("localization_key"), content)
            inventories.append((set(content), dispatch))
        self.assertEqual(inventories[0], inventories[1])

    def test_native_window_and_unchanged_fallback_getters_exist(self):
        native_gui = (BASE.OPT.eaw / "interface/eaw_welcome_screen.gui").read_text(encoding="utf-8-sig")
        native_tables = {
            n.get("name") for n in BASE.read(
                BASE.OPT.eaw / "common/scripted_localisation/EAW_welcomescreen_scripted_localisation.txt"
            )
        }
        for language in LANGUAGES:
            content, dispatch = map(locale, paths(language))
            for key, native in NATIVE.items():
                self.assertIn(f'"{key}"', native_gui)
                self.assertIn(native, native_tables)
                getter = GETTER.fullmatch(dispatch[key])[1]
                self.assertIn(getter, TABLES)
                fallback = TABLES[getter].all("text")[-1]
                self.assertFalse(fallback.all("trigger"))
                self.assertEqual(content[fallback.get("localization_key")], f"[Root.{native}]")
                self.assertNotIn(native, TABLES, "Fallback must not recurse through our adapter")

    def test_both_houses_get_distinct_histories_and_shared_region_after_renaming(self):
        world = BASE.World()
        for language in LANGUAGES:
            content, dispatch = map(locale, paths(language))
            histories = {}
            regions = {}
            for tag in ("ERI", "EYR"):
                for cosmetic in ("", "HSM_VER_UNIFIED", "HSM_VER_REGENCY"):
                    world.countries[tag].cosmetic = cosmetic
                    for key, value in dispatch.items():
                        selected = select(GETTER.fullmatch(value)[1], world, tag)
                        self.assertNotIn("original", selected)
                        self.assertNotIn("[Root.", content[selected])
                        if key == "EAW_WS_TAB_1_TXT":
                            histories[tag] = selected
                        elif key == "EAW_WS_TAB_2_TXT":
                            regions[tag] = selected
            self.assertNotEqual(histories["ERI"], histories["EYR"])
            self.assertEqual(regions["ERI"], regions["EYR"])

    def test_all_other_native_tags_retain_native_dispatch(self):
        world = BASE.World()
        tags = {
            n.key for path in (BASE.OPT.eaw / "common/country_tags").glob("*.txt")
            for n in BASE.read(path) if re.fullmatch(r"[A-Z0-9]{3}", n.key)
        }
        self.assertTrue({"AVI", "CYA", "GRI", "EQS"} <= tags)
        content, dispatch = map(locale, paths("english"))
        for tag in tags - {"ERI", "EYR"}:
            world.countries[tag] = BASE.Country(tag)
            for key, value in dispatch.items():
                selected = select(GETTER.fullmatch(value)[1], world, tag)
                self.assertEqual(content[selected], f"[Root.{NATIVE[key]}]", (tag, key))

    def test_embedded_opening_focus_names_resolve_in_both_languages(self):
        for language in LANGUAGES:
            content = locale(paths(language)[0])
            available = {}
            for path in (LOC / language).glob("*.yml"):
                # Other files may contain comments or headers; collect only entries.
                for line in path.read_text(encoding="utf-8-sig").splitlines():
                    match = ENTRY.fullmatch(line)
                    if match:
                        available[match[1]] = match[2]
            for key, value in content.items():
                for reference in re.findall(r"\$([^$]+)\$", value):
                    self.assertIn(reference, available, (language, key, reference))
                    self.assertTrue(available[reference])


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]] + BASE.REST)
