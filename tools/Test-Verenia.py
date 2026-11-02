"""Static integration checks and production-script fixtures, not an HOI4 emulator."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import unittest
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod/HoISubmod"
ARGS = argparse.ArgumentParser()
ARGS.add_argument("--eaw", type=Path, default=Path("C:/shit/Steam/steamapps/workshop/content/394360/1826643372"))
ARGS.add_argument("--game", type=Path, default=Path("C:/shit/Steam/steamapps/common/Hearts of Iron IV"))
OPT, REST = ARGS.parse_known_args()
TOKEN = re.compile(r'\s+|#[^\n]*|"(?:\\.|[^"\\])*"|[{}]|[<>!=]+|[^\s{}=<>!#"]+')


@dataclass
class Node:
    key: str
    op: str = ""
    value: str | list["Node"] = ""

    @property
    def children(self):
        return self.value if isinstance(self.value, list) else []

    def all(self, key):
        return [n for n in self.children if n.key == key]

    def get(self, key, default=""):
        found = self.all(key)
        return found[0].value if found else default


def parse(text):
    tokens = [t for t in TOKEN.findall(text) if not t.isspace() and not t.startswith("#")]
    pos = 0

    def block(nested=False):
        nonlocal pos
        result = []
        while pos < len(tokens):
            key = tokens[pos]
            pos += 1
            if key == "}":
                if not nested:
                    raise ValueError("Unexpected closing brace")
                return result
            if key == "{":
                raise ValueError("Unexpected opening brace")
            node = Node(key.strip('"'))
            if pos < len(tokens) and tokens[pos] in ("=", "<", ">", "<=", ">=", "!="):
                node.op = tokens[pos]
                pos += 1
                if pos >= len(tokens):
                    raise ValueError(f"Missing value for {key}")
                value = tokens[pos]
                pos += 1
                node.value = block(True) if value == "{" else value.strip('"')
            result.append(node)
        if nested:
            raise ValueError("Unclosed block")
        return result

    return block()


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.children)


def read(path):
    return parse(path.read_text(encoding="utf-8-sig"))


def verified_focus_art(record, hashes, read_asset):
    """Return the one permitted icon name, never infer approval from review text."""
    if record.get("approved") is not True or record.get("kind") != "focus":
        return None
    target = record["target"]
    if not re.fullmatch(r"[A-Za-z0-9_]+", target):
        raise ValueError(f"Invalid art target: {target}")
    exports = record["exports"]
    if len(exports) != 1 or (exports[0]["width"], exports[0]["height"]) != (99, 86):
        raise ValueError(f"Expected one native-size focus export: {target}")
    for name, prefix in ((record["source"], "art/verenia"),
                         (exports[0]["path"], "mod/HoISubmod/gfx")):
        path = Path(name)
        if (path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name
                or not path.is_relative_to(prefix)):
            raise ValueError(f"Out-of-scope art path: {name}")
        expected = hashes.get(name)
        if (not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected)
                or hashlib.sha256(read_asset(name)).hexdigest() != expected.lower()):
            raise ValueError(f"Art SHA256 missing/mismatch: {name}")
    return "GFX_HSM_VER_ART_" + target


def approved_native_focus_icon(target, definition, root=ROOT):
    candidates = []
    for manifest in sorted((root / "art/verenia").glob("batch-*.json")):
        batch = re.fullmatch(r"batch-(\d{2,})\.json", manifest.name)
        if not batch or int(batch[1]) <= 1:
            continue
        records = json.loads(manifest.read_text(encoding="utf-8-sig"))
        for record in records:
            if (record.get("target") != target or record.get("kind") != "focus"
                    or record.get("approved") is not True or record.get("file") != definition):
                continue
            baseline = manifest.with_name(manifest.stem + "-hashes.json")
            hashes = json.loads(baseline.read_text(encoding="utf-8-sig"))

            def read_asset(name):
                path = (root / name).resolve()
                if not path.is_relative_to(root.resolve()):
                    raise ValueError(f"Art symlink escapes repository: {name}")
                return path.read_bytes()

            name = verified_focus_art(record, hashes, read_asset)
            gfx = root / f"mod/HoISubmod/interface/HSM_VER_art_batch{batch[1]}.gfx"
            sprites = [n for n in walk(read(gfx)) if n.key == "spriteType"]
            texture = Path(record["exports"][0]["path"]).relative_to("mod/HoISubmod").as_posix()
            for sprite_name in (name, name + "_shine"):
                matching = [n for n in sprites if n.get("name") == sprite_name]
                if len(matching) != 1 or matching[0].get("textureFile") != texture:
                    raise ValueError(f"Approved art sprite/export mismatch: {sprite_name}")
            candidates.append(name)
    if len(candidates) > 1:
        raise ValueError(f"Duplicate approved focus art records: {target}")
    return candidates[0] if candidates else None


def effect_nodes(nodes):
    """Expose game effects for structural assertions without dropping guards."""
    result = []
    for node in nodes:
        if node.key == "hidden_effect":
            result.extend(effect_nodes(node.children))
        elif node.key not in {"custom_effect_tooltip", "show_ideas_tooltip"}:
            result.append(node)
    return result


def pre_union_idea_operations(nodes):
    """Compare legacy rewards across the storage-only spirit API migration.

    This does not expand arbitrary effects or discard guards. Post-union ledger
    behavior and numeric equivalence are tested separately in Test-VereniaSpirit.
    """
    result = []
    for n in nodes:
        if n.key == "effect_tooltip":
            continue
        if n.key == "hidden_effect":
            result.extend(pre_union_idea_operations(n.children))
        elif n.key.startswith(("HSM_VER_SP_add_", "HSM_VER_SP_remove_", "HSM_VER_SP_has_")):
            assert n.value == "yes"
            action, idea = n.key.removeprefix("HSM_VER_SP_").split("_", 1)
            result.append(Node({"add": "add_ideas", "remove": "remove_ideas", "has": "has_idea"}[action], "=", idea))
        elif n.key == "swap_ideas":
            result.extend([Node("remove_ideas", "=", n.get("remove_idea")), Node("add_ideas", "=", n.get("add_idea"))])
        else:
            result.append(Node(n.key, n.op, pre_union_idea_operations(n.children) if isinstance(n.value, list) else n.value))
    return result


def package_files():
    return sorted(p for p in MOD.rglob("*.txt") if p.name.startswith(("HSM_VER", "HSM_ERI", "HSM_EYR")))


def definitions(folder):
    result = {}
    # Native Grover guards delegate to the real Greifwald household predicate.
    for path in sorted((MOD / "common" / folder).glob("*.txt")):
        if not path.name.startswith(("HSM_VER", "HSM_AET")):
            continue
        for node in read(path):
            if node.key in result:
                raise ValueError(f"Duplicate {node.key}")
            result[node.key] = node.children
    return result


@dataclass
class Country:
    tag: str
    ai: bool = False
    exists: bool = True
    subject: bool = False
    capitulated: bool = False
    war: bool = False
    leader: str = ""
    faction: str = ""
    faction_leader: bool = False
    cosmetic: str = ""
    flags: set = field(default_factory=set)
    flag_days: dict = field(default_factory=dict)
    political_power: float = 0
    manpower: int = 0
    army_experience: float = 0
    ideas: set = field(default_factory=set)
    variables: dict = field(default_factory=dict)
    dynamic_modifiers: set = field(default_factory=set)
    wars: set = field(default_factory=set)
    focuses: set = field(default_factory=set)
    cores: set = field(default_factory=set)
    goals: set = field(default_factory=set)
    events: list = field(default_factory=list)


class World:
    def __init__(self):
        self.countries = {tag: Country(tag) for tag in ("ERI", "EYR", "AVI", "GRI")}
        self.countries["AET"] = Country("AET", exists=False)
        self.countries["ERI"].leader = "ERI_duke_vincent_erie"
        self.countries["EYR"].leader = "EYR_duke_iovinus_eyrie"
        self.countries["AVI"].leader = "AVI_lady_katrina_avian"
        self.triggers = definitions("scripted_triggers")
        self.effects = definitions("scripted_effects")
        self.events = {n.get("id"): n for p in (MOD / "events").glob("HSM_VER*.txt") for n in read(p) if n.key == "country_event"}
        self.global_flags = set()
        self.root = "ERI"
        self.sender = "EYR"
        self.trace = []

    def resolve(self, value):
        return {"ROOT": self.root, "FROM": self.sender}.get(value, value)

    def check(self, nodes, tag="ERI"):
        c = self.countries[tag]
        for n in nodes:
            v = n.value
            if n.key in self.countries:
                ok = self.check(n.children, n.key)
            elif n.key in ("ROOT", "FROM"):
                ok = self.check(n.children, self.resolve(n.key))
            elif n.key in self.triggers:
                ok = self.check(self.triggers[n.key], tag) == (v == "yes")
            elif n.key == "AND":
                ok = self.check(n.children, tag)
            elif n.key == "OR":
                ok = any(self.check([child], tag) for child in n.children)
            elif n.key == "NOT":
                ok = not any(self.check([child], tag) for child in n.children)
            elif n.key in ("hidden_trigger", "custom_trigger_tooltip"):
                ok = self.check([x for x in n.children if x.key != "tooltip"], tag)
            elif n.key == "always":
                ok = v == "yes"
            elif n.key in ("tag", "original_tag"):
                ok = c.tag == self.resolve(v)
            elif n.key == "has_cosmetic_tag":
                ok = c.cosmetic == v
            elif n.key == "has_dynamic_modifier":
                ok = n.get("modifier") in c.dynamic_modifiers
            elif n.key in ("exists", "is_subject", "has_capitulated", "has_war", "is_faction_leader", "is_ai"):
                attr = {"exists": "exists", "is_subject": "subject", "has_capitulated": "capitulated", "has_war": "war", "is_faction_leader": "faction_leader", "is_ai": "ai"}[n.key]
                ok = bool(getattr(c, attr)) == (v == "yes")
            elif n.key == "is_in_faction":
                ok = bool(c.faction) == (v == "yes")
            elif n.key == "is_in_faction_with":
                ok = bool(c.faction) and c.faction == self.countries[self.resolve(v)].faction
            elif n.key == "has_war_with":
                ok = self.resolve(v) in c.wars
            elif n.key == "has_border_war_with":
                ok = False
            elif n.key in ("has_country_flag", "has_idea", "has_completed_focus"):
                attr = {"has_country_flag": "flags", "has_idea": "ideas", "has_completed_focus": "focuses"}[n.key]
                ok = v in getattr(c, attr)
            elif n.key == "has_global_flag":
                ok = v in self.global_flags
            elif n.key == "focus_progress":
                progress = n.all("progress")
                assert len(progress) == 1 and progress[0].op == ">", "Only documented progress > thresholds are modelled"
                ok = getattr(c, "focus_progress", {}).get(n.get("focus"), 0.0) > float(progress[0].value)
            elif n.key == "has_focus_tree":
                ok = getattr(c, "focus_tree", "") == v
            elif n.key == "has_country_leader":
                ok = c.leader == n.get("character")
            else:
                raise AssertionError(f"Fixture evaluator has no predicate: {n.key}")
            if not ok:
                return False
        return True

    def test(self, name, tag="ERI"):
        return self.check(self.triggers[name], tag)

    def apply(self, name, tag="ERI"):
        self.run(self.effects[name], tag)

    def run(self, nodes, tag="ERI"):
        c = self.countries[tag]
        branch_taken = None
        for n in nodes:
            v = n.value
            if n.key == "if":
                branch_taken = self.check(n.get("limit", []), tag)
                if branch_taken:
                    self.run([x for x in n.children if x.key != "limit"], tag)
            elif n.key == "else_if":
                if not branch_taken and self.check(n.get("limit", []), tag):
                    branch_taken = True
                    self.run([x for x in n.children if x.key != "limit"], tag)
            elif n.key == "else":
                if not branch_taken:
                    self.run(n.children, tag)
                branch_taken = True
            elif n.key == "hidden_effect":
                self.run(n.children, tag)
            elif n.key in self.countries:
                self.run(n.children, n.key)
            elif n.key in self.effects:
                self.apply(n.key, tag)
            elif n.key == "set_country_flag":
                flag = n.get("flag") if n.children else v
                c.flags.add(flag)
                if n.children and n.get("days"):
                    c.flag_days[flag] = int(n.get("days"))
            elif n.key == "clr_country_flag":
                c.flags.discard(v)
                c.flag_days.pop(v, None)
            elif n.key == "unlock_national_focus":
                # History-only completion, unlike executing a completion reward.
                c.focuses.add(v)
            elif n.key == "uncomplete_national_focus":
                assert not n.get("uncomplete_children"), "Recursive uncompletion is not modelled"
                c.focuses.discard(n.get("focus"))
            elif n.key == "add_political_power":
                c.political_power += float(v)
            elif n.key == "add_manpower":
                c.manpower += int(v)
            elif n.key == "army_experience":
                c.army_experience += float(v)
            elif n.key == "add_ideas":
                c.ideas.add(v)
            elif n.key == "remove_ideas":
                c.ideas.discard(v)
            elif n.key in ("set_variable", "add_to_variable"):
                assert len(n.children) == 1 and not n.children[0].children
                variable = n.children[0]
                value = float(variable.value)
                c.variables[variable.key] = value + (c.variables.get(variable.key, 0) if n.key == "add_to_variable" else 0)
            elif n.key == "add_dynamic_modifier":
                c.dynamic_modifiers.add(n.get("modifier"))
            elif n.key == "remove_dynamic_modifier":
                c.dynamic_modifiers.discard(n.get("modifier"))
            elif n.key == "force_update_dynamic_modifier":
                assert v == "yes"
            elif n.key == "remove_state_core":
                c.cores.discard(v)
            elif n.key == "remove_wargoal":
                c.goals.discard((n.get("type"), n.get("target")))
            elif n.key == "country_event":
                c.events.append(n.get("id"))
            elif n.key == "create_faction":
                c.faction = v
                c.faction_leader = True
            elif n.key == "add_to_faction":
                target = self.countries[self.resolve(v)]
                if target.faction and target.faction != c.faction:
                    raise AssertionError("Forced existing faction transfer")
                target.faction = c.faction
            elif n.key in ("custom_effect_tooltip", "show_ideas_tooltip", "effect_tooltip"):
                # Tooltip rendering does not mutate the simulated game state.
                pass
            elif n.key in ("log", "set_truce", "remove_opinion_modifier", "set_rule", "cancel_border_war"):
                self.trace.append((tag, n.key, copy.deepcopy(v)))
            else:
                raise AssertionError(f"Fixture evaluator has no effect: {n.key}")

    def sign(self):
        self.apply("HSM_VER_sign_treaty")

    def armistice(self):
        self.apply("HSM_VER_offer_armistice")
        self.apply("HSM_VER_sign_armistice")

    def advance_days(self, days):
        # Only expire timed flags. Event delivery and daily hooks are explicit in fixtures.
        for c in self.countries.values():
            for flag in list(c.flag_days):
                c.flag_days[flag] -= days
                if c.flag_days[flag] <= 0:
                    c.flags.discard(flag)
                    del c.flag_days[flag]

    def choose(self, event_id, option_index=0, tag="ERI"):
        # Clicking an already-open event must revalidate effects even if its trigger changed.
        self.root = tag
        option = self.events[event_id].all("option")[option_index]
        self.run([n for n in option.children if n.key not in ("name", "trigger", "ai_chance")], tag)

    def charter(self):
        self.sign()
        self.countries["ERI"].flags.add("HSM_VER_charter_pending")
        self.apply("HSM_VER_ratify_charter")


class Integration(unittest.TestCase):
    def test_package_rejects_keywords_and_operators_reported_invalid_by_engine(self):
        triggers = (OPT.game / "documentation/triggers_documentation.md").read_text(encoding="utf-8-sig")
        effects = (OPT.game / "documentation/effects_documentation.md").read_text(encoding="utf-8-sig")
        self.assertIn("## has_political_power\n", triggers)
        self.assertNotIn("## political_power\n", triggers)
        self.assertIn("## diplomatic_relation\n", effects)
        forbidden = {"political_power", "non_aggression_pact", "create_non_aggression_pact", "remove_non_aggression_pact"}
        for name in forbidden - {"political_power"}:
            self.assertNotIn("## " + name + "\n", effects)
        for path in package_files() + [MOD / "events/Avian Events.txt"]:
            for node in walk(read(path)):
                self.assertNotIn(node.key, forbidden, f"Unsupported engine keyword: {path}: {node.key}")
                self.assertNotIn(node.op, (">=", "<=", "!="), f"Unsupported shorthand operator: {path}: {node.key}")

    def test_parse_all_package_and_overrides(self):
        files = package_files() + [MOD / p for p in ("events/Avian Events.txt", "common/national_focus/AVI.txt", "common/decisions/ERI_decisions.txt")]
        for path in files:
            with self.subTest(file=path.name):
                self.assertTrue(read(path))

    def test_new_event_ids_and_calls_resolve(self):
        ids = []
        refs = []
        for path in package_files():
            for n in walk(read(path)):
                if n.key in ("country_event", "news_event") and n.children:
                    value = n.get("id")
                    if n.get("is_triggered_only"):
                        ids.append(value)
                    elif value.startswith(("hsm_verenia.", "hsm_ver_")):
                        refs.append(value)
        self.assertEqual(len(ids), len(set(ids)), "Duplicate event ID")
        self.assertFalse(set(refs) - set(ids), f"Missing events: {set(refs) - set(ids)}")

    def test_scripted_calls_resolve(self):
        defined = set(definitions("scripted_effects")) | set(definitions("scripted_triggers"))
        for path in package_files():
            for n in walk(read(path)):
                if n.key.startswith(("HSM_VER_", "HSM_ZYP_")) and n.value in ("yes", "no"):
                    self.assertIn(n.key, defined, f"{path}: {n.key}")

    def test_english_russian_coverage_and_bom(self):
        localizations = {}
        for language in ("english", "russian"):
            found = {}
            paths = [p for p in (MOD / "localisation" / language).glob("*.yml") if p.name.startswith(("HSM_VER", "HSM_ERI", "HSM_EYR"))]
            self.assertTrue(paths)
            for p in paths:
                self.assertTrue(p.read_bytes().startswith(b"\xef\xbb\xbf"), f"Missing BOM {p}")
                for line in p.read_text(encoding="utf-8-sig").splitlines():
                    match = re.match(r'\s*([^#\s:]+):\d*\s+"(.*)"\s*$', line)
                    if match:
                        key, value = match.groups()
                        self.assertNotIn(key, found, f"Duplicate key {key} in {language}")
                        self.assertTrue(value.strip(), key)
                        found[key] = value
                    elif line.strip() and not line.lstrip().startswith(("#", "l_")):
                        self.fail(f"Malformed localization in {p}: {line}")
            localizations[language] = found
        self.assertEqual(set(localizations["english"]), set(localizations["russian"]))
        required = set()
        for path in package_files():
            for n in walk(read(path)):
                if n.key in ("focus", "shared_focus", "joint_focus") and n.children:
                    value = n.get("id")
                    required.update((value, value + "_desc"))
                if n.key in ("title", "desc", "text", "name", "custom_effect_tooltip", "tooltip") and isinstance(n.value, str) and n.value.startswith(("HSM_VER", "HSM_ERI", "HSM_EYR", "HSM_AVI", "HSM_ZYP", "hsm_verenia.", "hsm_ver_")):
                    required.add(n.value)
                if n.key.startswith(("HSM_VER", "HSM_ERI", "HSM_EYR", "HSM_AVI", "HSM_ZYP")) and n.children and (n.get("modifier") or "/decisions/" in path.as_posix()):
                    required.update((n.key, n.key + "_desc"))
        self.assertFalse(required - set(localizations["english"]), f"Missing localization {sorted(required - set(localizations['english']))}")

    def test_assets_exist_in_game_eaw_or_submod(self):
        sprites = set()
        for root in (OPT.game / "interface", OPT.eaw / "interface", MOD / "interface"):
            for p in root.rglob("*.gfx"):
                sprites.update(re.findall(r'\bname\s*=\s*"?(GFX_[^\s"}]+)', p.read_text(encoding="utf-8-sig", errors="replace")))
        self.assertTrue(sprites, "Missing installed sprite reference")
        missing = []
        for path in package_files():
            for n in walk(read(path)):
                if n.key in ("picture", "icon") and isinstance(n.value, str):
                    sprite = n.value
                    if sprite.startswith("GFX_"):
                        if sprite not in sprites:
                            missing.append((path.name, sprite))
                    elif "/ideas/" in path.as_posix() and "GFX_idea_" + sprite not in sprites:
                        missing.append((path.name, "GFX_idea_" + sprite))
        self.assertFalse(missing, missing)

    def test_custom_verenia_sprites_have_textures_and_shine(self):
        nodes = [n for n in walk(read(MOD / "interface/HSM_VER_art.gfx")) if n.key == "spriteType"]
        names = [n.get("name") for n in nodes]
        self.assertEqual(len(names), len(set(names)))
        for n in nodes:
            for field in walk(n.children):
                if field.key.lower() in ("texturefile", "animationmaskfile", "animationtexturefile", "effectfile"):
                    candidates = [Path(field.value)]
                    # Native EaW GFX uses the legacy .lua alias for compiled shaders.
                    if field.key.lower() == "effectfile" and candidates[0].suffix == ".lua":
                        candidates.append(candidates[0].with_suffix(".shader"))
                    self.assertTrue(any((root / candidate).is_file() for root in (MOD, OPT.eaw, OPT.game) for candidate in candidates), field.value)
            name = n.get("name")
            if name.startswith("GFX_HSM_VER_") and not name.endswith("_shine"):
                self.assertIn(name + "_shine", names)

    def test_research_categories_exist_in_installed_mod(self):
        categories = set()
        for root in (OPT.game, OPT.eaw):
            for path in (root / "common/technology_tags").glob("*.txt"):
                categories.update(n.key for n in walk(read(path)) if not n.op)
        self.assertTrue(categories)
        for path in package_files():
            for bonus in walk(read(path)):
                if bonus.key == "add_tech_bonus":
                    for category in bonus.all("category"):
                        self.assertIn(category.value, categories, f"Unknown research category {path}: {category.value}")

    def test_package_has_no_merge_markers_or_trailing_whitespace(self):
        for path in package_files():
            for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                self.assertEqual(line, line.rstrip(), f"Trailing whitespace: {path}:{number}")
                self.assertFalse(line.startswith(("<<<<<<<", "=======", ">>>>>>>")), f"Conflict marker: {path}:{number}")

    def test_focus_graph_and_coordinates(self):
        focus = {}
        trees = []
        for path in (MOD / "common/national_focus").glob("HSM_*.txt"):
            if not path.name.startswith(("HSM_VER", "HSM_ERI", "HSM_EYR")):
                continue
            for n in walk(read(path)):
                if n.key == "focus_tree":
                    trees.append(n)
                if n.key in ("focus", "shared_focus", "joint_focus") and n.children:
                    key = n.get("id")
                    self.assertNotIn(key, focus)
                    focus[key] = n
        native_nodes = read(MOD / "common/national_focus/AVI.txt")
        native_focus = {n.get("id"): n for n in native_nodes if n.key in ("shared_focus", "joint_focus") and n.children}
        for native_tree in (n for n in native_nodes if n.key == "focus_tree"):
            additions = [n for n in native_tree.all("shared_focus") if isinstance(n.value, str) and n.value.startswith(("HSM_AVI_", "HSM_VER_", "HSM_ZYP_"))]
            if additions:
                trees.append(Node("focus_tree", "=", [Node("id", "=", native_tree.get("id"))] + additions))
        tree_members = {}
        for tree in trees:
            roots = {n.value for n in tree.all("shared_focus") if isinstance(n.value, str)}
            included = {n.get("id") for n in tree.all("focus")}
            self.assertFalse(roots - focus.keys(), f"Missing shared roots {roots - focus.keys()}")
            included |= roots
            changed = True
            while changed:
                changed = False
                for key, n in focus.items():
                    parents = {x.value for p in n.all("prerequisite") for x in p.children}
                    if n.key in ("shared_focus", "joint_focus") and parents & included and key not in included:
                        included.add(key)
                        changed = True
            tree_members[tree.get("id")] = included
        attached = set().union(*tree_members.values())
        # Replaced by the Grover branch; retain these IDs for older save data.
        legacy_imperial = {
            "HSM_VER_IMP_settlement", "HSM_VER_IMP_household_record",
            "HSM_VER_IMP_open_archives", "HSM_VER_IMP_city_contracts",
            "HSM_VER_IMP_technical_agreement", "HSM_VER_IMP_public_accounts",
            "HSM_VER_IMP_last_year", "HSM_VER_IMP_return_the_keys",
        }
        self.assertEqual(set(focus) - attached, legacy_imperial,
                         f"Unexpected unattached foci {set(focus) - attached - legacy_imperial}")
        self.assertFalse(attached & legacy_imperial)
        coords = {}
        active = set()

        def position(key):
            if key in coords:
                return coords[key]
            self.assertNotIn(key, active, f"Relative-position cycle {key}")
            active.add(key)
            n = focus[key]
            x, y = int(n.get("x", "0")), int(n.get("y", "0"))
            if n.get("relative_position_id"):
                px, py = position(n.get("relative_position_id"))
                x, y = x + px, y + py
            active.remove(key)
            coords[key] = (x, y)
            return x, y

        for key, n in focus.items():
            for p in n.all("prerequisite"):
                for parent in p.children:
                    self.assertIn(parent.value, focus, f"Missing prerequisite {parent.value}")
            position(key)
        for tree_id, members in tree_members.items():
            positions = {key: coords[key] for key in members}
            self.assertEqual(len(positions), len(set(positions.values())), f"Overlapping foci in {tree_id}: {positions}")
            for key in members:
                parents = {x.value for p in focus[key].all("prerequisite") for x in p.children}
                self.assertFalse(parents - members, f"Unreachable prerequisite in {tree_id}: {key}")
        for key, n in focus.items():
            for p in n.all("prerequisite"):
                for parent in p.children:
                    self.assertLess(coords[parent.value][1], coords[key][1], f"Backwards prerequisite {parent.value} -> {key}")
            for p in n.all("mutually_exclusive"):
                for other in p.children:
                    target = focus.get(other.value, native_focus.get(other.value))
                    self.assertIsNotNone(target, other.value)
                    reciprocal = {x.value for m in target.all("mutually_exclusive") for x in m.children}
                    self.assertIn(key, reciprocal)
        native_coords = {}

        def native_position(key):
            if key not in native_coords:
                n = native_focus[key]
                base = native_position(n.get("relative_position_id")) if n.get("relative_position_id") else (0, 0)
                native_coords[key] = (base[0] + int(n.get("x", "0")), base[1] + int(n.get("y", "0")))
            return native_coords[key]

        for key in native_focus:
            native_position(key)
        for key, xy in coords.items():
            if key.startswith(("HSM_AVI_", "HSM_VER_REG_", "HSM_ZYP_")):
                self.assertNotIn(xy, native_coords.values(), f"Avian addition overlaps native tree: {key}")

    def test_overrides_preserve_native_inventory_and_layout(self):
        def inventory(path):
            return [(n.key, n.get("id")) for n in walk(read(path))
                    if n.children and n.get("id") and (
                        n.key in ("focus_tree", "focus", "shared_focus", "joint_focus")
                        or (n.key in ("country_event", "news_event")
                            and any(n.all(field) for field in ("title", "is_triggered_only", "trigger"))))]

        for rel in ("common/national_focus/AVI.txt", "events/Avian Events.txt"):
            self.assertEqual(inventory(OPT.eaw / rel), inventory(MOD / rel), rel)
        native = {n.get("id"): n for n in walk(read(OPT.eaw / "common/national_focus/AVI.txt")) if n.key == "shared_focus" and n.children}
        for n in walk(read(MOD / "common/national_focus/AVI.txt")):
            if n.key == "shared_focus" and n.children:
                for field_name in ("icon", "x", "y", "cost", "relative_position_id", "prerequisite", "mutually_exclusive"):
                    expected = native[n.get("id")].all(field_name)
                    if field_name == "icon" and n.all(field_name) != expected:
                        approved = approved_native_focus_icon(
                            n.get("id"), "mod/HoISubmod/common/national_focus/AVI.txt")
                        if approved is not None:
                            expected = [Node("icon", "=", approved)]
                    if n.get("id") == "the_second_winterfest_ball" and field_name == "mutually_exclusive":
                        expected = expected + [Node("mutually_exclusive", "=", [Node("focus", "=", "HSM_AVI_three_separate_seals")])]
                    if n.get("id") == "the_second_winterfest_ball" and field_name == "prerequisite":
                        expected = [
                            Node("prerequisite", "=", [Node("focus", "=", "tripartite_legion"), Node("focus", "=", "technological_cooperation")]),
                            Node("prerequisite", "=", [Node("focus", "=", "leaders_field_marshalls"), Node("focus", "=", "unified_railroad_network")]),
                        ]
                    self.assertEqual(n.all(field_name), expected, f"AVI {n.get('id')}: {field_name}")
        rel = "common/decisions/ERI_decisions.txt"
        for original, override in zip(read(OPT.eaw / rel), read(MOD / rel), strict=True):
            self.assertEqual(original.key, override.key)
            self.assertEqual([n.key for n in original.children], [n.key for n in override.children])

    def test_focus_art_requires_explicit_approval_and_both_hashes(self):
        record = {"approved": True, "kind": "focus", "target": "example",
                  "source": "art/verenia/example.png",
                  "exports": [{"path": "mod/HoISubmod/gfx/example.tga", "width": 99, "height": 86}]}
        assets = {record["source"]: b"source", record["exports"][0]["path"]: b"export"}
        hashes = {name: hashlib.sha256(data).hexdigest() for name, data in assets.items()}
        approved = verified_focus_art(record, hashes, assets.__getitem__)
        self.assertEqual(approved, "GFX_HSM_VER_ART_example")
        self.assertNotEqual(approved, "GFX_HSM_VER_ART_arbitrary")
        for approval in (False, None, "true", 1):
            with self.subTest(approval=approval):
                pending = dict(record, approved=approval, review="Approved", runtime_verified=True)
                self.assertIsNone(verified_focus_art(pending, hashes, assets.__getitem__))
        for name in assets:
            with self.subTest(asset=name):
                missing = dict(hashes)
                del missing[name]
                with self.assertRaises(ValueError):
                    verified_focus_art(record, missing, assets.__getitem__)
                changed = dict(assets, **{name: b"changed"})
                with self.assertRaises(ValueError):
                    verified_focus_art(record, hashes, changed.__getitem__)
        unsafe = dict(record, source="art/verenia/../../outside.png")
        with self.assertRaises(ValueError):
            verified_focus_art(unsafe, hashes, assets.__getitem__)

    def test_native_preservation_rejects_arbitrary_icon_and_gameplay_changes(self):
        from unittest.mock import patch

        original_read = read
        path = MOD / "common/national_focus/AVI.txt"
        for field_name, value in (("icon", "GFX_HSM_VER_ART_unapproved"), ("cost", "999")):
            with self.subTest(field=field_name):
                def altered_read(requested):
                    nodes = original_read(requested)
                    if requested == path:
                        focus = next(n for n in walk(nodes) if n.key == "shared_focus"
                                     and n.get("id") == "convene_the_council")
                        focus.all(field_name)[0].value = value
                    return nodes

                with patch.dict(self.test_overrides_preserve_native_inventory_and_layout.__globals__,
                                read=altered_read):
                    with self.assertRaises(AssertionError):
                        self.test_overrides_preserve_native_inventory_and_layout()

    def test_idea_modifiers_exist_in_installed_documentation(self):
        documentation = (OPT.game / "documentation/modifiers_documentation.md").read_text(encoding="utf-8-sig")
        supported = set()
        for section in re.split(r"(?m)^## ", documentation)[1:]:
            heading = re.sub(r"<span[^>]*></span>", "", section.splitlines()[0]).strip()
            if "<Building>" in heading:
                types = re.search(r"\* \*\*Modified types\*\*: (.+)", section)
                if types:
                    supported.update(heading.replace("<Building>", name.strip()) for name in types.group(1).split(","))
            else:
                supported.add(heading)
        for path in (MOD / "common/ideas").glob("HSM_*.txt"):
            if not path.name.startswith(("HSM_VER", "HSM_ERI", "HSM_EYR")):
                continue
            for n in walk(read(path)):
                if n.key == "modifier":
                    for modifier in n.children:
                        self.assertTrue(modifier.key in supported, f"Unknown modifier in {path.name}: {modifier.key}")


class NativeCompatibility(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.events = {n.get("id"): n for n in read(MOD / "events/Avian Events.txt") if n.key == "country_event"}

    def test_native_invitation_does_not_take_existing_faction_member(self):
        accept = self.events["avian.1"].all("option")[0]
        self.w.countries["AVI"].faction = "Avian league"
        self.w.countries["AVI"].faction_leader = True
        self.assertTrue(self.w.check(accept.get("trigger"), "ERI"))
        self.w.countries["ERI"].faction = "Erie league"
        self.assertFalse(self.w.check(accept.get("trigger"), "ERI"))
        self.w.root = "ERI"
        self.w.run([n for n in effect_nodes(accept.children) if n.key == "if"], "ERI")
        self.assertEqual(self.w.countries["ERI"].faction, "Erie league")

    def test_signed_vassalisation_needs_live_consent_and_free_parties(self):
        option = self.events["avian.6"].all("option")[0]
        condition = next(n for n in effect_nodes(option.children) if n.key == "if").get("limit")
        self.w.root = "AVI"
        self.w.sender = "ERI"
        c = self.w.countries["ERI"]
        c.flags.add("HSM_VER_treaty_signed")
        self.assertFalse(self.w.check(condition, "AVI"))
        c.flags.add("HSM_VER_avian_vassalisation_accepted")
        self.assertTrue(self.w.check(condition, "AVI"))
        for tag in ("ERI", "AVI"):
            for attribute, value in (("exists", False), ("subject", True), ("capitulated", True)):
                previous = getattr(self.w.countries[tag], attribute)
                setattr(self.w.countries[tag], attribute, value)
                self.assertFalse(self.w.check(condition, "AVI"), (tag, attribute))
                setattr(self.w.countries[tag], attribute, previous)

    def test_equal_union_option_never_subjugates_or_penalises(self):
        option = next(n for n in self.events["avian.5"].all("option") if n.get("name") == "HSM_VER_keep_equal_union")
        self.w.charter()
        self.assertTrue(self.w.check(option.get("trigger"), "ERI"))
        effects = [n for n in effect_nodes(option.children) if n.key not in ("name", "trigger", "ai_chance")]
        self.assertEqual([n.key for n in effects], ["clr_country_flag"])

    def test_native_border_skirmishes_stop_at_actual_armistice(self):
        decisions = {n.key: n for c in read(MOD / "common/decisions/ERI_decisions.txt") for n in c.children}
        for tag in ("ERI", "EYR"):
            self.assertTrue(self.w.check(decisions[tag + "_border_skirmish"].get("available"), tag))
        self.w.armistice()
        for tag in ("ERI", "EYR"):
            decision = decisions[tag + "_border_skirmish"]
            self.assertFalse(self.w.check(decision.get("available"), tag))
            completion = next(n for n in effect_nodes(decision.get("complete_effect")) if n.key == "if")
            self.assertFalse(self.w.check(completion.get("limit"), tag))


class TreatyFixtures(unittest.TestCase):
    def setUp(self):
        self.w = World()

    def test_offer_does_not_sign(self):
        self.w.apply("HSM_VER_offer_armistice")
        self.assertIn("HSM_VER_armistice_pending", self.w.countries["ERI"].flags)
        self.assertFalse(self.w.test("HSM_VER_armistice_valid"))
        self.assertEqual(self.w.countries["EYR"].events, ["hsm_verenia.20"])

    def test_concurrent_offer_not_queued_twice(self):
        self.w.apply("HSM_VER_offer_armistice")
        self.w.apply("HSM_VER_offer_armistice", "AVI")
        self.assertEqual(self.w.countries["EYR"].events, ["hsm_verenia.20"])

    def test_armistice_removes_inherited_wargoals(self):
        self.w.countries["ERI"].goals = {("annex_everything", "EYR"), ("puppet_wargoal_focus", "EYR"), ("annex_everything", "GRI")}
        self.w.apply("HSM_VER_offer_armistice")
        self.w.apply("HSM_VER_sign_armistice")
        self.assertTrue(self.w.test("HSM_VER_armistice_valid"))
        self.assertEqual(self.w.countries["ERI"].goals, {("annex_everything", "GRI")})

    def test_treaty_requires_real_both_signatures(self):
        self.w.countries["ERI"].flags.add("HSM_VER_treaty_signed")
        self.assertFalse(self.w.test("HSM_VER_negotiated_peace_valid"))
        self.w.sign()
        self.assertTrue(self.w.test("HSM_VER_negotiated_peace_valid"))

    def test_treaty_does_not_annex_or_form_faction(self):
        self.w.sign()
        for tag in ("ERI", "EYR"):
            c = self.w.countries[tag]
            self.assertTrue(c.exists)
            self.assertFalse(c.subject)
            self.assertFalse(c.faction)

    def test_charter_is_bilateral_without_avian(self):
        self.w.countries["AVI"].exists = False
        self.w.charter()
        self.assertTrue(self.w.test("HSM_VER_charter_valid"))
        self.assertNotIn("HSM_VER_charter_signed", self.w.countries["AVI"].flags)

    def test_observer_is_not_automatically_signatory(self):
        self.w.countries["AVI"].focuses.add("intergigantes")
        self.w.countries["AVI"].flags.add("HSM_VER_congress_observer")
        self.w.charter()
        self.assertEqual(self.w.countries["AVI"].events, ["hsm_verenia.63"])
        self.assertFalse(self.w.test("HSM_VER_avian_partner"))

    def test_stale_ratification_has_no_effect(self):
        self.w.sign()
        self.w.apply("HSM_VER_ratify_charter")
        self.assertFalse(self.w.test("HSM_VER_charter_valid"))

    def test_dead_or_puppeted_counterpart_blocks_new_negotiation(self):
        for attr in ("subject", "capitulated", "war"):
            with self.subTest(attr=attr):
                w = World()
                setattr(w.countries["EYR"], attr, True)
                w.apply("HSM_VER_offer_armistice")
                self.assertFalse(w.countries["EYR"].events)
        self.w.countries["EYR"].exists = False
        self.assertFalse(self.w.test("HSM_VER_can_offer_armistice"))

    def test_benefits_suspend_during_occupation_and_resume(self):
        self.w.charter()
        self.w.apply("HSM_VER_apply_joint_staff")
        self.w.countries["EYR"].capitulated = True
        self.w.apply("HSM_VER_maintain_agreements")
        self.assertNotIn("HSM_VER_joint_staff", self.w.countries["ERI"].ideas)
        self.assertIn("HSM_VER_charter_signed", self.w.countries["ERI"].flags)
        self.w.countries["EYR"].capitulated = False
        self.w.apply("HSM_VER_maintain_agreements")
        self.assertIn("HSM_VER_joint_staff", self.w.countries["ERI"].ideas)

    def test_judicial_exception_suspends_both_houses(self):
        self.w.charter()
        self.w.countries["ERI"].flags.add("HSM_VER_royal_exception")
        self.w.apply("HSM_VER_apply_joint_staff")
        self.w.apply("HSM_VER_apply_shared_services")
        self.w.apply("HSM_VER_suspend_charter")
        self.assertFalse(self.w.test("HSM_VER_charter_valid"))
        self.assertTrue(self.w.test("HSM_VER_negotiated_peace_valid"))
        for tag in ("ERI", "EYR"):
            self.w.apply("HSM_VER_maintain_agreements", tag)
            self.assertNotIn("HSM_VER_joint_staff", self.w.countries[tag].ideas)
        self.w.apply("HSM_VER_restore_charter")
        self.assertTrue(self.w.test("HSM_VER_charter_valid"))
        self.assertNotIn("HSM_VER_royal_exception", self.w.countries["ERI"].flags)

    def test_court_variants_do_not_stack(self):
        self.w.charter()
        c = self.w.countries["ERI"]
        c.flags.add("HSM_VER_civic_delegates")
        self.w.apply("HSM_VER_maintain_agreements")
        self.assertIn("HSM_VER_public_council", c.ideas)
        self.assertNotIn("HSM_VER_common_courts", c.ideas)
        c.flags.add("HSM_VER_ducal_presidency")
        self.w.apply("HSM_VER_maintain_agreements")
        self.assertIn("HSM_VER_limited_presidency", c.ideas)
        self.assertNotIn("HSM_VER_public_council", c.ideas)

    def test_defensive_league_cannot_steal_faction_member(self):
        self.w.charter()
        self.w.apply("HSM_VER_offer_defence")
        self.w.countries["EYR"].faction = "Other bloc"
        self.w.apply("HSM_VER_form_defensive_league")
        self.assertFalse(self.w.countries["ERI"].faction)
        self.assertEqual(self.w.countries["EYR"].faction, "Other bloc")

    def test_defensive_league_is_consenting_two_not_auto_three(self):
        self.w.charter()
        self.w.countries["AVI"].flags.add("HSM_VER_charter_signed")
        self.w.apply("HSM_VER_offer_defence")
        self.w.apply("HSM_VER_form_defensive_league")
        self.assertEqual(self.w.countries["ERI"].faction, self.w.countries["EYR"].faction)
        self.assertFalse(self.w.countries["AVI"].faction)
        self.assertEqual(self.w.countries["AVI"].events, ["hsm_verenia.82"])

    def test_actual_war_invalidates_not_merely_suspends(self):
        self.w.charter()
        self.w.countries["ERI"].wars.add("EYR")
        self.w.apply("HSM_VER_maintain_agreements")
        self.assertNotIn("HSM_VER_treaty_signed", self.w.countries["ERI"].flags)
        self.assertIn("HSM_VER_treaty_broken", self.w.countries["ERI"].flags)

    def test_existing_native_peace_is_adopted_once(self):
        self.w.countries["AVI"].focuses.add("treaty_of_friendship")
        self.w.apply("HSM_VER_start_campaign")
        self.assertTrue(self.w.test("HSM_VER_negotiated_peace_valid"))
        self.w.apply("HSM_VER_start_campaign")
        self.assertEqual(self.w.countries["ERI"].events, ["hsm_verenia.1"])

    def test_crisis_notifies_without_annexing_independent_house(self):
        self.w.charter()
        self.w.countries["AVI"].flags.add("HSM_VER_charter_signed")
        self.w.apply("HSM_VER_avian_crisis_response", "EYR")
        self.assertTrue(self.w.countries["EYR"].exists)
        self.assertFalse(self.w.countries["EYR"].subject)
        self.assertFalse(self.w.test("HSM_VER_avian_partner"))
        self.assertIn("hsm_verenia.95", self.w.countries["EYR"].events)


class NegotiationLifecycle(unittest.TestCase):
    def setUp(self):
        self.w = World()

    def test_old_armistice_response_cannot_survive_war(self):
        self.w.apply("HSM_VER_offer_armistice")
        self.w.apply("HSM_VER_void_bilateral_treaty")
        self.w.choose("hsm_verenia.20", tag="EYR")
        self.assertFalse(self.w.test("HSM_VER_armistice_valid"))
        self.w.choose("hsm_verenia.21")
        self.assertEqual(self.w.countries["ERI"].political_power, 0)

    def test_every_pending_negotiation_is_cleared_by_war(self):
        flags = {f"HSM_VER_{s}_pending" for s in ("armistice", "treaty", "charter", "avian", "defence", "judgement")}
        self.w.countries["ERI"].flags |= flags
        self.w.countries["AVI"].flags |= {"HSM_VER_congress_observer", "HSM_VER_avian_charter_pending"}
        self.w.apply("HSM_VER_void_bilateral_treaty")
        self.assertFalse(flags & self.w.countries["ERI"].flags)
        self.assertFalse(self.w.countries["AVI"].flags)

    def test_daily_fallback_cancels_armistice_without_treaty(self):
        self.w.armistice()
        self.w.countries["ERI"].wars.add("EYR")
        self.w.apply("HSM_VER_maintain_agreements")
        for tag in ("ERI", "EYR"):
            self.assertNotIn("HSM_VER_armistice", self.w.countries[tag].flags)
        self.w.countries["ERI"].wars.clear()
        self.assertFalse(self.w.test("HSM_VER_armistice_valid"))

    def test_all_new_war_relations_have_invalidation_hook(self):
        action = read(MOD / "common/on_actions/HSM_VER_diplomacy.txt")[0]
        body = action.all("on_war_relation_added")[0].get("effect")
        for root, sender in (("ERI", "EYR"), ("EYR", "ERI")):
            w = World()
            w.armistice()
            w.root, w.sender = root, sender
            w.run(body, root)
            self.assertNotIn("HSM_VER_armistice", w.countries["ERI"].flags)

    def test_native_mediation_cannot_bypass_retry_window(self):
        self.w.apply("HSM_VER_offer_armistice")
        self.w.choose("hsm_verenia.20", 2, "EYR")
        self.w.apply("HSM_VER_offer_armistice", "AVI")
        self.assertEqual(self.w.countries["EYR"].events.count("hsm_verenia.20"), 1)
        self.assertNotIn("HSM_VER_armistice_pending", self.w.countries["ERI"].flags)
        self.w.advance_days(90)
        self.w.apply("HSM_VER_offer_armistice", "AVI")
        self.assertEqual(self.w.countries["EYR"].events.count("hsm_verenia.20"), 2)

    def test_treaty_and_charter_dispatch_enforce_retry(self):
        self.w.armistice()
        self.w.apply("HSM_VER_offer_treaty")
        self.w.choose("hsm_verenia.30", 2, "EYR")
        self.w.apply("HSM_VER_offer_treaty", "AVI")
        self.assertEqual(self.w.countries["EYR"].events.count("hsm_verenia.30"), 1)
        self.w.sign()
        self.w.apply("HSM_VER_offer_charter")
        self.w.choose("hsm_verenia.62", 1)
        self.w.apply("HSM_VER_offer_charter")
        self.assertEqual(self.w.countries["ERI"].events.count("hsm_verenia.60"), 1)

    def test_mediation_pending_does_not_interrupt_focus(self):
        tree = read(MOD / "common/national_focus/HSM_ERI.txt")[0]
        focus = {n.get("id"): n for n in tree.all("focus")}
        self.w.apply("HSM_VER_offer_armistice", "AVI")
        self.assertTrue(self.w.check(focus["HSM_ERI_offer_armistice"].get("available")))
        self.w.apply("HSM_VER_sign_armistice")
        self.w.apply("HSM_VER_offer_treaty", "AVI")
        self.assertTrue(self.w.check(focus["HSM_ERI_friendship_treaty"].get("available")))

    def test_skipped_judgement_retries_after_liberation_then_resolves_once(self):
        self.w.charter()
        c = self.w.countries["ERI"]
        c.focuses.add("HSM_ERI_first_judgement")
        self.w.apply("HSM_VER_queue_judgement")
        self.w.countries["EYR"].capitulated = True
        self.assertFalse(self.w.check(self.w.events["hsm_verenia.70"].get("trigger")))
        self.w.advance_days(31)
        self.w.apply("HSM_VER_maintain_agreements")
        self.assertEqual(c.events.count("hsm_verenia.70"), 1)
        self.w.countries["EYR"].capitulated = False
        self.w.apply("HSM_VER_maintain_agreements")
        self.w.apply("HSM_VER_maintain_agreements")
        self.assertEqual(c.events.count("hsm_verenia.70"), 2)
        self.w.choose("hsm_verenia.70")
        self.w.choose("hsm_verenia.70")
        self.w.advance_days(31)
        self.w.apply("HSM_VER_maintain_agreements")
        self.assertEqual(c.political_power, -75)
        self.assertIn("HSM_VER_court_respected", c.flags)
        self.assertEqual(c.events.count("hsm_verenia.70"), 2)

    def test_defence_offer_cannot_be_duplicated_or_reversed_by_stale_refusal(self):
        self.w.charter()
        self.w.apply("HSM_VER_offer_defence")
        self.w.apply("HSM_VER_offer_defence")
        self.assertEqual(self.w.countries["EYR"].events.count("hsm_verenia.80"), 1)
        self.w.choose("hsm_verenia.80", tag="EYR")
        self.w.choose("hsm_verenia.80", 1, "EYR")
        self.w.apply("HSM_VER_offer_defence")
        self.assertIn("HSM_VER_defence_accepted", self.w.countries["ERI"].flags)
        self.assertNotIn("HSM_VER_defence_declined", self.w.countries["ERI"].flags)

    def test_avian_late_acceptance_rechecks_independence(self):
        self.w.countries["AVI"].focuses.add("intergigantes")
        self.w.sign()
        self.w.apply("HSM_VER_invite_avian")
        self.w.countries["AVI"].subject = True
        self.w.choose("hsm_verenia.50", tag="AVI")
        self.assertNotIn("HSM_VER_congress_observer", self.w.countries["AVI"].flags)

    def test_observer_is_not_reinvited_but_gets_delayed_ratification(self):
        self.w.countries["AVI"].focuses.add("intergigantes")
        self.w.sign()
        self.w.apply("HSM_VER_invite_avian")
        self.w.choose("hsm_verenia.50", tag="AVI")
        self.w.advance_days(121)
        self.w.apply("HSM_VER_invite_avian")
        self.assertEqual(self.w.countries["AVI"].events.count("hsm_verenia.50"), 1)
        self.w.charter()
        self.w.choose("hsm_verenia.63", 1, "AVI")
        self.assertNotIn("HSM_VER_congress_observer", self.w.countries["AVI"].flags)
        self.w.apply("HSM_VER_maintain_agreements", "AVI")
        self.assertEqual(self.w.countries["AVI"].events.count("hsm_verenia.63"), 1)
        self.w.choose("hsm_verenia.63", tag="AVI")
        self.assertNotIn("HSM_VER_charter_signed", self.w.countries["AVI"].flags)

    def test_pending_delivery_guards_outlast_explicit_event_timeout(self):
        for event_id in ("hsm_verenia.63", "hsm_verenia.70", "hsm_verenia.80"):
            self.assertLess(int(self.w.events[event_id].get("timeout_days")) + 1, 30)

    def test_timeout_closes_offer_on_delivery_not_later_acknowledgement(self):
        self.w.apply("HSM_VER_offer_armistice")
        timeout = self.w.events["hsm_verenia.29"]
        self.w.advance_days(30)
        self.assertTrue(self.w.check(timeout.get("trigger")))
        self.w.run(timeout.get("immediate"))
        self.w.choose("hsm_verenia.20", tag="EYR")
        self.assertFalse(self.w.test("HSM_VER_armistice_valid"))
        self.w.advance_days(60)
        self.w.apply("HSM_VER_offer_armistice")
        self.w.choose("hsm_verenia.29")
        self.assertIn("HSM_VER_armistice_pending", self.w.countries["ERI"].flags)

    def test_stale_refusal_does_not_relabel_ratified_charter(self):
        self.w.charter()
        self.w.choose("hsm_verenia.61", 2, "EYR")
        self.w.choose("hsm_verenia.62", 1)
        self.assertNotIn("HSM_VER_charter_refused", self.w.countries["ERI"].flags)


class AvianDispatchGovernment(unittest.TestCase):
    BLOCKERS = (
        ("focuses", "pursue_true_neutrality"),
        ("focuses", "foundation_allowed"),
        ("focuses", "fascists_win"),
        ("focuses", "communists_win"),
        ("focuses", "loyalists_win"),
        ("flags", "HSM_VER_CR_emergency"),
    )

    def test_ineligible_dispatch_consumes_no_pending_cooldown_or_event(self):
        for attribute, blocker in self.BLOCKERS:
            for effect, owner, pending in (
                ("HSM_VER_invite_avian", "ERI", "HSM_VER_avian_pending"),
                ("HSM_VER_offer_avian_charter", "AVI", "HSM_VER_avian_charter_pending"),
            ):
                with self.subTest(blocker=blocker, effect=effect):
                    w = World()
                    w.countries["AVI"].focuses.add("intergigantes")
                    if owner == "ERI":
                        w.sign()
                    else:
                        w.charter()
                        w.countries["AVI"].flags.add("HSM_VER_congress_observer")
                    blocked = getattr(w.countries["AVI"], attribute)
                    blocked.add(blocker)
                    self.assertFalse(w.test("HSM_VER_CR_union_government"))
                    before = {tag: (set(c.flags), dict(c.flag_days), list(c.events)) for tag, c in w.countries.items()}
                    for sender in ("ERI", "EYR", "AVI"):
                        w.apply(effect, sender)
                    after = {tag: (set(c.flags), dict(c.flag_days), list(c.events)) for tag, c in w.countries.items()}
                    self.assertEqual(before, after)
                    blocked.remove(blocker)
                    w.apply(effect)
                    self.assertIn(pending, w.countries[owner].flags)

    def test_avian_government_does_not_gate_bilateral_peace_or_charter(self):
        for attribute, blocker in self.BLOCKERS:
            with self.subTest(blocker=blocker):
                w = World()
                getattr(w.countries["AVI"], attribute).add(blocker)
                w.armistice()
                self.assertTrue(w.test("HSM_VER_armistice_valid"))
                w.apply("HSM_VER_offer_treaty")
                w.choose("hsm_verenia.30", tag="EYR")
                self.assertTrue(w.test("HSM_VER_negotiated_peace_valid"))
                w.apply("HSM_VER_offer_charter")
                w.apply("HSM_VER_ratify_charter")
                self.assertTrue(w.test("HSM_VER_charter_valid"))
                self.assertNotIn("HSM_VER_charter_signed", w.countries["AVI"].flags)


class NegotiationRecovery(unittest.TestCase):
    CASES = (
        ("armistice", "HSM_VER_offer_armistice", 45, 90, "hsm_verenia.29", "hsm_verenia.20", "EYR"),
        ("treaty", "HSM_VER_offer_treaty", 45, 90, "hsm_verenia.39", "hsm_verenia.30", "EYR"),
        ("charter", "HSM_VER_offer_charter", 60, 120, "hsm_verenia.69", "hsm_verenia.61", "EYR"),
        ("avian", "HSM_VER_invite_avian", 45, 120, "hsm_verenia.59", "hsm_verenia.50", "AVI"),
    )

    def world_for(self, kind):
        w = World()
        if kind == "avian":
            w.countries["AVI"].focuses.add("intergigantes")
        if kind == "treaty":
            w.armistice()
        elif kind in ("charter", "avian"):
            w.sign()
        return w

    def outcome_flag(self, kind):
        return "HSM_VER_avian_declined" if kind == "avian" else f"HSM_VER_{kind}_refused"

    def assert_unsigned(self, w, kind):
        trigger = {
            "armistice": "HSM_VER_armistice_valid",
            "treaty": "HSM_VER_negotiated_peace_valid",
            "charter": "HSM_VER_charter_valid",
        }.get(kind)
        if trigger:
            self.assertFalse(w.test(trigger))
        else:
            self.assertNotIn("HSM_VER_congress_observer", w.countries["AVI"].flags)

    def test_new_pending_windows_expire_before_retry_and_after_timeout_delivery(self):
        for kind, offer, lease, retry, timeout_id, _, _ in self.CASES:
            with self.subTest(kind=kind):
                w = self.world_for(kind)
                w.apply(offer)
                c = w.countries["ERI"]
                self.assertEqual(c.flag_days[f"HSM_VER_{kind}_pending"], lease)
                self.assertEqual(c.flag_days[f"HSM_VER_{kind}_retry"], retry)
                timeout_call = next(n for n in walk(w.effects[offer]) if n.key == "country_event" and n.get("id") == timeout_id)
                self.assertGreater(lease, int(timeout_call.get("days")) + int(w.events[timeout_id].get("timeout_days")))
                self.assertGreater(retry, lease)
                w.advance_days(lease - 1)
                w.apply("HSM_VER_maintain_agreements")
                self.assertIn(f"HSM_VER_{kind}_pending", c.flags)
                self.assertNotIn(self.outcome_flag(kind), c.flags)

    def test_dropped_offer_and_timeout_recover_after_annexation_without_early_retry(self):
        for kind, offer, lease, retry, timeout_id, answer_id, recipient in self.CASES:
            with self.subTest(kind=kind):
                w = self.world_for(kind)
                w.apply(offer)
                c = w.countries["ERI"]
                c.exists = False
                for country in w.countries.values():
                    country.events.clear()
                w.advance_days(lease)
                c.exists = True
                w.apply("HSM_VER_maintain_agreements")
                self.assertNotIn(f"HSM_VER_{kind}_pending", c.flags)
                self.assertIn(self.outcome_flag(kind), c.flags)
                self.assert_unsigned(w, kind)
                self.assertFalse(w.check(w.events[timeout_id].get("trigger")))
                w.choose(answer_id, tag=recipient)
                self.assert_unsigned(w, kind)
                self.assertEqual(c.political_power, 0)
                for sender in ("ERI", "AVI"):
                    w.apply(offer, sender)
                self.assertFalse(any(country.events for country in w.countries.values()))
                w.advance_days(retry - lease)
                w.apply("HSM_VER_maintain_agreements")
                w.apply(offer)
                self.assertIn(f"HSM_VER_{kind}_pending", c.flags)
                self.assertNotIn(self.outcome_flag(kind), c.flags)
                w.choose(timeout_id)
                self.assertIn(f"HSM_VER_{kind}_pending", c.flags)
                w.choose(answer_id, tag=recipient)
                self.assertNotIn(f"HSM_VER_{kind}_pending", c.flags)

    def test_legacy_untimed_pending_recovers_only_after_original_cooldown(self):
        for kind, offer, _, retry, _, _, _ in self.CASES:
            with self.subTest(kind=kind):
                w = self.world_for(kind)
                w.apply(offer)
                c = w.countries["ERI"]
                c.flag_days.pop(f"HSM_VER_{kind}_pending", None)
                c.flags.discard(f"HSM_VER_{kind}_offer_unresolved")
                w.advance_days(retry - 1)
                w.apply("HSM_VER_maintain_agreements")
                self.assertIn(f"HSM_VER_{kind}_pending", c.flags)
                w.advance_days(1)
                w.apply("HSM_VER_maintain_agreements")
                self.assertNotIn(f"HSM_VER_{kind}_pending", c.flags)
                self.assertIn(self.outcome_flag(kind), c.flags)
                self.assert_unsigned(w, kind)
                w.apply(offer)
                self.assertIn(f"HSM_VER_{kind}_pending", c.flags)

    def test_eyrie_owned_producers_recover_through_shared_register(self):
        for kind, _, _, retry, _, _, _ in self.CASES[:3]:
            with self.subTest(kind=kind):
                w = self.world_for(kind)
                offer = f"HSM_VER_eyr_offer_{kind}"
                w.apply(offer, "EYR")
                eri, eyr = w.countries["ERI"], w.countries["EYR"]
                eyr.exists = False
                for country in w.countries.values():
                    country.events.clear()
                w.advance_days(retry - 1)
                w.apply("HSM_VER_maintain_agreements")
                self.assertIn(f"HSM_VER_{kind}_pending", eri.flags)
                w.advance_days(1)
                w.apply("HSM_VER_maintain_agreements")
                self.assertNotIn(f"HSM_VER_{kind}_pending", eri.flags)
                self.assertNotIn(f"HSM_VER_{kind}_from_eyrie", eri.flags)
                self.assertIn(self.outcome_flag(kind), eri.flags)
                eyr.exists = True
                w.apply(offer, "EYR")
                self.assertIn(f"HSM_VER_{kind}_pending", eri.flags)
                self.assertIn(f"HSM_VER_{kind}_from_eyrie", eri.flags)

    def test_accepted_offers_are_not_relabelled_failed_after_deadlines(self):
        for kind, offer, _, retry, _, answer_id, recipient in self.CASES:
            with self.subTest(kind=kind):
                w = self.world_for(kind)
                w.apply(offer)
                w.choose(answer_id, tag=recipient)
                w.advance_days(retry + 1)
                w.apply("HSM_VER_maintain_agreements")
                c = w.countries["ERI"]
                self.assertNotIn(self.outcome_flag(kind), c.flags)
                self.assertNotIn(f"HSM_VER_{kind}_offer_unresolved", c.flags)

    def test_war_cancels_recovery_bookkeeping_without_later_false_refusal(self):
        for kind, offer, _, retry, _, _, _ in self.CASES:
            with self.subTest(kind=kind):
                w = self.world_for(kind)
                w.apply(offer)
                w.apply("HSM_VER_void_bilateral_treaty")
                w.advance_days(retry + 1)
                w.apply("HSM_VER_maintain_agreements")
                c = w.countries["ERI"]
                self.assertNotIn(f"HSM_VER_{kind}_offer_unresolved", c.flags)
                self.assertNotIn(self.outcome_flag(kind), c.flags)
                self.assert_unsigned(w, kind)

    def test_crisis_cancellation_preserves_contact_flags_without_false_timeout(self):
        w = self.world_for("avian")
        w.apply("HSM_VER_invite_avian")
        w.apply("HSM_VER_avian_crisis_response")
        c = w.countries["ERI"]
        self.assertIn("HSM_VER_CR_contact_opened", c.flags)
        self.assertEqual(c.flag_days["HSM_VER_CR_demand_pending"], 30)
        self.assertNotIn("HSM_VER_avian_pending", c.flags)
        self.assertNotIn("HSM_VER_avian_offer_unresolved", c.flags)
        w.apply("HSM_VER_maintain_agreements")
        self.assertNotIn("HSM_VER_avian_declined", c.flags)


class UnionReestablishment(unittest.TestCase):
    def completed_union(self):
        w = World()
        w.charter()
        c = w.countries["ERI"]
        c.focuses.add("HSM_ERI_generation_without_feud")
        c.flags.add("HSM_VER_union_established")
        w.apply("HSM_VER_void_bilateral_treaty")
        self.assertNotIn("HSM_VER_union_established", c.flags)
        return w

    def test_completed_union_restores_after_renewed_charter_without_replaying_rewards(self):
        w = self.completed_union()
        w.charter()
        before = {tag: (c.political_power, c.army_experience, list(c.events), set(c.focuses)) for tag, c in w.countries.items()}
        w.apply("HSM_VER_maintain_agreements")
        self.assertIn("HSM_VER_union_established", w.countries["ERI"].flags)
        self.assertTrue(w.test("HSM_VER_IMP_institutions_available"))
        w.apply("HSM_VER_maintain_agreements")
        after = {tag: (c.political_power, c.army_experience, list(c.events), set(c.focuses)) for tag, c in w.countries.items()}
        self.assertEqual(before, after)

    def test_treaty_alone_or_unfinished_finale_cannot_establish_union(self):
        w = self.completed_union()
        w.sign()
        w.apply("HSM_VER_maintain_agreements")
        self.assertNotIn("HSM_VER_union_established", w.countries["ERI"].flags)
        w.charter()
        w.countries["ERI"].focuses.clear()
        w.apply("HSM_VER_maintain_agreements")
        self.assertNotIn("HSM_VER_union_established", w.countries["ERI"].flags)

    def test_occupation_subjection_missing_partner_and_each_breach_delay_restoration(self):
        for obstacle in ("occupation", "subject", "absent", "eri_breach", "eyr_breach", "avi_breach"):
            with self.subTest(obstacle=obstacle):
                w = self.completed_union()
                w.charter()
                eri, eyr, avi = (w.countries[tag] for tag in ("ERI", "EYR", "AVI"))
                if obstacle == "occupation":
                    eyr.capitulated = True
                elif obstacle == "subject":
                    eri.subject = True
                elif obstacle == "absent":
                    eyr.exists = False
                elif obstacle == "eri_breach":
                    eri.flags.add("HSM_VER_royal_exception")
                elif obstacle == "eyr_breach":
                    eyr.flags.add("HSM_EYR_command_dispute")
                else:
                    avi.flags.update(("HSM_VER_charter_signed", "HSM_AVI_levy_exception"))
                w.apply("HSM_VER_maintain_agreements")
                self.assertNotIn("HSM_VER_union_established", eri.flags)
                eyr.capitulated = False
                eri.subject = False
                eyr.exists = True
                eri.flags.discard("HSM_VER_royal_exception")
                eyr.flags.discard("HSM_EYR_command_dispute")
                avi.flags.discard("HSM_AVI_levy_exception")
                w.apply("HSM_VER_maintain_agreements")
                self.assertIn("HSM_VER_union_established", eri.flags)

    def test_new_inter_house_war_invalidates_restored_union_again(self):
        w = self.completed_union()
        w.charter()
        w.apply("HSM_VER_maintain_agreements")
        c = w.countries["ERI"]
        self.assertIn("HSM_VER_union_established", c.flags)
        c.wars.add("EYR")
        w.apply("HSM_VER_maintain_agreements")
        self.assertNotIn("HSM_VER_union_established", c.flags)
        self.assertFalse(w.test("HSM_VER_charter_valid"))


class EyrieCampaign(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.eri = self.w.countries["ERI"]
        self.eyr = self.w.countries["EYR"]

    def test_eyrie_start_keeps_eries_intro_available(self):
        self.w.apply("HSM_VER_eyr_start_campaign", "EYR")
        self.w.apply("HSM_VER_start_campaign")
        self.w.apply("HSM_VER_eyr_start_campaign", "EYR")
        self.w.apply("HSM_VER_start_campaign")
        self.assertEqual(self.eyr.events, ["hsm_ver_eyrie.1"])
        self.assertEqual(self.eri.events, ["hsm_verenia.1"])

    def test_two_initiators_share_one_armistice_register(self):
        for first in ("HSM_VER_eyr_offer_armistice", "HSM_VER_offer_armistice"):
            w = World()
            w.apply(first, "EYR" if "eyr" in first else "ERI")
            w.apply("HSM_VER_eyr_offer_armistice", "EYR")
            w.apply("HSM_VER_offer_armistice")
            offers = sum(c.events.count("hsm_ver_eyrie.110") + c.events.count("hsm_verenia.20") for c in w.countries.values())
            self.assertEqual(offers, 1)
            self.assertFalse(w.test("HSM_VER_armistice_valid"))

    def test_eyrie_armistice_requires_actual_erie_answer(self):
        self.w.apply("HSM_VER_eyr_offer_armistice", "EYR")
        self.assertIn("hsm_ver_eyrie.110", self.eri.events)
        self.assertNotIn("hsm_ver_eyrie.110", self.eyr.events)
        self.w.choose("hsm_ver_eyrie.110", 1)
        self.w.choose("hsm_ver_eyrie.111", tag="EYR")
        self.w.choose("hsm_ver_eyrie.111", tag="EYR")
        self.assertTrue(self.w.test("HSM_VER_armistice_valid"))
        self.assertEqual(self.eyr.political_power, -35)

    def test_eyrie_refusal_cannot_be_bypassed_by_other_house(self):
        self.w.apply("HSM_VER_eyr_offer_armistice", "EYR")
        self.w.choose("hsm_ver_eyrie.110", 2)
        self.w.apply("HSM_VER_offer_armistice")
        self.assertNotIn("hsm_verenia.20", self.eyr.events)
        self.w.advance_days(90)
        self.w.apply("HSM_VER_offer_armistice")
        self.assertIn("hsm_verenia.20", self.eyr.events)

    def test_eyrie_treaty_counteroffer_paid_only_once(self):
        self.w.armistice()
        self.w.apply("HSM_VER_eyr_offer_treaty", "EYR")
        self.w.choose("hsm_ver_eyrie.120", 1)
        self.w.choose("hsm_ver_eyrie.121", tag="EYR")
        self.w.choose("hsm_ver_eyrie.121", tag="EYR")
        self.assertEqual(self.eyr.political_power, -50)
        self.assertTrue(self.w.test("HSM_VER_negotiated_peace_valid"))

    def test_eyrie_stale_answers_after_war_have_no_effect(self):
        self.w.armistice()
        self.w.apply("HSM_VER_eyr_offer_treaty", "EYR")
        self.w.apply("HSM_VER_void_bilateral_treaty")
        for event, tag in (("110", "ERI"), ("111", "EYR"), ("120", "ERI"), ("121", "EYR"), ("130", "ERI"), ("131", "EYR")):
            self.w.choose("hsm_ver_eyrie." + event, tag=tag)
        self.assertEqual(self.eyr.political_power, 0)
        self.assertFalse(self.w.test("HSM_VER_negotiated_peace_valid"))
        self.assertNotIn("HSM_VER_ducal_presidency", self.eri.flags)

    def test_eyrie_delivery_timeouts_precede_retry_and_do_not_reopen_old_offers(self):
        for kind, setup, offer, timeout, answer in (
            ("armistice", lambda: None, "armistice", "119", "111"),
            ("treaty", lambda: self.w.armistice(), "treaty", "129", "121"),
            ("charter", lambda: self.w.sign(), "charter", "139", "131"),
        ):
            self.setUp()
            setup()
            self.w.apply("HSM_VER_eyr_offer_" + offer, "EYR")
            event = self.w.events["hsm_ver_eyrie." + timeout]
            self.w.advance_days(45 if kind == "charter" else 30)
            self.assertTrue(self.w.check(event.get("trigger"), "EYR"))
            self.w.run(event.get("immediate"), "EYR")
            self.w.choose("hsm_ver_eyrie." + answer, tag="EYR")
            self.assertEqual(self.eyr.political_power, 0)
            self.assertNotIn("HSM_VER_" + kind + "_pending", self.eri.flags)
            self.w.advance_days(120)
            self.w.apply("HSM_VER_eyr_offer_" + offer, "EYR")
            self.w.choose("hsm_ver_eyrie." + timeout, tag="EYR")
            self.assertIn("HSM_VER_" + kind + "_pending", self.eri.flags)

    def test_requested_presidency_needs_second_signature(self):
        self.w.sign()
        self.w.apply("HSM_VER_eyr_offer_charter", "EYR")
        self.w.choose("hsm_ver_eyrie.130", 1)
        self.assertNotIn("HSM_VER_ducal_presidency", self.eri.flags)
        self.assertFalse(self.w.test("HSM_VER_charter_valid"))
        self.w.choose("hsm_ver_eyrie.131", tag="EYR")
        self.assertIn("HSM_VER_ducal_presidency", self.eri.flags)
        self.assertTrue(self.w.test("HSM_VER_charter_valid"))
        self.assertFalse(self.eyr.subject)

    def test_charter_rejection_preserves_treaty_and_has_one_notice(self):
        self.w.sign()
        self.w.apply("HSM_VER_eyr_offer_charter", "EYR")
        self.w.choose("hsm_ver_eyrie.130", 2)
        notice = self.w.events["hsm_ver_eyrie.139"]
        self.assertTrue(self.w.check(notice.get("trigger"), "EYR"))
        self.w.run(notice.get("immediate"), "EYR")
        self.assertFalse(self.w.check(notice.get("trigger"), "EYR"))
        self.w.choose("hsm_ver_eyrie.131", tag="EYR")
        self.assertFalse(self.w.test("HSM_VER_charter_valid"))
        self.assertTrue(self.w.test("HSM_VER_negotiated_peace_valid"))

    def test_new_league_follows_eyrie_initiative_and_avian_joins_its_leader(self):
        self.w.charter()
        avi = self.w.countries["AVI"]
        avi.flags.add("HSM_VER_charter_signed")
        self.w.apply("HSM_VER_eyr_offer_defence", "EYR")
        self.w.choose("hsm_ver_eyrie.140")
        self.assertTrue(self.eyr.faction_leader)
        self.assertFalse(self.eri.faction_leader)
        self.assertFalse(avi.faction)
        self.w.choose("hsm_verenia.82", tag="AVI")
        self.assertEqual(avi.faction, self.eyr.faction)
        self.w.choose("hsm_ver_eyrie.140", 1)
        self.assertNotIn("HSM_VER_defence_declined", self.eri.flags)

    def test_existing_house_leader_is_preserved(self):
        for host in ("ERI", "EYR"):
            w = World()
            w.charter()
            w.countries[host].faction = "Existing league"
            w.countries[host].faction_leader = True
            w.apply("HSM_VER_eyr_offer_defence", "EYR")
            w.choose("hsm_ver_eyrie.140")
            self.assertTrue(w.countries[host].faction_leader)
            self.assertEqual(w.countries["ERI"].faction, "Existing league")
            self.assertEqual(w.countries["EYR"].faction, "Existing league")

    def test_dissolved_league_allows_a_new_consent_process(self):
        self.w.charter()
        self.w.apply("HSM_VER_eyr_offer_defence", "EYR")
        self.w.choose("hsm_ver_eyrie.140")
        self.eri.faction = self.eyr.faction = ""
        self.eyr.faction_leader = False
        self.w.apply("HSM_VER_maintain_agreements")
        self.assertNotIn("HSM_VER_defence_accepted", self.eri.flags)
        self.assertFalse(self.w.test("HSM_VER_can_offer_defence"))
        self.w.advance_days(90)
        self.w.apply("HSM_VER_eyr_offer_defence", "EYR")
        self.assertFalse(self.eyr.faction)
        self.assertEqual(self.eri.events.count("hsm_ver_eyrie.140"), 2)
        self.w.choose("hsm_ver_eyrie.140")
        self.assertTrue(self.w.test("HSM_VER_defence_league_operational"))

    def test_suspended_charter_does_not_erase_military_agreement(self):
        self.w.charter()
        self.w.apply("HSM_VER_eyr_offer_defence", "EYR")
        self.w.choose("hsm_ver_eyrie.140")
        self.eyr.flags.add("HSM_EYR_command_dispute")
        self.w.apply("HSM_VER_suspend_charter")
        self.w.apply("HSM_VER_maintain_agreements")
        self.assertIn("HSM_VER_defence_accepted", self.eri.flags)
        self.assertEqual(self.eri.faction, self.eyr.faction)

    def test_late_avian_signatory_gets_one_offer_and_may_refuse(self):
        self.w.countries["AVI"].focuses.add("intergigantes")
        self.w.charter()
        self.w.apply("HSM_VER_eyr_offer_defence", "EYR")
        self.w.choose("hsm_ver_eyrie.140")
        avi = self.w.countries["AVI"]
        self.assertNotIn("hsm_verenia.82", avi.events)
        self.w.apply("HSM_VER_invite_avian")
        self.w.choose("hsm_verenia.50", tag="AVI")
        self.w.choose("hsm_verenia.63", tag="AVI")
        self.w.apply("HSM_VER_maintain_agreements", "AVI")
        self.w.apply("HSM_VER_maintain_agreements", "AVI")
        self.assertEqual(avi.events.count("hsm_verenia.82"), 1)
        self.w.choose("hsm_verenia.82", 1, "AVI")
        self.w.advance_days(91)
        self.w.apply("HSM_VER_maintain_agreements", "AVI")
        self.w.choose("hsm_verenia.82", tag="AVI")
        self.assertFalse(avi.faction)
        self.assertEqual(avi.events.count("hsm_verenia.82"), 1)

    def test_undelivered_avian_military_offer_retries_after_liberation(self):
        self.w.charter()
        avi = self.w.countries["AVI"]
        avi.flags.add("HSM_VER_charter_signed")
        self.w.apply("HSM_VER_eyr_offer_defence", "EYR")
        self.w.choose("hsm_ver_eyrie.140")
        avi.capitulated = True
        self.assertFalse(self.w.check(self.w.events["hsm_verenia.82"].get("trigger"), "AVI"))
        self.w.advance_days(91)
        self.w.apply("HSM_VER_maintain_agreements", "AVI")
        self.assertEqual(avi.events.count("hsm_verenia.82"), 1)
        avi.capitulated = False
        self.w.apply("HSM_VER_maintain_agreements", "AVI")
        self.assertEqual(avi.events.count("hsm_verenia.82"), 2)

    def test_stale_avian_refusal_after_war_does_not_block_new_ratification(self):
        self.w.countries["AVI"].focuses.add("intergigantes")
        self.w.charter()
        avi = self.w.countries["AVI"]
        avi.flags.add("HSM_VER_charter_signed")
        self.w.apply("HSM_VER_eyr_offer_defence", "EYR")
        self.w.choose("hsm_ver_eyrie.140")
        action = read(MOD / "common/on_actions/HSM_VER_diplomacy.txt")[0]
        self.w.root, self.w.sender = "AVI", "ERI"
        self.w.run(action.all("on_war_relation_added")[0].get("effect"), "AVI")
        self.assertNotIn("HSM_VER_avian_defence_pending", avi.flags)
        self.w.choose("hsm_verenia.82", 1, "AVI")
        self.assertNotIn("HSM_VER_avian_defence_declined", avi.flags)
        avi.flags.add("HSM_VER_congress_observer")
        self.w.apply("HSM_VER_offer_avian_charter")
        self.w.choose("hsm_verenia.63", tag="AVI")
        self.w.advance_days(91)
        self.w.apply("HSM_VER_maintain_agreements", "AVI")
        self.assertEqual(avi.events.count("hsm_verenia.82"), 2)

    def test_erie_defence_focus_does_not_report_failure_for_existing_league(self):
        tree = read(MOD / "common/national_focus/HSM_ERI.txt")[0]
        focus = next(n for n in tree.all("focus") if n.get("id") == "HSM_ERI_common_defence")
        response = [n for n in focus.get("completion_reward") if n.key in ("if", "else_if", "else")]
        self.w.charter()
        self.w.apply("HSM_VER_eyr_offer_defence", "EYR")
        self.w.run(response)
        self.assertNotIn("hsm_verenia.81", self.eri.events)
        self.w.choose("hsm_ver_eyrie.140")
        self.w.run(response)
        self.assertNotIn("hsm_verenia.81", self.eri.events)

    def test_neither_initiator_takes_foreign_faction_member(self):
        for tag in ("ERI", "EYR"):
            w = World()
            w.charter()
            w.countries[tag].faction = "Foreign league"
            w.apply("HSM_VER_eyr_offer_defence", "EYR")
            w.choose("hsm_ver_eyrie.140")
            self.assertNotIn("HSM_VER_defence_accepted", w.countries["ERI"].flags)
            self.assertEqual(w.countries[tag].faction, "Foreign league")

    def test_each_house_must_resolve_its_own_exception(self):
        for first in ("HSM_VER_restore_charter", "HSM_VER_eyr_withdraw_requisitions"):
            w = World()
            w.charter()
            w.countries["ERI"].flags.add("HSM_VER_royal_exception")
            w.countries["EYR"].flags.add("HSM_EYR_command_dispute")
            w.apply("HSM_VER_suspend_charter")
            w.apply(first)
            self.assertFalse(w.test("HSM_VER_charter_valid"))
            second = "HSM_VER_eyr_withdraw_requisitions" if first == "HSM_VER_restore_charter" else "HSM_VER_restore_charter"
            w.apply(second)
            self.assertTrue(w.test("HSM_VER_charter_valid"))

    def test_reratification_does_not_excuse_previous_requisitions(self):
        self.w.charter()
        self.eyr.flags.add("HSM_EYR_command_dispute")
        self.w.apply("HSM_VER_suspend_charter")
        self.w.apply("HSM_VER_void_bilateral_treaty")
        self.w.charter()
        self.assertFalse(self.w.test("HSM_VER_charter_valid"))
        self.assertNotIn("HSM_VER_common_courts", self.eyr.ideas)
        self.w.apply("HSM_VER_eyr_withdraw_requisitions", "EYR")
        self.assertTrue(self.w.test("HSM_VER_charter_valid"))

    def test_eyrie_command_case_retries_after_occupation_and_resolves_once(self):
        self.w.charter()
        self.eyr.focuses.add("HSM_EYR_the_return_order")
        self.w.apply("HSM_VER_eyr_queue_command_case", "EYR")
        self.eri.capitulated = True
        self.assertFalse(self.w.check(self.w.events["hsm_ver_eyrie.30"].get("trigger"), "EYR"))
        self.w.advance_days(31)
        self.w.apply("HSM_VER_eyr_queue_command_case", "EYR")
        self.assertEqual(self.eyr.events.count("hsm_ver_eyrie.30"), 1)
        self.eri.capitulated = False
        self.w.apply("HSM_VER_eyr_queue_command_case", "EYR")
        self.w.apply("HSM_VER_eyr_queue_command_case", "EYR")
        self.w.choose("hsm_ver_eyrie.30", tag="EYR")
        self.w.choose("hsm_ver_eyrie.30", tag="EYR")
        self.assertEqual(self.eyr.events.count("hsm_ver_eyrie.30"), 2)
        self.assertEqual(self.eyr.political_power, -75)
        self.assertTrue(self.w.test("HSM_VER_eyr_settlement_ready"))

    def test_protecting_officers_suspends_but_does_not_destroy_treaty(self):
        self.w.charter()
        self.eyr.focuses.add("HSM_EYR_the_return_order")
        self.w.apply("HSM_VER_eyr_queue_command_case", "EYR")
        self.w.choose("hsm_ver_eyrie.30", 1, "EYR")
        self.assertIn("HSM_EYR_exceptional_requisitions", self.eyr.ideas)
        self.assertFalse(self.w.test("HSM_VER_charter_valid"))
        self.assertTrue(self.w.test("HSM_VER_negotiated_peace_valid"))
        self.w.apply("HSM_VER_eyr_withdraw_requisitions", "EYR")
        self.assertTrue(self.w.test("HSM_VER_eyr_settlement_ready"))
        self.assertNotIn("HSM_EYR_exceptional_requisitions", self.eyr.ideas)

    def test_muster_and_command_choices_do_not_stack(self):
        self.w.choose("hsm_ver_eyrie.2", 0, "EYR")
        self.w.choose("hsm_ver_eyrie.2", 1, "EYR")
        self.assertEqual(self.eyr.political_power, -35)
        self.assertEqual(self.eyr.army_experience, 0)
        self.assertNotIn("HSM_EYR_officers_confidence", self.eyr.ideas)
        self.w.sign()
        self.w.choose("hsm_ver_eyrie.10", 0, "EYR")
        self.w.choose("hsm_ver_eyrie.10", 1, "EYR")
        self.assertIn("HSM_EYR_civic_scrutiny", self.eyr.ideas)
        self.assertNotIn("HSM_EYR_professional_command", self.eyr.ideas)

    def test_early_eyrie_policy_choices_recover_after_occupation(self):
        self.w.sign()
        self.eyr.focuses |= {"HSM_EYR_audit_the_muster", "HSM_EYR_limits_of_command"}
        self.w.apply("HSM_VER_eyr_queue_policy_scenes", "EYR")
        self.eyr.capitulated = True
        for number in ("2", "10"):
            self.assertFalse(self.w.check(self.w.events["hsm_ver_eyrie." + number].get("trigger"), "EYR"))
            self.w.choose("hsm_ver_eyrie." + number, tag="EYR")
        self.assertEqual(self.eyr.political_power, 0)
        self.w.advance_days(31)
        self.w.apply("HSM_VER_eyr_queue_policy_scenes", "EYR")
        self.eyr.capitulated = False
        self.w.apply("HSM_VER_eyr_queue_policy_scenes", "EYR")
        self.w.apply("HSM_VER_eyr_queue_policy_scenes", "EYR")
        for number in ("2", "10"):
            self.assertEqual(self.eyr.events.count("hsm_ver_eyrie." + number), 2)
            self.w.choose("hsm_ver_eyrie." + number, tag="EYR")
        self.w.advance_days(31)
        self.w.apply("HSM_VER_eyr_queue_policy_scenes", "EYR")
        self.assertEqual(self.eyr.political_power, -35)
        self.assertEqual(self.eyr.events.count("hsm_ver_eyrie.2"), 2)

    def test_actual_charter_bypasses_both_houses_signing_focus(self):
        self.w.charter()
        for path, key in (("HSM_ERI.txt", "HSM_ERI_common_statute"), ("HSM_VER_eyrie.txt", "HSM_EYR_a_charter_we_can_sign")):
            tree = read(MOD / "common/national_focus" / path)[0]
            focus = next(n for n in tree.all("focus") if n.get("id") == key)
            self.assertTrue(self.w.check(focus.get("bypass")))


class NegotiationProgression(unittest.TestCase):
    """Follow the production AI response weights, not just a forced accept option."""

    def weights(self, world, event_id, tag):
        event = world.events[event_id]
        self.assertTrue(world.check(event.get("trigger", []), tag))
        result = []
        for option in event.all("option"):
            if not world.check(option.get("trigger", []), tag):
                result.append(0)
                continue
            chance = option.all("ai_chance")[0]
            weight = float(chance.get("factor", "1"))
            for modifier in chance.all("modifier"):
                self.assertEqual(set(n.key for n in modifier.children) & {"add", "base"}, set())
                conditions = [n for n in modifier.children if n.key != "factor"]
                if world.check(conditions, tag):
                    weight *= float(modifier.get("factor", "1"))
            result.append(weight)
        self.assertGreater(sum(result), 0, "AI must have a live response")
        return result

    def cases(self):
        return (
            ("ERI", "EYR", "HSM_VER_offer_armistice", "hsm_verenia.20", "hsm_verenia.21", "HSM_VER_offer_treaty", "hsm_verenia.30", "hsm_verenia.31"),
            ("EYR", "ERI", "HSM_VER_eyr_offer_armistice", "hsm_ver_eyrie.110", "hsm_ver_eyrie.111", "HSM_VER_eyr_offer_treaty", "hsm_ver_eyrie.120", "hsm_ver_eyrie.121"),
        )

    def test_unprepared_armistice_has_a_finite_counteroffer_not_random_veto(self):
        for sender, recipient, offer, reply, counter, *_ in self.cases():
            with self.subTest(sender=sender):
                w = World()
                w.apply(offer, sender)
                self.assertEqual(self.weights(w, reply, recipient), [0, 100, 0])
                w.choose(reply, 1, recipient)
                self.assertIn(counter, w.countries[sender].events)
                self.assertEqual(self.weights(w, counter, sender), [100, 0])
                w.choose(counter, 0, sender)
                self.assertTrue(w.test("HSM_VER_armistice_valid"))
                self.assertEqual(w.countries[sender].political_power, -35)
                w.choose(counter, 0, sender)
                self.assertEqual(w.countries[sender].political_power, -35)
                for tag in ("ERI", "EYR"):
                    self.assertIn("HSM_VER_frontier_inspections", w.countries[tag].ideas)

    def test_prepared_guarantees_are_accepted_without_another_roll_or_inspection_fee(self):
        for sender, recipient, offer, reply, _, treaty, treaty_reply, _ in self.cases():
            with self.subTest(sender=sender):
                w = World()
                w.countries["ERI"].flags.add("HSM_VER_guarantees_prepared")
                w.apply(offer, sender)
                self.assertEqual(self.weights(w, reply, recipient), [100, 0, 0])
                w.choose(reply, 0, recipient)
                self.assertTrue(w.test("HSM_VER_armistice_valid"))
                w.apply(treaty, sender)
                self.assertEqual(self.weights(w, treaty_reply, recipient), [100, 0, 0])
                w.choose(treaty_reply, 0, recipient)
                self.assertTrue(w.test("HSM_VER_negotiated_peace_valid"))
                for tag in ("ERI", "EYR"):
                    self.assertEqual(w.countries[tag].political_power, 0)
                    self.assertNotIn("HSM_VER_frontier_inspections", w.countries[tag].ideas)

    def test_unprepared_treaty_reaches_binding_arbitration(self):
        for sender, recipient, _, _, _, offer, reply, counter in self.cases():
            with self.subTest(sender=sender):
                w = World()
                w.armistice()
                w.apply(offer, sender)
                self.assertEqual(self.weights(w, reply, recipient), [0, 100, 0])
                w.choose(reply, 1, recipient)
                self.assertEqual(self.weights(w, counter, sender), [100, 0])
                w.choose(counter, 0, sender)
                self.assertTrue(w.test("HSM_VER_negotiated_peace_valid"))
                self.assertEqual(w.countries[sender].political_power, -50)
                w.choose(counter, 0, sender)
                self.assertEqual(w.countries[sender].political_power, -50)

    def test_players_keep_the_right_to_refuse_even_prepared_terms(self):
        for sender, recipient, offer, reply, *_ in self.cases():
            with self.subTest(sender=sender):
                w = World()
                w.countries["ERI"].flags.add("HSM_VER_guarantees_prepared")
                w.apply(offer, sender)
                refusal = w.events[reply].all("option")[2]
                self.assertTrue(w.check(refusal.get("trigger", []), recipient))
                w.choose(reply, 2, recipient)
                self.assertFalse(w.test("HSM_VER_armistice_valid"))
                self.assertIn("HSM_VER_armistice_refused", w.countries["ERI"].flags)

    def test_player_may_reject_inspections_without_a_signed_armistice(self):
        for sender, recipient, offer, reply, counter, *_ in self.cases():
            w = World()
            w.apply(offer, sender)
            w.choose(reply, 1, recipient)
            w.choose(counter, 1, sender)
            self.assertFalse(w.test("HSM_VER_armistice_valid"))
            self.assertEqual(w.countries[sender].political_power, 0)

    def test_equal_charter_accepted_ducal_presidency_requires_actual_concession(self):
        for presidency in (False, True):
            w = World()
            w.sign()
            w.apply("HSM_VER_offer_charter")
            w.choose("hsm_verenia.60", int(presidency))
            expected = [0, 100, 0] if presidency else [100, 0, 0]
            self.assertEqual(self.weights(w, "hsm_verenia.61", "EYR"), expected)
            w.choose("hsm_verenia.61", int(presidency), "EYR")
            if presidency:
                self.assertFalse(w.test("HSM_VER_charter_valid"))
                w.choose("hsm_verenia.62", 0)
            self.assertTrue(w.test("HSM_VER_charter_valid"))
            self.assertNotIn("HSM_VER_ducal_presidency", w.countries["ERI"].flags)

    def test_ai_erie_accepts_eyrie_equal_charter(self):
        w = World()
        w.sign()
        w.apply("HSM_VER_eyr_offer_charter", "EYR")
        self.assertEqual(self.weights(w, "hsm_ver_eyrie.130", "ERI"), [100, 0, 0])
        w.choose("hsm_ver_eyrie.130")
        self.assertTrue(w.test("HSM_VER_charter_valid"))

    def test_guarantee_focus_is_available_before_ceasefire(self):
        for file, focus_id, prerequisites in (
            ("HSM_ERI.txt", "HSM_ERI_reciprocal_guarantees", {"HSM_ERI_family_letters", "HSM_ERI_hear_petitions"}),
            ("HSM_VER_eyrie.txt", "HSM_EYR_publish_the_rules", {"HSM_EYR_montagues_correspondence", "HSM_EYR_audit_the_muster"}),
        ):
            focus = next(n for n in read(MOD / "common/national_focus" / file)[0].all("focus") if n.get("id") == focus_id)
            self.assertEqual({n.get("focus") for n in focus.all("prerequisite")}, prerequisites)
            self.assertTrue(World().check(focus.get("available")))

    def test_inspection_cost_ends_with_expiry_or_war(self):
        for ending in ("expiry", "war"):
            w = World()
            w.countries["ERI"].flags.add("HSM_VER_guarantees_prepared")
            w.armistice()
            if ending == "expiry":
                w.advance_days(366)
                for tag in ("ERI", "EYR"):
                    w.apply("HSM_VER_maintain_agreements", tag)
            else:
                w.apply("HSM_VER_void_bilateral_treaty")
            for tag in ("ERI", "EYR"):
                self.assertNotIn("HSM_VER_frontier_inspections", w.countries[tag].ideas)

    def test_late_guarantees_apply_inspections_only_to_live_temporary_armistice(self):
        for treaty in (False, True):
            w = World()
            w.armistice()
            if treaty:
                w.sign()
            w.apply("HSM_VER_prepare_guarantees", "EYR")
            for tag in ("ERI", "EYR"):
                self.assertEqual("HSM_VER_frontier_inspections" in w.countries[tag].ideas, not treaty)

    def test_old_failed_save_gets_one_retry_without_consent_or_rewards(self):
        w = World()
        c = w.countries["ERI"]
        c.flags |= {"HSM_VER_armistice_refused", "HSM_VER_armistice_retry"}
        w.apply("HSM_VER_migrate_negotiation_revision")
        self.assertNotIn("HSM_VER_armistice_retry", c.flags)
        self.assertTrue(w.test("HSM_VER_can_offer_armistice"))
        self.assertFalse(w.test("HSM_VER_armistice_valid"))
        self.assertEqual(c.political_power, 0)
        w.apply("HSM_VER_offer_armistice")
        w.choose("hsm_verenia.20", 2, "EYR")
        w.apply("HSM_VER_migrate_negotiation_revision")
        self.assertIn("HSM_VER_armistice_retry", c.flags)

    def test_unexpired_inspections_resume_after_liberation_without_new_fee(self):
        w = World()
        w.apply("HSM_VER_prepare_guarantees")
        w.armistice()
        w.countries["EYR"].capitulated = True
        for tag in ("ERI", "EYR"):
            w.apply("HSM_VER_maintain_agreements", tag)
            self.assertNotIn("HSM_VER_frontier_inspections", w.countries[tag].ideas)
        w.countries["EYR"].capitulated = False
        for tag in ("ERI", "EYR"):
            w.apply("HSM_VER_maintain_agreements", tag)
            self.assertIn("HSM_VER_frontier_inspections", w.countries[tag].ideas)
            self.assertEqual(w.countries[tag].political_power, 0)

    def test_migration_does_not_interrupt_open_legacy_offer(self):
        w = World()
        c = w.countries["ERI"]
        c.flags |= {"HSM_VER_armistice_refused", "HSM_VER_armistice_pending", "HSM_VER_armistice_retry"}
        w.apply("HSM_VER_migrate_negotiation_revision")
        self.assertIn("HSM_VER_armistice_pending", c.flags)
        self.assertIn("HSM_VER_armistice_retry", c.flags)

    def test_old_deadline_cannot_cancel_reopened_counteroffer(self):
        for sender, recipient, armistice, armistice_reply, armistice_counter, treaty, treaty_reply, treaty_counter in self.cases():
            for kind, offer, reply, counter, deadline in (
                ("armistice", armistice, armistice_reply, armistice_counter, "hsm_verenia.29" if sender == "ERI" else "hsm_ver_eyrie.119"),
                ("treaty", treaty, treaty_reply, treaty_counter, "hsm_verenia.39" if sender == "ERI" else "hsm_ver_eyrie.129"),
            ):
                for accept_counter in (False, True):
                    with self.subTest(sender=sender, kind=kind, accepts=accept_counter):
                        w = World()
                        if kind == "treaty":
                            w.armistice()
                        w.apply(offer, sender)
                        # A legacy refusal, with its day-30 deadline still in the engine queue.
                        w.advance_days(1)
                        w.choose(reply, 2, recipient)
                        w.countries["ERI"].flags.discard("HSM_VER_negotiation_revision_2")
                        w.advance_days(19)
                        w.apply("HSM_VER_migrate_negotiation_revision")
                        w.apply(offer, sender)
                        w.advance_days(1)
                        w.choose(reply, 1, recipient)
                        w.advance_days(9)
                        event = w.events[deadline]
                        self.assertFalse(w.check(event.get("trigger"), sender))
                        self.assertIn("HSM_VER_" + kind + "_pending", w.countries["ERI"].flags)
                        if accept_counter:
                            w.choose(counter, 0, sender)
                            valid = "HSM_VER_armistice_valid" if kind == "armistice" else "HSM_VER_negotiated_peace_valid"
                            self.assertTrue(w.test(valid))
                        else:
                            w.advance_days(20)
                            self.assertTrue(w.check(event.get("trigger"), sender))
                            w.run(event.get("immediate"), sender)
                            self.assertNotIn("HSM_VER_" + kind + "_pending", w.countries["ERI"].flags)

    def test_repeated_negotiation_decisions_are_removed(self):
        for file in ("HSM_VER_diplomacy.txt", "HSM_VER_eyrie.txt"):
            decisions = read(MOD / "common/decisions" / file)[0].children
            for decision in decisions:
                self.assertFalse(decision.key.endswith(("reopen_armistice", "reopen_treaty", "renew_armistice", "return_to_congress", "reopen_charter", "invite_avian_again")))


if __name__ == "__main__":
    unittest.main(argv=[__file__] + REST, verbosity=2)
