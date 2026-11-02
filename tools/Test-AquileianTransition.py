"""Focused source scenarios for the seamless AQR transition; no generated writes.

Run: python -B -X utf8 tools/Test-AquileianTransition.py
Renders the helper in memory with the main builder's callback definitions and
reuses AquileianWorld's fail-closed interpreter. External phase predicates are
explicit fixture boundaries. This is not an HOI4 engine or UI playtest.
"""
from __future__ import annotations

import ast
import copy
from pathlib import Path
import runpy
import sys
import unittest

HERE = Path(__file__).resolve().parent
P = "HSM_AQR_"
saved_argv = sys.argv[:]
try:
    sys.argv = [str(HERE / "Test-AquileianRegions.py"), "--eaw", str(HERE.parent / "EaW")]
    HARNESS = runpy.run_path(str(HERE / "Test-AquileianRegions.py"))
finally:
    sys.argv = saved_argv
World, parse = HARNESS["AquileianWorld"], HARNESS["parse"]


def rendered():
    source = ast.parse((HERE / "Build-AquileianRegions.py").read_text(encoding="utf-8-sig"))
    main = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    callbacks = ("L", "block", "trig", "effect", "once", "tt", "focus", "event", "option")
    nodes = [n for n in source.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == "CONFIG" for t in n.targets)]
    nodes += [n for n in main.body if isinstance(n, ast.FunctionDef) and n.name in callbacks]
    env = dict(P=P, loc={}, triggers=[], effects=[], events=[], focuses=[])
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<builder callbacks only>", "exec"), env)
    helper = runpy.run_path(str(HERE / "aquileian_loyalty.py"))
    decisions = helper["build_loyalty"](*(env[k] for k in callbacks if k != "block"), env["CONFIG"])
    assert decisions == [] and env["focuses"] == [], "Automatic transition must not add visible focuses/decisions"
    # Real main-owned national_mandate completion, without running the builder.
    common = ast.parse((HERE / "aquileian_common.py").read_text(encoding="utf-8-sig"))
    main_calls = [n for n in ast.walk(common) if isinstance(n, ast.Expr)
                  and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
                  and n.value.func.id in ("once", "focus") and n.value.args
                  and isinstance(n.value.args[0], ast.Constant) and n.value.args[0].value == "national_mandate"]
    assert len(main_calls) == 2
    exec(compile(ast.Module(body=main_calls, type_ignores=[]), "<national mandate only>", "exec"), env)
    return env


class Transition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.render = rendered()

    def world(self, tag="JEB", regional_ai=False, centre_ai=True):
        w = World()
        w.triggers = {n.key: n.children for n in parse("\n".join(self.render["triggers"]))}
        w.effects = {n.key: n.children for n in parse("\n".join(self.render["effects"]))}
        w.events = {n.get("id"): n for n in parse("\n".join(self.render["events"]))}
        w.focuses = {n.get("id"): n for n in parse("\n".join(self.render["focuses"]))}
        # Owned helper inputs, explicitly supplied rather than silently ignored.
        w.triggers[P + "local_rule"] = parse("exists = yes has_capitulated = no has_country_flag = fixture_local_rule OR = { is_subject = no is_subject_of = JER }")
        w.triggers[P + "revolution_finished"] = parse("has_global_flag = JER_revolution_ended")
        w.triggers[P + "outcome"] = parse("has_country_flag = REVOLUTION_is_a_monarchist")
        w.triggers[P + "settled"] = parse("HSM_AQR_local_rule = yes has_country_flag = HSM_AQR_ratified")
        w.triggers[P + "rupture"] = parse("is_subject = no")
        # Native candidate eligibility is supplied by the settlement helper in
        # production. These isolated fixtures explicitly choose its result.
        for route in HARNESS["ROUTES"]:
            w.triggers[P + "native_candidate_" + route.key] = parse(
                "has_country_flag = fixture_candidate_" + route.key)
        w.global_flags.add("JER_revolution_ended")
        for region in ("JEB", "JRR", "JFT", "VIN"):
            c = w.countries[region]
            c.exists = region == tag
            c.flags.update({"fixture_local_rule", "REVOLUTION_is_a_monarchist"})
        c, centre = w.countries[tag], w.countries["JER"]
        c.ai, centre.ai = regional_ai, centre_ai
        c.political_power, c.stability = -25, .42
        c.subject, c.overlord = True, "JER"
        centre.flags.add("JER_is_monarchist")
        centre.focuses.update({"JER_state_of_aquileia", "native_progress"})
        centre.party_leaders = {"neutrality": "native_incumbent"}
        centre.focus_tree = "aquileian_focus"
        if not regional_ai:
            w.player_countries["regional_player"] = tag
        if not centre_ai:
            w.player_countries["centre_player"] = "JER"
        return w

    def open(self, w, tag="JEB", sender="JER"):
        w.scheduled.append((w.day, tag, "HSM_AQR.30", sender))
        return w.deliver("HSM_AQR.30", tag)

    def options(self, w, tag):
        return [o.get("name") for o in w.events["HSM_AQR.30"].all("option")
                if w.check(o.get("trigger", []), tag)]

    def test_two_choices_and_immediate_accept_all_controllers(self):
        for tag in ("JEB", "JRR", "JFT", "VIN"):
            for regional_ai, centre_ai in ((False, True), (True, True), (True, False), (False, False)):
                with self.subTest(tag=tag, regional_ai=regional_ai, centre_ai=centre_ai):
                    w = self.world(tag, regional_ai, centre_ai)
                    centre = w.countries["JER"]
                    preserved = copy.deepcopy((centre.party_leaders, centre.focus_tree, centre.focuses))
                    self.assertTrue(self.open(w, tag))
                    choices = self.options(w, tag)
                    self.assertEqual(len(choices), 2)
                    self.assertIn("HSM_AQR.30.lead", choices)
                    accept = next(n for n in choices if n != "HSM_AQR.30.lead")
                    expected = "incorporate" if regional_ai else "continue" if centre_ai else "game_over"
                    self.assertEqual(accept, "HSM_AQR.30." + expected)
                    w.click("HSM_AQR.30", accept, tag, sender="JER")
                    self.assertEqual(w.annexations, [("JER", tag, "yes")])
                    self.assertFalse(w.countries[tag].exists)
                    self.assertIn(P + "postwar_choice_answered", w.countries[tag].flags)
                    self.assertEqual(preserved, (centre.party_leaders, centre.focus_tree, centre.focuses))
                    self.assertEqual(len(w.player_changes), int(not regional_ai and centre_ai))
                    if not centre_ai:
                        self.assertEqual(w.player_countries["centre_player"], "JER")
                    w.click("HSM_AQR.30", accept, tag, sender="JER", stale=True)
                    self.assertEqual(len(w.annexations), 1)

    def test_free_immediate_war_before_ratification_and_idempotence(self):
        for subject, faction_leader in ((True, False), (False, False), (False, True)):
            with self.subTest(subject=subject, faction_leader=faction_leader):
                w = self.world()
                c, centre = w.countries["JEB"], w.countries["JER"]
                c.subject, c.overlord = subject, "JER" if subject else ""
                c.faction = centre.faction = w.countries["FLO"].faction = "shared"
                c.faction_leader, centre.faction_leader = faction_leader, not faction_leader
                c.naps.add("JER"); centre.naps.add("JEB")
                c.truces.add("JER"); centre.truces.add("JEB")
                c.guarantors.add("JER"); centre.guarantors.add("JEB")
                c.naps.add("FLO"); c.truces.add("FLO")
                other = copy.deepcopy(w.countries["FLO"])
                self.assertNotIn(P + "ratified", c.flags)
                self.assertTrue(self.open(w))
                w.click("HSM_AQR.30", "HSM_AQR.30.lead", "JEB", sender="JER")
                self.assertEqual((c.political_power, c.stability), (-25, .42))
                self.assertFalse(c.subject)
                self.assertEqual(c.wars, {"JER"})
                self.assertNotEqual(c.faction, centre.faction)
                self.assertNotIn("JER", c.naps | c.truces | c.guarantors)
                self.assertIn("FLO", c.naps & c.truces)
                self.assertEqual(w.countries["FLO"], other)
                self.assertIn(P + "leadership_war_started", c.flags)
                self.assertIn(P + "postwar_choice_answered", c.flags)
                self.assertIn(P + "national_mandate_done", c.flags)
                self.assertIn(P + "national_mandate", c.focuses)
                self.assertFalse(c.goals, "Completing the mandate must not grant a redundant war goal")
                before = copy.deepcopy(w.countries)
                w.effect(P + "national_countermandate", "JEB", sender="JER")
                self.assertEqual(w.countries, before)
                self.assertFalse(self.open(w))

    def test_stale_open_choices_have_no_effect(self):
        mutations = {
            "vanished": lambda w: setattr(w.countries["JER"], "exists", False),
            "changed_government": lambda w: setattr(w.countries["JER"], "government", "fascism"),
            "changed_regime": lambda w: w.countries["JER"].flags.discard("JER_is_monarchist"),
            "changed_identity": lambda w: setattr(w.countries["JER"], "original_tag", "FLO"),
            "foreign_overlord": lambda w: setattr(w.countries["JEB"], "overlord", "FLO"),
            "subject_centre": lambda w: setattr(w.countries["JER"], "subject", True),
            "war_with_centre": lambda w: w.countries["JEB"].wars.add("JER"),
            "human_centre": lambda w: setattr(w.countries["JER"], "ai", False),
        }
        for name, change in mutations.items():
            for choice in ("continue", "lead"):
                if name == "human_centre" and choice == "lead":
                    continue  # War against a human centre is explicitly allowed.
                with self.subTest(name=name, choice=choice):
                    w = self.world()
                    self.assertTrue(self.open(w))
                    change(w)
                    before = copy.deepcopy(w.countries)
                    w.click("HSM_AQR.30", "HSM_AQR.30." + choice, "JEB", sender="JER", stale=True)
                    self.assertEqual(w.countries, before)
                    self.assertFalse(w.annexations or w.player_changes)

    def test_first_refusal_preserves_second_provinces_open_or_queued_choice(self):
        for opened in (False, True):
            for second_choice in ("incorporate", "lead"):
                with self.subTest(opened=opened, second_choice=second_choice):
                    w = self.world(regional_ai=True)
                    for tag in ("JEB", "JRR"):
                        c = w.countries[tag]
                        c.exists, c.subject, c.overlord, c.ai = True, False, "", True
                    w.effect(P + "dispatch_postwar_choice", "JER")
                    w.day = 1
                    for _ in range(2):
                        self.assertTrue(w.deliver("HSM_AQR.456", "JER"))
                    w.day = 2
                    self.assertTrue(w.deliver("HSM_AQR.30", "JEB"))
                    if opened:
                        self.assertTrue(w.deliver("HSM_AQR.30", "JRR"))
                    w.click("HSM_AQR.30", "HSM_AQR.30.lead", "JEB", sender="JER")
                    self.assertTrue(w.countries["JER"].war)
                    # Model an allied province being called against the first
                    # refuser. That different war must not cancel its choice.
                    w.countries["JRR"].war = True
                    w.countries["JRR"].wars.add("JEB")
                    w.countries["JEB"].wars.add("JRR")
                    if not opened:
                        self.assertTrue(w.deliver("HSM_AQR.30", "JRR"))
                    w.root, w.sender = "JRR", "JER"
                    self.assertEqual(self.options(w, "JRR"), ["HSM_AQR.30.incorporate", "HSM_AQR.30.lead"])
                    w.click("HSM_AQR.30", "HSM_AQR.30." + second_choice, "JRR", sender="JER")
                    if second_choice == "lead":
                        self.assertEqual(w.countries["JER"].wars, {"JEB", "JRR"})
                    else:
                        self.assertEqual(w.annexations, [("JER", "JRR", "yes")])

    def test_already_fighting_another_country_can_receive_and_answer_offer(self):
        for choice in ("continue", "lead"):
            with self.subTest(choice=choice):
                w = self.world()
                c, centre = w.countries["JEB"], w.countries["JER"]
                c.war = centre.war = True
                c.wars.add("FLO")
                centre.wars.add("FLO")
                w.effect(P + "dispatch_postwar_choice", "JER")
                self.assertEqual(len(w.scheduled), 1)
                w.day = 1
                self.assertTrue(w.deliver("HSM_AQR.456", "JER"))
                w.day = 2
                self.assertTrue(w.deliver("HSM_AQR.30", "JEB"))
                self.assertEqual(self.options(w, "JEB"), ["HSM_AQR.30.continue", "HSM_AQR.30.lead"])
                w.click("HSM_AQR.30", "HSM_AQR.30." + choice, "JEB", sender="JER")
                self.assertIn(P + "postwar_choice_answered", c.flags)
                if choice == "lead":
                    self.assertEqual(c.wars, {"FLO", "JER"})
                    self.assertEqual(centre.wars, {"FLO", "JEB"})
                else:
                    self.assertEqual(w.annexations, [("JER", "JEB", "yes")])
                    self.assertEqual(w.player_countries["regional_player"], "JER")

    def test_stale_dismissal_resets_only_unanswered_episode(self):
        for reason in ("foreign_subject", "war_with_centre"):
            with self.subTest(reason=reason):
                w = self.world()
                self.assertTrue(self.open(w))
                c = w.countries["JEB"]
                if reason == "foreign_subject":
                    c.overlord = "FLO"
                else:
                    c.war = True
                    c.wars.add("JER")
                self.assertEqual(self.options(w, "JEB"), ["HSM_AQR.30.dismiss"])
                frozen = set(c.flags)
                w.effect(P + "dispatch_postwar_choice", "JER")
                self.assertEqual(c.flags, frozen, "Maintenance must not rewrite an open snapshot")
                w.click("HSM_AQR.30", "HSM_AQR.30.dismiss", "JEB", sender="JER")
                self.assertFalse({P + "postwar_choice_requested", P + "postwar_choice_delivered",
                                  P + "postwar_choice_answered", P + "transition_centre_neutrality"} & c.flags)
                self.assertFalse(w.annexations or w.player_changes)
                self.assertEqual(c.overlord, "FLO" if reason == "foreign_subject" else "JER")
                c.overlord, c.war = "JER", False
                c.wars.clear()
                w.effect(P + "dispatch_postwar_choice", "JER")
                self.assertEqual(len(w.scheduled), 1)

    def test_delayed_stale_offer_can_close_and_resend_for_new_government(self):
        w = self.world()
        c, centre = w.countries["JEB"], w.countries["JER"]
        w.effect(P + "dispatch_postwar_choice", "JER")
        w.day = 1
        self.assertTrue(w.deliver("HSM_AQR.456", "JER"))
        centre.government = "democratic"
        centre.flags.discard("JER_is_monarchist")
        centre.flags.add("JER_democracy_established")
        centre.party_leaders = {"democratic": "new_incumbent"}
        w.day = 2
        self.assertTrue(w.deliver("HSM_AQR.30", "JEB"))
        self.assertEqual(self.options(w, "JEB"), ["HSM_AQR.30.dismiss"])
        before = copy.deepcopy(w.countries)
        w.click("HSM_AQR.30", "HSM_AQR.30.continue", "JEB", sender="JER", stale=True)
        self.assertEqual(w.countries, before)
        w.effect(P + "dispatch_postwar_choice", "JER")
        self.assertIn(P + "transition_centre_neutrality", c.flags)
        self.assertNotIn(P + "transition_centre_democratic", c.flags)
        self.assertFalse(w.scheduled)
        w.click("HSM_AQR.30", "HSM_AQR.30.dismiss", "JEB", sender="JER")
        w.effect(P + "dispatch_postwar_choice", "JER")
        self.assertNotIn(P + "transition_centre_neutrality", c.flags)
        self.assertIn(P + "transition_centre_democratic", c.flags)
        self.assertNotIn(P + "transition_JER_is_monarchist", c.flags)
        self.assertIn(P + "transition_JER_democracy_established", c.flags)
        w.day = 3
        self.assertTrue(w.deliver("HSM_AQR.456", "JER"))
        w.day = 4
        self.assertTrue(w.deliver("HSM_AQR.30", "JEB"))
        self.assertEqual(len(self.options(w, "JEB")), 2)
        w.click("HSM_AQR.30", "HSM_AQR.30.continue", "JEB", sender="JER")
        self.assertEqual(w.annexations, [("JER", "JEB", "yes")])
        self.assertEqual(centre.party_leaders, {"democratic": "new_incumbent"})

    def test_invalid_undelivered_queue_resets_without_repeated_requests(self):
        w = self.world()
        c = w.countries["JEB"]
        w.effect(P + "dispatch_postwar_choice", "JER")
        c.overlord = "FLO"
        w.day = 1
        self.assertTrue(w.deliver("HSM_AQR.456", "JER"))
        self.assertFalse({P + "postwar_choice_requested", P + "postwar_choice_queued"} & c.flags)
        for _ in range(3):
            w.effect(P + "dispatch_postwar_choice", "JER")
        self.assertFalse(w.scheduled)
        c.overlord = "JER"
        w.countries["JER"].government = "fascism"
        w.effect(P + "dispatch_postwar_choice", "JER")
        for _ in range(3):
            w.effect(P + "dispatch_postwar_choice", "JER")
        self.assertEqual(len(w.scheduled), 1)
        self.assertIn(P + "transition_centre_fascism", c.flags)
        self.assertNotIn(P + "transition_centre_neutrality", c.flags)

    def test_ai_preferences_follow_native_candidates_then_selected_then_ratified(self):
        def weights(w):
            result = {}
            for opt in w.events["HSM_AQR.30"].all("option"):
                if opt.get("name") not in ("HSM_AQR.30.incorporate", "HSM_AQR.30.lead"):
                    continue
                terms = opt.get("ai_chance", [])
                weight = float(next(n.value for n in terms if n.key == "factor"))
                for modifier in (n for n in terms if n.key == "modifier"):
                    if w.check([n for n in modifier.children if n.key != "factor"], w.root):
                        weight *= float(modifier.get("factor"))
                result[opt.get("name").split(".")[-1]] = weight
            return result["incorporate"], result["lead"]

        w = self.world(regional_ai=True)
        w.root, w.sender = "JEB", "JER"
        c = w.countries["JEB"]
        self.assertEqual(weights(w), (20, 1))
        c.flags.add("fixture_candidate_JEB_constitutional")
        self.assertEqual(weights(w), (1, 30), "Own-model native candidate must matter before ratification")
        c.flags.add("fixture_candidate_JEB_moderate")
        self.assertEqual(weights(w), (20, 1), "A cross-family tie is not an authored winner")
        c.flags.add(P + "native_mandate_JEB_constitutional")
        self.assertEqual(weights(w), (1, 30))
        c.flags.add(P + "ratified_JEB_moderate")
        self.assertEqual(weights(w), (20, 1), "The final programme outranks an old selection")
        w = self.world("JFT", regional_ai=True)
        w.root, w.sender = "JFT", "JER"
        w.countries["JFT"].flags.add("fixture_candidate_JFT_dennis")
        self.assertEqual(weights(w), (20, 3))

    def test_fallback_sender_queue_latch_and_native_race(self):
        w = self.world()
        for region in ("JEB", "JRR", "JFT", "VIN"):
            w.countries[region].exists = True
        w.effect(P + "dispatch_postwar_choice", "JER")
        self.assertEqual(len(w.scheduled), 4)
        w.effect(P + "dispatch_postwar_choice", "JER")
        self.assertEqual(len(w.scheduled), 4)
        # Native .30 delivers first for JEB and consumes that pending episode.
        self.assertTrue(self.open(w))
        w.day = 1
        for _ in range(4):
            self.assertTrue(w.deliver("HSM_AQR.456", "JER"))
        packets = [p for p in w.scheduled if p[2] == "HSM_AQR.30"]
        self.assertEqual({p[1] for p in packets}, {"JRR", "JFT", "VIN"})
        self.assertEqual({p[3] for p in packets}, {"JER"})
        w.day = 2
        for region in ("JRR", "JFT", "VIN"):
            self.assertTrue(w.deliver("HSM_AQR.30", region))
            self.assertEqual(len(self.options(w, region)), 2)
        self.assertFalse(self.open(w), "Already delivered native event must not reopen")
        w.effect(P + "dispatch_postwar_choice", "JER")
        self.assertFalse(w.scheduled)

    def test_invalid_offer_and_retired_protocol(self):
        w = self.world()
        self.assertFalse(self.open(w, sender="FLO"))
        w.global_flags.clear()
        self.assertFalse(self.open(w))
        self.assertFalse(w.countries["JEB"].flags & {P + "postwar_choice_requested"})
        for number in range(450, 456):
            self.assertFalse(w.check(w.events[f"HSM_AQR.{number}"].get("trigger"), "JEB"))
        before = copy.deepcopy(w.countries)
        for name in ("request_support", "authorise_support", "take_national_leadership", "accept_leadership"):
            w.effect(P + name, "JEB", sender="JER")
        self.assertEqual(w.countries, before)
        w = self.world(centre_ai=False)
        self.assertTrue(self.open(w))
        before = copy.deepcopy(w.countries)
        w.effect(P + "accept_central_demand", "JEB", sender="JER")
        self.assertEqual(w.countries, before, "Human game-over requires its explicit option")

    def test_fresh_country_scopes_and_preview_only_war(self):
        w = self.world()
        for name in ("continue_at_centre", "merge_into_centre", "accept_central_demand"):
            self.assertFalse(HARNESS["stale_effects_after_tag_change"](w.effects[P + name], w.effects))
        self.assertTrue(self.open(w))
        choice = next(n for n in w.events["HSM_AQR.30"].all("option") if n.get("name") == "HSM_AQR.30.lead")
        preview = choice.get("effect_tooltip", [])
        self.assertTrue(any(n.key == "declare_war_on" for n in HARNESS["walk"](preview)))
        before = copy.deepcopy(w.countries)
        w.run([n for n in choice.children if n.key == "effect_tooltip"], "JEB")
        self.assertEqual(w.countries, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
