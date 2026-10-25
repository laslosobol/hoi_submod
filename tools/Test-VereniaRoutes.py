"""Route regression fixtures using production scripts, not an HOI4 emulator.

Run python -B tools/Test-VereniaRoutes.py [-q] [TestClass.test_name].
Imports the shared parser/evaluator without modifying it. Focus completion and
event delivery are explicit; no event is silently accepted on behalf of a player.
"""
from __future__ import annotations

import copy
import importlib.util
import runpy
import sys
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "verenia_routes_base", Path(__file__).with_name("Test-Verenia.py")
)
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)
Node, read, walk, MOD = BASE.Node, BASE.read, BASE.walk, BASE.MOD
RIVAL = {"ERI": "EYR", "EYR": "ERI"}
ROUTES = {
    "ERI": {
        "common": "HSM_ERI_cost_of_feud",
        "entry": "HSM_ERI_diplomatic_settlement",
        "force": "HSM_ERI_FORCE_the_price_of_victory",
        "first": "HSM_ERI_hear_petitions",
        "second": "HSM_ERI_family_letters",
        "guarantees": "HSM_ERI_reciprocal_guarantees",
        "armistice": "HSM_ERI_offer_armistice",
        "roads": "HSM_ERI_open_roads",
        "treaty": "HSM_ERI_friendship_treaty",
        "mandate": "HSM_ERI_mandate_for_peace",
        "charter": "HSM_ERI_common_statute",
        "staff": "HSM_ERI_joint_staff",
        "services": "HSM_ERI_shared_services",
        "case": "HSM_ERI_first_judgement",
        "defence": "HSM_ERI_common_defence",
        "reconstruction": "HSM_ERI_keep_our_word",
        "final": "HSM_ERI_generation_without_feud",
        "fallback": "HSM_ERI_peace_without_union",
        "armistice_reply": "hsm_verenia.20",
        "treaty_reply": "hsm_verenia.30",
        "charter_reply": "hsm_verenia.61",
        "case_event": "hsm_verenia.70",
    },
    "EYR": {
        "common": "HSM_EYR_the_price_of_vigilance",
        "entry": "HSM_EYR_diplomatic_settlement",
        "force": "HSM_EYR_FORCE_the_last_campaign",
        "first": "HSM_EYR_audit_the_muster",
        "second": "HSM_EYR_montagues_correspondence",
        "guarantees": "HSM_EYR_publish_the_rules",
        "armistice": "HSM_EYR_reciprocal_frontier",
        "roads": "HSM_EYR_inspect_both_sides",
        "treaty": "HSM_EYR_friendship_with_safeguards",
        "mandate": "HSM_EYR_limits_of_command",
        "charter": "HSM_EYR_a_charter_we_can_sign",
        "staff": "HSM_EYR_officers_at_one_table",
        "services": "HSM_EYR_shared_workshops",
        "case": "HSM_EYR_the_return_order",
        "defence": "HSM_EYR_a_defence_agreement",
        "reconstruction": "HSM_EYR_workshops_returned",
        "final": "HSM_EYR_a_border_without_orders",
        "fallback": "HSM_EYR_neighbours_without_a_council",
        "armistice_reply": "hsm_ver_eyrie.110",
        "treaty_reply": "hsm_ver_eyrie.120",
        "charter_reply": "hsm_ver_eyrie.130",
        "case_event": "hsm_ver_eyrie.30",
    },
}


def load_focuses():
    result = {}
    for path in (MOD / "common/national_focus").glob("*.txt"):
        if path.name == "AVI.txt" or path.name.startswith(("HSM_ERI", "HSM_EYR", "HSM_VER")):
            for node in walk(read(path)):
                if node.key in ("focus", "shared_focus") and node.children:
                    result[node.get("id")] = node
    return result


FOCUSES = load_focuses()


def references(node, field):
    return {item.value for group in node.all(field) for item in group.all("focus")}


def position(node):
    return int(node.get("x")), int(node.get("y"))


class RouteWorld(BASE.World):
    """Small extensions for actual focus rewards; unsupported commands still fail."""

    def __init__(self):
        super().__init__()
        self.technology = {tag: [] for tag in self.countries}
        self.states = {
            "401": {"owner": "ERI", "controller": "ERI", "slots": 5, "buildings": {}},
            "391": {"owner": "EYR", "controller": "EYR", "slots": 5, "buildings": {}},
        }
        for country in self.countries.values():
            country.naps = set()
            country.political_power = 250
        for tag in RIVAL:
            self.countries[tag].ideas.add("E_E_rivalry")

    def check(self, nodes, tag="ERI"):
        for node in nodes:
            value = node.value
            if node.key in ("hidden_trigger", "custom_trigger_tooltip"):
                ok = self.check([n for n in node.children if not (node.key == "custom_trigger_tooltip" and n.key == "tooltip")], tag)
            elif node.key in self.states:
                ok = self.check(node.children, node.key)
            elif node.key in ("owns_state", "controls_state"):
                field = "owner" if node.key == "owns_state" else "controller"
                ok = value in self.states and self.states[value][field] == tag
            elif node.key == "has_non_aggression_pact_with":
                ok = self.resolve(value) in self.countries[tag].naps
            elif node.key == "can_declare_war_on":
                target = self.resolve(value)
                country, other = self.countries[tag], self.countries[target]
                ok = (other.exists and not country.subject and target not in country.naps
                      and target not in country.wars
                      and not (country.faction and country.faction == other.faction))
            elif node.key == "has_wargoal_against":
                ok = any(target == self.resolve(value) for _, target in self.countries[tag].goals)
            elif node.key == "any_owned_state":
                ok = any(state["owner"] == tag and self.check(node.children, key)
                         for key, state in self.states.items())
            elif tag in self.states and node.key in ("is_core_of", "is_fully_controlled_by"):
                field = "owner" if node.key == "is_core_of" else "controller"
                ok = self.states[tag][field] == self.resolve(value)
            elif tag in self.states and node.key == "free_building_slots":
                assert node.get("building") == "industrial_complex"
                assert node.all("size")[0].op == ">" and node.get("size") == "0"
                ok = self.states[tag]["slots"] > sum(self.states[tag]["buildings"].values())
            else:
                ok = super().check([node], tag)
            if not ok:
                return False
        return True

    def run(self, nodes, tag="ERI"):
        # Keep if/else chains together when delegating to the shared evaluator.
        pending = []
        special = {"hidden_effect", "show_ideas_tooltip", "add_tech_bonus",
                   "add_extra_state_shared_building_slots", "add_building_construction",
                   "random_owned_state", "create_wargoal"} | self.states.keys()
        for node in nodes:
            if node.key not in special:
                pending.append(node)
                continue
            if pending:
                super().run(pending, tag)
                pending = []
            if node.key == "hidden_effect":
                self.run(node.children, tag)
            elif node.key == "show_ideas_tooltip":
                pass
            elif node.key in self.states:
                self.run(node.children, node.key)
            elif node.key == "add_tech_bonus":
                self.technology[tag].append(copy.deepcopy(node.children))
            elif node.key == "add_extra_state_shared_building_slots":
                self.states[tag]["slots"] += int(node.value)
            elif node.key == "add_building_construction":
                assert node.get("instant_build") == "yes"
                buildings = self.states[tag]["buildings"]
                kind = node.get("type")
                buildings[kind] = buildings.get(kind, 0) + int(node.get("level"))
            elif node.key == "random_owned_state":
                eligible = [key for key, state in self.states.items()
                            if state["owner"] == tag and self.check(node.get("limit", []), key)]
                if eligible:
                    self.run([n for n in node.children if n.key != "limit"], eligible[0])
            elif node.key == "create_wargoal":
                self.countries[tag].goals.add((node.get("type"), self.resolve(node.get("target"))))
        if pending:
            super().run(pending, tag)

    def available(self, key, tag):
        node, completed = FOCUSES[key], self.countries[tag].focuses
        return (key not in completed
                and all(references(Node("group", "=", [group]), "prerequisite") & completed
                        for group in node.all("prerequisite"))
                and not references(node, "mutually_exclusive") & completed
                and self.check(node.get("available", []), tag))

    def complete(self, key, tag):
        self.root = tag
        assert self.available(key, tag), "Unavailable focus: " + key
        self.countries[tag].focuses.add(key)
        self.run(FOCUSES[key].get("completion_reward", []), tag)

    def deliver(self, event, tag, option=0):
        self.root = tag
        assert event in self.countries[tag].events, "Unscheduled event: " + event
        node = self.events[event]
        assert self.check(node.get("trigger", []), tag), "Invalid event: " + event
        assert self.check(node.all("option")[option].get("trigger", []), tag)
        self.countries[tag].events.remove(event)
        self.run(node.get("immediate", []), tag)
        self.choose(event, option, tag)

    def ai_weight(self, key, tag):
        node = FOCUSES[key].all("ai_will_do")[0]
        value = float(node.get("factor", "1"))
        for modifier in node.all("modifier"):
            if self.check([n for n in modifier.children if n.key not in ("factor", "add")], tag):
                value *= float(modifier.get("factor", "1"))
                value += float(modifier.get("add", "0"))
        return value

    def snapshot(self):
        return copy.deepcopy((self.countries, self.technology, self.states, self.trace))


class RouteTests(unittest.TestCase):
    def test_state_tooltip_wrappers_preserve_predicates(self):
        world = RouteWorld()
        world.root = "EYR"
        predicates = (
            "is_core_of = ROOT is_fully_controlled_by = ROOT "
            "free_building_slots = { building = industrial_complex size > 0 include_locked = yes }"
        )
        plain = BASE.parse(predicates)
        wrapped = BASE.parse("hidden_trigger = { custom_trigger_tooltip = { tooltip = state_note " + predicates + " } }")
        original = copy.deepcopy(world.states["391"])
        for changes, expected in (({}, True), ({"owner": "ERI"}, False),
                                  ({"controller": "ERI"}, False), ({"slots": 0}, False)):
            with self.subTest(changes=changes):
                world.states["391"] = {**original, **changes}
                self.assertEqual(world.check(plain, "391"), expected)
                self.assertEqual(world.check(wrapped, "391"), expected)

    def prepare(self, tag, ai=True, terms=0):
        world, route = RouteWorld(), ROUTES[tag]
        world.countries[RIVAL[tag]].ai = ai
        for stage in ("common", "entry", "first", "second", "guarantees"):
            world.complete(route[stage], tag)
        world.deliver("hsm_ver_routes.1", tag, terms)
        return world

    def through_treaty(self, tag, ai=True, terms=0):
        world, route = self.prepare(tag, ai, terms), ROUTES[tag]
        world.complete(route["armistice"], tag)
        if not ai:
            world.deliver(route["armistice_reply"], RIVAL[tag])
        world.complete(route["roads"], tag)
        world.complete(route["treaty"], tag)
        if not ai:
            world.deliver(route["treaty_reply"], RIVAL[tag])
        return world

    def charter(self, world, tag, ai=True, presidency=False):
        route = ROUTES[tag]
        world.complete(route["mandate"], tag)
        world.complete(route["charter"], tag)
        if tag == "ERI":
            world.deliver("hsm_verenia.60", tag, int(presidency))
            if presidency and ai:
                world.deliver("hsm_verenia.62", tag)
        if not ai:
            world.deliver(route["charter_reply"], RIVAL[tag])

    def test_layout_imports_exclusion_and_no_backwards_edges(self):
        BASE.Integration("test_focus_graph_and_coordinates").test_focus_graph_and_coordinates()
        for tag, route in ROUTES.items():
            with self.subTest(tag=tag):
                self.assertEqual(position(FOCUSES[route["common"]]), (24, 0))
                self.assertEqual(position(FOCUSES[route["entry"]]), (14, 1))
                self.assertEqual(position(FOCUSES[route["force"]]), (34, 1))
                self.assertEqual(references(FOCUSES[route["entry"]], "mutually_exclusive"), {route["force"]})
                self.assertEqual(references(FOCUSES[route["force"]], "mutually_exclusive"), {route["entry"]})
                fallback = FOCUSES[route["fallback"]]
                self.assertEqual(position(fallback), (20, 5))
                self.assertEqual(references(fallback, "prerequisite"), {route["entry"]})
                self.assertEqual([n.get("id") for n in walk(fallback.get("completion_reward"))
                                  if n.key == "country_event"], ["hsm_ver_routes.2"])
                for stage, y in (("guarantees", 3), ("armistice", 4), ("roads", 5), ("treaty", 6)):
                    self.assertEqual(position(FOCUSES[route[stage]]), (14, y))
                self.assertEqual(FOCUSES[route["treaty"]].get("cost"), "7")

    def test_imperial_block_is_detached_and_far_right(self):
        nodes = {k: n for k, n in FOCUSES.items() if k.startswith("HSM_VER_IMP_")}
        self.assertEqual(len(nodes), 8)
        self.assertEqual(position(nodes["HSM_VER_IMP_settlement"]), (54, 0))
        self.assertFalse(nodes["HSM_VER_IMP_settlement"].all("prerequisite"))
        self.assertTrue(all(52 <= position(n)[0] <= 56 for n in nodes.values()))
        self.assertTrue(all(references(n, "prerequisite") <= nodes.keys() for n in nodes.values()))

    def test_default_human_fixture_and_is_ai_scope(self):
        world = RouteWorld()
        for tag in RIVAL:
            self.assertFalse(world.countries[tag].ai)
            self.assertFalse(world.test("HSM_VER_conference_ai_partner", tag))
            world.countries[RIVAL[tag]].ai = True
            self.assertTrue(world.test("HSM_VER_conference_ai_partner", tag))
            world.countries[RIVAL[tag]].ai = False

    def test_common_roots_do_not_commit_either_route(self):
        for tag, route in ROUTES.items():
            world = RouteWorld()
            world.complete(route["common"], tag)
            for country in world.countries.values():
                self.assertFalse(country.flags & {"HSM_VER_diplomatic_route", "HSM_VER_military_route"})

    def test_ai_waits_for_human_choice_then_selects_compatible_route(self):
        for tag, route in ROUTES.items():
            for choice in (None, "diplomacy", "military"):
                with self.subTest(tag=tag, human_choice=choice):
                    world = RouteWorld()
                    world.countries[tag].ai = True
                    world.complete(route["common"], tag)
                    if choice:
                        world.apply("HSM_VER_choose_" + choice, RIVAL[tag])
                    self.assertEqual(world.ai_weight(route["entry"], tag), 0 if choice is None else 100)
                    self.assertEqual(world.ai_weight(route["force"], tag), 1 if choice == "military" else 0)
                    if choice:
                        self.assertEqual(world.available(route["entry"], tag), choice == "diplomacy")
                        self.assertEqual(world.available(route["force"], tag), choice == "military")
                    domestic = "HSM_ERI_reconstruction" if tag == "ERI" else "HSM_EYR_borderland_reconstruction"
                    army = "HSM_ERI_army_for_a_country" if tag == "ERI" else "HSM_EYR_defensive_service"
                    self.assertTrue(world.available(domestic, tag))
                    self.assertTrue(world.available(army, tag))

    def test_ai_rival_does_not_suppress_weights_until_diplomatic_commitment(self):
        for tag, route in ROUTES.items():
            world = RouteWorld()
            world.countries[RIVAL[tag]].ai = True
            self.assertEqual(world.ai_weight(route["entry"], tag), 100)
            self.assertEqual(world.ai_weight(route["force"], tag), 1)
            world.apply("HSM_VER_choose_diplomacy", RIVAL[tag])
            self.assertEqual(world.ai_weight(route["force"], tag), 0)

    def test_diplomacy_commits_ai_but_not_human_and_blocks_military(self):
        for tag, route in ROUTES.items():
            for ai in (False, True):
                with self.subTest(tag=tag, ai=ai):
                    world = self.prepare(tag, ai)
                    self.assertIn("HSM_VER_diplomatic_route", world.countries[tag].flags)
                    self.assertEqual("HSM_VER_diplomatic_route" in world.countries[RIVAL[tag]].flags, ai)
                    self.assertFalse(world.available(route["force"], tag))
                    self.assertFalse(world.test("HSM_VER_FORCE_can_prepare", tag))
                    self.assertFalse(world.test("HSM_VER_FORCE_can_issue_goal", tag))
                    world.apply("HSM_VER_choose_military", tag)
                    self.assertNotIn("HSM_VER_military_route", world.countries[tag].flags)

    def test_ai_signs_at_focus_completion_without_reply_roll(self):
        for tag, route in ROUTES.items():
            for terms in (0, 1):
                with self.subTest(tag=tag, terms=terms):
                    world = self.prepare(tag, terms=terms)
                    world.complete(route["armistice"], tag)
                    self.assertTrue(world.test("HSM_VER_armistice_valid"))
                    self.assertNotIn(route["armistice_reply"], world.countries[RIVAL[tag]].events)
                    world.complete(route["roads"], tag)
                    world.complete(route["treaty"], tag)
                    self.assertTrue(world.test("HSM_VER_negotiated_peace_valid"))
                    self.assertNotIn(route["treaty_reply"], world.countries[RIVAL[tag]].events)
                    for house in RIVAL:
                        self.assertIn("HSM_VER_peace_dividend", world.countries[house].ideas)
                        self.assertNotIn("E_E_rivalry", world.countries[house].ideas)

    def test_full_ai_focus_campaign_reaches_defence_and_epilogue(self):
        for tag, route in ROUTES.items():
            for terms in (0, 1):
                with self.subTest(tag=tag, terms=terms):
                    world = self.through_treaty(tag, terms=terms)
                    self.charter(world, tag)
                    self.assertTrue(world.test("HSM_VER_charter_valid"))
                    for stage in ("staff", "services", "case"):
                        world.complete(route[stage], tag)
                    world.deliver(route["case_event"], tag)
                    for stage in ("defence", "reconstruction", "final"):
                        world.complete(route[stage], tag)
                    self.assertTrue(world.test("HSM_VER_defence_league_operational"))
                    final = "HSM_VER_union_established" if tag == "ERI" else "HSM_EYR_settlement_completed"
                    self.assertIn(final, world.countries[tag].flags)
                    self.assertTrue(world.technology[tag])
                    self.assertEqual(world.countries["ERI"].faction, world.countries["EYR"].faction)

    def test_erie_ai_charter_presidency_counteroffer_is_local_choice(self):
        world = self.through_treaty("ERI")
        world.complete(ROUTES["ERI"]["mandate"], "ERI")
        world.complete(ROUTES["ERI"]["charter"], "ERI")
        world.deliver("hsm_verenia.60", "ERI", 1)
        self.assertFalse(world.test("HSM_VER_charter_valid"))
        self.assertIn("hsm_verenia.62", world.countries["ERI"].events)
        world.deliver("hsm_verenia.62", "ERI", 1)
        self.assertTrue(world.available(ROUTES["ERI"]["fallback"], "ERI"))

    def test_humans_must_explicitly_accept_armistice_treaty_and_charter(self):
        for tag, route in ROUTES.items():
            world = self.prepare(tag, ai=False)
            for stage, valid in (("armistice", "HSM_VER_armistice_valid"), ("treaty", "HSM_VER_negotiated_peace_valid")):
                if stage == "treaty":
                    world.complete(route["roads"], tag)
                world.complete(route[stage], tag)
                self.assertFalse(world.test(valid))
                world.deliver(route[stage + "_reply"], RIVAL[tag])
                self.assertTrue(world.test(valid))
            world.complete(route["mandate"], tag)
            world.complete(route["charter"], tag)
            if tag == "ERI":
                world.deliver("hsm_verenia.60", tag)
            self.assertFalse(world.test("HSM_VER_charter_valid"))
            world.deliver(route["charter_reply"], RIVAL[tag])
            self.assertTrue(world.test("HSM_VER_charter_valid"))

    def test_human_refusal_at_each_stage_unlocks_unilateral_fallback(self):
        for tag, route in ROUTES.items():
            for refused in ("armistice", "treaty", "charter"):
                with self.subTest(tag=tag, refused=refused):
                    world = self.prepare(tag, ai=False)
                    world.complete(route["armistice"], tag)
                    if refused != "armistice":
                        world.deliver(route["armistice_reply"], RIVAL[tag])
                        world.complete(route["roads"], tag)
                        world.complete(route["treaty"], tag)
                    if refused == "charter":
                        world.deliver(route["treaty_reply"], RIVAL[tag])
                        world.complete(route["mandate"], tag)
                        world.complete(route["charter"], tag)
                        if tag == "ERI":
                            world.deliver("hsm_verenia.60", tag)
                    reply = route[refused + "_reply"]
                    world.deliver(reply, RIVAL[tag], 2)
                    # Replayed acceptance and new completion helpers must not undo the refusal.
                    world.choose(reply, 0, RIVAL[tag])
                    world.apply("HSM_VER_conclude_armistice", tag)
                    world.apply("HSM_VER_conclude_treaty", tag)
                    self.assertIn("HSM_VER_" + refused + "_refused", world.countries["ERI"].flags)
                    signed = "HSM_VER_armistice" if refused == "armistice" else "HSM_VER_" + refused + "_signed"
                    self.assertNotIn(signed, world.countries["ERI"].flags)
                    self.assertTrue(world.available(route["fallback"], tag))
                    world.complete(route["fallback"], tag)
                    world.deliver("hsm_ver_routes.2", tag)
                    self.assertTrue(world.technology[tag])

    def test_rival_military_choice_before_armistice_leaves_reachable_fallback(self):
        for tag, route in ROUTES.items():
            world = RouteWorld()
            world.complete(route["common"], tag)
            world.complete(route["entry"], tag)
            world.apply("HSM_VER_choose_military", RIVAL[tag])
            self.assertNotIn(route["armistice"], world.countries[tag].focuses)
            self.assertFalse(world.check(FOCUSES[route["armistice"]].get("available"), tag))
            self.assertTrue(world.available(route["fallback"], tag))
            world.complete(route["fallback"], tag)
            world.deliver("hsm_ver_routes.2", tag)

    def test_route_armistice_still_allows_roads_and_treaty_after_400_days(self):
        for tag, route in ROUTES.items():
            world = self.prepare(tag)
            world.complete(route["armistice"], tag)
            world.advance_days(400)
            self.assertTrue(world.test("HSM_VER_armistice_valid"))
            world.complete(route["roads"], tag)
            world.complete(route["treaty"], tag)
            self.assertTrue(world.test("HSM_VER_negotiated_peace_valid"))

    def test_human_accepted_route_armistice_is_also_promoted_for_both_houses(self):
        for tag, route in ROUTES.items():
            world = self.prepare(tag, ai=False)
            world.complete(route["armistice"], tag)
            world.deliver(route["armistice_reply"], RIVAL[tag])
            for house in RIVAL:
                self.assertNotIn("HSM_VER_armistice", world.countries[house].flag_days)
            world.advance_days(400)
            self.assertTrue(world.test("HSM_VER_armistice_valid"))
            world.complete(route["roads"], tag)
            world.complete(route["treaty"], tag)
            self.assertFalse(world.test("HSM_VER_negotiated_peace_valid"))
            world.deliver(route["treaty_reply"], RIVAL[tag])
            self.assertTrue(world.test("HSM_VER_negotiated_peace_valid"))

    def test_completion_helpers_do_not_repeat_agreements_or_rewards(self):
        for tag, route in ROUTES.items():
            world = self.prepare(tag)
            world.complete(route["armistice"], tag)
            before = world.snapshot()
            world.apply("HSM_VER_conclude_armistice", tag)
            self.assertEqual(world.snapshot(), before)
            world.complete(route["roads"], tag)
            world.complete(route["treaty"], tag)
            before = world.snapshot()
            world.apply("HSM_VER_conclude_armistice", tag)
            world.apply("HSM_VER_conclude_treaty", tag)
            self.assertEqual(world.snapshot(), before)

    def test_fallback_is_not_available_during_live_talks_or_successful_charter(self):
        for tag, route in ROUTES.items():
            world = self.prepare(tag, ai=False)
            self.assertFalse(world.available(route["fallback"], tag))
            world.complete(route["armistice"], tag)
            self.assertFalse(world.available(route["fallback"], tag))
            world.deliver(route["armistice_reply"], RIVAL[tag])
            self.assertFalse(world.available(route["fallback"], tag))
            world.complete(route["roads"], tag)
            world.complete(route["treaty"], tag)
            self.assertFalse(world.available(route["fallback"], tag))
            world.deliver(route["treaty_reply"], RIVAL[tag])
            self.charter(world, tag, ai=False)
            self.assertFalse(world.available(route["fallback"], tag))

    def test_unfinished_union_does_not_hide_actual_negotiation_collapse(self):
        for tag, route in ROUTES.items():
            for failure in ("disappeared", "subject", "capitulated", "leader"):
                for convention in ("HSM_VER_UNI_started", "HSM_VER_UNI_closed"):
                    with self.subTest(tag=tag, failure=failure, convention=convention):
                        world = self.through_treaty(tag)
                        self.charter(world, tag)
                        world.countries[tag].flags.add(convention)
                        # Even a completed diplomatic finale is not a founded state.
                        world.countries[tag].focuses.add(route["final"])
                        other = world.countries[RIVAL[tag]]
                        if failure == "disappeared":
                            other.exists = False
                        elif failure == "leader":
                            other.leader = "unrelated_successor"
                            world.countries["ERI"].flags.add("HSM_VER_charter_suspended")
                        else:
                            setattr(other, failure, True)
                        self.assertTrue(world.test("HSM_VER_conference_failed", tag))
                        self.assertTrue(world.available(route["fallback"], tag))

    def test_legacy_armistice_expires_without_route_commitment(self):
        world = RouteWorld()
        world.armistice()
        world.advance_days(366)
        self.assertFalse(world.test("HSM_VER_armistice_valid"))

    def test_existing_timed_armistice_promoted_on_choice_or_migration(self):
        for tag, route in ROUTES.items():
            for migration in (False, True):
                with self.subTest(tag=tag, migration=migration):
                    world = RouteWorld()
                    world.countries[RIVAL[tag]].ai = True
                    world.armistice()
                    world.advance_days(100)
                    self.assertIn("HSM_VER_armistice", world.countries["ERI"].flag_days)
                    if migration:
                        world.countries[tag].focuses.add(route["armistice"])
                    world.apply("HSM_VER_migrate_routes" if migration else "HSM_VER_choose_diplomacy", tag)
                    for house in RIVAL:
                        self.assertNotIn("HSM_VER_armistice", world.countries[house].flag_days)
                    world.advance_days(400)
                    self.assertTrue(world.test("HSM_VER_armistice_valid"))

    def test_guarantee_scene_and_cost_are_once_only_across_both_houses(self):
        for tag in RIVAL:
            for terms in (0, 1):
                with self.subTest(tag=tag, terms=terms):
                    world = self.prepare(tag, terms=terms)
                    self.assertEqual(world.countries[tag].political_power, 250 - 50 * terms)
                    before = world.snapshot()
                    for click in (terms, 1 - terms, terms):
                        world.choose("hsm_ver_routes.1", click, tag)
                        world.choose("hsm_ver_routes.1", click, RIVAL[tag])
                    self.assertEqual(world.snapshot(), before)
                    for house in RIVAL:
                        world.apply("HSM_VER_prepare_guarantees", house)
                        self.assertNotIn("hsm_ver_routes.1", world.countries[house].events)

    def test_repreparing_guarantees_does_not_replace_property_arbitration(self):
        for tag, route in ROUTES.items():
            world = self.prepare(tag, terms=1)
            world.complete(route["armistice"], tag)
            for house in RIVAL:
                world.apply("HSM_VER_prepare_guarantees", house)
            self.assertIn("HSM_VER_property_arbitration", world.countries["ERI"].flags)
            self.assertNotIn("HSM_VER_joint_inspection", world.countries["ERI"].flags)
            for house in RIVAL:
                self.assertNotIn("HSM_VER_frontier_inspections", world.countries[house].ideas)

    def test_migration_recovers_only_completed_stages_and_is_idempotent(self):
        for tag, route in ROUTES.items():
            for stage in ("entry", "armistice", "treaty", "charter"):
                with self.subTest(tag=tag, stage=stage):
                    world = RouteWorld()
                    world.countries[RIVAL[tag]].ai = True
                    stages = ["entry", "armistice", "treaty", "charter"]
                    completed = {route[s] for s in stages[:stages.index(stage) + 1]}
                    world.countries[tag].focuses = completed.copy()
                    states, pp = copy.deepcopy(world.states), world.countries[tag].political_power
                    world.apply("HSM_VER_migrate_routes", tag)
                    self.assertEqual(world.test("HSM_VER_armistice_valid"), stage != "entry")
                    self.assertEqual(world.test("HSM_VER_negotiated_peace_valid"), stage in ("treaty", "charter"))
                    if stage == "charter":
                        if tag == "ERI":
                            self.assertFalse(world.test("HSM_VER_charter_valid"))
                            world.deliver("hsm_verenia.60", tag)
                        self.assertTrue(world.test("HSM_VER_charter_valid"))
                    else:
                        self.assertFalse(world.test("HSM_VER_charter_valid"))
                    self.assertEqual(world.countries[tag].focuses, completed)
                    self.assertEqual(world.states, states)
                    self.assertEqual(world.countries[tag].political_power, pp)
                    self.assertFalse(world.technology[tag])
                    self.assertFalse(world.countries[RIVAL[tag]].focuses)
                    before = world.snapshot()
                    world.apply("HSM_VER_migrate_routes", tag)
                    self.assertEqual(world.snapshot(), before)

    def test_migration_never_overwrites_human_refusal_or_replays_offer(self):
        for tag, route in ROUTES.items():
            world = RouteWorld()
            world.countries[tag].focuses.update(route[s] for s in ("armistice", "treaty", "charter"))
            world.countries["ERI"].flags.add("HSM_VER_armistice_refused")
            world.apply("HSM_VER_migrate_routes", tag)
            self.assertFalse(world.test("HSM_VER_armistice_valid"))
            self.assertFalse(world.test("HSM_VER_negotiated_peace_valid"))
            self.assertFalse(world.test("HSM_VER_charter_valid"))
            self.assertIn("HSM_VER_armistice_refused", world.countries["ERI"].flags)
            self.assertFalse(world.countries["ERI"].events + world.countries["EYR"].events)

    def test_migration_prioritizes_old_military_root_without_awarding_diplomacy(self):
        for tag, route in ROUTES.items():
            world = RouteWorld()
            world.countries[RIVAL[tag]].ai = True
            world.countries[tag].focuses.update(route[s] for s in ("force", "armistice", "treaty", "charter"))
            world.apply("HSM_VER_migrate_routes", tag)
            self.assertIn("HSM_VER_military_route", world.countries[tag].flags)
            self.assertNotIn("HSM_VER_diplomatic_route", world.countries[tag].flags)
            self.assertFalse(world.test("HSM_VER_diplomatic_routes_open"))
            self.assertFalse(world.test("HSM_VER_negotiated_peace_valid"))

    def test_migration_does_not_duplicate_existing_charter_conference(self):
        for tag, route in ROUTES.items():
            world = self.through_treaty(tag)
            world.countries[tag].focuses.add(route["charter"])
            world.countries["ERI"].flags.add("HSM_VER_charter_pending")
            world.countries["ERI"].events.append("hsm_verenia.60")
            old_events = {house: world.countries[house].events.copy() for house in RIVAL}
            world.apply("HSM_VER_migrate_routes", tag)
            for house in RIVAL:
                self.assertEqual(world.countries[house].events, old_events[house])
            self.assertFalse(world.test("HSM_VER_charter_valid"))

    def test_completed_legacy_military_root_blocks_diplomacy_before_flag_migration(self):
        for tag, route in ROUTES.items():
            world = RouteWorld()
            world.complete(route["common"], tag)
            world.countries[tag].focuses.add(route["force"])
            self.assertNotIn("HSM_VER_military_route", world.countries[tag].flags)
            self.assertFalse(world.test("HSM_VER_diplomatic_routes_open"))
            world.apply("HSM_VER_choose_diplomacy", RIVAL[tag])
            for house in RIVAL:
                self.assertNotIn("HSM_VER_diplomatic_route", world.countries[house].flags)
            for native in ("ending_the_rivalry", "treaty_of_friendship"):
                world.root = "AVI"
                world.run(FOCUSES[native].get("completion_reward"), "AVI")
            self.assertNotIn("HSM_VER_armistice_pending", world.countries["ERI"].flags)
            self.assertNotIn("HSM_VER_treaty_pending", world.countries["ERI"].flags)
            self.assertFalse(world.test("HSM_VER_negotiated_peace_valid"))

    def test_military_root_preserves_army_route_and_locks_diplomacy(self):
        for tag, route in ROUTES.items():
            world = RouteWorld()
            world.complete(route["common"], tag)
            world.complete(route["force"], tag)
            self.assertIn("HSM_VER_military_route", world.countries[tag].flags)
            self.assertNotIn("HSM_VER_diplomatic_route", world.countries[tag].flags)
            self.assertFalse(world.available(route["entry"], tag))
            self.assertFalse(world.test("HSM_VER_diplomatic_routes_open"))
            self.assertTrue(world.test("HSM_VER_FORCE_can_prepare", tag))
            self.assertTrue(world.test("HSM_VER_FORCE_can_issue_goal", tag))
            world.apply("HSM_VER_choose_diplomacy", tag)
            self.assertNotIn("HSM_VER_diplomatic_route", world.countries[tag].flags)

    def test_military_clears_old_pending_offers_and_blocks_stale_responses(self):
        replies = (("hsm_verenia.20", "EYR"), ("hsm_verenia.21", "ERI"),
                   ("hsm_verenia.30", "EYR"), ("hsm_verenia.31", "ERI"),
                   ("hsm_verenia.61", "EYR"), ("hsm_verenia.62", "ERI"),
                   ("hsm_ver_eyrie.110", "ERI"), ("hsm_ver_eyrie.111", "EYR"),
                   ("hsm_ver_eyrie.120", "ERI"), ("hsm_ver_eyrie.121", "EYR"),
                   ("hsm_ver_eyrie.130", "ERI"), ("hsm_ver_eyrie.131", "EYR"))
        for tag in RIVAL:
            for event, recipient in replies:
                with self.subTest(tag=tag, event=event):
                    world = RouteWorld()
                    for kind in ("armistice", "treaty", "charter"):
                        world.countries["ERI"].flags.update({"HSM_VER_" + kind + suffix for suffix in
                                                           ("_pending", "_offer_unresolved", "_from_eyrie")})
                    world.apply("HSM_VER_choose_military", tag)
                    before = world.snapshot()
                    world.choose(event, 0, recipient)
                    self.assertEqual(world.snapshot(), before)
                    for kind in ("armistice", "treaty", "charter"):
                        self.assertNotIn("HSM_VER_" + kind + "_pending", world.countries["ERI"].flags)

    def test_military_blocks_native_mediation_and_stale_guarantee_cost(self):
        for tag, route in ROUTES.items():
            world = RouteWorld()
            world.complete(route["common"], tag)
            world.complete(route["force"], tag)
            world.countries[tag].goals.add(("annex_everything", RIVAL[tag]))
            for native in ("ending_the_rivalry", "treaty_of_friendship"):
                world.root = "AVI"
                world.run(FOCUSES[native].get("completion_reward"), "AVI")
            for house in RIVAL:
                world.apply("HSM_VER_conclude_armistice", house)
                world.apply("HSM_VER_conclude_treaty", house)
                world.apply("HSM_VER_sign_treaty", house)
                before = world.snapshot()
                world.choose("hsm_ver_routes.1", 1, house)
                self.assertEqual(world.snapshot(), before)
            self.assertFalse(world.test("HSM_VER_armistice_valid"))
            self.assertFalse(world.test("HSM_VER_negotiated_peace_valid"))
            self.assertIn(("annex_everything", RIVAL[tag]), world.countries[tag].goals)
            self.assertNotIn("HSM_VER_armistice_pending", world.countries["ERI"].flags)
            self.assertNotIn("HSM_VER_treaty_pending", world.countries["ERI"].flags)


class FoundedUnionRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.union = runpy.run_path(str(Path(__file__).with_name("Test-VereniaUnification.py")))

    def found(self, tag):
        world = self.union["UnionWorld"]().begin(tag, avian="neutral")
        # Prior diplomatic-route history is input; founding executes production effects.
        world.countries[tag].flags.add("HSM_VER_diplomatic_route")
        world.countries[tag].focuses.update(
            ROUTES[tag][stage] for stage in ("entry", "armistice", "treaty", "charter", "final")
        )
        world.found(tag)
        self.assertTrue(world.has(tag, "founded"))
        self.assertTrue(world.has(tag, "absorbed_" + RIVAL[tag]))
        self.assertFalse(world.countries[RIVAL[tag]].exists)
        self.assertFalse(world.test("HSM_VER_charter_valid", tag))
        return world

    def assert_fallback_closed(self, world, tag):
        self.assertFalse(world.test("HSM_VER_conference_failed", tag))
        self.assertFalse(RouteWorld.available(world, ROUTES[tag]["fallback"], tag))
        self.assertNotIn(ROUTES[tag]["fallback"], world.countries[tag].focuses)

    def test_founded_union_disappearance_is_not_failed_negotiation(self):
        for tag in RIVAL:
            with self.subTest(tag=tag):
                world = self.found(tag)
                self.assert_fallback_closed(world, tag)

    def test_occupation_or_territory_loss_does_not_erase_successful_union(self):
        for tag in RIVAL:
            founded = self.found(tag)
            for state in ("391", "400", "401", "500", "673"):
                for field in ("owner", "controller"):
                    with self.subTest(tag=tag, state=state, field=field):
                        world = copy.deepcopy(founded)
                        setattr(world.state_ids[state], field, "GRI")
                        self.assertFalse(world.test("HSM_VER_UNI_ducal_land_held", tag))
                        world.daily()
                        self.assertTrue(world.has(tag, "founded"))
                        self.assert_fallback_closed(world, tag)

    def test_postwar_migration_preserves_union_without_rewards_or_new_talks(self):
        for tag in RIVAL:
            with self.subTest(tag=tag):
                world = self.found(tag)
                world.countries[tag].war = True
                world.countries[tag].wars.add("AVI")
                world.apply("HSM_VER_maintain_agreements", tag)
                self.assert_fallback_closed(world, tag)
                world.end_wars()
                # Exercise migration in an old founded save without route metadata.
                world.countries[tag].flags.discard("HSM_VER_route_revision_3")
                world.countries[tag].flags.discard("HSM_VER_diplomatic_route")
                resources = world.resources()
                focuses = {house: c.focuses.copy() for house, c in world.countries.items()}
                scheduled = copy.deepcopy(world.scheduled)
                for _ in range(2):
                    world.apply("HSM_VER_migrate_routes", tag)
                    world.apply("HSM_VER_maintain_agreements", tag)
                    self.assertIn("HSM_VER_diplomatic_route", world.countries[tag].flags)
                    self.assertTrue(world.has(tag, "founded"))
                    self.assert_fallback_closed(world, tag)
                    self.assertEqual(world.resources(), resources)
                    self.assertEqual({house: c.focuses for house, c in world.countries.items()}, focuses)
                    self.assertEqual(world.scheduled, scheduled)


if __name__ == "__main__":
    unittest.main(argv=[__file__] + BASE.REST, verbosity=2)
