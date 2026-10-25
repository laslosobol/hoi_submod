"""Avian constitutional campaign and native dependency fixtures; not an HOI4 emulator.

Run with python -B tools/Test-VereniaAvian.py [-v] [TestClass.test_name].
The existing harness supplies --eaw/--game and the Clausewitz parser. Fixtures
execute production rewards, replies and hooks, never replacement treaty logic.
"""
from __future__ import annotations

import copy
import itertools
import re
import runpy
import unittest
from dataclasses import dataclass, field
from pathlib import Path

BASE = runpy.run_path(str(Path(__file__).with_name("Test-Verenia.py")))
Node, read, walk = (BASE[k] for k in ("Node", "read", "walk"))
MOD, OPT = BASE["MOD"], BASE["OPT"]
ROOT_FOCUS = "HSM_AVI_three_separate_seals"
UNIFICATION_ROOT = "HSM_VER_UNI_convention"
HOUSES = ("AVI", "ERI", "EYR")
LAYOUT = {
    "three_separate_seals": (50, 0),
    "two_legible_copies": (48, 1),
    "hear_the_towns": (52, 1),
    "charter_without_submission": (50, 2),
    "common_accounts": (48, 3),
    "roads_between_houses": (52, 3),
    "limited_joint_staff": (48, 4),
    "a_court_for_hosts": (52, 4),
    "the_first_common_budget": (50, 5),
    "the_unauthorised_levy": (50, 6),
    "honour_the_exemptions": (48, 7),
    "common_workshops": (52, 7),
    "defence_without_a_master": (48, 8),
    "open_minutes": (52, 8),
    "a_union_worth_keeping": (50, 9),
    "neighbours_without_a_chair": (55, 4),
}


@dataclass
class State:
    owner: str = "AVI"
    controller: str = "AVI"
    cores: set = field(default_factory=lambda: {"AVI"})
    capacity: int = 20
    extra_slots: int = 0
    buildings: dict = field(default_factory=dict)


class AvianWorld(BASE["World"]):
    def __init__(self):
        super().__init__()
        self.countries["AVI"].leader = "AVI_lady_katrina_avian"
        self.countries["AVI"].focuses.add("intergigantes")
        self.countries["AVI"].ideas.add("AVI_linguistic_antagonism")
        for country in self.countries.values():
            country.government = "neutrality"
            country.stability = 0.5
            country.bonuses = []
            country.defensive_wars = set()
            country.offensive_wars = set()
        self.game_rules = {"AVI_ai_behavior": "DEFAULT"}
        self.historical = False
        self.states = [State()]
        self.homelands = {470: self.states[0]}
        for tag, state_ids in (("ERI", (401, 500, 673)), ("EYR", (391, 400))):
            self.homelands.update({state_id: State(owner=tag, controller=tag, cores={tag}) for state_id in state_ids})
        self.previous = "AVI"
        self.day = 0
        self.scheduled = []
        self.focuses = {
            n.get("id"): n
            for path in (MOD / "common/national_focus").glob("*.txt")
            for n in walk(read(path))
            if n.key in ("focus", "shared_focus") and n.children
        }
        self.decisions = {
            n.key: n
            for path in (MOD / "common/decisions").glob("HSM_VER*.txt")
            for category in read(path)
            for n in category.children
        }
        self.hooks = {}
        for path in (MOD / "common/on_actions").glob("HSM_VER*.txt"):
            for container in read(path):
                for hook in container.children:
                    self.hooks.setdefault(hook.key, []).extend(hook.get("effect", []))
        self.root = "AVI"

    def check(self, nodes, tag="AVI"):
        for n in nodes:
            if n.key.isdigit() and int(n.key) in self.homelands:
                ok = self.check(n.children, self.homelands[int(n.key)])
            elif n.key == "owns_state":
                ok = self.homelands[int(n.value)].owner == tag
            elif n.key == "all_owned_state":
                previous = self.previous
                self.previous = tag
                ok = all(self.check(n.children, state) for state in self.homelands.values() if state.owner == tag)
                self.previous = previous
            elif n.key == "any_subject_country":
                ok = any(c.exists and c.subject and getattr(c, "overlord", "") == tag and self.check(n.children, t) for t, c in self.countries.items())
            elif n.key == "has_government":
                ok = self.countries[tag].government == n.value
            elif n.key == "has_game_rule":
                ok = self.game_rules.get(n.get("rule")) == n.get("option")
            elif n.key == "is_historical_focus_on":
                ok = self.historical == (n.value == "yes")
            elif n.key in ("has_defensive_war_with", "has_offensive_war_with"):
                wars = self.countries[tag].defensive_wars if n.key == "has_defensive_war_with" else self.countries[tag].offensive_wars
                ok = self.resolve(n.value) in wars
            elif n.key == "any_country":
                previous = self.previous
                self.previous = tag
                ok = any(c.exists and self.check(n.children, t) for t, c in self.countries.items())
                self.previous = previous
            elif n.key == "any_owned_state":
                ok = any(s.owner == tag and self.check(n.children, s) for s in self.states)
            elif isinstance(tag, State):
                if n.key in ("hidden_trigger", "custom_trigger_tooltip"):
                    ok = self.check([c for c in n.children if not (n.key == "custom_trigger_tooltip" and c.key == "tooltip")], tag)
                elif n.key == "is_core_of":
                    ok = self.resolve(n.value) in tag.cores
                elif n.key == "is_fully_controlled_by":
                    ok = tag.controller == self.resolve(n.value)
                elif n.key == "free_building_slots":
                    assert n.get("building") == "industrial_complex"
                    assert n.get("include_locked") == "yes"
                    size = n.all("size")[0]
                    assert size.op == ">" and size.value == "0"
                    ok = sum(tag.buildings.values()) < tag.capacity
                else:
                    raise AssertionError(f"Unsupported state predicate: {n.key}")
            else:
                ok = super().check([n], tag)
            if not ok:
                return False
        return True

    def resolve(self, value):
        return self.previous if value == "PREV" else super().resolve(value)

    def run(self, nodes, tag="AVI"):
        # Preserve conditional chains while extending the base interpreter.
        branch_taken = None
        for n in nodes:
            if n.key == "if":
                branch_taken = self.check(n.get("limit", []), tag)
                if branch_taken:
                    self.run([x for x in n.children if x.key != "limit"], tag)
            elif n.key == "else_if":
                assert branch_taken is not None, "else_if without if"
                if not branch_taken and self.check(n.get("limit", []), tag):
                    branch_taken = True
                    self.run([x for x in n.children if x.key != "limit"], tag)
            elif n.key == "else":
                assert branch_taken is not None, "else without if"
                if not branch_taken:
                    self.run(n.children, tag)
                branch_taken = True
            elif n.key == "hidden_effect":
                self.run(n.children, tag)
            elif n.key == "complete_national_focus":
                # The production entry explicitly runs the idempotent campaign effect.
                self.countries[tag].focuses.add(n.value)
            elif n.key in ("ROOT", "FROM"):
                self.run(n.children, self.resolve(n.key))
            elif n.key == "add_stability":
                self.countries[tag].stability += float(n.value)
            elif n.key == "add_tech_bonus":
                self.countries[tag].bonuses.append(copy.deepcopy(n.children))
            elif n.key == "country_event":
                assert not n.get("random_days"), "Random event scheduling is not modelled"
                delay = float(n.get("days", 0)) + float(n.get("hours", 0)) / 24
                self.scheduled.append((self.day + delay, tag, n.get("id"), self.root))
                super().run([n], tag)
            elif n.key in ("random_owned_state", "every_owned_state"):
                eligible = [s for s in self.states if s.owner == tag and self.check(n.get("limit", []), s)]
                selected = eligible[:1] if n.key == "random_owned_state" else eligible
                for state in selected:
                    self.run([x for x in n.children if x.key != "limit"], state)
            elif n.key == "add_extra_state_shared_building_slots":
                assert isinstance(tag, State)
                tag.extra_slots += int(n.value)
                tag.capacity += int(n.value)
            elif n.key == "add_building_construction":
                assert isinstance(tag, State) and n.get("instant_build") == "yes"
                building = n.get("type")
                tag.buildings[building] = tag.buildings.get(building, 0) + int(n.get("level"))
            else:
                super().run([n], tag)

    def advance_days(self, days):
        super().advance_days(days)
        self.day += days

    def deliver(self, event_id, tag):
        """Deliver one due packet; failed triggers discard it, as in scripted events."""
        packet = next((p for p in self.scheduled if p[1:3] == (tag, event_id) and p[0] <= self.day), None)
        assert packet is not None, f"No due {event_id} for {tag} on day {self.day}"
        self.scheduled.remove(packet)
        self.root, self.sender = tag, packet[3]
        event = self.events[event_id]
        if not self.countries[tag].exists or not self.check(event.get("trigger", []), tag):
            return False
        self.run(event.get("immediate", []), tag)
        return True

    def daily(self):
        for tag in HOUSES:
            self.root = tag
            self.run(self.hooks.get("on_daily_" + tag, []), tag)

    def war_between(self, attacker, defender):
        for tag, other in ((attacker, defender), (defender, attacker)):
            self.countries[tag].wars.add(other)
            self.countries[tag].war = True
        self.countries[attacker].offensive_wars.add(defender)
        self.countries[defender].defensive_wars.add(attacker)
        self.root, self.sender = attacker, defender
        self.run(self.hooks.get("on_war_relation_added", []), attacker)
        self.daily()

    def focus(self, suffix):
        return self.focuses["HSM_AVI_" + suffix]

    def available(self, suffix):
        focus = self.focus(suffix)
        self.root = "AVI"
        return self.check(focus.get("available", []), "AVI")

    def ai_weight(self, suffix):
        self.root = "AVI"
        weight = Node("ai", "=", self.focus(suffix).get("ai_will_do", []))
        result = float(weight.get("factor", 1))
        for modifier in weight.all("modifier"):
            assert all(n.key not in ("add", "base") for n in modifier.children)
            if self.check([n for n in modifier.children if n.key != "factor"]):
                result *= float(modifier.get("factor", 1))
        return result

    def reward(self, suffix):
        """Unit-execute a completion reward; prerequisite graph is tested separately."""
        self.root = "AVI"
        self.countries["AVI"].focuses.add("HSM_AVI_" + suffix)
        self.run(self.focus(suffix).get("completion_reward", []), "AVI")

    def route(self):
        self.countries["AVI"].focuses.add("treaty_of_friendship")
        assert self.available("three_separate_seals")
        self.reward("three_separate_seals")

    def tripartite(self):
        self.route()
        self.charter()
        self.choose("hsm_verenia.63", 0, "AVI")
        assert all("HSM_VER_charter_signed" in self.countries[t].flags for t in HOUSES)

    def can_decide(self, suffix):
        self.root = "AVI"
        decision = self.decisions["HSM_AVI_" + suffix]
        return self.check(decision.get("visible", [])) and self.check(decision.get("available", []))

    def decide(self, suffix):
        assert self.can_decide(suffix), f"Unavailable decision: {suffix}"
        decision = self.decisions["HSM_AVI_" + suffix]
        self.countries["AVI"].political_power -= float(decision.get("cost", 0))
        self.run(decision.get("complete_effect", []))

    def complete(self, suffix):
        focus = self.focus(suffix)
        completed = self.countries["AVI"].focuses
        assert all(any(n.value in completed for n in p.children) for p in focus.all("prerequisite")), suffix
        assert all(n.value not in completed for p in focus.all("mutually_exclusive") for n in p.children), suffix
        assert "HSM_AVI_" + suffix not in completed, suffix
        assert self.available(suffix), suffix
        self.reward(suffix)

    def budget(self, responses=(0, 0)):
        self.tripartite()
        self.reward("common_accounts")
        self.advance_days(1)
        for tag, response in zip(("ERI", "EYR"), responses):
            assert self.deliver("hsm_ver_avian.20", tag)
            if response is not None:
                self.choose("hsm_ver_avian.20", response, tag)

    def levy(self, option=0):
        self.budget()
        self.reward("the_first_common_budget")
        self.advance_days(1)
        assert self.deliver("hsm_ver_avian.10", "AVI")
        self.choose("hsm_ver_avian.10", 0, "AVI")
        self.reward("the_unauthorised_levy")
        self.advance_days(1)
        assert self.deliver("hsm_ver_avian.30", "AVI")
        self.choose("hsm_ver_avian.30", option, "AVI")

    def descriptions(self, event_id, tag="AVI"):
        self.root = tag
        return [n.get("text") for n in self.events[event_id].all("desc")
                if n.children and self.check(n.get("trigger", []), tag)]


class Harness(unittest.TestCase):
    def test_state_tooltip_wrappers_preserve_predicates(self):
        world = AvianWorld()
        predicates = (
            "is_core_of = ROOT is_fully_controlled_by = ROOT "
            "free_building_slots = { building = industrial_complex size > 0 include_locked = yes }"
        )
        plain = BASE["parse"](predicates)
        wrapped = BASE["parse"](
            "hidden_trigger = { custom_trigger_tooltip = { tooltip = state_note "
            + predicates + " } }"
        )
        for state, expected in (
            (State(), True), (State(cores=set()), False),
            (State(controller="GRI"), False), (State(capacity=0), False),
        ):
            with self.subTest(state=state):
                self.assertEqual(world.check(plain, state), expected)
                self.assertEqual(world.check(wrapped, state), expected)
        with self.assertRaisesRegex(AssertionError, "Unsupported state predicate"):
            world.check(BASE["parse"]("hidden_trigger = { unsupported_state_predicate = yes }"), State())

    def test_tooltips_are_not_gameplay_and_hidden_effects_still_execute(self):
        world = AvianWorld()
        before = copy.deepcopy((world.countries, world.trace))
        world.run(BASE["parse"]("custom_effect_tooltip = note show_ideas_tooltip = preview"))
        self.assertEqual((world.countries, world.trace), before)
        world.run(BASE["parse"]("hidden_effect = { add_political_power = -35 }"))
        self.assertEqual(world.countries["AVI"].political_power, -35)

    def test_unknown_operations_fail_closed(self):
        world = AvianWorld()
        with self.assertRaisesRegex(AssertionError, "no predicate"):
            world.check([Node("unsupported_test_predicate", "=", "yes")])
        with self.assertRaisesRegex(AssertionError, "no effect"):
            world.run([Node("unsupported_test_effect", "=", "yes")])

    def test_extended_effects_keep_conditional_chains(self):
        world = AvianWorld()
        world.run(BASE["parse"]("if = { limit = { always = yes } add_stability = 0.06 } else = { add_political_power = 999 }"))
        self.assertAlmostEqual(world.countries["AVI"].stability, 0.56)
        self.assertEqual(world.countries["AVI"].political_power, 0)


class AvianFixture(unittest.TestCase):
    def setUp(self):
        self.w = AvianWorld()
        self.avi = self.w.countries["AVI"]
        self.assertIn(ROOT_FOCUS, self.w.focuses, "Production Avian branch has not been written yet")


class NativeSplit(AvianFixture):
    def test_exact_focus_inventory_layout_and_graph(self):
        focuses = {k: n for k, n in self.w.focuses.items() if k.startswith("HSM_AVI_")}
        self.assertEqual(set(focuses), {"HSM_AVI_" + s for s in LAYOUT})
        for suffix, position in LAYOUT.items():
            focus = self.w.focus(suffix)
            self.assertFalse(focus.all("relative_position_id"))
            self.assertEqual((int(focus.get("x")), int(focus.get("y"))), position)
        done = {"treaty_of_friendship"}
        while set(focuses) - done:
            ready = {key for key, focus in focuses.items() if key not in done and all(any(n.value in done for n in p.children) for p in focus.all("prerequisite"))}
            self.assertTrue(ready, "Cycle or an undeclared prerequisite in Avian branch")
            done |= ready

    def test_only_initial_native_tree_imports_constitutional_continuations(self):
        trees = [n for n in read(MOD / "common/national_focus/AVI.txt") if n.key == "focus_tree"]
        for root in (ROOT_FOCUS, UNIFICATION_ROOT):
            imports = [n.get("id") for n in trees if root in [f.value for f in n.all("shared_focus")]]
            self.assertEqual(imports, ["avian"])
        self.assertEqual([n.value for p in self.w.focus("three_separate_seals").all("mutually_exclusive") for n in p.children], ["the_second_winterfest_ball"])
        full = self.w.focuses["full_integration"]
        self.assertFalse(full.all("mutually_exclusive"))
        ball = self.w.focuses["the_second_winterfest_ball"]
        self.assertIn(ROOT_FOCUS, [n.value for p in ball.all("mutually_exclusive") for n in p.children])

    def test_native_inventory_coordinates_and_prerequisites_preserved(self):
        native = read(OPT.eaw / "common/national_focus/AVI.txt")
        current = read(MOD / "common/national_focus/AVI.txt")
        self.assertEqual([(n.key, n.get("id")) for n in native], [(n.key, n.get("id")) for n in current])
        for old, new in zip(native, current):
            for key in ("x", "y", "relative_position_id", "prerequisite"):
                expected = copy.deepcopy(old.all(key))
                if old.get("id") == "the_second_winterfest_ball" and key == "prerequisite":
                    for group, alternative in zip(expected, ("technological_cooperation", "unified_railroad_network")):
                        group.children.append(Node("focus", "=", alternative))
                self.assertEqual(expected, new.all(key), (old.get("id"), key))
            if old.key == "focus_tree":
                additions = {"avian": {ROOT_FOCUS, UNIFICATION_ROOT, "HSM_VER_REG_after_defence"}, "avian_fascists": {"HSM_ZYP_victory_roll"}}
                self.assertEqual(old.all("shared_focus"), [n for n in new.all("shared_focus") if n.value not in additions.get(new.get("id"), set())])

    def test_other_native_political_branches_and_leader_rewards_are_preserved(self):
        native = {n.get("id"): n for n in read(OPT.eaw / "common/national_focus/AVI.txt") if n.key == "shared_focus"}
        protected = {"pursue_true_neutrality", "communists_win", "loyalists_win", "fascists_win", "foundation_allowed"}
        while True:
            descendants = {key for key, node in native.items() if any(p.value in protected for group in node.all("prerequisite") for p in group.children)}
            if descendants <= protected:
                break
            protected |= descendants
        protected |= {"leaders_field_marshalls", "tripartite_legion", "proclamation_of_neutrality", "intergigantes"}
        for key in protected:
            self.assertEqual(BASE["pre_union_idea_operations"]([native[key]]),
                             BASE["pre_union_idea_operations"]([self.w.focuses[key]]), key)
        # Tooltip wrappers may change; the native crisis effects must not.
        ui = runpy.run_path(str(Path(__file__).with_name("Test-VereniaFocusUI.py")))
        rewards = []
        for source in (OPT.eaw, MOD):
            focus = ui["focus_records"](ui["read"](source / "common/national_focus/AVI.txt"))["the_second_winterfest_ball"]
            rewards.append(ui["canonical"](ui["sections"](focus, "completion_reward"), "effect"))
        self.assertEqual(*rewards)

    def test_peaceful_entry_requires_intergigantes_not_common_proclamation(self):
        self.avi.focuses = {"treaty_of_friendship", "proclamation_of_neutrality"}
        self.assertFalse(self.w.available("three_separate_seals"))
        self.avi.focuses.add("intergigantes")
        self.assertTrue(self.w.available("three_separate_seals"))
        self.avi.focuses.add("pursue_true_neutrality")
        self.assertFalse(self.w.available("three_separate_seals"))
        self.avi.focuses.remove("pursue_true_neutrality")
        self.w.reward("three_separate_seals")
        self.assertTrue(self.w.test("HSM_VER_AVI_route_active"))
        self.avi.focuses.remove("intergigantes")
        self.assertFalse(self.w.test("HSM_VER_AVI_route_active"))

    def test_native_integration_enters_campaign_without_puppets_or_coup(self):
        self.avi.focuses.update({"treaty_of_friendship", "full_integration"})
        for tag in ("ERI", "EYR"):
            self.w.countries[tag].flags.add("HSM_VER_avian_vassalisation_accepted")
        focus = self.w.focuses["full_integration"]
        self.assertTrue(self.w.check(focus.get("available")))
        self.w.run(focus.get("completion_reward"))
        self.assertIn(ROOT_FOCUS, self.avi.focuses)
        self.assertIn("HSM_AVI_preserved_union", self.avi.flags)
        for tag in ("ERI", "EYR"):
            self.assertNotIn("HSM_VER_avian_vassalisation_accepted", self.w.countries[tag].flags)
            self.assertFalse(self.w.test("HSM_VER_CR_integration_retry_valid", tag))
        self.assertTrue(all(c.exists and not c.subject for c in self.w.countries.values()))
        self.assertFalse({"avian.5", "avian.6", "avian.10", "avi_news.3"} & {p[2] for p in self.w.scheduled})
        before = copy.deepcopy(self.w.countries)
        scheduled = list(self.w.scheduled)
        self.w.run(focus.get("completion_reward"))
        self.w.apply("HSM_VER_AVI_start_campaign", "AVI")
        self.assertEqual(self.w.countries, before)
        self.assertEqual(self.w.scheduled, scheduled)

    def test_old_constitutional_save_needs_no_native_full_integration(self):
        self.w.route()
        self.assertNotIn("full_integration", self.avi.focuses)
        self.assertFalse(self.w.focus("three_separate_seals").all("prerequisite"))
        self.assertTrue(self.w.check(self.w.focuses["full_integration"].get("bypass")))
        self.w.complete("two_legible_copies")
        self.w.complete("hear_the_towns")
        self.assertTrue(self.w.available("charter_without_submission"))
        self.avi.focuses.add("full_integration")
        self.assertTrue(self.w.test("HSM_VER_AVI_route_active"))

    def test_legacy_queued_vassal_request_rejects_constitutional_commitment(self):
        self.avi.focuses.update({"treaty_of_friendship", "full_integration"})
        self.w.apply("HSM_VER_AVI_begin_integration", "AVI")
        events = {n.get("id"): n for n in read(MOD / "events/Avian Events.txt") if n.key == "country_event"}
        invitation = events["avian.5"]
        accept = next(n for n in invitation.all("option") if n.get("name") == "avian.5.a")
        for tag in ("ERI", "EYR"):
            self.assertFalse(self.w.check(invitation.get("trigger"), tag), tag)
            # The same guard must also close an option opened before the route changed.
            guard = next(n for n in BASE["effect_nodes"](accept.children) if n.key == "if")
            self.assertFalse(self.w.check(guard.get("limit"), tag), tag)

    def test_native_crisis_is_explicit_choice_reachable_without_puppet_shortcut(self):
        self.avi.focuses.update({"treaty_of_friendship", "technological_cooperation", "unified_railroad_network"})
        ball = self.w.focuses["the_second_winterfest_ball"]
        self.assertTrue(all(any(n.value in self.avi.focuses for n in p.children) for p in ball.all("prerequisite")))
        self.assertTrue(self.w.check(ball.get("available")))
        self.assertFalse(any(c.subject for c in self.w.countries.values()))
        self.w.reward("three_separate_seals")
        self.assertFalse(self.w.check(ball.get("available")))
        self.assertNotIn("avian.10", self.avi.events)

    def test_native_entry_rechecks_government_and_preserves_existing_charter(self):
        self.w.tripartite()
        self.avi.focuses.add("full_integration")
        before = copy.deepcopy(self.w.countries)
        self.w.apply("HSM_VER_AVI_begin_integration", "AVI")
        self.assertEqual(self.w.countries, before)
        for invalid in ("pursue_true_neutrality", "fascists_win", "communists_win", "loyalists_win", "the_second_winterfest_ball"):
            world = AvianWorld()
            world.countries["AVI"].focuses.update({"treaty_of_friendship", "full_integration", invalid})
            world.apply("HSM_VER_AVI_begin_integration", "AVI")
            self.assertNotIn(ROOT_FOCUS, world.countries["AVI"].focuses)
            self.assertFalse(world.scheduled)

    def test_unification_root_position_and_settlement_handoff(self):
        self.assertIn(UNIFICATION_ROOT, self.w.focuses)
        root = self.w.focuses[UNIFICATION_ROOT]
        self.assertEqual((root.get("x"), root.get("y")), ("24", "2"))
        offsets = [n for n in root.all("offset") if self.w.check(n.get("trigger", []))]
        self.assertEqual(sum(int(n.get("x", 0)) for n in offsets), 34)
        self.assertEqual(24 + sum(int(n.get("x", 0)) for n in offsets), 58)
        self.w.levy()
        self.assertFalse(self.w.check(root.get("available")))
        self.w.reward("a_union_worth_keeping")
        self.assertTrue(self.w.check(root.get("available")))
        for tag in HOUSES:
            self.w.countries[tag].faction = "Intergigantes"
        self.avi.faction_leader = True
        self.assertTrue(self.w.check(root.get("available")))
        # Native entry must lead to the same convention as a pre-rework save.
        self.avi.focuses.add("full_integration")
        self.assertTrue(self.w.check(root.get("available")))

    def test_entry_requires_native_friendship_and_free_living_houses(self):
        self.assertFalse(self.w.available("three_separate_seals"))
        self.avi.focuses.add("treaty_of_friendship")
        self.assertTrue(self.w.available("three_separate_seals"))
        for tag, attr in itertools.product(HOUSES, ("exists", "subject", "capitulated")):
            with self.subTest(tag=tag, attribute=attr):
                country = self.w.countries[tag]
                original = getattr(country, attr)
                setattr(country, attr, attr != "exists")
                self.assertFalse(self.w.available("three_separate_seals"))
                setattr(country, attr, original)

    def test_entry_rejects_late_regimes_ball_and_broken_native_peace(self):
        self.avi.focuses.add("treaty_of_friendship")
        for focus in ("the_second_winterfest_ball", "fascists_win", "communists_win", "loyalists_win", "foundation_allowed", "pursue_true_neutrality"):
            with self.subTest(focus=focus):
                self.avi.focuses.add(focus)
                self.assertFalse(self.w.available("three_separate_seals"))
                self.avi.focuses.remove(focus)
        self.avi.leader = "another_government"
        self.assertFalse(self.w.available("three_separate_seals"))
        self.avi.leader = "AVI_lady_katrina_avian"
        self.w.countries["ERI"].flags.add("HSM_VER_treaty_broken")
        self.assertFalse(self.w.available("three_separate_seals"))

    def test_entry_adopts_peace_but_not_charter_or_subordination(self):
        self.w.route()
        self.assertIn("HSM_AVI_preserved_union", self.avi.flags)
        self.assertIn("HSM_VER_congress_observer", self.avi.flags)
        self.assertTrue(self.w.test("HSM_VER_negotiated_peace_valid"))
        for tag in HOUSES:
            self.assertNotIn("HSM_VER_charter_signed", self.w.countries[tag].flags)
            self.assertFalse(self.w.countries[tag].subject)
            self.assertTrue(self.w.countries[tag].exists)
        self.assertIn("AVI_linguistic_antagonism", self.avi.ideas)

    def test_entry_rejects_each_inter_house_war(self):
        self.avi.focuses.add("treaty_of_friendship")
        for left, right in itertools.combinations(HOUSES, 2):
            with self.subTest(pair=(left, right)):
                self.w.countries[left].wars.add(right)
                self.w.countries[right].wars.add(left)
                self.assertFalse(self.w.available("three_separate_seals"))
                self.w.countries[left].wars.clear()
                self.w.countries[right].wars.clear()

    def test_native_ai_paths_suppress_weight_but_never_player_availability(self):
        self.avi.focuses.add("treaty_of_friendship")
        paths = ("HISTORICAL", "NEUTRAL_ALTERNATE", "HARMONY_ALTERNATE", "FASCIST_ALTERNATE", "COMMUNIST_ALTERNATE")
        for path in paths:
            with self.subTest(flag=path):
                flag = "AVI_AI_" + path
                self.avi.flags.add(flag)
                self.assertEqual(self.w.ai_weight("three_separate_seals"), 0)
                self.assertTrue(self.w.available("three_separate_seals"))
                self.avi.flags.remove(flag)
            with self.subTest(rule=path):
                self.w.game_rules["AVI_ai_behavior"] = path if path == "HISTORICAL" else "AVI_" + path
                self.assertEqual(self.w.ai_weight("three_separate_seals"), 0)
                self.assertTrue(self.w.available("three_separate_seals"))
                self.w.game_rules["AVI_ai_behavior"] = "DEFAULT"
        self.w.historical = True
        self.assertEqual(self.w.ai_weight("three_separate_seals"), 0)
        self.assertTrue(self.w.available("three_separate_seals"))
        self.w.historical = False
        self.assertGreater(self.w.ai_weight("three_separate_seals"), 0)


class CharterConsent(AvianFixture):
    def test_sponsorship_uses_bilateral_handshake_then_separate_avian_assent(self):
        self.w.route()
        self.w.reward("charter_without_submission")
        self.assertIn("HSM_VER_charter_pending", self.w.countries["ERI"].flags)
        self.assertFalse(any("HSM_VER_charter_signed" in c.flags for c in self.w.countries.values()))
        self.w.advance_days(1)
        self.assertTrue(self.w.deliver("hsm_verenia.60", "ERI"))
        self.w.choose("hsm_verenia.60", 0, "ERI")
        self.w.advance_days(1)
        self.assertTrue(self.w.deliver("hsm_verenia.61", "EYR"))
        self.w.choose("hsm_verenia.61", 0, "EYR")
        self.assertNotIn("HSM_VER_charter_signed", self.avi.flags)
        bypass = self.w.focus("charter_without_submission").get("bypass")
        self.assertFalse(self.w.check(bypass))
        self.w.advance_days(1)
        self.assertTrue(self.w.deliver("hsm_verenia.63", "AVI"))
        self.w.choose("hsm_verenia.63", 0, "AVI")
        self.assertTrue(self.w.check(bypass))
        self.assertTrue(self.w.available("common_accounts"))

    def test_bilateral_timeout_opens_fallback_and_cooldown_retry(self):
        self.w.route()
        self.w.reward("charter_without_submission")
        self.assertFalse(self.w.available("neighbours_without_a_chair"))
        self.w.advance_days(45)
        self.assertTrue(self.w.deliver("hsm_verenia.69", "ERI"))
        self.assertTrue(self.w.available("neighbours_without_a_chair"))
        self.w.reward("neighbours_without_a_chair")
        self.assertFalse(self.w.can_decide("reconvene_charter"))
        self.w.advance_days(75)
        self.assertTrue(self.w.can_decide("reconvene_charter"))
        self.w.decide("reconvene_charter")
        self.assertEqual(self.avi.political_power, -35)
        self.assertIn("HSM_VER_charter_pending", self.w.countries["ERI"].flags)
        self.assertIn("HSM_AVI_independent_settlement", self.avi.flags)

    def test_avian_refusal_fallback_then_explicit_reconsideration(self):
        self.w.route()
        self.w.reward("charter_without_submission")
        self.w.charter()
        self.w.choose("hsm_verenia.63", 1, "AVI")
        self.assertTrue(self.w.available("neighbours_without_a_chair"))
        self.w.daily()
        self.assertNotIn("HSM_VER_avian_charter_pending", self.avi.flags)
        self.w.decide("reaffirm_membership")
        self.assertEqual(self.avi.political_power, -25)
        self.assertIn("HSM_VER_avian_charter_pending", self.avi.flags)
        self.w.choose("hsm_verenia.63", 0, "AVI")
        self.assertTrue(self.w.test("HSM_VER_AVI_three_party_charter"))
        self.assertFalse(self.w.can_decide("reaffirm_membership"))

    def test_repeated_sponsors_do_not_duplicate_pending_offers(self):
        self.w.route()
        self.w.reward("charter_without_submission")
        before = list(self.w.scheduled)
        for tag in HOUSES:
            self.w.apply("HSM_VER_AVI_sponsor_charter", tag)
        self.assertEqual(self.w.scheduled, before)

    def test_native_avian_led_league_is_recognised_without_transfer(self):
        self.w.tripartite()
        for tag in HOUSES:
            self.w.countries[tag].faction = "Intergigantes"
        self.avi.faction_leader = True
        self.assertTrue(self.w.test("HSM_VER_can_form_defensive_league"))
        self.w.apply("HSM_VER_offer_defence")
        self.w.choose("hsm_verenia.80", 0, "EYR")
        self.w.daily()
        self.assertTrue(self.w.test("HSM_VER_defence_league_operational"))
        for tag in HOUSES:
            self.assertEqual(self.w.countries[tag].faction, "Intergigantes")
        self.assertTrue(self.avi.faction_leader)
        self.assertIn("HSM_VER_defence_accepted", self.w.countries["ERI"].flags)
        self.w.countries["EYR"].faction = "unrelated"
        self.w.daily()
        self.assertNotIn("HSM_VER_defence_accepted", self.w.countries["ERI"].flags)


class BudgetProtocol(AvianFixture):
    def test_lost_annexation_timeout_expires_pending_and_keeps_retry_guard(self):
        for recipient in ("ERI", "EYR"):
            with self.subTest(recipient=recipient):
                world = AvianWorld()
                world.budget((None, 0) if recipient == "ERI" else (0, None))
                country = world.countries[recipient]
                country.exists = False
                world.advance_days(29)
                self.assertFalse(world.deliver("hsm_ver_avian.29", recipient))
                self.assertIn("HSM_AVI_budget_pending", country.flags)
                country.exists = True
                world.advance_days(14)
                world.daily()
                self.assertNotIn("HSM_AVI_budget_answered", country.flags)
                world.advance_days(2)
                world.daily()
                self.assertNotIn("HSM_AVI_budget_pending", country.flags)
                self.assertIn("HSM_AVI_budget_answered", country.flags)
                self.assertTrue(world.available("the_first_common_budget"))
                world.choose("hsm_ver_avian.20", 0, recipient)
                self.assertEqual(country.political_power, 0)
                self.assertNotIn("HSM_AVI_budget_signed", country.flags)
                self.assertFalse(world.can_decide("reopen_budget"))
                world.advance_days(43)
                self.assertFalse(world.can_decide("reopen_budget"))
                world.advance_days(1)
                world.decide("reopen_budget")
                self.assertIn("HSM_AVI_budget_pending", country.flags)
                self.assertNotIn("HSM_AVI_budget_answered", country.flags)
                world.choose("hsm_ver_avian.20", 0, recipient)
                self.assertEqual(country.political_power, -35)

    def test_reconcile_cannot_recreate_answers_after_war_voids_protocol(self):
        self.w.budget((None, None))
        self.w.war_between("AVI", "ERI")
        self.w.advance_days(100)
        for country in self.w.countries.values():
            country.wars.clear()
            country.offensive_wars.clear()
            country.defensive_wars.clear()
            country.war = False
        self.w.daily()
        self.w.charter()
        self.w.decide("reaffirm_membership")
        self.w.choose("hsm_verenia.63", 0, "AVI")
        self.w.daily()
        for tag in HOUSES:
            self.w.apply("HSM_VER_AVI_reconcile_budget_answer", tag)
            self.assertNotIn("HSM_AVI_budget_answered", self.w.countries[tag].flags)
            self.assertNotIn("HSM_AVI_budget_signed", self.w.countries[tag].flags)
        self.assertFalse(self.w.available("the_first_common_budget"))
        self.assertTrue(self.w.can_decide("reopen_budget"))

    def test_all_acceptance_refusal_combinations_and_truthful_descriptions(self):
        for responses in itertools.product((0, 1), repeat=2):
            with self.subTest(responses=responses):
                world = AvianWorld()
                world.budget(responses)
                accepted = sum(r == 0 for r in responses)
                for tag, response in zip(("ERI", "EYR"), responses):
                    country = world.countries[tag]
                    self.assertEqual(country.political_power, -35 if response == 0 else 0)
                    self.assertEqual("HSM_AVI_budget_signed" in country.flags, response == 0)
                    self.assertEqual("HSM_AVI_common_budget" in country.ideas, response == 0)
                    self.assertIn("HSM_AVI_budget_answered", country.flags)
                self.assertEqual("HSM_AVI_common_budget" in world.countries["AVI"].ideas, accepted > 0)
                self.assertTrue(world.available("the_first_common_budget"))
                key = {0: "d", 1: "one.d", 2: "both.d"}[accepted]
                self.assertEqual(world.descriptions("hsm_ver_avian.10"), ["hsm_ver_avian.10." + key])

    def test_recipient_scopes_ignore_sender_and_uninvited_countries(self):
        self.w.budget((None, None))
        self.w.sender = "GRI"
        self.w.choose("hsm_ver_avian.20", 0, "ERI")
        self.w.choose("hsm_ver_avian.20", 1, "EYR")
        self.w.choose("hsm_ver_avian.20", 0, "GRI")
        self.w.choose("hsm_ver_avian.20", 0, "AVI")
        self.assertEqual([self.w.countries[t].political_power for t in ("ERI", "EYR", "AVI", "GRI")], [-35, 0, 0, 0])

    def test_duplicate_reply_and_repeated_offer_are_idempotent(self):
        self.w.budget((0, None))
        before = copy.deepcopy(self.w.countries)
        scheduled = list(self.w.scheduled)
        self.w.choose("hsm_ver_avian.20", 0, "ERI")
        self.w.choose("hsm_ver_avian.20", 1, "ERI")
        self.w.apply("HSM_VER_AVI_offer_budget", "AVI")
        self.assertEqual(self.w.countries, before)
        self.assertEqual(self.w.scheduled, scheduled)

    def test_timeout_unblocks_budget_without_cost_and_rejects_late_reply(self):
        self.w.budget((None, None))
        self.w.advance_days(29)
        for tag in ("ERI", "EYR"):
            self.assertTrue(self.w.deliver("hsm_ver_avian.29", tag))
            self.w.choose("hsm_ver_avian.20", 0, tag)
            self.assertNotIn("HSM_AVI_budget_signed", self.w.countries[tag].flags)
            self.assertEqual(self.w.countries[tag].political_power, 0)
        self.assertTrue(self.w.available("the_first_common_budget"))
        self.assertFalse(self.w.can_decide("reopen_budget"))
        self.w.advance_days(60)
        self.w.decide("reopen_budget")
        self.assertEqual(self.avi.political_power, -35)
        for tag in ("ERI", "EYR"):
            self.assertIn("HSM_AVI_budget_pending", self.w.countries[tag].flags)

    def test_reoffer_only_unsigned_house_and_old_timeout_cannot_cancel_new_offer(self):
        self.w.budget((0, 1))
        self.w.advance_days(29)
        for tag in ("ERI", "EYR"):
            self.assertFalse(self.w.deliver("hsm_ver_avian.29", tag))
        self.w.advance_days(60)
        self.w.decide("reopen_budget")
        self.w.choose("hsm_ver_avian.29", 0, "EYR")
        self.assertIn("HSM_AVI_budget_pending", self.w.countries["EYR"].flags)
        self.assertNotIn("HSM_AVI_budget_pending", self.w.countries["ERI"].flags)
        self.w.choose("hsm_ver_avian.20", 0, "EYR")
        self.assertEqual(self.w.countries["ERI"].political_power, -35)
        self.assertEqual(self.w.countries["EYR"].political_power, -35)
        self.assertFalse(self.w.can_decide("reopen_budget"))

    def test_stale_reply_during_occupation_or_after_government_change(self):
        for changed_tag, attr, value in (("ERI", "capitulated", True), ("EYR", "subject", True), ("AVI", "leader", "other")):
            with self.subTest(tag=changed_tag, attr=attr):
                world = AvianWorld()
                world.budget((None, None))
                setattr(world.countries[changed_tag], attr, value)
                world.daily()
                for tag in ("ERI", "EYR"):
                    world.choose("hsm_ver_avian.20", 0, tag)
                    self.assertEqual(world.countries[tag].political_power, 0)
                    self.assertNotIn("HSM_AVI_budget_signed", world.countries[tag].flags)

    def test_occupation_pauses_benefits_without_erasing_consent_or_recharging(self):
        self.w.budget()
        for tag in HOUSES:
            with self.subTest(occupied=tag):
                self.w.countries[tag].capitulated = True
                self.w.daily()
                for participant in HOUSES:
                    self.assertNotIn("HSM_AVI_common_budget", self.w.countries[participant].ideas)
                    self.assertIn("HSM_AVI_budget_signed", self.w.countries[participant].flags)
                self.w.countries[tag].capitulated = False
                self.w.daily()
                self.assertTrue(all("HSM_AVI_common_budget" in self.w.countries[t].ideas for t in HOUSES))
        self.assertEqual(self.w.countries["ERI"].political_power, -35)

    def test_inter_house_war_voids_budget_and_stale_replies_even_after_rechartering(self):
        for left, right in itertools.combinations(HOUSES, 2):
            with self.subTest(pair=(left, right)):
                world = AvianWorld()
                world.budget((0, None))
                world.war_between(left, right)
                for tag in HOUSES:
                    self.assertNotIn("HSM_AVI_budget_signed", world.countries[tag].flags)
                    self.assertNotIn("HSM_AVI_common_budget", world.countries[tag].ideas)
                world.choose("hsm_ver_avian.20", 0, "EYR")
                self.assertEqual(world.countries["EYR"].political_power, 0)
                for tag in HOUSES:
                    world.countries[tag].wars.clear()
                    world.countries[tag].war = False
                world.charter()
                world.countries["AVI"].flags.add("HSM_VER_congress_observer")
                world.apply("HSM_VER_offer_avian_charter", "AVI")
                world.choose("hsm_verenia.63", 0, "AVI")
                world.daily()
                self.assertTrue(world.test("HSM_VER_AVI_three_party_charter"))
                self.assertTrue(all("HSM_AVI_common_budget" not in world.countries[t].ideas for t in HOUSES))
                world.advance_days(90)
                world.decide("reopen_budget")
                world.choose("hsm_ver_avian.20", 0, "EYR")
                self.assertEqual(world.countries["EYR"].political_power, -35)
                self.assertIn("HSM_AVI_common_budget", world.countries["AVI"].ideas)

    def test_daily_war_detection_covers_each_pair_if_war_hook_was_missed(self):
        for left, right in itertools.combinations(HOUSES, 2):
            with self.subTest(pair=(left, right)):
                world = AvianWorld()
                world.budget()
                world.countries[left].wars.add(right)
                world.countries[right].wars.add(left)
                world.daily()
                self.assertTrue(all("HSM_AVI_budget_signed" not in world.countries[t].flags for t in HOUSES))

    def test_native_ball_regime_milestones_and_leader_removal_void_signatures(self):
        for milestone in ("the_second_winterfest_ball", "communists_win", "loyalists_win", "fascists_win", "leader_change"):
            with self.subTest(milestone=milestone):
                world = AvianWorld()
                world.budget()
                avian = world.countries["AVI"]
                if milestone == "leader_change":
                    avian.leader = "another_leader"
                else:
                    avian.focuses.add(milestone)
                world.daily()
                for tag in HOUSES:
                    self.assertNotIn("HSM_AVI_budget_signed", world.countries[tag].flags)
                    self.assertNotIn("HSM_AVI_common_budget", world.countries[tag].ideas)
                avian.leader = "AVI_lady_katrina_avian"
                avian.focuses.discard(milestone)
                world.daily()
                self.assertTrue(all("HSM_AVI_common_budget" not in world.countries[t].ideas for t in HOUSES))


class PolicyAndRecovery(AvianFixture):
    def test_rejoining_charter_does_not_temporarily_forgive_unresolved_levy(self):
        self.w.levy(1)
        self.w.war_between("AVI", "EYR")
        for country in self.w.countries.values():
            country.wars.clear()
            country.offensive_wars.clear()
            country.defensive_wars.clear()
            country.war = False
        self.w.advance_days(90)
        self.w.daily()
        self.assertIn("HSM_AVI_levy_exception", self.avi.flags)
        self.w.decide("reaffirm_membership")
        self.w.choose("hsm_verenia.63", 0, "AVI")
        # Reconciliation must happen in the reply, before another decision can run.
        self.assertFalse(self.w.test("HSM_VER_AVI_three_party_charter"))
        self.assertNotIn("HSM_VER_common_courts", self.avi.ideas)
        self.assertFalse(self.w.can_decide("reopen_budget"))

    def test_language_options_are_exclusive_idempotent_and_preserve_native_conflict(self):
        for option, idea, cost in ((0, "HSM_AVI_translation_office", -50), (1, "HSM_AVI_local_clerks", 0)):
            with self.subTest(option=option):
                world = AvianWorld()
                world.route()
                world.reward("two_legible_copies")
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_avian.2", "AVI"))
                world.choose("hsm_ver_avian.2", option, "AVI")
                world.choose("hsm_ver_avian.2", 1 - option, "AVI")
                country = world.countries["AVI"]
                self.assertEqual(country.political_power, cost)
                self.assertEqual(country.ideas & {"HSM_AVI_translation_office", "HSM_AVI_local_clerks"}, {idea})
                self.assertIn("AVI_linguistic_antagonism", country.ideas)
                count = country.events.count("hsm_ver_avian.2")
                world.advance_days(90)
                world.daily()
                self.assertEqual(country.events.count("hsm_ver_avian.2"), count)

    def test_completed_policy_scenes_retry_after_lost_delivery_without_daily_spam(self):
        for suffix, event_id, resolved in (
            ("two_legible_copies", "2", "language_resolved"),
            ("the_first_common_budget", "10", "budget_reviewed"),
            ("the_unauthorised_levy", "30", "levy_resolved"),
        ):
            with self.subTest(scene=event_id):
                world = AvianWorld()
                world.budget()
                if event_id == "30":
                    world.countries["AVI"].flags.add("HSM_AVI_budget_reviewed")
                world.reward(suffix)
                world.countries["AVI"].capitulated = True
                world.advance_days(1)
                self.assertFalse(world.deliver("hsm_ver_avian." + event_id, "AVI"))
                world.choose("hsm_ver_avian." + event_id, 0, "AVI")
                self.assertNotIn("HSM_AVI_" + resolved, world.countries["AVI"].flags)
                world.countries["AVI"].capitulated = False
                for _ in range(5):
                    world.daily()
                country = world.countries["AVI"]
                self.assertEqual(country.events.count("hsm_ver_avian." + event_id), 1)
                world.advance_days(29)
                world.daily()
                self.assertEqual(country.events.count("hsm_ver_avian." + event_id), 2)
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_avian." + event_id, "AVI"))
                world.choose("hsm_ver_avian." + event_id, 0, "AVI")
                self.assertIn("HSM_AVI_" + resolved, country.flags)
                world.advance_days(90)
                world.daily()
                self.assertEqual(country.events.count("hsm_ver_avian." + event_id), 2)

    def test_levy_compliance_costs_once_and_cannot_later_defy(self):
        self.w.levy(0)
        self.w.choose("hsm_ver_avian.30", 1, "AVI")
        self.assertEqual(self.avi.political_power, -75)
        self.assertIn("HSM_AVI_levy_settled", self.avi.flags)
        self.assertNotIn("HSM_AVI_exceptional_levy", self.avi.ideas)
        self.assertTrue(self.w.available("honour_the_exemptions"))

    def test_all_three_breach_repairs_are_independent_in_every_order(self):
        repairs = {
            "ERI": "HSM_VER_restore_charter",
            "EYR": "HSM_VER_eyr_withdraw_requisitions",
            "AVI": "HSM_VER_AVI_withdraw_levy",
        }
        for order in itertools.permutations(HOUSES):
            with self.subTest(order=order):
                world = AvianWorld()
                world.levy(1)
                world.countries["ERI"].flags.add("HSM_VER_royal_exception")
                world.countries["EYR"].flags.add("HSM_EYR_command_dispute")
                for index, tag in enumerate(order):
                    world.apply(repairs[tag], tag)
                    world.daily()
                    restored = index == 2
                    self.assertEqual(world.test("HSM_VER_AVI_three_party_charter"), restored)
                    for participant in HOUSES:
                        country = world.countries[participant]
                        self.assertEqual("HSM_VER_charter_suspended" in country.flags, not restored)
                        self.assertEqual("HSM_AVI_common_budget" in country.ideas, restored)

    def test_defiance_suspends_all_benefits_and_paid_repair_is_idempotent(self):
        self.w.levy(1)
        for tag in HOUSES:
            country = self.w.countries[tag]
            self.assertIn("HSM_VER_charter_suspended", country.flags)
            self.assertFalse(country.ideas & {"HSM_AVI_common_budget", "HSM_VER_common_courts", "HSM_VER_joint_staff", "HSM_VER_shared_services"})
        self.assertEqual(self.avi.political_power, 100)
        self.assertFalse(self.w.available("honour_the_exemptions"))
        self.w.daily()
        self.assertFalse(self.w.test("HSM_VER_AVI_three_party_charter"))
        self.w.decide("withdraw_levy")
        self.w.apply("HSM_VER_AVI_withdraw_levy", "AVI")
        self.w.daily()
        self.assertEqual(self.avi.political_power, 0)
        self.assertNotIn("HSM_AVI_exceptional_levy", self.avi.ideas)
        self.assertFalse(self.w.can_decide("withdraw_levy"))
        self.assertTrue(self.w.available("honour_the_exemptions"))
        self.assertEqual(self.w.descriptions("hsm_ver_avian.41"), ["hsm_ver_avian.41.breach.d"])

    def test_civilian_factory_uses_only_eligible_owned_controlled_core_once(self):
        self.w.levy()
        self.w.states = [State(owner="ERI"), State(cores=set()), State(controller="GRI"), State(capacity=0), State()]
        self.w.reward("honour_the_exemptions")
        self.w.apply("HSM_VER_AVI_civilian_works", "AVI")
        self.assertEqual([s.extra_slots for s in self.w.states], [0, 0, 0, 0, 1])
        self.assertEqual([s.buildings for s in self.w.states], [{}, {}, {}, {}, {"industrial_complex": 1}])

    def test_civilian_factory_fallback_when_no_eligible_capacity_is_once_only(self):
        self.w.levy()
        self.w.states = [State(capacity=0), State(controller="GRI"), State(cores=set())]
        self.w.reward("honour_the_exemptions")
        self.w.apply("HSM_VER_AVI_civilian_works", "AVI")
        self.assertEqual(len(self.avi.bonuses), 1)
        bonus = Node("bonus", "=", self.avi.bonuses[0])
        self.assertEqual((bonus.get("bonus"), bonus.get("uses"), bonus.get("category")), ("1", "1", "construction_tech"))
        self.assertTrue(all(not s.buildings for s in self.w.states))


class CampaignFlow(AvianFixture):
    def test_settlement_handoff_is_guarded_and_issued_once(self):
        self.w.apply("HSM_VER_AVI_finish_first_settlement", "AVI")
        self.assertNotIn("HSM_AVI_settlement_completed", self.avi.flags)
        self.w.levy()
        self.w.apply("HSM_VER_AVI_finish_first_settlement", "AVI")
        before = copy.deepcopy(self.w.countries)
        scheduled = list(self.w.scheduled)
        self.w.apply("HSM_VER_AVI_finish_first_settlement", "AVI")
        self.assertEqual(self.w.countries, before)
        self.assertEqual(self.w.scheduled, scheduled)
        self.assertEqual(self.avi.events.count("hsm_ver_avian.50"), 1)
        self.w.advance_days(1)
        self.assertTrue(self.w.deliver("hsm_ver_avian.50", "AVI"))
        self.w.choose("hsm_ver_avian.50", 0, "AVI")
        self.assertTrue(all(c.exists and not c.subject for c in self.w.countries.values()))

    def test_revision_localization_has_bom_parity_and_no_duplicate_keys(self):
        languages = {}
        for language in ("english", "russian"):
            found = {}
            for suffix in ("", "_revision"):
                path = MOD / "localisation" / language / f"HSM_VER_avian{suffix}_l_{language}.yml"
                self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"), path)
                for line in path.read_text(encoding="utf-8-sig").splitlines():
                    if not line.strip() or line.startswith(("l_", "#")):
                        continue
                    match = re.fullmatch(r'\s+([^\s:]+):0 "([^"\n]*)"', line)
                    self.assertIsNotNone(match, (path, line))
                    key, value = match.groups()
                    self.assertNotIn(key, found, (language, key))
                    self.assertTrue(value.strip(), key)
                    found[key] = value
            languages[language] = found
        self.assertEqual(set(languages["english"]), set(languages["russian"]))
        for key in ("full_integration", "full_integration_desc", "HSM_AVI_full_integration_tt", "HSM_AVI_constituent_convention_tt", "HSM_AVI_settlement_completed"):
            self.assertIn(key, languages["english"])

    def test_full_campaign_with_both_budget_refusals_reaches_epilogue(self):
        self.avi.focuses.add("treaty_of_friendship")
        for suffix in ("three_separate_seals", "two_legible_copies", "hear_the_towns", "charter_without_submission"):
            self.w.complete(suffix)
        self.w.choose("hsm_ver_avian.2", 1, "AVI")
        self.w.choose("hsm_verenia.60", 0, "ERI")
        self.w.choose("hsm_verenia.61", 0, "EYR")
        self.w.choose("hsm_verenia.63", 0, "AVI")
        for suffix in ("common_accounts", "roads_between_houses", "limited_joint_staff", "a_court_for_hosts"):
            self.w.complete(suffix)
        self.assertFalse(self.w.available("the_first_common_budget"))
        for tag in ("ERI", "EYR"):
            self.w.choose("hsm_ver_avian.20", 1, tag)
        self.w.complete("the_first_common_budget")
        self.assertFalse(self.w.available("the_unauthorised_levy"))
        self.w.choose("hsm_ver_avian.10", 0, "AVI")
        self.w.complete("the_unauthorised_levy")
        self.w.choose("hsm_ver_avian.30", 0, "AVI")
        for suffix in ("honour_the_exemptions", "common_workshops", "defence_without_a_master", "open_minutes", "a_union_worth_keeping"):
            self.w.complete(suffix)
        self.assertIn("HSM_AVI_settlement_completed", self.avi.flags)
        self.assertIn("hsm_ver_avian.50", self.avi.events)
        self.assertEqual(self.avi.army_experience, 40)
        self.assertEqual(self.avi.political_power, -75)
        self.assertEqual(len(self.avi.bonuses), 6)
        self.assertEqual(self.w.states[0].buildings, {"industrial_complex": 1})
        for tag in HOUSES:
            country = self.w.countries[tag]
            self.assertTrue(country.exists)
            self.assertFalse(country.subject or country.faction)
            self.assertNotIn("HSM_AVI_common_budget", country.ideas)

    def test_events_have_bounded_response_windows_and_choices_have_ai_weights(self):
        events = {k: n for k, n in self.w.events.items() if k.startswith("hsm_ver_avian.")}
        self.assertEqual({k.split(".")[1] for k in events}, {"1", "2", "3", "4", "10", "20", "21", "29", "30", "31", "32", "41", "50", "51"})
        for key, event in events.items():
            self.assertEqual(event.get("timeout_days"), "13", key)
            options = event.all("option")
            if len(options) > 1:
                self.assertTrue(all(float(Node("ai", "=", o.get("ai_chance")).get("factor")) > 0 for o in options), key)

    def test_idea_modifiers_match_contracted_costs_and_benefits(self):
        ideas = {n.key: n for n in walk(read(MOD / "common/ideas/HSM_VER_avian.txt")) if n.key.startswith("HSM_AVI_") and n.children}
        expected = {
            "translation_office": {"stability_factor": "0.06", "research_speed_factor": "0.03", "political_power_gain": "-0.10"},
            "local_clerks": {"stability_factor": "0.03", "political_power_factor": "0.08"},
            "common_budget": {"production_speed_infrastructure_factor": "0.15", "production_factory_efficiency_gain_factor": "0.08", "political_power_factor": "-0.05"},
            "exceptional_levy": {"industrial_capacity_factory": "0.10", "stability_factor": "-0.07", "consumer_goods_factor": "0.05"},
        }
        self.assertEqual(set(ideas), {"HSM_AVI_" + k for k in expected})
        for key, modifiers in expected.items():
            self.assertEqual({n.key: n.value for n in ideas["HSM_AVI_" + key].get("modifier")}, modifiers)


if __name__ == "__main__":
    unittest.main(argv=[__file__, *BASE["REST"]], verbosity=2)
