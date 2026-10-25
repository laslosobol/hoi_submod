"""Post-unification production-script fixtures; not an HOI4 runtime/render test."""
from __future__ import annotations

import copy
import itertools
import re
import runpy
import unittest
from pathlib import Path

UNI = runpy.run_path(str(Path(__file__).with_name("Test-VereniaUnification.py")))
Node, read, walk, MOD, OPT, State = (UNI[k] for k in ("Node", "read", "walk", "MOD", "OPT", "State"))
PREFIX = "HSM_VER_CW_"
FILES = [MOD / folder / "HSM_VER_commonwealth.txt" for folder in
         ("common/national_focus", "common/scripted_triggers", "common/ideas", "events")]
FOCUSES = {n.get("id"): n for n in read(FILES[0])}
STAGES = ("first_budget", "citizens", "housing", "clinics", "market_roads",
          "machine_shops", "standards", "evening_classes", "institute",
          "common_service", "reserve_depots", "public_accounts", "ordinary_country")
COMPARE = UNI["REG"]["COMPARE"]
NATIVE_EFFECTS = {n.key: n.children for n in read(OPT.eaw / "common/scripted_effects/EAW_misc_effect.txt")
                  if n.key in {"decrease_poverty", "decrease_illiteracy", "increase_science_base", "increase_society_development"}}


class CommonwealthWorld(UNI["UnionWorld"]):
    def __init__(self):
        super().__init__()
        self.effects.update(NATIVE_EFFECTS)
        for country in self.countries.values():
            country.research_slots = 3

    def check(self, nodes, tag="ERI"):
        for n in nodes:
            if n.key == "amount_research_slots":
                ok = COMPARE[n.op](self.countries[tag].research_slots, int(n.value))
            elif n.key == "state":
                ok = tag is self.state_ids[n.value]
            elif n.key == "infrastructure":
                ok = COMPARE[n.op](tag.buildings.get("infrastructure", 0), int(n.value))
            elif n.key == "free_building_slots":
                assert isinstance(tag, State) and n.get("include_locked") == "yes"
                assert n.get("building") in ("industrial_complex", "arms_factory")
                free = tag.capacity - sum(v for k, v in tag.buildings.items() if k != "infrastructure")
                size = n.all("size")[0]
                ok = COMPARE[size.op](free, int(size.value))
            else:
                ok = super().check([n], tag)
            if not ok:
                return False
        return True

    def run(self, nodes, tag="ERI"):
        # Delegating a whole conditional chain preserves if/else ordering.
        if any(n.key in {"swap_ideas", "add_research_slot"} for n in nodes):
            for n in nodes:
                if n.key == "swap_ideas":
                    self.countries[tag].ideas.discard(n.get("remove_idea"))
                    self.countries[tag].ideas.add(n.get("add_idea"))
                elif n.key == "add_research_slot":
                    self.countries[tag].research_slots += int(n.value)
                else:
                    super().run([n], tag)
        else:
            super().run(nodes, tag)

    def established(self, host="ERI", avian=True):
        """Seed completed UNI history; the new campaign executes production code."""
        self.root = host
        country = self.countries[host]
        country.flags.update({"HSM_VER_UNI_founded", "HSM_VER_UNI_settled"})
        country.focuses.add("HSM_VER_UNI_settled_institutions")
        country.ideas.update({"HSM_VER_UNI_settled_state", "poverty2", "lack_of_scientists2", "pre_industrial_society", "better_science_base"})
        country.cosmetic = "HSM_VER_UNIFIED"
        for sid, state in self.state_ids.items():
            if sid != "470" or avian or host == "AVI":
                state.owner = state.controller = host
                state.cores.add(host)
                state.fully_controlled = True
        if avian and host != "AVI":
            country.flags.add("HSM_VER_UNI_absorbed_AVI")
        return self

    def available_cw(self, stage, host="ERI"):
        self.root = host
        return self.check(FOCUSES[PREFIX + stage].get("available", []), host)

    def complete_cw(self, stage, host="ERI"):
        self.complete_force(PREFIX + stage, host)

    def reply(self, number, choice, host):
        event = "hsm_ver_cw." + str(number)
        self.advance_days(1)
        assert self.deliver(event, host)
        self.choose(event, choice, host)


class Campaign(unittest.TestCase):
    def test_all_three_hosts_all_policy_combinations_reach_finale(self):
        for host, budget, justice, service in itertools.product(UNI["HOUSES"], range(2), range(2), range(2)):
            with self.subTest(host=host, choices=(budget, justice, service)):
                w = CommonwealthWorld().established(host)
                w.complete_cw("first_budget", host)
                self.assertFalse(w.available_cw("citizens", host))
                w.reply(1, budget, host)
                for stage in STAGES[1:]:
                    w.complete_cw(stage, host)
                    if stage == "citizens":
                        self.assertFalse(w.available_cw("housing", host))
                        w.reply(2, justice, host)
                    if stage == "common_service":
                        self.assertFalse(w.available_cw("reserve_depots", host))
                        w.reply(5, service, host)
                c = w.countries[host]
                self.assertIn(PREFIX + "completed", c.flags)
                self.assertIn("modern_society", c.ideas)
                self.assertIn("poverty5", c.ideas)
                self.assertEqual(c.research_slots, 4)
                self.assertEqual(c.cosmetic, "HSM_VER_UNIFIED")
                self.assertEqual(len([i for i in c.flags if i.startswith("HSM_VER_SP_owned_" + PREFIX)]), 6)
                self.assertFalse(any(i.startswith(PREFIX) for i in c.ideas))
                self.assertEqual(c.dynamic_modifiers, {"HSM_VER_SP_united_verenia"})
                self.assertEqual(len(w.annexations), 0)
                before = copy.deepcopy(w.countries)
                for number in (1, 2, 5):
                    w.choose("hsm_ver_cw." + str(number), 1, host)
                self.assertEqual(before, w.countries, "Resolved choices must not grant both policies")

    def test_real_union_completion_unlocks_common_campaign(self):
        for host in UNI["HOUSES"]:
            with self.subTest(host=host):
                w = CommonwealthWorld().begin(host)
                w.found(host)
                self.assertFalse(w.available_cw("first_budget", host))
                w.advance_days(60)
                w.complete(host, "settled_institutions")
                self.assertTrue(w.available_cw("first_budget", host))
                w.complete_cw("first_budget", host)
                w.reply(1, 0, host)
                self.assertTrue(w.available_cw("citizens", host))

    def test_war_occupation_and_lost_independence_pause_not_reward(self):
        for host in UNI["HOUSES"]:
            for problem in ("war", "subject", "capitulated", "exists", "occupation", "ownership", "founded", "settled"):
                with self.subTest(host=host, problem=problem):
                    w = CommonwealthWorld().established(host)
                    c = w.countries[host]
                    if problem in ("war", "subject", "capitulated"):
                        setattr(c, problem, True)
                    elif problem == "exists":
                        c.exists = False
                    elif problem == "occupation":
                        w.state_ids["401"].controller = "GRI"
                    elif problem == "ownership":
                        w.state_ids["401"].owner = "GRI"
                    else:
                        c.flags.discard("HSM_VER_UNI_" + problem)
                    self.assertFalse(w.available_cw("first_budget", host))

    def test_two_house_union_does_not_require_or_reward_independent_avian(self):
        for host in ("ERI", "EYR"):
            w = CommonwealthWorld().established(host, avian=False)
            before = copy.deepcopy(w.state_ids["470"])
            w.complete_cw("first_budget", host)
            w.reply(1, 0, host)
            w.complete_cw("market_roads", host)
            self.assertEqual(w.state_ids["470"], before)

    def test_native_development_never_downgrades_and_slots_cap_at_five(self):
        for slots in (3, 4, 5, 6):
            w = CommonwealthWorld().established()
            c = w.countries["ERI"]
            c.research_slots = slots
            c.ideas = {"no_poverty", "no_lack_of_scientists", "modern_society", "proper_science_base", PREFIX + "treasury"}
            for stage in ("housing", "clinics", "evening_classes", "institute", "ordinary_country"):
                w.run(FOCUSES[PREFIX + stage].get("completion_reward"), "ERI")
            self.assertTrue({"no_poverty", "no_lack_of_scientists", "modern_society", "proper_science_base"} <= c.ideas)
            self.assertEqual(c.research_slots, slots + (slots < 5))

    def test_full_building_slots_block_construction_and_roads_cap(self):
        w = CommonwealthWorld().established()
        w.countries["ERI"].ideas.add(PREFIX + "treasury")
        for state in w.states:
            state.capacity = 20
            state.buildings = {"industrial_complex": 19, "infrastructure": 5}
        self.assertFalse(w.available_cw("machine_shops"))
        before = copy.deepcopy(w.states)
        w.run(FOCUSES[PREFIX + "market_roads"].get("completion_reward"), "ERI")
        self.assertEqual(before, w.states)
        w.state_ids["401"].buildings["industrial_complex"] = 18
        self.assertTrue(w.available_cw("machine_shops"))

    def test_cannot_complete_focus_twice(self):
        w = CommonwealthWorld().established()
        w.complete_cw("first_budget")
        with self.assertRaises(AssertionError):
            w.complete_cw("first_budget")


class Structure(unittest.TestCase):
    def test_all_three_playable_trees_import_the_extension_without_overlaps(self):
        all_nodes = [n for path in (MOD / "common/national_focus").glob("*.txt") for n in read(path)]
        shared = {n.get("id"): n for n in all_nodes if n.key == "shared_focus" and n.children}
        trees = {n.get("id"): n for n in all_nodes if n.key == "focus_tree"}
        selected = [n for n in trees.values() if any(x.value == "HSM_VER_UNI_convention" for x in n.all("shared_focus"))]
        self.assertEqual(len(selected), 3)
        for tree in selected:
            imported = {n.value for n in tree.all("shared_focus") if not n.children}
            while True:
                found = {key for key, focus in shared.items() if any(
                    child.value in imported for group in focus.all("prerequisite") for child in group.children)}
                if found <= imported:
                    break
                imported.update(found)
            self.assertTrue(set(FOCUSES) <= imported, tree.get("id"))
            avi = tree.get("id") == "avian"
            native = {n.get("id"): n for n in tree.all("focus")}
            for key, focus in FOCUSES.items():
                position = (int(focus.get("x")) + (34 if avi else 0), int(focus.get("y")))
                for other_key, other in {**native, **{k: shared[k] for k in imported}}.items():
                    if other_key == key or other.get("relative_position_id"):
                        continue
                    dx = 34 if avi and other.get("offset") and other.get("offset")[0].key == "x" else 0
                    other_position = (int(other.get("x", "0")) + dx, int(other.get("y", "0")))
                    self.assertNotEqual(position, other_position, (tree.get("id"), key, other_key))

    def test_connected_shared_subtree_and_no_new_meter(self):
        self.assertEqual(set(FOCUSES), {PREFIX + stage for stage in STAGES})
        resolved = {"HSM_VER_UNI_settled_institutions"}
        for stage in STAGES:
            focus = FOCUSES[PREFIX + stage]
            self.assertTrue(all(any(n.value in resolved for n in p.children) for p in focus.all("prerequisite")))
            self.assertEqual(focus.get("cancel_if_invalid"), "no")
            self.assertEqual(focus.get("continue_if_invalid"), "no")
            resolved.add(PREFIX + stage)
        self.assertEqual(sum(int(n.get("cost")) * 7 for n in FOCUSES.values()), 721)
        for path in FILES:
            for n in walk(read(path)):
                self.assertNotIn(n.key, {"set_variable", "add_to_variable", "set_global_flag", "create_wargoal", "annex_country", "set_cosmetic_tag", "set_politics"})

    def test_idea_modifiers_are_engine_supported_and_native_effects_exist(self):
        docs = (OPT.game / "documentation/modifiers_documentation.md").read_text(encoding="utf-8-sig")
        supported = set(re.findall(r"^## (\S+)", docs, re.M))
        buildings = {n.key for root in (OPT.game, OPT.eaw) for path in (root / "common/buildings").glob("*.txt")
                     for group in read(path) for n in group.children}
        supported.update("production_speed_" + building + "_factor" for building in buildings)
        for n in walk(read(FILES[2])):
            if n.key == "modifier":
                for modifier in n.children:
                    self.assertTrue(modifier.key in supported, "Unsupported modifier: " + modifier.key)
        self.assertEqual(len(NATIVE_EFFECTS), 4)

    def test_english_russian_coverage_and_narrative_separation(self):
        locales = []
        for lang in ("english", "russian"):
            path = MOD / "localisation" / lang / ("HSM_VER_commonwealth_l_" + lang + ".yml")
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            values = {}
            for line in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
                if not line.strip():
                    continue
                match = re.fullmatch(r'\s*([^: ]+):0 "(.*)"', line)
                self.assertIsNotNone(match, line)
                key, value = match.groups()
                self.assertNotIn(key, values)
                values[key] = value
                self.assertNotRegex(value, r"\bAI\b|ИИ|HSM_VER_|[+-]\d+%")
            locales.append(values)
        self.assertEqual(locales[0].keys(), locales[1].keys())
        required = set()
        for path in FILES:
            for n in walk(read(path)):
                if n.key in {"name", "title", "text", "tooltip"} or (n.key == "desc" and not n.children):
                    required.add(n.value)
                if n.key == "shared_focus":
                    required.update((n.get("id"), n.get("id") + "_desc"))
                if n.key.startswith(PREFIX) and n.get("modifier"):
                    required.update((n.key, n.key + "_desc"))
        self.assertFalse(required - locales[0].keys(), required - locales[0].keys())

    def test_new_icons_and_event_pictures_exist(self):
        sprites = set()
        for root in (OPT.game / "interface", OPT.eaw / "interface", MOD / "interface"):
            for path in root.rglob("*.gfx"):
                sprites.update(re.findall(r'\bname\s*=\s*"?(GFX_[^\s"}]+)', path.read_text(encoding="utf-8-sig", errors="replace")))
        for path in FILES:
            for n in walk(read(path)):
                if n.key in {"icon", "picture"}:
                    sprite = n.value if n.value.startswith("GFX_") else "GFX_idea_" + n.value
                    self.assertTrue(sprite in sprites, "Missing sprite: " + sprite)


if __name__ == "__main__":
    unittest.main(argv=[__file__, *UNI["BASE"]["REST"]])
