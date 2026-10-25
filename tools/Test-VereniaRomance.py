"""Execute the romance's production scripts against bounded state fixtures.

python -B tools/Test-VereniaRomance.py [--eaw PATH] [-q]
Reuses the existing strict UNI/Grover interpreters; this is not a game playthrough.
Only the native add_country_leader_trait effect needs an additional fixture model.
"""
from __future__ import annotations

import copy
import itertools
import re
import runpy
import struct
import unittest
from pathlib import Path

GRO = runpy.run_path(str(Path(__file__).with_name("Test-VereniaGrover.py")))
UNI = GRO["SP"]["UNI"]
BASE = UNI["BASE"]
MOD, read, walk = (UNI[k] for k in ("MOD", "read", "walk"))
HOSTS = ("ERI", "EYR")
JOINT = "HSM_VER_rosaline_and_montague"
SINGLES = ("HSM_VER_rosaline_erie", "HSM_VER_montague_eyrie")
DUKES = {"ERI": "ERI_duke_vincent_erie", "EYR": "EYR_duke_iovinus_eyrie"}
P = "HSM_VER_ROM_"


class RomanceMixin:
    def run(self, nodes, tag="ERI"):
        taken = None
        for n in nodes:
            if n.key in ("if", "else_if", "else"):
                if n.key == "if":
                    taken = False
                assert taken is not None, "Conditional without if"
                if not taken and (n.key == "else" or self.check(n.get("limit", []), tag)):
                    taken = True
                    self.run([c for c in n.children if c.key != "limit"], tag)
            elif n.key == "add_country_leader_trait":
                assert isinstance(n.value, str)
                self.character_actions.append((n.key, self.countries[tag].leader, n.value))
            else:
                super().run([n], tag)

    def rom(self, suffix, host):
        self.root = host
        self.apply(P + suffix, host)

    def scene(self, number, host, choice=0):
        self.rom("maintain", host)
        self.advance_days(1)
        event = "hsm_ver_romance." + str(number)
        assert self.deliver(event, host), event
        self.choose(event, choice, host)

    def romance_packets(self):
        return [p for p in self.scheduled if p[2].startswith("hsm_ver_romance.")]


class RomanceWorld(RomanceMixin, UNI["UnionWorld"]):
    def story(self, host):
        self.prepare(host, avian="unsigned")
        for tag in HOSTS:
            self.countries[tag].flags.add("HSM_VER_diplomatic_route")
            self.countries[tag].characters.add(DUKES[tag])
        self.countries["ERI"].focuses.add("HSM_ERI_family_letters")
        self.countries["EYR"].focuses.add("HSM_EYR_montagues_correspondence")
        return self

    def convention(self, host):
        self.complete(host, "convention")
        self.replies(host)

    def full_arc(self, host, choice=0):
        self.story(host)
        self.scene(1, host)
        self.convention(host)
        self.scene(2, host, choice)
        self.draft(host)
        self.scene(3, host)
        self.replies(host, final=True)
        self.complete(host, "constitutional_act")
        self.scene(4, host)
        return self


class RomanceGrover(RomanceMixin, GRO["GroverWorld"]):
    def founder(self, host):
        rival = "EYR" if host == "ERI" else "ERI"
        self.countries[rival].exists = False
        self.countries[host].flags.update({"HSM_VER_UNI_diplomatic", "HSM_VER_UNI_president_" + host,
                                           "HSM_VER_UNI_absorbed_" + rival})
        return self


class RomanceGameplay(unittest.TestCase):
    def test_both_family_focuses_and_treaty_required(self):
        for host, missing in itertools.product(HOSTS, ("ERI", "EYR", "treaty")):
            with self.subTest(host=host, missing=missing):
                w = RomanceWorld().story(host)
                if missing == "treaty":
                    w.countries["ERI"].flags.discard("HSM_VER_treaty_signed")
                else:
                    w.countries[missing].focuses.discard("HSM_ERI_family_letters" if missing == "ERI" else "HSM_EYR_montagues_correspondence")
                w.rom("maintain", host)
                self.assertFalse(w.romance_packets())

    def test_single_delivery_even_with_both_daily_hooks_and_humans(self):
        w = RomanceWorld().story("ERI")
        w.countries["EYR"].ai = False
        for _ in range(10):
            for host in HOSTS:
                w.rom("maintain", host)
        self.assertEqual([(p[1], p[2]) for p in w.romance_packets()], [("ERI", "hsm_ver_romance.1")])

    def test_discarded_delivery_can_retry_after_peace(self):
        w = RomanceWorld().story("EYR")
        w.rom("maintain", "EYR")
        w.advance_days(1)
        w.countries["ERI"].war = True
        self.assertFalse(w.deliver("hsm_ver_romance.1", "EYR"))
        w.countries["ERI"].war = False
        w.advance_days(45)
        w.scene(1, "EYR")
        self.assertIn(P + "started", w.countries["ERI"].flags)

    def test_four_scenes_both_hosts_both_policy_choices(self):
        for host, choice in itertools.product(HOSTS, (0, 1)):
            with self.subTest(host=host, choice=choice):
                w = RomanceWorld().full_arc(host, choice)
                c = w.countries[host]
                self.assertEqual(c.leader, JOINT)
                self.assertTrue({JOINT, *SINGLES, DUKES[host]} <= c.characters)
                self.assertEqual(c.government, "neutrality")
                self.assertEqual(c.cosmetic, "HSM_VER_UNIFIED")
                self.assertTrue(w.test(P + "government", host))
                self.assertTrue(w.test("HSM_VER_GRO_government", host))
                self.assertTrue(w.test("HSM_VER_AVR_partner_available", host))
                trait = P + ("court_on_the_road" if choice else "doors_of_the_court")
                self.assertIn(("add_country_leader_trait", JOINT, trait), w.character_actions)
                self.assertFalse(w.test("HSM_VER_FORCE_eligible_house", host))
                self.assertNotIn(P + "legacy_handover", c.flags)

    def test_no_replacement_at_meeting_convention_or_draft(self):
        for host in HOSTS:
            w = RomanceWorld().story(host)
            w.scene(1, host)
            w.convention(host)
            w.scene(2, host)
            w.draft(host)
            w.scene(3, host)
            w.rom("crown", host)
            self.assertEqual(w.countries[host].leader, DUKES[host])
            self.assertFalse(w.character_actions)

    def test_work_requires_real_convention_and_betrothal_requires_admin_and_draft(self):
        w = RomanceWorld().story("ERI")
        w.scene(1, "ERI")
        w.rom("open_petitions", "ERI")
        self.assertNotIn(P + "service_agreed", w.countries["ERI"].flags)
        w.convention("ERI")
        w.scene(2, "ERI")
        for flag in ("HSM_VER_UNI_administration", "HSM_VER_UNI_draft"):
            probe = copy.deepcopy(w)
            probe.countries["ERI"].flags.add(flag)
            probe.rom("betroth", "ERI")
            self.assertNotIn(P + "betrothed", probe.countries["ERI"].flags)

    def test_open_scene_options_revalidate_after_war_coup_or_route_change(self):
        for failure in ("host_war", "partner_war", "coup", "military", "avian_presidency"):
            w = RomanceWorld().story("ERI")
            w.rom("maintain", "ERI")
            w.advance_days(1)
            self.assertTrue(w.deliver("hsm_ver_romance.1", "ERI"))
            if failure == "host_war":
                w.countries["ERI"].war = True
            elif failure == "partner_war":
                w.countries["EYR"].war = True
            elif failure == "coup":
                w.countries["ERI"].leader = "other_leader"
            elif failure == "military":
                w.countries["EYR"].flags.add("HSM_VER_military_route")
            else:
                w.countries["AVI"].flags.add("HSM_VER_UNI_leader")
            w.choose("hsm_ver_romance.1", 0, "ERI")
            self.assertNotIn(P + "started", w.countries["ERI"].flags, failure)

    def test_save_reload_and_annexation_preserve_unfinished_arc(self):
        for host in HOSTS:
            w = RomanceWorld().story(host)
            w.scene(1, host)
            w.convention(host)
            w.found(host)
            self.assertFalse(any(p[2] == "hsm_ver_romance.4" for p in w.romance_packets()))
            w = copy.deepcopy(w)
            w.scene(2, host, 1)
            w.scene(3, host)
            w.scene(4, host)
            self.assertEqual(w.countries[host].leader, JOINT)
            self.assertNotIn(P + "legacy_handover", w.countries[host].flags)

    def test_actual_founding_hook_and_daily_fallback_queue_only_one_migration_scene(self):
        for host in HOSTS:
            w = RomanceWorld().begin(host, avian="unsigned")
            w.found(host)
            for _ in range(5):
                w.rom("on_union", host)
                w.rom("maintain", host)
            self.assertEqual(len(w.romance_packets()), 1)
            self.assertEqual(w.countries[host].leader, DUKES[host])
            w.scene(4, host)
            self.assertIn(P + "legacy_handover", w.countries[host].flags)

    def test_provenance_excludes_avian_military_and_cosmetic_only_saves(self):
        for host in (*HOSTS, "AVI"):
            w = RomanceWorld().begin(host, military=host != "AVI")
            w.found(host)
            w.rom("maintain", host)
            self.assertFalse(w.romance_packets())
            self.assertNotEqual(w.countries[host].leader, JOINT)
        for missing in ("HSM_VER_UNI_diplomatic", "HSM_VER_UNI_founded", "HSM_VER_UNI_president_ERI", "HSM_VER_UNI_absorbed_EYR"):
            w = RomanceWorld().begin("ERI", avian="unsigned")
            w.found("ERI")
            w.scheduled.clear()
            w.countries["ERI"].flags.discard(missing)
            w.rom("crown", "ERI")
            self.assertNotEqual(w.countries["ERI"].leader, JOINT, missing)

    def test_delayed_handover_and_daily_never_override_a_successor(self):
        w = RomanceWorld().begin("ERI", avian="unsigned")
        w.found("ERI")
        w.advance_days(1)
        self.assertTrue(w.deliver("hsm_ver_romance.4", "ERI"))
        w.countries["ERI"].leader = "successor"
        w.choose("hsm_ver_romance.4", 0, "ERI")
        self.assertEqual(w.countries["ERI"].leader, "successor")
        self.assertFalse(w.character_actions)
        w = RomanceWorld().full_arc("EYR")
        before = copy.deepcopy(w.character_actions)
        w.countries["EYR"].leader = "successor"
        for _ in range(3):
            w.advance_days(60)
            w.rom("maintain", "EYR")
            w.choose("hsm_ver_romance.4", 0, "EYR")
        self.assertEqual(w.countries["EYR"].leader, "successor")
        self.assertEqual(w.character_actions, before)
        self.assertFalse(w.test(P + "government", "EYR"))

    def test_foreign_or_extinct_character_assignment_is_not_stolen(self):
        for token, exists in itertools.product((JOINT, *SINGLES), (False, True)):
            w = RomanceWorld().begin("ERI", avian="unsigned")
            w.found("ERI")
            w.countries["GRI"].characters.add(token)
            w.countries["GRI"].exists = exists
            w.rom("crown", "ERI")
            self.assertNotEqual(w.countries["ERI"].leader, JOINT)
            self.assertIn(token, w.countries["GRI"].characters)

    def test_double_click_and_later_ticks_cannot_repeat_appointments(self):
        w = RomanceWorld().full_arc("ERI")
        before = copy.deepcopy(w.character_actions)
        for _ in range(3):
            w.choose("hsm_ver_romance.4", 0, "ERI")
            w.advance_days(60)
            w.rom("maintain", "ERI")
        self.assertEqual(w.character_actions, before)
        self.assertFalse(w.romance_packets())

    def test_advisers_require_actual_joint_ruler(self):
        chars = read(MOD / "common/characters/HSM_VER_romance.txt")[0]
        w = RomanceWorld().full_arc("ERI")
        for token in SINGLES:
            advisor = next(c for c in chars.children if c.key == token).all("advisor")[0]
            self.assertTrue(w.check(advisor.get("available"), "ERI"))
            self.assertEqual(advisor.get("cost"), "100")
        w.countries["ERI"].leader = "successor"
        for token in SINGLES:
            advisor = next(c for c in chars.children if c.key == token).all("advisor")[0]
            self.assertFalse(w.check(advisor.get("available"), "ERI"))

    def test_late_avian_accession_keeps_joint_rulers_and_transfers_grover(self):
        for host in HOSTS:
            w = RomanceWorld().full_arc(host)
            for c in w.countries.values():
                c.characters.discard(GRO["GROVER"])
            w.countries["AVI"].characters.add(GRO["GROVER"])
            w.root = host
            w.apply("HSM_VER_AVR_offer", host)
            w.advance_days(1)
            self.assertTrue(w.deliver("hsm_ver_avr.1", "AVI"))
            w.choose("hsm_ver_avr.1", 1, "AVI")
            w.root = host
            w.apply("HSM_VER_AVR_customs", host)
            w.advance_days(1)
            self.assertTrue(w.deliver("hsm_ver_avr.2", "AVI"))
            w.choose("hsm_ver_avr.2", 1, "AVI")
            w.advance_days(60)
            w.root = host
            self.assertTrue(w.test("HSM_VER_AVR_can_integrate", host))
            w.apply("HSM_VER_AVR_integrate", host)
            self.assertFalse(w.countries["AVI"].exists)
            self.assertEqual(w.countries[host].leader, JOINT)
            self.assertIn(GRO["GROVER"], w.countries[host].characters)
            self.assertNotIn(GRO["GROVER"], w.countries["AVI"].characters)
            self.assertTrue(w.test("HSM_VER_AVR_absorbed", host))

    def test_grover_regency_survives_and_restores_independent_empire(self):
        for host in HOSTS:
            w = RomanceGrover(host).founder(host)
            w.prepare()
            w.rom("crown", host)
            self.assertEqual(w.countries[host].leader, JOINT)
            self.assertTrue(w.test("HSM_VER_GRO_government", host))
            self.assertTrue(w.test("HSM_VER_GRO_protected_household", host))
            w.gro("maintain")
            self.assertNotIn("HSM_VER_GRO_interrupted", w.countries[host].flags)
            self.assertIn(GRO["GROVER"], w.countries[host].characters)
            w.date = GRO["BIRTHDAY"] + GRO["datetime"].timedelta(days=1)
            w.gro("maintain")
            self.assertTrue(w.countries["GRI"].exists)
            self.assertFalse(w.countries["GRI"].subject)
            self.assertEqual(w.countries["GRI"].leader, GRO["GROVER"])
            self.assertEqual(w.countries[host].leader, JOINT)

    def test_couple_can_enter_grover_campaign_after_wedding(self):
        for host in HOSTS:
            w = RomanceGrover(host).founder(host)
            w.rom("crown", host)
            self.assertTrue(w.test("HSM_VER_GRO_can_start", host))
            w.mandate()
            self.assertTrue(w.test("HSM_VER_GRO_regency_live", host))
            self.assertTrue(w.test("HSM_VER_GRO_protected_household", host))


class RomanceSource(unittest.TestCase):
    def test_native_art_bindings_all_five_exports(self):
        chars = read(MOD / "common/characters/HSM_VER_romance.txt")
        portraits = [n.value for n in walk(chars) if n.key in ("large", "small")]
        self.assertEqual(len(portraits), 5)
        for relative in portraits:
            blob = (MOD / relative).read_bytes()
            width, height = struct.unpack_from("<HH", blob, 12)
            self.assertEqual((width, height), (65, 67) if "/Advisors/" in relative else (156, 210))

    def test_localisation_parity_encoding_and_scene_length(self):
        sets = []
        for lang in ("english", "russian"):
            blob = (MOD / f"localisation/{lang}/HSM_VER_romance_l_{lang}.yml").read_bytes()
            self.assertTrue(blob.startswith(b"\xef\xbb\xbf"))
            pairs = re.findall(r'^ ([\w.]+):0 "(.*)"$', blob.decode("utf-8-sig"), re.M)
            loc = dict(pairs)
            self.assertEqual(len(loc), len(pairs))
            sets.append(set(loc))
            for event in ("1", "2", "3", "4", "4.legacy"):
                self.assertGreater(len(loc[f"hsm_ver_romance.{event}.d"].split()), 100)
            for name in (JOINT, *SINGLES):
                self.assertIn(name, loc)
        self.assertEqual(*sets)

    def test_no_new_meters_random_effects_or_preunion_ruler_roles(self):
        scripts = [MOD / p / "HSM_VER_romance.txt" for p in ("events", "common/scripted_effects", "common/scripted_triggers", "common/on_actions")]
        forbidden = {"random", "random_list", "set_variable", "add_to_variable", "set_nationality", "retire", "set_politics", "annex_country"}
        self.assertFalse(forbidden & {n.key for p in scripts for n in walk(read(p))})
        chars = read(MOD / "common/characters/HSM_VER_romance.txt")
        self.assertFalse(any(n.key == "country_leader" for n in walk(chars)))
        effects = read(MOD / "common/scripted_effects/HSM_VER_romance.txt")
        appointing = [effect.key for effect in effects if any(n.key == "add_country_leader_role" for n in walk(effect.children))]
        self.assertEqual(appointing, [P + "crown"])

    def test_daily_hooks_and_exact_founding_hook_exist(self):
        hooks = read(MOD / "common/on_actions/HSM_VER_romance.txt")[0]
        self.assertEqual({h.key for h in hooks.children}, {"on_daily_ERI", "on_daily_EYR"})
        source = read(MOD / "common/scripted_effects/HSM_VER_unification.txt")
        founder = next(n for n in source if n.key == "HSM_VER_UNI_found_union")
        body = founder.all("if")[0].children
        hook = next(i for i, n in enumerate(body) if n.key == P + "on_union")
        for key, value in (("set_country_flag", "HSM_VER_UNI_founded"), ("clr_country_flag", "HSM_VER_UNI_committing")):
            self.assertTrue(any(n.key == key and n.value == value for n in body[:hook]))


if __name__ == "__main__":
    unittest.main(argv=[__file__, *BASE["REST"]], verbosity=2)
