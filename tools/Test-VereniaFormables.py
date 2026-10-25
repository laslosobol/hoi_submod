"""Native formable overrides: exact upstream delta and bounded eligibility fixtures.

python -B tools/Test-VereniaFormables.py [--eaw PATH]
Read-only checks; does not launch HOI4 or evaluate formation effects.
"""
from __future__ import annotations

import copy
import difflib
import itertools
import runpy
import unittest
from dataclasses import dataclass
from pathlib import Path

BASE = runpy.run_path(str(Path(__file__).with_name("Test-Verenia.py")))
Node, read, parse, walk = (BASE[k] for k in ("Node", "read", "parse", "walk"))
ROOT, MOD, EAW = BASE["ROOT"], BASE["MOD"], BASE["OPT"].eaw
DECISIONS = Path("common/decisions/griffon_decisions.txt")
CATEGORIES = Path("common/decisions/categories/eaw_formable_categories.txt")
BLOCKED = {"form_griffon_empire": ("ERI", "EYR"), "form_aquileia": ("ERI", "AVI")}
GOVERNMENTS = ("neutrality", "democratic", "fascism", "communism")


def one(nodes, key):
    found = [n for n in nodes if n.key == key]
    if len(found) != 1:
        raise AssertionError(f"Expected one {key}, found {len(found)}")
    return found[0]


def guards(tags):
    return parse(" ".join(f"NOT = {{ original_tag = {tag} }}" for tag in tags))


def expected_override(path, upstream):
    expected = copy.deepcopy(upstream)
    for decision, tags in BLOCKED.items():
        category = one(expected, decision + "_category")
        if path == CATEGORIES:
            allowed = one(category.children, "allowed").children
            if decision == "form_griffon_empire":
                allowed.extend(guards(tags))
            else:
                allowed[:0] = guards(tags)
            category.children.append(Node("visible", "=", guards(tags)))
        else:
            entry = one(category.children, decision)
            if decision == "form_griffon_empire":
                one(entry.get("allowed"), "NOT").children[:0] = parse(
                    " ".join(f"original_tag = {tag}" for tag in tags)
                )
            else:
                entry.children.insert(1, Node("allowed", "=", guards(tags)))
            one(entry.children, "visible").children[:0] = guards(tags)
    return expected


@dataclass(frozen=True)
class Country:
    original_tag: str
    tag: str = "D01"
    cosmetic: str = "HSM_VER_UNIFIED"
    government: str = "neutrality"
    owned: frozenset = frozenset({382, 377, 376, 435, 448, 517})
    existing: frozenset = frozenset()
    flags: frozenset = frozenset()
    focuses: frozenset = frozenset()
    subject: bool = False
    leader: str = ""


class Eligibility:
    """Only predicates used by the two generic decisions; unknowns fail closed."""

    def __init__(self):
        path = Path("common/scripted_triggers/EAW_triggers.txt")
        self.triggers = {n.key: n.children for n in read(effective(path))}

    def check(self, nodes, country):
        taken = None
        for n in nodes:
            if n.key in ("if", "else_if", "else"):
                if n.key == "if":
                    taken = False
                if taken is None:
                    raise AssertionError("Conditional without if")
                if not taken and (n.key == "else" or self.check(n.get("limit", []), country)):
                    taken = True
                    if not self.check([c for c in n.children if c.key != "limit"], country):
                        return False
                continue
            if n.key == "AND":
                ok = self.check(n.children, country)
            elif n.key == "OR":
                ok = any(self.check([c], country) for c in n.children)
            elif n.key in ("NOT", "NOR"):
                ok = not any(self.check([c], country) for c in n.children)
            elif n.key == "can_use_fast_continent_checks":
                ok = n.value == "no"  # Exercise the native original-tag fallback.
            elif n.key in self.triggers:
                ok = self.check(self.triggers[n.key], country) == (n.value == "yes")
            elif n.key in ("tag", "original_tag"):
                ok = getattr(country, n.key) == n.value
            elif n.key == "has_cosmetic_tag":
                ok = country.cosmetic == n.value
            elif n.key == "has_government":
                ok = country.government == n.value
            elif n.key == "is_subject":
                ok = country.subject == (n.value == "yes")
            elif n.key == "has_country_leader":
                ok = country.leader == n.get("character")
            elif n.key in ("country_exists", "has_country_flag", "has_completed_focus", "owns_state"):
                attr = {"country_exists": "existing", "has_country_flag": "flags",
                        "has_completed_focus": "focuses", "owns_state": "owned"}[n.key]
                value = int(n.value) if n.key == "owns_state" else n.value
                ok = value in getattr(country, attr)
            else:
                raise AssertionError(f"Unsupported eligibility predicate: {n.key}")
            if not ok:
                return False
        return True


def effective(path):
    return MOD / path if (MOD / path).is_file() else EAW / path


def effective_files(folder):
    paths = {p.relative_to(EAW): p for p in (EAW / folder).rglob("*.txt")}
    paths.update({p.relative_to(MOD): p for p in (MOD / folder).rglob("*.txt")})
    return paths


class Formables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upstream = {p: read(EAW / p) for p in (DECISIONS, CATEGORIES)}
        cls.local = {p: read(MOD / p) for p in (DECISIONS, CATEGORIES)}
        cls.eligibility = Eligibility()
        cls.tags = sorted({n.key for p in (EAW / "common/country_tags").glob("*.txt") for n in read(p)})

    def entry(self, tree, decision):
        return one(one(tree[DECISIONS], decision + "_category").children, decision)

    def category(self, tree, decision):
        return one(tree[CATEGORIES], decision + "_category")

    def selectable(self, tree, decision, country, include_allowed=True):
        category = self.category(tree, decision)
        entry = self.entry(tree, decision)
        gates = [(category, "visible"), (entry, "visible"), (entry, "available")]
        if include_allowed:
            gates.extend(((category, "allowed"), (entry, "allowed")))
        return all(self.eligibility.check(n.get(gate, []), country) for n, gate in gates)

    def test_complete_files_have_only_the_expected_structural_delta(self):
        for path in self.local:
            with self.subTest(path=path):
                self.assertEqual(self.local[path], expected_override(path, self.upstream[path]))

    def test_upstream_text_is_preserved_with_only_guard_insertions(self):
        for path, added in ((DECISIONS, 10), (CATEGORIES, 12)):
            with self.subTest(path=path):
                old = (EAW / path).read_text(encoding="utf-8-sig").splitlines()
                new = (MOD / path).read_text(encoding="utf-8-sig").splitlines()
                diff = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
                self.assertTrue(all(op in ("equal", "insert") for op, *_ in diff.get_opcodes()))
                self.assertEqual(len(new) - len(old), added)

    def test_all_original_countries_and_governments_keep_upstream_eligibility(self):
        self.assertTrue({"ERI", "EYR", "AVI", "CYA", "JES"}.issubset(self.tags))
        for tag, government, decision in itertools.product(self.tags, GOVERNMENTS, BLOCKED):
            with self.subTest(tag=tag, government=government, decision=decision):
                country = Country(tag, government=government)
                before = self.selectable(self.upstream, decision, country)
                self.assertEqual(self.selectable(self.local, decision, country),
                                 before and tag not in BLOCKED[decision])

    def test_allowed_and_visible_each_reject_blocked_original_tags(self):
        for decision, tags in BLOCKED.items():
            for tag, current, cosmetic, government in itertools.product(
                    tags, ("ERI", "AVI", "CYA", "D01"), ("", "HSM_VER_UNIFIED", "GRIF_EMPIRE"), GOVERNMENTS):
                country = Country(tag, current, cosmetic, government)
                with self.subTest(decision=decision, country=country):
                    for node in (self.category(self.local, decision), self.entry(self.local, decision)):
                        for gate in ("allowed", "visible"):
                            self.assertFalse(self.eligibility.check(one(node.children, gate).children, country))
                    self.assertFalse(self.selectable(self.local, decision, country, include_allowed=False))

    def test_avi_and_cya_keep_generic_empire_access_after_identity_changes(self):
        for tag, current, cosmetic, government in itertools.product(
                ("AVI", "CYA"), ("ERI", "EYR", "D01"), ("", "HSM_VER_UNIFIED", "GRIF_EMPIRE"), GOVERNMENTS):
            with self.subTest(tag=tag, current=current, cosmetic=cosmetic, government=government):
                self.assertTrue(self.selectable(self.local, "form_griffon_empire",
                                               Country(tag, current, cosmetic, government)))

    def test_remaining_aquileia_candidates_still_form(self):
        candidates = ("JFT", "JEB", "JRR", "VIN", "POM", "FLO", "AET", "FEZ", "FRN")
        for tag in candidates:
            with self.subTest(tag=tag):
                self.assertTrue(self.selectable(self.local, "form_aquileia", Country(tag)))
        for tag in ("EYR", "CYA"):
            self.assertFalse(self.selectable(self.local, "form_aquileia", Country(tag)))

    def test_native_conditions_still_apply_to_unblocked_countries(self):
        cases = {
            "form_griffon_empire": [Country("AVI", subject=True), Country("CYA", owned=frozenset()),
                                     Country("AVI", existing=frozenset({"GRD"})),
                                     Country("CYA", flags=frozenset({"holds_griffon_capital"})),
                                     Country("AET", government="fascism"), Country("TRD")],
            "form_aquileia": [Country("FLO", subject=True), Country("FLO", existing=frozenset({"JER"})),
                              Country("FLO", owned=frozenset({377})), Country("FRN", government="democratic"),
                              Country("AET", government="communism")],
        }
        for decision, countries in cases.items():
            for country in countries:
                with self.subTest(decision=decision, country=country):
                    self.assertFalse(self.selectable(self.upstream, decision, country))
                    self.assertFalse(self.selectable(self.local, decision, country))
        for tag in ("JFT", "JEB", "JRR", "VIN"):
            self.assertTrue(self.selectable(self.local, "form_aquileia", Country(tag, owned=frozenset({377}))))

    def test_every_standard_aquileia_entry_is_blocked_at_category_level(self):
        category = one(self.local[DECISIONS], "form_aquileia_category")
        self.assertEqual({n.key for n in category.children}, {
            "form_aquileia", "unite_aquileia_proper", "reclaim_northwest_peripherie",
            "reclaim_eastern_peripherie", "aquileia_strikes_back",
        })
        for decision in category.children:
            for tag in ("ERI", "AVI"):
                with self.subTest(decision=decision.key, tag=tag):
                    gate = self.category(self.local, "form_aquileia")
                    self.assertFalse(self.eligibility.check(gate.get("allowed"), Country(tag)))
                    self.assertFalse(self.eligibility.check(gate.get("visible"), Country(tag)))

    def test_effective_definitions_are_unique_and_use_same_path_overrides(self):
        found = {key + "_category": [] for key in BLOCKED}
        for relative, path in effective_files("common/decisions").items():
            text = path.read_text(encoding="utf-8-sig")
            if not any(key in text for key in found):
                continue
            for node in parse(text):
                if node.key in found:
                    found[node.key].append(relative)
        for paths in found.values():
            self.assertCountEqual(paths, [DECISIONS, CATEGORIES])
        for path in (DECISIONS, CATEGORIES):
            self.assertEqual(effective(path), MOD / path)

    def test_no_other_aquileia_formation_decision_bypasses_exclusions(self):
        markers = {"core_aquileian_heartland", "claim_all_de_jure_aquileia", "global.aquileia_var"}
        found = set()
        for relative, path in effective_files("common/decisions").items():
            if "categories" in relative.parts:
                continue
            text = path.read_text(encoding="utf-8-sig")
            if not any(marker in text for marker in markers):
                continue
            for category in parse(text):
                for decision in category.children:
                    if not any(n.key in markers for n in walk(decision.children)):
                        continue
                    found.add((relative.as_posix(), decision.key))
                    for tag in ("ERI", "AVI"):
                        with self.subTest(path=relative, decision=decision.key, tag=tag):
                            self.assertFalse(self.eligibility.check(decision.get("allowed", []), Country(tag)))
        self.assertEqual(found, {
            (DECISIONS.as_posix(), "form_aquileia"),
            ("common/decisions/JES_decisions.txt", "JES_move_capital_decision"),
        })
        jes = one(read(effective(Path("common/decisions/JES_decisions.txt"))), "political_actions")
        self.assertTrue(self.eligibility.check(one(jes.children, "JES_move_capital_decision").get("allowed"), Country("JES")))

    def test_zypressen_category_and_continuation_remain_eligible(self):
        path = Path("common/decisions/categories/AVI_decision_categories.txt")
        category = one(read(effective(path)), "puppet_kingdoms_n_stuff")
        country = Country("AVI", government="fascism", focuses=frozenset({"a_zypressen_on_the_imperial_throne"}))
        self.assertTrue(self.eligibility.check(category.get("allowed"), country))
        self.assertTrue(self.eligibility.check(category.get("visible"), country))
        trees = read(MOD / "common/national_focus/AVI.txt")
        imports = {n.get("id"): [i.value for i in n.all("shared_focus")] for n in trees if n.key == "focus_tree"}
        self.assertIn("HSM_ZYP_victory_roll", imports["avian_fascists"])
        self.assertTrue(all("HSM_ZYP_victory_roll" not in roots for key, roots in imports.items() if key != "avian_fascists"))

    def test_delta_contract_rejects_missing_guards_wrong_tags_and_unrelated_changes(self):
        expected = expected_override(DECISIONS, self.upstream[DECISIONS])
        for kind in ("missing", "current_tag", "wrong_country", "unrelated_effect"):
            changed = copy.deepcopy(self.local[DECISIONS])
            entry = one(one(changed, "form_griffon_empire_category").children, "form_griffon_empire")
            exclusions = one(entry.get("allowed"), "NOT").children
            if kind == "missing":
                exclusions.pop(0)
            elif kind == "current_tag":
                exclusions[0].key = "tag"
            elif kind == "wrong_country":
                exclusions[0].value = "CYA"
            else:
                entry.get("complete_effect").append(Node("add_political_power", "=", "100"))
            with self.subTest(kind=kind):
                self.assertNotEqual(changed, expected)


if __name__ == "__main__":
    unittest.main(argv=[__file__, *BASE["REST"]], verbosity=2)
