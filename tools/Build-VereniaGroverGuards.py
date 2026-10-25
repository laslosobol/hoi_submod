"""Mechanically guard native event/decision entry points without reserializing them.

Existing submod overrides (including CYA changes) are the input when present.
Only a missing file is sourced from installed EaW. --check is read-only.
"""
from __future__ import annotations

import argparse
import runpy
from pathlib import Path

API = runpy.run_path(str(Path(__file__).with_name("Build-VereniaSpirit.py")))
MOD, EAW, spans = API["MOD"], API["EAW"], API["spans"]
META = {"name", "trigger", "ai_chance", "highlight", "original_tag", "default_option"}
RULER = "HSM_VER_GRO_native_ruler_allowed"
HOUSEHOLD = "HSM_VER_GRO_native_household_allowed"
CHILD = "HSM_VER_GRO_native_childhood_allowed"
DEMAND = "HSM_VER_GRO_native_demand_allowed"


def field(node, key):
    return next((n for n in node.children if n.key == key), None)


def events(text, rules):
    edits = []
    found = set()
    for event in spans(text):
        event_id = field(event, "id")
        if not event_id or event_id.value not in rules:
            continue
        found.add(event_id.value)
        guard = rules[event_id.value]
        trigger = field(event, "trigger")
        if trigger and field(trigger, guard):
            continue
        if trigger:
            at = text.index("{", trigger.start) + 1
            edits.append((at, at, f"\n\t\t{guard} = yes"))
        else:
            edits.append((event_id.end, event_id.end, f"\n\ttrigger = {{ {guard} = yes }}"))
        for block in event.children:
            if block.key not in ("option", "immediate"):
                continue
            groups, current = [], []
            for node in block.children:
                if block.key == "option" and node.key in META:
                    if current:
                        groups.append(current)
                        current = []
                else:
                    current.append(node)
            if current:
                groups.append(current)
            for group in groups:
                start, end = group[0].start, group[-1].end
                original = text[start:end]
                edits.append((start, end, f"if = {{\n\t\t\tlimit = {{ hidden_trigger = {{ {guard} = yes }} }}\n\t\t\t{original}\n\t\t}}"))
    assert found == set(rules), set(rules) - found
    return apply(text, edits)


def apply(text, edits):
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    spans(text)
    return text


def decision_guards(text):
    edits = []
    names = {"GRI_demand_land", "GRI_demand_frontier", "GRI_offer_peace"}
    found = set()
    for category in spans(text):
        for decision in category.children:
            if decision.key not in names:
                continue
            found.add(decision.key)
            visibility = field(decision, "visible")
            if visibility and field(visibility, RULER):
                continue
            if visibility:
                at = text.index("{", visibility.start) + 1
                edits.append((at, at, f"\n\t\t\t{RULER} = yes"))
            else:
                at = text.index("{", decision.start) + 1
                edits.append((at, at, f"\n\t\tvisible = {{ {RULER} = yes }}"))
            target = field(decision, "target_root_trigger")
            if target:
                at = text.index("{", target.start) + 1
                edits.append((at, at, f"\n\t\t\t{RULER} = yes"))
            for effect in decision.children:
                if effect.key not in ("complete_effect", "remove_effect", "cancel_effect"):
                    continue
                at, end = text.index("{", effect.start) + 1, effect.end - 1
                original = text[at:end].rstrip()
                edits.append((at, end, f"\n\t\t\tif = {{ limit = {{ hidden_trigger = {{ {RULER} = yes }} }}\n{original}\n\t\t\t}}\n\t\t"))
    assert found == names, names - found
    return apply(text, edits)


def mandate_guard(text):
    root = next(n for n in spans(text) if n.key == "GRI_has_access_to_reichsmandates")
    if field(root, RULER):
        return text
    at = text.index("{", root.start) + 1
    return apply(text, [(at, at, f"\n\t{RULER} = yes")])


def outputs():
    imperial = {f"imperial.{n}": RULER for n in (1, 2, 3, 30, 300, 44, 71, 72, 73, 74, 75, 76, 123, 137)}
    imperial["imperial.70"] = DEMAND
    grover = {f"grover.{n}": CHILD for n in (*range(1, 15), 17)}
    grover.update({f"grover.{n}": HOUSEHOLD for n in (32, 35, 40, 41)})
    transforms = {
        "events/GriffonianEmpire Events.txt": lambda text: events(text, imperial),
        "events/Grover_Events.txt": lambda text: events(text, grover),
        "common/decisions/GRI_decisions.txt": decision_guards,
        "common/scripted_triggers/EAW_GRI_scripted_triggers.txt": mandate_guard,
    }
    for relative, transform in transforms.items():
        target = MOD / relative
        source = target if target.exists() else EAW / relative
        original = source.read_text(encoding="utf-8-sig")
        yield target, original, transform(original)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = 0
    for target, original, result in outputs():
        if not target.exists() or result != original:
            changed += 1
            print(target.relative_to(MOD))
            if not args.check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(result, encoding="utf-8", newline="\n")
    print(f"{changed} {'stale' if args.check else 'updated'} native guard files")
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
