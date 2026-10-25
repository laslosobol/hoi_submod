"""Bounded production-script fixtures, not an HOI4 emulator. No shared-file writes.

python -B tools/Test-VereniaZypressen.py [--eaw PATH] [--game PATH]
The parent must import HSM_ZYP_victory_roll ONLY into avian_fascists.
"""
from __future__ import annotations

import copy
import re
import runpy
import unittest
from dataclasses import dataclass, field
from pathlib import Path

BASE = runpy.run_path(str(Path(__file__).with_name("Test-Verenia.py")))
Node, read, walk, parse = (BASE[k] for k in ("Node", "read", "walk", "parse"))
MOD, OPT = BASE["MOD"], BASE["OPT"]
FILES = sorted(MOD.rglob("HSM_VER_zypressen.txt"))
FOCUSES = {n.get("id"): n for n in read(MOD / "common/national_focus/HSM_VER_zypressen.txt")}
TRIGGERS = {n.key: n.children for n in read(MOD / "common/scripted_triggers/HSM_VER_zypressen.txt")}
HEART = [int(n.key) for n in TRIGGERS["HSM_ZYP_herzland_held"]]
REGIONS = {r: [int(n.value) for n in walk(TRIGGERS[f"HSM_ZYP_{r}_owner"]) if n.key == "owns_state"] for r in ("west", "north", "south", "east")}
CROWNS = {n.get("tag"): Node("leader", value=n.get("has_country_leader")).get("character") for n in TRIGGERS["HSM_ZYP_dynastic_crown"][-1].children}


@dataclass
class State:
    owner: str = "OTH"
    controller: str = "OTH"
    capacity: int = 12
    buildings: dict = field(default_factory=dict)


class World(BASE["World"]):
    def __init__(self):
        super().__init__()
        self.countries = {t: BASE["Country"](t) for t in {"AVI", "OTH", "ALLY", *CROWNS}}
        for c in self.countries.values():
            c.government = "fascism"
            c.overlord = ""
            c.characters = set()
            c.stability = 0.5
            c.bonuses = []
        self.root = "AVI"
        self.sender = "AVI"
        self.prev = None
        self.avi = self.countries["AVI"]
        self.avi.leader = "AVI_trubach_von_zypressen"
        self.avi.focuses.add("a_zypressen_on_the_imperial_throne")
        self.states = {i: State() for i in {*HEART, *(s for ss in REGIONS.values() for s in ss)}}
        for i in HEART:
            self.states[i] = State("AVI", "AVI")
        self.packets = []
        self.day = 0

    def resolve(self, value):
        return self.prev if value == "PREV" else super().resolve(value)

    def scope(self, method, nodes, old, new):
        previous = self.prev
        self.prev = old
        try:
            return method(nodes, new)
        finally:
            self.prev = previous

    def check(self, nodes, tag="AVI"):
        for n in nodes:
            if n.key in ("hidden_trigger", "custom_trigger_tooltip"):
                ok = self.check([c for c in n.children if not (n.key == "custom_trigger_tooltip" and c.key == "tooltip")], tag)
            elif n.key in self.countries or n.key in ("ROOT", "FROM", "PREV"):
                ok = self.scope(self.check, n.children, tag, self.resolve(n.key))
            elif n.key.isdigit():
                ok = self.scope(self.check, n.children, tag, self.states[int(n.key)])
            elif n.key == "owner":
                ok = self.scope(self.check, n.children, tag, tag.owner)
            elif n.key == "overlord":
                overlord = self.countries[tag].overlord
                ok = bool(overlord) and self.scope(self.check, n.children, tag, overlord)
            elif n.key == "any_subject_country":
                ok = any(c.exists and c.overlord == tag and self.scope(self.check, n.children, tag, t) for t, c in self.countries.items())
            elif n.key == "any_country":
                ok = any(c.exists and self.scope(self.check, n.children, tag, t) for t, c in self.countries.items())
            elif n.key == "any_owned_state":
                ok = any(s.owner == tag and self.scope(self.check, n.children, tag, s) for s in self.states.values())
            elif n.key == "has_government":
                ok = self.countries[tag].government == n.value
            elif n.key == "is_subject_of":
                ok = self.countries[tag].overlord == self.resolve(n.value)
            elif n.key == "has_character":
                ok = n.value in self.countries[tag].characters
            elif n.key == "owns_state":
                ok = self.states[int(n.value)].owner == tag
            elif n.key == "has_full_control_of_state":
                s = self.states[int(n.value)]
                ok = s.owner == tag and s.controller == tag
            elif n.key == "has_wargoal_against":
                ok = any(g[1] == self.resolve(n.value) for g in self.countries[tag].goals)
            elif n.key == "is_fully_controlled_by":
                ok = tag.controller == self.resolve(n.value)
            elif n.key == "free_building_slots":
                assert n.get("building") in ("industrial_complex", "arms_factory")
                assert n.get("include_locked") == "yes"
                assert n.all("size")[0].op == ">" and n.get("size") == "0"
                ok = sum(tag.buildings.values()) < tag.capacity
            else:
                ok = super().check([n], tag)
            if not ok:
                return False
        return True

    def run(self, nodes, tag="AVI"):
        taken = None
        for n in nodes:
            if n.key == "if":
                taken = self.check(n.get("limit", []), tag)
                if taken:
                    self.run([x for x in n.children if x.key != "limit"], tag)
            elif n.key == "else_if":
                assert taken is not None
                if not taken and self.check(n.get("limit", []), tag):
                    taken = True
                    self.run([x for x in n.children if x.key != "limit"], tag)
            elif n.key == "else":
                assert taken is not None
                if not taken:
                    self.run(n.children, tag)
                taken = True
            elif n.key in self.countries or n.key in ("ROOT", "FROM", "PREV"):
                self.scope(self.run, n.children, tag, self.resolve(n.key))
            elif n.key == "every_country":
                for t, c in self.countries.items():
                    if c.exists and self.scope(self.check, n.get("limit", []), tag, t):
                        self.scope(self.run, [x for x in n.children if x.key != "limit"], tag, t)
            elif n.key == "random_owned_state":
                eligible = [s for s in self.states.values() if s.owner == tag and self.scope(self.check, n.get("limit", []), tag, s)]
                if eligible:
                    self.scope(self.run, [x for x in n.children if x.key != "limit"], tag, eligible[0])
            elif n.key == "add_extra_state_shared_building_slots":
                tag.capacity += int(n.value)
            elif n.key == "add_building_construction":
                assert n.get("instant_build") == "yes"
                b = n.get("type")
                tag.buildings[b] = tag.buildings.get(b, 0) + int(n.get("level"))
            elif n.key == "add_tech_bonus":
                self.countries[tag].bonuses.append(copy.deepcopy(n.children))
            elif n.key == "add_stability":
                self.countries[tag].stability += float(n.value)
            elif n.key == "country_event":
                self.packets.append((self.day + int(n.get("days", 0)), tag, n.get("id"), self.prev or self.root))
                super().run([n], tag)
            elif n.key == "create_wargoal":
                self.countries[tag].goals.add((n.get("type"), self.resolve(n.get("target")), tuple(int(x.key) for x in n.get("generator"))))
            else:
                super().run([n], tag)

    def tick(self, days=1):
        self.advance_days(days)
        self.day += days
        self.root = "AVI"
        hook = read(MOD / "common/on_actions/HSM_VER_zypressen.txt")[0].children[0]
        self.run(hook.get("effect"), "AVI")

    def deliver(self, event, tag="AVI"):
        packet = next(p for p in self.packets if p[0] <= self.day and p[1:3] == (tag, event))
        self.packets.remove(packet)
        self.root, self.sender = tag, packet[3]
        return self.countries[tag].exists and self.check(self.events[event].get("trigger", []), tag)

    def complete(self, suffix):
        f = FOCUSES["HSM_ZYP_" + suffix]
        self.root = "AVI"
        assert f.get("id") not in self.avi.focuses
        assert all(any(n.value in self.avi.focuses for n in p.children) for p in f.all("prerequisite"))
        assert self.check(f.get("available"))
        self.avi.focuses.add(f.get("id"))
        self.run(f.get("completion_reward"))

    def crown(self):
        self.complete("victory_roll")
        self.complete("imperial_coronation")
        self.tick()
        assert self.deliver("hsm_ver_zypressen.1")
        self.choose("hsm_ver_zypressen.1", 0, "AVI")

    def subject(self, tag="FLO"):
        c = self.countries[tag]
        c.subject = True
        c.overlord = "AVI"
        c.leader = CROWNS[tag]
        return c

    def offer(self, central=True):
        self.crown()
        self.subject()
        self.complete("rolls_of_the_crowns")
        self.tick()
        self.choose("hsm_ver_zypressen.2", int(central), "AVI")
        self.complete("commissions_not_orders")

    def take_region(self, r, owner="AVI"):
        for i in REGIONS[r]:
            self.states[i].owner = self.states[i].controller = owner


class Contract(unittest.TestCase):
    def test_state_tooltip_wrappers_preserve_predicates(self):
        world = World()
        predicates = (
            "is_fully_controlled_by = ROOT "
            "free_building_slots = { building = arms_factory size > 0 include_locked = yes }"
        )
        plain = parse(predicates)
        wrapped = parse("custom_trigger_tooltip = { tooltip = state_note hidden_trigger = { " + predicates + " } }")
        for state, expected in ((State("AVI", "AVI"), True),
                                (State("AVI", "OTH"), False), (State("AVI", "AVI", 0), False)):
            with self.subTest(state=state):
                self.assertEqual(world.check(plain, state), expected)
                self.assertEqual(world.check(wrapped, state), expected)

    def test_graph_bounds_and_parent_import(self):
        self.assertEqual(len(FOCUSES), 17)
        seen, coords = set(), set()
        for key, f in FOCUSES.items():
            self.assertFalse(f.get("relative_position_id"))
            pos = (int(f.get("x")), int(f.get("y")))
            self.assertGreaterEqual(pos[0], 56)
            self.assertNotIn(pos, coords)
            coords.add(pos)
            for p in f.all("prerequisite"):
                self.assertTrue(all(n.value in seen for n in p.children))
            seen.add(key)
        self.assertEqual((FOCUSES["HSM_ZYP_victory_roll"].get("x"), FOCUSES["HSM_ZYP_victory_roll"].get("y")), ("58", "0"))
        imports = [(n.get("id"), s.value) for n in read(MOD / "common/national_focus/AVI.txt") if n.key == "focus_tree" for s in n.all("shared_focus") if s.value == "HSM_ZYP_victory_roll"]
        self.assertTrue(not imports or imports == [("avian_fascists", "HSM_ZYP_victory_roll")])
        if not imports:
            print("PARENT INTEGRATION NEEDED: shared_focus = HSM_ZYP_victory_roll in avian_fascists only")

    def test_native_crowns_and_territory_sources(self):
        native = read(OPT.eaw / "common/decisions/AVI_decisions.txt")[0].children
        rulers = {n.key[8:]: next(x.value for x in walk(n.children) if x.key == "character") for n in native if n.key.startswith("release_")}
        rulers.update(FLO="FLO_archduke_trubach", BOI="BOI_king_trubach")
        self.assertEqual(CROWNS, rulers)
        for n in walk(read(MOD / "common/scripted_triggers/HSM_VER_zypressen.txt")):
            if n.key == "has_country_leader": self.assertEqual(n.get("ruling_only"), "yes")
        heart = []
        for p in (OPT.eaw / "history/states").glob("*.txt"):
            n = read(p)[0]
            if any(x.key == "add_core_of" and x.value in ("GRI", "BRZ", "STW", "KAT", "ANG", "YAL", "ROU", "PYT", "FEA") for x in n.get("history", [])):
                heart.append(int(n.get("id")))
        self.assertEqual(set(HEART), set(heart))

    def test_no_sovereignty_or_custody_mutations(self):
        forbidden = {"annex_country", "transfer_state", "add_state_core", "add_core_of", "set_autonomy", "declare_war_on", "recruit_character", "retire_character", "set_country_leader", "add_country_leader_role", "set_capital", "load_focus_tree", "set_cosmetic_tag", "set_politics"}
        self.assertFalse({n.key for p in FILES for n in walk(read(p))} & forbidden)

    def test_localization_and_assets(self):
        texts = [(p, p.read_text(encoding="utf-8-sig")) for p in FILES]
        expected = set()
        for _, text in texts:
            expected.update(re.findall(r'(?:title|desc|text|name|tooltip|custom_effect_tooltip|has_country_flag)\s*=\s*((?:HSM_ZYP_|hsm_ver_zypressen\.)[\w.]+)', text))
        for f in FOCUSES:
            expected.update((f, f + "_desc"))
        for part in ("ideas", "decisions", "decisions/categories"):
            for n in walk(read(MOD / f"common/{part}/HSM_VER_zypressen.txt")):
                if n.key.startswith("HSM_ZYP_") and n.children:
                    expected.update((n.key, n.key + "_desc"))
        sets = []
        for lang in ("english", "russian"):
            p = MOD / f"localisation/{lang}/HSM_VER_zypressen_l_{lang}.yml"
            self.assertTrue(p.read_bytes().startswith(b"\xef\xbb\xbf"))
            text = p.read_text(encoding="utf-8-sig")
            lines = [l for l in text.splitlines()[1:] if l.strip()]
            entries = [re.fullmatch(r' ([\w.]+):0 "(?:[^"\\]|\\["\\nrt])*"', l) for l in lines]
            self.assertTrue(all(entries))
            keys = [e[1] for e in entries]
            self.assertEqual(len(keys), len(set(keys)))
            self.assertFalse(expected - set(keys), sorted(expected - set(keys)))
            sets.append(set(keys))
        self.assertEqual(*sets)
        sprites = "\n".join(p.read_text(encoding="utf-8-sig", errors="replace") for root in (OPT.eaw, OPT.game) for p in (root / "interface").rglob("*.gfx"))
        for _, text in texts:
            for name in re.findall(r'(?:icon|picture)\s*=\s*(GFX_\w+)', text):
                self.assertRegex(sprites, r'name\s*=\s*"?' + re.escape(name) + r'(?:"|\s)')


class Behaviour(unittest.TestCase):
    def setUp(self):
        self.w = World()

    def test_unsupported_predicates_and_effects_fail(self):
        with self.assertRaises(AssertionError): self.w.check(parse("invented_predicate = yes"))
        with self.assertRaises(AssertionError): self.w.run(parse("invented_effect = yes"))

    def test_daily_hook_is_inert_before_campaign_entry(self):
        self.w.effects["HSM_ZYP_maintain"] = parse("must_not_run_on_other_routes = yes")
        self.w.tick()
        self.w.avi.flags.add("HSM_ZYP_started")
        with self.assertRaises(AssertionError): self.w.tick()

    def test_entry_requires_native_goal_and_settled_entire_herzland(self):
        self.assertTrue(self.w.test("HSM_ZYP_entry", "AVI"))
        for state in HEART:
            s = self.w.states[state]
            s.owner = "OTH"
            self.assertFalse(self.w.test("HSM_ZYP_entry", "AVI"))
            s.owner, s.controller = "AVI", "OTH"
            self.assertFalse(self.w.test("HSM_ZYP_entry", "AVI"))
            s.controller = "AVI"
        self.w.avi.focuses.clear()
        self.assertFalse(self.w.test("HSM_ZYP_entry", "AVI"))

    def test_subject_capital_counts_but_allied_capital_does_not(self):
        self.w.subject("GRI")
        self.w.states[382] = State("GRI", "GRI")
        self.assertTrue(self.w.test("HSM_ZYP_entry", "AVI"))
        self.w.countries["GRI"].overlord = "OTH"
        self.w.countries["GRI"].faction = self.w.avi.faction = "same"
        self.assertFalse(self.w.test("HSM_ZYP_entry", "AVI"))

    def test_crown_is_new_once_only_and_invalidates_while_open(self):
        self.w.complete("victory_roll"); self.w.complete("imperial_coronation")
        self.assertNotIn("HSM_ZYP_crowned", self.w.avi.flags)
        self.w.avi.war = True
        self.w.choose("hsm_ver_zypressen.1", 0, "AVI")
        self.assertNotIn("HSM_ZYP_crowned", self.w.avi.flags)
        self.w.avi.war = False
        self.w.choose("hsm_ver_zypressen.1", 0, "AVI")
        stability = self.w.avi.stability
        self.w.choose("hsm_ver_zypressen.1", 0, "AVI")
        self.assertEqual(stability, self.w.avi.stability)

    def test_offer_acceptance_is_recipient_scoped_and_once_only(self):
        self.w.offer()
        c = self.w.countries["FLO"]
        self.w.choose("hsm_ver_zypressen.10", 0, "FLO")
        self.assertIn("HSM_ZYP_common_ministries", c.ideas)
        self.assertNotIn("HSM_ZYP_signed", self.w.avi.flags)
        self.w.choose("hsm_ver_zypressen.10", 0, "FLO")
        self.assertEqual(len(c.bonuses), 1)
        self.w.tick()
        self.assertIn("HSM_ZYP_dynastic_exchange", self.w.avi.ideas)

    def test_autonomous_offer_and_counteroffer_require_correct_choices(self):
        self.w.offer(False)
        self.w.choose("hsm_ver_zypressen.10", 0, "FLO")
        self.assertNotIn("HSM_ZYP_signed", self.w.countries["FLO"].flags)
        self.w.choose("hsm_ver_zypressen.10", 1, "FLO")
        self.assertIn("HSM_ZYP_autonomous_crown", self.w.countries["FLO"].ideas)
        self.w = World(); self.w.offer()
        self.w.choose("hsm_ver_zypressen.10", 2, "FLO")
        self.assertNotIn("HSM_ZYP_signed", self.w.countries["FLO"].flags)
        self.w.tick()
        self.assertTrue(self.w.deliver("hsm_ver_zypressen.11"))
        self.w.choose("hsm_ver_zypressen.11", 0, "AVI")
        self.assertIn("HSM_ZYP_autonomous_crown", self.w.countries["FLO"].ideas)
        self.assertNotIn("HSM_ZYP_autonomous_crown", self.w.avi.ideas)

    def test_refusal_expiry_retry_and_late_counter(self):
        self.w.offer()
        c = self.w.countries["FLO"]
        self.w.choose("hsm_ver_zypressen.10", 3, "FLO")
        self.assertFalse(self.w.test("HSM_ZYP_can_invite", "FLO"))
        self.w.tick(91)
        self.assertTrue(self.w.test("HSM_ZYP_can_invite", "FLO"))
        self.w.apply("HSM_ZYP_offer_congress", "AVI")
        self.w.tick(31)
        self.w.choose("hsm_ver_zypressen.10", 0, "FLO")
        self.assertNotIn("HSM_ZYP_signed", c.flags)
        self.w.tick(60); self.w.apply("HSM_ZYP_offer_congress", "AVI")
        self.w.choose("hsm_ver_zypressen.10", 2, "FLO")
        self.w.sender = "FLO"; self.w.tick(31)
        self.w.choose("hsm_ver_zypressen.11", 0, "AVI")
        self.assertNotIn("HSM_ZYP_signed", c.flags)

    def test_foreign_overlord_or_non_dynastic_ruler_cannot_consent(self):
        for attr, value in (("overlord", "OTH"), ("leader", "someone_else")):
            self.w = World(); self.w.offer()
            c = self.w.countries["FLO"]; setattr(c, attr, value)
            self.w.choose("hsm_ver_zypressen.10", 0, "FLO")
            self.assertNotIn("HSM_ZYP_signed", c.flags)

    def test_occupation_pauses_but_secession_voids_agreements(self):
        self.w.offer(); c = self.w.countries["FLO"]
        self.w.choose("hsm_ver_zypressen.10", 0, "FLO")
        c.capitulated = True; self.w.tick()
        self.assertNotIn("HSM_ZYP_common_ministries", c.ideas)
        self.assertIn("HSM_ZYP_signed", c.flags)
        c.capitulated = False; self.w.tick()
        self.assertIn("HSM_ZYP_common_ministries", c.ideas)
        self.assertEqual(len(c.bonuses), 1)
        c.overlord = ""; self.w.tick()
        self.assertNotIn("HSM_ZYP_signed", c.flags)
        self.assertNotIn("HSM_ZYP_common_ministries", c.ideas)

    def test_lost_policy_delivery_is_requeued_without_daily_spam(self):
        self.w.crown(); self.w.complete("rolls_of_the_crowns")
        n = len(self.w.avi.events)
        self.w.tick(); self.assertEqual(n, len(self.w.avi.events))
        self.w.tick(30); self.assertEqual(n + 1, len(self.w.avi.events))
        self.w.choose("hsm_ver_zypressen.2", 0, "AVI")
        self.w.tick(31); self.assertEqual(n + 1, len(self.w.avi.events))

    def test_grover_facts_are_exclusive_and_death_overrides_residue(self):
        def variants():
            return [n.get("text") for n in self.w.events["hsm_ver_zypressen.3"].all("desc") if self.w.check(n.get("trigger"))]
        self.assertEqual(variants(), ["hsm_ver_zypressen.3.d"])
        self.w.countries["OTH"].characters.add("GRI_emperor_grover_vi")
        self.assertEqual(variants(), ["hsm_ver_zypressen.3.foreign.d"])
        self.w.avi.characters.add("GRI_emperor_grover_vi")
        self.assertEqual(variants(), ["hsm_ver_zypressen.3.local.d"])
        self.w.global_flags.add("GRI_grover_vi_dead")
        self.assertEqual(variants(), ["hsm_ver_zypressen.3.dead.d"])

    def test_dynamic_owner_goals_skip_allies_subjects_self_and_wars(self):
        self.w.crown(); self.w.avi.focuses.add("HSM_ZYP_western_campaign")
        self.w.apply("HSM_ZYP_review_frontiers", "AVI")
        self.assertEqual({g[1] for g in self.w.avi.goals}, {"OTH"})
        self.w.avi.goals.clear()
        self.w.countries["OTH"].subject = True
        self.w.apply("HSM_ZYP_review_frontiers", "AVI")
        self.assertFalse(self.w.avi.goals)
        self.w.countries["OTH"].subject = False
        self.w.countries["OTH"].faction = self.w.avi.faction = "same"
        self.w.apply("HSM_ZYP_review_frontiers", "AVI")
        self.assertFalse(self.w.avi.goals)
        self.w.countries["OTH"].faction = ""
        self.w.countries["OTH"].wars.add("AVI")
        self.w.apply("HSM_ZYP_review_frontiers", "AVI")
        self.assertFalse(self.w.avi.goals)

    def test_staging_and_new_owner_retargeting(self):
        self.w.crown(); self.w.avi.focuses.update(("HSM_ZYP_western_campaign", "HSM_ZYP_northern_campaign"))
        self.w.apply("HSM_ZYP_review_frontiers", "AVI")
        self.assertEqual({g[2] for g in self.w.avi.goals}, {tuple(REGIONS["west"])})
        self.w.avi.goals.clear(); self.w.take_region("west")
        self.w.apply("HSM_ZYP_review_frontiers", "AVI")
        self.assertEqual({g[2] for g in self.w.avi.goals}, {tuple(REGIONS["north"])})
        self.w.states[REGIONS["north"][0]].owner = "ALLY"
        self.w.apply("HSM_ZYP_review_frontiers", "AVI")
        self.assertEqual({g[1] for g in self.w.avi.goals}, {"OTH", "ALLY"})

    def test_factory_fallback_and_event_reward_idempotence(self):
        self.w.crown()
        for s in self.w.states.values(): s.capacity = 0
        self.w.choose("hsm_ver_zypressen.4", 0, "AVI")
        self.assertEqual(len(self.w.avi.bonuses), 2)
        self.w.choose("hsm_ver_zypressen.4", 0, "AVI")
        self.assertEqual(len(self.w.avi.bonuses), 2)
        self.w = World(); self.w.crown()
        self.w.choose("hsm_ver_zypressen.4", 0, "AVI")
        self.assertEqual(sum(s.buildings.get("industrial_complex", 0) for s in self.w.states.values()), 1)
        self.assertTrue(all(s.owner == s.controller == "AVI" for s in self.w.states.values() if s.buildings))

    def test_foreign_overlord_without_regional_land_is_targeted_not_its_subject(self):
        self.w.crown(); self.w.avi.focuses.add("HSM_ZYP_western_campaign")
        c = self.w.countries["OTH"]
        c.subject = True; c.overlord = "ALLY"
        self.w.apply("HSM_ZYP_review_frontiers", "AVI")
        self.assertEqual(self.w.avi.goals, {("annex_everything", "ALLY", ())})
        self.assertFalse(self.w.avi.wars)
        self.w.avi.goals.clear()
        self.w.countries["ALLY"].faction = self.w.avi.faction = "same"
        self.w.apply("HSM_ZYP_review_frontiers", "AVI")
        self.assertFalse(self.w.avi.goals)
        self.assertTrue(self.w.test("HSM_ZYP_west_settled", "AVI"))

    def test_complete_route_without_any_subject_acceptance(self):
        self.w.crown()
        for f in ("household_register", "rolls_of_the_crowns"):
            self.w.complete(f)
        self.w.choose("hsm_ver_zypressen.2", 1, "AVI")
        self.w.complete("repair_the_arteries")
        self.w.choose("hsm_ver_zypressen.4", 1, "AVI")
        for f in ("commissions_not_orders", "arsenals_and_workshops", "common_colleges", "the_muster_dispute"):
            self.w.complete(f)
        self.w.choose("hsm_ver_zypressen.5", 1, "AVI")
        for f, r in (("western_campaign", "west"), ("northern_campaign", "north"), ("southern_campaign", "south"), ("eastern_campaign", "east")):
            self.w.complete(f); self.w.take_region(r)
            if r == "west": self.w.complete("reconstruction_contracts")
        for f in ("seats_for_new_crowns", "accounts_after_campaign", "crown_and_countries"):
            self.w.complete(f)
        self.assertEqual(len(self.w.avi.focuses & set(FOCUSES)), 17)
        self.assertIn("hsm_ver_zypressen.7", self.w.avi.events)
        self.assertFalse(self.w.avi.cores)
        self.assertFalse(self.w.avi.wars)


if __name__ == "__main__":
    unittest.main(argv=[__file__, *BASE["REST"]], verbosity=2)
