"use strict";

// Deterministic script fixtures, not an HOI4 runtime. Facility placement and
// modifier caches refresh only on installation or an explicit force update.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "..");
const mod = path.join(root, "mod/HoISubmod");
function parse(text) {
    const tokens = text.replace(/^\uFEFF/, "").match(/"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}]|[<>!=]=?|[^\s{}=<>!#"]+/g)?.filter(t => !t.startsWith("#")) ?? [];
    let i = 0;
    function body(nested = false) {
        const out = [];
        while (i < tokens.length && tokens[i] !== "}") {
            const key = tokens[i++];
            if (!["=", ">", "<", ">=", "<="].includes(tokens[i])) { out.push({ key, value: null }); continue; }
            const op = tokens[i++]; let value = tokens[i++];
            assert.notEqual(value, undefined, "Missing value: " + key);
            if (value === "{") { value = body(true); assert.equal(tokens[i++], "}", "Unclosed " + key); }
            else if (value.startsWith('"')) value = JSON.parse(value);
            out.push({ key, op, value });
        }
        if (!nested) assert.equal(i, tokens.length, "Unexpected closing brace");
        return out;
    }
    return body();
}
const read = file => parse(fs.readFileSync(path.join(mod, file), "utf8"));
const prop = (body, key) => body.find(n => n.key === key)?.value;
function dictionary(body) {
    const out = {};
    for (const n of body) { assert.equal(out[n.key], undefined, "Duplicate definition " + n.key); out[n.key] = n.value; }
    return out;
}
const triggers = {};
for (const file of ["HSM_BAR_cases.txt", "HSM_BAR_anomalies.txt", "HSM_BAR_research_triggers.txt"]) Object.assign(triggers, dictionary(read("common/scripted_triggers/" + file)));
triggers.HSM_BAR_collegium_active = prop(read("common/scripted_triggers/HSM_BAR_collegium_triggers.txt"), "HSM_BAR_collegium_active");
assert(Array.isArray(triggers.HSM_BAR_collegium_active), "Missing Collegium lifecycle predicate");
const effects = {
    ...dictionary(read("common/scripted_effects/HSM_BAR_anomalies.txt")),
    ...dictionary(read("common/scripted_effects/HSM_BAR_cases.txt")),
    ...dictionary(read("common/scripted_effects/HSM_BAR_case_outcomes.txt")),
    ...dictionary(read("common/scripted_effects/HSM_BAR_service_rewards.txt"))
};
for (const [file, name] of [["HSM_BAR_core_effects.txt", "HSM_BAR_core_refresh"], ["HSM_BAR_collegium_effects.txt", "HSM_BAR_collegium_refresh"]]) {
    effects[name] = prop(read("common/scripted_effects/" + file), name);
    assert(Array.isArray(effects[name]), "Missing refresh effect " + name);
}
const dynamicModifiers = {};
for (const file of ["HSM_BAR_core.txt", "HSM_BAR_collegium_modifiers.txt", "HSM_BAR_anomalous_research.txt"]) {
    Object.assign(dynamicModifiers, dictionary(read("common/dynamic_modifiers/" + file)));
}
function number(value, s) {
    const literal = Number(value);
    if (Number.isFinite(literal)) return literal;
    assert(/^HSM_BAR_\w+$/.test(value), "Unsupported variable reference " + value);
    return s.vars[value] || 0;
}
function cacheModifier(name, s) {
    assert(dynamicModifiers[name], "Unsupported dynamic modifier " + name);
    s.modifierCache[name] = Object.fromEntries(dynamicModifiers[name]
        .filter(n => !["icon", "enable", "remove_trigger"].includes(n.key))
        .map(n => [n.key, number(n.value, s)]));
}
const projects = dictionary(read("common/special_projects/projects/HSM_BAR_cases.txt"));
const decisions = dictionary(prop(read("common/decisions/HSM_BAR_cases_studies.txt"), "HSM_BAR_cases_studies"));
const rumors = {};
for (const category of read("common/decisions/HSM_BAR_cases_rumors.txt")) Object.assign(rumors, dictionary(category.value));
const categories = dictionary(read("common/decisions/categories/HSM_BAR_cases.txt"));
const events = Object.fromEntries(read("events/HSM_BAR_cases.txt").filter(n => n.key === "country_event").map(n => [prop(n.value, "id"), n.value]));
const ids = Object.keys(projects).map(k => k.replace("HSM_BAR_project_case_", ""));
function world(dlc = false) {
    const countries = {};
    for (const id of ["BAR", "YAL", "DED", "CRY", "AAA"]) countries[id] = { id, originalTag: id, war: false, flags: new Set(), focuses: new Set(), ideas: new Set(), vars: {}, exists: true, capitulated: false, agency: false, pp: 200, events: [], bonuses: [], modifiers: new Set(), modifierCache: {}, modifierInstalls: {}, modifierUpdates: 0 };
    for (const f of ["active", "directorate", "service_founded", "field_research_open", "institute_open", "foreign_mandate"]) countries.BAR.flags.add("HSM_BAR_" + f);
    const states = {};
    for (const [id, owner, continent] of [[624,"BAR","asia"],[398,"YAL","asia"],[665,"YAL","asia"],[415,"DED","asia"],[344,"CRY","europe"],[900,"AAA","africa"]]) states[id] = { id: String(id), owner, controller: owner, continent, reactor: 0, facility: id === 624 ? 1 : 0 };
    return { countries, states, root: countries.BAR, from: countries.YAL, flags: new Set(), vars: {}, crowns: [], dlc: new Set(dlc ? ["Gotterdammerung", "La Resistance"] : []), failed: 0 };
}
function scope(key, w, stack) {
    if (key === "ROOT") return w.root;
    if (key === "FROM") return w.from;
    if (key === "THIS") return stack[0];
    if (/^PREV(?:\.PREV)*$/.test(key)) return stack[key.split(".").length];
    if (w.countries[key]) return w.countries[key];
    if (w.states[key]) return w.states[key];
    if (key.startsWith("var:")) {
        const name = key.slice(4), value = name.startsWith("global.") ? w.vars[name.slice(7)] : stack[0].vars[name];
        return w.states[value];
    }
}
function test(nodes, w, stack = [w.root]) {
    return nodes.every(n => {
        const s = stack[0], v = n.value; let answer;
        if (n.key === "AND") answer = test(v, w, stack);
        else if (n.key === "OR") answer = v.some(x => test([x], w, stack));
        else if (n.key === "NOT") answer = !v.some(x => test([x], w, stack));
        else if (n.key === "custom_trigger_tooltip") answer = test(v.filter(x => x.key !== "tooltip"), w, stack);
        else if (n.key === "has_country_flag") answer = s.flags.has(v);
        else if (n.key === "has_completed_focus") { assert.equal(typeof v, "string"); answer = s.focuses.has(v); }
        else if (n.key === "has_intelligence_agency") { assert(["yes", "no"].includes(v)); answer = s.agency === (v === "yes"); }
        else if (n.key === "has_dynamic_modifier") answer = s.modifiers.has(typeof v === "string" ? v : prop(v, "modifier"));
        else if (n.key === "has_global_flag") answer = w.flags.has(v);
        else if (n.key === "has_variable") answer = s.vars[v] !== undefined;
        else if (n.key === "has_dlc") { assert.equal(typeof v, "string", "Expected DLC name"); assert.equal(n.op, "="); answer = w.dlc.has(v); }
        else if (n.key === "tag") answer = s.id === scope(v, w, stack)?.id;
        else if (n.key === "original_tag") { assert.equal(typeof v, "string"); assert.equal(n.op, "="); answer = s.originalTag === v; }
        else if (n.key === "has_war") { assert(["yes", "no"].includes(v)); assert.equal(n.op, "="); answer = s.war === (v === "yes"); }
        else if (n.key === "exists") answer = s.exists === (v === "yes");
        else if (n.key === "has_capitulated") answer = s.capitulated === (v === "yes");
        else if (n.key === "controls_state") answer = w.states[v]?.controller === s.id;
        else if (n.key === "is_controlled_by") answer = s.controller === scope(v, w, stack)?.id;
        else if (n.key === "is_fully_controlled_by") answer = s.owner === scope(v, w, stack)?.id && s.controller === s.owner;
        else if (n.key === "is_on_continent") answer = s.continent === v;
        else if (["has_political_power", "nuclear_reactor", "magical_facility"].includes(n.key)) {
            const actual = s[{ has_political_power: "pp", nuclear_reactor: "reactor", magical_facility: "facility" }[n.key]];
            if (n.op === ">") answer = actual > Number(v);
            else if (n.op === "<") answer = actual < Number(v);
            else if (n.op === "=") answer = actual === Number(v);
            else throw Error("Unsupported comparison " + n.op);
        }
        else if (n.key === "any_country") answer = Object.values(w.countries).some(c => c.exists && test(v, w, [c, ...stack]));
        else if (n.key === "any_owned_state") answer = Object.values(w.states).some(c => c.owner === s.id && test(v, w, [c, ...stack]));
        else if (n.key === "any_of_scopes") {
            assert.equal(prop(v, "array"), "global.HSM_BAR_case_crowns");
            answer = w.crowns.some(c => test(v.filter(x => x.key !== "array"), w, [c, ...stack]));
        }
        else if (triggers[n.key]) answer = test(triggers[n.key], w, stack) === (v === "yes");
        else {
            const target = scope(n.key, w, stack);
            if (target) answer = test(v, w, [target, ...stack]);
            else if (n.key.startsWith("var:")) answer = false;
            else throw Error("Unsupported predicate " + n.key);
        }
        return answer;
    });
}
function run(nodes, w, stack = [w.root]) {
    for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i], s = stack[0], v = n.value;
        if (n.key === "if") {
            let taken = false;
            do {
                const branch = nodes[i];
                if (!taken && (branch.key === "else" || test(prop(branch.value, "limit"), w, stack))) { run(branch.value.filter(x => x.key !== "limit"), w, stack); taken = true; }
                if (!["else_if", "else"].includes(nodes[i + 1]?.key)) break;
                i++;
            } while (true);
        }
        else if (n.key === "set_country_flag") {
            if (Array.isArray(v)) {
                assert(v.every(x => ["flag", "days", "value"].includes(x.key)), "Unsupported flag metadata");
                assert.equal(typeof prop(v, "flag"), "string");
                s.flags.add(prop(v, "flag"));
            } else s.flags.add(v);
        }
        else if (n.key === "clr_country_flag") s.flags.delete(v);
        else if (n.key === "add_ideas" || n.key === "remove_ideas") {
            assert.equal(typeof v, "string");
            s.ideas[n.key === "add_ideas" ? "add" : "delete"](v);
        }
        else if (n.key === "create_intelligence_agency") {
            assert.deepEqual(v.map(x => x.key).sort(), ["icon", "name"]);
            assert(!s.agency, "Agency was recreated");
            s.agency = true;
            s.agencyDefinition = structuredClone(v);
        }
        else if (n.key === "load_focus_tree") {
            assert.deepEqual(v.map(x => x.key).sort(), ["keep_completed", "tree"]);
            assert.equal(prop(v, "keep_completed"), "yes", "Fixture supports preserved focus progress only");
            s.tree = prop(v, "tree");
        }
        else if (n.key === "remove_opinion_modifier") {
            assert.deepEqual(v.map(x => x.key).sort(), ["modifier", "target"]);
            assert(s.opinions instanceof Set, "Missing opinion state");
            s.opinions.delete(prop(v, "target") + ":" + prop(v, "modifier"));
        }
        else if (n.key === "add_political_power") s.pp += Number(v);
        else if (n.key === "add_tech_bonus") s.bonuses.push(JSON.stringify(v));
        else if (n.key === "country_event") s.events.push(prop(v, "id"));
        else if (["set_variable", "add_to_variable", "subtract_from_variable", "multiply_variable"].includes(n.key)) {
            assert.equal(v.length, 1, "Expected one variable assignment");
            const entry = v[0], amount = number(entry.value, s), before = number(entry.key, s);
            const result = n.key === "set_variable" ? amount : n.key === "add_to_variable" ? before + amount : n.key === "subtract_from_variable" ? before - amount : before * amount;
            s.vars[entry.key] = result;
        }
        else if (n.key === "clear_variable") {
            assert.equal(typeof v, "string", "Expected scalar variable name");
            assert(/^HSM_BAR_\w+$/.test(v), "Unsupported variable name " + v);
            delete s.vars[v];
        }
        else if (n.key === "clamp_variable") {
            const name = prop(v, "var"), value = Math.min(number(prop(v, "max"), s), Math.max(number(prop(v, "min"), s), number(name, s)));
            s.vars[name] = value;
        }
        else if (n.key === "add_dynamic_modifier") {
            assert.deepEqual(v.map(x => x.key), ["modifier"]);
            const name = prop(v, "modifier");
            cacheModifier(name, s);
            s.modifiers.add(name);
            s.modifierInstalls[name] = (s.modifierInstalls[name] || 0) + 1;
        }
        else if (n.key === "remove_dynamic_modifier") {
            assert.deepEqual(v.map(x => x.key), ["modifier"]);
            const name = prop(v, "modifier");
            s.modifiers.delete(name);
            delete s.modifierCache[name];
        }
        else if (n.key === "force_update_dynamic_modifier") {
            assert.equal(v, "yes");
            for (const name of s.modifiers) cacheModifier(name, s);
            s.modifierUpdates++;
        }
        // Native world-state observation has its own full registry regression suite.
        // It does not grant field-investigation flags or complete laboratory studies.
        else if (n.key === "HSM_BAR_anomalies_pulse") continue;
        else if (n.key === "hidden_effect") run(v, w, stack);
        else if (n.key === "HSM_BAR_case_failed") w.failed++;
        else if (n.key === "custom_effect_tooltip") continue;
        else if (n.key === "for_each_scope_loop") {
            assert.equal(prop(v, "array"), "global.HSM_BAR_case_crowns");
            for (const c of w.crowns) run(v.filter(x => x.key !== "array"), w, [c, ...stack]);
        }
        else if (effects[n.key]) run(effects[n.key], w, stack);
        else {
            const target = scope(n.key, w, stack);
            if (target) run(v, w, [target, ...stack]);
            else throw Error("Unsupported effect " + n.key);
        }
    }
}
const flag = (w, ...f) => f.forEach(k => w.root.flags.add("HSM_BAR_" + k));
const has = (w, f) => w.root.flags.has("HSM_BAR_" + f);
const valid = (id, w, country = w.root) => test(triggers[id], w, [country]);
const effect = (id, w) => run(effects[id], w);
function access(w, id) {
    flag(w, "case_" + id + "_known", "case_" + id + "_investigated");
    if (["chalice", "phylactery", "darkheart"].includes(id)) { w.flags.add("HSM_BAR_case_" + id + "_secured"); w.vars["HSM_BAR_case_" + id + "_site"] = "624"; }
    if (id === "reactor") w.states[624].reactor = 1;
    if (id === "crown") { const c = w.countries.AAA; c.flags.add("HSM_BAR_case_crown_secured"); c.vars.HSM_BAR_case_crown_site = "624"; w.crowns.push(c); }
}
module.exports = { parse, read, dictionary, prop, world, access, flag, has, valid, effect, test, run, effects, triggers, projects, decisions, events, ids, mod };
if (require.main === module) {
const costs = { rock:15,titan:20,entity:25,amulet:15,plants:15,reactor:30,crown:25,chalice:20,phylactery:25,darkheart:30,grover:15,rosa:15,herald:20,sombra:20,echo:10,marsh:10,compass:10 };
let passed = 0, failed = 0;
function scenario(name, fn) { try { fn(); passed++; console.log("PASS: " + name); } catch (e) { failed++; console.error("FAIL: " + name + "\n" + e.stack); } }
scenario("17 distinct case projects, no accidental replacement of plants by reactor", () => {
    assert.equal(ids.length, 17); assert(ids.includes("plants") && ids.includes("reactor"));
    for (const id of ids) assert(events["hsm_bar_cases." + (ids.indexOf(id) + 1)]);
});
scenario("focus flags cannot substitute for completed studies", () => {
    const w = world(); flag(w, "project_wards_done", "project_containment_done", "project_forensics_done", "normalization", "suppression_authorized");
    for (const key of ["HSM_BAR_case_review_ready", "HSM_BAR_containment_knowledge_ready", "HSM_BAR_forensics_knowledge_ready", "HSM_BAR_suppression_knowledge_ready", "HSM_BAR_research_suppression_eligible"]) assert(!valid(key, w), key);
});
scenario("Collegium lifecycle fields are explicit and unknown predicates remain rejected", () => {
    const w = world();
    assert(test(parse("original_tag = BAR has_war = no"), w));
    w.root.id = "AAA"; w.root.war = true;
    assert(test(parse("original_tag = BAR has_war = yes"), w));
    assert(!test(parse("original_tag = AAA"), w));
    assert(!test(parse("has_war = no"), w));
    assert.throws(() => test(parse("has_war = maybe"), w));
    assert.throws(() => test(parse("original_tag = { tag = BAR }"), w));
    assert.throws(() => test(parse("unsupported_collegium_predicate = yes"), w), /Unsupported predicate/);
});
scenario("local evidence ladder is reachable without any foreign event", () => {
    const w = world();
    for (const id of ["rock", "entity", "echo", "titan", "compass", "amulet"]) { access(w, id); effect("HSM_BAR_cases_" + id + "_complete", w); }
    assert(valid("HSM_BAR_suppression_knowledge_ready", w));
    assert(!valid("HSM_BAR_research_suppression_eligible", w));
    flag(w, "normalization", "project_forensics_done", "suppression_authorized");
    assert(valid("HSM_BAR_research_suppression_eligible", w));
    assert.equal(w.flags.size, 0);
});
scenario("fresh Service reaches the ladder through actual survey, fieldwork and study callbacks", () => {
    const w = world(); flag(w, "region_local_open");
    assert.equal(w.flags.size, 0);
    assert(![...w.root.flags].some(f => /_studied|_investigated|_done|_closed|barrad_.*_alive/.test(f)));
    effect("HSM_BAR_case_local_survey", w);
    for (const id of ["rock", "titan", "entity", "amulet"]) {
        assert(has(w, "case_" + id + "_known"));
        effect("HSM_BAR_case_investigate_" + id, w);
        assert(has(w, "case_" + id + "_investigated"));
        effect("HSM_BAR_cases_" + id + "_complete", w);
    }
    for (const id of ["echo", "compass"]) {
        effect("HSM_BAR_cases_" + id + "_rumor_complete", w);
        effect("HSM_BAR_cases_" + id + "_complete", w);
    }
    effect("HSM_BAR_cases_echo_reserve", w);
    assert(valid("HSM_BAR_case_review_ready", w));
    assert(valid("HSM_BAR_suppression_knowledge_ready", w));
    assert.equal(w.flags.size, 0, "Foreign or conditional native outcome was required");
    assert.equal(w.states[624].reactor, 0, "An operating reactor was required");
});
scenario("legacy case closure cannot strand mandatory fieldwork or subsequent studies", () => {
    const w = world(); flag(w, "region_local_open"); effect("HSM_BAR_case_local_survey", w);
    for (const id of ["rock", "titan", "entity", "amulet"]) {
        flag(w, "case_" + id + "_closed");
        effect("HSM_BAR_case_investigate_" + id, w);
        effect("HSM_BAR_cases_" + id + "_complete", w);
        assert(has(w, "study_" + id + "_done"), id);
    }
});
scenario("legacy physical dispositions require completed studies and still recheck site access", () => {
    const original = dictionary(prop(read("common/decisions/HSM_BAR_anomalies.txt"), "HSM_BAR_anomalies"));
    for (const id of ["rock", "titan", "entity", "amulet", "plants"]) {
        for (const mode of ["protect", "restrict"]) {
            const w = world(); flag(w, "region_local_open", "case_" + id + "_investigated", "project_wards_done", "project_containment_done", mode === "protect" ? "coexistence" : "normalization");
            const gate = prop(original["HSM_BAR_case_" + id + "_" + mode], "available");
            assert(!test(gate, w)); effect("HSM_BAR_case_dispose_" + id + "_" + mode, w); assert(!has(w, "case_" + id + "_closed"));
            flag(w, "study_" + id + "_done"); assert(test(gate, w));
            w.states[624].controller = "YAL"; assert(!test(gate, w));
            effect("HSM_BAR_case_dispose_" + id + "_" + mode, w); assert(!has(w, "case_" + id + "_closed"));
        }
    }
});
scenario("each mandatory study is necessary and unrelated studies do not substitute", () => {
    for (const missing of ["rock", "entity", "echo", "titan", "compass", "amulet"]) {
        const w = world(); for (const id of ids.filter(x => x !== missing)) flag(w, "study_" + id + "_done");
        assert(!valid("HSM_BAR_suppression_knowledge_ready", w), missing);
    }
});
scenario("every research tier rejects focus-only progress, even with its generic predecessor done", () => {
    for (const [tier, predecessor] of [["wards",null],["containment","wards"],["forensics","containment"],["suppression","forensics"]]) {
        const w = world(); flag(w, "normalization", "suppression_authorized");
        if (predecessor) flag(w, "project_" + predecessor + "_done");
        assert(!valid("HSM_BAR_research_" + tier + "_eligible", w), tier);
        for (const id of ["rock","entity","echo","titan","compass","amulet"]) flag(w, "study_" + id + "_done");
        assert(valid("HSM_BAR_research_" + tier + "_eligible", w), tier);
    }
});
scenario("doctrine review requires a resolved mundane file", () => {
    const w = world(); flag(w, "study_rock_done", "study_echo_done");
    assert(!valid("HSM_BAR_case_review_ready", w)); effect("HSM_BAR_cases_echo_reserve", w);
    assert(valid("HSM_BAR_case_review_ready", w)); assert(!valid("HSM_BAR_containment_knowledge_ready", w));
});
scenario("Collegium wards retain their original eligibility", () => {
    const w = world(); w.root.flags.delete("HSM_BAR_directorate"); flag(w, "collegium");
    assert(valid("HSM_BAR_research_wards_eligible", w));
    assert(!valid("HSM_BAR_research_containment_eligible", w));
});
scenario("normalization permission and completed forensics remain separate requirements", () => {
    for (const missing of ["normalization", "project_forensics_done", "suppression_authorized"]) {
        const w = world(); for (const id of ids) flag(w, "study_" + id + "_done");
        for (const f of ["normalization", "project_forensics_done", "suppression_authorized"].filter(x => x !== missing)) flag(w, f);
        assert(!valid("HSM_BAR_research_suppression_eligible", w), missing);
    }
});
scenario("all native and fallback outputs execute the same guarded case completion", () => {
    for (const id of ids) {
        const native = world(true), fallback = world(false); access(native, id); access(fallback, id);
        const output = prop(prop(projects["HSM_BAR_project_case_" + id], "project_output"), "country_effects");
        assert.deepEqual(output, prop(decisions["HSM_BAR_study_" + id], "remove_effect"));
        run(output, native); run(prop(decisions["HSM_BAR_study_" + id], "remove_effect"), fallback);
        assert(has(native, "study_" + id + "_done")); assert.deepEqual(native.root.events, fallback.root.events);
        effect("HSM_BAR_cases_" + id + "_apply", native); effect("HSM_BAR_cases_" + id + "_apply", fallback);
        assert.deepEqual(native.root.bonuses, fallback.root.bonuses); assert.equal(native.root.pp, fallback.root.pp);
    }
});
scenario("a checked rumor or known name alone cannot complete any case study", () => {
    for (const id of ids) {
        const w = world(); flag(w, "case_" + id + "_rumor", "case_" + id + "_known");
        effect("HSM_BAR_cases_" + id + "_complete", w);
        assert(!has(w, "study_" + id + "_done"), id);
        assert.equal(w.root.events.length, 0); assert.equal(w.root.bonuses.length, 0);
    }
});
scenario("premature, replayed and cross-choice rewards are impossible for every study", () => {
    for (const id of ids) {
        const w = world(); access(w, id);
        effect("HSM_BAR_cases_" + id + "_apply", w); assert.equal(w.root.bonuses.length, 0);
        effect("HSM_BAR_cases_" + id + "_complete", w); effect("HSM_BAR_cases_" + id + "_complete", w);
        assert.equal(w.root.events.length, 1);
        effect("HSM_BAR_cases_" + id + "_apply", w); effect("HSM_BAR_cases_" + id + "_apply", w); effect("HSM_BAR_cases_" + id + "_reserve", w);
        assert.equal(w.root.bonuses.length, 0); assert.equal(w.root.pp, 200 - costs[id]); assert(!Object.hasOwn(w.root.vars, "HSM_BAR_cover_integrity"));
        assert(has(w, "study_" + id + "_applied")); assert(w.root.modifiers.has("HSM_BAR_anomalous_research"));
    }
});
scenario("reserved results cannot later be cashed in; deferred results can", () => {
    for (const id of ids) {
        const w = world(); access(w, id); effect("HSM_BAR_cases_" + id + "_complete", w);
        effect("HSM_BAR_cases_" + id + "_reserve", w); effect("HSM_BAR_cases_" + id + "_reserve", w); effect("HSM_BAR_cases_" + id + "_apply", w);
        assert(!Object.hasOwn(w.root.vars, "HSM_BAR_cover_integrity")); assert.equal(w.root.bonuses.length, 0); assert.equal(w.root.pp, 200);
    }
});
scenario("lost site, vault, reactor or facility grants no study and permits guarded retry", () => {
    for (const id of ["rock", "titan", "entity", "amulet", "plants", "reactor", "crown", "chalice", "phylactery", "darkheart"]) {
        const w = world(true); access(w, id); w.states[624].controller = "YAL";
        effect("HSM_BAR_cases_" + id + "_complete", w); assert(!has(w, "study_" + id + "_done")); assert(has(w, "study_" + id + "_retry"));
        w.states[624].controller = "BAR"; assert(test(prop(decisions["HSM_BAR_study_" + id], "visible"), w));
        effect("HSM_BAR_cases_" + id + "_complete", w); assert(has(w, "study_" + id + "_done")); assert(!has(w, "study_" + id + "_retry"));
    }
});
scenario("physical application rechecks custody; acquired documents remain readable", () => {
    const w = world(); access(w, "chalice"); effect("HSM_BAR_cases_chalice_complete", w); w.states[624].controller = "YAL";
    effect("HSM_BAR_cases_chalice_apply", w); assert.equal(w.root.bonuses.length, 0);
    assert(has(w, "study_chalice_done")); effect("HSM_BAR_cases_chalice_reserve", w); assert(has(w, "study_chalice_reserved"));
    access(w, "rosa"); assert(valid("HSM_BAR_cases_rosa_eligible", w));
});
scenario("no research rewards after capitulation, route loss or institute closure", () => {
    for (const loss of ["capitulated", "active", "directorate", "service_founded", "institute_open"]) {
        const w = world(); access(w, "echo"); if (loss === "capitulated") w.root.capitulated = true; else w.root.flags.delete("HSM_BAR_" + loss);
        effect("HSM_BAR_cases_echo_complete", w); assert(!has(w, "study_echo_done")); assert.equal(w.root.bonuses.length, 0);
    }
});
scenario("regional gates block premature mundane fieldwork and protect once-only results", () => {
    for (const [id, region] of [["echo","local"],["compass","local"],["marsh","riverlands"]]) {
        const w = world(); effect("HSM_BAR_cases_" + id + "_rumor_complete", w); assert(!has(w, "case_" + id + "_known"));
        flag(w, "region_" + region + "_open"); effect("HSM_BAR_cases_" + id + "_rumor_complete", w);
        assert(has(w, "case_" + id + "_investigated")); assert(!has(w, "study_" + id + "_done"));
        assert(!valid("HSM_BAR_cases_" + id + "_rumor_available", w));
    }
});
scenario("regional mandate alone cannot expose every country as an intelligence target", () => {
    const w = world(); w.from = w.countries.CRY;
    assert(!valid("HSM_BAR_operation_recon_target", w, w.from));
    w.flags.add("HSM_BAR_case_sombra_returned"); assert(!valid("HSM_BAR_operation_recon_target", w, w.from));
    flag(w, "region_equus_open"); assert(!valid("HSM_BAR_operation_recon_target", w, w.from));
    effect("HSM_BAR_cases_sombra_rumor_complete", w); assert(valid("HSM_BAR_operation_recon_target", w, w.from));
    w.flags.clear(); assert(!valid("HSM_BAR_operation_recon_target", w, w.from));
});
scenario("crown rumor checks follow physical region and keep independent instances", () => {
    const w = world(); const a = w.countries.AAA, c = w.countries.CRY;
    for (const [holder, site] of [[a,"900"],[c,"344"]]) { holder.flags.add("HSM_BAR_case_crown_exists"); holder.vars.HSM_BAR_case_crown_site = site; w.crowns.push(holder); }
    flag(w, "region_equus_open"); effect("HSM_BAR_cases_crown_equus_rumor_complete", w);
    assert(c.flags.has("HSM_BAR_case_crown_rumor")); assert(!a.flags.has("HSM_BAR_case_crown_rumor"));
    flag(w, "region_zebrica_open"); effect("HSM_BAR_cases_crown_zebrica_rumor_complete", w); assert(a.flags.has("HSM_BAR_case_crown_rumor"));
});
scenario("reactor inquiry requires an actual reactor and an intact local site", () => {
    const w = world(); flag(w, "region_local_open"); assert(!valid("HSM_BAR_cases_reactor_rumor_available", w));
    w.states[624].reactor = 1; effect("HSM_BAR_cases_reactor_rumor_complete", w); assert(has(w, "case_reactor_investigated"));
    w.states[624].reactor = 0; effect("HSM_BAR_cases_reactor_complete", w); assert(!has(w, "study_reactor_done"));
});
scenario("Zebrica's empty lead awards neither magical knowledge nor farmable benefits", () => {
    const w = world(); flag(w, "region_zebrica_open"); effect("HSM_BAR_cases_zebrica_rumor_complete", w); effect("HSM_BAR_cases_zebrica_rumor_complete", w);
    assert(has(w, "case_zebrica_inconclusive")); assert(has(w, "case_zebrica_closed")); assert.equal(w.root.events.length, 1);
    assert.equal(w.root.bonuses.length, 0); assert.equal(w.root.pp, 200); assert(!valid("HSM_BAR_containment_knowledge_ready", w));
});
scenario("all regional categories have real decisions and both languages cover every new UI key", () => {
    const loc = {};
    for (const language of ["english", "russian"]) {
        const bytes = fs.readFileSync(path.join(mod, "localisation", language, "HSM_BAR_cases_l_" + language + ".yml"));
        assert.equal(bytes.subarray(0, 3).toString("hex"), "efbbbf");
        const lines = bytes.toString("utf8").split(/\r?\n/); loc[language] = new Map();
        for (const line of lines.slice(1).filter(x => x.trim())) { const m = line.match(/^ ([^ :]+):0 "(.*)"$/); assert(m, line); assert(!loc[language].has(m[1]), m[1]); loc[language].set(m[1], m[2]); }
    }
    assert.deepEqual([...loc.english.keys()].sort(), [...loc.russian.keys()].sort());
    for (const language of ["english","russian"]) {
        for (const region of ["local","equus","griffonia","north","riverlands","zebrica"]) assert(loc[language].has("HSM_BAR_region_" + region + "_open"));
        assert(loc[language].has("HSM_BAR_cases_review_ready_tt"));
        for (const [key, value] of loc[language]) if (key.endsWith("_desc") || /^hsm_bar_cases\.\d+\.d$/.test(key)) assert(!/native incident|native ritual|authored investigation|in this campaign|в этой кампании|из исходного сюжета/i.test(value), key);
    }
    for (const key of [...Object.keys(projects), ...Object.keys(decisions), ...Object.keys(rumors), ...Object.keys(categories)]) assert(loc.english.has(key), "Missing localization: " + key);
    for (const region of ["local", "equus", "griffonia", "north", "riverlands", "zebrica"]) assert(prop(read("common/decisions/HSM_BAR_cases_rumors.txt"), "HSM_BAR_cases_" + region)?.length > 0, region);
});
scenario("study files use concrete helpers and never grant fabricated bodies or leaders", () => {
    const code = fs.readFileSync(path.join(mod, "common/scripted_effects/HSM_BAR_cases.txt"), "utf8");
    assert(!/\$[A-Z_]+\$|recruit_character|create_country_leader|transfer_state|kill_country_leader|set_global_flag/.test(code));
    for (const id of ids) { assert.equal(prop(projects["HSM_BAR_project_case_" + id], "specialization"), "specialization_magical"); assert(effects["HSM_BAR_cases_" + id + "_complete"]); }
});
scenario("obsolete political_power predicate is rejected, not interpreted as a valid trigger", () => {
    assert.throws(() => test(parse("political_power > 14"), world()), /Unsupported predicate political_power/);
    assert(test(parse("has_political_power > 14"), world()));
    for (const f of ["common/scripted_effects/HSM_BAR_cases.txt","events/HSM_BAR_cases.txt","common/decisions/HSM_BAR_cases_studies.txt"]) assert(!/\\bpolitical_power\\s*[=<>]/.test(fs.readFileSync(path.join(mod,f),"utf8")), f);
});
console.log(`Barrad case progression: ${passed} scenarios passed; ${failed} failed.`);
console.log("Boundary: deterministic script execution; in-game GUI, project scheduling and spy timing still require a playtest.");
process.exitCode = failed ? 1 : 0;

}
