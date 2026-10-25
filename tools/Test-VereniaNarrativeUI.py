"""Read-only Verenia narrative/source UI audit; no engine rendering or simulation.

Run with python -B -X utf8 tools/Test-VereniaNarrativeUI.py
  [--baseline ORIGINALS] [--eaw EAW_ROOT] [--game HOI4_ROOT]
The default ORIGINALS is outputs/qa/verenia-narrative-before, a pre-edit snapshot
with game-relative paths. --self-test runs synthetic regressions only;
--equivalence-only checks the actual files without the editorial/UI audit.

Reuses Test-VereniaFocusUI.py's parser, localization, idea previews and source
row estimates through runpy, without running its CLI or editing that test.
Metadata is opaque. Triggers retain boolean grouping; effects retain order,
native parameters, limits, AI and branch selection. Only presentation syntax
is normalized. A purely presentational if/else chain can disappear as a whole;
empty branches must remain when they guard later gameplay branches.
Helpers, on_actions, ideas and focus scripts in the snapshot are also compared
so moving an effect into a helper cannot conceal a gameplay change.

UI scope: local Verenia decisions and event options, plus HSM-related native
Erie decisions/Avian options. Unrelated native Avian options are not audited.
Decision available/remove/cancel requirements are hover rows. Option trigger,
decision visible/allowed and category visibility are selection gates, preserved
by equivalence but not charged as hover rows. Event trigger/immediate/after
are preserved, not counted as option rewards. A flag/log-only acknowledgement
does not need a fabricated result. Actual effects need a visible native result,
idea preview or meaningful localized summary, including conditional results.

Budgets count all possibly visible branches, at 72 columns by default, using
the focus audit's EN/RU native-row allowances. These are source estimates, NOT
engine output or screenshot-fit guarantees. External references are estimated
without dependencies; --eaw/--game enable strict localization/idea checks with
game < EAW < submod precedence. HSM references are always strict. Description
checks use actual focus/decision/category keys, not every *_desc localization;
they flag obvious numeric stats or engine instructions, not ordinary dates,
character names, or narrative discussion of stability or engineering.
"""
from __future__ import annotations

import argparse
from collections import Counter
import difflib
import json
from pathlib import Path
import re
import runpy
import sys
from types import SimpleNamespace
import unittest


FOCUS = SimpleNamespace(**runpy.run_path(str(Path(__file__).with_name("Test-VereniaFocusUI.py"))))
ROOT = Path(__file__).resolve().parents[1]
parse, read, walk, Node = FOCUS.parse, FOCUS.read, FOCUS.walk, FOCUS.Node
PREFIXES = FOCUS.PREFIXES
EVENTS = {"country_event", "news_event", "state_event", "unit_leader_event"}
OPTION_METADATA = {
    "name", "trigger", "ai_chance", "original_tag", "highlighted",
    "default_option", "fire_only_once", "visible", "allowed", "icon",
}
OPTION_TRIGGERS = {"trigger", "visible", "allowed"}
DECISION_TRIGGERS = {
    "available", "visible", "allowed", "target_trigger", "target_root_trigger",
    "activation", "remove_trigger", "cancel_trigger",
}
DECISION_EFFECTS = {"complete_effect", "remove_effect", "timeout_effect", "cancel_effect"}
HOVER_REQUIREMENTS = {"available", "remove_trigger", "cancel_trigger"}
PRESENTATION = FOCUS.PRESENTATION_EFFECTS | {"effect_tooltip"}
CONTROL_METADATA = {
    "limit", "chance", "modifier", "trigger", "seed", "original_tag",
    "count", "array", "value", "start", "end", "compare", "add",
}
BOOKKEEPING = {
    "log", "set_country_flag", "clr_country_flag", "set_global_flag",
    "clr_global_flag", "set_state_flag", "clr_state_flag", "set_character_flag",
    "clr_character_flag", "set_unit_leader_flag", "clr_unit_leader_flag",
}
PUBLIC_NATIVE = FOCUS.CONCRETE_EFFECTS | {
    "set_autonomy", "annex_country", "transfer_state", "puppet", "release",
    "release_puppet", "set_politics", "set_popularities", "add_popularity",
    "set_country_leader", "recruit_character", "retire_character",
    "set_cosmetic_tag", "drop_cosmetic_tag", "set_non_aggression_pact",
    "set_truce", "declare_war_on", "white_peace", "start_border_war",
    "cancel_border_war", "activate_decision", "activate_targeted_decision",
    "unlock_decision_tooltip", "load_focus_tree", "add_to_tech_sharing_group",
    "set_technology", "add_dynamic_modifier", "remove_dynamic_modifier",
}


def related(nodes):
    return any(n.key.lower().startswith("hsm_") or
               isinstance(n.value, str) and n.value.lower().startswith("hsm_")
               for n in walk(nodes))


def opaque(nodes):
    return tuple((n.key, n.op, opaque(n.children) if n.block else n.value) for n in nodes)


def trigger(nodes, parent="AND"):
    # Use the shared normalizer's implicit-AND protection under OR/NOT/NOR/NAND.
    return FOCUS.canonical(nodes, "trigger", parent)


def effect_container(key):
    return (key in FOCUS.GUARDED_EFFECTS or FOCUS.is_scope(key)
            or key.startswith(("every_", "random_", "any_", "event_target:", "var:")))


def scoped_body_has_effect(nodes):
    """Empty deterministic scopes do not make a tooltip-only branch gameplay.

    Random/loop commands remain significant even when their bodies are empty:
    removing them could change RNG consumption or loop behavior.
    """
    for key, op, value in nodes:
        if key in {"limit", "trigger"}:
            continue
        if op == "=" and isinstance(value, tuple) and (
                FOCUS.is_scope(key) or key.startswith("event_target:")):
            if scoped_body_has_effect(value):
                return True
        else:
            return True
    return False


def flatten_hidden(nodes):
    for n in nodes:
        if n.key == "hidden_effect" and n.block and n.op == "=":
            yield from flatten_hidden(n.children)
        else:
            yield n


def effects(nodes):
    """Canonical effects; unknown native parameter blocks remain wholly opaque."""
    nodes = tuple(n for n in flatten_hidden(nodes) if not (n.key in PRESENTATION and n.op == "="))
    result, index = [], 0

    def one(n):
        if not n.block or n.op != "=":
            return (n.key, n.op, opaque(n.children) if n.block else n.value)
        if n.key in {"limit", "trigger"}:
            value = trigger(n.children)
        elif n.key == "random_list":
            # Weights and modifiers affect selection even when a branch is empty.
            value = tuple((c.key, c.op, effects(c.children) if c.block and c.key.isdigit()
                           else opaque(c.children) if c.block else c.value) for c in n.children)
        elif effect_container(n.key):
            value = effects(n.children)
        else:
            value = opaque(n.children)
        return (n.key, n.op, value)

    while index < len(nodes):
        n = nodes[index]
        if n.key == "if" and n.block and n.op == "=":
            end = index + 1
            while (end < len(nodes) and nodes[end].key in {"else_if", "else"}
                   and nodes[end].block and nodes[end].op == "="):
                end += 1
            chain = nodes[index:end]
            # Keep every guard up to the last gameplay arm. Trailing tooltip-only
            # arms cannot affect earlier actions; leading/middle arms can.
            bodies = [effects(tuple(c for c in b.children if c.key != "limit")) for b in chain]
            significant = [i for i, body in enumerate(bodies) if scoped_body_has_effect(body)]
            if significant:
                result.extend(one(b) for b in chain[:significant[-1] + 1])
            index = end
            continue
        normalized = one(n)
        if not (n.block and n.op == "=" and
                (FOCUS.is_scope(n.key) or n.key.startswith("event_target:")) and
                not scoped_body_has_effect(normalized[2])):
            result.append(normalized)
        index += 1
    return tuple(result)


def field(n, mode):
    normalizer = {"trigger": trigger, "effect": effects, "metadata": opaque}[mode]
    return (n.key, n.op, normalizer(n.children) if n.block else n.value)


def option_parts(option):
    return (tuple(n for n in option.children if n.key in OPTION_METADATA),
            tuple(n for n in option.children if n.key not in OPTION_METADATA))


def hover_requirements(record):
    # Local vanilla events/Britain.txt:314 and events/MTG_Britain.txt:4800
    # explicitly document option trigger as hiding the option. Decisions'
    # common/decisions/_documentation.md:6-35 distinguishes available from gates.
    if record.key == "option":
        return ()
    return tuple(c for n in record.children if n.key in HOVER_REQUIREMENTS for c in n.children)


def canonical_option(option):
    metadata, body = option_parts(option)
    return (option.op,
            tuple(field(n, "trigger" if n.key in OPTION_TRIGGERS else "metadata") for n in metadata),
            effects(body))


def canonical_record(record, triggers=(), effect_fields=()):
    return tuple(field(n, "trigger" if n.key in triggers else
                       "effect" if n.key in effect_fields else "metadata") for n in record.children)


def canonical_event(event):
    return tuple((n.key, canonical_option(n)) if n.key == "option" and n.block else
                 field(n, "trigger" if n.key == "trigger" else
                       "effect" if n.key in {"immediate", "after"} else "metadata")
                 for n in event.children)


def file_kind(path):
    parts = path.parts
    if parts[0] == "events":
        return "events"
    if "decisions" in parts:
        return "categories" if "categories" in parts else "decisions"
    return parts[1]


def canonical_file(nodes, kind):
    def visit(n):
        if not n.block:
            return (n.key, n.op, n.value)
        if kind == "events" and n.key in EVENTS:
            value = canonical_event(n)
        elif kind == "decisions":
            value = tuple((d.key, d.op, canonical_record(d, DECISION_TRIGGERS, DECISION_EFFECTS)
                           if d.block else d.value) for d in n.children)
        elif kind == "categories":
            value = canonical_record(n, DECISION_TRIGGERS)
        elif kind == "scripted_effects":
            value = effects(n.children)
        elif kind == "scripted_triggers":
            value = trigger(n.children)
        elif kind == "national_focus":
            value = (canonical_record(n, {"available", "bypass"}, {"completion_reward", "completion_reward_joint_originator", "completion_reward_joint_member"})
                     if n.key in {"focus", "shared_focus", "joint_focus"} else tuple(visit(c) for c in n.children))
        elif kind == "on_actions":
            value = tuple(field(c, "effect") if c.key == "effect" else visit(c) for c in n.children)
        else:
            value = opaque(n.children)
        return (n.key, n.op, value)
    return tuple(visit(n) for n in nodes)


def sources(root):
    if not root.is_dir():
        raise ValueError(f"Source directory does not exist: {root}")
    paths = []
    for folder in ("events", "common/decisions", "common/national_focus", "common/scripted_effects",
                   "common/scripted_triggers", "common/on_actions", "common/ideas"):
        paths.extend(p for p in (root / folder).rglob("*.txt")
                     if p.name.startswith(PREFIXES) or p.name in {"Avian Events.txt", "AVI.txt", "ERI_decisions.txt"})
    return {p.relative_to(root): read(p) for p in sorted(paths)}


def difference(label, before, after):
    if before == after:
        return []
    delta = difflib.unified_diff(json.dumps(before, indent=1).splitlines(),
                                 json.dumps(after, indent=1).splitlines(),
                                 fromfile="before", tofile="after", n=2, lineterm="")
    return [f"{label}: semantic/order change\n" + "\n".join(list(delta)[:40])]


def compare_sources(before, after):
    errors, counts = [], Counter()
    if not before:
        return ["No baseline game scripts found; ORIGINALS must contain game-relative directories."], counts
    for path in sorted(before.keys() | after.keys()):
        if path not in before or path not in after:
            errors.append(f"{path.as_posix()}: script {'added' if path not in before else 'removed'}")
            continue
        kind = file_kind(path)
        counts[kind] += 1
        errors.extend(difference(path.as_posix(), canonical_file(before[path], kind), canonical_file(after[path], kind)))
    return errors, counts


class Localization(FOCUS.Localization):
    def resolve(self, key, stack=()):
        # The shared implementation reserves uppercase HSM_; event IDs also use
        # lowercase hsm_ver*. Missing local event names must never be estimates.
        if not isinstance(key, str) or not key:
            raise ValueError(f"invalid localization key: {key!r}")
        if key.lower().startswith("hsm_") and key not in self.values:
            raise ValueError(f"missing localization: {key}")
        return super().resolve(key, stack)


def meaningful_summary(text):
    plain = text.strip().lower().rstrip(".! ")
    return (len(re.findall(r"\w", plain)) >= 10 and plain not in {
        "acknowledged", "nothing happens", "no effect", "no effects", "continue",
        "we shall see", "we will proceed", "a public result", "placeholder",
    } and not re.fullmatch(r"[xX\s.]+", plain))


class NarrativeHover(FOCUS.Hover):
    def localized(self, key):
        text = super().localized(key)
        if not getattr(self, "reference_only", False) and re.search(r"\bHSM_[A-Za-z0-9_]+\b|\bhsm_ver[\w.]+", text):
            self.error(f"raw HSM identifier in public localization: {key}")
        return text

    def validate_references(self, nodes, seen=None):
        previous = getattr(self, "reference_only", False)
        self.reference_only = True
        try:
            self._validate_references(nodes, seen)
        finally:
            self.reference_only = previous

    def _validate_references(self, nodes, seen=None):
        seen = set() if seen is None else seen
        for n in walk(nodes):
            if n.key == "custom_effect_tooltip":
                self.localized(n.get("localization_key") if n.block else n.value)
            elif n.key == "custom_trigger_tooltip":
                self.localized(n.get("tooltip"))
            elif n.key == "show_ideas_tooltip":
                self.idea_rows(n, 0)
            for mode, definitions in (("effect", self.effects), ("trigger", self.triggers)):
                if n.key in definitions and (mode, n.key) not in seen:
                    seen.add((mode, n.key))
                    self.validate_references(definitions[n.key], seen)

    def rewards(self, nodes, depth=0, chain=(), unconditional=True):
        rows, public = [], []
        for n in nodes:
            if n.key in FOCUS.GUARDED_EFFECTS or n.key.startswith(("every_", "random_", "any_")):
                if not self.enter(n, chain):
                    continue
                rows.append(self.native(n, depth))
                if n.key == "random_list":
                    bodies = [b.children for b in n.children if b.block and b.key.isdigit()]
                else:
                    bodies = [n.children]
                for body in bodies:
                    clean = tuple(c for c in body if c.key not in CONTROL_METADATA - {"limit"})
                    more, evidence = self.rewards(clean, depth + 1, chain, unconditional)
                    rows.extend(more)
                    public.extend(evidence)
            else:
                more, evidence = super().rewards((n,), depth, chain, unconditional)
                rows.extend(more)
                if n.key == "custom_effect_tooltip":
                    evidence = evidence if more and meaningful_summary(more[0].text) else []
                if n.key in PUBLIC_NATIVE and n.key not in FOCUS.CONCRETE_EFFECTS and unconditional:
                    evidence.append("native:" + n.key)
                public.extend(evidence)
        return rows, public


def actual_effect(nodes, definitions, seen=()):
    """Bookkeeping alone is inert for UI purposes, not for equivalence."""
    for n in nodes:
        if n.key in PRESENTATION or n.key in BOOKKEEPING or n.key in CONTROL_METADATA:
            continue
        if n.key in definitions:
            if n.key in seen:
                raise ValueError("effect cycle while checking actual results: " + " -> ".join((*seen, n.key)))
            if actual_effect(definitions[n.key], definitions, (*seen, n.key)):
                return True
        elif n.block and (n.key == "hidden_effect" or effect_container(n.key)):
            if actual_effect(n.children, definitions, seen):
                return True
        else:
            # Unknown commands may have gameplay; never silently exempt them.
            return True
    return False


STAT = (r"(?:political power|\bPP\b|stability|war support|manpower|research (?:bonus|speed)|"
        r"construction speed|factory output|consumer goods|army experience|navy experience|air experience|"
        r"\u043f\u043e\u043b\u0438\u0442\u0438\u0447\u0435\u0441\u043a\w* \u0432\u043b\u0430\u0441\w*|"
        r"\u0441\u0442\u0430\u0431\u0438\u043b\u044c\u043d\w*|\u043f\u043e\u0434\u0434\u0435\u0440\u0436\w* \u0432\u043e\u0439\u043d\w*|"
        r"\u043f\u043e\u043b\u0438\u0442\u0432\u043b\u0430\u0441\w*)")
NUMBER = r"[+\-\u2212]?\d+(?:[.,]\d+)?\s*%?"
LEAKS = (
    ("quantified gameplay stat", re.compile(rf"(?:{NUMBER}\s+{STAT}|{STAT}\s*[:=+\-\u2212]?\s*{NUMBER})", re.I)),
    ("signed percentage stat", re.compile(r"[+\-\u2212]\d+(?:[.,]\d+)?\s*%")),
    ("raw script identifier", re.compile(r"\b(?:HSM_[\w]+|hsm_ver[\w.]+|(?:set|has|clr)_country_flag|hidden_effect|custom_(?:effect|trigger)_tooltip)\b")),
    ("engine/manual instruction", re.compile(
        r"\b(?:cooldown|tooltip|AI[- ]controlled|human[- ]controlled|engine (?:check|limitation|mechanic)|"
        r"scripted (?:effect|trigger)|country flag|game mechanic|decision (?:can be taken|is available)|"
        r"focus (?:completion|reward)|\u043a\u0443\u043b\u0434\u0430\u0443\u043d\w*|"
        r"\u0434\u0432\u0438\u0436\u043e\u043a|\u0438\u0433\u0440\u043e\u0432\w* \u043c\u0435\u0445\u0430\u043d\u0438\u043a\w*)\b", re.I)),
)


def description_issues(text):
    return [f"{label}: {match.group()!r}" for label, pattern in LEAKS if (match := pattern.search(text))]


def description_keys(record, key):
    explicit = record.all("desc")
    if explicit:
        return tuple(n.value for n in explicit if not n.block) + tuple(
            n.value for block in explicit if block.block for n in block.children if n.key == "text" and not n.block)
    label = record.get("text", key)
    return (label + "_desc",) if isinstance(label, str) else ()


def records(source):
    """Yield actual content definitions, never nested native argument names."""
    seen = set()
    for path, nodes in source.items():
        kind = file_kind(path)
        if kind == "national_focus":
            items = (("focus", k, n) for k, n in FOCUS.focus_records(nodes).items())
        elif kind == "events":
            items = (("event", n.get("id"), n) for n in nodes if n.key in EVENTS and n.block)
        elif kind == "decisions":
            items = (("decision", n.key, n) for category in nodes for n in category.children if n.block)
        elif kind == "categories":
            items = (("category", n.key, n) for n in nodes if n.block)
        else:
            continue
        for typ, key, node in items:
            if not key or (typ, key) in seen:
                raise ValueError(f"{path}:{node.line}: missing/duplicate {typ} ID {key!r}")
            seen.add((typ, key))
            yield path, typ, key, node


def selected_options(event, native=False):
    return tuple(n for n in event.all("option") if not native or related(n.children))


def public_event_keys(event, options):
    result = []
    for n in event.children:
        if n.key in {"title", "desc"}:
            if n.block:
                result.extend(c.value for c in n.children if c.key == "text" and not c.block)
            else:
                result.append(n.value)
    result.extend(n.get("name") for n in options)
    return result


def audit(mod, source, options):
    dependencies = tuple(p for p in (options.game, options.eaw) if p is not None)
    for path in dependencies:
        if not path.is_dir():
            raise ValueError(f"Dependency directory does not exist: {path}")
    triggers = FOCUS.definitions(mod, "scripted_triggers")
    definitions = FOCUS.definitions(mod, "scripted_effects")
    wanted = set()
    for nodes in (*source.values(), *definitions.values()):
        for n in walk(nodes):
            if n.key == "show_ideas_tooltip":
                if n.block:
                    wanted.update(c.key for c in n.children)
                else:
                    wanted.add(n.value)
    # The shared loader reapplies the local definitions after the dependencies.
    ideas = FOCUS.idea_definitions(mod, dependencies, wanted)
    localizations = {lang: Localization.load(mod, lang, dependencies) for lang in ("english", "russian")}
    errors, counts, budgets = [], Counter(), []

    def check_hover(path, key, node, requirements, bodies):
        counts["hovers"] += 1
        for language, loc in localizations.items():
            hover = NarrativeHover(triggers, definitions, ideas, loc, language, options.max_summary_chars)
            block_fields = OPTION_TRIGGERS if node.key == "option" else DECISION_TRIGGERS | DECISION_EFFECTS
            for n in node.children:
                if n.key in block_fields and not n.block:
                    hover.error(f"{n.key} must be a block")
            hover.validate_references(node.children)
            conditions = hover.conditions(requirements)
            rewards = []
            for label, body in bodies:
                more, public = hover.rewards(body)
                rewards.extend(more)
                if actual_effect(body, definitions) and not public:
                    hover.error(f"{label}: actual gameplay has no meaningful visible public result; expose stats, an idea preview or a localized outcome")
            cl, cc = FOCUS.measure(conditions, options.line_width)
            el, ec = FOCUS.measure(rewards, options.line_width)
            if cl > options.max_condition_lines or el > options.max_effect_lines or cl + el > options.max_total_lines:
                hover.error(f"source estimate exceeds budget: conditions {cl}/{options.max_condition_lines}, effects {el}/{options.max_effect_lines}, total {cl + el}/{options.max_total_lines}")
            budgets.append((cl + el, key, language, cl, el, cc + ec))
            errors.extend(f"{path.as_posix()}:{node.line}:{key} [{language}]: {e}" for e in hover.errors)
            counts["external_idea_estimates"] += len(hover.external_ideas)

    for path, typ, key, node in records(source):
        own = key.lower().startswith("hsm_")
        if not own and not related(node.children):
            continue
        if typ == "event":
            selected = selected_options(node, native=path.name == "Avian Events.txt")
            counts["events"] += 1
            counts["options"] += len(selected)
            counts["native_options_skipped"] += len(node.all("option")) - len(selected)
            for lang, loc in localizations.items():
                for loc_key in public_event_keys(node, selected):
                    try:
                        if not loc.resolve(loc_key).strip():
                            raise ValueError(f"empty localization: {loc_key}")
                    except ValueError as exc:
                        errors.append(f"{path.as_posix()}:{node.line}:{key} [{lang}]: {exc}")
            for index, option in enumerate(selected, 1):
                _, body = option_parts(option)
                check_hover(path, f"{key}/{option.get('name', str(index))}", option,
                            hover_requirements(option), [("option effects", body)])
            continue
        counts[{"focus": "focuses", "category": "categories", "decision": "decisions"}[typ]] += 1
        for lang, loc in localizations.items():
            keys = description_keys(node, key)
            if not keys:
                errors.append(f"{path.as_posix()}:{node.line}:{key} [{lang}]: missing description key")
            for desc_key in keys:
                try:
                    text = loc.resolve(desc_key)
                    if not text.strip():
                        raise ValueError(f"empty description: {desc_key}")
                    errors.extend(f"{path.as_posix()}:{node.line}:{desc_key} [{lang}]: {e}" for e in description_issues(text))
                except ValueError as exc:
                    errors.append(f"{path.as_posix()}:{node.line}:{desc_key} [{lang}]: {exc}")
        if typ == "decision":
            requirements = hover_requirements(node)
            bodies = [(n.key, n.children) for n in node.children if n.key in DECISION_EFFECTS]
            check_hover(path, key, node, requirements, bodies)
    if not counts["options"] or not counts["decisions"] or not counts["focuses"]:
        errors.append("No Verenia options, decisions or focuses found; check --mod")
    counts["external_localization_estimates"] = sum(len(loc.external) for loc in localizations.values())
    return errors, counts, budgets


class AnalyzerTests(unittest.TestCase):
    def eq(self, before, after, kind="events"):
        return canonical_file(parse(before), kind) == canonical_file(parse(after), kind)

    def hover(self, scripts="", loc=None, ideas=None, triggers=""):
        return NarrativeHover({n.key: n.children for n in parse(triggers)},
                              {n.key: n.children for n in parse(scripts)}, ideas or {},
                              Localization(loc or {"note": "Gain 25 political power."}), "english")

    def test_option_metadata_separate_from_effects(self):
        before = 'country_event = { id = test.1 option = { name = yes trigger = { tag = ERI } ai_chance = { factor = 5 } add_stability = .1 } }'
        after = before.replace('tag = ERI', 'custom_trigger_tooltip = { tooltip = note tag = ERI }').replace('add_stability = .1', 'custom_effect_tooltip = note hidden_effect = { add_stability = .1 }')
        self.assertTrue(self.eq(before, after))
        for old, new in [('factor = 5', 'factor = 6'), ('name = yes', 'name = no'),
                         ('tag = ERI', 'tag = EYR'), ('add_stability = .1', 'add_stability = .2'),
                         ('ai_chance = { factor = 5 }', 'hidden_effect = { ai_chance = { factor = 5 } }')]:
            with self.subTest(new=new):
                self.assertFalse(self.eq(before, before.replace(old, new)))

    def test_grouping_preserved_under_nonconjunctive_parents(self):
        for parent in ('OR', 'NOT', 'NOR', 'NAND'):
            grouped = parse(f'{parent} = {{ AND = {{ tag = ERI has_war = no }} }}')
            wrapped = parse(f'{parent} = {{ custom_trigger_tooltip = {{ tooltip = note tag = ERI has_war = no }} }}')
            ungrouped = parse(f'{parent} = {{ tag = ERI has_war = no }}')
            with self.subTest(parent=parent):
                self.assertEqual(trigger(grouped), trigger(wrapped))
                self.assertNotEqual(trigger(ungrouped), trigger(wrapped))
                self.assertNotEqual(trigger(parse(f'{parent} = {{}}')),
                                    trigger(parse(f'{parent} = {{ hidden_trigger = {{}} }}')))

    def test_empty_presentation_chain_and_gameplay_chain(self):
        pure = 'if = { limit = { tag = ERI } custom_effect_tooltip = note } else = { show_ideas_tooltip = spirit }'
        self.assertEqual(effects(parse(pure)), ())
        mixed = pure.replace('show_ideas_tooltip = spirit', 'add_stability = .1')
        empty = mixed.replace('custom_effect_tooltip = note', '')
        self.assertEqual(effects(parse(mixed)), effects(parse(empty)))
        self.assertNotEqual(effects(parse(mixed)), effects(parse('else = { add_stability = .1 }')))
        self.assertNotEqual(effects(parse(mixed)), effects(parse(mixed.replace('tag = ERI', 'tag = EYR'))))

    def test_hidden_chain_and_real_limits_never_dropped(self):
        before = 'if = { limit = { tag = ERI } add_stability = .1 } else = { add_political_power = 5 }'
        after = 'custom_effect_tooltip = note hidden_effect = { ' + before + ' }'
        self.assertEqual(effects(parse(before)), effects(parse(after)))
        self.assertNotEqual(effects(parse(before)), effects(parse(before.replace('tag = ERI', 'tag = EYR'))))
        self.assertNotEqual(effects(parse('if = { limit = { tag = ERI } set_country_flag = HSM_done }')), ())
        self.assertNotEqual(effects(parse('random_list = { 10 = {} 90 = { add_stability = .1 } }')),
                            effects(parse('random_list = { 90 = { add_stability = .1 } }')))

    def test_tooltip_only_scopes_removed_but_random_selection_preserved(self):
        raw = 'if = { limit = { has_country_flag = HSM_test } ERI = { show_ideas_tooltip = spirit } }'
        self.assertEqual(effects(parse(raw)), ())
        self.assertNotEqual(effects(parse(raw.replace('ERI', 'random_country'))), ())
        mixed = raw + ' else_if = { limit = { tag = AVI } add_stability = .1 }'
        self.assertNotEqual(effects(parse(mixed)), effects(parse(mixed.replace('HSM_test', 'HSM_changed'))))

    def test_empty_first_and_middle_arms_keep_branch_selection(self):
        raw = 'if = { limit = { tag = ERI } custom_effect_tooltip = note } else_if = { limit = { tag = EYR } custom_effect_tooltip = note } else = { add_stability = .1 }'
        self.assertEqual(len(effects(parse(raw))), 3)
        self.assertNotEqual(effects(parse(raw)), effects(parse('add_stability = .1')))
        self.assertNotEqual(effects(parse(raw)), effects(parse(raw.replace('tag = EYR', 'tag = AVI'))))

    def test_trailing_tooltip_arms_and_empty_preview_scopes_are_presentation(self):
        raw = 'if = { limit = { tag = ERI } add_stability = .1 }'
        extra = ' else_if = { limit = { tag = EYR } custom_effect_tooltip = note } else = { show_ideas_tooltip = spirit }'
        self.assertEqual(effects(parse(raw)), effects(parse(raw + extra)))
        self.assertEqual(effects(parse('ERI = { EYR = { show_ideas_tooltip = spirit } }')), ())

    def test_preserves_native_parameters_repeats_order_and_unknown_commands(self):
        raw = 'add_tech_bonus = { name = bonus tooltip = native uses = 1 category = a category = b bonus = .5 } add_stability = .1 unknown_command = { custom_effect_tooltip = argument }'
        for old, new in [('uses = 1', 'uses = 2'), ('tooltip = native', 'tooltip = changed'),
                         ('category = a category = b', 'category = b category = a'),
                         ('custom_effect_tooltip = argument', '')]:
            with self.subTest(new=new):
                self.assertNotEqual(effects(parse(raw)), effects(parse(raw.replace(old, new))))

    def test_event_metadata_trigger_immediate_after_preserved(self):
        raw = 'add_namespace = test country_event = { id = test.1 title = title desc = { trigger = { tag = ERI } text = desc } picture = pic is_triggered_only = yes timeout_days = 7 trigger = { has_war = no } immediate = { set_country_flag = HSM_seen } option = { name = ack } after = { country_event = { id = test.2 days = 5 } } }'
        for old, new in [('id = test.1', 'id = test.3'), ('title = title', 'title = other'),
                         ('tag = ERI', 'tag = EYR'), ('pic', 'other'), ('timeout_days = 7', 'timeout_days = 8'),
                         ('has_war = no', 'has_war = yes'), ('HSM_seen', 'HSM_other'), ('days = 5', 'days = 6'),
                         ('add_namespace = test', 'add_namespace = changed')]:
            with self.subTest(new=new):
                self.assertFalse(self.eq(raw, raw.replace(old, new)))

    def test_decision_all_fields_and_effect_hooks_preserved(self):
        raw = 'category = { decision = { icon = icon cost = 35 days_re_enable = 90 visible = { tag = ERI } available = { has_war = no } ai_will_do = { factor = 1 } complete_effect = { add_stability = .1 } remove_effect = { add_stability = .2 } timeout_effect = { add_stability = .3 } cancel_effect = { add_stability = .4 } } }'
        wrapped = raw.replace('has_war = no', 'custom_trigger_tooltip = { tooltip = note has_war = no }').replace('add_stability = .1', 'hidden_effect = { add_stability = .1 } custom_effect_tooltip = note')
        self.assertTrue(self.eq(raw, wrapped, 'decisions'))
        for old, new in [('cost = 35', 'cost = 36'), ('days_re_enable = 90', 'days_re_enable = 91'),
                         ('tag = ERI', 'tag = EYR'), ('factor = 1', 'factor = 2'),
                         ('.1', '.5'), ('.2', '.5'), ('.3', '.5'), ('.4', '.5')]:
            with self.subTest(new=new):
                self.assertFalse(self.eq(raw, raw.replace(old, new), 'decisions'))

    def test_file_removals_helpers_and_scalar_fields_cannot_escape(self):
        path = Path('common/scripted_effects/HSM_VER_test.txt')
        before = {path: parse('HSM_VER_test = { add_stability = .1 }')}
        self.assertTrue(compare_sources(before, {})[0])
        self.assertTrue(compare_sources(before, {path: parse('HSM_VER_test = { add_stability = .2 }')})[0])
        self.assertFalse(self.eq('cat = { dec = { available = yes } }', 'cat = { dec = { available = no } }', 'decisions'))
        self.assertFalse(self.eq('cat = { dec = { available = {} } }', 'cat = { dec = { available = {} available = {} } }', 'decisions'))

    def test_acknowledgement_vs_actual_effects(self):
        for raw in ('', 'set_country_flag = HSM_seen', 'hidden_effect = { clr_country_flag = HSM_pending log = ack }'):
            self.assertFalse(actual_effect(parse(raw), {}))
        for raw in ('add_political_power = 5', 'country_event = test.1', 'hidden_effect = { add_stability = .1 }',
                    'if = { limit = { tag = ERI } add_stability = .1 }', 'unknown_command = yes', 'add_to_variable = { x = 5 }'):
            self.assertTrue(actual_effect(parse(raw), {}))
        hover = self.hover(scripts='HSM_VER_gain = { hidden_effect = { add_stability = .1 } }')
        self.assertTrue(actual_effect(parse('HSM_VER_gain = yes'), hover.effects))
        self.assertFalse(hover.rewards(parse('HSM_VER_gain = yes'))[1])
        self.assertTrue(hover.rewards(parse('custom_effect_tooltip = note HSM_VER_gain = yes'))[1])
        self.assertFalse(self.hover(loc={'note': 'Acknowledged.'}).rewards(parse('custom_effect_tooltip = note'))[1])

    def test_guarded_visible_stats_and_recursive_flag_leaks(self):
        hover = self.hover(triggers='HSM_VER_alias = { HSM_VER_inner = yes } HSM_VER_inner = { has_country_flag = HSM_private }')
        self.assertTrue(hover.rewards(parse('if = { limit = { HSM_VER_alias = yes } add_stability = .1 }'))[1])
        self.assertTrue(any('raw HSM flag' in e for e in hover.errors))
        hover = self.hover(triggers='HSM_VER_alias = { has_country_flag = HSM_private }')
        hover.conditions(parse('custom_trigger_tooltip = { tooltip = note HSM_VER_alias = yes }'))
        self.assertEqual(hover.errors, [])
        hover = self.hover(triggers='HSM_VER_a = { HSM_VER_a = yes }')
        hover.conditions(parse('HSM_VER_a = yes'))
        self.assertTrue(any('cycle' in e for e in hover.errors))

    def test_option_visibility_is_not_a_hover_requirement_or_effect(self):
        raw = 'option = { name = ack trigger = { HSM_VER_gate = yes } ai_chance = { factor = 1 } add_stability = .1 }'
        option = parse(raw)[0]
        hover = self.hover(triggers='HSM_VER_gate = { has_country_flag = HSM_private }')
        hover.validate_references(option.children)
        self.assertEqual(hover.conditions(hover_requirements(option)), [])
        _, body = option_parts(option)
        self.assertTrue(hover.rewards(body)[1])
        self.assertEqual(hover.errors, [])
        self.assertNotEqual(canonical_option(option), canonical_option(parse(raw.replace('HSM_VER_gate = yes', 'HSM_VER_gate = no'))[0]))
        hover.rewards(parse('if = { limit = { HSM_VER_gate = yes } add_stability = .1 }'))
        self.assertTrue(any('raw HSM flag' in e for e in hover.errors))

    def test_decision_selection_gates_are_not_hover_requirements(self):
        decision = parse('HSM_VER_decision = { allowed = { has_country_flag = HSM_allowed } visible = { has_country_flag = HSM_visible } target_trigger = { has_country_flag = HSM_target } available = { has_country_flag = HSM_available } }')[0]
        hover = self.hover()
        hover.conditions(hover_requirements(decision))
        self.assertEqual(len(hover.errors), 1)
        self.assertIn('HSM_available', hover.errors[0])

    def test_invisible_tooltip_reference_is_validated_not_called_a_public_leak(self):
        hover = self.hover(loc={'note': 'Debug HSM_VER_private state.'})
        hover.validate_references(parse('trigger = { custom_trigger_tooltip = { tooltip = note has_country_flag = HSM_private } }'))
        self.assertEqual(hover.errors, [])
        hover.conditions(parse('custom_trigger_tooltip = { tooltip = note has_country_flag = HSM_private }'))
        self.assertTrue(any('raw HSM identifier' in e for e in hover.errors))

    def test_native_avian_option_scope_not_event_scope(self):
        event = parse('country_event = { immediate = { HSM_VER_begin = yes } option = { name = unrelated add_stability = .1 } option = { name = touched HSM_VER_finish = yes } }')[0]
        self.assertEqual([n.get('name') for n in selected_options(event, True)], ['touched'])
        self.assertEqual(len(selected_options(event)), 2)

    def test_strict_references_hidden_previews_and_lowercase_event_names(self):
        hover = self.hover()
        hover.validate_references(parse('hidden_effect = { custom_effect_tooltip = HSM_missing show_ideas_tooltip = HSM_missing_idea }'))
        self.assertTrue(any('missing localization' in e for e in hover.errors))
        self.assertTrue(any('missing idea' in e for e in hover.errors))
        with self.assertRaises(ValueError):
            Localization({}, allow_external=True).resolve('hsm_ver_crisis.1.a')
        with self.assertRaises(ValueError):
            Localization({}, allow_external=False).resolve('native_desc')
        loc = Localization({}, allow_external=True)
        self.assertTrue(loc.resolve('native_desc'))
        self.assertIn('native_desc', loc.external)

    def test_idea_preview_and_localized_alias_expansion(self):
        spirit = parse('spirit = { modifier = { stability_factor = .1 } }')[0]
        hover = self.hover(ideas={'spirit': spirit}, loc={'spirit': 'Civilian Compact', 'note': '$detail$', 'detail': 'Gain 25 political power.'})
        rows, public = hover.rewards(parse('show_ideas_tooltip = spirit custom_effect_tooltip = note'))
        self.assertEqual(len(rows), 3)
        self.assertTrue(public)
        self.assertEqual(hover.errors, [])
        with self.assertRaises(ValueError):
            Localization({'a': '$b$', 'b': '$a$'}).resolve('a')
        hover = self.hover(loc={'note': 'Set HSM_VER_private to proceed.'})
        hover.rewards(parse('custom_effect_tooltip = note'))
        self.assertTrue(any('raw HSM identifier' in e for e in hover.errors))

    def test_description_missing_key_is_strict_and_explicit_keys_used(self):
        explicit = parse('focus = { id = HSM_test desc = alternate }')[0]
        self.assertEqual(description_keys(explicit, 'HSM_test'), ('alternate',))
        loc = Localization({'HSM_test': 'Present title'}, allow_external=True)
        with self.assertRaises(ValueError):
            loc.resolve(description_keys(parse('focus = { id = HSM_test }')[0], 'HSM_test')[0])

    def test_source_budget_is_localized_and_counts_all_guarded_branches(self):
        hover = self.hover(loc={'note': 'A detailed result. ' * 60})
        rows, _ = hover.rewards(parse('if = { limit = { tag = ERI } custom_effect_tooltip = note } else = { custom_effect_tooltip = note }'))
        lines, chars = FOCUS.measure(rows, 72)
        self.assertGreater(lines, 30)
        self.assertGreater(chars, 1200)
        self.assertTrue(any('character budget' in e for e in hover.errors))

    def test_actual_description_keys_and_story_numbers(self):
        node = parse('focus = { id = HSM_test completion_reward = { add_tech_bonus = { name = bonus } } }')[0]
        self.assertEqual(description_keys(node, 'HSM_test'), ('HSM_test_desc',))
        for text in ('In 1012, Grover VI read the letters on 23 October.',
                     'Three engineers spent 90 days repairing the bridge.',
                     'Katrina asks whether stability can survive another winter.',
                     '\u0413\u0440\u043e\u0432\u0435\u0440 VI \u0432 1012 \u0433\u043e\u0434\u0443 \u0432\u0441\u0442\u0440\u0435\u0442\u0438\u043b \u0438\u043d\u0436\u0435\u043d\u0435\u0440\u0430.'):
            self.assertEqual(description_issues(text), [])
        for text in ('Spend 35 political power.', 'Grants +5% stability.', 'The cooldown is 90 days.',
                     'AI-controlled Erie accepts.', 'Set HSM_VER_private.',
                     '35 \u043f\u043e\u043b\u0438\u0442\u0438\u0447\u0435\u0441\u043a\u043e\u0439 \u0432\u043b\u0430\u0441\u0442\u0438.'):
            self.assertTrue(description_issues(text), text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mod', type=Path, default=ROOT / 'mod/HoISubmod')
    parser.add_argument('--baseline', type=Path, default=ROOT / 'outputs/qa/verenia-narrative-before')
    parser.add_argument('--eaw', type=Path, help='optional Equestria at War root, as in Test-VereniaFocusUI.py')
    parser.add_argument('--game', type=Path, help='optional HOI4 root; precedence game < EAW < submod')
    parser.add_argument('--self-test', action='store_true')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--equivalence-only', action='store_true')
    mode.add_argument('--ui-only', action='store_true', help='audit current UI after intentional gameplay changes; do not compare or rewrite the historical baseline')
    parser.add_argument('--line-width', type=int, default=72)
    parser.add_argument('--max-condition-lines', type=int, default=18)
    parser.add_argument('--max-effect-lines', type=int, default=18)
    parser.add_argument('--max-total-lines', type=int, default=30)
    parser.add_argument('--max-summary-chars', type=int, default=600)
    parser.add_argument('--top', type=int, default=8)
    parser.add_argument('--max-errors', type=int, default=40, help='maximum detailed failures to print; 0 prints all')
    parser.add_argument('-q', '--quiet', action='store_true')
    options = parser.parse_args(argv)
    if min(options.line_width, options.max_condition_lines, options.max_effect_lines,
           options.max_total_lines, options.max_summary_chars) < 1 or min(options.top, options.max_errors) < 0:
        parser.error('budgets must be positive; --top and --max-errors nonnegative')
    result = unittest.TextTestRunner(verbosity=1 if options.quiet else 2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(AnalyzerTests))
    if not result.wasSuccessful():
        return 1
    if options.self_test:
        return 0
    try:
        source = sources(options.mod)
        if options.ui_only:
            errors = []
            print('SKIP historical baseline equivalence (--ui-only); no baseline files changed.')
        else:
            errors, compared = compare_sources(sources(options.baseline), source)
            print(f'Baseline equivalence: {sum(compared.values())} game script files compared; {len(errors)} violations.')
            print('  ' + ', '.join(f'{kind}={count}' for kind, count in sorted(compared.items())))
        if not options.equivalence_only:
            failures, counts, budgets = audit(options.mod, source, options)
            errors.extend(failures)
            print(f'UI audit: {counts["options"]} options, {counts["decisions"]} decisions; descriptions: {counts["focuses"]} focuses, {counts["categories"]} categories; EN/RU checked.')
            print(f'Native Avian: only HSM-related options audited; {counts["native_options_skipped"]} unrelated options skipped in related events.')
            if options.game is None and options.eaw is None:
                print(f'SKIP external reference verification: {counts["external_localization_estimates"]} localization references and {counts["external_idea_estimates"]} idea occurrences estimated. Supply --eaw/--game for strict checks.')
            else:
                print('Strict external localization/idea reference verification enabled (game < EAW < submod).')
            print(f'SOURCE ESTIMATES ONLY: {options.line_width} columns; condition/effect/total budgets {options.max_condition_lines}/{options.max_effect_lines}/{options.max_total_lines}; no engine rendering.')
            for total, key, language, cl, el, chars in sorted(budgets, reverse=True)[:options.top]:
                print(f'  {key} [{language}]: {cl} condition + {el} effect = {total} lines; {chars} characters')
        for error in errors[:options.max_errors or None]:
            print('FAIL ' + error)
        if options.max_errors and len(errors) > options.max_errors:
            print(f'  {len(errors) - options.max_errors} further violations omitted; --max-errors 0 prints all.')
        print(f'{"FAIL" if errors else "PASS"}: {len(errors)} static QA violations.')
        return int(bool(errors))
    except (ValueError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
