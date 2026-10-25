"""Scoped native-tooltip regressions; no engine rendering or baseline writes.

python -B -X utf8 tools/Test-VereniaNativeUI.py
The frozen gameplay digests cover only pre-existing owned scripts. New worker
files are deliberately outside that inventory, not accepted into an old baseline.
Full UI budgets remain in Test-VereniaFocusUI.py and Test-VereniaNarrativeUI.py.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod/HoISubmod"
QA = runpy.run_path(str(Path(__file__).with_name("Test-VereniaNarrativeUI.py")))
BASELINE = json.loads(Path(__file__).with_name("verenia-native-ui-baseline.json").read_text(encoding="utf-8"))
read, walk = QA["read"], QA["walk"]


def visible(nodes):
    for node in nodes:
        if node.key != "hidden_effect":
            yield node
            yield from visible(node.children)


def owned_locales():
    return sorted(p for p in (MOD / "localisation").rglob("HSM_VER*.yml")
                  if not p.name.startswith(("HSM_VER_commonwealth", "HSM_VER_focus_ui_domestic"))
                  and "development" not in p.name)


class NativePresentation(unittest.TestCase):
    def test_owned_gameplay_matches_frozen_pre_repair_digests(self):
        self.assertEqual(len(BASELINE["sha256"]), 83)
        for relative, expected in BASELINE["sha256"].items():
            with self.subTest(path=relative):
                normalized = QA["canonical_file"](read(MOD / relative), QA["file_kind"](Path(relative)))
                actual = hashlib.sha256(json.dumps(normalized, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
                self.assertEqual(actual, expected, "Gameplay/order changed; do not regenerate the baseline to accept it")

    def test_archive_has_native_two_fifty_percent_research_bonuses(self):
        nodes = read(MOD / "common/national_focus/HSM_VER_imperial.txt")
        focus = next(n for n in nodes if n.get("id") == "HSM_VER_IMP_open_archives")
        effects = list(visible(focus.get("completion_reward")))
        bonuses = [n for n in effects if n.key == "add_tech_bonus"]
        self.assertEqual(len(bonuses), 1)
        self.assertEqual((bonuses[0].get("bonus"), bonuses[0].get("uses"), bonuses[0].get("category")), ("0.5", "2", "industry"))
        self.assertNotIn("HSM_VER_FUI_archive_effect_tt", [n.value for n in effects if n.key == "custom_effect_tooltip"])

    def test_owned_focus_research_bonuses_are_not_hidden(self):
        checked = 0
        for relative in BASELINE["sha256"]:
            if "national_focus/HSM_" not in relative:
                continue
            for focus in walk(read(MOD / relative)):
                if focus.key not in ("focus", "shared_focus"):
                    continue
                reward = focus.get("completion_reward", [])
                all_bonuses = [n for n in walk(reward) if n.key == "add_tech_bonus"]
                shown = [n for n in visible(reward) if n.key == "add_tech_bonus"]
                with self.subTest(focus=focus.get("id")):
                    self.assertEqual(shown, all_bonuses)
                checked += len(all_bonuses)
        self.assertGreater(checked, 0)

    def test_both_treaties_preview_the_conditional_peace_dividend(self):
        for filename, focus_id in (("HSM_ERI.txt", "HSM_ERI_friendship_treaty"),
                                   ("HSM_VER_eyrie.txt", "HSM_EYR_friendship_with_safeguards")):
            focus = next(n for n in walk(read(MOD / "common/national_focus" / filename)) if n.get("id") == focus_id)
            reward = focus.get("completion_reward")
            self.assertEqual([(n.key, n.value) for n in reward[:3]], [
                ("custom_effect_tooltip", "HSM_VER_UI_ducal_treaty_reward_tt"),
                ("custom_effect_tooltip", "HSM_VER_UI_ducal_treaty_recipients_tt"),
                ("show_ideas_tooltip", "HSM_VER_peace_dividend"),
            ])
            self.assertFalse(any(n.key == "add_ideas" for n in walk(reward)))
            self.assertEqual([(n.key, n.value) for n in reward[3].children], [("HSM_VER_conclude_treaty", "yes")])
        for language, condition, refusal in (("english", "Upon ratification", "refuse"),
                                              ("russian", "При ратификации", "отказать")):
            loc = QA["Localization"].load(MOD, language)
            self.assertIn(condition, loc.resolve("HSM_VER_UI_ducal_treaty_recipients_tt"))
            self.assertIn(refusal, loc.resolve("HSM_VER_UI_ducal_treaty_reward_tt"))

    def test_owned_localizations_have_no_controller_meta(self):
        meta = re.compile(r"\b(?:AI|ИИ|players?|human)\b|игрок", re.I)
        for path in owned_locales():
            for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                if ":" in line and not line.lstrip().startswith("#"):
                    with self.subTest(path=path.name, line=number):
                        self.assertIsNone(meta.search(line.split(":", 1)[1]))

    def test_owned_files_have_no_trailing_whitespace(self):
        paths = [MOD / p for p in BASELINE["sha256"]] + owned_locales()
        paths += [Path(__file__).with_name(name) for name in (
            "Test-VereniaNativeUI.py", "Test-VereniaFocusUI.py", "Test-VereniaAvian.py",
            "Test-VereniaRoutes.py", "Test-VereniaZypressen.py", "verenia-native-ui-baseline.json",
        )]
        for path in paths:
            for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                with self.subTest(path=path.name, line=number):
                    self.assertEqual(line, line.rstrip())


if __name__ == "__main__":
    unittest.main()
