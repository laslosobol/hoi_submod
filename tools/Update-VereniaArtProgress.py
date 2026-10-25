"""Reconcile progress from reviewed assets and live bindings; never bind/export art.

Default is a READ-ONLY preview: it never updates progress.json.
--apply writes only art/verenia/progress.json; --check is read-only and exits
1 for stale progress, 0 when current. --self-test uses in-memory fault injection.
Batch 01 alone supports its historical review+hash approval convention; later
portraits require portrait-bindings approval, icons require approved=true.
Scoped companies use company-bindings approval, inline hashes and live policy
checks; their sources/exports are deduplicated against optional export batches.
Counts are static integration evidence, not visual approval or in-game QA.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = "mod/HoISubmod/"
ART = "art/verenia/"
PROGRESS = ART + "progress.json"
LEGACY = {"vincent", "iovinus", "katrina", "trubach", "corporation",
          "union", "regency", "spirit"}
def load_parser_api():
    """The legacy validator parses argv at load time; never expose our CLI."""
    saved = sys.argv
    try:
        sys.argv = [str(ROOT / "tools/Test-Verenia.py")]
        return runpy.run_path(sys.argv[0])
    finally:
        sys.argv = saved


API = load_parser_api()
parse, walk = API["parse"], API["walk"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Snapshot:
    def __init__(self, root=ROOT):
        self.root = root
        self.data = {}
        self.listings = {}

    def path(self, name):
        path = (self.root / name).resolve()
        require(path.is_relative_to(self.root.resolve()), f"Path escapes repository: {name}")
        return path

    def read(self, name):
        if name not in self.data:
            path = self.path(name)
            self.data[name] = path.read_bytes() if path.is_file() else None
        return self.data[name]

    def json(self, name):
        raw = self.read(name)
        require(raw is not None, f"Missing required input: {name}")
        return json.loads(raw.decode("utf-8-sig"))

    def glob(self, folder, pattern):
        key = folder, pattern
        if key not in self.listings:
            self.listings[key] = sorted(p.relative_to(self.root).as_posix()
                                        for p in (self.root / folder).glob(pattern))
        return self.listings[key]

    def verify(self):
        for name, raw in self.data.items():
            path = self.path(name)
            require((path.read_bytes() if path.is_file() else None) == raw,
                    f"Concurrent input change: {name}; rerun")
        for (folder, pattern), names in self.listings.items():
            require(sorted(p.relative_to(self.root).as_posix()
                           for p in (self.root / folder).glob(pattern)) == names,
                    f"Concurrent file-list change: {folder}; rerun")


def nodes(files, name):
    raw = files.read(name)
    require(raw is not None, f"Missing definition: {name}")
    return parse(raw.decode("utf-8-sig"))


def effective(files, name):
    if name.startswith("EaW/"):
        override = MOD + name[4:]
        if files.read(override) is not None:
            return override
    return name


def select(tree, selector):
    for key, index in selector:
        matches = [n for n in tree if n.key == key]
        require(index < len(matches), f"Missing selector: {key}[{index}]")
        node = matches[index]
        tree = node.children
    return node.value


def sprites(files):
    result = {}
    # Mod files shadow same-named EaW files, then individual sprite aliases.
    mod = files.glob(MOD + "interface", "**/*.gfx")
    shadowed = {p.removeprefix(MOD) for p in mod}
    paths = [p for p in files.glob("EaW/interface", "**/*.gfx")
             if p.removeprefix("EaW/") not in shadowed] + mod
    for path in paths:
        for n in walk(nodes(files, path)):
            if n.key.lower() == "spritetype":
                fields = {c.key.lower(): c.value for c in n.children}
                if fields.get("name") and isinstance(fields.get("texturefile"), str):
                    result[fields["name"]] = fields["texturefile"].replace("\\", "/")
    return result


def checked_hash(files, path, expected):
    raw = files.read(path)
    require(raw is not None and isinstance(expected, str)
            and hashlib.sha256(raw).hexdigest() == expected.lower(),
            f"Missing/unreviewed asset: {path}")


def company_evidence(files, data, row, gfx, api):
    """Use the company binder's policy and transformation, never legacy portraits."""
    target = row["id"]
    require(data.get("binding_policy") == api["POLICY"]
            and data.get("schema_version") == 1
            and data.get("source_file") == api["SOURCE"]
            and data.get("countries") == list(api["TAGS"]), "Company scope/policy mismatch")
    require(target in api["CATEGORIES"] and row.get("target") == target
            and row.get("clone") == api["clone_id"](target)
            and row.get("category") == api["CATEGORIES"][target]
            and row.get("file") == api["SOURCE"]
            and row.get("kind") == "manufacturer", "Company identity mismatch")
    require(row.get("approved") is True, "Company not approved")
    checked_hash(files, api["SOURCE"], data.get("source_file_sha256"))
    native = files.read(api["SOURCE"])
    node, _ = api["definition"](native, target)
    require(next(n.value for n in node.children if n.key == "picture")
            == row.get("original_picture"), "Company picture pin mismatch")
    api["API"]["relative"](row["source"], ART.rstrip("/"))
    checked_hash(files, row["source"], row.get("source_sha256"))
    require(len(row["exports"]) == 1, "Expected one company export")
    export = row["exports"][0]
    path = MOD + f"gfx/interface/ideas/HSM_VER_COMP/{target}.tga"
    require(export["path"] == path and (export["width"], export["height"]) == (64, 64),
            "Company export path/size mismatch")
    checked_hash(files, path, export.get("sha256"))
    api["API"]["native_tga"](files.read(path), (64, 64))
    actual = files.read(api["OUTPUT"])
    require(actual is not None, "Company override missing")
    keys = {n.key for n in walk(parse(actual.decode("utf-8-sig")))}
    selected = {t for t in api["CATEGORIES"] if api["clone_id"](t) in keys}
    require(target in selected, "Company clone not bound")
    require(actual == api["transformed"](native, selected), "Company override/policy drift")
    clone = api["clone_id"](target)
    for other in files.glob(MOD + "common/ideas", "**/*.txt"):
        if other != api["OUTPUT"]:
            require(not any(n.key == clone for n in walk(nodes(files, other))),
                    f"Duplicate company clone: {other}")
    alias = "GFX_idea_" + clone
    matches = []
    for other in files.glob(MOD + "interface", "**/*.gfx"):
        matches.extend(other for n in walk(nodes(files, other))
                       if n.key.lower() == "spritetype" and n.get("name") == alias)
    require(matches == [api["GFX"]] and gfx.get(alias) == path.removeprefix(MOD),
            "Missing/ambiguous company sprite")
    return "company", target


def binding_evidence(files, row, batch, hashes, portraits, catalog, gfx):
    target = row.get("target", row["id"])
    portrait = portraits.get(target)
    legacy = batch == "01" and row["id"] in LEGACY
    if "approved" in row:
        require(row["approved"] is True, "Manifest not approved")
    elif legacy:
        require(bool(row.get("review")), "Missing legacy review")
    else:
        require(portrait is not None and portrait.get("approved") is True,
                "No explicit approval")
    source = row["source"]
    checked_hash(files, source, hashes.get(source))
    exports = row["exports"]
    require(exports, "No exports")
    for export in exports:
        path = export["path"]
        require(path.startswith(MOD + "gfx/"), "Export outside mod graphics")
        checked_hash(files, path, hashes.get(path))
        raw = files.read(path)
        require(len(raw) >= 18 and raw[2] == 2 and raw[16] == 32
                and int.from_bytes(raw[12:14], "little") == export["width"]
                and int.from_bytes(raw[14:16], "little") == export["height"],
                f"Invalid native export: {path}")
    paths = {e["path"].removeprefix(MOD) for e in exports}
    if portrait is not None:
        require(portrait["source"] == source, "Portrait source mismatch")
        require(legacy or portrait.get("approved") is True, "Portrait not approved")
        if not legacy:
            checked_hash(files, source, portrait.get("source_sha256"))
        bound = set()
        require(portrait["bindings"], "No portrait selectors")
        related = [p for p in portraits.values() if p["source"] == source]
        bindings = []
        for peer in related:
            require(legacy or (peer.get("approved") is True and peer.get("bindable") is True),
                    f"Unapproved/unbindable shared source: {peer['id']}")
            if not legacy:
                checked_hash(files, source, peer.get("source_sha256"))
            bindings.extend(peer["bindings"])
        for binding in bindings:
            name = effective(files, "EaW/" + binding["file"])
            value = select(nodes(files, name), binding["selector"])
            value = gfx.get(value, value)
            # Manufacturer picture values are implicit GFX_idea_ aliases.
            value = gfx.get("GFX_idea_" + value, value)
            expected = binding["export"]["path"].removeprefix(MOD)
            require(value == expected and expected in paths, f"Unbound selector: {target}")
            if not legacy:
                checked_hash(files, binding["export"]["path"], binding["export"].get("sha256"))
            bound.add(expected)
        require(bound == paths, f"Unbound exports: {target}")
        return "portrait" if row.get("portrait") else "institution", target
    if legacy and row["id"] == "spirit":
        matches = [n for n in nodes(files, MOD + "common/dynamic_modifiers/HSM_VER_spirit.txt")
                   if n.key == target]
        kind, field = "unified_spirit", "icon"
    else:
        kind = row.get("kind", "focus" if legacy else None)
        require(kind in ("focus", "spirit"), "Unknown target kind")
        definition = catalog.get((kind, target))
        require(definition is not None, f"Target outside catalog: {target}")
        require(legacy or row.get("file") == definition["file"], "Definition file mismatch")
        tree = nodes(files, effective(files, definition["file"]))
        if kind == "focus":
            matches = [n for n in walk(tree) if n.key in ("focus", "shared_focus", "joint_focus")
                       and n.get("id") == target]
        else:
            matches = [n for n in walk(tree) if n.key == target]
        field = "icon" if kind == "focus" else "picture"
    require(len(matches) == 1, f"Missing/ambiguous target: {target}")
    value = matches[0].get(field)
    alias = value if value.startswith("GFX_") else "GFX_idea_" + value
    require(len(paths) == 1 and gfx.get(alias) in paths, f"Unbound sprite: {target}")
    if kind == "focus":
        require(gfx.get(alias + "_shine") in paths, f"Unbound shine sprite: {target}")
    return kind, target


def reconcile(files):
    previous = files.json(PROGRESS)
    original = files.json(ART + "icon-briefs.json")["records"]
    native = files.json(ART + "native-spirit-briefs.json")["records"]
    catalog = {}
    for row in original + native:
        key = row["kind"], row["id"]
        require(key not in catalog, f"Duplicate brief: {key}")
        catalog[key] = row
    for row in files.json(ART + "inventory.json"):
        if row["kind"] in ("focus", "spirit"):
            catalog.setdefault((row["kind"], row["id"]), row)
    portraits = {r["id"]: r for r in files.json(ART + "portrait-bindings.json")["records"]}
    gfx = sprites(files)
    company_api = runpy.run_path(str(ROOT / "tools/Bind-VereniaCompanies.py"))
    company_data = files.json(ART + "company-bindings.json")
    company_rows = {r["id"]: r for r in company_data["records"]}
    require(len(company_rows) == len(company_data["records"])
            and set(company_rows) == set(company_api["CATEGORIES"]),
            "Expected eleven unique company records")
    company_complete, company_diagnostics = set(), []
    for target, row in company_rows.items():
        try:
            company_evidence(files, company_data, row, gfx, company_api)
        except (ValueError, KeyError, TypeError) as error:
            company_diagnostics.append({"id": target, "reason": str(error)})
        else:
            company_complete.add(target)
    complete, sources, exports, seen, batches, diagnostics = set(), set(), set(), set(), {}, []
    kinds = {}
    for manifest in files.glob(ART.rstrip("/"), "batch-*.json"):
        match = re.fullmatch(r"batch-(\d+)\.json", Path(manifest).name)
        if not match:
            continue
        batch = match[1]
        rows = files.json(manifest)
        baseline = manifest[:-5] + "-hashes.json"
        hashes = files.json(baseline) if files.read(baseline) is not None else {}
        integrated = 0
        for row in rows:
            target = row.get("target", row["id"])
            key = row.get("kind", "legacy_or_portrait"), target
            require(key not in seen, f"Duplicate manifest target: {key}")
            seen.add(key)
            try:
                if target in company_rows:
                    company = company_rows[target]
                    require(target in company_complete, "Company approval/hash/binding incomplete")
                    require(row["source"] == company["source"] and row.get("approved") is True
                            and row.get("kind") == "manufacturer"
                            and row.get("file") == company["file"]
                            and row["id"] == target, "Company batch mismatch")
                    require([{k: e[k] for k in ("path", "width", "height")} for e in row["exports"]]
                            == [{k: e[k] for k in ("path", "width", "height")} for e in company["exports"]],
                            "Company batch exports mismatch")
                    for path in [row["source"]] + [e["path"] for e in row["exports"]]:
                        checked_hash(files, path, hashes.get(path))
                    kind = "company"
                else:
                    kind, target = binding_evidence(files, row, batch, hashes, portraits, catalog, gfx)
            except (ValueError, KeyError, TypeError) as error:
                diagnostics.append({"batch": batch, "id": target, "reason": str(error)})
                continue
            integrated += 1
            complete.add((kind, target))
            sources.add(row["source"])
            exports.update(e["path"] for e in row["exports"])
            kinds.setdefault(kind, set()).add(row["source"])
        batches[batch] = {"records": len(rows), "integrated_records": integrated}
    for target in company_complete:
        row = company_rows[target]
        complete.add(("company", target))
        sources.add(row["source"])
        exports.update(e["path"] for e in row["exports"])
        kinds.setdefault("company", set()).add(row["source"])
    result = copy.deepcopy(previous)
    runtime_api = runpy.run_path(str(ROOT / 'tools/Bind-VereniaRuntimeArt.py'))
    runtime_complete, runtime_diagnostics = [], []
    try:
        runtime_outputs, candidates = runtime_api['plan'](files)
        require(all(files.read(p) == raw for p, raw in runtime_outputs.items()),
                'Runtime artwork scripts are stale or missing')
        runtime_complete = candidates
    except (ValueError, KeyError, TypeError) as error:
        runtime_diagnostics.append(str(error))
    runtime_new_sources = {}
    for kind, row in runtime_complete:
        runtime_new_sources.setdefault(kind, set()).update({row['source']} - sources)
        sources.add(row['source'])
        exports.update(e['path'] for e in row['exports'])
    result['completed_mio_records'] = sum(k == 'mio' for k, r in runtime_complete)
    result['completed_mio_new_sources'] = len(runtime_new_sources.get('mio', set()))
    result['completed_generated_advisor_templates'] = sum(k == 'generated_advisor' for k, r in runtime_complete)
    result['completed_generated_advisor_sources'] = len(runtime_new_sources.get('generated_advisor', set()))
    result['runtime_art_diagnostics'] = runtime_diagnostics
    for kind, manifest in [('mio', 'mio-bindings.json'), ('generated_advisor', 'generated-advisor-bindings.json')]:
        covered = {r['id'] for k, r in runtime_complete if k == kind}
        result['pending_' + kind + '_records'] = [r['id'] for r in files.json(ART + manifest)['records'] if r['id'] not in covered]
    result.update({
        "status": "incomplete", "completed_batches": [b for b, v in batches.items()
            if v["records"] and v["records"] == v["integrated_records"]],
        "integrated_sources": len(sources), "game_exports": len(exports),
        "completed_focus_icons": sum(k == "focus" for k, _ in complete),
        "completed_spirit_icons": sum(k == "spirit" for k, _ in complete),
        "completed_named_portrait_sources": len(kinds.get("portrait", set())),
        "completed_institution_sources": len(kinds.get("institution", set())),
        "completed_unified_spirit_sources": len(kinds.get("unified_spirit", set())),
        "completed_company_icons": len(company_complete),
        "completed_company_sources": len(kinds.get("company", set())),
        "pending_company_records": [{"kind": "manufacturer", "id": t}
                                    for t in company_rows if t not in company_complete],
        "company_diagnostics": company_diagnostics,
        "pending_original_briefs": [{"kind": r["kind"], "id": r["id"]} for r in original
                                    if (r["kind"], r["id"]) not in complete],
        "additional_native_spirit_briefs": ART + "native-spirit-briefs.json",
        "additional_native_spirits": len(native),
        "pending_native_spirit_briefs": [{"kind": r["kind"], "id": r["id"]} for r in native
                                        if (r["kind"], r["id"]) not in complete],
        "completed_native_spirit_icons": sum((r["kind"], r["id"]) in complete for r in native),
        "next_original_brief_index": next((i for i, r in enumerate(original)
            if (r["kind"], r["id"]) not in complete), None),
        "batch_progress": batches, "unintegrated_records": diagnostics,
    })
    result["pending_counts"] = {
        "focus": sum(r["kind"] == "focus" for r in result["pending_original_briefs"]),
        "original_spirit": sum(r["kind"] == "spirit" for r in result["pending_original_briefs"]),
        "native_spirit": len(result["pending_native_spirit_briefs"]),
        "company": len(result["pending_company_records"]),
        "mio": len(result['pending_mio_records']),
        "generated_advisor": len(result['pending_generated_advisor_records']),
    }
    result["spirit_progress"] = {
        "completed_country_idea_icons": result["completed_spirit_icons"],
        "completed_unified_dynamic_spirit_sources": result["completed_unified_spirit_sources"],
        "completed_spirit_sources_total": len(kinds.get("spirit", set())
                                               | kinds.get("unified_spirit", set())),
        "pending_country_idea_icons": (result["pending_counts"]["original_spirit"]
                                       + result["pending_counts"]["native_spirit"]),
        "counting_note": "completed_spirit_icons counts separate country ideas only. The preexisting unified dynamic spirit is reported separately and included in integrated_sources and completed_spirit_sources_total; it does not complete its component ideas.",
    }
    blocker_path = previous.get("blockers", ART + "generation-blockers.json")
    result["explicit_blockers"] = files.json(blocker_path) if isinstance(blocker_path, str) else copy.deepcopy(blocker_path)
    result["explicit_blocker_count"] = len(result["explicit_blockers"])
    result['generated_advisor_templates'] = (
        f"{result['completed_generated_advisor_templates']}/30 generated advisor templates approved, hash-verified and bound; "
        "separate from named characters; in-game verification pending")
    result['mio_organizations'] = (
        f"{result['completed_mio_records']}/10 generic MIO organizations bound with country-scoped artwork effects; "
        "no global replacements; in-game verification pending")
    result['legacy_manufacturers'] = (
        f"{result['completed_company_icons']}/11 companies approved, hash-verified and bound under preserve-hired-v2; "
        "native stats preserved; in-game verification pending")
    result['notes'] = (
        f"Static artwork integration checkpoint with {result['explicit_blocker_count']} recorded generation blockers. "
        "Approved assets and reviews are recorded in export/batch and binding manifests. "
        "Blocked targets retain original artwork; generated advisor templates and MIO coverage are counted separately. "
        "In-game verification remains pending.")
    archives, historical_targets = [], set()
    for name in files.glob(ART.rstrip('/'), 'generation-blockers-archive-*.json'):
        entries = files.json(name)
        historical_targets.update(entries)
        archives.append({'path': name, 'sha256': hashlib.sha256(files.read(name)).hexdigest(),
                         'records': len(entries)})
    bound_targets = {target for kind, target in complete}
    result['rejection_history_archives'] = archives
    result['historical_blocked_targets'] = len(historical_targets)
    result['resolved_historical_blocked_targets'] = len(historical_targets & bound_targets)
    integrated = (not any(result['pending_counts'].values())
                  and not result['explicit_blocker_count'] and not diagnostics
                  and not company_diagnostics and not runtime_diagnostics)
    result['status'] = 'artwork_integrated_runtime_pending' if integrated else 'incomplete'
    if integrated:
        result['notes'] = (
            'All tracked artwork is approved, hash-verified and statically bound. '
            f"All {len(historical_targets)} historically blocked targets are covered; prior failed-attempt records remain in the byte-preserved rejection archives. "
            'Generated advisor templates and MIO mappings are counted separately from named characters and unique sources. '
            'In-game verification remains pending; this is not a runtime QA claim.')
    # Preserve historical test claims, but never present them as current checks.
    if "validation" in result:
        result.setdefault("previous_checkpoint_validation", result.pop("validation"))
    result["progress_validation"] = {
        "method": "Approved sources and exports with matching SHA256; actual definition/selector and sprite texture bindings. All exports must bind before counting a source.",
        "legacy_approval": "Only the eight batch01 IDs accept historical review plus matching baseline hashes. Other portraits require portrait-bindings approved=true; other icons require manifest approved=true.",
        "not_run": "Image resampling comparison, fresh visual review, gameplay tests and in-game QA are not performed by this tool.",
        "scope": "Pending lists cover main and separate native briefs. Manufacturer/template/MIO notes and explicit blockers are retained; absence of pending icons is not full artwork completion.",
        "index": "next_original_brief_index is zero-based and includes blocked targets.",
        "companies": "company-bindings.json approval and inline hashes, native file pin, preserve-hired policy transformation and unique live clone/sprite bindings. Sources/exports deduplicated across batches; company counts are separate from institutions and spirits. Runtime and localization QA remain separate.",
        "runtime_art": "MIO and generated-advisor manifests require approval, asset hashes, native definition pins, exact selectors and matching generated effect/hooks/sprites. MIO records count separately from new sources; reused company sources are deduplicated. Generated templates never count as named characters. Engine runtime QA pending.",
    }
    return result


def company_self_test(files, expected):
    """Real binder transformations, synthetic assets, no filesystem writes."""
    api = runpy.run_path(str(ROOT / "tools/Bind-VereniaCompanies.py"))
    fixture = copy.deepcopy(files)
    data = fixture.json(ART + "company-bindings.json")
    # Isolate from future live company approvals.
    for r in data["records"]:
        r["approved"] = False
    row = data["records"][0]
    row["approved"] = True
    source, asset = row["source"], row["exports"][0]["path"]
    tga = bytearray(18 + 64 * 64 * 4)
    tga[2], tga[12], tga[14], tga[16], tga[17] = 2, 64, 64, 32, 8
    fixture.data[source], fixture.data[asset] = b"reviewed company", bytes(tga)
    row["source_sha256"] = hashlib.sha256(fixture.data[source]).hexdigest()
    row["exports"][0]["sha256"] = hashlib.sha256(fixture.data[asset]).hexdigest()
    native = fixture.read(api["SOURCE"])
    fixture.data[api["OUTPUT"]] = api["transformed"](native, {row["id"]})
    alias = "GFX_idea_" + row["clone"]
    fixture.data[api["GFX"]] = ('spriteTypes={spriteType={name=' + alias
        + ' texturefile="' + asset.removeprefix(MOD) + '"}}').encode()
    fixture.listings[(MOD + "common/ideas", "**/*.txt")] = [api["OUTPUT"]]
    fixture.listings[(MOD + "interface", "**/*.gfx")] = [api["GFX"]]
    gfx = {alias: asset.removeprefix(MOD)}

    def check():
        return company_evidence(fixture, data, row, gfx, api)

    require(check() == ("company", row["id"]), "Bound company omitted")
    def rejected():
        try:
            check()
        except (ValueError, KeyError, TypeError):
            return
        raise ValueError("Invalid company counted")
    for name in (source, asset, api["OUTPUT"], api["SOURCE"]):
        old = fixture.data[name]
        for replacement in (None, old + b"drift"):
            fixture.data[name] = replacement
            rejected()
        fixture.data[name] = old
    row["approved"] = False
    rejected()
    row["approved"] = True
    data["binding_policy"] = "obsolete"
    rejected()
    data["binding_policy"] = api["POLICY"]
    bound = fixture.data[api["OUTPUT"]]
    fixture.data[api["OUTPUT"]] = native
    rejected()
    fixture.data[api["OUTPUT"]] = bound
    gfx[alias] = "wrong.tga"
    rejected()
    gfx[alias] = asset.removeprefix(MOD)
    fixture.listings[(MOD + "interface", "**/*.gfx")].append("duplicate.gfx")
    fixture.data["duplicate.gfx"] = fixture.data[api["GFX"]]
    rejected()
    fixture.listings[(MOD + "interface", "**/*.gfx")].pop()
    # Exercise aggregate accounting with the same asset also present in a batch.
    from unittest.mock import patch
    aggregate = copy.deepcopy(files)
    aggregate.data[ART + "company-bindings.json"] = json.dumps(data).encode()
    def evidence(_files, _data, candidate, _gfx, _api):
        require(candidate["id"] == row["id"], "Company not approved")
        return "company", candidate["id"]
    with patch.dict(reconcile.__globals__, company_evidence=evidence):
        single = reconcile(aggregate)
        batch = dict(row, portrait=False)
        manifest = ART + "batch-99999.json"
        aggregate.data[manifest] = json.dumps([batch]).encode()
        aggregate.data[manifest[:-5] + "-hashes.json"] = json.dumps({
            source: row["source_sha256"], asset: row["exports"][0]["sha256"]}).encode()
        aggregate.data[source], aggregate.data[asset] = fixture.data[source], fixture.data[asset]
        aggregate.listings[(ART.rstrip("/"), "batch-*.json")].append(manifest)
        doubled = reconcile(aggregate)
    require(single["completed_company_icons"] == 1 and single["pending_counts"]["company"] == 10,
            "Company pending/completed accounting wrong")
    for key in ("completed_institution_sources", "completed_spirit_icons", "completed_focus_icons"):
        require(single[key] == expected[key], f"Company altered existing accounting: {key}")
    for key in ("integrated_sources", "game_exports", "completed_company_icons",
                "completed_institution_sources", "completed_spirit_icons", "completed_focus_icons"):
        require(single[key] == doubled[key], f"Company batch double counting: {key}")
    require(doubled["batch_progress"]["99999"]["integrated_records"] == 1,
            "Company export batch not recognized")
    print("Company self-test passed: approval, hashes, missing assets, policy/override drift, sprite collision, separate counts and batch deduplication.")


def self_test(files, expected):
    require(expected["batch_progress"].get("10") == {"records": 9, "integrated_records": 9},
            "Batch10 is not fully integrated; inspect diagnostics")
    require(reconcile(files) == expected, "Not deterministic")
    manifest = ART + "batch-10.json"
    first = files.json(manifest)[0]
    base = expected["integrated_sources"]
    from unittest.mock import patch
    saved = sys.argv
    with patch.object(runpy, "run_path", side_effect=lambda path:
                      require(sys.argv == [path], "Validator received caller arguments")):
        load_parser_api()
    require(sys.argv is saved, "Caller argv not restored")
    with patch.object(runpy, "run_path", side_effect=RuntimeError("fixture")):
        try:
            load_parser_api()
        except RuntimeError:
            pass
    require(sys.argv is saved, "Caller argv not restored after loader failure")
    for batch, count in (("11", 9), ("12", 8)):
        if batch in expected["batch_progress"]:
            require(expected["batch_progress"][batch] == {"records": count, "integrated_records": count},
                    f"Batch{batch} is not fully integrated")
    require(expected["spirit_progress"]["completed_unified_dynamic_spirit_sources"] == 1,
            "Unified dynamic spirit omitted")
    require(expected["spirit_progress"]["completed_country_idea_icons"]
            == expected["completed_spirit_icons"], "Country/dynamic spirit counts confused")
    real = binding_evidence

    def unbound(*args):
        if args[1]["id"] == first["id"]:
            raise ValueError("Injected unbound output")
        return real(*args)

    with patch.dict(reconcile.__globals__, binding_evidence=unbound):
        changed = reconcile(files)
    require(changed["integrated_sources"] == base - 1 and "10" not in changed["completed_batches"],
            "Unbound output counted")
    require(any(r["id"] == first["id"] for r in changed["pending_original_briefs"]), "Lost pending target")
    for name, replacement in [(first["source"], b"changed"),
                              (first["exports"][0]["path"], None)]:
        old = files.data[name]
        try:
            files.data[name] = replacement
            require(reconcile(files)["integrated_sources"] == base - 1, "Missing/drifted asset counted")
        finally:
            files.data[name] = old
    definition = first["file"]
    old = files.data[definition]
    try:
        alias = ("GFX_HSM_VER_ART_" + first["target"]).encode()
        require(alias in old, "Batch10 fixture has no current binding")
        files.data[definition] = old.replace(alias, b"GFX_unbound_test")
        require(reconcile(files)["integrated_sources"] == base - 1,
                "Actual definition drift counted")
    finally:
        files.data[definition] = old
    old = files.data[manifest]
    try:
        rows = files.json(manifest)
        rows[0]["approved"] = False
        files.data[manifest] = json.dumps(rows).encode()
        require(reconcile(files)["integrated_sources"] == base - 1, "Unapproved output counted")
        rows.append(rows[0])
        files.data[manifest] = json.dumps(rows).encode()
        try:
            reconcile(files)
        except ValueError as error:
            require("Duplicate" in str(error), "Unexpected duplicate failure")
        else:
            raise ValueError("Duplicate target accepted")
    finally:
        files.data[manifest] = old
    # Native definitions must read the mod override, never the upstream picture.
    fixture = Snapshot()
    source, asset = "art/verenia/test.png", MOD + "gfx/interface/ideas/test.tga"
    native_file = "EaW/common/ideas/zzz_AVI_ideas.txt"
    override = MOD + "common/ideas/zzz_AVI_ideas.txt"
    raw = bytearray(18 + 64 * 64 * 4)
    raw[2], raw[16] = 2, 32
    raw[12:14] = raw[14:16] = (64).to_bytes(2, "little")
    fixture.data.update({source: b"reviewed", asset: bytes(raw),
        native_file: b'ideas={country={test={picture=old}}}',
        override: b'ideas={country={test={picture=HSM_VER_ART_test}}}'})
    hashes = {p: hashlib.sha256(fixture.data[p]).hexdigest() for p in (source, asset)}
    row = {"id": "test", "target": "test", "kind": "spirit", "approved": True,
           "file": native_file, "source": source,
           "exports": [{"path": asset, "width": 64, "height": 64}]}
    catalog = {("spirit", "test"): {"file": native_file}}
    gfx = {"GFX_idea_HSM_VER_ART_test": asset.removeprefix(MOD)}
    require(binding_evidence(fixture, row, "99", hashes, {}, catalog, gfx) == ("spirit", "test"),
            "Native override not recognized")
    fixture.data[override] = None
    try:
        binding_evidence(fixture, row, "99", hashes, {}, catalog, gfx)
    except ValueError:
        pass
    else:
        raise ValueError("Unbound native output counted")
    require(expected["additional_native_spirits"] == 49, "Native scope drift")
    require(expected["explicit_blockers"] == files.json(ART + "generation-blockers.json"), "Blockers lost")
    company_self_test(files, expected)
    if expected['completed_mio_records']:
        damaged = copy.deepcopy(files)
        path = MOD + 'common/scripted_effects/HSM_VER_runtime_art.txt'
        damaged.data[path] = files.read(path) + b'\n# synthetic binding drift\n'
        rejected = reconcile(damaged)
        require(rejected['completed_mio_records'] == 0 and rejected['runtime_art_diagnostics'],
                'Runtime script drift was counted')
        require(expected['integrated_sources'] - rejected['integrated_sources'] ==
                expected['completed_mio_new_sources'] + expected['completed_generated_advisor_sources'],
                'Runtime records double counted reused sources')
        require(expected['completed_named_portrait_sources'] == rejected['completed_named_portrait_sources'],
                'Generated templates changed named-character count')
        print('Runtime progress self-test passed: script drift rejection, reused-source deduplication and separate template accounting.')
    print("Self-test passed: argv isolation/restoration, available batches10-12, separate dynamic spirit, deterministic, actual definition drift, unbound/unapproved/missing/drifted rejection, duplicate guard, native override/missing binding, 49 native spirits, blockers preserved.")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="write reconciled progress.json only")
    mode.add_argument("--check", action="store_true", help="read-only; exit 1 if stale, 0 if current")
    mode.add_argument("--self-test", action="store_true", help="read-only in-memory regression tests")
    args = parser.parse_args()
    files = Snapshot()
    result = reconcile(files)
    if args.self_test:
        self_test(files, result)
    changed = result != files.json(PROGRESS)
    files.verify()
    if args.apply and changed:
        files.path(PROGRESS).write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("integrated_sources", "game_exports", "completed_focus_icons",
        "completed_spirit_icons", "completed_unified_spirit_sources", "spirit_progress",
        "completed_company_icons", "completed_company_sources", "company_diagnostics",
        "completed_mio_records", "completed_mio_new_sources", "completed_generated_advisor_templates",
        "completed_generated_advisor_sources", "runtime_art_diagnostics",
        "explicit_blocker_count", "pending_counts", "completed_batches", "unintegrated_records")}, indent=2))
    if args.apply:
        print("APPLY: progress.json updated" if changed else "APPLY: progress.json already current; no write")
    elif args.check:
        print("CHECK: stale (exit 1); run with --apply to update" if changed else "CHECK: current (exit 0); no files written")
    else:
        print("READ-ONLY: no files written. " +
              ("Progress stale; run with --apply to update." if changed else "Progress current."))
    return int(args.check and changed)


if __name__ == "__main__":
    raise SystemExit(main())
