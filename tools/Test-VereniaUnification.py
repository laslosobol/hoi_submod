"""Execute the production UNI effects, focus rewards, event options and hooks.

Existing diplomatic/war history is fixture input. This strict, scoped interpreter
is not HOI4; unsupported operations fail. Run with the bundled Python and -B.
No existing harness or production file is modified by this suite.
"""
from __future__ import annotations

import copy
import itertools
import re
import runpy
import struct
import unittest
from pathlib import Path

FORCE = runpy.run_path(str(Path(__file__).with_name("Test-VereniaForce.py")))
REG = FORCE["REG"]
BASE = FORCE["BASE"]
Node, read, walk, MOD, OPT, State = (FORCE[k] for k in ("Node", "read", "walk", "MOD", "OPT", "State"))
HOUSES = ("ERI", "EYR", "AVI")
LAND = {"ERI": ("401", "500", "673"), "EYR": ("391", "400"), "AVI": ("470",)}
RIVAL = {"ERI": "EYR", "EYR": "ERI"}
FINAL = {"ERI": "HSM_VER_union_established", "EYR": "HSM_EYR_settlement_completed", "AVI": "HSM_AVI_settlement_completed"}
FORCE_FINAL = {"ERI": "HSM_ERI_FORCE_inheritance_without_feud", "EYR": "HSM_EYR_FORCE_road_that_stays_open"}
PREFIX = "HSM_VER_UNI_"
COSMETIC = "HSM_VER_UNIFIED"
STAGES = ("convention", "customs_union", "common_works", "common_administration", "unified_command", "constitutional_draft", "constitutional_act", "settled_institutions")
REWARDS = ("start_convention", "establish_customs", "build_common_works", "establish_administration", "establish_command", "open_ratification", "found_union", "settle_institutions")
GROVER = "GRI_emperor_grover_vi"
FILES = [MOD / folder / "HSM_VER_unification.txt" for folder in ("common/national_focus", "common/scripted_triggers", "common/scripted_effects", "events", "common/ideas", "common/on_actions")]


class UnionWorld(FORCE["ForceWorld"]):
    def __init__(self):
        super().__init__()
        self.focuses.update({
            n.get("id"): n
            for path in (MOD / "common/national_focus").glob("*.txt")
            for n in walk(read(path)) if n.key == "joint_focus" and n.children
        })
        self.all_hooks = self.hooks
        self.hooks = {}
        for container in read(MOD / "common/on_actions/HSM_VER_unification.txt"):
            for hook in container.children:
                self.hooks.setdefault(hook.key, []).extend(hook.get("effect", []))
        for country in self.countries.values():
            country.ai = True
            country.political_power = 500
            country.cosmetic = ""
        self.states = [self.state_ids[s] for ids in LAND.values() for s in ids]
        self.state_ids = {s: self.state_ids[s] for ids in LAND.values() for s in ids}
        self.scheduled = []

    def check(self, nodes, tag="ERI"):
        for n in nodes:
            if n.key == "any_subject_country":
                ok = any(c.exists and c.subject and c.overlord == tag
                         and self.scoped_check(n.children, target, tag)
                         for target, c in self.countries.items())
            elif n.key == "all_owned_state":
                ok = all(self.scoped_check(n.children, state, tag)
                         for state in self.states if state.owner == tag)
            else:
                ok = super().check([n], tag)
            if not ok:
                return False
        return True

    def run(self, nodes, tag="ERI"):
        # Delegate whole conditional chains to the existing strict interpreter.
        if any(n.key == "set_cosmetic_tag" for n in nodes):
            for n in nodes:
                if n.key == "set_cosmetic_tag":
                    self.countries[tag].cosmetic = n.value
                else:
                    super().run([n], tag)
        else:
            super().run(nodes, tag)

    def uni(self, effect, host):
        self.root = host
        self.apply(PREFIX + effect, host)

    def valid(self, trigger, host):
        self.root = host
        return self.test(PREFIX + trigger, host)

    def has(self, tag, flag):
        return PREFIX + flag in self.countries[tag].flags

    def prepare(self, host, *, military=False, subject=False, avian="member"):
        """Certified prior-route history; all UNI progression remains production code."""
        self.countries[host].ai = False
        if military:
            other = RIVAL[host]
            self.countries[host].flags.update(FORCE["PROOF"] | {"HSM_VER_FORCE_settlement_started"})
            self.countries[host].focuses.add(FORCE_FINAL[host])
            self.countries[other].exists = subject
            self.countries[other].subject = subject
            self.countries[other].overlord = host if subject else ""
            if not subject:
                for sid in LAND[other]:
                    self.state_ids[sid].owner = self.state_ids[sid].controller = host
        else:
            for tag in ("ERI", "EYR"):
                self.countries[tag].flags.update({"HSM_VER_treaty_signed", "HSM_VER_charter_signed"})
            for tag, flag in FINAL.items():
                self.countries[tag].flags.add(flag)
        avi = self.countries["AVI"]
        # The inherited Avian fixture starts on Intergigantes. Select one route,
        # not both mutually exclusive native focuses when modelling neutrality.
        avi.focuses.difference_update({"intergigantes", "pursue_true_neutrality"})
        if avian in ("member", "unsigned"):
            avi.focuses.add("intergigantes")
            if avian == "member":
                avi.flags.update({"HSM_VER_charter_signed", "HSM_VER_congress_observer"})
        elif avian == "neutral":
            avi.focuses.add("pursue_true_neutrality")
        elif avian == "absent":
            avi.exists = False
            self.state_ids["470"].owner = self.state_ids["470"].controller = "GRI"
        else:
            raise AssertionError(avian)
        return self

    def available(self, host, stage):
        self.root = host
        return self.check(self.focuses[PREFIX + stage].get("available", []), host)

    def reward(self, host, stage):
        self.root = host
        focus = self.focuses[PREFIX + stage]
        recipients = [host]
        if focus.key == "joint_focus":
            recipients += [tag for tag in HOUSES if tag != host
                           and self.check(focus.get("joint_trigger", []), tag)]
        for tag in recipients:
            self.countries[tag].focuses.add(PREFIX + stage)
        for tag in recipients:
            self.run(focus.get("completion_reward", []), tag)
        if focus.key == "joint_focus":
            self.run(focus.get("completion_reward_joint_originator", []), host)
            for tag in recipients:
                if tag != host:
                    self.run(focus.get("completion_reward_joint_member", []), tag)

    def complete(self, host, stage):
        focus = self.focuses[PREFIX + stage]
        completed = self.countries[host].focuses
        assert PREFIX + stage not in completed, stage
        assert all(any(n.value in completed for n in p.children) for p in focus.all("prerequisite")), stage
        assert self.available(host, stage), (host, stage)
        self.reward(host, stage)

    def event_id(self, host, final=False):
        return "hsm_ver_uni." + str((20 if final else 10) + HOUSES.index(host))

    def replies(self, host, *, final=False, responses=None):
        responses = responses or {}
        self.advance_days(1)
        kind = "vote" if final else "invite"
        for tag in HOUSES:
            if self.has(tag, kind + "_pending_" + host):
                assert self.deliver(self.event_id(host, final), tag)
                response = responses.get(tag, 1)
                if response is not None:
                    self.choose(self.event_id(host, final), response, tag)

    def begin(self, host, **kwargs):
        self.prepare(host, **kwargs)
        self.complete(host, "convention")
        self.replies(host)
        return self

    def draft(self, host):
        self.complete(host, "customs_union")
        self.complete(host, "common_works")
        self.advance_days(60)
        self.complete(host, "common_administration")
        self.advance_days(90)
        self.complete(host, "unified_command")
        self.complete(host, "constitutional_draft")

    def found(self, host):
        self.draft(host)
        self.replies(host, final=True)
        self.complete(host, "constitutional_act")

    def daily(self):
        for tag in HOUSES:
            if self.countries[tag].exists:
                self.root = tag
                self.run(self.hooks.get("on_daily_" + tag, []), tag)

    def resources(self):
        return copy.deepcopy((
            [(t, c.political_power, c.stability, c.manpower, c.army_experience, c.bonuses)
             for t, c in self.countries.items()],
            [(s, st.owner, st.controller, st.cores, st.extra_slots, st.buildings)
             for s, st in self.state_ids.items()], self.annexations, self.character_actions))

    def overseas(self, owner):
        state = State(owner=owner, controller=owner, cores={"GRI"})
        state.fully_controlled = True
        self.states.append(state)
        self.state_ids["9999"] = state
        return state


class Production(unittest.TestCase):
    def test_foundation_with_all_other_production_annex_hooks_enabled(self):
        for host in HOUSES:
            with self.subTest(host=host):
                w = UnionWorld().begin(host)
                w.hooks = w.all_hooks
                w.found(host)
                self.assertTrue(w.has(host, "founded"))
                self.assertEqual(set(w.annexations), {(host, t) for t in HOUSES if t != host})

    def test_existing_war_hooks_preserve_long_war_recovery(self):
        for host in HOUSES:
            with self.subTest(host=host):
                w = UnionWorld().begin(host)
                w.draft(host)
                w.replies(host, final=True)
                w.hooks = w.all_hooks
                w.war_between("GRI", host)
                w.advance_days(200)
                w.daily()
                self.assertTrue(w.has(host, "leader"))
                self.assertFalse(w.has(host, "closed"))
                w.end_wars()
                w.daily()
                w.replies(host, final=True)
                w.complete(host, "constitutional_act")
                self.assertTrue(w.has(host, "founded"))

    def test_three_presidents_and_both_reply_orders(self):
        for host in HOUSES:
            for order in itertools.permutations([t for t in HOUSES if t != host]):
                with self.subTest(host=host, order=order):
                    w = UnionWorld().begin(host)
                    leader = w.countries[host].leader
                    w.draft(host)
                    self.assertFalse(w.available(host, "constitutional_act"))
                    w.advance_days(1)
                    for tag in order:
                        self.assertTrue(w.deliver(w.event_id(host, True), tag))
                        w.choose(w.event_id(host, True), 1, tag)
                    w.complete(host, "constitutional_act")
                    self.assertTrue(w.has(host, "founded"))
                    self.assertEqual(w.countries[host].leader, leader)
                    self.assertEqual(w.countries[host].cosmetic, COSMETIC)
                    self.assertEqual([h for h in HOUSES if w.has(h, "leader")], [host])
                    for other in HOUSES:
                        self.assertEqual(w.has(host, "absorbed_" + other), other != host)
                        for sid in LAND[other]:
                            self.assertEqual(w.state_ids[sid].owner, host)
                            self.assertIn(host, w.state_ids[sid].cores)
                    self.assertIn("HSM_VER_SP_owned_" + PREFIX + "constitutional_state", w.countries[host].flags)
                    self.assertIn("HSM_VER_SP_united_verenia", w.countries[host].dynamic_modifiers)
                    self.assertNotIn(PREFIX + "constitutional_state", w.countries[host].ideas)
                    self.assertTrue(w.test("HSM_VER_UNI_ducal_land_held", host))
                    w.advance_days(59)
                    self.assertFalse(w.available(host, "settled_institutions"))
                    w.advance_days(1)
                    w.complete(host, "settled_institutions")
                    self.assertIn("HSM_VER_SP_owned_" + PREFIX + "settled_state", w.countries[host].flags)
                    self.assertNotIn("HSM_VER_SP_owned_" + PREFIX + "constitutional_state", w.countries[host].flags)

    def test_ducal_union_without_avian_membership(self):
        for host, avian in itertools.product(("ERI", "EYR"), ("neutral", "absent", "unsigned")):
            with self.subTest(host=host, avian=avian):
                w = UnionWorld().begin(host, avian=avian)
                w.found(host)
                self.assertFalse(w.has(host, "absorbed_AVI"))
                self.assertNotIn(host, w.state_ids["470"].cores)
                self.assertFalse(any(target == "AVI" for _, target in w.annexations))

    def test_avian_precursor_is_compatible_but_neutrality_never_is(self):
        w = UnionWorld().prepare("AVI")
        w.countries["AVI"].focuses.add("full_integration")
        self.assertTrue(w.available("AVI", "convention"))
        w.countries["AVI"].focuses.add("pursue_true_neutrality")
        self.assertFalse(w.available("AVI", "convention"))

    def test_exact_entry_final_flags_and_military_victory_proof(self):
        for host in HOUSES:
            w = UnionWorld().prepare(host)
            w.countries[host].flags.remove(FINAL[host])
            self.assertFalse(w.available(host, "convention"))
        for host in RIVAL:
            for missing in (*FORCE["PROOF"], "HSM_VER_FORCE_settlement_started", "focus"):
                with self.subTest(host=host, missing=missing):
                    w = UnionWorld().prepare(host, military=True, avian="absent")
                    if missing == "focus":
                        w.countries[host].focuses.remove(FORCE_FINAL[host])
                    else:
                        w.countries[host].flags.remove(missing)
                    self.assertFalse(w.available(host, "convention"))
                    w.uni("start_convention", host)
                    self.assertFalse(w.has(host, "leader"))

    def test_military_absent_or_own_subject_in_both_duchies(self):
        for host, subject in itertools.product(RIVAL, (False, True)):
            with self.subTest(host=host, subject=subject):
                w = UnionWorld().begin(host, military=True, subject=subject, avian="absent")
                other = RIVAL[host]
                self.assertEqual(w.has(other, "invited_" + host), subject)
                self.assertNotIn(host, w.state_ids[LAND[other][0]].cores)
                w.found(host)
                self.assertEqual(w.annexations, [(host, other)] if subject else [])
                self.assertTrue(w.has(host, "absorbed_" + other))
                for sid in LAND[other]:
                    self.assertIn(host, w.state_ids[sid].cores)

    def test_host_keeps_unrelated_own_subjects_and_their_faction(self):
        for host, military in itertools.product(RIVAL, (False, True)):
            with self.subTest(host=host, military=military):
                w = UnionWorld().prepare(host, military=military, subject=military, avian="neutral")
                # Avian and GRI remain existing subjects; neither is an annexation target.
                for tag in ("AVI", "GRI"):
                    w.countries[tag].subject = True
                    w.countries[tag].overlord = host
                for tag in HOUSES + ("GRI",):
                    w.countries[tag].faction = "VER"
                w.countries[host].faction_leader = True
                w.complete(host, "convention")
                w.replies(host)
                w.found(host)
                self.assertTrue(w.countries["AVI"].exists)
                self.assertTrue(w.countries["GRI"].exists)
                self.assertEqual(w.countries["AVI"].overlord, host)
                self.assertFalse(w.has(host, "absorbed_AVI"))

    def test_ai_cannot_take_uncommitted_human_campaign(self):
        for host, human in itertools.permutations(HOUSES, 2):
            w = UnionWorld().prepare(host)
            w.countries[host].ai = True
            w.countries[human].ai = False
            self.assertFalse(w.available(host, "convention"))
            w.countries[host].ai = False
            self.assertTrue(w.available(host, "convention"))
        for host in RIVAL:
            w = UnionWorld().prepare(host, military=True, subject=True, avian="absent")
            w.countries[host].ai = True
            w.countries[RIVAL[host]].ai = False
            self.assertFalse(w.available(host, "convention"))

    def test_ai_waits_for_human_avian_before_charter_membership(self):
        for host in RIVAL:
            for route in ("undecided", "intergigantes"):
                for occupied in (False, True):
                    with self.subTest(host=host, route=route, occupied=occupied):
                        w = UnionWorld().prepare(host, avian="unsigned")
                        w.countries[host].ai = True
                        avi = w.countries["AVI"]
                        avi.ai = False
                        if route == "undecided":
                            avi.focuses.discard("intergigantes")
                        if occupied:
                            avi.capitulated = True
                            w.state_ids["470"].controller = "GRI"
                        self.assertFalse(w.available(host, "convention"))
                        w.countries[host].ai = False
                        self.assertTrue(w.available(host, "convention"))

    def test_nonunion_human_avian_does_not_hold_up_ai_unification(self):
        for host in RIVAL:
            for exit_choice in ("pursue_true_neutrality", "the_second_winterfest_ball",
                                "communists_win", "fascists_win", "loyalists_win", "new_ruler"):
                with self.subTest(host=host, exit_choice=exit_choice):
                    w = UnionWorld().prepare(host, avian="unsigned")
                    w.countries[host].ai = True
                    avi = w.countries["AVI"]
                    avi.ai = False
                    if exit_choice == "new_ruler":
                        avi.leader = "AVI_nonconstitutional_ruler"
                    else:
                        avi.focuses.add(exit_choice)
                    self.assertTrue(w.available(host, "convention"))

    def test_single_presidency_even_with_multiple_completed_roots(self):
        for first in HOUSES:
            w = UnionWorld().prepare(first)
            for other in HOUSES:
                w.countries[other].ai = False
            w.reward(first, "convention")
            for other in HOUSES:
                w.reward(other, "convention")
            w.daily()
            self.assertEqual([h for h in HOUSES if w.has(h, "leader")], [first])

    def test_real_waits_and_political_costs(self):
        for host in HOUSES:
            w = UnionWorld().begin(host)
            w.complete(host, "customs_union")
            self.assertTrue(w.available(host, "common_administration"))
            w.complete(host, "common_works")
            w.countries[host].political_power = 99
            before = w.resources()
            w.uni("establish_administration", host)
            self.assertEqual(before, w.resources())
            w.countries[host].political_power = 100
            w.complete(host, "common_administration")
            self.assertEqual(w.countries[host].political_power, 0)
            w.countries[host].political_power = 50
            w.advance_days(89)
            self.assertFalse(w.available(host, "unified_command"))
            w.advance_days(1)
            w.complete(host, "unified_command")
            self.assertEqual(w.countries[host].political_power, 0)

    def test_human_participation_and_absorption_are_separate(self):
        for host in HOUSES:
            other = next(h for h in ("ERI", "EYR") if h != host)
            for military in ((False, True) if host != "AVI" else (False,)):
                w = UnionWorld().prepare(host, military=military, subject=military)
                w.countries[other].ai = False
                w.complete(host, "convention")
                w.replies(host)
                self.assertTrue(w.has(other, "member_" + host))
                self.assertFalse(w.has(other, "consent_" + host))
                w.draft(host)
                w.replies(host, final=True, responses={other: None})
                before = w.resources()
                w.uni("found_union", host)
                self.assertEqual(before, w.resources())
                # The real first/default option is refusal, also for a subject.
                w.choose(w.event_id(host, True), 0, other)
                self.assertTrue(w.countries[other].exists)
                self.assertTrue(w.has(host, "closed"))
                self.assertFalse(w.has(host, "leader"))
                self.assertFalse(w.has(other, "consent_" + host))
                self.assertFalse(w.has(other, "vote_pending_" + host))
                w.choose(w.event_id(host, True), 1, other)
                w.uni("found_union", host)
                self.assertFalse(w.annexations)

    def test_optional_avian_can_decline_either_stage(self):
        for host, final in itertools.product(RIVAL, (False, True)):
            w = UnionWorld().prepare(host)
            w.complete(host, "convention")
            w.replies(host, responses={"AVI": 1 if final else 0})
            w.draft(host)
            w.replies(host, final=True, responses={"AVI": 0})
            w.complete(host, "constitutional_act")
            self.assertTrue(w.has(host, "founded"))
            self.assertTrue(w.countries["AVI"].exists)
            self.assertFalse(w.has(host, "absorbed_AVI"))
            self.assertFalse(w.has("AVI", "member_" + host))

    def test_mandatory_invitation_refusal_and_timeout_are_terminal(self):
        for host, timeout in itertools.product(HOUSES, (False, True)):
            w = UnionWorld().prepare(host)
            other = next(h for h in ("ERI", "EYR") if h != host)
            w.complete(host, "convention")
            w.replies(host, responses={other: None if timeout else 0})
            if timeout:
                w.advance_days(45)
                w.daily()
            self.assertTrue(w.has(host, "closed"))
            count = len(w.scheduled)
            w.reward(host, "convention")
            w.daily()
            w.choose(w.event_id(host), 1, other)
            self.assertEqual(len(w.scheduled), count)
            self.assertFalse(w.has(other, "member_" + host))

    def test_annexation_only_cores_native_homeland(self):
        for host in HOUSES:
            w = UnionWorld().begin(host)
            other = next(t for t in HOUSES if t != host)
            overseas = w.overseas(other)
            w.found(host)
            self.assertEqual(overseas.owner, host)
            self.assertEqual(overseas.cores, {"GRI"})
            self.assertFalse(any(state is overseas for state, _ in w.core_actions))

    def test_invalid_territory_war_subject_faction_and_government_block_entry(self):
        mutations = {
            "war": lambda w, t: setattr(w.countries[t], "war", True),
            "subject": lambda w, t: setattr(w.countries[t], "subject", True),
            "capitulation": lambda w, t: setattr(w.countries[t], "capitulated", True),
            "lost_land": lambda w, t: setattr(w.state_ids[LAND[t][0]], "owner", "GRI"),
            "occupation": lambda w, t: setattr(w.state_ids[LAND[t][0]], "controller", "GRI"),
            "partial_occupation": lambda w, t: setattr(w.state_ids[LAND[t][0]], "fully_controlled", False),
            "leader": lambda w, t: setattr(w.countries[t], "leader", "foreign_regime"),
            "ideology": lambda w, t: setattr(w.countries[t], "government", "fascism"),
            "foreign_faction": lambda w, t: setattr(w.countries[t], "faction", "foreign"),
        }
        for host, (name, mutate) in itertools.product(HOUSES, mutations.items()):
            with self.subTest(host=host, invalid=name):
                w = UnionWorld().prepare(host)
                mutate(w, host)
                self.assertFalse(w.available(host, "convention"))
                w.uni("start_convention", host)
                self.assertFalse(w.has(host, "leader"))

    def test_final_guard_revalidates_even_an_already_open_human_event(self):
        for host, change in itertools.product(HOUSES, ("war", "foreign_subject", "territory", "dead_president")):
            with self.subTest(host=host, change=change):
                w = UnionWorld().begin(host)
                w.draft(host)
                other = next(t for t in ("ERI", "EYR") if t != host)
                w.replies(host, final=True, responses={other: None})
                if change == "war":
                    w.countries[other].war = True
                elif change == "foreign_subject":
                    w.countries[other].subject = True
                    w.countries[other].overlord = "GRI"
                elif change == "territory":
                    w.state_ids[LAND[other][0]].controller = "GRI"
                else:
                    w.countries[host].leader = "replacement"
                w.choose(w.event_id(host, True), 1, other)
                w.uni("found_union", host)
                self.assertFalse(w.annexations)
                self.assertFalse(w.has(other, "consent_" + host))
                w.daily()
                political_loss = change in ("foreign_subject", "dead_president")
                self.assertEqual(w.has(host, "closed"), political_loss)
                self.assertEqual(w.has(host, "leader"), not political_loss)
                self.assertEqual(w.has(host, "suspended"), not political_loss)

    def test_final_consents_void_on_war_then_peace(self):
        for host in HOUSES:
            w = UnionWorld().begin(host)
            w.draft(host)
            w.replies(host, final=True)
            w.countries[host].war = True
            w.hook("on_war_relation_added", host, "GRI")
            w.countries[host].war = False
            w.daily()
            w.uni("found_union", host)
            self.assertFalse(w.has(host, "closed"))
            self.assertTrue(w.has(host, "leader"))
            self.assertFalse(w.available(host, "constitutional_act"))
            for other in HOUSES:
                if other != host:
                    self.assertFalse(w.has(other, "consent_" + host))
            self.assertFalse(w.annexations)

    def test_military_cannot_absorb_foreign_subject_or_released_duke(self):
        for host, status in itertools.product(RIVAL, ("foreign", "free", "lost_state", "occupied", "children")):
            w = UnionWorld().begin(host, military=True, subject=True, avian="absent")
            w.draft(host)
            w.replies(host, final=True)
            other = RIVAL[host]
            if status == "foreign":
                w.countries[other].overlord = "GRI"
            elif status == "free":
                w.countries[other].subject = False
            elif status == "lost_state":
                w.state_ids[LAND[other][0]].owner = "GRI"
            elif status == "occupied":
                w.state_ids[LAND[other][0]].fully_controlled = False
            else:
                w.countries["GRI"].subject = True
                w.countries["GRI"].overlord = other
            w.uni("found_union", host)
            self.assertFalse(w.annexations)
            self.assertFalse(w.has(host, "founded"))

    def test_war_suspends_early_stages_and_recovers_without_duplicate_rewards(self):
        for host in HOUSES:
            w = UnionWorld().begin(host)
            w.complete(host, "customs_union")
            w.complete(host, "common_works")
            before = w.resources()
            w.countries[host].war = True
            w.daily()
            self.assertTrue(w.has(host, "suspended"))
            self.assertNotIn(PREFIX + "customs_spirit", w.countries[host].ideas)
            w.countries[host].war = False
            w.daily()
            self.assertFalse(w.has(host, "suspended"))
            self.assertIn(PREFIX + "customs_spirit", w.countries[host].ideas)
            self.assertEqual(before, w.resources())
            w.advance_days(60)
            w.complete(host, "common_administration")

    def test_political_dissolution_releases_lock_and_dead_host_is_swept(self):
        for host, cause in itertools.product(HOUSES, ("subjugated", "dead", "regime")):
            w = UnionWorld().begin(host)
            if cause == "subjugated":
                w.countries[host].subject = True
                w.countries[host].overlord = "GRI"
            elif cause == "dead":
                w.countries[host].exists = False
            else:
                w.countries[host].leader = "replacement"
            w.daily()
            self.assertFalse(w.has(host, "leader"))
            self.assertTrue(w.has(host, "closed"))
            for tag in HOUSES:
                self.assertFalse(w.has(tag, "member_" + host))

    def test_two_hundred_day_external_war_requires_fresh_consent_then_founds(self):
        for host in HOUSES:
            for military in ((False, True) if host != "AVI" else (False,)):
                for affected in (host, next(t for t in ("ERI", "EYR") if t != host)):
                    with self.subTest(host=host, military=military, affected=affected):
                        w = UnionWorld().begin(host, military=military, subject=military)
                        w.draft(host)
                        w.replies(host, final=True)
                        before = w.resources()
                        completed = set(w.countries[host].focuses)
                        w.countries[affected].war = True
                        w.state_ids[LAND[affected][0]].controller = "GRI"
                        w.hook("on_war_relation_added", affected, "GRI")
                        self.assertTrue(w.has(host, "suspended"))
                        w.advance_days(200)
                        w.daily()
                        self.assertTrue(w.has(host, "leader"))
                        self.assertFalse(w.has(host, "closed"))
                        for other in HOUSES:
                            if other != host:
                                self.assertFalse(w.has(other, "consent_" + host))
                                self.assertFalse(w.has(other, "vote_pending_" + host))
                                # An old event's timeout/refusal cannot end a suspended mandate.
                                w.choose(w.event_id(host, True), 0, other)
                        w.countries[affected].war = False
                        w.state_ids[LAND[affected][0]].controller = affected
                        w.daily()
                        self.assertEqual(w.resources(), before)
                        self.assertEqual(w.countries[host].focuses, completed)
                        self.assertFalse(w.available(host, "constitutional_act"))
                        self.assertFalse(w.has(host, "suspended"))
                        w.replies(host, final=True)
                        w.complete(host, "constitutional_act")
                        self.assertTrue(w.has(host, "founded"))

    def test_long_occupation_without_war_also_resumes_paid_administration(self):
        for host in HOUSES:
            w = UnionWorld().begin(host)
            w.complete(host, "customs_union")
            w.complete(host, "common_works")
            w.advance_days(60)
            w.complete(host, "common_administration")
            before = w.resources()
            w.state_ids[LAND[host][0]].fully_controlled = False
            w.daily()
            w.advance_days(200)
            w.daily()
            self.assertTrue(w.has(host, "suspended"))
            self.assertFalse(w.has(host, "closed"))
            w.state_ids[LAND[host][0]].fully_controlled = True
            w.daily()
            self.assertEqual(w.resources(), before)
            self.assertFalse(w.available(host, "unified_command"))
            w.advance_days(90)
            w.complete(host, "unified_command")
            self.assertEqual(w.countries[host].political_power, 350)

    def test_short_war_quarantines_old_event_timeouts_before_new_ballots(self):
        w = UnionWorld().begin("ERI")
        w.draft("ERI")
        w.replies("ERI", final=True, responses={"EYR": None})
        w.countries["ERI"].war = True
        w.daily()
        w.advance_days(5)
        w.countries["ERI"].war = False
        w.daily()
        self.assertFalse(w.has("EYR", "vote_pending_ERI"))
        w.choose(w.event_id("ERI", True), 0, "EYR")
        self.assertFalse(w.has("ERI", "closed"))
        w.advance_days(27)
        w.daily()
        self.assertTrue(w.has("EYR", "vote_pending_ERI"))
        w.replies("ERI", final=True)
        w.complete("ERI", "constitutional_act")

    def test_unanswered_invitation_is_deferred_through_long_war(self):
        w = UnionWorld().prepare("ERI")
        w.complete("ERI", "convention")
        w.replies("ERI", responses={"EYR": None})
        w.countries["EYR"].war = True
        w.daily()
        w.advance_days(200)
        w.daily()
        self.assertFalse(w.has("ERI", "closed"))
        self.assertTrue(w.has("EYR", "invite_deferred_ERI"))
        w.choose(w.event_id("ERI"), 0, "EYR")
        self.assertFalse(w.has("ERI", "closed"))
        w.countries["EYR"].war = False
        w.daily()
        w.replies("ERI")
        self.assertTrue(w.has("EYR", "member_ERI"))
        w.found("ERI")

    def test_optional_member_external_war_pauses_without_forced_withdrawal(self):
        for host in RIVAL:
            w = UnionWorld().begin(host)
            w.draft(host)
            w.replies(host, final=True)
            w.countries["AVI"].war = True
            w.daily()
            w.advance_days(200)
            w.daily()
            self.assertTrue(w.has("AVI", "member_" + host))
            self.assertTrue(w.has(host, "suspended"))
            w.countries["AVI"].war = False
            w.daily()
            w.replies(host, final=True)
            w.complete(host, "constitutional_act")
            self.assertTrue(w.has(host, "absorbed_AVI"))

    def test_failed_convention_allows_new_president_but_not_old_event_replay(self):
        w = UnionWorld().prepare("ERI")
        w.complete("ERI", "convention")
        w.replies("ERI", responses={"EYR": 0})
        w.countries["EYR"].ai = False
        w.complete("EYR", "convention")
        w.replies("EYR")
        w.choose(w.event_id("ERI"), 1, "EYR")
        self.assertFalse(w.has("EYR", "member_ERI"))
        self.assertTrue(w.has("ERI", "member_EYR"))
        self.assertEqual([h for h in HOUSES if w.has(h, "leader")], ["EYR"])

    def test_all_rewards_and_delayed_reports_are_idempotent(self):
        for host in HOUSES:
            w = UnionWorld().begin(host)
            w.found(host)
            w.advance_days(60)
            w.complete(host, "settled_institutions")
            self.assertTrue(w.deliver("hsm_ver_uni.30", host))
            baseline = w.resources()
            for _ in range(2):
                for stage, effect in zip(STAGES, REWARDS):
                    w.reward(host, stage)
                    w.uni(effect, host)
                for target in HOUSES:
                    if target != host:
                        w.choose(w.event_id(host), 1, target)
                        w.choose(w.event_id(host, True), 1, target)
                w.daily()
            self.assertEqual(baseline, w.resources())
            self.assertFalse(w.check(w.events["hsm_ver_uni.30"].get("trigger"), host))

    def test_production_ai_choice_has_one_positive_option_for_valid_compact(self):
        for host in HOUSES:
            w = UnionWorld().prepare(host)
            w.complete(host, "convention")
            for final in (False, True):
                if final:
                    w.replies(host)
                    w.draft(host)
                for other in HOUSES:
                    if other == host:
                        continue
                    event = w.events[w.event_id(host, final)]
                    weights = []
                    for option in event.all("option"):
                        ai = Node("ai", "=", option.get("ai_chance"))
                        weight = float(ai.get("factor", 1))
                        for modifier in ai.all("modifier"):
                            if w.check([n for n in modifier.children if n.key != "factor"], other):
                                weight *= float(modifier.get("factor", 1))
                        weights.append(weight)
                    self.assertEqual(weights, [0, 100])

    def test_actual_child_custody_transfers_without_inventing_or_promoting(self):
        for host, source in itertools.permutations(HOUSES, 2):
            for custody in ("actual", "elsewhere", "dead", "absent"):
                with self.subTest(host=host, source=source, custody=custody):
                    w = UnionWorld().begin(host)
                    for country in w.countries.values():
                        country.characters.discard(GROVER)
                    if custody in ("actual", "dead"):
                        w.countries[source].characters.add(GROVER)
                    elif custody == "elsewhere":
                        w.countries["GRI"].characters.add(GROVER)
                    if custody == "dead":
                        w.global_flags.add("GRI_grover_vi_dead")
                    leader = w.countries[host].leader
                    w.found(host)
                    self.assertEqual(GROVER in w.countries[host].characters, custody == "actual")
                    self.assertEqual(w.countries[host].leader, leader)
                    self.assertTrue(all(a[0] == "set_nationality" for a in w.character_actions))


class Structure(unittest.TestCase):
    def test_parse_references_wait_values_and_scoped_annexations(self):
        w = UnionWorld()
        definitions = set(w.triggers) | set(w.effects)
        for path in FILES:
            nodes = read(path)
            self.assertTrue(nodes)
            for n in walk(nodes):
                if n.key.startswith(PREFIX) and n.value in ("yes", "no"):
                    self.assertIn(n.key, definitions, (path, n.key))
                if n.key == "set_country_flag" and n.children:
                    self.assertEqual(n.get("value"), "1")
                    self.assertGreater(int(n.get("days")), 0)
                if n.key == "annex_country":
                    self.assertIn(n.get("target"), HOUSES)
                    self.assertEqual(n.get("transfer_troops"), "yes")
                self.assertNotIn(n.key, {"set_global_flag", "puppet", "set_politics", "recruit_character", "add_country_leader_role", "transfer_state"})
                self.assertNotIn(n.op, {">=", "<=", "!="})
                if n.key == "country_event" and n.children and not n.get("is_triggered_only"):
                    self.assertIn(n.get("id"), w.events)
        own_triggers = {n.key for n in read(FILES[1])}
        self.assertNotIn("HSM_VER_UNI_ducal_land_held", own_triggers)

    def test_focus_layout_prerequisites_and_pause_semantics(self):
        focuses = read(FILES[0])
        self.assertEqual([n.get("id") for n in focuses], [PREFIX + s for s in STAGES])
        for i, focus in enumerate(focuses):
            expected_positions = {"common_works": ("22", "4"), "common_administration": ("26", "4")}
            self.assertEqual((focus.get("x"), focus.get("y")), expected_positions.get(STAGES[i], ("24", str(i + 2))))
            offset = focus.all("offset")[0]
            self.assertEqual((offset.get("x"), offset.get("y")), ("34", "0"))
            self.assertEqual(offset.get("trigger")[0].value, "AVI")
            self.assertEqual(focus.get("cancel_if_invalid"), "no")
            self.assertEqual(focus.get("continue_if_invalid"), "no")
            expected_parents = {
                "common_administration": {"customs_union"},
                "unified_command": {"common_works", "common_administration"},
            }.get(STAGES[i], {STAGES[i - 1]} if i else set())
            self.assertEqual({n.value for group in focus.all("prerequisite") for n in group.children},
                             {PREFIX + parent for parent in expected_parents})
            self.assertEqual(focus.key, "joint_focus" if STAGES[i] in
                             ("customs_union", "common_works", "common_administration", "unified_command") else "shared_focus")

    def test_localisation_coverage_bom_and_clear_absorption_warning(self):
        locales = {}
        for lang in ("english", "russian"):
            found = {}
            for stem in ("HSM_VER_unification", "HSM_VER_focus_ui_postwar", "HSM_VER_event_ui_postwar", "HSM_VER_cooperation"):
                path = MOD / "localisation" / lang / (stem + "_l_" + lang + ".yml")
                self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
                for line in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
                    if not line.strip():
                        continue
                    match = re.fullmatch(r'\s*([^: ]+):0 "(.*)"', line)
                    self.assertIsNotNone(match, line)
                    key, value = match.groups()
                    self.assertNotIn(key, found)
                    found[key] = value
            locales[lang] = found
        self.assertEqual(locales["english"].keys(), locales["russian"].keys())
        required = set()
        for path in FILES:
            for n in walk(read(path)):
                if n.key in ("shared_focus", "joint_focus") and n.children:
                    required.update((n.get("id"), n.get("id") + "_desc"))
                if n.key in ("name", "title", "desc", "tooltip", "custom_effect_tooltip") and isinstance(n.value, str):
                    required.add(n.value)
                if n.key.startswith(PREFIX) and n.get("modifier"):
                    required.update((n.key, n.key + "_desc"))
        self.assertFalse(required - locales["english"].keys())
        warning = locales["english"]["HSM_VER_UNI_absorption_warning_tt"]
        self.assertIn("end of our independent state", warning)
        self.assertIn("government, forces and holdings", warning)
        for tag in HOUSES:
            self.assertIn("House", locales["english"][PREFIX + tag])

    def test_focus_and_idea_sprites_exist(self):
        sprites = set()
        for root in (OPT.game / "interface", OPT.eaw / "interface", MOD / "interface"):
            for path in root.rglob("*.gfx"):
                sprites.update(re.findall(r'\bname\s*=\s*"?(GFX_[^\s"}]+)', path.read_text(encoding="utf-8-sig", errors="replace")))
        self.assertTrue(sprites)
        for path in FILES:
            for n in walk(read(path)):
                if n.key in ("picture", "icon") and isinstance(n.value, str):
                    sprite = n.value if n.value.startswith("GFX_") else "GFX_idea_" + n.value
                    self.assertIn(sprite, sprites, (path, sprite))


class CosmeticIdentity(unittest.TestCase):
    def test_old_union_saves_migrate_for_each_house_without_gameplay_changes(self):
        for host in HOUSES:
            with self.subTest(host=host):
                w = UnionWorld()
                w.countries[host].flags.add(PREFIX + "founded")
                w.countries[host].cosmetic = PREFIX + host
                expected = copy.deepcopy(w.countries)
                expected[host].cosmetic = COSMETIC
                w.uni("migrate_cosmetic", host)
                self.assertEqual(w.countries, expected)
                w.uni("migrate_cosmetic", host)
                self.assertEqual(w.countries, expected)

    def test_daily_hook_upgrades_existing_union(self):
        for host in HOUSES:
            with self.subTest(host=host):
                w = UnionWorld()
                w.countries[host].flags.add(PREFIX + "founded")
                w.countries[host].cosmetic = PREFIX + host
                w.run(w.hooks["on_daily_" + host], host)
                self.assertEqual(w.countries[host].cosmetic, COSMETIC)

    def test_migration_never_overwrites_other_identities_or_unfounded_countries(self):
        for host, cosmetic in itertools.product(HOUSES, ("", COSMETIC, "GRI", "AVI_empire")):
            with self.subTest(host=host, cosmetic=cosmetic):
                w = UnionWorld()
                w.countries[host].flags.add(PREFIX + "founded")
                w.countries[host].cosmetic = cosmetic
                before = copy.deepcopy(w.countries)
                w.uni("migrate_cosmetic", host)
                self.assertEqual(w.countries, before)
        for host, founded, exists in itertools.product((*HOUSES, "GRI"), (False, True), (False, True)):
            if host in HOUSES and founded and exists:
                continue
            with self.subTest(host=host, founded=founded, exists=exists):
                w = UnionWorld()
                c = w.countries[host]
                c.exists, c.cosmetic = exists, PREFIX + "ERI"
                if founded:
                    c.flags.add(PREFIX + "founded")
                before = copy.deepcopy(w.countries)
                w.uni("migrate_cosmetic", host)
                self.assertEqual(w.countries, before)

    def test_only_shared_identity_is_assigned_by_unification(self):
        assignments = [n.value for n in walk(read(MOD / "common/scripted_effects/HSM_VER_unification.txt"))
                       if n.key == "set_cosmetic_tag"]
        self.assertEqual(assignments, [COSMETIC, COSMETIC])
        docs = (OPT.game / "documentation/triggers_documentation.md").read_text(encoding="utf-8-sig")
        self.assertIn("## has_cosmetic_tag", docs)

    def test_cosmetic_color_override_preserves_every_upstream_entry(self):
        relative = "common/countries/cosmetic.txt"
        upstream = (OPT.eaw / relative).read_text(encoding="utf-8-sig").rstrip()
        current = (MOD / relative).read_text(encoding="utf-8-sig")
        self.assertTrue(current.startswith(upstream), "Rebase cosmetic.txt against updated EaW; do not remove upstream colours")
        addition = re.sub(r"#[^\n]*", "", current[len(upstream):]).strip()
        for cosmetic in ("HSM_VER_UNIFIED", "HSM_VER_REGENCY"):
            match = re.match(re.escape(cosmetic) + r"\s*=\s*\{\s*color\s*=\s*rgb\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}\s*color_ui\s*=\s*rgb\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}\s*\}", addition)
            self.assertIsNotNone(match, addition)
            self.assertEqual(tuple(map(int, match.groups())), (62, 137, 124, 62, 137, 124))
            addition = addition[match.end():].strip()
        self.assertEqual(addition, "", "Unexpected extra cosmetic override")

    def test_shared_name_covers_all_ideologies_in_both_languages(self):
        for lang, name, adjective in (("english", "Verenia", "Verenian"), ("russian", "\u0412\u0435\u0440\u0435\u043d\u0438\u044f", "\u0412\u0435\u0440\u0435\u043d\u0441\u043a.")):
            path = MOD / "localisation" / lang / ("HSM_VER_cosmetic_l_" + lang + ".yml")
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            values = {}
            for line in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
                match = re.fullmatch(r'\s*([^: ]+):0 "(.*)"', line)
                self.assertIsNotNone(match, line)
                key, value = match.groups()
                self.assertNotIn(key, values)
                values[key] = value
            self.assertEqual(len(values), 15)
            self.assertEqual(values[COSMETIC], name)
            self.assertEqual(values[COSMETIC + "_DEF"], name)
            self.assertEqual(values[COSMETIC + "_ADJ"], adjective)
            for ideology, suffix in itertools.product(("neutrality", "democratic", "fascism", "communism"), ("", "_DEF", "_ADJ")):
                self.assertEqual(values[COSMETIC + "_" + ideology + suffix], "$" + COSMETIC + suffix + "$")

    def test_flag_exports_match_engine_sizes_and_are_opaque_nonblank_tga(self):
        for folder, size in (("", (82, 52)), ("medium", (41, 26)), ("small", (10, 7))):
            with self.subTest(size=size):
                data = (MOD / "gfx/flags" / folder / (COSMETIC + ".tga")).read_bytes()
                self.assertEqual(data[0:3], bytes((0, 0, 2)))
                self.assertEqual(struct.unpack_from("<HH", data, 12), size)
                self.assertEqual(data[16:18], bytes((32, 8)))
                self.assertEqual(len(data), 18 + size[0] * size[1] * 4)
                pixels = list(struct.iter_unpack("BBBB", data[18:]))
                self.assertTrue(all(a == 255 for b, g, r, a in pixels))
                self.assertGreater(len(set(pixels)), 16)
                self.assertTrue(any(g > r * 1.2 for b, g, r, a in pixels), "Missing teal field")
                self.assertTrue(any(r > g * 1.3 for b, g, r, a in pixels), "Missing crimson shield")
                self.assertTrue(any(min(r, g, b) > 170 for b, g, r, a in pixels), "Missing light band")


if __name__ == "__main__":
    unittest.main(argv=[__file__, *BASE["REST"]])
