"""Build minimal JER focus hooks for active regional campaigns.

Only common/national_focus/JER.txt is generated. Its untouched bytes come from
the repository's EaW snapshot, which must match the explicitly supplied installed
--eaw reference and the reviewed SHA256. No source tree is modified.

--check (also the default) is read-only and returns 1 for missing/stale output.
--apply writes the canonical override, refusing an unrelated existing override.
JER_state_of_aquileia and JER_fight_for_freedom immediately start the regional
campaign through HSM_AQR_start_regions, after their native completion rewards.
JER_the_triumph and JER_integrate_the_loyal are also patched. Active
HSM_AQR_started regions receive guarded HSM_AQR.30 instead of immediate annexation;
their troops/characters are not removed or transferred before their response.
The loyal-integration focus keeps its native aquileia.54 calls for unflagged
recipients, and its original allegiance checks, war goals and seven-day delay.

Module API for source checks: patch(raw_bytes), build(eaw_path), triumph(text).
The campaign owns HSM_AQR.30's acceptance/refusal and delayed-event guards.
This does not replace other native demand sources or peace-conference on_actions.
Build-AquileianPreparationHooks.py owns the separate mission-timeout callback.
"""
from __future__ import annotations

import argparse
import hashlib
import runpy
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELATIVE = Path("common/national_focus/JER.txt")
SNAPSHOT = ROOT / "EaW" / RELATIVE
OUTPUT = ROOT / "mod/HoISubmod" / RELATIVE
REVIEWED_SHA256 = "7b415747f52bc315efa7aa68637c1694348203aa0b751e8788543f8e7983b1b4"
# Permit only the exact previously generated Triumph revisions to migrate.
# Manual changes or any other JER override still require an explicit review.
LEGACY_OUTPUT_SHA256 = frozenset({
    "93c08093de5feb5285dfa13fded3e8fc49d1062841452f798b758e99e1d9e8af",
    "f5ab72d65c057ec789d0f95cb7606ed1cdacd9bbeda9b822246215fb863343a8",
    "5171a1d9cb11809b9e7c41b1cbf212c777ee18c37c0adf35f79bad2918b2f8dc",
    "50731d19bc270529545d34095694b22975a6d4a0cec88a5c751da2d09ee8ebf4",
})
REGIONS = ("JEB", "JRR", "JFT", "VIN")
FLAG = "HSM_AQR_started"
START_FOCUSES = ("JER_state_of_aquileia", "JER_fight_for_freedom")

# Reuse the source-preserving parser without exposing this tool's CLI to the
# historical Test-Verenia argument parser imported by Build-VereniaSpirit.
_argv = sys.argv
try:
    sys.argv = [str(Path(__file__))]
    _api = runpy.run_path(str(ROOT / "tools/Build-VereniaSpirit.py"))
finally:
    sys.argv = _argv
spans = _api["spans"]
parse, TOKEN = _api["API"]["parse"], _api["API"]["TOKEN"]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.children)


def one(nodes, key):
    found = [node for node in nodes if node.key == key]
    require(len(found) == 1, f"Expected exactly one {key}, found {len(found)}")
    return found[0]


def focus_span(text, identifier):
    """Return the unique native focus span, validating syntax first."""
    parse(text.lstrip("\ufeff"))
    found = [node for node in walk(spans(text.lstrip("\ufeff")))
             if node.key == "shared_focus"
             and any(child.key == "id" and child.value == identifier
                     for child in node.children)]
    require(len(found) == 1, f"Expected exactly one shared_focus {identifier}")
    return found[0]


def triumph(text):
    return focus_span(text, "JER_the_triumph")


def body_start(text, node):
    tokens = [m for m in TOKEN.finditer(text, node.start, node.end)
              if not m[0].isspace() and not m[0].startswith("#")]
    require(len(tokens) >= 4 and tokens[1][0] == "=" and tokens[2][0] == "{"
            and tokens[-1][0] == "}", f"Expected block: {node.key}")
    return tokens[2].end()


def patch(raw):
    """Insert hooks within four focus effects; preserve native source bytes."""
    decoded = raw.decode("utf-8")
    bom = "\ufeff" if decoded.startswith("\ufeff") else ""
    text = decoded[len(bom):]
    require(FLAG not in text, "Input already contains the AQR hook; use the native snapshot")
    focus = triumph(text)
    select = one(focus.children, "select_effect")
    hidden = one(select.children, "hidden_effect")
    annexes = [node for node in walk(hidden.children) if node.key == "annex_country"]
    require(Counter(one(node.children, "target").value for node in annexes)
            == Counter({"JRR": 1, "JEB": 1, "JFT": 2, "VIN": 2}),
            "Native triumph annexation structure drifted")
    newline = "\r\n" if "\r\n" in text else "\n"
    edits = []

    # These scopes contain pre-annexation troop deletion and JEB's character
    # transfer as well as the JEB/JRR AI annexations. Keep all of it in else.
    for tag in REGIONS:
        country = one(hidden.children, tag)
        start = body_start(text, country)
        prefix = (newline + "\t\t\t\t\tif = {" + newline
                  + f"\t\t\t\t\t\tlimit = {{ exists = yes has_country_flag = {FLAG} }}" + newline
                  + "\t\t\t\t\t\tcountry_event = { id = HSM_AQR.30 days = 7 }" + newline
                  + "\t\t\t\t\t}" + newline
                  + "\t\t\t\t\telse = {")
        edits.append((start, prefix))
        edits.append((country.end - 1, "\t}" + newline + "\t\t\t\t"))

    # JFT/VIN annexations are separate sibling ifs, selected by the native
    # troop-transfer flags. Preserve those flags/branches for nonparticipants.
    guarded = Counter()
    for branch in hidden.children:
        if branch.key != "if":
            continue
        actions = [node for node in walk(branch.children) if node.key == "annex_country"]
        require(len(actions) == 1, "Unexpected sibling if in native triumph")
        tag = one(actions[0].children, "target").value
        require(tag in ("JFT", "VIN"), f"Unexpected annexation sibling: {tag}")
        limit = one(branch.children, "limit")
        edits.append((body_start(text, limit), newline
                      + f"\t\t\t\t\t\tNOT = {{ {tag} = {{ has_country_flag = {FLAG} }} }}"))
        guarded[tag] += 1
    require(guarded == Counter({"JFT": 2, "VIN": 2}), "Missing JFT/VIN annexation guards")

    loyal = focus_span(text, "JER_integrate_the_loyal")
    reward = one(loyal.children, "completion_reward")
    demands = [node for node in walk(reward.children) if node.key == "country_event"]
    require(len(demands) == 4, "Native loyal-integration event count drifted")
    recipients = Counter()
    for branch in reward.children:
        if branch.key != "if":
            continue
        countries = [node for node in branch.children if node.key in REGIONS]
        require(len(countries) == 1, "Expected one recipient per loyal-integration branch")
        country = countries[0]
        demand = one(country.children, "country_event")
        require(one(demand.children, "id").value == "aquileia.54"
                and one(demand.children, "days").value == "7"
                and len(demand.children) == 2,
                "Native loyal-integration demand or delay drifted")
        # Keep the original demand byte-for-byte inside else, in the same
        # recipient scope. The enclosing allegiance checks/war goals are intact.
        indent = "\t" * 6
        prefix = ("if = {" + newline
                  + indent + f"limit = {{ has_country_flag = {FLAG} }}" + newline
                  + indent + "country_event = { id = HSM_AQR.30 days = 7 }" + newline
                  + "\t" * 5 + "}" + newline + "\t" * 5 + "else = {" + newline
                  + indent)
        edits.append((demand.start, prefix))
        edits.append((demand.end, newline + "\t" * 5 + "}"))
        recipients[country.key] += 1
    require(recipients == Counter(REGIONS), "Missing or repeated loyal-integration recipient")
    allowed_blocks = [select, reward]
    for identifier in START_FOCUSES:
        start_reward = one(focus_span(text, identifier).children, "completion_reward")
        allowed_blocks.append(start_reward)
        edits.append((start_reward.end - 1,
                      "\thidden_effect = { HSM_AQR_start_regions = yes }" + newline + "\t\t"))
    require(len({at for at, _ in edits}) == len(edits), "Overlapping insertion anchors")
    require(all(any(block.start < at < block.end for block in allowed_blocks)
                for at, _ in edits), "Insertion escaped the four authorized focus effects")

    # Insertions only: concatenate every original slice unchanged, including
    # comments, whitespace, BOM and line endings outside the added guards.
    parts, cursor = [], 0
    for at, added in sorted(edits):
        parts.extend((text[cursor:at], added))
        cursor = at
    parts.append(text[cursor:])
    result = "".join(parts)
    parse(result)
    def outside(source, blocks):
        parts, cursor = [], 0
        for block in sorted(blocks, key=lambda n: n.start):
            parts.append(source[cursor:block.start])
            cursor = block.end
        return "".join(parts) + source[cursor:]

    changed_select = one(triumph(result).children, "select_effect")
    changed_reward = one(focus_span(result, "JER_integrate_the_loyal").children, "completion_reward")
    changed_blocks = [changed_select, changed_reward] + [
        one(focus_span(result, identifier).children, "completion_reward")
        for identifier in START_FOCUSES]
    require(outside(text, allowed_blocks) == outside(result, changed_blocks),
            "Unrelated native bytes changed")
    # Every native JER tree keeps the same independent post-revolution recovery
    # root, including after its later political tree reloads.
    trees = [node for node in spans(result) if node.key == "focus_tree"]
    require(len(trees) == 6, "Native Aquileian tree inventory drifted")
    root_line = "\tshared_focus = HSM_AQR_REC_postwar_housing" + newline
    with_roots = result
    for tree in sorted(trees, key=lambda n: n.end, reverse=True):
        with_roots = with_roots[:tree.end-1] + root_line + with_roots[tree.end-1:]
    require(with_roots.replace(root_line, "") == result,
            "Recovery import changed unrelated native bytes")
    parse(with_roots)
    return (bom + with_roots).encode("utf-8")


def build(eaw, snapshot=SNAPSHOT):
    """Refuse upstream drift before producing bytes; this function never writes."""
    installed = Path(eaw) / RELATIVE
    raw = Path(snapshot).read_bytes()
    live = installed.read_bytes()
    snapshot_hash = hashlib.sha256(raw).hexdigest()
    live_hash = hashlib.sha256(live).hexdigest()
    require(raw == live,
            f"EaW drift: snapshot SHA256={snapshot_hash}; installed SHA256={live_hash}. "
            "Review upstream differences before regenerating the JER override.")
    require(snapshot_hash == REVIEWED_SHA256,
            f"Unreviewed JER baseline SHA256={snapshot_hash}; expected {REVIEWED_SHA256}. "
            "Matching snapshots alone do not approve a new baseline.")
    return patch(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eaw", type=Path, required=True,
                        help="Explicit installed EaW directory to compare with EaW/ snapshot")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Read-only consistency check (default)")
    modes.add_argument("--apply", action="store_true", help="Write only the canonical JER override")
    args = parser.parse_args()
    try:
        result = build(args.eaw)
        previous = OUTPUT.read_bytes() if OUTPUT.exists() else None
        if previous == result:
            print(f"OK: {OUTPUT.relative_to(ROOT)} (reviewed native SHA256 {REVIEWED_SHA256})")
            return 0
        require(previous is None or previous == SNAPSHOT.read_bytes()
                or hashlib.sha256(previous).hexdigest() in LEGACY_OUTPUT_SHA256,
                "JER override differs from the canonical patch/native snapshot; "
                "refusing to overwrite unrelated or manually edited content.")
        if not args.apply:
            print(f"STALE: {OUTPUT.relative_to(ROOT)}; --check wrote nothing")
            return 1
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(result)
        print(f"WROTE: {OUTPUT.relative_to(ROOT)}; two start callbacks, two absorption guards and six recovery imports")
        return 0
    except (OSError, ValueError, AssertionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
