"""Production-script regressions for VERENIA_REGENCY_CONTRACT.md.

Run python -B tools/Test-VereniaRegency.py [-q] [TestClass.test_name].
Reuses the Avian/parser harness. State, character, date and war-side operations
are explicit fixture models; unsupported operations fail, never silently pass.
This is not an HOI4 runtime or a simulation of native custody event scheduling.
"""
from __future__ import annotations

import copy
import datetime
import itertools
import operator
import re
import runpy
import unittest
from dataclasses import dataclass
from pathlib import Path

AVIAN = runpy.run_path(str(Path(__file__).with_name("Test-VereniaAvian.py")))
BASE = AVIAN["BASE"]
Node, read, walk, MOD, OPT = (AVIAN[k] for k in ("Node", "read", "walk", "MOD", "OPT"))
State = AVIAN["State"]
GROVER = "GRI_emperor_grover_vi"
KATRINA = "AVI_lady_katrina_avian"
DEAD = "GRI_grover_vi_dead"
HOUSES = ("AVI", "ERI", "EYR")
HERZLAND = ("GRI", "BRZ", "STW", "KAT", "ANG", "YAL", "ROU", "PYT", "FEA")
DUCAL = ("391", "400", "401", "500", "673")
LAYOUT = {
    "after_defence": (50, 12), "household_file": (48, 13),
    "civilian_contracts": (52, 13), "agreement_for_herzland": (50, 14),
    "schools_and_witnesses": (48, 15), "defence_articles": (52, 15),
    "petitions_to_the_council": (50, 16), "rebuilding_the_quarters": (48, 17),
    "reserved_house_rights": (52, 17), "a_finite_guardianship": (48, 18),
    "a_union_without_a_throne": (52, 18), "the_settled_frontier": (50, 19),
}
COMPARE = {"=": operator.eq, "!=": operator.ne, ">": operator.gt,
           "<": operator.lt, ">=": operator.ge, "<=": operator.le}
IDEOLOGY_GROUPS = {
    subtype.key: group.key
    for container in read(OPT.eaw / "common/ideologies/00_ideologies.txt")
    for group in container.children
    for subtype in group.get("types", [])
}


@dataclass
class CharacterScope:
    token: str
    country: str


class RegencyWorld(AVIAN["AvianWorld"]):
    def __init__(self):
        super().__init__()
        # Execute the regency's existing dependencies; UNI is exercised via its
        # production land predicate and explicit founding/absorption contract.
        self.hooks = {}
        for module in ("diplomacy", "avian", "crisis", "eyrie", "force", "imperial", "regency", "zypressen"):
            for container in read(MOD / f"common/on_actions/HSM_VER_{module}.txt"):
                for hook in container.children:
                    self.hooks.setdefault(hook.key, []).extend(hook.get("effect", []))
        for tag in (*HERZLAND, "CYA", "FLO", "D01"):
            if tag not in self.countries:
                country = copy.deepcopy(self.countries["GRI"])
                country.tag = tag
                self.countries[tag] = country
        for tag, country in self.countries.items():
            country.original_tag = tag
            country.overlord = ""
            country.characters = set()
            country.war_allies = set()
            country.roles = {}
            country.party_leaders = {}
        self.countries["GRI"].characters.add(GROVER)
        self.countries["AVI"].characters.add(KATRINA)
        for group in ("neutrality", "democratic", "fascism"):
            self.countries["AVI"].party_leaders[group] = KATRINA
        self.portraits = {}
        self.character_actions = []
        self.idea_actions = []
        self.date = datetime.date(1020, 1, 1)
        self.previous = None
        self.states = []
        self.state_ids = {}
        self.arrays = {}
        # Two sentinels per original-core array detect loops checking only one item.
        for index, tag in enumerate(HERZLAND):
            states = []
            for offset in range(2):
                state_id = "382" if (index, offset) == (0, 0) else str(9000 + index * 2 + offset)
                state = State(cores={tag})
                states.append(state)
                self.states.append(state)
                self.state_ids[state_id] = state
            self.arrays[tag + ".original_cores"] = states
        for state_id in (*DUCAL, "470"):
            state = State(cores={"AVI"})
            self.state_ids[state_id] = state
            self.states.append(state)

    def resolve(self, value):
        return self.previous if value == "PREV" else super().resolve(value)

    def scoped_check(self, nodes, target, source):
        previous = self.previous
        self.previous = source
        try:
            return self.check(nodes, target)
        finally:
            self.previous = previous

    def scoped_run(self, nodes, target, source):
        previous = self.previous
        self.previous = source
        try:
            self.run(nodes, target)
        finally:
            self.previous = previous

    def check(self, nodes, tag="AVI"):
        for n in nodes:
            if n.key in self.triggers:
                ok = self.check(self.triggers[n.key], tag) == (n.value == "yes")
            elif n.key in ("AND", "OR", "NOT"):
                if n.key == "AND":
                    ok = self.check(n.children, tag)
                else:
                    any_true = any(self.check([child], tag) for child in n.children)
                    ok = any_true if n.key == "OR" else not any_true
            elif n.key in self.countries or n.key in ("ROOT", "FROM", "PREV"):
                ok = self.scoped_check(n.children, self.resolve(n.key), tag)
            elif n.key in self.state_ids:
                ok = self.scoped_check(n.children, self.state_ids[n.key], tag)
            elif n.key in ("owner", "controller"):
                assert isinstance(tag, State)
                ok = self.scoped_check(n.children, getattr(tag, n.key), tag)
            elif n.key in ("all_of_scopes", "any_of_scopes"):
                scopes = self.arrays[n.get("array")]
                checks = [self.scoped_check([x for x in n.children if x.key not in ("array", "tooltip")], scope, tag) for scope in scopes]
                ok = all(checks) if n.key == "all_of_scopes" else any(checks)
            elif n.key in ("any_country", "any_possible_country"):
                ok = any(self.scoped_check(n.children, t, tag) for t, c in self.countries.items()
                         if c.exists or n.key == "any_possible_country")
            elif n.key == "date":
                parts = tuple(map(int, n.value.split(".")))
                assert len(parts) == 3, "Hour-specific date comparisons are not modelled"
                ok = COMPARE[n.op](self.date, datetime.date(*parts))
            elif n.key == "original_tag":
                ok = self.countries[tag].original_tag == self.resolve(n.value)
            elif n.key == "has_character":
                ok = n.value in self.countries[tag].characters
            elif n.key == "has_country_leader":
                assert n.get("ruling_only", "yes") == "yes"
                ok = self.countries[tag].leader == n.get("character")
            elif n.key == "has_country_leader_ideology":
                country = self.countries[tag]
                role = country.roles.get(country.leader)
                ok = role is not None and role.get("ideology") == n.value
            elif n.key == "is_subject_of":
                ok = self.countries[tag].subject and self.countries[tag].overlord == self.resolve(n.value)
            elif n.key == "has_war_together_with":
                ok = self.resolve(n.value) in self.countries[tag].war_allies
            elif n.key in ("owns_state", "controls_state", "has_full_control_of_state"):
                state = self.state_ids[n.value]
                ok = state.owner == tag if n.key == "owns_state" else state.controller == tag
                if n.key == "has_full_control_of_state":
                    ok = ok and state.owner == tag
            elif n.key in ("is_owned_by", "is_owned_and_controlled_by"):
                assert isinstance(tag, State)
                ok = tag.owner == self.resolve(n.value)
                if n.key == "is_owned_and_controlled_by":
                    ok = ok and tag.controller == self.resolve(n.value)
            else:
                ok = super().check([n], tag)
            if not ok:
                return False
        return True

    def run(self, nodes, tag="AVI"):
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
            elif n.key in self.countries or n.key in ("ROOT", "FROM", "PREV"):
                self.scoped_run(n.children, self.resolve(n.key), tag)
            elif n.key in self.state_ids:
                self.scoped_run(n.children, self.state_ids[n.key], tag)
            elif n.key == "every_country":
                for target, country in self.countries.items():
                    if country.exists and self.scoped_check(n.get("limit", []), target, tag):
                        self.scoped_run([x for x in n.children if x.key != "limit"], target, tag)
            elif n.key in (GROVER, KATRINA):
                assert n.key in self.countries[tag].characters, "Character scope is not local"
                self.scoped_run(n.children, CharacterScope(n.key, tag), tag)
            elif n.key == "set_nationality":
                character = tag.token if isinstance(tag, CharacterScope) else n.get("character")
                source = tag.country if isinstance(tag, CharacterScope) else tag
                target = self.resolve(n.value if not n.children else n.get("target_country"))
                assert character in self.countries[source].characters
                self.countries[source].characters.remove(character)
                self.countries[target].characters.add(character)
                self.character_actions.append((n.key, character, source, target))
            elif n.key == "recruit_character":
                self.countries[tag].characters.add(n.value)
                self.character_actions.append((n.key, n.value, tag))
            elif n.key in ("set_global_flag", "clr_global_flag"):
                if n.key == "set_global_flag":
                    self.global_flags.add(n.value)
                else:
                    self.global_flags.discard(n.value)
            elif n.key == "add_country_leader_role":
                character = n.get("character", tag.token if isinstance(tag, CharacterScope) else "")
                country = tag.country if isinstance(tag, CharacterScope) else tag
                assert character in self.countries[country].characters
                role = Node("role", "=", n.get("country_leader", []))
                self.countries[country].roles[character] = role
                if n.get("promote_leader") == "yes":
                    group = IDEOLOGY_GROUPS[role.get("ideology")]
                    self.countries[country].party_leaders[group] = character
                    if self.countries[country].government == group:
                        self.countries[country].leader = character
                self.character_actions.append((n.key, character, country, role.get("ideology")))
            elif n.key == "set_politics":
                assert all(x.key in ("ruling_party", "elections_allowed") for x in n.children)
                country = self.countries[tag]
                if n.get("ruling_party"):
                    country.government = n.get("ruling_party")
                    country.leader = country.party_leaders.get(country.government, "unmodelled_party_leader")
            elif n.key == "set_portraits":
                character = n.get("character", tag.token if isinstance(tag, CharacterScope) else "")
                self.portraits[character] = copy.deepcopy(n.children)
            elif n.key == "add_ideas":
                self.idea_actions.append((tag, n.value))
                super().run([n], tag)
            else:
                super().run([n], tag)

    def advance_days(self, days):
        super().advance_days(days)
        self.date += datetime.timedelta(days=days)

    def hook(self, name, root, sender):
        self.root, self.sender = root, sender
        self.run(self.hooks.get(name, []), root)

    def join_defence(self, attacker, *defenders):
        for tag in defenders:
            self.countries[tag].wars.add(attacker)
            self.countries[tag].defensive_wars.add(attacker)
            self.countries[tag].war = True
            self.countries[attacker].wars.add(tag)
            self.countries[attacker].offensive_wars.add(tag)
            self.countries[attacker].war = True
        for tag in defenders:
            self.countries[tag].war_allies.update(set(defenders) - {tag})

    def end_wars(self):
        for country in self.countries.values():
            for attribute in ("wars", "defensive_wars", "offensive_wars", "war_allies"):
                getattr(country, attribute).clear()
            country.war = False

    def local_child(self, host="AVI"):
        for country in self.countries.values():
            country.characters.discard(GROVER)
        self.countries[host].characters.add(GROVER)

    def reg(self, name, tag="AVI"):
        self.root = tag
        self.apply("HSM_VER_REG_" + name, tag)

    def regtest(self, name, tag="AVI"):
        self.root = tag
        return self.test("HSM_VER_REG_" + name, tag)

    def context(self):
        """Seed certified history for isolated custody/vote tests, not provenance tests."""
        self.budget()
        country = self.countries["AVI"]
        country.flags.update({"HSM_AVI_settlement_completed", "HSM_VER_REG_started",
                              "HSM_VER_REG_defensive_war", "HSM_VER_REG_defeat", "HSM_VER_REG_peace"})
        country.focuses.add("HSM_AVI_a_union_worth_keeping")
        assert self.regtest("context")

    def proposal(self, kind="regency"):
        self.context()
        if kind == "regency":
            self.local_child()
        self.countries["AVI"].focuses.add("HSM_VER_REG_agreement_for_herzland")
        self.reg("propose_" + kind)
        assert "HSM_VER_REG_pending" in self.countries["AVI"].flags

    def agreement(self, kind="regency"):
        self.proposal(kind)
        self.reg("sign", "ERI")
        self.reg("sign", "EYR")
        assert self.regtest("agreement_live")

    def reward_reg(self, suffix):
        self.root = "AVI"
        key = "HSM_VER_REG_" + suffix
        self.countries["AVI"].focuses.add(key)
        self.run(self.focuses[key].get("completion_reward", []))

    def available_reg(self, suffix):
        self.root = "AVI"
        return self.check(self.focuses["HSM_VER_REG_" + suffix].get("available", []))

    def decision_reg(self, suffix, execute=False):
        self.root = "AVI"
        decision = self.decisions["HSM_VER_REG_" + suffix]
        allowed = self.check(decision.get("visible", [])) and self.check(decision.get("available", []))
        if execute:
            assert allowed, suffix
            self.countries["AVI"].political_power -= float(decision.get("cost", 0))
            self.run(decision.get("complete_effect", []))
        return allowed

    def war_setup(self, victim="EYR", aggressor="GRI"):
        self.budget()
        self.countries["AVI"].flags.add("HSM_AVI_settlement_completed")
        self.countries["AVI"].focuses.add("HSM_AVI_a_union_worth_keeping")
        self.hook("on_declare_war", aggressor, victim)
        self.join_defence(aggressor, *dict.fromkeys((victim, "AVI", "ERI")))

    def certify_victory(self, victor="AVI"):
        self.countries["GRI"].capitulated = True
        self.hook("on_capitulation_immediate", "GRI", victor)
        self.end_wars()
        self.countries["GRI"].exists = False
        self.hook("on_peaceconference_ended", "AVI", "GRI")

    def unify(self, absorbed=("ERI", "EYR")):
        """Model only UNI's published output, never create diplomatic history."""
        avian = self.countries["AVI"]
        avian.flags.add("HSM_VER_UNI_founded")
        for tag in absorbed:
            avian.flags.add("HSM_VER_UNI_absorbed_" + tag)
            self.countries[tag].exists = False
        for state_id in DUCAL:
            self.state_ids[state_id].owner = self.state_ids[state_id].controller = "AVI"

    def estate_proposal(self, kind="regency", absorbed=("ERI", "EYR")):
        self.context()
        self.unify(absorbed)
        if kind == "regency":
            self.local_child()
        self.countries["AVI"].focuses.add("HSM_VER_REG_agreement_for_herzland")
        self.reg("propose_" + kind)


class WarProvenance(unittest.TestCase):
    def test_actual_defensive_victory_and_exact_45_day_settling(self):
        for victor in ("AVI", "ERI"):
            with self.subTest(victor=victor):
                world = RegencyWorld()
                world.war_setup()
                world.certify_victory(victor)
                self.assertIn("HSM_VER_REG_peace", world.countries["AVI"].flags)
                self.assertFalse(world.available_reg("after_defence"))
                world.advance_days(44)
                world.daily()
                self.assertFalse(world.available_reg("after_defence"))
                world.advance_days(1)
                world.daily()
                self.assertTrue(world.available_reg("after_defence"))

    def test_original_empire_and_actual_victim_are_required(self):
        for reason in ("different_tag", "wrong_original", "non_signatory", "no_preserved_union"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.budget()
                aggressor, victim = "GRI", "EYR"
                if reason == "different_tag":
                    aggressor = "D01"
                    world.countries[aggressor].original_tag = "GRI"
                elif reason == "wrong_original":
                    world.countries["GRI"].original_tag = "D01"
                elif reason == "non_signatory":
                    victim = "FLO"
                else:
                    world.countries["AVI"].flags.remove("HSM_AVI_preserved_union")
                world.hook("on_declare_war", aggressor, victim)
                self.assertNotIn("HSM_VER_REG_defensive_war", world.countries["AVI"].flags)

    def test_defeat_requires_avian_defence_qualifying_victor_and_recorded_victim(self):
        for reason in ("avi_absent", "avi_offensive", "victim_absent", "unrelated_victor", "victor_offensive", "no_declaration"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.war_setup()
                victor = "ERI"
                if reason == "avi_absent":
                    world.countries["AVI"].defensive_wars.clear()
                elif reason == "avi_offensive":
                    world.countries["AVI"].offensive_wars.add("GRI")
                elif reason == "victim_absent":
                    world.countries["EYR"].defensive_wars.clear()
                elif reason == "unrelated_victor":
                    victor = "CYA"
                    world.countries[victor].defensive_wars.add("GRI")
                elif reason == "victor_offensive":
                    world.countries["ERI"].offensive_wars.add("GRI")
                else:
                    world.countries["GRI"].flags.discard("HSM_VER_REG_aggressor")
                world.hook("on_capitulation_immediate", "GRI", victor)
                self.assertNotIn("HSM_VER_REG_defeat", world.countries["AVI"].flags)

    def test_nonqualifying_peace_conference_does_not_certify_avian(self):
        for reason in ("other_winner", "other_loser", "winner_bypass", "loser_bypass", "no_defeat"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.war_setup()
                world.hook("on_capitulation_immediate", "GRI", "AVI")
                root, sender = "AVI", "GRI"
                if reason == "other_winner":
                    root = "ERI"
                elif reason == "other_loser":
                    sender = "CYA"
                elif reason.endswith("bypass"):
                    world.countries["AVI" if reason == "winner_bypass" else "GRI"].flags.add("bypass_on_peaceconference_ended")
                else:
                    world.countries["AVI"].flags.remove("HSM_VER_REG_defeat")
                world.end_wars()
                world.hook("on_peaceconference_ended", root, sender)
                self.assertNotIn("HSM_VER_REG_peace", world.countries["AVI"].flags)

    def test_liberation_and_later_house_offensive_erase_old_victory(self):
        for reason in ("liberation", "new_offensive"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.war_setup()
                world.hook("on_capitulation_immediate", "GRI", "AVI")
                if reason == "liberation":
                    world.hook("on_uncapitulation", "GRI", "AVI")
                else:
                    world.hook("on_declare_war", "EYR", "GRI")
                world.end_wars()
                world.hook("on_peaceconference_ended", "AVI", "GRI")
                self.assertNotIn("HSM_VER_REG_defeat", world.countries["AVI"].flags)
                self.assertNotIn("HSM_VER_REG_peace", world.countries["AVI"].flags)

    def test_territory_and_eri_certificates_do_not_backfill_avian_history(self):
        world = RegencyWorld()
        world.budget()
        world.countries["AVI"].flags.add("HSM_AVI_settlement_completed")
        world.countries["ERI"].flags.update({"HSM_VER_IMP_defensive_war_recorded", "HSM_VER_IMP_defeat_recorded", "HSM_VER_IMP_peace_recorded"})
        world.countries["GRI"].exists = False
        world.advance_days(100)
        world.daily()
        self.assertFalse(world.available_reg("after_defence"))


class AgreementVotes(unittest.TestCase):
    def test_each_proposal_needs_two_independent_house_signatures(self):
        for kind, order in itertools.product(("regency", "civil"), (("ERI", "EYR"), ("EYR", "ERI"))):
            with self.subTest(kind=kind, order=order):
                world = RegencyWorld()
                world.proposal(kind)
                world.sender = "CYA"
                for outsider in ("AVI", "CYA"):
                    world.choose("hsm_ver_regency.10", 0, outsider)
                self.assertFalse(world.regtest("agreement_live"))
                world.choose("hsm_ver_regency.10", 0, order[0])
                self.assertFalse(world.regtest("agreement_live"))
                world.choose("hsm_ver_regency.10", 0, order[1])
                self.assertTrue(world.regtest("agreement_live"))
                flag = "HSM_VER_REG_regency" if kind == "regency" else "HSM_VER_REG_compact"
                self.assertIn(flag, world.countries["AVI"].flags)
                for tag in HOUSES:
                    self.assertFalse(world.countries[tag].subject or world.countries[tag].faction)

    def test_refusal_cancels_partial_consent_without_punishment_or_auto_compact(self):
        for kind, refusing in itertools.product(("regency", "civil"), ("ERI", "EYR")):
            with self.subTest(kind=kind, refusing=refusing):
                world = RegencyWorld()
                world.proposal(kind)
                other = "EYR" if refusing == "ERI" else "ERI"
                before = {t: world.countries[t].political_power for t in HOUSES}
                world.choose("hsm_ver_regency.10", 0, other)
                world.choose("hsm_ver_regency.10", 1, refusing)
                world.choose("hsm_ver_regency.10", 0, refusing)
                self.assertFalse(world.regtest("agreement_live"))
                self.assertNotIn("HSM_VER_REG_compact", world.countries["AVI"].flags)
                self.assertEqual({t: world.countries[t].political_power for t in HOUSES}, before)
                for tag in ("ERI", "EYR"):
                    self.assertNotIn("HSM_VER_REG_signed", world.countries[tag].flags)
                    self.assertIn("HSM_VER_charter_signed", world.countries[tag].flags)

    def test_signed_replies_cannot_reverse_or_replay_final_agreement(self):
        world = RegencyWorld()
        world.agreement()
        before = copy.deepcopy(world.countries)
        events = list(world.scheduled)
        for tag, choice in itertools.product(("ERI", "EYR"), (0, 1)):
            world.choose("hsm_ver_regency.10", choice, tag)
        self.assertEqual(world.countries, before)
        self.assertEqual(world.scheduled, events)

    def test_dropped_votes_expire_at_45_and_new_civil_proposal_waits_90(self):
        world = RegencyWorld()
        world.proposal()
        world.choose("hsm_ver_regency.10", 0, "ERI")
        world.advance_days(44)
        world.daily()
        self.assertIn("HSM_VER_REG_pending", world.countries["AVI"].flags)
        world.advance_days(1)
        world.daily()
        self.assertNotIn("HSM_VER_REG_pending", world.countries["AVI"].flags)
        world.choose("hsm_ver_regency.10", 0, "EYR")
        self.assertFalse(world.regtest("agreement_live"))
        self.assertFalse(world.decision_reg("reconsider_agreement"))
        world.advance_days(44)
        self.assertFalse(world.decision_reg("reconsider_agreement"))
        world.advance_days(1)
        world.decision_reg("reconsider_agreement", True)
        world.choose("hsm_ver_regency.3", 1, "AVI")
        self.assertNotIn("HSM_VER_REG_signed", world.countries["ERI"].flags)
        for tag in ("ERI", "EYR"):
            world.choose("hsm_ver_regency.10", 0, tag)
        self.assertTrue(world.regtest("agreement_live"))
        self.assertIn("HSM_VER_REG_compact", world.countries["AVI"].flags)

    def test_stale_votes_revalidate_death_custody_occupation_and_war(self):
        for reason in ("death", "custody", "adult", "occupied", "war"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.proposal()
                world.choose("hsm_ver_regency.10", 0, "ERI")
                if reason == "death":
                    world.global_flags.add(DEAD)
                elif reason == "custody":
                    world.local_child("CYA")
                elif reason == "adult":
                    world.date = datetime.date(1021, 5, 22)
                elif reason == "occupied":
                    world.countries["EYR"].capitulated = True
                else:
                    world.war_between("AVI", "EYR")
                world.choose("hsm_ver_regency.10", 0, "EYR")
                self.assertFalse(world.regtest("agreement_live"))
                self.assertNotIn("HSM_VER_REG_regency", world.countries["AVI"].flags)

    def test_custody_refusal_and_timeout_preserve_host_with_90_day_retry(self):
        for refuse in (False, True):
            with self.subTest(refuse=refuse):
                world = RegencyWorld()
                world.context()
                world.local_child("EYR")
                world.reg("request_household")
                if refuse:
                    world.choose("hsm_ver_regency.12", 1, "EYR")
                world.advance_days(45)
                world.choose("hsm_ver_regency.12", 0, "EYR")
                self.assertIn(GROVER, world.countries["EYR"].characters)
                self.assertFalse(world.decision_reg("request_household"))
                world.advance_days(45)
                world.decision_reg("request_household", True)
                world.choose("hsm_ver_regency.12", 0, "EYR")
                self.assertIn(GROVER, world.countries["AVI"].characters)


class MajorityLifecycle(unittest.TestCase):
    def test_majority_appointment_waits_for_live_peace_control_and_both_signatures(self):
        for reason in ("foreign_war", "avi_occupied", "eyrie_occupied", "capital_control", "herzland_control", "eri_consent", "eyrie_consent", "charter_suspended"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.agreement()
                avian = world.countries["AVI"]
                if reason == "foreign_war":
                    world.join_defence("FLO", "AVI")
                    restore = world.end_wars
                elif reason in ("avi_occupied", "eyrie_occupied"):
                    country = world.countries["AVI" if reason == "avi_occupied" else "EYR"]
                    country.capitulated = True
                    restore = lambda: setattr(country, "capitulated", False)
                elif reason in ("capital_control", "herzland_control"):
                    state = world.state_ids["382"] if reason == "capital_control" else world.arrays["FEA.original_cores"][1]
                    state.controller = "CYA"
                    restore = lambda: setattr(state, "controller", "AVI")
                elif reason in ("eri_consent", "eyrie_consent"):
                    country = world.countries["ERI" if reason == "eri_consent" else "EYR"]
                    country.flags.remove("HSM_VER_REG_signed")
                    restore = lambda: country.flags.add("HSM_VER_REG_signed")
                else:
                    world.countries["ERI"].flags.add("HSM_VER_royal_exception")
                    world.apply("HSM_VER_reconcile_charter_suspension", "ERI")
                    restore = lambda: world.apply("HSM_VER_restore_charter", "ERI")
                world.date = datetime.date(1021, 5, 22)
                world.daily()
                world.choose("hsm_ver_regency.14", 0, "AVI")
                self.assertNotIn("HSM_VER_REG_regency", avian.flags)
                self.assertNotIn("HSM_VER_REG_joint_guardianship", avian.ideas)
                self.assertIn("HSM_VER_REG_majority_due", avian.flags)
                self.assertEqual(avian.leader, KATRINA)
                self.assertEqual(world.character_actions, [])
                restore()
                world.daily()
                world.choose("hsm_ver_regency.14", 0, "AVI")
                self.assertEqual(avian.leader, GROVER)

    def test_already_open_majority_event_rechecks_context_and_retries(self):
        world = RegencyWorld()
        world.agreement()
        world.date = datetime.date(1021, 5, 22)
        world.daily()
        world.advance_days(1)
        self.assertTrue(world.deliver("hsm_ver_regency.14", "AVI"))
        avian = world.countries["AVI"]
        avian.capitulated = True
        world.choose("hsm_ver_regency.14", 0, "AVI")
        self.assertEqual(avian.leader, KATRINA)
        self.assertIn("HSM_VER_REG_majority_due", avian.flags)
        world.advance_days(45)
        world.daily()
        self.assertEqual(avian.events.count("hsm_ver_regency.14"), 1)
        avian.capitulated = False
        world.daily()
        self.assertEqual(avian.events.count("hsm_ver_regency.14"), 2)
        world.advance_days(1)
        self.assertTrue(world.deliver("hsm_ver_regency.14", "AVI"))
        world.choose("hsm_ver_regency.14", 0, "AVI")
        self.assertEqual(avian.leader, GROVER)

    def test_inter_house_war_cancels_pending_appointment_not_just_pauses_it(self):
        world = RegencyWorld()
        world.agreement()
        world.date = datetime.date(1021, 5, 22)
        world.daily()
        world.war_between("AVI", "EYR")
        avian = world.countries["AVI"]
        self.assertNotIn("HSM_VER_REG_majority_due", avian.flags)
        world.end_wars()
        world.charter()
        avian.flags.add("HSM_VER_congress_observer")
        world.apply("HSM_VER_offer_avian_charter", "AVI")
        world.choose("hsm_verenia.63", 0, "AVI")
        world.daily()
        world.choose("hsm_ver_regency.14", 0, "AVI")
        self.assertTrue(world.regtest("context"))
        self.assertEqual(avian.leader, KATRINA)
        self.assertEqual(world.character_actions, [])

    def test_accepted_regency_ending_never_becomes_a_false_expired_proposal(self):
        for reason in ("death", "custody", "government", "majority"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.agreement()
                avian = world.countries["AVI"]
                if reason == "death":
                    world.global_flags.add(DEAD)
                elif reason == "custody":
                    world.local_child("CYA")
                elif reason == "government":
                    avian.leader = "other_government"
                else:
                    world.date = datetime.date(1021, 5, 22)
                for _ in range(3):
                    world.daily()
                world.advance_days(100)
                world.daily()
                self.assertNotIn("hsm_ver_regency.15", avian.events)
                self.assertNotIn("HSM_VER_REG_refused", avian.flags)

    def test_majority_after_not_on_may_21_and_constitutional_appointment_once(self):
        world = RegencyWorld()
        world.agreement()
        avian = world.countries["AVI"]
        world.date = datetime.date(1021, 5, 21)
        world.daily()
        self.assertIn("HSM_VER_REG_regency", avian.flags)
        self.assertIn("HSM_VER_REG_joint_guardianship", avian.ideas)
        self.assertEqual(avian.leader, KATRINA)
        world.advance_days(1)
        world.daily()
        self.assertNotIn("HSM_VER_REG_regency", avian.flags)
        self.assertNotIn("HSM_VER_REG_joint_guardianship", avian.ideas)
        self.assertIn("HSM_VER_REG_majority_due", avian.flags)
        world.advance_days(1)
        self.assertTrue(world.deliver("hsm_ver_regency.14", "AVI"))
        world.choose("hsm_ver_regency.14", 0, "AVI")
        world.choose("hsm_ver_regency.14", 0, "AVI")
        self.assertEqual(avian.leader, GROVER)
        self.assertEqual(avian.roles[GROVER].get("ideology"), "constitutional_monarchism")
        self.assertEqual(avian.government, IDEOLOGY_GROUPS["constitutional_monarchism"])
        self.assertEqual(avian.government, "neutrality")
        self.assertEqual(len(world.character_actions), 1)
        self.assertIn("Grover_VI_good.tga", str(world.portraits[GROVER]))
        world.daily()
        self.assertTrue(world.regtest("successor_government"))
        self.assertTrue(world.regtest("agreement_live"))
        self.assertTrue(world.test("HSM_VER_AVI_government_available"))
        self.assertTrue(all("HSM_AVI_common_budget" in world.countries[t].ideas for t in HOUSES))

    def test_majority_ends_guardianship_even_during_foreign_war(self):
        world = RegencyWorld()
        world.agreement()
        world.join_defence("FLO", "AVI")
        world.date = datetime.date(1021, 5, 22)
        world.daily()
        avian = world.countries["AVI"]
        self.assertNotIn("HSM_VER_REG_regency", avian.flags)
        self.assertNotIn("HSM_VER_REG_joint_guardianship", avian.ideas)
        self.assertIn("HSM_VER_REG_majority_due", avian.flags)
        self.assertEqual(avian.leader, KATRINA)

    def test_minor_regency_occupation_pauses_without_ending_or_changing_custody(self):
        world = RegencyWorld()
        world.agreement()
        avian = world.countries["AVI"]
        for tag in HOUSES:
            with self.subTest(occupied=tag):
                world.countries[tag].capitulated = True
                world.daily()
                self.assertNotIn("HSM_VER_REG_joint_guardianship", avian.ideas)
                self.assertIn("HSM_VER_REG_regency", avian.flags)
                self.assertIn(GROVER, avian.characters)
                world.countries[tag].capitulated = False
                world.daily()
                self.assertIn("HSM_VER_REG_joint_guardianship", avian.ideas)
        self.assertEqual(world.character_actions, [])

    def test_party_change_with_katrina_still_leading_cannot_certify_false_majority(self):
        for party in ("democratic", "fascism"):
            with self.subTest(party=party):
                world = RegencyWorld()
                world.agreement()
                avian = world.countries["AVI"]
                world.run(BASE["parse"]("set_politics = { ruling_party = " + party + " }"))
                self.assertEqual(avian.leader, KATRINA)
                world.date = datetime.date(1021, 5, 22)
                world.daily()
                world.choose("hsm_ver_regency.14", 0, "AVI")
                self.assertNotIn("HSM_VER_REG_majority", avian.flags)
                self.assertNotIn("HSM_VER_REG_majority_due", avian.flags)
                self.assertEqual(avian.government, party)
                self.assertEqual(world.character_actions, [])

    def test_death_custody_and_government_changes_end_regency_without_resurrection(self):
        for reason in ("death", "custody", "government", "ball", "communist", "loyalist", "fascist"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.agreement()
                avian = world.countries["AVI"]
                if reason == "death":
                    world.global_flags.add(DEAD)
                elif reason == "custody":
                    world.local_child("CYA")
                elif reason == "government":
                    avian.leader = "other_government"
                else:
                    avian.focuses.add({"ball": "the_second_winterfest_ball", "communist": "communists_win", "loyalist": "loyalists_win", "fascist": "fascists_win"}[reason])
                world.daily()
                self.assertNotIn("HSM_VER_REG_regency", avian.flags)
                self.assertNotIn("HSM_VER_REG_joint_guardianship", avian.ideas)
                self.assertIn("HSM_VER_REG_ended", avian.flags)
                avian.leader = KATRINA
                world.date = datetime.date(1021, 5, 22)
                world.daily()
                world.choose("hsm_ver_regency.14", 0, "AVI")
                self.assertNotEqual(avian.leader, GROVER)
                self.assertEqual(world.character_actions, [])

    def test_stale_majority_reply_revalidates_death_foreign_custody_and_government(self):
        for reason in ("death", "custody", "government", "subject", "ball"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.agreement()
                world.date = datetime.date(1021, 5, 22)
                world.daily()
                avian = world.countries["AVI"]
                if reason == "death":
                    world.global_flags.add(DEAD)
                elif reason == "custody":
                    world.local_child("CYA")
                elif reason == "government":
                    avian.leader = "other_government"
                elif reason == "subject":
                    avian.subject = True
                else:
                    avian.focuses.add("the_second_winterfest_ball")
                world.choose("hsm_ver_regency.14", 0, "AVI")
                world.daily()
                self.assertNotEqual(avian.leader, GROVER)
                self.assertEqual(world.character_actions, [])
                if reason != "subject":
                    avian.leader = KATRINA
                    world.local_child()
                    world.daily()
                    world.choose("hsm_ver_regency.14", 0, "AVI")
                    self.assertEqual(world.character_actions, [])

    def test_unrecorded_grover_leader_does_not_keep_avian_government_or_budget(self):
        world = RegencyWorld()
        world.context()
        world.local_child()
        world.date = datetime.date(1021, 5, 22)
        world.countries["AVI"].leader = GROVER
        self.assertFalse(world.regtest("successor_government"))
        self.assertFalse(world.test("HSM_VER_AVI_government_available"))
        world.daily()
        for tag in HOUSES:
            self.assertNotIn("HSM_AVI_budget_signed", world.countries[tag].flags)
            self.assertNotIn("HSM_AVI_common_budget", world.countries[tag].ideas)

    def test_lost_adult_successor_with_katrina_returning_requires_fresh_civil_consent(self):
        for reason in ("death", "foreign_custody", "replacement"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.context()
                world.local_child()
                world.reward_reg("agreement_for_herzland")
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_regency.3", "AVI"))
                world.choose("hsm_ver_regency.3", 0, "AVI")
                world.choose("hsm_ver_regency.10", 0, "ERI")
                world.choose("hsm_ver_regency.10", 0, "EYR")
                world.reward_reg("schools_and_witnesses")
                world.choose("hsm_ver_regency.4", 0, "AVI")
                world.reward_reg("defence_articles")
                world.choose("hsm_ver_regency.5", 0, "AVI")
                world.reward_reg("petitions_to_the_council")
                world.choose("hsm_ver_regency.6", 0, "AVI")
                world.reward_reg("reserved_house_rights")
                world.date = datetime.date(1021, 5, 22)
                world.daily()
                world.choose("hsm_ver_regency.14", 0, "AVI")
                world.advance_days(90)
                avian = world.countries["AVI"]
                self.assertTrue(world.regtest("successor_government"))
                self.assertTrue(world.regtest("agreement_live"))
                self.assertTrue(world.available_reg("a_finite_guardianship"))
                self.assertFalse(world.regtest("can_propose"))
                self.assertIn("HSM_VER_REG_reserved_rights", avian.ideas)
                self.assertIn("HSM_VER_REG_joint_logistics", avian.ideas)
                actions = list(world.character_actions)

                if reason == "death":
                    world.global_flags.add(DEAD)
                elif reason == "foreign_custody":
                    world.local_child("CYA")
                avian.leader = KATRINA
                avian.party_leaders["neutrality"] = KATRINA
                world.daily()
                self.assertIn("HSM_VER_REG_majority", avian.flags)
                self.assertFalse(world.regtest("successor_government"))
                self.assertFalse(world.regtest("agreement_live"))
                self.assertFalse(world.available_reg("a_finite_guardianship"))
                self.assertFalse(any(idea.startswith("HSM_VER_REG_") for idea in avian.ideas))
                self.assertTrue(world.regtest("can_propose"))
                self.assertNotIn("hsm_ver_regency.15", avian.events)

                world.decision_reg("reconsider_agreement", True)
                world.choose("hsm_ver_regency.3", 1, "AVI")
                for tag in ("ERI", "EYR"):
                    self.assertNotIn("HSM_VER_REG_signed", world.countries[tag].flags)
                self.assertFalse(world.regtest("agreement_live"))
                world.choose("hsm_ver_regency.10", 0, "ERI")
                self.assertFalse(world.regtest("agreement_live"))
                world.choose("hsm_ver_regency.10", 0, "EYR")
                self.assertTrue(world.regtest("agreement_live"))
                self.assertIn("HSM_VER_REG_civil_settlement", avian.ideas)
                self.assertFalse(world.available_reg("a_finite_guardianship"))
                self.assertTrue(world.available_reg("a_union_without_a_throne"))
                self.assertEqual(world.character_actions, actions)
                self.assertEqual(avian.leader, KATRINA)

    def test_terminated_regency_can_request_civil_compact_without_automatic_assent(self):
        world = RegencyWorld()
        world.agreement()
        world.local_child("CYA")
        world.daily()
        world.advance_days(90)
        world.decision_reg("reconsider_agreement", True)
        world.choose("hsm_ver_regency.3", 1, "AVI")
        self.assertFalse(world.regtest("agreement_live"))
        for tag in ("ERI", "EYR"):
            self.assertNotIn("HSM_VER_REG_signed", world.countries[tag].flags)
            world.choose("hsm_ver_regency.10", 0, tag)
        self.assertTrue(world.regtest("agreement_live"))
        self.assertIn("HSM_VER_REG_compact", world.countries["AVI"].flags)
        self.assertIn(GROVER, world.countries["CYA"].characters)
        self.assertEqual(world.character_actions, [])


class RewardsAndNarrative(unittest.TestCase):
    def test_daily_refresh_does_not_reapply_existing_regency_ideas(self):
        world = RegencyWorld()
        world.agreement()
        world.reward_reg("reserved_house_rights")
        world.reward_reg("defence_articles")
        world.choose("hsm_ver_regency.5", 0, "AVI")
        world.idea_actions.clear()
        for _ in range(3):
            world.daily()
        self.assertEqual([item for item in world.idea_actions if item[1].startswith("HSM_VER_REG_")], [])

    def test_civilian_factory_is_griffenheim_only_once_and_fallback_is_once(self):
        for capacity in (0, 20):
            with self.subTest(capacity=capacity):
                world = RegencyWorld()
                world.context()
                world.state_ids["382"].capacity = capacity
                world.reward_reg("civilian_contracts")
                world.reg("build_city")
                other_states = [s for key, s in world.state_ids.items() if key != "382"]
                self.assertTrue(all(not s.buildings and not s.extra_slots for s in other_states))
                if capacity:
                    self.assertEqual(world.state_ids["382"].buildings, {"industrial_complex": 1})
                    self.assertEqual(world.state_ids["382"].extra_slots, 1)
                else:
                    self.assertEqual(len(world.countries["AVI"].bonuses), 1)
                    bonus = Node("bonus", "=", world.countries["AVI"].bonuses[0])
                    self.assertEqual((bonus.get("category"), bonus.get("bonus"), bonus.get("uses")), ("industry", "1", "2"))

    def test_factory_never_builds_in_foreign_owned_or_occupied_griffenheim(self):
        world = RegencyWorld()
        world.context()
        for attribute in ("owner", "controller"):
            setattr(world.state_ids["382"], attribute, "CYA")
            world.reg("build_city")
            self.assertNotIn("HSM_VER_REG_city_built", world.countries["AVI"].flags)
            self.assertFalse(world.state_ids["382"].buildings)
            setattr(world.state_ids["382"], attribute, "AVI")

    def test_policy_choices_never_stack_or_replay(self):
        for option, idea in ((0, "HSM_VER_REG_joint_logistics"), (1, "HSM_VER_REG_territorial_reserves")):
            with self.subTest(option=option):
                world = RegencyWorld()
                world.agreement()
                world.reward_reg("defence_articles")
                world.choose("hsm_ver_regency.5", option, "AVI")
                world.choose("hsm_ver_regency.5", 1 - option, "AVI")
                world.daily()
                self.assertEqual(world.countries["AVI"].ideas & {"HSM_VER_REG_joint_logistics", "HSM_VER_REG_territorial_reserves"}, {idea})

    def test_missed_domestic_scenes_retry_without_repeating_focus_rewards(self):
        for suffix, event_id, seen in (("agreement_for_herzland", "3", "proposal_seen"), ("schools_and_witnesses", "4", "school_seen"), ("defence_articles", "5", "defence_resolved"), ("petitions_to_the_council", "6", "petition_seen")):
            with self.subTest(scene=event_id):
                world = RegencyWorld()
                if event_id == "3":
                    world.context()
                    world.local_child()
                else:
                    world.agreement()
                if event_id == "6":
                    world.reward_reg("schools_and_witnesses")
                    world.choose("hsm_ver_regency.4", 0, "AVI")
                    world.reward_reg("defence_articles")
                    world.choose("hsm_ver_regency.5", 0, "AVI")
                world.reward_reg(suffix)
                avian = world.countries["AVI"]
                bonus_count = len(avian.bonuses)
                avian.capitulated = True
                world.advance_days(1)
                self.assertFalse(world.deliver("hsm_ver_regency." + event_id, "AVI"))
                world.choose("hsm_ver_regency." + event_id, 0, "AVI")
                self.assertNotIn("HSM_VER_REG_" + seen, avian.flags)
                avian.capitulated = False
                for _ in range(3):
                    world.daily()
                self.assertEqual(avian.events.count("hsm_ver_regency." + event_id), 1)
                world.advance_days(44)
                world.daily()
                self.assertEqual(avian.events.count("hsm_ver_regency." + event_id), 2)
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_regency." + event_id, "AVI"))
                world.choose("hsm_ver_regency." + event_id, 0, "AVI")
                self.assertIn("HSM_VER_REG_" + seen, avian.flags)
                self.assertEqual(len(avian.bonuses), bonus_count)

    def test_factual_household_descriptions_have_one_matching_variant(self):
        for status in ("minor", "adult", "dead", "foreign", "unknown"):
            with self.subTest(status=status):
                world = RegencyWorld()
                world.context()
                world.local_child("CYA" if status == "foreign" else "AVI")
                if status == "adult":
                    world.date = datetime.date(1021, 5, 22)
                elif status == "dead":
                    world.global_flags.add(DEAD)
                elif status == "unknown":
                    world.countries["AVI"].characters.discard(GROVER)
                self.assertEqual(world.descriptions("hsm_ver_regency.2"), ["hsm_ver_regency.2." + status + ".d"])

    def test_child_scenes_only_record_memories_for_actual_living_local_minor(self):
        for child in (True, False):
            with self.subTest(child=child):
                world = RegencyWorld()
                world.agreement("regency" if child else "civil")
                for event_id, flag in (("4", "school"), ("6", "petition")):
                    self.assertEqual(world.descriptions("hsm_ver_regency." + event_id), ["hsm_ver_regency." + event_id + (".child.d" if child else ".d")])
                    world.choose("hsm_ver_regency." + event_id, 0, "AVI")
                    world.choose("hsm_ver_regency." + event_id, 0, "AVI")
                    self.assertEqual("HSM_VER_REG_" + flag + "_memory" in world.countries["AVI"].flags, child)
                self.assertEqual(world.descriptions("hsm_ver_regency.14"), ["hsm_ver_regency.14.memory.d" if child else "hsm_ver_regency.14.d"])


class Integration(unittest.TestCase):
    def test_twelve_absolute_foci_only_in_initial_native_tree(self):
        world = RegencyWorld()
        focuses = {key: n for key, n in world.focuses.items() if key.startswith("HSM_VER_REG_")}
        self.assertEqual(set(focuses), {"HSM_VER_REG_" + suffix for suffix in LAYOUT})
        for suffix, position in LAYOUT.items():
            focus = focuses["HSM_VER_REG_" + suffix]
            self.assertFalse(focus.all("relative_position_id"))
            self.assertEqual((int(focus.get("x")), int(focus.get("y"))), position)
        imported = [n.get("id") for n in read(MOD / "common/national_focus/AVI.txt") if n.key == "focus_tree" and any(x.value == "HSM_VER_REG_after_defence" for x in n.all("shared_focus"))]
        self.assertEqual(imported, ["avian"])

    def test_all_new_events_bound_response_windows_and_references_exist(self):
        world = RegencyWorld()
        events = {key: n for key, n in world.events.items() if key.startswith("hsm_ver_regency.")}
        self.assertEqual(set(events), {f"hsm_ver_regency.{n}" for n in range(1, 18)})
        for key, event in events.items():
            self.assertEqual(event.get("timeout_days"), "13", key)
        for path in MOD.rglob("HSM_VER_regency.txt"):
            for node in walk(read(path)):
                if node.key == "country_event" and node.get("id"):
                    self.assertIn(node.get("id"), world.events)

    def test_both_finales_reach_settlement_without_waiting_for_age(self):
        for kind, unified in itertools.product(("regency", "civil"), (False, True)):
            with self.subTest(kind=kind, unified=unified):
                world = RegencyWorld()
                world.agreement(kind)
                if unified:
                    world.unify()
                    world.reg("maintain")
                    for event in (16, 17):
                        world.choose(f"hsm_ver_regency.{event}", 0, "AVI")
                avian = world.countries["AVI"]
                for suffix in ("schools_and_witnesses", "defence_articles"):
                    self.assertTrue(world.available_reg(suffix))
                    world.reward_reg(suffix)
                world.choose("hsm_ver_regency.4", 0, "AVI")
                world.choose("hsm_ver_regency.5", 0, "AVI")
                self.assertTrue(world.available_reg("petitions_to_the_council"))
                world.reward_reg("petitions_to_the_council")
                world.choose("hsm_ver_regency.6", 0, "AVI")
                for suffix in ("rebuilding_the_quarters", "reserved_house_rights"):
                    self.assertTrue(world.available_reg(suffix))
                    world.reward_reg(suffix)
                finale = "a_finite_guardianship" if kind == "regency" else "a_union_without_a_throne"
                self.assertTrue(world.available_reg(finale))
                world.reward_reg(finale)
                world.reward_reg("the_settled_frontier")
                self.assertIn("HSM_VER_REG_settlement_finished", avian.flags)
                self.assertEqual(avian.army_experience, 25)
                self.assertEqual(len(avian.bonuses), 2)
                self.assertEqual(avian.leader, KATRINA)
                self.assertTrue(all(not world.countries[tag].subject for tag in HOUSES))


class UnifiedSettlement(unittest.TestCase):
    def test_two_local_estate_votes_execute_real_regency_and_civil_rewards(self):
        for kind, order in itertools.product(("regency", "civil"), ((16, 17), (17, 16))):
            with self.subTest(kind=kind, order=order):
                world = RegencyWorld()
                world.estate_proposal(kind)
                avian = world.countries["AVI"]
                for tag in ("ERI", "EYR"):
                    self.assertNotIn("hsm_ver_regency.10", world.countries[tag].events)
                    world.reg("sign", tag)
                    self.assertNotIn("HSM_VER_REG_signed", world.countries[tag].flags)
                world.advance_days(1)
                self.assertTrue(world.deliver(f"hsm_ver_regency.{order[0]}", "AVI"))
                world.choose(f"hsm_ver_regency.{order[0]}", 0, "AVI")
                self.assertFalse(world.regtest("agreement_live"))
                world.choose(f"hsm_ver_regency.{order[1]}", 0, "AVI")
                self.assertTrue(world.regtest("agreement_live"))
                expected = "HSM_VER_REG_joint_guardianship" if kind == "regency" else "HSM_VER_REG_civil_settlement"
                self.assertIn(expected, avian.ideas)
                world.reg("build_city")
                world.reg("build_city")
                self.assertEqual(world.state_ids["382"].buildings.get("industrial_complex"), 1)
                world.reward_reg("schools_and_witnesses")
                self.assertEqual(len(avian.bonuses), 1)
                self.assertEqual(world.character_actions, [])
                before = copy.deepcopy(world.countries)
                for event in (16, 17):
                    world.choose(f"hsm_ver_regency.{event}", 0, "AVI")
                self.assertEqual(world.countries, before)

    def test_partial_absorption_requires_one_foreign_and_one_local_vote(self):
        for absorbed, event, live in (("ERI", 16, "EYR"), ("EYR", 17, "ERI")):
            with self.subTest(absorbed=absorbed):
                world = RegencyWorld()
                world.estate_proposal("civil", (absorbed,))
                self.assertNotIn("hsm_ver_regency.10", world.countries[absorbed].events)
                self.assertIn("hsm_ver_regency.10", world.countries[live].events)
                world.choose(f"hsm_ver_regency.{event}", 0, "AVI")
                self.assertFalse(world.regtest("agreement_live"))
                world.choose("hsm_ver_regency.10", 0, live)
                self.assertTrue(world.regtest("agreement_live"))
                self.assertNotIn("HSM_VER_REG_signed", world.countries[absorbed].flags)

    def test_existing_foreign_agreement_requires_new_estate_assent_after_absorption(self):
        world = RegencyWorld()
        world.agreement()
        world.unify()
        world.reg("maintain")
        self.assertNotIn("HSM_VER_REG_joint_guardianship", world.countries["AVI"].ideas)
        for event in (16, 17):
            world.choose(f"hsm_ver_regency.{event}", 0, "AVI")
        self.assertTrue(world.regtest("agreement_live"))
        self.assertIn("HSM_VER_REG_joint_guardianship", world.countries["AVI"].ideas)
        world.date = datetime.date(1021, 5, 22)
        world.reg("maintain")
        world.choose("hsm_ver_regency.14", 0, "AVI")
        self.assertEqual(world.countries["AVI"].leader, GROVER)
        self.assertTrue(world.regtest("successor_government"))

    def test_pending_foreign_votes_switch_to_local_hearings_after_absorption(self):
        world = RegencyWorld()
        world.proposal()
        world.unify()
        world.reg("maintain")
        for tag in ("ERI", "EYR"):
            world.choose("hsm_ver_regency.10", 0, tag)
            self.assertNotIn("HSM_VER_REG_signed", world.countries[tag].flags)
        for event in (16, 17):
            world.choose(f"hsm_ver_regency.{event}", 0, "AVI")
        self.assertTrue(world.regtest("agreement_live"))

    def test_refusal_expiry_and_retry_are_explicit_without_a_substitute_compact(self):
        for refusal in (True, False):
            with self.subTest(refusal=refusal):
                world = RegencyWorld()
                world.estate_proposal()
                world.choose("hsm_ver_regency.16", 0, "AVI")
                if refusal:
                    world.choose("hsm_ver_regency.17", 1, "AVI")
                world.advance_days(45)
                world.reg("maintain")
                world.choose("hsm_ver_regency.17", 0, "AVI")
                avian = world.countries["AVI"]
                self.assertFalse(world.regtest("agreement_live"))
                self.assertFalse(avian.flags & {"HSM_VER_REG_regency", "HSM_VER_REG_compact"})
                self.assertFalse(world.regtest("can_propose"))
                world.advance_days(45)
                world.reg("propose_civil")
                for event in (16, 17):
                    world.choose(f"hsm_ver_regency.{event}", 0, "AVI")
                self.assertTrue(world.regtest("agreement_live"))
                self.assertIn("HSM_VER_REG_civil_settlement", avian.ideas)

    def test_stale_estate_votes_cannot_grant_benefits_or_custody(self):
        for reason in ("death", "adult", "foreign_custody", "released", "subject", "capitulated", "no_founding", "no_absorption", "no_history", "war"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.estate_proposal()
                avian = world.countries["AVI"]
                if reason == "death":
                    world.global_flags.add(DEAD)
                elif reason == "adult":
                    world.date = datetime.date(1021, 5, 22)
                elif reason == "foreign_custody":
                    world.local_child("CYA")
                elif reason == "released":
                    world.countries["ERI"].exists = True
                elif reason == "subject":
                    avian.subject = True
                elif reason == "capitulated":
                    avian.capitulated = True
                elif reason == "no_founding":
                    avian.flags.remove("HSM_VER_UNI_founded")
                elif reason == "no_absorption":
                    avian.flags.remove("HSM_VER_UNI_absorbed_ERI")
                elif reason == "no_history":
                    world.countries["ERI"].flags.remove("HSM_VER_treaty_signed")
                else:
                    world.join_defence("FLO", "AVI")
                for event in (16, 17):
                    world.choose(f"hsm_ver_regency.{event}", 0, "AVI")
                self.assertFalse(world.regtest("agreement_live"))
                self.assertNotIn("HSM_VER_REG_regency", avian.flags)
                self.assertEqual(world.character_actions, [])

    def test_all_ducal_land_owner_controller_losses_remove_actual_ideas(self):
        for state_id, attribute in itertools.product((*DUCAL, "470"), ("owner", "controller")):
            with self.subTest(state=state_id, attribute=attribute):
                world = RegencyWorld()
                world.estate_proposal("civil")
                for event in (16, 17):
                    world.choose(f"hsm_ver_regency.{event}", 0, "AVI")
                world.choose("hsm_ver_regency.6", 0, "AVI")
                world.reward_reg("reserved_house_rights")
                self.assertIn("HSM_VER_REG_reserved_rights", world.countries["AVI"].ideas)
                setattr(world.state_ids[state_id], attribute, "CYA")
                world.reg("maintain")
                self.assertFalse(world.regtest("context"))
                self.assertFalse(world.countries["AVI"].ideas & {"HSM_VER_REG_civil_settlement", "HSM_VER_REG_reserved_rights"})
                world.reg("build_city")
                self.assertFalse(world.state_ids["382"].buildings)

    def test_foreign_annexation_release_cannot_reuse_host_founding(self):
        world = RegencyWorld()
        world.context()
        world.unify()
        # Execute only the production hook owning this invalidation contract.
        actions = read(MOD / "common/on_actions/HSM_VER_imperial.txt")[0]
        world.root, world.sender = "CYA", "AVI"
        world.run(next(n for n in actions.children if n.key == "on_annex").get("effect"), "CYA")
        self.assertIn("HSM_VER_IMP_union_dispossessed", world.countries["AVI"].flags)
        self.assertFalse(world.regtest("context"))
        world.reg("build_city")
        self.assertFalse(world.state_ids["382"].buildings)

    def test_focus_completion_rechecks_conditions_before_any_reward(self):
        for suffix in LAYOUT:
            with self.subTest(focus=suffix):
                world = RegencyWorld()
                world.estate_proposal("civil")
                for event in (16, 17):
                    world.choose(f"hsm_ver_regency.{event}", 0, "AVI")
                avian = world.countries["AVI"]
                avian.flags.update({"HSM_VER_REG_school_seen", "HSM_VER_REG_petition_seen", "HSM_VER_REG_defence_resolved"})
                world.state_ids["391"].controller = "CYA"
                before = (copy.deepcopy(avian.flags), copy.deepcopy(avian.ideas),
                          copy.deepcopy(avian.bonuses), avian.army_experience,
                          copy.deepcopy(world.state_ids["382"].buildings), list(world.scheduled))
                world.reward_reg(suffix)
                after = (avian.flags, avian.ideas, avian.bonuses, avian.army_experience,
                         world.state_ids["382"].buildings, world.scheduled)
                self.assertEqual(before, after)
                self.assertEqual(world.focuses["HSM_VER_REG_" + suffix].get("cancel_if_invalid"), "yes")

    def test_unified_defender_requires_actual_gri_attack_capitulation_and_conference(self):
        for defensive in (True, False):
            with self.subTest(defensive=defensive):
                world = RegencyWorld()
                world.budget()
                avian = world.countries["AVI"]
                avian.flags.add("HSM_AVI_settlement_completed")
                world.unify()
                if defensive:
                    world.hook("on_declare_war", "GRI", "AVI")
                    world.join_defence("GRI", "AVI")
                else:
                    world.hook("on_declare_war", "AVI", "GRI")
                    world.join_defence("AVI", "GRI")
                world.certify_victory()
                world.advance_days(45)
                self.assertEqual(world.regtest("context"), defensive)
                self.assertEqual("HSM_VER_REG_peace" in avian.flags, defensive)
                world.reg("build_city")
                self.assertEqual(bool(world.state_ids["382"].buildings), defensive)

    def test_no_charter_no_defensive_certificate_or_no_absorption_means_no_settlement(self):
        for tag, flag in (("ERI", "HSM_VER_treaty_signed"), ("EYR", "HSM_VER_treaty_signed"),
                          *((t, "HSM_VER_charter_signed") for t in HOUSES),
                          *(("AVI", "HSM_VER_REG_" + proof) for proof in ("defensive_war", "defeat", "peace")),
                          ("AVI", "HSM_VER_UNI_absorbed_ERI"), ("AVI", "HSM_VER_UNI_absorbed_EYR")):
            with self.subTest(tag=tag, flag=flag):
                world = RegencyWorld()
                world.context()
                world.unify()
                world.countries[tag].flags.remove(flag)
                self.assertFalse(world.regtest("context"))
                world.reg("build_city")
                self.assertFalse(world.state_ids["382"].buildings)

    def test_later_avian_admission_receipts_cannot_replace_avian_host_charter(self):
        for proof in ("HSM_VER_FORCE_AVI_integrated", "HSM_VER_AVR_ratified"):
            with self.subTest(proof=proof):
                world = RegencyWorld()
                world.context()
                world.unify()
                avian = world.countries["AVI"]
                avian.flags.add(proof)
                avian.flags.remove("HSM_VER_charter_signed")
                world.reg("build_city")
                self.assertFalse(world.regtest("context"))
                self.assertFalse(world.state_ids["382"].buildings)

    def test_absorbed_house_character_residue_never_becomes_custody(self):
        world = RegencyWorld()
        world.context()
        world.local_child("ERI")
        world.unify()
        world.reg("request_household")
        world.reg("recover_household")
        world.reg("receive_household", "ERI")
        self.assertEqual(world.character_actions, [])
        self.assertNotIn(GROVER, world.countries["AVI"].characters)
        self.assertNotIn("hsm_ver_regency.12", world.countries["ERI"].events)
        self.assertFalse(world.regtest("local_minor"))

    def test_localisation_bom_parity_references_and_timed_flag_values(self):
        keys = {}
        for language in ("english", "russian"):
            path = MOD / f"localisation/{language}/HSM_VER_regency_l_{language}.yml"
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            lines = path.read_text(encoding="utf-8-sig").splitlines()[1:]
            entries = [re.fullmatch(r' ([A-Za-z0-9_.]+):0 "(?:\\.|[^"\\])*"', line) for line in lines if line.strip()]
            self.assertTrue(all(entries))
            keys[language] = {entry[1] for entry in entries}
            self.assertEqual(len(keys[language]), len(entries))
        self.assertEqual(keys["english"], keys["russian"])
        for path in MOD.rglob("HSM_VER_regency.txt"):
            for node in walk(read(path)):
                if node.key in ("title", "desc", "text", "name", "custom_effect_tooltip", "tooltip") and isinstance(node.value, str) and node.value.startswith(("HSM_VER_REG_", "hsm_ver_regency.")):
                    self.assertIn(node.value, keys["english"])
                if node.key == "set_country_flag" and node.children:
                    self.assertEqual(node.get("value"), "1")


class Harness(unittest.TestCase):
    def test_unknown_operations_fail_closed(self):
        world = RegencyWorld()
        with self.assertRaisesRegex(AssertionError, "no predicate"):
            world.check([Node("unsupported_regency_predicate", "=", "yes")])
        with self.assertRaisesRegex(AssertionError, "no effect"):
            world.run([Node("unsupported_regency_effect", "=", "yes")])

    def test_scoped_original_core_loop_checks_every_state(self):
        world = RegencyWorld()
        predicate = BASE["parse"]("all_of_scopes = { array = GRI.original_cores owner = { tag = AVI } is_fully_controlled_by = AVI }")
        self.assertTrue(world.check(predicate))
        world.arrays["GRI.original_cores"][1].controller = "CYA"
        self.assertFalse(world.check(predicate))

    def test_strict_date_boundary(self):
        world = RegencyWorld()
        world.date = datetime.date(1021, 5, 21)
        predicate = [Node("date", ">", "1021.5.21")]
        self.assertFalse(world.check(predicate))
        world.advance_days(1)
        self.assertTrue(world.check(predicate))


class HerzlandScopes(unittest.TestCase):
    def test_arrays_exactly_match_native_herzland_definition(self):
        world = RegencyWorld()
        native = next(n for n in read(OPT.eaw / "common/scripted_effects/00_scripted_effects.txt") if n.key == "core_all_herzland_states")
        expected = {n.value for n in walk(native.children) if n.key == "array"}
        actual = [n.value for n in walk(world.triggers["HSM_VER_REG_herzland_held"]) if n.key == "array"]
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(expected))

    def test_every_original_core_requires_acceptable_owner_and_controller(self):
        world = RegencyWorld()
        world.context()
        for array, states in world.arrays.items():
            for index, state in enumerate(states):
                for attribute in ("owner", "controller"):
                    with self.subTest(array=array, index=index, attribute=attribute):
                        setattr(state, attribute, "CYA")
                        self.assertFalse(world.regtest("herzland_held"))
                        setattr(state, attribute, "AVI")
                        self.assertTrue(world.regtest("herzland_held"))

    def test_subjects_and_only_independent_actual_house_partners_are_eligible(self):
        world = RegencyWorld()
        world.context()
        state = world.arrays["BRZ.original_cores"][1]
        for holder in ("ERI", "EYR", "FLO"):
            country = world.countries[holder]
            for attribute in ("owner", "controller"):
                setattr(state, attribute, holder)
                self.assertEqual(world.regtest("herzland_held"), holder != "FLO")
                country.subject, country.overlord = True, "AVI"
                self.assertTrue(world.regtest("herzland_held"))
                country.overlord = "CYA"
                self.assertFalse(world.regtest("herzland_held"))
                country.subject, country.overlord = False, ""
                if holder in ("ERI", "EYR"):
                    country.flags.remove("HSM_VER_charter_signed")
                    self.assertFalse(world.regtest("herzland_held"))
                    country.flags.add("HSM_VER_charter_signed")
                setattr(state, attribute, "AVI")

    def test_griffenheim_must_be_personally_owned_and_controlled_by_avian(self):
        world = RegencyWorld()
        world.context()
        for attribute in ("owner", "controller"):
            setattr(world.state_ids["382"], attribute, "ERI")
            self.assertTrue(world.regtest("herzland_held"))
            self.assertFalse(world.regtest("context"))
            setattr(world.state_ids["382"], attribute, "AVI")


class Custody(unittest.TestCase):
    def test_previous_house_transfer_cannot_be_repeated_after_native_custody_changes(self):
        for later_host in ("ERI", "EYR", "GRI"):
            with self.subTest(later_host=later_host):
                world = RegencyWorld()
                world.context()
                world.local_child("ERI")
                world.reg("request_household")
                world.choose("hsm_ver_regency.12", 0, "ERI")
                self.assertIn("HSM_VER_REG_household_received", world.countries["AVI"].flags)
                world.local_child(later_host)
                if later_host == "GRI":
                    world.countries["GRI"].exists = False
                world.advance_days(90)
                world.reg("request_household")
                world.reg("recover_household")
                if later_host != "GRI":
                    world.choose("hsm_ver_regency.12", 0, later_host)
                self.assertEqual(world.character_actions, [("set_nationality", GROVER, "ERI", "AVI")])
                self.assertIn(GROVER, world.countries[later_host].characters)

    def test_idea_is_not_character_and_death_overrides_local_residue(self):
        world = RegencyWorld()
        world.context()
        world.countries["AVI"].ideas.add("GRI_grover_vi")
        self.assertFalse(world.regtest("local_minor"))
        world.local_child()
        self.assertTrue(world.regtest("local_minor"))
        world.global_flags.add(DEAD)
        for predicate in ("local_minor", "local_adult", "foreign_household", "can_recover_household"):
            self.assertFalse(world.regtest(predicate), predicate)

    def test_minor_boundary_and_existing_reigning_character(self):
        world = RegencyWorld()
        world.context()
        world.local_child()
        for day, minor in ((20, True), (21, True), (22, False)):
            world.date = datetime.date(1021, 5, day)
            self.assertEqual(world.regtest("local_minor"), minor)
            self.assertEqual(world.regtest("local_adult"), not minor)
        world.date = datetime.date(1020, 1, 1)
        world.countries["AVI"].leader = GROVER
        self.assertFalse(world.regtest("minor"))

    def test_recover_annexed_original_gri_strictly_once_without_recruiting(self):
        world = RegencyWorld()
        world.context()
        world.countries["GRI"].exists = False
        self.assertTrue(world.regtest("can_recover_household"))
        world.reg("recover_household")
        world.reg("recover_household")
        self.assertEqual(world.character_actions, [("set_nationality", GROVER, "GRI", "AVI")])
        self.assertNotIn(GROVER, world.countries["GRI"].characters)
        self.assertIn(GROVER, world.countries["AVI"].characters)

    def test_recovery_rejects_live_foreign_dead_adult_ruling_and_missing_character(self):
        for reason in ("gri_alive", "foreign_cya", "foreign_house", "dead", "adult", "ruling", "absent"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.context()
                gri = world.countries["GRI"]
                gri.exists = False
                if reason == "gri_alive":
                    gri.exists = True
                elif reason.startswith("foreign"):
                    world.countries["CYA" if reason == "foreign_cya" else "ERI"].characters.add(GROVER)
                elif reason == "dead":
                    world.global_flags.add(DEAD)
                elif reason == "adult":
                    world.date = datetime.date(1021, 5, 22)
                elif reason == "ruling":
                    gri.leader = GROVER
                else:
                    gri.characters.clear()
                world.reg("recover_household")
                self.assertEqual(world.character_actions, [])
                self.assertNotIn(GROVER, world.countries["AVI"].characters)

    def test_recovery_needs_every_original_gri_core_personally_owned_and_controlled(self):
        world = RegencyWorld()
        world.context()
        world.countries["GRI"].exists = False
        for state in world.arrays["GRI.original_cores"]:
            for attribute in ("owner", "controller"):
                setattr(state, attribute, "ERI")
                self.assertFalse(world.regtest("can_recover_household"))
                setattr(state, attribute, "AVI")

    def test_house_transfer_requires_explicit_reply_and_cannot_repeat(self):
        for host in ("ERI", "EYR"):
            with self.subTest(host=host):
                world = RegencyWorld()
                world.context()
                world.local_child(host)
                world.reg("request_household")
                self.assertNotIn(GROVER, world.countries["AVI"].characters)
                self.assertIn("HSM_VER_REG_custody_pending", world.countries[host].flags)
                packets = list(world.scheduled)
                world.reg("request_household")
                self.assertEqual(world.scheduled, packets)
                world.sender = "CYA"
                world.reg("receive_household", host)
                world.reg("receive_household", host)
                self.assertEqual(world.character_actions, [("set_nationality", GROVER, host, "AVI")])
                self.assertFalse(world.regtest("agreement_live"))

    def test_other_hosts_never_solicited_or_modified(self):
        for host in ("CYA", "FLO", "GRI"):
            with self.subTest(host=host):
                world = RegencyWorld()
                world.context()
                world.local_child(host)
                old = copy.deepcopy(world.countries[host])
                world.reg("request_household")
                world.reg("recover_household")
                self.assertEqual(world.countries[host], old)
                self.assertEqual(world.countries[host].characters, old.characters)
                self.assertEqual(world.character_actions, [])

    def test_stale_custody_acceptance_revalidates_every_critical_condition(self):
        for reason in ("death", "adult", "ruling", "foreign_transfer", "war", "subject", "timeout"):
            with self.subTest(reason=reason):
                world = RegencyWorld()
                world.context()
                world.local_child("ERI")
                world.reg("request_household")
                if reason == "death":
                    world.global_flags.add(DEAD)
                elif reason == "adult":
                    world.date = datetime.date(1021, 5, 22)
                elif reason == "ruling":
                    world.countries["ERI"].leader = GROVER
                elif reason == "foreign_transfer":
                    world.local_child("CYA")
                elif reason == "war":
                    world.join_defence("FLO", "AVI")
                elif reason == "subject":
                    world.countries["ERI"].subject = True
                else:
                    world.advance_days(46)
                world.reg("receive_household", "ERI")
                self.assertNotIn(GROVER, world.countries["AVI"].characters)
                self.assertEqual(world.character_actions, [])
if __name__ == "__main__":
    unittest.main(argv=[__file__, *BASE["REST"]], verbosity=2)
