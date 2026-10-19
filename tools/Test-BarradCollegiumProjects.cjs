"use strict";

// Self-contained Clausewitz fixtures executing the emitted scripts, not an HOI4 runtime.
// node tools/Test-BarradCollegiumProjects.cjs [--native] [--game-root PATH] [--eaw-root PATH]
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const B = require("./Build-BarradCollegiumProjects.cjs");
const { projects, departments, factories, modifiers, variable, prefix: P } = B;
const mod = path.resolve(__dirname, "../mod/HoISubmod");
const read = file => fs.readFileSync(path.join(mod, file), "utf8");
// Keep duplicate keys, scope nesting and comparison operators; fail on unknown syntax.
function parse(text) {
    const tokens = text.replace(/^\uFEFF/, "").match(/"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}]|[<>!=]=?|[^\s{}=<>!#"]+/g)?.filter(t => !t.startsWith("#")) || [];
    let cursor = 0;
    function body(nested = false) {
        const out = [];
        while (cursor < tokens.length && tokens[cursor] !== "}") {
            const key = tokens[cursor++], op = tokens[cursor++], token = tokens[cursor++];
            assert(["=", "<", ">", "<=", ">=", "!="].includes(op), `Bad operator ${key} ${op}`);
            assert(token && token !== "}", `Missing value for ${key}`);
            const value = token === "{" ? body(true) : token.startsWith('"') ? JSON.parse(token) : token;
            out.push({ key, op, value });
        }
        if (nested) assert.equal(tokens[cursor++], "}", "Unclosed block");
        return out;
    }
    const nodes = body();
    assert.equal(cursor, tokens.length, "Unexpected closing brace");
    return nodes;
}
function one(nodes, key) {
    const found = nodes.filter(n => n.key === key);
    assert.equal(found.length, 1, `Expected one ${key}`);
    return found[0].value;
}
function dictionary(nodes) {
    assert.equal(new Set(nodes.map(n => n.key)).size, nodes.length, "Duplicate definition");
    return Object.fromEntries(nodes.map(n => [n.key, n.value]));
}
const walk = nodes => nodes.flatMap(n => [n, ...(Array.isArray(n.value) ? walk(n.value) : [])]);
const triggers = dictionary([...parse(read("common/scripted_triggers/HSM_BAR_mtk_projects.txt")), ...parse(read("common/scripted_triggers/HSM_BAR_mtk_ui.txt"))]);
const effects = dictionary(parse(read("common/scripted_effects/HSM_BAR_mtk_projects.txt")));
const decisions = dictionary(one(parse(read("common/decisions/HSM_BAR_mtk_projects.txt")), P + "projects_missions"));
const missions = Object.fromEntries(Object.entries(decisions).filter(([, nodes]) => nodes.some(n => n.key === "days_mission_timeout")));
const policies = Object.fromEntries(Object.entries(decisions).filter(([key]) => !missions[key]));
const dynamic = one(parse(read("common/dynamic_modifiers/HSM_BAR_mtk_projects.txt")), P + "research");
const actions = one(parse(read("common/on_actions/HSM_BAR_mtk_projects.txt")), "on_actions");
const categories = dictionary(parse(read("common/decisions/categories/HSM_BAR_mtk_projects.txt")));
const journal = one(one(parse(read("common/scripted_guis/HSM_BAR_mtk.txt")), "scripted_gui"), "HSM_BAR_mtk_window");
const journalEffects = dictionary(one(journal, "effects"));
const id = p => P + p.id;
const stageDays = (p, stage) => p[stage === "theory" ? "theoryDays" : "trialDays"];
const stageCost = (p, stage) => p[stage === "theory" ? "theoryCost" : "trialCost"];
const stages = ["theory", "trials"];
const flag = (s, name) => s.flags.set(name, s.day);
const has = (s, name) => s.flags.has(name);
function world() {
    const s = { tag: "BAR", original: "BAR", exists: true, ai: false, capitulated: false, owner: "BAR", controller: "BAR", day: 0,
        flags: new Map(), focuses: new Set(["HSM_BAR_collegium_oath"]), characters: new Set(Object.values(departments).map(d => d.character)),
        pp: 10000, factories: 4, war: false, variables: {}, missions: new Map(), modifiers: new Set(["unrelated_modifier"]), cache: { unrelated_modifier: { research_speed_factor: 0.123 } }, installs: 0 };
    for (const f of ["HSM_BAR_active", "HSM_BAR_collegium", "HSM_BAR_collegium_initialized", ...Object.values(departments).map(d => d.alive)]) flag(s, f);
    return s;
}
function compare(actual, op, expected) {
    if (op === "=") return actual === expected;
    if (op === ">") return actual > expected;
    if (op === "<") return actual < expected;
    if (op === ">=") return actual >= expected;
    if (op === "<=") return actual <= expected;
    if (op === "!=") return actual !== expected;
    throw Error("Unsupported comparison " + op);
}
function condition(nodes, s) {
    return nodes.every(n => {
        const { key: k, value: v, op } = n;
        if (k === "AND") return condition(v, s);
        if (k === "OR") return v.some(child => condition([child], s));
        if (k === "NOT") return !v.some(child => condition([child], s));
        if (k === "ROOT" || k === "BAR") return condition(v, s);
        if (k === "FROM.FROM") return condition(v, { ...s, changedState: s.changedState || "624" });
        if (k === "state") return s.changedState === v;
        if (triggers[k]) { assert(["yes", "no"].includes(v), "Unsupported trigger argument block: " + k); return condition(triggers[k], s) === (v === "yes"); }
        if (k === "always") return v === "yes";
        if (k === "tag") return s.tag === v;
        if (k === "original_tag") return s.original === v;
        if (k === "exists") return s.exists === (v === "yes");
        if (k === "is_ai") return s.ai === (v === "yes");
        if (k === "has_war") return s.war === (v === "yes");
        if (k === "has_variable") return Object.hasOwn(s.variables, v);
        if (k === "check_variable") { assert.equal(v.length, 1); return compare(s.variables[v[0].key] || 0, v[0].op, Number(v[0].value)); }
        if (k === "num_of_civilian_factories_available_for_projects") return compare(s.factories - (s.cache[P + "research"]?.civilian_factory_use || 0), op, Number(v));
        if (k === "has_capitulated") return s.capitulated === (v === "yes");
        if (k === "has_completed_focus") return s.focuses.has(v);
        if (k === "has_character") return s.characters.has(v);
        if (k === "owns_state") { assert.equal(v, "624"); return s.owner === s.tag; }
        if (k === "controls_state") { assert.equal(v, "624"); return s.controller === s.tag; }
        if (k === "has_political_power") return compare(s.pp, op, Number(v));
        if (k === "has_active_mission") return s.missions.has(v);
        if (k === "has_dynamic_modifier") return s.modifiers.has(typeof v === "string" ? v : one(v, "modifier"));
        if (k === "has_country_flag") {
            if (typeof v === "string") return has(s, v);
            const name = one(v, "flag");
            return has(s, name) && v.filter(x => x.key !== "flag").every(x => {
                assert.equal(x.key, "days");
                return compare(s.day - s.flags.get(name), x.op, Number(x.value));
            });
        }
        throw Error("Unsupported predicate " + k);
    });
}
function cache(s) {
    if (!s.modifiers.has(P + "research")) return;
    s.cache[P + "research"] = Object.fromEntries(dynamic.filter(n => !["icon", "enable", "remove_trigger"].includes(n.key)).map(n => [n.key, s.variables[n.value] || 0]));
}
function execute(nodes, s) {
    for (let i = 0; i < nodes.length; i++) {
        const { key: k, value: v } = nodes[i];
        if (k === "if") {
            let taken = false;
            do {
                const branch = nodes[i];
                if (!taken && (branch.key === "else" || condition(one(branch.value, "limit"), s))) {
                    execute(branch.value.filter(n => n.key !== "limit"), s);
                    taken = true;
                }
                if (!["else", "else_if"].includes(nodes[i + 1]?.key)) break;
                i++;
            } while (true);
        } else if (k === "hidden_effect" || k === "ROOT" || k === "BAR") execute(v, s);
        else if (effects[k]) { assert.equal(v, "yes"); execute(effects[k], s); }
        else if (k === "set_country_flag") { assert.equal(typeof v, "string"); if (!has(s, v)) flag(s, v); }
        else if (k === "clr_country_flag") s.flags.delete(v);
        else if (k === "add_political_power") s.pp += Number(v);
        else if (k === "set_variable" || k === "add_to_variable") {
            assert.equal(v.length, 1);
            assert(Number.isFinite(Number(v[0].value)));
            s.variables[v[0].key] = (k === "set_variable" ? 0 : s.variables[v[0].key] || 0) + Number(v[0].value);
        } else if (k === "activate_mission") {
            assert(missions[v], "Unknown mission " + v);
            if (!s.missions.has(v)) s.missions.set(v, s.day + Number(one(missions[v], "days_mission_timeout")));
        } else if (k === "remove_mission") s.missions.delete(v);
        else if (k === "add_dynamic_modifier") {
            assert.equal(one(v, "modifier"), P + "research");
            s.modifiers.add(P + "research"); s.installs++; cache(s);
        } else if (k === "remove_dynamic_modifier") {
            const name = one(v, "modifier");
            s.modifiers.delete(name); delete s.cache[name];
        } else if (k === "force_update_dynamic_modifier") { assert.equal(v, "yes"); cache(s); }
        else throw Error("Unsupported effect " + k);
    }
}
const effect = (name, s) => { assert(effects[name], name); execute(effects[name], s); };
const can = (p, stage, s) => condition(triggers[`${id(p)}_can_${stage}`], s);
const start = (p, stage, s) => effect(`${id(p)}_start_${stage}`, s);
const callback = (p, stage, type, s) => execute(one(missions[`${id(p)}_${stage}_mission`], type + "_effect"), s);
function tick(s, days, removalFirst = true) {
    for (let d = 0; d < days; d++) {
        s.day++;
        for (const [name, due] of [...s.missions]) {
            if (condition(one(missions[name], "cancel_trigger"), s)) {
                s.missions.delete(name);
                execute(one(missions[name], "cancel_effect"), s);
            } else if (s.day >= due) {
                if (removalFirst) s.missions.delete(name);
                execute(one(missions[name], "timeout_effect"), s);
                s.missions.delete(name);
            }
        }
    }
}
function finish(p, stage, s, removalFirst = true) {
    assert(can(p, stage, s), `${p.id}/${stage} cannot start`);
    start(p, stage, s);
    tick(s, stageDays(p, stage), removalFirst);
    assert(has(s, `${id(p)}_${stage === "theory" ? "theory" : "done"}`));
}
function preparations(p, s) {
    if (p.opus) for (const sibling of projects.filter(x => x.department === p.department && !x.opus && !x.partners)) flag(s, id(sibling) + "_done");
    for (const q of p.prerequisites || []) flag(s, P + q + "_done");
}
function expected(s) {
    const totals = Object.fromEntries(modifiers.map(m => [m, 0]));
    if (condition(triggers[P + "programme_access"], s)) for (const p of projects) if (has(s, id(p) + "_done")) {
        for (const [m, value] of Object.entries(B.rewards[p.id])) totals[m] += value;
    }
    if (condition(triggers[P + "programme_access"], s)) for (const p of projects) {
      // Interactive trials keep the same paid laboratories while awaiting a response.
      if (has(s, id(p) + "_experiment_active") && has(s, id(p) + "_trials_running") && !has(s, id(p) + "_done") &&
          s.owner === s.tag && s.controller === s.tag && B.faculties(p).every(d => has(s, departments[d].alive) && s.characters.has(departments[d].character))) {
          totals.civilian_factory_use += factories(p, has(s, id(p) + "_instrumented") ? "instrumented" : "trials");
          continue;
      }
      for (const method of ["theory", "trials", "instrumented"]) {
        if (condition(triggers[`${id(p)}_${method}_timer_valid`], s) && s.missions.has(`${id(p)}_${method}_mission`)) {
            const stage = method === "theory" ? "theory" : "trials";
            totals.civilian_factory_use += has(s, `${id(p)}_${stage}_revised_contract`) ? factories(p, method) : Number(method === "instrumented");
        }
      }
    }
    return totals;
}
function exactTotals(s) {
    for (const [m, amount] of Object.entries(expected(s))) assert(Math.abs((s.variables[variable(m)] || 0) - amount) < 1e-10, m);
    if (s.modifiers.has(P + "research")) assert.deepEqual(s.cache[P + "research"], expected(s));
    assert.deepEqual(s.cache.unrelated_modifier, { research_speed_factor: 0.123 });
}
let passed = 0, failed = 0;
function test(name, run) {
    try { run(); passed++; }
    catch (error) { failed++; console.error("FAIL: " + name + "\n" + error.stack); }
}

test("generated files, immutable original outcomes and 286 hidden missions with eight method choices", () => {
    for (const [file, content] of Object.entries(B.generate())) assert.equal(read(file), content, file);
    assert.equal(Object.keys(missions).length, 26 * (3 + 4 * 2));
    assert.deepEqual(Object.keys(policies).sort(), Object.keys(departments).flatMap(d => ["replication", "instrumentation"].map(choice => `${P}${d}_choose_${choice}`)).sort());
    assert.deepEqual(Object.keys(effects).filter(k => /_select_/.test(k)).sort(), Object.keys(departments).flatMap(d => ["replication", "instrumentation"].map(choice => `${P}${d}_select_${choice}`)).sort());
    assert.equal(projects.length, 26);
    const outcomes = ["success", "partial", "failure", "partial", "success", "success", "success", "partial", "failure", "success", "partial", "success", "success", "partial", "failure", "success", "partial", "success", "success", "failure", "partial", "success", "partial", "partial"];
    for (const [i, p] of projects.entries()) {
        assert.equal(p.number, i + 1);
        if (i < 24) {
            assert.equal(p.department, Object.keys(departments)[Math.floor(i / 6)]);
            assert.equal(p.opus, i % 6 === 5);
            assert.equal(p.outcome, outcomes[i]);
        }
        assert(p.theoryDays >= 28 && p.theoryDays <= 84);
        assert(p.trialDays >= 35 && p.trialDays <= 126);
        assert.equal(p.instrumentedDays, p.trialDays - (p.opus ? 21 : 7));
        assert.equal(p.instrumentedCost, p.trialCost + (p.opus ? 35 : 15));
        assert(!Object.hasOwn(p, "civilianCost"));
        for (const method of ["theory", "trials", "replication", "instrumented"]) assert.equal(factories(p, method), (p.opus ? 2 : 1) + Number(method === "instrumented"), `${p.id}/${method}`);
        for (const stage of stages) {
            const mission = missions[`${id(p)}_${stage}_mission`];
            assert.equal(one(mission, "days_mission_timeout"), String(stageDays(p, stage)));
            assert(!condition(one(mission, "activation"), world()));
            assert(!condition(one(mission, "available"), world()));
            assert.equal(one(one(mission, "ai_will_do"), "factor"), "0");
            assert.equal(one(mission, "cancel_if_not_visible"), "no");
            assert(!mission.some(n => ["complete_effect", "cost", "fire_only_once", "selectable_mission"].includes(n.key)));
        }
    }
    for (const nodes of [...Object.values(decisions), ...Object.values(categories)]) assert.deepEqual(one(nodes, "visible"), parse("always = no"), "Native decision interface must remain hidden");
    assert(!walk(Object.values(effects).flat()).some(n => ["country_event", "activate_decision", "recruit_character", "set_technology", "create_country_leader"].includes(n.key)));
    assert(!walk([...Object.values(triggers).flat(), ...Object.values(effects).flat()]).some(n => ["has_country_flag", "set_country_flag"].includes(n.key) && typeof n.value === "string" && /_(civilian|field)$/.test(n.value)), "Legacy application flags may be cleared, never read or set");
    assert(!walk(Object.values(effects).flat()).some(n => n.key === "add_to_variable" && n.value.some(v => v.key === variable("political_power_gain"))), "Research has no ongoing PP upkeep");
});

for (const p of projects) {
    for (const removalFirst of [true, false]) test(`${p.id}: complete ${p.outcome}, callback removal order=${removalFirst}`, () => {
        const s = world(); preparations(p, s);
        effect(P + "projects_pulse", s);
        const before = { ...expected(s) }, pp = s.pp;
        assert(!can(p, "trials", s));
        start(p, "trials", s); assert.equal(s.pp, pp);
        start(p, "theory", s);
        assert.equal(s.pp, pp - p.theoryCost);
        assert(has(s, P + p.department + "_busy"));
        start(p, "theory", s); assert.equal(s.pp, pp - p.theoryCost);
        tick(s, p.theoryDays - 1, removalFirst);
        s.day += 0.99;
        callback(p, "theory", "timeout", s);
        assert(!has(s, id(p) + "_theory"));
        s.day -= 0.99;
        callback(p, "theory", "timeout", s);
        assert(!has(s, id(p) + "_theory"));
        tick(s, 1, removalFirst);
        assert(has(s, id(p) + "_theory"));
        assert(!has(s, P + p.department + "_busy"));
        assert.deepEqual(expected(s), before);
        finish(p, "trials", s, removalFirst);
        assert.equal(s.pp, pp - p.theoryCost - p.trialCost);
        assert.equal(s.variables[P + p.department + "_completed"], p.opus ? 5 : 1);
        assert.equal(s.missions.size, 0);
        assert(!has(s, P + p.department + "_busy"));
        for (const stage of stages) {
            callback(p, stage, "timeout", s); callback(p, stage, "cancel", s); start(p, stage, s);
        }
        for (let i = 0; i < 4; i++) effect(P + "projects_refresh", s);
        assert.equal(s.pp, pp - p.theoryCost - p.trialCost);
        assert.equal(s.installs, 1);
        exactTotals(s);
        if (p.outcome === "failure") assert.deepEqual(expected(s), before);
        else for (const m of modifiers) assert(Math.abs(expected(s)[m] - before[m] - (B.rewards[p.id][m] || 0)) < 1e-10, m);
    });
    for (const stage of stages) {
        test(`${p.id}/${stage}: insufficient PP and exact-cost boundary`, () => {
            const s = world(); preparations(p, s);
            if (stage === "trials") flag(s, id(p) + "_theory");
            s.pp = stageCost(p, stage) - 1;
            const snapshot = structuredClone(s);
            assert(!can(p, stage, s)); start(p, stage, s); assert.deepEqual(s, snapshot);
            s.pp += 0.99;
            assert(!can(p, stage, s)); start(p, stage, s); assert.equal(s.pp, stageCost(p, stage) - 0.01);
            s.pp = stageCost(p, stage) - 1;
            s.pp++; assert(can(p, stage, s)); start(p, stage, s); assert.equal(s.pp, 0);
            start(p, stage, s); assert.equal(s.pp, 0);
        });
        test(`${p.id}/${stage}: cancel, restart and replay old timeout/cancel`, () => {
            const s = world(); preparations(p, s);
            if (stage === "trials") flag(s, id(p) + "_theory");
            start(p, stage, s); tick(s, stageDays(p, stage) - 2);
            s.controller = "WIT";
            tick(s, 1);
            assert.equal(s.missions.size, 0); assert(!has(s, P + p.department + "_busy"));
            assert(!has(s, id(p) + "_done"));
            assert.equal(has(s, id(p) + "_theory"), stage === "trials");
            callback(p, stage, "timeout", s);
            s.controller = "BAR"; start(p, stage, s);
            const due = s.missions.get(`${id(p)}_${stage}_mission`), pp = s.pp;
            tick(s, 1); // The old attempt would now time out.
            callback(p, stage, "timeout", s); callback(p, stage, "cancel", s);
            assert.equal(s.missions.get(`${id(p)}_${stage}_mission`), due);
            assert(has(s, `${id(p)}_${stage}_running`));
            tick(s, stageDays(p, stage) - 1);
            assert(has(s, id(p) + (stage === "theory" ? "_theory" : "_done")));
            assert.equal(s.pp, pp); exactTotals(s);
        });
    }
}

const invalidators = {
    foreign: s => { s.tag = "WIT"; },
    civil_war_clone: s => { s.tag = "D01"; },
    wrong_original: s => { s.original = "WIT"; },
    inactive: s => s.flags.delete("HSM_BAR_active"),
    no_collegium: s => s.flags.delete("HSM_BAR_collegium"),
    uninitialized: s => s.flags.delete("HSM_BAR_collegium_initialized"),
    directorate: s => flag(s, "HSM_BAR_directorate"),
    capitulated: s => { s.capitulated = true; },
    no_oath: s => s.focuses.clear(),
    annexed: s => { s.exists = false; },
    lost_owner: s => { s.owner = "WIT"; },
    lost_control: s => { s.controller = "WIT"; }
};
for (const p of projects) for (const stage of stages) {
    for (const [label, invalidate] of Object.entries({ ...invalidators,
        dead_faculty: s => s.flags.delete(departments[p.department].alive),
        retired_faculty: s => s.characters.delete(departments[p.department].character)
    })) test(`${p.id}/${stage}: reject start and last-moment completion after ${label}`, () => {
        const cold = world(); preparations(p, cold);
        if (stage === "trials") flag(cold, id(p) + "_theory");
        invalidate(cold);
        const before = structuredClone(cold);
        assert(!can(p, stage, cold)); start(p, stage, cold); assert.deepEqual(cold, before);
        const s = world(); preparations(p, s);
        if (stage === "trials") flag(s, id(p) + "_theory");
        start(p, stage, s); s.day += stageDays(p, stage);
        invalidate(s);
        assert(condition(one(missions[`${id(p)}_${stage}_mission`], "cancel_trigger"), s));
        callback(p, stage, "timeout", s);
        assert(!has(s, id(p) + "_done"));
        assert.equal(has(s, id(p) + "_theory"), stage === "trials");
        assert(!has(s, P + p.department + "_busy"));
        assert.equal(s.missions.size, 0);
        exactTotals(s);
    });
}

for (const department of Object.keys(departments)) {
    const prep = projects.filter(p => p.department === department && !p.opus && !p.partners);
    const opus = projects.find(p => p.department === department && p.opus);
    test(`${department}: all 32 preparation subsets; theories, UI counters and other departments cannot unlock opus`, () => {
        for (let bits = 0; bits < 32; bits++) {
            const s = world(); s.variables[P + department + "_completed"] = 5;
            for (const p of projects.filter(p => p.department !== department || p.partners)) flag(s, id(p) + "_done");
            prep.forEach((p, i) => { flag(s, id(p) + "_theory"); if (bits & (1 << i)) flag(s, id(p) + "_done"); });
            effect(P + "projects_refresh", s);
            assert.equal(can(opus, "theory", s), bits === 31);
            assert.equal(s.variables[P + department + "_completed"], prep.filter((_, i) => bits & (1 << i)).length);
        }
        const s = world();
        for (const p of prep) { finish(p, "theory", s); finish(p, "trials", s); }
        assert(prep.some(p => p.outcome === "failure"));
        assert(can(opus, "theory", s));
        finish(opus, "theory", s); finish(opus, "trials", s);
        assert.equal(s.variables[P + department + "_completed"], 5);
    });
}

test("four independent departments and same-department exclusion, including orphan native missions", () => {
    const s = world();
    for (const d of Object.keys(departments)) {
        const [a, b] = projects.filter(p => p.department === d);
        start(a, "theory", s);
        assert(!can(b, "theory", s));
        flag(s, id(b) + "_theory"); assert(!can(b, "trials", s));
    }
    assert.equal(s.missions.size, 4);
    effect(id(projects[0]) + "_cancel_theory", s);
    assert.equal(s.missions.size, 3);
    for (const d of ["leopold", "silver", "asinti"]) assert(has(s, P + d + "_busy"));
    const orphan = world();
    orphan.missions.set(id(projects[0]) + "_theory_mission", 14);
    assert(!can(projects[1], "theory", orphan));
    flag(orphan, P + "projects_initialized"); effect(P + "projects_pulse", orphan);
    assert(can(projects[1], "theory", orphan));
});

test("earned theory, done flags and benefits survive temporary access or faculty loss", () => {
    const s = world();
    finish(projects[0], "theory", s); finish(projects[0], "trials", s);
    finish(projects[1], "theory", s); start(projects[1], "trials", s);
    s.owner = "WIT"; s.controller = "WIT";
    execute(one(one(actions, "on_state_control_changed"), "effect"), s);
    assert(condition(triggers[P + "available"], s));
    assert(has(s, id(projects[0]) + "_done")); assert(has(s, id(projects[1]) + "_theory"));
    assert(!has(s, id(projects[1]) + "_done")); assert.equal(s.missions.size, 0); exactTotals(s);
    s.owner = "BAR"; s.controller = "BAR"; assert(can(projects[1], "trials", s));
    s.flags.delete(departments.viira.alive); effect(P + "projects_pulse", s);
    assert(condition(triggers[P + "available"], s)); exactTotals(s);
    flag(s, departments.viira.alive); s.ai = true; effect(P + "projects_pulse", s);
    assert(s.modifiers.has(P + "research")); assert(has(s, id(projects[0]) + "_done"));
    s.ai = false; s.capitulated = true;
    execute(one(one(actions, "on_capitulation"), "effect"), s);
    assert(!condition(triggers[P + "available"], s));
    assert(has(s, id(projects[1]) + "_theory")); assert(!s.modifiers.has(P + "research"));
    s.capitulated = false; effect(P + "projects_pulse", s); exactTotals(s);
    finish(projects[1], "trials", s); exactTotals(s);
});

test("maintenance releases interrupted mission locks; stale callbacks leave a different project running", () => {
    const s = world(), a = projects[0], b = projects[1];
    start(a, "theory", s);
    // Native remove_mission itself intentionally has no cancellation callback.
    execute(parse(`remove_mission = ${id(a)}_theory_mission`), s);
    effect(P + "projects_pulse", s);
    assert(!has(s, id(a) + "_theory_running"));
    assert(!has(s, P + "viira_busy")); assert(!has(s, id(a) + "_theory"));
    start(b, "theory", s);
    callback(a, "theory", "cancel", s); callback(a, "theory", "timeout", s);
    assert(has(s, id(b) + "_theory_running")); assert(has(s, P + "viira_busy"));
    tick(s, b.theoryDays); assert(has(s, id(b) + "_theory"));
});

// Installed scripts document the hooks, not the C++ scheduler's internal ordering.
// Cover a daily pulse on either side of the native timeout transaction without
// claiming a pulse can interleave mission removal and that transaction's callback.
for (const p of projects) for (const stage of stages) test(`${p.id}/${stage}: daily pulse before/after timeout preserves completion`, () => {
    for (const pulseFirst of [true, false]) for (const removalFirst of [true, false]) {
        const s = world(); preparations(p, s);
        if (stage === "trials") flag(s, id(p) + "_theory");
        start(p, stage, s);
        const pp = s.pp, mission = `${id(p)}_${stage}_mission`;
        const daily = one(one(actions, "on_daily_BAR"), "effect");
        s.day += stageDays(p, stage);
        if (pulseFirst) {
            execute(daily, s);
            assert(has(s, `${id(p)}_${stage}_running`));
            assert(has(s, P + p.department + "_busy"));
            assert(s.missions.has(mission));
        }
        if (removalFirst) s.missions.delete(mission);
        callback(p, stage, "timeout", s);
        s.missions.delete(mission);
        if (!pulseFirst) execute(daily, s);
        assert(has(s, id(p) + (stage === "theory" ? "_theory" : "_done")));
        assert(!has(s, `${id(p)}_${stage}_running`));
        assert(!has(s, P + p.department + "_busy"));
        assert.equal(s.pp, pp); exactTotals(s);
    }
});

test("save/load preserves active mission deadlines, paid costs and completed results", () => {
    const s = world(); finish(projects[0], "theory", s); start(projects[0], "trials", s);
    tick(s, 10); const restored = structuredClone(s), pp = s.pp;
    effect(P + "projects_pulse", restored);
    assert.equal(restored.missions.get(id(projects[0]) + "_trials_mission"), s.missions.get(id(projects[0]) + "_trials_mission"));
    tick(restored, projects[0].trialDays - 10);
    assert(has(restored, id(projects[0]) + "_done")); assert.equal(restored.pp, pp);
    exactTotals(restored);
});

test("Silver clinical pause blocks new trials but preserves theory and already running trials", () => {
    const s = world(), p = projects.find(p => p.department === "silver");
    flag(s, "HSM_BAR_collegium_trial_pause"); finish(p, "theory", s);
    assert(!can(p, "trials", s));
    s.flags.delete("HSM_BAR_collegium_trial_pause"); start(p, "trials", s);
    flag(s, "HSM_BAR_collegium_trial_pause"); tick(s, p.trialDays);
    assert(has(s, id(p) + "_done")); exactTotals(s);
});

for (const route of ["hook", "daily_inactive", "daily_directorate"]) test(`institution teardown via ${route} removes all results/timers; old callbacks cannot restore them`, () => {
    const s = world();
    for (const p of projects) { flag(s, id(p) + "_theory"); flag(s, id(p) + "_done"); }
    effect(P + "projects_pulse", s);
    for (const p of projects.filter(p => p.number % 6 === 1)) {
        s.flags.delete(id(p) + "_done"); start(p, "trials", s);
    }
    if (route === "hook") {
        const dissolve = one(parse(read("common/scripted_effects/HSM_BAR_core_effects.txt")), "HSM_BAR_dissolve_institutions");
        // Execute the actual synchronous integration hook; other institutions are separate fixtures.
        const hooks = dissolve.filter(n => n.key === "if" && walk([n]).some(q => q.key === P + "projects_teardown"));
        assert.equal(hooks.length, 1);
        assert(dissolve.indexOf(hooks[0]) < dissolve.findIndex(n => n.key === "clr_country_flag" && n.value === "HSM_BAR_collegium"));
        execute(hooks, s);
        execute(dissolve.filter(n => n.key === "clr_country_flag"), s);
    } else {
        if (route === "daily_inactive") s.flags.delete("HSM_BAR_active");
        else flag(s, "HSM_BAR_directorate");
        execute(one(one(actions, "on_daily_BAR"), "effect"), s);
    }
    assert.equal(s.missions.size, 0); assert(!s.modifiers.has(P + "research"));
    for (const p of projects) {
        assert(!has(s, id(p) + "_theory")); assert(!has(s, id(p) + "_done"));
        for (const stage of stages) { callback(p, stage, "timeout", s); callback(p, stage, "cancel", s); }
    }
    for (const d of Object.keys(departments)) { assert.equal(s.variables[P + d + "_completed"], 0); assert(!has(s, P + d + "_busy")); }
    exactTotals(s);
    flag(s, "HSM_BAR_active"); flag(s, "HSM_BAR_collegium"); s.flags.delete("HSM_BAR_directorate");
    effect(P + "projects_pulse", s); start(projects[0], "theory", s);
    callback(projects[0], "theory", "timeout", s); assert(!has(s, id(projects[0]) + "_theory"));
});

test("all completed rewards have exact independent unified totals and recomputation does not stack", () => {
    const s = world();
    for (const p of projects) flag(s, id(p) + "_done");
    effect(P + "projects_pulse", s);
    const totals = { research_speed_factor: 0.18, recon_factor: 0.25, experience_loss_factor: -0.15,
        modifier_army_sub_unit_category_magical_infantry_max_org_factor: 0.20, army_org_regain: 0.25,
        attrition: -0.10, industrial_capacity_factory: 0.20, production_factory_efficiency_gain_factor: 0.25,
        casualty_trickleback: 0.25, stability_factor: 0.05, supply_consumption_factor: -0.10,
        production_speed_buildings_factor: 0, political_power_gain: 0, civilian_factory_use: 0 };
    assert.deepEqual(Object.keys(totals).sort(), modifiers.slice().sort());
    for (const [m, value] of Object.entries(totals)) assert(Math.abs(s.variables[variable(m)] - value) < 1e-10, m);
    for (let i = 0; i < 10; i++) effect(P + "projects_pulse", s);
    exactTotals(s); assert.equal(s.installs, 1);
    for (const p of projects) if (p.outcome !== "failure") s.flags.delete(id(p) + "_done");
    effect(P + "projects_refresh", s);
    for (const m of modifiers) assert.equal(s.variables[variable(m)], 0);
});

function neutralMissionDescription(text) {
    // Forbid indirect disclosure through static or scripted localization as well as plain rewards.
    assert(!/\$|\[|HSM_BAR_|%|[+-]\d|\b(?:success\w*|fail\w*|partial|reward\w*|benefit\w*|bonus\w*)\b|неудач|провал|успех|частичн|бонус|наград|выгод/i.test(text), "Mission description discloses a result: " + text);
}

test("mission spoiler guard rejects effect references, scripted results and literal outcomes in both languages", () => {
    for (const spoiler of ["$HSM_BAR_mtk_sleep_lecture_effects$", "$HSM_BAR_mtk_chorus_conclusion$",
        "[GetHSMBARMtkEffects]", "Research speed: +0.5%", "The trial fails.", "A successful trial.",
        "No permanent benefit.", "Partial application.", "Бонус: +1%", "Исследование неудачно.", "Частичный успех."]) {
        assert.throws(() => neutralMissionDescription("A signed report. " + spoiler), /discloses a result/);
    }
});

test("EN/RU gameplay localization covers all mission stages and tooltips without owning project titles", () => {
    const sets = [];
    for (const language of ["english", "russian"]) {
        const text = read(`localisation/${language}/HSM_BAR_mtk_project_effects_l_${language}.yml`);
        assert(text.startsWith(`\uFEFFl_${language}:\n`));
        const entries = [...text.matchAll(/^ (\w+):0 "(.*)"$/gm)];
        const loc = new Map(entries.map(m => [m[1], m[2]]));
        assert.equal(entries.length, loc.size); sets.push([...loc.keys()].sort());
        const descriptions = { theory: new Set(), trials: new Set(), instrumented: new Set() };
        for (const p of projects) {
            assert(!loc.has(id(p) + "_title"));
            assert(loc.has(id(p) + "_effects"));
            for (const stage of stages) {
                const tooltip = loc.get(`${id(p)}_start_${stage}_tt`);
                if (stage === "theory") assert(tooltip.includes(String(stageDays(p, stage))) && tooltip.includes(String(stageCost(p, stage))));
                else {
                    assert(tooltip.startsWith(`[GetHSMBARMtkTrialBudget_${p.id}]`));
                    for (const method of ["replication", "instrumented"]) {
                        const amount = method === "instrumented" ? p.instrumentedCost : p.trialCost;
                        const days = method === "instrumented" ? p.instrumentedDays : p.trialDays;
                        const budget = loc.get(`${id(p)}_budget_${method}`);
                        assert.deepEqual(budget.match(/\d+/g).map(Number), [amount, days, factories(p, method)]);
                    }
                }
                assert(tooltip.includes("$STATE_624$") && tooltip.includes("$HSM_BAR_collegium_oath$"));
                assert(tooltip.includes(`$${departments[p.department].character}$`));
                const plainTooltip = tooltip.replace(/\$[A-Za-z0-9_]+\$/g, "").replace(/\[GetHSMBARMtkMethod_(viira|leopold|silver|asinti)\]/g, "").replace(`[GetHSMBARMtkTrialBudget_${p.id}]`, "");
                assert(!/\bBAR\b|\b624\b|HSM_BAR_|\[|\b(?:flag|variable|trigger)\b|флаг|переменн/i.test(plainTooltip));
                assert(tooltip.includes(language === "english" ? "Department free" : "Кафедра свободна"));
                assert(tooltip.includes(language === "english" ? "refund its cost" : "затраты не возвращаются"));
                assert(tooltip.includes(language === "english" ? "Restarting costs the same" : "Повторный запуск оплачивается заново"));
                if (p.opus) assert(tooltip.includes(language === "english"
                    ? "All five departmental preparations finished, including failures"
                    : "Завершены все пять подготовительных проектов кафедры, включая неудачные"));
                const description = loc.get(`${id(p)}_${stage}_mission_desc`);
                assert(description, `${id(p)}_${stage}_mission_desc`);
                neutralMissionDescription(description);
                assert(description.startsWith(`${stageDays(p, stage)} `));
                descriptions[stage].add(description.replace(/^\d+ /, ""));
                if (stage === "trials") assert(description.includes(language === "english"
                    ? "signed test report and conclusion" : "подписанный отчёт об испытаниях и заключение"));
                assert(loc.get(`${id(p)}_${stage}_mission`).includes(`$${id(p)}_title$`));
            }
            for (const value of Object.values(B.rewards[p.id])) assert(loc.get(id(p) + "_effects").includes(`${Number((value * 100).toFixed(3))}%`));
            const instrumentedDescription = loc.get(id(p) + "_instrumented_mission_desc");
            neutralMissionDescription(instrumentedDescription);
            assert(instrumentedDescription.startsWith(p.instrumentedDays + " "));
            assert.deepEqual(instrumentedDescription.match(/\d+/g).map(Number), [p.instrumentedDays, factories(p, "instrumented")]);
            descriptions.instrumented.add(instrumentedDescription.replace(/\d+/g, "#"));
            assert(loc.get(id(p) + "_instrumented_mission").includes(`$${id(p)}_title$`));
            assert.deepEqual([...loc.keys()].filter(key => key.startsWith(id(p) + "_effects")), [id(p) + "_effects"]);
            assert.deepEqual([...loc.keys()].filter(key => key.startsWith(id(p) + "_budget_")).sort(), [id(p) + "_budget_instrumented", id(p) + "_budget_replication"]);
        }
        // All outcomes share the same stage description; none can reveal a project's fate.
        for (const stage of Object.keys(descriptions)) assert.equal(descriptions[stage].size, 1);
        assert(loc.has(P + "research") && loc.has(P + "research_desc"));
        for (const key of Object.keys(categories)) assert(loc.has(key));
        for (const key of Object.keys(policies)) assert(loc.has(key) && loc.has(key + "_desc"));
    }
    assert.deepEqual(sets[0], sets[1]);
});

test("department pacing differs, with bounded factory/time/PP tradeoffs", () => {
    const totals = Object.fromEntries(Object.keys(departments).map(d => [d, projects.filter(p => p.department === d && !p.partners).reduce((a, p) => ({days: a.days + p.theoryDays + p.trialDays, pp: a.pp + p.theoryCost + p.trialCost}), {days: 0, pp: 0})]));
    assert.deepEqual(totals, {viira: {days: 581, pp: 465}, leopold: {days: 511, pp: 515}, silver: {days: 644, pp: 490}, asinti: {days: 651, pp: 495}});
    for (const [method, aggregate] of [["trials", {days: 2569, pp: 2145}], ["instrumented", {days: 2331, pp: 2615}]]) {
        assert.deepEqual(projects.reduce((a, p) => ({days: a.days + p.theoryDays + (method === "instrumented" ? p.instrumentedDays : p.trialDays), pp: a.pp + p.theoryCost + (method === "instrumented" ? p.instrumentedCost : p.trialCost)}), {days: 0, pp: 0}), aggregate);
    }
    assert.equal(one(dynamic, "icon"), "GFX_idea_HSM_BAR_art_collegium");
    for (const nodes of Object.values(policies)) { assert.equal(one(nodes, "cost"), "0"); assert.equal(one(one(nodes, "ai_will_do"), "factor"), "0"); }
    for (const p of projects) {
        const mission = missions[id(p) + "_instrumented_mission"];
        assert.equal(one(mission, "days_mission_timeout"), String(p.instrumentedDays));
        assert(!mission.some(n => n.key === "modifier"), "Reservations must not rely on a mission being manually selected");
        assert(!condition(one(mission, "activation"), world()));
        assert(!condition(one(mission, "available"), world()));
    }
});
test("each stage adds the specified duration and PP cost to its original contract", () => {
    // Original theory days, trial days, theory PP and trial PP, independent of the catalog.
    const original = {
        field_atlas: [14, 28, 15, 25], shared_senses: [28, 42, 20, 30], sleep_lecture: [21, 28, 15, 20],
        crystal_memory: [28, 35, 25, 35], spell_notation: [14, 21, 10, 20], chorus: [42, 84, 45, 65],
        prosthetics: [14, 21, 10, 30], self_repair: [21, 35, 15, 40], revolver_howitzer: [14, 28, 10, 35],
        crystal_drive: [21, 28, 20, 45], sorting_engine: [14, 21, 15, 30], manufactory: [35, 63, 40, 85],
        necrotic_suture: [21, 35, 15, 25], tissue_bank: [28, 42, 25, 35], ageless_sleep: [35, 42, 20, 25],
        spell_sterilisation: [14, 28, 15, 20], phantom_pain: [21, 35, 20, 30], last_minute: [49, 98, 50, 70],
        ritual_brake: [21, 28, 20, 20], silent_witness: [28, 21, 15, 15], place_memory: [35, 42, 20, 25],
        threshold_compass: [21, 35, 20, 30], empty_vessel: [28, 49, 25, 35], contact: [56, 91, 55, 75],
        sensate_prosthesis: [21, 42, 25, 45], interrupt_notation: [28, 35, 30, 40]
    };
    assert.deepEqual(Object.keys(original), projects.map(p => p.id));
    for (const p of projects) {
        const [theoryDays, trialDays, theoryCost, trialCost] = original[p.id];
        const extraDays = p.opus ? 28 : 14, extraCost = p.opus ? 20 : 10;
        assert.deepEqual([p.theoryDays, p.trialDays, p.theoryCost, p.trialCost],
            [theoryDays + extraDays, trialDays + extraDays, theoryCost + extraCost, trialCost + extraCost], p.id);
        assert.equal(p.instrumentedDays, trialDays - (p.opus ? 21 : 7) + extraDays, p.id);
        assert.equal(p.instrumentedCost, trialCost + (p.opus ? 35 : 15) + extraCost, p.id);
    }
});
function select(p, choice, s) {
    effect(P + p.department + "_select_" + choice, s);
}
for (const p of projects) for (const method of ["theory", "trials", "instrumented"]) {
    const stage = method === "theory" ? "theory" : "trials";
    const days = method === "instrumented" ? p.instrumentedDays : stageDays(p, stage);
    const payment = method === "instrumented" ? p.instrumentedCost : stageCost(p, stage);
    const required = (p.opus ? 2 : 1) + Number(method === "instrumented");
    const contract = `${id(p)}_${stage}_revised_contract`, mission = `${id(p)}_${method}_mission`;
    const ready = () => {
        const s = world(); preparations(p, s);
        if (stage === "trials") flag(s, id(p) + "_theory");
        // A method selected for later trials must not increase theory's reservation.
        if (method !== "trials") select(p, "instrumentation", s);
        return s;
    };
    test(`${p.id}/${method}: exact factory boundary, paid reservation, release and replay`, () => {
        assert.equal(factories(p, method), required);
        for (const release of ["finish", "cancel", "orphan", "teardown"]) {
            const s = ready(); s.pp = payment;
            flag(s, id(p) + "_civilian"); flag(s, id(p) + "_field");
            for (let count = 0; count < required; count++) {
                s.factories = count; const before = structuredClone(s);
                assert(!can(p, stage, s)); start(p, stage, s); assert.deepEqual(s, before);
            }
            s.factories = required; assert(can(p, stage, s)); start(p, stage, s);
            assert.equal(s.pp, 0); assert(has(s, contract));
            assert.equal(s.missions.get(mission), days);
            assert.equal(s.cache[P + "research"].civilian_factory_use, required);
            assert.equal(s.variables[variable("political_power_gain")], 0);
            exactTotals(s);
            for (let i = 0; i < 3; i++) { start(p, stage, s); effect(P + "projects_pulse", s); }
            assert.equal(s.pp, 0); assert.equal(s.cache[P + "research"].civilian_factory_use, required);
            if (release === "finish") {
                // A new contract cannot finish at the old save's shorter deadline.
                s.day = days - (p.opus ? 28 : 14); callback(p, method, "timeout", s);
                assert(has(s, contract)); assert(s.missions.has(mission));
                s.day = days - 0.01; callback(p, method, "timeout", s);
                assert(has(s, contract)); assert(s.missions.has(mission));
                s.day = days; callback(p, method, "timeout", s);
                assert(has(s, id(p) + (stage === "theory" ? "_theory" : "_done")));
            } else if (release === "cancel") effect(`${id(p)}_cancel_${stage}`, s);
            else if (release === "orphan") { s.missions.delete(mission); effect(P + "projects_pulse", s); }
            else effect(P + "projects_teardown", s);
            assert(!has(s, contract)); assert.equal(s.missions.size, 0);
            assert.equal(s.variables[variable("civilian_factory_use")], 0);
            callback(p, method, "timeout", s); callback(p, method, "cancel", s);
            assert.equal(s.pp, 0); assert.equal(s.variables[variable("civilian_factory_use")], 0); exactTotals(s);
        }
    });
    test(`${p.id}/${method}: available factory boundary subtracts another faculty's reservation`, () => {
        const s = ready();
        const other = projects.find(q => !q.opus && !q.partners && ![p.department, ...(p.partners || [])].includes(q.department) && !(p.prerequisites || []).includes(q.id));
        s.factories = required;
        start(other, "theory", s); assert.equal(s.cache[P + "research"].civilian_factory_use, 1);
        const before = structuredClone(s); assert(!can(p, stage, s)); start(p, stage, s); assert.deepEqual(s, before);
        s.factories++; assert(can(p, stage, s)); start(p, stage, s);
        assert.equal(s.cache[P + "research"].civilian_factory_use, required + 1); exactTotals(s);
        effect(`${id(p)}_cancel_${stage}`, s);
        assert.equal(s.cache[P + "research"].civilian_factory_use, 1);
        assert(s.missions.has(id(other) + "_theory_mission"));
        effect(id(other) + "_cancel_theory", s); assert.equal(s.cache[P + "research"].civilian_factory_use, 0); exactTotals(s);
    });
    test(`${p.id}/${method}: old-save deadline and flags survive migration without progress reset or charge`, () => {
        for (const removalFirst of [true, false]) for (const application of ["civilian", "field", "both"]) {
            const s = ready(), oldDays = days - (p.opus ? 28 : 14), oldReservation = Number(method === "instrumented");
            s.day = 23; s.pp = 713; s.factories = oldReservation;
            flag(s, P + "projects_initialized"); flag(s, `${id(p)}_${stage}_running`);
            if (method === "instrumented") flag(s, id(p) + "_instrumented");
            const oldFlags = [P + p.department + "_civilian", ...["civilian", "field"].filter(f => application === f || application === "both").map(f => id(p) + "_" + f)];
            for (const f of oldFlags) flag(s, f);
            s.missions.set(mission, s.day + oldDays);
            const loaded = structuredClone(s); loaded.day += 3;
            effect(P + "projects_pulse", loaded);
            assert(!has(loaded, contract)); assert.equal(loaded.flags.get(`${id(p)}_${stage}_running`), 23);
            assert.equal(loaded.missions.get(mission), 23 + oldDays); assert.equal(loaded.pp, 713);
            assert.equal(loaded.cache[P + "research"].civilian_factory_use, oldReservation); exactTotals(loaded);
            for (const f of oldFlags) assert.equal(loaded.flags.get(f), s.flags.get(f));
            loaded.day = 23 + oldDays - 0.01; callback(p, method, "timeout", loaded);
            assert(loaded.missions.has(mission)); assert(!has(loaded, id(p) + (stage === "theory" ? "_theory" : "_done")));
            loaded.day = 23 + oldDays;
            if (removalFirst) loaded.missions.delete(mission);
            callback(p, method, "timeout", loaded);
            assert(has(loaded, id(p) + (stage === "theory" ? "_theory" : "_done")));
            assert(!has(loaded, contract)); assert.equal(loaded.missions.size, 0);
            for (const f of oldFlags) assert.equal(loaded.flags.get(f), s.flags.get(f));
            assert.equal(loaded.cache[P + "research"].civilian_factory_use, 0);
            assert.equal(loaded.cache[P + "research"].political_power_gain, 0); exactTotals(loaded);
            const rewards = structuredClone(loaded.variables);
            callback(p, method, "timeout", loaded); callback(p, method, "cancel", loaded);
            assert.deepEqual(loaded.variables, rewards); assert.equal(loaded.pp, 713);
            // A cancelled legacy timer cannot complete a new, fully paid contract early.
            const restarted = structuredClone(s); restarted.factories = required;
            effect(`${id(p)}_cancel_${stage}`, restarted); start(p, stage, restarted);
            assert(has(restarted, contract)); assert.equal(restarted.pp, 713 - payment);
            assert.equal(restarted.cache[P + "research"].civilian_factory_use, required);
            assert.equal(restarted.missions.get(mission), 23 + days);
            restarted.day += oldDays; callback(p, method, "timeout", restarted); callback(p, method, "cancel", restarted);
            assert(has(restarted, contract)); assert(restarted.missions.has(mission));
            tick(restarted, days - oldDays, removalFirst);
            assert(!has(restarted, contract)); assert(has(restarted, id(p) + (stage === "theory" ? "_theory" : "_done")));
            assert.equal(restarted.pp, 713 - payment); exactTotals(restarted);
        }
    });
}
for (const p of projects) for (const instrumented of [false, true]) {
    test(`${p.id}: ${instrumented ? "instrumented" : "sequential"} snapshots costs and timer; old application flags have no effect`, () => {
      for (let mask = 0; mask < 16; mask++) {
        const s = world(); preparations(p, s); flag(s, id(p) + "_theory");
        const legacy = [P + p.department + "_civilian", P + p.department + "_field", id(p) + "_civilian", id(p) + "_field"];
        legacy.forEach((f, i) => { if (mask & (1 << i)) flag(s, f); });
        if (instrumented) select(p, "instrumentation", s);
        const payment = instrumented ? p.instrumentedCost : p.trialCost;
        s.pp = payment - 0.01; const before = structuredClone(s); start(p, "trials", s); assert.deepEqual(s, before);
        s.pp = payment; start(p, "trials", s); assert.equal(s.pp, 0);
        assert(!has(s, id(p) + "_civilian")); assert(!has(s, id(p) + "_field"));
        assert(has(s, id(p) + "_trials_revised_contract"));
        const method = instrumented ? "instrumented" : "trials", days = instrumented ? p.instrumentedDays : p.trialDays;
        assert.equal(s.missions.get(id(p) + "_" + method + "_mission"), days);
        assert.equal(s.cache[P + "research"].civilian_factory_use, factories(p, method));
        const paid = structuredClone(s);
        effect(P + p.department + "_select_" + (instrumented ? "replication" : "instrumentation"), s);
        assert.deepEqual(s, paid, "A busy department cannot alter its paid contract");
        // Even externally changed department policy cannot change the project's snapshot.
        if (instrumented) s.flags.delete(P + p.department + "_instrumented"); else flag(s, P + p.department + "_instrumented");
        for (const f of legacy) flag(s, f);
        tick(s, days - 1); callback(p, method, "timeout", s); assert(!has(s, id(p) + "_done"));
        effect(P + "projects_pulse", s); assert(has(s, id(p) + "_trials_running"));
        tick(s, 1); assert(has(s, id(p) + "_done")); assert.equal(s.missions.size, 0);
        assert(!has(s, id(p) + "_trials_revised_contract"));
        assert.equal(s.variables[variable("civilian_factory_use")], 0);
        assert.equal(s.variables[variable("political_power_gain")], 0);
        exactTotals(s);
        const results = structuredClone(s.variables);
        for (const f of legacy) s.flags.delete(f);
        effect(P + "projects_refresh", s);
        assert.deepEqual(s.variables, results, "Legacy flags cannot change unified rewards");
        callback(p, method, "cancel", s); callback(p, "trials", "cancel", s); callback(p, "instrumented", "timeout", s);
        assert.deepEqual(s.variables, results, "Late callbacks must preserve completed rewards");
        assert.equal(s.pp, 0); exactTotals(s);
      }
    });
}
for (const p of projects) test(`${p.id}: instrumented cancellation then other-method reentry cannot be completed by old timer`, () => {
    const s = world(); preparations(p, s); flag(s, id(p) + "_theory"); select(p, "instrumentation", s);
    const pp = s.pp; start(p, "trials", s); tick(s, p.instrumentedDays - 1);
    s.controller = "WIT"; effect(P + "projects_pulse", s);
    assert.equal(s.missions.size, 0); assert(!has(s, id(p) + "_civilian")); assert(!has(s, id(p) + "_instrumented"));
    assert(!has(s, id(p) + "_trials_revised_contract"));
    s.controller = "BAR"; select(p, "replication", s); start(p, "trials", s);
    const due = s.missions.get(id(p) + "_trials_mission");
    callback(p, "instrumented", "cancel", s); callback(p, "instrumented", "timeout", s);
    assert.equal(s.missions.get(id(p) + "_trials_mission"), due);
    tick(s, p.trialDays - 1); callback(p, "instrumented", "timeout", s); assert(!has(s, id(p) + "_done"));
    tick(s, 1); assert(has(s, id(p) + "_done"));
    assert.equal(s.pp, pp - p.instrumentedCost - p.trialCost); exactTotals(s);
});
for (const p of projects) for (const [label, invalidate] of Object.entries({ ...invalidators,
    dead_faculty: s => s.flags.delete(departments[p.department].alive),
    retired_faculty: s => s.characters.delete(departments[p.department].character)
})) test(`${p.id}/instrumented: ${label} rejects work and releases factory without a result`, () => {
    const s = world(); preparations(p, s); flag(s, id(p) + "_theory"); select(p, "instrumentation", s);
    const cold = structuredClone(s); invalidate(cold); const before = structuredClone(cold);
    start(p, "trials", cold); assert.deepEqual(cold, before);
    start(p, "trials", s); assert.equal(s.cache[P + "research"].civilian_factory_use, factories(p, "instrumented"));
    s.day = p.instrumentedDays; invalidate(s); callback(p, "instrumented", "timeout", s);
    assert(!has(s, id(p) + "_done")); assert(has(s, id(p) + "_theory"));
    assert(!has(s, id(p) + "_civilian")); assert(!has(s, id(p) + "_instrumented"));
    assert.equal(s.missions.size, 0); assert.equal(s.variables[variable("civilian_factory_use")], 0); exactTotals(s);
});
for (const p of projects) for (const stage of stages) test(`${p.id}/${stage}: AI has the same paid prerequisites and timers without GUI access`, () => {
    const s = world(); s.ai = true; preparations(p, s);
    if (stage === "trials") flag(s, id(p) + "_theory");
    assert(!condition(triggers[P + "available"], s)); assert(condition(triggers[P + "programme_access"], s));
    const pp = s.pp; finish(p, stage, s); assert.equal(s.pp, pp - stageCost(p, stage));
    assert(s.modifiers.has(P + "research")); exactTotals(s);
    s.ai = false; effect(P + "projects_pulse", s); exactTotals(s);
});
test("instrumented reservations cannot be shared by two faculties and release on cancel", () => {
    const s = world(); s.factories = 2;
    const a = projects[0], b = projects.find(p => p.department === "leopold");
    for (const p of [a, b]) { flag(s, id(p) + "_theory"); select(p, "instrumentation", s); }
    start(a, "trials", s); assert(!can(b, "trials", s));
    assert.equal(s.cache[P + "research"].civilian_factory_use, 2);
    const pp = s.pp; start(b, "trials", s); assert.equal(s.pp, pp);
    effect(id(a) + "_cancel_trials", s); assert(can(b, "trials", s));
    assert.equal(s.cache[P + "research"].civilian_factory_use, 0);
    start(b, "trials", s); assert.equal(s.missions.size, 1);
    tick(s, b.instrumentedDays); assert.equal(s.cache[P + "research"].civilian_factory_use, 0);
});
test("AI weekly dispatch is peace-only, budget-reserving and replay-safe", () => {
    const weekly = one(one(actions, "on_weekly_BAR"), "effect");
    for (const invalidate of [s => { s.ai = false; }, s => { s.war = true; }, s => { s.pp = 100; }, s => { s.owner = "WIT"; }, s => s.flags.delete("HSM_BAR_collegium")]) {
        const s = world(); s.ai = true; invalidate(s); const pp = s.pp; execute(weekly, s); assert.equal(s.missions.size, 0); assert.equal(s.pp, pp);
    }
    const s = world(); s.ai = true; s.pp = projects[0].theoryCost + 100;
    execute(weekly, s); assert.equal(s.pp, 100); assert.equal(s.missions.size, 1);
    const after = structuredClone(s); execute(weekly, s); assert.deepEqual(s, after);
    tick(s, projects[0].theoryDays); s.pp = projects[0].trialCost + 100;
    execute(weekly, s); assert.equal(s.pp, 100); assert(!has(s, id(projects[0]) + "_civilian"));
    assert(!has(s, id(projects[0]) + "_field"));
    assert(!has(s, id(projects[0]) + "_instrumented"));
});
test("AI completes all 26 fixed outcomes conservatively; opuses still require five completed preparations", () => {
    const s = world(); s.ai = true; const weekly = one(one(actions, "on_weekly_BAR"), "effect");
    for (let day = 0; day < 1000 && !projects.every(p => has(s, id(p) + "_done")); day++) {
        if (day % 7 === 0) execute(weekly, s);
        for (const p of projects.filter(p => p.opus && (has(s, id(p) + "_theory_running") || has(s, id(p) + "_trials_running")))) {
            for (const q of projects.filter(q => q.department === p.department && !q.opus && !q.partners)) assert(has(s, id(q) + "_done"));
        }
        tick(s, 1); effect(P + "projects_pulse", s);
    }
    assert(projects.every(p => has(s, id(p) + "_done"))); assert.equal(s.missions.size, 0);
    assert.equal(s.pp, 10000 - 2145);
    for (const p of projects) {
        for (const f of ["civilian", "field", "experiment_active", "observation_ready", "verify_running", "experiment_record"])
            assert(!has(s, id(p) + "_" + f), "Legacy AI must autocomplete without interactive checkpoints");
    }
    assert.equal(s.variables[variable("political_power_gain")], 0); exactTotals(s);
});
test("AI honors clinical moratorium and absent faculty, and resumes without advancing blocked trials", () => {
    const s = world(); s.ai = true;
    for (const p of projects.filter(p => p.department !== "silver")) flag(s, id(p) + "_done");
    for (const p of projects.filter(p => p.department === "silver" && !p.opus)) flag(s, id(p) + "_theory");
    const p = projects.find(p => p.id === "necrotic_suture");
    flag(s, "HSM_BAR_collegium_trial_pause"); const pp = s.pp;
    effect(P + "projects_ai_week", s); assert.equal(s.missions.size, 0); assert.equal(s.pp, pp);
    s.flags.delete("HSM_BAR_collegium_trial_pause"); s.characters.delete(departments.silver.character);
    tick(s, 7); effect(P + "projects_ai_week", s); assert.equal(s.missions.size, 0); assert.equal(s.pp, pp);
    s.characters.add(departments.silver.character); tick(s, 7); effect(P + "projects_ai_week", s);
    assert(has(s, id(p) + "_trials_running")); assert.equal(s.pp, pp - p.trialCost);
    // Moratorium only blocks new admissions, matching the pre-existing clinic policy.
    flag(s, "HSM_BAR_collegium_trial_pause"); tick(s, p.trialDays); assert(has(s, id(p) + "_done")); exactTotals(s);
});
test("teardown clears policies, snapshots, reservations and AI cadence; old callbacks cannot restore work", () => {
    const s = world(); s.ai = true; effect(P + "projects_ai_week", s);
    s.ai = false; effect(id(projects[0]) + "_cancel_theory", s);
    const p = projects[0]; flag(s, id(p) + "_theory"); select(p, "instrumentation", s); start(p, "trials", s);
    flag(s, P + p.department + "_civilian"); flag(s, id(p) + "_civilian"); flag(s, id(p) + "_field");
    effect(P + "projects_teardown", s);
    for (const f of ["ai_dispatch", "ai_week_tick", "viira_instrumented", "viira_civilian", "field_atlas_instrumented", "field_atlas_civilian"]) assert(!has(s, P + f));
    for (const q of projects) for (const f of ["civilian", "field", "theory_revised_contract", "trials_revised_contract"]) assert(!has(s, id(q) + "_" + f));
    assert.equal(s.missions.size, 0); callback(p, "instrumented", "timeout", s); assert(!has(s, id(p) + "_done"));
    start(p, "theory", s); callback(p, "instrumented", "cancel", s); assert(has(s, id(p) + "_theory_running"));
});
test("completed old saves receive unified results with no new payment or upkeep regardless of application flags", () => {
    const clean = world(); for (const p of projects) flag(clean, id(p) + "_done");
    effect(P + "projects_pulse", clean);
    for (const flags of [[], ["civilian"], ["field"], ["civilian", "field"]]) {
        const s = world();
        for (const p of projects) { flag(s, id(p) + "_done"); for (const f of flags) flag(s, id(p) + "_" + f); }
        for (const d of Object.keys(departments)) { for (const f of flags) flag(s, P + d + "_" + f); effect(P + d + "_select_instrumentation", s); }
        // Simulate cached values from a previous version, including field upkeep.
        s.variables[variable("political_power_gain")] = -0.25;
        s.variables[variable("research_speed_factor")] = 0.025;
        effect(P + "projects_pulse", s);
        assert.deepEqual(s.variables, clean.variables);
        assert.equal(s.variables[variable("research_speed_factor")], 0.18);
        for (const p of projects) { start(p, "trials", s); callback(p, "instrumented", "timeout", s); }
        tick(s, 30); effect(P + "projects_pulse", s);
        assert.deepEqual(s.variables, clean.variables); assert.equal(s.pp, 10000); assert.equal(s.missions.size, 0); exactTotals(s);
    }
});

test("two joint dossiers have explicit original prerequisites and bounded authored outcomes", () => {
    const joints = projects.filter(p => p.partners);
    assert.deepEqual(joints.map(p => [p.id, p.number, p.department, p.partners, p.prerequisites, p.outcome]), [
        ["sensate_prosthesis", 25, "leopold", ["silver"], ["prosthetics", "phantom_pain"], "partial"],
        ["interrupt_notation", 26, "viira", ["asinti"], ["spell_notation", "ritual_brake"], "success"]
    ]);
    assert.deepEqual(B.rewards.sensate_prosthesis, {experience_loss_factor: -0.05, army_org_regain: 0.05});
    assert.deepEqual(B.rewards.interrupt_notation, {supply_consumption_factor: -0.05, modifier_army_sub_unit_category_magical_infantry_max_org_factor: 0.05});
});
for (const p of projects.filter(p => p.partners)) {
    test(`${p.id}: every prerequisite subset, both stages, counters and theory cannot substitute for conclusions`, () => {
        for (const stage of stages) for (let bits = 0; bits < 4; bits++) {
            const s = world();
            for (const d of [p.department, ...p.partners]) s.variables[P + d + "_completed"] = 5;
            for (const q of projects.filter(q => !p.prerequisites.includes(q.id) && q.id !== p.id)) flag(s, id(q) + "_done");
            p.prerequisites.forEach((q,i) => { flag(s, P + q + "_theory"); if (bits & (1 << i)) flag(s, P + q + "_done"); });
            if (stage === "trials") flag(s, id(p) + "_theory");
            assert.equal(can(p, stage, s), bits === 3);
            if (bits !== 3) { const before = structuredClone(s); start(p, stage, s); assert.deepEqual(s, before); }
        }
        for (const q of p.prerequisites) for (const stage of stages) {
            const s = world(); preparations(p,s); if (stage === "trials") flag(s,id(p)+"_theory");
            start(p,stage,s); s.flags.delete(P+q+"_done"); s.day += stageDays(p,stage);
            callback(p,stage,"timeout",s); assert(!has(s,id(p)+"_done")); assert.equal(s.missions.size,0);
        }
    });
    test(`${p.id}: both faculties lock, other faculties stay free, one reservation and one invoice`, () => {
        const s = world(); preparations(p,s); flag(s,id(p)+"_theory"); s.factories=3;
        select(p,"instrumentation",s); const pp=s.pp;
        start(p,"trials",s); assert.equal(s.pp,pp-p.instrumentedCost);
        assert.equal(s.missions.size,1); assert.equal(s.variables[variable("civilian_factory_use")],2);
        for (const d of [p.department,...p.partners]) {
            assert(has(s,P+d+"_busy"));
            const q=projects.find(q=>q.department===d&&!q.opus&&!q.partners&&!p.prerequisites.includes(q.id));
            assert(!can(q,"theory",s));
            const before=structuredClone(s); for(const choice of ["replication","instrumentation"]) effect(P+d+"_select_"+choice,s);
            assert.deepEqual(s,before);
        }
        for (const d of Object.keys(departments).filter(d=>![p.department,...p.partners].includes(d))) assert(can(projects.find(q=>q.department===d),"theory",s));
        effect(id(p)+"_cancel_trials",s); assert.equal(s.missions.size,0); assert.equal(s.variables[variable("civilian_factory_use")],0);
        for(const d of [p.department,...p.partners]) assert(!has(s,P+d+"_busy"));
        assert(has(s,id(p)+"_theory")); assert(!has(s,id(p)+"_done")); assert.equal(s.pp,pp-p.instrumentedCost);
        exactTotals(s);
        for(const d of [p.department,...p.partners]) for(const orphan of [false,true]) {
            const t=world(); preparations(p,t);
            const q=projects.find(q=>q.department===d&&!q.opus&&!q.partners&&!p.prerequisites.includes(q.id));
            if(orphan)t.missions.set(id(q)+"_theory_mission",q.theoryDays); else start(q,"theory",t);
            assert(!can(p,"theory",t));
        }
    });
    for(const d of [p.department,...p.partners]) for(const method of ["theory","trials","instrumented"]) for(const loss of ["life","character"]) test(`${p.id}/${method}: ${d} ${loss} loss cancels both locks at timeout and rejects fresh starts`,()=>{
        const s=world(); preparations(p,s); const stage=method==="theory"?"theory":"trials";
        if(stage==="trials")flag(s,id(p)+"_theory"); if(method==="instrumented")select(p,"instrumentation",s);
        const invalidate=t=>loss==="life"?t.flags.delete(departments[d].alive):t.characters.delete(departments[d].character);
        const cold=structuredClone(s); invalidate(cold); const before=structuredClone(cold); start(p,stage,cold); assert.deepEqual(cold,before);
        start(p,stage,s); s.day+=method==="instrumented"?p.instrumentedDays:stageDays(p,stage); invalidate(s); callback(p,method,"timeout",s);
        assert(!has(s,id(p)+"_done")); assert.equal(s.missions.size,0);
        for(const department of [p.department,...p.partners])assert(!has(s,P+department+"_busy")); exactTotals(s);
    });
    test(`${p.id}: teardown releases a live joint trial, old callbacks cannot recreate it`,()=>{
        const s=world(); preparations(p,s); flag(s,id(p)+"_theory"); select(p,"instrumentation",s); start(p,"trials",s);
        assert.equal(s.missions.size,1); effect(P+"projects_teardown",s);
        for(const method of ["theory","trials","instrumented"]){callback(p,method,"timeout",s);callback(p,method,"cancel",s);}
        assert.equal(s.missions.size,0); assert(!has(s,id(p)+"_theory")); assert(!has(s,id(p)+"_done"));
        assert.equal(s.variables[variable("civilian_factory_use")],0);
        for(const department of [p.department,...p.partners]) assert(!has(s,P+department+"_busy"));
    });
}
test("joint clinical admissions honor Silver's moratorium without cancelling ongoing care",()=>{
    const p=projects.find(p=>p.id==="sensate_prosthesis"),s=world(); preparations(p,s); flag(s,"HSM_BAR_collegium_trial_pause");
    finish(p,"theory",s); assert(!can(p,"trials",s));
    s.flags.delete("HSM_BAR_collegium_trial_pause"); start(p,"trials",s); flag(s,"HSM_BAR_collegium_trial_pause"); tick(s,p.trialDays);
    assert(has(s,id(p)+"_done")); exactTotals(s);
});
for(const p of projects) test(`${p.id}: actual journal policies, paid start, busy rejection, cancel and restart`,()=>{
    const s=world(); preparations(p,s); flag(s,id(p)+"_theory");
    Object.assign(s.variables,{HSM_BAR_mtk_open:1,HSM_BAR_mtk_project:p.number,HSM_BAR_mtk_department:Object.keys(departments).indexOf(p.partners?.[0]||p.department)+1,HSM_BAR_mtk_document:5});
    const click=key=>execute(journalEffects[P+key+"_click"],s);
    const initialPP=s.pp;
    for(const choice of ["instrumentation","replication","instrumentation"])click(`policy_${p.department}_${choice}`);
    assert(has(s,P+p.department+"_instrumented")); assert.equal(s.pp,initialPP);
    for(const axis of ["rig","control"])click(`${p.id}_prepare_${axis}_a`);
    click(`start_${p.id}_trials`); assert.equal(s.pp,initialPP-p.instrumentedCost); assert.equal(s.missions.size,1);
    const paid=structuredClone(s); click(`policy_${p.department}_replication`); click(`start_${p.id}_trials`); assert.deepEqual(s,paid);
    click(`cancel_${p.id}_trials`); assert.equal(s.missions.size,0); assert(has(s,id(p)+"_theory")); assert(!has(s,id(p)+"_done"));
    const cancelled=structuredClone(s); click(`cancel_${p.id}_trials`); assert.deepEqual(s,cancelled);
    click(`policy_${p.department}_replication`);
    for(const axis of ["rig","control"])click(`${p.id}_prepare_${axis}_a`);
    click(`start_${p.id}_trials`);
    callback(p,"instrumented","timeout",s); callback(p,"instrumented","cancel",s); assert(has(s,id(p)+"_trials_running"));
    tick(s,p.trialDays); assert(has(s,id(p)+"_observation_ready")); assert(!has(s,id(p)+"_done"));
    const response=JSON.parse(fs.readFileSync(path.join(__dirname,"data/barrad-collegium-experiments.json"),"utf8")).find(e=>e.id===p.id).responses[0];
    click(`${p.id}_respond_a`); tick(s,response.days[0]);
    assert(has(s,id(p)+"_done")); assert(has(s,id(p)+"_experiment_record")); assert(!has(s,id(p)+"_field")); assert(!has(s,id(p)+"_civilian"));
    click(`cancel_${p.id}_trials`); assert(has(s,id(p)+"_done")); assert.equal(s.pp,initialPP-p.instrumentedCost-p.trialCost-response.cost[0]); exactTotals(s);
});
test("all eight actual journal method handlers reject foreign, closed, wrong-page and missing faculty calls",()=>{
    for(const d of Object.keys(departments))for(const choice of ["replication","instrumentation"])for(const invalidate of [
        s=>{s.tag="WIT";},s=>{s.ai=true;},s=>{delete s.variables.HSM_BAR_mtk_open;},s=>{s.variables.HSM_BAR_mtk_document=1;},
        s=>{s.variables.HSM_BAR_mtk_project=0;},s=>s.flags.delete(departments[d].alive),s=>s.characters.delete(departments[d].character)
    ]){
        const s=world(),p=projects.find(p=>p.department===d);Object.assign(s.variables,{HSM_BAR_mtk_open:1,HSM_BAR_mtk_project:p.number,HSM_BAR_mtk_department:Object.keys(departments).indexOf(d)+1,HSM_BAR_mtk_document:5});
        if(choice==="replication")flag(s,P+d+"_instrumented");
        invalidate(s);const before=structuredClone(s);execute(journalEffects[P+`policy_${d}_${choice}_click`],s);assert.deepEqual(s,before);
    }
});

require("./Test-BarradCollegiumExperiments.cjs")({ B, P, projects, departments, modifiers, variable, id, test, world,
    flag, has, preparations, select, effect, condition, execute, triggers, effects, missions, journalEffects,
    one, walk, tick, callback, expected, exactTotals, invalidators });

if (process.argv.includes("--native")) {
    const arg = (key, fallback) => process.argv.includes(key) ? process.argv[process.argv.indexOf(key) + 1] : fallback;
    const game = arg("--game-root", process.env.HOI4_GAME_ROOT || "C:/shit/Steam/steamapps/common/Hearts of Iron IV");
    const eaw = arg("--eaw-root", process.env.EAW_ROOT || "C:/shit/Steam/steamapps/workshop/content/394360/1826643372");
    const nativeRead = (base, file) => fs.readFileSync(path.join(base, file), "utf8");
    test("installed engine and EaW validate every modifier and native faculty ID", () => {
        const doc = nativeRead(game, "documentation/modifiers_documentation.md");
        const unit = nativeRead(eaw, "common/units/unit_modifiers/eaw_unit_modifiers.txt");
        const deployed = nativeRead(eaw, "common/dynamic_modifiers/ED_dynamic_modifiers.txt");
        for (const modifier of modifiers) {
            if (modifier.startsWith("modifier_army_sub_unit_")) { assert(unit.includes(modifier)); assert(deployed.includes(modifier + " =")); }
            else assert(new RegExp("^## " + modifier + "\\r?$", "m").test(doc), modifier);
        }
        const characters = nativeRead(eaw, "common/characters/BAR.txt");
        const deaths = nativeRead(eaw, "common/scripted_effects/EAW_BAR_effect.txt");
        for (const faculty of Object.values(departments)) {
            assert(new RegExp("\\b" + faculty.character + "\\s*=\\s*\\{").test(characters));
            assert(deaths.includes("clr_country_flag = " + faculty.alive));
        }
    });
    test("installed mission API, used predicates, icons and native mission patterns", () => {
        const effectDoc = nativeRead(game, "documentation/effects_documentation.md");
        const triggerDoc = nativeRead(game, "documentation/triggers_documentation.md");
        for (const key of ["activate_mission", "remove_mission", "add_dynamic_modifier", "force_update_dynamic_modifier"]) assert(effectDoc.includes("## " + key + "\n"));
        assert(effectDoc.includes("Removes mission without running complete or timeout effects"));
        const nativePredicates = new Set();
        function collectPredicates(nodes) {
            for (const n of nodes) {
                if (["AND", "OR", "NOT"].includes(n.key)) collectPredicates(n.value);
                else if (triggers[n.key]) assert(["yes", "no"].includes(n.value), n.key);
                else {
                    nativePredicates.add(n.key);
                    if (Array.isArray(n.value)) assert(["has_country_flag", "check_variable"].includes(n.key), n.key);
                }
            }
        }
        collectPredicates(Object.values(triggers).flat());
        for (const key of nativePredicates) assert(triggerDoc.includes("## " + key + "\n"), key);
        const nativeMissions = nativeRead(eaw, "common/decisions/BAR_decisions.txt");
        for (const key of ["activation", "days_mission_timeout", "timeout_effect", "cancel_effect", "cancel_trigger"]) assert(new RegExp("\\b" + key + "\\s*=").test(nativeMissions));
        assert(nativeRead(game, "interface/decisions.gfx").includes('name = "GFX_decision_generic_research"'));
        assert(nativeRead(eaw, "common/on_actions/_documentation.md").includes("`on_weekly_TAG`"));
        assert(nativeRead(eaw, "common/on_actions/eaw_EQS_on_actions.txt").includes("on_weekly_EQS"));
        assert(nativeMissions.includes("civilian_factory_use = 2"));
        assert(nativeMissions.includes("cancel_if_not_visible = yes"), "Installed native boolean controls visibility cancellation");
        assert(nativeRead(game, "common/decisions/_documentation.md").includes("Used to filter out decisions that should appear in decision interface"));
        assert.equal(one(dynamic, "icon"), "GFX_idea_HSM_BAR_art_collegium", "Parent-owned art registration contract");
    });
}
console.log(`Barrad Collegium projects: ${passed} scenarios passed; ${failed} failed. 26 projects / ${Object.keys(missions).length} hidden timed missions / 8 journal method choices.`);
console.log("Boundary: executes generated gameplay scripts in deterministic fixtures; native HOI4 scheduling and GUI still need an in-game playtest.");
process.exitCode = failed ? 1 : 0;
