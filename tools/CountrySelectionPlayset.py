"""Inspect selector providers and declared dependencies, not runtime UI behaviour."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("playset_parser", Path(__file__).with_name("Test-Verenia.py"))
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)

TITLE = "Equestria at War: Expanded Stories"
FILES = ("common/bookmarks/z_scenario_main.txt", "interface/frontendgamesetupview.gui")


def mod_info(user_dir, registry):
    descriptor = (user_dir / registry).resolve()
    if not descriptor.is_relative_to(user_dir.resolve()):
        raise ValueError(f"Descriptor outside the user directory: {registry}")
    nodes = BASE.read(descriptor)
    values = BASE.Node("descriptor", "=", nodes)
    root = values.get("path")
    if not root:
        raise ValueError(f"Archived or unresolved mod: {registry}; inspect its load order manually.")
    return {"registry": registry, "descriptor": descriptor, "root": Path(root).resolve(),
            "name": values.get("name"), "dependencies": [n.key for n in values.get("dependencies", [])],
            "replaces": [n.value.replace("\\", "/").rstrip("/") for n in values.all("replace_path")]}


def overrides(mod, relative):
    return (mod["root"] / relative).is_file() or any(
        relative == parent or relative.startswith(parent + "/") for parent in mod["replaces"])


def ordered_after(mod, other, mods):
    by_name = {m["name"]: m for m in mods}
    pending = list(mod.get("dependencies", []))
    visited = set()
    while pending:
        name = pending.pop()
        if name == other["name"]:
            return True
        if name not in visited:
            visited.add(name)
            pending.extend(by_name.get(name, {}).get("dependencies", []))
    return False


def conflicts(mods):
    own = [m for m in mods if m["root"] == BASE.MOD.resolve()]
    if len(own) != 1:
        raise ValueError("Enable exactly one copy of Expanded Stories before checking the selector.")
    return own[0], [m for m in mods if m is not own[0] and any(overrides(m, path) for path in FILES)
                    and (not ordered_after(own[0], m, mods) or ordered_after(m, own[0], mods))]


def visible_title(text):
    result, count = re.subn(r'(?m)^name\s*=\s*"[^"\r\n]*"', f'name="{TITLE}"', text)
    if count != 1:
        raise ValueError("Expected one descriptor name; no files were changed.")
    return result


def sync_dependencies(text):
    """Merge repository load-after declarations; preserve local-only dependencies."""
    values = BASE.Node("descriptor", "=", BASE.parse(text))
    blocks = values.all("dependencies")
    if len(blocks) > 1:
        raise ValueError("Multiple dependency blocks; reconcile the descriptor manually.")
    expected = BASE.Node("descriptor", "=", BASE.read(BASE.MOD / "descriptor.mod"))
    names = list(dict.fromkeys([n.key for n in values.get("dependencies", [])]
                              + [n.key for n in expected.get("dependencies", [])]))
    replacement = "dependencies={\n" + "".join(f'    "{name}"\n' for name in names) + "}"
    if not blocks:
        return text.rstrip() + "\n" + replacement + "\n"
    # A dependencies block contains only quoted names, not nested script blocks.
    pattern = r'(?m)^\s*dependencies\s*=\s*\{(?:"[^"\r\n]*"|#[^\r\n]*|[^{}"])*\}'
    updated, count = re.subn(pattern, lambda _: replacement, text)
    if count != 1:
        raise ValueError("Cannot safely locate the dependency block; no files were changed.")
    return updated


def inspect(user_dir):
    config = json.loads((user_dir / "dlc_load.json").read_text(encoding="utf-8-sig"))
    mods = [mod_info(user_dir, entry) for entry in config["enabled_mods"]]
    own, shadowing = conflicts(mods)
    for relative in FILES:
        providers = [m for m in mods if overrides(m, relative)]
        print(f"{relative}: providers = " + ", ".join(m["name"] for m in providers))
    for mod in shadowing:
        print(f"UNRESOLVED PRIORITY: {mod['name']}; launcher position alone is not proof of file precedence.")
    return config, mods, own, shadowing


def repair(user_dir, config, mods, own, shadowing):
    database = user_dir / "launcher-v2.sqlite"
    if not database.is_file():
        raise ValueError("Launcher database missing; inspect the registered mod before applying.")
    connection = sqlite3.connect(database, timeout=3)
    try:
        active = connection.execute("SELECT id FROM playsets WHERE isActive=1 AND isRemoved=0").fetchall()
        if len(active) != 1:
            raise ValueError("Expected one active launcher playset.")
        playset = active[0][0]
        rows = connection.execute(
            "SELECT pm.modId, pm.enabled, m.gameRegistryId, m.dirPath FROM playsets_mods pm "
            "JOIN mods m ON m.id=pm.modId WHERE pm.playsetId=? ORDER BY pm.position", (playset,)).fetchall()
        if [r[2] for r in rows if r[1]] != config["enabled_mods"]:
            raise ValueError("Launcher and launch configuration disagree; reopen the launcher and retry.")
        selected = [r for r in rows if r[2] == own["registry"]]
        if len(selected) != 1 or Path(selected[0][3]).resolve() != BASE.MOD.resolve():
            raise ValueError("Launcher mod identity differs from the checked workspace.")
        descriptor_text = own["descriptor"].read_text(encoding="utf-8-sig")
        renamed = sync_dependencies(visible_title(descriptor_text))
        updated_own = {**own, "dependencies": [n.key for n in BASE.Node("descriptor", "=", BASE.parse(renamed)).get("dependencies", [])]}
        updated_mods = [updated_own if m["registry"] == own["registry"] else m for m in mods]
        for mod in shadowing:
            if not ordered_after(updated_own, mod, updated_mods) or ordered_after(mod, updated_own, updated_mods):
                raise ValueError(f"Unresolved dependency conflict with {mod['name']}; no launcher files were changed.")
        config_path = user_dir / "dlc_load.json"
        original_descriptor = own["descriptor"].read_bytes()

        backup = BASE.ROOT / "outputs/launcher-backup" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup.mkdir(parents=True)
        shutil.copy2(config_path, backup / "dlc_load.json")
        shutil.copy2(own["descriptor"], backup / "local-descriptor.mod")
        with closing(sqlite3.connect(backup / "launcher-v2.sqlite")) as snapshot:
            connection.backup(snapshot)
        try:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("UPDATE mods SET displayName=? WHERE id=?", (TITLE, selected[0][0]))
                own["descriptor"].write_text(renamed, encoding="utf-8", newline="")
        except Exception:
            own["descriptor"].write_bytes(original_descriptor)
            raise
        print(f"Backup: {backup}")
        print("Synchronized this mod's name and dependency declarations. Playset order and enabled mods are unchanged.")
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-dir", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="Close the game and launcher first; saves a backup.")
    args = parser.parse_args()
    config, mods, own, shadowing = inspect(args.user_dir)
    if args.apply:
        repair(args.user_dir, config, mods, own, shadowing)
        _, _, own, shadowing = inspect(args.user_dir)
    if shadowing:
        raise SystemExit("Selector priority is not explicitly resolved; inspect descriptor dependencies.")
    if own["name"] != TITLE:
        raise SystemExit("The registered descriptor still has the old name.")
    bookmark = BASE.Node("root", "=", BASE.read(own["root"] / FILES[0]))
    labels = [n.key for n in BASE.walk(bookmark.children) if n.key == "HSM_CSS_Filter"]
    if len(labels) != 5:
        raise SystemExit("Expected one ordered filter and four country labels.")
    print("OK (static): four cards exist and dependencies order this mod after known selector providers.")
    print("Restart HOI4 and check the fourth tab; this check cannot confirm which file the running game loaded or whether clicks work.")


if __name__ == "__main__":
    main()
