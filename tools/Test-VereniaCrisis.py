"""Production-script fixtures for VERENIA_CRISIS_CONTRACT.md, not an HOI4 emulator.

Run with python -B -X utf8 tools/Test-VereniaCrisis.py [-v] [TestClass.test_name].
Uses the existing parser and Avian fixture. Event delivery, native focus rewards,
and daily hooks are explicit; no crisis policy is implemented in this harness.
The separate engine-contract checks cover PP/pact keywords and comparison syntax
against installed documentation, including source paths not taken by fixtures.
"""
from __future__ import annotations

import copy
import itertools
import operator
import re
import runpy
import unittest
from dataclasses import dataclass
from pathlib import Path

AVIAN = runpy.run_path(str(Path(__file__).with_name("Test-VereniaAvian.py")))
BASE = AVIAN["BASE"]
Node, read, walk, parse = (BASE[k] for k in ("Node", "read", "walk", "parse"))
MOD, OPT, REST = (BASE[k] for k in ("MOD", "OPT", "REST"))
HOUSES = ("ERI", "EYR")
PREFIX = "HSM_VER_CR_"
EVENT_PREFIX = "hsm_ver_crisis."
COMPARISONS = {"=": operator.eq, ">": operator.gt, "<": operator.lt}
ENGINE_SOURCES = (
    "common/scripted_triggers/HSM_VER_crisis.txt",
    "common/scripted_effects/HSM_VER_crisis.txt",
    "events/HSM_VER_crisis.txt",
    "events/Avian Events.txt",
)


def documentation_sections(path):
    parts = re.split(r"(?m)^## ([a-z_]+)\s*$", path.read_text(encoding="utf-8-sig"))
    return dict(zip(parts[1::2], parts[2::2]))


def validate_engine_contract(nodes, triggers, effects):
    # This is a bounded regression guard, not a replacement for the engine parser.
    short_ops = set(re.findall(r"check_variable = \{ varname ([=<>]+) ", triggers["check_variable"]))
    assert short_ops == {"=", ">", "<"}, "Installed comparison documentation changed"
    trigger_names = {"political_power", "has_political_power", "check_variable",
                     "has_non_aggression_pact_with"}
    effect_names = {"non_aggression_pact", "create_non_aggression_pact",
                    "remove_non_aggression_pact", "diplomatic_relation"}
    for n in walk(nodes):
        assert n.op in short_ops | {""}, f"Unsupported comparison operator {n.op!r} at {n.key}"
        if n.key in trigger_names:
            assert n.key in triggers, f"Undocumented engine trigger: {n.key}"
        if n.key in effect_names:
            assert n.key in effects, f"Undocumented engine effect: {n.key}"
        if n.key == "check_variable":
            if n.get("var"):
                assert {c.key for c in n.children} <= {"var", "value", "compare", "tooltip"}
                assert n.get("value") != "" and all(c.op == "=" for c in n.children)
                assert n.get("compare") in {
                    "less_than", "less_than_or_equals", "greater_than", "greater_than_or_equals",
                    "equals", "not_equals",
                }, "Unsupported check_variable compare value"
                assert re.search(r"\b" + re.escape(n.get("compare")) + r"\b", triggers["check_variable"])
            else:
                assert len(n.children) == 1, "Malformed shorthand check_variable"
                assert n.children[0].op in short_ops, f"Unsupported comparison operator {n.children[0].op!r}"
                assert not n.children[0].children and n.children[0].value != ""
        if n.key == "diplomatic_relation":
            assert {c.key for c in n.children} == {"country", "relation", "active"}
            assert all(c.op == "=" for c in n.children)
            assert n.get("country") and n.get("relation") == "non_aggression_pact"
            assert n.get("active") in ("yes", "no")


@dataclass(frozen=True)
class Window:
    event_id: str
    recipient: str
    sender: str
    opened: float
    deadline: float | None


class CrisisWorld(AVIAN["AvianWorld"]):
    def __init__(self):
        super().__init__()
        for country in self.countries.values():
            country.overlord = None
            country.variables = {}
            country.idea_days = {}
            country.non_aggression = set()
            country.faction_template = ""
        self.events.update({n.get("id"): n for n in read(MOD / "events/Avian Events.txt")
                            if n.key == "country_event"})
        # Bounded active-party roles from EaW common/characters/AVI.txt.
        self.countries["AVI"].rulers = {"neutrality": "AVI_lady_katrina_avian",
                                        "democratic": "AVI_lady_katrina_avian",
                                        "fascism": "AVI_lady_katrina_avian",
                                        "communism": "AVI_aaron_redtail"}
        self.windows = {}
        self.dlcs = set()
        self.crisis_hooks = {}
        path = MOD / "common/on_actions/HSM_VER_crisis.txt"
        if path.exists():
            for container in read(path):
                for hook in container.children:
                    self.crisis_hooks.setdefault(hook.key, []).extend(hook.get("effect", []))

    def number(self, value, tag):
        try:
            return float(value)
        except ValueError:
            return self.countries[tag].variables.get(value, 0)

    def check(self, nodes, tag="AVI"):
        for n in nodes:
            if n.key == "is_subject_of":
                c = self.countries[tag]
                ok = c.subject and c.overlord == self.resolve(n.value)
            elif n.key == "has_political_power":
                assert n.op in COMPARISONS, f"Unsupported PP comparison operator: {n.op}"
                ok = COMPARISONS[n.op](self.countries[tag].political_power, float(n.value))
            elif n.key == "check_variable":
                assert len(n.children) == 1, "Only native shorthand variable comparisons are modelled"
                comparison = n.children[0]
                assert comparison.op in COMPARISONS, f"Unsupported variable comparison operator: {comparison.op}"
                ok = COMPARISONS[comparison.op](self.number(comparison.key, tag), self.number(comparison.value, tag))
            elif n.key == "has_non_aggression_pact_with":
                ok = self.resolve(n.value) in self.countries[tag].non_aggression
            elif n.key == "has_faction_template":
                ok = self.countries[tag].faction_template == n.value
            elif n.key == "has_dlc":
                ok = n.value in self.dlcs
            elif n.key == "any_other_country":
                ok = any(c.exists and t != tag and self.check(n.children, t)
                         for t, c in self.countries.items())
            else:
                ok = super().check([n], tag)
            if not ok:
                return False
        return True

    def run(self, nodes, tag="AVI"):
        # Dispatch one operation at a time but preserve the whole conditional chain.
        branch_taken = None
        for n in nodes:
            c = self.countries[tag]
            if n.key == "if":
                branch_taken = self.check(n.get("limit", []), tag)
                if branch_taken:
                    self.run([x for x in n.children if x.key != "limit"], tag)
            elif n.key == "else_if":
                assert branch_taken is not None, "else_if without if"
                if not branch_taken and self.check(n.get("limit", []), tag):
                    branch_taken = True
                    self.run([x for x in n.children if x.key != "limit"], tag)
            elif n.key == "else":
                assert branch_taken is not None, "else without if"
                if not branch_taken:
                    self.run(n.children, tag)
                branch_taken = True
            elif n.key in ("add_to_variable", "set_variable"):
                assert {x.key for x in n.children} == {"var", "value"}
                variable, value = n.get("var"), self.number(n.get("value"), tag)
                c.variables[variable] = value + (c.variables.get(variable, 0) if n.key == "add_to_variable" else 0)
            elif n.key == "add_timed_idea":
                c.ideas.add(n.get("idea"))
                c.idea_days[n.get("idea")] = float(n.get("days"))
                self.trace.append((tag, n.key, copy.deepcopy(n.value)))
            elif n.key == "remove_ideas":
                c.ideas.discard(n.value)
                c.idea_days.pop(n.value, None)
            elif n.key == "set_politics":
                assert n.get("ruling_party"), "Political operations outside ruling party are not modelled"
                c.government = n.get("ruling_party")
                if tag == "AVI":
                    c.leader = c.rulers.get(c.government, "")
            elif n.key == "complete_national_focus":
                c.focuses.add(n.value)
            elif n.key == "set_autonomy":
                assert n.get("autonomy_state") in ("autonomy_integrated_puppet", "autonomy_puppet")
                target = self.countries[self.resolve(n.get("target"))]
                target.subject, target.overlord = True, tag
                self.trace.append((tag, n.key, copy.deepcopy(n.value)))
            elif n.key == "annex_country":
                self.annex(tag, self.resolve(n.get("target")))
                self.trace.append((tag, n.key, copy.deepcopy(n.value)))
            elif n.key == "add_country_leader_role":
                if n.get("promote_leader") == "yes":
                    c.leader = n.get("character")
                    role = Node("country_leader", "=", n.get("country_leader"))
                    assert tag == "AVI" and role.get("ideology") == "nazism"
                    c.rulers["fascism"] = c.leader
                self.trace.append((tag, n.key, copy.deepcopy(n.value)))
            elif n.key == "diplomatic_relation":
                assert {x.key for x in n.children} == {"country", "relation", "active"}
                assert n.get("relation") == "non_aggression_pact"
                assert n.get("active") in ("yes", "no")
                target = self.resolve(n.get("country"))
                for left, right in ((tag, target), (target, tag)):
                    partners = self.countries[left].non_aggression
                    partners.add(right) if n.get("active") == "yes" else partners.discard(right)
                self.trace.append((tag, n.key, copy.deepcopy(n.value)))
            elif n.key == "country_event" and not n.children:
                self.run([Node("country_event", "=", [Node("id", "=", n.value)])], tag)
            elif n.key == "dismantle_faction":
                faction = c.faction
                for member in self.countries.values():
                    if member.faction == faction:
                        member.faction, member.faction_leader = "", False
            elif n.key in ("log", "load_focus_tree", "set_party_name", "add_popularity",
                           "add_opinion_modifier", "set_cosmetic_tag"):
                # Presentation/native metadata is recorded, never used to decide crisis outcomes.
                self.trace.append((tag, n.key, copy.deepcopy(n.value)))
            elif n.key in ("AVI_lady_katrina_avian", "AVI_trubach_von_zypressen",
                           "AVI_aaron_redtail", "ERI_duke_vincent_erie", "EYR_duke_iovinus_eyrie"):
                assert all(x.key in ("retire", "add_trait") for x in n.children)
                if n.get("retire") == "yes" and c.leader == n.key:
                    c.leader = ""
                if n.get("retire") == "yes" and tag == "AVI":
                    c.rulers = {party: ruler for party, ruler in c.rulers.items() if ruler != n.key}
                self.trace.append((tag, n.key, copy.deepcopy(n.value)))
            else:
                super().run([n], tag)

    def advance_days(self, days):
        assert days >= 0
        super().advance_days(days)
        for c in self.countries.values():
            for idea in list(c.idea_days):
                c.idea_days[idea] -= days
                if c.idea_days[idea] <= 0:
                    c.ideas.discard(idea)
                    del c.idea_days[idea]

    def open_event(self, event_id, tag, sender=None):
        self.root, self.sender = tag, sender or tag
        event = self.events[event_id]
        if not self.countries[tag].exists or not self.check(event.get("trigger", []), tag):
            return False
        self.run(event.get("immediate", []), tag)
        timeout = event.get("timeout_days")
        window = Window(event_id, tag, self.sender, self.day,
                        self.day + float(timeout) if timeout else None)
        self.windows[tag, event_id] = window
        return window

    def deliver(self, event_id, tag):
        packet = next((p for p in self.scheduled if p[1:3] == (tag, event_id) and p[0] <= self.day), None)
        assert packet is not None, f"No due {event_id} for {tag} on day {self.day}"
        self.scheduled.remove(packet)
        return self.open_event(event_id, tag, packet[3])

    def choose_window(self, window, index=0, stale=False):
        assert isinstance(window, Window), "Event did not open"
        if not stale and window.deadline is not None:
            assert self.day <= window.deadline, "Event window has expired"
        self.root, self.sender = window.recipient, window.sender
        # stale=True probes option-level guards, bypassing only UI expiry/visibility.
        self.choose(window.event_id, index, window.recipient)

    def option_available(self, window, index):
        self.root, self.sender = window.recipient, window.sender
        return self.check(self.events[window.event_id].all("option")[index].get("trigger", []), window.recipient)

    def option_index(self, window, name):
        matches = [i for i, option in enumerate(self.events[window.event_id].all("option")) if option.get("name") == name]
        assert len(matches) == 1, (window.event_id, name)
        return matches[0]

    def choose_named(self, window, name, stale=False):
        self.choose_window(window, self.option_index(window, name), stale=stale)

    def option_weight(self, window, index):
        self.root, self.sender = window.recipient, window.sender
        chance = Node("ai_chance", "=", self.events[window.event_id].all("option")[index].get("ai_chance", []))
        result = float(chance.get("factor", chance.get("base", 1)))
        for modifier in chance.all("modifier"):
            assert all(n.key not in ("add", "base") for n in modifier.children)
            if self.check([n for n in modifier.children if n.key != "factor"], window.recipient):
                result *= float(modifier.get("factor", 1))
        return result

    def native(self, number, index=0):
        window = self.open_event("avian." + str(number), "AVI")
        assert window, f"Native event avian.{number} did not open"
        self.choose_window(window, index)

    def native_focus(self, name):
        self.root, self.sender = "AVI", "AVI"
        self.countries["AVI"].focuses.add(name)
        self.run(self.focuses[name].get("completion_reward", []), "AVI")

    def daily(self):
        # Fixed explicit fixture order, not a claim about engine callback ordering.
        for tag in (*HOUSES, "AVI"):
            self.root, self.sender = tag, tag
            self.run(self.crisis_hooks.get("on_daily_" + tag, []), tag)

    def subject_of(self, tag, overlord):
        c = self.countries[tag]
        c.subject, c.overlord = bool(overlord), overlord

    def war_between(self, attacker, defender):
        for tag, other in ((attacker, defender), (defender, attacker)):
            self.countries[tag].wars.add(other)
            self.countries[tag].war = True
        self.root, self.sender = attacker, defender
        self.run(self.crisis_hooks.get("on_war_relation_added", []), attacker)
        self.daily()

    def annex(self, winner, annexed):
        c = self.countries[annexed]
        c.exists, c.subject, c.overlord = False, False, None
        context = self.root, self.sender
        self.root, self.sender = winner, annexed
        self.run(self.crisis_hooks.get("on_annex", []), winner)
        self.root, self.sender = context

    def crisis(self, name, tag="ERI"):
        self.root, self.sender = tag, tag
        self.apply(PREFIX + name, tag)

    def predicate(self, name, tag="ERI"):
        self.root, self.sender = tag, tag
        return self.test(PREFIX + name, tag)

    def route(self, mode):
        if mode == "neutral":
            self.native_focus("pursue_true_neutrality")
            self.daily()
        elif mode == "foundation":
            self.native_focus("pursue_true_neutrality")
            self.native(24)
            self.daily()
        else:
            self.native({"military": 15, "loyalist": 16, "technocrat": 17}[mode])

    def benefits(self, tag):
        return PREFIX + "civilian_transit" in self.countries[tag].ideas

    def snapshot(self):
        return {tag: copy.deepcopy(vars(c)) for tag, c in self.countries.items()}


class EngineSyntax(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = documentation_sections(OPT.game / "documentation/triggers_documentation.md")
        cls.effects = documentation_sections(OPT.game / "documentation/effects_documentation.md")

    def validate(self, nodes):
        validate_engine_contract(nodes, self.triggers, self.effects)

    def test_keyword_inventory_comes_from_installed_engine_documentation(self):
        self.assertIn("Supported Scopes: COUNTRY", self.triggers["has_political_power"])
        self.assertIn("Supported Scopes: COUNTRY", self.effects["diplomatic_relation"])
        self.assertNotIn("political_power", self.triggers)
        for name in ("non_aggression_pact", "create_non_aggression_pact", "remove_non_aggression_pact"):
            self.assertNotIn(name, self.effects)

    def test_pact_shape_matches_installed_game_and_eaw_sources(self):
        sources = (
            OPT.game / "common/scripted_effects/DEN_scripted_effects.txt",
            OPT.eaw / "common/scripted_effects/EAW_WNG_effect.txt",
        )
        for path in sources:
            with self.subTest(path=path):
                pacts = [n for n in walk(read(path)) if n.key == "diplomatic_relation"
                         and n.get("relation") == "non_aggression_pact" and n.get("active") == "yes"]
                self.assertTrue(pacts, f"Installed reference changed: {path}")
                self.validate(pacts)

    def test_owned_sources_pass_independent_engine_contract(self):
        for relative in ENGINE_SOURCES:
            with self.subTest(path=relative):
                self.validate(read(MOD / relative))

    def test_reintroducing_bad_pp_keyword_in_each_source_is_rejected(self):
        for relative in ENGINE_SOURCES[:3]:
            with self.subTest(path=relative):
                source = (MOD / relative).read_text(encoding="utf-8-sig")
                self.assertIn("has_political_power", source)
                broken = source.replace("has_political_power", "political_power")
                with self.assertRaisesRegex(AssertionError, "Undocumented engine trigger: political_power"):
                    self.validate(parse(broken))

    def test_reintroducing_bad_pact_keywords_is_rejected(self):
        source = (MOD / "common/scripted_effects/HSM_VER_crisis.txt").read_text(encoding="utf-8-sig")
        supported = "diplomatic_relation = { country = AVI relation = non_aggression_pact active = yes }"
        self.assertIn(supported, source)
        for name in ("non_aggression_pact", "create_non_aggression_pact", "remove_non_aggression_pact"):
            with self.subTest(name=name):
                broken = source.replace(supported, name + " = AVI")
                with self.assertRaisesRegex(AssertionError, "Undocumented engine effect: " + name):
                    self.validate(parse(broken))

    def test_reintroducing_bad_native_comparison_tokens_is_rejected(self):
        source = (MOD / "events/Avian Events.txt").read_text(encoding="utf-8-sig")
        for opponent in ("communist_effort", "fascist_effort"):
            supported = "NOT = { check_variable = { loyalist_effort < " + opponent + " } }"
            self.assertIn(supported, source)
            for op in (">=", "<=", "!="):
                with self.subTest(opponent=opponent, op=op):
                    broken = source.replace(supported, f"check_variable = {{ loyalist_effort {op} {opponent} }}")
                    with self.assertRaisesRegex(AssertionError, "Unsupported comparison operator"):
                        self.validate(parse(broken))

    def test_documented_long_form_comparison_does_not_authorize_shorthand_tokens(self):
        self.validate(parse("check_variable = { var = loyalist_effort value = communist_effort "
                            "compare = greater_than_or_equals }"))
        with self.assertRaisesRegex(AssertionError, "Unsupported check_variable compare"):
            self.validate(parse("check_variable = { var = loyalist_effort value = communist_effort "
                                "compare = greater_or_equal }"))


class Harness(unittest.TestCase):
    def test_unknown_operations_fail_closed(self):
        w = CrisisWorld()
        with self.assertRaisesRegex(AssertionError, "no predicate"):
            w.check(parse("unsupported_crisis_predicate = yes"))
        with self.assertRaisesRegex(AssertionError, "no effect"):
            w.run(parse("unsupported_crisis_effect = yes"))

    def test_old_bogus_engine_commands_are_not_fixture_aliases(self):
        w = CrisisWorld()
        with self.assertRaisesRegex(AssertionError, "no predicate"):
            w.check(parse("political_power > 24"))
        for name in ("non_aggression_pact", "create_non_aggression_pact", "remove_non_aggression_pact"):
            with self.subTest(name=name), self.assertRaisesRegex(AssertionError, "no effect"):
                w.run(parse(f"{name} = ERI"))

    def test_undocumented_shorthand_operators_are_not_fixture_extensions(self):
        w = CrisisWorld()
        for op in (">=", "<=", "!="):
            with self.subTest(op=op), self.assertRaisesRegex(AssertionError, "Unsupported variable comparison"):
                w.check(parse(f"check_variable = {{ loyalist_effort {op} communist_effort }}"))

    def test_negated_less_than_preserves_inclusive_variable_comparison(self):
        w = CrisisWorld()
        comparison = parse("NOT = { check_variable = { loyalist_effort < communist_effort } }")
        for left, right in itertools.product(range(3), repeat=2):
            w.countries["AVI"].variables = {"loyalist_effort": left, "communist_effort": right}
            self.assertEqual(w.check(comparison), left >= right)

    def test_conditional_chains_keep_new_operations_in_scope(self):
        w = CrisisWorld()
        w.run(parse("if = { limit = { always = no } add_political_power = 900 } "
                    "else_if = { limit = { always = yes } "
                    "ERI = { add_to_variable = { var = native_effort value = 1 } } } "
                    "else = { add_political_power = 900 }"))
        self.assertEqual(w.countries["ERI"].variables, {"native_effort": 1})
        self.assertEqual(w.countries["AVI"].political_power, 0)


class CrisisFixture(unittest.TestCase):
    def setUp(self):
        self.w = CrisisWorld()
        self.avi = self.w.countries["AVI"]
        for tag in HOUSES:
            self.w.countries[tag].political_power = 200

    def choose_effect(self, window, effect, stale=False):
        options = self.w.events[window.event_id].all("option")
        matches = [i for i, option in enumerate(options)
                   if any(n.key == PREFIX + effect for n in walk(option.children))]
        self.assertEqual(len(matches), 1, (window.event_id, effect))
        self.w.choose_window(window, matches[0], stale=stale)

    def offer(self, tag="ERI", mode="loyalist"):
        if not self.w.predicate("known_government"):
            self.w.route(mode)
        self.w.crisis("offer_compact", tag)
        self.assertIn(PREFIX + "offer_pending", self.w.countries[tag].flags)
        self.w.advance_days(1)
        window = self.w.deliver(EVENT_PREFIX + "3", "AVI")
        self.assertIsInstance(window, Window)
        self.assertEqual(window.sender, tag)
        return window

    def sign_compact(self, tag="ERI", mode="loyalist"):
        window = self.offer(tag, mode)
        self.choose_effect(window, "accept_compact")
        self.assertIn(PREFIX + "compact", self.w.countries[tag].flags)
        return window

    def change_context(self, tag, change):
        c = self.w.countries[tag]
        if change == "missing":
            c.exists = False
        elif change == "occupied":
            c.capitulated = True
        elif change == "subject":
            self.w.subject_of(tag, "GRI")
        elif change == "war":
            c.war = True
            c.wars.add("GRI")
        elif change == "route":
            self.avi.government = "fascism"
        else:
            raise AssertionError(change)


class Emergency(CrisisFixture):
    def start(self):
        self.w.native(10)

    def aid(self, tag):
        window = self.w.deliver(EVENT_PREFIX + "1", tag)
        self.assertIsInstance(window, Window)
        return window

    def test_native_attack_opens_both_houses_before_delayed_first_battle(self):
        self.start()
        self.assertIn(PREFIX + "emergency", self.avi.flags)
        for tag in HOUSES:
            window = self.aid(tag)
            self.assertEqual(window.deadline - window.opened, 7)
        battle = [p for p in self.w.scheduled if p[2] == "avian.11"]
        self.assertEqual(len(battle), 1)
        self.assertEqual(battle[0][0], 14)
        self.w.advance_days(13)
        with self.assertRaisesRegex(AssertionError, "No due"):
            self.w.deliver("avian.11", "AVI")
        self.w.advance_days(1)
        self.assertTrue(self.w.deliver("avian.11", "AVI"))

    def test_aid_replay_costs_once_per_house_and_uses_native_effort(self):
        self.start()
        for tag in HOUSES:
            window = self.aid(tag)
            self.choose_effect(window, "support_loyalists")
            self.assertEqual(self.w.countries[tag].political_power, 160)
            before = self.w.snapshot()
            for effect in ("send_medics", "support_loyalists", "guard_border"):
                self.choose_effect(window, effect, stale=True)
            self.assertEqual(self.w.snapshot(), before)
        self.assertEqual(self.avi.variables, {"loyalist_effort": 2})
        self.w.crisis("begin", "AVI")
        self.assertEqual([self.w.countries[tag].events.count(EVENT_PREFIX + "1") for tag in HOUSES], [1, 1])

    def test_medics_cost_25_and_guard_is_free(self):
        for medical_house in HOUSES:
            self.setUp()
            other = next(tag for tag in HOUSES if tag != medical_house)
            self.start()
            self.choose_effect(self.aid(medical_house), "send_medics")
            self.choose_effect(self.aid(other), "guard_border")
            self.assertEqual(self.w.countries[medical_house].political_power, 175)
            self.assertEqual(self.w.countries[other].political_power, 200)
            self.assertEqual(self.avi.idea_days[PREFIX + "emergency_hospitals"], 120)
            self.assertFalse(self.avi.variables)
            self.w.advance_days(120)
            self.assertNotIn(PREFIX + "emergency_hospitals", self.avi.ideas)

    def test_second_house_medics_record_help_without_refreshing_hospitals(self):
        for first in HOUSES:
            with self.subTest(first=first):
                self.setUp()
                second = next(tag for tag in HOUSES if tag != first)
                self.start()
                windows = {tag: self.aid(tag) for tag in HOUSES}
                self.choose_effect(windows[first], "send_medics")
                hospital = PREFIX + "emergency_hospitals"
                self.assertEqual(self.avi.idea_days[hospital], 120)
                additions = [entry for entry in self.w.trace if entry[:2] == ("AVI", "add_timed_idea")]
                self.assertEqual(len(additions), 1)
                self.w.advance_days(3)
                self.choose_effect(windows[second], "send_medics")
                self.assertEqual(self.avi.idea_days[hospital], 117)
                self.assertEqual([entry for entry in self.w.trace if entry[:2] == ("AVI", "add_timed_idea")], additions)
                for tag in HOUSES:
                    self.assertEqual(self.w.countries[tag].political_power, 175)
                    self.assertIn(PREFIX + "medics", self.w.countries[tag].flags)
                    self.assertIn(PREFIX + "aid_answered", self.w.countries[tag].flags)
                self.w.advance_days(117)
                self.assertNotIn(hospital, self.avi.ideas)
                self.assertNotIn(hospital, self.avi.idea_days)

    def test_emergency_accepts_independent_and_avian_subject_only(self):
        for tag, overlord in itertools.product(HOUSES, (None, "AVI", "GRI")):
            with self.subTest(tag=tag, overlord=overlord):
                self.setUp()
                self.w.subject_of(tag, overlord)
                self.start()
                self.assertEqual(EVENT_PREFIX + "1" in self.w.countries[tag].events, overlord != "GRI")
                if overlord != "GRI":
                    self.choose_effect(self.aid(tag), "guard_border")
                    self.assertEqual(self.w.countries[tag].overlord, overlord)

    def test_queued_ball_can_reach_house_after_independence(self):
        for tag in HOUSES:
            self.w.subject_of(tag, "AVI")
        self.w.native_focus("the_second_winterfest_ball")
        for tag in HOUSES:
            self.w.subject_of(tag, None)
        window = self.w.deliver("avian.10", "AVI")
        self.w.choose_window(window)
        for tag in HOUSES:
            self.choose_effect(self.aid(tag), "support_loyalists")
            self.assertFalse(self.w.countries[tag].subject)
        self.assertEqual(self.avi.variables["loyalist_effort"], 2)

    def test_aid_rechecks_money_and_live_participants(self):
        for tag, effect in itertools.product(HOUSES, ("send_medics", "support_loyalists")):
            required = 25 if effect == "send_medics" else 40
            self.setUp()
            self.start()
            window = self.aid(tag)
            self.w.countries[tag].political_power = required - 1
            before = self.w.snapshot()
            self.choose_effect(window, effect, stale=True)
            self.assertEqual(self.w.snapshot(), before)
            self.w.countries[tag].political_power = required
            self.choose_effect(window, effect)
            self.assertEqual(self.w.countries[tag].political_power, 0)
        for tag, changed, change in itertools.product(HOUSES, ("self", "AVI"), ("missing", "occupied", "subject")):
            with self.subTest(tag=tag, participant=changed, change=change):
                self.setUp()
                self.start()
                window = self.aid(tag)
                self.change_context(tag if changed == "self" else changed, change)
                before = self.w.snapshot()
                self.choose_effect(window, "support_loyalists", stale=True)
                self.assertEqual(self.w.snapshot(), before)

    def test_outcome_or_expired_fallback_makes_aid_stale(self):
        for tag, ending in itertools.product(HOUSES, ("outcome", "timeout")):
            self.setUp()
            self.start()
            window = self.aid(tag)
            if ending == "outcome":
                self.w.native(16)
            else:
                self.w.advance_days(12)
            before = self.w.snapshot()
            self.choose_effect(window, "send_medics", stale=True)
            self.assertEqual(self.w.snapshot(), before)


class CompactOffers(CrisisFixture):
    def test_acceptance_creates_only_a_missing_bilateral_non_aggression_pact(self):
        for tag, existing in itertools.product(HOUSES, (False, True)):
            with self.subTest(tag=tag, existing=existing):
                self.setUp()
                other = next(t for t in HOUSES if t != tag)
                self.w.countries[other].non_aggression.add("AVI")
                self.avi.non_aggression.add(other)
                if existing:
                    self.w.countries[tag].non_aggression.add("AVI")
                    self.avi.non_aggression.add(tag)
                window = self.sign_compact(tag)
                pacts = [entry for entry in self.w.trace if entry[1] == "diplomatic_relation"]
                relation = parse("country = AVI relation = non_aggression_pact active = yes")
                self.assertEqual(pacts, [] if existing else [(tag, "diplomatic_relation", relation)])
                self.assertIn("AVI", self.w.countries[tag].non_aggression)
                self.assertEqual(self.avi.non_aggression, set(HOUSES))
                self.assertTrue(self.w.benefits(tag))
                self.assertTrue(self.w.benefits("AVI"))
                self.choose_effect(window, "accept_compact", stale=True)
                self.assertEqual([entry for entry in self.w.trace if entry[1] == "diplomatic_relation"], pacts)

    def test_each_route_requires_separate_avian_consent_and_costs_once(self):
        for tag, mode in itertools.product(HOUSES, ("military", "technocrat", "loyalist", "neutral", "foundation")):
            with self.subTest(tag=tag, mode=mode):
                self.setUp()
                window = self.offer(tag, mode)
                c = self.w.countries[tag]
                self.assertEqual(c.political_power, 165)
                self.assertNotIn(PREFIX + "compact", c.flags)
                self.assertNotIn("AVI", c.non_aggression)
                self.assertFalse(self.w.benefits(tag))
                before = self.w.snapshot()
                self.w.crisis("offer_compact", tag)
                self.assertEqual(self.w.snapshot(), before)
                self.choose_effect(window, "accept_compact")
                self.assertEqual(c.political_power, 165)
                self.assertIn("AVI", c.non_aggression)
                self.assertIn(tag, self.avi.non_aggression)
                self.assertTrue(self.w.benefits(tag))
                self.assertTrue(self.w.benefits("AVI"))
                self.assertIn(PREFIX + "mode_" + mode, c.flags)
                self.assertTrue(c.exists)
                self.assertFalse(c.subject or c.faction or c.cores)
                self.assertNotIn("HSM_VER_charter_signed", c.flags)
                before = self.w.snapshot()
                self.choose_effect(window, "accept_compact", stale=True)
                self.choose_effect(window, "refuse_compact", stale=True)
                self.assertEqual(self.w.snapshot(), before)

    def test_concurrent_houses_keep_sender_context_and_separate_answers(self):
        self.w.route("loyalist")
        for tag in HOUSES:
            self.w.crisis("offer_compact", tag)
        self.w.advance_days(1)
        windows = [self.w.deliver(EVENT_PREFIX + "3", "AVI") for _ in HOUSES]
        self.assertEqual({window.sender for window in windows}, set(HOUSES))
        accepted, refused = windows
        self.choose_effect(accepted, "accept_compact")
        self.choose_effect(refused, "refuse_compact")
        self.assertTrue(self.w.benefits(accepted.sender))
        self.assertFalse(self.w.benefits(refused.sender))
        self.assertNotIn(PREFIX + "compact", self.w.countries[refused.sender].flags)
        self.assertEqual([self.w.countries[t].political_power for t in HOUSES], [165, 165])
        self.assertEqual(self.avi.non_aggression, {accepted.sender})

    def test_accept_and_refuse_revalidate_live_sender_and_recipient(self):
        for tag, participant, change, effect in itertools.product(
                HOUSES, ("sender", "recipient"), ("missing", "occupied", "subject", "war"),
                ("accept_compact", "refuse_compact")):
            with self.subTest(tag=tag, participant=participant, change=change, effect=effect):
                self.setUp()
                window = self.offer(tag)
                self.change_context(tag if participant == "sender" else "AVI", change)
                before = self.w.snapshot()
                self.choose_effect(window, effect, stale=True)
                self.assertEqual(self.w.snapshot(), before)

    def test_historical_route_cannot_authorize_reply_after_political_change(self):
        for tag, mode, government in itertools.product(HOUSES, ("military", "technocrat"), ("neutrality", "democratic")):
            with self.subTest(tag=tag, mode=mode, government=government):
                self.setUp()
                window = self.offer(tag, mode)
                self.avi.government = government
                before = self.w.snapshot()
                self.choose_effect(window, "accept_compact", stale=True)
                self.assertEqual(self.w.snapshot(), before)
                self.w.daily()
                self.assertNotIn(PREFIX + "offer_pending", self.w.countries[tag].flags)
        self.setUp()
        window = self.offer("ERI", "neutral")
        self.w.native(24)
        before = self.w.snapshot()
        self.choose_effect(window, "accept_compact", stale=True)
        self.assertEqual(self.w.snapshot(), before)

    def test_refusal_retries_only_at_90_days_and_charges_new_attempt(self):
        for tag in HOUSES:
            self.setUp()
            window = self.offer(tag)
            self.choose_effect(window, "refuse_compact")
            c = self.w.countries[tag]
            self.assertNotIn(PREFIX + "offer_pending", c.flags)
            self.assertFalse(self.w.benefits(tag))
            self.w.advance_days(88)
            self.assertFalse(self.w.predicate("can_offer", tag))
            self.w.advance_days(1)
            self.assertTrue(self.w.predicate("can_offer", tag))
            second = self.offer(tag)
            self.assertEqual(c.political_power, 130)
            self.choose_effect(second, "accept_compact")
            self.assertIn(PREFIX + "compact", c.flags)

    def test_timeout_at_30_days_and_flag_fallback_at_45(self):
        for tag, drop_timeout in itertools.product(HOUSES, (False, True)):
            with self.subTest(tag=tag, drop_timeout=drop_timeout):
                self.setUp()
                window = self.offer(tag)
                self.w.advance_days(28)
                self.assertIn(PREFIX + "offer_pending", self.w.countries[tag].flags)
                self.w.advance_days(1)
                if drop_timeout:
                    self.w.scheduled = [p for p in self.w.scheduled if p[2] != EVENT_PREFIX + "29"]
                    self.w.advance_days(14)
                    self.assertIn(PREFIX + "offer_pending", self.w.countries[tag].flags)
                    self.w.advance_days(1)
                else:
                    self.assertTrue(self.w.deliver(EVENT_PREFIX + "29", tag))
                self.assertNotIn(PREFIX + "offer_pending", self.w.countries[tag].flags)
                before = self.w.snapshot()
                self.choose_effect(window, "accept_compact", stale=True)
                self.assertEqual(self.w.snapshot(), before)
                self.assertFalse(self.w.predicate("can_offer", tag))
                self.w.advance_days(90 - self.w.day)
                self.assertTrue(self.w.predicate("can_offer", tag))

    def test_dropped_reply_can_retry_and_old_window_expires_before_retry(self):
        for tag in HOUSES:
            self.setUp()
            window = self.offer(tag)
            self.assertEqual(window.deadline - window.opened, 13)
            self.w.advance_days(89)
            self.assertTrue(self.w.predicate("can_offer", tag))
            new_window = self.offer(tag)
            before = self.w.snapshot()
            with self.assertRaisesRegex(AssertionError, "window has expired"):
                self.choose_effect(window, "refuse_compact")
            self.assertEqual(self.w.snapshot(), before)
            self.choose_effect(new_window, "accept_compact")
            self.assertEqual(self.w.countries[tag].political_power, 130)

    def test_offer_requires_money_and_live_peaceful_independent_participants(self):
        for tag, participant, change in itertools.product(HOUSES, ("self", "AVI"), ("missing", "occupied", "subject", "war")):
            self.setUp()
            self.w.route("loyalist")
            self.change_context(tag if participant == "self" else "AVI", change)
            self.assertFalse(self.w.predicate("can_offer", tag))
            before = self.w.snapshot()
            self.w.crisis("offer_compact", tag)
            self.assertEqual(self.w.snapshot(), before)
        for tag in HOUSES:
            self.setUp()
            self.w.route("loyalist")
            self.w.countries[tag].political_power = 34
            self.assertFalse(self.w.predicate("can_offer", tag))
            self.w.countries[tag].political_power = 35
            self.assertTrue(self.w.predicate("can_offer", tag))
            self.w.crisis("offer_compact", tag)
            self.assertEqual(self.w.countries[tag].political_power, 0)

    def test_retry_decision_uses_real_category_and_charges_once(self):
        decision = self.w.decisions[PREFIX + "reopen_talks"]
        category = read(MOD / "common/decisions/categories/HSM_VER_crisis.txt")[0]
        for tag in HOUSES:
            self.setUp()
            window = self.offer(tag)
            self.choose_effect(window, "refuse_compact")
            self.w.advance_days(89)
            self.w.root, self.w.sender = tag, tag
            self.assertTrue(self.w.check(category.get("allowed"), tag))
            self.assertFalse(self.w.check(category.get("visible"), tag))
            self.w.countries[tag].flags.add("HSM_VER_diplomatic_route")
            self.assertTrue(self.w.check(category.get("visible"), tag))
            self.assertTrue(self.w.check(decision.get("visible"), tag))
            self.assertTrue(self.w.check(decision.get("available"), tag))
            self.w.countries[tag].political_power -= float(decision.get("cost", 0))
            self.w.run(decision.get("complete_effect"), tag)
            self.assertEqual(self.w.countries[tag].political_power, 130)
            self.w.countries[tag].flags.add("HSM_VER_military_route")
            self.assertFalse(self.w.check(category.get("visible"), tag))
            self.assertFalse(self.w.predicate("reply_valid", tag))


class SignedCompacts(CrisisFixture):
    def test_occupation_pauses_and_liberation_restores_without_new_cost(self):
        for tag, occupied in itertools.product(HOUSES, ("house", "AVI")):
            with self.subTest(tag=tag, occupied=occupied):
                self.setUp()
                self.sign_compact(tag)
                country = self.w.countries[tag if occupied == "house" else "AVI"]
                country.capitulated = True
                self.w.daily()
                self.assertIn(PREFIX + "compact", self.w.countries[tag].flags)
                self.assertFalse(self.w.benefits(tag))
                self.assertFalse(self.w.benefits("AVI"))
                self.assertNotIn(EVENT_PREFIX + "11", self.w.countries[tag].events)
                country.capitulated = False
                self.w.daily()
                self.assertTrue(self.w.benefits(tag))
                self.assertTrue(self.w.benefits("AVI"))
                self.assertEqual(self.w.countries[tag].political_power, 165)

    def test_one_occupied_house_does_not_remove_other_house_or_avian_benefit(self):
        for occupied in HOUSES:
            self.setUp()
            for tag in HOUSES:
                self.sign_compact(tag)
            other = next(t for t in HOUSES if t != occupied)
            self.w.countries[occupied].capitulated = True
            self.w.daily()
            self.assertFalse(self.w.benefits(occupied))
            self.assertTrue(self.w.benefits(other))
            self.assertTrue(self.w.benefits("AVI"))

    def test_bilateral_war_invalidates_permanently_and_reconciliation_needs_signature(self):
        for tag, attacker in itertools.product(HOUSES, ("house", "AVI")):
            with self.subTest(tag=tag, attacker=attacker):
                self.setUp()
                self.sign_compact(tag)
                pair = (tag, "AVI") if attacker == "house" else ("AVI", tag)
                self.w.war_between(*pair)
                c = self.w.countries[tag]
                self.assertNotIn(PREFIX + "compact", c.flags)
                self.assertNotIn(PREFIX + "report_due", c.flags)
                self.assertFalse(self.w.benefits(tag))
                self.assertFalse(self.w.benefits("AVI"))
                for participant in (tag, "AVI"):
                    self.w.countries[participant].wars.clear()
                    self.w.countries[participant].war = False
                self.w.daily()
                self.assertFalse(self.w.benefits(tag))
                self.assertEqual(c.events.count(EVENT_PREFIX + "11"), 1)
                self.w.advance_days(89)
                window = self.offer(tag)
                self.assertFalse(self.w.benefits(tag))
                self.choose_effect(window, "accept_compact")
                self.assertTrue(self.w.benefits(tag))
                self.assertEqual(c.political_power, 130)

    def test_subjugation_disappearance_and_route_change_void_signature(self):
        for tag, participant, change in itertools.product(HOUSES, ("house", "AVI"), ("subject", "missing", "route")):
            if change == "route" and participant != "AVI":
                continue
            with self.subTest(tag=tag, participant=participant, change=change):
                self.setUp()
                self.sign_compact(tag)
                target = tag if participant == "house" else "AVI"
                self.change_context(target, change)
                self.w.daily()
                c = self.w.countries[tag]
                self.assertNotIn(PREFIX + "compact", c.flags)
                self.assertFalse(self.w.benefits(tag))
                self.assertFalse(self.w.benefits("AVI"))
                self.w.subject_of(target, None)
                self.w.countries[target].exists = True
                self.avi.government = "neutrality"
                self.w.daily()
                self.assertFalse(self.w.benefits(tag))
                self.assertEqual(c.events.count(EVENT_PREFIX + "11"), 1)

    def test_neutrality_to_foundation_invalidates_same_ideology_compact(self):
        self.sign_compact("ERI", "neutral")
        original_government = self.avi.government
        self.w.native(24)
        self.assertEqual(self.avi.government, original_government)
        self.w.daily()
        self.assertNotIn(PREFIX + "compact", self.w.countries["ERI"].flags)
        self.assertFalse(self.w.benefits("ERI"))
        self.w.advance_days(89)
        window = self.offer("ERI", "foundation")
        self.assertIn(PREFIX + "mode_foundation", self.w.countries["ERI"].flags)
        self.assertNotIn(PREFIX + "mode_neutral", self.w.countries["ERI"].flags)
        self.choose_effect(window, "accept_compact")
        self.assertTrue(self.w.benefits("ERI"))

    def test_external_war_does_not_void_bilateral_compact(self):
        for tag in HOUSES:
            self.setUp()
            self.sign_compact(tag)
            self.w.war_between(tag, "GRI")
            self.assertIn(PREFIX + "compact", self.w.countries[tag].flags)
            self.assertTrue(self.w.benefits(tag))


class Demands(CrisisFixture):
    def demand(self, tag, mode="military"):
        self.w.route(mode)
        self.w.advance_days(1)
        window = self.w.deliver("hsm_verenia.95", tag)
        self.assertIsInstance(window, Window)
        return window

    def test_hostile_demands_use_current_regime_and_allow_peaceful_refusal(self):
        for tag, mode in itertools.product(HOUSES, ("military", "technocrat")):
            with self.subTest(tag=tag, mode=mode):
                self.setUp()
                window = self.demand(tag, mode)
                self.assertEqual(self.w.descriptions("hsm_verenia.95", tag), [PREFIX + "demand_" + mode + "_desc"])
                self.choose_effect(window, "reject_supremacy")
                c = self.w.countries[tag]
                self.assertFalse(c.subject or c.wars)
                self.assertFalse(self.avi.wars)
                self.assertEqual(c.political_power, 200)
                self.assertIn(PREFIX + "resistance", c.flags)
                self.assertEqual(c.idea_days[PREFIX + "border_watch"], 180)
                before = self.w.snapshot()
                self.choose_effect(window, "reject_supremacy", stale=True)
                self.choose_effect(window, "accept_suzerainty", stale=True)
                self.assertEqual(self.w.snapshot(), before)

    def test_negotiation_does_not_submit_and_avian_can_refuse(self):
        for tag, accept in itertools.product(HOUSES, (False, True)):
            self.setUp()
            window = self.demand(tag)
            self.choose_effect(window, "negotiate_demand")
            self.assertFalse(self.w.countries[tag].subject)
            self.assertEqual(self.w.countries[tag].political_power, 165)
            self.w.advance_days(1)
            reply = self.w.deliver(EVENT_PREFIX + "3", "AVI")
            self.choose_effect(reply, "accept_compact" if accept else "refuse_compact")
            self.assertEqual(self.w.benefits(tag), accept)
            self.assertFalse(self.w.countries[tag].subject)

    def test_explicit_suzerainty_applies_only_to_consenting_house(self):
        for tag in HOUSES:
            self.setUp()
            other = next(t for t in HOUSES if t != tag)
            window = self.demand(tag)
            self.choose_effect(window, "accept_suzerainty")
            self.assertEqual(self.w.countries[tag].overlord, "AVI")
            self.assertTrue(self.w.countries[tag].subject)
            self.assertTrue(self.w.countries[tag].exists)
            self.assertFalse(self.w.countries[other].subject)
            self.assertFalse(self.w.countries[tag].wars)
            self.w.advance_days(1)
            self.assertTrue(self.w.deliver(EVENT_PREFIX + "12", tag))

    def test_suzerainty_rechecks_wars_subjects_occupation_and_factions(self):
        for tag, participant, change in itertools.product(HOUSES, ("house", "AVI"), ("war", "subject", "occupied", "missing")):
            with self.subTest(tag=tag, participant=participant, change=change):
                self.setUp()
                window = self.demand(tag)
                self.change_context(tag if participant == "house" else "AVI", change)
                before = self.w.snapshot()
                self.choose_effect(window, "accept_suzerainty", stale=True)
                self.assertEqual(self.w.snapshot(), before)
        for tag, faction, leader in itertools.product(HOUSES, ("foreign", "avian"), (False, True)):
            self.setUp()
            window = self.demand(tag)
            self.avi.faction = "Avian league"
            c = self.w.countries[tag]
            c.faction = "Foreign league" if faction == "foreign" else self.avi.faction
            c.faction_leader = leader
            allowed = faction == "avian" and not leader
            self.assertEqual(self.w.predicate("can_submit", tag), allowed)
            self.choose_effect(window, "accept_suzerainty", stale=True)
            self.assertEqual(c.subject, allowed)

    def test_obsolete_demand_cannot_restore_hostile_route_or_submit(self):
        for tag, effect in itertools.product(HOUSES, ("reject_supremacy", "negotiate_demand", "accept_suzerainty")):
            self.setUp()
            window = self.demand(tag)
            self.avi.government = "democratic"
            before = self.w.snapshot()
            self.choose_effect(window, effect, stale=True)
            self.assertEqual(self.w.snapshot(), before)

    def test_dropped_demand_retries_after_occupation(self):
        for tag in HOUSES:
            self.setUp()
            self.w.route("military")
            self.w.countries[tag].capitulated = True
            self.w.advance_days(1)
            self.assertFalse(self.w.deliver("hsm_verenia.95", tag))
            self.w.advance_days(30)
            self.w.daily()
            count = self.w.countries[tag].events.count("hsm_verenia.95")
            self.w.countries[tag].capitulated = False
            self.w.daily()
            self.assertEqual(self.w.countries[tag].events.count("hsm_verenia.95"), count + 1)
            self.w.advance_days(1)
            self.assertTrue(self.w.deliver("hsm_verenia.95", tag))

    def test_demand_pending_is_required_for_all_three_choices(self):
        for tag, effect in itertools.product(HOUSES, ("reject_supremacy", "negotiate_demand", "accept_suzerainty")):
            self.setUp()
            window = self.demand(tag)
            self.w.advance_days(30)
            self.assertNotIn(PREFIX + "demand_pending", self.w.countries[tag].flags)
            before = self.w.snapshot()
            self.choose_effect(window, effect, stale=True)
            self.assertEqual(self.w.snapshot(), before)


class NativeConsent(CrisisFixture):
    def invitation(self, tag):
        self.avi.focuses.add("full_integration")
        self.avi.faction = "Native union"
        for house in HOUSES:
            self.w.countries[house].faction = self.avi.faction
        window = self.w.open_event("avian.5", tag, "AVI")
        self.assertIsInstance(window, Window)
        return window

    def test_treaty_and_charter_signers_retain_nonzero_native_acceptance(self):
        for tag, signature in itertools.product(HOUSES, ("HSM_VER_treaty_signed", "HSM_VER_charter_signed")):
            self.setUp()
            window = self.invitation(tag)
            accept = self.w.option_index(window, "avian.5.a")
            self.assertEqual(self.w.option_weight(window, accept), 100)
            self.w.countries[tag].flags.add(signature)
            self.assertEqual(self.w.option_weight(window, accept), 35)
            self.assertTrue(self.w.option_available(window, self.w.option_index(window, "HSM_VER_keep_equal_union")))
            for route in ("HARMONY_ALTERNATE", "COMMUNIST_ALTERNATE", "FASCIST_ALTERNATE"):
                flag = "AVI_AI_" + route
                self.avi.flags.add(flag)
                self.assertEqual(self.w.option_weight(window, accept), 280)
                self.avi.flags.remove(flag)
                self.w.game_rules["AVI_ai_behavior"] = "AVI_" + route
                self.assertEqual(self.w.option_weight(window, accept), 280)
                self.w.game_rules["AVI_ai_behavior"] = "DEFAULT"

    def test_default_defer_is_free_and_never_grants_suzerainty(self):
        for tag in HOUSES:
            self.setUp()
            window = self.invitation(tag)
            self.assertEqual(self.w.option_index(window, PREFIX + "integration_defer"), 0)
            self.assertEqual(self.w.option_weight(window, 0), 0)
            self.w.choose_named(window, PREFIX + "integration_defer")
            self.assertEqual(self.w.countries[tag].political_power, 200)
            self.assertFalse(self.w.countries[tag].subject)
            self.assertNotIn("HSM_VER_avian_vassalisation_accepted", self.w.countries[tag].flags)
            self.assertNotIn("avian.6", self.avi.events)

    def test_open_native_invitation_rechecks_context_before_acceptance_or_refusal(self):
        modes = ("military", "technocrat", "loyalist", "neutral", "foundation")
        contexts = list(itertools.product(("house", "AVI"), ("annex", "subject", "occupied")))
        contexts += [("house", "war"), ("house", "foreign_faction"), ("AVI", "missing_focus")]
        contexts += [("AVI", mode) for mode in modes]
        for tag, option, (participant, change) in itertools.product(HOUSES, ("avian.5.a", "avian.5.b"), contexts):
            with self.subTest(tag=tag, option=option, participant=participant, change=change):
                self.setUp()
                window = self.invitation(tag)
                target = tag if participant == "house" else "AVI"
                if change == "annex":
                    self.w.annex("GRI", target)
                elif change == "war":
                    self.w.war_between(tag, "AVI")
                elif change == "foreign_faction":
                    self.w.countries[tag].faction = "Foreign league"
                elif change == "missing_focus":
                    self.avi.focuses.remove("full_integration")
                elif change in modes:
                    self.w.route(change)
                else:
                    self.change_context(target, change)
                self.assertFalse(self.w.predicate("native_integration_context", tag))
                before = self.w.snapshot()
                trace = copy.deepcopy(self.w.trace)
                scheduled = list(self.w.scheduled)
                self.w.choose_named(window, option, stale=True)
                self.assertEqual(self.w.snapshot(), before)
                self.assertEqual(self.w.trace, trace)
                self.assertEqual(self.w.scheduled, scheduled)
                self.assertEqual(self.w.countries[tag].political_power, 200)
                self.assertNotIn("HSM_VER_avian_vassalisation_accepted", self.w.countries[tag].flags)
                self.assertNotIn((tag, "set_cosmetic_tag", "AVI_blue"), self.w.trace)

    def test_native_acceptance_replay_cannot_repeat_reward_or_extend_consent(self):
        for tag, unaligned in itertools.product(HOUSES, (False, True)):
            with self.subTest(tag=tag, unaligned=unaligned):
                self.setUp()
                window = self.invitation(tag)
                if unaligned:
                    self.w.countries[tag].faction = ""
                self.assertTrue(self.w.predicate("native_integration_context", tag))
                self.w.choose_named(window, "avian.5.a")
                self.assertEqual(self.w.countries[tag].political_power, 225)
                self.assertEqual(self.w.trace.count((tag, "set_cosmetic_tag", "AVI_blue")), 1)
                self.assertEqual(self.avi.events.count("avian.6"), 1)
                self.w.advance_days(1)
                self.assertEqual(self.w.countries[tag].flag_days["HSM_VER_avian_vassalisation_accepted"], 44)
                before = self.w.snapshot()
                trace = copy.deepcopy(self.w.trace)
                scheduled = list(self.w.scheduled)
                self.w.choose_named(window, "avian.5.a", stale=True)
                self.assertEqual(self.w.snapshot(), before)
                self.assertEqual(self.w.trace, trace)
                self.assertEqual(self.w.scheduled, scheduled)

    def test_open_native_reply_cannot_subjugate_sender_in_foreign_faction(self):
        for tag, participant in itertools.product(HOUSES, ("sender", "AVI")):
            with self.subTest(tag=tag, participant=participant):
                self.setUp()
                other = next(t for t in HOUSES if t != tag)
                invitations = {t: self.invitation(t) for t in HOUSES}
                for t in HOUSES:
                    self.w.choose_named(invitations[t], "avian.5.a")
                replies = {window.sender: window for window in
                           (self.w.deliver("avian.6", "AVI"), self.w.deliver("avian.6", "AVI"))}
                self.w.countries[tag if participant == "sender" else "AVI"].faction = "Foreign league"
                trace = copy.deepcopy(self.w.trace)
                self.w.choose_named(replies[tag], "avian.6.a", stale=True)
                self.assertFalse(self.w.countries[tag].subject)
                self.assertIsNone(self.w.countries[tag].overlord)
                self.assertEqual(self.avi.political_power, 0)
                self.assertEqual(self.w.trace, trace)
                self.assertNotIn("HSM_VER_avian_vassalisation_accepted", self.w.countries[tag].flags)
                self.assertIn("HSM_VER_avian_vassalisation_accepted", self.w.countries[other].flags)

    def test_native_reply_never_subjugates_without_explicit_unexpired_consent(self):
        for tag, signature in itertools.product(HOUSES, (None, "HSM_VER_treaty_signed", "HSM_VER_charter_signed")):
            with self.subTest(tag=tag, signature=signature):
                self.setUp()
                if signature:
                    self.w.countries[tag].flags.add(signature)
                reply = self.w.open_event("avian.6", "AVI", tag)
                self.w.choose_window(reply)
                self.assertFalse(self.w.countries[tag].subject)
                self.assertEqual(self.avi.political_power, 0)
                invitation = self.invitation(tag)
                self.w.choose_named(invitation, "avian.5.a")
                self.assertEqual(self.w.countries[tag].flag_days["HSM_VER_avian_vassalisation_accepted"], 45)
                reply = self.w.deliver("avian.6", "AVI")
                self.w.advance_days(45)
                self.w.choose_window(reply, stale=True)
                self.assertFalse(self.w.countries[tag].subject)
                self.assertEqual(self.avi.political_power, 0)

    def test_native_acceptance_consumes_only_its_sender_consent(self):
        for tag in HOUSES:
            self.setUp()
            other = next(t for t in HOUSES if t != tag)
            invitations = {t: self.invitation(t) for t in HOUSES}
            for t in HOUSES:
                self.w.choose_named(invitations[t], "avian.5.a")
            replies = {window.sender: window for window in (self.w.deliver("avian.6", "AVI"), self.w.deliver("avian.6", "AVI"))}
            self.w.choose_window(replies[tag])
            self.assertEqual(self.w.countries[tag].overlord, "AVI")
            self.assertFalse(self.w.countries[other].subject)
            self.assertNotIn("HSM_VER_avian_vassalisation_accepted", self.w.countries[tag].flags)
            self.assertIn("HSM_VER_avian_vassalisation_accepted", self.w.countries[other].flags)
            self.assertEqual(self.avi.political_power, 50)
            self.w.choose_window(replies[tag], stale=True)
            self.assertEqual(self.avi.political_power, 50)

    def test_native_consent_cannot_cross_a_new_political_route(self):
        for tag, mode in itertools.product(HOUSES, ("military", "technocrat", "loyalist", "neutral", "foundation")):
            self.setUp()
            invitation = self.invitation(tag)
            self.w.choose_named(invitation, "avian.5.a")
            reply = self.w.deliver("avian.6", "AVI")
            self.w.route(mode)
            before = self.avi.political_power
            self.w.choose_window(reply, stale=True)
            self.assertFalse(self.w.countries[tag].subject)
            self.assertEqual(self.avi.political_power, before)
            self.assertNotIn("HSM_VER_avian_vassalisation_accepted", self.w.countries[tag].flags)

    def test_native_consent_rechecks_live_sender_and_recipient(self):
        for tag, participant, change in itertools.product(HOUSES, ("sender", "recipient"), ("missing", "occupied", "subject")):
            self.setUp()
            invitation = self.invitation(tag)
            self.w.choose_named(invitation, "avian.5.a")
            reply = self.w.deliver("avian.6", "AVI")
            self.change_context(tag if participant == "sender" else "AVI", change)
            self.w.choose_window(reply, stale=True)
            self.assertNotEqual(self.w.countries[tag].overlord, "AVI")
            self.assertEqual(self.avi.political_power, 0)
        for tag in HOUSES:
            self.setUp()
            self.w.choose_named(self.invitation(tag), "avian.5.a")
            reply = self.w.deliver("avian.6", "AVI")
            self.w.war_between(tag, "AVI")
            self.w.choose_window(reply, stale=True)
            self.assertFalse(self.w.countries[tag].subject)

    def test_retry_decision_costs_35_and_opens_fresh_independent_choices(self):
        for tag in HOUSES:
            self.setUp()
            c = self.w.countries[tag]
            c.flags.add("HSM_VER_treaty_signed")
            window = self.invitation(tag)
            self.w.choose_named(window, "HSM_VER_keep_equal_union")
            self.assertFalse(c.subject)
            self.assertFalse(self.w.predicate("integration_retry_valid", tag))
            self.w.advance_days(89)
            self.assertFalse(self.w.predicate("integration_retry_valid", tag))
            self.w.advance_days(1)
            self.assertTrue(self.w.predicate("integration_retry_valid", tag))
            decision = self.w.decisions[PREFIX + "reconsider_integration"]
            self.assertEqual(int(decision.get("days_re_enable")), 90)
            self.avi.political_power = 100
            self.w.root, self.w.sender = "AVI", "AVI"
            self.assertTrue(self.w.check(decision.get("available"), "AVI"))
            self.avi.political_power -= float(decision.get("cost"))
            self.w.run(decision.get("complete_effect"), "AVI")
            self.assertEqual(self.avi.political_power, 65)
            self.assertFalse(any(self.w.countries[t].subject for t in HOUSES))
            self.w.advance_days(1)
            window = self.w.deliver("avian.5", tag)
            self.assertIsInstance(window, Window)
            self.assertEqual(window.deadline - window.opened, 13)
            self.w.choose_named(window, "HSM_VER_keep_equal_union")
            self.assertFalse(c.subject)
            self.assertFalse(self.w.predicate("integration_retry_valid", tag))

    def test_native_retry_excludes_equal_union_and_invalid_participants(self):
        for tag, change in itertools.product(HOUSES, ("missing", "occupied", "subject", "war", "faction", "equal_union", "emergency")):
            self.setUp()
            self.invitation(tag)
            self.w.advance_days(90)
            if change == "faction":
                self.w.countries[tag].faction = "Foreign league"
            elif change == "equal_union":
                self.avi.focuses.add("HSM_AVI_three_separate_seals")
            elif change == "emergency":
                self.w.native(10)
            else:
                self.change_context(tag, change)
            self.assertFalse(self.w.predicate("integration_retry_valid", tag))
            before = self.w.snapshot()
            self.w.crisis("retry_integration", tag)
            self.assertEqual(self.w.snapshot(), before)


class OldCharterGuards(CrisisFixture):
    def test_old_native_faction_invitation_cannot_join_a_new_coup_government(self):
        for tag, mode in itertools.product(HOUSES, ("military", "technocrat")):
            with self.subTest(tag=tag, mode=mode):
                self.setUp()
                other = next(t for t in HOUSES if t != tag)
                self.avi.faction = "Original Avian league"
                self.avi.faction_leader = True
                self.avi.faction_template = "faction_template_AVI_INTERGIGANTES_FACTION"
                self.w.countries[other].faction = self.avi.faction
                window = self.w.open_event("avian.1", tag, "AVI")
                self.assertIsInstance(window, Window)
                accept = self.w.option_index(window, "avian.1.a")
                self.assertTrue(self.w.option_available(window, accept))
                self.w.route(mode)
                self.assertEqual(self.avi.faction, "Original Avian league")
                self.assertTrue(self.avi.faction_leader)
                self.assertFalse(self.w.option_available(window, accept))
                before = self.w.snapshot()
                trace = copy.deepcopy(self.w.trace)
                scheduled = list(self.w.scheduled)
                self.w.choose_named(window, "avian.1.a", stale=True)
                self.assertEqual(self.w.snapshot(), before)
                self.assertEqual(self.w.trace, trace)
                self.assertEqual(self.w.scheduled, scheduled)
                self.assertFalse(self.w.countries[tag].faction)
                self.assertNotIn("avian.3", self.avi.events)

    def test_native_faction_invitation_still_accepts_under_original_government(self):
        for tag in HOUSES:
            with self.subTest(tag=tag):
                self.setUp()
                self.avi.faction = "Original Avian league"
                self.avi.faction_leader = True
                window = self.w.open_event("avian.1", tag, "AVI")
                self.assertIsInstance(window, Window)
                self.assertTrue(self.w.option_available(window, self.w.option_index(window, "avian.1.a")))
                self.w.choose_named(window, "avian.1.a")
                self.assertEqual(self.w.countries[tag].faction, self.avi.faction)
                self.assertEqual(self.avi.events.count("avian.3"), 1)

    def test_queued_observer_and_charter_acceptance_cannot_survive_route_change(self):
        for stage, mode in itertools.product(("observer", "charter"), ("military", "technocrat", "loyalist", "neutral", "foundation")):
            with self.subTest(stage=stage, mode=mode):
                self.setUp()
                self.w.root = "ERI"
                self.w.charter()
                self.w.apply("HSM_VER_invite_avian", "ERI")
                self.w.advance_days(1)
                window = self.w.deliver("hsm_verenia.50", "AVI")
                self.assertIsInstance(window, Window)
                if stage == "charter":
                    self.w.choose_window(window)
                    self.w.advance_days(1)
                    window = self.w.deliver("hsm_verenia.63", "AVI")
                    self.assertIsInstance(window, Window)
                self.w.route(mode)
                self.w.choose_window(window, stale=True)
                self.assertNotIn("HSM_VER_congress_observer", self.avi.flags)
                self.assertNotIn("HSM_VER_charter_signed", self.avi.flags)
                self.assertNotIn("HSM_VER_common_courts", self.avi.ideas)
                self.assertTrue(self.w.test("HSM_VER_negotiated_peace_valid", "ERI"))
                self.assertTrue(self.w.test("HSM_VER_charter_valid", "ERI"))

    def test_equal_union_has_no_automatic_crisis_and_native_ball_stays_locked(self):
        self.w.root = "AVI"
        self.avi.focuses.add("treaty_of_friendship")
        self.w.reward("three_separate_seals")
        self.w.advance_days(100)
        self.w.daily()
        self.assertFalse(self.w.check(self.w.focuses["the_second_winterfest_ball"].get("available"), "AVI"))
        self.assertNotIn(PREFIX + "started", self.avi.flags)
        self.assertNotIn("avian.10", self.avi.events)


class CoronationGuards(CrisisFixture):
    def guarded_coronation_effect(self, key):
        option = next(n for n in self.w.events["avian.20"].all("option") if n.get("name") == "avian.20.a")
        effects = [n for n in walk(option.children) if n.key == key]
        self.assertEqual(len(effects), 1, f"Expected exactly one coronation {key}")
        guards = [n for n in option.children if n.key == "if" and any(child is effects[0] for child in n.children)]
        self.assertEqual(len(guards), 1, f"Coronation {key} must be directly guarded")
        return guards[0], effects[0]

    def test_capital_move_requires_both_ownership_and_control_of_state_391(self):
        guard, effect = self.guarded_coronation_effect("set_capital")
        self.assertEqual(guard.get("limit"), parse("owns_state = 391 controls_state = 391"))
        self.assertEqual(effect.children, parse("state = 391 remember_old_capital = no"))

    def test_new_faction_guard_preserves_allies_and_allows_native_annexed_subject_route(self):
        for actual_subjects in (False, True):
            with self.subTest(actual_subjects=actual_subjects):
                self.setUp()
                guard, effect = self.guarded_coronation_effect("create_faction_from_template")
                self.assertEqual(guard.get("limit"), parse("is_in_faction = no"))
                self.assertEqual(effect.value, "faction_template_AVI_ZYPRESSEN_FACTION")
                self.avi.faction = "Original Avian league"
                self.avi.faction_leader = True
                self.avi.faction_template = "faction_template_AVI_INTERGIGANTES_FACTION"
                for tag in HOUSES:
                    self.w.countries[tag].faction = self.avi.faction
                    if actual_subjects:
                        self.w.subject_of(tag, "AVI")
                self.w.native(15)
                self.assertEqual(self.w.check(guard.get("limit"), "AVI"), actual_subjects)
                if actual_subjects:
                    self.assertFalse(self.avi.faction)
                    self.assertTrue(all(not self.w.countries[tag].exists for tag in HOUSES))
                else:
                    self.assertEqual(self.avi.faction, "Original Avian league")
                    self.assertTrue(all(self.w.countries[tag].exists for tag in HOUSES))
                    self.assertTrue(all(self.w.countries[tag].faction == self.avi.faction for tag in HOUSES))


class AftermathAndEndings(CrisisFixture):
    def test_loyalists_acknowledge_each_aid_choice_without_free_subject_independence(self):
        for tag, overlord, aid in itertools.product(
                HOUSES, (None, "AVI"),
                ("support_loyalists", "send_medics", "guard_border")):
            with self.subTest(tag=tag, overlord=overlord, aid=aid):
                self.setUp()
                self.w.subject_of(tag, overlord)
                self.w.native(10)
                window = self.w.deliver(EVENT_PREFIX + "1", tag)
                self.choose_effect(window, aid)
                self.w.native(16)
                self.w.advance_days(1)
                aftermath = self.w.deliver(EVENT_PREFIX + "5", tag)
                self.assertIsInstance(aftermath, Window)
                suffix = {"support_loyalists": "support", "send_medics": "medics", "guard_border": "border"}[aid]
                self.assertEqual(self.w.descriptions(EVENT_PREFIX + "5", tag), [EVENT_PREFIX + "5." + suffix + ".d"])
                self.assertEqual(self.w.option_available(aftermath, 1), overlord is None)
                self.w.choose_window(aftermath, 0)
                self.assertEqual(self.w.countries[tag].overlord, overlord)
                self.assertEqual(self.w.countries[tag].subject, overlord is not None)
                self.assertNotIn(PREFIX + "compact", self.w.countries[tag].flags)

    def test_loyalist_aftermath_excludes_foreign_subjects_and_retries_dropped_scene(self):
        for tag in HOUSES:
            self.setUp()
            self.w.subject_of(tag, "GRI")
            self.w.route("loyalist")
            self.assertNotIn(EVENT_PREFIX + "5", self.w.countries[tag].events)
            self.w.subject_of(tag, None)
            self.w.daily()
            self.w.countries[tag].capitulated = True
            self.w.advance_days(1)
            self.assertFalse(self.w.deliver(EVENT_PREFIX + "5", tag))
            self.w.advance_days(30)
            self.w.countries[tag].capitulated = False
            self.w.daily()
            self.w.advance_days(1)
            window = self.w.deliver(EVENT_PREFIX + "5", tag)
            self.assertIsInstance(window, Window)
            self.w.choose_window(window)
            count = self.w.countries[tag].events.count(EVENT_PREFIX + "5")
            self.w.advance_days(31)
            self.w.daily()
            self.assertEqual(self.w.countries[tag].events.count(EVENT_PREFIX + "5"), count)

    def test_isolation_and_foundation_letters_are_distinct_and_house_specific(self):
        self.w.route("neutral")
        self.w.advance_days(1)
        for tag in HOUSES:
            window = self.w.deliver(EVENT_PREFIX + "7", tag)
            self.assertIsInstance(window, Window)
            self.assertEqual(self.w.descriptions(EVENT_PREFIX + "7", tag), [EVENT_PREFIX + "7." + tag.lower() + ".d"])
            self.w.choose_window(window, 0)
            self.assertFalse(self.w.countries[tag].subject or self.w.countries[tag].faction)
        self.w.native(24)
        self.w.daily()
        self.w.advance_days(1)
        for tag in HOUSES:
            window = self.w.deliver(EVENT_PREFIX + "8", tag)
            self.assertIsInstance(window, Window)
            self.w.choose_window(window, 0)
            self.assertIn(PREFIX + "isolation_seen", self.w.countries[tag].flags)
            self.assertIn(PREFIX + "foundation_seen", self.w.countries[tag].flags)
            self.assertFalse(self.w.countries[tag].subject or self.w.countries[tag].faction)
        self.w.advance_days(90)
        self.w.daily()
        for tag in HOUSES:
            self.assertEqual(self.w.countries[tag].events.count(EVENT_PREFIX + "7"), 1)
            self.assertEqual(self.w.countries[tag].events.count(EVENT_PREFIX + "8"), 1)

    def test_foundation_rejection_does_not_emit_admission_scene(self):
        self.w.route("neutral")
        self.w.native(24, 1)
        self.w.daily()
        self.assertNotIn("foundation_allowed", self.avi.focuses)
        for tag in HOUSES:
            self.assertNotIn(EVENT_PREFIX + "8", self.w.countries[tag].events)

    def test_native_election_keeps_loyalist_compact_and_does_not_restore_aristocrat(self):
        for tag, option, subject in itertools.product(HOUSES, (0, 1), (False, True)):
            with self.subTest(tag=tag, option=option, subject=subject):
                self.setUp()
                if subject:
                    self.w.subject_of(tag, "AVI")
                    self.w.route("loyalist")
                else:
                    self.sign_compact(tag)
                self.w.advance_days(1)
                aftermath = self.w.deliver(EVENT_PREFIX + "5", tag)
                self.assertIsInstance(aftermath, Window)
                self.w.choose_named(aftermath, EVENT_PREFIX + "5.a")
                self.w.native_focus("permit_local_elections")
                native = self.w.deliver("avian.19", "AVI")
                self.w.choose_window(native)
                self.assertEqual(self.avi.government, "democratic")
                self.assertEqual(self.avi.leader, "AVI_lady_katrina_avian")
                self.w.daily()
                self.w.advance_days(1)
                window = self.w.deliver(EVENT_PREFIX + "9", tag)
                self.assertIsInstance(window, Window)
                self.w.choose_window(window, option)
                self.assertEqual(self.avi.government, "democratic")
                self.assertEqual(self.avi.leader, "AVI_lady_katrina_avian")
                self.assertEqual(self.w.countries[tag].subject, subject)
                self.assertEqual(self.w.benefits(tag), not subject)
                self.assertIn(PREFIX + "elections_seen", self.w.countries[tag].flags)
                self.assertEqual(PREFIX + "elections_welcomed" in self.w.countries[tag].flags, option == 0)
                self.w.advance_days(31)
                self.w.daily()
                self.assertEqual(self.w.countries[tag].events.count(EVENT_PREFIX + "9"), 1)

    def test_election_reply_drops_if_current_government_changes(self):
        for tag in HOUSES:
            self.setUp()
            self.w.route("loyalist")
            self.w.advance_days(1)
            aftermath = self.w.deliver(EVENT_PREFIX + "5", tag)
            self.assertIsInstance(aftermath, Window)
            self.w.choose_named(aftermath, EVENT_PREFIX + "5.a")
            self.w.native_focus("permit_local_elections")
            self.w.choose_window(self.w.deliver("avian.19", "AVI"))
            self.w.daily()
            self.avi.government = "fascism"
            self.w.advance_days(1)
            self.assertFalse(self.w.deliver(EVENT_PREFIX + "9", tag))
            self.assertNotIn(PREFIX + "elections_seen", self.w.countries[tag].flags)

    def test_old_save_dispatches_elections_only_after_each_house_acknowledges_loyalists(self):
        for first in HOUSES:
            with self.subTest(first=first):
                self.setUp()
                second = next(t for t in HOUSES if t != first)
                self.w.route("loyalist")
                self.w.native_focus("permit_local_elections")
                self.w.choose_window(self.w.deliver("avian.19", "AVI"))
                self.w.daily()
                for tag in HOUSES:
                    self.assertEqual(self.w.countries[tag].events.count(EVENT_PREFIX + "5"), 1)
                    self.assertNotIn(EVENT_PREFIX + "9", self.w.countries[tag].events)
                    self.assertNotIn(PREFIX + "elections_pending", self.w.countries[tag].flags)
                self.w.advance_days(1)
                aftermaths = {tag: self.w.deliver(EVENT_PREFIX + "5", tag) for tag in HOUSES}
                for window in aftermaths.values():
                    self.assertIsInstance(window, Window)
                self.w.daily()
                self.assertTrue(all(EVENT_PREFIX + "9" not in self.w.countries[tag].events for tag in HOUSES))
                self.w.choose_named(aftermaths[first], EVENT_PREFIX + "5.a")
                self.w.daily()
                self.assertEqual(self.w.countries[first].events.count(EVENT_PREFIX + "9"), 1)
                self.assertNotIn(EVENT_PREFIX + "9", self.w.countries[second].events)
                self.w.advance_days(1)
                election = self.w.deliver(EVENT_PREFIX + "9", first)
                self.assertIsInstance(election, Window)
                self.w.choose_named(election, EVENT_PREFIX + "9.a")
                self.w.choose_named(aftermaths[second], EVENT_PREFIX + "5.a")
                self.w.daily()
                self.assertEqual(self.w.countries[first].events.count(EVENT_PREFIX + "9"), 1)
                self.assertEqual(self.w.countries[second].events.count(EVENT_PREFIX + "9"), 1)
                self.w.advance_days(1)
                election = self.w.deliver(EVENT_PREFIX + "9", second)
                self.assertIsInstance(election, Window)
                self.w.choose_named(election, EVENT_PREFIX + "9.a")

    def test_sixty_day_report_is_once_per_house_without_repeated_rewards(self):
        for tag, mode in itertools.product(HOUSES, ("military", "technocrat", "loyalist", "neutral", "foundation")):
            with self.subTest(tag=tag, mode=mode):
                self.setUp()
                self.sign_compact(tag, mode)
                c = self.w.countries[tag]
                self.w.advance_days(59)
                self.w.daily()
                self.assertNotIn(EVENT_PREFIX + "15", c.events)
                self.w.advance_days(1)
                self.w.daily()
                self.assertEqual(c.events.count(EVENT_PREFIX + "15"), 1)
                self.w.advance_days(1)
                window = self.w.deliver(EVENT_PREFIX + "15", tag)
                self.assertIsInstance(window, Window)
                self.assertEqual(self.w.descriptions(EVENT_PREFIX + "15", tag), [EVENT_PREFIX + "15." + mode + ".d"])
                before_pp = c.political_power
                self.w.choose_window(window)
                self.assertEqual(c.political_power, before_pp)
                before = self.w.snapshot()
                self.w.choose_window(window, stale=True)
                self.assertEqual(self.w.snapshot(), before)
                self.w.advance_days(120)
                self.w.daily()
                self.assertEqual(c.events.count(EVENT_PREFIX + "15"), 1)
                self.assertIn(PREFIX + "report_seen", c.flags)

    def test_dropped_report_recovers_after_liberation(self):
        for tag in HOUSES:
            self.setUp()
            self.sign_compact(tag)
            self.w.advance_days(60)
            self.w.daily()
            self.w.countries[tag].capitulated = True
            self.w.advance_days(1)
            self.assertFalse(self.w.deliver(EVENT_PREFIX + "15", tag))
            self.w.advance_days(30)
            self.w.daily()
            self.assertEqual(self.w.countries[tag].events.count(EVENT_PREFIX + "15"), 1)
            self.w.countries[tag].capitulated = False
            self.w.daily()
            self.w.advance_days(1)
            self.assertTrue(self.w.deliver(EVENT_PREFIX + "15", tag))

    def test_independent_border_ending_waits_90_days_and_is_not_a_reward_loop(self):
        for tag in HOUSES:
            self.setUp()
            self.w.route("military")
            self.w.advance_days(1)
            demand = self.w.deliver("hsm_verenia.95", tag)
            self.choose_effect(demand, "reject_supremacy")
            self.w.advance_days(89)
            self.w.daily()
            c = self.w.countries[tag]
            self.assertNotIn(EVENT_PREFIX + "16", c.events)
            self.w.advance_days(1)
            self.w.daily()
            self.w.advance_days(1)
            window = self.w.deliver(EVENT_PREFIX + "16", tag)
            self.assertIsInstance(window, Window)
            self.w.choose_window(window)
            before = self.w.snapshot()
            self.w.choose_window(window, stale=True)
            self.assertEqual(self.w.snapshot(), before)
            self.w.advance_days(91)
            self.w.daily()
            self.assertEqual(c.events.count(EVENT_PREFIX + "16"), 1)
            self.assertEqual(c.political_power, 200)
            self.assertFalse(c.subject or c.wars)


class NativeBoundaries(CrisisFixture):
    def test_ball_requires_both_actual_avian_subjects(self):
        available = self.w.focuses["the_second_winterfest_ball"].get("available")
        self.avi.faction = "Native union"
        for tag in HOUSES:
            self.w.countries[tag].faction = self.avi.faction
            self.w.subject_of(tag, "AVI")
        self.assertTrue(self.w.check(available, "AVI"))
        for tag, overlord in itertools.product(HOUSES, (None, "GRI")):
            with self.subTest(tag=tag, overlord=overlord):
                self.w.subject_of(tag, overlord)
                self.assertFalse(self.w.check(available, "AVI"))
                self.w.subject_of(tag, "AVI")

    def test_native_battle_sequence_and_victory_selection_preserved(self):
        source = {n.get("id"): n for n in read(OPT.eaw / "events/Avian Events.txt") if n.key == "country_event"}
        for number in (11, 12, 13, 14):
            with self.subTest(event=number):
                key = "avian." + str(number)
                self.assertEqual(self.w.events[key], source[key])
        for old, new in zip(source["avian.18"].all("option"), self.w.events["avian.18"].all("option")):
            if old.get("name") == "avian.18.b":
                self.assertEqual([n for n in BASE["effect_nodes"](old.children) if n.key != "trigger"],
                                 [n for n in BASE["effect_nodes"](new.children) if n.key != "trigger"])
            else:
                self.assertEqual(old, new)
        for choice, variable, victory in ((0, "communist_effort", "avian.17"),
                                          (1, "loyalist_effort", "avian.16"),
                                          (2, "fascist_effort", "avian.15")):
            w = CrisisWorld()
            for number in (11, 12, 13, 14):
                w.native(number, choice)
            self.assertEqual(w.countries["AVI"].variables, {variable: 9})
            window = w.open_event("avian.18", "AVI")
            self.assertEqual([w.option_available(window, i) for i in range(3)],
                             [i == choice for i in range(3)])
            w.choose_window(window, choice)
            self.assertIn(victory, w.countries["AVI"].events)

    def test_all_native_battle_allocations_have_exactly_one_winner_with_zero_one_two_aids(self):
        native = next(n for n in read(OPT.eaw / "events/Avian Events.txt") if n.get("id") == "avian.18")
        variables = ("communist_effort", "loyalist_effort", "fascist_effort")
        checked, aid_ties = 0, 0
        for choices in itertools.product(range(3), repeat=4):
            self.setUp()
            self.w.native(10)
            for number, choice in zip((11, 12, 13, 14), choices):
                self.w.native(number, choice)
            expected = [sum(weight for choice, weight in zip(choices, (3, 2, 2, 2)) if choice == side)
                        for side in range(3)]
            self.assertEqual([self.avi.variables.get(v, 0) for v in variables], expected)
            for aid_count in range(3):
                with self.subTest(choices=choices, aid_count=aid_count):
                    if aid_count:
                        window = self.w.deliver(EVENT_PREFIX + "1", HOUSES[aid_count - 1])
                        self.choose_effect(window, "support_loyalists")
                    outcome = self.w.open_event("avian.18", "AVI")
                    available = [self.w.option_available(outcome, i) for i in range(3)]
                    self.assertEqual(sum(available), 1)
                    if not aid_count:
                        original = [self.w.check(option.get("trigger"), "AVI") for option in native.all("option")]
                        self.assertEqual(available, original)
                    scores = expected.copy()
                    scores[1] += aid_count
                    winner = available.index(True)
                    self.assertEqual(scores[winner], max(scores))
                    if scores.count(max(scores)) > 1:
                        aid_ties += 1
                        self.assertGreater(aid_count, 0)
                        self.assertEqual(winner, 1)
                    checked += 1
        self.assertEqual(checked, 243)
        self.assertGreater(aid_ties, 0, "Fixture must exercise actual aid-induced ties")

    def test_loyalist_tie_fallback_requires_both_crisis_start_and_real_aid(self):
        # The native distribution 3+2 against 2+2 becomes 5:5 after one aid point.
        self.w.native(10)
        for number, choice in zip((11, 12, 13, 14), (0, 0, 1, 1)):
            self.w.native(number, choice)
        self.choose_effect(self.w.deliver(EVENT_PREFIX + "1", "EYR"), "support_loyalists")
        window = self.w.open_event("avian.18", "AVI")
        self.assertTrue(self.w.option_available(window, 1))
        self.avi.flags.remove(PREFIX + "started")
        self.assertFalse(self.w.option_available(window, 1))
        self.avi.flags.add(PREFIX + "started")
        self.w.countries["EYR"].flags.remove(PREFIX + "supported_loyalists")
        self.assertFalse(self.w.option_available(window, 1))

    def test_coups_annex_only_actual_subjects(self):
        for number, tag, overlord in itertools.product((15, 17), HOUSES, (None, "AVI", "GRI")):
            with self.subTest(event=number, tag=tag, overlord=overlord):
                w = CrisisWorld()
                w.subject_of(tag, overlord)
                w.native(number)
                c = w.countries[tag]
                self.assertEqual(c.exists, overlord != "AVI")
                self.assertEqual("hsm_verenia.95" in c.events, overlord is None)
                if overlord == "GRI":
                    self.assertEqual(c.overlord, "GRI")
                self.assertFalse(c.wars)

    def test_current_political_mode_not_historical_focus_alone(self):
        for mode, focus, government in (("military", "fascists_win", "fascism"),
                                         ("technocrat", "communists_win", "communism"),
                                         ("loyalist", "loyalists_win", "neutrality")):
            with self.subTest(mode=mode):
                w = CrisisWorld()
                avi = w.countries["AVI"]
                avi.focuses.add(focus)
                avi.government = government
                avi.leader = {"military": "AVI_trubach_von_zypressen", "technocrat": "AVI_aaron_redtail",
                              "loyalist": "AVI_lady_katrina_avian"}[mode]
                self.assertTrue(w.predicate(mode + "_government"))
                avi.government = "democratic" if mode != "loyalist" else "fascism"
                self.assertFalse(w.predicate(mode + "_government"))
        self.avi.focuses.add("loyalists_win")
        self.avi.government = "democratic"
        self.assertTrue(self.w.predicate("loyalist_government"))

    def test_government_snapshot_belongs_to_each_house(self):
        self.avi.focuses.add("fascists_win")
        self.avi.government = "fascism"
        self.avi.leader = "AVI_trubach_von_zypressen"
        self.w.countries["ERI"].flags.add(PREFIX + "mode_military")
        self.w.countries["EYR"].flags.add(PREFIX + "mode_technocrat")
        self.assertTrue(self.w.predicate("same_government", "ERI"))
        self.assertFalse(self.w.predicate("same_government", "EYR"))
        self.avi.focuses.add("communists_win")
        self.avi.government = "communism"
        self.avi.leader = "AVI_aaron_redtail"
        self.assertFalse(self.w.predicate("same_government", "ERI"))
        self.assertTrue(self.w.predicate("same_government", "EYR"))

    def test_replacement_leader_invalidates_current_route_despite_same_ideology(self):
        for mode in ("military", "technocrat", "loyalist", "neutral", "foundation"):
            with self.subTest(mode=mode):
                self.setUp()
                window = self.offer("ERI", mode)
                self.assertTrue(self.w.predicate(mode + "_government"))
                self.avi.leader = "replacement_leader"
                self.assertFalse(self.w.predicate(mode + "_government"))
                before = self.w.snapshot()
                self.choose_effect(window, "accept_compact", stale=True)
                self.assertEqual(self.w.snapshot(), before)


class Annexation(CrisisFixture):
    def test_annexed_house_loses_signature_and_liberation_cannot_restore_it(self):
        for annexed, winner in itertools.product(HOUSES, ("AVI", "GRI")):
            with self.subTest(annexed=annexed, winner=winner):
                self.setUp()
                for tag in HOUSES:
                    self.sign_compact(tag)
                other = next(t for t in HOUSES if t != annexed)
                self.w.annex(winner, annexed)
                c = self.w.countries[annexed]
                self.assertFalse(c.exists)
                self.assertNotIn(PREFIX + "compact", c.flags)
                self.assertNotIn(PREFIX + "report_due", c.flags)
                self.assertFalse(self.w.benefits(annexed))
                self.assertTrue(self.w.benefits(other))
                self.assertTrue(self.w.benefits("AVI"))
                c.exists = True
                self.w.daily()
                self.assertFalse(self.w.benefits(annexed))
                self.assertNotIn(PREFIX + "compact", c.flags)

    def test_avian_annexation_clears_all_pending_and_signed_arrangements(self):
        for signed in HOUSES:
            self.setUp()
            pending = next(t for t in HOUSES if t != signed)
            self.sign_compact(signed)
            window = self.offer(pending)
            self.w.annex("GRI", "AVI")
            for tag in HOUSES:
                c = self.w.countries[tag]
                for suffix in ("compact", "offer_pending", "report_due", "report_pending"):
                    self.assertNotIn(PREFIX + suffix, c.flags)
                self.assertFalse(self.w.benefits(tag))
            self.avi.exists = True
            self.w.daily()
            before = self.w.snapshot()
            self.choose_effect(window, "accept_compact", stale=True)
            self.assertEqual(self.w.snapshot(), before)
            self.assertFalse(self.w.benefits(signed) or self.w.benefits(pending))

    def test_unrelated_annexation_does_not_invalidate_house_compact(self):
        self.sign_compact("ERI")
        self.w.annex("EYR", "GRI")
        self.assertIn(PREFIX + "compact", self.w.countries["ERI"].flags)
        self.assertTrue(self.w.benefits("ERI"))

    def test_civilian_invalidation_preserves_existing_non_aggression_pact(self):
        for tag in HOUSES:
            self.setUp()
            self.w.countries[tag].non_aggression.add("AVI")
            self.avi.non_aggression.add(tag)
            self.sign_compact(tag)
            self.avi.leader = "replacement_leader"
            self.w.daily()
            self.assertNotIn(PREFIX + "compact", self.w.countries[tag].flags)
            self.assertFalse(self.w.benefits(tag))
            self.assertIn("AVI", self.w.countries[tag].non_aggression)
            self.assertIn(tag, self.avi.non_aggression)


class SourceContract(CrisisFixture):
    def test_all_crisis_sources_exist_parse_and_calls_resolve(self):
        paths = [MOD / "events/HSM_VER_crisis.txt"] + [MOD / "common" / folder / "HSM_VER_crisis.txt"
                for folder in ("scripted_triggers", "scripted_effects", "on_actions", "ideas",
                               "decisions", "decisions/categories")]
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"Missing production source: {path}")
                nodes = read(path)
                self.assertTrue(nodes)
                for n in walk(nodes):
                    if n.key.startswith(PREFIX) and n.value in ("yes", "no"):
                        self.assertIn(n.key, self.w.effects.keys() | self.w.triggers.keys())
                    if n.key == "country_event" and n.get("id").startswith(EVENT_PREFIX):
                        self.assertIn(n.get("id"), set(self.w.events))

    def test_civilian_benefit_has_only_contracted_modifiers(self):
        ideas = {n.key: n for n in walk(read(MOD / "common/ideas/HSM_VER_crisis.txt")) if n.key.startswith(PREFIX)}
        modifiers = ideas[PREFIX + "civilian_transit"].get("modifier")
        self.assertEqual({n.key: float(n.value) for n in modifiers},
                         {"production_speed_infrastructure_factor": 0.10, "industrial_capacity_factory": 0.05})

    def test_crisis_has_no_new_meter_or_division_manipulation(self):
        for path in MOD.rglob("HSM_VER_crisis.txt"):
            for n in walk(read(path)):
                self.assertNotIn(n.key, ("delete_unit", "delete_units", "delete_unit_template_and_units",
                                         "teleport_armies", "set_variable", "declare_war_on", "add_state_core"), str(path))
                if n.key == "add_to_variable":
                    self.assertEqual(n.get("var"), "loyalist_effort")
                    self.assertEqual(float(n.get("value")), 1)


if __name__ == "__main__":
    unittest.main(argv=[__file__] + REST, verbosity=2)
