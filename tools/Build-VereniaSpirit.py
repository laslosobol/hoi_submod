"""Generate Verenia's modifier ledger and mechanically route its idea operations.

The original idea definitions remain the single source of modifier values and
native tooltips. No source ideas, timed programmes or development laws are edited.
Run --check to detect stale generated files or unconverted script operations.
"""
from __future__ import annotations

import argparse
import re
import runpy
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod/HoISubmod"
API = runpy.run_path(str(Path(__file__).with_name("Test-Verenia.py")))
EAW = API["OPT"].eaw
read = API["read"]
PREFIX = "HSM_VER_SP_"
SOURCES = (
    "HSM_ERI_development", "HSM_EYR_development", "HSM_VER_identity",
    "HSM_VER_erie_force", "HSM_VER_eyrie_force", "HSM_VER_eyrie",
    "HSM_VER_avian", "HSM_VER_diplomacy", "HSM_VER_unification",
    "HSM_VER_commonwealth", "HSM_VER_grover",
)
EXCLUDE = {
    "HSM_VER_frontier_inspections", "HSM_VER_petition_commitments",
    "HSM_VER_peace_dividend", "HSM_VER_UNI_customs_spirit",
    "HSM_VER_UNI_works_spirit", "HSM_VER_UNI_administration_spirit",
    "HSM_VER_UNI_command_spirit",
    "HSM_VER_GRO_guardianship", "HSM_VER_GRO_transition",
    "HSM_VER_GRO_open_court_legacy", "HSM_VER_GRO_managed_court_legacy",
    "HSM_VER_GRO_rule_of_law", "HSM_VER_GRO_patrons_legacy",
}
NATIVE = (
    "AVI_econcoop", "AVI_common_markets", "AVI_studentexchange",
    "AVI_relaxd_citizenship", "AVI_unified_intelligence_agency",
    "AVI_unified_intelligence_agency_lar", "AVI_annual_military_exercises",
    "AVI_the_strong_arm_of_the_revolution", "AVI_Kriegsamt",
    "AVI_socialist_economics", "AVI_Wirtschaftsministerium",
    "AVI_long_arm_of_the_revolution", "AVI_long_arm_of_the_revolution_lar",
    "AVI_Evidenzbureau", "AVI_Evidenzbureau_lar",
)
# Later ranks replace earlier ones, never stack with their predecessors.
FAMILIES = (
    ("AVI_econcoop", "AVI_common_markets", "AVI_socialist_economics", "AVI_Wirtschaftsministerium"),
    ("AVI_annual_military_exercises", "AVI_the_strong_arm_of_the_revolution", "AVI_Kriegsamt"),
    ("AVI_unified_intelligence_agency", "AVI_unified_intelligence_agency_lar",
     "AVI_long_arm_of_the_revolution", "AVI_long_arm_of_the_revolution_lar",
     "AVI_Evidenzbureau", "AVI_Evidenzbureau_lar"),
    ("HSM_VER_UNI_constitutional_state", "HSM_VER_UNI_settled_state"),
    ("HSM_ERI_DEV_reconstruction_service", "HSM_ERI_DEV_public_services"),
    ("HSM_ERI_DEV_officer_corps", "HSM_ERI_DEV_integrated_staff"),
    ("HSM_EYR_DEV_observer_sections", "HSM_EYR_DEV_coordinated_signals"),
)


def components():
    result = {}
    for name in SOURCES:
        country = read(MOD / f"common/ideas/{name}.txt")[0].all("country")[0]
        result.update((n.key, n) for n in country.children if n.key not in EXCLUDE)
    native = read(EAW / "common/ideas/zzz_AVI_ideas.txt")[0].all("country")[0]
    result.update((n.key, n) for n in native.children if n.key in NATIVE)
    assert set(NATIVE) <= result.keys()
    for name, node in result.items():
        assert node.get("modifier"), name
        assert not any(node.get(k) for k in ("research_bonus", "equipment_bonus", "targeted_modifier", "on_add", "on_remove")), name
        assert all(not n.children and float(n.value) == float(n.value) for n in node.get("modifier")), name
    return result


def flag(name):
    return PREFIX + "owned_" + name


def call(action, name):
    return PREFIX + action + "_" + name


def emit(nodes):
    return " ".join(f"{n.key} {n.op} {{ {emit(n.children)} }}" if n.children else f"{n.key} {n.op} {n.value}" for n in nodes)


@dataclass
class Span:
    key: str
    value: str
    start: int
    end: int
    children: list


def spans(text):
    """Parse token spans so mechanical edits preserve surrounding layout/comments."""
    tokens = [m for m in API["TOKEN"].finditer(text) if not m[0].isspace() and not m[0].startswith("#")]
    pos = 0

    def block(nested=False):
        nonlocal pos
        result = []
        while pos < len(tokens):
            key = tokens[pos]
            pos += 1
            if key[0] == "}":
                assert nested
                return result, key.end()
            value, children, end = "", [], key.end()
            if pos < len(tokens) and tokens[pos][0] in ("=", "<", ">", "<=", ">=", "!="):
                pos += 1
                token = tokens[pos]
                pos += 1
                if token[0] == "{":
                    children, end = block(True)
                else:
                    value, end = token[0].strip('"'), token.end()
            result.append(Span(key[0], value, key.start(), end, children))
        assert not nested
        return result, len(text)

    return block()[0]


def route(text, names):
    edits = []

    def visit(nodes, display=False):
        for node in nodes:
            if node.key in ("effect_tooltip", "show_ideas_tooltip", "ai_will_do", "ai_chance"):
                # AI checks must still see consolidated components, unlike previews.
                if node.key in ("effect_tooltip", "show_ideas_tooltip"):
                    continue
            if node.key in ("add_ideas", "remove_ideas", "has_idea") and node.value in names:
                action = {"add_ideas": "add", "remove_ideas": "remove", "has_idea": "has"}[node.key]
                edits.append((node.start, node.end, f"{call(action, node.value)} = yes"))
            elif node.key == "swap_ideas":
                pair = {n.key: n.value for n in node.children}
                if names.intersection(pair.values()):
                    actual = []
                    for key, action in (("remove_idea", "remove"), ("add_idea", "add")):
                        name = pair.get(key)
                        if name:
                            actual.append(f"{call(action, name)} = yes" if name in names else f"{action}_ideas = {name}")
                    old = text[node.start:node.end]
                    edits.append((node.start, node.end, f"effect_tooltip = {{ {old} }} hidden_effect = {{ {' '.join(actual)} }}"))
                else:
                    visit(node.children)
            elif node.key in ("add_ideas", "remove_ideas") and node.children:
                assert not names.intersection(n.key for n in node.children), "Handle multi-idea operations explicitly"
            else:
                visit(node.children)

    visit(spans(text))
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    return text


def generated(data):
    header = "# Generated by tools/Build-VereniaSpirit.py; modifier values come from source ideas.\n"
    # Engine modifier names are case-insensitive; variable names are our own.
    modifiers = sorted({n.key.lower() for idea in data.values() for n in idea.get("modifier")})
    dynamic = header + "HSM_VER_SP_united_verenia = {\n\ticon = GFX_idea_HSM_VER_SP_united_verenia\n\tenable = { HSM_VER_SP_active = yes }\n"
    dynamic += "".join(f"\t{key} = HSM_VER_SP_value_{key}\n" for key in modifiers) + "}\n"
    triggers = header + "HSM_VER_SP_active = { HSM_VER_UNI_house = yes exists = yes has_country_flag = HSM_VER_UNI_founded }\n"
    effects = header
    for name in data:
        triggers += f"{call('has', name)} = {{ custom_trigger_tooltip = {{ tooltip = {call('has', name)}_tt OR = {{ has_idea = {name} has_country_flag = {flag(name)} }} }} }}\n"
        effects += f"""
{call('add', name)} = {{
 show_ideas_tooltip = {name}
 hidden_effect = {{
  if = {{
   limit = {{ HSM_VER_SP_active = yes }}
   set_country_flag = {flag(name)}
   remove_ideas = {name}
   HSM_VER_SP_refresh = yes
  }}
  else = {{ add_ideas = {name} }}
 }}
}}
{call('remove', name)} = {{
 effect_tooltip = {{ remove_ideas = {name} }}
 hidden_effect = {{
  if = {{
   limit = {{ OR = {{ has_idea = {name} has_country_flag = {flag(name)} }} }}
   remove_ideas = {name}
   clr_country_flag = {flag(name)}
   HSM_VER_SP_refresh = yes
  }}
 }}
}}
"""
    effects += "\nHSM_VER_SP_capture = {\n"
    for name in data:
        effects += f" if = {{ limit = {{ has_idea = {name} }} set_country_flag = {flag(name)} remove_ideas = {name} }}\n"
    effects += "}\n\nHSM_VER_SP_normalize = {\n"
    for family in FAMILIES:
        for i in range(len(family) - 1, 0, -1):
            high = family[i]
            effects += f" if = {{ limit = {{ has_country_flag = {flag(high)} }}\n"
            for low in family[:i]:
                effects += f"  clr_country_flag = {flag(low)}\n  remove_ideas = {low}\n"
            effects += " }\n"
    effects += "}\n\nHSM_VER_SP_normalize_native_ideas = {\n"
    # Defeated Avian can be integrated before the common state is proclaimed.
    # Its upgraded programmes must also replace the recipient's raw older ideas.
    for family in FAMILIES:
        if not all(name in NATIVE for name in family):
            continue
        for i in range(len(family) - 1, 0, -1):
            effects += f" if = {{ limit = {{ has_idea = {family[i]} }}\n"
            for low in family[:i]:
                effects += f"  remove_ideas = {low}\n"
            effects += " }\n"
    effects += "}\n\nHSM_VER_SP_cancel_invalid = {\n"
    for name, idea in data.items():
        if idea.get("cancel") and name != "HSM_AVI_common_budget":
            effects += f" if = {{ limit = {{ has_country_flag = {flag(name)} {emit(idea.get('cancel'))} }} clr_country_flag = {flag(name)} }}\n"
    effects += "}\n\nHSM_VER_SP_recalculate = {\n"
    for key in modifiers:
        effects += f" set_variable = {{ HSM_VER_SP_value_{key} = 0 }}\n"
    for name, idea in data.items():
        effects += f" if = {{ limit = {{ has_country_flag = {flag(name)} }}\n"
        for n in idea.get("modifier"):
            effects += f"  add_to_variable = {{ HSM_VER_SP_value_{n.key.lower()} = {n.value} }}\n"
        effects += " }\n"
    effects += "}\n"
    # Read actual possession before annexation, not merely completed focus history.
    effects += "\nHSM_VER_SP_inherit_avian = {\n if = { limit = { OR = { tag = ERI tag = EYR } }\n"
    for name in NATIVE:
        effects += f"  if = {{ limit = {{ AVI = {{ {call('has', name)} = yes }} }} {call('add', name)} = yes }}\n"
    effects += "  if = { limit = { NOT = { HSM_VER_SP_active = yes } } HSM_VER_SP_normalize_native_ideas = yes }\n"
    effects += "  set_country_flag = HSM_VER_SP_avian_imported\n }\n}\n"
    result = {
        "common/dynamic_modifiers/HSM_VER_spirit.txt": dynamic,
        "common/scripted_triggers/HSM_VER_spirit.txt": triggers,
        "common/scripted_effects/HSM_VER_spirit_components.txt": effects,
    }
    for lang in ("english", "russian"):
        loc = "\ufeffl_" + lang + ":\n"
        for name in data:
            value = f"Действует «${name}$»." if lang == "russian" else f"${name}$ is in force."
            loc += f' {call("has", name)}_tt:0 "{value}"\n'
        result[f"localisation/{lang}/HSM_VER_spirit_components_l_{lang}.yml"] = loc
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--eaw", type=Path, default=EAW)
    opt = parser.parse_args()
    data = components()
    changed = []
    outputs = {MOD / name: value for name, value in generated(data).items()}
    for folder in ("common/national_focus", "common/scripted_effects", "common/scripted_triggers", "common/on_actions", "common/decisions", "events"):
        for path in (MOD / folder).rglob("*.txt"):
            if path.name.startswith(("HSM_VER", "HSM_ERI", "HSM_EYR")) or path.name in ("AVI.txt", "Avian Events.txt"):
                if "spirit" not in path.name:
                    outputs[path] = route(path.read_text(encoding="utf-8-sig"), set(data))
    for path, text in outputs.items():
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old == text:
            continue
        changed.append(str(path.relative_to(ROOT)))
        if not opt.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    print(f"{len(data)} components, {len(changed)} {'stale' if opt.check else 'updated'} files")
    for name in changed:
        print(name)
    if opt.check and changed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
