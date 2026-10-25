"""Bounded parsed-source Grover regressions, not an HOI4 engine emulator.

python -B -X utf8 tools/Test-VereniaGrover.py [--eaw PATH] [--game PATH]
Only fixture state is mutated. Effects, triggers, choices and hooks come from
production; unknown executable operations raise. No game or native scheduler runs.
"""
from __future__ import annotations

import copy
import datetime
import itertools
import re
import runpy
import subprocess
import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path

SP = runpy.run_path(str(Path(__file__).with_name("Test-VereniaSpirit.py")))
REG, BASE = SP["UNI"]["REG"], SP["BASE"]
Node, parse = BASE["Node"], BASE["parse"]
read, walk, MOD, OPT = (SP[k] for k in ("read", "walk", "MOD", "OPT"))
P = "HSM_VER_GRO_"
GROVER, DEAD = "GRI_emperor_grover_vi", "GRI_grover_vi_dead"
HOSTS = ("ERI", "EYR")
HOME = frozenset(("391", "400", "401", "500", "673"))
VERENIA = HOME | {"470"}
HEART = frozenset(map(str, (378, 382, 397, 398, 399, 402, 405, 411, 422, 423,
    424, 433, 434, 437, 439, 440, 441, 443, 447, 458, 479, 486, 492, 497, 498,
    506, 520, 538, 539, 545, 546, 547, 554, 555, 568, 665, 666, 674)))
NATIVE_HEART_TAGS = {"GRI", "BRZ", "STW", "KAT", "ANG", "YAL", "ROU", "PYT", "FEA"}
CHOICES = (
    ("lessons", "queue_lessons", 4, ("open_education", "filtered_education")),
    ("petition", "queue_petition", 5, ("apply_law", "protect_patron")),
    ("service", "queue_service", 6, ("logistics", "command")),
    ("articles", "queue_articles", 7, ("sign_articles",)),
)
BIRTHDAY = datetime.date(1021, 5, 21)
PRE_GROVER_REF = "ff58d4bc7635cc84abd3d329f0248af15ada04bc"
NATIVE_RULES = {
    "events/GriffonianEmpire Events.txt": {
        **{f"imperial.{n}": P + "native_ruler_allowed" for n in (1, 2, 3, 30, 300, 44, 71, 72, 73, 74, 75, 76, 123, 137)},
        "imperial.70": P + "native_demand_allowed",
    },
    "events/Grover_Events.txt": {
        **{f"grover.{n}": P + "native_childhood_allowed" for n in (*range(1, 15), 17)},
        **{f"grover.{n}": P + "native_household_allowed" for n in (32, 35, 40, 41)},
    },
}
NATIVE_GUARDS = {guard for rules in NATIVE_RULES.values() for guard in rules.values()}
OPTION_METADATA = {"name", "trigger", "ai_chance", "highlight", "original_tag", "default_option"}


def one(nodes, key):
    found = [n for n in nodes if n.key == key]
    if len(found) != 1:
        raise AssertionError(f"Expected one {key}; got {len(found)}")
    return found[0]


def native_states():
    return {n.get("id"): n for path in (OPT.eaw / "history/states").glob("*.txt")
            for n in read(path) if n.key == "state"}


NATIVE_STATES = native_states()
REGION = one(read(next((OPT.eaw / "map/strategicregions").glob("164-*.txt"))), "strategic_region")
REGION_PROVINCES = {n.key for n in REGION.get("provinces")}
CAPITAL_DISTRICT = {sid for sid, n in NATIVE_STATES.items()
                    if {p.key for p in n.get("provinces")} <= REGION_PROVINCES}


@dataclass
class State(REG["State"]):
    sid: str = ""
    region: str = "0"
    fully_controlled: bool = True
    flags: set = field(default_factory=set)
    claims: set = field(default_factory=set)


class GroverWorld(SP["SpiritWorld"]):
    def __deepcopy__(self, memo):
        # Parsed production definitions are read-only; clone only fixture state.
        result = object.__new__(type(self))
        memo[id(self)] = result
        source_keys = {"triggers", "effects", "events", "focuses", "decisions", "hooks", "all_hooks", "gro_hooks"}
        for key, value in vars(self).items():
            setattr(result, key, value if key in source_keys else copy.deepcopy(value, memo))
        return result

    def __init__(self, host):
        super().__init__()
        self.host = self.root = host
        self.sender = host
        self.previous = None
        self.date = datetime.date(1020, 1, 1)
        self.day = 0
        self.scheduled = []
        self.state_ids = {}
        for sid in HEART | VERENIA | {"1", "75"}:
            cores = {n.value for n in NATIVE_STATES[sid].get("history", []) if n.key == "add_core_of"}
            self.state_ids[sid] = State(owner=host, controller=host, cores=cores,
                                       sid=sid, region="164" if sid in CAPITAL_DISTRICT else "0")
        self.states = list(self.state_ids.values())
        self.homelands = {int(sid): state for sid, state in self.state_ids.items()}
        self.state_ids["75"].owner = self.state_ids["75"].controller = "CYA"
        self.countries["GRI"].exists = False
        self.countries["GRI"].characters = {GROVER}
        for country in self.countries.values():
            country.war_support = 0.5
            country.doctrine_bonuses = []
            country.technology = {"native_tech"}
            country.capital = "382"
            country.focus_tree = "native_tree"
            country.popularities = {}
            country.elections = True
            country.research_slots = 3
            country.forces = {"army": 0.0, "air": 0.0, "navy": 0.0, "stockpile": 0.0}
            country.officers = set()
        c = self.countries[host]
        c.flags = {"HSM_VER_UNI_founded", "HSM_VER_diplomatic_route"}
        c.focuses.clear()
        c.cosmetic = "HSM_VER_UNIFIED"
        c.technology = {"host_tech", "native_tech"}
        c.forces = {"army": 40.0, "air": 200.0, "navy": 12.0, "stockpile": 400.0}
        c.officers = {"host_general", "host_admiral"}
        self.global_targets = {}
        self.global_variables = {}
        self.unit_transfers = []
        self.state_transfers = []
        self.tree_loads = []
        self.gro_hooks = {}
        path = MOD / "common/on_actions/HSM_VER_grover.txt"
        if path.exists():
            for container in read(path):
                for hook in container.children:
                    self.gro_hooks.setdefault(hook.key, []).extend(hook.get("effect", []))

    def scope_target(self, name, scope):
        if name == "capital_scope":
            return self.state_ids[self.countries[scope].capital]
        if name == "owner":
            return scope.owner
        if name == "overlord":
            return self.countries[scope].overlord
        if name == "faction_leader":
            faction = self.countries[scope].faction
            leaders = [t for t, c in self.countries.items() if faction and c.faction == faction and c.faction_leader]
            assert len(leaders) == 1, "Fixture faction needs exactly one leader"
            return leaders[0]
        raise AssertionError(name)

    def check(self, nodes, tag="ERI"):
        for n in nodes:
            if n.key in ("owner", "overlord", "faction_leader", "capital_scope"):
                ok = self.scoped_check(n.children, self.scope_target(n.key, tag), tag)
            elif n.key in ("state", "region", "has_state_flag"):
                assert isinstance(tag, State), n.key
                ok = (tag.sid == n.value if n.key == "state" else tag.region == n.value
                      if n.key == "region" else n.value in tag.flags)
            elif n.key in ("any_owned_state", "all_owned_state"):
                checks = [self.scoped_check(n.children, s, tag) for s in self.states if s.owner == tag]
                ok = any(checks) if n.key == "any_owned_state" else all(checks)
            elif n.key == "amount_research_slots":
                ok = REG["COMPARE"][n.op](self.countries[tag].research_slots, int(n.value))
            elif n.key == "free_building_slots":
                assert isinstance(tag, State)
                assert n.get("building") in ("industrial_complex", "arms_factory")
                assert n.get("include_locked") == "yes"
                size = one(n.children, "size")
                assert size.op == ">" and size.value == "0"
                assert {c.key for c in n.children} == {"building", "size", "include_locked"}
                ok = sum(tag.buildings.values()) < tag.capacity
            else:
                ok = super().check([n], tag)
            if not ok:
                return False
        return True

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
            elif n.key in self.effects:
                assert n.value == "yes", "Parameterized scripted effects are not modelled"
                self.run(self.effects[n.key], tag)
            elif n.key in ("owner", "overlord", "faction_leader", "capital_scope"):
                self.scoped_run(n.children, self.scope_target(n.key, tag), tag)
            elif n.key in ("every_state", "every_owned_state", "random_owned_state"):
                eligible = [s for s in self.states if (n.key == "every_state" or s.owner == tag)
                            and self.scoped_check(n.get("limit", []), s, tag)]
                # Deterministic first eligible state; random selection itself is not simulated.
                for state in (eligible[:1] if n.key == "random_owned_state" else eligible):
                    self.scoped_run([c for c in n.children if c.key != "limit"], state, tag)
            elif n.key in ("set_state_flag", "clr_state_flag", "add_core_of", "remove_core_of", "remove_claim_by"):
                assert isinstance(tag, State), n.key
                collection = tag.flags if "state_flag" in n.key else tag.claims if n.key == "remove_claim_by" else tag.cores
                if n.key in ("set_state_flag", "add_core_of"):
                    collection.add(self.resolve(n.value))
                else:
                    collection.discard(self.resolve(n.value))
            elif n.key == "transfer_state_to":
                assert isinstance(tag, State)
                target = self.resolve(n.value)
                self.state_transfers.append((tag.sid, tag.owner, target))
                tag.owner = tag.controller = target
                self.countries[target].exists = True
            elif n.key in ("set_cosmetic_tag", "drop_cosmetic_tag"):
                self.countries[tag].cosmetic = n.value if n.key == "set_cosmetic_tag" else ""
            elif n.key == "set_capital":
                assert {c.key for c in n.children} <= {"state", "remember_old_capital"}
                assert self.state_ids[n.get("state")].owner == tag, "Cannot move capital to unowned state"
                self.countries[tag].capital = n.get("state")
            elif n.key == "set_autonomy":
                assert n.get("autonomy_state") == "autonomy_free"
                target = self.countries[self.resolve(n.get("target"))]
                assert target.overlord == tag
                target.subject, target.overlord = False, ""
            elif n.key == "inherit_technology":
                self.countries[tag].technology.update(self.countries[self.resolve(n.value)].technology)
            elif n.key == "save_global_event_target_as":
                self.global_targets[n.value] = tag
            elif n.key == "set_variable" and any(c.key.startswith("global.") for c in n.children):
                assert len(n.children) == 1
                value = n.children[0]
                self.global_variables[value.key] = tag if value.value == "THIS" else self.resolve(value.value)
            elif n.key == "set_popularities":
                assert {c.key for c in n.children} <= {"neutrality", "democratic", "fascism", "communism"}
                self.countries[tag].popularities = {c.key: float(c.value) for c in n.children}
            elif n.key == "set_politics":
                super().run([n], tag)
                if n.get("elections_allowed"):
                    self.countries[tag].elections = n.get("elections_allowed") == "yes"
            elif n.key == "load_focus_tree":
                assert {c.key for c in n.children} == {"tree", "keep_completed"}
                self.countries[tag].focus_tree = n.get("tree")
                if n.get("keep_completed") == "no":
                    self.countries[tag].focuses.clear()
                self.tree_loads.append((tag, copy.deepcopy(n.children)))
            elif n.key == "transfer_units_fraction":
                allowed = {"target", "size", "army_ratio", "air_ratio", "navy_ratio", "stockpile_ratio", "keep_unit_leaders_trigger"}
                assert {c.key for c in n.children} <= allowed
                assert n.get("keep_unit_leaders_trigger") == parse("always = yes")
                source, target = self.countries[tag], self.countries[self.resolve(n.get("target"))]
                for kind in source.forces:
                    fraction = float(n.get(kind + "_ratio", n.get("size", 0)))
                    assert 0 <= fraction <= 1
                    amount = source.forces[kind] * fraction
                    source.forces[kind] -= amount
                    target.forces[kind] += amount
                self.unit_transfers.append((tag, n.get("target"), copy.deepcopy(n.children)))
            elif n.key == "add_doctrine_cost_reduction":
                assert {c.key for c in n.children} == {"name", "cost_reduction", "uses", "category"}
                self.countries[tag].doctrine_bonuses.append(copy.deepcopy(n.children))
            elif n.key == "add_war_support":
                self.countries[tag].war_support += float(n.value)
            elif n.key == "add_research_slot":
                self.countries[tag].research_slots += int(n.value)
            else:
                if isinstance(tag, State) and n.key not in ("add_extra_state_shared_building_slots", "add_building_construction"):
                    raise AssertionError(f"Unsupported state effect: {n.key}")
                super().run([n], tag)

    def has(self, flag, tag=None):
        return P + flag in self.countries[tag or self.host].flags

    def valid(self, suffix, tag=None):
        tag = tag or self.host
        self.root = tag
        return self.test(P + suffix, tag)

    def gro(self, suffix, tag=None):
        tag = tag or self.host
        self.root = tag
        self.apply(P + suffix, tag)

    def complete(self, suffix, tag=None):
        tag = tag or self.host
        self.root = tag
        f = self.focuses[P + suffix]
        c = self.countries[tag]
        assert f.get("id") not in c.focuses, "Focus is already completed"
        assert all(any(n.value in c.focuses for n in group.children) for group in f.all("prerequisite")), suffix
        assert all(n.value not in c.focuses for group in f.all("mutually_exclusive") for n in group.children), suffix
        assert self.check(f.get("available", []), tag), suffix
        c.focuses.add(f.get("id"))
        self.run(f.get("completion_reward", []), tag)

    def daily(self):
        self.root = self.host
        self.run(self.gro_hooks["on_daily_" + self.host], self.host)

    def snapshot(self):
        return copy.deepcopy(({t: vars(c) for t, c in self.countries.items()}, self.state_ids,
                              self.scheduled, self.global_flags, self.character_actions,
                              self.global_targets, self.global_variables, self.unit_transfers,
                              self.state_transfers, self.tree_loads, self.portraits))

    def begin(self):
        self.complete("open_court")
        self.complete("household_file")
        return self

    def mandate(self):
        self.begin()
        self.complete("mandate")
        return self

    def prepare(self, choices=(0, 0, 0)):
        self.mandate()
        for focus, event, option in (("lessons", 4, choices[0]), ("petitions", 5, choices[1])):
            self.complete(focus)
            self.advance_days(1)
            assert self.deliver(f"hsm_ver_grover.{event}", self.host)
            self.choose(f"hsm_ver_grover.{event}", option, self.host)
        for focus in ("registers", "districts", "home_workshops", "service"):
            self.complete(focus)
        self.advance_days(1)
        assert self.deliver("hsm_ver_grover.6", self.host)
        self.choose("hsm_ver_grover.6", choices[2], self.host)
        self.complete("succession_articles")
        self.advance_days(1)
        assert self.deliver("hsm_ver_grover.7", self.host)
        self.choose("hsm_ver_grover.7", 0, self.host)
        self.complete("prepared_crown")
        return self


class Fixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates = {host: GroverWorld(host) for host in HOSTS}

    def world(self, host="ERI", route="diplomatic"):
        w = copy.deepcopy(self.templates[host])
        w.countries[host].flags.discard("HSM_VER_diplomatic_route")
        w.countries[host].flags.add("HSM_VER_" + route + "_route")
        return w


class EntryAndCustody(Fixtures):
    def test_exact_38_match_native_original_herzland_cores_and_exclude_verenia(self):
        native = {sid for sid, n in NATIVE_STATES.items() if any(
            c.key == "add_core_of" and c.value in NATIVE_HEART_TAGS for c in n.get("history", []))}
        self.assertEqual(len(HEART), 38)
        self.assertEqual(HEART, native)
        self.assertFalse(HEART & VERENIA)
        w = self.world()
        listed = [n.value for n in walk(w.triggers[P + "herzland_state"]) if n.key == "state"]
        self.assertCountEqual(listed, HEART)
        self.assertCountEqual([n.key for n in w.triggers[P + "herzland_held"]], HEART)
        for sid, state in w.state_ids.items():
            self.assertEqual(w.check(w.triggers[P + "herzland_state"], state), sid in HEART)

    def test_entry_requires_actual_owner_and_controller_of_every_38_and_five_homelands(self):
        for host, sid, attribute in itertools.product(HOSTS, sorted(HEART | HOME), ("owner", "controller")):
            with self.subTest(host=host, sid=sid, attribute=attribute):
                w = self.world(host)
                self.assertTrue(w.valid("can_start"))
                setattr(w.state_ids[sid], attribute, "CYA")
                w.countries["CYA"].subject, w.countries["CYA"].overlord = True, host
                self.assertFalse(w.valid("can_start"))
                w.gro("start")
                self.assertFalse(w.has("started"))

    def test_entry_government_original_identity_union_route_and_existing_gri_guards(self):
        for host, bad in itertools.product(HOSTS, ("subject", "war", "capitulated", "leader", "government", "origin", "union", "route", "dispossessed", "gri", "restored")):
            with self.subTest(host=host, bad=bad):
                w = self.world(host)
                c = w.countries[host]
                if bad in ("subject", "war", "capitulated"):
                    setattr(c, bad, True)
                elif bad == "leader": c.leader = GROVER
                elif bad == "government": c.government = "fascism"
                elif bad == "origin": c.original_tag = "CYA"
                elif bad == "union": c.flags.discard("HSM_VER_UNI_founded")
                elif bad == "route": c.flags.discard("HSM_VER_diplomatic_route")
                elif bad == "dispossessed": c.flags.add("HSM_VER_IMP_union_dispossessed")
                elif bad == "gri": w.countries["GRI"].exists = True
                else: w.countries["GRI"].flags.add(P + "restored")
                before = w.snapshot()
                w.gro("start")
                self.assertEqual(w.snapshot(), before)

    def test_all_four_route_memories_and_start_are_once_only(self):
        routes = {P + h.lower() + "_" + r for h, r in itertools.product(HOSTS, ("diplomatic", "military"))}
        for host, route in itertools.product(HOSTS, ("diplomatic", "military")):
            w = self.world(host, route)
            w.gro("start")
            self.assertEqual(w.countries[host].flags & routes, {P + host.lower() + "_" + route})
            before = w.snapshot()
            w.gro("start")
            self.assertEqual(w.snapshot(), before)

    def test_absent_gri_recovery_moves_only_the_original_character(self):
        for host in HOSTS:
            w = self.world(host)
            w.countries["GRI"].ideas.add("GRI_grover_vi")
            w.gro("start")
            self.assertTrue(w.valid("can_recover"))
            w.gro("household")
            self.assertFalse(w.countries["GRI"].exists)
            self.assertEqual([t for t, c in w.countries.items() if GROVER in c.characters], [host])
            self.assertEqual(w.character_actions, [("set_nationality", GROVER, "GRI", host)])
            self.assertNotIn("GRI_grover_vi", w.countries["GRI"].ideas)
            self.assertFalse(w.valid("can_recover"))

    def test_dead_foreign_unknown_and_duplicate_custody_cannot_create_regency(self):
        for host, custody in itertools.product(HOSTS, ("dead", "foreign", "unknown", "duplicate", "foreign_and_absent_gri")):
            with self.subTest(host=host, custody=custody):
                w = self.world(host)
                w.gro("start")
                if custody != "foreign_and_absent_gri": w.countries["GRI"].characters.clear()
                if custody == "dead":
                    w.global_flags.add(DEAD)
                    w.countries[host].characters.add(GROVER)
                if custody in ("foreign", "duplicate", "foreign_and_absent_gri"):
                    w.countries["CYA"].characters.add(GROVER)
                if custody == "duplicate": w.countries[host].characters.add(GROVER)
                before_characters = {t: set(c.characters) for t, c in w.countries.items()}
                self.assertFalse(w.valid("local_alive"))
                self.assertFalse(w.valid("can_recover"))
                w.gro("household")
                w.gro("establish")
                self.assertFalse(w.has("mandate"))
                self.assertEqual({t: c.characters for t, c in w.countries.items()}, before_characters)
                self.assertTrue(w.valid("civil_available"))
                w.gro("civil")
                self.assertTrue(w.has("civil_finished"))

    def test_declining_living_local_grover_allows_civil_fallback(self):
        for host, adult in itertools.product(HOSTS, (False, True)):
            with self.subTest(host=host, adult=adult):
                w = self.world(host)
                if adult:
                    w.date = BIRTHDAY + datetime.timedelta(days=1)
                w.begin()
                self.assertTrue(w.valid("local_alive"))
                self.assertTrue(w.valid("civil_available"), "Living local Grover must not force acceptance of the regency")
                characters = {t: set(c.characters) for t, c in w.countries.items()}
                before_actions = copy.deepcopy(w.character_actions)
                w.complete("civil_compact")
                self.assertTrue(w.has("civil_finished"))
                self.assertFalse(w.valid("can_mandate"))
                self.assertEqual({t: c.characters for t, c in w.countries.items()}, characters)
                self.assertEqual(w.character_actions, before_actions)
                self.assertIn(GROVER, w.countries[host].characters)
                self.assertNotIn(DEAD, w.global_flags)
                self.assertFalse(w.countries["GRI"].exists)
                event = w.events["hsm_ver_grover.9"]
                self.assertTrue(w.check(event.get("trigger"), host))
                descriptions = [n.get("text") for n in event.all("desc")
                                if w.check(n.get("trigger", []), host)]
                self.assertEqual(descriptions, ["hsm_ver_grover.9.local.d"])
                before = w.snapshot()
                w.gro("civil")
                w.daily()
                self.assertEqual(w.snapshot(), before)

    def test_ai_prefers_mandate_for_local_child_and_adult_but_can_take_civil_fallback(self):
        def weight(w, suffix):
            nodes = w.focuses[P + suffix].get("ai_will_do")
            self.assertTrue(all(n.key in ("factor", "modifier") for n in nodes))
            result = float(one(nodes, "factor").value)
            for modifier in (n for n in nodes if n.key == "modifier"):
                factor = float(one(modifier.children, "factor").value)
                if w.check([n for n in modifier.children if n.key != "factor"], w.host):
                    result *= factor
            return result

        for host, adult in itertools.product(HOSTS, (False, True)):
            with self.subTest(host=host, adult=adult):
                w = self.world(host).begin()
                if adult:
                    w.date = BIRTHDAY + datetime.timedelta(days=1)
                self.assertTrue(w.valid("can_mandate"))
                self.assertTrue(w.valid("civil_available"))
                self.assertGreater(weight(w, "mandate"), weight(w, "civil_compact"))
                self.assertEqual(weight(w, "civil_compact"), 0)
                w.countries[host].characters.discard(GROVER)
                self.assertFalse(w.valid("can_mandate"))
                self.assertTrue(w.valid("civil_available"))
                self.assertGreater(weight(w, "civil_compact"), 0)

    def test_unknown_executable_operations_raise_in_all_scopes(self):
        w = self.world()
        for scope in (w.host, w.state_ids["382"]):
            for operation in (w.check, w.run):
                with self.assertRaises(AssertionError):
                    operation(parse("unsupported_grover_operation = yes"), scope)


class Programme(Fixtures):
    def test_household_retry_cooldown_and_category_visibility(self):
        category = one(read(MOD / "common/decisions/categories/HSM_VER_grover.txt"), P + "category")
        decisions = one(read(MOD / "common/decisions/HSM_VER_grover.txt"), P + "category")
        retry = one(decisions.children, P + "household_retry_decision")
        for host in HOSTS:
            w = self.world(host).begin()
            self.assertTrue(w.check(category.get("allowed"), host))
            self.assertTrue(w.check(category.get("visible"), host))
            self.assertFalse(w.check(retry.get("available"), host))
            w.advance_days(89)
            self.assertFalse(w.check(retry.get("available"), host))
            w.advance_days(1)
            self.assertTrue(w.check(retry.get("available"), host))
            w.run(retry.get("complete_effect"), host)
            self.assertFalse(w.check(retry.get("available"), host))
            w.complete("mandate")
            self.assertFalse(w.check(retry.get("visible"), host))

    def test_expired_choice_is_requeued_by_actual_daily_hook(self):
        for host in HOSTS:
            w = self.world(host).mandate()
            w.complete("lessons")
            w.advance_days(1)
            self.assertTrue(w.deliver("hsm_ver_grover.4", host))
            w.advance_days(34)
            self.assertFalse(w.has("lessons_pending"))
            w.daily()
            self.assertTrue(w.has("lessons_pending"))
            self.assertEqual(sum(p[2] == "hsm_ver_grover.4" for p in w.scheduled), 1)
            before = w.snapshot()
            w.daily()
            self.assertEqual(w.snapshot(), before)

    def test_interrupted_close_decision_finishes_civil_once_without_new_character(self):
        decisions = one(read(MOD / "common/decisions/HSM_VER_grover.txt"), P + "category")
        close = one(decisions.children, P + "close_interrupted")
        for host in HOSTS:
            w = self.world(host).mandate()
            w.global_flags.add(DEAD)
            w.daily()
            self.assertTrue(w.check(close.get("visible"), host))
            self.assertTrue(w.check(close.get("available"), host))
            before_characters = copy.deepcopy(w.character_actions)
            w.run(close.get("complete_effect"), host)
            self.assertTrue(w.has("civil_finished"))
            self.assertEqual(w.character_actions, before_characters)
            before = w.snapshot()
            w.run(close.get("complete_effect"), host)
            self.assertEqual(w.snapshot(), before)

    def test_mandate_and_release_recheck_each_home_state(self):
        for host in HOSTS:
            started = self.world(host).begin()
            prepared = self.world(host).prepare()
            prepared.date = BIRTHDAY + datetime.timedelta(days=1)
            for template, gate, effect in ((started, "can_mandate", "establish"), (prepared, "can_release", "release_empire")):
                for sid, attr in itertools.product(HOME, ("owner", "controller")):
                    with self.subTest(host=host, gate=gate, sid=sid, attr=attr):
                        w = copy.deepcopy(template)
                        setattr(w.state_ids[sid], attr, "CYA")
                        self.assertFalse(w.valid(gate))
                        before = w.snapshot()
                        w.gro(effect)
                        self.assertEqual(w.snapshot(), before)

    def test_staged_cores_mark_only_new_cores_and_never_verenia(self):
        for host in HOSTS:
            w = self.world(host).mandate()
            preexisting = {"382", "674"}
            for sid in preexisting: w.state_ids[sid].cores.add(host)
            before = {sid: set(s.cores) for sid, s in w.state_ids.items()}
            w.gro("core_capital")
            for sid, state in w.state_ids.items():
                expected = sid in HEART & CAPITAL_DISTRICT and sid not in preexisting
                self.assertEqual(P + "core_" + host in state.flags, expected, sid)
            w.gro("core_districts")
            for sid, state in w.state_ids.items():
                self.assertEqual(P + "core_" + host in state.flags, sid in HEART - preexisting, sid)
                self.assertEqual(state.cores, before[sid] | ({host} if sid in HEART else set()), sid)
            before_repeat = w.snapshot()
            w.gro("core_capital")
            w.gro("core_districts")
            self.assertEqual(w.snapshot(), before_repeat)

    def test_cleanup_removes_only_programme_cores_even_after_ownership_loss(self):
        for host in HOSTS:
            w = self.world(host).mandate()
            w.state_ids["382"].cores.add(host)
            before = {sid: set(s.cores) for sid, s in w.state_ids.items()}
            w.gro("core_capital")
            w.gro("core_districts")
            w.state_ids["674"].owner = w.state_ids["674"].controller = "CYA"
            w.gro("interrupt")
            self.assertTrue(w.has("interrupted"))
            self.assertFalse(w.has("mandate"))
            for sid, state in w.state_ids.items():
                self.assertEqual(state.cores, before[sid], sid)
                self.assertNotIn(P + "core_" + host, state.flags)
            self.assertEqual(w.countries[host].cosmetic, "HSM_VER_UNIFIED")
            self.assertFalse(w.countries[host].ideas & {P + "guardianship", P + "transition"})
            before_repeat = w.snapshot()
            w.gro("interrupt")
            self.assertEqual(w.snapshot(), before_repeat)

    def test_factories_and_slot_fallback_are_once_only_and_require_actual_home_control(self):
        for host, capacity in itertools.product(HOSTS, (0, 20)):
            w = self.world(host).mandate()
            for sid in ("391", "401"): w.state_ids[sid].capacity = capacity
            w.state_ids["401"].controller = "CYA"
            w.gro("build_home")
            self.assertFalse(w.has("home_built"))
            w.state_ids["401"].controller = host
            w.gro("build_home")
            self.assertTrue(w.has("home_built"))
            for sid in ("391", "401"):
                self.assertEqual(w.state_ids[sid].buildings.get("industrial_complex", 0), int(capacity > 0))
            bonuses = [n for b in w.countries[host].bonuses for n in b if n.key == "name" and n.value == P + "home_workshops"]
            self.assertEqual(len(bonuses), 2 if capacity == 0 else 0)
            before = w.snapshot()
            w.gro("build_home")
            self.assertEqual(w.snapshot(), before)

    def test_each_choice_requires_unexpired_pending_and_rejects_replay(self):
        for host, (stage, queue, event, options) in itertools.product(HOSTS, CHOICES):
            for choice in range(len(options)):
                with self.subTest(host=host, stage=stage, choice=choice):
                    w = self.world(host).mandate()
                    w.countries[host].flags.update(P + x + "_done" for x in ("lessons", "petition", "service") if x != stage)
                    before = w.snapshot()
                    w.choose(f"hsm_ver_grover.{event}", choice, host)
                    self.assertEqual(w.snapshot(), before)
                    w.gro(queue)
                    self.assertTrue(w.has(stage + "_pending"))
                    queued = w.snapshot()
                    w.gro(queue)
                    self.assertEqual(w.snapshot(), queued)
                    expired = copy.deepcopy(w)
                    expired.advance_days(35)
                    before_expired = expired.snapshot()
                    expired.choose(f"hsm_ver_grover.{event}", choice, host)
                    self.assertEqual(expired.snapshot(), before_expired)
                    w.advance_days(34)
                    w.choose(f"hsm_ver_grover.{event}", choice, host)
                    self.assertTrue(w.has(stage + "_done"))
                    self.assertFalse(w.has(stage + "_pending"))
                    before_replay = w.snapshot()
                    for option in range(len(options)):
                        w.choose(f"hsm_ver_grover.{event}", option, host)
                    w.gro(queue)
                    self.assertEqual(w.snapshot(), before_replay)

    def test_interruption_closes_pending_choices_and_cleans_core_provenance(self):
        for host, reason in itertools.product(HOSTS, ("death", "custody", "duplicate", "government", "subject", "gri", "annex")):
            with self.subTest(host=host, reason=reason):
                w = self.world(host).mandate()
                w.gro("core_capital")
                w.gro("core_districts")
                w.complete("lessons")
                if reason == "death": w.global_flags.add(DEAD)
                elif reason == "custody": w.countries[host].characters.discard(GROVER)
                elif reason == "duplicate": w.countries["CYA"].characters.add(GROVER)
                elif reason == "government": w.countries[host].government = "fascism"
                elif reason == "subject": w.countries[host].subject = True
                elif reason == "gri": w.countries["GRI"].exists = True
                else:
                    w.root, w.sender = "CYA", host
                    w.run(w.gro_hooks["on_annex"], "CYA")
                if reason != "annex": w.daily()
                self.assertTrue(w.has("interrupted"))
                self.assertFalse(any(P + "core_" + host in s.flags for s in w.states))
                before = w.snapshot()
                w.choose("hsm_ver_grover.4", 0, host)
                self.assertEqual(w.snapshot(), before)


class Handover(Fixtures):
    def test_release_cannot_skip_preparation_or_signed_articles(self):
        for host, missing in itertools.product(HOSTS, ("prepared", "articles_done")):
            w = self.world(host).prepare()
            w.date = BIRTHDAY + datetime.timedelta(days=1)
            w.countries[host].flags.discard(P + missing)
            self.assertFalse(w.valid("can_release"))
            before = w.snapshot()
            w.gro("release_empire")
            self.assertEqual(w.snapshot(), before)

    def test_adulthood_waits_for_peace_preparation_and_all_38_states(self):
        for host in HOSTS:
            w = self.world(host).prepare()
            w.date = BIRTHDAY
            w.daily()
            self.assertFalse(w.has("completed"))
            w.date += datetime.timedelta(days=1)
            w.countries[host].war = True
            w.daily()
            self.assertTrue(w.has("adult_acknowledged"))
            self.assertIn(P + "transition", w.countries[host].ideas)
            self.assertNotIn(P + "guardianship", w.countries[host].ideas)
            self.assertFalse(w.has("completed"))
            w.countries[host].war = False
            for sid in sorted(HEART):
                w.state_ids[sid].controller = "CYA"
                self.assertFalse(w.valid("can_release"), sid)
                w.state_ids[sid].controller = host
            w.daily()
            self.assertTrue(w.has("completed"))

    def test_exact_38_transfer_preserves_other_owners_and_preexisting_host_cores(self):
        for host in HOSTS:
            w = self.world(host)
            w.state_ids["382"].cores.add(host)
            for sid in VERENIA | {"1", "75"}:
                w.state_ids[sid].cores.add("GRI")
                w.state_ids[sid].claims.add("GRI")
            before_cores = {sid: set(s.cores) for sid, s in w.state_ids.items()}
            before_owners = {sid: (s.owner, s.controller) for sid, s in w.state_ids.items()}
            w.prepare()
            w.date = BIRTHDAY + datetime.timedelta(days=1)
            w.daily()
            self.assertCountEqual([sid for sid, _, _ in w.state_transfers], HEART)
            for sid, state in w.state_ids.items():
                expected_owner = ("GRI", "GRI") if sid in HEART else before_owners[sid]
                self.assertEqual((state.owner, state.controller), expected_owner, sid)
                expected_cores = before_cores[sid] | {"GRI"} if sid in HEART else before_cores[sid] - {"GRI"} if sid in VERENIA else before_cores[sid]
                self.assertEqual(state.cores, expected_cores, sid)
                self.assertNotIn(P + "core_" + host, state.flags)
            self.assertEqual(w.countries[host].capital, "401" if host == "ERI" else "391")
            self.assertEqual(w.countries["GRI"].capital, "382")
            self.assertTrue(all("GRI" not in w.state_ids[s].claims for s in VERENIA))
            self.assertIn("GRI", w.state_ids["1"].claims)

    def test_original_character_independence_faction_tree_technology_and_global_identity(self):
        for host, faction_mode in itertools.product(HOSTS, ("none", "leader", "member")):
            with self.subTest(host=host, faction=faction_mode):
                w = self.world(host).prepare()
                c, gri = w.countries[host], w.countries["GRI"]
                if faction_mode != "none":
                    c.faction = "existing_alliance"
                    c.faction_leader = faction_mode == "leader"
                    w.countries["CYA"].faction = c.faction
                    w.countries["CYA"].faction_leader = faction_mode == "member"
                gri.subject, gri.overlord = True, "CYA"
                gri.focuses = {"old_imperial_focus"}
                gri.goals = {(kind, target) for kind, target in itertools.product(("annex_everything", "take_state_focus"), (*HOSTS, "AVI", "CYA"))}
                w.date = BIRTHDAY + datetime.timedelta(days=1)
                w.daily()
                self.assertTrue(gri.exists)
                self.assertFalse(gri.subject)
                self.assertFalse(c.subject)
                self.assertEqual(gri.overlord, "")
                self.assertTrue(c.faction)
                self.assertEqual(c.faction, gri.faction)
                self.assertEqual(gri.leader, GROVER)
                self.assertEqual([t for t, cc in w.countries.items() if GROVER in cc.characters], ["GRI"])
                self.assertEqual(w.character_actions[0], ("set_nationality", GROVER, "GRI", host))
                self.assertIn(("set_nationality", GROVER, host, "GRI"), w.character_actions)
                self.assertFalse(any(a[0] == "recruit_character" for a in w.character_actions))
                self.assertEqual(gri.focus_tree, P + "restored_empire")
                self.assertEqual(len(w.tree_loads), 1)
                self.assertFalse(gri.focuses)
                self.assertEqual(gri.technology, c.technology)
                self.assertEqual(w.global_targets["griffonian_empire"], "GRI")
                self.assertEqual(w.global_variables["global.griffonian_empire_var"], "GRI")
                self.assertEqual(gri.goals, {("annex_everything", "CYA"), ("take_state_focus", "CYA")})
                self.assertTrue(w.valid("partnership", host))
                self.assertTrue(w.valid("partnership", "GRI"))

    def test_army_fraction_and_all_final_rewards_happen_once(self):
        for host in HOSTS:
            w = self.world(host).prepare()
            officers = set(w.countries[host].officers)
            w.date = BIRTHDAY + datetime.timedelta(days=1)
            w.daily()
            self.assertEqual(w.countries[host].forces, {"army": 30, "air": 150, "navy": 12, "stockpile": 300})
            self.assertEqual(w.countries["GRI"].forces, {"army": 10, "air": 50, "navy": 0, "stockpile": 100})
            self.assertEqual(w.countries[host].officers, officers)
            self.assertFalse(w.countries["GRI"].officers)
            self.assertEqual(len(w.unit_transfers), 1)
            for tag in (host, "GRI"):
                for name in ("common_market", "joint_defence"):
                    c = w.countries[tag]
                    self.assertTrue(P + name in c.ideas or "HSM_VER_SP_owned_" + P + name in c.flags)
            before = w.snapshot()
            for _ in range(3):
                w.daily()
                w.gro("release_empire")
            self.assertEqual(w.snapshot(), before)

    def test_existing_gri_is_never_overwritten(self):
        for host in HOSTS:
            w = self.world(host).prepare()
            w.date = BIRTHDAY + datetime.timedelta(days=1)
            gri = w.countries["GRI"]
            gri.exists = True
            gri.leader, gri.government, gri.cosmetic = "other_ruler", "fascism", "OTHER_GRI"
            before_gri = copy.deepcopy(vars(gri))
            before_states = {s.sid: (s.owner, s.controller) for s in w.states}
            w.gro("release_empire")
            w.daily()
            self.assertEqual(vars(gri), before_gri)
            self.assertEqual({s.sid: (s.owner, s.controller) for s in w.states}, before_states)
            self.assertFalse(w.unit_transfers)
            self.assertFalse(w.tree_loads)
            self.assertTrue(w.has("interrupted"))

    def test_all_route_and_choice_memories_survive_in_gri_and_select_accession_prose(self):
        for host, route, choices in itertools.product(HOSTS, ("diplomatic", "military"), itertools.product((0, 1), repeat=3)):
            with self.subTest(host=host, route=route, choices=choices):
                w = self.world(host, route).prepare(choices)
                w.date = BIRTHDAY + datetime.timedelta(days=1)
                w.daily()
                self.assertTrue(w.has(host.lower() + "_" + route, "GRI"))
                for index, (_, _, _, options) in enumerate(CHOICES[:3]):
                    self.assertTrue(w.has(options[choices[index]], "GRI"))
                    self.assertFalse(w.has(options[1 - choices[index]], "GRI"))
                w.advance_days(2)
                self.assertTrue(w.deliver("hsm_ver_grover.11", "GRI"))
                texts = [n.get("text") for n in w.events["hsm_ver_grover.11"].all("desc")
                         if w.check(n.get("trigger", []), "GRI")]
                suffix = "open" if choices[0] == 0 else "filtered"
                expected = "hsm_ver_grover.11." + suffix + ("_law" if choices[1] == 0 else "_patron") + ("_logistics" if choices[2] == 0 else "_command") + ".d"
                self.assertEqual(texts, [expected])


class CourtDescriptions(Fixtures):
    SCENES = (1, 4, 5, 6, 7, 10)

    def couple(self, host):
        # Fixture the established joint government; evaluate real ROM predicates.
        w = self.world(host)
        rival = "EYR" if host == "ERI" else "ERI"
        w.countries[rival].exists = False
        c = w.countries[host]
        c.flags.update({"HSM_VER_UNI_diplomatic", "HSM_VER_UNI_president_" + host,
                        "HSM_VER_UNI_absorbed_" + rival, "HSM_VER_ROM_crowned"})
        c.leader = "HSM_VER_rosaline_and_montague"
        c.characters.add(c.leader)
        self.assertTrue(w.test("HSM_VER_ROM_government", host))
        return w

    def selected(self, w, number):
        return [n.get("text") for n in w.events[f"hsm_ver_grover.{number}"].all("desc")
                if w.check(n.get("trigger", []), w.host)]

    def test_original_dukes_keep_exactly_one_description_on_all_four_routes(self):
        for host, route in itertools.product(HOSTS, ("diplomatic", "military")):
            w = self.world(host, route)
            w.gro("start")
            self.assertFalse(w.test("HSM_VER_ROM_government", host))
            for number in self.SCENES:
                with self.subTest(host=host, route=route, scene=number):
                    self.assertEqual(self.selected(w, number),
                                     [f"hsm_ver_grover.{number}.{host.lower()}_{route}.d"])

    def test_joint_government_selects_exactly_one_shared_scene_for_both_founders_and_ages(self):
        for host, adult in itertools.product(HOSTS, (False, True)):
            w = self.couple(host)
            if adult:
                w.date = BIRTHDAY + datetime.timedelta(days=1)
            w.gro("start")
            for number in self.SCENES:
                with self.subTest(host=host, adult=adult, scene=number):
                    self.assertEqual(self.selected(w, number), [f"hsm_ver_grover.{number}.romance.d"])

    def test_stale_romance_memories_do_not_select_joint_government_prose(self):
        for host, bad in itertools.product(HOSTS, ("leader", "crowned", "government", "subject", "founder", "rival")):
            w = self.couple(host)
            w.gro("start")
            c = w.countries[host]
            if bad == "leader": c.leader = "successor"
            elif bad == "crowned": c.flags.remove("HSM_VER_ROM_crowned")
            elif bad == "government": c.government = "fascism"
            elif bad == "subject": c.subject = True
            elif bad == "founder": c.flags.remove("HSM_VER_UNI_founded")
            else: w.countries["EYR" if host == "ERI" else "ERI"].exists = True
            self.assertFalse(w.test("HSM_VER_ROM_government", host))
            for number in self.SCENES:
                with self.subTest(host=host, bad=bad, scene=number):
                    self.assertEqual(self.selected(w, number),
                                     [f"hsm_ver_grover.{number}.{host.lower()}_diplomatic.d"])

    def test_joint_handover_description_survives_actual_independent_restoration(self):
        for host in HOSTS:
            with self.subTest(host=host):
                w = self.couple(host).prepare()
                w.date = BIRTHDAY + datetime.timedelta(days=1)
                w.gro("maintain")
                self.assertTrue(w.countries["GRI"].exists)
                self.assertFalse(w.countries["GRI"].subject)
                event = w.events["hsm_ver_grover.10"]
                self.assertTrue(w.check(event.get("trigger"), host))
                self.assertEqual(self.selected(w, 10), ["hsm_ver_grover.10.romance.d"])


class Integration(Fixtures):
    def test_companion_files_and_all_scripted_event_idea_focus_and_tree_references(self):
        required = [MOD / folder / "HSM_VER_grover.txt" for folder in (
            "common/scripted_triggers", "common/scripted_effects", "common/national_focus", "events",
            "common/ideas", "common/on_actions", "common/decisions", "common/decisions/categories")]
        required += [MOD / folder / "HSM_VER_grover_restored.txt" for folder in ("events", "common/national_focus", "common/ideas")]
        self.assertTrue(all(p.is_file() for p in required), [str(p) for p in required if not p.is_file()])
        w = self.world()
        definitions = set(w.effects) | set(w.triggers)
        ideas = {n.key for p in (MOD / "common/ideas").glob("HSM_VER_grover*.txt")
                 for container in read(p) for group in container.children for n in group.children}
        files = {p: read(p) for p in required}
        tree_ids = {n.get("id") for p in (MOD / "common/national_focus").glob("*.txt") for n in read(p) if n.key == "focus_tree"}
        for path, nodes in files.items():
            with self.subTest(path=path.name, folder=path.parent.name):
                self.assertTrue(nodes)
                for n in walk(nodes):
                    self.assertNotIn(n.op, (">=", "<=", "!="), f"Unsupported inline operator {n.key}")
                    if n.key.startswith("HSM_") and n.value in ("yes", "no"):
                        self.assertIn(n.key, definitions)
                    if n.key == "country_event" and n.children and not n.get("is_triggered_only"):
                        self.assertIn(n.get("id"), w.events)
                    if n.key in ("focus", "shared_focus") and not n.children:
                        self.assertIn(n.value, w.focuses)
                    if n.key == "load_focus_tree":
                        self.assertIn(n.get("tree"), tree_ids)
                    if n.key in ("add_ideas", "remove_ideas") and isinstance(n.value, str) and n.value.startswith(P):
                        self.assertIn(n.value, ideas)

    def test_grover_flag_references_have_production_writers(self):
        nodes = [n for p in MOD.rglob("HSM_VER_grover*.txt") for n in walk(read(p))]
        writes = {n.get("flag") if n.children else n.value for n in nodes if n.key == "set_country_flag"}
        reads = {n.value for n in nodes if n.key == "has_country_flag" and str(n.value).startswith(P)}
        self.assertFalse(reads - writes, f"Unwritten Grover flags: {sorted(reads - writes)}")

    def test_host_tree_imports_and_restored_tree_are_explicit(self):
        for path in ("HSM_ERI.txt", "HSM_VER_eyrie.txt"):
            nodes = read(MOD / "common/national_focus" / path)
            self.assertTrue(any(n.key == "shared_focus" and n.value == P + "open_court" for n in walk(nodes)))
        trees = [n for n in read(MOD / "common/national_focus/HSM_VER_grover_restored.txt") if n.key == "focus_tree"]
        self.assertEqual(len(trees), 1)
        self.assertEqual(trees[0].get("id"), P + "restored_empire")
        self.assertEqual(trees[0].get("default"), "no")
        for focus in trees[0].all("focus"):
            self.assertNotEqual(focus.get("repeatable"), "yes")

    def test_installed_engine_documents_the_new_state_and_transfer_operations(self):
        documented = {
            "effects": ("transfer_state_to", "transfer_units_fraction", "set_nationality", "inherit_technology",
                        "add_core_of", "remove_core_of", "remove_claim_by", "load_focus_tree", "set_capital"),
            "triggers": ("state", "region", "is_owned_and_controlled_by", "has_character", "original_tag"),
        }
        for kind, names in documented.items():
            text = (OPT.game / "documentation" / f"{kind}_documentation.md").read_text(encoding="utf-8-sig")
            for name in names:
                self.assertIn("## " + name + "\n", text)

    def test_english_russian_localisation_bom_parity_and_full_references(self):
        all_keys = {}
        for language in ("english", "russian"):
            paths = [MOD / "localisation" / language / f"HSM_VER_grover{suffix}_l_{language}.yml"
                     for suffix in ("", "_restored", "_romance")]
            self.assertTrue(all(p.is_file() for p in paths), f"Waiting for Grover localisation: {language}")
            keys = {}
            for path in paths:
                self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"), path)
                for line in path.read_text(encoding="utf-8-sig").splitlines():
                    if not line.strip() or line.lstrip().startswith(("#", "l_")):
                        continue
                    match = re.fullmatch(r'\s*([A-Za-z0-9_.]+):\d+\s+"((?:\\.|[^"\\])*)"\s*', line)
                    self.assertIsNotNone(match, f"Malformed localisation: {path.name}: {line}")
                    key, value = match.groups()
                    self.assertNotIn(key, keys, f"Duplicate {language} key: {key}")
                    self.assertTrue(value.strip(), key)
                    keys[key] = value
            all_keys[language] = set(keys)
        self.assertEqual(all_keys["english"], all_keys["russian"])
        required = set()
        for path in MOD.rglob("HSM_VER_grover*.txt"):
            for n in walk(read(path)):
                if n.key in ("focus", "shared_focus") and n.children:
                    required.update((n.get("id"), n.get("id") + "_desc"))
                if n.key in ("name", "title", "text", "desc", "tooltip", "custom_effect_tooltip", "create_faction"):
                    if isinstance(n.value, str) and n.value.startswith((P, "hsm_ver_grover")):
                        required.add(n.value)
        for path in (MOD / "common/ideas").glob("HSM_VER_grover*.txt"):
            for container in read(path):
                for group in container.children:
                    for idea in group.children:
                        required.update((idea.key, idea.key + "_desc"))
        decisions = one(read(MOD / "common/decisions/HSM_VER_grover.txt"), P + "category")
        for key in (P + "category", *(n.key for n in decisions.children)):
            required.update((key, key + "_desc"))
        required.update("HSM_VER_REGENCY" + ideology + suffix
                        for ideology in ("", "_neutrality", "_democratic", "_fascism", "_communism")
                        for suffix in ("", "_DEF", "_ADJ"))
        self.assertFalse(required - all_keys["english"], sorted(required - all_keys["english"]))

    def test_restored_focus_rewards_execute_without_releasing_more_land(self):
        order = ("oath", "reconstruction", "charter", "embassies", "workshops", "courts", "defence", "university", "arsenals", "peace")
        for host in HOSTS:
            w = self.world(host).prepare()
            w.date = BIRTHDAY + datetime.timedelta(days=1)
            w.daily()
            before_land = copy.deepcopy(w.state_transfers)
            before_characters = copy.deepcopy(w.character_actions)
            for suffix in order:
                w.complete("restored_" + suffix, "GRI")
                with self.assertRaises(AssertionError):
                    w.complete("restored_" + suffix, "GRI")
            self.assertEqual(w.state_transfers, before_land)
            self.assertEqual(w.character_actions, before_characters)
            self.assertEqual(w.countries["GRI"].research_slots, 4)
            self.assertEqual(w.countries["GRI"].army_experience, 50)

    def test_spirit_components_execute_real_arithmetic_and_keep_gri_native(self):
        names = {P + "common_market", P + "joint_defence"}
        self.assertTrue(names <= set(SP["COMPONENTS"]), "Spirit source/generator integration is incomplete")
        for host in HOSTS:
            w = self.world(host).prepare()
            w.date = BIRTHDAY + datetime.timedelta(days=1)
            w.daily()
            c = w.countries[host]
            self.assertTrue(all("HSM_VER_SP_owned_" + name in c.flags for name in names))
            SP["LedgerAssertions"].assertValues(self, w, host, SP["owned"](c))
            self.assertIn(SP["DYNAMIC"], c.dynamic_modifiers)
            self.assertFalse(c.ideas & names)
            gri = w.countries["GRI"]
            self.assertTrue(names <= gri.ideas)
            self.assertFalse(names & SP["owned"](gri))
            self.assertNotIn(SP["DYNAMIC"], gri.dynamic_modifiers)
        for name in ("guardianship", "transition", "open_court_legacy", "managed_court_legacy", "rule_of_law", "patrons_legacy"):
            self.assertNotIn(P + name, SP["COMPONENTS"])


def without_native_guards(nodes):
    """Undo only the new protection wrappers for the pre-Grover CYA delta audit."""
    result = []
    limits = [parse(f"hidden_trigger = {{ {guard} = yes }}") for guard in NATIVE_GUARDS]
    for node in nodes:
        if node.key in NATIVE_GUARDS:
            if node.value != "yes":
                raise AssertionError(f"Unexpected native guard polarity: {node.key}")
            continue
        if node.key == "if" and node.get("limit") in limits:
            result.extend(without_native_guards([c for c in node.children if c.key != "limit"]))
            continue
        node = copy.deepcopy(node)
        if isinstance(node.value, list):
            node.value = without_native_guards(node.children)
        if node.key == "trigger" and not node.children:
            continue
        result.append(node)
    return result


class NativeProtection(Fixtures):
    def native_events(self, path):
        return {n.get("id"): n for n in read(MOD / path) if n.key == "country_event"}

    def protected_world(self, holder, mandated=False):
        if holder in HOSTS:
            w = self.world(holder).begin()
            if mandated:
                w.complete("mandate")
            return w
        w = self.world()
        w.countries["GRI"].exists = True
        w.countries["GRI"].flags.add(P + "restored")
        return w

    def test_guards_allow_normal_native_paths_and_detect_each_actual_protected_household(self):
        w = self.world()
        for root in ("GRI", "ERI", "EYR", "CYA"):
            w.root, w.sender = root, "GRI"
            for guard in NATIVE_GUARDS:
                self.assertTrue(w.check(parse(guard + " = yes"), root), (root, guard))
        for holder, mandated, root in itertools.product(("GRI", *HOSTS), (False, True), ("GRI", *HOSTS, "CYA")):
            with self.subTest(holder=holder, mandated=mandated, root=root):
                w = self.protected_world(holder, mandated)
                w.root, w.sender = root, "GRI"
                self.assertFalse(w.check(parse(P + "native_household_allowed = yes"), root))
                self.assertFalse(w.check(parse(P + "native_childhood_allowed = yes"), root))
                w.countries[holder].characters.discard(GROVER)
                self.assertTrue(w.check(parse(P + "native_household_allowed = yes"), root))

    def test_native_event_triggers_and_already_open_options_recheck_protection(self):
        for path, rules in NATIVE_RULES.items():
            events = self.native_events(path)
            for event_id, guard in rules.items():
                holders = ("GRI", "ERI", "EYR") if "Grover_Events" in path else ("GRI",)
                stages = [(holder, mandated) for holder in holders
                          for mandated in ((False, True) if holder in HOSTS else (False,))]
                for holder, mandated in stages:
                    with self.subTest(event=event_id, holder=holder, mandated=mandated):
                        w = self.protected_world(holder, mandated)
                        root = "CYA" if event_id == "imperial.70" or guard.endswith("household_allowed") else "GRI"
                        w.root, w.sender = root, "GRI"
                        event = events[event_id]
                        self.assertEqual(one(event.get("trigger"), guard).value, "yes")
                        self.assertFalse(w.check(event.get("trigger"), root))
                        before = w.snapshot()
                        w.run(event.get("immediate", []), root)
                        for option in event.all("option"):
                            w.run([n for n in option.children if n.key not in OPTION_METADATA], root)
                        self.assertEqual(w.snapshot(), before)
                        self.assertNotIn(DEAD, w.global_flags)
                        self.assertEqual([t for t, c in w.countries.items() if GROVER in c.characters], [holder])

    def test_native_decisions_and_reichsmandates_reject_restored_empire(self):
        w = self.world()
        gri = w.countries["GRI"]
        gri.exists = True
        gri.flags.add(P + "restored")
        w.root, w.sender = "GRI", "ERI"
        wanted = {"GRI_demand_land", "GRI_demand_frontier", "GRI_offer_peace"}
        decisions = [n for c in read(MOD / "common/decisions/GRI_decisions.txt") for n in c.children if n.key in wanted]
        self.assertEqual({n.key for n in decisions}, wanted)
        for decision in decisions:
            self.assertFalse(w.check(decision.get("visible"), "GRI"))
            if decision.get("target_root_trigger"):
                self.assertFalse(w.check(decision.get("target_root_trigger"), "GRI"))
            before = w.snapshot()
            for key in ("complete_effect", "remove_effect", "cancel_effect"):
                w.run(decision.get(key, []), "GRI")
            self.assertEqual(w.snapshot(), before)
        trigger = one(read(MOD / "common/scripted_triggers/EAW_GRI_scripted_triggers.txt"), "GRI_has_access_to_reichsmandates")
        self.assertFalse(w.check(trigger.children, "GRI"))
        gri.flags.discard(P + "restored")
        self.assertTrue(w.check(trigger.children, "GRI"))
        w.countries["CYA"].flags.add("holds_griffon_capital")
        self.assertTrue(w.check(trigger.children, "CYA"))

    def test_unguarded_native_ast_matches_prior_cya_overrides_or_installed_source(self):
        paths = [*NATIVE_RULES, "common/decisions/GRI_decisions.txt", "common/scripted_triggers/EAW_GRI_scripted_triggers.txt"]
        for relative in paths:
            with self.subTest(path=relative):
                if relative == "events/Grover_Events.txt":
                    before = read(OPT.eaw / relative)
                else:
                    original = subprocess.run(["git", "show", f"{PRE_GROVER_REF}:mod/HoISubmod/{relative}"],
                                              cwd=BASE["ROOT"], capture_output=True, check=True, encoding="utf-8")
                    before = parse(original.stdout.lstrip("\ufeff"))
                self.assertEqual(without_native_guards(read(MOD / relative)), without_native_guards(before))

    def test_guard_builder_check_is_read_only_and_idempotent(self):
        paths = [MOD / p for p in (*NATIVE_RULES, "common/decisions/GRI_decisions.txt", "common/scripted_triggers/EAW_GRI_scripted_triggers.txt")]
        before = {p: p.read_bytes() for p in paths}
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(Path(__file__).with_name("Build-VereniaGroverGuards.py")), "--check"],
                                cwd=BASE["ROOT"], capture_output=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("0 stale native guard files", result.stdout)
        self.assertEqual({p: p.read_bytes() for p in paths}, before)


if __name__ == "__main__":
    unittest.main(argv=[__file__, *BASE["REST"]], verbosity=2)
