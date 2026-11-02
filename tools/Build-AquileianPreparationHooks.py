"""Add one regional preparation callback after native mission-timeout resolution.

Generate only mod/HoISubmod/common/decisions/JER_decisions.txt from the reviewed
EaW snapshot, after comparing it with the explicitly supplied installed --eaw.
Default/--check is read-only; --apply writes the canonical override. Existing
unrelated overrides and upstream drift are rejected before any write.

HSM_AQR_record_native_outcome runs in the regional ROOT scope, after native local
winner flags and JER_revolution_begun are set, before the one-day regional events.
Native support comparisons, ties, event queues, complete_effect and governments
are unchanged. Instant completion resolves through main's daily global-end check;
the global flags are only set when aquileia.17/.47 options execute. No event file
is overridden, and the campaign owns the callback's implementation/idempotency.

Module API: patch(raw_bytes), build(eaw_path), mission(text).
"""
from __future__ import annotations

import argparse
import hashlib
import runpy
import sys
from pathlib import Path

API = runpy.run_path(str(Path(__file__).with_name("Build-AquileianNativeHooks.py")))
ROOT, spans, parse, walk, one, require = (
    API[k] for k in ("ROOT", "spans", "parse", "walk", "one", "require"))
RELATIVE = Path("common/decisions/JER_decisions.txt")
SNAPSHOT = ROOT / "EaW" / RELATIVE
OUTPUT = ROOT / "mod/HoISubmod" / RELATIVE
REVIEWED_SHA256 = "9d8b2a9ddbbb3093ee72b7c6bd9da4b9cb18b7feb23f445a243ddcb1b508a5d8"
CALLBACK = "HSM_AQR_record_native_outcome"
LEGACY_CALLBACK = "HSM_AQR_resolve_preparation"


def mission(text):
    parse(text.lstrip("\ufeff"))
    return one(list(walk(spans(text.lstrip("\ufeff")))), "JER_revolution_mission")


def patch(raw, callback=CALLBACK):
    decoded = raw.decode("utf-8")
    bom = "\ufeff" if decoded.startswith("\ufeff") else ""
    text = decoded[len(bom):]
    require(CALLBACK not in text and LEGACY_CALLBACK not in text, "Input already contains the callback; use the native snapshot")
    timeout = one(mission(text).children, "timeout_effect")
    last = timeout.children[-1]
    require(last.key == "hidden_effect" and len(last.children) == 1
            and last.children[0].key == "set_global_flag"
            and last.children[0].value == "JER_revolution_begun",
            "Native timeout ending drifted; callback must follow native resolution")
    newline = "\r\n" if "\r\n" in text else "\n"
    hook = newline.join((
        "\thidden_effect = {",
        "\t\t\t\tif = {",
        "\t\t\t\t\tlimit = { OR = { original_tag = JEB original_tag = JRR original_tag = JFT original_tag = VIN } }",
        f"\t\t\t\t\t{callback} = yes",
        "\t\t\t\t}",
        "\t\t\t}",
        "\t\t",
    ))
    at = timeout.end - 1
    result = text[:at] + hook + text[at:]
    parse(result)
    # The callback is one trailing effect, not a replacement for native logic.
    changed_timeout = one(mission(result).children, "timeout_effect")
    require(len(changed_timeout.children) == len(timeout.children) + 1,
            "Expected exactly one appended timeout effect")
    require(result[:at] == text[:at] and result[at + len(hook):] == text[at:],
            "Native bytes changed beyond the single callback insertion")
    return (bom + result).encode("utf-8")


def build(eaw, snapshot=SNAPSHOT):
    raw = Path(snapshot).read_bytes()
    live = (Path(eaw) / RELATIVE).read_bytes()
    digest, live_digest = hashlib.sha256(raw).hexdigest(), hashlib.sha256(live).hexdigest()
    require(raw == live,
            f"EaW drift: snapshot SHA256={digest}; installed SHA256={live_digest}. Review before rebuilding.")
    require(digest == REVIEWED_SHA256,
            f"Unreviewed JER decision baseline SHA256={digest}; expected {REVIEWED_SHA256}")
    return patch(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eaw", type=Path, required=True, help="Installed EaW root")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Read-only consistency check (default)")
    modes.add_argument("--apply", action="store_true", help="Write only the mission callback override")
    args = parser.parse_args()
    try:
        result = build(args.eaw)
        previous = OUTPUT.read_bytes() if OUTPUT.exists() else None
        if previous == result:
            print(f"OK: {OUTPUT.relative_to(ROOT)} (reviewed native SHA256 {REVIEWED_SHA256})")
            return 0
        require(previous is None or previous in (SNAPSHOT.read_bytes(), patch(SNAPSHOT.read_bytes(), LEGACY_CALLBACK)),
                "JER decisions override differs from the canonical patch/native snapshot; refusing unrelated edits")
        if not args.apply:
            print(f"STALE: {OUTPUT.relative_to(ROOT)}; --check wrote nothing")
            return 1
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(result)
        print(f"WROTE: {OUTPUT.relative_to(ROOT)}; one callback after native timeout resolution")
        return 0
    except (OSError, ValueError, AssertionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
