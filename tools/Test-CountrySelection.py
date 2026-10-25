"""Static selector integration checks; these do not replace an in-game UI check."""
from __future__ import annotations

import importlib.util
import json
import re
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from unittest import mock
from pathlib import Path

from PIL import Image


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


BASE = module("selector_test_parser", "Test-Verenia.py")
BUILD = module("selector_test_build", "Build-CountrySelection.py")
PLAYSET = module("selector_test_playset", "CountrySelectionPlayset.py")
ART = module("selector_test_art", "Render-CountrySelectionMaps.py")
BOOKMARK = BASE.read(BASE.MOD / BUILD.BOOKMARK)[0].children[0]
UPSTREAM = BASE.read(BASE.OPT.eaw / BUILD.BOOKMARK)[0].children[0]
GUI = BASE.read(BASE.MOD / BUILD.GUI)


def country_entries(bookmark):
    return {n.key: n for n in bookmark.children if re.fullmatch("[A-Z]{3}", n.key)}


def effective_files(folder, suffix):
    result = {}
    for root in (BASE.OPT.game, BASE.OPT.eaw, BASE.MOD):
        result.update({p.relative_to(root / folder).as_posix(): p for p in (root / folder).rglob("*" + suffix)})
    return list(result.values())


def definitions_for(identifiers, folder):
    found = {}
    definition = re.compile(r"(?m)^\s*(?:" + "|".join(map(re.escape, identifiers)) + r")\s*=\s*\{")
    for path in effective_files(folder, ".txt"):
        text = path.read_text(encoding="utf-8-sig")
        if not definition.search(text):
            continue
        for node in BASE.walk(BASE.parse(text)):
            if node.key in identifiers and isinstance(node.value, list):
                found[node.key] = node
    return found


def localization(language):
    path = BASE.MOD / f"localisation/{language}/HSM_country_selection_l_{language}.yml"
    text = path.read_text(encoding="utf-8-sig")
    return path, dict(re.findall(r'^ ([\w.]+):0 "(.*)"$', text, re.M))


class CountrySelection(unittest.TestCase):
    def test_branding_uses_expanded_stories(self):
        for language in ("english", "russian"):
            loc = localization(language)[1]
            self.assertEqual(loc["HSM_CSS_Filter"], "£texticon_HSM_CSS_stories_icon")
            self.assertIn("Equestria at War: Expanded Stories", loc["HSM_CSS_Filter_tt"])
            self.assertNotIn("HoISubmod", loc["HSM_CSS_Filter_tt"])
        for path in (BASE.MOD / "descriptor.mod", BASE.ROOT / "launcher/HoISubmod.mod.example"):
            descriptor = BASE.Node("descriptor", "=", BASE.read(path))
            self.assertEqual(descriptor.get("name"), PLAYSET.TITLE)
            self.assertEqual([n.key for n in descriptor.get("dependencies")],
                             ["Equestria at War"])

    def test_launcher_position_does_not_resolve_the_ghosts_conflict(self):
        with tempfile.TemporaryDirectory(prefix="selector-test-", dir=BASE.ROOT) as directory:
            root = Path(directory).resolve()
            self.assertTrue(root.is_relative_to(BASE.ROOT.resolve()))
            target = root / BUILD.BOOKMARK
            target.parent.mkdir(parents=True)
            target.write_text('bookmarks = { bookmark = { label_order = { CSS_GriffoniaFilter } } }')
            own = {"registry": "mod/local.mod", "root": BASE.MOD.resolve(), "name": PLAYSET.TITLE, "replaces": []}
            other = {"registry": "mod/goy.mod", "root": root, "name": "Ghosts of Yore", "replaces": []}
            self.assertEqual(PLAYSET.conflicts([own, other])[1], [other])
            self.assertEqual(PLAYSET.conflicts([other, own])[1], [other])
            own["dependencies"] = [other["name"]]
            self.assertEqual(PLAYSET.conflicts([own, other])[1], [])
            self.assertEqual(PLAYSET.conflicts([other, own])[1], [])
            other["dependencies"] = [own["name"]]
            self.assertEqual(PLAYSET.conflicts([own, other])[1], [other])

    def test_load_order_detects_directory_replacement(self):
        own = {"registry": "local", "name": PLAYSET.TITLE, "root": BASE.MOD.resolve(), "replaces": []}
        other = {"registry": "other", "name": "Other", "root": Path("Z:/absent-mod"), "replaces": ["common/bookmarks"]}
        self.assertEqual(PLAYSET.conflicts([own, other])[1], [other])

    def test_rename_preserves_descriptor_fields(self):
        descriptor = 'name="HoISubmod"\npath="C:/local"\ndependencies={"Equestria at War"}\n'
        self.assertEqual(PLAYSET.visible_title(descriptor).splitlines()[1:], descriptor.splitlines()[1:])

    def test_dependency_sync_preserves_local_fields_and_is_idempotent(self):
        original = 'name="Local"\npath="C:/local"\nreplace_path="example"\ndependencies={"Local dependency"}\n'
        updated = PLAYSET.sync_dependencies(original)
        node = BASE.Node("descriptor", "=", BASE.parse(updated))
        self.assertEqual(node.get("path"), "C:/local")
        self.assertEqual(node.get("replace_path"), "example")
        self.assertEqual([n.key for n in node.get("dependencies")],
                         ["Local dependency", "Equestria at War"])
        self.assertEqual(PLAYSET.sync_dependencies(updated), updated)
        with self.assertRaises(ValueError):
            PLAYSET.sync_dependencies('dependencies={}\ndependencies={}\n')

    def test_transitive_dependencies_and_missing_optional_mod(self):
        eaw = {"name": "Equestria at War", "dependencies": []}
        goy = {"name": "EaW – Ghosts of Yore", "dependencies": [eaw["name"]]}
        own = {"name": PLAYSET.TITLE, "dependencies": [goy["name"]]}
        self.assertTrue(PLAYSET.ordered_after(own, eaw, [own, goy, eaw]))
        self.assertFalse(PLAYSET.ordered_after(own, eaw, [own, eaw]))
        own["dependencies"].append(eaw["name"])
        self.assertTrue(PLAYSET.ordered_after(own, eaw, [own, eaw]))

    def test_persistent_repair_is_scoped_and_preserves_disabled_mods(self):
        with tempfile.TemporaryDirectory(prefix="selector-test-", dir=BASE.ROOT) as directory:
            root = Path(directory).resolve()
            self.assertTrue(root.is_relative_to(BASE.ROOT.resolve()))
            (root / "mod").mkdir()
            descriptor = root / "mod/local.mod"
            descriptor.write_text(f'name="HoISubmod"\npath="{BASE.MOD.as_posix()}"\n', encoding="utf-8")
            config = {"enabled_mods": ["eaw", "mod/local.mod", "goy", "tech"], "disabled_dlcs": ["test-dlc"]}
            config_path = root / "dlc_load.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            database = root / "launcher-v2.sqlite"
            with closing(sqlite3.connect(database)) as conn:
                conn.executescript("CREATE TABLE playsets (id TEXT, isActive INT, isRemoved INT, loadOrder TEXT);"
                                   "CREATE TABLE mods (id TEXT, gameRegistryId TEXT, dirPath TEXT, displayName TEXT);"
                                   "CREATE TABLE playsets_mods (playsetId TEXT, modId TEXT, enabled INT, position INT);")
                conn.executemany("INSERT INTO playsets VALUES (?,?,?,?)", [("active", 1, 0, "custom"), ("other", 0, 0, "custom")])
                for i, registry in enumerate(["eaw", "mod/local.mod", "disabled", "goy", "tech"]):
                    conn.execute("INSERT INTO mods VALUES (?,?,?,?)", (str(i), registry, str(BASE.MOD), "old"))
                    conn.execute("INSERT INTO playsets_mods VALUES (?,?,?,?)", ("active", str(i), int(registry != "disabled"), i))
                    conn.execute("INSERT INTO playsets_mods VALUES (?,?,?,?)", ("other", str(i), 0, i))
                conn.commit()
            own = {"registry": "mod/local.mod", "descriptor": descriptor, "name": PLAYSET.TITLE}
            with mock.patch.object(PLAYSET.BASE, "ROOT", root):
                before = descriptor.read_bytes()
                with self.assertRaises(ValueError):
                    PLAYSET.repair(root, config, [own], own, [{"registry": "goy", "name": "EaW – Ghosts of Yore"}])
                self.assertEqual(descriptor.read_bytes(), before)
                PLAYSET.repair(root, config, [own], own, [{"registry": "eaw", "name": "Equestria at War"}])
            updated = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(updated, config)
            self.assertIn(PLAYSET.TITLE, descriptor.read_text(encoding="utf-8"))
            self.assertNotIn("EaW – Ghosts of Yore", descriptor.read_text(encoding="utf-8"))
            with closing(sqlite3.connect(database)) as conn:
                self.assertEqual(conn.execute("SELECT modId,enabled FROM playsets_mods WHERE playsetId='active' ORDER BY position").fetchall(),
                                 [("0", 1), ("1", 1), ("2", 0), ("3", 1), ("4", 1)])
                self.assertEqual(conn.execute("SELECT modId,enabled,position FROM playsets_mods WHERE playsetId='other' ORDER BY position").fetchall(),
                                 [(str(i), 0, i) for i in range(5)])
            self.assertEqual(len(list((root / "outputs/launcher-backup").glob("*/launcher-v2.sqlite"))), 1)

    def test_generated_overrides_are_current(self):
        for relative, expected in BUILD.expected_files(BASE.OPT.eaw).items():
            self.assertEqual(expected, (BASE.MOD / relative).read_text(encoding="utf-8-sig"))

    def test_only_four_cards_and_one_filter_are_added(self):
        original = country_entries(UPSTREAM)
        current = country_entries(BOOKMARK)
        self.assertEqual(set(current) - set(original), set(BUILD.TAGS))
        self.assertEqual(len(current), len(original) + 4)
        self.assertEqual(len(current), sum(1 for n in BOOKMARK.children if re.fullmatch("[A-Z]{3}", n.key)))
        for tag, entry in original.items():
            self.assertEqual(current[tag], entry, tag)
        self.assertEqual(
            [n for n in UPSTREAM.children if n.key != "label_order"],
            [n for n in BOOKMARK.children if n.key not in {*BUILD.TAGS, "label_order"}],
        )

    def test_original_tabs_and_default_stay_first(self):
        self.assertEqual([n.key for n in BOOKMARK.get("label_order")],
                         ["CSS_EquestriaFilter", "CSS_GriffoniaFilter", "CSS_ZebricaFilter", "HSM_CSS_Filter"])
        self.assertEqual(BOOKMARK.get("date"), "1007.1.1.12")
        self.assertEqual(BOOKMARK.get("default_country"), "EQS")
        self.assertEqual(BOOKMARK.get("apply_filter_to_majors"), "yes")
        self.assertEqual(BOOKMARK.get("sort_unplayed_first"), "no")

    def test_our_cards_are_exclusive_to_submod_tab(self):
        current = country_entries(BOOKMARK)
        featured = [tag for tag, n in current.items() if "HSM_CSS_Filter" in [v.key for v in n.get("label", [])]]
        self.assertEqual(featured, list(BUILD.TAGS))
        self.assertNotIn("BAR", featured)
        for tag in featured:
            self.assertNotEqual(current[tag].get("minor"), "yes")
            self.assertEqual([v.key for v in current[tag].get("label")], ["HSM_CSS_Filter"])

    def test_no_extra_scenario_or_history_effects(self):
        self.assertEqual(len(BASE.read(BASE.MOD / BUILD.BOOKMARK)[0].all("bookmark")), 1)
        for tag in BUILD.TAGS:
            self.assertEqual({n.key for n in country_entries(BOOKMARK)[tag].children},
                             {"history", "ideology", "label", "ideas", "focuses"})
        self.assertNotIn("replace_path", (BASE.MOD / "descriptor.mod").read_text())

    def test_gui_only_adds_tooltip(self):
        native = BASE.read(BASE.OPT.eaw / BUILD.GUI)
        ours = BASE.read(BASE.MOD / BUILD.GUI)
        target = next(n for n in BASE.walk(ours) if n.get("name") == "gamesetup_interesting_countries_window")
        extra = [n for n in target.children if n.get("name") == "hsm_tooltip_override"]
        self.assertEqual(len(extra), 1)
        target.value.remove(extra[0])
        self.assertEqual(ours, native)

    def test_tooltip_follows_three_existing_tabs(self):
        target = next(n for n in BASE.walk(GUI) if n.get("name") == "gamesetup_interesting_countries_window")
        regions = []
        for name in ("equus", "griffonia", "zebrica", "hsm"):
            box = next(n for n in target.children if n.get("name") == name + "_tooltip_override")
            position = BASE.Node("position", "=", box.get("position"))
            self.assertEqual(position.get("x"), "-66")
            self.assertEqual(box.get("maxwidth"), "93")
            regions.append((int(position.get("y")), int(box.get("maxheight"))))
        self.assertEqual(regions, [(45, 105), (150, 105), (255, 105), (360, 105)])

    def test_cards_fit_native_grid(self):
        countries = next(n for n in BASE.walk(GUI) if n.get("name") == "countries")
        grid = countries.all("gridboxType")[0]
        self.assertEqual(grid.get("max_slots_horizontal"), "4")
        self.assertLessEqual(len(BUILD.TAGS), int(grid.get("max_slots_horizontal")) * int(grid.get("max_slots_vertical")))

    def test_preview_ideas_exist(self):
        ideas = {n.key for tag in BUILD.TAGS for n in country_entries(BOOKMARK)[tag].get("ideas")}
        self.assertEqual(set(definitions_for(ideas, "common/ideas")), ideas)

    def test_preview_focuses_exist(self):
        references = {n.key for tag in BUILD.TAGS for n in country_entries(BOOKMARK)[tag].get("focuses")}
        found = {n.get("id") for p in (BASE.MOD / "common/national_focus").glob("*.txt")
                 for n in BASE.walk(BASE.read(p)) if n.key in {"focus", "shared_focus"} and n.children}
        self.assertEqual(references - found, set())
        for tag in BUILD.TAGS:
            self.assertEqual(len(country_entries(BOOKMARK)[tag].get("focuses")), 3)

    def test_preview_focus_titles_are_localized(self):
        references = {n.key for tag in BUILD.TAGS for n in country_entries(BOOKMARK)[tag].get("focuses")}
        for language in ("english", "russian"):
            keys = set()
            for path in (BASE.MOD / f"localisation/{language}").rglob("*.yml"):
                keys.update(re.findall(r"(?m)^\s+([\w.]+):", path.read_text(encoding="utf-8-sig")))
            self.assertEqual(references - keys, set(), language)

    def test_starting_leader_portraits_resolve(self):
        characters = {"CYA_countess_taillow_sumpfkiel", "ERI_duke_vincent_erie",
                      "EYR_duke_iovinus_eyrie", "AVI_lady_katrina_avian"}
        found = definitions_for(characters, "common/characters")
        self.assertEqual(set(found), characters)
        for character in found.values():
            portraits = BASE.Node("portraits", "=", character.get("portraits"))
            civilian = BASE.Node("civilian", "=", portraits.get("civilian"))
            path = civilian.get("large")
            self.assertTrue(path)
            self.assertTrue(any((root / path).is_file() for root in (BASE.MOD, BASE.OPT.eaw, BASE.OPT.game)), path)

    def test_english_russian_and_native_map_spacing(self):
        english = localization("english")[1]
        native_text = (BASE.OPT.eaw / "localisation/english/eaw_bookmarks_l_english.yml").read_text(encoding="utf-8-sig")
        native = re.search(r' EQS_GATHERING_STORM_DESC:0 "(.*)"', native_text)[1]
        before, after = re.match(r'((?:\\n)+)£\w+((?:\\n)+)', native).groups()
        for language in ("english", "russian"):
            path, loc = localization(language)
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertEqual(set(loc), set(english))
            for tag in BUILD.TAGS:
                text = loc[country_entries(BOOKMARK)[tag].get("history")]
                self.assertTrue(text.startswith(before + f"£GFX_HSM_CSS_{tag}_map" + after))
                self.assertLess(len(text.split(after)[-1]), 650)
            self.assertNotIn("@BAR", loc["HSM_CSS_Filter_tt"])

    def test_map_assets_resolve_and_have_native_dimensions(self):
        sprites = BASE.read(BASE.MOD / "interface/HSM_country_selection.gfx")[0].children
        maps = [s for s in sprites if s.get("name").endswith("_map")]
        self.assertEqual({s.get("name") for s in maps}, {f"GFX_HSM_CSS_{tag}_map" for tag in BUILD.TAGS})
        for sprite in maps:
            image = Image.open(BASE.MOD / sprite.get("textureFile")).convert("RGBA")
            self.assertEqual(image.size, (485, 344))
            self.assertIsNone(image.crop((0, 0, 92, 344)).getbbox())
            self.assertGreater(len(image.crop((101, 20, 467, 294)).convert("RGB").getcolors(200000)), 150)
            self.assertEqual(image.getchannel("A").getextrema(), (0, 255))

    def test_maps_use_reviewed_atlas_sources_and_native_frame(self):
        expected = ART.render_maps(BASE.OPT.eaw)
        with Image.open(BASE.OPT.eaw / ART.TEMPLATE) as source:
            frame = source.convert("RGBA")
        signatures = set()
        for tag, image in expected.items():
            with Image.open(ART.OUT / f"HSM_{tag}.tga") as stored:
                self.assertEqual(image.tobytes(), stored.convert("RGBA").tobytes())
            signatures.add(image.tobytes())
            for box in ((0, 0, 104, 344), (464, 0, 485, 344), (104, 0, 464, 21), (104, 322, 464, 344)):
                self.assertEqual(image.crop(box).tobytes(), frame.crop(box).tobytes())
        self.assertEqual(len(signatures), 4)

    def test_tab_icon_has_native_dimensions_alpha_and_registered_sprite(self):
        sprites = BASE.read(BASE.MOD / "interface/HSM_country_selection.gfx")[0].children
        sprite = next(s for s in sprites if s.get("name") == "GFX_texticon_HSM_CSS_stories_icon")
        with Image.open(BASE.MOD / sprite.get("textureFile")) as source:
            image = source.convert("RGBA")
        self.assertEqual(image.size, (78, 70))
        self.assertEqual(image.getchannel("A").getextrema(), (0, 255))
        self.assertEqual(image.tobytes(), ART.render_icon().tobytes())
        x0, y0, x1, y1 = image.getbbox()
        self.assertGreaterEqual(min(x0, y0), 3)
        self.assertGreaterEqual(min(78 - x1, 70 - y1), 3)

    def test_illustrated_tooltip_uses_native_spacing_and_a_real_asset(self):
        sprites = BASE.read(BASE.MOD / "interface/HSM_country_selection.gfx")[0].children
        intro = next(s for s in sprites if s.get("name") == "GFX_HSM_CSS_stories_intro")
        with Image.open(BASE.MOD / intro.get("textureFile")) as im:
            self.assertEqual(im.size, (325, 207))
            self.assertGreater(len(im.convert("RGB").getcolors(100000)), 1000)
        native = (BASE.OPT.eaw / "localisation/english/eaw_bookmarks_l_english.yml").read_text(encoding="utf-8-sig")
        tooltip = re.search(r' CSS_GriffoniaFilter_tt:0 "(.*)"', native)[1]
        spacing = re.search(r'((?:\\n)+)£\w+((?:\\n)+)', tooltip).groups()
        for language in ("english", "russian"):
            text = localization(language)[1]["HSM_CSS_Filter_tt"]
            self.assertIn(spacing[0] + "£GFX_HSM_CSS_stories_intro" + spacing[1] + "§L", text)
            self.assertNotIn("@", text)
            self.assertTrue(text.endswith("§!"))

    def test_upstream_card_addition_requires_manual_reconciliation(self):
        with self.assertRaises(ValueError):
            BUILD.replace_once("duplicate duplicate", "duplicate", "replacement")
        with self.assertRaises(ValueError):
            BUILD.replace_once("changed", "missing", "replacement")


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], *BASE.REST])
