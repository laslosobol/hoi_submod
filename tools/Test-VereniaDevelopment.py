"""Execute domestic rewards against the installed EaW development effects.

Run with Python -B -X utf8. --eaw and --game override the local installs.
This strict, scoped script interpreter is not an HOI4 engine or tooltip renderer.
Idea on_add effects are outside its scope; production uses native swaps so those
engine callbacks (including electrical grids and research facilities) remain intact.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import re
import runpy
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod/HoISubmod"
ARGS = argparse.ArgumentParser()
ARGS.add_argument("--eaw", type=Path, default=Path("C:/shit/Steam/steamapps/workshop/content/394360/1826643372"))
ARGS.add_argument("--game", type=Path, default=Path("C:/shit/Steam/steamapps/common/Hearts of Iron IV"))
OPT, REST = ARGS.parse_known_args()
PARSER = runpy.run_path(str(Path(__file__).with_name("Test-VereniaFocusUI.py")))
read, walk = PARSER["read"], PARSER["walk"]
NATIVE_NAMES = {"decrease_poverty", "decrease_illiteracy", "increase_society_development",
                "increase_society_development_gradual", "increase_science_base"}
NATIVE = {n.key: n.children for n in read(OPT.eaw / "common/scripted_effects/EAW_misc_effect.txt") if n.key in NATIVE_NAMES}
EFFECTS = NATIVE | {n.key: n.children for n in read(MOD / "common/scripted_effects/HSM_VER_development.txt")}
EFFECTS.update({n.key: n.children for p in (MOD / "common/scripted_effects").glob("HSM_VER_spirit*.txt") for n in read(p)})
TRIGGERS = {n.key: n.children for p in (MOD / "common/scripted_triggers").glob("HSM_VER*.txt") for n in read(p)}
FOCUSES = {tag: {n.get("id"): n for n in read(MOD / f"common/national_focus/HSM_{tag}_development.txt")
                 if n.key == "shared_focus"} for tag in ("ERI", "EYR")}
DOMESTIC = {tag: {key: n for key, n in fs.items() if int(n.get("x")) < 6} for tag, fs in FOCUSES.items()}
FINAL_IDEAS = {"no_poverty", "modern_society", "no_lack_of_scientists", "proper_science_base"}
TECHS = {"electronic_mechanical_engineering", "basic_machine_tools", "construction1", "construction2"}
POVERTY = ["poverty", "poverty1", "poverty2", "poverty3", "poverty4", "poverty5", "no_poverty"]
LITERACY = ["lack_of_scientists", "lack_of_scientists1", "lack_of_scientists2", "lack_of_scientists3", "no_lack_of_scientists"]
SCIENCE = ["poor_science_base", "better_science_base", "big_science_base", "proper_science_base"]
SOCIETY = ["tribal_society", "tribal_society2", "tribal_society3", "tribal_society4", "agrarian_society",
           "agrarian_society2", "agrarian_society3", "agrarian_society4", "agrarian_society5", "agrarian_society6",
           "pre_industrial_society", "pre_industrial_society1", "pre_industrial_society2", "pre_industrial_society3",
           "outdated_industry", "outdated_industry2", "modern_society"]


@dataclass
class State:
    sid: str
    owner: str
    controller: str
    core: bool = True
    slots: int = 30
    buildings: dict = field(default_factory=lambda: {"industrial_complex": 4, "arms_factory": 2, "infrastructure": 2})

    def factories(self):
        return sum(self.buildings.get(k, 0) for k in ("industrial_complex", "arms_factory", "dockyard"))


def compare(value, op, expected):
    return {"=": value == expected, "<": value < expected, ">": value > expected,
            "<=": value <= expected, ">=": value >= expected}[op]


class World:
    def __init__(self, tag="ERI", worst=False, society="tribal_society"):
        self.tag = tag
        history = read(OPT.eaw / f"history/countries/{tag} - House{'Erie' if tag == 'ERI' else 'Eyrie'}.txt")
        self.ideas = {idea.key for n in history if n.key == "add_ideas" for idea in n.children}
        self.slots = int(next(n.value for n in history if n.key == "set_research_slots"))
        if worst:
            self.ideas = {"poverty", "lack_of_scientists", "poor_science_base", society}
        self.flags, self.completed, self.techs = set(), set(), set(TECHS)
        self.states = [State(s, tag, tag) for s in (("401", "500") if tag == "ERI" else ("391", "400"))]
        self.political_power, self.stability, self.bonuses = 0, 0, []
        # These sources must never satisfy an owned-factory requirement.
        self.trade_factories, self.subject_factories = 0, 0

    def check(self, nodes, scope=None):
        for n in nodes:
            k, v = n.key, n.value
            if k in TRIGGERS:
                ok = self.check(TRIGGERS[k], scope) == (v == "yes")
            elif k in ("tag", "original_tag"):
                ok = v == self.tag
            elif k == "exists":
                ok = v == "yes"
            elif k == "OR":
                ok = any(self.check((c,), scope) for c in n.children)
            elif k == "NOT":
                ok = not any(self.check((c,), scope) for c in n.children)
            elif k in ("AND", "custom_trigger_tooltip", "hidden_trigger"):
                ok = self.check(n.children, scope)
            elif k == "tooltip":
                continue
            elif k == "has_idea":
                ok = v in self.ideas
            elif k == "has_country_flag":
                ok = v in self.flags
            elif k == "has_completed_focus":
                ok = v in self.completed
            elif k == "has_tech":
                ok = v in self.techs
            elif k == "amount_research_slots":
                ok = compare(self.slots, n.op, int(v))
            elif k == "num_of_owned_factories":
                ok = compare(sum(s.factories() for s in self.states if s.owner == self.tag), n.op, int(v))
            elif k == "any_owned_state":
                ok = any(self.check(n.children, s) for s in self.states if s.owner == self.tag)
            elif k == "is_core_of":
                assert v == "ROOT"
                ok = scope.core
            elif k == "is_fully_controlled_by":
                assert v == "ROOT"
                ok = scope.controller == self.tag
            elif k == "state":
                ok = scope.sid == v
            elif k == "infrastructure":
                ok = compare(scope.buildings[k], n.op, int(v))
            elif k == "free_building_slots":
                size = n.all("size")[0]
                ok = compare(scope.slots - scope.factories(), size.op, int(size.value))
            else:
                raise AssertionError(f"Unsupported trigger: {k}")
            if not ok:
                return False
        return True

    def run(self, nodes, scope=None):
        chain_taken = False
        for n in nodes:
            k, v = n.key, n.value
            if k in ("if", "else_if", "else"):
                if k == "if":
                    chain_taken = False
                if not chain_taken and (k == "else" or self.check(n.get("limit", ()), scope)):
                    self.run(tuple(c for c in n.children if c.key != "limit"), scope)
                    chain_taken = True
            elif k in EFFECTS:
                self.run(EFFECTS[k], scope)
            elif k == "hidden_effect":
                self.run(n.children, scope)
            elif k in ("custom_effect_tooltip", "effect_tooltip", "show_ideas_tooltip"):
                continue
            elif k == "set_country_flag":
                self.flags.add(v)
            elif k == "add_ideas":
                self.ideas.add(v)
            elif k == "remove_ideas":
                self.ideas.discard(v)
            elif k == "clr_country_flag":
                self.flags.discard(v)
            elif k == "swap_ideas":
                self.ideas.discard(n.get("remove_idea"))
                self.ideas.add(n.get("add_idea"))
            elif k == "add_research_slot":
                self.slots += int(v)
            elif k == "add_political_power":
                self.political_power += int(v)
            elif k == "add_stability":
                self.stability += float(v)
            elif k == "add_tech_bonus":
                self.bonuses.append(tuple((c.key, c.value) for c in n.children))
            elif k in ("random_owned_state", "every_owned_state"):
                candidates = [s for s in self.states if s.owner == self.tag and self.check(n.get("limit", ()), s)]
                for s in candidates[:1] if k == "random_owned_state" else candidates:
                    self.run(tuple(c for c in n.children if c.key != "limit"), s)
            elif k == "add_extra_state_shared_building_slots":
                scope.slots += int(v)
            elif k == "add_building_construction":
                assert n.get("instant_build") == "yes"
                building = n.get("type")
                scope.buildings[building] = scope.buildings.get(building, 0) + int(n.get("level"))
            else:
                raise AssertionError(f"Unsupported effect: {k}")

    def effect(self, key):
        self.run(EFFECTS[key])

    def reward(self, key):
        self.run(DOMESTIC[self.tag][key].get("completion_reward"))

    def complete(self, key):
        f = DOMESTIC[self.tag][key]
        assert key not in self.completed, key
        assert all(any(n.value in self.completed for n in p.children) for p in f.all("prerequisite")), key
        assert self.check(f.get("available", ())), key
        self.completed.add(key)
        self.reward(key)

    def finish(self):
        pending = set(DOMESTIC[self.tag]) - self.completed
        while pending:
            ready = [k for k in pending if all(any(c.value in self.completed for c in p.children)
                     for p in DOMESTIC[self.tag][k].all("prerequisite"))]
            assert ready, f"Unreachable focuses: {pending}"
            for k in sorted(ready):
                self.complete(k)
                pending.remove(k)

    def daily(self):
        hooks = read(MOD / "common/on_actions/HSM_VER_development.txt")[0]
        self.run(hooks.all("on_daily_" + self.tag)[0].get("effect"))


class DevelopmentTests(unittest.TestCase):
    def test_native_contract_and_reported_failure(self):
        self.assertEqual(set(NATIVE), NATIVE_NAMES)
        w = World("EYR")
        self.assertIn("poverty", w.ideas)
        self.assertIn("pre_industrial_society", w.ideas)
        self.assertEqual(w.slots, 3)
        for _ in range(2):
            w.effect("decrease_poverty")
            w.effect("increase_society_development_gradual")
        self.assertIn("poverty2", w.ideas)
        self.assertIn("pre_industrial_society2", w.ideas)
        for _ in range(4):
            w.effect("increase_society_development_gradual")
        self.assertIn("modern_society", w.ideas)
        native_decisions = read(OPT.eaw / "common/decisions/_society_advancement_decisions.txt")
        flags = {n.value for n in walk(native_decisions) if n.key == "has_country_flag"}
        self.assertTrue({"can_improve_poverty", "can_improve_illiteracy", "can_improve_society_development"} <= flags)
        docs = (OPT.game / "documentation/triggers_documentation.md").read_text(encoding="utf-8-sig")
        self.assertIn("## num_of_owned_factories", docs)

    def test_actual_and_worst_starts_finish_without_generic_decisions(self):
        for tag in DOMESTIC:
            for society in (None, "tribal_society", "communal_society", "agrarian_society", "pre_industrial_society"):
                with self.subTest(tag=tag, society=society):
                    w = World(tag, worst=society is not None, society=society)
                    w.daily()
                    w.finish()
                    self.assertTrue(FINAL_IDEAS <= w.ideas)
                    self.assertEqual(w.slots, 5)

    def test_early_milestones_do_not_finish_development(self):
        for tag in DOMESTIC:
            w = World(tag, worst=True)
            for key, f in DOMESTIC[tag].items():
                if int(f.get("y")) <= 1:
                    w.complete(key)
            self.assertIn("poverty1", w.ideas)
            self.assertIn("lack_of_scientists1", w.ideas)
            self.assertEqual(w.slots, 3)
            self.assertFalse(FINAL_IDEAS & w.ideas)

    def test_every_floor_is_monotone_and_idempotent_at_every_native_tier(self):
        for levels in (POVERTY, LITERACY, SCIENCE, SOCIETY):
            for target_index, target in enumerate(levels):
                effect = "HSM_VER_DEV_ensure_" + target
                if effect not in EFFECTS:
                    continue
                for start_index, start in enumerate(levels):
                    with self.subTest(target=target, start=start):
                        w = World()
                        w.ideas = {start}
                        w.effect(effect)
                        self.assertEqual(w.ideas, {levels[max(start_index, target_index)]})
                        after = copy.deepcopy(w.__dict__)
                        w.effect(effect)
                        self.assertEqual(w.__dict__, after)

    def test_advanced_and_special_societies_keep_earned_progress(self):
        for tag in DOMESTIC:
            for society in ("modern_society", "SON_post_scarcity_society", "clockwerk_industry"):
                for slots in (3, 4, 5, 6):
                    w = World(tag)
                    w.ideas = FINAL_IDEAS - {"modern_society"} | {society}
                    w.slots = slots
                    w.finish()
                    self.assertTrue(FINAL_IDEAS - {"modern_society"} | {society} <= w.ideas)
                    self.assertEqual(w.slots, max(5, slots))
                    if society != "modern_society":
                        self.assertNotIn("modern_society", w.ideas)

    def test_complete_rewards_are_safe_to_replay(self):
        for tag in DOMESTIC:
            w = World(tag, worst=True)
            w.finish()
            before = copy.deepcopy(w.__dict__)
            for key in DOMESTIC[tag]:
                w.reward(key)
            self.assertEqual(w.__dict__, before)

    def test_schooling_and_insurance_retain_rewards_after_native_development_is_complete(self):
        for tag in DOMESTIC:
            stages = ["universal_schooling", "social_insurance"]
            if tag == "EYR":
                stages.append("teacher_training")
            for stage in stages:
                with self.subTest(tag=tag, stage=stage):
                    w = World(tag)
                    w.ideas = set(FINAL_IDEAS)
                    key = f"HSM_{tag}_{stage}"
                    w.reward(key)
                    self.assertEqual(w.ideas, FINAL_IDEAS)
                    self.assertEqual(len(w.bonuses), 1)
                    before = copy.deepcopy(w.__dict__)
                    w.reward(key)
                    self.assertEqual(w.__dict__, before)

    def test_owned_factory_and_technology_boundaries(self):
        for tag, focuses in DOMESTIC.items():
            for key, f in focuses.items():
                gates = [n for n in walk(f.get("available", ())) if n.key == "num_of_owned_factories"]
                for gate in gates:
                    w = World(tag)
                    w.states = [State("1", tag, tag, buildings={"industrial_complex": int(gate.value)})]
                    w.trade_factories = w.subject_factories = 100
                    w.states.append(State("2", "GRI", tag, buildings={"arms_factory": 100}))
                    self.assertFalse(w.check(f.get("available")), key)
                    w.states[0].buildings["industrial_complex"] += 1
                    self.assertTrue(w.check(f.get("available")), key)
                    for tech in (n.value for n in walk(f.get("available")) if n.key == "has_tech"):
                        w.techs.remove(tech)
                        self.assertFalse(w.check(f.get("available")), (key, tech))
                        w.techs.add(tech)

    def test_factories_only_use_owned_controlled_cores_with_room(self):
        for tag, name in (("ERI", "civilian_industry"), ("EYR", "rural_processing")):
            key = f"HSM_{tag}_{name}"
            for failure in ("foreign", "occupied", "noncore", "full"):
                w = World(tag)
                w.states = [State("1", tag, tag)]
                s = w.states[0]
                if failure == "foreign":
                    s.owner = "GRI"
                elif failure == "occupied":
                    s.controller = "GRI"
                elif failure == "noncore":
                    s.core = False
                else:
                    s.slots = s.factories()
                before = copy.deepcopy(w.states)
                self.assertFalse(w.check(DOMESTIC[tag][key].get("available")))
                w.reward(key)
                self.assertEqual(w.states, before)
            w = World(tag)
            before = sum(s.factories() for s in w.states)
            w.reward(key)
            self.assertEqual(sum(s.factories() for s in w.states), before + 1)

    def test_old_completed_tree_migrates_without_repaying_and_finishes(self):
        for tag in DOMESTIC:
            w = World(tag)
            old = [k for k, f in DOMESTIC[tag].items() if int(f.get("y")) <= 6
                   and not k.endswith(("public_libraries", "district_housing"))
                   and not (tag == "EYR" and k.endswith("teacher_training"))]
            w.completed.update(old)
            w.slots = 5
            for _ in range(2):
                w.effect("decrease_poverty")
                w.effect("increase_society_development_gradual")
                w.effect("increase_science_base")
            w.daily()
            self.assertIn("proper_science_base", w.ideas)
            self.assertIn("pre_industrial_society2", w.ideas)
            self.assertNotIn("no_poverty", w.ideas)
            after = copy.deepcopy(w.__dict__)
            w.daily()
            for k in old:
                w.reward(k)
            self.assertEqual(w.__dict__, after)
            self.assertEqual((w.political_power, w.bonuses), (0, []))
            w.finish()
            self.assertTrue(FINAL_IDEAS <= w.ideas)
            self.assertEqual(w.slots, 5)

    def test_partial_migration_does_not_award_unearned_progress(self):
        for tag, name in (("ERI", "restore_public_services"), ("EYR", "fair_grain_markets")):
            w = World(tag, worst=True)
            w.completed.add(f"HSM_{tag}_{name}")
            w.effect("decrease_poverty")
            ideas = set(w.ideas)
            w.daily()
            self.assertEqual(w.ideas, ideas)
            self.assertEqual(w.slots, 3)
            self.assertIn("can_improve_poverty", w.flags)
            self.assertNotIn("can_improve_society_development", w.flags)
            self.assertNotIn("proper_science_base_unlocked", w.flags)

    def test_new_game_migration_never_rewards_or_reapplies_later_laws(self):
        w = World(worst=True)
        before = copy.deepcopy(w.__dict__)
        w.daily()
        before["flags"].add("HSM_VER_DEV_migrated_v1")
        self.assertEqual(w.__dict__, before)
        w.finish()
        w.ideas.remove("no_poverty")
        w.ideas.add("poverty5")
        after = copy.deepcopy(w.__dict__)
        w.daily()
        self.assertEqual(w.__dict__, after)

    def test_ui_localization_coordinates_and_military_preservation(self):
        hashes = {"ERI": "cf431de8024836e62bee7368496b6d2a34eeac42077c2ddad4d41eb7a3c82ee9",
                  "EYR": "32694ada25ebe0055ffb86508bfb04cc6eb60a6c03e68dc0528379b063666107"}
        for tag, root in (("ERI", "army_for_a_country"), ("EYR", "defensive_service")):
            path = MOD / f"common/national_focus/HSM_{tag}_development.txt"
            suffix = path.read_text().split(f"shared_focus = {{\n\tid = HSM_{tag}_{root}")[1]
            # Compare the pre-union operations, allowing only the ledger routing.
            # Keep the original hashes: changed modifiers/rewards still fail.
            build = runpy.run_path(str(Path(__file__).with_name("Build-VereniaSpirit.py")))
            whole = "shared_focus = {\n\tid = HSM_" + tag + "_" + root + suffix
            edits = []
            def original(nodes):
                skip = False
                for i, n in enumerate(nodes):
                    if skip:
                        skip = False
                        continue
                    if n.key == "effect_tooltip" and len(n.children) == 1 and n.children[0].key == "swap_ideas":
                        following = nodes[i + 1]
                        self.assertEqual(following.key, "hidden_effect")
                        swap = n.children[0]
                        edits.append((n.start, following.end, whole[swap.start:swap.end]))
                        skip = True
                    elif n.key.startswith(("HSM_VER_SP_add_", "HSM_VER_SP_remove_", "HSM_VER_SP_has_")):
                        action, name = n.key.removeprefix("HSM_VER_SP_").split("_", 1)
                        self.assertIn(name, build["components"]())
                        key = {"add": "add_ideas", "remove": "remove_ideas", "has": "has_idea"}[action]
                        edits.append((n.start, n.end, f"{key} = {name}"))
                    else:
                        original(n.children)
            original(build["spans"](whole))
            for start, end, replacement in reversed(edits):
                whole = whole[:start] + replacement + whole[end:]
            original_suffix = whole.split(f"shared_focus = {{\n\tid = HSM_{tag}_{root}")[1]
            self.assertEqual(hashlib.sha256(original_suffix.encode()).hexdigest(), hashes[tag])
            coordinates = [(f.get("x"), f.get("y")) for f in FOCUSES[tag].values()]
            self.assertEqual(len(coordinates), len(set(coordinates)))
            self.assertTrue(all(int(x) <= 9 for x, y in coordinates))
            nodes = tuple(n for f in DOMESTIC[tag].values() for n in f.children)
            for n in walk(nodes):
                self.assertNotIn(n.key, {"set_variable", "add_to_variable", "num_of_factories", "num_of_civilian_factories"})
                if n.key == "custom_trigger_tooltip":
                    self.assertFalse(any(c.key == "has_country_flag" and str(c.value).endswith("_paid")
                                         for c in walk(n.children)), "Paid bookkeeping must be hidden")
                if n.key == "hidden_effect":
                    self.assertFalse({c.key for c in walk(n.children)} & {"add_tech_bonus", "add_research_slot", *NATIVE_NAMES})
            for lang in ("english", "russian"):
                loc_paths = [MOD / f"localisation/{lang}/HSM_{tag}_development_l_{lang}.yml",
                             MOD / f"localisation/{lang}/HSM_VER_focus_ui_domestic_l_{lang}.yml"]
                loc = {}
                for loc_path in loc_paths:
                    self.assertTrue(loc_path.read_bytes().startswith(b"\xef\xbb\xbf"), loc_path)
                    for line in loc_path.read_text(encoding="utf-8-sig").splitlines()[1:]:
                        if not line.strip() or line.lstrip().startswith("#"):
                            continue
                        match = PARSER["LOC_LINE"].fullmatch(line)
                        self.assertIsNotNone(match, line)
                        self.assertNotIn(match[1], loc)
                        loc[match[1]] = match[2]
                needed = {k for key in DOMESTIC[tag] for k in (key, key + "_desc")}
                needed.update(n.value for n in walk(nodes) if n.key in {"custom_effect_tooltip", "tooltip", "name"})
                self.assertFalse(needed - loc.keys(), needed - loc.keys())
                for key in DOMESTIC[tag]:
                    self.assertFalse(re.search(r"\d|\bAI\b|script|counter", loc[key + "_desc"], re.I), key)

    def test_domestic_hover_budget_with_installed_game_and_eaw(self):
        options = SimpleNamespace(game=OPT.game, eaw=OPT.eaw, line_width=72,
                                  max_condition_lines=18, max_effect_lines=18,
                                  max_total_lines=30, max_summary_chars=600)
        paths = [MOD / f"common/national_focus/HSM_{tag}_development.txt" for tag in DOMESTIC]
        errors, counts, budgets = PARSER["audit"](MOD, paths, options)
        self.assertFalse(errors, "\n".join(errors))
        self.assertEqual(counts["focuses"], sum(map(len, FOCUSES.values())))
        self.assertTrue(budgets)


if __name__ == "__main__":
    unittest.main(argv=[__file__, *REST], verbosity=2)
