"""Standalone identity-branch contracts and production-script fixtures.

Run python -B -X utf8 tools/Test-VereniaIdentity.py [-q] [--eaw PATH] [--game PATH].
Reuses the repository parser and evaluates the installed native literacy effect.
These fixtures do not emulate HOI4 or require the parent trees to import the roots.
"""
from __future__ import annotations

import copy
import importlib.util
import re
import runpy
import sys
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "verenia_identity_parser", Path(__file__).with_name("Test-Verenia.py")
)
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)
ROM = runpy.run_path(str(Path(__file__).with_name("Test-VereniaRomance.py")))

FOCUS_PATH = BASE.MOD / "common/national_focus/HSM_VER_identity.txt"
IDEA_PATH = BASE.MOD / "common/ideas/HSM_VER_identity.txt"
FOCUS_NODES = BASE.read(FOCUS_PATH)
FOCUSES = {n.get("id"): n for n in FOCUS_NODES}
IDEAS = {n.key: n for n in BASE.read(IDEA_PATH)[0].get("country")}
PREFIX = "HSM_VER_ID_"
ROOTS = {tag: PREFIX + tag + "_language_question" for tag in ("ERI", "EYR")}
LITERACY = (
    "lack_of_scientists", "lack_of_scientists1", "lack_of_scientists2",
    "lack_of_scientists3", "no_lack_of_scientists",
)
ROUTES = {
    "ERI": (
        ("aquileian_classrooms", "translated_journals", "local_histories", "public_scholarships"),
        ("two_living_languages", "district_teacher_colleges", "local_histories", "public_scholarships"),
    ),
    "EYR": (
        ("herzland_classrooms", "technical_lexicon", "parish_archives", "civic_fellowships"),
        ("two_living_languages", "interpreters_college", "parish_archives", "civic_fellowships"),
    ),
}
FLAGS = {n.value for n in BASE.walk(FOCUS_NODES) if n.key == "set_country_flag"}
ELIGIBLE = "HSM_VER_ID_eligible_house"
ELIGIBLE_TOOLTIP = "HSM_VER_ID_eligible_tt"


def route(tag, choice):
    return [ROOTS[tag]] + [PREFIX + tag + "_" + suffix for suffix in ROUTES[tag][choice]]


def refs(focus, field):
    return {n.value for block in focus.all(field) for n in block.all("focus")}


class IdentityWorld(BASE.World):
    def __init__(self):
        super().__init__()
        self.countries["D01"] = BASE.Country("D01", leader="ERI_duke_vincent_erie")
        for country in self.countries.values():
            country.government = "neutrality"
            country.stability = 0.5
            country.bonuses = []
            country.ideas.add(LITERACY[0])
        native = BASE.read(BASE.OPT.eaw / "common/scripted_effects/EAW_misc_effect.txt")
        self.effects["decrease_illiteracy"] = next(
            n.children for n in native if n.key == "decrease_illiteracy"
        )

    def check(self, nodes, tag="ERI"):
        for node in nodes:
            if node.key == "has_government":
                ok = self.countries[tag].government == node.value
            else:
                ok = super().check([node], tag)
            if not ok:
                return False
        return True

    def run(self, nodes, tag="ERI"):
        pending = []
        for node in nodes:
            if node.key not in ("add_stability", "add_tech_bonus", "swap_ideas"):
                pending.append(node)
                continue
            # Preserve contiguous if/else_if chains in the base interpreter.
            super().run(pending, tag)
            pending = []
            country = self.countries[tag]
            if node.key == "add_stability":
                country.stability += float(node.value)
            elif node.key == "add_tech_bonus":
                country.bonuses.append(copy.deepcopy(node.children))
            else:
                country.ideas.discard(node.get("remove_idea"))
                country.ideas.add(node.get("add_idea"))
        super().run(pending, tag)

    def available(self, focus_id, tag):
        focus = FOCUSES[focus_id]
        done = self.countries[tag].focuses
        return (
            focus_id not in done
            and self.check(focus.get("allow_branch", []), tag)
            and self.check(focus.get("available", []), tag)
            and not refs(focus, "mutually_exclusive") & done
            and all(any(n.value in done for n in block.all("focus"))
                    for block in focus.all("prerequisite"))
        )

    def reward(self, focus_id, tag):
        self.root = tag
        self.run(FOCUSES[focus_id].get("completion_reward"), tag)

    def complete(self, focus_id, tag):
        assert self.available(focus_id, tag), (tag, focus_id)
        self.reward(focus_id, tag)
        self.countries[tag].focuses.add(focus_id)

    def snapshot(self):
        # vars includes fixture-only rewards added to the shared Country class.
        return copy.deepcopy({tag: vars(country) for tag, country in self.countries.items()})


class IdentityRomanceWorld(ROM["RomanceWorld"]):
    """Execute real union/romance transitions and identity rewards together."""

    def __init__(self):
        super().__init__()
        native = BASE.read(BASE.OPT.eaw / "common/scripted_effects/EAW_misc_effect.txt")
        self.effects["decrease_illiteracy"] = next(
            n.children for n in native if n.key == "decrease_illiteracy"
        )
        for country in self.countries.values():
            country.ideas.add(LITERACY[0])

    def run(self, nodes, tag="ERI"):
        pending = []
        for node in nodes:
            if node.key != "swap_ideas":
                pending.append(node)
                continue
            super().run(pending, tag)
            pending = []
            country = self.countries[tag]
            country.ideas.discard(node.get("remove_idea"))
            country.ideas.add(node.get("add_idea"))
        super().run(pending, tag)

    # Keep the union interpreter's available/reward/complete methods intact.
    identity_available = IdentityWorld.available
    identity_reward = IdentityWorld.reward
    snapshot = IdentityWorld.snapshot

    def identity_complete(self, focus_id, tag):
        assert self.identity_available(focus_id, tag), (tag, focus_id)
        self.identity_reward(focus_id, tag)
        self.countries[tag].focuses.add(focus_id)

    def before_handover(self, host, legacy=False):
        if legacy:
            self.begin(host, avian="unsigned")
            self.found(host)
        else:
            self.story(host)
            self.scene(1, host)
            self.convention(host)
            self.scene(2, host)
            self.draft(host)
            self.scene(3, host)
            self.replies(host, final=True)
            self.complete(host, "constitutional_act")
        assert self.countries[host].leader == ROM["DUKES"][host]
        return self


class VereniaIdentity(unittest.TestCase):
    def test_standalone_roots_graph_and_layout(self):
        self.assertEqual(len(FOCUS_NODES), len(FOCUSES))
        self.assertTrue(all(n.key == "shared_focus" for n in FOCUS_NODES))
        self.assertEqual(set(ROOTS.values()), {key for key, n in FOCUSES.items() if not n.all("prerequisite")})
        for tag, root in ROOTS.items():
            nodes = {key: n for key, n in FOCUSES.items() if key.startswith(PREFIX + tag + "_")}
            self.assertEqual(7, len(nodes))
            self.assertEqual(("64", "0"), (nodes[root].get("x"), nodes[root].get("y")))
            self.assertEqual(tag, BASE.Node("allow_branch", "=", nodes[root].get("allow_branch")).get("tag"))
            positions = set()
            for key, node in nodes.items():
                pos = (int(node.get("x")), int(node.get("y")))
                self.assertIn(pos[0], (62, 64, 66))
                self.assertTrue(0 <= pos[1] <= 5)
                self.assertNotIn(pos, positions)
                positions.add(pos)
                self.assertEqual("yes", node.get("cancel_if_invalid"))
                self.assertNotEqual("yes", node.get("available_if_capitulated"))
                self.assertNotEqual("yes", node.get("repeatable"))
                for parent in refs(node, "prerequisite"):
                    self.assertIn(parent, nodes)
                    self.assertLess(int(nodes[parent].get("y")), pos[1])
                for other in refs(node, "mutually_exclusive"):
                    self.assertIn(other, nodes)
                    self.assertIn(key, refs(nodes[other], "mutually_exclusive"))
            for choice, x in enumerate(("62", "66")):
                self.assertEqual(x, nodes[route(tag, choice)[1]].get("x"))
                self.assertEqual(x, nodes[route(tag, choice)[2]].get("x"))

    def test_native_reference_and_ruling_government_contract(self):
        native = {n.get("id"): n for n in BASE.read(BASE.MOD / "common/national_focus/AVI.txt") if n.key == "shared_focus"}
        for key in ("language_problem", "choose_aquelian", "choose_griffish", "dual_hegemony"):
            self.assertIn(key, native)
        for key in ("choose_aquelian", "choose_griffish", "dual_hegemony"):
            self.assertIn("decrease_illiteracy", {n.key for n in BASE.walk(native[key].get("completion_reward"))})
        trigger = BASE.definitions("scripted_triggers")["HSM_VER_FORCE_eligible_house"]
        leaders = [n for n in BASE.walk(trigger) if n.key == "has_country_leader"]
        self.assertTrue(leaders)
        self.assertTrue(all(n.get("ruling_only") == "yes" for n in leaders))

    def test_localisation_bom_and_exact_key_coverage(self):
        required = {key + suffix for key in FOCUSES.keys() | IDEAS.keys() for suffix in ("", "_desc")}
        required.update(n.get("name") for n in BASE.walk(FOCUS_NODES) if n.key == "add_tech_bonus")
        required.update(FLAGS)
        required.add(ELIGIBLE_TOOLTIP)
        for language in ("english", "russian"):
            path = BASE.MOD / "localisation" / language / f"HSM_VER_identity_l_{language}.yml"
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"), path)
            lines = path.read_text(encoding="utf-8-sig").splitlines()
            self.assertEqual("l_" + language + ":", lines[0])
            found = {}
            for line in lines[1:]:
                if not line.strip():
                    continue
                match = re.fullmatch(r' ([^\s:]+):0 "([^"\n]+)"', line)
                self.assertIsNotNone(match, line)
                key, value = match.groups()
                self.assertNotIn(key, found)
                found[key] = value
                if language == "russian":
                    self.assertRegex(value, r"[\u0400-\u04ff]", key)
            self.assertEqual(required, found.keys())

    def test_existing_assets_and_technology_categories(self):
        sprites, categories = set(), set()
        for root in (BASE.OPT.game, BASE.OPT.eaw, BASE.MOD):
            for path in (root / "interface").rglob("*.gfx"):
                sprites.update(re.findall(r'\bname\s*=\s*"?(GFX_[^\s"}]+)', path.read_text(encoding="utf-8-sig", errors="replace")))
            for path in (root / "common/technology_tags").glob("*.txt"):
                categories.update(n.key for n in BASE.walk(BASE.read(path)) if not n.op)
        self.assertTrue(sprites)
        self.assertTrue(categories)
        for node in FOCUS_NODES:
            self.assertIn(node.get("icon"), sprites)
        for node in IDEAS.values():
            self.assertIn("GFX_idea_" + node.get("picture"), sprites)
        for node in BASE.walk(FOCUS_NODES):
            if node.key == "add_tech_bonus":
                self.assertTrue(node.all("category"))
                self.assertTrue({n.value for n in node.all("category")} <= categories)

    def test_domestic_effects_engine_keywords_and_flags(self):
        docs = BASE.OPT.game / "documentation"
        effects = (docs / "effects_documentation.md").read_text(encoding="utf-8-sig")
        triggers = (docs / "triggers_documentation.md").read_text(encoding="utf-8-sig")
        modifiers = (docs / "modifiers_documentation.md").read_text(encoding="utf-8-sig")
        allowed = {"if", "limit", "tag", ELIGIBLE, "has_country_flag", "NOT", "OR",
                   "set_country_flag", "add_political_power", "decrease_illiteracy", "add_ideas", "add_tech_bonus",
                   "name", "bonus", "uses", "category", "add_stability",
                   "hidden_effect", "hidden_trigger", "custom_effect_tooltip", "show_ideas_tooltip"}
        allowed.update("HSM_VER_SP_add_" + key for key in IDEAS)
        for focus in FOCUSES.values():
            nodes = list(BASE.walk(focus.get("completion_reward")))
            self.assertTrue({n.key for n in nodes} <= allowed)
            for node in nodes:
                if node.key.startswith("add_") or node.key in {"set_country_flag", "hidden_effect", "custom_effect_tooltip", "show_ideas_tooltip"}:
                    self.assertIn("## " + node.key + "\n", effects)
                if node.key == "hidden_trigger":
                    self.assertIn("## hidden_trigger\n", triggers)
                if node.key == "set_country_flag":
                    if isinstance(node.value, list):
                        self.assertEqual("1", node.get("value"))
                        self.assertTrue(node.get("days"))
                    else:
                        self.assertTrue(node.value.startswith(PREFIX))
                self.assertNotIn(node.op, (">=", "<=", "!="))
        for idea in IDEAS.values():
            for modifier in idea.get("modifier"):
                self.assertIn("## " + modifier.key + "\n", modifiers)

    def test_all_four_paths_have_useful_local_rewards(self):
        for tag in ROOTS:
            for choice in (0, 1):
                with self.subTest(tag=tag, choice=choice):
                    world = IdentityWorld()
                    before = world.snapshot()
                    for focus in route(tag, choice):
                        world.complete(focus, tag)
                    country = world.countries[tag]
                    expected_policy = "bilingual" if choice else {"ERI": "aquileian", "EYR": "herzland"}[tag]
                    self.assertEqual({PREFIX + expected_policy + "_curriculum", PREFIX + "public_endowment"}, country.ideas & IDEAS.keys())
                    self.assertEqual({LITERACY[1]}, country.ideas & set(LITERACY))
                    self.assertEqual(50, country.political_power)
                    self.assertAlmostEqual(0.53, country.stability)
                    bonus = BASE.Node("bonus", "=", country.bonuses[0])
                    self.assertEqual("0.5", bonus.get("bonus"))
                    self.assertEqual("2", bonus.get("uses"))
                    expected_categories = {"electronics", "industry"} if choice else {"electronics" if tag == "ERI" else "industry"}
                    self.assertEqual(expected_categories, {n.value for n in bonus.all("category")})
                    for other in world.countries.keys() - {tag}:
                        self.assertEqual(before[other], world.snapshot()[other])

    def test_native_literacy_advances_exactly_once_at_every_level(self):
        for tag in ROOTS:
            for choice in (0, 1):
                for level, idea in enumerate(LITERACY):
                    world = IdentityWorld()
                    country = world.countries[tag]
                    country.ideas = {idea}
                    world.complete(ROOTS[tag], tag)
                    world.complete(route(tag, choice)[1], tag)
                    self.assertEqual({LITERACY[min(level + 1, len(LITERACY) - 1)]}, country.ideas & set(LITERACY))

    def test_mutually_exclusive_choices_cannot_stack_or_switch(self):
        for tag in ROOTS:
            for choice in (0, 1):
                world = IdentityWorld()
                world.complete(ROOTS[tag], tag)
                self.assertTrue(world.available(route(tag, 0)[1], tag))
                self.assertTrue(world.available(route(tag, 1)[1], tag))
                world.complete(route(tag, choice)[1], tag)
                other = route(tag, 1 - choice)
                before = world.snapshot()
                for focus in other[1:3]:
                    self.assertFalse(world.available(focus, tag))
                    world.reward(focus, tag)
                self.assertEqual(before, world.snapshot())

    def test_all_rewards_are_idempotent(self):
        for tag in ROOTS:
            for choice in (0, 1):
                world = IdentityWorld()
                for focus in route(tag, choice):
                    world.complete(focus, tag)
                    before = world.snapshot()
                    world.reward(focus, tag)
                    self.assertEqual(before, world.snapshot(), focus)

    def test_rewards_cannot_skip_their_preceding_institutions(self):
        for tag in ROOTS:
            for focus in (key for key in FOCUSES if key.startswith(PREFIX + tag + "_") and key != ROOTS[tag]):
                world = IdentityWorld()
                before = world.snapshot()
                self.assertFalse(world.available(focus, tag))
                world.reward(focus, tag)
                self.assertEqual(before, world.snapshot(), focus)

    def test_foreign_tags_cannot_gain_either_house_branch(self):
        for owner in ROOTS:
            for tag in ("ERI", "EYR", "AVI", "GRI", "D01"):
                if owner == tag:
                    continue
                world = IdentityWorld()
                for focus in route(owner, 0) + route(owner, 1):
                    grants = {n.value for n in BASE.walk(FOCUSES[focus].get("completion_reward")) if n.key == "set_country_flag"}
                    world.countries[tag].flags = FLAGS - grants
                    world.countries[tag].focuses = set(FOCUSES) - {focus} - refs(FOCUSES[focus], "mutually_exclusive")
                    before = world.snapshot()
                    self.assertFalse(world.available(focus, tag))
                    world.reward(focus, tag)
                    self.assertEqual(before, world.snapshot(), (tag, focus))

    def test_government_loss_blocks_in_flight_rewards(self):
        for tag in ROOTS:
            for choice in (0, 1):
                for stage, focus in enumerate(route(tag, choice)):
                    for attr, value in (("subject", True), ("capitulated", True), ("exists", False), ("leader", "other_ruler")):
                        world = IdentityWorld()
                        for earlier in route(tag, choice)[:stage]:
                            world.complete(earlier, tag)
                        self.assertTrue(world.available(focus, tag))
                        setattr(world.countries[tag], attr, value)
                        before = world.snapshot()
                        self.assertFalse(world.available(focus, tag))
                        world.reward(focus, tag)
                        self.assertEqual(before, world.snapshot(), (tag, focus, attr))

    def test_ideas_are_bound_to_the_actual_government_and_choice(self):
        for tag in ROOTS:
            for choice in (0, 1):
                world = IdentityWorld()
                for focus in route(tag, choice):
                    world.complete(focus, tag)
                for key in world.countries[tag].ideas & IDEAS.keys():
                    self.assertFalse(world.check(IDEAS[key].get("cancel"), tag))
                    self.assertEqual("no", BASE.Node("allowed_civil_war", "=", IDEAS[key].get("allowed_civil_war")).get("always"))
                    for attr, value in (("subject", True), ("capitulated", True), ("exists", False), ("leader", "other_ruler")):
                        previous = getattr(world.countries[tag], attr)
                        setattr(world.countries[tag], attr, value)
                        self.assertTrue(world.check(IDEAS[key].get("cancel"), tag))
                        setattr(world.countries[tag], attr, previous)
                    world.countries["D01"].flags = world.countries[tag].flags.copy()
                    self.assertTrue(world.check(IDEAS[key].get("cancel"), "D01"))

    def test_rival_choice_and_foreign_war_do_not_gate_domestic_education(self):
        world = IdentityWorld()
        for tag in ROOTS:
            world.countries[tag].war = True
            world.countries[tag].wars.add("GRI")
            for focus in route(tag, 1):
                world.complete(focus, tag)
        for tag in ROOTS:
            self.assertIn(PREFIX + tag + "_balanced", world.countries[tag].flags)
            self.assertFalse(world.countries[tag].faction)


class IdentityHandover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = {
            (tag, legacy): IdentityRomanceWorld().before_handover(tag, legacy)
            for tag in ROOTS for legacy in (False, True)
        }
        cls.crowned = {}
        for tag in ROOTS:
            world = copy.deepcopy(cls.before[tag, False])
            world.scene(4, tag)
            cls.crowned[tag] = world

    def assertIdentityBenefits(self, world, tag, choice):
        world.apply("HSM_VER_SP_refresh", tag)
        policy = "bilingual" if choice else {"ERI": "aquileian", "EYR": "herzland"}[tag]
        expected = {PREFIX + policy + "_curriculum", PREFIX + "public_endowment"}
        country = world.countries[tag]
        actual = {idea for idea in IDEAS if world.test("HSM_VER_SP_has_" + idea, tag)}
        self.assertEqual(expected, actual)
        for idea in expected:
            self.assertFalse(world.check(IDEAS[idea].get("cancel"), tag))
        spirit = ROM["GRO"]["SP"]
        self.assertIn(spirit["DYNAMIC"], country.dynamic_modifiers)
        spirit["LedgerAssertions"].assertValues(self, world, tag, spirit["owned"](country))
        before = world.snapshot()
        world.apply("HSM_VER_SP_refresh", tag)
        self.assertEqual(before, world.snapshot())

    def test_every_focus_checks_identity_government_on_start_and_reward(self):
        for focus_id, focus in FOCUSES.items():
            with self.subTest(focus=focus_id):
                tag = focus_id[len(PREFIX):][:3]
                for field in ("available", "completion_reward"):
                    nodes = list(BASE.walk(focus.get(field)))
                    self.assertEqual(["yes"], [n.value for n in nodes if n.key == ELIGIBLE])
                    self.assertNotIn("HSM_VER_FORCE_eligible_house", {n.key for n in nodes})
                    self.assertIn(tag, [n.value for n in nodes if n.key == "tag"])
                tooltips = [n.get("tooltip") for n in BASE.walk(focus.get("available"))
                            if n.key == "custom_trigger_tooltip"]
                self.assertIn(ELIGIBLE_TOOLTIP, tooltips)
                self.assertNotIn("HSM_VER_UI_DOM_eligible_tt", tooltips)

    def test_identity_extension_does_not_reopen_force_or_change_ducal_routes(self):
        for tag in ROOTS:
            world = self.crowned[tag]
            self.assertEqual(ROM["JOINT"], world.countries[tag].leader)
            self.assertTrue(world.test("HSM_VER_ROM_government", tag))
            self.assertTrue(world.test(ELIGIBLE, tag))
            self.assertFalse(world.test("HSM_VER_FORCE_eligible_house", tag))
            self.assertFalse(world.test("HSM_VER_FORCE_can_prepare", tag))
            # The old identity branch also served original dukes on military
            # routes. Only the new co-ruler alternative excludes those routes.
            duke = copy.deepcopy(self.before[tag, False])
            duke.countries[tag].flags.update({"HSM_VER_military_route", "HSM_VER_UNI_military"})
            self.assertTrue(duke.test(ELIGIBLE, tag))

    def test_both_policies_continue_at_every_handover_stage_and_cannot_repeat(self):
        for tag in ROOTS:
            for choice in (0, 1):
                path = route(tag, choice)
                for legacy in (False, True):
                    for completed in range(len(path) + 1):
                        with self.subTest(tag=tag, choice=choice, legacy=legacy, completed=completed):
                            world = copy.deepcopy(self.before[tag, legacy])
                            for focus in path[:completed]:
                                world.identity_complete(focus, tag)
                            if completed < len(path):
                                self.assertTrue(world.identity_available(path[completed], tag))
                            earned = world.countries[tag].flags & FLAGS
                            world.scene(4, tag)
                            self.assertEqual(ROM["JOINT"], world.countries[tag].leader)
                            self.assertEqual(earned, world.countries[tag].flags & FLAGS)
                            # Copying the fixture models a save/reload boundary.
                            world = copy.deepcopy(world)
                            for focus in path[:completed]:
                                before = world.snapshot()
                                world.identity_reward(focus, tag)
                                self.assertEqual(before, world.snapshot(), focus)
                            for focus in path[completed:]:
                                before = world.snapshot()
                                world.identity_complete(focus, tag)
                                country = world.countries[tag]
                                expected_power = 25 if focus in (path[0], path[3]) else 0
                                self.assertEqual(before[tag]["political_power"] + expected_power,
                                                 country.political_power)
                                expected_stability = 0.03 if focus == path[3] else 0
                                self.assertAlmostEqual(before[tag]["stability"] + expected_stability,
                                                       country.stability)
                                for other in before.keys() - {tag}:
                                    self.assertEqual(before[other], world.snapshot()[other])
                                after = world.snapshot()
                                world.identity_reward(focus, tag)
                                self.assertEqual(after, world.snapshot(), focus)
                            country = world.countries[tag]
                            self.assertTrue(set(path) <= country.focuses)
                            self.assertEqual({LITERACY[1]}, country.ideas & set(LITERACY))
                            expected_bonus = FOCUSES[path[2]]
                            expected_bonus = next(n.children for n in BASE.walk(expected_bonus.get("completion_reward"))
                                                  if n.key == "add_tech_bonus")
                            # Parser classes differ between the two imported suites.
                            as_values = lambda nodes: [(n.key, n.op, n.value) for n in nodes]
                            self.assertEqual(1, sum(as_values(b) == as_values(expected_bonus) for b in country.bonuses))
                            for focus in route(tag, 1 - choice)[1:3]:
                                before = world.snapshot()
                                self.assertFalse(world.identity_available(focus, tag))
                                world.identity_reward(focus, tag)
                                self.assertEqual(before, world.snapshot(), focus)
                            self.assertIdentityBenefits(world, tag, choice)

    def test_all_in_flight_rewards_revalidate_current_co_ruler_and_provenance(self):
        for tag in ROOTS:
            rival = "EYR" if tag == "ERI" else "ERI"
            failures = [
                ("subject", True), ("capitulated", True), ("exists", False),
                ("leader", "unrelated_usurper"), ("leader", ROM["SINGLES"][0]),
                ("leader", ROM["SINGLES"][1]), ("government", "fascism"),
                ("original_tag", "D01"), ("rival_exists", True),
                *[("remove_flag", flag) for flag in (
                    "HSM_VER_ROM_crowned", "HSM_VER_UNI_founded", "HSM_VER_UNI_diplomatic",
                    "HSM_VER_UNI_president_" + tag, "HSM_VER_UNI_absorbed_" + rival)],
                *[("add_flag", flag) for flag in (
                    "HSM_VER_UNI_military", "HSM_VER_military_route", "HSM_VER_IMP_union_dispossessed")],
            ]
            for choice in (0, 1):
                world = copy.deepcopy(self.crowned[tag])
                for focus in route(tag, choice):
                    self.assertTrue(world.identity_available(focus, tag))
                    for attr, value in failures:
                        with self.subTest(tag=tag, focus=focus, attr=attr, value=value):
                            probe = copy.deepcopy(world)
                            country = probe.countries[tag]
                            if attr == "remove_flag":
                                country.flags.remove(value)
                            elif attr == "add_flag":
                                country.flags.add(value)
                            elif attr == "rival_exists":
                                probe.countries[rival].exists = value
                            else:
                                setattr(country, attr, value)
                            before = probe.snapshot()
                            self.assertFalse(probe.identity_available(focus, tag))
                            probe.identity_reward(focus, tag)
                            self.assertEqual(before, probe.snapshot())
                            # Previously earned identity benefits must still be
                            # cancelled when the current government loses eligibility.
                            for idea in IDEAS:
                                if world.test("HSM_VER_SP_has_" + idea, tag):
                                    self.assertTrue(probe.check(IDEAS[idea].get("cancel"), tag))
                            probe.apply("HSM_VER_SP_cancel_invalid", tag)
                            self.assertFalse(any(probe.test("HSM_VER_SP_has_" + idea, tag)
                                                 for idea in IDEAS))
                    world.identity_complete(focus, tag)

    def test_foreign_tags_cannot_use_copied_co_ruler_history(self):
        for tag in ROOTS:
            for choice in (0, 1):
                world = copy.deepcopy(self.crowned[tag])
                for focus in route(tag, choice):
                    for foreign in ("AVI", "GRI", "D01"):
                        probe = copy.deepcopy(world)
                        country = copy.deepcopy(probe.countries[tag])
                        country.tag = foreign
                        probe.countries[foreign] = country
                        before = probe.snapshot()
                        self.assertFalse(probe.identity_available(focus, foreign))
                        probe.identity_reward(focus, foreign)
                        self.assertEqual(before, probe.snapshot())
                    world.identity_complete(focus, tag)

    def test_unearned_institutions_cannot_be_skipped_after_handover(self):
        for tag in ROOTS:
            world = copy.deepcopy(self.crowned[tag])
            for focus in FOCUSES:
                if not focus.startswith(PREFIX + tag + "_") or focus == ROOTS[tag]:
                    continue
                before = world.snapshot()
                self.assertFalse(world.identity_available(focus, tag))
                world.identity_reward(focus, tag)
                self.assertEqual(before, world.snapshot(), focus)

    def test_identity_benefits_survive_co_rule_and_spirit_refresh(self):
        for tag in ROOTS:
            for choice in (0, 1):
                for timing in ("before_union", "before_handover", "after_handover"):
                    with self.subTest(tag=tag, choice=choice, timing=timing):
                        path = route(tag, choice)
                        if timing == "before_union":
                            world = IdentityRomanceWorld()
                            for focus in path:
                                world.identity_complete(focus, tag)
                            world.before_handover(tag)
                        else:
                            world = copy.deepcopy(self.before[tag, False])
                            if timing == "before_handover":
                                for focus in path:
                                    world.identity_complete(focus, tag)
                        world.scene(4, tag)
                        if timing == "after_handover":
                            for focus in path:
                                world.identity_complete(focus, tag)
                        self.assertIdentityBenefits(world, tag, choice)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], *BASE.REST], verbosity=2)
