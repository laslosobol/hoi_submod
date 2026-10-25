"""Production-script fixtures for the standalone Avian branch; no engine emulation."""
import copy
import runpy
import unittest
from pathlib import Path

FORCE = runpy.run_path(str(Path(__file__).with_name("Test-VereniaForce.py")))
World, MOD, read, walk = (FORCE[k] for k in ("ForceWorld", "MOD", "read", "walk"))


class AvianRelations(unittest.TestCase):
    def world(self, host="ERI", united=False):
        w = World()
        w.charter()
        w.countries["AVI"].focuses.add("intergigantes")
        w.countries[host].political_power = 250
        if united:
            rival = "EYR" if host == "ERI" else "ERI"
            w.countries[rival].exists = False
            for state in ("391", "400", "401", "500", "673"):
                w.state_ids[state].owner = w.state_ids[state].controller = host
            w.countries[host].flags.update({"HSM_VER_UNI_founded", "HSM_VER_UNI_absorbed_" + rival})
        w.root = host
        return w

    def agree(self, w, host):
        w.root = host
        w.apply("HSM_VER_AVR_offer", host)
        w.advance_days(1)
        self.assertTrue(w.deliver("hsm_ver_avr.1", "AVI"))
        w.choose("hsm_ver_avr.1", 1, "AVI")
        w.root = host

    def ratify(self, w, host):
        self.agree(w, host)
        w.apply("HSM_VER_AVR_customs", host)
        w.advance_days(1)
        self.assertTrue(w.deliver("hsm_ver_avr.2", "AVI"))
        w.choose("hsm_ver_avr.2", 1, "AVI")
        w.root = host

    def test_common_proclamation_selects_neither_route(self):
        w = self.world()
        avi = w.countries["AVI"]
        avi.focuses.discard("intergigantes")
        avi.focuses.add("proclamation_of_neutrality")
        self.assertFalse(w.test("HSM_VER_AVI_intergigantes_route"))
        self.assertFalse(w.test("HSM_VER_FORCE_can_claim_avian"))
        avi.focuses.add("pursue_true_neutrality")
        self.assertTrue(w.test("HSM_VER_FORCE_can_claim_avian"))
        self.assertFalse(w.test("HSM_VER_AVR_can_offer"))

    def test_intergigantes_selects_peace_not_conquest(self):
        for host in ("ERI", "EYR"):
            w = self.world(host)
            self.assertTrue(w.test("HSM_VER_AVR_can_offer", host))
            self.assertFalse(w.test("HSM_VER_FORCE_can_claim_avian", host))
            w.force("claim_avian", host)
            self.assertFalse(w.goal_actions)

    def test_new_regime_cannot_borrow_old_intergigantes_focus(self):
        w = self.world()
        w.countries["AVI"].focuses.add("fascists_win")
        self.assertFalse(w.test("HSM_VER_AVI_intergigantes_route"))
        w.apply("HSM_VER_AVR_offer")
        self.assertNotIn("hsm_ver_avr.1", w.countries["AVI"].events)

    def test_agreement_opens_membership_without_annexation(self):
        for host in ("ERI", "EYR"):
            w = self.world(host)
            self.agree(w, host)
            self.assertTrue(w.test("HSM_VER_AVR_agreement_live", host))
            self.assertIn("HSM_VER_charter_signed", w.countries["AVI"].flags)
            self.assertFalse(w.test("HSM_VER_AVR_accession_context", host))
            self.assertTrue(w.countries["AVI"].exists)
            self.assertFalse(w.annexations)

    def test_conquest_and_postwar_proof_also_work_after_diplomatic_ducal_union(self):
        for host in ("ERI", "EYR"):
            w = self.world(host, True)
            w.countries["AVI"].focuses = {"pursue_true_neutrality"}
            self.assertTrue(w.test("HSM_VER_FORCE_can_claim_avian", host))
            w.force("claim_avian", host)
            self.assertEqual(w.goal_actions, [(host, ("annex_everything", "AVI"))])
            w.avian_victory(host)
            self.assertTrue(w.test("HSM_VER_FORCE_avian_victory", host))

    def test_diplomatic_house_can_conquer_neutral_avian_not_the_reverse(self):
        for host in ("ERI", "EYR"):
            for united in (False, True):
                with self.subTest(host=host, united=united):
                    w = self.world(host, united)
                    w.countries[host].flags.add("HSM_VER_diplomatic_route")
                    w.countries[host].focuses.add("HSM_" + host + "_avian_question")
                    w.countries["AVI"].focuses = {"pursue_true_neutrality"}
                    self.assertFalse(w.test("HSM_VER_FORCE_settlement_active", host))
                    self.assertFalse(w.test("HSM_VER_AVR_can_offer", host))
                    force_file = "HSM_VER_erie_force.txt" if host == "ERI" else "HSM_VER_eyrie_force.txt"
                    claim = next(n for n in read(MOD / "common/national_focus" / force_file)
                                 if n.get("id") == "HSM_" + host + "_FORCE_avian_claim")
                    prerequisites = [n.value for block in claim.all("prerequisite")
                                     for n in block.all("focus")]
                    self.assertEqual(prerequisites, ["HSM_" + host + "_avian_question"])
                    self.assertTrue(w.check(claim.get("available", []), host))
                    w.run(claim.get("completion_reward", []), host)
                    self.assertEqual(w.goal_actions, [(host, ("annex_everything", "AVI"))])
                    self.assertFalse(w.test("HSM_VER_FORCE_can_claim_avian", "AVI"))
                    w.force("claim_avian", "AVI")
                    self.assertEqual(w.goal_actions, [(host, ("annex_everything", "AVI"))])

    def test_annexation_after_explicit_consent_transition_and_final_effect(self):
        for host in ("ERI", "EYR"):
            w = self.world(host, True)
            self.ratify(w, host)
            self.assertEqual(w.countries[host].political_power, 175)
            self.assertTrue(w.countries["AVI"].exists)
            self.assertFalse(w.test("HSM_VER_AVR_can_integrate", host))
            w.advance_days(59)
            self.assertFalse(w.test("HSM_VER_AVR_can_integrate", host))
            w.advance_days(1)
            self.assertTrue(w.test("HSM_VER_AVR_can_integrate", host))
            w.apply("HSM_VER_AVR_integrate", host)
            self.assertEqual(w.annexations, [(host, "AVI")])
            self.assertIn(host, w.state_ids["470"].cores)
            self.assertTrue(w.test("HSM_VER_AVR_absorbed", host))
            before = copy.deepcopy(w.countries[host].bonuses)
            w.apply("HSM_VER_AVR_integrate", host)
            w.apply("HSM_VER_AVR_customs", host)
            self.assertEqual(len(w.annexations), 1)
            self.assertEqual(before, w.countries[host].bonuses)
            self.assertEqual(w.countries[host].political_power, 175)

    def test_refusal_of_association_is_terminal_not_repeated_letters(self):
        w = self.world()
        w.apply("HSM_VER_AVR_offer")
        w.advance_days(1)
        w.deliver("hsm_ver_avr.1", "AVI")
        w.choose("hsm_ver_avr.1", 0, "AVI")
        w.choose("hsm_ver_avr.1", 1, "AVI")
        w.advance_days(200)
        w.apply("HSM_VER_AVR_offer")
        self.assertEqual(w.countries["AVI"].events.count("hsm_ver_avr.1"), 1)
        self.assertFalse(w.test("HSM_VER_AVR_agreement_live"))

    def test_final_refusal_preserves_avian_country_and_treaty(self):
        w = self.world(united=True)
        self.agree(w, "ERI")
        w.apply("HSM_VER_AVR_customs")
        w.advance_days(1)
        w.deliver("hsm_ver_avr.2", "AVI")
        w.choose("hsm_ver_avr.2", 0, "AVI")
        w.choose("hsm_ver_avr.2", 1, "AVI")
        w.advance_days(200)
        w.apply("HSM_VER_AVR_maintain")
        w.apply("HSM_VER_AVR_integrate")
        self.assertTrue(w.countries["AVI"].exists)
        self.assertTrue(w.test("HSM_VER_AVR_agreement_live"))
        self.assertEqual(w.countries["AVI"].events.count("hsm_ver_avr.2"), 1)
        self.assertFalse(w.annexations)

    def test_no_stale_reply_or_annexation_when_context_changes(self):
        for reason in ("subject", "war", "occupation", "foreign_faction", "regime", "lost_ducal_land"):
            with self.subTest(reason=reason):
                w = self.world(united=True)
                self.ratify(w, "ERI")
                w.advance_days(60)
                avi = w.countries["AVI"]
                if reason == "subject":
                    avi.subject, avi.overlord = True, "GRI"
                elif reason == "war":
                    w.declare("GRI", "AVI")
                elif reason == "occupation":
                    w.state_ids["470"].controller = "GRI"
                elif reason == "foreign_faction":
                    avi.faction = "foreign"
                elif reason == "regime":
                    avi.focuses.add("fascists_win")
                else:
                    w.state_ids["400"].controller = "GRI"
                w.apply("HSM_VER_AVR_integrate")
                w.apply("HSM_VER_AVR_maintain")
                self.assertFalse(w.annexations)
                self.assertNotIn("HSM_VER_AVR_ratified", w.countries["ERI"].flags)

    def test_cross_host_consent_is_not_transferable(self):
        w = self.world(united=True)
        self.ratify(w, "ERI")
        w.advance_days(60)
        w.countries["AVI"].flags.discard("HSM_VER_AVR_annex_ERI")
        w.countries["AVI"].flags.add("HSM_VER_AVR_annex_EYR")
        w.apply("HSM_VER_AVR_integrate")
        self.assertFalse(w.annexations)

    def test_interrupted_association_recovers_after_long_external_war(self):
        w = self.world(united=True)
        w.apply("HSM_VER_AVR_offer")
        w.declare("GRI", "AVI")
        w.apply("HSM_VER_AVR_maintain")
        w.advance_days(200)
        w.apply("HSM_VER_AVR_maintain")
        self.assertEqual(w.countries["AVI"].events.count("hsm_ver_avr.1"), 1)
        w.end_wars()
        w.apply("HSM_VER_AVR_maintain")
        w.apply("HSM_VER_AVR_maintain")
        self.assertEqual(w.countries["AVI"].events.count("hsm_ver_avr.1"), 2)

    def test_legacy_invitation_does_not_select_new_peace_route(self):
        for host, old in (("ERI", "HSM_ERI_invite_avian"), ("EYR", "HSM_EYR_a_seat_for_avian")):
            w = self.world(host)
            w.countries[host].focuses.add(old)
            w.countries["AVI"].focuses = {"pursue_true_neutrality"}
            w.apply("HSM_VER_AVR_maintain", host)
            self.assertTrue(w.test("HSM_VER_FORCE_can_claim_avian", host))
            force_file = "HSM_VER_erie_force.txt" if host == "ERI" else "HSM_VER_eyrie_force.txt"
            claim = next(n for n in read(MOD / "common/national_focus" / force_file)
                         if n.get("id") == "HSM_" + host + "_FORCE_avian_claim")
            self.assertNotEqual(claim.all("mutually_exclusive")[0].get("focus"), old)
            self.assertNotIn("hsm_ver_avr.1", w.countries["AVI"].events)

    def test_external_land_transfers_do_not_create_cores(self):
        w = self.world(united=True)
        foreign = w.state_ids["382"]
        foreign.owner = foreign.controller = "AVI"
        self.ratify(w, "ERI")
        w.advance_days(60)
        w.apply("HSM_VER_AVR_integrate")
        self.assertEqual(foreign.owner, "ERI")
        self.assertNotIn("ERI", foreign.cores)

    def test_household_transfer_never_invents_custody_or_revives_grover(self):
        grover = "GRI_emperor_grover_vi"
        for host in ("ERI", "EYR"):
            for situation in ("local", "dead", "foreign", "duplicate"):
                w = self.world(host, True)
                if situation != "foreign":
                    w.countries["AVI"].characters.add(grover)
                if situation != "duplicate" and situation != "foreign":
                    w.countries["GRI"].characters.discard(grover)
                if situation == "dead":
                    w.global_flags.add("GRI_grover_vi_dead")
                self.ratify(w, host)
                w.advance_days(60)
                w.apply("HSM_VER_AVR_integrate", host)
                self.assertEqual(grover in w.countries[host].characters, situation == "local")

    def test_actual_union_transaction_then_late_avian_accession_with_all_hooks(self):
        union = runpy.run_path(str(Path(__file__).with_name("Test-VereniaUnification.py")))
        for host in ("ERI", "EYR"):
            w = union["UnionWorld"]()
            full = World()
            for sid, state in full.state_ids.items():
                if sid not in w.state_ids:
                    w.state_ids[sid] = state
                    w.states.append(state)
            w.hooks = w.all_hooks
            w.begin(host, avian="unsigned")
            w.found(host)
            self.assertTrue(w.test("HSM_VER_UNI_ducal_land_held", host))
            self.assertTrue(w.countries["AVI"].exists)
            self.ratify(w, host)
            w.advance_days(60)
            w.apply("HSM_VER_AVR_integrate", host)
            self.assertTrue(w.test("HSM_VER_AVR_absorbed", host))
            self.assertEqual(w.annexations, [(host, "EYR" if host == "ERI" else "ERI"), (host, "AVI")])
            self.assertFalse(w.countries["AVI"].exists)

    def test_actual_avian_union_transaction_with_all_hooks(self):
        union = runpy.run_path(str(Path(__file__).with_name("Test-VereniaUnification.py")))
        w = union["UnionWorld"]()
        full = World()
        for sid, state in full.state_ids.items():
            if sid not in w.state_ids:
                w.state_ids[sid] = state
                w.states.append(state)
        w.hooks = w.all_hooks
        w.begin("AVI")
        w.found("AVI")
        self.assertEqual(w.annexations, [("AVI", "ERI"), ("AVI", "EYR")])
        self.assertTrue(w.test("HSM_VER_UNI_ducal_land_held", "AVI"))

    def test_actual_ducal_union_then_neutral_avian_war_has_visible_waits(self):
        union = runpy.run_path(str(Path(__file__).with_name("Test-VereniaUnification.py")))
        for host in ("ERI", "EYR"):
            with self.subTest(host=host):
                w = union["UnionWorld"]()
                full = World()
                for sid, state in full.state_ids.items():
                    if sid not in w.state_ids:
                        w.state_ids[sid] = state
                        w.states.append(state)
                w.hooks = w.all_hooks
                w.begin(host, avian="neutral")
                w.found(host)
                w.daily()
                self.assertFalse(w.test("HSM_VER_charter_valid", host))
                self.assertTrue(w.test("HSM_VER_AVR_regional_authority", host))
                prefix = "HSM_" + host + "_FORCE_"
                w.complete_force("HSM_" + host + "_avian_question", host)
                w.complete_force(prefix + "avian_claim", host)
                w.declare(host, "AVI")
                w.daily()
                w.capitulate("AVI", host)
                w.end_wars()
                w.run(FORCE["parse"]("annex_country = { target = AVI transfer_troops = yes }"), host)
                w.hook("on_peaceconference_ended", host, "AVI")
                w.advance_days(2)
                w.daily()
                self.assertTrue(w.test("HSM_VER_AVR_regional_authority", host))
                self.assertFalse(w.available_force(prefix + "avian_articles", host))
                checks = {
                    n.get("tooltip"): w.check([n], host)
                    for n in w.triggers["HSM_VER_FORCE_avian_victory"]
                    if n.key == "custom_trigger_tooltip"
                }
                self.assertEqual([key for key, passed in checks.items() if not passed],
                                 ["HSM_VER_FORCE_avian_settling_complete_tt"])
                w.advance_days(27)
                self.assertFalse(w.available_force(prefix + "avian_articles", host))
                w.advance_days(1)
                w.daily()
                w.complete_force(prefix + "avian_articles", host)
                w.advance_days(1)
                self.assertTrue(w.deliver("hsm_ver_force.12", host))
                w.choose("hsm_ver_force.12", 0, host)
                w.advance_days(89)
                self.assertFalse(w.available_force(prefix + "avian_integration", host))
                checks = {
                    n.get("tooltip"): w.check([n], host)
                    for n in w.triggers["HSM_VER_FORCE_can_integrate_avian"]
                    if n.key == "custom_trigger_tooltip"
                }
                self.assertEqual([key for key, passed in checks.items() if not passed],
                                 ["HSM_VER_FORCE_avian_transition_complete_tt"])
                w.advance_days(1)
                w.daily()
                w.complete_force(prefix + "avian_integration", host)
                self.assertIn(host, w.state_ids["470"].cores)
                self.assertIn("HSM_VER_FORCE_AVI_integrated", w.countries[host].flags)
                self.assertFalse(w.test("HSM_VER_charter_valid", host))

    def test_absorbed_sponsors_treaty_does_not_block_the_actual_union_host(self):
        union = runpy.run_path(str(Path(__file__).with_name("Test-VereniaUnification.py")))
        for host, sponsor in (("ERI", "EYR"), ("EYR", "ERI")):
            w = union["UnionWorld"]().prepare(host)
            self.agree(w, sponsor)
            w.complete(host, "convention")
            w.replies(host, responses={"AVI": 0})
            w.found(host)
            self.assertTrue(w.countries["AVI"].exists)
            self.assertFalse(w.countries[sponsor].exists)
            w.apply("HSM_VER_AVR_maintain", host)
            self.assertNotIn("HSM_VER_AVR_partner_" + sponsor, w.countries["AVI"].flags)
            self.assertTrue(w.test("HSM_VER_AVR_can_offer", host))
            self.assertFalse(w.test("HSM_VER_AVR_can_integrate", host))
            self.agree(w, host)
            self.assertIn("HSM_VER_AVR_partner_" + host, w.countries["AVI"].flags)
            self.assertNotIn("HSM_VER_AVR_annex_" + host, w.countries["AVI"].flags)

    def test_focus_branches_are_separate_from_ducal_choice(self):
        for host, filename, invite in (
            ("ERI", "HSM_ERI.txt", "HSM_ERI_avian_association"),
            ("EYR", "HSM_VER_eyrie.txt", "HSM_EYR_avian_association"),
        ):
            nodes = [n for n in walk(read(MOD / "common/national_focus" / filename))
                     if n.key == "focus" and n.get("id") == invite]
            focus = nodes[0]
            self.assertEqual(focus.all("prerequisite")[0].get("focus"), "HSM_" + host + "_avian_question")
            self.assertEqual((focus.get("x"), focus.get("y")), ("42", "1"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
