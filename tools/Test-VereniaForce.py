"""Production-script fixtures for VERENIA_FORCE_CONTRACT.md, not an HOI4 emulator.

Run python -B tools/Test-VereniaForce.py [-q] [TestClass.test_name].
Reuses the strict parser, scope, state and event models without editing old tests.
War/peace hooks are explicitly dispatched with their installed native scopes;
territorial outcomes are fixture inputs, never substitute production effects.
"""
from __future__ import annotations

import copy
import itertools
import runpy
import unittest
from pathlib import Path

REG = runpy.run_path(str(Path(__file__).with_name("Test-VereniaRegency.py")))
BASE = REG["BASE"]
Node, read, walk, MOD, OPT, State = (REG[k] for k in ("Node", "read", "walk", "MOD", "OPT", "State"))
parse = BASE["parse"]
HOUSES = ("ERI", "EYR")
RIVAL = {"ERI": "EYR", "EYR": "ERI"}
DUKE = {"ERI": "ERI_duke_vincent_erie", "EYR": "EYR_duke_iovinus_eyrie"}
PROOF = {"HSM_VER_FORCE_war_recorded", "HSM_VER_FORCE_rival_defeated", "HSM_VER_FORCE_peace_recorded"}
SEATS = ("391", "400", "401", "500", "673")
AVIAN_PROOF = {"HSM_VER_FORCE_AVI_war", "HSM_VER_FORCE_AVI_defeated", "HSM_VER_FORCE_AVI_peace"}
LEGACY_AVIAN_FOCUS = {"ERI": "HSM_ERI_invite_avian", "EYR": "HSM_EYR_a_seat_for_avian"}


class ForceWorld(REG["RegencyWorld"]):
    def __init__(self):
        super().__init__()
        for country in self.countries.values():
            country.naps = set()
            country.war_support = 0.5
            country.blocked_declarations = set()
        for tag in HOUSES:
            self.countries[tag].ideas.add("E_E_rivalry")
            self.countries[tag].party_leaders["neutrality"] = DUKE[tag]
        for key, states in self.arrays.items():
            for state in states:
                state.owner = state.controller = key.split(".")[0]
        for filename in ("391-Verenia.txt", "400-Eyrie.txt", "401-Erie.txt", "500-Balefire.txt", "673-Comrik.txt", "470-Avian.txt"):
            source = read(OPT.eaw / "history/states" / filename)[0]
            history = Node("history", "=", source.get("history"))
            owner = history.get("owner")
            state = State(owner=owner, controller=owner,
                          cores={n.value for n in history.all("add_core_of")})
            state.buildings = {n.key: int(n.value) for n in history.get("buildings", [])
                               if n.key in ("industrial_complex", "arms_factory", "infrastructure")}
            self.state_ids[source.get("id")] = state
            self.states.append(state)
        for state in self.states:
            state.fully_controlled = True
        self.goal_actions = []
        self.relations = []
        self.annexations = []
        self.core_actions = []
        self.root = "ERI"

    def check(self, nodes, tag="ERI"):
        for n in nodes:
            if n.key == "has_non_aggression_pact_with":
                ok = self.resolve(n.value) in self.countries[tag].naps
            elif n.key == "can_declare_war_on":
                country = self.countries[tag]
                target = self.resolve(n.value)
                other = self.countries[target]
                # Engine-only diplomatic/rule exclusions are explicit fixture inputs.
                ok = (country.exists and other.exists and not country.subject
                      and target not in country.blocked_declarations
                      and target not in country.naps and target not in country.wars
                      and not (country.faction and country.faction == other.faction))
            elif n.key == "has_wargoal_against":
                target = self.resolve(n.get("target") if n.children else n.value)
                ok = any(t == target and (not n.get("type") or kind == n.get("type"))
                         for kind, t in self.countries[tag].goals)
            elif n.key == "has_political_power":
                ok = REG["COMPARE"][n.op](self.countries[tag].political_power, float(n.value))
            elif n.key == "is_fully_controlled_by":
                assert isinstance(tag, State)
                ok = tag.controller == self.resolve(n.value) and tag.fully_controlled
            elif n.key == "has_full_control_of_state":
                state = self.state_ids[n.value]
                ok = state.controller == tag and state.fully_controlled
            elif n.key == "free_building_slots":
                assert isinstance(tag, State)
                assert n.get("building") in ("industrial_complex", "arms_factory")
                assert n.get("include_locked") == "yes"
                size = n.all("size")[0]
                assert size.op == ">" and size.value == "0"
                ok = sum(v for k, v in tag.buildings.items() if k != "infrastructure") < tag.capacity
            else:
                ok = super().check([n], tag)
            if not ok:
                return False
        return True

    def run(self, nodes, tag="ERI"):
        branch_taken = None
        for n in nodes:
            if n.key == "if":
                branch_taken = self.check(n.get("limit", []), tag)
                if branch_taken:
                    self.run([x for x in n.children if x.key != "limit"], tag)
            elif n.key == "else_if":
                assert branch_taken is not None
                if not branch_taken and self.check(n.get("limit", []), tag):
                    branch_taken = True
                    self.run([x for x in n.children if x.key != "limit"], tag)
            elif n.key == "else":
                assert branch_taken is not None
                if not branch_taken:
                    self.run(n.children, tag)
                branch_taken = True
            elif n.key == "create_wargoal":
                target = self.resolve(n.get("target"))
                goal = (n.get("type"), target)
                assert target in self.countries
                self.countries[tag].goals.add(goal)
                self.goal_actions.append((tag, goal))
            elif n.key == "add_war_support":
                self.countries[tag].war_support += float(n.value)
            elif n.key in ("show_ideas_tooltip", "log"):
                assert tag in self.countries and isinstance(n.value, str)
                self.trace.append((tag, n.key, n.value))
            elif n.key == "diplomatic_relation":
                assert n.get("relation") == "non_aggression_pact"
                target = self.resolve(n.get("country"))
                assert n.get("active") in ("yes", "no")
                self.nap(tag, target, n.get("active") == "yes")
                self.relations.append((tag, target, n.get("relation"), n.get("active")))
            elif n.key == "add_core_of":
                assert isinstance(tag, State)
                target = self.resolve(n.value)
                tag.cores.add(target)
                self.core_actions.append((tag, target))
            elif n.key == "annex_country":
                target = self.resolve(n.get("target"))
                assert n.get("transfer_troops") == "yes"
                self.annexations.append((tag, target))
                for state in self.states:
                    if state.owner == target:
                        state.owner = tag
                        if state.controller == target:
                            state.controller = tag
                country = self.countries[target]
                country.exists = country.subject = False
                country.overlord = ""
                root, sender = self.root, self.sender
                self.hook("on_annex", tag, target)
                self.root, self.sender = root, sender
            else:
                super().run([n], tag)

    def nap(self, first, second, active=True):
        for tag, other in ((first, second), (second, first)):
            if active:
                self.countries[tag].naps.add(other)
            else:
                self.countries[tag].naps.discard(other)

    def force(self, suffix, tag="ERI"):
        self.root = tag
        self.apply("HSM_VER_FORCE_" + suffix, tag)

    def force_test(self, suffix, tag="ERI"):
        self.root = tag
        return self.test("HSM_VER_FORCE_" + suffix, tag)

    def declare(self, attacker, defender):
        self.hook("on_declare_war", attacker, defender)
        self.join_defence(attacker, defender)
        self.hook("on_war_relation_added", attacker, defender)

    def capitulate(self, loser, winner):
        self.countries[loser].capitulated = True
        self.hook("on_capitulation_immediate", loser, winner)

    def peace(self, winner, loser, subject=False):
        self.end_wars()
        self.countries[loser].capitulated = False
        self.countries[loser].exists = subject
        self.countries[loser].subject = subject
        self.countries[loser].overlord = winner if subject else ""
        for state_id in SEATS:
            state = self.state_ids[state_id]
            holder = loser if subject and loser in state.cores else winner
            state.owner = state.controller = holder
        self.hook("on_peaceconference_ended", winner, loser)

    def victory(self, winner="ERI", subject=False):
        self.declare(winner, RIVAL[winner])
        self.capitulate(RIVAL[winner], winner)
        self.peace(winner, RIVAL[winner], subject)
        self.advance_days(30)

    def reward_force(self, focus_id, tag):
        self.root = tag
        self.countries[tag].focuses.add(focus_id)
        self.run(self.focuses[focus_id].get("completion_reward", []), tag)

    def available_force(self, focus_id, tag):
        self.root = tag
        return self.check(self.focuses[focus_id].get("available", []), tag)

    def complete_force(self, focus_id, tag):
        focus = self.focuses[focus_id]
        country = self.countries[tag]
        assert focus_id not in country.focuses
        assert all(any(n.value in country.focuses for n in group.children)
                   for group in focus.all("prerequisite")), focus_id
        assert not any(n.value in country.focuses for group in focus.all("mutually_exclusive") for n in group.children)
        self.root = tag
        if focus.get("bypass") and self.check(focus.get("bypass"), tag):
            country.focuses.add(focus_id)
        else:
            assert self.available_force(focus_id, tag), focus_id
            self.reward_force(focus_id, tag)

    def erie(self, suffix):
        self.reward_force("HSM_ERI_FORCE_" + suffix, "ERI")

    def erie_settlement(self, policy=0, claim=None, subject=False):
        self.erie("the_price_of_victory")
        self.victory("ERI", subject)
        self.erie("terms_for_the_defeated")
        self.choose("hsm_ver_eri_force.4", policy, "ERI")
        if claim is not None:
            self.erie("district_charters" if policy == 0 else "ducal_commissioners")
            self.erie("the_first_petition")
            self.choose("hsm_ver_eri_force.5", claim, "ERI")

    def eyrie(self, suffix):
        self.reward_force("HSM_EYR_FORCE_" + suffix, "EYR")

    def eyrie_settlement(self, policy=0, post=0, workshop=None, subject=False):
        self.eyrie("the_last_campaign")
        self.victory("EYR", subject)
        self.eyrie("victory_and_the_garrison")
        self.choose("hsm_ver_eyr_force.2", policy, "EYR")
        self.eyrie("montagues_unsent_reply")
        self.choose("hsm_ver_eyr_force.3", post, "EYR")
        if workshop is not None:
            self.eyrie("workshops_after_war")
            self.advance_days(120)
            self.daily()
            self.choose("hsm_ver_eyr_force.4", workshop, "EYR")

    def resources(self, tag):
        country = self.countries[tag]
        return copy.deepcopy((country.political_power, country.manpower, country.army_experience,
                              country.bonuses, [(s.extra_slots, s.buildings) for s in self.states]))

    def select_avian_route(self, route):
        assert route in (None, "intergigantes", "pursue_true_neutrality")
        focuses = self.countries["AVI"].focuses
        focuses.difference_update({"intergigantes", "pursue_true_neutrality"})
        focuses.add("proclamation_of_neutrality")
        if route:
            focuses.add(route)

    def avian_frontier(self, house, *, avian_route="pursue_true_neutrality", authority="force"):
        self.select_avian_route(avian_route)
        if authority == "force":
            self.victory(house)
            self.force("open_settlement", house)
        elif authority == "charter":
            self.charter()
            assert self.test("HSM_VER_charter_valid", house)
        elif authority == "union":
            # Founding and territorial outcomes are inputs from the separate UNI
            # campaign; this fixture must not invent military victory certificates.
            self.countries[house].flags.add("HSM_VER_UNI_founded")
            self.countries[RIVAL[house]].exists = False
            for state_id in SEATS:
                self.state_ids[state_id].owner = self.state_ids[state_id].controller = house
            assert self.test("HSM_VER_UNI_ducal_land_held", house)
        else:
            raise AssertionError(f"Unknown regional authority: {authority}")
        country = self.countries[house]
        country.political_power = 200
        self.complete_force("HSM_" + house + "_avian_question", house)

    def avian_peace(self, house, subject=False):
        self.end_wars()
        avian = self.countries["AVI"]
        avian.capitulated = False
        avian.exists = avian.subject = subject
        avian.overlord = house if subject else ""
        self.state_ids["470"].owner = self.state_ids["470"].controller = "AVI" if subject else house
        self.hook("on_peaceconference_ended", house, "AVI")

    def avian_victory(self, house, subject=False):
        self.declare(house, "AVI")
        self.capitulate("AVI", house)
        self.avian_peace(house, subject)
        self.advance_days(30)

    def avian_terms(self, house, subject=False, policy=0, *, authority="force"):
        self.avian_frontier(house, authority=authority)
        prefix = "HSM_" + house + "_FORCE_"
        self.complete_force(prefix + "avian_claim", house)
        self.avian_victory(house, subject)
        self.complete_force(prefix + "avian_articles", house)
        self.advance_days(1)
        event = "hsm_ver_force.11" if subject else "hsm_ver_force.12"
        target = "AVI" if subject else house
        assert self.deliver(event, target)
        self.choose(event, policy, target)


class Harness(unittest.TestCase):
    def test_native_seats_and_original_dukes(self):
        world = ForceWorld()
        for tag, state_ids in (("ERI", ("401", "500", "673")), ("EYR", ("391", "400"))):
            for state_id in state_ids:
                self.assertEqual(world.state_ids[state_id].owner, tag)
                self.assertIn(tag, world.state_ids[state_id].cores)
        for tag, state_id in (("ERI", "401"), ("EYR", "400")):
            self.assertEqual(world.state_ids[state_id].owner, tag)
            self.assertEqual(world.state_ids[state_id].cores, {tag})
            source = read(OPT.eaw / "history/countries" / (tag + " - House" + ("Erie" if tag == "ERI" else "Eyrie") + ".txt"))
            self.assertIn(DUKE[tag], {n.value for n in source if n.key == "recruit_character"})

    def test_unknown_operations_fail_closed(self):
        world = ForceWorld()
        with self.assertRaises(AssertionError):
            world.check(parse("invented_predicate = yes"))
        with self.assertRaises(AssertionError):
            world.run(parse("invented_effect = yes"))

    def test_tooltip_conditions_and_hidden_effects_are_transparent(self):
        world = ForceWorld()
        condition = parse("custom_trigger_tooltip = { tooltip = localised_key 400 = { is_owned_by = EYR } EYR = { is_subject = no } }")
        self.assertTrue(world.check(condition))
        world.countries["EYR"].subject = True
        self.assertFalse(world.check(condition))
        with self.assertRaises(AssertionError):
            world.check(parse("custom_trigger_tooltip = { tooltip = localised_key invented_predicate = yes }"))
        world.run(parse("hidden_effect = { EYR = { add_political_power = 7 set_country_flag = tested_hidden_scope } }"))
        self.assertEqual(world.countries["EYR"].political_power, 7)
        self.assertIn("tested_hidden_scope", world.countries["EYR"].flags)
        self.assertNotIn("tested_hidden_scope", world.countries["ERI"].flags)
        before = copy.deepcopy(world.countries)
        world.run(parse("show_ideas_tooltip = HSM_ERI_FORCE_war_obligations"))
        self.assertEqual(before, world.countries)
        self.assertEqual(world.trace[-1], ("ERI", "show_ideas_tooltip", "HSM_ERI_FORCE_war_obligations"))


class HostilityLocks(unittest.TestCase):
    def test_only_original_independent_ruling_dukes_are_eligible(self):
        for tag, reason in itertools.product(HOUSES, ("subject", "capitulated", "absent", "replacement")):
            with self.subTest(tag=tag, reason=reason):
                world = ForceWorld()
                self.assertTrue(world.force_test("eligible_house", tag))
                country = world.countries[tag]
                if reason == "replacement":
                    country.leader = "other_ruling_character"
                else:
                    setattr(country, {"subject": "subject", "capitulated": "capitulated", "absent": "exists"}[reason], reason != "absent")
                self.assertFalse(world.force_test("eligible_house", tag))
        for tag in ("AVI", "GRI", "D01"):
            self.assertFalse(ForceWorld().force_test("eligible_house", tag))

    def test_live_agreements_block_preparation_and_stale_goal_completion(self):
        for tag, agreement in itertools.product(HOUSES, ("armistice", "treaty_signed", "nap", "faction")):
            with self.subTest(tag=tag, agreement=agreement):
                world = ForceWorld()
                self.assertTrue(world.force_test("can_prepare", tag))
                self.assertTrue(world.force_test("can_issue_goal", tag))
                world.force("prepare", tag)
                if agreement == "nap":
                    world.nap(tag, RIVAL[tag])
                elif agreement == "faction":
                    for house in HOUSES:
                        world.countries[house].faction = "shared_faction"
                else:
                    for house in HOUSES:
                        world.countries[house].flags.add("HSM_VER_" + agreement)
                self.assertFalse(world.force_test("can_prepare", tag))
                self.assertFalse(world.force_test("can_issue_goal", tag))
                world.force("issue_goal", tag)
                self.assertEqual(world.goal_actions, [])

    def test_subject_or_absent_rival_cannot_receive_a_fresh_goal(self):
        for tag, reason in itertools.product(HOUSES, ("foreign_subject", "own_subject", "annexed")):
            with self.subTest(tag=tag, reason=reason):
                world = ForceWorld()
                rival = world.countries[RIVAL[tag]]
                rival.subject = reason != "annexed"
                rival.exists = reason != "annexed"
                rival.overlord = tag if reason == "own_subject" else "GRI"
                self.assertFalse(world.force_test("can_issue_goal", tag))
                self.assertFalse(world.force_test("can_prepare", tag))
                world.force("issue_goal", tag)
                self.assertEqual(world.goal_actions, [])

    def test_native_white_peace_cooldown_blocks_goal(self):
        for tag, holder in itertools.product(HOUSES, HOUSES):
            with self.subTest(tag=tag, holder=holder):
                world = ForceWorld()
                world.countries[holder].flags.add("had_war_with_rival")
                self.assertFalse(world.force_test("can_issue_goal", tag))
                world.force("issue_goal", tag)
                self.assertEqual(world.goal_actions, [])

    def test_refusal_is_not_a_peace_or_a_military_lock(self):
        for tag in HOUSES:
            world = ForceWorld()
            for country in world.countries.values():
                country.flags.update({"HSM_VER_armistice_refused", "HSM_VER_treaty_refused", "HSM_VER_armistice_retry", "HSM_VER_treaty_retry"})
            self.assertTrue(world.force_test("can_prepare", tag))
            self.assertTrue(world.force_test("can_issue_goal", tag))

    def test_goal_is_exact_rival_and_never_a_declaration(self):
        for tag in HOUSES:
            world = ForceWorld()
            world.sender = "AVI"
            world.force("issue_goal", tag)
            self.assertEqual({target for kind, target in world.countries[tag].goals}, {RIVAL[tag]})
            self.assertFalse(any(c.war for c in world.countries.values()))
            self.assertEqual(world.countries["AVI"].goals, set())

    def test_native_friendship_and_engine_declaration_lock_are_respected(self):
        for tag, lock in itertools.product(HOUSES, ("native_friendship", "engine_rule")):
            world = ForceWorld()
            if lock == "native_friendship":
                world.countries["AVI"].focuses.add("treaty_of_friendship")
                self.assertFalse(world.force_test("can_prepare", tag))
            else:
                world.countries[tag].blocked_declarations.add(RIVAL[tag])
            self.assertFalse(world.force_test("can_issue_goal", tag))
            world.force("issue_goal", tag)
            self.assertEqual(world.goal_actions, [])

    def test_goal_idempotence_and_armistice_removal(self):
        for tag in HOUSES:
            world = ForceWorld()
            world.force("issue_goal", tag)
            world.force("issue_goal", tag)
            self.assertEqual(world.goal_actions, [(tag, ("annex_everything", RIVAL[tag]))])
            world.root = "ERI"
            world.armistice()
            self.assertTrue(world.test("HSM_VER_armistice_valid", "ERI"))
            self.assertFalse(world.countries[tag].goals)

    def test_native_friendship_adoption_differs_from_a_refused_new_campaign_offer(self):
        for house, legacy in itertools.product(HOUSES, (False, True)):
            with self.subTest(house=house, legacy=legacy):
                world = ForceWorld()
                if not legacy:
                    world.apply("HSM_VER_enable_negotiated_campaign", "ERI")
                world.countries["AVI"].focuses.add("treaty_of_friendship")
                if legacy:
                    self.assertFalse(world.force_test("can_prepare", house))
                    world.apply("HSM_VER_enable_negotiated_campaign", "ERI")
                    self.assertTrue(world.test("HSM_VER_negotiated_peace_valid", "ERI"))
                else:
                    world.armistice()
                    world.reward_force("treaty_of_friendship", "AVI")
                    world.choose("hsm_verenia.30", 2, "EYR")
                    self.assertIn("HSM_VER_treaty_refused", world.countries["ERI"].flags)
                    self.assertFalse(world.force_test("can_prepare", house))
                    world.advance_days(365)
                    self.assertFalse(world.test("HSM_VER_negotiated_peace_valid", "ERI"))
                self.assertEqual(world.force_test("can_prepare", house), not legacy)
                self.assertEqual(world.force_test("can_issue_goal", house), not legacy)
                world.force("issue_goal", house)
                self.assertEqual(bool(world.goal_actions), not legacy)


class WarEvidence(unittest.TestCase):
    def test_actual_bilateral_war_is_recorded_before_any_focus(self):
        for attacker in HOUSES:
            world = ForceWorld()
            world.declare(attacker, RIVAL[attacker])
            for tag in HOUSES:
                self.assertIn("HSM_VER_FORCE_war_recorded", world.countries[tag].flags)
                self.assertTrue(world.force_test("at_war", tag))
                self.assertTrue(world.force_test("can_prepare", tag))
                self.assertFalse(world.force_test("can_issue_goal", tag))
                self.assertNotIn("HSM_VER_FORCE_campaign", world.countries[tag].flags)

    def test_daily_only_backfills_actual_current_rival_war(self):
        for opponent in ("EYR", "GRI", "AVI", None):
            with self.subTest(opponent=opponent):
                world = ForceWorld()
                if opponent:
                    world.join_defence("ERI", opponent)
                world.daily()
                for tag in HOUSES:
                    self.assertEqual("HSM_VER_FORCE_war_recorded" in world.countries[tag].flags, opponent == "EYR")
                    self.assertNotIn("HSM_VER_FORCE_rival_defeated", world.countries[tag].flags)
                    self.assertFalse(world.force_test("settlement_context", tag))

    def test_capitulation_requires_exact_loser_and_a_participating_victor(self):
        for house, wrong in itertools.product(HOUSES, ("loser", "winner", "no_war")):
            with self.subTest(house=house, wrong=wrong):
                world = ForceWorld()
                if wrong != "no_war":
                    world.declare(house, RIVAL[house])
                world.capitulate("GRI" if wrong == "loser" else RIVAL[house], "GRI" if wrong == "winner" else house)
                self.assertNotIn("HSM_VER_FORCE_rival_defeated", world.countries[house].flags)
        for house in HOUSES:
            world = ForceWorld()
            world.declare(house, RIVAL[house])
            world.countries["GRI"].war_allies.add(house)
            world.capitulate(RIVAL[house], "GRI")
            self.assertIn("HSM_VER_FORCE_rival_defeated", world.countries[house].flags)

    def test_actual_peace_requires_exact_rival_and_complete_proof(self):
        for house, missing in itertools.product(HOUSES, ("winner", "loser", "war_recorded", "rival_defeated")):
            with self.subTest(house=house, missing=missing):
                world = ForceWorld()
                world.declare(house, RIVAL[house])
                world.capitulate(RIVAL[house], house)
                if missing in ("war_recorded", "rival_defeated"):
                    world.countries[house].flags.remove("HSM_VER_FORCE_" + missing)
                world.end_wars()
                world.hook("on_peaceconference_ended", "GRI" if missing == "winner" else house,
                           "GRI" if missing == "loser" else RIVAL[house])
                self.assertNotIn("HSM_VER_FORCE_peace_recorded", world.countries[house].flags)

    def test_native_white_peace_bypass_on_either_participant_invalidates_defeat(self):
        for house, holder in itertools.product(HOUSES, HOUSES):
            with self.subTest(house=house, holder=holder):
                world = ForceWorld()
                world.declare(house, RIVAL[house])
                world.capitulate(RIVAL[house], house)
                world.countries[holder].flags.add("bypass_on_peaceconference_ended")
                world.peace(house, RIVAL[house])
                world.daily()
                self.assertFalse(PROOF & world.countries[house].flags)
                world.countries[holder].flags.remove("bypass_on_peaceconference_ended")
                world.hook("on_peaceconference_ended", house, RIVAL[house])
                world.advance_days(30)
                self.assertFalse(world.force_test("settlement_context", house))

    def test_uncapitulation_clears_defeat_before_later_peace(self):
        for house in HOUSES:
            world = ForceWorld()
            world.declare(house, RIVAL[house])
            world.capitulate(RIVAL[house], house)
            world.countries[RIVAL[house]].capitulated = False
            world.hook("on_uncapitulation", RIVAL[house], "GRI")
            self.assertNotIn("HSM_VER_FORCE_rival_defeated", world.countries[house].flags)
            world.peace(house, RIVAL[house])
            world.advance_days(30)
            self.assertFalse(world.force_test("settlement_context", house))

    def test_new_bilateral_war_clears_old_certificates_for_both_houses(self):
        for attacker in HOUSES:
            world = ForceWorld()
            for house in HOUSES:
                world.countries[house].flags.update(PROOF | {"HSM_VER_FORCE_settling"})
            world.declare(attacker, RIVAL[attacker])
            for house in HOUSES:
                self.assertEqual(PROOF & world.countries[house].flags, {"HSM_VER_FORCE_war_recorded"})
                self.assertNotIn("HSM_VER_FORCE_settling", world.countries[house].flags)

    def test_settling_exactly_thirty_days_with_annexed_or_defeated_subject(self):
        for house, subject in itertools.product(HOUSES, (False, True)):
            with self.subTest(house=house, subject=subject):
                world = ForceWorld()
                world.declare(house, RIVAL[house])
                world.capitulate(RIVAL[house], house)
                world.peace(house, RIVAL[house], subject)
                self.assertFalse(world.force_test("settlement_context", house))
                world.advance_days(29)
                self.assertFalse(world.force_test("settlement_context", house))
                world.advance_days(1)
                self.assertTrue(world.force_test("settlement_context", house))
                self.assertTrue(world.force_test("can_prepare", house))
                self.assertFalse(world.force_test("settlement_active", house))


class TerritorialSettlement(unittest.TestCase):
    def test_external_war_blocks_new_settlement_opening_but_not_territorial_proof(self):
        for house in HOUSES:
            world = ForceWorld()
            world.victory(house)
            world.declare("GRI", house)
            world.daily()
            self.assertTrue(world.force_test("settlement_held", house))
            self.assertFalse(world.force_test("settlement_context", house))
            world.force("open_settlement", house)
            self.assertFalse(world.force_test("settlement_active", house))
            self.assertNotIn("HSM_VER_FORCE_settlement_started", world.countries[house].flags)
            world.end_wars()
            world.force("open_settlement", house)
            self.assertTrue(world.force_test("settlement_active", house))

    def test_external_war_preserves_established_institutions_and_usable_military_modifiers(self):
        for house, policy, subject in itertools.product(HOUSES, (0, 1), (False, True)):
            with self.subTest(house=house, policy=policy, subject=subject):
                world = ForceWorld()
                if house == "ERI":
                    world.erie_settlement(policy, 1, subject)
                    idea_id, modifier_key = "HSM_ERI_FORCE_patron_claims", "army_attack_factor"
                    idea_file = "HSM_VER_erie_force.txt"
                else:
                    world.eyrie_settlement(policy, 1, 1 if policy == 0 else 2, subject)
                    idea_id, modifier_key = ("HSM_EYR_FORCE_supervised_correspondence", "planning_speed")
                    idea_file = "HSM_VER_eyrie_force.txt"
                country = world.countries[house]
                prefix = "HSM_" + house + "_FORCE_"
                ideas = {i for i in country.ideas if i.startswith(prefix)}
                resources = world.resources(house)
                world.declare("GRI", house)
                if subject:
                    world.join_defence("GRI", RIVAL[house])
                for _ in range(3):
                    world.daily()
                self.assertTrue(country.war)
                self.assertTrue(world.force_test("settlement_held", house))
                self.assertFalse(world.force_test("settlement_context", house))
                self.assertTrue(world.force_test("settlement_active", house))
                self.assertEqual(ideas, {i for i in country.ideas if i.startswith(prefix)})
                self.assertIn(idea_id, country.ideas)
                definitions = {n.key: n for n in walk(read(MOD / "common/ideas" / idea_file))
                               if n.get("modifier")}
                bonus = Node("modifier", "=", definitions[idea_id].get("modifier"))
                self.assertGreater(float(bonus.get(modifier_key)), 0)
                for idea in ideas:
                    cancel = definitions[idea].get("cancel")
                    if cancel:
                        self.assertFalse(world.check(cancel, house), idea)
                self.assertEqual(resources, world.resources(house))
                focus = "reconstruction_contracts" if house == "ERI" else ("useful_trades" if policy == 0 else "permanent_district_staff")
                self.assertTrue(world.available_force(prefix + focus, house))
                world.reward_force(prefix + focus, house)
                after = world.resources(house)
                self.assertNotEqual(resources, after)
                world.daily()
                self.assertEqual(after, world.resources(house))

    def test_renewed_bilateral_war_removes_established_benefits_until_new_victory_proof(self):
        for house in HOUSES:
            world = ForceWorld()
            if house == "ERI":
                world.erie_settlement(1, 1, subject=True)
            else:
                world.eyrie_settlement(1, 1, 2, subject=True)
            country = world.countries[house]
            rival = world.countries[RIVAL[house]]
            prefix = "HSM_" + house + "_FORCE_"
            self.assertTrue({i for i in country.ideas if i.startswith(prefix)})
            rival.subject = False
            rival.overlord = ""
            world.declare(RIVAL[house], house)
            world.daily()
            self.assertFalse(world.force_test("settlement_held", house))
            self.assertFalse(world.force_test("settlement_active", house))
            self.assertFalse({i for i in country.ideas if i.startswith(prefix)})
            self.assertEqual(PROOF & country.flags, {"HSM_VER_FORCE_war_recorded"})
            world.end_wars()
            rival.subject = True
            rival.overlord = house
            world.daily()
            self.assertFalse(world.force_test("settlement_active", house))
            self.assertFalse({i for i in country.ideas if i.startswith(prefix)})
            self.assertFalse(PROOF & country.flags)

    def test_controller_status_without_full_control_of_any_province_is_insufficient(self):
        for house, state_id, subject in itertools.product(HOUSES, SEATS, (False, True)):
            with self.subTest(house=house, state=state_id, subject=subject):
                world = ForceWorld()
                world.victory(house, subject)
                self.assertTrue(world.force_test("settlement_context", house))
                world.state_ids[state_id].fully_controlled = False
                self.assertFalse(world.force_test("settlement_context", house))

    def test_each_of_five_states_needs_settled_owner_and_controller(self):
        for house, state_id, attribute in itertools.product(HOUSES, SEATS, ("owner", "controller")):
            with self.subTest(house=house, state=state_id, attribute=attribute):
                world = ForceWorld()
                world.victory(house)
                self.assertTrue(world.force_test("settlement_context", house))
                setattr(world.state_ids[state_id], attribute, "GRI")
                self.assertFalse(world.force_test("settlement_context", house))
                world.force("open_settlement", house)
                self.assertIn("E_E_rivalry", world.countries[house].ideas)

    def test_occupation_alone_and_unrelated_puppets_do_not_qualify(self):
        for house, reason in itertools.product(HOUSES, ("occupation", "independent_rival", "foreign_puppet", "unrelated_puppet", "no_proof")):
            with self.subTest(house=house, reason=reason):
                world = ForceWorld()
                world.victory(house, subject=True)
                rival = world.countries[RIVAL[house]]
                if reason == "occupation":
                    rival.subject = False
                    for state in world.states:
                        if state.owner == RIVAL[house]:
                            state.controller = house
                elif reason == "independent_rival":
                    rival.subject = False
                elif reason == "foreign_puppet":
                    rival.overlord = "GRI"
                elif reason == "unrelated_puppet":
                    world.countries["CYA"].subject = True
                    world.countries["CYA"].overlord = house
                    for state in world.states:
                        if state.owner == RIVAL[house]:
                            state.owner = state.controller = "CYA"
                else:
                    world.countries[house].flags.difference_update(PROOF)
                self.assertFalse(world.force_test("settlement_context", house))

    def test_opening_only_removes_rivalry_from_victor_and_actual_defeated_subject(self):
        for house, subject in itertools.product(HOUSES, (False, True)):
            world = ForceWorld()
            world.victory(house, subject)
            before = [(s.owner, s.controller, set(s.cores)) for s in world.states]
            avian = copy.deepcopy(world.countries["AVI"])
            world.force("open_settlement", house)
            world.force("open_settlement", house)
            self.assertTrue(world.force_test("settlement_active", house))
            self.assertNotIn("E_E_rivalry", world.countries[house].ideas)
            self.assertEqual("E_E_rivalry" in world.countries[RIVAL[house]].ideas, not subject)
            self.assertEqual(before, [(s.owner, s.controller, set(s.cores)) for s in world.states])
            self.assertEqual(avian, world.countries["AVI"])


class AvianConsent(unittest.TestCase):
    def offer(self, house):
        world = ForceWorld()
        world.select_avian_route("intergigantes")
        world.victory(house)
        world.force("open_settlement", house)
        world.force("approach_avian", house)
        world.advance_days(1)
        self.assertTrue(world.deliver("hsm_ver_force.4", house))
        world.choose("hsm_ver_force.4", 0, house)
        world.advance_days(1)
        self.assertTrue(world.deliver("hsm_ver_force.1", "AVI"))
        self.assertEqual(world.sender, house)
        return world

    def test_actual_from_house_consent_only_creates_bilateral_nap(self):
        for house, option in itertools.product(HOUSES, (0, 1)):
            with self.subTest(house=house, option=option):
                world = self.offer(house)
                before = [(s.owner, s.controller, set(s.cores)) for s in world.states]
                avian = world.countries["AVI"]
                self.assertFalse(avian.naps)
                world.choose("hsm_ver_force.1", option, "AVI")
                world.choose("hsm_ver_force.1", 1 - option, "AVI")
                self.assertIn("HSM_VER_FORCE_avian_resolved", world.countries[house].flags)
                self.assertEqual(avian.naps, {house} if option == 0 else set())
                self.assertEqual(len(world.relations), 1 if option == 0 else 0)
                self.assertFalse(avian.subject)
                self.assertEqual(avian.faction, "")
                self.assertEqual(avian.leader, REG["KATRINA"])
                self.assertEqual(before, [(s.owner, s.controller, set(s.cores)) for s in world.states])

    def test_legacy_avian_offers_remain_blocked_during_war_on_either_side(self):
        for house, side in itertools.product(HOUSES, ("victor", "avian")):
            with self.subTest(house=house, side=side):
                world = ForceWorld()
                world.select_avian_route("intergigantes")
                world.victory(house)
                world.force("open_settlement", house)
                self.assertTrue(world.test("HSM_VER_AVI_intergigantes_route", house))
                world.declare("GRI", house if side == "victor" else "AVI")
                self.assertTrue(world.force_test("settlement_active", house))
                world.force("approach_avian", house)
                self.assertNotIn("HSM_VER_FORCE_avian_pending", world.countries[house].flags)
                self.assertNotIn("hsm_ver_force.1", world.countries["AVI"].events)
                self.assertFalse(world.countries["AVI"].naps)

    def test_victor_external_war_cancels_pending_reply_until_a_fresh_peacetime_offer(self):
        for house in HOUSES:
            world = self.offer(house)
            world.declare("GRI", house)
            world.sender = house
            world.choose("hsm_ver_force.1", 0, "AVI")
            self.assertFalse(world.countries["AVI"].naps)
            world.daily()
            self.assertTrue(world.force_test("settlement_active", house))
            self.assertNotIn("HSM_VER_FORCE_avian_pending", world.countries[house].flags)
            world.force("approach_avian", house)
            self.assertEqual(world.countries["AVI"].events.count("hsm_ver_force.1"), 1)
            world.end_wars()
            world.sender = house
            world.choose("hsm_ver_force.1", 0, "AVI")
            self.assertFalse(world.countries["AVI"].naps)
            self.assertNotIn("HSM_VER_FORCE_avian_resolved", world.countries[house].flags)
            world.force("approach_avian", house)
            world.advance_days(1)
            self.assertTrue(world.deliver("hsm_ver_force.1", "AVI"))
            world.choose("hsm_ver_force.1", 0, "AVI")
            self.assertEqual(world.countries["AVI"].naps, {house})

    def test_delayed_avian_acceptance_rechecks_both_sides_and_exact_territory(self):
        for house, stale in itertools.product(HOUSES, ("avian_war", "victor_war", "avian_subject", "avian_occupied", "new_duke", "territory", "pending_expired", "wrong_sender", "neutral_route", "undecided_route", "conflicting_routes")):
            with self.subTest(house=house, stale=stale):
                world = self.offer(house)
                if stale == "avian_war":
                    world.join_defence("GRI", "AVI")
                elif stale == "victor_war":
                    world.join_defence("GRI", house)
                elif stale == "avian_subject":
                    world.countries["AVI"].subject = True
                elif stale == "avian_occupied":
                    world.countries["AVI"].capitulated = True
                elif stale == "new_duke":
                    world.countries[house].leader = "replacement"
                elif stale == "territory":
                    world.state_ids["500"].controller = "GRI"
                elif stale == "pending_expired":
                    world.advance_days(45)
                elif stale == "neutral_route":
                    world.select_avian_route("pursue_true_neutrality")
                elif stale == "undecided_route":
                    world.select_avian_route(None)
                elif stale == "conflicting_routes":
                    world.countries["AVI"].focuses.add("pursue_true_neutrality")
                else:
                    world.sender = "GRI"
                world.choose("hsm_ver_force.1", 0, "AVI")
                self.assertFalse(world.countries["AVI"].naps)
                self.assertFalse(world.relations)
                self.assertNotIn("HSM_VER_FORCE_avian_resolved", world.countries[house].flags)

    def test_dropped_invitation_expires_and_resolved_offer_never_repeats(self):
        for house in HOUSES:
            world = self.offer(house)
            world.force("approach_avian", house)
            self.assertEqual(world.countries["AVI"].events.count("hsm_ver_force.1"), 1)
            world.advance_days(45)
            world.force("approach_avian", house)
            self.assertEqual(world.countries["AVI"].events.count("hsm_ver_force.1"), 2)
            world.advance_days(1)
            self.assertTrue(world.deliver("hsm_ver_force.1", "AVI"))
            world.choose("hsm_ver_force.1", 1, "AVI")
            world.advance_days(100)
            world.force("approach_avian", house)
            self.assertEqual(world.countries["AVI"].events.count("hsm_ver_force.1"), 2)


class ErieSettlement(unittest.TestCase):
    def test_daily_refresh_does_not_reinstall_existing_spirits(self):
        for policy, claim, finale in itertools.product((0, 1), (0, 1), (False, True)):
            world = ForceWorld()
            world.erie_settlement(policy, claim)
            if finale:
                world.erie("a_bound_duke" if policy == 0 else "a_single_chancery")
            before = world.resources("ERI")
            world.idea_actions.clear()
            for _ in range(3):
                world.daily()
            self.assertFalse([idea for tag, idea in world.idea_actions if idea.startswith("HSM_ERI_FORCE_")])
            self.assertEqual(before, world.resources("ERI"))
        world = ForceWorld()
        world.erie("the_price_of_victory")
        world.idea_actions.clear()
        world.daily()
        self.assertNotIn(("ERI", "HSM_ERI_FORCE_war_obligations"), world.idea_actions)

    def test_both_full_routes_reach_finale_without_avian_assent(self):
        for policy, war_before_root in itertools.product((0, 1), (False, True)):
            with self.subTest(policy=policy, war_before_root=war_before_root):
                world = ForceWorld()
                country = world.countries["ERI"]
                country.focuses.add("HSM_ERI_cost_of_feud")
                if war_before_root:
                    world.declare("ERI", "EYR")
                complete = lambda suffix: world.complete_force("HSM_ERI_FORCE_" + suffix, "ERI")
                for suffix in ("the_price_of_victory", "promises_in_writing", "not_a_dowry", "final_ultimatum"):
                    complete(suffix)
                self.assertEqual(len(world.goal_actions), 0 if war_before_root else 1)
                if not war_before_root:
                    world.declare("ERI", "EYR")
                world.capitulate("EYR", "ERI")
                world.peace("ERI", "EYR")
                world.advance_days(30)
                complete("terms_for_the_defeated")
                world.choose("hsm_ver_eri_force.4", policy, "ERI")
                complete("district_charters" if policy == 0 else "ducal_commissioners")
                complete("the_first_petition")
                world.choose("hsm_ver_eri_force.5", 1, "ERI")
                world.advance_days(45)
                world.daily()
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_eri_force.6", "ERI"))
                complete("reconstruction_contracts")
                complete("a_regular_levy")
                bonuses = len(country.bonuses)
                complete("the_third_house")
                self.assertEqual(len(country.bonuses), bonuses + 1)
                bonus = Node("bonus", "=", country.bonuses[-1])
                self.assertEqual((bonus.get("bonus"), bonus.get("uses"), bonus.get("category")), ("1.0", "1", "electronics"))
                world.daily()
                world.advance_days(1)
                self.assertNotIn("hsm_ver_force.4", country.events)
                self.assertNotIn("hsm_ver_force.1", world.countries["AVI"].events)
                complete("a_bound_duke" if policy == 0 else "a_single_chancery")
                complete("inheritance_without_feud")
                self.assertIn("HSM_ERI_FORCE_inheritance_without_feud", country.focuses)
                self.assertFalse(world.countries["AVI"].naps)
                self.assertEqual(world.countries["AVI"].leader, REG["KATRINA"])

    def test_terms_and_estate_choices_are_mutually_exclusive_and_replay_safe(self):
        for policy, claim in itertools.product((0, 1), repeat=2):
            with self.subTest(policy=policy, claim=claim):
                world = ForceWorld()
                world.erie_settlement(policy, claim)
                country = world.countries["ERI"]
                before = world.resources("ERI")
                world.choose("hsm_ver_eri_force.4", 1 - policy, "ERI")
                world.choose("hsm_ver_eri_force.5", 1 - claim, "ERI")
                self.assertEqual("HSM_ERI_FORCE_rights" in country.flags, policy == 0)
                self.assertEqual("HSM_ERI_FORCE_central" in country.flags, policy == 1)
                self.assertEqual("HSM_ERI_FORCE_court_upheld" in country.flags, claim == 0)
                self.assertEqual("HSM_ERI_FORCE_patron_award" in country.flags, claim == 1)
                self.assertEqual(before, world.resources("ERI"))

    def test_stale_terms_and_petition_never_bind_an_invalid_settlement(self):
        for event, reason in itertools.product((4, 5), ("bilateral_war", "government", "territory", "foreign_puppet")):
            with self.subTest(event=event, reason=reason):
                world = ForceWorld()
                world.erie("the_price_of_victory")
                world.victory("ERI", subject=True)
                world.erie("terms_for_the_defeated")
                if event == 5:
                    world.choose("hsm_ver_eri_force.4", 0, "ERI")
                    world.erie("the_first_petition")
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_eri_force." + str(event), "ERI"))
                if reason == "bilateral_war":
                    world.countries["EYR"].subject = False
                    world.countries["EYR"].overlord = ""
                    world.declare("EYR", "ERI")
                elif reason == "government":
                    world.countries["ERI"].leader = "replacement"
                elif reason == "territory":
                    world.state_ids["391"].controller = "GRI"
                else:
                    world.countries["EYR"].overlord = "GRI"
                before = world.resources("ERI")
                for option in (0, 1):
                    world.choose("hsm_ver_eri_force." + str(event), option, "ERI")
                flag = "HSM_ERI_FORCE_terms_decided" if event == 4 else "HSM_ERI_FORCE_claim_decided"
                self.assertNotIn(flag, world.countries["ERI"].flags)
                self.assertEqual(before, world.resources("ERI"))

    def test_dropped_or_occupation_interrupted_terms_retry_without_focus_replay(self):
        for interrupt in (False, True):
            world = ForceWorld()
            world.erie("the_price_of_victory")
            world.victory()
            world.erie("terms_for_the_defeated")
            country = world.countries["ERI"]
            resources = world.resources("ERI")
            world.advance_days(1)
            if interrupt:
                country.capitulated = True
                self.assertFalse(world.deliver("hsm_ver_eri_force.4", "ERI"))
            else:
                self.assertTrue(world.deliver("hsm_ver_eri_force.4", "ERI"))
            world.daily()
            self.assertEqual(country.events.count("hsm_ver_eri_force.4"), 1)
            world.advance_days(29)
            country.capitulated = False
            world.daily()
            self.assertEqual(country.events.count("hsm_ver_eri_force.4"), 2)
            world.advance_days(1)
            self.assertTrue(world.deliver("hsm_ver_eri_force.4", "ERI"))
            world.choose("hsm_ver_eri_force.4", 0, "ERI")
            world.advance_days(40)
            world.daily()
            self.assertEqual(country.events.count("hsm_ver_eri_force.4"), 2)
            self.assertEqual(resources, world.resources("ERI"))

    def test_prewar_scenes_retry_after_treaty_interrupt_without_duplicate_research(self):
        world = ForceWorld()
        for suffix in ("the_price_of_victory", "promises_in_writing", "not_a_dowry"):
            world.erie(suffix)
        resources = world.resources("ERI")
        for tag in HOUSES:
            world.countries[tag].flags.add("HSM_VER_treaty_signed")
        world.advance_days(1)
        for event in (1, 2, 3):
            self.assertFalse(world.deliver("hsm_ver_eri_force." + str(event), "ERI"))
        world.advance_days(30)
        world.daily()
        for tag in HOUSES:
            world.countries[tag].flags.remove("HSM_VER_treaty_signed")
        world.daily()
        world.advance_days(1)
        for event in (1, 2, 3):
            self.assertTrue(world.deliver("hsm_ver_eri_force." + str(event), "ERI"))
        world.advance_days(35)
        world.daily()
        for event in (1, 2, 3):
            self.assertEqual(world.countries["ERI"].events.count("hsm_ver_eri_force." + str(event)), 2)
        self.assertEqual(resources, world.resources("ERI"))

    def test_consequence_wait_is_exact_and_dropped_scene_recovers(self):
        world = ForceWorld()
        world.erie_settlement(0, 1)
        country = world.countries["ERI"]
        world.advance_days(44)
        world.daily()
        self.assertNotIn("hsm_ver_eri_force.6", country.events)
        world.advance_days(1)
        world.daily()
        self.assertEqual(country.events.count("hsm_ver_eri_force.6"), 1)
        country.capitulated = True
        world.advance_days(1)
        self.assertFalse(world.deliver("hsm_ver_eri_force.6", "ERI"))
        world.advance_days(29)
        country.capitulated = False
        world.daily()
        world.advance_days(1)
        self.assertTrue(world.deliver("hsm_ver_eri_force.6", "ERI"))
        self.assertIn("HSM_ERI_FORCE_consequence_seen", country.flags)
        world.advance_days(45)
        world.daily()
        self.assertEqual(country.events.count("hsm_ver_eri_force.6"), 2)

    def test_settlement_ideas_pause_and_return_without_reissuing_rewards(self):
        for policy, reason in itertools.product((0, 1), ("capitulation", "government", "territory", "subject")):
            with self.subTest(policy=policy, reason=reason):
                world = ForceWorld()
                world.erie_settlement(policy, 0)
                world.erie("reconstruction_contracts")
                country = world.countries["ERI"]
                ideas = {idea for idea in country.ideas if idea.startswith("HSM_ERI_FORCE_")}
                self.assertTrue(ideas)
                resources = world.resources("ERI")
                flags = set(country.flags)
                if reason == "capitulation":
                    country.capitulated = True
                elif reason == "government":
                    country.leader = "replacement"
                elif reason == "territory":
                    world.state_ids["673"].controller = "GRI"
                else:
                    country.subject = True
                world.daily()
                self.assertFalse({idea for idea in country.ideas if idea.startswith("HSM_ERI_FORCE_")})
                world.end_wars()
                country.leader = DUKE["ERI"]
                country.subject = False
                country.capitulated = False
                world.state_ids["673"].controller = "ERI"
                for _ in range(3):
                    world.daily()
                self.assertEqual(ideas, {idea for idea in country.ideas if idea.startswith("HSM_ERI_FORCE_")})
                self.assertTrue(flags <= country.flags)
                self.assertEqual(resources, world.resources("ERI"))

    def test_levy_grants_actual_army_experience_and_two_infantry_bonuses(self):
        world = ForceWorld()
        world.erie_settlement(0, 0)
        before = world.countries["ERI"].army_experience
        world.erie("a_regular_levy")
        self.assertEqual(world.countries["ERI"].army_experience - before, 25)
        bonus = Node("bonus", "=", world.countries["ERI"].bonuses[-1])
        self.assertEqual((bonus.get("category"), bonus.get("uses"), float(bonus.get("bonus"))), ("infantry_weapons", "2", 1.0))

    def test_bound_duke_reverses_patron_award_and_has_one_matching_scene(self):
        for policy, claim in itertools.product((0, 1), repeat=2):
            world = ForceWorld()
            world.erie_settlement(policy, claim)
            world.advance_days(45)
            world.daily()
            world.advance_days(1)
            self.assertTrue(world.deliver("hsm_ver_eri_force.6", "ERI"))
            suffix = "a_bound_duke" if policy == 0 else "a_single_chancery"
            self.assertTrue(world.available_force("HSM_ERI_FORCE_" + suffix, "ERI"))
            world.erie(suffix)
            country = world.countries["ERI"]
            if policy == 0:
                self.assertNotIn("HSM_ERI_FORCE_patron_award", country.flags)
                self.assertNotIn("HSM_ERI_FORCE_patron_claims", country.ideas)
                self.assertIn("HSM_ERI_FORCE_equal_judgement", country.ideas)
                self.assertEqual("HSM_ERI_FORCE_reversed_award" in country.flags, claim == 1)
            world.root = "ERI"
            descriptions = [n.get("text") for n in world.events["hsm_ver_eri_force.7"].all("desc")
                            if world.check(n.get("trigger", []), "ERI")]
            self.assertEqual(len(descriptions), 1)


class EyrieSettlement(unittest.TestCase):
    def test_two_routes_reach_finale_without_compelling_avian(self):
        for policy, subject in itertools.product((0, 1), (False, True)):
            with self.subTest(policy=policy, subject=subject):
                world = ForceWorld()
                country = world.countries["EYR"]
                country.focuses.add("HSM_EYR_the_price_of_vigilance")
                complete = lambda suffix: world.complete_force("HSM_EYR_FORCE_" + suffix, "EYR")
                for suffix in ("the_last_campaign", "break_the_rival_line", "field_liaison", "supply_the_columns"):
                    complete(suffix)
                world.declare("EYR", "ERI")
                world.capitulate("ERI", "EYR")
                world.peace("EYR", "ERI", subject)
                world.advance_days(30)
                complete("victory_and_the_garrison")
                world.choose("hsm_ver_eyr_force.2", policy, "EYR")
                complete("montagues_unsent_reply")
                world.choose("hsm_ver_eyr_force.3", policy, "EYR")
                complete("publish_release_schedule" if policy == 0 else "district_commands")
                complete("workshops_after_war")
                world.advance_days(120)
                world.daily()
                world.choose("hsm_ver_eyr_force.4", 0 if policy == 0 else 3, "EYR")
                complete("useful_trades" if policy == 0 else "permanent_district_staff")
                world.countries["AVI"].subject = True
                bonuses = len(country.bonuses)
                complete("avians_border")
                self.assertEqual(len(country.bonuses), bonuses + 1)
                bonus = Node("bonus", "=", country.bonuses[-1])
                self.assertEqual((bonus.get("bonus"), bonus.get("uses"), bonus.get("category")), ("1.0", "1", "electronics"))
                self.assertNotIn("hsm_ver_force.4", country.events)
                self.assertNotIn("hsm_ver_force.1", world.countries["AVI"].events)
                complete("inspections_not_parades")
                world.advance_days(29)
                world.daily()
                self.assertFalse(world.available_force("HSM_EYR_FORCE_road_that_stays_open", "EYR"))
                world.advance_days(1)
                world.daily()
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_eyr_force.5", "EYR"))
                world.choose("hsm_ver_eyr_force.5", 0, "EYR")
                complete("road_that_stays_open")
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_eyr_force.6", "EYR"))
                world.choose("hsm_ver_eyr_force.6", 0, "EYR")
                self.assertIn("HSM_EYR_FORCE_ending_seen", country.flags)
                self.assertFalse(world.countries["AVI"].naps)

    def test_order_and_correspondence_are_independent_once_only_choices(self):
        for policy, post in itertools.product((0, 1), repeat=2):
            world = ForceWorld()
            world.eyrie_settlement(policy, post)
            country = world.countries["EYR"]
            world.choose("hsm_ver_eyr_force.2", 1 - policy, "EYR")
            world.choose("hsm_ver_eyr_force.3", 1 - post, "EYR")
            self.assertEqual("HSM_EYR_FORCE_civilian_order" in country.flags, policy == 0)
            self.assertEqual("HSM_EYR_FORCE_military_order" in country.flags, policy == 1)
            self.assertEqual("HSM_EYR_FORCE_private_post" in country.flags, post == 0)
            self.assertEqual("HSM_EYR_FORCE_countersigned_post" in country.flags, post == 1)
            self.assertEqual(len([i for i in country.ideas if i.startswith("HSM_EYR_FORCE_")]), 2)

    def test_workshop_wait_is_120_days_and_each_option_charges_or_rewards_once(self):
        for policy, option in ((0, 0), (0, 1), (1, 2), (1, 3)):
            with self.subTest(policy=policy, option=option):
                world = ForceWorld()
                world.eyrie_settlement(policy)
                world.eyrie("workshops_after_war")
                country = world.countries["EYR"]
                before = world.resources("EYR")
                world.advance_days(119)
                world.daily()
                self.assertNotIn("hsm_ver_eyr_force.4", country.events)
                world.choose("hsm_ver_eyr_force.4", option, "EYR")
                self.assertEqual(before, world.resources("EYR"))
                world.advance_days(1)
                world.daily()
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_eyr_force.4", "EYR"))
                world.choose("hsm_ver_eyr_force.4", option, "EYR")
                self.assertEqual(country.political_power - before[0], -75 if option in (0, 3) else 0)
                after = world.resources("EYR")
                for other in range(4):
                    world.choose("hsm_ver_eyr_force.4", other, "EYR")
                world.advance_days(150)
                world.daily()
                self.assertEqual(after, world.resources("EYR"))
                self.assertEqual(country.events.count("hsm_ver_eyr_force.4"), 1)
                self.assertIn("HSM_EYR_FORCE_workshops_decided", country.flags)

    def test_stale_workshop_choices_cannot_charge_or_build(self):
        for option, invalid in itertools.product(range(4), ("bilateral_war", "government", "territory", "pending_expired")):
            with self.subTest(option=option, invalid=invalid):
                world = ForceWorld()
                world.eyrie_settlement(0 if option < 2 else 1, subject=True)
                world.eyrie("workshops_after_war")
                world.advance_days(120)
                world.daily()
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_eyr_force.4", "EYR"))
                if invalid == "bilateral_war":
                    world.countries["ERI"].subject = False
                    world.countries["ERI"].overlord = ""
                    world.declare("ERI", "EYR")
                elif invalid == "government":
                    world.countries["EYR"].leader = "replacement"
                elif invalid == "territory":
                    world.state_ids["500"].controller = "GRI"
                else:
                    world.advance_days(30)
                before = world.resources("EYR")
                world.choose("hsm_ver_eyr_force.4", option, "EYR")
                self.assertEqual(before, world.resources("EYR"))
                self.assertNotIn("HSM_EYR_FORCE_workshops_decided", world.countries["EYR"].flags)

    def test_workshop_factory_stays_in_owned_full_control_land_or_falls_back(self):
        for military, capacity in itertools.product((False, True), (0, 20)):
            with self.subTest(military=military, capacity=capacity):
                world = ForceWorld()
                world.eyrie_settlement(int(military), subject=True)
                for state in world.states:
                    if state.owner == "EYR":
                        state.capacity = capacity
                occupied = State(owner="EYR", controller="EYR", capacity=20)
                occupied.fully_controlled = False
                world.states.append(occupied)
                before = [copy.deepcopy(s.buildings) for s in world.states]
                bonus_count = len(world.countries["EYR"].bonuses)
                world.root = "EYR"
                world.apply("HSM_VER_EYR_FORCE_" + ("military_workshop" if military else "civilian_workshop"), "EYR")
                changed = [s for s, old in zip(world.states, before) if s.buildings != old]
                self.assertEqual(len(changed), 1 if capacity else 0)
                self.assertTrue(all(s.owner == "EYR" and s.controller == "EYR" and s.fully_controlled for s in changed))
                self.assertEqual(len(world.countries["EYR"].bonuses) - bonus_count, 0 if capacity else 1)
                if not capacity:
                    bonus = Node("bonus", "=", world.countries["EYR"].bonuses[-1])
                    self.assertEqual(bonus.get("category"), "support_tech" if military else "industry")

    def test_interrupted_scenes_recover_without_focus_reward_repetition(self):
        for event in (2, 3, 4, 5):
            with self.subTest(event=event):
                world = ForceWorld()
                world.eyrie("the_last_campaign")
                world.victory("EYR")
                world.eyrie("victory_and_the_garrison")
                if event >= 3:
                    world.choose("hsm_ver_eyr_force.2", 0, "EYR")
                    world.eyrie("montagues_unsent_reply")
                if event >= 4:
                    world.choose("hsm_ver_eyr_force.3", 0, "EYR")
                    world.eyrie("workshops_after_war")
                    world.advance_days(120)
                    world.daily()
                if event >= 5:
                    world.choose("hsm_ver_eyr_force.4", 0, "EYR")
                    world.eyrie("inspections_not_parades")
                    world.advance_days(30)
                    world.daily()
                event_id = "hsm_ver_eyr_force." + str(event)
                country = world.countries["EYR"]
                country.capitulated = True
                world.advance_days(1)
                self.assertFalse(world.deliver(event_id, "EYR"))
                resources = world.resources("EYR")
                world.advance_days(29)
                world.daily()
                self.assertEqual(country.events.count(event_id), 1)
                country.capitulated = False
                world.daily()
                world.advance_days(1)
                self.assertTrue(world.deliver(event_id, "EYR"))
                self.assertEqual(country.events.count(event_id), 2)
                self.assertEqual(resources, world.resources("EYR"))

    def test_ideas_pause_restore_and_do_not_rebuild_or_charge_on_daily_refresh(self):
        for policy, option in ((0, 0), (0, 1), (1, 2), (1, 3)):
            world = ForceWorld()
            world.eyrie_settlement(policy, 1, option)
            country = world.countries["EYR"]
            ideas = {i for i in country.ideas if i.startswith("HSM_EYR_FORCE_")}
            resources = world.resources("EYR")
            world.countries["EYR"].leader = "replacement"
            world.daily()
            self.assertFalse({i for i in country.ideas if i.startswith("HSM_EYR_FORCE_")})
            world.countries["EYR"].leader = DUKE["EYR"]
            world.idea_actions.clear()
            world.daily()
            self.assertEqual(ideas, {i for i in country.ideas if i.startswith("HSM_EYR_FORCE_")})
            world.idea_actions.clear()
            for _ in range(3):
                world.daily()
            self.assertEqual([i for tag, i in world.idea_actions if i.startswith("HSM_EYR_FORCE_")], [])
            self.assertEqual(resources, world.resources("EYR"))


class AvianUnification(unittest.TestCase):
    def test_native_avian_heartland_and_engine_pp_keyword(self):
        world = ForceWorld()
        self.assertEqual(world.state_ids["470"].owner, "AVI")
        self.assertEqual(world.state_ids["470"].cores, {"AVI"})
        documentation = (OPT.game / "documentation/triggers_documentation.md").read_text(encoding="utf-8-sig")
        self.assertIn("## has_political_power\n", documentation)
        world.countries["ERI"].political_power = 75
        self.assertTrue(world.check(parse("has_political_power > 74")))
        with self.assertRaises(AssertionError):
            world.check(parse("political_power > 74"))

    def test_conquest_uses_separate_root_in_fresh_and_completed_old_tree(self):
        for house, old, legacy_invitation in itertools.product(HOUSES, (False, True), (False, True)):
            world = ForceWorld()
            world.avian_frontier(house)
            prefix = "HSM_" + house + "_FORCE_"
            self.assertEqual(world.countries[house].focuses, {"HSM_" + house + "_avian_question"})
            if legacy_invitation:
                world.countries[house].focuses.add(LEGACY_AVIAN_FOCUS[house])
            if old:
                third = "the_third_house" if house == "ERI" else "avians_border"
                finale = "inheritance_without_feud" if house == "ERI" else "road_that_stays_open"
                world.countries[house].focuses.update({prefix + third, prefix + finale})
                world.countries[house].flags.add("HSM_VER_FORCE_avian_resolved")
                world.nap(house, "AVI")
                self.assertFalse(world.available_force(prefix + "avian_claim", house))
                world.nap(house, "AVI", False)  # The player's ordinary diplomacy, not a mod effect.
            world.complete_force(prefix + "avian_claim", house)
            self.assertEqual(world.goal_actions, [(house, ("annex_everything", "AVI"))])
            self.assertFalse(world.countries[house].war)
            self.assertFalse(world.countries["AVI"].subject)

    def test_active_association_completion_still_excludes_conquest(self):
        for house in HOUSES:
            with self.subTest(house=house):
                world = ForceWorld()
                world.avian_frontier(house)
                claim = "HSM_" + house + "_FORCE_avian_claim"
                self.assertTrue(world.available_force(claim, house))
                # A later Avian route change cannot undo the House's completed
                # association choice; old invitation history is tested separately.
                world.countries[house].focuses.add("HSM_" + house + "_avian_association")
                before = copy.deepcopy((world.countries, world.scheduled))
                with self.assertRaises(AssertionError):
                    world.complete_force(claim, house)
                self.assertEqual(before, (world.countries, world.scheduled))
                self.assertNotIn(claim, world.countries[house].focuses)
                self.assertFalse(world.goal_actions)

    def test_legacy_choice_requires_consent_and_never_unlocks_intergigantes_conquest(self):
        for house, choice in itertools.product(HOUSES, (0, 1)):
            world = ForceWorld()
            world.avian_frontier(house, avian_route="intergigantes")
            world.force("approach_avian", house)
            self.assertNotIn("hsm_ver_force.1", world.countries["AVI"].events)
            world.advance_days(1)
            self.assertTrue(world.deliver("hsm_ver_force.4", house))
            world.choose("hsm_ver_force.4", choice, house)
            world.choose("hsm_ver_force.4", 1 - choice, house)
            self.assertFalse(world.countries["AVI"].naps)
            self.assertEqual(world.countries["AVI"].events.count("hsm_ver_force.1"), 1 if choice == 0 else 0)
            self.assertFalse(world.force_test("can_claim_avian", house))
            world.force("claim_avian", house)
            self.assertFalse(world.goal_actions)

    def test_new_wargoal_rechecks_pacts_faction_subjects_and_engine_rules(self):
        locks = ("nap", "faction", "foreign_subject", "own_subject", "absent", "pending", "engine", "war", "capital", "ruler")
        for house, reason in itertools.product(HOUSES, locks):
            with self.subTest(house=house, reason=reason):
                world = ForceWorld()
                world.avian_frontier(house)
                country, avian = world.countries[house], world.countries["AVI"]
                self.assertTrue(world.force_test("can_claim_avian", house))
                if reason == "nap": world.nap(house, "AVI")
                elif reason == "faction": country.faction = avian.faction = "same"
                elif reason in ("foreign_subject", "own_subject"):
                    avian.subject = True
                    avian.overlord = house if reason == "own_subject" else "GRI"
                elif reason == "absent": avian.exists = False
                elif reason == "pending": country.flags.add("HSM_VER_FORCE_avian_pending")
                elif reason == "engine": country.blocked_declarations.add("AVI")
                elif reason == "war": world.declare("GRI", house)
                elif reason == "capital": world.state_ids["470"].owner = "GRI"
                else: country.leader = "replacement"
                before = copy.deepcopy((country.naps, country.faction, avian.overlord))
                world.force("claim_avian", house)
                self.assertFalse(world.goal_actions)
                self.assertEqual(before, (country.naps, country.faction, avian.overlord))

    def test_claim_requires_actual_neutral_route_and_rechecks_stale_completion(self):
        for house, authority, route in itertools.product(
            HOUSES, ("force", "charter", "union"), (None, "intergigantes", "both", "pursue_true_neutrality")
        ):
            with self.subTest(house=house, authority=authority, route=route):
                world = ForceWorld()
                world.avian_frontier(house, authority=authority)
                focus_id = "HSM_" + house + "_FORCE_avian_claim"
                self.assertTrue(world.available_force(focus_id, house))
                world.select_avian_route("intergigantes" if route == "both" else route)
                if route == "both":
                    world.countries["AVI"].focuses.add("pursue_true_neutrality")
                neutral = route == "pursue_true_neutrality"
                self.assertEqual(world.available_force(focus_id, house), neutral)
                self.assertFalse(world.check(world.focuses[focus_id].get("bypass"), house))
                if neutral:
                    world.complete_force(focus_id, house)
                    self.assertEqual(world.goal_actions, [(house, ("annex_everything", "AVI"))])
                else:
                    before = copy.deepcopy((world.countries, world.states, world.scheduled))
                    with self.assertRaises(AssertionError):
                        world.complete_force(focus_id, house)
                    # In-flight completion must recheck the route independently
                    # of the focus availability and mutual-exclusion metadata.
                    world.force("claim_avian", house)
                    self.assertEqual(before, (world.countries, world.states, world.scheduled))
                    self.assertFalse(world.goal_actions)
                self.assertFalse(world.countries[house].war)
                self.assertFalse(world.annexations)

    def test_claim_notifies_avian_under_every_regional_authority(self):
        for house, authority in itertools.product(HOUSES, ("force", "charter", "union")):
            with self.subTest(house=house, authority=authority):
                world = ForceWorld()
                world.avian_frontier(house, authority=authority)
                self.assertTrue(world.test("HSM_VER_AVR_regional_authority", house))
                if authority != "force":
                    self.assertFalse(world.force_test("settlement_active", house))
                    self.assertFalse(PROOF & world.countries[house].flags)
                world.complete_force("HSM_" + house + "_FORCE_avian_claim", house)
                self.assertEqual(world.goal_actions, [(house, ("annex_everything", "AVI"))])
                self.assertEqual(world.countries["AVI"].events.count("hsm_ver_force.10"), 1)
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_force.10", "AVI"))
                self.assertEqual(world.sender, house)
                self.assertFalse(world.countries[house].war)

    def test_claim_rechecks_lost_regional_authority(self):
        for house, authority in itertools.product(HOUSES, ("force", "charter", "union")):
            with self.subTest(house=house, authority=authority):
                world = ForceWorld()
                world.avian_frontier(house, authority=authority)
                self.assertTrue(world.force_test("can_claim_avian", house))
                if authority == "force":
                    world.countries[house].flags.remove("HSM_VER_FORCE_rival_defeated")
                elif authority == "charter":
                    world.countries[RIVAL[house]].flags.add("HSM_VER_charter_suspended")
                else:
                    world.state_ids["500"].controller = "GRI"
                self.assertFalse(world.test("HSM_VER_AVR_regional_authority", house))
                self.assertFalse(world.available_force("HSM_" + house + "_FORCE_avian_claim", house))
                before = copy.deepcopy((world.countries, world.states, world.scheduled))
                world.force("claim_avian", house)
                self.assertEqual(before, (world.countries, world.states, world.scheduled))
                self.assertFalse(world.goal_actions)

    def test_legacy_approach_requires_intergigantes_not_common_proclamation(self):
        for house, route in itertools.product(HOUSES, (None, "intergigantes", "pursue_true_neutrality")):
            with self.subTest(house=house, route=route):
                world = ForceWorld()
                world.avian_frontier(house, avian_route=route)
                world.force("approach_avian", house)
                self.assertEqual(world.countries[house].events.count("hsm_ver_force.4"), int(route == "intergigantes"))
                self.assertNotIn("hsm_ver_force.1", world.countries["AVI"].events)
                self.assertFalse(world.countries["AVI"].naps)
                self.assertFalse(world.goal_actions)

    def test_civil_register_focus_and_daily_refresh_never_start_legacy_diplomacy(self):
        for house, route, sought in itertools.product(
            HOUSES, (None, "intergigantes", "pursue_true_neutrality"), (False, True)
        ):
            with self.subTest(house=house, route=route, sought=sought):
                world = ForceWorld()
                world.avian_frontier(house, avian_route=route)
                country = world.countries[house]
                prefix = "HSM_" + house + "_FORCE_"
                parents = ("reconstruction_contracts", "a_regular_levy") if house == "ERI" else ("useful_trades",)
                country.focuses.update(prefix + suffix for suffix in parents)
                country.flags.add("HSM_VER_FORCE_campaign")
                if sought:
                    country.flags.add("HSM_VER_FORCE_avian_sought")
                register = "the_third_house" if house == "ERI" else "avians_border"
                before = len(country.bonuses)
                world.complete_force(prefix + register, house)
                self.assertEqual(len(country.bonuses), before + 1)
                bonus = Node("bonus", "=", country.bonuses[-1])
                self.assertEqual((bonus.get("bonus"), bonus.get("uses"), bonus.get("category")), ("1.0", "1", "electronics"))
                for days in (1, 45, 100):
                    world.advance_days(days)
                    world.daily()
                    self.assertNotIn("hsm_ver_force.4", country.events)
                    self.assertNotIn("hsm_ver_force.1", world.countries["AVI"].events)
                    self.assertNotIn("HSM_VER_FORCE_avian_choice_pending", country.flags)
                    self.assertNotIn("HSM_VER_FORCE_avian_pending", country.flags)
                    self.assertEqual(len(country.bonuses), before + 1)
                self.assertFalse(world.countries["AVI"].naps)
                self.assertFalse(world.goal_actions)

    def test_wars_without_regional_authority_do_not_create_avian_proof(self):
        for house in HOUSES:
            world = ForceWorld()
            world.select_avian_route("pursue_true_neutrality")
            # Removing the state also proves that the early route gate runs first.
            del world.state_ids["470"]
            world.declare(house, "AVI")
            world.daily()
            world.capitulate("AVI", house)
            self.assertFalse(AVIAN_PROOF & world.countries[house].flags)

    def test_actual_war_both_hook_directions_and_in_progress_save_recovery(self):
        for house, mode, authority in itertools.product(HOUSES, ("attack", "defend", "loaded"), ("force", "charter", "union")):
            world = ForceWorld()
            world.avian_frontier(house, authority=authority)
            if mode == "loaded":
                world.join_defence("AVI", house)
                world.daily()
            else:
                world.declare(house if mode == "attack" else "AVI", "AVI" if mode == "attack" else house)
            self.assertIn("HSM_VER_FORCE_AVI_war", world.countries[house].flags)
            world.capitulate("AVI", house)
            world.avian_peace(house)
            self.assertFalse(world.force_test("avian_victory", house))
            world.advance_days(29)
            self.assertFalse(world.force_test("avian_victory", house))
            world.advance_days(1)
            self.assertTrue(world.force_test("avian_victory", house))

    def test_no_victory_from_white_peace_occupation_gift_or_foreign_side(self):
        for house, reason in itertools.product(HOUSES, ("gift", "white_peace", "foreign_side", "occupation", "winner_bypass", "loser_bypass", "uncapitulation")):
            with self.subTest(house=house, reason=reason):
                world = ForceWorld()
                world.avian_frontier(house)
                if reason != "gift":
                    world.declare(house, "AVI")
                    if reason != "white_peace": world.capitulate("AVI", "GRI" if reason == "foreign_side" else house)
                if reason == "uncapitulation": world.hook("on_uncapitulation", "AVI", house)
                if reason.endswith("bypass"):
                    world.countries[house if reason == "winner_bypass" else "AVI"].flags.add("bypass_on_peaceconference_ended")
                if reason == "occupation":
                    world.state_ids["470"].controller = house
                else:
                    world.avian_peace(house)
                world.advance_days(30)
                world.daily()
                self.assertFalse(world.force_test("avian_victory", house))
                self.assertFalse(world.available_force("HSM_" + house + "_FORCE_avian_articles", house))

    def test_postwar_ownership_and_provenance_cannot_be_borrowed(self):
        for house, reason in itertools.product(HOUSES, ("foreign_owner", "foreign_controller", "partial_control", "foreign_subject", "unrelated_subject", "missing_war", "missing_defeat", "missing_peace")):
            world = ForceWorld()
            world.avian_frontier(house)
            world.avian_victory(house, True)
            state = world.state_ids["470"]
            if reason == "foreign_owner": state.owner = "GRI"
            elif reason == "foreign_controller": state.controller = "GRI"
            elif reason == "partial_control": state.fully_controlled = False
            elif reason == "foreign_subject": world.countries["AVI"].overlord = "GRI"
            elif reason == "unrelated_subject":
                world.countries["AVI"].exists = False
                world.countries["CYA"].subject = True
                world.countries["CYA"].overlord = house
                state.owner = state.controller = "CYA"
            else:
                flag = {"missing_war": "war", "missing_defeat": "defeated", "missing_peace": "peace"}[reason]
                world.countries[house].flags.remove("HSM_VER_FORCE_AVI_" + flag)
            self.assertFalse(world.force_test("avian_victory", house))
            world.force("open_avian_terms", house)
            self.assertEqual(world.countries[house].political_power, 200)

    def test_complete_annexed_routes_core_only_avian_and_build_once(self):
        for house, policy, authority in itertools.product(HOUSES, (0, 1), ("force", "charter", "union")):
            world = ForceWorld()
            world.avian_terms(house, False, policy, authority=authority)
            prefix = "HSM_" + house + "_FORCE_"
            country, state = world.countries[house], world.state_ids["470"]
            self.assertEqual(country.political_power, 125)
            self.assertTrue(world.test("HSM_VER_SP_has_HSM_VER_FORCE_AVI_transition", house))
            self.assertNotIn(house, state.cores)
            world.advance_days(89)
            self.assertFalse(world.available_force(prefix + "avian_integration", house))
            world.advance_days(1)
            world.complete_force(prefix + "avian_integration", house)
            self.assertIn(house, state.cores)
            self.assertEqual(state.buildings["industrial_complex"], 2)
            self.assertEqual([(s, t) for s, t in world.core_actions], [(state, house)])
            self.assertFalse(world.annexations)
            idea = "HSM_VER_FORCE_AVI_" + ("charter" if policy == 0 else "commission")
            self.assertTrue(world.test("HSM_VER_SP_has_" + idea, house))
            self.assertFalse(world.test("HSM_VER_SP_has_HSM_VER_FORCE_AVI_transition", house))
            before = world.resources(house)
            world.force("integrate_avian", house)
            world.force("open_avian_terms", house)
            world.daily()
            self.assertEqual(before, world.resources(house))
            self.assertEqual(len(world.core_actions), 1)

    def test_defeated_own_puppet_extra_holdings_require_consent_not_disposal(self):
        for house, direct_heartland in itertools.product(HOUSES, (False, True)):
            world = ForceWorld()
            world.avian_frontier(house)
            prefix = "HSM_" + house + "_FORCE_"
            world.complete_force(prefix + "avian_claim", house)
            world.avian_victory(house, True)
            extra = State(owner="AVI", controller="AVI", cores={"GRI"})
            extra.fully_controlled = True
            world.states.append(extra)
            if direct_heartland: world.state_ids["470"].owner = world.state_ids["470"].controller = house
            world.complete_force(prefix + "avian_articles", house)
            world.advance_days(1)
            self.assertTrue(world.deliver("hsm_ver_force.11", "AVI"))
            self.assertFalse(world.force_test("can_integrate_avian", house))
            world.choose("hsm_ver_force.11", 0, "AVI")
            self.assertTrue(world.countries["AVI"].exists)
            world.advance_days(90)
            world.complete_force(prefix + "avian_integration", house)
            self.assertEqual(world.annexations, [(house, "AVI")])
            self.assertFalse(world.countries["AVI"].exists)
            self.assertEqual(extra.owner, house)
            self.assertEqual(extra.cores, {"GRI"})
            self.assertIn(house, world.state_ids["470"].cores)
            self.assertIn("HSM_VER_FORCE_AVI_charter", world.countries[house].ideas)

    def test_ai_subject_accepts_guarantees_but_human_refusal_is_not_overridden(self):
        world = ForceWorld()
        options = world.events["hsm_ver_force.11"].all("option")
        self.assertEqual([Node("ai", "=", o.get("ai_chance")).get("factor") for o in options], ["100", "0"])
        for house in HOUSES:
            world = ForceWorld()
            world.avian_terms(house, True, 1)
            world.advance_days(200)
            world.daily()
            world.force("integrate_avian", house)
            self.assertFalse(world.annexations)
            self.assertTrue(world.countries["AVI"].subject)
            self.assertFalse(world.force_test("can_integrate_avian", house))
            self.assertEqual(world.countries["AVI"].events.count("hsm_ver_force.11"), 1)
            # Normal subject integration is an external engine action, never a mod fallback annex.
            world.run(parse("annex_country = { target = AVI transfer_troops = yes }"), house)
            world.daily()
            world.advance_days(1)
            self.assertTrue(world.deliver("hsm_ver_force.12", house))
            self.assertEqual(world.countries[house].political_power, 125)

    def test_stale_subject_response_and_final_reward_cannot_steal_a_puppet(self):
        reasons = ("foreign_overlord", "independent", "war", "occupied", "ruler", "expired", "wrong_sender")
        for house, reason in itertools.product(HOUSES, reasons):
            with self.subTest(house=house, reason=reason):
                world = ForceWorld()
                world.avian_frontier(house)
                world.avian_victory(house, True)
                world.force("open_avian_terms", house)
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_force.11", "AVI"))
                if reason == "foreign_overlord": world.countries["AVI"].overlord = "GRI"
                elif reason == "independent": world.countries["AVI"].subject = False
                elif reason == "war": world.declare("GRI", house)
                elif reason == "occupied": world.state_ids["470"].controller = "GRI"
                elif reason == "ruler": world.countries[house].leader = "replacement"
                elif reason == "expired": world.advance_days(45)
                else: world.sender = "GRI"
                world.choose("hsm_ver_force.11", 0, "AVI")
                self.assertNotIn("HSM_VER_FORCE_AVI_consent_" + house, world.countries["AVI"].flags)
                world.advance_days(100)
                world.force("integrate_avian", house)
                self.assertFalse(world.annexations)

    def test_final_reward_rechecks_consent_ownership_and_live_government(self):
        for house, reason in itertools.product(HOUSES, ("overlord", "consent", "controller", "partial", "war", "ruler", "subject")):
            world = ForceWorld()
            world.avian_terms(house, True)
            world.advance_days(90)
            self.assertTrue(world.force_test("can_integrate_avian", house))
            if reason == "overlord": world.countries["AVI"].overlord = "GRI"
            elif reason == "consent": world.countries["AVI"].flags.remove("HSM_VER_FORCE_AVI_consent_" + house)
            elif reason == "controller": world.state_ids["470"].controller = "GRI"
            elif reason == "partial": world.state_ids["470"].fully_controlled = False
            elif reason == "war": world.declare("GRI", house)
            elif reason == "ruler": world.countries[house].leader = "replacement"
            else: world.countries[house].subject = True
            before = world.resources(house)
            world.force("integrate_avian", house)
            self.assertFalse(world.annexations)
            self.assertFalse(world.core_actions)
            self.assertEqual(before, world.resources(house))

    def test_lost_event_delivery_recovers_without_recharging(self):
        for house, subject in itertools.product(HOUSES, (False, True)):
            world = ForceWorld()
            world.avian_frontier(house)
            world.avian_victory(house, subject)
            world.reward_force("HSM_" + house + "_FORCE_avian_articles", house)
            event, target = ("hsm_ver_force.11", "AVI") if subject else ("hsm_ver_force.12", house)
            world.countries[house].capitulated = True
            world.advance_days(1)
            self.assertFalse(world.deliver(event, target))
            world.advance_days(44)
            world.countries[house].capitulated = False
            world.daily()
            world.advance_days(1)
            self.assertTrue(world.deliver(event, target))
            world.choose(event, 0, target)
            self.assertEqual(world.countries[house].political_power, 125)
            self.assertEqual(world.countries[target].events.count(event), 2)
            self.assertLess(int(world.events[event].get("timeout_days")), 45)

    def test_terms_payment_boundary_and_idempotence(self):
        for house in HOUSES:
            world = ForceWorld()
            world.avian_frontier(house)
            world.avian_victory(house)
            world.countries[house].political_power = 74
            world.force("open_avian_terms", house)
            self.assertEqual(world.countries[house].political_power, 74)
            world.countries[house].political_power = 75
            world.force("open_avian_terms", house)
            world.force("open_avian_terms", house)
            self.assertEqual(world.countries[house].political_power, 0)
            self.assertEqual(world.countries[house].events.count("hsm_ver_force.12"), 1)

    def test_renewed_war_and_foreign_annexation_destroy_old_victory(self):
        for house, reason in itertools.product(HOUSES, ("renewed_war", "foreign_annex", "foreign_owner", "foreign_overlord", "overlord_with_direct_heartland")):
            world = ForceWorld()
            world.avian_terms(house, True)
            if reason == "renewed_war":
                world.countries["AVI"].subject = False
                world.declare("AVI", house)
            elif reason == "foreign_annex":
                world.hook("on_annex", "GRI", "AVI")
            elif reason == "foreign_owner":
                world.state_ids["470"].owner = "GRI"
                world.daily()
            else:
                if reason == "overlord_with_direct_heartland":
                    world.state_ids["470"].owner = world.state_ids["470"].controller = house
                world.countries["AVI"].overlord = "GRI"
                world.daily()
            self.assertNotIn("HSM_VER_FORCE_AVI_peace", world.countries[house].flags)
            self.assertNotIn("HSM_VER_FORCE_AVI_consent_" + house, world.countries["AVI"].flags)
            world.end_wars()
            world.countries["AVI"].subject = True
            world.countries["AVI"].overlord = house
            world.state_ids["470"].owner = world.state_ids["470"].controller = "AVI"
            world.advance_days(100)
            world.force("integrate_avian", house)
            self.assertFalse(world.annexations)

    def test_integration_benefits_pause_on_loss_and_restore_without_reward_farm(self):
        for house, policy in itertools.product(HOUSES, (0, 1)):
            world = ForceWorld()
            world.avian_terms(house, False, policy)
            world.advance_days(90)
            world.force("integrate_avian", house)
            country = world.countries[house]
            idea = "HSM_VER_FORCE_AVI_" + ("charter" if policy == 0 else "commission")
            before = world.resources(house)
            world.declare("GRI", house)
            world.daily()
            self.assertIn(idea, country.ideas)
            world.state_ids["470"].controller = "GRI"
            world.daily()
            self.assertNotIn(idea, country.ideas)
            world.state_ids["470"].controller = house
            world.daily()
            self.assertIn(idea, country.ideas)
            self.assertEqual(before, world.resources(house))

    def test_delayed_epilogue_has_one_policy_description_and_no_second_reward(self):
        for house, policy, authority in itertools.product(HOUSES, (0, 1), ("force", "charter", "union")):
            with self.subTest(house=house, policy=policy, authority=authority):
                world = ForceWorld()
                world.avian_terms(house, False, policy, authority=authority)
                world.advance_days(90)
                world.force("integrate_avian", house)
                self.assertTrue(world.test("HSM_VER_AVR_regional_authority", house))
                if authority != "force":
                    self.assertFalse(world.force_test("settlement_active", house))
                    self.assertFalse(PROOF & world.countries[house].flags)
                before = world.resources(house)
                world.advance_days(59)
                world.daily()
                self.assertNotIn("hsm_ver_force.14", world.countries[house].events)
                world.advance_days(1)
                world.daily()
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_force.14", house))
                descriptions = [n.get("text") for n in world.events["hsm_ver_force.14"].all("desc") if world.check(n.get("trigger"), house)]
                self.assertEqual(descriptions, ["hsm_ver_force.14.d_" + ("charter" if policy == 0 else "commission")])
                world.choose("hsm_ver_force.14", 0, house)
                world.daily()
                self.assertEqual(world.countries[house].events.count("hsm_ver_force.14"), 1)
                self.assertEqual(before, world.resources(house))


class ForceIntegration(unittest.TestCase):
    def test_avian_roots_are_imported_separately_from_military_story(self):
        world = ForceWorld()
        for house, filename, association in (
            ("ERI", "HSM_ERI.txt", "HSM_ERI_avian_association"),
            ("EYR", "HSM_VER_eyrie.txt", "HSM_EYR_avian_association"),
        ):
            root_id = "HSM_" + house + "_avian_question"
            root = world.focuses[root_id]
            self.assertFalse(root.all("prerequisite"))
            self.assertFalse(root.get("relative_position_id"))
            self.assertEqual((root.get("x"), root.get("y")), ("44", "0"))
            trees = [n for n in read(MOD / "common/national_focus" / filename) if n.key == "focus_tree"]
            self.assertTrue(any(root_id in {n.value for n in tree.all("shared_focus")} for tree in trees))
            claim_id = "HSM_" + house + "_FORCE_avian_claim"
            claim = world.focuses[claim_id]
            self.assertEqual(claim.all("prerequisite"), [Node("prerequisite", "=", [Node("focus", "=", root_id)])])
            self.assertEqual(claim.get("mutually_exclusive"), [Node("focus", "=", association)])
            self.assertIn(Node("focus", "=", claim_id), world.focuses[association].get("mutually_exclusive"))
            historical = world.focuses[LEGACY_AVIAN_FOCUS[house]]
            self.assertEqual(historical.get("allow_branch"), [Node("always", "=", "no")])
            self.assertEqual(historical.get("available"), [Node("always", "=", "no")])
            self.assertFalse(historical.all("mutually_exclusive"))
            self.assertEqual(historical.get("completion_reward"), [])

    def test_interrupted_completed_settlement_opening_is_recovered_by_daily_hook(self):
        for tag, root, opening in (
            ("ERI", "the_price_of_victory", "terms_for_the_defeated"),
            ("EYR", "the_last_campaign", "victory_and_the_garrison"),
        ):
            with self.subTest(tag=tag):
                world = ForceWorld()
                prefix = "HSM_" + tag + "_FORCE_"
                world.reward_force(prefix + root, tag)
                world.victory(tag)
                world.countries[tag].capitulated = True
                world.reward_force(prefix + opening, tag)
                self.assertNotIn("HSM_VER_FORCE_settlement_started", world.countries[tag].flags)
                resources = world.resources(tag)
                world.countries[tag].capitulated = False
                world.daily()
                self.assertTrue(world.force_test("settlement_active", tag))
                event = "hsm_ver_eri_force.4" if tag == "ERI" else "hsm_ver_eyr_force.2"
                self.assertEqual(world.countries[tag].events.count(event), 1)
                world.daily()
                self.assertEqual(world.resources(tag), resources)
                self.assertEqual(world.countries[tag].events.count(event), 1)

    def test_force_roots_follow_correct_story_and_have_separate_absolute_layout(self):
        for tag, filename, root, parent in (
            ("ERI", "HSM_VER_erie_force.txt", "the_price_of_victory", "HSM_ERI_cost_of_feud"),
            ("EYR", "HSM_VER_eyrie_force.txt", "the_last_campaign", "HSM_EYR_the_price_of_vigilance"),
        ):
            nodes = read(MOD / "common/national_focus" / filename)
            focuses = {n.get("id"): n for n in nodes if n.key == "shared_focus"}
            self.assertGreaterEqual(len(focuses), 12)
            prefix = "HSM_" + tag + "_FORCE_"
            self.assertEqual(focuses[prefix + root].get("prerequisite"), [Node("focus", "=", parent)])
            avian_branch = {prefix + suffix: (46, y) for suffix, y in
                           (("avian_claim", 1), ("avian_articles", 2), ("avian_integration", 3))}
            for key, focus in focuses.items():
                self.assertTrue(key.startswith(prefix))
                self.assertFalse(focus.get("relative_position_id"))
                if key in avian_branch:
                    self.assertEqual((int(focus.get("x")), int(focus.get("y"))), avian_branch[key])
                else:
                    self.assertIn(int(focus.get("x")), range(32, 39))
                self.assertGreaterEqual(int(focus.get("y")), 1)
                self.assertEqual(focus.get("cancel_if_invalid"), "yes")

    def test_territorial_effects_are_confined_to_guarded_avian_integration(self):
        forbidden = {"puppet", "set_autonomy", "transfer_state", "set_state_owner",
                     "add_state_core", "declare_war_on", "create_faction", "add_to_faction",
                     "recruit_character", "set_nationality", "promote_character", "add_country_leader_role"}
        files = list(MOD.rglob("HSM_VER*force.txt"))
        self.assertGreaterEqual(len(files), 8)
        for path in files:
            for n in walk(read(path)):
                self.assertNotIn(n.key, forbidden, f"{path}: {n.key}")
            for root in read(path):
                for n in walk([root]):
                    if n.key in ("annex_country", "add_core_of"):
                        self.assertEqual(root.key, "HSM_VER_FORCE_integrate_avian")
                        self.assertEqual(path.parent.name, "scripted_effects")
                        if n.key == "annex_country":
                            self.assertEqual(n.get("target"), "AVI")
                        else:
                            self.assertIn(n.value, HOUSES)


if __name__ == "__main__":
    unittest.main(argv=[__file__] + BASE["REST"])
