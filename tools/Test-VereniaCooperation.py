"""Joint-focus/AI coordination contracts executed from production ASTs.

The fixture models only documented focus dispatch and ordered strategy lists;
it does not substitute for an in-game AI/multiplayer playtest.
"""
from __future__ import annotations
import copy
import itertools
import runpy
import unittest
from pathlib import Path

UNI = runpy.run_path(str(Path(__file__).with_name("Test-VereniaUnification.py")))
World, read, walk, MOD, Node = (UNI[k] for k in ("UnionWorld", "read", "walk", "MOD", "Node"))
HOUSES = UNI["HOUSES"]
STAGES = ("customs_union", "common_works", "common_administration", "unified_command")
FLAGS = ("customs", "works", "administration", "command")
INTRO = {"ERI": "HSM_ERI_cost_of_feud", "EYR": "HSM_EYR_the_price_of_vigilance"}
MILITARY = {"ERI": "HSM_ERI_FORCE_the_price_of_victory", "EYR": "HSM_EYR_FORCE_the_last_campaign"}
PLANS = read(MOD / "common/ai_strategy_plans/HSM_VER_cooperation.txt")


class CooperationWorld(World):
    def __init__(self):
        super().__init__()
        for tag, c in self.countries.items():
            c.focus_tree = "HSM_" + tag + "_negotiated_verenia"
            c.focus_progress = {}

    def cooperate(self):
        self.apply("HSM_VER_COOP_coordinate_routes", "ERI")

    def active_plans(self, tag):
        return [p for p in PLANS if self.check(p.get("allowed", []), tag)
                and self.check(p.get("enable", []), tag)
                and not self.check(p.get("abort", []), tag)]

    def next_planned(self, tag):
        plans = self.active_plans(tag)
        assert len(plans) <= 1, [p.key for p in plans]
        if not plans:
            return None
        completed = self.countries[tag].focuses
        for reference in plans[0].get("ai_national_focuses"):
            focus_id = reference.key
            focus = self.focuses[focus_id]
            if focus_id in completed:
                continue
            if any(not any(n.value in completed for n in g.children) for g in focus.all("prerequisite")):
                continue
            if any(n.value in completed for g in focus.all("mutually_exclusive") for n in g.children):
                continue
            if self.check(focus.get("available", []), tag):
                return focus_id
        return None


class AIPlans(unittest.TestCase):
    def test_intro_has_ordered_priority_before_every_development_root(self):
        for caller in ("ERI", "EYR"):
            w = CooperationWorld()
            w.root = caller
            w.cooperate()
            for tag in INTRO:
                self.assertEqual(w.next_planned(tag), INTRO[tag])
                self.assertEqual(len(w.active_plans(tag)), 1)
                self.assertIn("HSM_VER_diplomatic_route", w.countries[tag].flags)
                w.countries[tag].focuses.add(INTRO[tag])
                self.assertEqual(w.next_planned(tag), "HSM_" + tag + "_diplomatic_settlement")

    def test_ai_pair_resolution_is_idempotent_in_either_daily_order(self):
        for order in itertools.permutations(("ERI", "EYR")):
            w = CooperationWorld()
            for _ in range(3):
                for tag in order:
                    w.root = tag
                    w.apply("HSM_VER_COOP_coordinate_routes", tag)
            for tag in INTRO:
                self.assertIn("HSM_VER_diplomatic_route", w.countries[tag].flags)
                self.assertNotIn("HSM_VER_military_route", w.countries[tag].flags)

    def test_uncommitted_human_keeps_choice_and_ai_starts_own_intro(self):
        for human, ai in (("ERI", "EYR"), ("EYR", "ERI")):
            w = CooperationWorld()
            w.countries[human].ai = False
            w.cooperate()
            self.assertEqual(w.next_planned(ai), INTRO[ai])
            self.assertFalse(w.countries[human].flags)
            self.assertFalse(w.countries[ai].flags)
            w.countries[ai].focuses.add(INTRO[ai])
            # No forced route while waiting: normal domestic selection remains possible.
            self.assertEqual(w.active_plans(ai), [])

    def test_ai_follows_human_started_or_completed_route_without_touching_human(self):
        for human, ai in (("ERI", "EYR"), ("EYR", "ERI")):
            for kind in ("military", "diplomatic"):
                for form in ("flag", "progress", "history"):
                    with self.subTest(human=human, kind=kind, form=form):
                        w = CooperationWorld()
                        h = w.countries[human]
                        h.ai = False
                        focus = MILITARY[human] if kind == "military" else "HSM_" + human + "_diplomatic_settlement"
                        if form == "flag":
                            h.flags.add("HSM_VER_" + kind + "_route")
                        elif form == "progress":
                            h.focus_progress[focus] = 0.01
                        else:
                            h.focuses.add(focus)
                        before = copy.deepcopy((h.flags, h.focuses, h.focus_progress))
                        w.cooperate()
                        self.assertEqual(before, (h.flags, h.focuses, h.focus_progress))
                        self.assertIn("HSM_VER_" + kind + "_route", w.countries[ai].flags)
                        w.countries[ai].focuses.add(INTRO[ai])
                        self.assertEqual(w.next_planned(ai), MILITARY[ai] if kind == "military" else "HSM_" + ai + "_diplomatic_settlement")

    def test_existing_ai_military_choice_wins_over_other_ai_default(self):
        for first in INTRO:
            for form in ("flag", "progress", "history"):
                w = CooperationWorld()
                c = w.countries[first]
                if form == "flag":
                    c.flags.add("HSM_VER_military_route")
                elif form == "progress":
                    c.focus_progress[MILITARY[first]] = 0.4
                else:
                    c.focuses.add(MILITARY[first])
                w.cooperate()
                for tag in INTRO:
                    self.assertTrue(w.test("HSM_VER_COOP_military_choice", tag))
                    self.assertFalse(w.test("HSM_VER_COOP_diplomatic_choice", tag))

    def test_existing_opposite_legacy_choices_are_not_rewritten(self):
        w = CooperationWorld()
        w.countries["ERI"].flags.add("HSM_VER_military_route")
        w.countries["EYR"].flags.add("HSM_VER_diplomatic_route")
        before = {t: set(c.flags) for t, c in w.countries.items()}
        w.cooperate()
        self.assertEqual(before, {t: c.flags for t, c in w.countries.items()})

    def test_diplomatic_completion_cannot_overwrite_a_started_military_choice(self):
        for diplomat, soldier in (("ERI", "EYR"), ("EYR", "ERI")):
            w = CooperationWorld()
            w.countries[soldier].focus_progress[MILITARY[soldier]] = 0.5
            focus = w.focuses["HSM_" + diplomat + "_diplomatic_settlement"]
            self.assertFalse(w.check(focus.get("available"), diplomat))
            before = {t: set(c.flags) for t, c in w.countries.items()}
            w.run(focus.get("completion_reward"), diplomat)
            self.assertEqual(before, {t: c.flags for t, c in w.countries.items()})

    def test_campaign_plan_stops_after_coup_or_loss_of_independence(self):
        for tag, route, invalid in itertools.product(("ERI", "EYR"), ("diplomatic", "military"), ("coup", "subject")):
            with self.subTest(tag=tag, route=route, invalid=invalid):
                w = CooperationWorld()
                country = w.countries[tag]
                country.focuses.add(INTRO[tag])
                country.flags.add("HSM_VER_" + route + "_route")
                self.assertEqual(len(w.active_plans(tag)), 1)
                if invalid == "coup":
                    country.leader = "unrelated_successor"
                else:
                    country.subject = True
                self.assertEqual(w.active_plans(tag), [])

    def test_plan_lists_and_focus_factors_reference_loaded_production_focuses(self):
        w = CooperationWorld()
        self.assertEqual(len(PLANS), 6)
        for plan in PLANS:
            for n in plan.get("ai_national_focuses"):
                self.assertIn(n.key, w.focuses)
            for n in plan.get("focus_factors", []):
                self.assertIn(n.key, w.focuses)
                self.assertEqual(n.value, "0")


class JointProjects(unittest.TestCase):
    def test_members_can_initiate_customs_for_every_presidency(self):
        for host in HOUSES:
            for originator in HOUSES:
                with self.subTest(host=host, originator=originator):
                    w = CooperationWorld().begin(host)
                    self.assertIn("HSM_VER_UNI_convention", w.countries[originator].focuses)
                    w.complete(originator, "customs_union")
                    self.assertTrue(w.has(host, "customs"))
                    self.assertEqual([h for h in HOUSES if w.has(h, "customs")], [host])
                    for tag in HOUSES:
                        self.assertIn("HSM_VER_UNI_customs_union", w.countries[tag].focuses)
                        self.assertTrue(w.test("HSM_VER_UNI_receives_customs", tag))

    def test_sibling_projects_can_run_together_and_finish_in_either_order(self):
        for host in HOUSES:
            for order in itertools.permutations(("common_works", "common_administration")):
                w = CooperationWorld().begin(host)
                w.complete(host, "customs_union")
                members = [t for t in HOUSES if t != host]
                for actor, stage in zip(members, order):
                    self.assertTrue(w.available(actor, stage))
                    w.countries[actor].focus_progress["HSM_VER_UNI_" + stage] = 0.5
                before_pp = {t: c.political_power for t, c in w.countries.items()}
                # Both 28-day projects were eligible at the same instant.
                w.advance_days(28)
                for actor, stage in zip(members, order):
                    w.complete(actor, stage)
                self.assertTrue(w.has(host, "works"))
                self.assertTrue(w.has(host, "administration"))
                for tag in HOUSES:
                    self.assertEqual(w.countries[tag].political_power, before_pp[tag] - (100 if tag == host else 0))
                    for stage in order:
                        self.assertIn("HSM_VER_UNI_" + stage, w.countries[tag].focuses)
                self.assertFalse(w.available(host, "unified_command"))
                w.advance_days(89)
                self.assertFalse(w.available(host, "unified_command"))
                w.advance_days(1)
                self.assertTrue(w.available(members[0], "unified_command"))
                w.complete(members[0], "unified_command")
                self.assertEqual(w.countries[host].political_power, before_pp[host] - 150)
                # Constitution and absorption remain exclusively presidential.
                self.assertFalse(w.available(members[0], "constitutional_draft"))
                self.assertFalse(w.available(members[0], "constitutional_act"))
                self.assertTrue(w.available(host, "constitutional_draft"))

    def test_each_maturation_and_both_projects_are_independently_required(self):
        w = CooperationWorld().begin("ERI")
        w.complete("EYR", "customs_union")
        w.complete("ERI", "common_administration")
        w.advance_days(90)
        self.assertFalse(w.available("ERI", "unified_command"))
        w.complete("EYR", "common_works")
        self.assertTrue(w.available("ERI", "unified_command"))
        for flag in ("customs_wait", "admin_wait"):
            w.countries["ERI"].flags.add("HSM_VER_UNI_" + flag)
            self.assertFalse(w.available("EYR", "unified_command"))
            w.countries["ERI"].flags.discard("HSM_VER_UNI_" + flag)

    def test_only_presidents_budget_matters_and_duplicate_rewards_do_not_pay_again(self):
        w = CooperationWorld().begin("ERI")
        w.complete("EYR", "customs_union")
        w.countries["ERI"].political_power = 99
        w.countries["EYR"].political_power = 500
        self.assertFalse(w.available("EYR", "common_administration"))
        w.countries["ERI"].political_power = 200
        w.countries["EYR"].political_power = 0
        self.assertTrue(w.available("EYR", "common_administration"))
        w.complete("EYR", "common_administration")
        w.complete("AVI", "common_works")
        before = w.resources()
        for tag in HOUSES:
            for stage in ("customs_union", "common_administration", "common_works"):
                w.reward(tag, stage)
        self.assertEqual(before, w.resources())

    def test_membership_requires_the_accepted_active_presidency(self):
        w = CooperationWorld().begin("ERI", avian="neutral")
        self.assertFalse(w.test("HSM_VER_COOP_joint_member", "AVI"))
        self.assertFalse(w.test("HSM_VER_COOP_joint_member", "GRI"))
        w.countries["AVI"].flags.add("HSM_VER_UNI_member_EYR")
        self.assertFalse(w.test("HSM_VER_COOP_joint_member", "AVI"))
        w.countries["EYR"].flags.add("HSM_VER_UNI_leader")
        self.assertFalse(w.test("HSM_VER_COOP_joint_member", "ERI"))
        self.assertFalse(w.test("HSM_VER_COOP_joint_member", "EYR"))

    def test_history_only_repair_of_partial_old_save_does_not_charge_or_grant(self):
        w = CooperationWorld().begin("ERI")
        w.complete("ERI", "customs_union")
        w.complete("ERI", "common_works")
        w.complete("ERI", "common_administration")
        for tag in HOUSES:
            w.countries[tag].focuses.difference_update("HSM_VER_UNI_" + s for s in STAGES)
        before = w.resources()
        w.apply("HSM_VER_COOP_sync_history", "EYR")
        self.assertEqual(before, w.resources())
        for tag in HOUSES:
            for stage in STAGES[:3]:
                self.assertIn("HSM_VER_UNI_" + stage, w.countries[tag].focuses)
            self.assertNotIn("HSM_VER_UNI_unified_command", w.countries[tag].focuses)
        self.assertEqual(w.countries["ERI"].flag_days["HSM_VER_UNI_admin_wait"], 90)

    def test_deferred_old_completion_uses_existing_recovery_once(self):
        w = CooperationWorld().begin("ERI")
        w.countries["ERI"].focuses.update("HSM_VER_UNI_" + s for s in STAGES[:3])
        before_pp = w.countries["ERI"].political_power
        w.daily()
        self.assertTrue(w.has("ERI", "administration"))
        self.assertEqual(w.countries["ERI"].political_power, before_pp - 100)
        before = w.resources()
        w.daily()
        self.assertEqual(before, w.resources())
        self.assertIn("HSM_VER_UNI_common_administration", w.countries["EYR"].focuses)

    def test_suspension_preserves_shared_history_and_failed_presidency_does_not_autonominate(self):
        w = CooperationWorld().begin("ERI")
        w.complete("EYR", "customs_union")
        w.war_between("GRI", "ERI")
        w.daily()
        self.assertIn("HSM_VER_UNI_convention", w.countries["EYR"].focuses)
        self.assertFalse(w.available("EYR", "common_works"))
        w.end_wars()
        w.daily()
        w.uni("close_convention", "ERI")
        w.daily()
        self.assertFalse(w.has("EYR", "leader"))
        self.assertNotIn("HSM_VER_UNI_convention", w.countries["EYR"].focuses)

    def test_sync_does_not_claim_an_existing_private_convention_record(self):
        w = CooperationWorld().prepare("ERI")
        w.countries["EYR"].focuses.add("HSM_VER_UNI_convention")
        w.complete("ERI", "convention")
        w.replies("ERI")
        self.assertNotIn("HSM_VER_COOP_shared_history", w.countries["EYR"].flags)
        w.uni("close_convention", "ERI")
        w.apply("HSM_VER_COOP_release_shared_history", "ERI")
        self.assertIn("HSM_VER_UNI_convention", w.countries["EYR"].focuses)

    def test_ai_contributes_available_joint_projects_before_private_story(self):
        w = CooperationWorld().begin("ERI")
        w.complete("ERI", "customs_union")
        for tag in INTRO:
            w.countries[tag].ai = True
            w.countries[tag].flags.add("HSM_VER_diplomatic_route")
            w.countries[tag].focuses.add(INTRO[tag])
        self.assertEqual(w.next_planned("ERI"), "HSM_VER_UNI_common_works")
        self.assertEqual(w.next_planned("EYR"), "HSM_VER_UNI_common_administration")

    def test_production_hooks_scope_and_recipient_contract(self):
        w = CooperationWorld()
        hooks = read(MOD / "common/on_actions/HSM_VER_cooperation.txt")[0]
        self.assertTrue(hooks.all("on_startup"))
        for tag in HOUSES:
            self.assertTrue(hooks.all("on_daily_" + tag))
        for stage in STAGES:
            focus = w.focuses["HSM_VER_UNI_" + stage]
            self.assertEqual(focus.key, "joint_focus")
            self.assertTrue(focus.get("joint_trigger"))
            self.assertTrue(focus.get("completion_reward_joint_originator"))
            self.assertFalse(focus.get("completion_reward_joint_member"))
            self.assertFalse(any(n.key.startswith("HSM_VER_COOP_complete_")
                                 for n in walk(focus.get("completion_reward", []))))
        for path in (MOD / "common/scripted_triggers/HSM_VER_cooperation.txt",
                     MOD / "common/scripted_effects/HSM_VER_cooperation.txt"):
            self.assertFalse(any(n.key in ("ROOT", "FROM") for n in walk(read(path))))

    def test_founder_hook_is_after_commit_and_does_not_replace_consent(self):
        w = CooperationWorld().begin("ERI")
        found = w.effects["HSM_VER_UNI_found_union"][0].children
        clear = next(i for i, n in enumerate(found) if n.key == "clr_country_flag" and n.value == "HSM_VER_UNI_committing")
        hook = next(i for i, n in enumerate(found) if n.key == "HSM_VER_ROM_on_union")
        self.assertGreater(hook, clear)
        self.assertIn("HSM_VER_ROM_on_union", w.effects)
        self.assertFalse(w.available("ERI", "constitutional_act"))
        self.assertFalse(w.annexations)


if __name__ == "__main__":
    unittest.main(argv=[__file__] + UNI["BASE"]["REST"])

