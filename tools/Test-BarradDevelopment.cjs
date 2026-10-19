"use strict";

// node tools/Test-BarradDevelopment.cjs [--eaw-root PATH]
// Deterministic script fixtures, not an HOI4 runtime or a rendered tree check.
// Native EaW development effects execute from the installed mod, not replicas.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const F = require("./Test-BarradCases.cjs");
const { parse, read, prop, dictionary, mod } = F;
const root = path.resolve(__dirname, "..");
const argIndex = process.argv.indexOf("--eaw-root");
if (argIndex >= 0) assert(process.argv[argIndex + 1] && !process.argv[argIndex + 1].startsWith("--"), "Missing --eaw-root path");
const eaw = argIndex >= 0 ? process.argv[argIndex + 1] : process.env.EAW_ROOT || "C:/shit/Steam/steamapps/workshop/content/394360/1826643372";
const nativeRead = file => parse(fs.readFileSync(path.join(eaw, file), "utf8"));
const walk = nodes => nodes.flatMap(n => [n, ...(Array.isArray(n.value) ? walk(n.value) : [])]);
const many = (nodes, key) => nodes.filter(n => n.key === key);
function one(nodes, key) {
    const found = many(nodes, key);
    assert.equal(found.length, 1, "Expected one " + key);
    return found[0].value;
}
const nativeEffectFile = "common/scripted_effects/EAW_misc_effect.txt";
const nativeTriggerFile = "common/scripted_triggers/EAW_triggers.txt";
const nativeEffects = nativeRead(nativeEffectFile);
const nativeTriggers = nativeRead(nativeTriggerFile);
const helperNames = ["decrease_poverty", "decrease_illiteracy", "increase_society_development", "increase_science_base"];
const nativeTriggerNames = ["has_poverty", "has_illiteracy", "has_tribal_society", "has_agrarian_society", "has_pre_industrial_society", "has_outdated_industry"];
const effects = Object.fromEntries(helperNames.map(id => [id, one(nativeEffects, id)]));
Object.assign(effects, dictionary(read("common/scripted_effects/HSM_BAR_social_survey.txt")));
effects.HSM_BAR_establish_institute = one(read("common/scripted_effects/HSM_BAR_research_effects.txt"), "HSM_BAR_establish_institute");
effects.HSM_BAR_dissolve_institutions = one(read("common/scripted_effects/HSM_BAR_core_effects.txt"), "HSM_BAR_dissolve_institutions");
effects.HSM_BAR_collegium_remove_constitution = one(read("common/scripted_effects/HSM_BAR_collegium_effects.txt"), "HSM_BAR_collegium_remove_constitution");
const triggers = {
    ...dictionary(read("common/scripted_triggers/HSM_BAR_development.txt")),
    ...Object.fromEntries(nativeTriggerNames.map(id => [id, one(nativeTriggers, id)]))
};
const common = read("common/national_focus/HSM_BAR_common.txt");
const focuses = dictionary(common.filter(n => n.key === "shared_focus").map(n => ({ key: one(n.value, "id"), value: n.value })));
const decisionNodes = read("common/decisions/HSM_BAR_development.txt");
assert.equal(decisionNodes.length, 1, "Expected one development category");
const decisions = dictionary(decisionNodes[0].value);
const category = one(read("common/decisions/categories/HSM_BAR_development.txt"), decisionNodes[0].key);
const eventNodes = read("events/HSM_BAR_development.txt");
const events = dictionary(many(eventNodes, "country_event").map(n => ({ key: one(n.value, "id"), value: n.value })));
const routeFiles = ["HSM_BAR_republic.txt", "HSM_BAR_collegium.txt", "HSM_BAR_directorate.txt"];
const routeNodes = routeFiles.flatMap(file => read("common/national_focus/" + file));
const oldFocusIds = ["common_reconstruction", "public_works", "land_register", "workshops", "neighbour_conference", "technical_school", "border_watch", "magical_institute", "defence_stores", "reconstruction_accounts"];
const newFocusIds = ["food_cooperatives", "village_schools", "teacher_training", "clean_water", "power_grid", "machine_tools", "workers_housing", "polytechnic", "industrial_standards", "regional_markets", "civil_laboratories", "extension_schools", "precision_industry", "scholarships", "research_council", "national_grid", "social_insurance", "developed_republic"];
const programSpecs = [
    ["living_standards", "land_register", "decrease_poverty", "has_poverty", 50, 120, ["poverty", "poverty1", "poverty2", "poverty3", "poverty4", "poverty5", "no_poverty"]],
    ["school_network", "village_schools", "decrease_illiteracy", "has_illiteracy", 50, 120, ["lack_of_scientists", "lack_of_scientists1", "lack_of_scientists2", "lack_of_scientists3", "no_lack_of_scientists"]],
    ["industrial_program", "power_grid", "increase_society_development", null, 75, 180, ["tribal_society", "agrarian_society", "pre_industrial_society", "outdated_industry", "modern_society"]],
    ["research_grants", "civil_laboratories", "increase_science_base", null, 75, 180, ["poor_science_base", "better_science_base", "big_science_base", "proper_science_base"]]
].map(([name, focus, helper, trigger, cost, days, ladder]) => ({ id: "HSM_BAR_development_" + name, focus: "HSM_BAR_" + focus, helper, trigger, cost, days, ladder }));

function world(route = "directorate", slots = 2) {
    const w = F.world(false), s = w.root;
    s.flags = new Set(["HSM_BAR_active", "HSM_BAR_" + route]);
    s.ideas = new Set();
    s.focuses = new Set();
    s.slots = slots;
    s.pp = 10000;
    s.stability = 0.5;
    s.warSupport = 0.4;
    s.armyExperience = 0;
    s.technologies = new Set();
    s.war = false;
    for (const tag of ["EQS", "WIT", "ZES", "OLV"]) w.countries[tag] = { id: tag, flags: new Set(), ideas: new Set(), opinions: new Set() };
    s.opinions = new Set();
    w.effectCalls = [];
    for (const state of Object.values(w.states)) { state.buildings = {}; state.extraSlots = 0; }
    return w;
}
function condition(nodes, w, s = w.root) {
    assert(Array.isArray(nodes), "Expected condition block");
    return nodes.every(n => {
        const v = n.value;
        if (["AND", "hidden_trigger"].includes(n.key)) return condition(v, w, s);
        if (n.key === "OR") return v.some(c => condition([c], w, s));
        if (["NOT", "NOR"].includes(n.key)) return !v.some(c => condition([c], w, s));
        if (n.key === "custom_trigger_tooltip") return condition(v.filter(c => c.key !== "tooltip"), w, s);
        if (n.key === "always") return v === "yes";
        if (["tag", "original_tag"].includes(n.key)) return s.id === v;
        if (n.key === "has_country_flag") return s.flags.has(v);
        if (n.key === "has_idea") return s.ideas.has(v);
        if (n.key === "has_completed_focus") return s.focuses.has(v);
        if (n.key === "has_capitulated") return s.capitulated === (v === "yes");
        if (n.key === "has_war") return s.war === (v === "yes");
        if (n.key === "has_dlc") return w.dlc.has(v);
        if (n.key === "owns_state") return w.states[v]?.owner === s.id;
        if (n.key === "controls_state") return w.states[v]?.controller === s.id;
        if (n.key === "is_owned_by") return s.owner === (v === "ROOT" || v === "PREV" ? w.root.id : v);
        if (n.key === "is_controlled_by") return s.controller === (v === "ROOT" || v === "PREV" ? w.root.id : v);
        if (n.key === "is_fully_controlled_by") return s.owner === s.controller && s.owner === (v === "ROOT" || v === "PREV" ? w.root.id : v);
        if (n.key === "capital_scope") return condition(v, w, w.states[624]);
        if (n.key === "amount_research_slots") {
            const expected = Number(v);
            if (n.op === "<") return s.slots < expected;
            if (n.op === ">") return s.slots > expected;
            if (n.op === "=") return s.slots === expected;
            throw Error("Unsupported slot comparator " + n.op);
        }
        if (Object.hasOwn(triggers, n.key)) {
            assert(["yes", "no"].includes(v), "Unsupported trigger arguments " + n.key);
            return condition(triggers[n.key], w, s) === (v === "yes");
        }
        if (Object.hasOwn(w.states, n.key)) return condition(v, w, w.states[n.key]);
        throw Error("Unsupported development predicate " + n.key);
    });
}
function run(nodes, w, s = w.root) {
    assert(Array.isArray(nodes), "Expected effect block");
    for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i], v = n.value;
        if (n.key === "if") {
            let taken = false;
            do {
                const branch = nodes[i];
                if (!taken && (branch.key === "else" || condition(one(branch.value, "limit"), w, s))) {
                    run(branch.value.filter(c => c.key !== "limit"), w, s);
                    taken = true;
                }
                if (!["else_if", "else"].includes(nodes[i + 1]?.key)) break;
                i++;
            } while (true);
        } else if (n.key === "hidden_effect") run(v, w, s);
        // An effect_tooltip previews native effects but cannot execute them.
        else if (n.key === "effect_tooltip") {
            assert(Array.isArray(v));
            for (const entry of v) {
                assert(helperNames.includes(entry.key), "Unsupported preview command " + entry.key);
                assert.equal(entry.value, "yes");
            }
        }
        else if (n.key === "swap_ideas") {
            assert.deepEqual(v.map(c => c.key).sort(), ["add_idea", "remove_idea"]);
            s.ideas.delete(one(v, "remove_idea"));
            s.ideas.add(one(v, "add_idea"));
        } else if (n.key === "add_ideas" || n.key === "remove_ideas") {
            for (const id of Array.isArray(v) ? v.map(c => c.key) : [v]) s.ideas[n.key === "add_ideas" ? "add" : "delete"](id);
        } else if (n.key === "set_country_flag") { assert.equal(typeof v, "string"); s.flags.add(v); }
        else if (n.key === "clr_country_flag") { assert.equal(typeof v, "string"); s.flags.delete(v); }
        else if (n.key === "add_research_slot") s.slots += Number(v);
        else if (n.key === "add_political_power") s.pp += Number(v);
        else if (n.key === "add_stability") s.stability += Number(v);
        else if (n.key === "add_war_support") s.warSupport += Number(v);
        else if (n.key === "army_experience") s.armyExperience += Number(v);
        else if (n.key === "add_tech_bonus") s.bonuses.push(v);
        else if (n.key === "add_to_variable") {
            assert.equal(v.length, 1);
            s.vars[v[0].key] = (s.vars[v[0].key] || 0) + Number(v[0].value);
        } else if (n.key === "set_technology") {
            for (const entry of v) {
                if (entry.key === "popup") { assert.equal(entry.value, "no"); continue; }
                assert.equal(entry.value, "1"); s.technologies.add(entry.key);
            }
        } else if (n.key === "country_event") s.events.push(one(v, "id"));
        else if (n.key === "random_owned_controlled_state") {
            const state = Object.values(w.states).find(c => c.owner === s.id && c.controller === s.id && condition(prop(v, "limit") || [], w, c));
            if (state) run(v.filter(c => c.key !== "limit"), w, state);
        } else if (n.key === "capital_scope") run(v, w, w.states[624]);
        else if (Object.hasOwn(w.states, n.key)) run(v, w, w.states[n.key]);
        else if (Object.hasOwn(w.countries, n.key)) run(v, w, w.countries[n.key]);
        else if (n.key === "add_extra_state_shared_building_slots") s.extraSlots += Number(v);
        else if (n.key === "add_building_construction") {
            assert.equal(one(v, "instant_build"), "yes");
            const type = one(v, "type");
            s.buildings[type] = (s.buildings[type] || 0) + Number(one(v, "level"));
        } else if (["HSM_BAR_core_refresh", "HSM_BAR_refresh_service_training", "HSM_BAR_refresh_case_outcomes"].includes(n.key)) {
            assert.equal(v, "yes"); assert.equal(s, w.root);
            F.run([n], w);
        } else if (["remove_dynamic_modifier", "clear_variable"].includes(n.key)) {
            assert.equal(s, w.root); F.run([n], w);
        } else if (n.key === "remove_opinion_modifier") {
            assert.deepEqual(v.map(c => c.key).sort(), ["modifier", "target"]);
            s.opinions.delete(one(v, "target") + ":" + one(v, "modifier"));
        } else if (Object.hasOwn(effects, n.key)) {
            assert.equal(v, "yes", "Unexpected helper arguments " + n.key);
            w.effectCalls.push(n.key);
            run(effects[n.key], w, s);
        } else if (n.key === "custom_effect_tooltip" || n.key === "log") {
            assert.equal(typeof v, "string");
        } else throw Error("Unsupported development effect " + n.key);
    }
}
function prepare(spec, route = "directorate", idea = spec.ladder[0]) {
    const w = world(route);
    w.root.focuses.add(spec.focus);
    if (idea) w.root.ideas.add(idea);
    return w;
}
const visible = (spec, w) => condition(prop(category, "visible") || [], w) && condition(one(decisions[spec.id], "visible"), w);
const available = (spec, w) => condition(one(decisions[spec.id], "available"), w);
const callback = (spec, key, w) => run(one(decisions[spec.id], key), w);
const stateOf = w => JSON.stringify({ ideas: [...w.root.ideas].sort(), slots: w.root.slots, pp: w.root.pp, events: w.root.events, calls: w.effectCalls });
function start(spec, w) {
    assert(visible(spec, w), "Program hidden: " + spec.id);
    assert(available(spec, w), "Program unavailable: " + spec.id);
    w.root.pp -= Number(one(decisions[spec.id], "cost"));
    callback(spec, "complete_effect", w);
}
function completeFocus(id, w) {
    const f = focuses[id];
    assert(f, "Missing focus " + id);
    assert(!w.root.focuses.has(id), "Already completed " + id);
    for (const group of many(f, "prerequisite")) assert(group.value.some(n => n.key === "focus" && w.root.focuses.has(n.value)), "Missing prerequisite " + id);
    assert(condition(prop(f, "available") || [], w), "Focus unavailable: " + id);
    run(one(f, "completion_reward"), w);
    w.root.focuses.add(id);
}
function completeBranch(w) {
    const pending = new Set(Object.keys(focuses));
    while (pending.size) {
        let advanced = false;
        for (const id of pending) {
            const f = focuses[id];
            if (!many(f, "prerequisite").every(g => g.value.some(n => w.root.focuses.has(n.value)))) continue;
            if (!condition(prop(f, "available") || [], w)) continue;
            completeFocus(id, w); pending.delete(id); advanced = true;
        }
        assert(advanced, "Unreachable development focuses: " + [...pending].join(", "));
    }
}
let passed = 0, failed = 0;
function scenario(name, fn) {
    try { fn(); passed++; console.log("PASS: " + name); }
    catch (error) { failed++; console.error("FAIL: " + name + "\n" + error.stack); }
}
console.log("EaW source: " + eaw);
scenario("strict fixtures reject unknown conditions and effects", () => {
    assert.throws(() => condition(parse("invented_condition = yes"), world()), /Unsupported development predicate/);
    assert.throws(() => run(parse("invented_effect = yes"), world()), /Unsupported development effect/);
    assert.throws(() => run(parse("effect_tooltip = { invented_effect = yes }"), world()), /Unsupported preview command/);
});
scenario("installed EaW helpers and predicates match the bundled snapshot where present", () => {
    for (const [file, names] of [[nativeEffectFile, helperNames], [nativeTriggerFile, nativeTriggerNames]]) {
        const snapshot = path.join(root, "EaW", file);
        if (!fs.existsSync(snapshot)) continue;
        const bundled = parse(fs.readFileSync(snapshot, "utf8")), installed = nativeRead(file);
        for (const name of names) assert.deepEqual(one(installed, name), one(bundled, name), "EaW snapshot drift: " + name);
    }
    const history = nativeRead("history/countries/BAR - Baard.txt");
    assert.equal(one(history, "set_research_slots"), "2");
});
scenario("28 connected shared focuses retain the original IDs, use short durations and distinct positions", () => {
    assert.deepEqual(Object.keys(focuses).sort(), [...oldFocusIds, ...newFocusIds].map(id => "HSM_BAR_" + id).sort());
    assert.equal(one(focuses.HSM_BAR_common_reconstruction, "x"), "26");
    const positions = new Set();
    for (const [id, f] of Object.entries(focuses)) {
        assert(["4", "5"].includes(one(f, "cost")), id + " duration");
        const position = one(f, "x") + "," + one(f, "y");
        assert(!positions.has(position), "Overlapping focus " + id); positions.add(position);
        const prerequisites = many(f, "prerequisite");
        if (id !== "HSM_BAR_common_reconstruction") assert(prerequisites.length, "Disconnected focus " + id);
        for (const group of prerequisites) for (const n of group.value) { assert.equal(n.key, "focus"); assert(focuses[n.value], id + " external prerequisite " + n.value); }
        for (const key of ["allow_branch", "mutually_exclusive"]) assert.equal(prop(f, key), undefined, id + " gated by " + key);
    }
});
scenario("all five custom trees include the same reconstruction root exactly once", () => {
    const trees = many(routeNodes, "focus_tree");
    assert.equal(trees.length, 5);
    for (const t of trees) assert.equal(t.value.filter(n => n.key === "shared_focus" && n.value === "HSM_BAR_common_reconstruction").length, 1, prop(t.value, "id"));
});
scenario("every development focus checks homeland access, permits war and needs neither government nor anomaly knowledge", () => {
    for (const route of ["collegium", "directorate"]) for (const [id, f] of Object.entries(focuses)) {
        const w = world(route), gate = one(f, "available");
        assert(condition(gate, w), id);
        w.root.war = true;
        assert(condition(gate, w), "Wartime focus blocked: " + id);
        for (const invalidate of [
            s => s.root.flags.clear(),
            s => { s.root.capitulated = true; },
            s => { s.states[624].owner = "WIT"; },
            s => { s.states[624].controller = "WIT"; }
        ]) {
            const invalid = world(route); invalidate(invalid);
            assert(!condition(gate, invalid), "Unavailable homeland allowed focus: " + id);
        }
    }
});
scenario("native development is not replaced by a currency or the retired society decision", () => {
    const commands = walk([...common, ...decisionNodes]);
    for (const name of helperNames) assert(commands.some(n => n.key === name && n.value === "yes"), "Missing native helper " + name);
    assert(!commands.some(n => /^(?:set|add_to|subtract_from|multiply|divide|clamp)_variable$/.test(n.key)), "Development introduced a currency or retired meter");
    const allFocusCommands = walk([...common, ...routeNodes]);
    assert(!allFocusCommands.some(n => n.key === "set_country_flag" && n.value === "BAR_upgrade_society_pp"), "Retired upgrade decision is still granted");
});
for (const spec of programSpecs) {
    scenario(spec.id + ": actual native helper advances each tier once and stops at maximum", () => {
        for (let i = 0; i < spec.ladder.length; i++) {
            const w = prepare(spec, "directorate", spec.ladder[i]);
            run(parse(spec.helper + " = yes"), w);
            assert.deepEqual([...w.root.ideas], [spec.ladder[Math.min(i + 1, spec.ladder.length - 1)]]);
            if (spec.trigger) assert.equal(condition(parse(spec.trigger + " = yes"), w), i + 1 < spec.ladder.length - 1);
        }
        const empty = prepare(spec, "directorate", null);
        run(parse(spec.helper + " = yes"), empty);
        assert.equal(empty.root.ideas.size, 0, "Helper manufactured a missing society idea");
    });
    scenario(spec.id + ": cost, duration, repeatability and exact single helper contract", () => {
        const d = decisions[spec.id]; assert(d);
        assert.equal(Number(one(d, "cost")), spec.cost);
        assert.equal(Number(one(d, "days_remove")), spec.days);
        assert.notEqual(prop(d, "fire_only_once"), "yes");
        const expiry = one(d, "remove_effect");
        assert.equal(walk(one(expiry, "hidden_effect")).filter(n => n.key === spec.helper).length, 1);
        assert.equal(walk(expiry).filter(n => n.key === "effect_tooltip").length, 1);
        const preview = walk(expiry).find(n => n.key === "effect_tooltip").value;
        assert.deepEqual(preview, parse(spec.helper + " = yes"));
        assert(!walk(one(d, "complete_effect")).some(n => helperNames.includes(n.key)), "Improvement paid immediately");
        assert(!walk(one(d, "cancel_effect")).some(n => helperNames.includes(n.key)), "Cancellation grants progress");
    });
    for (const route of ["collegium", "directorate"]) scenario(spec.id + "/" + route + ": no start reward, timed reward once, replay inert and repeat possible", () => {
        const w = prepare(spec, route), original = [...w.root.ideas];
        assert(visible(spec, w)); assert(available(spec, w));
        start(spec, w);
        assert.deepEqual([...w.root.ideas], original);
        assert.equal(w.root.pp, 10000 - spec.cost);
        assert(w.root.flags.has(spec.id + "_running"));
        assert.equal(w.effectCalls.length, 0);
        callback(spec, "remove_effect", w);
        assert.deepEqual([...w.root.ideas], [spec.ladder[1]]);
        assert(!w.root.flags.has(spec.id + "_running"));
        const after = stateOf(w);
        callback(spec, "remove_effect", w);
        assert.equal(stateOf(w), after, "Replayed callback advanced development twice");
        start(spec, w); callback(spec, "remove_effect", w);
        assert.deepEqual([...w.root.ideas], [spec.ladder[2]]);
        assert.equal(w.root.pp, 10000 - spec.cost * 2);
    });
    scenario(spec.id + ": cancellation clears the pending flag and a late completion gives nothing", () => {
        const w = prepare(spec); start(spec, w);
        callback(spec, "cancel_effect", w);
        assert(!w.root.flags.has(spec.id + "_running"));
        const before = stateOf(w);
        callback(spec, "remove_effect", w);
        assert.equal(stateOf(w), before);
        start(spec, w); callback(spec, "remove_effect", w);
        assert.deepEqual([...w.root.ideas], [spec.ladder[1]], "Cancellation made future runs impossible");
    });
    scenario(spec.id + ": dissolution clears the pending run even if institutions return before expiry", () => {
        const w = prepare(spec); start(spec, w);
        run(parse("HSM_BAR_dissolve_institutions = yes"), w);
        assert(!w.root.flags.has(spec.id + "_running"));
        w.root.flags.add("HSM_BAR_active"); w.root.flags.add("HSM_BAR_directorate");
        const before = stateOf(w);
        callback(spec, "remove_effect", w);
        assert.equal(stateOf(w), before);
        start(spec, w); callback(spec, "remove_effect", w);
        assert.deepEqual([...w.root.ideas], [spec.ladder[1]]);
    });
    const invalidators = {
        "no active flag": w => w.root.flags.delete("HSM_BAR_active"),
        "no route": w => w.root.flags.delete("HSM_BAR_directorate"),
        "wrong tag": w => { w.root.id = "WIT"; },
        "lost focus": w => w.root.focuses.clear(),
        "occupied capital": w => { w.states[624].controller = "WIT"; },
        "lost ownership": w => { w.states[624].owner = "WIT"; },
        "capitulated": w => { w.root.capitulated = true; },
        "maximum reached": w => { w.root.ideas = new Set([spec.ladder.at(-1)]); },
        "native idea removed": w => w.root.ideas.clear()
    };
    for (const [label, invalidate] of Object.entries(invalidators)) scenario(spec.id + ": " + label + " blocks selection and queued reward", () => {
        const w = prepare(spec); start(spec, w); invalidate(w);
        assert(!available(spec, w), "Invalid program remained selectable");
        const before = stateOf(w);
        assert(condition(one(decisions[spec.id], "cancel_trigger"), w), "Invalidated program will not cancel");
        callback(spec, "remove_effect", w);
        assert.equal(stateOf(w), before, "Invalidated program still gave a reward");
        assert(!w.root.flags.has(spec.id + "_running"), "Obsolete running flag retained");
        callback(spec, "complete_effect", w);
        assert(!w.root.flags.has(spec.id + "_running"), "Stale start armed an invalid programme");
        assert.equal(stateOf(w), before);
    });
    scenario(spec.id + ": war alone does not stop development", () => {
        const w = prepare(spec); w.root.war = true;
        start(spec, w); callback(spec, "remove_effect", w);
        assert.deepEqual([...w.root.ideas], [spec.ladder[1]]);
    });
    scenario(spec.id + ": maximum and absent native ideas hide the program", () => {
        for (const idea of [spec.ladder.at(-1), null]) { const w = prepare(spec, "directorate", idea); assert(!visible(spec, w)); assert(!available(spec, w)); }
        const w = prepare(spec); w.root.focuses.clear(); assert(!visible(spec, w));
    });
}
scenario("exactly four improvement programs exist", () => assert.deepEqual(Object.keys(decisions).sort(), programSpecs.map(s => s.id).sort()));
scenario("parallel development programs have independent completion and cancellation flags", () => {
    const w = world();
    for (const spec of programSpecs) { w.root.focuses.add(spec.focus); w.root.ideas.add(spec.ladder[0]); start(spec, w); }
    callback(programSpecs[0], "remove_effect", w);
    callback(programSpecs[1], "cancel_effect", w);
    for (const spec of programSpecs.slice(2)) assert(w.root.flags.has(spec.id + "_running"), "Unrelated pending flag was cleared");
    for (const spec of programSpecs) callback(spec, "remove_effect", w);
    for (const [index, spec] of programSpecs.entries()) {
        assert(w.root.ideas.has(spec.ladder[index === 1 ? 0 : 1]));
        assert(!w.root.flags.has(spec.id + "_running"));
    }
});
scenario("industrial improvement handles every native intermediate level as a major step", () => {
    const spec = programSpecs[2];
    const tiers = {
        agrarian_society: ["communal_society", "tribal_society", "tribal_society2", "tribal_society3", "tribal_society4"],
        pre_industrial_society: ["agrarian_society", "agrarian_society2", "agrarian_society3", "agrarian_society4", "agrarian_society5", "agrarian_society6"],
        outdated_industry: ["pre_industrial_society", "pre_industrial_society1", "pre_industrial_society2", "pre_industrial_society3"],
        modern_society: ["outdated_industry", "outdated_industry2"]
    };
    for (const [next, previous] of Object.entries(tiers)) for (const idea of previous) {
        const w = prepare(spec, "directorate", idea); start(spec, w); callback(spec, "remove_effect", w);
        assert.deepEqual([...w.root.ideas], [next], idea);
    }
});
for (const route of ["collegium", "directorate"]) {
    for (const slots of [2, 3, 4, 5, 6]) scenario(route + ": all three slot focuses cap starts " + slots + " correctly without DLC", () => {
        const w = world(route, slots);
        completeBranch(w);
        assert.equal(w.root.slots, Math.max(5, slots));
        assert.equal(w.root.focuses.size, 28);
        assert.equal(w.dlc.size, 0);
        assert.equal(w.flags.size, 0);
    });
    scenario(route + ": all four maximum levels reachable from the worst tiers without anomalies or foreign conditions", () => {
        const w = world(route);
        for (const spec of programSpecs) w.root.ideas.add(spec.ladder[0]);
        completeBranch(w);
        for (const spec of programSpecs) {
            let terms = 0;
            while (visible(spec, w)) {
                assert(++terms < 10, "Nonterminating program " + spec.id);
                start(spec, w); callback(spec, "remove_effect", w);
            }
            assert(w.root.ideas.has(spec.ladder.at(-1)), "Maximum unreachable " + spec.id);
            assert.equal(spec.ladder.filter(id => w.root.ideas.has(id)).length, 1, "Duplicate tier ideas");
        }
        assert.equal(w.root.slots, 5);
        assert.equal(w.flags.size, 0);
        assert(![...w.root.flags].some(f => /case_.*_(studied|investigated)|HSM_BAR_study_/.test(f)), "Anomaly knowledge unexpectedly required");
    });
}
scenario("only the three documented focus rewards grant guarded research slots", () => {
    const slotFocuses = Object.entries(focuses).filter(([, f]) => walk(one(f, "completion_reward")).some(n => n.key === "add_research_slot"));
    assert.deepEqual(slotFocuses.map(([id]) => id).sort(), ["HSM_BAR_technical_school", "HSM_BAR_polytechnic", "HSM_BAR_research_council"].sort());
    for (const [id, f] of slotFocuses) {
        const w = world("directorate", 5); run(one(f, "completion_reward"), w); assert.equal(w.root.slots, 5, id);
        const w6 = world("directorate", 6); run(one(f, "completion_reward"), w6); assert.equal(w6.root.slots, 6, id);
    }
});
scenario("native society PP decision is hidden and unavailable for each custom route flag, otherwise unchanged", () => {
    const upstream = nativeRead("common/decisions/BAR_decisions.txt");
    const original = one(one(upstream, "BAR_society_upgrade_lame"), "BAR_society_upgrade_pp");
    const current = one(one(read("common/decisions/BAR_decisions.txt"), "BAR_society_upgrade_lame"), "BAR_society_upgrade_pp");
    const flags = ["HSM_BAR_active", "HSM_BAR_collegium", "HSM_BAR_directorate"];
    const guard = parse(flags.map(f => "NOT = { has_country_flag = " + f + " }").join("\n"));
    const legacyCategory = one(read("common/decisions/categories/BAR_decision_categories.txt"), "BAR_society_upgrade_lame");
    assert.deepEqual(one(legacyCategory, "visible"), guard);
    for (const key of ["visible", "available"]) {
        const old = one(original, key);
        assert.equal(old[0].key, "original_tag");
        assert.deepEqual(one(current, key), [old[0], ...guard, ...old.slice(1)], "Unexpected native predicate change: " + key);
        for (let mask = 0; mask < 8; mask++) {
            const w = world(); w.root.flags = new Set(["BAR_upgrade_society_pp", ...flags.filter((_, i) => mask & (1 << i))]);
            w.root.ideas.add("pre_industrial_society");
            assert.equal(condition(one(current, key), w), mask === 0);
            assert.equal(condition(one(legacyCategory, "visible"), w), mask === 0);
        }
    }
    assert.deepEqual(current.filter(n => !["visible", "available"].includes(n.key)), original.filter(n => !["visible", "available"].includes(n.key)));
});
scenario("both development narrative events require the active route and reject replay", () => {
    assert.deepEqual(Object.keys(events).sort(), ["hsm_bar_development.1", "hsm_bar_development.2"]);
    for (const [id, event] of Object.entries(events)) {
        for (const route of ["collegium", "directorate"]) {
            const w = world(route);
            const gate = one(event, "trigger");
            const focus = one(gate, "has_completed_focus");
            assert(!condition(gate, w), "Event fired before the relevant focus: " + id);
            w.root.focuses.add(focus);
            assert(condition(gate, w), "Fresh event blocked: " + id + "/" + route);
            const inactive = world(route); inactive.root.focuses.add(focus); inactive.root.flags.clear(); assert(!condition(gate, inactive), "Event leaked outside custom route");
            run(one(event, "immediate"), w);
            assert(!condition(gate, w), "Event trigger lacks replay guard " + id);
            for (const option of many(event, "option")) run(option.value.filter(n => !["name", "ai_chance", "trigger"].includes(n.key)), w);
        }
    }
});
console.log(`RESULT: ${passed} passed, ${failed} failed; deterministic development scenarios, not an HOI4 runtime test.`);
if (failed) process.exitCode = 1;
