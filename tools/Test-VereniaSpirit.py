"""Execute Verenia's production spirit ledger and annexation regressions.

Run python -B tools/Test-VereniaSpirit.py [-v] [TestClass.test_name].
Source coefficients come from the builder, not its generated arithmetic. The
strict shared interpreter is a script fixture, not an HOI4 engine simulation.
"""
from __future__ import annotations

import copy
import itertools
import re
import runpy
import unittest
from decimal import Decimal
from pathlib import Path

UNI = runpy.run_path(str(Path(__file__).with_name("Test-VereniaUnification.py")))
BASE = UNI["BASE"]
MOD, OPT, read, walk = (UNI[k] for k in ("MOD", "OPT", "read", "walk"))
GEN = runpy.run_path(str(Path(__file__).with_name("Build-VereniaSpirit.py")))
GEN["components"].__globals__["EAW"] = OPT.eaw
COMPONENTS = GEN["components"]()
PREFIX = "HSM_VER_SP_"
OWNED = PREFIX + "owned_"
VALUE = PREFIX + "value_"
DYNAMIC = PREFIX + "united_verenia"
FOUNDED = "HSM_VER_UNI_founded"
HOUSES = ("ERI", "EYR", "AVI")
NATIVE = set(GEN["NATIVE"])
COEFFICIENTS = {
    name: {n.key.lower(): Decimal(n.value) for n in idea.get("modifier")}
    for name, idea in COMPONENTS.items()
}
MODIFIERS = {key for values in COEFFICIENTS.values() for key in values}
UNRELATED = {"AVI_scienceexchange", "AVI_fortify", "agrarian_society",
             "better_science_base", "E_E_rivalry"}
NATIVE_EARNED = {"AVI_common_markets", "AVI_studentexchange",
                 "AVI_relaxd_citizenship", "AVI_annual_military_exercises",
                 "AVI_unified_intelligence_agency_lar"}


def owned(country):
    return {flag[len(OWNED):] for flag in country.flags if flag.startswith(OWNED)}


def expected_values(names):
    result = dict.fromkeys(MODIFIERS, Decimal(0))
    for name in set(names):
        for key, value in COEFFICIENTS[name].items():
            result[key] += value
    return result


def executable(nodes):
    """Do not mistake tooltip previews for executed grants or removals."""
    for node in nodes:
        if node.key in {"effect_tooltip", "show_ideas_tooltip", "custom_effect_tooltip"}:
            continue
        yield node
        yield from executable(node.children)


class SpiritWorld(UNI["UnionWorld"]):
    def __init__(self):
        super().__init__()
        self.at_avian_annex = []
        self.dlcs = set()

    def check(self, nodes, tag="ERI"):
        for node in nodes:
            if node.key == "has_dlc":
                ok = node.value in self.dlcs
            else:
                ok = super().check([node], tag)
            if not ok:
                return False
        return True

    def spirit(self, effect, host):
        self.root = host
        self.apply(PREFIX + effect, host)

    def component(self, action, name, host):
        self.spirit(action + "_" + name, host)

    def hook(self, name, root, sender):
        if name == "on_annex" and sender == "AVI":
            recipient = self.countries[root]
            self.at_avian_annex.append((root, owned(recipient) | recipient.ideas))
            # Make post-annex lookups unable to rescue a missing pre-annex import.
            donor = self.countries[sender]
            donor.ideas.clear()
            donor.flags.difference_update({f for f in donor.flags if f.startswith(OWNED)})
        super().hook(name, root, sender)


class LedgerAssertions(unittest.TestCase):
    def assertValues(self, world, host, names):
        country = world.countries[host]
        actual = {k[len(VALUE):]: v for k, v in country.variables.items()
                  if k.startswith(VALUE)}
        expected = expected_values(names)
        # Binding uniqueness is checked separately, so a stale extra variable
        # does not hide unrelated lifecycle failures behind the same assertion.
        self.assertTrue(expected.keys() <= actual.keys(), sorted(expected.keys() - actual.keys()))
        for key, value in expected.items():
            # The shared harness uses floats; allow only binary rounding error.
            self.assertAlmostEqual(actual[key], float(value), delta=1e-10,
                                   msg=f"{host}: {key}, components={sorted(names)}")

    def assertLedger(self, world, host, names):
        country = world.countries[host]
        self.assertEqual(owned(country), set(names))
        self.assertFalse(country.ideas.intersection(COMPONENTS))
        self.assertIn(DYNAMIC, country.dynamic_modifiers)
        self.assertValues(world, host, names)


class Arithmetic(LedgerAssertions):
    def test_every_component_exact_coefficients_for_every_host(self):
        for host in HOUSES:
            world = SpiritWorld()
            country = world.countries[host]
            for name in COMPONENTS:
                with self.subTest(host=host, component=name):
                    country.flags = {FOUNDED, OWNED + name}
                    world.spirit("recalculate", host)
                    self.assertValues(world, host, {name})

    def test_full_coefficient_sum_and_recalculation_replace_stale_values(self):
        for host in HOUSES:
            with self.subTest(host=host):
                world = SpiritWorld()
                country = world.countries[host]
                country.flags.update(OWNED + name for name in COMPONENTS)
                country.variables.update({VALUE + key: 999 for key in MODIFIERS})
                country.variables["unrelated_variable"] = 17
                world.spirit("recalculate", host)
                self.assertValues(world, host, COMPONENTS)
                snapshot = copy.deepcopy(country.variables)
                world.spirit("recalculate", host)
                self.assertEqual(country.variables, snapshot)
                country.flags.difference_update(OWNED + name for name in COMPONENTS)
                world.spirit("recalculate", host)
                self.assertValues(world, host, set())
                self.assertEqual(country.variables["unrelated_variable"], 17)

    def test_mixed_regional_native_sum_preserves_costs_and_population(self):
        names = {"HSM_ERI_DEV_public_services", "HSM_AVI_translation_office",
                 "HSM_VER_joint_staff", "HSM_VER_UNI_constitutional_state",
                 "AVI_common_markets", "AVI_studentexchange", "AVI_relaxd_citizenship",
                 "AVI_unified_intelligence_agency_lar"}
        for host in HOUSES:
            with self.subTest(host=host):
                world = SpiritWorld()
                country = world.countries[host]
                country.flags.add(FOUNDED)
                country.ideas.update(names)
                world.spirit("refresh", host)
                self.assertLedger(world, host, names)
                for key, value in {"monthly_population": .18, "political_power_gain": -.20,
                                   "supply_consumption_factor": -.13, "stability_factor": .125,
                                   "research_speed_factor": .055, "consumer_goods_factor": -.10,
                                   "production_speed_buildings_factor": .20}.items():
                    self.assertAlmostEqual(country.variables[VALUE + key], value, delta=1e-10)


class Lifecycle(LedgerAssertions):
    def test_preunion_wrappers_preserve_real_ideas_for_all_components(self):
        for host in HOUSES:
            world = SpiritWorld()
            country = world.countries[host]
            for name in COMPONENTS:
                with self.subTest(host=host, component=name):
                    world.component("add", name, host)
                    self.assertIn(name, country.ideas)
                    self.assertTrue(world.test(PREFIX + "has_" + name, host))
                    world.spirit("maintain", host)
                    self.assertFalse(owned(country))
                    self.assertFalse(country.dynamic_modifiers)
                    self.assertFalse(country.variables)
                    world.component("remove", name, host)
                    self.assertNotIn(name, country.ideas)
                    self.assertFalse(world.test(PREFIX + "has_" + name, host))

    def test_unfounded_absent_and_foreign_tags_are_not_converted(self):
        for host, founded, exists in itertools.product((*HOUSES, "GRI"), (False, True), (False, True)):
            if host in HOUSES and founded and exists:
                continue
            with self.subTest(host=host, founded=founded, exists=exists):
                world = SpiritWorld()
                country = world.countries[host]
                country.exists = exists
                country.ideas.update(NATIVE_EARNED)
                if founded:
                    country.flags.add(FOUNDED)
                before = copy.deepcopy(world.countries)
                world.spirit("maintain", host)
                self.assertEqual(world.countries, before)

    def test_existing_save_capture_is_idempotent_and_preserves_unrelated_state(self):
        names = NATIVE_EARNED | {"HSM_VER_common_courts", "HSM_AVI_common_budget"}
        for host in HOUSES:
            with self.subTest(host=host):
                world = SpiritWorld()
                country = world.countries[host]
                country.flags.add(FOUNDED)
                country.ideas.update(names | UNRELATED)
                country.variables["other_system"] = 42
                country.dynamic_modifiers.add("other_dynamic_modifier")
                resources = world.resources()
                neighbours = copy.deepcopy({t: c for t, c in world.countries.items() if t != host})
                world.spirit("maintain", host)
                self.assertLedger(world, host, names)
                self.assertTrue(UNRELATED <= country.ideas)
                self.assertEqual(country.variables["other_system"], 42)
                self.assertEqual(country.dynamic_modifiers, {DYNAMIC, "other_dynamic_modifier"})
                before = copy.deepcopy(country)
                for _ in range(3):
                    world.spirit("maintain", host)
                self.assertEqual(country, before)
                self.assertEqual(world.resources(), resources)
                self.assertEqual({t: c for t, c in world.countries.items() if t != host}, neighbours)

    def test_postunion_add_remove_and_legacy_raw_capture_do_not_stack(self):
        names = ("AVI_common_markets", "HSM_AVI_translation_office", "HSM_VER_joint_staff")
        for host in HOUSES:
            with self.subTest(host=host):
                world = SpiritWorld()
                country = world.countries[host]
                country.flags.add(FOUNDED)
                for name in names:
                    world.component("add", name, host)
                    world.component("add", name, host)
                self.assertLedger(world, host, names)
                country.ideas.update(names)
                world.spirit("maintain", host)
                self.assertLedger(world, host, names)
                for i, name in enumerate(names):
                    world.component("remove", name, host)
                    world.component("remove", name, host)
                    self.assertFalse(world.test(PREFIX + "has_" + name, host))
                    self.assertLedger(world, host, names[i + 1:])

    def test_native_and_regional_families_keep_only_highest_owned_tier(self):
        for host in HOUSES:
            world = SpiritWorld()
            country = world.countries[host]
            for family in GEN["FAMILIES"]:
                with self.subTest(host=host, family=family):
                    country.flags = {FOUNDED}
                    country.ideas = set(family)
                    world.spirit("refresh", host)
                    self.assertLedger(world, host, {family[-1]})
                    for low in family[:-1]:
                        world.component("add", low, host)
                        self.assertFalse(world.test(PREFIX + "has_" + low, host))
                        self.assertLedger(world, host, {family[-1]})
                    world.component("remove", family[-1], host)
                    self.assertLedger(world, host, set())

    def test_economic_upgrade_replaces_instead_of_adding_both_tiers(self):
        for host in HOUSES:
            with self.subTest(host=host):
                world = SpiritWorld()
                world.countries[host].flags.add(FOUNDED)
                world.component("add", "AVI_econcoop", host)
                world.component("add", "AVI_common_markets", host)
                self.assertLedger(world, host, {"AVI_common_markets"})
                self.assertAlmostEqual(world.countries[host].variables[VALUE + "production_speed_buildings_factor"], .15)

    def test_remove_clears_raw_and_ledger_copies_even_before_union(self):
        for host, founded in itertools.product(HOUSES, (False, True)):
            with self.subTest(host=host, founded=founded):
                world = SpiritWorld()
                country = world.countries[host]
                name = "AVI_studentexchange"
                country.flags.add(OWNED + name)
                country.ideas.add(name)
                if founded:
                    country.flags.add(FOUNDED)
                world.component("remove", name, host)
                self.assertNotIn(name, country.ideas)
                self.assertNotIn(name, owned(country))
                self.assertFalse(world.test(PREFIX + "has_" + name, host))

    def test_identity_component_cancellation_is_rechecked_after_conversion(self):
        for host, idea, consent in (
            ("ERI", "HSM_VER_ID_aquileian_curriculum", "HSM_VER_ID_ERI_aquileian"),
            ("EYR", "HSM_VER_ID_herzland_curriculum", "HSM_VER_ID_EYR_herzland"),
        ):
            with self.subTest(host=host):
                world = SpiritWorld()
                country = world.countries[host]
                country.flags.update({FOUNDED, consent})
                world.component("add", idea, host)
                self.assertLedger(world, host, {idea})
                country.flags.remove(consent)
                world.spirit("maintain", host)
                self.assertLedger(world, host, set())

    def test_existing_save_is_captured_by_each_production_daily_hook(self):
        for host in HOUSES:
            with self.subTest(host=host):
                world = SpiritWorld()
                country = world.countries[host]
                country.flags.add(FOUNDED)
                country.ideas.add("AVI_studentexchange")
                world.root = host
                world.run(world.hooks["on_daily_" + host], host)
                self.assertIn("AVI_studentexchange", owned(country))
                self.assertNotIn("AVI_studentexchange", country.ideas)
                self.assertIn(DYNAMIC, country.dynamic_modifiers)
                self.assertValues(world, host, owned(country))

    def test_incorporated_charter_and_budget_survive_foreign_treaty_cleanup(self):
        institutions = {"HSM_VER_common_courts", "HSM_VER_joint_staff",
                        "HSM_VER_shared_services", "HSM_AVI_common_budget"}
        for host, founded in itertools.product(HOUSES, (False, True)):
            with self.subTest(host=host, founded=founded):
                world = SpiritWorld()
                country = world.countries[host]
                if founded:
                    country.flags.add(FOUNDED)
                country.ideas.update(institutions)
                world.spirit("refresh", host)
                for _ in range(3):
                    world.apply("HSM_VER_remove_charter_benefits", host)
                    world.apply("HSM_VER_AVI_refresh_budget", host)
                    world.apply("HSM_VER_AVI_void_budget", host)
                    world.spirit("maintain", host)
                if founded:
                    self.assertLedger(world, host, institutions)
                else:
                    self.assertFalse(institutions & country.ideas)
                    self.assertFalse(owned(country))

    def test_native_grants_use_real_ideas_until_each_recipient_is_founded(self):
        for host, founded, lar in itertools.product(HOUSES, (False, True), (False, True)):
            with self.subTest(host=host, founded=founded, lar=lar):
                world = SpiritWorld()
                if founded:
                    world.countries[host].flags.add(FOUNDED)
                if lar:
                    world.dlcs.add("La Resistance")
                for focus in ("pursue_economic_cooperation", "student_exchange_program",
                              "annual_military_exercises", "unified_intelligence_agency"):
                    world.root = "AVI"
                    world.run(world.focuses[focus].get("completion_reward"), "AVI")
                names = {"AVI_econcoop", "AVI_studentexchange", "AVI_annual_military_exercises",
                         "AVI_unified_intelligence_agency" + ("_lar" if lar else "")}
                for recipient in HOUSES:
                    country = world.countries[recipient]
                    if founded and recipient == host:
                        self.assertLedger(world, recipient, names)
                    else:
                        self.assertTrue(names <= country.ideas)
                        self.assertFalse(owned(country))
                        self.assertNotIn(DYNAMIC, country.dynamic_modifiers)

    def test_native_regime_focus_swaps_replace_consolidated_predecessors(self):
        for lar, regime in itertools.product((False, True), ("communist", "fascist")):
            with self.subTest(lar=lar, regime=regime):
                world = SpiritWorld()
                country = world.countries["AVI"]
                country.flags.add(FOUNDED)
                if lar:
                    world.dlcs.add("La Resistance")
                suffix = "_lar" if lar else ""
                for name in ("AVI_common_markets", "AVI_annual_military_exercises",
                             "AVI_unified_intelligence_agency" + suffix):
                    world.component("add", name, "AVI")
                if regime == "communist":
                    focuses = ("a_socialist_economic_system", "the_strong_arm_of_the_revolution",
                               "the_long_arm_of_the_revolution")
                    expected = {"AVI_socialist_economics", "AVI_the_strong_arm_of_the_revolution",
                                "AVI_long_arm_of_the_revolution" + suffix}
                else:
                    focuses = ("restructure_the_ministry_of_economics", "restructure_the_war_office",
                               "restructure_the_secret_service")
                    expected = {"AVI_Wirtschaftsministerium", "AVI_Kriegsamt", "AVI_Evidenzbureau" + suffix}
                for focus in focuses:
                    world.run(world.focuses[focus].get("completion_reward"), "AVI")
                self.assertLedger(world, "AVI", expected)


class Inheritance(LedgerAssertions):
    def test_actual_native_ideas_and_ledger_entries_import_once(self):
        for host, ledger in itertools.product(("ERI", "EYR"), (False, True)):
            with self.subTest(host=host, ledger=ledger):
                world = SpiritWorld()
                country, avian = world.countries[host], world.countries["AVI"]
                country.flags.add(FOUNDED)
                country.ideas.add("AVI_studentexchange")
                if ledger:
                    avian.flags.update(OWNED + n for n in NATIVE_EARNED)
                else:
                    avian.ideas.update(NATIVE_EARNED)
                avian.ideas.update({"AVI_scienceexchange", "HSM_AVI_translation_office"})
                donor = copy.deepcopy(avian)
                for _ in range(3):
                    world.spirit("inherit_avian", host)
                self.assertLedger(world, host, NATIVE_EARNED)
                self.assertEqual(avian, donor)
                self.assertIn(PREFIX + "avian_imported", country.flags)

    def test_preunion_inheritance_replaces_raw_native_ranks_without_downgrade(self):
        families = [family for family in GEN["FAMILIES"] if set(family) <= NATIVE]
        for host, family, donor_upgrades in itertools.product(("ERI", "EYR"), families, (False, True)):
            with self.subTest(host=host, family=family, donor_upgrades=donor_upgrades):
                world = SpiritWorld()
                low, high = family[0], family[-1]
                host_idea, donor_idea = (low, high) if donor_upgrades else (high, low)
                world.countries[host].ideas.add(host_idea)
                world.countries["AVI"].ideas.add(donor_idea)
                for _ in range(2):
                    world.spirit("inherit_avian", host)
                    world.spirit("maintain", host)
                    self.assertEqual(set(family) & world.countries[host].ideas, {high})
                    self.assertFalse(owned(world.countries[host]))
                world.countries[host].flags.add(FOUNDED)
                world.spirit("refresh", host)
                self.assertLedger(world, host, {high})

    def test_focus_history_alone_cannot_invent_native_benefits(self):
        for host in ("ERI", "EYR"):
            with self.subTest(host=host):
                world = SpiritWorld()
                world.countries[host].flags.add(FOUNDED)
                world.countries["AVI"].focuses.update({"common_markets_agreement", "student_exchange_program",
                                                       "relax_citizenship_requirements", "annual_military_exercises",
                                                       "unified_intelligence_agency", "technological_cooperation"})
                world.spirit("inherit_avian", host)
                world.spirit("refresh", host)
                self.assertLedger(world, host, set())

    def test_migration_imports_only_certified_absent_avian_once(self):
        for host, exists, absorbed in itertools.product(("ERI", "EYR"), (False, True), (False, True)):
            with self.subTest(host=host, exists=exists, absorbed=absorbed):
                world = SpiritWorld()
                country, avian = world.countries[host], world.countries["AVI"]
                country.flags.add(FOUNDED)
                if absorbed:
                    country.flags.add("HSM_VER_UNI_absorbed_AVI")
                avian.exists = exists
                avian.ideas.update(NATIVE_EARNED)
                world.spirit("maintain", host)
                imported = not exists and absorbed
                self.assertLedger(world, host, NATIVE_EARNED if imported else set())
                if imported:
                    world.component("remove", "AVI_studentexchange", host)
                    world.spirit("maintain", host)
                    self.assertLedger(world, host, NATIVE_EARNED - {"AVI_studentexchange"})

    def test_native_inheritance_normalizes_donor_and_recipient_tiers(self):
        for host in ("ERI", "EYR"):
            with self.subTest(host=host):
                world = SpiritWorld()
                country = world.countries[host]
                country.flags.add(FOUNDED)
                country.ideas.add("AVI_econcoop")
                world.countries["AVI"].ideas.update({"AVI_common_markets", "AVI_socialist_economics"})
                world.spirit("inherit_avian", host)
                self.assertLedger(world, host, {"AVI_socialist_economics"})

    def test_union_foundation_captures_before_annex_for_all_hosts(self):
        for host in HOUSES:
            with self.subTest(host=host):
                world = SpiritWorld().begin(host)
                world.countries["AVI"].ideas.update(NATIVE_EARNED)
                world.countries[host].ideas.add("AVI_studentexchange")
                world.found(host)
                self.assertIn(FOUNDED, world.countries[host].flags)
                self.assertTrue(NATIVE_EARNED <= owned(world.countries[host]))
                self.assertFalse(world.countries[host].ideas.intersection(COMPONENTS))
                self.assertValues(world, host, owned(world.countries[host]))
                if host != "AVI":
                    self.assertEqual(len(world.at_avian_annex), 1)
                    self.assertTrue(NATIVE_EARNED <= world.at_avian_annex[0][1])
                before = copy.deepcopy(world.countries[host])
                world.spirit("maintain", host)
                self.assertEqual(world.countries[host], before)

    def test_union_without_avian_cannot_import_living_neighbour(self):
        for host in ("ERI", "EYR"):
            with self.subTest(host=host):
                world = SpiritWorld().begin(host, avian="neutral")
                world.countries["AVI"].ideas.update(NATIVE_EARNED)
                world.found(host)
                world.spirit("maintain", host)
                self.assertTrue(world.countries["AVI"].exists)
                self.assertFalse(NATIVE.intersection(owned(world.countries[host])))
                self.assertFalse(world.at_avian_annex)

    def test_avr_accession_captures_before_annex_for_both_dukes(self):
        for host in ("ERI", "EYR"):
            with self.subTest(host=host):
                world = SpiritWorld().begin(host, avian="neutral")
                world.found(host)
                world.select_avian_route("intergigantes")
                world.countries["AVI"].ideas.update(NATIVE_EARNED)
                world.root = host
                world.apply("HSM_VER_AVR_offer", host)
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_avr.1", "AVI"))
                world.choose("hsm_ver_avr.1", 1, "AVI")
                world.root = host
                world.apply("HSM_VER_AVR_customs", host)
                world.advance_days(1)
                self.assertTrue(world.deliver("hsm_ver_avr.2", "AVI"))
                world.choose("hsm_ver_avr.2", 1, "AVI")
                world.advance_days(60)
                world.root = host
                self.assertTrue(world.test("HSM_VER_AVR_can_integrate", host))
                world.apply("HSM_VER_AVR_integrate", host)
                self.assertEqual(len(world.at_avian_annex), 1)
                self.assertTrue(NATIVE_EARNED <= world.at_avian_annex[0][1])
                self.assertTrue(NATIVE_EARNED <= owned(world.countries[host]))
                self.assertValues(world, host, owned(world.countries[host]))

    def test_force_integration_captures_before_annex_for_both_dukes(self):
        for host in ("ERI", "EYR"):
            with self.subTest(host=host):
                world = SpiritWorld()
                world.hooks = world.all_hooks
                world.avian_terms(host, subject=True, authority="union")
                world.countries["AVI"].ideas.update(NATIVE_EARNED)
                world.advance_days(90)
                world.force("integrate_avian", host)
                self.assertEqual(len(world.at_avian_annex), 1)
                self.assertTrue(NATIVE_EARNED <= world.at_avian_annex[0][1])
                self.assertTrue(NATIVE_EARNED <= owned(world.countries[host]))
                self.assertValues(world, host, owned(world.countries[host]))


class Structure(unittest.TestCase):
    def test_generated_files_match_current_source_coefficients(self):
        for relative, expected in GEN["generated"](COMPONENTS).items():
            with self.subTest(path=relative):
                path = MOD / relative
                self.assertTrue(path.exists(), relative)
                self.assertEqual(path.read_text(encoding="utf-8"), expected,
                                 "Run tools/Build-VereniaSpirit.py to regenerate")

    def test_component_selection_includes_the_two_grover_partnerships(self):
        self.assertEqual(len(COMPONENTS), 80)
        self.assertTrue({"HSM_VER_GRO_common_market", "HSM_VER_GRO_joint_defence"} <= set(COMPONENTS))
        self.assertFalse({"HSM_VER_GRO_guardianship", "HSM_VER_GRO_transition",
                          "HSM_VER_GRO_open_court_legacy", "HSM_VER_GRO_managed_court_legacy",
                          "HSM_VER_GRO_rule_of_law", "HSM_VER_GRO_patrons_legacy"} & set(COMPONENTS))
        self.assertFalse(set(COMPONENTS).intersection(GEN["EXCLUDE"] | UNRELATED))
        self.assertEqual({n for n in COMPONENTS if n.startswith("AVI_")}, NATIVE)
        permitted = {"allowed", "allowed_civil_war", "available", "cancel", "modifier", "picture", "removal_cost"}
        for name, idea in COMPONENTS.items():
            with self.subTest(component=name):
                self.assertTrue({n.key for n in idea.children} <= permitted)
                self.assertEqual(len(idea.all("modifier")), 1)
                modifiers = idea.get("modifier")
                self.assertTrue(modifiers)
                self.assertEqual(len(modifiers), len({n.key.lower() for n in modifiers}))
                for node in modifiers:
                    self.assertFalse(node.children)
                    self.assertEqual(node.op, "=")
                    self.assertTrue(Decimal(node.value).is_finite())

    def test_dynamic_modifier_has_one_supported_binding_per_modifier(self):
        docs = (OPT.game / "documentation/modifiers_documentation.md").read_text(encoding="utf-8-sig")
        supported = set(re.findall(r"^## ([A-Za-z_][A-Za-z_0-9]*)\s*$", docs, re.M))
        self.assertTrue(supported)
        self.assertIn("production_speed_<Building>_factor", docs)
        buildings = {n.key for root in (OPT.game, OPT.eaw, MOD)
                     for path in (root / "common/buildings").glob("*.txt")
                     for container in read(path) if container.key == "buildings"
                     for n in container.children}
        supported.update("production_speed_" + name + "_factor" for name in buildings)
        self.assertFalse(MODIFIERS - supported, sorted(MODIFIERS - supported))
        definitions = read(MOD / "common/dynamic_modifiers/HSM_VER_spirit.txt")
        self.assertEqual([n.key for n in definitions], [DYNAMIC])
        dynamic = definitions[0]
        entries = [n for n in dynamic.children if n.key not in {"icon", "enable"}]
        self.assertEqual(len(entries), len(MODIFIERS), "Case aliases must share one sum and binding")
        self.assertEqual({n.key for n in entries}, MODIFIERS)
        for node in entries:
            self.assertEqual(node.value, VALUE + node.key)
        self.assertEqual(dynamic.get("enable"), BASE["parse"]("HSM_VER_SP_active = yes"))

    def test_all_wrapper_references_resolve_and_no_executable_raw_operations_remain(self):
        world = SpiritWorld()
        for name in COMPONENTS:
            self.assertIn(PREFIX + "has_" + name, world.triggers)
            for action in ("add", "remove"):
                self.assertIn(PREFIX + action + "_" + name, world.effects)
        for folder in ("common/national_focus", "common/scripted_effects", "common/scripted_triggers",
                       "common/on_actions", "common/decisions", "events"):
            for path in (MOD / folder).rglob("*.txt"):
                nodes = read(path)
                for node in walk(nodes):
                    match = re.fullmatch(r"HSM_VER_SP_(add|remove|has)_(.+)", node.key)
                    if match and node.value in ("yes", "no"):
                        action, name = match.groups()
                        self.assertIn(name, COMPONENTS, (path, node.key))
                        self.assertIn(node.key, world.triggers if action == "has" else world.effects)
                if path.name in {"HSM_VER_spirit.txt", "HSM_VER_spirit_components.txt"}:
                    continue
                for node in executable(nodes):
                    if node.key in {"add_ideas", "remove_ideas", "has_idea", "add_idea", "remove_idea"}:
                        references = {n.key for n in node.children} if node.children else {node.value}
                        self.assertFalse(references.intersection(COMPONENTS), (path, node))
                    if node.key == "add_timed_idea":
                        self.assertNotIn(node.get("idea"), COMPONENTS, (path, node))

    def test_timed_programmes_development_laws_and_special_research_are_not_captured(self):
        source = read(OPT.eaw / "common/scripted_effects/EAW_misc_effect.txt")
        development = [n for n in source if n.key.startswith(("increase_society_development", "increase_science_development"))]
        self.assertTrue(development)
        laws = {n.value for effect in development for n in walk(effect.children)
                if n.key in {"add_idea", "remove_idea", "has_idea"} and isinstance(n.value, str)}
        self.assertIn("agrarian_society", laws)
        self.assertFalse(laws.intersection(COMPONENTS))
        for relative in ("common/national_focus/AVI.txt", "events/Avian Events.txt"):
            current, native = read(MOD / relative), read(OPT.eaw / relative)
            timed = lambda nodes: [n for n in walk(nodes) if n.key == "add_timed_idea"]
            self.assertEqual(timed(current), timed(native))
        self.assertFalse({"AVI_scienceexchange", "avithreehousescorp", "avitripartitecolleges",
                          "AVI_foundation", "AVI_foundation_lar"}.intersection(COMPONENTS))
        operations = list(executable(read(MOD / "common/scripted_effects/HSM_VER_spirit_components.txt")))
        self.assertFalse({n.key for n in operations}.intersection({"add_research_slot", "add_tech_bonus", "add_to_tech_sharing_group"}))


if __name__ == "__main__":
    unittest.main(argv=[__file__, *BASE["REST"]])
