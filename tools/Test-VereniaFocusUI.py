"""Portable static hover QA, not an HOI4 renderer or gameplay interpreter.

Run: python -B -X utf8 tools/Test-VereniaFocusUI.py [--baseline ORIGINALS]
     [--eaw EAW_ROOT] [--game HOI4_ROOT]
Use --self-test for the analyzer's synthetic regressions only. No game install,
third-party packages, output files, or production edits are required. ORIGINALS
may contain flat focus *.txt copies or a common/national_focus directory.
Without it, equivalence is explicitly SKIPPED; the UI checks still run.

Budget policy: wrap localized text at 72 character columns, retain explicit
newlines, reserve 24 columns for dynamic names, and estimate native rows at
48 EN / 60 RU columns plus localized arguments. This is a repeatable source
budget, NOT pixel measurement, actual engine output, or proof of screenshot fit.
All potentially visible conditional branches count toward the budget. Events
are not expanded into their future choices. Descriptions are not hover results.
Individual custom effect summaries also have a 600-character editorial limit.
Unresolved non-HSM localization/ideas use explicit estimates when neither
dependency is supplied; supplying sources enables strict reference validation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import difflib
import json
from pathlib import Path
import re
import sys
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
PREFIXES = ("HSM_VER", "HSM_ERI", "HSM_EYR", "HSM_AVI", "HSM_ZYP")
REWARD_FIELDS = ("completion_reward", "completion_reward_joint_originator", "completion_reward_joint_member")
FIELDS = ("available", "bypass", *REWARD_FIELDS)
OPERATORS = {"=", "<", ">", "<=", ">=", "!=", "?="}
TOKEN = re.compile(r'\s+|#[^\n]*|"(?:\\.|[^"\\])*"|[{}]|[<>!?=]+|[^\s{}=<>!?#"]+')
LOC_LINE = re.compile(r'^\s*([^\s:#]+):\d*\s+"((?:\\.|[^"\\])*)"\s*(?:#.*)?$')
SUBSTITUTION = re.compile(r'\$([^$|]+)(?:\|[^$]*)?\$')
PRESENTATION_EFFECTS = {"custom_effect_tooltip", "show_ideas_tooltip"}
TRIGGER_WRAPPERS = {"custom_trigger_tooltip", "hidden_trigger"}
BOOLEAN_GROUPS = {"AND", "OR", "NOT", "NOR", "NAND"}
FLAG_TESTS = {"has_country_flag", "has_global_flag", "has_state_flag", "has_unit_leader_flag", "has_character_flag"}
# A deliberately explicit allowlist: unknown commands never prove a public reward.
CONCRETE_EFFECTS = {
    "add_political_power", "add_stability", "add_war_support", "add_manpower",
    "army_experience", "navy_experience", "air_experience", "add_command_power",
    "add_tech_bonus", "add_doctrine_cost_reduction", "add_research_slot",
    "add_ideas", "add_timed_idea", "swap_ideas", "remove_ideas",
    "add_building_construction", "add_extra_state_shared_building_slots",
    "add_equipment_to_stockpile", "add_resource", "add_state_core",
    "add_state_claim", "create_wargoal", "create_faction", "add_to_faction",
    "add_offsite_building", "add_opinion_modifier", "set_rule",
}
SILENT_EFFECTS = {
    "set_country_flag", "clr_country_flag", "set_global_flag", "clr_global_flag",
    "set_state_flag", "clr_state_flag", "set_variable", "add_to_variable",
    "subtract_from_variable", "set_temp_variable", "add_to_temp_variable", "log",
}
EVENT_EFFECTS = {"country_event", "news_event", "state_event", "unit_leader_event"}
GUARDED_EFFECTS = {"if", "else_if", "else", "random", "random_list", "while", "for_loop", "for_each_scope_loop"}


@dataclass(frozen=True)
class Node:
    key: str
    op: str = ""
    value: str | tuple["Node", ...] = ""
    line: int = 0

    @property
    def children(self):
        return self.value if isinstance(self.value, tuple) else ()

    @property
    def block(self):
        return isinstance(self.value, tuple)

    def all(self, key):
        return tuple(n for n in self.children if n.key == key)

    def get(self, key, default=""):
        found = self.all(key)
        return found[0].value if found else default


def parse(text, source="<fixture>"):
    """Ordered Clausewitz AST, including repeated keys, operators and bare lists."""
    tokens = []
    end, line = 0, 1
    for match in TOKEN.finditer(text.lstrip("\ufeff")):
        if match.start() != end:
            raise ValueError(f"{source}:{line}: invalid token or unterminated quote")
        token = match.group()
        if not token.isspace() and not token.startswith("#"):
            tokens.append((token, line))
        line += token.count("\n")
        end = match.end()
    if end != len(text.lstrip("\ufeff")):
        raise ValueError(f"{source}:{line}: invalid trailing token")
    pos = 0

    def atom(token):
        # Preserve escape sequences. Only syntactic quote delimiters disappear.
        return token[1:-1] if token.startswith('"') else token

    def block(nested=False):
        nonlocal pos
        result = []
        while pos < len(tokens):
            key, number = tokens[pos]
            pos += 1
            if key == "}" and nested:
                return tuple(result)
            if key in ("{", "}") or re.fullmatch(r'[<>!?=]+', key):
                raise ValueError(f"{source}:{number}: unexpected {key}")
            op, value = "", ""
            if pos < len(tokens) and re.fullmatch(r'[<>!?=]+', tokens[pos][0]):
                op = tokens[pos][0]
                pos += 1
                if op not in OPERATORS or pos == len(tokens) or tokens[pos][0] == "}":
                    raise ValueError(f"{source}:{number}: invalid assignment to {key}")
                raw = tokens[pos][0]
                pos += 1
                if raw in OPERATORS:
                    raise ValueError(f"{source}:{number}: missing value for {key}")
                value = block(True) if raw == "{" else atom(raw)
            result.append(Node(atom(key), op, value, number))
        if nested:
            raise ValueError(f"{source}:{line}: unclosed block")
        return tuple(result)

    return block()


def read(path):
    return parse(path.read_text(encoding="utf-8-sig"), str(path))


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.children)


def canonical(nodes, mode="trigger", parent="AND"):
    """Remove only presentation syntax, never sort/deduplicate gameplay nodes.

    A trigger wrapper implicitly ANDs its children. Splicing several children
    directly into OR/NOT would change that logic, so retain an AND in that case.
    Explicit boolean blocks and all native parameters remain intact.
    """
    result = []
    for n in nodes:
        if mode == "effect" and n.key in PRESENTATION_EFFECTS:
            continue
        if mode == "effect" and n.key == "hidden_effect" and n.block:
            result.extend(canonical(n.children, mode, parent))
            continue
        if mode == "trigger" and n.key in TRIGGER_WRAPPERS and n.block:
            children = n.children
            if n.key == "custom_trigger_tooltip":
                children = tuple(c for c in children if c.key != "tooltip")
            stripped = canonical(children, mode, "AND")
            if parent in {"OR", "NOT", "NOR", "NAND"} and len(stripped) != 1:
                result.append(("AND", "=", stripped))
            else:
                result.extend(stripped)
            continue
        child_mode = "trigger" if mode == "effect" and n.key in {"limit", "trigger"} else mode
        value = canonical(n.children, child_mode, n.key) if n.block else n.value
        result.append((n.key, n.op, value))
    return tuple(result)


def focus_records(nodes):
    found = {}
    for n in walk(nodes):
        if n.key in {"focus", "shared_focus", "joint_focus"} and n.block:
            key = n.get("id")
            if not key or key in found:
                raise ValueError(f"missing/duplicate focus ID: {key!r}, line {n.line}")
            found[key] = n
    return found


def sections(focus, field):
    return tuple(c for n in focus.all(field) for c in n.children)


def reward_sections(focus):
    # Include both joint roles conservatively in the hover budget; neither may
    # hide an unresolved tooltip or silently disappear from static validation.
    return tuple(c for field in REWARD_FIELDS for c in sections(focus, field))


def inert_legacy(focus):
    disabled = (("always", "=", "no"),)
    return (canonical(sections(focus, "allow_branch")) == disabled
            and canonical(sections(focus, "available")) == disabled
            and not canonical(reward_sections(focus), "effect"))


def focus_paths(mod):
    return sorted(p for p in (mod / "common/national_focus").glob("*.txt")
                  if p.name.startswith(PREFIXES) or p.name == "AVI.txt")


def definitions(mod, folder):
    found = {}
    for path in sorted((mod / "common" / folder).glob("*.txt")):
        for node in read(path):
            if node.block:
                if node.key in found:
                    raise ValueError(f"Duplicate {folder} definition {node.key}: {path}")
                found[node.key] = node.children
    return found


def idea_definitions(mod, dependencies=(), wanted=()):
    found = {}
    # Parse local ideas strictly. Read upstream files only for referenced ideas
    # not overridden locally, so unrelated native syntax cannot break this QA.
    local = {}
    for source in (mod, *dependencies):
        seen = set()
        needed = set(wanted) - local.keys()
        candidate = re.compile(r'(?m)^\s*(?:' + '|'.join(re.escape(k) for k in sorted(needed)) + r')\s*=') if needed else None
        if source != mod and candidate is None:
            continue
        for path in sorted((source / "common/ideas").glob("*.txt")):
            text = path.read_text(encoding="utf-8-sig")
            if source != mod and not candidate.search(text):
                continue
            for root in parse(text, str(path)):
                if root.key == "ideas":
                    for category in root.children:
                        for idea in category.children:
                            if idea.block:
                                if source == mod and idea.key in seen:
                                    raise ValueError(f"Duplicate idea {idea.key}: {path}")
                                seen.add(idea.key)
                                found[idea.key] = idea
        if source == mod:
            local = dict(found)
    found.update(local)
    return found


class Localization:
    def __init__(self, values, allow_external=False):
        self.values = values
        self.cache = {}
        self.allow_external = allow_external
        self.external = set()
        self.estimated = set()

    @classmethod
    def load(cls, mod, language, dependencies=()):
        values = {}
        for source in (*dependencies, mod):
            seen = set()
            for path in sorted((source / "localisation").rglob(f"*l_{language}.yml")):
                for line in path.read_text(encoding="utf-8-sig").splitlines():
                    match = LOC_LINE.fullmatch(line)
                    if match:
                        key, value = match.groups()
                        if source == mod and key.startswith(PREFIXES) and key in seen:
                            raise ValueError(f"Duplicate {language} localization {key}: {path}")
                        seen.add(key)
                        values[key] = value
        return cls(values, allow_external=not dependencies)

    def resolve(self, key, stack=()):
        if key in stack:
            raise ValueError("localization cycle: " + " -> ".join((*stack, key)))
        if key in self.cache:
            if key in self.estimated:
                self.estimated.update(stack)
            return self.cache[key]
        if key not in self.values:
            if self.allow_external and not key.startswith("HSM_"):
                self.external.add(key)
                self.estimated.update((*stack, key))
                return "X" * 24
            raise ValueError(f"missing localization: {key}")
        text = SUBSTITUTION.sub(lambda m: self.resolve(m[1], (*stack, key)), self.values[key])
        text = re.sub(r'\\([nrt"\\])', lambda m: {"n": "\n", "r": "", "t": " ", '"': '"', "\\": "\\"}[m[1]], text)
        text = re.sub(r'\u00a7.', '', text)
        text = re.sub(r'\[[^]\n]+\]', 'X' * 24, text)
        text = re.sub(r'\u00a3[^\s\u00a3]+\u00a3?', 'XX', text)
        if len(text) > 100000:
            raise ValueError(f"localization expansion exceeds 100000 characters: {key}")
        self.cache[key] = text
        return text


@dataclass(frozen=True)
class Row:
    text: str
    depth: int = 0
    estimated: bool = False


def measure(rows, width):
    lines = 0
    chars = 0
    for row in rows:
        chars += len(row.text)
        usable = max(16, width - 2 * row.depth)
        for paragraph in row.text.split("\n"):
            lines += max(1, len(textwrap.wrap(paragraph, usable, break_long_words=True, break_on_hyphens=False)))
    return lines, chars


class Hover:
    def __init__(self, triggers, effects, ideas, loc, language, max_summary_chars=600):
        self.triggers, self.effects, self.ideas = triggers, effects, ideas
        self.loc, self.language = loc, language
        self.errors = []
        self.visits = 0
        self.max_summary_chars = max_summary_chars
        self.external_ideas = set()

    def error(self, text):
        if text not in self.errors:
            self.errors.append(text)

    def enter(self, node, chain):
        self.visits += 1
        if self.visits > 20000 or len(chain) > 64:
            raise ValueError("visible script expansion exceeds safety budget")
        if node.key in chain:
            self.error("script cycle: " + " -> ".join((*chain, node.key)))
            return False
        return True

    def localized(self, key):
        try:
            text = self.loc.resolve(key)
            if not text.strip():
                self.error(f"empty public localization: {key}")
            return text
        except ValueError as exc:
            self.error(str(exc))
            return ""

    def native(self, node, depth):
        # Native templates belong to the game/upstream mod. Count a transparent
        # allowance, plus any locally known names; do not invent renderer text.
        text = "N" * (60 if self.language == "russian" else 48)
        for child in (node, *node.children):
            if isinstance(child.value, str) and child.value in self.loc.values:
                text += " " + self.localized(child.value)
        return Row(text, depth, True)

    def conditions(self, nodes, depth=0, chain=()):
        rows = []
        for n in nodes:
            if not self.enter(n, chain):
                continue
            if n.key == "hidden_trigger":
                continue
            if n.key == "custom_trigger_tooltip":
                keys = n.all("tooltip")
                if len(keys) != 1 or not isinstance(keys[0].value, str):
                    self.error(f"line {n.line}: custom_trigger_tooltip needs one tooltip key")
                else:
                    key = keys[0].value
                    text = self.localized(key)
                    rows.append(Row(text, depth, key in self.loc.estimated))
                continue
            if n.key in self.triggers:
                if n.value == "no":
                    rows.append(self.native(Node("NOT"), depth))
                rows.extend(self.conditions(self.triggers[n.key], depth, (*chain, n.key)))
                continue
            if n.key.startswith(PREFIXES):
                self.error(f"unresolved scripted trigger: {n.key}")
            if n.key in FLAG_TESTS:
                flag = n.get("flag") if n.block else n.value
                if isinstance(flag, str) and flag.startswith("HSM_"):
                    via = " -> ".join(chain) or "focus"
                    self.error(f"raw HSM flag escapes custom_trigger_tooltip: {flag} (via {via}, line {n.line})")
            rows.append(self.native(n, depth))
            # Boolean/scoped conditions expand; native parameter blocks do not.
            if n.block and (n.key in BOOLEAN_GROUPS or is_scope(n.key)
                            or n.key.startswith(("any_", "all_"))
                            or n.key in {"if", "else_if", "else", "limit"}):
                rows.extend(self.conditions(n.children, depth + 1, chain))
        return rows

    def idea_rows(self, node, depth):
        if node.block and any(c.op for c in node.children):
            self.error("show_ideas_tooltip must use an idea ID or bare ID list")
            return []
        ids = [c.key for c in node.children] if node.block else [node.value]
        rows = []
        for key in ids:
            if key not in self.ideas:
                if self.loc.allow_external and not key.startswith("HSM_"):
                    self.external_ideas.add(key)
                    rows.append(self.native(node, depth))
                    continue
                self.error(f"show_ideas_tooltip references missing idea definition: {key}")
                continue
            idea = self.ideas[key]
            name = idea.get("name", key)
            text = self.localized(name)
            rows.append(Row(text, depth, name in self.loc.estimated))
            # Idea descriptions are not reliably shown by this effect. Its name
            # and modifier rows are; count modifiers, including conditional ones.
            for item in walk(idea.children):
                if item.key in {"modifier", "equipment_bonus", "research_bonus", "targeted_modifier"}:
                    rows.extend(self.native(m, depth + 1) for m in item.children)
        return rows

    def validate_idea_references(self, nodes, seen=None):
        """Validate even hidden previews without using them as public evidence."""
        seen = set() if seen is None else seen
        for node in walk(nodes):
            if node.key == "show_ideas_tooltip":
                self.idea_rows(node, 0)
            elif node.key in self.effects and node.key not in seen:
                seen.add(node.key)
                self.validate_idea_references(self.effects[node.key], seen)

    def rewards(self, nodes, depth=0, chain=(), unconditional=True):
        rows, public = [], []
        for n in nodes:
            if not self.enter(n, chain):
                continue
            if n.key == "hidden_effect":
                continue
            if n.key == "custom_effect_tooltip":
                key = n.get("localization_key") if n.block else n.value
                text = self.localized(key)
                rows.append(Row(text, depth, key in self.loc.estimated))
                if len(text) > self.max_summary_chars:
                    self.error(f"effect summary {key} exceeds character budget: {len(text)}/{self.max_summary_chars}")
                if text.strip() and unconditional:
                    public.append("summary:" + key)
            elif n.key == "show_ideas_tooltip":
                before = len(self.errors)
                idea_rows = self.idea_rows(n, depth)
                rows.extend(idea_rows)
                # A guarded native preview is still a visible result, just as a
                # guarded add_ideas effect is. Hidden effects were skipped above.
                if idea_rows and len(self.errors) == before and all(r.text.strip() for r in idea_rows):
                    public.append("idea preview")
            elif n.key in self.effects:
                more, evidence = self.rewards(self.effects[n.key], depth, (*chain, n.key), unconditional)
                rows.extend(more)
                public.extend(evidence)
            elif n.key in SILENT_EFFECTS:
                continue
            elif n.key == "limit":
                rows.extend(self.conditions(n.children, depth + 1))
            elif n.key in GUARDED_EFFECTS or n.key.startswith(("every_", "random_", "any_")):
                rows.append(self.native(n, depth))
                more, evidence = self.rewards(n.children, depth + 1, chain, False)
                rows.extend(more)
                public.extend(evidence)
            elif n.block and (is_scope(n.key) or n.key == "effect_tooltip"):
                if n.key != "effect_tooltip":
                    rows.append(self.native(n, depth))
                more, evidence = self.rewards(n.children, depth + 1, chain, unconditional)
                rows.extend(more)
                public.extend(evidence)
            else:
                if n.key.startswith(PREFIXES):
                    self.error(f"unresolved scripted effect: {n.key}")
                rows.append(self.native(n, depth))
                # Native guarded rewards and event notifications are visible
                # results; they do not need a prose duplicate to qualify.
                if n.key in CONCRETE_EFFECTS:
                    public.append("native:" + n.key)
                elif n.key in EVENT_EFFECTS:
                    event_id = n.get("id") if n.block else n.value
                    if isinstance(event_id, str) and event_id:
                        public.append("event:" + event_id)
                    else:
                        self.error(f"line {n.line}: event notification needs an event ID")
        return rows, public


def is_scope(key):
    return bool(re.fullmatch(r'[A-Z][A-Z0-9]{2}|\d+|(?:ROOT|FROM|PREV|THIS)(?:\.(?:FROM|PREV))*', key)) or key in {"owner", "controller", "capital_scope", "overlord"}


def compare_focus(before, after):
    errors = []

    def changed(label, old, new):
        if old != new:
            delta = list(difflib.unified_diff(
                json.dumps(old, indent=1).splitlines(), json.dumps(new, indent=1).splitlines(),
                fromfile="before", tofile="after", lineterm="", n=2))
            errors.append(f"{label}: semantic/order change\n" + "\n".join(delta[:36]))

    # Metadata is opaque: no wrapper removal, sorting, or folding.
    changed("metadata", canonical(tuple(n for n in before.children if n.key not in FIELDS), "metadata"),
            canonical(tuple(n for n in after.children if n.key not in FIELDS), "metadata"))
    for field in FIELDS:
        mode = "effect" if field in REWARD_FIELDS else "trigger"
        # Preserve field presence, duplicates, and field-level operators too.
        old = tuple((n.op, canonical(n.children, mode) if n.block else n.value) for n in before.all(field))
        new = tuple((n.op, canonical(n.children, mode) if n.block else n.value) for n in after.all(field))
        changed(field, old, new)
    return errors


def compare_baseline(directory, paths):
    if not directory.is_dir():
        raise ValueError(f"Baseline directory does not exist: {directory}")
    files = list(directory.rglob("*.txt"))
    errors, count = [], 0
    current_names = {p.name for p in paths}
    for original in files:
        if (original.name.startswith(PREFIXES) or original.name == "AVI.txt") and original.name not in current_names:
            errors.append(f"{original.name}: baseline focus file removed")
    for path in paths:
        matches = [p for p in files if p.name == path.name]
        if len(matches) != 1:
            errors.append(f"{path.name}: expected one original baseline file, found {len(matches)}")
            continue
        old, new = focus_records(read(matches[0])), focus_records(read(path))
        for key in sorted(old.keys() | new.keys()):
            if key not in old or key not in new:
                errors.append(f"{path.name}:{key}: focus {'added' if key not in old else 'removed'}")
            else:
                count += 1
                errors.extend(f"{path.name}:{new[key].line}:{key}: {error}" for error in compare_focus(old[key], new[key]))
    return errors, count


def audit(mod, paths, options):
    triggers = definitions(mod, "scripted_triggers")
    effects = definitions(mod, "scripted_effects")
    dependencies = tuple(p for p in (options.game, options.eaw) if p is not None)
    for path in dependencies:
        if not path.is_dir():
            raise ValueError(f"Dependency directory does not exist: {path}")
    wanted = set()
    for nodes in [*(read(path) for path in paths), *effects.values()]:
        for node in walk(nodes):
            if node.key == "show_ideas_tooltip":
                if node.block:
                    wanted.update(c.key for c in node.children)
                else:
                    wanted.add(node.value)
    ideas = idea_definitions(mod, dependencies, wanted)
    localizations = {lang: Localization.load(mod, lang, dependencies) for lang in ("english", "russian")}
    errors, budgets = [], []
    counts = Counter()
    seen = set()
    for path in paths:
        for key, focus in focus_records(read(path)).items():
            if key in seen:
                errors.append(f"{path.name}:{focus.line}: duplicate focus {key}")
            seen.add(key)
            own = key.startswith(PREFIXES)
            related = any(n.key.startswith(PREFIXES) or isinstance(n.value, str) and n.value.startswith(PREFIXES)
                          for field in FIELDS for n in walk(sections(focus, field)))
            if not own and not related:
                continue
            counts["focuses"] += 1
            if inert_legacy(focus):
                counts["inert_legacy"] += 1
                continue
            for language, loc in localizations.items():
                hover = Hover(triggers, effects, ideas, loc, language, options.max_summary_chars)
                for field in FIELDS:
                    if any(not n.block for n in focus.all(field)):
                        hover.error(f"{field} must be a block")
                hover.validate_idea_references(reward_sections(focus))
                conditions = []
                for field in ("available", "bypass"):
                    conditions.extend(hover.conditions(sections(focus, field)))
                rewards, public = hover.rewards(reward_sections(focus))
                if own and not public:
                    hover.error("no visible public completion result; expose a native reward, event notification or idea preview, or add a brief localized summary for complex effects")
                cl, cc = measure(conditions, options.line_width)
                el, ec = measure(rewards, options.line_width)
                budgets.append((cl + el, key, language, cl, el, cc + ec,
                                sum(r.estimated for r in (*conditions, *rewards))))
                if cl > options.max_condition_lines or el > options.max_effect_lines or cl + el > options.max_total_lines:
                    hover.error(f"estimated hover budget exceeded: conditions {cl}/{options.max_condition_lines}, effects {el}/{options.max_effect_lines}, total {cl + el}/{options.max_total_lines} lines; {cc + ec} characters")
                errors.extend(f"{path.name}:{focus.line}:{key} [{language}]: {error}" for error in hover.errors)
                counts["external_idea_estimates"] += len(hover.external_ideas)
    if not counts["focuses"]:
        errors.append("No Verenia focuses found; check --mod")
    counts["external_localization_estimates"] = sum(len(loc.external) for loc in localizations.values())
    return errors, counts, budgets


class AnalyzerTests(unittest.TestCase):
    def test_joint_focus_rewards_and_both_roles_are_inspected(self):
        node = parse('joint_focus = { id = HSM_joint completion_reward = {} completion_reward_joint_originator = { add_stability = .05 } completion_reward_joint_member = { custom_effect_tooltip = missing_joint_text } }')[0]
        self.assertIn("HSM_joint", focus_records((node,)))
        hover = self.hover()
        rows, public = hover.rewards(reward_sections(node))
        self.assertTrue(public)
        self.assertTrue(rows)
        self.assertTrue(any("missing_joint_text" in error for error in hover.errors))

    def hover(self, triggers="", effects="", ideas=None, loc=None):
        return Hover({n.key: n.children for n in parse(triggers)},
                     {n.key: n.children for n in parse(effects)}, ideas or {},
                     Localization(loc or {"note": "A public result."}), "english")

    def test_parser_preserves_comments_strings_duplicates_operators_lists(self):
        nodes = parse('x = { name = "a # } \\" b" category = a category = b days > 2 list = { a b } } # ignored')
        self.assertEqual([n.value for n in nodes[0].all("category")], ["a", "b"])
        self.assertEqual(nodes[0].all("days")[0].op, ">")
        self.assertEqual(nodes[0].get("name"), 'a # } \\" b')
        self.assertEqual(nodes[0].get("list")[1].key, "b")
        for bad in ('x = {', 'x = }', 'x =', 'x = "bad', '} x = 1', 'x == 1'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse(bad)

    def test_canonical_removes_only_presentation(self):
        old = parse('has_war = no NOT = { has_country_flag = HSM_a OR = { tag = ERI tag = EYR } }')
        new = parse('custom_trigger_tooltip = { tooltip = note has_war = no hidden_trigger = { NOT = { has_country_flag = HSM_a OR = { tag = ERI tag = EYR } } } }')
        self.assertEqual(canonical(old), canonical(new))
        self.assertNotEqual(canonical(old), canonical(parse('NOT = { has_country_flag = HSM_a }')))
        old = parse('if = { limit = { tag = ERI } country_event = { id = evt.1 days = 2 } } else = { add_tech_bonus = { name = bonus tooltip = native bonus = .5 uses = 2 category = a category = b } }')
        new = parse('custom_effect_tooltip = note hidden_effect = { if = { limit = { custom_trigger_tooltip = { tooltip = note tag = ERI } } country_event = { id = evt.1 days = 2 } } else = { add_tech_bonus = { name = bonus tooltip = native bonus = .5 uses = 2 category = a category = b } } } show_ideas_tooltip = spirit')
        self.assertEqual(canonical(old, "effect"), canonical(new, "effect"))
        for changed in ('days = 3', 'id = evt.2', 'tooltip = changed', 'name = different', 'uses = 3', 'category = c'):
            original = {'days': 'days = 2', 'id': 'id = evt.1', 'tooltip': 'tooltip = native', 'name': 'name = bonus', 'uses': 'uses = 2', 'category': 'category = b'}[changed.split()[0]]
            with self.subTest(changed=changed):
                raw = 'if = { limit = { tag = ERI } country_event = { id = evt.1 days = 2 } } else = { add_tech_bonus = { name = bonus tooltip = native bonus = .5 uses = 2 category = a category = b } }'
                self.assertNotEqual(canonical(old, "effect"), canonical(parse(raw.replace(original, changed)), "effect"))

    def test_boolean_grouping_order_and_negative_calls_are_not_erased(self):
        for parent in ("OR", "NOT", "NOR", "NAND"):
            with self.subTest(parent=parent):
                plain = parse(f'{parent} = {{ tag = ERI has_war = no }}')
                wrapped = parse(f'{parent} = {{ custom_trigger_tooltip = {{ tooltip = note tag = ERI has_war = no }} }}')
                grouped = parse(f'{parent} = {{ AND = {{ tag = ERI has_war = no }} }}')
                self.assertNotEqual(canonical(plain), canonical(wrapped))
                self.assertEqual(canonical(grouped), canonical(wrapped))
                self.assertNotEqual(canonical(parse(f'{parent} = {{}}')), canonical(parse(f'{parent} = {{ hidden_trigger = {{}} }}')))
        self.assertNotEqual(canonical(parse('HSM_ref = yes')), canonical(parse('HSM_ref = no')))
        self.assertNotEqual(canonical(parse('a = 1 b = 2')), canonical(parse('b = 2 a = 1')))
        self.assertNotEqual(canonical(parse('OR = { a = 1 b = 2 }')), canonical(parse('AND = { a = 1 b = 2 }')))

    def test_recursive_triggers_expand_until_wrappers(self):
        hover = self.hover('HSM_VER_a = { HSM_VER_b = yes } HSM_VER_b = { tag = ERI custom_trigger_tooltip = { tooltip = note HSM_VER_a = yes has_country_flag = HSM_private } }')
        self.assertEqual(len(hover.conditions(parse('HSM_VER_a = yes'))), 2)
        self.assertEqual(hover.errors, [])
        hover = self.hover('HSM_VER_a = { HSM_VER_b = no } HSM_VER_b = { NOT = { ERI = { has_country_flag = { flag = HSM_private days > 2 } } } }')
        hover.conditions(parse('HSM_VER_a = yes'))
        self.assertTrue(any('raw HSM flag' in e and 'HSM_VER_a -> HSM_VER_b' in e for e in hover.errors))
        hover = self.hover('HSM_VER_a = { HSM_VER_b = yes } HSM_VER_b = { HSM_VER_a = yes }')
        hover.conditions(parse('HSM_VER_a = yes'))
        self.assertTrue(any('script cycle' in e for e in hover.errors))

    def test_hidden_and_wrapped_flags_do_not_leak(self):
        hover = self.hover()
        rows = hover.conditions(parse('hidden_trigger = { has_country_flag = HSM_a } custom_trigger_tooltip = { tooltip = note has_global_flag = HSM_b } has_country_flag = native'))
        self.assertEqual(len(rows), 2)
        self.assertEqual(hover.errors, [])

    def test_public_results_distinguish_hidden_guarded_and_event_effects(self):
        for raw in ('hidden_effect = { add_stability = .1 }',
                    'if = { limit = { always = yes } custom_effect_tooltip = note }',
                    'hidden_effect = { country_event = { id = evt.1 } }',
                    'country_event = { days = 1 }',
                    'set_country_flag = HSM_done',
                    'hidden_effect = { custom_effect_tooltip = note }',
                    'if = { limit = { always = yes } hidden_effect = { add_stability = .1 } }',
                    'unknown_reward = yes'):
            with self.subTest(raw=raw):
                self.assertFalse(self.hover().rewards(parse(raw))[1])
        for raw in ('add_stability = .1', 'add_tech_bonus = { name = bonus uses = 1 bonus = .5 category = industry }',
                    'if = { limit = { always = yes } add_stability = .1 }',
                    'country_event = { id = evt.1 }',
                    'if = { limit = { hidden_trigger = { always = yes } } country_event = { id = evt.1 days = 1 } }',
                    'random_owned_state = { add_extra_state_shared_building_slots = 1 }',
                    'ROOT = { add_political_power = 25 }',
                    'custom_effect_tooltip = note hidden_effect = { country_event = { id = evt.1 } }'):
            with self.subTest(raw=raw):
                self.assertTrue(self.hover().rewards(parse(raw))[1])
        hover = self.hover(effects='HSM_VER_reward = { HSM_VER_inner = yes } HSM_VER_inner = { add_manpower = 100 }')
        self.assertTrue(hover.rewards(parse('HSM_VER_reward = yes'))[1])
        self.assertFalse(hover.rewards(parse('hidden_effect = { HSM_VER_reward = yes }'))[1])

    def test_idea_previews_resolve_definition_and_localization_without_grant(self):
        idea = parse('spirit = { modifier = { political_power_gain = .1 } }')[0]
        hover = self.hover(ideas={'spirit': idea}, loc={'spirit': 'Public spirit'})
        raw = parse('show_ideas_tooltip = spirit')
        rows, public = hover.rewards(raw)
        self.assertEqual(len(rows), 2)
        self.assertTrue(public)
        self.assertTrue(hover.rewards(parse('if = { limit = { always = yes } show_ideas_tooltip = spirit }'))[1])
        self.assertFalse(hover.rewards(parse('hidden_effect = { show_ideas_tooltip = spirit }'))[1])
        self.assertEqual(canonical(raw, 'effect'), ())
        self.assertFalse(hover.rewards(parse('hidden_effect = { show_ideas_tooltip = spirit }'))[1])
        self.assertFalse(hover.rewards(parse('show_ideas_tooltip = missing'))[1])
        self.assertTrue(any('missing idea' in e for e in hover.errors))
        hover = self.hover(ideas={'spirit': idea})
        self.assertFalse(hover.rewards(raw)[1])
        self.assertTrue(any('missing localization' in e for e in hover.errors))

    def test_localization_expansion_newlines_formatting_cycles_and_ru(self):
        loc = Localization({'a': '\u00a7Y$b$\u00a7!\\nNext [ROOT.GetName] \u00a3army_experience', 'b': '\u041f\u0440\u0438\u0432\u0435\u0442'})
        text = loc.resolve('a')
        self.assertEqual(text, '\u041f\u0440\u0438\u0432\u0435\u0442\nNext ' + 'X' * 24 + ' XX')
        self.assertEqual(measure([Row('a\n\nb')], 72)[0], 3)
        self.assertGreater(measure([Row('word ' * 100)], 72)[0], 5)
        for values in ({'a': '$missing$'}, {'a': '$b$', 'b': '$a$'}):
            with self.assertRaises(ValueError):
                Localization(values).resolve('a')

    def test_missing_external_references_are_estimates_only_without_sources(self):
        loc = Localization({'HSM_note': 'Build in $STATE_400$.'}, allow_external=True)
        self.assertIn('X' * 24, loc.resolve('HSM_note'))
        self.assertEqual(loc.external, {'STATE_400'})
        self.assertIn('HSM_note', loc.estimated)
        with self.assertRaises(ValueError):
            loc.resolve('HSM_missing')
        with self.assertRaises(ValueError):
            Localization(loc.values).resolve('HSM_note')

    def test_long_localized_effect_summary_exceeds_character_budget(self):
        hover = self.hover(loc={'note': 'word ' * 130})
        hover.rewards(parse('custom_effect_tooltip = note'))
        self.assertTrue(any('650/600' in e for e in hover.errors))

    def test_hidden_previews_still_require_valid_ids(self):
        hover = self.hover(effects='HSM_VER_reward = { hidden_effect = { show_ideas_tooltip = HSM_missing } }')
        hover.validate_idea_references(parse('HSM_VER_reward = yes'))
        self.assertTrue(any('missing idea definition: HSM_missing' in e for e in hover.errors))

    def test_legacy_exemption_requires_hidden_disabled_and_inert(self):
        raw = 'focus = { id = HSM_old allow_branch = { always = no } available = { always = no } completion_reward = {} }'
        self.assertTrue(inert_legacy(parse(raw)[0]))
        for changed in (raw.replace('allow_branch', 'unknown'), raw.replace('available', 'unknown'), raw.replace('completion_reward = {}', 'completion_reward = { hidden_effect = { add_manpower = 5 } }')):
            self.assertFalse(inert_legacy(parse(changed)[0]))

    def test_comparison_preserves_duplicate_fields_and_no_reward_reordering(self):
        old = parse('focus = { available = { a = 1 } completion_reward = { add_stability = .1 add_political_power = 5 } }')[0]
        new = parse('focus = { available = { custom_trigger_tooltip = { tooltip = note a = 1 } } completion_reward = { custom_effect_tooltip = note hidden_effect = { add_stability = .1 add_political_power = 5 } } }')[0]
        self.assertEqual(compare_focus(old, new), [])
        new = parse('focus = { available = { a = 1 } available = { a = 2 } completion_reward = { add_political_power = 5 add_stability = .1 } }')[0]
        self.assertEqual(len(compare_focus(old, new)), 2)

    def test_focus_metadata_is_ordered_and_never_stripped(self):
        raw = ('focus = { id = HSM_test icon = GFX_original x = 2 y = 3 cost = 5 '
               'prerequisite = { focus = first focus = second } '
               'ai_will_do = { factor = 1 } allow_branch = { tag = ERI } '
               'available = { tag = ERI } }')
        original = parse(raw)[0]
        for before, after in (('GFX_original', 'GFX_changed'), ('x = 2', 'x = 4'),
                              ('y = 3', 'y = 4'), ('cost = 5', 'cost = 6'),
                              ('focus = first focus = second', 'focus = second focus = first'),
                              ('factor = 1', 'factor = 2'), ('allow_branch = { tag = ERI }',
                               'allow_branch = { custom_trigger_tooltip = { tooltip = note tag = ERI } }'),
                              ('x = 2 y = 3', 'y = 3 x = 2')):
            with self.subTest(after=after):
                errors = compare_focus(original, parse(raw.replace(before, after))[0])
                self.assertTrue(any(e.startswith('metadata:') for e in errors))
        wrapped = raw.replace('available = { tag = ERI }',
                              'available = { custom_trigger_tooltip = { tooltip = note tag = ERI } }')
        self.assertEqual(compare_focus(original, parse(wrapped)[0]), [])

    def test_scalar_field_changes_are_not_empty_block_equivalence(self):
        old = parse('focus = { available = yes }')[0]
        new = parse('focus = { available = no }')[0]
        self.assertTrue(compare_focus(old, new))

    def test_effect_cycle_is_bounded_and_does_not_prove_public_reward(self):
        hover = self.hover(effects='HSM_VER_a = { HSM_VER_b = yes } HSM_VER_b = { HSM_VER_a = yes }')
        self.assertFalse(hover.rewards(parse('HSM_VER_a = yes'))[1])
        self.assertTrue(any('script cycle' in e for e in hover.errors))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mod', type=Path, default=ROOT / 'mod/HoISubmod')
    parser.add_argument('--baseline', type=Path, help='read-only original focus *.txt directory; omission explicitly skips equivalence')
    parser.add_argument('--eaw', type=Path, help='optional Equestria at War root for strict external localization/idea verification')
    parser.add_argument('--game', type=Path, help='optional HOI4 root; precedence is game, EAW, submod')
    parser.add_argument('--self-test', action='store_true', help='only run synthetic analyzer regressions')
    parser.add_argument('--line-width', type=int, default=72)
    parser.add_argument('--max-condition-lines', type=int, default=18)
    parser.add_argument('--max-effect-lines', type=int, default=18)
    parser.add_argument('--max-total-lines', type=int, default=30)
    parser.add_argument('--max-summary-chars', type=int, default=600)
    parser.add_argument('--top', type=int, default=8, help='number of largest estimated EN/RU hovers to print')
    parser.add_argument('-q', '--quiet', action='store_true')
    options = parser.parse_args(argv)
    if min(options.line_width, options.max_condition_lines, options.max_effect_lines, options.max_total_lines, options.max_summary_chars) < 1 or options.top < 0:
        parser.error('budget sizes must be positive; --top must be nonnegative')
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AnalyzerTests)
    result = unittest.TextTestRunner(verbosity=1 if options.quiet else 2).run(suite)
    if not result.wasSuccessful():
        return 1
    if options.self_test:
        return 0
    try:
        paths = focus_paths(options.mod)
        if not paths:
            raise ValueError(f'No focus files in {options.mod}')
        errors = []
        if options.baseline is not None:
            failures, count = compare_baseline(options.baseline, paths)
            errors.extend(failures)
            print(f'Baseline equivalence: {count} focuses compared, {len(failures)} violations.')
        else:
            print('SKIP baseline equivalence: supply --baseline ORIGINALS (no machine-specific default or self-generated baseline).')
        failures, counts, budgets = audit(options.mod, paths, options)
        errors.extend(failures)
        print(f'UI audit: {counts["focuses"]} focuses, {counts["inert_legacy"]} hidden inert legacy IDs exempt; EN/RU checked.')
        if options.game is None and options.eaw is None:
            print(f'SKIP external reference verification: no --game/--eaw; {counts["external_localization_estimates"]} localization references and {counts["external_idea_estimates"]} idea occurrences estimated. HSM references remain strict.')
        else:
            print('External reference verification enabled (game < EAW < submod); missing references are failures.')
        print(f'Source estimates only: {options.line_width} columns; condition/effect/total line limits {options.max_condition_lines}/{options.max_effect_lines}/{options.max_total_lines}. No engine rendering or screenshots.')
        for total, key, language, cl, el, chars, estimates in sorted(budgets, reverse=True)[:options.top]:
            print(f'  {key} [{language}]: {cl} condition + {el} effect = {total} lines, {chars} characters; {estimates} estimated rows')
        for error in errors:
            print('FAIL ' + error)
        print(f'{"FAIL" if errors else "PASS"}: {len(errors)} static QA violations.')
        return int(bool(errors))
    except (ValueError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
