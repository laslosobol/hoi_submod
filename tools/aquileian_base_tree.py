"""Native nonpolitical Griffon focus import for the four AQR campaigns.

build_base(eaw) returns (shared_focus_text, {loc_key: (english, russian)}).
root_ids(eaw) returns the validated list of shared roots for the caller's tree.
ROOT_IDS also exposes that inventory; this module creates no tree or file.
The political root and its 28 descendants are replaced by the caller's fifteen
authored programmes. The other 44 native focuses retain their content: only
definition IDs, focus references and absolute x coordinates change. In
particular, the idea named griffon_tank_licenses must NOT be namespaced.

The native tree's separate RIV_dreams_of_a_federation shared import is not one of
the 73 definitions. Its inclusion/position remains the caller's responsibility.
The excluded political branch includes government-changing event callbacks.
Any such callback remaining in the imported branches fails validation.

Read-only self-check: python -B -X utf8 tools/aquileian_base_tree.py --eaw EaW
Standalone parser: importing this module reads no files and does not parse argv
or import the historical Verenia builders/test runners.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import NamedTuple

PREFIX = "HSM_AQR_BASE_"
SOURCE = Path("common/national_focus/generic_griffon.txt")
X_OFFSET = 32
EXPECTED_COUNT = 73
EXPECTED_IMPORTED_COUNT = 44
POLITICAL_ROOT = "griffon_political_effort"
ROOT_IDS = tuple(PREFIX + name for name in (
    "griffon_industrial_effort",
    "griffon_expand_army", "griffon_aviation_effort", "griffon_naval_effort",
))
NATIVE_ROOT_IDS = (PREFIX + POLITICAL_ROOT,) + ROOT_IDS
FOCUS_REFERENCES = frozenset({
    "focus", "relative_position_id", "has_completed_focus", "has_focus",
    "complete_national_focus", "unlock_national_focus", "cancel_national_focus",
})
# Confirmed in EaW/events/GriffonContinental Events.txt. Do not rename event IDs.
GOVERNMENT_EVENTS = {
    "griffonian.3": "fascism", "griffonian.4": "democratic",
    "griffonian.5": "neutrality",
}
TOKEN = re.compile(r'\s+|#[^\n]*|"(?:\\.|[^"\\])*"|[{}]|[<>!=]+|[^\s{}=<>!#"]+')
OPERATORS = {"=", "<", ">", "<=", ">=", "!="}


class Node(NamedTuple):
    key: str
    start: int
    end: int
    value: str
    value_start: int
    value_end: int
    children: tuple["Node", ...] | None


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _parse(text: str) -> tuple[Node, ...]:
    """Parse spans, retaining duplicate keys, list atoms and quoted strings."""
    tokens, offset = [], 0
    while offset < len(text):
        token = TOKEN.match(text, offset)
        _require(token is not None, f"Invalid token/unterminated string at {offset}")
        offset = token.end()
        if not token[0].isspace() and not token[0].startswith("#"):
            tokens.append(token)
    pos = 0

    def block(nested: bool = False) -> tuple[tuple[Node, ...], int]:
        nonlocal pos
        result = []
        while pos < len(tokens):
            key = tokens[pos]
            pos += 1
            if key[0] == "}":
                _require(nested, "Unexpected closing brace")
                return tuple(result), key.end()
            _require(key[0] != "{" and key[0] not in OPERATORS,
                     f"Expected key at {key.start()}")
            value, children, end = "", None, key.end()
            value_start = value_end = -1
            if pos < len(tokens) and tokens[pos][0] in OPERATORS:
                pos += 1
                _require(pos < len(tokens), f"Missing value for {key[0]}")
                token = tokens[pos]
                pos += 1
                if token[0] == "{":
                    children, end = block(True)
                else:
                    _require(token[0] != "}" and token[0] not in OPERATORS,
                             f"Missing value for {key[0]}")
                    value = token[0].strip('"')
                    value_start, value_end, end = token.start(), token.end(), token.end()
            result.append(Node(key[0].strip('"'), key.start(), end, value,
                               value_start, value_end, children))
        _require(not nested, "Unclosed block")
        return tuple(result), len(text)

    return block()[0]


def _fields(node: Node, key: str) -> tuple[Node, ...]:
    return tuple(n for n in node.children or () if n.key == key)


def _one(node: Node, key: str) -> Node:
    found = _fields(node, key)
    _require(len(found) == 1, f"Expected exactly one {key} in {node.key}")
    return found[0]


def _walk(nodes):
    for node in nodes:
        yield node
        yield from _walk(node.children or ())


def _graph(focuses: tuple[Node, ...]) -> tuple[tuple[str, ...], dict[str, int]]:
    by_id = {_one(f, "id").value: f for f in focuses}
    _require(len(by_id) == len(focuses) and "" not in by_id, "Duplicate/missing focus ID")
    dependencies, positions = {}, {}
    for fid, focus in by_id.items():
        for n in _walk(focus.children or ()):
            if n.key in FOCUS_REFERENCES and n.children is None:
                _require(n.value in by_id, f"Unresolved {n.key}: {fid} -> {n.value}")
        groups = _fields(focus, "prerequisite")
        _require(all(_fields(group, "focus") for group in groups),
                 f"Empty prerequisite group: {fid}")
        dependencies[fid] = tuple(n.value for group in groups for n in _fields(group, "focus"))
        relative = _fields(focus, "relative_position_id")
        _require(len(relative) <= 1, f"Duplicate relative position: {fid}")
        positions[fid] = tuple(n.value for n in relative)
        _require(re.fullmatch(r"-?\d+", _one(focus, "x").value) is not None,
                 f"Noninteger x coordinate: {fid}")

    def acyclic(edges, label):
        active, done = set(), set()

        def visit(fid):
            _require(fid not in active, f"{label} cycle at {fid}")
            if fid in done:
                return
            active.add(fid)
            for target in edges[fid]:
                visit(target)
            active.remove(fid)
            done.add(fid)

        for fid in by_id:
            visit(fid)

    acyclic(dependencies, "Prerequisite")
    acyclic(positions, "Relative position")
    resolved = {}

    def x(fid):
        if fid not in resolved:
            resolved[fid] = int(_one(by_id[fid], "x").value)
            if positions[fid]:
                resolved[fid] += x(positions[fid][0])
        return resolved[fid]

    for fid in by_id:
        x(fid)
    return tuple(fid for fid in by_id if not dependencies[fid]), resolved


def _rewrite(text, focuses, mapping, shift, kind):
    blocks = []
    for focus in focuses:
        identifier = _one(focus, "id")
        edits = [(focus.start, focus.start + len(focus.key), kind)]

        def replace(node, value):
            _require(node.value_start >= 0, f"Expected scalar: {node.key}")
            if text[node.value_start:node.value_end].startswith('"'):
                value = '"' + value + '"'
            edits.append((node.value_start, node.value_end, value))

        replace(identifier, mapping[identifier.value])
        for node in _walk(focus.children or ()):
            if node.key in FOCUS_REFERENCES and node.children is None:
                replace(node, mapping[node.value])
        if not _fields(focus, "relative_position_id"):
            coordinate = _one(focus, "x")
            replace(coordinate, str(int(coordinate.value) + shift))
        raw = text[focus.start:focus.end]
        for start, end, replacement in sorted(edits, reverse=True):
            raw = raw[:start - focus.start] + replacement + raw[end - focus.start:]
        blocks.append(raw)
    return "\n\n".join(blocks) + "\n"


def _political_warnings(focuses) -> tuple[str, ...]:
    notes = []
    for focus in focuses:
        fid = _one(focus, "id").value
        for node in _walk(focus.children or ()):
            if node.key == "country_event":
                event = _one(node, "id").value if node.children is not None else node.value
                if event in GOVERNMENT_EVENTS:
                    notes.append(f"{fid} retains {event}, which can set ruling_party="
                                 f"{GOVERNMENT_EVENTS[event]} and elections_allowed=no")
            elif node.key in {"set_politics", "set_ruling_party", "start_civil_war"}:
                notes.append(f"{fid} retains direct {node.key}")
    return tuple(notes)


def _descendants(focuses: tuple[Node, ...], root: str) -> set[str]:
    """Structural descendants through any prerequisite edge, plus root itself."""
    dependencies = {
        _one(focus, "id").value: {
            node.value for group in _fields(focus, "prerequisite")
            for node in _fields(group, "focus")
        }
        for focus in focuses
    }
    _require(root in dependencies, f"Missing branch root: {root}")
    found = {root}
    while True:
        expanded = found | {fid for fid, parents in dependencies.items() if parents & found}
        if expanded == found:
            return found
        found = expanded


def _native(eaw: Path):
    text = (Path(eaw) / SOURCE).read_text(encoding="utf-8-sig")
    trees = _parse(text)
    _require(len(trees) == 1 and trees[0].key == "focus_tree"
             and _one(trees[0], "id").value == "generic_griffon_focus",
             "Expected native generic_griffon_focus tree")
    focuses = _fields(trees[0], "focus")
    _require(len(focuses) == EXPECTED_COUNT,
             f"Native inventory changed: expected 73 focuses, found {len(focuses)}")
    roots, positions = _graph(focuses)
    _require(tuple(PREFIX + fid for fid in roots) == NATIVE_ROOT_IDS, "Native root inventory changed")
    return text, focuses, roots, positions


def _base(eaw: Path):
    text, native, _, _ = _native(eaw)
    excluded = _descendants(native, POLITICAL_ROOT)
    focuses = tuple(f for f in native if _one(f, "id").value not in excluded)
    _require(len(focuses) == EXPECTED_IMPORTED_COUNT,
             f"Nonpolitical inventory changed: expected 44 focuses, found {len(focuses)}")
    roots, positions = _graph(focuses)  # Reject dangling references to excluded focuses.
    _require(tuple(PREFIX + fid for fid in roots) == ROOT_IDS, "Imported root inventory changed")
    notes = _political_warnings(focuses)
    _require(not notes, "Government-changing effects remain in imported branches: " + "; ".join(notes))
    return text, focuses, roots, positions


def root_ids(eaw: Path) -> list[str]:
    """Return four nonpolitical namespaced roots in native source order."""
    _, _, roots, _ = _base(eaw)
    return [PREFIX + fid for fid in roots]


def build_base(eaw: Path) -> tuple[str, dict[str, tuple[str, str]]]:
    """Read native source; return 44 nonpolitical blocks and 88 EN/RU aliases.

    Aliases use the native localization in each language. Non-focus references
    (ideas, events, flags, tech bonuses, icons and log text) stay native.
    """
    text, focuses, _, positions = _base(eaw)
    mapping = {_one(f, "id").value: PREFIX + _one(f, "id").value for f in focuses}
    result = _rewrite(text, focuses, mapping, X_OFFSET, "shared_focus")
    converted = _parse(result)
    new_roots, new_positions = _graph(converted)
    _require(new_roots == ROOT_IDS and len(converted) == EXPECTED_IMPORTED_COUNT,
             "Converted graph inventory drifted")
    _require(all(new_positions[mapping[fid]] == value + X_OFFSET
                 for fid, value in positions.items()), "Layout translation is inconsistent")
    _require(min(new_positions.values()) > 30, "Native graph overlaps authored x=3..30")
    # Exact reverse transformation proves every reward, condition, comment and
    # reference outside the explicit substitutions survived without reformatting.
    restored = _rewrite(result, converted, {v: k for k, v in mapping.items()},
                        -X_OFFSET, "focus")
    original = "\n\n".join(text[f.start:f.end] for f in focuses) + "\n"
    _require(restored == original, "Native content changed beyond ID/reference/layout edits")
    aliases = {}
    for old, new in mapping.items():
        for suffix in ("", "_desc"):
            aliases[new + suffix] = (f"${old}{suffix}$", f"${old}{suffix}$")
    return result, aliases


def self_check(eaw: Path) -> None:
    """Bounded in-memory regressions plus the actual 73-focus source contract."""
    sample = '''# focus = bogus { }
focus = { id = root x = 3 y = 0 completion_reward = {
    log = "root # { \\"quote\\" }" add_political_power = 120
} }
focus = { id = child x = -2 y = 1 relative_position_id = "root"
    prerequisite = { focus = root } # reference comment
    completion_reward = { add_ideas = child has_completed_focus = "root" }
    search_filters = { FOCUS_FILTER_POLITICAL }
}
'''
    native = _parse(sample)
    _graph(native)
    changed = _rewrite(sample, native, {"root": PREFIX + "root", "child": PREFIX + "child"},
                       X_OFFSET, "shared_focus")
    _require('add_ideas = child' in changed and '# reference comment' in changed,
             "Non-focus identifier/comment was rewritten")
    _require('relative_position_id = "HSM_AQR_BASE_root"' in changed
             and 'has_completed_focus = "HSM_AQR_BASE_root"' in changed,
             "Quoted reference did not retain its quotes")
    _require(_graph(_parse(changed))[1] == {PREFIX + "root": 35, PREFIX + "child": 33},
             "Relative coordinates shifted more than once")
    for broken in ('focus = {', 'focus = { id = }', 'focus = { log = "oops }'):
        try:
            _parse(broken)
        except ValueError:
            pass
        else:
            raise AssertionError("Malformed fixture accepted")
    for broken in (sample.replace('focus = root', 'focus = missing'),
                   sample.replace('id = root x', 'id = root prerequisite = { focus = child } x'),
                   sample.replace('id = root x', 'id = root relative_position_id = child x')):
        try:
            _graph(_parse(broken))
        except ValueError:
            pass
        else:
            raise AssertionError("Dangling reference/cycle accepted")
    # Deliberately reversed order and mixed alternatives ensure exclusion is
    # transitive and follows every prerequisite edge, not source order/layout.
    branch_fixture = _parse('''
focus = { id = grandchild prerequisite = { focus = child } }
focus = { id = child prerequisite = { focus = political focus = economy } }
focus = { id = economy }
focus = { id = political }
''')
    _require(_descendants(branch_fixture, "political") == {"political", "child", "grandchild"},
             "Political descendant filtering missed a branch or removed an unrelated root")
    _, native, _, _ = _native(eaw)
    excluded = _descendants(native, POLITICAL_ROOT)
    _require(len(excluded) == 29, "Native political inventory changed")
    result, loc = build_base(eaw)
    focuses = _parse(result)
    actual_ids = {_one(f, "id").value for f in focuses}
    expected_ids = {PREFIX + _one(f, "id").value for f in native
                    if _one(f, "id").value not in excluded}
    _require(actual_ids == expected_ids and len(actual_ids) == 44, "Imported focus inventory mismatch")
    expected_loc = {fid + suffix: (f"${fid.removeprefix(PREFIX)}{suffix}$",) * 2
                    for fid in expected_ids for suffix in ("", "_desc")}
    _require(loc == expected_loc and len(loc) == 88, "Aliases include excluded or missing focuses")
    _require(not _political_warnings(focuses), "Imported government-changing callback survived")
    tank = next(f for f in focuses if _one(f, "id").value == PREFIX + "griffon_tank_licenses")
    _require(any(n.key == "add_ideas" and n.value == "griffon_tank_licenses"
                 for n in _walk(tank.children or ())), "Focus/idea name collision")
    roots, positions = _graph(focuses)
    _require(root_ids(eaw) == list(roots), "root_ids API differs from emitted shared roots")
    print(f"PASS: 73 native focuses, {len(excluded)} political focuses excluded; "
          f"{len(focuses)} shared focuses, {len(roots)} roots, {len(loc)} bilingual aliases; "
          f"resolved x={min(positions.values())}..{max(positions.values())}; "
          "lossless rewards/conditions, reference/lexer regressions. No files written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eaw", type=Path, default=Path(__file__).resolve().parents[1] / "EaW")
    self_check(parser.parse_args().eaw)
