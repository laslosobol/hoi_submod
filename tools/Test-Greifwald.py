"""Execute Greifwald's parsed production scripts, not a second campaign model.

python -B -X utf8 tools/Test-Greifwald.py [--eaw PATH] [--game PATH] [-q]
Only in-memory fixtures change. Unknown executable primitives fail closed.
The engine scheduler, UI, AI and multiplayer ordering still require playtesting.
"""
from __future__ import annotations

import copy
import datetime
import itertools
import re
import runpy
import unittest
from pathlib import Path

G = runpy.run_path(str(Path(__file__).with_name("Test-VereniaGrover.py")))
BASE, REG = G["BASE"], G["REG"]
Node, parse, read, walk, MOD, OPT = (G[k] for k in ("Node", "parse", "read", "walk", "MOD", "OPT"))
State, CharacterScope = G["State"], REG["CharacterScope"]
P = "HSM_AET_"
GROVER, DEAD = G["GROVER"], G["DEAD"]
COUNT, TRIMMEL = "AET_count_cloudet", "CHN_trimmel"
HOME, HEART = {"495", "496"}, G["HEART"]
BIRTHDAY = G["BIRTHDAY"]
MAIN = ("opening refuge home_budget congress mandate household court_accounts service "
        "working_table prepare obituary interim delegates union revenues succession winter "
        "workshops roads scholars demobilisation").split()
CRISIS = "letters audience hearing signature".split()
EVENTS = {1, 2, 3, 4, *range(10, 18), *range(20, 28), *range(30, 34), 40, 41, 42}
METADATA = G["OPTION_METADATA"] | {"available"}


def sources(folder):
    return sorted((MOD / folder).glob("HSM_AET*.txt"))


def native_preview(nodes):
    """Expose visible effect previews, preserving their production conditionals.

    Tests execute this on an isolated copy; normal execution still ignores
    effect_tooltip, and hidden rewards are never counted as visible previews.
    """
    result = []
    for node in nodes:
        if node.key in METADATA | {"hidden_effect", "custom_effect_tooltip", "show_ideas_tooltip"}:
            continue
        if node.key == "effect_tooltip":
            result.extend(node.children)
        elif node.key in ("if", "else_if", "else"):
            result.append(Node(node.key, node.op,
                               node.all("limit") + native_preview([n for n in node.children if n.key != "limit"])))
        else:
            result.append(node)
    return result


class GreifwaldWorld(G["GroverWorld"]):
    """Extend generic script operations only; route decisions stay in production."""

    def __init__(self):
        super().__init__("ERI")
        clean = copy.deepcopy(self.countries["CYA"])
        for tag in ("AET", "CHN", "HEL", "JER", "ANG", "ERI", "EYR", "GRI", "CYA"):
            if tag not in self.countries:
                self.countries[tag] = copy.deepcopy(clean)
                self.countries[tag].tag = self.countries[tag].original_tag = tag
        for c in self.countries.values():
            c.flags.clear()
            c.flag_days.clear()
            c.focuses.clear()
            c.characters.clear()
            c.ideas.clear()
            c.roles.clear()
            c.party_leaders.clear()
            c.variables.clear()
            c.dynamic_modifiers.clear()
            c.events.clear()
            c.political_power = 1000
            c.subject = c.capitulated = c.war = False
            c.overlord = c.faction = c.cosmetic = ""
            c.faction_leader = False
            c.exists = True
            c.leader = "fixture_" + c.tag
            c.government = "neutrality"
            c.forces = dict.fromkeys(("army", "air", "navy", "stockpile"), 0.0)
            c.officers.clear()
        self.host = self.root = self.sender = "AET"
        self.previous = None
        aet = self.countries["AET"]
        aet.characters = {COUNT}
        aet.leader = COUNT
        self.leader_roles = {
            character.key: character.all("country_leader")
            for path in [OPT.eaw / "common/characters/AET.txt", *sources("common/characters")]
            for container in read(path) if container.key == "characters"
            for character in container.children}
        for role in self.leader_roles[COUNT]:
            aet.party_leaders[REG["IDEOLOGY_GROUPS"][role.get("ideology")]] = COUNT
        aet.focuses = {"AET_realpolitik", "AET_complete_neutrality"}
        aet.capital = "495"
        aet.focus_tree = "greifwald_focus"
        aet.technology = {"host_tech", "native_tech"}
        aet.ideas = {"poverty", "lack_of_scientists2"}
        aet.forces = {"army": 40.0, "air": 200.0, "navy": 12.0, "stockpile": 400.0}
        aet.officers = {"host_general", "host_admiral"}
        self.countries["CHN"].characters = {TRIMMEL}
        self.countries["GRI"].exists = False
        self.countries["GRI"].characters = {GROVER}
        self.state_ids = {}
        # Native ownership/core sets are fixture inputs. No AET route flags are seeded.
        for sid, native in G["NATIVE_STATES"].items():
            history = Node("history", "=", native.get("history", []))
            owner = history.get("owner", "JER")
            if owner not in self.countries:
                self.countries[owner] = copy.deepcopy(clean)
                self.countries[owner].tag = self.countries[owner].original_tag = owner
                self.countries[owner].characters.clear()
            self.state_ids[sid] = State(
                owner=owner, controller=owner, sid=sid,
                cores={n.value for n in history.all("add_core_of")},
                region="164" if sid in G["CAPITAL_DISTRICT"] else "0")
        self.states = list(self.state_ids.values())
        self.homelands = {int(s): v for s, v in self.state_ids.items()}
        self.original_cores = {
            tag: [s for s in self.states if tag in s.cores] for tag in self.countries}
        self.arrays = {tag + ".original_cores": states for tag, states in self.original_cores.items()}
        self.own("382", "378")  # Deliberately only two of 38 Herzland states.
        for sid in HOME:
            self.own(sid)
        self.character_names = {}
        self.guarantees, self.military_access = set(), set()
        self.executed_effects = set()
        self.aet_hooks = {}
        for folder, target in (("common/scripted_triggers", self.triggers),
                               ("common/scripted_effects", self.effects)):
            for path in sources(folder):
                for node in read(path):
                    assert node.key not in target or target[node.key] == node.children, f"Conflicting scripted definition: {node.key}"
                    target[node.key] = node.children
        for path in sources("events"):
            self.events.update({n.get("id"): n for n in read(path) if n.key == "country_event"})
        # Execute the installed socioeconomic helpers, rather than duplicating their tiers.
        self.effects.update({n.key: n.children for n in read(OPT.eaw / "common/scripted_effects/EAW_misc_effect.txt")
                             if n.key in ("decrease_poverty", "decrease_illiteracy")})
        for path in sources("common/on_actions"):
            for container in read(path):
                for hook in container.children:
                    self.aet_hooks.setdefault(hook.key, []).extend(hook.get("effect", []))

    def own(self, *states, tag="AET"):
        for sid in states:
            self.state_ids[sid].owner = self.state_ids[sid].controller = tag

    def holder(self, tag):
        for c in self.countries.values():
            c.characters.discard(GROVER)
            if c.leader == GROVER:
                c.leader = "fixture_" + c.tag
        if tag:
            self.countries[tag].characters.add(GROVER)
        return self

    def resolve(self, value):
        if value == "THIS":
            return self.current_scope
        if value == "GRD":
            return self.global_targets.get("griffonian_empire", "GRI")
        return super().resolve(value)

    def check(self, nodes, tag="AET"):
        for n in nodes:
            if n.key == "is_owned_and_controlled_by":
                assert isinstance(tag, State)
                target = self.resolve(n.value)
                ok = tag.owner == target and tag.controller == target and tag.fully_controlled
            elif n.key in ("all_original_cores_owned_and_controlled_by_ROOT", "any_original_cores_controlled_by_ROOT"):
                states = self.original_cores[tag]
                result = (all(s.owner == self.root and s.controller == self.root and s.fully_controlled for s in states)
                          if n.key.startswith("all_") else any(s.controller == self.root for s in states))
                ok = result == (n.value == "yes")
            elif n.key == "has_country_flag" and n.children:
                raise AssertionError("Numeric flag comparisons are not yet modelled")
            elif n.key == "check_variable":
                assert len(n.children) == 1
                v = n.children[0]
                ok = REG["COMPARE"][v.op](self.countries[tag].variables.get(v.key, 0), float(v.value))
            elif n.key == "infrastructure":
                assert isinstance(tag, State)
                # Engine docs: building_count_trigger uses `<Building> < <int>`.
                ok = REG["COMPARE"][n.op](tag.buildings.get("infrastructure", 0), float(n.value))
            else:
                ok = super().check([n], tag)
            if not ok:
                return False
        return True

    def run(self, nodes, tag="AET"):
        old_scope = getattr(self, "current_scope", None)
        self.current_scope = tag
        try:
            # Keep whole if/else chains in GroverWorld; dispatch extensions per node.
            taken = None
            for n in nodes:
                if n.key in ("if", "else_if", "else"):
                    if n.key == "if":
                        taken = False
                    assert taken is not None, "Conditional without if"
                    if not taken and (n.key == "else" or self.check(n.get("limit", []), tag)):
                        taken = True
                        self.run([x for x in n.children if x.key != "limit"], tag)
                elif n.key in self.effects:
                    self.executed_effects.add(n.key)
                    assert n.value == "yes", "Parameterized effects need explicit support"
                    self.run(self.effects[n.key], tag)
                elif n.key in (COUNT, TRIMMEL):
                    assert n.key in self.countries[tag].characters, "Character must belong to current country"
                    self.scoped_run(n.children, CharacterScope(n.key, tag), tag)
                elif n.key in ("every_possible_country", "random_country"):
                    eligible = [t for t, c in self.countries.items()
                                if (n.key == "every_possible_country" or c.exists)
                                and self.scoped_check(n.get("limit", []), t, tag)]
                    for target in (eligible[:1] if n.key == "random_country" else eligible):
                        self.scoped_run([x for x in n.children if x.key != "limit"], target, tag)
                elif n.key == "set_character_name":
                    assert isinstance(tag, CharacterScope)
                    self.character_names[tag.token] = n.value
                elif n.key == "promote_character":
                    assert not n.children or {x.key for x in n.children} == {"character", "ideology"}
                    token = n.get("character") if n.children else n.value
                    assert token in self.countries[tag].characters
                    roles = self.leader_roles[token]
                    if n.children:
                        roles = [r for r in roles if r.get("ideology") == n.get("ideology")]
                    assert len(roles) == 1, "Multi-role promotion requires an explicit native ideology"
                    group = REG["IDEOLOGY_GROUPS"][roles[0].get("ideology")]
                    self.countries[tag].party_leaders[group] = token
                    if self.countries[tag].government == group:
                        self.countries[tag].leader = token
                elif n.key in ("retire_character", "retire"):
                    token = tag.token if isinstance(tag, CharacterScope) else n.value
                    country = tag.country if isinstance(tag, CharacterScope) else tag
                    self.countries[country].characters.discard(token)
                    if self.countries[country].leader == token:
                        self.countries[country].leader = ""
                    self.character_actions.append(("retire", token, country))
                elif n.key == "mark_focus_tree_layout_dirty":
                    assert n.value == "yes"  # UI-only; not a gameplay reward.
                elif n.key == "swap_ideas":
                    assert {x.key for x in n.children} == {"add_idea", "remove_idea"}
                    c = self.countries[tag]
                    c.ideas.discard(n.get("remove_idea"))
                    c.ideas.add(n.get("add_idea"))
                elif n.key in ("give_guarantee", "give_military_access"):
                    (self.guarantees if n.key == "give_guarantee" else self.military_access).add((tag, self.resolve(n.value)))
                elif n.key == "remove_wargoal":
                    self.countries[tag].goals.discard((n.get("type"), self.resolve(n.get("target"))))
                else:
                    super().run([n], tag)
        finally:
            self.current_scope = old_scope

    def aet(self, suffix, tag="AET", sender=None):
        self.root = tag
        if sender is not None:
            self.sender = sender
        self.run(parse(f"{P}{suffix} = yes"), tag)

    def valid(self, suffix, tag="AET", sender=None):
        self.root = tag
        if sender is not None:
            self.sender = sender
        return self.test(P + suffix, tag)

    def complete(self, suffix, tag="AET"):
        self.root = tag
        f = self.focuses[P + suffix]
        c = self.countries[tag]
        assert f.get("id") not in c.focuses, f"Already completed: {suffix}"
        assert all(any(n.value in c.focuses for n in group.children) for group in f.all("prerequisite")), suffix
        assert all(n.value not in c.focuses for group in f.all("mutually_exclusive") for n in group.children), suffix
        assert self.check(f.get("available", []), tag), f"Unavailable: {suffix}"
        c.focuses.add(f.get("id"))
        self.run(f.get("completion_reward", []), tag)

    def option(self, number, effect):
        eid = f"HSM_AET.{number}"
        matches = [o for o in self.events[eid].all("option")
                   if any(n.key == P + effect for n in walk(o.children))]
        assert len(matches) == 1, f"Expected one {eid} option calling {effect}, got {len(matches)}"
        return matches[0]

    def click(self, number, effect, tag="AET", sender=None, stale=False):
        self.root = tag
        if sender is not None:
            self.sender = sender
        option = self.option(number, effect)
        if not stale:
            assert self.check(option.get("trigger", []), tag), f"Hidden choice: {number}/{effect}"
            assert self.check(option.get("available", []), tag), f"Unavailable choice: {number}/{effect}"
        self.run([n for n in option.children if n.key not in METADATA], tag)

    def answer(self, number, effect, tag="AET"):
        eid = f"HSM_AET.{number}"
        packet = next((p for p in self.scheduled if p[1:3] == (tag, eid)), None)
        assert packet, f"Production did not schedule {eid} for {tag}"
        delay = max(0, packet[0] - self.day)
        assert delay == int(delay), "Sub-day scheduler delivery needs explicit support"
        self.advance_days(int(delay))
        assert self.deliver(eid, tag), f"Production trigger rejected {eid}"
        self.click(number, effect, tag)

    def scene(self, focus, number, effect):
        self.complete(focus)
        self.answer(number, effect)
        return self

    def take_decision(self, suffix):
        self.root = self.sender = "AET"
        matches = [n for p in sources("common/decisions") for category in read(p)
                   for n in category.children if n.key == P + suffix]
        assert len(matches) == 1, suffix
        decision = matches[0]
        assert decision.get("cost", "0") == "0", "Decision payment needs explicit support"
        for gate in ("visible", "available"):
            assert self.check(decision.get(gate, []), "AET"), f"Decision {gate}: {suffix}"
        self.run(decision.get("complete_effect", []), "AET")

    def daily(self, tag="AET"):
        self.root = self.sender = tag
        assert "on_daily" in self.aet_hooks or "on_daily_" + tag in self.aet_hooks, "Missing reconciliation hook"
        self.run(self.aet_hooks.get("on_daily", []), tag)
        self.run(self.aet_hooks.get("on_daily_" + tag, []), tag)

    def snapshot(self):
        # Instrumentation counters are intentionally excluded, all gameplay retained.
        return copy.deepcopy((super().snapshot(), self.character_names, self.idea_actions,
                              self.goal_actions, self.relations, self.annexations,
                              self.guarantees, self.military_access))


class Harness(unittest.TestCase):
    def test_promotion_respects_native_party_roles_and_rejects_ambiguous_count(self):
        w = GreifwaldWorld()
        w.countries["AET"].leader = "fixture_incumbent"
        with self.assertRaisesRegex(AssertionError, "explicit native ideology"):
            w.run(parse("promote_character = AET_count_cloudet"))
        w.run(parse("promote_character = { character = AET_count_cloudet ideology = conservatism }"))
        self.assertEqual(w.countries["AET"].party_leaders["democratic"], COUNT)
        self.assertEqual(w.countries["AET"].leader, "fixture_incumbent")
        w.run(parse("promote_character = { character = AET_count_cloudet ideology = despotism }"))
        self.assertEqual(w.countries["AET"].leader, COUNT)

    def test_unknown_operations_raise_and_tooltips_do_not_execute(self):
        w = GreifwaldWorld()
        for kind in ("effect", "trigger"):
            with self.subTest(kind=kind), self.assertRaises(AssertionError):
                (w.run if kind == "effect" else w.check)(parse("not_a_real_primitive = yes"), "AET")
        before = w.snapshot()
        w.run(parse("effect_tooltip = { add_political_power = 999 }"))
        self.assertEqual(w.snapshot(), before)

    def test_character_identity_and_partial_control_are_fixture_inputs(self):
        w = GreifwaldWorld()
        self.assertTrue(w.check(parse(f"has_country_leader = {{ character = {COUNT} ruling_only = yes }}")))
        w.character_names[TRIMMEL] = COUNT
        self.assertFalse(w.check(parse(f"has_country_leader = {{ character = {TRIMMEL} ruling_only = yes }}")))
        w.state_ids["378"].fully_controlled = False
        self.assertFalse(w.check(parse("is_owned_and_controlled_by = AET"), w.state_ids["378"]))
        self.assertEqual({s.sid for s in w.states if s.owner == "AET" and s.sid in HEART}, {"378", "382"})

    def test_nested_country_prev_removes_only_the_target_wargoal(self):
        w = GreifwaldWorld()
        w.countries["GRI"].goals = {("annex_everything", "AET"), ("annex_everything", "CYA"),
                                     ("take_state_focus", "AET")}
        w.run(parse("GRI = { every_country = { limit = { tag = AET } GRI = { remove_wargoal = { type = annex_everything target = PREV } } } }"))
        self.assertEqual(w.countries["GRI"].goals, {("annex_everything", "CYA"), ("take_state_focus", "AET")})

    def test_native_socioeconomic_helpers_execute_real_tiers(self):
        w = GreifwaldWorld()
        w.run(parse("decrease_poverty = yes decrease_illiteracy = yes"))
        self.assertEqual(w.countries["AET"].ideas, {"poverty1", "lack_of_scientists3"})


class CoreEffects(unittest.TestCase):
    """Run core effects without waiting for the narrative file; no UI is simulated."""

    def relief(self, holder="AET"):
        w = GreifwaldWorld().holder(holder)
        w.complete("opening")
        w.aet("accept_relief")
        w.complete("refuge")
        w.aet("receive_refugees")
        return w

    def test_core_relief_rewards_are_once_only(self):
        w = self.relief()
        before = w.snapshot()
        for effect in ("finish_opening", "accept_relief", "finish_refuge", "receive_refugees"):
            w.aet(effect)
        self.assertEqual(w.snapshot(), before)

    def test_original_recovery_executes_from_absent_gri(self):
        w = self.relief("GRI")
        self.assertIn(GROVER, w.countries["AET"].characters)
        self.assertNotIn(GROVER, w.countries["GRI"].characters)
        self.assertEqual([a[0] for a in w.character_actions], ["set_nationality"])

    def test_unknown_dead_and_adult_predicates_execute_independently(self):
        w = self.relief(None)
        self.assertFalse(w.valid("local_alive"))
        self.assertNotIn(DEAD, w.global_flags)
        w.holder("AET")
        for delta in (-1, 0, 1):
            w.date = BIRTHDAY + datetime.timedelta(days=delta)
            self.assertEqual(w.valid("adult"), delta > 0)
        w.global_flags.add(DEAD)
        self.assertFalse(w.valid("local_alive"))
        self.assertFalse(w.valid("adult"))

    def test_retired_custody_effects_are_inert_even_with_old_pending_flags(self):
        for host in ("CYA", "EYR"):
            with self.subTest(host=host):
                w = self.relief(host)
                w.countries["AET"].flags.add(P + "request_pending")
                w.countries[host].flags.add(P + "custody_request")
                before = w.snapshot()
                self.assertFalse(w.valid("can_request"))
                self.assertFalse(w.test(P + "host_can_offer", host))
                w.aet("request_custody")
                w.aet("offer_custody", host, "AET")
                w.aet("refuse_custody", host, "AET")
                self.assertEqual(w.snapshot(), before)
                self.assertIn(GROVER, w.countries[host].characters)
                self.assertNotIn(GROVER, w.countries["AET"].characters)


    def test_closed_mission_keeps_actual_local_household_protected(self):
        w = self.relief()
        w.aet("close_relief")
        self.assertFalse(w.valid("active"))
        self.assertTrue(w.valid("protected_household"))
        self.assertFalse(w.test("HSM_VER_GRO_native_household_allowed", "CYA"))
        w.holder("CYA")
        self.assertFalse(w.valid("protected_household"))

    def test_actual_trimmel_starts_crisis_without_custody(self):
        w = self.relief(None)
        w.character_names[COUNT] = "CHN_hivesmarschall_trimmel"
        w.countries["AET"].focuses.add("AET_weird_lord")
        w.daily()
        self.assertFalse(w.valid("crisis"))
        w.countries["AET"].leader = TRIMMEL
        w.countries["AET"].characters.add(TRIMMEL)
        w.countries["CHN"].characters.discard(TRIMMEL)
        w.daily()
        self.assertTrue(w.valid("crisis"))
        before = w.snapshot()
        w.daily()
        self.assertEqual(w.snapshot(), before)

    def test_public_budget_executes_affordability_and_exact_cost(self):
        w = self.relief()
        w.countries["AET"].political_power = 49
        before = w.snapshot()
        w.aet("home_public")
        self.assertEqual(w.snapshot(), before)
        w.countries["AET"].political_power = 50
        w.aet("home_public")
        self.assertEqual(w.countries["AET"].political_power, 0)


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = GreifwaldWorld()
        missing = [P + name for name in MAIN + CRISIS if P + name not in cls.template.focuses]
        assert not missing, "Incoming production scripts are missing: " + ", ".join(missing)

    def world(self, holder="GRI"):
        return copy.deepcopy(self.template).holder(holder)

    def congress(self, holder="AET"):
        w = self.world(holder)
        for focus, number, choice in (("opening", 1, "accept_relief"), ("refuge", 2, "receive_refugees"),
                                      ("home_budget", 3, "home_public"), ("congress", 4, "sign_congress")):
            w.scene(focus, number, choice)
        return w

    def mandated(self):
        return self.congress().scene("mandate", 10, "accept_mandate")

    def development(self, w):
        for suffix in ("workshops", "roads", "scholars", "demobilisation"):
            w.complete(suffix)
        return w

    def prepared(self, w=None):
        if w is None:
            w = self.mandated()
        w.scene("household", 11, "school_open")
        w.answer(27, "gift_private")
        w.scene("court_accounts", 12, "accounts_public")
        w.scene("service", 13, "service_law")
        w.scene("working_table", 14, "judge_patron")
        w.answer(15, "revise_contracts")
        self.development(w)
        w.scene("prepare", 16, "sign_handover")
        return w

    def replace_count(self, w, keep_count=True):
        # External native AET_weird_lord outcome is fixture input, not campaign progress.
        w.countries["CHN"].characters.discard(TRIMMEL)
        c = w.countries["AET"]
        c.characters.add(TRIMMEL)
        if not keep_count:
            c.characters.discard(COUNT)
        c.leader = TRIMMEL
        c.party_leaders["neutrality"] = TRIMMEL
        c.focuses.add("AET_weird_lord")
        w.character_names[TRIMMEL] = COUNT
        w.daily()
        return w


class Custody(Fixture):
    def test_impostor_grover_and_duplicate_live_custody_do_not_authorize_mandate(self):
        w = self.congress(None)
        w.countries["AET"].ideas.add("ANG_fake_grover")
        w.countries["AET"].characters.add("ANG_fake_grover_char")
        self.assertFalse(w.valid("local_alive"))
        self.assertFalse(w.valid("can_mandate"))
        w.holder("AET")
        w.countries["CYA"].characters.add(GROVER)
        self.assertFalse(w.valid("local_alive"))
        self.assertFalse(w.valid("can_mandate"))

    def test_unknown_is_not_dead_and_cannot_create_an_emperor(self):
        for holder in (None, "CYA", "ERI", "EYR"):
            with self.subTest(holder=holder):
                w = self.congress(holder)
                self.assertFalse(w.valid("can_mandate"))
                self.assertFalse(w.valid("can_union"))
                before = w.snapshot()
                for effect in ("recover", "accept_mandate", "acknowledge_death"):
                    w.aet(effect)
                self.assertEqual(w.snapshot(), before)
                self.assertNotIn(DEAD, w.global_flags)
                self.assertEqual([t for t, c in w.countries.items() if GROVER in c.characters], [holder] if holder else [])
        w = self.congress(None)
        w.global_flags.add(DEAD)
        self.assertTrue(w.valid("can_union"))

    def test_dead_flag_overrides_even_a_leftover_original_character(self):
        w = self.congress()
        w.global_flags.add(DEAD)
        self.assertFalse(w.valid("local_alive"))
        self.assertFalse(w.valid("minor"))
        self.assertFalse(w.valid("adult"))
        self.assertFalse(w.valid("can_mandate"))
        self.assertTrue(w.valid("can_union"))

    def test_recovery_requires_capital_and_absent_gri_without_a_live_holder(self):
        for obstruction in (None, "capital", "gri_exists", "foreign", "dead"):
            with self.subTest(obstruction=obstruction):
                w = self.world("GRI")
                if obstruction == "capital":
                    w.own("382", tag="CYA")
                elif obstruction == "gri_exists":
                    w.countries["GRI"].exists = True
                    w.countries["GRI"].capitulated = True
                elif obstruction == "foreign":
                    w.holder("CYA")
                elif obstruction == "dead":
                    w.global_flags.add(DEAD)
                w.scene("opening", 1, "accept_relief")
                self.assertEqual(GROVER in w.countries["AET"].characters, obstruction is None)
                self.assertFalse(any(a[0] == "recruit_character" and a[1] == GROVER for a in w.character_actions))

    def test_foreign_guardians_remain_in_control_without_a_transfer_decision(self):
        for condition in ("regent", "sovereign", "war", "capitulated", "subject"):
            with self.subTest(condition=condition):
                w = self.congress("CYA")
                host = w.countries["CYA"]
                if condition == "sovereign":
                    host.leader = GROVER
                elif condition == "war":
                    host.war = True
                elif condition == "capitulated":
                    host.capitulated = True
                elif condition == "subject":
                    host.subject = True
                    host.overlord = "JER"
                with self.assertRaises(AssertionError):
                    w.take_decision("offer_shelter")
                w.take_decision("household_review")
                w.daily()
                w.advance_days(100)
                w.daily()
                self.assertIn(GROVER, host.characters)
                self.assertFalse(w.valid("can_mandate"))
                self.assertFalse(w.valid("can_union"))
                self.assertFalse(any(p[2] in ("HSM_AET.40", "HSM_AET.41", "HSM_AET.42") for p in w.scheduled))

    def test_saved_custody_offer_cannot_deliver_or_transfer_after_retirement(self):
        w = self.congress("CYA")
        w.countries["AET"].flags.add(P + "request_pending")
        w.countries["CYA"].flags.add(P + "custody_request")
        w.run(parse("country_event = { id = HSM_AET.40 days = 1 }"), "CYA")
        w.advance_days(1)
        self.assertFalse(w.deliver("HSM_AET.40", "CYA"))
        before = w.snapshot()
        for reply in ("offer_custody", "refuse_custody"):
            w.click(40, reply, "CYA", sender="AET", stale=True)
        self.assertEqual(w.snapshot(), before)
        fallback = next(o for o in w.events["HSM_AET.40"].all("option") if o.get("name") == P + "context_lost")
        self.assertTrue(w.check(fallback.get("trigger", []), "CYA"))
        w.run([n for n in fallback.children if n.key not in METADATA], "CYA")
        self.assertEqual(w.snapshot(), before)


class Regency(Fixture):
    def test_interruption_removes_only_provenance_marked_regency_cores(self):
        w = self.congress()
        w.state_ids["378"].cores.add("AET")
        w.scene("mandate", 10, "accept_mandate")
        self.assertNotIn(P + "temporary_core", w.state_ids["378"].flags)
        self.assertIn(P + "temporary_core", w.state_ids["382"].flags)
        w.global_flags.add(DEAD)
        w.holder(None)
        w.daily()
        self.assertIn("AET", w.state_ids["378"].cores)
        self.assertNotIn("AET", w.state_ids["382"].cores)
        self.assertTrue(all("AET" in w.state_ids[s].cores for s in HOME))
        self.assertFalse(w.state_transfers)

    def test_foreign_faction_leader_must_accept_and_stale_acceptance_cannot_move_gri(self):
        for response in ("accept", "refuse", "stale"):
            with self.subTest(response=response):
                w = self.prepared()
                w.countries["AET"].faction = "foreign_alliance"
                w.countries["JER"].faction = "foreign_alliance"
                w.countries["JER"].faction_leader = True
                w.date = BIRTHDAY + datetime.timedelta(days=1)
                w.daily()
                self.assertFalse(w.countries["GRI"].faction)
                w.advance_days(1)
                self.assertTrue(w.deliver("HSM_AET_system.3", "JER"))
                event = w.events["HSM_AET_system.3"]
                option = next(o for o in event.all("option") if o.get("name") == "HSM_AET_system.3." + ("b" if response == "refuse" else "a"))
                if response == "stale":
                    w.countries["AET"].faction = "other_alliance"
                before = w.snapshot()
                w.run([n for n in option.children if n.key not in METADATA], "JER")
                if response == "stale":
                    self.assertEqual(w.snapshot(), before)
                self.assertEqual(w.countries["GRI"].faction, "foreign_alliance" if response == "accept" else "")

    def test_restored_tree_is_playable_without_further_annexations_or_character_changes(self):
        w = self.prepared()
        w.date = BIRTHDAY + datetime.timedelta(days=1)
        w.daily()
        before_land = copy.deepcopy(w.state_transfers)
        before_characters = copy.deepcopy(w.character_actions)
        for suffix in ("oath", "towns", "army", "schools", "debts", "settlement"):
            w.complete("GRI_" + suffix, "GRI")
            with self.assertRaisesRegex(AssertionError, "Already completed"):
                w.complete("GRI_" + suffix, "GRI")
        self.assertEqual(w.state_transfers, before_land)
        self.assertEqual(w.character_actions, before_characters)
        self.assertIn(P + "imperial_settlement", w.countries["GRI"].ideas)
        self.assertNotIn(P + "imperial_compact", w.countries["GRI"].ideas)

    def test_restored_oath_removes_inherited_bureaucracy_and_previews_the_removal(self):
        w = self.prepared()
        # Pre-annexation native ideas are external fixture state, not route rewards.
        w.countries["GRI"].ideas.update({"GRI_bureaucracy", "GRI_land_thougth"})
        w.countries["AET"].ideas.add("GRI_bureaucracy")  # Scope sentinel.
        w.date = BIRTHDAY + datetime.timedelta(days=1)
        w.daily()
        self.assertIn("GRI_bureaucracy", w.countries["GRI"].ideas)
        before = w.snapshot()
        preview = copy.deepcopy(w)
        preview.root = "GRI"
        preview.run(native_preview(w.focuses[P + "GRI_oath"].get("completion_reward", [])), "GRI")
        self.assertNotIn("GRI_bureaucracy", preview.countries["GRI"].ideas,
                         "The native focus preview must disclose the removal")
        self.assertEqual(w.snapshot(), before)
        pp = w.countries["GRI"].political_power
        w.complete("GRI_oath", "GRI")
        self.assertNotIn("GRI_bureaucracy", w.countries["GRI"].ideas)
        self.assertIn("GRI_land_thougth", w.countries["GRI"].ideas)
        self.assertIn("GRI_bureaucracy", w.countries["AET"].ideas)
        self.assertEqual(w.countries["GRI"].political_power, pp + 50)
        before = w.snapshot()
        with self.assertRaisesRegex(AssertionError, "Already completed"):
            w.complete("GRI_oath", "GRI")
        self.assertEqual(w.snapshot(), before)

    def test_handover_bonus_is_bound_to_actual_transfer_and_cannot_accumulate(self):
        w = self.prepared()
        c = w.countries["AET"]
        efficiency = P + "value_production_factory_max_efficiency_factor"
        research = P + "value_research_speed_factor"
        baseline = {key: c.variables.get(key, 0) for key in (efficiency, research)}
        self.assertNotIn(P + "handover_done", c.flags)
        self.assertAlmostEqual(baseline[efficiency], 0)
        self.assertAlmostEqual(baseline[research], .10)  # School + scholars, already earned.
        for obstruction in ("minor", "war", "occupation", "identity"):
            with self.subTest(obstruction=obstruction):
                blocked = copy.deepcopy(w)
                if obstruction != "minor":
                    blocked.date = BIRTHDAY + datetime.timedelta(days=1)
                if obstruction == "war":
                    blocked.countries["AET"].war = True
                elif obstruction == "occupation":
                    blocked.state_ids["378"].fully_controlled = False
                elif obstruction == "identity":
                    self.replace_count(blocked)
                blocked.daily()
                blocked.aet("handover")
                self.assertFalse(blocked.state_transfers)
                self.assertNotIn(P + "handover_done", blocked.countries["AET"].flags)
                for key, value in baseline.items():
                    self.assertAlmostEqual(blocked.countries["AET"].variables.get(key, 0), value)
        w.date = BIRTHDAY + datetime.timedelta(days=1)
        w.daily()
        self.assertEqual({sid for sid, old, new in w.state_transfers}, {"378", "382"})
        self.assertIn(P + "handover_done", c.flags)
        self.assertNotIn(P + "handover_done", w.countries["GRI"].flags)
        self.assertAlmostEqual(c.variables[efficiency], baseline[efficiency] + .10)
        self.assertAlmostEqual(c.variables[research], baseline[research] + .05)
        modifier = next(n for path in sources("common/dynamic_modifiers") for n in read(path)
                        if n.key == P + "compact")
        self.assertEqual(modifier.get("production_factory_max_efficiency_factor"), efficiency)
        self.assertEqual(modifier.get("research_speed_factor"), research)
        before = w.snapshot()
        for _ in range(3):
            w.aet("handover")
            w.click(16, "sign_handover", stale=True)
            w.aet("refresh")
            w.daily()
        self.assertEqual(w.snapshot(), before)
        self.assertEqual(len(w.unit_transfers), 1)

    def test_daily_repairs_a_legacy_handover_bonus_without_repeating_the_transfer(self):
        restored = self.prepared()
        restored.date = BIRTHDAY + datetime.timedelta(days=1)
        restored.daily()
        for legacy, relationship in itertools.product((False, True), ("allied", "annexed", "subject", "war")):
            with self.subTest(legacy=legacy, relationship=relationship):
                w = copy.deepcopy(restored)
                c, gri = w.countries["AET"], w.countries["GRI"]
                if legacy:
                    c.flags.remove(P + "handover_done")  # Save predating the county reward.
                # Subsequent diplomacy/conquest is external history; the original transfer
                # and its preparation/completion flags were earned through production.
                if relationship == "annexed":
                    gri.exists = False
                    w.own("378", "382", tag="CYA")
                elif relationship == "subject":
                    gri.subject, gri.overlord = True, "CYA"
                elif relationship == "war":
                    w.join_defence("GRI", "AET")
                self.assertEqual(w.valid("restored_pair"), relationship == "allied")
                w.aet("refresh")
                self.assertAlmostEqual(c.variables.get(P + "value_production_factory_max_efficiency_factor", 0),
                                       0 if legacy else .10)
                self.assertAlmostEqual(c.variables[P + "value_research_speed_factor"], .10 if legacy else .15)
                transfers = copy.deepcopy((w.state_transfers, w.unit_transfers, w.character_actions))
                pp = c.political_power
                w.daily()
                self.assertIn(P + "handover_done", c.flags)
                self.assertAlmostEqual(c.variables[P + "value_production_factory_max_efficiency_factor"], .10)
                self.assertAlmostEqual(c.variables[P + "value_research_speed_factor"], .15)
                self.assertEqual((w.state_transfers, w.unit_transfers, w.character_actions), transfers)
                self.assertEqual(c.political_power, pp)
                before = w.snapshot()
                for _ in range(3):
                    w.daily()
                    w.aet("refresh")
                self.assertEqual(w.snapshot(), before)

    def test_legacy_handover_repair_requires_both_historical_milestones_and_no_union(self):
        restored = self.prepared()
        restored.date = BIRTHDAY + datetime.timedelta(days=1)
        restored.daily()
        for obstruction in ("missing_preparation", "missing_completion", "union"):
            with self.subTest(obstruction=obstruction):
                w = copy.deepcopy(restored)
                c = w.countries["AET"]
                c.flags.remove(P + "handover_done")
                # Incomplete/conflicting legacy metadata must not fabricate entitlement.
                if obstruction == "missing_preparation":
                    c.flags.remove(P + "prepare_done")
                elif obstruction == "missing_completion":
                    c.flags.remove(P + "completed")
                else:
                    c.flags.add(P + "union_done")
                w.aet("refresh")
                before = w.snapshot()
                w.daily()
                self.assertEqual(w.snapshot(), before)
                self.assertNotIn(P + "handover_done", c.flags)
                self.assertAlmostEqual(c.variables.get(P + "value_production_factory_max_efficiency_factor", 0), 0)
                self.assertAlmostEqual(c.variables[P + "value_research_speed_factor"], .10)

    def test_gri_daily_bureaucracy_repair_requires_both_restoration_and_completed_oath(self):
        restored = self.prepared()
        restored.date = BIRTHDAY + datetime.timedelta(days=1)
        restored.daily()
        before_oath = copy.deepcopy(restored)
        restored.complete("GRI_oath", "GRI")
        native = self.world("GRI")
        native.countries["GRI"].exists = True
        native.countries["GRI"].leader = GROVER
        for name, base, should_remove in (("native_regency", native, False),
                                          ("restored_before_oath", before_oath, False),
                                          ("legacy_completed_oath", restored, True)):
            with self.subTest(state=name):
                w = copy.deepcopy(base)
                c = w.countries["GRI"]
                c.ideas.update({"GRI_bureaucracy", "GRI_land_thougth"})
                before = w.snapshot()
                pp = c.political_power
                w.daily("GRI")
                self.assertEqual("GRI_bureaucracy" not in c.ideas, should_remove)
                self.assertIn("GRI_land_thougth", c.ideas)
                self.assertEqual(c.political_power, pp, "Migration must not replay oath payment")
                if not should_remove:
                    self.assertEqual(w.snapshot(), before)
                after = w.snapshot()
                w.daily("GRI")
                self.assertEqual(w.snapshot(), after)

    def test_union_completion_never_grants_the_handover_bonus(self):
        for former_regency in (False, True):
            with self.subTest(former_regency=former_regency):
                w = self.prepared() if former_regency else self.congress(None)
                w.global_flags.add(DEAD)
                w.holder(None)
                w.daily()
                for focus, event, effect in (("obituary", 20, "acknowledge_death"),
                                             ("interim", 21, "accept_interim"),
                                             ("delegates", 22, "delegates_equal"),
                                             ("union", 23, "sign_union"),
                                             ("revenues", 24, "revenues_local"),
                                             ("succession", 25, "succession_assembly")):
                    w.scene(focus, event, effect)
                if not former_regency:
                    self.development(w)
                w.scene("winter", 26, "conclude_union")
                c = w.countries["AET"]
                self.assertIn(P + "completed", c.flags)
                self.assertNotIn(P + "handover_done", c.flags)
                self.assertFalse(w.state_transfers)
                self.assertAlmostEqual(c.variables.get(P + "value_production_factory_max_efficiency_factor", 0), 0)
                self.assertAlmostEqual(c.variables[P + "value_research_speed_factor"], .10 if former_regency else .05)
                before = w.snapshot()
                w.aet("handover")
                w.aet("refresh")
                w.click(26, "conclude_union", stale=True)
                w.daily()
                self.assertEqual(w.snapshot(), before)

    def test_majority_is_strict_and_preparation_can_finish_while_minor(self):
        w = self.prepared()
        self.assertIn(P + "prepare_done", w.countries["AET"].flags)
        self.assertFalse(w.countries["GRI"].exists)
        for date, adult in ((BIRTHDAY - datetime.timedelta(days=1), False), (BIRTHDAY, False),
                            (BIRTHDAY + datetime.timedelta(days=1), True)):
            w.date = date
            self.assertEqual(w.valid("adult"), adult)
            self.assertEqual(w.valid("minor"), not adult)
        w.countries["AET"].war = True
        w.daily()
        self.assertFalse(w.countries["GRI"].exists)
        w.countries["AET"].war = False
        w.daily()
        self.assertTrue(w.countries["GRI"].exists)
        self.assertIn(GROVER, w.countries["GRI"].characters)

    def test_partial_herzland_handover_never_takes_home_adelart_or_foreign_land(self):
        w = self.prepared()
        w.own("493", "494")  # Conquered Adelart must remain outside the treaty.
        w.state_ids["378"].cores.add("AET")  # Marked programme core; removed on handover.
        before_owners = {sid: s.owner for sid, s in w.state_ids.items()}
        forces = copy.deepcopy(w.countries["AET"].forces)
        officers = copy.deepcopy(w.countries["AET"].officers)
        w.countries["GRI"].goals.update((kind, target) for kind in ("annex_everything", "take_state_focus", "puppet_wargoal_focus")
                                         for target in ("AET", "CYA"))
        w.date = BIRTHDAY + datetime.timedelta(days=1)
        w.daily()
        self.assertEqual({sid for sid, owner in before_owners.items() if w.state_ids[sid].owner != owner}, {"382", "378"})
        for sid in HOME | {"493", "494"}:
            self.assertEqual(w.state_ids[sid].owner, "AET")
        self.assertEqual(w.countries["GRI"].capital, "382")
        self.assertEqual(w.global_targets["griffonian_empire"], "GRI")
        self.assertEqual(w.global_variables["global.griffonian_empire_var"], "GRI")
        self.assertEqual(w.countries["GRI"].leader, GROVER)
        for kind in forces:
            ratio = 0 if kind == "navy" else .25
            self.assertEqual(w.countries["GRI"].forces[kind], forces[kind] * ratio)
            self.assertEqual(w.countries["AET"].forces[kind], forces[kind] * (1 - ratio))
        self.assertEqual(w.countries["AET"].officers, officers)
        self.assertFalse(w.countries["GRI"].officers)
        self.assertFalse(w.countries["GRI"].subject)
        self.assertFalse(w.countries["GRI"].goals)
        self.assertEqual(w.countries["AET"].faction, w.countries["GRI"].faction)
        self.assertTrue(w.countries["AET"].faction)
        before = w.snapshot()
        w.daily()
        w.aet("handover")
        self.assertEqual(w.snapshot(), before)
        self.assertEqual(len(w.unit_transfers), 1)

    def test_occupation_and_existing_gri_block_handover_without_erasing_preparation(self):
        for obstruction in ("occupied_herzland", "capital", "homeland", "existing_gri", "lost_custody"):
            with self.subTest(obstruction=obstruction):
                w = self.prepared()
                w.date = BIRTHDAY + datetime.timedelta(days=1)
                if obstruction == "occupied_herzland":
                    w.state_ids["378"].fully_controlled = False
                elif obstruction in ("capital", "homeland"):
                    w.state_ids["382" if obstruction == "capital" else "495"].controller = "CYA"
                elif obstruction == "existing_gri":
                    w.countries["GRI"].exists = True
                else:
                    w.holder("CYA")
                self.assertFalse(w.valid("can_handover"))
                w.daily()
                self.assertFalse(w.state_transfers)
                self.assertFalse(w.unit_transfers)
                self.assertIn(P + "prepare_done", w.countries["AET"].flags)

    def test_death_mid_regency_opens_complete_union_without_resurrection(self):
        w = self.mandated()
        w.scene("household", 11, "school_open")
        w.global_flags.add(DEAD)
        w.holder(None)
        w.daily()
        self.assertFalse(w.valid("regency"))
        self.assertTrue(w.valid("can_union"))
        for focus, event, effect in (("obituary", 20, "acknowledge_death"), ("interim", 21, "accept_interim"),
                                     ("delegates", 22, "delegates_equal"), ("union", 23, "sign_union"),
                                     ("revenues", 24, "revenues_local"), ("succession", 25, "succession_assembly")):
            w.scene(focus, event, effect)
        self.development(w)
        w.scene("winter", 26, "conclude_union")
        self.assertIn(P + "completed", w.countries["AET"].flags)
        self.assertFalse(w.countries["GRI"].exists)
        self.assertTrue(all(GROVER not in c.characters for c in w.countries.values()))
        for sid in ("382", "378"):
            self.assertIn("AET", w.state_ids[sid].cores)
            self.assertNotIn(P + "temporary_core", w.state_ids[sid].flags)
        self.assertFalse(w.state_transfers)
        self.assertFalse(w.goal_actions)
        before = w.snapshot()
        w.click(11, "school_court", stale=True)
        w.click(27, "gift_public", stale=True)
        w.click(26, "conclude_union", stale=True)
        self.assertEqual(w.snapshot(), before)


class Identity(Fixture):
    def test_actual_trimmel_not_display_name_focus_history_or_character_presence(self):
        w = self.congress()
        w.countries["AET"].focuses.add("AET_weird_lord")
        w.countries["AET"].characters.add(TRIMMEL)
        w.countries["CHN"].characters.discard(TRIMMEL)
        w.character_names[COUNT] = "CHN_hivesmarschall_trimmel"
        w.daily()
        self.assertFalse(w.valid("trimmel"))
        self.assertFalse(w.valid("crisis"))
        self.replace_count(w)
        self.assertTrue(w.valid("trimmel"))
        self.assertTrue(w.valid("crisis"))
        self.assertFalse(w.valid("can_mandate"))
        self.development(w)  # Domestic work stays playable during the crisis.

    def test_all_legal_settlements_restore_legitimacy_and_reject_stale_hearing(self):
        for choice, count_present in itertools.product(("dismiss_impostor", "ratify_trimmel", "dismiss_without_compensation"), (True, False)):
            with self.subTest(choice=choice, count_present=count_present):
                w = self.replace_count(self.congress(), count_present)
                w.scene("letters", 30, "investigate_open")
                w.scene("audience", 31, "record_identity")
                if choice == "dismiss_without_compensation":
                    w.countries["AET"].political_power = 0
                w.scene("hearing", 32, choice)
                expected = TRIMMEL if choice == "ratify_trimmel" else COUNT if count_present else "HSM_AET_civic_council"
                self.assertEqual(w.countries["AET"].leader, expected)
                self.assertFalse(w.valid("legitimate"))  # Hearing is not the final signature.
                before = w.snapshot()
                for other in ("dismiss_impostor", "ratify_trimmel", "dismiss_without_compensation"):
                    w.click(32, other, stale=True)
                self.assertEqual(w.snapshot(), before)
                if choice == "dismiss_without_compensation":
                    self.assertEqual(w.countries["AET"].political_power, 0)
                    w.countries["AET"].political_power = 35  # External income before signing.
                w.scene("signature", 33, "settle_identity")
                self.assertTrue(w.valid("legitimate"))
                before = w.snapshot()
                w.click(33, "settle_identity", stale=True)
                w.daily()
                self.assertEqual(w.snapshot(), before)
                self.assertFalse(w.valid("crisis"))

    def test_crisis_blocks_prepared_handover_until_signature(self):
        w = self.replace_count(self.prepared())
        w.date = BIRTHDAY + datetime.timedelta(days=1)
        w.daily()
        self.assertFalse(w.countries["GRI"].exists)
        w.scene("letters", 30, "investigate_quiet")
        w.scene("audience", 31, "record_identity")
        w.scene("hearing", 32, "ratify_trimmel")
        w.daily()
        self.assertFalse(w.countries["GRI"].exists)
        w.scene("signature", 33, "settle_identity")
        w.daily()
        self.assertTrue(w.countries["GRI"].exists)


class Rewards(Fixture):
    def test_opening_recovers_invalid_delivery_after_government_returns_and_timer_expires(self):
        w = self.world("AET")
        w.complete("opening")
        w.countries["AET"].leader = "AET_prelate_ludwig_ebonwing"
        w.advance_days(1)
        self.assertFalse(w.deliver("HSM_AET.1", "AET"))
        before = w.snapshot()
        w.click(1, "accept_relief", stale=True)
        self.assertEqual(w.snapshot(), before)
        w.countries["AET"].leader = COUNT
        w.advance_days(20)
        w.daily()
        self.assertFalse([p for p in w.scheduled if p[2] == "HSM_AET.1"])
        w.advance_days(25)
        w.daily()
        w.daily()
        self.assertEqual(len([p for p in w.scheduled if p[2] == "HSM_AET.1"]), 1)
        pp = w.countries["AET"].political_power
        w.answer(1, "accept_relief")
        self.assertEqual(w.countries["AET"].political_power, pp + 25)
        before = w.snapshot()
        w.click(1, "accept_relief", stale=True)
        w.aet("retry_opening")
        w.daily()
        self.assertEqual(w.snapshot(), before)
        w.advance_days(50)
        w.daily()
        self.assertEqual(w.countries["AET"].political_power, pp + 25)
        self.assertFalse([p for p in w.scheduled if p[2] == "HSM_AET.1"])

    def test_every_education_finance_and_army_choice_is_exclusive_and_idempotent(self):
        stages = (("household", 11, ("school_open", "school_court")),
                  ("court_accounts", 12, ("accounts_public", "accounts_patron")),
                  ("service", 13, ("service_law", "service_contract")),
                  ("working_table", 14, ("judge_patron", "protect_patron")))
        for choices in itertools.product((0, 1), repeat=4):
            with self.subTest(choices=choices):
                w = self.mandated()
                for (focus, number, effects), index in zip(stages, choices):
                    w.scene(focus, number, effects[index])
                    before = w.snapshot()
                    for effect in effects:
                        w.click(number, effect, stale=True)
                    w.aet("finish_" + focus)
                    self.assertEqual(w.snapshot(), before, (choices, focus))

    def test_home_budget_charges_exactly_once_and_insufficient_funds_do_nothing(self):
        for effect, cost in (("home_public", 50), ("home_credit", 25)):
            with self.subTest(effect=effect):
                w = self.world("AET")
                w.scene("opening", 1, "accept_relief")
                w.scene("refuge", 2, "receive_refugees")
                w.complete("home_budget")
                w.advance_days(1)
                self.assertTrue(w.deliver("HSM_AET.3", "AET"))
                w.countries["AET"].political_power = cost - 1
                before = w.snapshot()
                w.click(3, effect, stale=True)
                self.assertEqual(w.snapshot(), before)
                w.countries["AET"].political_power = cost
                w.click(3, effect)
                self.assertEqual(w.countries["AET"].political_power, 0)
                before = w.snapshot()
                w.click(3, effect, stale=True)
                self.assertEqual(w.snapshot(), before)

    def test_development_rewards_and_native_social_improvements_cannot_repeat(self):
        w = self.congress()
        self.development(w)
        self.assertIn("poverty1", w.countries["AET"].ideas)
        self.assertIn("lack_of_scientists3", w.countries["AET"].ideas)
        self.assertEqual(sum(s.buildings.get("industrial_complex", 0) for s in w.states), 1)
        self.assertEqual(w.countries["AET"].army_experience, 50)
        before = w.snapshot()
        for suffix in ("workshops", "roads", "scholars", "demobilisation"):
            w.aet("finish_" + suffix)
        w.aet("refresh")
        w.aet("refresh")
        self.assertEqual(w.snapshot(), before)
        self.assertEqual({d for d in w.countries["AET"].dynamic_modifiers if d.startswith(P)}, {P + "compact"})

    def test_building_reward_avoids_occupied_homeland_and_uses_once_only_full_capacity_fallback(self):
        for blocked in ("occupied", "full"):
            with self.subTest(blocked=blocked):
                w = self.congress()
                baseline = copy.deepcopy(w.countries["AET"].bonuses)
                for sid in HOME:
                    if blocked == "occupied":
                        w.state_ids[sid].controller = "CYA"
                    else:
                        w.state_ids[sid].capacity = 0
                w.complete("workshops")
                self.assertEqual(sum(s.buildings.get("industrial_complex", 0) for s in w.states), 0)
                self.assertEqual(w.countries["AET"].bonuses[:-1], baseline)
                self.assertEqual(len(w.countries["AET"].bonuses), len(baseline) + 1)
                self.assertEqual(G["one"](w.countries["AET"].bonuses[-1], "name").value, P + "workshops")
                before = w.snapshot()
                w.aet("finish_workshops")
                self.assertEqual(w.snapshot(), before)

    def test_daily_reconciliation_does_not_duplicate_a_pending_disagreement(self):
        w = self.mandated()
        w.scene("household", 11, "school_open")
        w.scene("court_accounts", 12, "accounts_public")
        w.scene("service", 13, "service_law")
        w.scene("working_table", 14, "judge_patron")
        self.assertEqual(len([p for p in w.scheduled if p[2] == "HSM_AET.15"]), 1)
        for _ in range(3):
            w.daily()
        self.assertEqual(len([p for p in w.scheduled if p[2] == "HSM_AET.15"]), 1)

    def test_open_regency_options_are_inert_after_custody_or_regime_loss(self):
        for obstruction in ("custody", "regime", "death"):
            with self.subTest(obstruction=obstruction):
                w = self.mandated()
                w.complete("household")
                w.advance_days(1)
                self.assertTrue(w.deliver("HSM_AET.11", "AET"))
                if obstruction == "custody":
                    w.holder("CYA")
                elif obstruction == "regime":
                    w.countries["AET"].leader = "AET_prelate_ludwig_ebonwing"
                else:
                    w.global_flags.add(DEAD)
                before = w.snapshot()
                for effect in ("school_open", "school_court"):
                    w.click(11, effect, stale=True)
                self.assertEqual(w.snapshot(), before)


class ReviewerRegressions(Fixture):
    def paid_scenes(self):
        """Reach each budget through real choices; prices are the public contract."""
        w = self.world("AET")
        w.scene("opening", 1, "accept_relief")
        w.scene("refuge", 2, "receive_refugees")
        w.complete("home_budget")
        yield w, 3, (("home_public", 50), ("home_credit", 25))

        w = self.mandated()
        w.scene("household", 11, "school_open")
        w.complete("court_accounts")
        yield w, 12, (("accounts_public", 50), ("accounts_patron", 25))
        w.answer(12, "accounts_public")
        w.scene("service", 13, "service_law")
        w.complete("working_table")
        yield w, 14, (("judge_patron", 75),)
        protected = copy.deepcopy(w)
        protected.answer(14, "protect_patron")
        yield protected, 15, (("revise_contracts", 100),)
        w.answer(14, "judge_patron")
        yield w, 15, (("revise_contracts", 50),)
        w.answer(15, "revise_contracts")
        self.development(w)
        w.complete("prepare")
        yield w, 16, (("sign_handover", 50),)

        w = self.congress(None)
        w.global_flags.add(DEAD)
        w.scene("obituary", 20, "acknowledge_death")
        w.scene("interim", 21, "accept_interim")
        for focus, number, choices in (
                ("delegates", 22, ("delegates_equal", "delegates_population")),
                ("union", 23, ("sign_union",)),
                ("revenues", 24, ("revenues_local", "revenues_central")),
                ("succession", 25, ("succession_assembly", "succession_council"))):
            w.complete(focus)
            yield w, number, tuple((c, 35) for c in choices)
            w.answer(number, choices[0])

        w = self.replace_count(self.congress())
        w.complete("letters")
        yield w, 30, (("investigate_open", 25), ("investigate_quiet", 10))
        w.answer(30, "investigate_open")
        w.scene("audience", 31, "record_identity")
        w.complete("hearing")
        yield w, 32, (("dismiss_impostor", 50), ("ratify_trimmel", 75))
        w.answer(32, "dismiss_impostor")
        w.complete("signature")
        yield w, 33, (("settle_identity", 35),)

    def test_every_paid_choice_rejects_fractional_shortfall_and_charges_exactly(self):
        covered = set()
        for base, number, choices in self.paid_scenes():
            for effect, cost in choices:
                covered.add(P + effect)
                for balance in (cost - .5, cost, cost + .5):
                    with self.subTest(event=number, effect=effect, balance=balance):
                        w = copy.deepcopy(base)
                        w.countries["AET"].political_power = balance
                        option = w.option(number, effect)
                        available = (w.check(option.get("trigger", []))
                                     and w.check(option.get("available", [])))
                        self.assertEqual(available, balance >= cost)
                        if balance < cost:
                            before = w.snapshot()
                            w.click(number, effect, stale=True)
                            self.assertEqual(w.snapshot(), before, "Stale UI must not overspend")
                            w.aet(effect)
                            self.assertEqual(w.snapshot(), before, "Direct effect must not overspend")
                        else:
                            w.click(number, effect)
                            self.assertEqual(w.countries["AET"].political_power, balance - cost)
                            before = w.snapshot()
                            w.click(number, effect, stale=True)
                            w.aet(effect)
                            self.assertEqual(w.snapshot(), before)
        paid = {key for key, body in self.template.effects.items() if key.startswith(P)
                and any(n.key == "add_political_power" and float(n.value) < 0 for n in walk(body))}
        self.assertEqual(covered, paid, "Every production payment needs a reachable boundary scenario")

    def deliver_paid_packet(self, w, number):
        event_id = f"HSM_AET.{number}"
        packets = [p for p in w.scheduled if p[1:3] == ("AET", event_id)]
        self.assertEqual(len(packets), 1, event_id)
        w.advance_days(max(0, packets[0][0] - w.day))
        self.assertTrue(w.deliver(event_id, "AET"), event_id)

    def postpone_option(self, w, number):
        options = [o for o in w.events[f"HSM_AET.{number}"].all("option")
                   if o.get("name") == P + "postpone"]
        self.assertEqual(len(options), 1, number)
        return options[0]

    def test_every_paid_packet_allows_free_deferral_even_when_a_choice_is_affordable(self):
        covered = set()
        for base, number, choices in self.paid_scenes():
            covered.add(number)
            w = copy.deepcopy(base)
            self.deliver_paid_packet(w, number)
            option = self.postpone_option(w, number)
            balances = {0, 1000, *(cost + offset for effect, cost in choices for offset in (-.5, 0, .5))}
            for balance in sorted(balances):
                with self.subTest(event=number, choices=choices, balance=balance):
                    w.countries["AET"].political_power = balance
                    self.assertTrue(w.check(option.get("trigger", [])))
                    self.assertTrue(w.check(option.get("available", [])))
                    chance = option.get("ai_chance", [])
                    weight = float(G["one"](chance, "factor").value)
                    for modifier in (n for n in chance if n.key == "modifier"):
                        if w.check([n for n in modifier.children if n.key != "factor"]):
                            weight *= float(modifier.get("factor"))
                    self.assertEqual(weight, 0 if balance >= max(cost for effect, cost in choices) else 100,
                                     "AI deferral weight must depend on the expensive choice, not the cheap one")
                    before = w.snapshot()
                    for _ in range(2):
                        w.run([n for n in option.children if n.key not in METADATA])
                    self.assertEqual(w.snapshot(), before, "Deferral must not pay, reward or commit a choice")
        self.assertEqual(covered, {3, 12, 14, 15, 16, 22, 23, 24, 25, 30, 32, 33})

    def test_deferred_packets_retry_once_and_preserve_the_expensive_choice(self):
        for base, number, choices in self.paid_scenes():
            effect, cost = max(choices, key=lambda choice: choice[1])
            with self.subTest(event=number, effect=effect, cost=cost):
                w = copy.deepcopy(base)
                w.countries["AET"].political_power = cost - .5
                self.deliver_paid_packet(w, number)
                option = self.postpone_option(w, number)
                self.assertTrue(w.check(option.get("trigger", [])))
                self.assertTrue(w.check(option.get("available", [])))
                before = w.snapshot()
                w.run([n for n in option.children if n.key not in METADATA])
                self.assertEqual(w.snapshot(), before)
                event_id = f"HSM_AET.{number}"
                for _ in range(3):
                    w.daily()
                self.assertFalse([p for p in w.scheduled if p[1:3] == ("AET", event_id)])
                w.advance_days(61)  # Both the 45-day invitations and 60-day disagreement guard expire.
                for _ in range(3):
                    w.daily()
                self.assertEqual(len([p for p in w.scheduled if p[1:3] == ("AET", event_id)]), 1)
                self.assertEqual(w.countries["AET"].political_power, cost - .5)
                w.countries["AET"].political_power = cost  # External income; no invented route reward.
                w.answer(number, effect)
                self.assertEqual(w.countries["AET"].political_power, 0)
                before = w.snapshot()
                w.click(number, effect, stale=True)
                w.aet(effect)
                self.assertEqual(w.snapshot(), before)
                self.assertFalse(w.check(option.get("trigger", [])), "A settled packet must not offer deferral")
                w.advance_days(61)
                for _ in range(3):
                    w.daily()
                self.assertFalse([p for p in w.scheduled if p[1:3] == ("AET", event_id)])
                self.assertEqual(w.countries["AET"].political_power, 0)

    def test_revision_native_preview_matches_both_prior_judgements(self):
        covered = set()
        for base, number, choices in self.paid_scenes():
            if number != 15:
                continue
            effect, cost = choices[0]
            covered.add(cost)
            with self.subTest(cost=cost):
                w = copy.deepcopy(base)
                w.countries["AET"].political_power = cost
                option = w.option(number, effect)
                before = w.snapshot()
                preview = copy.deepcopy(w)
                preview.run(native_preview(option.children))
                self.assertEqual(preview.countries["AET"].political_power, 0,
                                 "Native preview must show the currently applicable 50/100 PP debit")
                self.assertEqual(w.snapshot(), before)
                w.click(number, effect)
                self.assertEqual(w.countries["AET"].political_power, 0)
                self.assertNotIn(P + "protect_patron", w.countries["AET"].flags)
                self.assertIn(P + "judge_patron", w.countries["AET"].flags)
        self.assertEqual(covered, {50, 100})

    def test_stale_relief_closure_cannot_erase_union_restoration_or_wartime_relief(self):
        for outcome in ("union", "completed_union", "restored", "war"):
            with self.subTest(outcome=outcome):
                w = self.congress()
                w.take_decision("end_mission")
                w.advance_days(1)
                self.assertTrue(w.deliver("HSM_AET_system.7", "AET"))
                close = next(o for o in w.events["HSM_AET_system.7"].all("option")
                             if any(n.key == P + "close_relief" for n in walk(o.children)))
                if outcome == "war":
                    w.countries["AET"].war = True
                elif outcome == "restored":
                    w.scene("mandate", 10, "accept_mandate")
                    self.prepared(w)
                    w.date = BIRTHDAY + datetime.timedelta(days=1)
                    w.daily()
                    self.assertTrue(w.countries["GRI"].exists)
                else:
                    w.global_flags.add(DEAD)
                    w.holder(None)
                    for focus, event, effect in (("obituary", 20, "acknowledge_death"),
                                                 ("interim", 21, "accept_interim"),
                                                 ("delegates", 22, "delegates_equal"),
                                                 ("union", 23, "sign_union")):
                        w.scene(focus, event, effect)
                    if outcome == "completed_union":
                        w.scene("revenues", 24, "revenues_local")
                        w.scene("succession", 25, "succession_assembly")
                        self.development(w)
                        w.scene("winter", 26, "conclude_union")
                before = w.snapshot()
                w.run([n for n in close.children if n.key not in METADATA])
                self.assertEqual(w.snapshot(), before, "Already-open closure changed a later settlement")
                w.aet("close_relief")
                self.assertEqual(w.snapshot(), before, "Closure effect failed to revalidate")
                self.assertNotIn(P + "closed", w.countries["AET"].flags)

    def test_mandate_review_allows_reconsideration_without_any_decline_reward(self):
        w = self.congress()
        stability = w.countries["AET"].stability
        pp = w.countries["AET"].political_power
        w.scene("mandate", 10, "decline_mandate")
        self.assertAlmostEqual(w.countries["AET"].stability, stability)
        self.assertEqual(w.countries["AET"].political_power, pp)
        for _ in range(3):
            w.take_decision("household_review")
            self.assertTrue(w.valid("can_mandate"))
            w.answer(10, "decline_mandate")
            self.assertAlmostEqual(w.countries["AET"].stability, stability)
            self.assertEqual(w.countries["AET"].political_power, pp)
            before = w.snapshot()
            w.click(10, "decline_mandate", stale=True)
            self.assertEqual(w.snapshot(), before)
            w.advance_days(31)
        w.take_decision("household_review")
        w.answer(10, "accept_mandate")
        self.assertTrue(w.valid("regency"))
        self.assertAlmostEqual(w.countries["AET"].stability, stability)
        self.assertEqual(w.countries["AET"].political_power, pp)

    def test_gift_retries_after_invalid_delivery_and_late_validity_without_duplicate_rewards(self):
        for school, gift in itertools.product(("school_open", "school_court"), ("gift_private", "gift_public")):
            with self.subTest(school=school, gift=gift):
                w = self.mandated()
                w.scene("household", 11, school)
                w.state_ids["382"].controller = "CYA"
                w.advance_days(30)
                self.assertFalse(w.deliver("HSM_AET.27", "AET"))
                before = w.snapshot()
                for choice in ("gift_private", "gift_public"):
                    w.click(27, choice, stale=True)
                self.assertEqual(w.snapshot(), before)
                w.advance_days(31)
                w.daily()
                self.assertFalse([p for p in w.scheduled if p[2] == "HSM_AET.27"])
                w.state_ids["382"].controller = "AET"
                w.daily()
                w.daily()
                self.assertEqual(len([p for p in w.scheduled if p[2] == "HSM_AET.27"]), 1)
                pp, stability = w.countries["AET"].political_power, w.countries["AET"].stability
                w.answer(27, gift)
                self.assertEqual(w.countries["AET"].political_power, pp + (25 if gift == "gift_public" else 0))
                self.assertAlmostEqual(w.countries["AET"].stability, stability + (.03 if gift == "gift_private" else 0))
                before = w.snapshot()
                for choice in ("gift_private", "gift_public"):
                    w.click(27, choice, stale=True)
                w.daily()
                self.assertEqual(w.snapshot(), before)
                w.advance_days(61)
                w.daily()
                self.assertFalse([p for p in w.scheduled if p[2] == "HSM_AET.27"])

    def test_congress_stale_ratification_waits_for_actual_legitimate_settlement(self):
        w = self.world("AET")
        w.scene("opening", 1, "accept_relief")
        w.scene("refuge", 2, "receive_refugees")
        w.scene("home_budget", 3, "home_public")
        w.complete("congress")
        w.advance_days(1)
        self.assertTrue(w.deliver("HSM_AET.4", "AET"))
        self.replace_count(w)
        self.assertFalse(w.valid("can_congress"))
        before = w.snapshot()
        w.click(4, "sign_congress", stale=True)
        w.aet("sign_congress")
        self.assertEqual(w.snapshot(), before)
        w.scene("letters", 30, "investigate_open")
        w.scene("audience", 31, "record_identity")
        w.scene("hearing", 32, "ratify_trimmel")
        self.assertFalse(w.valid("can_congress"))
        w.scene("signature", 33, "settle_identity")
        self.assertTrue(w.valid("can_congress"))
        w.advance_days(46)
        w.daily()
        w.answer(4, "sign_congress")
        self.assertIn(P + "congress_done", w.countries["AET"].flags)

    def test_count_or_council_restoration_selects_a_real_ruling_party_role(self):
        for government, present, choice in itertools.product(
                ("neutrality", "democratic", "fascism"), (True, False),
                ("dismiss_impostor", "dismiss_without_compensation")):
            with self.subTest(government=government, count=present, choice=choice):
                w = self.replace_count(self.congress(), present)
                c = w.countries["AET"]
                c.government = government
                c.party_leaders[government] = TRIMMEL
                w.scene("letters", 30, "investigate_open")
                w.scene("audience", 31, "record_identity")
                if choice == "dismiss_without_compensation":
                    c.political_power = 49.5
                w.scene("hearing", 32, choice)
                party = "democratic" if present and government == "democratic" else "neutrality"
                self.assertEqual(c.government, party)
                self.assertEqual(c.leader, COUNT if present else P + "civic_council")
                self.assertEqual(c.party_leaders[party], c.leader)


    def test_safe_first_options_do_not_accept_external_consent_or_close_relief(self):
        w = self.congress()
        w.take_decision("end_mission")
        w.advance_days(1)
        self.assertTrue(w.deliver("HSM_AET_system.7", "AET"))
        first = w.events["HSM_AET_system.7"].all("option")[0]
        self.assertEqual(first.get("name"), "HSM_AET_system.7.b")
        before = w.snapshot()
        w.run([n for n in first.children if n.key not in METADATA])
        self.assertEqual(w.snapshot(), before)

        w = self.prepared()
        w.countries["AET"].faction = w.countries["JER"].faction = "foreign_alliance"
        w.countries["JER"].faction_leader = True
        w.date = BIRTHDAY + datetime.timedelta(days=1)
        w.daily()
        w.advance_days(1)
        self.assertTrue(w.deliver("HSM_AET_system.3", "JER"))
        first = w.events["HSM_AET_system.3"].all("option")[0]
        self.assertEqual(first.get("name"), "HSM_AET_system.3.b")
        w.run([n for n in first.children if n.key not in METADATA], "JER")
        self.assertFalse(w.countries["GRI"].faction)
        self.assertNotIn(P + "alliance_request", w.countries["JER"].flags)


class NarrativeSelectors(Fixture):
    def description_keys(self, w, event_id, tag="AET", *, context_lost=False):
        w.root = tag
        keys = []
        for desc in w.events[event_id].all("desc"):
            if not desc.children:
                keys.append(desc.value)
            elif w.check(desc.get("trigger", []), tag):
                keys.append(desc.get("text"))
        self.assertEqual(len(keys), 1, (event_id, keys))
        if context_lost:
            self.assertEqual(keys[0], P + "context_lost_desc", event_id)
        else:
            self.assertNotEqual(keys[0], P + "context_lost_desc", event_id)
        return keys[0]

    def invalidate_restored_government(self, w, reason):
        c = w.countries["GRI"]
        if reason == "replacement":
            c.leader = c.party_leaders["neutrality"] = "fixture_successor"
            self.assertIn(GROVER, c.characters, "Presence alone must not count as ruling")
        elif reason == "subject":
            c.subject, c.overlord = True, "CYA"
        elif reason == "capitulation":
            c.capitulated = True
        elif reason == "absent":
            c.exists = False
        elif reason == "unrestored":
            c.flags.remove(P + "restored")
        else:
            self.fail(f"Unknown restoration interruption: {reason}")

    def test_restored_focus_availability_rechecks_actual_government_for_all_six_focuses(self):
        restored = self.prepared()
        restored.date = BIRTHDAY + datetime.timedelta(days=1)
        restored.daily()
        for reason in (None, "replacement", "subject", "capitulation", "absent", "unrestored"):
            w = copy.deepcopy(restored)
            if reason:
                self.invalidate_restored_government(w, reason)
            self.assertEqual(w.valid("restored_government", "GRI"), reason is None)
            for suffix in ("oath", "towns", "army", "schools", "debts", "settlement"):
                with self.subTest(interruption=reason, focus=suffix):
                    focus = w.focuses[P + "GRI_" + suffix]
                    self.assertEqual(w.check(focus.get("available", []), "GRI"), reason is None)

    def test_restored_notifications_reject_invalid_delivery_and_close_already_open_packets(self):
        restored = self.prepared()
        restored.date = BIRTHDAY + datetime.timedelta(days=1)
        restored.daily()
        for suffix in ("oath", "army", "debts"):
            restored.complete("GRI_" + suffix, "GRI")
        restored.advance_days(2)  # The real restoration/oath/debts packets are all due.
        policy_flags = {P + name for name in ("school_open", "service_law", "trimmel_ratified",
                                              "judge_patron", "protect_patron")}
        variants = {4: (set(), {"school_open"}),
                    8: (set(), {"service_law"}, {"trimmel_ratified"}, {"service_law", "trimmel_ratified"}),
                    9: (set(), {"judge_patron"}, {"protect_patron"}, {"judge_patron", "protect_patron"})}
        for number, branches in variants.items():
            event_id = f"HSM_AET_system.{number}"
            for branch, reason, already_open in itertools.product(
                    branches, ("replacement", "subject", "capitulation"), (False, True)):
                with self.subTest(event=number, branch=sorted(branch), interruption=reason, already_open=already_open):
                    w = copy.deepcopy(restored)
                    # All description branches must close. Positive branch reachability is
                    # separately tested through the actual inherited-policy campaigns.
                    w.countries["GRI"].flags.difference_update(policy_flags)
                    w.countries["GRI"].flags.update(P + name for name in branch)
                    event = w.events[event_id]
                    self.assertTrue(w.check(event.get("trigger", []), "GRI"))
                    self.description_keys(w, event_id, "GRI")
                    visible = [o.get("name") for o in event.all("option")
                               if w.check(o.get("trigger", []), "GRI")]
                    self.assertEqual(visible, [event_id + ".a"])
                    if already_open:
                        self.assertTrue(w.deliver(event_id, "GRI"))
                    self.invalidate_restored_government(w, reason)
                    self.assertFalse(w.check(event.get("trigger", []), "GRI"))
                    if not already_open:
                        expected = copy.deepcopy(w)
                        expected.scheduled.remove(next(p for p in expected.scheduled if p[1:3] == ("GRI", event_id)))
                        self.assertFalse(w.deliver(event_id, "GRI"))
                        self.assertEqual(w.snapshot(), expected.snapshot(), "Rejected delivery must only discard its packet")
                    self.description_keys(w, event_id, "GRI", context_lost=True)
                    available = [o for o in event.all("option") if w.check(o.get("trigger", []), "GRI")
                                 and w.check(o.get("available", []), "GRI")]
                    self.assertEqual([o.get("name") for o in available], [P + "context_lost"])
                    before = w.snapshot()
                    for option in event.all("option"):
                        w.run([n for n in option.children if n.key not in METADATA], "GRI")
                    self.assertEqual(w.snapshot(), before, "Stale acknowledgements and context loss must be inert")

    def test_refugee_packet_uses_death_text_only_for_confirmed_death(self):
        for holder, dead in (("AET", False), ("CYA", False), (None, False),
                             (None, True), ("AET", True)):
            with self.subTest(holder=holder, dead=dead):
                w = self.world(holder)
                if dead:
                    w.global_flags.add(DEAD)
                w.scene("opening", 1, "accept_relief")
                w.complete("refuge")
                w.advance_days(1)
                self.assertTrue(w.deliver("HSM_AET.2", "AET"))
                key = self.description_keys(w, "HSM_AET.2")
                self.assertEqual(key == "HSM_AET.2.dead.d", dead)

    def test_interim_distinguishes_direct_union_from_an_actual_former_guardian(self):
        for former_guardian in (False, True):
            with self.subTest(former_guardian=former_guardian):
                w = self.mandated() if former_guardian else self.congress(None)
                w.global_flags.add(DEAD)
                w.holder(None)
                w.daily()
                w.scene("obituary", 20, "acknowledge_death")
                w.complete("interim")
                w.advance_days(1)
                self.assertTrue(w.deliver("HSM_AET.21", "AET"))
                key = self.description_keys(w, "HSM_AET.21")
                self.assertEqual(key == "HSM_AET.21.direct.d", not former_guardian)

    def test_restored_callbacks_select_one_variant_from_the_policies_actually_transferred(self):
        oath_keys = {(True, True): "HSM_AET_system.8.law_trimmel.d",
                     (True, False): "HSM_AET_system.8.law.d",
                     (False, True): "HSM_AET_system.8.contract_trimmel.d",
                     (False, False): "HSM_AET_system.8.d"}
        for open_school, lawful_service, ratified in itertools.product((False, True), repeat=3):
            with self.subTest(open_school=open_school, lawful_service=lawful_service, ratified=ratified):
                # Vary schooling independently of service and ruler: the callbacks must not
                # accidentally select the right prose using the wrong inherited flag.
                w = self.mandated()
                w.scene("household", 11, "school_open" if open_school else "school_court")
                w.answer(27, "gift_public")
                w.scene("court_accounts", 12, "accounts_public")
                w.scene("service", 13, "service_law" if lawful_service else "service_contract")
                judgement = "judge_patron" if open_school else "protect_patron"
                w.scene("working_table", 14, judgement)
                w.answer(15, "uphold_contracts")
                self.development(w)
                w.scene("prepare", 16, "sign_handover")
                if ratified:
                    self.replace_count(w)
                    w.scene("letters", 30, "investigate_open")
                    w.scene("audience", 31, "record_identity")
                    w.scene("hearing", 32, "ratify_trimmel")
                    w.scene("signature", 33, "settle_identity")
                w.date = BIRTHDAY + datetime.timedelta(days=1)
                w.daily()
                w.advance_days(2)
                self.assertTrue(w.deliver("HSM_AET_system.4", "GRI"))
                self.assertEqual(self.description_keys(w, "HSM_AET_system.4", "GRI"),
                                 "HSM_AET_system.4.open.d" if open_school else "HSM_AET_system.4.d")
                w.complete("GRI_oath", "GRI")
                w.advance_days(1)
                self.assertTrue(w.deliver("HSM_AET_system.8", "GRI"))
                self.assertEqual(self.description_keys(w, "HSM_AET_system.8", "GRI"),
                                 oath_keys[lawful_service, ratified])
                w.complete("GRI_army", "GRI")
                w.complete("GRI_debts", "GRI")
                w.advance_days(1)
                self.assertTrue(w.deliver("HSM_AET_system.9", "GRI"))
                self.assertEqual(self.description_keys(w, "HSM_AET_system.9", "GRI"),
                                 "HSM_AET_system.9.judged.d" if open_school else "HSM_AET_system.9.protected.d")
        # Legacy saves can lack inherited judgement metadata, or contain both old flags.
        for flags, key in ((set(), "HSM_AET_system.9.d"),
                           ({P + "judge_patron", P + "protect_patron"}, "HSM_AET_system.9.protected.d")):
            legacy = copy.deepcopy(w)
            legacy.countries["GRI"].flags.difference_update({P + "judge_patron", P + "protect_patron"})
            legacy.countries["GRI"].flags.update(flags)
            self.assertEqual(self.description_keys(legacy, "HSM_AET_system.9", "GRI"), key)


class Integration(Fixture):
    def test_required_public_interfaces_present(self):
        self.assertTrue({f"HSM_AET.{n}" for n in EVENTS} <= set(self.template.events),
                        "Missing required narrative events")
        self.assertTrue({P + "finish_" + n for n in MAIN + CRISIS} <= set(self.template.effects))
        for folder in ("events", "common/national_focus", "common/scripted_effects", "common/scripted_triggers",
                       "common/on_actions", "common/dynamic_modifiers", "common/characters"):
            self.assertTrue(sources(folder), folder)

    def test_real_script_references_and_engine_keywords(self):
        w = self.world()
        paths = sorted(MOD.rglob("HSM_AET*.txt"))
        definitions = set(w.triggers) | set(w.effects)
        native_focuses = {n.get("id") for n in walk(read(OPT.eaw / "common/national_focus/AET.txt"))
                          if n.key in ("focus", "shared_focus") and n.children}
        trees = {n.get("id") for p in (MOD / "common/national_focus").glob("*.txt") for n in read(p) if n.key == "focus_tree"}
        for path in paths:
            for n in walk(read(path)):
                with self.subTest(path=str(path.relative_to(MOD)), key=n.key):
                    self.assertNotEqual(n.key, "political_power", "Use documented has_political_power predicate")
                    self.assertNotEqual(n.key, "default_option", "Safe fallback must be the first option")
                    self.assertNotIn(n.op, ("<=", ">=", "!="))
                    if n.key.startswith(P) and n.value in ("yes", "no"):
                        self.assertIn(n.key, definitions)
                    if n.key == "country_event" and n.children and n.get("id", "").startswith("HSM_AET.") and not n.get("is_triggered_only"):
                        self.assertIn(n.get("id"), w.events)
                    if n.key in ("focus", "shared_focus") and not n.children:
                        self.assertIn(n.value, set(w.focuses) | native_focuses)
                    if n.key == "load_focus_tree":
                        self.assertIn(n.get("tree"), trees)
                    if n.key in ("recruit_character", "generate_character"):
                        self.assertNotEqual(n.value, GROVER)
                        self.assertNotEqual(n.get("token_base"), GROVER)
                    self.assertNotEqual(n.key, "create_wargoal", "This continuation has no continental war goals")

    def test_focus_graph_imports_are_complete_acyclic_and_preserve_native_inventory(self):
        w = self.world()
        roots = set()
        graph = {}
        for suffix in MAIN + CRISIS:
            fid = P + suffix
            f = w.focuses[fid]
            self.assertNotEqual(f.get("repeatable"), "yes")
            deps = {n.value for group in f.all("prerequisite") for n in group.children}
            graph[fid] = deps
            if not deps:
                roots.add(fid)
            for dep in deps:
                self.assertIn(dep, w.focuses)
            self.assertTrue(any(n.key == P + "finish_" + suffix for n in walk(f.get("completion_reward", []))))
        visiting, seen = set(), set()
        def visit(fid):
            self.assertNotIn(fid, visiting, f"Focus cycle at {fid}")
            if fid in seen:
                return
            visiting.add(fid)
            for dep in graph.get(fid, ()):
                visit(dep)
            visiting.remove(fid)
            seen.add(fid)
        for fid in graph:
            visit(fid)
        native = read(OPT.eaw / "common/national_focus/AET.txt")
        override = read(MOD / "common/national_focus/AET.txt")
        original = {n.get("id"): n for n in native if n.key == "shared_focus" and n.children}
        actual = {n.get("id"): n for n in override if n.key == "shared_focus" and n.children}
        self.assertTrue(set(original) <= set(actual))
        native_right = max(int(f.get("x", "0")) for f in original.values())
        positions = [(int(w.focuses[P + suffix].get("x")), int(w.focuses[P + suffix].get("y")))
                     for suffix in MAIN + CRISIS]
        self.assertGreater(min(x for x, y in positions), native_right,
                           "New columns overlap the actual native AET footprint")
        self.assertEqual(len(positions), len(set(positions)), "New focus coordinates collide")
        for fid, f in original.items():
            for key in ("icon", "x", "y", "prerequisite", "mutually_exclusive"):
                self.assertEqual(f.all(key), actual[fid].all(key), f"Native graph/layout changed: {fid}/{key}")
        for tree in (n for n in override if n.key == "focus_tree"):
            self.assertTrue(roots <= {n.value for n in tree.all("shared_focus")}, tree.get("id"))
        for suffix in ("prepare", "winter"):
            def ancestors(fid):
                return set(graph.get(fid, ())) | {a for d in graph.get(fid, ()) for a in ancestors(d)}
            self.assertTrue({P + x for x in ("workshops", "roads", "scholars", "demobilisation")} <= ancestors(P + suffix))
        for suffix in ("mandate", "obituary"):
            self.assertFalse(w.focuses[P + suffix].all("mutually_exclusive"))

    def test_localisation_bom_parity_duplicates_and_references(self):
        languages = {}
        for lang in ("english", "russian"):
            paths = sorted((MOD / "localisation" / lang).glob("HSM_AET*_l_*.yml"))
            self.assertTrue(paths, f"Missing {lang} localisation")
            values = {}
            for path in paths:
                self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"), str(path))
                lines = path.read_text(encoding="utf-8-sig").splitlines()
                self.assertEqual(lines[0].strip(), "l_" + lang + ":", str(path))
                for line in lines[1:]:
                    if not line.strip() or line.lstrip().startswith("#"):
                        continue
                    match = re.fullmatch(r'\s*([A-Za-z0-9_.]+):\d+\s+"((?:\\.|[^"\\])*)"\s*', line)
                    self.assertIsNotNone(match, f"Malformed {path.name}: {line}")
                    key, value = match.groups()
                    self.assertNotIn(key, values, f"Duplicate {lang}: {key}")
                    self.assertTrue(value.strip(), key)
                    values[key] = value
            languages[lang] = values
        self.assertEqual(set(languages["english"]), set(languages["russian"]))
        needed = {P + "context_lost"}
        for path in MOD.rglob("HSM_AET*.txt"):
            for n in walk(read(path)):
                if n.key in ("focus", "shared_focus") and n.children:
                    needed.update((n.get("id"), n.get("id") + "_desc"))
                if n.key in ("name", "title", "desc", "text", "tooltip", "custom_effect_tooltip", "create_faction"):
                    if isinstance(n.value, str) and n.value.startswith((P, "HSM_AET.")):
                        needed.add(n.value)
        self.assertFalse(needed - set(languages["english"]), sorted(needed - set(languages["english"])))

    def test_every_story_option_revalidates_context_and_has_free_fallback(self):
        for number in EVENTS:
            event = self.template.events[f"HSM_AET.{number}"]
            self.assertTrue(event.get("trigger"), f"Missing trigger: {number}")
            options = event.all("option")
            fallback = [o for o in options if o.get("name") == P + "context_lost"]
            self.assertEqual(len(fallback), 1, number)
            self.assertFalse(any(n.key == "add_political_power" for n in walk(fallback[0].children)))
            for option in options:
                self.assertTrue(option.get("trigger"), f"Unconditional option {number}/{option.get('name')}")

    def test_definitions_and_flags_are_unique_and_have_real_writers(self):
        for folder, kind in (("events", "country_event"), ("common/national_focus", "shared_focus")):
            found = {}
            for path in sources(folder):
                for node in walk(read(path)):
                    if node.key != kind or not node.children:
                        continue
                    key = node.get("id")
                    # A nested country_event is a call, not a definition.
                    if kind == "country_event" and not node.get("is_triggered_only") and not node.get("title"):
                        continue
                    self.assertNotIn(key, found, f"Duplicate {kind}: {key}")
                    found[key] = path
        nodes = [n for p in MOD.rglob("HSM_AET*.txt") for n in walk(read(p))]
        writes = {n.get("flag") if n.children else n.value for n in nodes if n.key == "set_country_flag"}
        reads = {n.value for n in nodes if n.key == "has_country_flag" and isinstance(n.value, str) and n.value.startswith(P)}
        self.assertFalse(reads - writes, f"Flags without production writers: {sorted(reads - writes)}")


class NativeGuards(Fixture):
    def test_pragmatic_aet_cannot_use_native_empire_or_aquileia_formables(self):
        w = self.congress()
        categories = read(MOD / "common/decisions/griffon_decisions.txt")
        menus = read(MOD / "common/decisions/categories/eaw_formable_categories.txt")
        for name in ("form_griffon_empire", "form_aquileia"):
            category = G["one"](categories, name + "_category")
            menu = G["one"](menus, name + "_category")
            decision = G["one"](category.children, name)
            self.assertFalse(w.check(menu.get("visible"), "AET"), name)
            for gate in ("visible", "available"):
                self.assertFalse(w.check(decision.get(gate), "AET"), (name, gate))

    def test_native_childhood_execution_and_adoption_recheck_actual_aet_household(self):
        events = {n.get("id"): n for n in read(MOD / "events/Grover_Events.txt") if n.key == "country_event"}
        for number in (*range(1, 15), 17, 32, 35, 40, 41):
            with self.subTest(event=number):
                w = self.mandated()
                w.root, w.sender = "CYA", "GRI"
                event = events[f"grover.{number}"]
                self.assertFalse(w.check(event.get("trigger", []), "CYA"))
                before = w.snapshot()
                w.run(event.get("immediate", []), "CYA")
                for option in event.all("option"):
                    w.run([n for n in option.children if n.key not in METADATA], "CYA")
                self.assertEqual(w.snapshot(), before)

    def test_restored_gri_rejects_native_coronation_and_tree_replacement(self):
        w = self.prepared()
        w.date = BIRTHDAY + datetime.timedelta(days=1)
        w.daily()
        events = {n.get("id"): n for n in read(MOD / "events/GriffonianEmpire Events.txt") if n.key == "country_event"}
        w.root, w.sender = "GRI", "AET"
        for number in (3, 44, 75, 123, 137):
            with self.subTest(event=number):
                event = events[f"imperial.{number}"]
                self.assertFalse(w.check(event.get("trigger", []), "GRI"))
                before = w.snapshot()
                w.run(event.get("immediate", []), "GRI")
                for option in event.all("option"):
                    w.run([n for n in option.children if n.key not in METADATA], "GRI")
                self.assertEqual(w.snapshot(), before)


if __name__ == "__main__":
    unittest.main(argv=[__file__, *BASE["REST"]], verbosity=2)
