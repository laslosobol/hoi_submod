"""Aquileian regional source scenarios, not an HOI4 emulator.

python -B -X utf8 tools/Test-AquileianRegions.py --eaw EaW Harness
python -B -X utf8 tools/Test-AquileianRegions.py --eaw EaW Inventory

Only in-memory fixture state changes. Harness tests need no generated AQR files;
production checks fail explicitly when those files are missing. Unknown executed
operations fail closed. Native event ordering, focus duration/cancellation, AI,
combat, UI and real save/reload remain engine playtest work.
"""
from __future__ import annotations

import copy
import datetime
import operator
import re
import runpy
import subprocess
import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path

BASE = runpy.run_path(str(Path(__file__).with_name("Test-Verenia.py")))
Node, parse, read, walk, ROOT, MOD, OPT = (
    BASE[k] for k in ("Node", "parse", "read", "walk", "ROOT", "MOD", "OPT"))
P = "HSM_AQR_"
REGIONS = ("JEB", "JRR", "JFT", "VIN")
ROUTE_COUNTS = {"JEB": 4, "JRR": 3, "JFT": 4, "VIN": 4}
COMPARE = {"=": operator.eq, "!=": operator.ne, ">": operator.gt, "<": operator.lt}
# Installed documentation/triggers_documentation.html#check_variable. Inclusive
# comparisons are named fields, not compact >=/<= Clausewitz operators.
VARIABLE_COMPARE = {"equals": operator.eq, "not_equals": operator.ne,
                    "greater_than": operator.gt, "greater_than_or_equals": operator.ge,
                    "less_than": operator.lt, "less_than_or_equals": operator.le}
OPTION_METADATA = {"name", "trigger", "available", "ai_chance", "highlight",
                   "original_tag", "default_option"}


def invalid_comparison_tokens(source):
    # The existing lexer keeps quoted strings/comments intact; neither is code.
    return [(source.count("\n", 0, match.start()) + 1, match.group())
            for match in BASE["TOKEN"].finditer(source) if match.group() in (">=", "<=")]


def parse(source):
    invalid = invalid_comparison_tokens(source)
    assert not invalid, f"Unsupported engine comparison token(s): {invalid}; use explicit check_variable compare"
    return BASE["parse"](source)


def read(path):
    return parse(path.read_text(encoding="utf-8-sig"))


def stale_effects_after_tag_change(nodes, scripted=None):
    """Conservative source check, not emulation of HOI4's invalidated scope.

    Follow effect lists/conditionals and AQR scripted calls. After a possible
    player switch, further effects require an explicit literal country scope.
    Trigger/parameter blocks are data, not effect siblings.
    """
    scripted = scripted or {}
    faults = []
    wrappers = {'if', 'else_if', 'else', 'hidden_effect'}
    metadata = OPTION_METADATA | {'limit', 'tooltip', 'custom_effect_tooltip', 'effect_tooltip'}

    def sequence(body, stale=False, path=(), calls=()):
        for n in body:
            here = (*path, n.key)
            if n.key in metadata:
                continue
            if re.fullmatch(r'[A-Z][A-Z0-9]{2}', n.key) and n.children:
                switched = sequence(n.children, False, here, calls)
                stale = stale or switched
            elif n.key in wrappers:
                stale = sequence(n.children, stale, here, calls) or stale
            elif n.key in scripted and n.value == 'yes':
                assert n.key not in calls, f'Recursive effect needs explicit scope analysis: {n.key}'
                stale = sequence(scripted[n.key], stale, here, (*calls, n.key)) or stale
            else:
                if stale:
                    faults.append('/'.join(here))
                if n.key == 'change_tag_from':
                    stale = True
        return stale

    sequence(nodes)
    return faults


@dataclass(frozen=True)
class Route:
    key: str
    camp: str
    preparation: str
    character: str
    party: str

    @property
    def tag(self):
        return self.key[:3]


# Independent expected identities/parties. Do not derive an expected outcome
# from the same production CONFIG or effect that the scenario executes.
ROUTES = (
    Route("JEB_royal", "royal", "JER_JEB_monarchist", "JEB_duke_michel_discret", "neutrality"),
    Route("JEB_constitutional", "rev", "JER_JEB_revolutionary", "JEB_duke_michel_discret", "democratic"),
    Route("JEB_moderate", "rev", "JER_JEB_revolutionary", P + "JEB_moderate", "democratic"),
    Route("JEB_cocardiers", "rev", "JER_JEB_revolutionary", P + "JEB_cocardiers", "neutrality"),
    Route("JRR_absolutist", "royal", "JRR_absolutist", P + "jeanne_discret", "neutrality"),
    Route("JRR_coalition", "royal", "JRR_reformism", P + "jeanne_discret", "democratic"),
    Route("JRR_colette", "rev", "JER_JRR_revolutionary", "JRR_colonel_colette_solide", "fascism"),
    Route("JFT_dennis", "royal", "JER_JFT_monarchist", "JFT_baron_dennis_discret", "neutrality"),
    Route("JFT_communes", "rev", "JER_JFT_commie_supp", P + "JFT_communes", "communism"),
    Route("JFT_enfants", "rev", "JER_JFT_fash_supp", P + "JFT_enfants", "fascism"),
    Route("JFT_fja", "rev", "JER_JFT_dem_supp", P + "JFT_fja", "democratic"),
    Route("VIN_gadiffer", "royal", "JER_VIN_monarchist", "VIN_duke_gadiffer_discret", "neutrality"),
    Route("VIN_abc", "rev", "JER_VIN_movements1", P + "VIN_abc", "communism"),
    Route("VIN_chevaliers", "rev", "JER_VIN_movements2", P + "VIN_chevaliers", "neutrality"),
    Route("VIN_sis", "rev", "JER_VIN_movements3", P + "VIN_sis", "democratic"),
)

NATIVE_OUTCOMES = {"royal": "REVOLUTION_is_a_monarchist", "rev": "REVOLUTION_is_a_revolutionary"}
GLOBAL_OUTCOMES = {"royal": "JER_revolution_ended", "rev": "JER_revolution_ended_2"}

# Native committee/movement counters, independently named from their EaW sources.
NATIVE_MOVEMENTS = {
    "JEB_constitutional": "JEB_michel",
    "JEB_moderate": "JEB_moderate_revolutionary_clubs",
    "JEB_cocardiers": "JEB_extremist_revolutionary_clubs",
    "JFT_communes": "JFT_second_commune_influence",
    "JFT_enfants": "JFT_les_enfants_terribles",
    "JFT_fja": "JFT_FJA_socdems",
    "VIN_abc": "VIN_abc_influence",
    "VIN_chevaliers": "VIN_chevaliers_influence",
    "VIN_sis": "VIN_students_influence",
}


def sources(folder):
    return sorted((MOD / folder).glob("HSM_AQR*.txt"))


def put_unique(index, key, value, origin):
    if not key or key in index:
        raise AssertionError(f"Missing/duplicate definition {key!r}: {origin}")
    index[key] = value


def references(focus, field_name):
    return {n.value for group in focus.all(field_name) for n in group.all("focus")}


class Production:
    """Index actual AQR scripts without importing a writing builder."""

    def __init__(self):
        self.triggers, self.effects, self.events = {}, {}, {}
        self.ideas = {}
        self.focuses, self.shared, self.trees, self.hooks, self.decisions = {}, {}, {}, {}, {}
        self.decision_categories, self.decision_category_for = {}, {}
        # Scripted-GUI properties bind variables/widgets, not country operations.
        # The GUI owner's suite validates those files and their render bindings.
        self.paths = sorted(path for path in MOD.rglob("HSM_AQR*.txt")
                            if path.relative_to(MOD).parts[:2] != ("common", "scripted_guis"))
        if not self.paths:
            raise AssertionError("AQR production is not generated yet; run Harness alone until integration is ready")
        self.nodes = {p: read(p) for p in self.paths}
        for folder, target in (("common/scripted_triggers", self.triggers),
                               ("common/scripted_effects", self.effects)):
            for path in sources(folder):
                for node in self.nodes[path]:
                    put_unique(target, node.key, node.children, path)
        for path in sources("events"):
            for node in self.nodes[path]:
                if node.key == "country_event":
                    put_unique(self.events, node.get("id"), node, path)
        for path in sources("common/ideas"):
            for container in self.nodes[path]:
                for category in container.all("country"):
                    for idea in category.children:
                        put_unique(self.ideas, idea.key, idea, path)
        for path in sources("common/national_focus"):
            for node in self.nodes[path]:
                if node.key == "focus_tree":
                    put_unique(self.trees, node.get("id"), node, path)
                for focus in walk([node]):
                    if focus.key in ("focus", "shared_focus") and focus.children:
                        put_unique(self.focuses, focus.get("id"), focus, path)
                        if focus.key == "shared_focus":
                            self.shared[focus.get("id")] = focus
        for path in sources("common/on_actions"):
            for container in self.nodes[path]:
                if container.key == "on_actions":
                    for hook in container.children:
                        self.hooks.setdefault(hook.key, []).extend(hook.get("effect", []))
        for path in sources("common/decisions"):
            for category in self.nodes[path]:
                for decision in category.children:
                    if decision.children:
                        put_unique(self.decisions, decision.key, decision, path)
                        self.decision_category_for[decision.key] = category.key
        for path in sources("common/decisions/categories"):
            for category in self.nodes[path]:
                put_unique(self.decision_categories, category.key, category, path)
        self.routes = sorted(fid[len(P):-len("_pledge")] for fid in self.focuses
                             if re.fullmatch(P + r"(?:JEB|JRR|JFT|VIN)_.+_pledge", fid))
        self.native_trees, self.native_focuses, self.native_shared = {}, {}, {}
        for path in (MOD / "common/national_focus/JER.txt", OPT.eaw / "common/national_focus/generic_griffon.txt",
                     OPT.eaw / "common/national_focus/RIV_shared.txt"):
            for node in read(path):
                if node.key == "focus_tree":
                    put_unique(self.native_trees, node.get("id"), node, path)
                for focus in walk([node]):
                    if focus.key in ("focus", "shared_focus") and focus.children:
                        put_unique(self.native_focuses, focus.get("id"), focus, path)
                        if focus.key == "shared_focus":
                            self.native_shared[focus.get("id")] = focus

    def tree_members(self, tree_id):
        tree = (self.trees | self.native_trees)[tree_id]
        shared = self.shared | self.native_shared
        members = {f.get("id") for f in tree.all("focus")}
        imports = {f.value for f in tree.all("shared_focus") if not f.children}
        missing = imports - shared.keys()
        if missing:
            raise AssertionError(f"Unresolved shared roots in {tree_id}: {sorted(missing)}")
        members.update(imports)
        # Native shared roots include their prerequisite-linked descendants.
        changed = True
        while changed:
            additions = {fid for fid, f in shared.items()
                         if references(f, "prerequisite") & members} - members
            changed = bool(additions)
            members.update(additions)
        return members


@dataclass
class Country(BASE["Country"]):
    original_tag: str = ""
    overlord: str = ""
    government: str = "neutrality"
    stability: float = .5
    war_support: float = .5
    capital: str = ""
    focus_tree: str = ""
    characters: set = field(default_factory=set)
    party_leaders: dict = field(default_factory=dict)
    party_names: dict = field(default_factory=dict)
    popularities: dict = field(default_factory=dict)
    roles: dict = field(default_factory=dict)
    elections: bool = True
    naps: set = field(default_factory=set)
    truces: set = field(default_factory=set)
    guarantors: set = field(default_factory=set)
    technology: set = field(default_factory=set)
    research_slots: int = 3
    air_experience: float = 0
    navy_experience: float = 0
    bonuses: list = field(default_factory=list)
    idea_days: dict = field(default_factory=dict)
    templates: dict = field(default_factory=dict)
    units: list = field(default_factory=list)
    stockpile: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.original_tag:
            self.original_tag = self.tag


@dataclass
class State:
    sid: str
    owner: str
    controller: str
    cores: set = field(default_factory=set)
    claims: set = field(default_factory=set)
    fully_controlled: bool = True
    capacity: int = 20
    buildings: dict = field(default_factory=dict)
    coastal: bool = False


@dataclass(frozen=True)
class CharacterScope:
    owner: str
    character: str


class AquileianWorld(BASE["World"]):
    """Generic primitives only; political transitions must come from scripts."""

    def __deepcopy__(self, memo):
        result = object.__new__(type(self))
        memo[id(self)] = result
        readonly = {"triggers", "effects", "events", "focuses", "hooks", "decisions",
                    "tree_members", "character_definitions", "ideology_groups", "idea_definitions",
                    "decision_categories", "decision_category_for"}
        for key, value in vars(self).items():
            setattr(result, key, value if key in readonly else copy.deepcopy(value, memo))
        return result

    def __init__(self, production=None):
        # Deliberately do not initialize VER countries, flags or on-actions.
        self.countries = {t: Country(t) for t in (*REGIONS, "JER", "JHZ", "GRI", "FLO")}
        self.countries["JHZ"].exists = False
        self.root = self.sender = "JEB"
        self.previous = self.current_scope = None
        self.triggers = dict(production.triggers) if production else {}
        self.effects = dict(production.effects) if production else {}
        self.events = dict(production.events) if production else {}
        self.focuses = (production.native_focuses | production.focuses) if production else {}
        self.shared_focus_ids = set(production.shared) | set(production.native_shared) if production else set()
        self.hooks = dict(production.hooks) if production else {}
        self.decisions = dict(production.decisions) if production else {}
        self.decision_categories = dict(production.decision_categories) if production else {}
        self.decision_category_for = dict(production.decision_category_for) if production else {}
        self.idea_definitions = dict(production.ideas) if production else {}
        self.tree_members = ({key: production.tree_members(key) for key in production.trees | production.native_trees}
                             if production else {})
        # Explicit opt-in boundaries for native focus rewards; never silently stub unknown operations.
        self.native_completion_boundaries, self.native_boundary_calls = set(), []
        self.states, self.global_flags, self.global_targets = {}, set(), {}
        self.arrays, self.global_variables = {}, {}
        self.scheduled, self.trace, self.transfers, self.annexations = [], [], [], []
        self.releases, self.hook_calls, self.tree_loads = [], [], []
        # Spawn requests only: no province placement, equipment or combat simulation.
        self.unit_spawns = []
        self.unit_deletions = []
        self.temp_variables = {}
        self.player_countries, self.player_changes = {}, []
        self.day = 0.0
        self.date = datetime.date(1007, 1, 1)
        self.character_definitions, self.ideology_groups = {}, {}

    def load_native_countries(self):
        self.ideology_groups = {
            sub.key: group.key for top in read(OPT.eaw / "common/ideologies/00_ideologies.txt")
            for group in top.children for sub in group.get("types", [])}
        for tag in (*REGIONS, "JER"):
            c = self.countries[tag]
            history = read(next((OPT.eaw / "history/countries").glob(tag + "*.txt")))
            for node in history:
                if node.key == "capital":
                    c.capital = node.value
                elif node.key == "recruit_character":
                    c.characters.add(node.value)
                elif node.key == "set_politics":
                    c.government = node.get("ruling_party")
                elif node.key == "add_ideas":
                    c.ideas.update(n.key for n in node.children) if node.children else c.ideas.add(node.value)
            for container in read(OPT.eaw / f"common/characters/{tag}.txt"):
                if container.key == "characters":
                    self.character_definitions.update({n.key: n for n in container.children})
            for character in c.characters:
                roles = self.character_definitions[character].all("country_leader")
                c.roles[character] = copy.deepcopy(roles)
                for role in roles:
                    c.party_leaders[self.ideology_groups[role.get("ideology")]] = character
            c.leader = c.party_leaders.get(c.government, "fixture_incumbent")
        for path in sources("common/characters"):
            for container in read(path):
                if container.key == "characters":
                    self.character_definitions.update({n.key: n for n in container.children})
        history = read(next((OPT.eaw / "history/countries").glob("JER*.txt")))
        for node in history:
            if node.key == "set_autonomy" and node.get("target") in REGIONS:
                c = self.countries[node.get("target")]
                c.subject, c.overlord = True, "JER"
            elif node.key == "add_to_faction" and node.value in (*REGIONS, "JER"):
                self.countries[node.value].faction = "fixture_native_aquileia"

    def load_native_states(self):
        """History is fixture input; dated history blocks are not simulated."""
        for path in sorted((OPT.eaw / "history/states").glob("*.txt")):
            for node in read(path):
                if node.key != "state":
                    continue
                history = Node("history", "=", node.get("history", []))
                owner = history.get("owner")
                if owner and owner not in self.countries:
                    self.countries[owner] = Country(owner)
                self.states[node.get("id")] = State(
                    node.get("id"), owner, history.get("controller", owner),
                    cores={n.value for n in history.all("add_core_of")},
                    coastal=any(n.get('naval_base', '0') != '0' for n in history.get('buildings', []) if n.children),
                    buildings={n.key: int(n.value) for n in history.get("buildings", [])
                               if n.key in ("infrastructure", "industrial_complex", "arms_factory", "dockyard")})
        for tag in {core for s in self.states.values() for core in s.cores}:
            self.arrays[tag + ".original_cores"] = [s for s in self.states.values() if tag in s.cores]

    def load_native_helpers(self):
        wanted = {"decrease_poverty", "decrease_illiteracy", "increase_society_development"}
        for node in read(OPT.eaw / "common/scripted_effects/EAW_misc_effect.txt"):
            if node.key in wanted:
                self.effects[node.key] = node.children
        assert wanted <= self.effects.keys(), "Native socioeconomic helpers missing"
        for node in read(OPT.eaw / "common/scripted_effects/00_scripted_effects.txt"):
            if node.key in ("core_aquileian_heartland", "claim_all_de_jure_aquileia"):
                self.effects[node.key] = node.children

    def set_players(self, assignments):
        """Explicit fixture input; one player per country, no co-op simulation."""
        assert len(set(assignments.values())) == len(assignments)
        assert all(tag in self.countries and self.countries[tag].exists for tag in assignments.values())
        self.player_countries = dict(assignments)
        for tag, country in self.countries.items():
            country.ai = tag not in assignments.values()

    def resolve(self, value):
        if value == "PREV":
            return self.previous
        if value == "THIS":
            return self.current_scope
        if isinstance(value, str) and value.startswith("event_target:"):
            return self.global_targets[value.split(":", 1)[1]]
        return super().resolve(value)

    def scope(self, name, current):
        if name in ("owner", "controller"):
            assert isinstance(current, State)
            return getattr(current, name)
        if name == "overlord":
            return self.countries[current].overlord
        if name == "capital_scope":
            return self.states[self.countries[current].capital]
        if name in self.states:
            return self.states[name]
        return self.resolve(name)

    def scoped(self, operation, nodes, target, source):
        previous = self.previous
        self.previous = source
        try:
            return operation(nodes, target)
        finally:
            self.previous = previous

    def check(self, nodes, tag=None):
        tag = self.root if tag is None else tag
        taken = None
        for n in nodes:
            assert n.op not in (">=", "<="), f"Unsupported engine comparison token: {n.op}"
            v = n.value
            if n.key in ("if", "else_if", "else"):
                if n.key == "if":
                    taken = False
                assert taken is not None, "Conditional trigger without preceding if"
                ok = True
                if not taken and (n.key == "else" or self.check(n.get("limit", []), tag)):
                    taken = True
                    ok = self.check([x for x in n.children if x.key != "limit"], tag)
            elif n.key in ("AND", "OR", "NOT"):
                values = [self.check([x], tag) for x in n.children]
                ok = all(values) if n.key == "AND" else any(values) if n.key == "OR" else not any(values)
            elif n.key in ("hidden_trigger", "custom_trigger_tooltip"):
                ok = self.check([x for x in n.children if x.key != "tooltip"], tag)
            elif n.key in self.triggers:
                assert v in ("yes", "no"), "Parameterized triggers need explicit support"
                ok = self.check(self.triggers[n.key], tag) == (v == "yes")
            elif n.key in self.character_definitions:
                assert isinstance(tag, str), "Character scopes require an owning country"
                ok = (n.key in self.countries[tag].characters
                      and self.scoped(self.check, n.children, CharacterScope(tag, n.key), tag))
            elif (n.key in self.countries or n.key in self.states
                  or n.key in ("ROOT", "FROM", "PREV", "THIS", "owner", "controller", "overlord", "capital_scope")
                  or n.key.startswith("event_target:")):
                target = self.scope(n.key, tag)
                assert target, f"Empty scope: {n.key}"
                ok = self.scoped(self.check, n.children, target, tag)
            elif n.key in ("any_country", "any_possible_country", "any_subject_country"):
                eligible = [t for t, c in self.countries.items()
                            if (c.exists or n.key == "any_possible_country")
                            and (n.key != "any_subject_country" or c.subject and c.overlord == tag)]
                ok = any(self.scoped(self.check, n.children, t, tag) for t in eligible)
            elif n.key in ("any_owned_state", "all_owned_state", "all_controlled_state", "any_state"):
                eligible = [s for s in self.states.values() if n.key == "any_state"
                            or (s.controller == tag if n.key == "all_controlled_state" else s.owner == tag)]
                values = [self.scoped(self.check, n.children, s, tag) for s in eligible]
                ok = all(values) if n.key.startswith("all_") else any(values)
            elif n.key in ("all_of_scopes", "any_of_scopes"):
                values = [self.scoped(self.check, [x for x in n.children if x.key not in ("array", "tooltip")], s, tag)
                          for s in self.arrays[n.get("array")]]
                ok = all(values) if n.key == "all_of_scopes" else any(values)
            elif n.key == "always":
                ok = v == "yes"
            elif isinstance(tag, CharacterScope):
                assert n.key == 'has_ideology', f'Unsupported character predicate: {n.key}'
                roles = self.countries[tag.owner].roles.get(tag.character,
                            self.character_definitions[tag.character].all('country_leader'))
                ok = any(role.get('ideology') == v for role in roles)
            elif n.key == "is_in_array":
                assert isinstance(tag, State) and len(n.children) == 1
                term = n.children[0]
                assert term.key == "state_original_cores", "Only the native original-core state array is modelled"
                # The startup snapshot is independent of subsequently added/removed cores.
                ok = any(s.sid == tag.sid for s in self.arrays[self.resolve(term.value) + ".original_cores"])
            elif isinstance(tag, State):
                if n.key in ("is_owned_by", "is_controlled_by", "is_fully_controlled_by", "is_owned_and_controlled_by"):
                    target = self.resolve(v)
                    ok = (tag.owner == target if n.key == "is_owned_by" else
                          tag.controller == target if n.key == "is_controlled_by" else
                          tag.controller == target and tag.fully_controlled)
                    if n.key == "is_owned_and_controlled_by":
                        ok = ok and tag.owner == target
                elif n.key in ("is_core_of", "is_claimed_by"):
                    ok = self.resolve(v) in (tag.cores if n.key == "is_core_of" else tag.claims)
                elif n.key == "state":
                    ok = tag.sid == v
                elif n.key == "is_coastal":
                    ok = tag.coastal == (v == 'yes')
                elif n.key in ("infrastructure", "industrial_complex", "arms_factory", "dockyard"):
                    ok = COMPARE[n.op](tag.buildings.get(n.key, 0), float(v))
                else:
                    raise AssertionError(f"Unsupported state predicate: {n.key}")
            elif n.key == "original_tag":
                ok = self.countries[tag].original_tag == self.resolve(v)
            elif n.key == "is_subject_of":
                c = self.countries[tag]
                ok = c.subject and c.overlord == self.resolve(v)
            elif n.key == "country_exists":
                ok = self.countries[self.resolve(v)].exists
            elif n.key in ("has_government", "has_character"):
                c = self.countries[tag]
                ok = c.government == v if n.key == "has_government" else v in c.characters
            elif n.key == "has_template":
                ok = v in self.countries[tag].templates
            elif n.key == "has_political_power":
                ok = COMPARE[n.op](self.countries[tag].political_power, float(v))
            elif n.key == "amount_research_slots":
                ok = COMPARE[n.op](self.countries[tag].research_slots, float(v))
            elif n.key == "has_stability":
                ok = COMPARE[n.op](self.countries[tag].stability, float(v))
            elif n.key == "has_variable":
                ok = v in self.countries[tag].variables or v in self.temp_variables.get(tag, {})
            elif n.key == "has_dynamic_modifier":
                ok = (n.get("modifier") if n.children else v) in self.countries[tag].dynamic_modifiers
            elif n.key in ("has_non_aggression_pact_with", "has_truce_with"):
                collection = self.countries[tag].naps if n.key == "has_non_aggression_pact_with" else self.countries[tag].truces
                ok = self.resolve(v) in collection
            elif n.key == "is_guaranteed_by":
                ok = self.resolve(v) in self.countries[tag].guarantors
            elif n.key in ("owns_state", "controls_state", "has_full_control_of_state"):
                state = self.states[v]
                ok = state.owner == tag if n.key == "owns_state" else state.controller == tag
                if n.key == "has_full_control_of_state":
                    ok = ok and state.fully_controlled
            elif n.key == "date":
                ok = COMPARE[n.op](self.date, datetime.date(*map(int, v.split("."))))
            elif n.key == "check_variable":
                if n.all("var") or n.all("value") or n.all("compare"):
                    fields = {term.key for term in n.children}
                    assert {"var", "value", "compare"} <= fields <= {"var", "value", "compare", "tooltip"}, "Malformed explicit check_variable"
                    assert len(fields) == len(n.children) and all(term.op == "=" and not term.children for term in n.children), "Malformed explicit check_variable"
                    assert n.get("compare") in VARIABLE_COMPARE, "Unsupported check_variable compare"
                    ok = VARIABLE_COMPARE[n.get("compare")](self.number(n.get("var"), tag), self.number(n.get("value"), tag))
                else:
                    assert len(n.children) == 1 and n.children[0].op in ("=", ">", "<"), "Unsupported compact check_variable"
                    term = n.children[0]
                    ok = COMPARE[term.op](self.number(term.key, tag), self.number(term.value, tag))
            elif n.key == "has_country_flag" and n.children:
                raise AssertionError("Numeric flag comparisons need explicit support")
            else:
                ok = super().check([n], tag)
            if not ok:
                return False
        return True

    def number(self, value, tag):
        try:
            return float(value)
        except ValueError:
            # Native Aquileian variables include literal names such as JER.parliament_max.
            assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", value), f"Unsupported numeric expression: {value}"
            return self.temp_variables.get(tag, {}).get(value, self.countries[tag].variables.get(value, 0))

    def idea_modifiers(self, tag, idea_ids, target=None):
        """Sum selected active idea coefficients, not engine combat/economy totals."""
        assert set(idea_ids) <= self.idea_definitions.keys(), "Missing idea definition"
        result = {}
        for idea_id in self.countries[tag].ideas & set(idea_ids):
            idea = self.idea_definitions[idea_id]
            blocks = idea.all("modifier") if target is None else [
                block for block in idea.all("targeted_modifier") if block.get("tag") == target]
            for block in blocks:
                for term in block.children:
                    if term.key != "tag":
                        assert not term.children, "Conditional/nested idea modifiers need explicit support"
                        result[term.key] = result.get(term.key, 0) + float(term.value)
        return result

    def run(self, nodes, tag=None):
        tag = self.root if tag is None else tag
        prior_scope = self.current_scope
        self.current_scope = tag
        taken = None
        try:
            for n in nodes:
                assert n.op not in (">=", "<="), f"Unsupported engine comparison token: {n.op}"
                v = n.value
                if n.key in ("if", "else_if", "else"):
                    if n.key == "if":
                        taken = False
                    assert taken is not None, "Conditional without preceding if"
                    if not taken and (n.key == "else" or self.check(n.get("limit", []), tag)):
                        taken = True
                        self.run([x for x in n.children if x.key != "limit"], tag)
                elif n.key == "hidden_effect":
                    self.run(n.children, tag)
                elif n.key in ("effect_tooltip", "custom_effect_tooltip", "show_ideas_tooltip"):
                    pass
                elif n.key in self.effects:
                    assert v == "yes", "Parameterized effects need explicit support"
                    self.run(self.effects[n.key], tag)
                elif n.key in self.character_definitions:
                    assert isinstance(tag, str) and n.key in self.countries[tag].characters, f"Absent scoped character: {n.key}"
                    self.scoped(self.run, n.children, CharacterScope(tag, n.key), tag)
                elif (n.key in self.countries or n.key in self.states
                      or n.key in ("ROOT", "FROM", "PREV", "THIS", "owner", "controller", "overlord", "capital_scope")
                      or n.key.startswith("event_target:")):
                    self.scoped(self.run, n.children, self.scope(n.key, tag), tag)
                elif n.key in ("every_country", "every_possible_country", "every_subject_country"):
                    eligible = [t for t, c in self.countries.items()
                                if (c.exists or n.key == "every_possible_country")
                                and (n.key != "every_subject_country" or c.subject and c.overlord == tag)
                                and self.scoped(self.check, n.get("limit", []), t, tag)]
                    for target in eligible:
                        self.scoped(self.run, [x for x in n.children if x.key != "limit"], target, tag)
                elif n.key in ("every_state", "every_owned_state", "random_owned_state", "random_owned_controlled_state"):
                    eligible = [s for s in self.states.values()
                                if (n.key == "every_state" or s.owner == tag)
                                and (n.key != "random_owned_controlled_state" or s.controller == tag and s.fully_controlled)
                                and self.scoped(self.check, n.get("limit", []), s, tag)]
                    for state in (eligible[:1] if n.key.startswith("random_") else eligible):
                        self.scoped(self.run, [x for x in n.children if x.key != "limit"], state, tag)
                elif n.key == "for_each_scope_loop":
                    for state in self.arrays[n.get("array")]:
                        self.scoped(self.run, [x for x in n.children if x.key != "array"], state, tag)
                elif n.key in ("set_global_flag", "clr_global_flag"):
                    (self.global_flags.add if n.key == "set_global_flag" else self.global_flags.discard)(v)
                elif n.key == "save_global_event_target_as":
                    self.global_targets[v] = tag
                elif n.key == "complete_national_focus":
                    assert isinstance(v, str), "Block focus completion needs explicit support"
                    assert v in self.focuses, f"Unknown focus completion: {v}"
                    country = self.countries[tag]
                    if v not in country.focuses:
                        # Scripted completion bypasses selection gates; unlock is history-only.
                        country.focuses.add(v)
                        if v in self.native_completion_boundaries:
                            self.native_boundary_calls.append((tag, v, copy.deepcopy(self.focuses[v].get("completion_reward", []))))
                        else:
                            self.run(self.focuses[v].get("completion_reward", []), tag)
                elif n.key == "uncomplete_national_focus":
                    assert {x.key for x in n.children} <= {"focus", "uncomplete_children", "refund_political_power"}
                    assert n.get("refund_political_power", "no") == "no", "Focus refunds need explicit support"
                    focus_id = n.get("focus")
                    assert focus_id in self.focuses
                    country, removed = self.countries[tag], {focus_id}
                    country.focuses.discard(focus_id)
                    if n.get("uncomplete_children", "no") == "yes":
                        while True:
                            children = {fid for fid in country.focuses & self.focuses.keys()
                                        if references(self.focuses[fid], "prerequisite") & removed
                                        and not all(any(p.value in country.focuses for p in group.all("focus"))
                                                    for group in self.focuses[fid].all("prerequisite"))}
                            if not children:
                                break
                            country.focuses.difference_update(children)
                            removed.update(children)
                    for fid in removed:
                        self.run(self.focuses[fid].get("on_uncomplete", []), tag)
                elif n.key == "create_unit":
                    assert {x.key for x in n.children} <= {"division", "owner", "count", "id", "prioritize_location"}
                    assert n.get("division") and n.get("owner"), "Spawn needs a division and explicit owner"
                    owner = self.resolve(n.get("owner"))
                    assert owner in self.countries and self.countries[owner].exists
                    count = self.number(n.get("count", "1"), tag)
                    assert count > 0 and int(count) == count
                    self.unit_spawns.append((tag.sid if isinstance(tag, State) else tag,
                                             owner, int(count), copy.deepcopy(n.children)))
                    division = parse(n.get("division").replace('\\"', '"'))
                    template = next((x.value for x in division if x.key == "division_template"), None)
                    assert template in self.countries[owner].templates, f"Missing unit template: {template}"
                    self.countries[owner].units.extend((template, copy.deepcopy(division)) for _ in range(int(count)))
                elif n.key == "division_template":
                    assert {x.key for x in n.children} <= {"name", "is_locked", "priority", "regiments", "support"}
                    name = n.get("name")
                    assert name and name not in self.countries[tag].templates, "Template edits need explicit support"
                    self.countries[tag].templates[name] = copy.deepcopy(n.children)
                elif n.key == "delete_unit_template_and_units":
                    assert {x.key for x in n.children} <= {"division_template", "disband"}
                    assert n.get("disband", "no") in ("yes", "no")
                    name = n.get("division_template")
                    country = self.countries[tag]
                    self.unit_deletions.append((tag, name, n.get("disband", "no")))
                    country.templates.pop(name, None)
                    country.units[:] = [unit for unit in country.units if unit[0] != name]
                    # Demobilisation refunds and equipment consumption are not simulated.
                elif n.key == "add_equipment_to_stockpile":
                    assert {x.key for x in n.children} == {"type", "amount", "producer"}
                    key = (n.get("type"), self.resolve(n.get("producer")))
                    stockpile = self.countries[tag].stockpile
                    stockpile[key] = stockpile.get(key, 0) + self.number(n.get("amount"), tag)
                elif n.key == "add_timed_idea":
                    assert {x.key for x in n.children} == {"idea", "days"}, "Only day-based idea timers are modelled"
                    days = self.number(n.get("days"), tag)
                    assert days > 0 and int(days) == days
                    country = self.countries[tag]
                    country.ideas.add(n.get("idea"))
                    country.idea_days[n.get("idea")] = int(days)
                elif n.key == "remove_ideas":
                    assert isinstance(v, str), "Only single-idea removal is modelled"
                    self.countries[tag].ideas.discard(v)
                    self.countries[tag].idea_days.pop(v, None)
                elif n.key == "add_dynamic_modifier":
                    assert {x.key for x in n.children} == {"modifier"}, "Scoped/timed dynamics need explicit support"
                    self.countries[tag].dynamic_modifiers.add(n.get("modifier"))
                elif n.key == "set_variable" and any(x.key.startswith("global.") for x in n.children):
                    assert len(n.children) == 1
                    term = n.children[0]
                    self.global_variables[term.key] = self.resolve(term.value)
                elif n.key in ("set_variable", "add_to_variable", "subtract_from_variable", "clamp_variable",
                               "set_temp_variable", "add_to_temp_variable"):
                    values = (self.temp_variables.setdefault(tag, {}) if "temp_variable" in n.key
                              else self.countries[tag].variables)
                    if n.key == "clamp_variable":
                        assert {x.key for x in n.children} == {"var", "min", "max"}
                        name = n.get("var")
                        lower, upper = self.number(n.get("min"), tag), self.number(n.get("max"), tag)
                        assert lower <= upper
                        values[name] = min(upper, max(lower, values.get(name, 0)))
                    else:
                        if n.get("var"):
                            assert {x.key for x in n.children} == {"var", "value"}
                            name, value = n.get("var"), self.number(n.get("value"), tag)
                        else:
                            assert len(n.children) == 1 and not n.children[0].children
                            name, value = n.children[0].key, self.number(n.children[0].value, tag)
                        values[name] = (value if n.key.startswith("set_") else values.get(name, 0)
                                        + (value if n.key.startswith("add_") else -value))
                elif n.key in ("transfer_state", "transfer_state_to"):
                    state = tag if n.key == "transfer_state_to" else self.states[v]
                    target = self.resolve(v) if n.key == "transfer_state_to" else tag
                    assert isinstance(state, State) and target in self.countries
                    self.transfers.append((state.sid, state.owner, target))
                    state.owner = state.controller = target
                    state.fully_controlled = True
                    self.countries[target].exists = True
                elif n.key in ("add_core_of", "remove_core_of", "add_claim_by", "remove_claim_by"):
                    assert isinstance(tag, State)
                    collection = tag.cores if "core" in n.key else tag.claims
                    (collection.add if n.key.startswith("add_") else collection.discard)(self.resolve(v))
                elif n.key == "release_puppet":
                    assert isinstance(tag, str)
                    target = self.resolve(v)
                    country = self.countries[target]
                    assert not country.exists, "Release fixture currently supports an absent target only"
                    states = [s for s in self.states.values() if s.owner == tag and target in s.cores]
                    assert states, "Release fixture needs at least one owned target core"
                    for state in states:
                        self.run(parse(f"transfer_state_to = {target}"), state)
                    country.exists, country.subject, country.overlord = True, True, tag
                    self.releases.append((tag, target))
                    # Engine hook ordering is an external input; dispatch hooks explicitly.
                elif n.key == "annex_country":
                    assert set(x.key for x in n.children) == {"target", "transfer_troops"}
                    assert n.get("transfer_troops") in ("yes", "no")
                    target = self.resolve(n.get("target"))
                    assert target != tag and self.countries[target].exists
                    for state in self.states.values():
                        if state.owner == target:
                            self.transfers.append((state.sid, target, tag))
                            state.owner = tag
                            if state.controller == target:
                                state.controller = tag
                    country = self.countries[target]
                    country.exists = country.subject = False
                    country.overlord = ""
                    # Troop/stockpile disposition is recorded, not simulated.
                    self.annexations.append((tag, target, n.get("transfer_troops")))
                elif n.key == "change_tag_from":
                    assert isinstance(tag, str) and isinstance(v, str)
                    source = self.resolve(v)
                    assert source in self.countries and tag in self.countries and self.countries[tag].exists
                    if not self.countries[source].ai:
                        players = [p for p, country in self.player_countries.items() if country == source]
                        assert len(players) == 1, "Tag-switch scenarios need explicit player assignments"
                        assert self.countries[tag].ai, "Occupied-player destination is outside the fixture model"
                        self.player_countries[players[0]] = tag
                        self.countries[source].ai, self.countries[tag].ai = True, False
                        self.player_changes.append((players[0], source, tag))
                    # Country identity, territory, leadership and focus tree are unchanged.
                elif n.key == "set_autonomy":
                    assert {x.key for x in n.children} == {"target", "autonomy_state"}
                    target = self.countries[self.resolve(n.get("target"))]
                    assert n.get("autonomy_state") == "autonomy_free", "Only independence is modelled"
                    assert target.overlord == tag
                    target.subject, target.overlord = False, ""
                elif n.key == "end_puppet":
                    target = self.countries[self.resolve(v)]
                    assert target.subject and target.overlord == tag
                    target.subject, target.overlord = False, ""
                elif n.key == "puppet":
                    target = self.countries[self.resolve(v)]
                    assert target.exists, "This fixture requires territorial creation before puppeting"
                    target.subject, target.overlord = True, tag
                elif n.key == "inherit_technology":
                    self.countries[tag].technology.update(self.countries[self.resolve(v)].technology)
                elif n.key == "leave_faction":
                    assert v == "yes"
                    self.countries[tag].faction = ""
                    self.countries[tag].faction_leader = False
                elif n.key == 'remove_from_faction':
                    target = self.countries[self.resolve(v)]
                    assert self.countries[tag].faction_leader and self.countries[tag].faction
                    assert target.faction == self.countries[tag].faction
                    target.faction, target.faction_leader = '', False
                elif n.key == 'diplomatic_relation':
                    assert {x.key for x in n.children} == {'country', 'relation', 'active'}
                    assert n.get('active') == 'no', 'Only explicit cancellation is needed by these scenarios'
                    target_tag = self.resolve(n.get('country'))
                    target, country = self.countries[target_tag], self.countries[tag]
                    if n.get('relation') == 'non_aggression_pact':
                        country.naps.discard(target_tag)
                        target.naps.discard(tag)
                    elif n.get('relation') == 'guarantee':
                        target.guarantors.discard(tag)  # Scope guarantees target, not the reverse.
                    else:
                        raise AssertionError('Unsupported diplomatic relation: ' + n.get('relation'))
                elif n.key == 'set_truce':
                    assert {x.key for x in n.children} == {'target', 'days'}
                    assert n.get('days') == '0', 'Positive truce duration needs a separate expiry model'
                    target = self.resolve(n.get('target'))
                    self.countries[tag].truces.discard(target)
                    self.countries[target].truces.discard(tag)
                elif n.key == 'declare_war_on':
                    assert {x.key for x in n.children} == {'target', 'type'}
                    assert n.get('type') == 'annex_everything', 'Only the authored annexation war is modelled'
                    target = self.resolve(n.get('target'))
                    country, opponent = self.countries[tag], self.countries[target]
                    assert tag != target and country.exists and opponent.exists
                    assert not country.subject and not opponent.subject
                    assert not country.faction or country.faction != opponent.faction
                    assert target not in country.naps and target not in country.truces
                    # Bilateral declaration only: no combat, automatic allies or peace conference.
                    country.wars.add(target)
                    opponent.wars.add(tag)
                    country.war = opponent.war = True
                elif n.key == "country_event":
                    assert n.children and not n.get("random_days") and not n.get("random_hours")
                    delay = float(n.get("days", 0)) + float(n.get("hours", 0)) / 24
                    self.scheduled.append((self.day + delay, tag, n.get("id"), self.root))
                elif n.key in ("air_experience", "navy_experience"):
                    c = self.countries[tag]
                    setattr(c, n.key, getattr(c, n.key) + float(v))
                elif n.key in ("add_stability", "add_war_support", "add_research_slot"):
                    attribute = {"add_stability": "stability", "add_war_support": "war_support",
                                 "add_research_slot": "research_slots"}[n.key]
                    c = self.countries[tag]
                    setattr(c, attribute, getattr(c, attribute) + float(v))
                elif n.key == "add_tech_bonus":
                    self.countries[tag].bonuses.append(copy.deepcopy(n.children))
                elif n.key == "swap_ideas":
                    assert {x.key for x in n.children} == {"add_idea", "remove_idea"}
                    self.countries[tag].ideas.discard(n.get("remove_idea"))
                    self.countries[tag].idea_days.pop(n.get("remove_idea"), None)
                    self.countries[tag].ideas.add(n.get("add_idea"))
                elif n.key in ("set_cosmetic_tag", "drop_cosmetic_tag"):
                    self.countries[tag].cosmetic = v if n.key == "set_cosmetic_tag" else ""
                elif n.key == "set_capital":
                    assert {x.key for x in n.children} <= {"state", "remember_old_capital"}
                    assert self.states[n.get("state")].owner == tag
                    self.countries[tag].capital = n.get("state")
                elif n.key == "recruit_character":
                    assert v in self.character_definitions, f"Unknown recruit: {v}"
                    self.countries[tag].characters.add(v)
                elif n.key == "set_nationality":
                    assert isinstance(tag, CharacterScope) and isinstance(v, str)
                    destination = self.countries[self.resolve(v)]
                    origin = self.countries[tag.owner]
                    assert tag.character in origin.characters
                    origin.characters.remove(tag.character)
                    destination.characters.add(tag.character)
                    if tag.character in origin.roles:
                        destination.roles[tag.character] = origin.roles.pop(tag.character)
                    origin.party_leaders = {p: c for p, c in origin.party_leaders.items() if c != tag.character}
                    if origin.leader == tag.character:
                        origin.leader = "unmodelled_successor"
                elif n.key == "promote_character":
                    if n.children:
                        assert {x.key for x in n.children} == {"character", "ideology"}
                        character, ideology = n.get("character"), n.get("ideology")
                    else:
                        character, ideology = v, None
                    assert character in self.countries[tag].characters, f"Absent promotion: {character}"
                    country = self.countries[tag]
                    roles = country.roles.get(character, self.character_definitions[character].all("country_leader"))
                    if ideology:
                        roles = [role for role in roles if role.get("ideology") == ideology]
                    assert len(roles) == 1, "Multi-role promotion needs an explicit ideology"
                    party = self.ideology_groups[roles[0].get("ideology")]
                    country.party_leaders[party] = character
                    if country.government == party:
                        country.leader = character
                elif n.key == "retire_character":
                    assert isinstance(v, str)
                    country = self.countries[tag]
                    country.characters.discard(v)
                    country.roles.pop(v, None)
                    country.party_leaders = {p: c for p, c in country.party_leaders.items() if c != v}
                    if country.leader == v:
                        country.leader = "unmodelled_successor"
                elif n.key == "add_country_leader_role":
                    assert {x.key for x in n.children} <= {"character", "country_leader", "promote_leader"}
                    character = n.get("character")
                    country = self.countries[tag]
                    assert character in country.characters, f"Absent character: {character}"
                    role = Node("country_leader", "=", n.get("country_leader", []))
                    roles = country.roles.get(character, self.character_definitions[character].all('country_leader'))
                    assert not any(r.get('ideology') == role.get('ideology') for r in roles), f'Duplicate country leader role: {character}/{role.get("ideology")}'
                    country.roles.setdefault(character, copy.deepcopy(roles)).append(copy.deepcopy(role))
                    group = self.ideology_groups[role.get("ideology")]
                    if n.get("promote_leader") == "yes":
                        country.party_leaders[group] = character
                        if country.government == group:
                            country.leader = character
                elif n.key == "set_politics":
                    assert {x.key for x in n.children} <= {"ruling_party", "elections_allowed"}
                    country = self.countries[tag]
                    if n.get("ruling_party"):
                        country.government = n.get("ruling_party")
                        country.leader = country.party_leaders.get(country.government, "unmodelled_party_leader")
                    if n.get("elections_allowed"):
                        country.elections = n.get("elections_allowed") == "yes"
                elif n.key == "set_party_name":
                    assert {x.key for x in n.children} <= {"ideology", "name", "long_name"}
                    self.countries[tag].party_names[n.get("ideology")] = (n.get("name"), n.get("long_name"))
                elif n.key == "set_popularities":
                    assert {x.key for x in n.children} == {"neutrality", "democratic", "communism", "fascism"}
                    values = {x.key: float(x.value) for x in n.children}
                    assert all(0 <= v <= 100 for v in values.values()) and abs(sum(values.values()) - 100) < 1e-8
                    self.countries[tag].popularities = values
                elif n.key == "create_wargoal":
                    assert {x.key for x in n.children} <= {"type", "target", "generator"}
                    self.countries[tag].goals.add((n.get("type"), self.resolve(n.get("target"))))
                elif n.key == "load_focus_tree":
                    assert {x.key for x in n.children} <= {"tree", "keep_completed"}
                    target = n.get("tree")
                    assert target in self.tree_members
                    country = self.countries[tag]
                    if n.get("keep_completed") == "yes":
                        country.focuses.intersection_update(self.tree_members[target] | self.shared_focus_ids)
                    else:
                        assert not country.focuses, "Nonempty shared-only retention needs explicit support"
                    country.focus_tree = target
                    self.tree_loads.append((tag, target))
                elif n.key == "mark_focus_tree_layout_dirty":
                    assert v == "yes"
                elif isinstance(tag, State):
                    if n.key == "add_extra_state_shared_building_slots":
                        tag.capacity += int(v)
                    elif n.key == "add_building_construction":
                        assert n.get("instant_build") == "yes"
                        kind = n.get("type")
                        tag.buildings[kind] = tag.buildings.get(kind, 0) + int(n.get("level"))
                    else:
                        raise AssertionError(f"Unsupported state effect: {n.key}")
                else:
                    super().run([n], tag)
        finally:
            self.current_scope = prior_scope
            if prior_scope is None:
                self.temp_variables.clear()

    def effect(self, name, tag, sender=None):
        self.root, self.sender = tag, sender or tag
        self.run(self.effects[name], tag)

    def available(self, focus_id, tag):
        self.root = tag
        focus, country = self.focuses[focus_id], self.countries[tag]
        if country.focus_tree:
            assert country.focus_tree in self.tree_members
            if focus_id not in self.tree_members[country.focus_tree]:
                return False
        return (focus_id not in country.focuses
                and all(any(n.value in country.focuses for n in group.all("focus"))
                        for group in focus.all("prerequisite"))
                and not references(focus, "mutually_exclusive") & country.focuses
                and self.check(focus.get("allow_branch", []), tag)
                and self.check(focus.get("available", []), tag))

    def complete(self, focus_id, tag):
        assert self.available(focus_id, tag), f"Unavailable focus: {tag}/{focus_id}"
        focus = self.focuses[focus_id]
        assert not focus.get("bypass"), "Bypass needs explicit scenario support"
        self.countries[tag].focuses.add(focus_id)
        self.run(focus.get("completion_reward", []), tag)

    def advance_days(self, days):
        assert days >= 0 and int(days) == days
        super().advance_days(days)
        for country in self.countries.values():
            for idea in list(country.idea_days):
                country.idea_days[idea] -= days
                if country.idea_days[idea] <= 0:
                    country.ideas.discard(idea)
                    del country.idea_days[idea]
        self.day += days
        self.date += datetime.timedelta(days=days)

    def deliver(self, event_id, tag):
        packet = next((p for p in self.scheduled if p[1:3] == (tag, event_id) and p[0] <= self.day), None)
        assert packet is not None, f"No due {event_id} for {tag}"
        self.scheduled.remove(packet)
        self.root, self.sender = tag, packet[3]
        event = self.events[event_id]
        if not self.countries[tag].exists or not self.check(event.get("trigger", []), tag):
            return False
        self.run(event.get("immediate", []), tag)
        return True

    def click(self, event_id, option_name, tag, sender=None, stale=False):
        self.root, self.sender = tag, sender or self.sender
        matches = [o for o in self.events[event_id].all("option") if o.get("name") == option_name]
        assert len(matches) == 1, (event_id, option_name)
        option = matches[0]
        if not stale:
            assert self.check(option.get("trigger", []), tag), "Hidden option"
            assert self.check(option.get("available", []), tag), "Unavailable option"
        self.run([n for n in option.children if n.key not in OPTION_METADATA], tag)

    def hook(self, name, root, sender=None):
        self.root, self.sender = root, sender or root
        self.hook_calls.append((name, self.root, self.sender))
        self.run(self.hooks.get(name, []), root)

    def daily(self):
        assert "on_daily" in self.hooks, "Missing AQR production on_daily hook"
        self.hook("on_daily", self.root)

    @staticmethod
    def decision_cost(decision):
        cost = decision.get("cost", "0")
        assert isinstance(cost, str) and re.fullmatch(r"\d+(?:\.\d+)?", cost), "Only literal nonnegative PP costs are modelled"
        assert not any(decision.all(k) for k in ("custom_cost_trigger", "custom_cost_text", "days_remove", "days_mission_timeout")), "Custom costs and timed decisions need explicit support"
        return float(cost)

    def decision_available(self, decision_id, tag):
        self.root = self.sender = tag
        decision = self.decisions[decision_id]
        cost = self.decision_cost(decision)
        category_id = self.decision_category_for.get(decision_id)
        if category_id:
            category = self.decision_categories[category_id]
            if not all(self.check(category.get(k, []), tag) for k in ("allowed", "visible")):
                return False
        return (all(self.check(decision.get(k, []), tag) for k in ("allowed", "visible", "available"))
                and (cost == 0 or self.countries[tag].political_power >= cost))

    def decision(self, decision_id, tag):
        assert self.decision_available(decision_id, tag), f"Unavailable decision: {decision_id}"
        decision = self.decisions[decision_id]
        # Literal native cost is an engine boundary; the effect must not charge it again.
        self.countries[tag].political_power -= self.decision_cost(decision)
        # Native UI cooldown/fire_only_once are not simulated. Scripted flags must protect replay.
        self.run(decision.get("complete_effect", []), tag)

    def snapshot(self):
        # Exclude execution instrumentation and temporary evaluation scopes.
        return copy.deepcopy((self.countries, self.states, self.global_flags,
                              self.global_targets, self.global_variables, self.scheduled, self.day, self.date,
                              self.transfers, self.annexations, self.releases, self.tree_loads, self.unit_spawns,
                              self.unit_deletions, self.player_countries, self.player_changes, self.native_boundary_calls))


class EngineContract(unittest.TestCase):
    def test_tag_change_scope_checker_rejects_direct_nested_and_scripted_followup_effects(self):
        unsafe = (
            'JER = { change_tag_from = ROOT annex_country = { target = JEB transfer_troops = yes } }',
            'JER = { if = { limit = { ROOT = { is_ai = no } } change_tag_from = ROOT } annex_country = { target = JEB } }',
            'JER = { hidden_effect = { change_tag_from = ROOT } set_country_flag = after_switch }',
            'JER = { HSM_AQR_fixture_switch = yes annex_country = { target = JEB } }',
        )
        effects = {P + 'fixture_switch': parse('change_tag_from = ROOT')}
        for source in unsafe:
            with self.subTest(source=source):
                self.assertTrue(stale_effects_after_tag_change(parse(source), effects))
        safe = (
            'if = { limit = { is_ai = no } JER = { change_tag_from = ROOT } } JER = { annex_country = { target = JEB } }',
            'JER = { change_tag_from = ROOT } JER = { set_country_flag = after_switch annex_country = { target = JEB } }',
            'JER = { add_political_power = 1 change_tag_from = ROOT }',
        )
        for source in safe:
            with self.subTest(source=source):
                self.assertFalse(stale_effects_after_tag_change(parse(source), effects))

    def test_inclusive_operator_tokens_are_rejected_in_code_but_not_comments_or_strings(self):
        harmless = '# >= <= are invalid operators\ntext = "display >= 5; # <= 7"\nvalue = 1'
        self.assertFalse(invalid_comparison_tokens(harmless))
        parse(harmless)
        for source in ('check_variable = { score >= other }',
                       'if = { limit = { always = no } hidden_effect = { value <= 2 } }',
                       'tooltip = "quoted # >="\n# <= comment\nscore<=10'):
            with self.subTest(source=source):
                self.assertTrue(invalid_comparison_tokens(source))
                with self.assertRaisesRegex(AssertionError, 'Unsupported engine comparison'):
                    parse(source)
        w = AquileianWorld()
        for symbol in ('>=', '<='):
            with self.subTest(symbol=symbol):
                # Also reject manually supplied ASTs from the permissive base parser.
                with self.assertRaisesRegex(AssertionError, 'Unsupported compact check_variable'):
                    w.check(BASE['parse']('check_variable = { score ' + symbol + ' 5 }'), 'JEB')
                with self.assertRaisesRegex(AssertionError, 'Unsupported engine comparison'):
                    w.check([Node('has_political_power', symbol, '5')], 'JEB')

    def test_explicit_variable_comparisons_match_the_installed_engine_contract(self):
        documentation = (OPT.game / 'documentation/triggers_documentation.html').read_text(encoding='utf-8-sig')
        section = documentation.split('<h2 id="check_variable">', 1)[1].split('<h2 ', 1)[0]
        w = AquileianWorld()
        c = w.countries['JEB']
        c.variables['other'] = 5
        expected = {'equals': (False, True, False), 'not_equals': (True, False, True),
                    'less_than': (True, False, False), 'less_than_or_equals': (True, True, False),
                    'greater_than': (False, False, True), 'greater_than_or_equals': (False, True, True)}
        for comparison, results in expected.items():
            self.assertIn(comparison, section)
            for amount, result in zip((4.999, 5, 5.001), results):
                with self.subTest(compare=comparison, amount=amount):
                    c.variables['score'] = amount
                    for rhs in ('5', 'other'):
                        source = 'check_variable = { var = score value = ' + rhs + ' compare = ' + comparison + ' }'
                        self.assertEqual(w.check(parse(source), 'JEB'), result)
        for body in ('var = score value = 5 compare = at_least',
                     'var = score compare = equals', 'var = score var = other value = 5 compare = equals'):
            with self.subTest(malformed=body), self.assertRaises(AssertionError):
                w.check(parse('check_variable = { ' + body + ' }'), 'JEB')

    def test_aqr_runtime_and_native_overrides_contain_no_unsupported_operator_tokens(self):
        paths = set(MOD.rglob('HSM_AQR*.txt')) | set((MOD / 'interface').glob('HSM_AQR*.gui'))
        paths.update(MOD / relative for relative in (
            'common/national_focus/JER.txt', 'common/decisions/JER_decisions.txt',
            'common/decisions/categories/JER_decision_categories.txt', 'common/decisions/Formables.txt'))
        self.assertTrue(paths)
        failures = [(str(path.relative_to(MOD)), line, token) for path in sorted(paths) if path.exists()
                    for line, token in invalid_comparison_tokens(path.read_text(encoding='utf-8-sig'))]
        self.assertFalse(failures, f'Unsupported engine comparison tokens (file, line, token): {failures}')


class Harness(unittest.TestCase):
    def test_war_primitives_cancel_only_named_relations_and_never_transfer_territory(self):
        w = AquileianWorld()
        host, centre, foreign = (w.countries[t] for t in ('JEB', 'JER', 'FLO'))
        host.faction = centre.faction = foreign.faction = 'shared'
        host.faction_leader = True
        host.naps = {'JER', 'FLO'}
        centre.naps = {'JEB'}
        host.truces = {'JER', 'FLO'}
        centre.truces = {'JEB'}
        host.guarantors = {'JER', 'FLO'}
        centre.guarantors = {'JEB', 'FLO'}
        foreign_before = copy.deepcopy(foreign)
        w.states['1'] = State('1', 'JER', 'JER', {'JER'})
        before = copy.deepcopy(w.states)
        w.run(parse('''remove_from_faction = JER
diplomatic_relation = { country = JER relation = non_aggression_pact active = no }
set_truce = { target = JER days = 0 }
diplomatic_relation = { country = JER relation = guarantee active = no }
JER = { diplomatic_relation = { country = JEB relation = guarantee active = no } }
declare_war_on = { target = JER type = annex_everything }'''), 'JEB')
        self.assertEqual(host.naps, {'FLO'})
        self.assertEqual(host.truces, {'FLO'})
        self.assertFalse(centre.naps or centre.truces or centre.faction)
        self.assertEqual(host.guarantors, {'FLO'})
        self.assertEqual(centre.guarantors, {'FLO'})
        self.assertEqual(host.faction, 'shared')
        self.assertEqual(host.wars, {'JER'})
        self.assertEqual(centre.wars, {'JEB'})
        self.assertTrue(host.war and centre.war)
        self.assertEqual(foreign, foreign_before)
        self.assertEqual(w.states, before)
        self.assertFalse(w.annexations or host.goals or centre.goals)

    def test_character_ideology_guard_reuses_existing_roles_and_rejects_duplicate_additions(self):
        for cached in (False, True):
            with self.subTest(native_cache=cached):
                w = AquileianWorld()
                character = 'fixture_leader'
                definition = parse('fixture_leader = { country_leader = { ideology = liberalism } }')[0]
                w.character_definitions[character] = definition
                w.ideology_groups.update(liberalism='democratic', conservatism='democratic', despotism='neutrality')
                c = w.countries['JEB']
                c.characters.add(character)
                c.government = 'democratic'
                if cached:
                    c.roles[character] = copy.deepcopy(definition.all('country_leader'))
                self.assertTrue(w.check(parse('fixture_leader = { has_ideology = liberalism }'), 'JEB'))
                self.assertFalse(w.check(parse('fixture_leader = { has_ideology = conservatism }'), 'JEB'), 'Check the sub-ideology, not just its group')
                add = parse('add_country_leader_role = { character = fixture_leader country_leader = { ideology = liberalism } promote_leader = yes }')
                before = w.snapshot()
                with self.assertRaisesRegex(AssertionError, 'Duplicate country leader role'):
                    w.run(add, 'JEB')
                self.assertEqual(w.snapshot(), before)
                for ideology in ('liberalism', 'despotism'):
                    guarded = parse('''if = { limit = { fixture_leader = { has_ideology = IDEOLOGY } }
promote_character = { character = fixture_leader ideology = IDEOLOGY }
} else = { add_country_leader_role = { character = fixture_leader
country_leader = { ideology = IDEOLOGY } promote_leader = yes } }'''.replace('IDEOLOGY', ideology))
                    w.run(guarded, 'JEB')
                    roles = c.roles.get(character, definition.all('country_leader'))
                    self.assertEqual(sum(r.get('ideology') == ideology for r in roles), 1)
                    self.assertTrue(w.check(parse('fixture_leader = { has_ideology = ' + ideology + ' }'), 'JEB'))
                    once = w.snapshot()
                    w.run(guarded, 'JEB')
                    self.assertEqual(w.snapshot(), once)
                self.assertEqual({r.get('ideology') for r in c.roles[character]}, {'liberalism', 'despotism'})
                self.assertEqual(c.leader, character)
                self.assertEqual(c.party_leaders, {'democratic': character, 'neutrality': character})
                c.characters.remove(character)
                self.assertFalse(w.check(parse('fixture_leader = { has_ideology = liberalism }'), 'JEB'))

    def test_literal_decision_cost_is_checked_before_effect_and_zero_cost_allows_negative_pp(self):
        w = AquileianWorld()
        w.decisions = {n.key: n for n in parse('''
paid = { cost = 35 available = { NOT = { has_country_flag = blocked } } complete_effect = { add_manpower = 5 } }
free = { cost = 0 complete_effect = { add_manpower = 1 } }
''')}
        c = w.countries["JEB"]
        for pp, blocked in ((34.999, False), (35, True)):
            c.political_power = pp
            c.flags = {"blocked"} if blocked else set()
            before = w.snapshot()
            self.assertFalse(w.decision_available("paid", "JEB"))
            with self.assertRaisesRegex(AssertionError, "Unavailable decision"):
                w.decision("paid", "JEB")
            self.assertEqual(w.snapshot(), before)
        c.flags.clear()
        w.decision("paid", "JEB")
        self.assertEqual((c.political_power, c.manpower), (0, 5))
        c.political_power = -10
        w.decision("free", "JEB")
        self.assertEqual((c.political_power, c.manpower), (-10, 6))

    def test_recursive_focus_uncompletion_respects_or_parents_without_refunding_old_rewards(self):
        w = AquileianWorld()
        sources = ('focus = { id = political }', 'focus = { id = economy }',
                   'focus = { id = child prerequisite = { focus = political } }',
                   'focus = { id = grandchild prerequisite = { focus = child } }',
                   'focus = { id = alternative prerequisite = { focus = political focus = economy } }',
                   'focus = { id = requires_both prerequisite = { focus = political } prerequisite = { focus = economy } }')
        w.focuses = {n.get("id"): n for s in sources for n in parse(s)}
        c = w.countries["JER"]
        c.focuses = set(w.focuses)
        c.political_power, c.ideas = 123, {"earned_factory_policy"}
        w.run(parse("uncomplete_national_focus = { focus = political uncomplete_children = yes refund_political_power = no }"), "JER")
        self.assertEqual(c.focuses, {"economy", "alternative"})
        self.assertEqual(c.political_power, 123)
        self.assertEqual(c.ideas, {"earned_factory_policy"})

    def test_native_player_switch_guard_preserves_country_identity_and_other_players(self):
        native = next(n for n in read(OPT.eaw / "events/Angriver Events.txt")
                      if n.key == "country_event" and n.get("id") == "angriver.71")
        option = next(o for o in native.all("option") if o.get("name") == "angriver.71.a")
        switch = next(n for n in option.all("if") if any(x.key == "change_tag_from" for x in walk([n])))
        for destination_human in (False, True):
            with self.subTest(destination_human=destination_human):
                w = AquileianWorld()
                w.countries["FAT"] = Country("FAT", leader="native_incumbent", focus_tree="native_tree",
                                               focuses={"native_completed"})
                players = {"regional_player": "JEB", "other_player": "FLO"}
                if destination_human:
                    players["centre_player"] = "FAT"
                w.set_players(players)
                w.states["1"] = State("1", "JEB", "JEB", {"JEB"})
                countries, states = copy.deepcopy(w.countries), copy.deepcopy(w.states)
                w.run([switch], "JEB")
                if destination_human:
                    self.assertEqual(w.player_countries, players)
                    self.assertFalse(w.player_changes)
                    self.assertEqual(w.countries, countries)
                else:
                    self.assertEqual(w.player_countries, {"regional_player": "FAT", "other_player": "FLO"})
                    self.assertEqual(w.player_changes, [("regional_player", "JEB", "FAT")])
                    countries["JEB"].ai, countries["FAT"].ai = True, False
                    self.assertEqual(w.countries, countries)
                self.assertEqual(w.states, states)
                self.assertFalse(w.annexations)
                self.assertEqual((w.root, w.sender), ("JEB", "JEB"), "Player movement does not rewrite script scopes")
                before = w.snapshot()
                w.run([switch], "JEB")
                self.assertEqual(w.snapshot(), before)

    def test_reciprocal_control_and_original_core_queries_use_actual_nested_country(self):
        w = AquileianWorld()
        w.states = {"1": State("1", "JEB", "FLO", {"FLO"}),
                    "2": State("2", "FLO", "JEB", {"FLO"})}
        w.arrays["FLO.original_cores"] = list(w.states.values())
        w.arrays["JEB.original_cores"] = []
        w.root, w.sender = "JRR", "JEB"
        owned = parse("FROM = { all_owned_state = { is_fully_controlled_by = PREV } }")
        controlled = parse("FROM = { all_controlled_state = { is_owned_by = PREV } }")
        self.assertFalse(w.check(owned, "JRR"))
        self.assertFalse(w.check(controlled, "JRR"))
        w.states["1"].controller = "JEB"
        self.assertTrue(w.check(owned, "JRR"))
        self.assertFalse(w.check(controlled, "JRR"), "Foreign territory under occupation still blocks")
        w.states["2"].controller = "FLO"
        self.assertTrue(w.check(controlled, "JRR"))
        w.run(parse("1 = { remove_core_of = FLO add_core_of = JEB }"), "JRR")
        self.assertTrue(w.check(parse("is_in_array = { state_original_cores = FLO }"), w.states["1"]))
        self.assertFalse(w.check(parse("is_in_array = { state_original_cores = JEB }"), w.states["1"]))
        self.assertEqual(w.states["1"].owner, "JEB")
        self.assertEqual(w.states["2"].owner, "FLO")
        w.countries["FLO"].guarantors.add("JEB")
        self.assertTrue(w.check(parse("FLO = { is_guaranteed_by = FROM }"), "JRR"))
        self.assertFalse(w.check(parse("FLO = { is_guaranteed_by = ROOT }"), "JRR"))

    def test_scripted_focus_completion_runs_reward_while_unlock_only_marks_history(self):
        w = AquileianWorld()
        for fid in ("automatic", "history"):
            w.focuses[fid] = parse(f'focus = {{ id = {fid} available = {{ always = no }} completion_reward = {{ add_political_power = 7 }} }}')[0]
        self.assertFalse(w.available("automatic", "JRR"))
        w.run(parse("JRR = { complete_national_focus = automatic unlock_national_focus = history }"))
        self.assertEqual(w.countries["JRR"].focuses, {"automatic", "history"})
        self.assertEqual(w.countries["JRR"].political_power, 7)
        self.assertEqual(w.countries["JEB"].political_power, 0)
        before = w.snapshot()
        w.run(parse("JRR = { if = { limit = { NOT = { has_completed_focus = automatic } } complete_national_focus = automatic } }"))
        self.assertEqual(w.snapshot(), before)
        with self.assertRaisesRegex(AssertionError, "Unknown focus"):
            w.run(parse("complete_national_focus = missing"))

    def test_unit_spawn_requests_preserve_state_owner_count_and_ignore_previews(self):
        w = AquileianWorld()
        w.states["377"] = State("377", "JER", "JER", {"JER"})
        w.run(parse('division_template = { name = "Militia" regiments = { infantry = { x = 0 y = 0 } } }'))
        payload = 'create_unit = { division = "division_template = \\"Militia\\" start_experience_factor = 0.2" owner = ROOT count = 2 }'
        w.run(parse("effect_tooltip = { " + payload + " }"))
        self.assertFalse(w.unit_spawns)
        before = w.snapshot()
        w.run(parse("377 = { " + payload + " }"))
        self.assertEqual(w.unit_spawns[0][:3], ("377", "JEB", 2))
        self.assertNotEqual(w.snapshot(), before)
        self.assertEqual(w.states["377"].owner, "JER", "Spawn requests cannot transfer territory")
        for source in ('create_unit = { owner = JEB }', 'add_army_experience = 10'):
            with self.subTest(source=source), self.assertRaises(AssertionError):
                w.run(parse(source))

    def test_timed_ideas_expire_or_remove_without_leaking_targeted_coefficients(self):
        w = AquileianWorld()
        w.idea_definitions["test_support"] = parse('test_support = { modifier = { stability_factor = -0.1 } targeted_modifier = { tag = JER attack_bonus_against = 0.05 defense_bonus_against = 0.1 } }')[0]
        w.countries["JEB"].ideas.add("unrelated")
        w.run(parse("add_timed_idea = { idea = test_support days = 3 }"))
        self.assertEqual(w.idea_modifiers("JEB", {"test_support"}), {"stability_factor": -.1})
        self.assertEqual(w.idea_modifiers("JEB", {"test_support"}, "JER"),
                         {"attack_bonus_against": .05, "defense_bonus_against": .1})
        for other in ("JRR", "FLO"):
            self.assertEqual(w.idea_modifiers("JEB", {"test_support"}, other), {})
        self.assertEqual(w.idea_modifiers("JER", {"test_support"}, "JEB"), {})
        w.advance_days(2)
        self.assertTrue(w.check(parse("has_idea = test_support")))
        w.advance_days(1)
        self.assertEqual(w.countries["JEB"].ideas, {"unrelated"})
        self.assertEqual(w.idea_modifiers("JEB", {"test_support"}, "JER"), {})
        w.run(parse("add_timed_idea = { idea = test_support days = 3 } remove_ideas = test_support"))
        self.assertFalse(w.countries["JEB"].idea_days)
        w.advance_days(3)
        self.assertEqual(w.countries["JEB"].ideas, {"unrelated"})
        with self.assertRaisesRegex(AssertionError, "Scoped/timed"):
            w.run(parse("add_dynamic_modifier = { modifier = unsupported scope = JER days = 3 }"))

    def test_parser_keeps_groups_and_rejects_unbalanced_blocks(self):
        node = parse('focus = { id = example prerequisite = { focus = a focus = b } prerequisite = { focus = c } }')[0]
        self.assertEqual([[n.value for n in group.all("focus")] for group in node.all("prerequisite")], [["a", "b"], ["c"]])
        for text in ("if = {", "}", "x ="):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse(text)

    def test_conditional_chains_hidden_rewards_and_previews_are_distinct(self):
        w = AquileianWorld()
        w.run(parse('if = { limit = { always = no } add_political_power = 99 } else_if = { limit = { always = yes } hidden_effect = { add_political_power = 7 } } else = { add_political_power = 99 } effect_tooltip = { add_political_power = 999 }'))
        self.assertEqual(w.countries["JEB"].political_power, 7)
        for operation in (w.check, w.run):
            with self.assertRaises(AssertionError):
                operation(parse("unimplemented_fixture_primitive = yes"))

    def test_prerequisite_groups_exclusions_branch_and_tree_membership(self):
        w = AquileianWorld()
        w.focuses["end"] = parse('focus = { id = end prerequisite = { focus = a focus = b } prerequisite = { focus = c } mutually_exclusive = { focus = rival } allow_branch = { is_subject = no } completion_reward = { add_political_power = 20 } }')[0]
        w.tree_members = {"regional": {"end"}, "foreign": set()}
        c = w.countries["JEB"]
        c.focus_tree = "regional"
        for completed, expected in ((set(), False), ({"a"}, False), ({"c"}, False),
                                    ({"a", "c"}, True), ({"b", "c"}, True), ({"a", "c", "rival"}, False)):
            with self.subTest(completed=completed):
                c.focuses = completed
                self.assertEqual(w.available("end", "JEB"), expected)
        c.focuses = {"b", "c"}
        c.subject = True
        self.assertFalse(w.available("end", "JEB"))
        c.subject, c.focus_tree = False, "foreign"
        self.assertFalse(w.available("end", "JEB"))
        c.focus_tree = "regional"
        w.complete("end", "JEB")
        with self.assertRaises(AssertionError):
            w.complete("end", "JEB")
        self.assertEqual(c.political_power, 20)

    def test_subject_identity_and_nested_prev_do_not_leak(self):
        w = AquileianWorld()
        w.countries["JRR"].subject, w.countries["JRR"].overlord = True, "JEB"
        w.run(parse('JRR = { if = { limit = { is_subject_of = PREV } PREV = { add_political_power = 11 } } }'))
        self.assertEqual(w.countries["JEB"].political_power, 11)
        self.assertEqual(w.countries["JRR"].political_power, 0)
        self.assertIsNone(w.previous)
        self.assertTrue(w.check(parse("is_subject = yes is_subject_of = JEB"), "JRR"))
        self.assertFalse(w.check(parse("is_subject_of = JER"), "JRR"))

    def test_release_and_annex_conserve_unrelated_land_and_cores(self):
        w = AquileianWorld()
        w.countries["JRR"].exists = False
        w.states = {
            "1": State("1", "JEB", "JEB", {"JRR", "JER"}),
            "2": State("2", "JEB", "JEB", {"JRR"}),
            "3": State("3", "FLO", "FLO", {"JRR"}),
            "4": State("4", "JEB", "JEB", {"JEB"}),
        }
        original = copy.deepcopy(w.states)
        w.run(parse("release_puppet = JRR"))
        self.assertEqual({sid for sid, s in w.states.items() if s.owner == "JRR"}, {"1", "2"})
        self.assertTrue(w.check(parse("exists = yes is_subject_of = JEB"), "JRR"))
        w.run(parse("annex_country = { target = JRR transfer_troops = no }"))
        self.assertFalse(w.countries["JRR"].exists)
        self.assertEqual(w.states, original)
        self.assertEqual(w.annexations, [("JEB", "JRR", "no")])
        self.assertFalse(w.hook_calls, "Engine hook dispatch is explicit")

    def test_both_state_transfer_spellings_update_only_the_selected_state(self):
        w = AquileianWorld()
        w.states = {"1": State("1", "JER", "FLO", {"JER"}),
                    "2": State("2", "FLO", "FLO", {"FLO"})}
        other = copy.deepcopy(w.states["2"])
        w.run(parse("transfer_state = 1"))
        self.assertEqual((w.states["1"].owner, w.states["1"].controller), ("JEB", "JEB"))
        w.run(parse("1 = { transfer_state_to = JRR }"))
        self.assertEqual((w.states["1"].owner, w.states["1"].controller), ("JRR", "JRR"))
        self.assertEqual(w.states["1"].cores, {"JER"})
        self.assertEqual(w.states["2"], other)

    def test_queued_delivery_and_stale_click_recheck_context(self):
        w = AquileianWorld()
        w.events["test.1"] = parse('country_event = { id = test.1 trigger = { is_subject = no } option = { name = accept trigger = { is_subject = no } if = { limit = { is_subject = no } add_political_power = 50 } } }')[0]
        w.run(parse("JRR = { country_event = { id = test.1 days = 1 } }"))
        w.advance_days(1)
        w.countries["JRR"].subject = True
        self.assertFalse(w.deliver("test.1", "JRR"))
        self.assertFalse(w.scheduled)
        w.click("test.1", "accept", "JRR", sender="JEB", stale=True)
        self.assertEqual(w.countries["JRR"].political_power, 0)
        self.assertEqual(w.sender, "JEB")

    def test_focus_reload_retains_only_completed_members(self):
        w = AquileianWorld()
        w.countries["JEB"].focuses = {"kept", "foreign"}
        w.tree_members["regional"] = {"kept", "new"}
        w.run(parse("load_focus_tree = { tree = regional keep_completed = yes }"))
        self.assertEqual(w.countries["JEB"].focuses, {"kept"})
        self.assertEqual(w.countries["JEB"].focus_tree, "regional")


class NativeSupportResolution(unittest.TestCase):
    """Execute native decision fields; subsequent native events remain unmodelled."""

    @classmethod
    def setUpClass(cls):
        nodes = read(OPT.eaw / "common/decisions/JER_decisions.txt")
        cls.mission = next(n for category in nodes for n in category.children if n.key == "JER_revolution_mission")

    def test_native_timeout_uses_actual_support_and_gives_ties_to_revolutionaries(self):
        events = {"JEB": ("aquileia.9", "aquileia.10"), "JRR": ("aquileia.11", "aquileia.12"),
                  "VIN": ("aquileia.13", "aquileia.14"), "JFT": ("aquileia.15", "aquileia.45")}
        for tag, event_ids in events.items():
            for royal, revolutionary, camp, index in ((51, 50, "royal", 0), (50, 51, "rev", 1), (50, 50, "rev", 1)):
                with self.subTest(tag=tag, royal=royal, revolutionary=revolutionary):
                    w = AquileianWorld()
                    w.root = w.sender = tag
                    w.countries[tag].variables.update(monarchist_support=royal, revolutionary_support=revolutionary)
                    w.run(self.mission.get("timeout_effect", []), tag)
                    self.assertEqual(w.countries[tag].flags & set(NATIVE_OUTCOMES.values()), {NATIVE_OUTCOMES[camp]})
                    self.assertEqual(w.scheduled, [(1, tag, event_ids[index], tag)])
                    self.assertIn("JER_revolution_begun", w.global_flags)
                    self.assertFalse(w.global_flags & {"JER_revolution_ended", "JER_revolution_ended_2"})
                    self.assertTrue(all(not c.flags for other, c in w.countries.items() if other != tag))

    def test_native_immediate_success_requires_all_four_strict_wins_and_queues_distinct_event(self):
        for focus, royal, revolutionary, event in (("JER_state_of_aquileia", 51, 50, "aquileia.47"),
                                                   ("JER_fight_for_freedom", 50, 51, "aquileia.17")):
            with self.subTest(focus=focus):
                w = AquileianWorld()
                w.root = w.sender = "JER"
                w.countries["JER"].focuses.add(focus)
                for tag in REGIONS:
                    w.countries[tag].variables.update(monarchist_support=royal, revolutionary_support=revolutionary)
                for observer in ("JER", *REGIONS):
                    self.assertTrue(w.check(self.mission.get("available", []), observer))
                for tied in REGIONS:
                    w.countries[tied].variables["monarchist_support"] = revolutionary
                    self.assertFalse(w.check(self.mission.get("available", []), "JER"))
                    w.countries[tied].variables["monarchist_support"] = royal
                w.run(self.mission.get("complete_effect", []), "JER")
                self.assertEqual(w.scheduled, [(1, "JER", event, "JER")])
                self.assertTrue(all(not c.flags for c in w.countries.values()), "Queued victory is not a delivered local outcome")
                self.assertFalse(w.global_flags)

    def test_native_influence_effect_changes_and_clamps_both_competing_variables(self):
        nodes = read(OPT.eaw / "common/decisions/JEB_decisions.txt")
        decision = next(n for category in nodes for n in category.children if n.key == "JER_JEB_mon_raids")
        for royal, revolutionary, expected in ((50, 50, (55, 45)), (99, 1, (100, 0))):
            with self.subTest(royal=royal, revolutionary=revolutionary):
                w = AquileianWorld()
                w.countries["JEB"].variables.update(monarchist_support=royal, revolutionary_support=revolutionary)
                w.run(decision.get("remove_effect", []), "JEB")
                self.assertEqual(tuple(w.countries["JEB"].variables[k] for k in ("monarchist_support", "revolutionary_support")), expected)
                self.assertFalse(w.countries["JER"].variables)


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production = Production()
        cls.template = AquileianWorld(cls.production)
        cls.template.load_native_states()
        cls.template.load_native_countries()
        cls.template.load_native_helpers()
        for tag in REGIONS:
            cls.template.countries[tag].focus_tree = P + "regional_tree"

    def world(self, route):
        w = copy.deepcopy(self.template)
        w.root = w.sender = route.tag
        w.countries[route.tag].political_power = 100
        # External native preparation decision, not a fabricated AQR mandate.
        w.countries[route.tag].flags.add(route.preparation)
        w.countries[route.tag].flags.add("JER_" + route.tag + ("_monarchist" if route.camp == "royal" else "_revolutionary"))
        if route.key in NATIVE_MOVEMENTS:
            # An external native preparation result; no authored eligibility flags.
            w.countries[route.tag].variables[NATIVE_MOVEMENTS[route.key]] = 60
        w.countries["JER"].focuses.add("JER_state_of_aquileia" if route.camp == "royal" else "JER_fight_for_freedom")
        return w

    @staticmethod
    def start(w):
        w.effect(P + "start_regions", "JER")

    def organised(self, route):
        w = self.world(route)
        self.start(w)
        self.outcome(w, route.tag, route.camp)
        w.daily()
        self.select_native(w, route)
        for focus in (route.key + "_pledge", route.key + "_organise"):
            w.complete(P + focus, route.tag)
        return w

    def select_native(self, w, route):
        event_id = "HSM_AQR." + str(410 + REGIONS.index(route.tag))
        w.advance_days(1)
        self.assertTrue(w.deliver(event_id, route.tag))
        w.click(event_id, event_id + "." + route.key, route.tag)

    @staticmethod
    def legacy_without_native_snapshot(w, tag):
        """An old-save input predating this feature, retaining all earned grants."""
        c = w.countries[tag]
        c.flags = {f for f in c.flags if not f.startswith(P + "native_")
                   and f != P + "snapshot_native_politics_done"}
        c.flag_days = {f: days for f, days in c.flag_days.items() if f in c.flags}
        c.variables = {k: v for k, v in c.variables.items() if not k.startswith(P + "native_value_")}
        w.scheduled = [p for p in w.scheduled if not (p[1] == tag and p[2] in
                       {"HSM_AQR." + str(n) for n in range(410, 414)})]

    @staticmethod
    def outcome(w, tag, camp, *, local=True, global_camp=None, finished=True):
        """The native contest/war result is an explicit external fixture input."""
        w.countries[tag].flags.difference_update(NATIVE_OUTCOMES.values())
        w.global_flags.difference_update(GLOBAL_OUTCOMES.values())
        w.global_flags.add("JER_revolution_begun")
        if local:
            w.countries[tag].flags.add(NATIVE_OUTCOMES[camp])
        if finished:
            w.global_flags.add(GLOBAL_OUTCOMES[global_camp or camp])

    def assembly(self, route):
        w = self.organised(route)
        w.complete(P + route.key + "_settle", route.tag)
        event_id = "HSM_AQR." + str(100 + ROUTES.index(route))
        w.advance_days(1)
        self.assertTrue(w.deliver(event_id, route.tag))
        return w, event_id

    def ratified(self, route=ROUTES[1], choice="a"):
        w, event_id = self.assembly(route)
        w.click(event_id, event_id + "." + choice, route.tag)
        return w

    def national(self, route=ROUTES[1], choice="a", proclaim=True):
        w = self.ratified(route, choice)
        w.complete(P + "regional_articles", route.tag)
        w.daily()  # Real maintenance records the prior native subordination.
        c = w.countries[route.tag]
        c.subject, c.overlord, c.faction = False, "", ""
        w.complete(P + "national_mandate", route.tag)
        # Outcome of an ordinary external war/peace conference, not an AQR effect.
        for state in w.states.values():
            if state.owner == "JER":
                state.owner = state.controller = route.tag
        w.countries["JER"].exists = False
        for tag in REGIONS:
            w.countries[tag].subject, w.countries[tag].overlord = False, ""
        if proclaim:
            w.complete(P + "proclaim", route.tag)
        return w

    @staticmethod
    def centre_outcome(w, camp):
        """External native political settlement; not execution of native outcome events."""
        c = w.countries["JER"]
        c.flags.difference_update({"JER_is_monarchist", "JER_democracy_established"})
        c.flags.add("JER_is_monarchist" if camp == "royal" else "JER_democracy_established")
        c.government = "neutrality" if camp == "royal" else "democratic"
        c.focus_tree = "aquileian_focus"


class NativePhase(Fixture):
    def test_registration_only_marks_existing_regions_without_focus_or_reward(self):
        for phase in ("none", "preparation", "local_result", "begun", "global_end"):
            with self.subTest(phase=phase):
                w = copy.deepcopy(self.template)
                if phase == "preparation": w.countries["JER"].focuses.add("JER_state_of_aquileia")
                elif phase == "local_result": w.countries["JEB"].flags.add(NATIVE_OUTCOMES["royal"])
                elif phase == "begun": w.global_flags.add("JER_revolution_begun")
                elif phase == "global_end": w.global_flags.add(GLOBAL_OUTCOMES["royal"])
                expected = list(w.snapshot())
                registered = set() if phase == "none" else {"JEB"} if phase == "local_result" else set(REGIONS)
                for tag in registered:
                    expected[0][tag].flags.add(P + "started")
                self.start(w)
                self.assertEqual(w.snapshot(), tuple(expected), "Registration cannot grant focus progress, units, ideas or currency")
                self.assertTrue(all(P + "opening" not in c.focuses for c in w.countries.values()))
                before = w.snapshot()
                self.start(w)
                self.assertEqual(w.snapshot(), before)

    def test_recording_uses_native_outcome_and_freezes_it_without_mechanical_grants(self):
        for tag in REGIONS:
            for camp in ("royal", "rev"):
                for local in (False, True):
                    with self.subTest(tag=tag, camp=camp, local=local):
                        route = next(r for r in ROUTES if r.tag == tag and r.camp == camp)
                        w = self.world(route)
                        self.start(w)
                        self.outcome(w, tag, camp, local=local, finished=not local)
                        # Deliberately contrary support: the already delivered native result wins.
                        w.countries[tag].variables.update(monarchist_support=10 if camp == "royal" else 90,
                                                          revolutionary_support=90 if camp == "royal" else 10)
                        before = w.snapshot()
                        w.effect(P + "record_native_outcome", tag)
                        c = w.countries[tag]
                        self.assertEqual(c.flags & set(NATIVE_OUTCOMES.values()), {NATIVE_OUTCOMES[camp]})
                        self.assertIn(P + "native_outcome_recorded", c.flags)
                        # The settlement helper may snapshot flags/variables, but no economic or political effects.
                        after = list(w.snapshot())
                        for country, previous in before[0].items():
                            observed = after[0][country]
                            for variable in ("monarchist_support", "revolutionary_support"):
                                self.assertEqual(observed.variables.get(variable), previous.variables.get(variable))
                            observed.flags, observed.flag_days, observed.variables = previous.flags, previous.flag_days, previous.variables
                        self.assertEqual(tuple(after), before)
                        w.global_flags.difference_update(GLOBAL_OUTCOMES.values())
                        w.global_flags.add(GLOBAL_OUTCOMES["rev" if camp == "royal" else "royal"])
                        c.variables.update(monarchist_support=50, revolutionary_support=50)
                        frozen = w.snapshot()
                        w.effect(P + "record_native_outcome", tag)
                        self.assertEqual(w.snapshot(), frozen, "A later global government cannot resnapshot the local result")

    def test_opening_waits_for_postwar_peace_and_local_rule_then_queues_once(self):
        for tag in REGIONS:
            with self.subTest(tag=tag):
                route = next(r for r in ROUTES if r.tag == tag and r.camp == "royal")
                w = self.world(route)
                self.start(w)
                for resolved in (False, True):
                    if resolved:
                        self.outcome(w, tag, "royal", finished=False)
                        w.effect(P + "record_native_outcome", tag)
                    before = w.snapshot()
                    w.effect(P + "open_postwar", tag)
                    self.assertEqual(w.snapshot(), before, "Native preparation or an unfinished revolution cannot open the tree")
                w.global_flags.add(GLOBAL_OUTCOMES["royal"])
                for changed in ("war", "capitulated", "annexed", "foreign_subject"):
                    blocked = copy.deepcopy(w)
                    c = blocked.countries[tag]
                    if changed == "war": c.war = True
                    elif changed == "capitulated": c.capitulated = True
                    elif changed == "annexed": c.exists = False
                    else: c.subject, c.overlord = True, "FLO"
                    before = blocked.snapshot()
                    blocked.effect(P + "open_postwar", tag)
                    blocked.effect(P + "opening", tag)
                    self.assertEqual(blocked.snapshot(), before, changed)
                pp = w.countries[tag].political_power
                w.effect(P + "open_postwar", tag)
                self.assertIn(P + "opening", w.countries[tag].focuses)
                self.assertFalse(w.available(P + "opening", tag))
                self.assertEqual(w.countries[tag].political_power, pp)
                eid = "HSM_AQR." + str(410 + REGIONS.index(tag))
                self.assertEqual([p[2] for p in w.scheduled if p[1] == tag], [eid])
                before = w.snapshot()
                w.effect(P + "open_postwar", tag)
                self.assertEqual(w.snapshot(), before)

    def test_destroyed_centre_without_native_result_cannot_infer_a_winner_from_support(self):
        for tag in REGIONS:
            for royal, revolutionary in ((80, 20), (20, 80), (50, 50)):
                with self.subTest(tag=tag, royal=royal, revolutionary=revolutionary):
                    w = self.world(next(r for r in ROUTES if r.tag == tag and r.camp == "royal"))
                    self.start(w)
                    w.countries[tag].variables.update(monarchist_support=royal, revolutionary_support=revolutionary)
                    w.countries["JER"].exists = False
                    before = w.snapshot()
                    w.effect(P + "record_native_outcome", tag)
                    w.effect(P + "open_postwar", tag)
                    self.assertEqual(w.snapshot(), before)
                    self.assertFalse(w.countries[tag].flags & set(NATIVE_OUTCOMES.values()))
                    self.assertNotIn(P + "native_outcome_recorded", w.countries[tag].flags)
                    self.assertNotIn(P + "opening", w.countries[tag].focuses)


class NativeSettlement(Fixture):
    def ready(self, route, *, values=None, preparation_flags=None, chosen_camp=None):
        w = self.world(route)
        c = w.countries[route.tag]
        if values is not None:
            for variable in (*NATIVE_MOVEMENTS.values(), "JEB_other_clubs"):
                c.variables.pop(variable, None)
            c.variables.update(values)
        if preparation_flags is not None:
            c.flags.difference_update(r.preparation for r in ROUTES if r.tag == route.tag)
            c.flags.difference_update({"JER_" + route.tag + "_monarchist", "JER_" + route.tag + "_revolutionary"})
            c.flags.update(preparation_flags)
        if chosen_camp:
            c.flags.difference_update({"JER_" + route.tag + "_monarchist", "JER_" + route.tag + "_revolutionary"})
            c.flags.add("JER_" + route.tag + ("_monarchist" if chosen_camp == "royal" else "_revolutionary"))
        self.start(w)
        self.outcome(w, route.tag, route.camp)
        w.daily()
        return w, "HSM_AQR." + str(410 + REGIONS.index(route.tag))

    def candidates(self, w, tag):
        return {r.key for r in ROUTES if w.check(w.triggers[P + "native_candidate_" + r.key], tag)}

    def test_all_fifteen_programmes_require_the_real_selection_before_pledging_and_grant_nothing(self):
        for route in ROUTES:
            with self.subTest(route=route.key):
                w, eid = self.ready(route)
                c = w.countries[route.tag]
                self.assertEqual(self.candidates(w, route.tag), {route.key})
                self.assertFalse(w.available(P + route.key + "_pledge", route.tag))
                w.advance_days(1)
                self.assertTrue(w.deliver(eid, route.tag))
                before = list(w.snapshot())
                w.click(eid, eid + "." + route.key, route.tag)
                expected_country = before[0][route.tag]
                expected_country.flags.add(P + "native_mandate_" + route.key)
                for flag in (P + "native_settlement_pending", P + "native_settlement_queued"):
                    expected_country.flags.discard(flag)
                    expected_country.flag_days.pop(flag, None)
                self.assertEqual(w.snapshot(), tuple(before), "Selection may only change mandate/pending metadata")
                self.assertTrue(w.available(P + route.key + "_pledge", route.tag))
                self.assertFalse(any(w.available(P + r.key + "_pledge", route.tag)
                                     for r in ROUTES if r.key != route.key))
                selected = w.snapshot()
                for alternative in (r for r in ROUTES if r.tag == route.tag):
                    w.click(eid, eid + "." + alternative.key, route.tag, stale=True)
                self.assertEqual(w.snapshot(), selected, "Stale alternative selection cannot replace a valid mandate")
                w.complete(P + route.key + "_pledge", route.tag)
                self.assertEqual(c.political_power, 100)

    def test_native_movement_strength_ties_signed_values_and_marais_determine_candidates(self):
        scenarios = (
            ("JEB_constitutional", (60, 20, 10, 10), (), {"JEB_constitutional"}),
            ("JEB_constitutional", (40, 40, 10, 10), (), {"JEB_constitutional", "JEB_moderate"}),
            ("JEB_constitutional", (20, 10, 10, 60), (), {"JEB_constitutional"}),
            ("JEB_constitutional", (20, 20, 10, 60), (), {"JEB_constitutional", "JEB_moderate"}),
            ("JEB_constitutional", (40, 10, 10, 40), (), {"JEB_constitutional"}),
            ("JEB_constitutional", (27, 58, 102, 39), (), {"JEB_cocardiers"}),
            ("JEB_constitutional", (0, 0, 0, 0), (), set()),
            ("JFT_communes", (30, 40, 10), (), {"JFT_enfants"}),
            ("JFT_communes", (30, 30, 0), (), {"JFT_communes", "JFT_enfants"}),
            ("JFT_communes", (-4, -2, 0), ("JER_JFT_commie_supp", "JER_JFT_fash_supp"), {"JFT_enfants"}),
            ("JFT_communes", (0, 0, 0), ("JER_JFT_dem_supp",), {"JFT_fja"}),
            ("JFT_communes", (0, 0, 0), (), set()),
            ("VIN_abc", (5, 10, 1), (), {"VIN_chevaliers"}),
            ("VIN_abc", (10, 0, 10), (), {"VIN_abc", "VIN_sis"}),
            ("VIN_abc", (0, 0, 0), ("JER_VIN_movements2",), {"VIN_chevaliers"}),
            ("VIN_abc", (-4, -2, 0), ("JER_VIN_movements1", "JER_VIN_movements2"), {"VIN_chevaliers"}),
            ("VIN_abc", (0, 0, 0), (), set()),
        )
        for rid, scores, flags, expected in scenarios:
            with self.subTest(region=rid[:3], scores=scores, flags=flags):
                route = next(r for r in ROUTES if r.key == rid)
                variables = [v for key, v in NATIVE_MOVEMENTS.items() if key.startswith(route.tag)]
                if route.tag == "JEB": variables.append("JEB_other_clubs")
                w, eid = self.ready(route, values=dict(zip(variables, scores)), preparation_flags=flags)
                self.assertEqual(self.candidates(w, route.tag), expected)
                if not expected:
                    self.assertFalse([p for p in w.scheduled if p[1:3] == (route.tag, eid)])
                    self.assertFalse(w.decision_available(P + 'native_settlement_retry_' + route.tag, route.tag))
                    before = w.snapshot()
                    for r in (r for r in ROUTES if r.tag == route.tag):
                        w.effect(P + 'native_select_' + r.key, route.tag)
                    self.assertEqual(w.snapshot(), before)
                    continue
                w.advance_days(1)
                self.assertTrue(w.deliver(eid, route.tag))
                visible = {o.get("name").removeprefix(eid + ".") for o in w.events[eid].all("option")
                           if w.check(o.get("trigger", []), route.tag)}
                self.assertEqual(visible, expected | {"later"})
                descriptions = [d.get("text") for d in w.events[eid].all("desc")
                                if w.check(d.get("trigger", []), route.tag)]
                self.assertEqual(len(descriptions), 1, (rid, scores, descriptions))

    def test_westkeep_native_agreements_and_actual_winner_override_former_allegiance(self):
        for flags, expected in (((), set()),
                                (("JRR_absolutist",), {"JRR_absolutist"}),
                                (("JRR_reformism",), {"JRR_coalition"}),
                                (("JRR_absolutist", "JRR_reformism"), {"JRR_absolutist", "JRR_coalition"})):
            with self.subTest(flags=flags):
                w, _ = self.ready(ROUTES[4], preparation_flags=flags, chosen_camp="rev")
                self.assertEqual(self.candidates(w, "JRR"), expected)
        for tag in REGIONS:
            for camp in ("royal", "rev"):
                route = next(r for r in ROUTES if r.tag == tag and r.camp == camp)
                with self.subTest(tag=tag, winner=camp):
                    w, _ = self.ready(route, chosen_camp="rev" if camp == "royal" else "royal")
                    self.assertIn(route.key, self.candidates(w, tag))
                    self.assertFalse(self.candidates(w, tag) & {r.key for r in ROUTES if r.camp != camp})

    def test_recorded_movements_and_native_flags_cannot_be_rewritten_by_later_spending(self):
        for route in (ROUTES[2], ROUTES[5], ROUTES[8], ROUTES[12]):
            with self.subTest(route=route.key):
                w, _ = self.ready(route)
                c = w.countries[route.tag]
                expected = self.candidates(w, route.tag)
                snapshot = {k: v for k, v in c.variables.items() if k.startswith(P + "native_value_")}
                frozen_flags = {f for f in c.flags if f.startswith(P + "native_flag_")}
                for r in ROUTES:
                    if r.tag == route.tag:
                        c.flags.add(r.preparation)
                        if r.key in NATIVE_MOVEMENTS:
                            c.variables[NATIVE_MOVEMENTS[r.key]] = 0 if r.key == route.key else 999
                w.effect(P + "record_native_outcome", route.tag)
                w.effect(P + "snapshot_native_politics", route.tag)
                self.assertEqual({k: v for k, v in c.variables.items() if k.startswith(P + "native_value_")}, snapshot)
                self.assertEqual({f for f in c.flags if f.startswith(P + "native_flag_")}, frozen_flags)
                self.assertEqual(self.candidates(w, route.tag), expected)

    def test_deferral_retry_and_failed_delivery_require_explicit_requeue_without_daily_spam(self):
        queue = list(walk(self.production.effects[P + 'queue_native_settlement']))
        latch = next(i for i, n in enumerate(queue) if n.key == 'set_country_flag'
                     and n.value == P + 'native_settlement_requested')
        calls = [i for i, n in enumerate(queue) if n.key == 'country_event']
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(latch < i for i in calls), 'Latch must be permanent and written before scheduling')
        for tag in REGIONS:
            route = next(r for r in ROUTES if r.tag == tag and r.camp == "rev")
            ready, eid = self.ready(route)
            self.assertIn(P + 'native_settlement_requested', ready.countries[tag].flags)
            self.assertNotIn(P + 'native_settlement_requested', ready.countries[tag].flag_days)
            # Old saves can already contain duplicate queued packets. Preserve
            # the real producer's recipient, sender and due time for that input.
            packet = next(p for p in ready.scheduled if p[1:3] == (tag, eid))
            ready.scheduled.append(copy.deepcopy(packet))
            ready.advance_days(1)
            self.assertTrue(ready.deliver(eid, tag))
            before_duplicate = list(ready.snapshot())
            before_duplicate[5].remove(packet)
            self.assertFalse(ready.deliver(eid, tag), 'Only the first queued packet may open before selection')
            self.assertEqual(ready.snapshot(), tuple(before_duplicate), 'Rejected duplicate must not reset the open event lease')
            self.assertFalse(any(f.startswith(P + 'native_mandate_') for f in ready.countries[tag].flags))
            for pp in (-5, 0, 49.5, 500):
                with self.subTest(tag=tag, pp=pp):
                    w = copy.deepcopy(ready)
                    c = w.countries[tag]
                    c.political_power = pp
                    retry = P + "native_settlement_retry_" + tag
                    self.assertFalse(w.decision_available(retry, tag))
                    w.click(eid, eid + ".later", tag)
                    w.daily()
                    self.assertFalse([p for p in w.scheduled if p[1:3] == (tag, eid)])
                    self.assertTrue(w.decision_available(retry, tag))
                    w.decision(retry, tag)
                    self.assertFalse(w.decision_available(retry, tag))
                    w.run(w.decisions[retry].get("complete_effect", []), tag)
                    self.assertEqual(len([p for p in w.scheduled if p[1:3] == (tag, eid)]), 1)
                    self.assertEqual(c.political_power, pp)
                    self.select_native(w, route)
                    self.assertEqual(c.political_power, pp)
                    self.assertFalse(w.decision_available(retry, tag))

        # The permanent request latch survives both failed delivery and lease expiry.
        w, eid = self.ready(ROUTES[2])
        c = w.countries["JEB"]
        c.war = True
        w.advance_days(1)
        self.assertFalse(w.deliver(eid, "JEB"))
        c.war = False
        w.daily()
        self.assertFalse([p for p in w.scheduled if p[1:3] == ("JEB", eid)])
        for elapsed in (6, 30, 90):
            w.advance_days(elapsed)
            w.daily()
            self.assertFalse([p for p in w.scheduled if p[1:3] == ('JEB', eid)])
            self.assertIn(P + 'native_settlement_requested', c.flags)
        retry = P + 'native_settlement_retry_JEB'
        self.assertTrue(w.decision_available(retry, 'JEB'))
        w.decision(retry, 'JEB')
        self.assertEqual(len([p for p in w.scheduled if p[1:3] == ("JEB", eid)]), 1)
        w.advance_days(1)
        self.assertTrue(w.deliver(eid, "JEB"))
        w.advance_days(30)
        w.daily()
        self.assertFalse([p for p in w.scheduled if p[1:3] == ("JEB", eid)])
        self.assertTrue(w.decision_available(P + "native_settlement_retry_JEB", "JEB"))

    def test_delivery_and_open_options_recheck_native_character_and_local_context(self):
        for route in (r for r in ROUTES if not r.character.startswith(P)):
            ready, eid = self.ready(route)
            for changed in ("war", "capitulated", "foreign_subject", "annexed", "character", "winner"):
                with self.subTest(route=route.key, changed=changed):
                    w = copy.deepcopy(ready)
                    c = w.countries[route.tag]
                    if changed == "war": c.war = True
                    elif changed == "capitulated": c.capitulated = True
                    elif changed == "foreign_subject": c.subject, c.overlord = True, "FLO"
                    elif changed == "annexed": c.exists = False
                    elif changed == "character": c.characters.remove(route.character)
                    else: self.outcome(w, route.tag, "rev" if route.camp == "royal" else "royal")
                    w.advance_days(1)
                    self.assertFalse(w.deliver(eid, route.tag))
                    before = w.snapshot()
                    w.click(eid, eid + "." + route.key, route.tag, stale=True)
                    self.assertEqual(w.snapshot(), before)

        # Test an actually opened packet too: its pending lease must survive an
        # invalid old click, rather than being silently cleared outside the guard.
        for changed in ('character', 'capitulated'):
            w, eid = self.ready(ROUTES[1])
            w.advance_days(1)
            self.assertTrue(w.deliver(eid, 'JEB'))
            if changed == 'character':
                w.countries['JEB'].characters.remove(ROUTES[1].character)
            else:
                w.countries['JEB'].capitulated = True
            before = w.snapshot()
            w.click(eid, eid + '.' + ROUTES[1].key, 'JEB', stale=True)
            self.assertEqual(w.snapshot(), before)

    def test_legacy_unratified_route_can_resume_without_replay_and_ratified_programme_is_preserved(self):
        route = ROUTES[2]
        w = self.organised(route)
        self.legacy_without_native_snapshot(w, route.tag)
        c = w.countries[route.tag]
        focuses, pp = set(c.focuses), c.political_power
        w.daily()
        self.assertNotIn(P + "route_" + route.key, c.flags)
        self.assertEqual(c.focuses, focuses)
        self.assertEqual(c.political_power, pp)
        self.assertFalse(w.decision_available(P + "resume_" + route.key, route.tag))
        w.effect(P + "finish_" + route.key + "_organise", route.tag)
        self.assertEqual(c.political_power, pp)
        self.select_native(w, route)
        self.assertTrue(w.decision_available(P + "resume_" + route.key, route.tag))
        w.decision(P + "resume_" + route.key, route.tag)
        self.assertIn(P + "route_" + route.key, c.flags)
        w.effect(P + "finish_" + route.key + "_organise", route.tag)
        self.assertEqual(c.political_power, pp)
        self.assertEqual(c.focuses, focuses)

        # A paid legacy programme survives a rival movement's stronger snapshot.
        route = ROUTES[2]
        w = self.ratified(route)
        self.legacy_without_native_snapshot(w, route.tag)
        c = w.countries[route.tag]
        c.variables[NATIVE_MOVEMENTS["JEB_cocardiers"]] = 100
        earned = (c.political_power, c.leader, set(c.focuses),
                  {k: v for k, v in c.variables.items() if k.startswith(P + "mod_")})
        w.daily()
        self.assertIn(P + "route_" + route.key, c.flags)
        self.assertIn(P + "ratified_" + route.key, c.flags)
        self.assertTrue(w.check(w.triggers[P + "native_eligible_" + route.key], route.tag))
        self.assertEqual((c.political_power, c.leader, set(c.focuses),
                          {k: v for k, v in c.variables.items() if k.startswith(P + "mod_")}), earned)
        self.assertFalse([p for p in w.scheduled if p[1:3] == (route.tag, "HSM_AQR.410")])


class Restoration(Fixture):
    LEADERS = ("JER_king_moriset_discret", "JER_vivienne_discret", "JER_theodore_verany")
    NATIVE_BOUNDARIES = {"JER_state_of_aquileia", "JER_fight_for_freedom"}

    def ready(self, leader, holder="JER", human=True):
        camp = "republic" if leader == self.LEADERS[2] else "royal"
        route = ROUTES[2] if camp == "republic" else ROUTES[0]
        w = self.national(route)
        # The survival and custody of native characters are external saved-game facts.
        for c in w.countries.values():
            for char in self.LEADERS:
                c.characters.discard(char)
                c.roles.pop(char, None)
            c.party_leaders = {p: char for p, char in c.party_leaders.items() if char not in self.LEADERS}
        holder = route.tag if holder == "ROOT" else holder
        w.countries[holder].characters.add(leader)
        w.countries[holder].roles[leader] = copy.deepcopy(w.character_definitions[leader].all("country_leader"))
        w.set_players({"regional_player": route.tag, "unrelated_player": "FLO"} if human else {"unrelated_player": "FLO"})
        w.native_completion_boundaries = set(self.NATIVE_BOUNDARIES)
        old = w.countries["JER"]
        old.focus_tree = "aquileian_focus"
        opposite = "JER_state_of_aquileia" if camp == "republic" else "JER_fight_for_freedom"
        child = next(fid for fid, f in self.production.native_focuses.items()
                     if references(f, "prerequisite") == {opposite})
        old.focuses = {opposite, child, "JER_liberal_industry", "JER_army_reforms"}
        w.countries[route.tag].technology.add("fixture_researched_technology")
        return w, route, camp, child

    def test_native_focus_boundaries_are_explicit_and_vivienne_completion_cannot_select_the_shooting_event(self):
        p = self.production
        self.assertEqual(len([t for t in p.native_trees if t.startswith("aquileian_")]), 6)
        self.assertIn(P + "REC_postwar_housing", p.tree_members("aquileian_focus"))
        for fid in self.NATIVE_BOUNDARIES:
            focus = p.native_focuses[fid]
            reward = focus.get("completion_reward", [])
            self.assertEqual([n.value for n in reward if n.key == "add_political_power"], ["50"])
            self.assertTrue(any(n.key == "load_focus_tree" and n.get("tree") == "aquileian_focus" for n in walk(reward)))
            self.assertTrue(any(n.key == P + "start_regions" for n in walk(reward)))
        shooting = p.native_focuses["JER_to_kill_an_idea"]
        self.assertTrue(any(n.key == "country_event" and n.get("id") == "aquileia.49" for n in walk(shooting.get("select_effect", []))))
        self.assertFalse(any(n.key == "country_event" for n in walk(shooting.get("completion_reward", []))))
        for camp in ("royal", "republic"):
            nodes = list(walk(p.effects[P + "RESTORE_" + camp]))
            self.assertFalse(any(n.key in ("recruit_character", "create_country_leader") for n in nodes))
            uncomplete = next(n for n in nodes if n.key == "uncomplete_national_focus")
            self.assertEqual((uncomplete.get("uncomplete_children"), uncomplete.get("refund_political_power")), ("yes", "no"))
            self.assertLess(next(i for i, n in enumerate(nodes) if n.key == "set_country_flag" and n.value == P + "RESTORE_moriset"),
                            next(i for i, n in enumerate(nodes) if n.key == "transfer_state_to"))

    def test_surviving_native_leader_handover_preserves_economic_tree_and_foreign_countries(self):
        for leader in self.LEADERS:
            for holder in ("ROOT", "JER"):
                for human in (False, True):
                    with self.subTest(leader=leader, holder=holder, human=human):
                        w, route, camp, opposite_child = self.ready(leader, holder, human)
                        foreign = {sid: (s.owner, s.controller) for sid, s in w.states.items() if s.owner != route.tag}
                        owned = {sid for sid, s in w.states.items() if s.owner == route.tag}
                        others = {tag: copy.deepcopy(c) for tag, c in w.countries.items() if tag not in (route.tag, "JER")}
                        w.effect(P + "RESTORE_" + camp, route.tag)
                        jer = w.countries["JER"]
                        self.assertTrue(jer.exists)
                        self.assertFalse(w.countries[route.tag].exists)
                        self.assertEqual(jer.leader, leader)
                        self.assertEqual(jer.government, "democratic" if camp == "republic" else "neutrality")
                        self.assertEqual(jer.focus_tree, "aquileian_focus")
                        self.assertTrue({"JER_liberal_industry", "JER_army_reforms"} <= jer.focuses)
                        self.assertNotIn(opposite_child, jer.focuses)
                        root = "JER_fight_for_freedom" if camp == "republic" else "JER_state_of_aquileia"
                        self.assertIn(root, jer.focuses)
                        self.assertEqual([(tag, fid) for tag, fid, _ in w.native_boundary_calls], [("JER", root)])
                        self.assertEqual(w.annexations[-1], ("JER", route.tag, "yes"))
                        self.assertTrue(all(w.states[sid].owner == "JER" for sid in owned))
                        self.assertEqual({sid: (w.states[sid].owner, w.states[sid].controller) for sid in foreign}, foreign)
                        self.assertEqual({tag: w.countries[tag] for tag in others}, others)
                        self.assertIn("fixture_researched_technology", jer.technology)
                        self.assertEqual(w.player_countries.get("regional_player"), "JER" if human else None)
                        self.assertEqual(w.player_countries["unrelated_player"], "FLO")
                        self.assertFalse(any(p[2] == "aquileia.49" for p in w.scheduled))
                        if leader == self.LEADERS[1]:
                            self.assertIn("JER_to_kill_an_idea", jer.focuses)
                            self.assertNotIn(self.LEADERS[0], jer.characters)
                        before = w.snapshot()
                        w.effect(P + "RESTORE_" + camp, route.tag)
                        self.assertEqual(w.snapshot(), before)

    def test_established_same_camp_campaign_keeps_incumbent_tree_government_and_elections(self):
        # These roles are authored by native events, not present in character definitions.
        # Project only the recorded event result; do not claim to run elections or their other effects.
        role_events = {"JER_grand_cru": "aquileia.110", "JER_sugar_crepe": "aquileia.184",
                       "JER_thibault_devereux": "aquileia.194", "JER_victor_allard": "aquileia.194",
                       "JER_the_peoples_assemblee": "aquileia.207"}
        events = {n.get("id"): n for n in read(OPT.eaw / "events/Aquileia Events.txt") if n.key == "country_event"}
        for leader in (*self.LEADERS, "JER_grand_cru", "JER_cecile_gaudreau", "JER_leonard_rodier",
                       "JER_sugar_crepe", "JER_thibault_devereux", "JER_victor_allard", "JER_the_peoples_assemblee"):
            for elections in (False, True):
                with self.subTest(leader=leader, elections=elections):
                    royal = leader in self.LEADERS[:2]
                    w, route, camp, _ = self.ready(self.LEADERS[0] if royal else self.LEADERS[2])
                    jer = w.countries["JER"]
                    for char in self.LEADERS:
                        jer.characters.discard(char)
                    jer.characters.add(leader)
                    roles = copy.deepcopy(w.character_definitions[leader].all("country_leader"))
                    if leader in role_events:
                        grants = [n for n in walk(events[role_events[leader]].children)
                                  if n.key == "add_country_leader_role" and n.get("character") == leader]
                        self.assertEqual(len(grants), 1)
                        self.assertEqual(grants[0].get("promote_leader"), "yes")
                        roles = copy.deepcopy(grants[0].all("country_leader"))
                    self.assertTrue(roles, "No native definition or event-authored leader role")
                    jer.roles[leader] = roles
                    jer.government = w.ideology_groups[roles[0].get("ideology")]
                    jer.leader, jer.elections = leader, elections
                    root = "JER_state_of_aquileia" if royal else "JER_fight_for_freedom"
                    jer.focuses = {root, "JER_liberal_industry", "JER_army_reforms"}
                    jer.flags.add("JER_is_monarchist" if royal else "JER_democracy_established")
                    jer.focus_tree = "aquileian_focus_" + {"neutrality": "monarchist", "democratic": "democratic",
                                                          "fascism": "fascist", "communism": "communist"}[jer.government] + "_victory"
                    before = (jer.leader, jer.government, jer.elections, jer.focus_tree, set(jer.focuses))
                    w.effect(P + "RESTORE_" + camp, route.tag)
                    self.assertTrue(jer.exists)
                    self.assertFalse(w.countries[route.tag].exists)
                    self.assertEqual((jer.leader, jer.government, jer.elections, jer.focus_tree, jer.focuses), before)
                    self.assertIn(P + "RESTORE_preserve_national_campaign", w.countries[route.tag].flags)
                    self.assertFalse(w.native_boundary_calls, "A preserved national campaign must not replay its opening")
                    self.assertFalse(w.tree_loads, "The established national tree stays loaded")

    def test_restoration_never_resurrects_missing_leaders_or_steals_foreign_characters(self):
        for leader in self.LEADERS:
            for holder in (None, "FLO"):
                with self.subTest(leader=leader, holder=holder):
                    w, route, camp, _ = self.ready(leader)
                    w.countries["JER"].characters.discard(leader)
                    if holder:
                        w.countries[holder].characters.add(leader)
                    self.assertFalse(w.check(w.triggers[P + "RESTORE_" + camp + "_ready"], route.tag))
                    before = w.snapshot()
                    w.effect(P + "RESTORE_" + camp, route.tag)
                    self.assertEqual(w.snapshot(), before)

    def test_queued_and_open_restoration_rechecks_capital_control_peace_and_remaining_land(self):
        for leader in (self.LEADERS[0], self.LEADERS[2]):
            for invalid in ("capital_owner", "capital_controller", "partial_capital", "occupied_other_state",
                            "only_capital", "jer_returned", "war", "subject", "capitulated", "leader_gone"):
                with self.subTest(leader=leader, invalid=invalid):
                    w, route, camp, _ = self.ready(leader)
                    w.effect(P + "RESTORE_convene", route.tag)
                    w.advance_days(1)
                    c = w.countries[route.tag]
                    if invalid == "capital_owner":
                        w.states["377"].owner = "FLO"
                    elif invalid == "capital_controller":
                        w.states["377"].controller = "FLO"
                    elif invalid == "partial_capital":
                        w.states["377"].fully_controlled = False
                    elif invalid == "occupied_other_state":
                        next(s for s in w.states.values() if s.owner == route.tag and s.sid != "377").controller = "FLO"
                    elif invalid == "only_capital":
                        for s in w.states.values():
                            if s.owner == route.tag and s.sid != "377":
                                s.owner = s.controller = "FLO"
                    elif invalid == "jer_returned":
                        w.countries["JER"].exists = True
                    elif invalid == "subject":
                        c.subject, c.overlord = True, "FLO"
                    elif invalid == "leader_gone":
                        w.countries["JER"].characters.discard(leader)
                    else:
                        setattr(c, "war" if invalid == "war" else "capitulated", True)
                    self.assertFalse(w.deliver("HSM_AQR.480", route.tag))
                    before = w.snapshot()
                    w.click("HSM_AQR.480", "HSM_AQR.480.b" if camp == "royal" else "HSM_AQR.480.c", route.tag, stale=True)
                    self.assertEqual(w.snapshot(), before)

    def test_paid_reconstruction_progress_transfers_before_focus_completion_without_replaying_grants(self):
        for stages in range(4):
            with self.subTest(stages=stages):
                w, route, camp, _ = self.ready(self.LEADERS[0])
                c = w.countries[route.tag]
                w.complete(P + "invite_regions", route.tag)
                w.complete(P + "national_services", route.tag)
                c.political_power = 1000  # External accrual, not a script reward.
                focus_ids = [P + "REC_" + suffix for suffix in ("postwar_housing", "demobilisation", "food_networks")[:stages]]
                for fid in focus_ids:
                    w.complete(fid, route.tag)
                paid_flags = {f for f in c.flags if f.startswith(P + "REC_") and f.endswith("_done")}
                crisis_ideas = {i for i in c.ideas if i in {P + "REC_crisis", P + "REC_roofs", P + "REC_returning_workers"}}
                capacity = w.states["377"].capacity
                jer = w.countries["JER"]
                pp, xp, stability = jer.political_power, jer.army_experience, jer.stability
                w.effect(P + "RESTORE_" + camp, route.tag)
                self.assertTrue(paid_flags <= jer.flags)
                self.assertTrue(set(focus_ids) <= jer.focuses)
                self.assertEqual(jer.ideas & {P + "REC_crisis", P + "REC_roofs", P + "REC_returning_workers"}, crisis_ideas)
                self.assertEqual(w.states["377"].capacity, capacity)
                # Native root reward is the explicit boundary; these assertions cover REC replay only.
                self.assertEqual((jer.political_power, jer.army_experience, jer.stability), (pp, xp, stability))


class SeamlessTransition(Fixture):
    def offered(self, route, human_centre=False, human_region=True):
        w=self.world(route)
        players={'observer':'FLO'}
        if human_region: players['regional_player']=route.tag
        if human_centre: players['central_player']='JER'
        w.set_players(players)
        self.start(w); self.outcome(w,route.tag,route.camp); self.centre_outcome(w,route.camp)
        w.daily()
        w.advance_days(1)
        while any(p[1:3]==('JER','HSM_AQR.456') and p[0]<=w.day for p in w.scheduled):
            self.assertTrue(w.deliver('HSM_AQR.456','JER'))
        w.advance_days(1)
        self.assertTrue(w.deliver('HSM_AQR.30',route.tag))
        return w

    def test_all_fifteen_programmes_receive_a_direct_free_support_or_war_choice_before_ratification(self):
        for route in ROUTES:
            for support in (True,False):
                with self.subTest(route=route.key,support=support):
                    w=self.offered(route); c=w.countries[route.tag]
                    self.assertNotIn(P+'ratified',c.flags)
                    options=[o.get('name') for o in w.events['HSM_AQR.30'].all('option') if w.check(o.get('trigger',[]),route.tag)]
                    self.assertEqual(set(options),{'HSM_AQR.30.continue','HSM_AQR.30.lead'})
                    c.political_power=-20
                    pp,stability=c.political_power,c.stability
                    jer=copy.deepcopy(w.countries['JER'])
                    name='HSM_AQR.30.continue' if support else 'HSM_AQR.30.lead'
                    w.click('HSM_AQR.30',name,route.tag,sender='JER')
                    if support:
                        self.assertFalse(c.exists)
                        self.assertEqual(w.player_countries['regional_player'],'JER')
                        self.assertEqual(w.countries['JER'].leader,jer.leader)
                        self.assertEqual(w.countries['JER'].focuses,jer.focuses)
                    else:
                        self.assertIn('JER',c.wars)
                        self.assertFalse(c.subject)
                        self.assertEqual((c.political_power,c.stability),(pp,stability))
                        self.assertIn(P+'national_mandate',c.focuses)
                    before=w.snapshot()
                    w.click('HSM_AQR.30',name,route.tag,sender='JER',stale=True)
                    self.assertEqual(before,w.snapshot())

    def test_refusal_does_not_block_regional_government_or_later_campaign(self):
        for route in ROUTES:
            w=self.offered(route)
            w.click('HSM_AQR.30','HSM_AQR.30.lead',route.tag,sender='JER')
            self.select_native(w,route)
            for stage in ('pledge','organise','settle'): w.complete(P+route.key+'_'+stage,route.tag)
            eid='HSM_AQR.'+str(100+ROUTES.index(route))
            w.advance_days(1);self.assertTrue(w.deliver(eid,route.tag));w.click(eid,eid+'.a',route.tag)
            self.assertEqual(w.countries[route.tag].government,route.party)
            w.complete(P+'CAM_'+route.key+'_m1',route.tag)

    def test_human_centre_is_never_taken_over(self):
        for route in (ROUTES[0],ROUTES[6],ROUTES[8],ROUTES[12]):
            w=self.offered(route,human_centre=True)
            self.assertFalse(w.check(parse('HSM_AQR_can_continue_at_centre = yes'),route.tag))
            w.click('HSM_AQR.30','HSM_AQR.30.game_over',route.tag,sender='JER')
            self.assertEqual(w.player_countries['central_player'],'JER')
            self.assertNotEqual(w.player_countries.get('regional_player'),'JER')
            self.assertFalse(w.countries[route.tag].exists)

    def test_removed_approval_protocol_is_inert_and_has_no_visible_entry(self):
        for fid in (P+'central_convention',P+'national_countermandate'):
            self.assertNotIn(fid,self.production.focuses)
        self.assertNotIn(P+'reconvene_congress',self.production.decisions)
        for number in range(450,456):
            event=self.production.events['HSM_AQR.'+str(number)]
            self.assertEqual(event.get('hidden'),'yes')
            self.assertFalse(event.all('option'))
            self.assertEqual(event.get('trigger'),parse('always = no'))


class Reconstruction(Fixture):
    R = P + "REC_"
    PERIPHERY = ("POM", "FLO", "AET", "FEZ", "HEL")
    STAGES = (("postwar_housing", 75, "roofs"), ("demobilisation", 50, "returning_workers"), ("food_networks", 50, None))

    def ready(self, native=True, united=False):
        if native:
            w = copy.deepcopy(self.template)
            tag = "JER"
            self.centre_outcome(w, "royal")
            w.countries[tag].focuses.add("JER_state_of_aquileia")
            w.global_flags.add("JER_revolution_ended")
            w.root = tag
            w.daily()
        else:
            tag = ROUTES[1].tag
            w = self.national()
            w.complete(P + "invite_regions", tag)
            w.complete(P + "national_services", tag)
        if united:
            if native:
                # Explicit external native union outcome; no claim to execute its event chain.
                for state in w.states.values():
                    if state.owner in REGIONS:
                        state.owner = state.controller = tag
                for region in REGIONS:
                    w.countries[region].exists = False
            else:
                w.advance_days(2)
                for region in REGIONS:
                    if region != tag:
                        self.assertTrue(w.deliver("HSM_AQR.20", region))
                        w.click("HSM_AQR.20", "HSM_AQR.20.b", region, sender=tag)
                for suffix in ("national_schools", "national_army", "national_recovery", "national_settlement"):
                    w.complete(P + suffix, tag)
        return w, tag

    def conference(self, native=True):
        w, tag = self.ready(native, united=True)
        w.countries[tag].political_power = 1000
        for suffix, _, _ in self.STAGES:
            w.complete(self.R + suffix, tag)
        w.complete(self.R + "peripheral_conference", tag)
        w.advance_days(1)
        return w, tag

    def test_native_and_regional_crises_have_exact_paid_stages_and_no_repeated_rewards(self):
        for native in (False, True):
            with self.subTest(native=native):
                w, tag = self.ready(native)
                c = w.countries[tag]
                crisis_ids = {self.R + suffix for suffix in ("crisis", "roofs", "returning_workers")}
                self.assertEqual(c.ideas & crisis_ids, {self.R + "crisis"})
                initial = w.states["377"].capacity, c.army_experience, c.stability
                for suffix, price, next_idea in self.STAGES:
                    for balance in (0, price - .001):
                        c.political_power = balance
                        self.assertFalse(w.available(self.R + suffix, tag))
                        before = w.snapshot()
                        w.effect(self.R + suffix, tag)
                        self.assertEqual(w.snapshot(), before)
                    c.political_power = price
                    w.complete(self.R + suffix, tag)
                    self.assertEqual(c.political_power, 0)
                    self.assertEqual(c.ideas & crisis_ids, {self.R + next_idea} if next_idea else set())
                    self.assertIn(self.R + suffix + "_done", c.flags)
                    c.political_power = 1000
                    before = w.snapshot()
                    w.effect(self.R + suffix, tag)
                    w.effect(P + "begin_reconstruction", tag)
                    self.assertEqual(w.snapshot(), before)
                self.assertEqual((w.states["377"].capacity, c.army_experience, c.stability),
                                 (initial[0] + 2, initial[1] + 15, initial[2] + .05))
                self.assertFalse(w.available(self.R + "peripheral_conference", tag), "Reconstruction alone is not unification")

    def test_both_national_hosts_offer_only_consensual_bounded_accession(self):
        for native in (False, True):
            ready, host = self.conference(native)
            packets = [p for p in ready.scheduled if p[2] == "HSM_AQR.501"]
            self.assertEqual({p[1] for p in packets}, set(self.PERIPHERY))
            self.assertEqual(len(packets), 5)
            self.assertTrue(all(p[3] == host for p in packets))
            for recipient in self.PERIPHERY:
                for own_subject in (False, True):
                    with self.subTest(host=host, recipient=recipient, own_subject=own_subject):
                        w = copy.deepcopy(ready)
                        if own_subject:
                            w.countries[recipient].subject, w.countries[recipient].overlord = True, host
                        self.assertTrue(w.deliver("HSM_AQR.501", recipient))
                        self.assertEqual(w.events["HSM_AQR.501"].all("option")[0].get("name"), "HSM_AQR.501.a")
                        before = {sid: (s.owner, s.controller) for sid, s in w.states.items()}
                        prior_annexes = list(w.annexations)
                        w.click("HSM_AQR.501", "HSM_AQR.501.b", recipient, sender=host)
                        self.assertEqual(w.annexations, prior_annexes + [(host, recipient, "yes")])
                        self.assertTrue(all((s.owner, s.controller) == ((host, host) if before[sid][0] == recipient else before[sid])
                                            for sid, s in w.states.items()))
                        after = w.snapshot()
                        w.click("HSM_AQR.501", "HSM_AQR.501.b", recipient, sender=host, stale=True)
                        self.assertEqual(w.snapshot(), after)

    def test_stale_peripheral_offers_recheck_both_governments_subjects_and_reciprocal_control(self):
        ready, host = self.conference()
        for changed in ("foreign_subject", "foreign_faction", "own_subject", "occupied", "foreign_controlled", "war", "capitulation", "host_capital", "host_unification", "expiry", "wrong_sender"):
            with self.subTest(changed=changed):
                w, recipient = copy.deepcopy(ready), "FLO"
                c = w.countries[recipient]
                sender = host
                if changed == "foreign_subject": c.subject, c.overlord = True, "GRI"
                elif changed == "foreign_faction": c.faction = "foreign_alliance"
                elif changed == "own_subject": w.countries["AET"].subject, w.countries["AET"].overlord = True, recipient
                elif changed == "occupied": next(s for s in w.states.values() if s.owner == recipient).controller = "GRI"
                elif changed == "foreign_controlled": next(s for s in w.states.values() if s.owner == "GRI").controller = recipient
                elif changed == "war": c.war = True
                elif changed == "capitulation": c.capitulated = True
                elif changed == "host_capital": w.states["377"].controller = "GRI"
                elif changed == "host_unification": w.arrays["JRR.original_cores"][0].controller = "GRI"
                elif changed == "expiry": w.advance_days(60)
                else: sender = "JEB"
                if changed != "wrong_sender":
                    self.assertFalse(w.deliver("HSM_AQR.501", recipient))
                before = w.snapshot()
                w.click("HSM_AQR.501", "HSM_AQR.501.b", recipient, sender=sender, stale=True)
                self.assertEqual(w.snapshot(), before)

    def test_recall_renews_only_unanswered_or_previously_ineligible_invites_and_respects_refusal(self):
        w, host = self.ready(True, united=True)
        w.countries[host].political_power = 1000
        for suffix, _, _ in self.STAGES:
            w.complete(self.R + suffix, host)
        w.countries["AET"].war = True
        w.complete(self.R + "peripheral_conference", host)
        self.assertNotIn(self.R + "sent_AET", w.countries[host].flags)
        w.advance_days(1)
        self.assertTrue(w.deliver("HSM_AQR.501", "FLO"))
        w.click("HSM_AQR.501", "HSM_AQR.501.a", "FLO", sender=host)
        self.assertFalse(w.annexations or w.countries[host].goals)
        w.countries["AET"].war = False
        before = len(w.scheduled)
        w.decision(self.R + "recall_conference", host)
        self.assertEqual(len(w.scheduled), before + 1)
        after = w.snapshot()
        w.effect(self.R + "send_invitations", host)
        self.assertEqual(w.snapshot(), after)
        w.advance_days(60)
        before = len(w.scheduled)
        w.decision(self.R + "recall_conference", host)
        renewed = w.scheduled[before:]
        self.assertEqual({p[1] for p in renewed}, set(self.PERIPHERY) - {"FLO"})
        self.assertTrue(all(p[3] == host for p in renewed))

    def test_refusal_never_declares_war_and_claim_requires_independence_and_clear_diplomacy(self):
        ready, host = self.conference()
        self.assertTrue(ready.deliver("HSM_AQR.501", "FLO"))
        ready.click("HSM_AQR.501", "HSM_AQR.501.a", "FLO", sender=host)
        ready.advance_days(1)
        self.assertTrue(ready.deliver("HSM_AQR.503", host))
        self.assertFalse(ready.countries[host].goals or ready.countries[host].war)
        for changed in ("subject", "faction", "pact", "truce", "guarantee", "war", "capitulation"):
            with self.subTest(changed=changed):
                w = copy.deepcopy(ready)
                c, target = w.countries[host], w.countries["FLO"]
                if changed == "subject": target.subject, target.overlord = True, "GRI"
                elif changed == "faction": target.faction = c.faction = "same_alliance"
                elif changed == "pact": c.naps.add("FLO")
                elif changed == "truce": c.truces.add("FLO")
                elif changed == "guarantee": target.guarantors.add(host)
                elif changed == "war": target.war = True
                else: target.capitulated = True
                before = w.snapshot()
                w.click("HSM_AQR.503", "HSM_AQR.503.b", host, sender="FLO", stale=True)
                self.assertEqual(w.snapshot(), before)
        ready.click("HSM_AQR.503", "HSM_AQR.503.b", host, sender="FLO")
        self.assertEqual(ready.countries[host].goals, {("annex_everything", "FLO")})
        self.assertFalse(ready.countries[host].war)
        after = ready.snapshot()
        ready.click("HSM_AQR.503", "HSM_AQR.503.b", host, sender="FLO", stale=True)
        self.assertEqual(ready.snapshot(), after)

    def test_articles_core_only_later_owned_fully_controlled_original_peripheral_states(self):
        w, host = self.conference()
        w.complete(self.R + "peripheral_articles", host)
        eligible = w.arrays["FLO.original_cores"][0]
        occupied = w.arrays["AET.original_cores"][0]
        foreign = w.arrays["FEZ.original_cores"][0]
        outside = next(s for s in w.states.values() if s.owner == "GRI" and not s.cores & set(self.PERIPHERY))
        for state in (eligible, occupied, outside):
            state.owner = state.controller = host  # Explicit later peace-conference acquisition.
            state.cores.discard(host)
        occupied.controller = "GRI"
        foreign.cores.discard(host)
        before = {sid: (s.owner, s.controller) for sid, s in w.states.items()}
        w.countries[host].war = True
        w.daily()
        self.assertNotIn(host, eligible.cores)
        w.countries[host].war = False
        w.daily()
        self.assertIn(host, eligible.cores)
        self.assertTrue(all(host not in s.cores for s in (occupied, foreign, outside)))
        self.assertEqual({sid: (s.owner, s.controller) for sid, s in w.states.items()}, before)
        after = w.snapshot()
        w.effect(self.R + "integrate_owned", host)
        self.assertEqual(w.snapshot(), after)


class Routes(Fixture):
    def test_all_fifteen_routes_install_their_actual_government_for_both_constitutions(self):
        for route in ROUTES:
            for choice in ("a", "b"):
                with self.subTest(route=route.key, choice=choice):
                    w, event_id = self.assembly(route)
                    c = w.countries[route.tag]
                    self.assertEqual(c.political_power, 135)
                    w.click(event_id, event_id + "." + choice, route.tag)
                    self.assertEqual(c.political_power, 85)
                    self.assertEqual((c.leader, c.government), (route.character, route.party))
                    self.assertEqual(c.elections, route.party == "democratic")
                    self.assertEqual(c.party_names[route.party], (P + route.key + "_party",) * 2)
                    self.assertEqual(c.popularities, {party: 55 if party == route.party else 15
                                                     for party in ("neutrality", "democratic", "communism", "fascism")})
                    self.assertIn(route.character, c.characters)
                    self.assertTrue({P + "ratified", P + "ratified_" + route.key,
                                     P + "constitution_" + choice} <= c.flags)
                    self.assertNotIn(P + "constitution_" + ("b" if choice == "a" else "a"), c.flags)
                    before = w.snapshot()
                    w.click(event_id, event_id + "." + choice, route.tag, stale=True)
                    w.effect(P + "ratify_" + route.key + "_" + choice, route.tag)
                    w.effect(P + "finish_" + route.key + "_organise", route.tag)
                    self.assertEqual(w.snapshot(), before, "Repeated settlement/organisation must not pay again")

    def test_all_route_payments_reject_fractional_shortfall_and_charge_exactly_once(self):
        for route in ROUTES:
            ready, event_id = self.assembly(route)
            for choice in ("a", "b"):
                for balance in (49.5, 50, 50.5):
                    with self.subTest(route=route.key, choice=choice, balance=balance):
                        w = copy.deepcopy(ready)
                        c = w.countries[route.tag]
                        c.political_power = balance
                        self.assertEqual(w.check(w.triggers[P + "can_ratify_" + route.key], route.tag), balance >= 50)
                        before = w.snapshot()
                        w.click(event_id, event_id + "." + choice, route.tag, stale=True)
                        if balance < 50:
                            self.assertEqual(w.snapshot(), before)
                        else:
                            self.assertEqual(c.political_power, balance - 50)
                            paid = w.snapshot()
                            w.effect(P + "ratify_" + route.key + "_" + choice, route.tag)
                            self.assertEqual(w.snapshot(), paid)

    def test_deferral_is_free_at_every_balance_and_real_decision_reopens_the_packet(self):
        for route in ROUTES:
            ready, event_id = self.assembly(route)
            for balance in (0, 49.5, 50, 500):
                with self.subTest(route=route.key, balance=balance):
                    w = copy.deepcopy(ready)
                    c = w.countries[route.tag]
                    c.political_power = balance
                    before = w.snapshot()
                    w.click(event_id, P + "defer", route.tag)
                    self.assertEqual(w.snapshot(), before)
                    decision = P + "ratify_again_" + route.key
                    self.assertEqual(w.check(w.decisions[decision].get("available", []), route.tag), balance >= 50)
                    c.political_power = 50  # External PP accrual, not a script reward.
                    w.decision(decision, route.tag)
                    self.assertEqual(len([p for p in w.scheduled if p[1:3] == (route.tag, event_id)]), 1)
                    w.advance_days(1)
                    self.assertTrue(w.deliver(event_id, route.tag))
                    w.click(event_id, event_id + ".b", route.tag)
                    self.assertEqual(c.political_power, 0)
                    self.assertEqual(c.leader, route.character)
                    self.assertFalse(w.check(w.decisions[decision].get("available", []), route.tag))

    def test_absent_native_character_cannot_consume_pp_or_ratify_a_phantom_government(self):
        for route in (r for r in ROUTES if not r.character.startswith(P)):
            ready, event_id = self.assembly(route)
            for choice in ("a", "b"):
                with self.subTest(route=route.key, choice=choice):
                    w = copy.deepcopy(ready)
                    c = w.countries[route.tag]
                    c.characters.remove(route.character)
                    if c.leader == route.character:
                        c.leader = "fixture_successor"
                    before = w.snapshot()
                    self.assertFalse(w.check(w.triggers[P + "can_ratify_" + route.key], route.tag))
                    w.click(event_id, event_id + "." + choice, route.tag, stale=True)
                    self.assertEqual(w.snapshot(), before)

    def test_local_outcome_outranks_global_result_and_peace_is_required_for_settlement(self):
        for route in ROUTES:
            organised = self.organised(route)
            rival = "rev" if route.camp == "royal" else "royal"
            for local, camp, global_camp, expected in (
                    (True, route.camp, rival, True), (True, rival, route.camp, False),
                    (False, route.camp, route.camp, True), (False, rival, rival, False)):
                with self.subTest(route=route.key, local=local, camp=camp, global_camp=global_camp):
                    w = copy.deepcopy(organised)
                    self.outcome(w, route.tag, camp, local=local, global_camp=global_camp)
                    focus = P + route.key + "_settle"
                    self.assertEqual(w.available(focus, route.tag), expected)
                    w.countries[route.tag].war = True
                    self.assertFalse(w.available(focus, route.tag))

    def test_corrected_native_outcome_clears_stale_mandate_without_replaying_old_grants(self):
        # Corrected historical save predating the snapshot feature, not a second revolution.
        for route in ROUTES:
            with self.subTest(route=route.key):
                w = self.organised(route)
                self.legacy_without_native_snapshot(w, route.tag)
                c = w.countries[route.tag]
                before_pp = c.political_power
                winner = "rev" if route.camp == "royal" else "royal"
                replacement = next(r for r in ROUTES if r.tag == route.tag and r.camp == winner)
                # Corrected legacy political inputs include an actual native
                # programme; a winning camp alone no longer creates one.
                c.flags.add(replacement.preparation)
                if replacement.key in NATIVE_MOVEMENTS:
                    c.variables[NATIVE_MOVEMENTS[replacement.key]] = 60
                self.outcome(w, route.tag, winner)
                w.daily()
                self.assertNotIn(P + "route_" + route.key, c.flags)
                self.assertNotIn(P + "ratified", c.flags)
                self.assertIn(P + "finish_" + route.key + "_organise_done", c.flags)
                w.effect(P + "finish_" + route.key + "_organise", route.tag)
                self.assertEqual(c.political_power, before_pp)
                self.select_native(w, replacement)
                w.complete(P + replacement.key + "_pledge", route.tag)
                w.complete(P + replacement.key + "_organise", route.tag)
                self.assertIn(P + "route_" + replacement.key, c.flags)
                self.assertEqual(c.political_power, before_pp + 35)
                repeat = w.snapshot()
                w.effect(P + "finish_" + replacement.key + "_organise", route.tag)
                self.assertEqual(w.snapshot(), repeat)

    def test_stale_paid_choices_and_delivery_reject_war_capitulation_and_foreign_subjecthood(self):
        for route in ROUTES:
            ready, event_id = self.assembly(route)
            for invalid in ("war", "capitulated", "foreign_subject", "annexed", "lost_contest"):
                with self.subTest(route=route.key, invalid=invalid):
                    w = copy.deepcopy(ready)
                    c = w.countries[route.tag]
                    # This packet was produced by a genuine settlement focus.
                    w.effect(P + "finish_" + route.key + "_settle", route.tag)
                    w.advance_days(1)
                    if invalid == "war":
                        c.war = True
                    elif invalid == "capitulated":
                        c.capitulated = True
                    elif invalid == "foreign_subject":
                        c.subject, c.overlord = True, "FLO"
                    elif invalid == "annexed":
                        c.exists = False
                    else:
                        self.outcome(w, route.tag, "rev" if route.camp == "royal" else "royal")
                    self.assertFalse(w.deliver(event_id, route.tag))
                    before = w.snapshot()
                    for choice in ("a", "b"):
                        w.click(event_id, event_id + "." + choice, route.tag, stale=True)
                    self.assertEqual(w.snapshot(), before)

    def test_stale_organisation_reward_rechecks_actual_local_administration(self):
        for route in ROUTES:
            with self.subTest(route=route.key):
                w = self.world(route)
                self.start(w)
                self.outcome(w, route.tag, route.camp)
                w.daily()
                self.select_native(w, route)
                w.complete(P + route.key + "_pledge", route.tag)
                c = w.countries[route.tag]
                c.subject, c.overlord = True, "FLO"
                self.assertFalse(w.available(P + route.key + "_organise", route.tag))
                before = w.snapshot()
                w.effect(P + "finish_" + route.key + "_organise", route.tag)
                self.assertEqual(w.snapshot(), before)


class NationalIdentity(Fixture):
    REPUBLICS = {"JEB_moderate", "JEB_cocardiers", "JRR_colette", "JFT_communes",
                 "JFT_enfants", "JFT_fja", "VIN_abc", "VIN_chevaliers", "VIN_sis"}

    def expected_tag(self, route):
        return "JER_REPUBLIC" if route.key in self.REPUBLICS else "HSM_AQR_KINGDOM"

    def test_all_programmes_keep_their_government_and_get_the_matching_national_identity(self):
        for route in ROUTES:
            for choice in ("a", "b"):
                with self.subTest(route=route.key, constitution=choice):
                    w = self.national(route, choice, proclaim=False)
                    c = w.countries[route.tag]
                    identity = (c.leader, c.government, c.elections, copy.deepcopy(c.party_leaders))
                    w.complete(P + "proclaim", route.tag)
                    self.assertEqual(c.cosmetic, self.expected_tag(route))
                    self.assertEqual((c.leader, c.government, c.elections, c.party_leaders), identity)
                    self.assertIn("JER_formed", c.flags, "Retain native national integration compatibility")

    def test_old_formed_saves_are_repaired_without_replaying_proclamation_or_changing_the_government(self):
        for route in ROUTES:
            ready = self.national(route)
            for old_tag in ("JER_formed", "JER_JFT_formed", "JER_REPUBLIC", "HSM_AQR_KINGDOM"):
                with self.subTest(route=route.key, old_tag=old_tag):
                    w = copy.deepcopy(ready)
                    w.countries[route.tag].cosmetic = old_tag
                    expected = copy.deepcopy(w.snapshot())
                    expected[0][route.tag].cosmetic = self.expected_tag(route)
                    w.effect(P + "refresh_national_identity", route.tag)
                    self.assertEqual(w.snapshot(), expected, "Only the national cosmetic may change")
                    w.effect(P + "refresh_national_identity", route.tag)
                    self.assertEqual(w.snapshot(), expected)
            ready.countries[route.tag].cosmetic = "JER_formed"
            ready.daily()
            self.assertEqual(ready.countries[route.tag].cosmetic, self.expected_tag(route))

    def test_repair_preserves_later_cosmetics_and_requires_a_sovereign_ratified_nation(self):
        route = next(r for r in ROUTES if r.key == "JFT_communes")
        ready = self.national(route)
        for invalid in ("no_nation", "not_ratified", "subject", "lost_capital", "imperial", "puppet_cosmetic"):
            with self.subTest(invalid=invalid):
                w = copy.deepcopy(ready)
                c = w.countries[route.tag]
                c.cosmetic = "JER_JFT_formed"
                if invalid == "no_nation": c.flags.discard(P + "nation")
                elif invalid == "not_ratified": c.flags.discard(P + "ratified")
                elif invalid == "subject": c.subject, c.overlord = True, "FLO"
                elif invalid == "lost_capital": w.states["377"].controller = "FLO"
                else: c.cosmetic = "GRI_formed" if invalid == "imperial" else "foreign_puppet_fixture"
                before = w.snapshot()
                w.effect(P + "refresh_national_identity", route.tag)
                self.assertEqual(w.snapshot(), before)

    def test_native_republic_has_republican_names_flags_and_a_map_colour_for_every_ideology(self):
        for language in ("english", "russian"):
            source = (OPT.eaw / f"localisation/{language}/country_JER_l_{language}.yml").read_text(encoding="utf-8-sig")
            for ideology in ("neutrality", "democratic", "communism", "fascism"):
                for suffix in ("", "_DEF", "_ADJ"):
                    key = "JER_REPUBLIC_" + ideology + suffix
                    found = re.findall(r'^\s*' + re.escape(key) + r':\d*\s+"([^"\n]+)"', source, re.M)
                    self.assertEqual(len(found), 1, key)
                    self.assertNotRegex(found[0].lower(), r'kingdom|королевств')
                    if suffix != "_ADJ":
                        self.assertRegex(found[0].lower(), r'republic|республик')
                for size in ("", "medium", "small"):
                    flag = OPT.eaw / "gfx/flags" / size / ("JER_REPUBLIC_" + ideology + ".tga")
                    self.assertGreater(flag.stat().st_size, 18, str(flag))
        colours = (OPT.eaw / "common/countries/cosmetic.txt").read_text(encoding="utf-8-sig")
        self.assertRegex(colours, r'JER_REPUBLIC\s*=\s*\{\s*color\s*=\s*rgb\s*\{\s*84\s+104\s+181\s*\}')

    def test_monarchies_including_harmonic_coalitions_have_royal_names_flags_and_colour(self):
        expected = {"english": ("Kingdom of Aquileia", "the Kingdom of Aquileia", "Aquileian"),
                    "russian": ("Королевство Аквелия", "Королевство Аквелия", "Аквелийск")}
        for language, names in expected.items():
            source = (MOD / f"localisation/{language}/HSM_AQR_regions_l_{language}.yml").read_text(encoding="utf-8-sig")
            for ideology in ("neutrality", "democratic", "communism", "fascism"):
                for suffix, name in zip(("", "_DEF", "_ADJ"), names):
                    key = "HSM_AQR_KINGDOM_" + ideology + suffix
                    found = re.findall(r'^\s*' + re.escape(key) + r':\d*\s+"([^"\n]+)"', source, re.M)
                    self.assertEqual(found, [name], key)
        for ideology in ("neutrality", "democratic", "communism", "fascism"):
            for size in ("", "medium", "small"):
                folder = Path("gfx/flags") / size
                actual = MOD / folder / ("HSM_AQR_KINGDOM_" + ideology + ".tga")
                self.assertEqual(actual.read_bytes(), (OPT.eaw / folder / "JER_neutrality.tga").read_bytes())
        colours = (MOD / "common/countries/cosmetic.txt").read_text(encoding="utf-8-sig")
        colours = re.sub(r'#[^\n]*', '', colours).strip()
        self.assertEqual(len(re.findall(r'\bHSM_AQR_KINGDOM\s*=', colours)), 1)
        self.assertIsNotNone(re.search(
            r'HSM_AQR_KINGDOM\s*=\s*\{\s*color\s*=\s*rgb\s*\{\s*152\s+60\s+85\s*\}'
            r'\s*color_ui\s*=\s*rgb\s*\{\s*152\s+60\s+85\s*\}\s*\}', colours))


class National(Fixture):
    def test_every_route_reaches_its_constitutional_epilogue_only_after_real_unification(self):
        for route in ROUTES:
            for choice in ("a", "b"):
                with self.subTest(route=route.key, choice=choice):
                    w = self.national(route, choice)
                    c = w.countries[route.tag]
                    self.assertIn("JER_formed", c.flags)
                    self.assertEqual("JER_JFT_formed" in c.flags, route.tag == "JFT")
                    self.assertNotIn("uniting_aquileia_proper", c.flags)
                    w.complete(P + "invite_regions", route.tag)
                    w.complete(P + "national_services", route.tag)
                    w.complete(P + "national_schools", route.tag)
                    self.assertFalse(w.available(P + "national_recovery", route.tag), "Both national branches are required")
                    w.complete(P + "national_army", route.tag)
                    w.complete(P + "national_recovery", route.tag)
                    self.assertFalse(w.available(P + "national_settlement", route.tag), "A proclamation is not full unification")
                    before = w.snapshot()
                    w.effect(P + "national_settlement", route.tag)
                    self.assertEqual(w.snapshot(), before)
                    self.assertNotIn("uniting_aquileia_proper", c.flags, "Divided regions cannot unlock native expansion")
                    w.advance_days(2)
                    for tag in REGIONS:
                        if tag != route.tag:
                            self.assertTrue(w.deliver("HSM_AQR.20", tag))
                            w.click("HSM_AQR.20", "HSM_AQR.20.b", tag, sender=route.tag)
                    self.assertTrue(w.available(P + "national_settlement", route.tag))
                    self.assertNotIn("uniting_aquileia_proper", c.flags, "Unification still needs its settlement focus")
                    # An occupied single original core must still block the finale.
                    core = w.arrays["JRR.original_cores"][-1]
                    controller = core.controller
                    core.controller = "FLO"
                    self.assertFalse(w.available(P + "national_settlement", route.tag))
                    before = w.snapshot()
                    w.effect(P + "national_settlement", route.tag)
                    self.assertEqual(w.snapshot(), before)
                    self.assertNotIn("uniting_aquileia_proper", c.flags)
                    core.controller = controller
                    w.countries[route.tag].war = True
                    self.assertFalse(w.available(P + "national_settlement", route.tag))
                    before = w.snapshot()
                    w.effect(P + "national_settlement", route.tag)
                    self.assertEqual(w.snapshot(), before)
                    self.assertNotIn("uniting_aquileia_proper", c.flags)
                    w.countries[route.tag].war = False
                    w.complete(P + "national_settlement", route.tag)
                    self.assertIn("uniting_aquileia_proper", c.flags, "Completed actual unification unlocks native expansion")
                    event_id = "HSM_AQR." + str(200 + ROUTES.index(route))
                    matching = [p for p in w.scheduled if p[2].startswith("HSM_AQR.2") and p[2] not in ("HSM_AQR.20", "HSM_AQR.21", "HSM_AQR.22")]
                    self.assertEqual([p[2] for p in matching], [event_id])
                    w.advance_days(1)
                    self.assertTrue(w.deliver(event_id, route.tag))
                    descriptions = [d.get("text") for d in w.events[event_id].all("desc")
                                    if w.check(d.get("trigger", []), route.tag)]
                    self.assertEqual(descriptions, [event_id + "." + choice + "_desc"])
                    self.assertEqual(w.countries[route.tag].focus_tree, P + "regional_tree")
                    settled = w.snapshot()
                    w.effect(P + "national_settlement", route.tag)
                    self.assertEqual(w.snapshot(), settled)

    def test_loyal_and_independent_reforms_use_native_development_without_repeat_rewards(self):
        for tag in REGIONS:
            route = next(r for r in ROUTES if r.tag == tag)
            for independent in (False, True):
                with self.subTest(tag=tag, independent=independent):
                    w = self.ratified(route)
                    c = w.countries[tag]
                    if independent:
                        c.subject, c.overlord = False, ""
                    c.ideas = {"poverty", "lack_of_scientists2", "fixture_unrelated_idea"}
                    starting_pp = c.political_power
                    w.complete(P + "regional_articles", tag)
                    self.assertEqual(c.political_power, starting_pp + 75, "Native preview must not duplicate the actual reward")
                    for focus in ("provincial_schools", "local_credit"):
                        w.complete(P + focus, tag)
                    self.assertEqual(c.ideas, {"poverty1", "lack_of_scientists3", "fixture_unrelated_idea"})
                    self.assertFalse(w.available(P + "common_market", tag), "All three regional branches are required")
                    w.complete(P + "supply_contracts", tag)
                    self.assertEqual(c.army_experience, 15)
                    before_factories = sum(s.buildings.get("industrial_complex", 0) for s in w.states.values())
                    w.complete(P + "common_market", tag)
                    self.assertEqual(sum(s.buildings.get("industrial_complex", 0) for s in w.states.values()), before_factories + 1)
                    before = w.snapshot()
                    for effect in ("regional_articles", "provincial_schools", "local_credit", "supply_contracts", "common_market"):
                        w.effect(P + effect, tag)
                    self.assertEqual(w.snapshot(), before)

    def test_national_challenge_needs_real_rupture_and_respects_faction_pact_and_truce(self):
        route = ROUTES[0]
        w = self.ratified(route)
        w.complete(P + "regional_articles", route.tag)
        self.assertFalse(w.available(P + "national_mandate", route.tag))
        c = w.countries[route.tag]
        self.assertIn(P + "former_subject", c.flags, "Post-revolution maintenance observed native JER subjecthood")
        c.subject, c.overlord, c.faction = False, "", ""
        self.assertTrue(w.available(P + "national_mandate", route.tag))
        for relation in ("faction", "nap", "truce"):
            with self.subTest(relation=relation):
                blocked = copy.deepcopy(w)
                bc = blocked.countries[route.tag]
                if relation == "faction":
                    bc.faction = blocked.countries["JER"].faction
                else:
                    (bc.naps if relation == "nap" else bc.truces).add("JER")
                self.assertFalse(blocked.available(P + "national_mandate", route.tag))
                before = blocked.snapshot()
                blocked.effect(P + "national_mandate", route.tag)
                self.assertEqual(blocked.snapshot(), before)
        w.complete(P + "national_mandate", route.tag)
        self.assertEqual(c.goals, {("annex_everything", "JER")})

    def test_proclamation_rechecks_capital_old_centre_peace_and_sovereignty_without_annexing_regions(self):
        for route in (ROUTES[1], ROUTES[7]):
            ready = self.national(route, proclaim=False)
            self.assertFalse({"JER_formed", "JER_JFT_formed", "uniting_aquileia_proper"}
                             & ready.countries[route.tag].flags)
            for invalid in ("old_centre", "subject", "war", "capital_owner", "capital_controller", "partial_control"):
                with self.subTest(route=route.key, invalid=invalid):
                    w = copy.deepcopy(ready)
                    c = w.countries[route.tag]
                    if invalid == "old_centre":
                        w.countries["JER"].exists = True
                    elif invalid == "subject":
                        c.subject, c.overlord = True, "FLO"
                    elif invalid == "war":
                        c.war = True
                    elif invalid == "capital_owner":
                        w.states["377"].owner = "FLO"
                    elif invalid == "capital_controller":
                        w.states["377"].controller = "FLO"
                    else:
                        w.states["377"].fully_controlled = False
                    self.assertFalse(w.available(P + "proclaim", route.tag))
                    before = w.snapshot()
                    w.effect(P + "proclaim", route.tag)
                    self.assertEqual(w.snapshot(), before)
            w = copy.deepcopy(ready)
            countries_before = {t: c.exists for t, c in w.countries.items()}
            ownership_before = {sid: (s.owner, s.controller) for sid, s in w.states.items()}
            pp = w.countries[route.tag].political_power
            w.complete(P + "proclaim", route.tag)
            self.assertEqual(w.countries[route.tag].cosmetic, "HSM_AQR_KINGDOM")
            self.assertIn("JER_formed", w.countries[route.tag].flags)
            self.assertEqual("JER_JFT_formed" in w.countries[route.tag].flags, route.tag == "JFT")
            self.assertNotIn("uniting_aquileia_proper", w.countries[route.tag].flags)
            self.assertEqual(w.countries[route.tag].capital, "377")
            self.assertEqual(w.countries[route.tag].political_power, pp + 100)
            self.assertEqual(countries_before, {t: c.exists for t, c in w.countries.items()})
            self.assertEqual(ownership_before, {sid: (s.owner, s.controller) for sid, s in w.states.items()})
            before = w.snapshot()
            w.effect(P + "proclaim", route.tag)
            self.assertEqual(w.snapshot(), before)

    def test_invitations_skip_foreign_subjects_and_retry_after_war_without_bypassing_refusal(self):
        w = self.national()
        w.countries["JRR"].war = True
        w.countries["JFT"].subject, w.countries["JFT"].overlord = True, "JEB"
        w.countries["VIN"].subject, w.countries["VIN"].overlord = True, "FLO"
        w.complete(P + "invite_regions", "JEB")
        recipients = lambda: [p[1] for p in w.scheduled if p[2] == "HSM_AQR.20"]
        self.assertEqual(recipients(), ["JFT"])
        w.effect(P + "invite_regions", "JEB")
        self.assertEqual(recipients(), ["JFT"], "Pending offer must not duplicate")
        w.countries["JRR"].war = False
        w.decision(P + "resend", "JEB")
        self.assertEqual(set(recipients()), {"JRR", "JFT"})
        w.advance_days(2)
        self.assertTrue(w.deliver("HSM_AQR.20", "JRR"))
        ownership = {sid: (s.owner, s.controller) for sid, s in w.states.items()}
        w.click("HSM_AQR.20", "HSM_AQR.20.a", "JRR", sender="JEB")
        self.assertEqual(ownership, {sid: (s.owner, s.controller) for sid, s in w.states.items()})
        self.assertTrue(w.countries["JRR"].exists)
        w.advance_days(31)
        w.effect(P + "invite_regions", "JEB")
        self.assertNotIn("JRR", recipients())
        w.complete(P + "break_resistance", "JEB")
        self.assertIn(("annex_everything", "JRR"), w.countries["JEB"].goals)
        self.assertNotIn(("annex_everything", "VIN"), w.countries["JEB"].goals)

    def test_accession_transfers_only_consenting_recipient_and_cannot_replay(self):
        for subject in (False, True):
            with self.subTest(subject=subject):
                w = self.national()
                if subject:
                    w.countries["JRR"].subject, w.countries["JRR"].overlord = True, "JEB"
                w.complete(P + "invite_regions", "JEB")
                w.advance_days(2)
                self.assertTrue(w.deliver("HSM_AQR.20", "JRR"))
                before = copy.deepcopy(w.states)
                consenting = {sid for sid, s in before.items() if s.owner == "JRR"}
                self.assertTrue(consenting)
                w.click("HSM_AQR.20", "HSM_AQR.20.b", "JRR", sender="JEB")
                self.assertFalse(w.countries["JRR"].exists)
                self.assertEqual(w.annexations, [("JEB", "JRR", "yes")])
                for sid, state in w.states.items():
                    if sid in consenting:
                        self.assertEqual(state.owner, "JEB")
                        self.assertEqual(state.cores, before[sid].cores)
                    else:
                        self.assertEqual(state, before[sid], sid)
                saved = w.snapshot()
                w.click("HSM_AQR.20", "HSM_AQR.20.b", "JRR", sender="JEB", stale=True)
                self.assertEqual(w.snapshot(), saved)

    def test_queued_and_open_accession_rejects_changed_sender_or_recipient(self):
        ready = self.national()
        ready.complete(P + "invite_regions", "JEB")
        ready.advance_days(2)
        for invalid in ("sender_subject", "sender_annexed", "sender_capitulated", "sender_war",
                        "sender_capital_owner", "sender_capital_controller", "sender_capital_partial_control",
                        "recipient_subject", "recipient_annexed", "recipient_capitulated", "recipient_war", "wrong_sender"):
            for opened in (False, True):
                with self.subTest(invalid=invalid, opened=opened):
                    w = copy.deepcopy(ready)
                    if opened:
                        self.assertTrue(w.deliver("HSM_AQR.20", "JRR"))
                    country = w.countries["JEB" if invalid.startswith("sender_") else "JRR"]
                    if invalid.endswith("subject"):
                        country.subject, country.overlord = True, "FLO"
                    elif invalid.endswith("annexed"):
                        country.exists = False
                    elif invalid.endswith("capitulated"):
                        country.capitulated = True
                    elif invalid.endswith("war"):
                        country.war = True
                    elif invalid == "sender_capital_owner":
                        w.states["377"].owner = "FLO"
                    elif invalid == "sender_capital_controller":
                        w.states["377"].controller = "FLO"
                    elif invalid == "sender_capital_partial_control":
                        w.states["377"].fully_controlled = False
                    if invalid.startswith("sender_capital_"):
                        self.assertFalse(w.check(w.triggers[P + "national"], "JEB"))
                        self.assertFalse(w.available(P + "national_services", "JEB"))
                        before = w.snapshot()
                        w.effect(P + "national_services", "JEB")
                        self.assertEqual(w.snapshot(), before, "Lost capital must also block stale national rewards")
                    if invalid == "wrong_sender" and not opened:
                        w.scheduled = [(day, tag, event, "FLO" if (tag, event) == ("JRR", "HSM_AQR.20") else sender)
                                       for day, tag, event, sender in w.scheduled]
                    if not opened:
                        self.assertFalse(w.deliver("HSM_AQR.20", "JRR"))
                    before = w.snapshot()
                    w.click("HSM_AQR.20", "HSM_AQR.20.b", "JRR",
                            sender="FLO" if invalid == "wrong_sender" else "JEB", stale=True)
                    self.assertEqual(w.snapshot(), before)



class PolicyLedger(Fixture):
    def assert_ledger(self, world, tag, expected):
        actual = {key.removeprefix(P + "mod_"): value for key, value in world.countries[tag].variables.items()
                  if key.startswith(P + "mod_") and abs(value) > 1e-9}
        self.assertEqual(actual.keys(), expected.keys())
        for key, value in expected.items():
            self.assertAlmostEqual(actual[key], value, msg=key)

    def test_opening_and_refresh_cannot_grant_an_unearned_programme(self):
        w = self.world(ROUTES[0])
        self.start(w)
        self.assert_ledger(w, "JEB", {})
        w.effect(P + "refresh", "JEB")
        self.assertIn(P + "compact", w.countries["JEB"].dynamic_modifiers)
        before = w.snapshot()
        w.effect(P + "refresh", "JEB")
        w.effect(P + "refresh", "JEB")
        self.assertEqual(w.snapshot(), before)

    def test_replacement_removes_old_policy_but_preserves_earned_development(self):
        w = self.ratified(ROUTES[0], "a")
        c = w.countries["JEB"]
        self.assert_ledger(w, "JEB", {"army_org_factor": .05, "stability_factor": .10, "political_power_factor": .10})
        c.ideas = {"poverty", "lack_of_scientists2"}
        for focus in ("regional_articles", "provincial_schools", "local_credit"):
            w.complete(P + focus, "JEB")
        ideas = set(c.ideas)
        self.legacy_without_native_snapshot(w, "JEB")
        # External legacy committee record, required before freezing the result.
        c.variables[NATIVE_MOVEMENTS['JEB_moderate']] = 60
        self.outcome(w, "JEB", "rev")
        w.daily()
        self.assert_ledger(w, "JEB", {"political_power_factor": .05})
        self.assertEqual(c.ideas, ideas)
        self.assertNotIn(P + "ratified_JEB_royal", c.flags)
        # The first tick attempts opening before clearing the obsolete ratification.
        # The next daily tick can queue the now-unratified province's settlement.
        self.assertFalse([p for p in w.scheduled if p[1:3] == ("JEB", "HSM_AQR.410")])
        w.advance_days(1)
        w.daily()
        self.assertEqual([p[0] for p in w.scheduled if p[1:3] == ("JEB", "HSM_AQR.410")], [w.day + 1])
        replacement = ROUTES[2]
        self.select_native(w, replacement)
        for stage in ("pledge", "organise", "settle"):
            w.complete(P + replacement.key + "_" + stage, "JEB")
        w.advance_days(1)
        self.assertTrue(w.deliver("HSM_AQR.102", "JEB"))
        w.click("HSM_AQR.102", "HSM_AQR.102.b", "JEB")
        self.assert_ledger(w, "JEB", {"political_power_factor": .05, "consumer_goods_factor": -.05,
                                      "production_speed_buildings_factor": .10,
                                      "industrial_capacity_factory": .10, "army_org_factor": .05,
                                      "stability_factor": -.05})
        self.assertEqual(c.ideas, ideas)
        before = w.snapshot()
        w.effect(P + "refresh", "JEB")
        w.effect(P + "refresh", "JEB")
        w.daily()
        self.assertEqual(w.snapshot(), before)


class Partition(Fixture):
    def conquered(self):
        w = self.national()
        w.countries["GRI"].exists = False
        for sid in ("382", "397", "378", "398"):
            w.states[sid].owner = w.states[sid].controller = "JEB"
            w.states[sid].cores.add("JEB")
        w.states["398"].controller = "FLO"  # Owned but not controlled.
        w.states["399"].owner, w.states["399"].controller = "FLO", "JEB"  # Controlled foreign land.
        return w

    def test_partition_transfers_only_owned_controlled_nonborder_states_and_is_idempotent(self):
        w = self.conquered()
        before = copy.deepcopy(w.states)
        w.effect(P + "partition", "JEB")
        self.assertTrue(w.countries["JHZ"].exists)
        self.assertTrue(w.check(parse("is_subject_of = JEB"), "JHZ"))
        self.assertEqual({sid for sid, s in w.states.items() if s.owner != before[sid].owner}, {"382", "397"})
        for sid, state in w.states.items():
            if sid in {"382", "397"}:
                self.assertEqual((state.owner, state.controller), ("JHZ", "JHZ"))
                self.assertIn("JHZ", state.cores)
                self.assertNotIn("JEB", state.cores)
            else:
                self.assertEqual(state, before[sid], sid)
        saved = w.snapshot()
        w.effect(P + "partition", "JEB")
        self.assertEqual(w.snapshot(), saved)
        w.effect(P + "border", "JEB")
        self.assertIn("JEB", w.states["378"].cores)
        self.assertEqual(w.states["399"], before["399"])
        self.assertEqual(w.states["398"], before["398"])

    def test_partition_rejects_foreign_jhz_war_existing_empire_and_lost_griffenheim(self):
        ready = self.conquered()
        for invalid in ("sovereign_jhz", "foreign_subject_jhz", "war", "gri", "ownership", "control", "partial"):
            with self.subTest(invalid=invalid):
                w = copy.deepcopy(ready)
                jhz = w.countries["JHZ"]
                if invalid in ("sovereign_jhz", "foreign_subject_jhz"):
                    jhz.exists = True
                    jhz.subject = invalid == "foreign_subject_jhz"
                    jhz.overlord = "FLO" if jhz.subject else ""
                elif invalid == "war":
                    w.countries["JEB"].war = True
                elif invalid == "gri":
                    w.countries["GRI"].exists = True
                elif invalid == "ownership":
                    w.states["382"].owner = "FLO"
                elif invalid == "control":
                    w.states["382"].controller = "FLO"
                else:
                    w.states["382"].fully_controlled = False
                before = w.snapshot()
                w.effect(P + "partition", "JEB")
                self.assertEqual(w.snapshot(), before)

    def test_existing_own_jhz_adopts_the_settlement_but_keeps_its_tree_and_completed_focuses(self):
        w = self.conquered()
        jhz = w.countries["JHZ"]
        jhz.exists, jhz.subject, jhz.overlord = True, True, "JEB"
        jhz.leader, jhz.government, jhz.focus_tree = "fixture_existing_ruler", "communism", "fixture_existing_tree"
        jhz.focuses = {"fixture_completed_focus"}
        jhz.capital = "382"
        w.states["382"].owner = w.states["382"].controller = "JHZ"
        w.effect(P + "partition", "JEB")
        self.assertEqual((jhz.government, jhz.cosmetic, jhz.elections), ("democratic", "JER_PUPPET", True))
        self.assertEqual(jhz.focus_tree, "fixture_existing_tree")
        self.assertEqual(jhz.focuses, {"fixture_completed_focus"})
        self.assertFalse(w.tree_loads)

    def test_all_fifteen_border_governments_follow_the_route_including_neutral_republics(self):
        royal = {"JEB_royal", "JEB_constitutional", "JRR_absolutist", "JRR_coalition", "JFT_dennis", "VIN_gadiffer"}
        for route in ROUTES:
            with self.subTest(route=route.key):
                w = self.national(route)
                w.countries["GRI"].exists = False
                w.states["382"].owner = w.states["382"].controller = route.tag
                w.countries[route.tag].technology = {"fixture_known_technology"}
                w.effect(P + "partition", route.tag)
                jhz = w.countries["JHZ"]
                self.assertEqual(jhz.overlord, route.tag)
                self.assertEqual(jhz.cosmetic, "JER_PUPPET" if route.key in royal else "JER_REPUBLIC_PUPPET")
                expected_party = route.party
                self.assertEqual(jhz.government, expected_party)
                self.assertEqual(jhz.elections, expected_party == "democratic")
                self.assertEqual(jhz.focus_tree, "generic_griffon_focus")
                self.assertIn("fixture_known_technology", jhz.technology)


class NativeCompatibility(Fixture):
    def test_support_and_restoration_choose_literal_origin_before_switch_and_reacquire_jer(self):
        for name in ('continue_at_centre', 'RESTORE_royal', 'RESTORE_republic'):
            with self.subTest(effect=name):
                body = self.production.effects[P + name]
                branches = [n for n in walk(body) if n.key in ('if', 'else_if')
                            and any(x.key == 'change_tag_from' for x in walk(n.children))
                            and Node('limit', '=', n.get('limit', [])).get('tag') in REGIONS]
                self.assertEqual([n.key for n in branches], ['if', 'else_if', 'else_if', 'else_if'])
                self.assertEqual(len(branches), 4)
                for branch, tag in zip(branches, REGIONS):
                    limit = Node('limit', '=', branch.get('limit', []))
                    self.assertEqual((limit.get('tag'), limit.get('original_tag')), (tag, tag))
                    switches = [n for n in walk(branch.children) if n.key == 'change_tag_from']
                    self.assertEqual([n.value for n in switches], [tag], 'Never resolve ROOT after the player switch')
                    switch_scopes = [n for n in walk(branch.children) if n.key == 'JER'
                                     and any(x.key == 'change_tag_from' for x in walk(n.children))]
                    self.assertEqual(len(switch_scopes), 1)
                    self.assertFalse(any(n.key == 'annex_country' for n in walk(switch_scopes[0].children)))
                    self.assertEqual([n.get('target') for n in walk(branch.children) if n.key == 'annex_country'], [tag])

    def test_native_committee_category_closes_after_recording_with_only_the_authorized_visibility_insertion(self):
        from hashlib import sha256
        relative = Path("common/decisions/categories/JER_decision_categories.txt")
        native_raw = (OPT.eaw / relative).read_bytes()
        self.assertEqual(sha256(native_raw).hexdigest(), "44919731bd90a46320306b4725c0b4896b8d86cfe74c437c9404db33c6afac1d")
        self.assertEqual(native_raw, (ROOT / "EaW" / relative).read_bytes())
        generated = (MOD / relative).read_bytes().decode("utf-8-sig")
        header = "# Generated by tools/Build-AquileianRegions.py.\n"
        insertion = "\n\tvisible = { NOT = { has_country_flag = HSM_AQR_native_outcome_recorded } }\n"
        self.assertTrue(generated.startswith(header))
        self.assertEqual(generated.count(insertion), 1)
        # The generator wraps source with its header and canonical outer whitespace only.
        restored = generated[len(header):].replace(insertion, "", 1)
        self.assertEqual(restored, native_raw.decode("utf-8-sig").strip() + "\n")
        native, effective = read(OPT.eaw / relative), read(MOD / relative)
        category_id = "JER_JEB_committee_of_public_safety_category"
        committee = next(n for n in effective if n.key == category_id)
        visibility = parse("visible = { NOT = { has_country_flag = HSM_AQR_native_outcome_recorded } }")[0]
        self.assertEqual(committee.all("visible"), [visibility])
        normalized = [Node(n.key, n.op, [child for child in n.children if child != visibility])
                      if n.key == category_id else n for n in effective]
        self.assertEqual(normalized, native, "Every other category and committee field must remain pristine")
        w = AquileianWorld()
        w.root = "JEB"
        w.countries["JEB"].government = "democratic"
        self.assertTrue(w.check(committee.get("allowed", []), "JEB"))
        self.assertTrue(w.check(committee.get("visible", []), "JEB"))
        w.global_flags.add(GLOBAL_OUTCOMES["rev"])
        w.countries["JER"].flags.add(P + "native_outcome_recorded")
        self.assertTrue(w.check(committee.get("visible", []), "JEB"), "The guard belongs to this province's recorded result")
        w.countries["JEB"].flags.add(P + "native_outcome_recorded")
        self.assertFalse(w.check(committee.get("visible", []), "JEB"))
        for tag in ("JER", "JRR", "JFT", "VIN"):
            self.assertFalse(w.check(committee.get("allowed", []), tag))

    def test_native_support_decisions_are_unchanged_except_the_single_outcome_callback(self):
        hook = parse('''hidden_effect = { if = {
limit = { OR = { original_tag = JEB original_tag = JRR original_tag = JFT original_tag = VIN } }
HSM_AQR_record_native_outcome = yes
} }''')[0]
        for tag in ("JER", *REGIONS):
            with self.subTest(tag=tag):
                relative = Path("common/decisions") / (tag + "_decisions.txt")
                native = read(OPT.eaw / relative)
                effective_path = MOD / relative if (MOD / relative).exists() else OPT.eaw / relative
                effective = read(effective_path)
                if tag == "JER":
                    mission = next(n for category in effective for n in category.children if n.key == "JER_revolution_mission")
                    timeout = mission.get("timeout_effect", [])
                    self.assertEqual(timeout[-1], hook, "Record only after the native outcome has been assigned")
                    calls = [n for n in walk(effective) if n.key == P + "record_native_outcome"]
                    self.assertEqual(len(calls), 1)
                    def strip_callback(nodes):
                        result = []
                        for n in nodes:
                            children = n.children
                            if n.key == "JER_revolution_mission":
                                children = [Node(child.key, child.op, child.children[:-1]) if child.key == "timeout_effect" else child
                                            for child in children]
                            result.append(Node(n.key, n.op, strip_callback(children) if isinstance(n.value, list) else n.value))
                        return result
                    effective = strip_callback(effective)
                self.assertEqual(effective, native, "Native prices, influence amounts, ties, queues and other decision content must remain unchanged")

    def test_native_triumph_and_loyal_integration_offer_real_choices_before_any_annexation(self):
        definitions = {n.get("id"): n for n in walk(read(MOD / "common/national_focus/JER.txt"))
                       if n.key in ("focus", "shared_focus") and n.children}
        for focus_id, field_name in (("JER_the_triumph", "select_effect"),
                                     ("JER_integrate_the_loyal", "completion_reward")):
            with self.subTest(focus=focus_id):
                w = copy.deepcopy(self.template)
                w.countries["JER"].focuses.add("JER_state_of_aquileia")
                self.start(w)
                for tag in REGIONS:
                    self.outcome(w, tag, 'royal')
                self.centre_outcome(w, 'royal')
                w.root = w.sender = "JER"
                countries = copy.deepcopy(w.countries)
                states = copy.deepcopy(w.states)
                w.run(definitions[focus_id].get(field_name, []), "JER")
                self.assertEqual(w.countries, countries, "Selection must not remove countries, characters or treasury")
                self.assertEqual(w.states, states)
                self.assertFalse(w.annexations)
                packets = [p for p in w.scheduled if p[2] == "HSM_AQR.30"]
                self.assertEqual({p[1] for p in packets}, set(REGIONS))
                self.assertEqual(len(packets), 4)
                self.assertTrue(all(p[0] == 7 and p[3] == "JER" for p in packets))
                w.advance_days(7)
                for tag in REGIONS:
                    self.assertTrue(w.deliver("HSM_AQR.30", tag))
                    live = [o for o in w.events["HSM_AQR.30"].all("option") if w.check(o.get('trigger',[]),tag)]
                    self.assertEqual(len(live), 2)
                    w.click("HSM_AQR.30", "HSM_AQR.30.lead", tag, sender="JER")
                    self.assertTrue(w.countries[tag].exists)
                    self.assertFalse(w.countries[tag].subject)
                    self.assertIn('JER',w.countries[tag].wars)
                    self.assertFalse(w.annexations)

    def test_jer_override_preserves_native_content_except_authorized_integration_and_start_hooks(self):
        allowed = {"JER_the_triumph": "select_effect", "JER_integrate_the_loyal": "completion_reward"}
        starts = {"JER_state_of_aquileia", "JER_fight_for_freedom"}
        hook = parse("hidden_effect = { HSM_AQR_start_regions = yes }")[0]
        reconstruction = Node("shared_focus", "=", "HSM_AQR_REC_postwar_housing")
        def normalized(nodes):
            result = []
            for n in nodes:
                children = n.children
                if n.key == "focus_tree":
                    children = [c for c in children if c != reconstruction]
                elif n.key in ("focus", "shared_focus") and n.children and n.get("id") in allowed:
                    children = [c for c in children if c.key != allowed[n.get("id")]]
                elif n.key in ("focus", "shared_focus") and n.children and n.get("id") in starts:
                    children = [Node(c.key, c.op, [x for x in c.children if x != hook])
                                if c.key == "completion_reward" else c for c in children]
                result.append(Node(n.key, n.op, normalized(children) if isinstance(n.value, list) else n.value))
            return result
        path = Path("common/national_focus/JER.txt")
        native, patched = read(OPT.eaw / path), read(MOD / path)
        native_trees = {n.get("id"): n for n in native if n.key == "focus_tree"}
        patched_trees = {n.get("id"): n for n in patched if n.key == "focus_tree"}
        self.assertEqual(len(patched_trees), 6)
        self.assertEqual(native_trees.keys(), patched_trees.keys())
        for tree_id, tree in patched_trees.items():
            with self.subTest(tree=tree_id):
                self.assertEqual(tree.children.count(reconstruction), 1)
                self.assertEqual([c for c in tree.children if c != reconstruction], native_trees[tree_id].children)
        start_focuses = [n for n in walk(read(MOD / path)) if n.key in ("focus", "shared_focus") and n.get("id") in starts]
        self.assertEqual({f.get("id") for f in start_focuses}, starts)
        for focus in start_focuses:
            self.assertEqual(focus.get("completion_reward", []).count(hook), 1)
        self.assertEqual(normalized(native), normalized(patched))

    def test_native_formation_decisions_explicitly_exclude_all_four_original_tags(self):
        nodes = read(MOD / "common/decisions/griffon_decisions.txt")
        decisions = {n.key: n for category in nodes for n in category.children}
        expected = parse("NOT = { OR = { " + " ".join("original_tag = " + t for t in REGIONS) + " } }")[0]
        w = AquileianWorld()
        for name in ("form_aquileia", "form_griffon_empire", "unite_aquileia_proper"):
            with self.subTest(decision=name):
                self.assertIn(expected, decisions[name].get("allowed", []))
                for tag in REGIONS:
                    self.assertFalse(w.check([expected], tag))
                self.assertTrue(w.check([expected], "FLO"))


class Inventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production = Production()

    def test_player_tag_changes_require_fresh_country_scope_for_followup_effects(self):
        p = self.production
        roots = dict(p.effects)
        roots.update({fid + '/reward': f.get('completion_reward', []) for fid, f in p.focuses.items()})
        roots.update({eid + '/' + o.get('name'): o.children for eid, event in p.events.items() for o in event.all('option')})
        roots.update({did + '/complete': d.get('complete_effect', []) for did, d in p.decisions.items()})
        roots.update({'hook/' + hook: body for hook, body in p.hooks.items()})
        failures = {name: faults for name, body in roots.items()
                    if (faults := stale_effects_after_tag_change(body, p.effects))}
        self.assertFalse(failures, f'Effects after change_tag_from lack a fresh literal country scope: {failures}')

    def test_retired_preparation_and_local_influence_have_no_runtime_definitions_or_references(self):
        p = self.production
        retired_prefixes = (P + "prep_", P + "prepared_", P + "influence_", P + "can_influence_", P + "can_prepare")
        retired = {P + name for name in ("chosen_royal", "chosen_rev", "assembled", "sabotaged",
                   "preparation_disrupted", "against_centre", "local_campaign_cooldown", "local_assembly_done",
                   "capture_preparation_choice", "add_preparation_support", "resolve_preparation",
                   "refresh_revolution", "refresh_central_support", "provides_regional_support")}
        retired.update(P + "regional_support_" + str(n) for n in range(1, 5))
        bad = []
        for path, nodes in p.nodes.items():
            for n in walk(nodes):
                for value in (n.key, n.value):
                    if isinstance(value, str) and (value in retired or value.startswith(retired_prefixes) or "Milice provinciale" in value):
                        bad.append((str(path.relative_to(MOD)), value))
                if n.key in ("set_variable", "add_to_variable", "subtract_from_variable", "multiply_variable", "divide_variable", "clamp_variable"):
                    target = n.get("var") if n.get("var") else n.children[0].key if n.children else None
                    self.assertNotIn(target, {"monarchist_support", "revolutionary_support"},
                                     "Authored runtime must not write the native influence scores")
        self.assertFalse(bad, "Retired authored preparation still appears in generated scripts")
        self.assertFalse({"HSM_AQR." + str(n) for n in range(400, 404)} & p.events.keys(), "Retired sabotage events must be removed")

    def test_fifteen_programmes_have_all_stages_and_real_finish_effects(self):
        p = self.production
        self.assertEqual(len(p.routes), 15)
        self.assertEqual(set(p.routes), {route.key for route in ROUTES})
        self.assertEqual({tag: sum(r.startswith(tag + "_") for r in p.routes) for tag in REGIONS}, ROUTE_COUNTS)
        required = {P + x for x in ("opening", "national_mandate", "proclaim", "invite_regions")}
        self.assertTrue(required <= p.focuses.keys(), sorted(required - p.focuses.keys()))
        for route in p.routes:
            for stage in ("pledge", "organise", "settle"):
                with self.subTest(route=route, stage=stage):
                    suffix = route + "_" + stage
                    focus = p.focuses[P + suffix]
                    self.assertNotEqual(focus.get("repeatable"), "yes")
                    self.assertIn(P + "finish_" + suffix, p.effects)
                    self.assertTrue(any(n.key == P + "finish_" + suffix
                                        for n in walk(focus.get("completion_reward", []))))
            for choice in ("a", "b"):
                self.assertIn(P + "ratify_" + route + "_" + choice, p.effects)

    def test_focus_dependencies_are_resolved_and_acyclic(self):
        p = self.production
        graph = {fid: references(f, "prerequisite") for fid, f in p.focuses.items()}
        for fid, focus in p.focuses.items():
            for field_name in ("prerequisite", "mutually_exclusive"):
                self.assertFalse(references(focus, field_name) - p.focuses.keys(), (fid, field_name))
        visiting, visited = set(), set()
        def visit(fid):
            self.assertNotIn(fid, visiting, f"Focus cycle at {fid}")
            if fid in visited:
                return
            visiting.add(fid)
            for parent in graph[fid]:
                visit(parent)
            visiting.remove(fid)
            visited.add(fid)
        for fid in graph:
            visit(fid)
        self.assertTrue(p.trees)
        members = set().union(*(p.tree_members(t) for t in p.trees))
        self.assertFalse(p.focuses.keys() - members, "Unattached focus definitions")

    def test_no_global_generic_override_or_unnamespaced_focus_definition(self):
        self.assertFalse((MOD / "common/national_focus/generic_griffon.txt").exists())
        self.assertTrue(all(fid.startswith(P) for fid in self.production.focuses))
        self.assertTrue(all(tid.startswith(P) for tid in self.production.trees))

    def test_tree_selection_and_daily_maintenance_are_connected_to_actual_production(self):
        p = self.production
        w = AquileianWorld(p)
        tree = p.trees[P + "regional_tree"]
        selector = Node("country", "=", tree.get("country", []))
        self.assertEqual(selector.get("factor"), "0")
        self.assertTrue(selector.all("modifier"))
        for tag in (*REGIONS, "JER", "FLO", "GRI", "JHZ"):
            score = float(selector.get("factor"))
            for modifier in selector.all("modifier"):
                if w.check([n for n in modifier.children if n.key not in ("add", "factor")], tag):
                    score = score * float(modifier.get("factor", "1")) + float(modifier.get("add", "0"))
            self.assertEqual(score > 5, tag in REGIONS, tag)
        self.assertIn("on_daily", p.hooks)
        self.assertTrue(any(n.key == P + "tick" for n in walk(p.hooks["on_daily"])))

    def test_all_gfx_references_resolve_in_submod_eaw_or_installed_game(self):
        needed = {n.value for nodes in self.production.nodes.values() for n in walk(nodes)
                  if n.key in ("icon", "picture") and isinstance(n.value, str) and n.value.startswith("GFX_")}
        definitions = set()
        for root in (OPT.game, OPT.eaw, MOD):
            for path in (root / "interface").rglob("*.gfx"):
                definitions.update(re.findall(r'\bname\s*=\s*"?(GFX_[A-Za-z0-9_.-]+)', path.read_text(encoding="utf-8-sig")))
        self.assertTrue(needed)
        self.assertFalse(needed - definitions, f"Unresolved sprites: {sorted(needed - definitions)}")

    def test_generator_check_reports_no_missing_or_stale_outputs(self):
        command = [sys.executable, "-B", "-X", "utf8", str(ROOT / "tools/Build-AquileianRegions.py"),
                   "--eaw", str(OPT.eaw), "--check"]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scripted_references_and_flags_have_production_writers(self):
        p = self.production
        definitions = p.effects.keys() | p.triggers.keys()
        nodes = [n for tree in p.nodes.values() for n in walk(tree)]
        writes = {n.get("flag") if n.children else n.value for n in nodes if n.key == "set_country_flag"}
        reads = {n.value for n in nodes if n.key == "has_country_flag"
                 and isinstance(n.value, str) and n.value.startswith(P)}
        # Old peaceful leadership refusals still waive the support cooldown in
        # migrated saves; the retired request chain must never write new ones.
        legacy_read_only = {P + 'leadership_rejected'}
        self.assertFalse(legacy_read_only & writes, 'Do not revive retired peaceful leadership state')
        self.assertFalse(reads - writes - legacy_read_only, sorted(reads - writes - legacy_read_only))
        for node in nodes:
            with self.subTest(key=node.key, value=str(node.value)[:90]):
                if node.key.startswith(P) and isinstance(node.value, str) and node.value in ("yes", "no"):
                    self.assertIn(node.key, definitions)
                if node.key == "country_event" and node.children and not node.get("is_triggered_only"):
                    event_id = node.get("id")
                    if event_id.startswith("HSM_AQR"):
                        self.assertIn(event_id, p.events)
                if node.key == "load_focus_tree":
                    self.assertIn(node.get("tree"), p.trees | p.native_trees)
                    self.assertTrue(p.tree_members(node.get("tree")), "Referenced tree must resolve real focus members")

    def test_generic_subtrees_are_replaced_with_authored_campaigns(self):
        p=self.production
        self.assertFalse(any(fid.startswith(P+'BASE_') or fid.startswith('griffon_') for fid in p.focuses))
        self.assertEqual(sum(fid.startswith(P+'CAM_') for fid in p.focuses),180)
        self.assertEqual(sum(fid.startswith(P+'LOCAL_') for fid in p.focuses),16)
        self.assertFalse((MOD/'common/national_focus/generic_griffon.txt').exists())
        reset_events={'griffon.1','griffon.2','griffon.3','griffon.4','griffon.5','griffon.6','griffon.7'}
        for focus in p.focuses.values():
            self.assertFalse({n.get('id') if n.children else n.value for n in walk(focus.get('completion_reward',[])) if n.key=='country_event'} & reset_events)

    def test_localization_encoding_parity_duplicates_and_script_references(self):
        languages = {}
        for language in ("english", "russian"):
            files = sorted((MOD / "localisation" / language).glob("HSM_AQR*_l_*.yml"))
            self.assertTrue(files, f"Missing {language} AQR localization")
            values = {}
            for path in files:
                self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"), str(path))
                lines = path.read_text(encoding="utf-8-sig").splitlines()
                self.assertEqual(lines[0].strip(), "l_" + language + ":", str(path))
                for line_no, line in enumerate(lines[1:], 2):
                    if not line.strip() or line.lstrip().startswith("#"):
                        continue
                    match = re.fullmatch(r'\s*([A-Za-z0-9_.-]+):\d+\s+"((?:\\.|[^"\\])*)"\s*', line)
                    self.assertIsNotNone(match, f"Malformed {path}:{line_no}: {line}")
                    key, value = match.groups()
                    self.assertNotIn(key, values, f"Duplicate {language}: {key}")
                    self.assertTrue(value.strip(), f"Empty {language}: {key}")
                    values[key] = value
            languages[language] = values
        self.assertEqual(languages["english"].keys(), languages["russian"].keys())
        required = {key for fid in self.production.focuses for key in (fid, fid + "_desc")}
        for tree in self.production.nodes.values():
            for node in walk(tree):
                if (node.key in ("name", "title", "desc", "text", "tooltip", "custom_effect_tooltip", "create_faction")
                        and isinstance(node.value, str) and node.value.startswith("HSM_AQR")):
                    required.add(node.value)
        for language, values in languages.items():
            self.assertFalse(required - values.keys(), f"Missing {language}: {sorted(required - values.keys())}")
            for key, value in values.items():
                refs = set(re.findall(r'\$(HSM_AQR[A-Za-z0-9_.]+)(?:\|[^$]*)?\$', value))
                self.assertFalse(refs - values.keys(), f"Broken {language} references in {key}: {refs - values.keys()}")
                # Dynamic scope references must be retained by translation.
                if language == "russian":
                    self.assertEqual(sorted(re.findall(r'\[[^\[\]]+\]', value)),
                                     sorted(re.findall(r'\[[^\[\]]+\]', languages["english"][key])), key)


if __name__ == "__main__":
    unittest.main(argv=[__file__, *BASE["REST"]], verbosity=2)
