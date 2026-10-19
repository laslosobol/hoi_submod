"use strict";
// Deterministic fixtures execute these Clausewitz files, not a second gameplay implementation.
// Native-source checks are read-only; this is not an HOI4 runtime test.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const {parse, prop} = require("./Test-BarradArchiveSkin.cjs");
const repo = path.resolve(__dirname, "..");
const mod = path.join(repo, "mod/HoISubmod");
const P = "HSM_BAR_mtc_frontiers";
const states = [614, 615, 616, 617, 627, 628, 629];
const read = file => fs.readFileSync(path.join(mod, file), "utf8").replace(/^\uFEFF/, "");
const load = folder => parse(read(folder + "/" + P + ".txt"), true);
function dictionary(nodes) {
    assert.equal(new Set(nodes.map(n => n.key)).size, nodes.length, "Duplicate definition");
    return Object.fromEntries(nodes.map(n => [n.key, n.value]));
}
const triggers = dictionary(load("common/scripted_triggers"));
const effects = dictionary(load("common/scripted_effects"));
const diplomacyTriggers = dictionary(parse(read("common/scripted_triggers/HSM_BAR_diplomacy.txt"), true));
const diplomacyEffects = dictionary(parse(read("common/scripted_effects/HSM_BAR_diplomacy.txt"), true));
const decisions = dictionary(prop(load("common/decisions"), P + "_policy"));
const actions = dictionary(prop(load("common/on_actions"), "on_actions"));
const focuses = Object.fromEntries(load("common/national_focus").map(n => [prop(n.value, "id"), n.value]));
const events = Object.fromEntries(load("events").filter(n => n.key === "country_event").map(n => [prop(n.value, "id"), n.value]));
const walk = nodes => nodes.flatMap(n => [n, ...(Array.isArray(n.value) ? walk(n.value) : [])]);
function world() {
    const w = {day: 0, countries: {}, states: {}, events: [], removed: [], bonuses: []};
    for (const tag of ["BAR", "WIT", "ZES", "OLV", "RIV"]) w.countries[tag] = {
        tag, original: tag, exists: true, subject: false, capitulated: false,
        flags: new Map(), focuses: new Set(), wars: new Set(), factions: new Set(), pacts: new Set(), guarantees: new Set(), opinions: {}, goals: new Set(), decisions: new Set(), pp: 500
    };
    const b = w.countries.BAR;
    b.flags.set("HSM_BAR_active", {day: 0}); b.flags.set("HSM_BAR_collegium", {day: 0});
    b.focuses.add("HSM_BAR_civic_foreign_office");
    b.neighbours = new Set(["WIT", "ZES", "OLV"]);
    for (const id of [...states, 624, 413, 412]) w.states[id] = {
        id, owner: id === 624 ? "BAR" : id === 413 ? "ZES" : id === 412 ? "OLV" : "WIT",
        controller: id === 624 ? "BAR" : id === 413 ? "ZES" : id === 412 ? "OLV" : "WIT",
        cores: new Set([id === 624 ? "BAR" : id === 413 ? "ZES" : id === 412 ? "OLV" : "WIT"]),
        flags: new Map(), compliance: 60, resistance: 10
    };
    return w;
}
const boolean = value => value === "yes";
function compare(actual, op, expected) {
    return ({"=": () => actual === expected, ">": () => actual > expected, "<": () => actual < expected,
        ">=": () => actual >= expected, "<=": () => actual <= expected, "!=": () => actual !== expected})[op]();
}
function hasFlag(w, scope, value) {
    const name = Array.isArray(value) ? prop(value, "flag") : value;
    const flag = scope.flags.get(name);
    if (!flag || (flag.expires !== undefined && w.day >= flag.expires)) return false;
    return !Array.isArray(value) || value.every(n => n.key === "flag" || (n.key === "days" && compare(w.day - flag.day, n.op, Number(n.value))));
}
function check(w, scope, nodes, ctx = {}) {
    return nodes.every(n => {
        const {key: k, value: v, op} = n;
        if (k === "AND" || k === "limit") return check(w, scope, v, ctx);
        if (k === "OR") return v.some(child => check(w, scope, [child], ctx));
        if (k === "NOT") return v.every(child => !check(w, scope, [child], ctx));
        if (triggers[k]) { assert(["yes", "no"].includes(v), "Unsupported scripted trigger arguments: " + k); return check(w, scope, triggers[k], ctx) === boolean(v); }
        if (diplomacyTriggers[k]) { assert(["yes", "no"].includes(v)); return check(w, scope, diplomacyTriggers[k], ctx) === boolean(v); }
        if (w.countries[k]) return check(w, w.countries[k], v, ctx);
        if (w.states[k]) return check(w, w.states[k], v, ctx);
        if (k === "ROOT" || k === "FROM") { assert(ctx[k], "Missing scope " + k); return check(w, ctx[k], v, ctx); }
        if (k === "tag") return scope.tag === v;
        if (k === "original_tag") return scope.original === v;
        if (k === "exists") return scope.exists === boolean(v);
        if (k === "is_subject") return scope.subject === boolean(v);
        if (k === "has_capitulated") return scope.capitulated === boolean(v);
        if (k === "has_country_flag" || k === "has_state_flag") return hasFlag(w, scope, v);
        if (k === "has_completed_focus") return scope.focuses.has(v);
        if (k === "has_decision") return scope.decisions.has(v);
        if (k === "has_war_with") return scope.wars.has(v);
        if (k === "has_war") return (scope.wars.size > 0) === boolean(v);
        if (k === "is_in_faction_with") return scope.factions.has(v);
        if (k === "has_non_aggression_pact_with") return scope.pacts.has(v);
        if (k === "has_guaranteed") return scope.guarantees.has(v);
        if (k === "is_neighbor_of") return scope.neighbours.has(v);
        if (k === "has_opinion") { const value = v.find(n => n.key === "value"); return compare(scope.opinions[prop(v, "target")] || 0, value.op, Number(value.value)); }
        if (k === "has_wargoal_against") return scope.goals.has(v);
        if (k === "owns_state") return w.states[v].owner === scope.tag;
        if (k === "controls_state") return w.states[v].controller === scope.tag;
        if (k === "state") return scope.id === Number(v);
        if (k === "is_owned_by") return scope.owner === v;
        if (k === "is_controlled_by") return scope.controller === v;
        if (k === "is_core_of") return scope.cores.has(v);
        if (k === "compliance" || k === "resistance") {
            assert(["=", "<", ">"].includes(op), "Unsupported native state comparison: " + op);
            return compare(scope[k], op, Number(v));
        }
        throw Error("Unsupported fixture trigger: " + k);
    });
}
function run(w, scope, nodes, ctx = {ROOT: scope}) {
    let branch = false;
    for (const {key: k, value: v} of nodes) {
        if (k === "if") { branch = check(w, scope, prop(v, "limit"), ctx); if (branch) run(w, scope, v.filter(n => n.key !== "limit"), ctx); continue; }
        if (k === "else_if") { if (!branch) { branch = check(w, scope, prop(v, "limit"), ctx); if (branch) run(w, scope, v.filter(n => n.key !== "limit"), ctx); } continue; }
        if (k === "else") { if (!branch) run(w, scope, v, ctx); continue; }
        if (effects[k]) { run(w, scope, effects[k], ctx); continue; }
        if (diplomacyEffects[k]) { run(w, scope, diplomacyEffects[k], ctx); continue; }
        if (w.countries[k]) { run(w, w.countries[k], v, ctx); continue; }
        if (w.states[k]) { run(w, w.states[k], v, ctx); continue; }
        if (k === "ROOT" || k === "FROM") { assert(ctx[k]); run(w, ctx[k], v, ctx); continue; }
        if (k === "every_state") {
            for (const state of Object.values(w.states)) if (check(w, state, prop(v, "limit"), ctx)) run(w, state, v.filter(n => n.key !== "limit"), ctx);
            continue;
        }
        if (k === "set_country_flag" || k === "set_state_flag") {
            const name = Array.isArray(v) ? prop(v, "flag") : v;
            scope.flags.set(name, {day: w.day, ...(Array.isArray(v) && prop(v, "days") ? {expires: w.day + Number(prop(v, "days"))} : {})}); continue;
        }
        if (k === "clr_country_flag" || k === "clr_state_flag") { scope.flags.delete(v); continue; }
        if (k === "create_wargoal") { assert.equal(prop(v, "expire"), "180"); scope.goals.add(prop(v, "target")); continue; }
        if (k === "remove_wargoal") { scope.goals.delete(prop(v, "target")); continue; }
        if (k === "country_event") { w.events.push(prop(v, "id")); continue; }
        if (k === "remove_decision") { w.removed.push(v); continue; }
        if (k === "add_compliance") { scope.compliance += Number(v); continue; }
        if (k === "add_core_of") { scope.cores.add(v); continue; }
        if (k === "army_experience") { scope.xp = (scope.xp || 0) + Number(v); continue; }
        if (k === "add_tech_bonus") { w.bonuses.push(v); continue; }
        if (k === "custom_effect_tooltip") continue;
        throw Error("Unsupported fixture effect: " + k);
    }
}
const bar = w => w.countries.BAR;
function effect(w, name, scope = bar(w)) { run(w, scope, effects[P + name]); }
function action(w, name, root = "BAR", from = "WIT") {
    const ctx = {ROOT: w.countries[root], FROM: w.countries[from]};
    run(w, ctx.ROOT, prop(actions[name], "effect"), ctx);
}
function war(w, attacker = "WIT", direct = true) {
    const defender = attacker === "WIT" ? "BAR" : "WIT";
    if (direct) action(w, "on_declare_war", attacker, defender);
    bar(w).wars.add("WIT"); w.countries.WIT.wars.add("BAR");
    action(w, "on_war_relation_added", attacker, defender);
}
function peace(w, gain = [614], conference = true) {
    if (conference) action(w, "on_peaceconference_started");
    bar(w).wars.delete("WIT"); w.countries.WIT.wars.delete("BAR");
    for (const s of gain) Object.assign(w.states[s], {owner: "BAR", controller: "BAR"});
    action(w, "on_peaceconference_ended");
}
function start(w, name) {
    const d = decisions[P + name], b = bar(w);
    if (!check(w, b, prop(d, "available")) || b.pp < Number(prop(d, "cost"))) return false;
    b.pp -= Number(prop(d, "cost")); run(w, b, prop(d, "complete_effect")); return true;
}
function cancel(w, name) { const d = decisions[P + name]; if (check(w, bar(w), prop(d, "cancel_trigger"))) run(w, bar(w), prop(d, "cancel_effect")); }
function finish(w, name) { run(w, bar(w), prop(decisions[P + name], "remove_effect")); }
function completeFocus(w, id) {
    const f = focuses[id], b = bar(w);
    if (b.focuses.has(id) || !check(w, b, prop(f, "available"))) return false;
    for (const group of f.filter(n => n.key === "prerequisite")) if (!group.value.some(n => b.focuses.has(n.value))) return false;
    // Rewards must work even before the engine records the completing focus.
    run(w, b, prop(f, "completion_reward")); b.focuses.add(id); return true;
}
function bypassFocus(w, id) {
    const b = bar(w), condition = prop(focuses[id], "bypass");
    if (b.focuses.has(id) || !condition || !check(w, b, condition)) return false;
    b.focuses.add(id); return true;
}
function optionEffects(w, option) { run(w, bar(w), option.filter(n => !["name", "trigger", "ai_chance"].includes(n.key))); }
function integratedWorld(id = 614) { const w = world(); war(w); peace(w, [id]); bar(w).focuses.add(P + "_WIT_councils"); bar(w).focuses.add(P + "_WIT_charter"); return w; }
let passed = 0, failed = 0;
function test(name, body) { try { body(); passed++; console.log("PASS " + name); } catch (e) { failed++; console.error("FAIL " + name + "\n" + e.stack); } }

test("11 compact 28/35-day focuses, independent root, guarded start and reward", () => {
    assert.equal(Object.keys(focuses).length, 11);
    const positions = new Set();
    for (const [id, f] of Object.entries(focuses)) {
        const x = Number(prop(f, "x")), y = Number(prop(f, "y"));
        assert(x >= 54 && x <= 66 && y >= 0 && y <= 12);
        assert(!positions.has(x + "," + y)); positions.add(x + "," + y);
        assert(["4", "5"].includes(prop(f, "cost")));
        assert.equal(prop(f, "cancel_if_invalid"), "yes");
        assert.equal(prop(f, "continue_if_invalid"), "no");
        assert(walk(prop(f, "available")).some(n => n.key === P + "_access"));
        assert(walk(prop(f, "completion_reward")).some(n => n.key === P + "_access"));
        if (id === P) assert.equal(prop(f, "prerequisite"), undefined);
        else assert(focuses[prop(prop(f, "prerequisite"), "focus")]);
        const w = world(); bar(w).flags.delete("HSM_BAR_collegium");
        run(w, bar(w), prop(f, "completion_reward"));
        assert.deepEqual(w.events, []); assert.deepEqual(w.bonuses, []); assert(!bar(w).xp);
    }
});
test("root gives reconnaissance research even when diplomacy is already open", () => {
    const w = world(); bar(w).flags.set("HSM_BAR_diplomacy_open", {day: 0});
    assert(completeFocus(w, P));
    assert.equal(w.bonuses.length, 1);
    assert.equal(prop(w.bonuses[0], "category"), "recon_tech");
    assert.equal(prop(w.bonuses[0], "bonus"), "0.5"); assert.equal(prop(w.bonuses[0], "uses"), "1");
    assert.deepEqual(w.events, ["hsm_bar_mtc_frontiers.1"]);
    assert(!completeFocus(w, P)); assert.equal(w.bonuses.length, 1);
});
test("only fourteen defensive settlement decisions remain; category waits for councils and victory", () => {
    assert.equal(Object.keys(decisions).length, 14);
    assert(Object.keys(decisions).every(k => /_(registry|citizenship)_\d+$/.test(k)));
    const category = prop(load("common/decisions/categories"), P + "_policy");
    const w = world(); bar(w).focuses.add(P);
    assert(!check(w, bar(w), prop(category, "visible")));
    const q = integratedWorld(); assert(check(q, bar(q), prop(category, "visible")));
    bar(q).flags.delete(P + "_WIT_victory"); assert(!check(q, bar(q), prop(category, "visible")));
});
for (const tag of ["ZES", "OLV"]) {
    const mandate = P + "_" + tag + "_mandate", hearing = P + "_" + tag + "_hearing";
    const prepare = () => { const w = world(); bar(w).focuses.add(hearing); return w; };
    const oldSave = () => { const w = prepare(); bar(w).focuses.add(mandate); return w; };
    const issued = P + "_" + tag + "_goal_issued";
    const hearingEvent = events["hsm_bar_mtc_frontiers." + (tag === "ZES" ? 7 : 8)];
    const envoy = prop(hearingEvent, "option");
    test(tag + " mandate focus directly grants a 180-day goal; no decision, payment, war or cores", () => {
        const w = prepare(); assert(!bar(w).focuses.has(mandate)); assert.equal(bar(w).goals.size, 0);
        assert(completeFocus(w, mandate)); assert.equal(bar(w).pp, 500);
        assert(bar(w).goals.has(tag)); assert.equal(bar(w).wars.size, 0);
        assert.equal(bar(w).flags.get(P + "_" + tag + "_goal").expires, 180);
        assert(hasFlag(w, bar(w), issued)); assert.equal(bar(w).flags.get(issued).expires, undefined);
        assert(!w.states[tag === "ZES" ? 413 : 412].cores.has("BAR"));
        assert(!completeFocus(w, mandate));
        const notices = w.events.length; effect(w, "_" + tag + "_authorize"); assert.equal(w.events.length, notices);
        assert.equal(decisions[P + "_" + tag + "_debate"], undefined);
    });
    const invalid = {
        dead: w => w.countries[tag].exists = false,
        subject: w => w.countries[tag].subject = true,
        capitulated: w => w.countries[tag].capitulated = true,
        "BAR subject": w => bar(w).subject = true,
        "BAR capitulated": w => bar(w).capitulated = true,
        "BAR homeland lost": w => w.states[624].controller = "WIT",
        faction: w => bar(w).factions.add(tag),
        pact: w => bar(w).pacts.add(tag),
        treaty: w => bar(w).flags.set("HSM_BAR_" + tag + "_agreement", {day: 0}),
        "pending negotiation": w => bar(w).flags.set("HSM_BAR_dip_" + tag + "_pending", {day: 0}),
        "friendly BAR": w => bar(w).opinions[tag] = 50,
        "friendly target": w => w.countries[tag].opinions.BAR = 50,
        "BAR guarantee": w => bar(w).guarantees.add(tag),
        "target guarantee": w => w.countries[tag].guarantees.add("BAR"),
        war: w => bar(w).wars.add(tag),
        "not adjacent": w => bar(w).neighbours.delete(tag),
        "other route": w => bar(w).flags.set("HSM_BAR_directorate", {day: 0}),
        "no foreign office": w => bar(w).focuses.delete("HSM_BAR_civic_foreign_office"),
        "no hearing": w => bar(w).focuses.delete(hearing),
        "existing goal": w => bar(w).goals.add(tag),
        "live mandate marker": w => bar(w).flags.set(P + "_" + tag + "_goal", {day: 0, expires: 180}),
        "issued history": w => bar(w).flags.set(issued, {day: 0})
    };
    for (const [reason, mutate] of Object.entries(invalid)) test(tag + " blocks " + reason + " at focus start AND reward", () => {
        const w = prepare(); mutate(w); assert(!completeFocus(w, mandate)); assert.equal(bar(w).pp, 500);
        const q = prepare(); assert(check(q, bar(q), prop(focuses[mandate], "available"))); mutate(q);
        const before = structuredClone(q);
        run(q, bar(q), prop(focuses[mandate], "completion_reward")); assert.deepEqual(q, before);
        effect(q, "_" + tag + "_authorize"); assert.deepEqual(q, before);
    });
    test(tag + " notice cannot issue or renew a goal; old pending votes cannot authorize", () => {
        const event = events["hsm_bar_mtc_frontiers." + (tag === "ZES" ? 2 : 3)];
        const w = prepare(); bar(w).flags.set(P + "_" + tag + "_vote", {day: 0});
        assert(!check(w, bar(w), prop(event, "trigger")));
        for (const option of event.filter(n => n.key === "option")) optionEffects(w, option.value);
        assert.equal(bar(w).goals.size, 0);
        assert(completeFocus(w, mandate)); assert(check(w, bar(w), prop(event, "trigger")));
        w.day = 181; bar(w).goals.delete(tag);
        assert(!check(w, bar(w), prop(event, "trigger"))); assert(!completeFocus(w, mandate));
        for (const option of event.filter(n => n.key === "option")) optionEffects(w, option.value);
        assert.equal(bar(w).goals.size, 0);
    });
    for (const [reason, mutate] of Object.entries(invalid).filter(([reason]) => !["existing goal", "live mandate marker", "issued history", "no hearing"].includes(reason))) test(tag + " daily reconciliation withdraws issued goal after " + reason, () => {
        const q = prepare(); assert(completeFocus(q, mandate)); mutate(q);
        action(q, "on_daily_BAR"); assert(!bar(q).goals.has(tag));
        const r = prepare(); bar(r).goals.add(tag); effect(r, "_teardown"); assert(bar(r).goals.has(tag), "Do not erase goals not issued here");
    });
    test(tag + " completed old mandate with no recorded vote recovers once through daily maintenance", () => {
        const w = oldSave(); action(w, "on_daily_BAR");
        assert(bar(w).goals.has(tag)); assert(hasFlag(w, bar(w), issued));
        assert.equal(bar(w).flags.get(issued).expires, undefined);
        assert.equal(bar(w).flags.get(P + "_" + tag + "_goal").expires, 180);
        assert.equal(w.events.length, 1); assert.equal(bar(w).pp, 500); assert.equal(bar(w).wars.size, 0);
        const before = structuredClone(w); action(w, "on_daily_BAR"); assert.deepEqual(w, before);
        w.day = 181; bar(w).goals.delete(tag); action(w, "on_daily_BAR");
        effect(w, "_" + tag + "_authorize");
        assert.equal(bar(w).goals.size, 0); assert.equal(w.events.length, 1); assert(hasFlag(w, bar(w), issued));
    });
    for (const [reason, mutate] of Object.entries(invalid).filter(([reason]) => !["dead", "existing goal", "live mandate marker", "issued history"].includes(reason))) test(tag + " old-save recovery waits for " + reason + " without consuming the mandate", () => {
        const w = oldSave(), valid = structuredClone(w); mutate(w); action(w, "on_daily_BAR");
        assert(!hasFlag(w, bar(w), issued)); assert.equal(bar(w).goals.size, 0); assert.equal(w.events.length, 0);
        // Restore the blocked country/state conditions, keeping the maintenance result history.
        w.countries = valid.countries; w.states = valid.states;
        action(w, "on_daily_BAR"); assert(bar(w).goals.has(tag)); assert(hasFlag(w, bar(w), issued));
        assert.equal(w.events.length, 1);
    });
    for (const evidence of ["vote", "goal", "existing goal"]) test(tag + " legacy " + evidence + " is consumed before expiry, not renewed", () => {
        const w = oldSave();
        if (evidence !== "existing goal") bar(w).flags.set(P + "_" + tag + "_" + evidence, {day: 0, expires: evidence === "vote" ? 30 : 180});
        if (evidence !== "vote") bar(w).goals.add(tag);
        action(w, "on_daily_BAR"); assert(hasFlag(w, bar(w), issued));
        assert.equal(w.events.length, 0); assert.equal(bar(w).pp, 500);
        if (evidence !== "vote") assert(bar(w).goals.has(tag), "Adoption must not replace or prematurely revoke the existing goal");
        w.day = 181; bar(w).goals.delete(tag); action(w, "on_daily_BAR");
        assert(!bar(w).goals.has(tag)); assert.equal(w.events.length, 0);
    });
    for (const evidence of ["vote", "goal"]) test(tag + " direct teardown preserves legacy " + evidence + " before clearing transient flags", () => {
        const w = oldSave(); bar(w).flags.set(P + "_" + tag + "_" + evidence, {day: 0});
        if (evidence === "goal") bar(w).goals.add(tag);
        bar(w).flags.delete("HSM_BAR_collegium"); effect(w, "_teardown");
        assert(hasFlag(w, bar(w), issued)); assert(!hasFlag(w, bar(w), P + "_" + tag + "_" + evidence));
        bar(w).flags.set("HSM_BAR_collegium", {day: 0}); w.day = 200; action(w, "on_daily_BAR");
        assert(!bar(w).goals.has(tag)); assert.equal(w.events.length, 0);
    });
    test(tag + " new-focus goal is never renewed after expiry, revocation or teardown", () => {
        for (const ending of ["expiry", "treaty", "teardown"]) {
            const w = prepare(); assert(completeFocus(w, mandate)); action(w, "on_daily_BAR");
            assert(bar(w).goals.has(tag), "Recording consumption must not self-revoke a valid goal");
            if (ending === "expiry") { w.day = 181; bar(w).goals.delete(tag); }
            if (ending === "treaty") { bar(w).pacts.add(tag); action(w, "on_daily_BAR"); bar(w).pacts.delete(tag); }
            if (ending === "teardown") effect(w, "_teardown");
            action(w, "on_daily_BAR"); effect(w, "_" + tag + "_authorize");
            assert(!bar(w).goals.has(tag)); assert(hasFlag(w, bar(w), issued)); assert.equal(w.events.length, 1);
        }
    });
    test(tag + " an incomplete mandate never receives a migration reward", () => {
        const w = prepare(); action(w, "on_daily_BAR");
        assert(!hasFlag(w, bar(w), issued)); assert.equal(bar(w).goals.size, 0); assert.equal(w.events.length, 0);
    });
    test(tag + " extinction after reaching the branch records consumption before native bypass", () => {
        for (const owner of ["BAR", "RIV"]) {
            const w = world(); bar(w).focuses.add(P + "_staff"); w.countries[tag].exists = false;
            Object.assign(w.states[tag === "ZES" ? 413 : 412], {owner, controller: owner});
            assert(!bypassFocus(w, hearing)); assert(!bypassFocus(w, mandate), "Never bypass before recording consumption");
            action(w, "on_daily_BAR"); assert(hasFlag(w, bar(w), issued));
            assert(bypassFocus(w, hearing)); assert(bypassFocus(w, mandate));
            assert.equal(bar(w).goals.size, 0); assert.equal(w.events.length, 0); assert.equal(w.bonuses.length, 0);
            w.countries[tag].exists = true; action(w, "on_daily_BAR");
            assert.equal(bar(w).goals.size, 0); assert.equal(w.events.length, 0);
            assert(!completeFocus(w, mandate)); effect(w, "_" + tag + "_authorize"); assert.equal(bar(w).goals.size, 0);
        }
    });
    test(tag + " annexation after an old completed mandate consumes recovery even without bypass", () => {
        const w = oldSave(); w.countries[tag].exists = false; action(w, "on_daily_BAR");
        assert(hasFlag(w, bar(w), issued)); w.countries[tag].exists = true; action(w, "on_daily_BAR");
        assert.equal(bar(w).goals.size, 0); assert.equal(w.events.length, 0);
    });
    test(tag + " no premature consumption before the frontier branch, and ownership alone is not extinction", () => {
        const w = world(); w.countries[tag].exists = false; action(w, "on_daily_BAR");
        assert(!hasFlag(w, bar(w), issued)); assert(!bypassFocus(w, hearing)); assert(!bypassFocus(w, mandate));
        const q = world(); bar(q).focuses.add(P + "_staff");
        Object.assign(q.states[tag === "ZES" ? 413 : 412], {owner: "BAR", controller: "BAR"});
        action(q, "on_daily_BAR"); assert(!hasFlag(q, bar(q), issued)); assert(!bypassFocus(q, hearing));
    });
    test(tag + " absent target on a non-Collegium route cannot bypass or consume an unissued mandate", () => {
        const w = world(); bar(w).focuses.add(P + "_staff"); w.countries[tag].exists = false;
        bar(w).flags.delete("HSM_BAR_collegium"); action(w, "on_daily_BAR");
        assert(!hasFlag(w, bar(w), issued)); assert(!bypassFocus(w, hearing)); assert(!bypassFocus(w, mandate));
    });
    test(tag + " history erased before upgrading is indistinguishable from never voting, but recovers only once", () => {
        const w = oldSave();
        bar(w).flags.set(P + "_" + tag + "_goal", {day: 0, expires: 180});
        w.day = 181; action(w, "on_daily_BAR");
        assert(bar(w).goals.has(tag)); assert(hasFlag(w, bar(w), issued));
        w.day = 362; bar(w).goals.delete(tag); action(w, "on_daily_BAR");
        assert(!bar(w).goals.has(tag)); assert.equal(w.events.length, 1);
    });
    test(tag + " hearing always gives logistics research, including friendly or pending diplomatic relations", () => {
        for (const flag of [null, "HSM_BAR_" + tag + "_agreement", "HSM_BAR_dip_" + tag + "_pending"]) {
            const w = world(); bar(w).focuses.add(P + "_staff");
            if (flag) bar(w).flags.set(flag, {day: 0});
            assert(completeFocus(w, hearing)); assert.equal(w.bonuses.length, 1);
            assert.equal(prop(w.bonuses[0], "category"), "logistics_tech");
            assert.equal(prop(w.bonuses[0], "bonus"), "0.5"); assert.equal(prop(w.bonuses[0], "uses"), "1");
            assert.equal(bar(w).goals.size, 0); assert.equal(bar(w).wars.size, 0);
            assert(!completeFocus(w, hearing));
            const acknowledgment = hearingEvent.filter(n => n.key === "option")[1].value;
            optionEffects(w, acknowledgment); optionEffects(w, acknowledgment);
            assert.equal(w.bonuses.length, 1, "Event reentry cannot duplicate the focus reward");
        }
    });
    test(tag + " hearing envoy invokes real existing diplomacy; no treaty or war is forced", () => {
        const w = world(); assert(check(w, bar(w), prop(envoy, "trigger")));
        optionEffects(w, envoy); assert(hasFlag(w, bar(w), "HSM_BAR_dip_" + tag + "_pending"));
        assert(w.events.includes("hsm_bar_diplomacy." + (tag === "ZES" ? 20 : 30)));
        assert(!hasFlag(w, bar(w), "HSM_BAR_" + tag + "_agreement"));
        assert.equal(bar(w).wars.size, 0); assert.equal(bar(w).goals.size, 0);
    });
    test(tag + " envoy rejects treaty, pending talks, cooldown, rejection and route loss at click time", () => {
        for (const flag of ["HSM_BAR_" + tag + "_agreement", ...["pending", "cooldown", "rejected"].map(s => "HSM_BAR_dip_" + tag + "_" + s), "HSM_BAR_directorate"]) {
            const w = world(); bar(w).flags.set(flag, {day: 0}); const before = structuredClone(w);
            assert(!check(w, bar(w), prop(envoy, "trigger"))); optionEffects(w, envoy); assert.deepEqual(w, before);
        }
    });
}
test("permanent mandate consumption is never cleared or timed, and each target recovers independently", () => {
    const flags = ["ZES", "OLV"].map(tag => P + "_" + tag + "_goal_issued");
    for (const n of walk(load("common/scripted_effects"))) {
        assert(!(n.key === "clr_country_flag" && flags.includes(n.value)));
        if (n.key === "set_country_flag" && Array.isArray(n.value)) assert(!flags.includes(prop(n.value, "flag")));
    }
    const w = world();
    for (const tag of ["ZES", "OLV"]) {
        bar(w).focuses.add(P + "_" + tag + "_hearing"); bar(w).focuses.add(P + "_" + tag + "_mandate");
    }
    bar(w).flags.set(P + "_ZES_vote", {day: 0, expires: 30}); action(w, "on_daily_BAR");
    assert(!bar(w).goals.has("ZES")); assert(bar(w).goals.has("OLV"));
    for (const flag of flags) assert(hasFlag(w, bar(w), flag));
    assert.equal(w.events.length, 1);
});

test("direct aggression plus defensive peace conference records only newly awarded historical states", () => {
    const w = world(); Object.assign(w.states[615], {owner: "BAR", controller: "BAR"});
    war(w); peace(w, [614, 615, 413]);
    assert(hasFlag(w, bar(w), P + "_WIT_victory"));
    assert(hasFlag(w, w.states[614], P + "_settlement"));
    assert(!hasFlag(w, w.states[615], P + "_settlement"));
    assert(!hasFlag(w, w.states[413], P + "_settlement"));
    assert(!w.states[614].cores.has("BAR"));
    assert.equal(w.states[616].owner, "WIT");
    assert(!hasFlag(w, bar(w), P + "_defending"));
});
for (const [name, setup] of Object.entries({
    "BAR offensive war": w => war(w, "BAR"),
    "WIT allied proxy war": w => war(w, "WIT", false),
    "unrelated native declaration": w => { action(w, "on_declare_war", "WIT", "RIV"); war(w, "WIT", false); },
    "pre-route declaration": w => { bar(w).flags.delete("HSM_BAR_collegium"); war(w); bar(w).flags.set("HSM_BAR_collegium", {day: 0}); },
    "BAR capitulation then liberation": w => { war(w); bar(w).capitulated = true; action(w, "on_capitulation_immediate"); bar(w).capitulated = false; },
    "BAR conference defeat": w => { war(w); action(w, "on_peaceconference_started", "WIT", "BAR"); },
    "institution dissolution": w => { war(w); effect(w, "_teardown"); },
    "expired direct token": w => { action(w, "on_declare_war", "WIT", "BAR"); w.day = 2; war(w, "WIT", false); }
})) test(name + " cannot produce defensive victory", () => { const w = world(); setup(w); peace(w); assert(!hasFlag(w, bar(w), P + "_WIT_victory")); });
test("white peace and stale callbacks cannot authorize a later proxy war", () => {
    const w = world(); war(w); peace(w, [], false); assert(!hasFlag(w, bar(w), P + "_WIT_victory"));
    war(w, "WIT", false); peace(w); assert(!hasFlag(w, bar(w), P + "_WIT_victory"));
    const q = world(); war(q); bar(q).wars.clear(); action(q, "on_daily_BAR");
    action(q, "on_peaceconference_started"); action(q, "on_peaceconference_ended"); assert(!hasFlag(q, bar(q), P + "_WIT_victory"));
});
test("temporary homeland occupation without capitulation does not erase aggression", () => {
    const w = world(); war(w); w.states[624].controller = "WIT"; action(w, "on_daily_BAR");
    assert(hasFlag(w, bar(w), P + "_defending")); w.states[624].controller = "BAR"; peace(w);
    assert(hasFlag(w, bar(w), P + "_WIT_victory"));
});
test("winning unrelated conference is not enough; absent control excludes province", () => {
    const w = world(); war(w); action(w, "on_peaceconference_started", "BAR", "RIV");
    bar(w).wars.clear(); action(w, "on_peaceconference_ended"); assert(!hasFlag(w, bar(w), P + "_WIT_victory"));
    const q = world(); war(q); action(q, "on_peaceconference_started"); bar(q).wars.clear();
    Object.assign(q.states[614], {owner: "BAR", controller: "RIV"}); action(q, "on_peaceconference_ended");
    assert(!hasFlag(q, q.states[614], P + "_settlement"));
});
for (const id of states) {
    test(id + " independent paid 60/120-day stages; replay/early callbacks give nothing", () => {
        const w = integratedWorld(id), s = w.states[id]; s.compliance = 60;
        assert(start(w, "_registry_" + id)); assert.equal(bar(w).pp, 450);
        assert(!start(w, "_registry_" + id)); w.day = 60; finish(w, "_registry_" + id);
        assert.equal(s.compliance, 70); finish(w, "_registry_" + id); assert.equal(s.compliance, 70);
        assert(start(w, "_citizenship_" + id)); assert.equal(bar(w).pp, 350); w.day = 180;
        finish(w, "_citizenship_" + id); assert(s.cores.has("BAR")); assert(s.cores.has("WIT"));
        assert(!start(w, "_citizenship_" + id)); assert.equal(w.events.filter(e => e === "hsm_bar_mtc_frontiers.6").length, 1);
        for (const other of states.filter(n => n !== id)) assert(!w.states[other].cores.has("BAR"));
        const q = integratedWorld(id); start(q, "_registry_" + id); q.day = 59; finish(q, "_registry_" + id);
        assert(!hasFlag(q, q.states[id], P + "_registered"));
        assert(!start(q, "_citizenship_" + id));
    });
}
const integrationInvalid = {
    "third-party owner": w => w.states[614].owner = "RIV",
    "occupation only": w => w.states[614].owner = "WIT",
    "third-party control": w => w.states[614].controller = "RIV",
    "low compliance": w => w.states[614].compliance = 24,
    "high resistance": w => w.states[614].resistance = 36,
    war: w => bar(w).wars.add("ZES"),
    "lost homeland": w => w.states[624].controller = "RIV",
    "no settlement": w => w.states[614].flags.delete(P + "_settlement"),
    "no councils": w => bar(w).focuses.delete(P + "_WIT_councils"),
    "lost route": w => bar(w).flags.delete("HSM_BAR_collegium"),
    "capitulated": w => bar(w).capitulated = true
};
for (const [name, mutate] of Object.entries(integrationInvalid)) test("integration blocks " + name + " at start and cancellation prevents late completion", () => {
    const w = integratedWorld(); mutate(w); assert(!start(w, "_registry_614"));
    const q = integratedWorld(); start(q, "_registry_614"); mutate(q); q.day = 60; cancel(q, "_registry_614"); finish(q, "_registry_614");
    assert(!hasFlag(q, q.states[614], P + "_registered")); assert.equal(bar(q).pp, 450);
});
test("reconciliation with remaining Wittenland does not revoke rights in already awarded provinces", () => {
    const w = integratedWorld();
    bar(w).flags.set("HSM_BAR_WIT_agreement", {day: 0});
    bar(w).pacts.add("WIT"); bar(w).factions.add("WIT");
    assert(start(w, "_registry_614")); w.day = 60; finish(w, "_registry_614");
    assert(start(w, "_citizenship_614")); w.day = 180; finish(w, "_citizenship_614");
    assert(w.states[614].cores.has("BAR"));
    assert(!start(w, "_registry_615")); assert(!w.states[615].cores.has("BAR"));
});
test("citizenship requires the higher thresholds even at completion", () => {
    for (const [c, r, allowed] of [[59, 10, false], [60, 11, false], [60, 10, true]]) {
        const w = integratedWorld(); w.states[614].flags.set(P + "_registered", {day: 0}); Object.assign(w.states[614], {compliance: c, resistance: r});
        assert.equal(start(w, "_citizenship_614"), allowed);
    }
    const w = integratedWorld(); w.states[614].flags.set(P + "_registered", {day: 0}); start(w, "_citizenship_614");
    w.day = 120; w.states[614].resistance = 11; finish(w, "_citizenship_614"); assert(!w.states[614].cores.has("BAR"));
});
test("councils unlock actual registration before charter, but citizenship waits for charter", () => {
    const w = integratedWorld(); bar(w).focuses.delete(P + "_WIT_charter");
    assert(check(w, bar(w), prop(decisions[P + "_registry_614"], "visible")));
    assert(!check(w, bar(w), prop(decisions[P + "_citizenship_614"], "visible")));
    assert(start(w, "_registry_614")); w.day = 60; finish(w, "_registry_614");
    assert(hasFlag(w, w.states[614], P + "_registered"));
    assert(!w.states[614].cores.has("BAR")); assert(!start(w, "_citizenship_614"));
    bar(w).focuses.add(P + "_WIT_charter"); assert(start(w, "_citizenship_614"));
    bar(w).focuses.delete(P + "_WIT_charter"); w.day = 180; finish(w, "_citizenship_614");
    assert(!w.states[614].cores.has("BAR"), "Late charter loss cannot award a core");
});
test("teardown clears work and owned goals but retains history, treaties and completed provincial status", () => {
    const w = integratedWorld(); start(w, "_registry_614"); bar(w).flags.set("HSM_BAR_WIT_agreement", {day: 0});
    w.states[615].cores.add("BAR"); effect(w, "_teardown"); w.day = 120; finish(w, "_registry_614");
    assert(!hasFlag(w, w.states[614], P + "_registered")); assert(w.states[615].cores.has("BAR"));
    assert(hasFlag(w, bar(w), P + "_WIT_victory")); assert(hasFlag(w, bar(w), "HSM_BAR_WIT_agreement"));
    assert.equal(w.removed.length, 14);
});
test("real institutional hook immediately cancels work and transient defensive candidacy", () => {
    const dissolve = prop(parse(read("common/scripted_effects/HSM_BAR_core_effects.txt")), "HSM_BAR_dissolve_institutions");
    const hooks = dissolve.filter(n => walk([n]).some(q => q.key === P + "_teardown"));
    assert.equal(hooks.length, 1);
    const w = integratedWorld(); bar(w).focuses.add(P); start(w, "_registry_614");
    run(w, bar(w), hooks); assert.equal(w.removed.length, 14);
    run(w, bar(w), dissolve.filter(n => n.key === "clr_country_flag"));
    w.day = 60; finish(w, "_registry_614"); assert(!hasFlag(w, w.states[614], P + "_registered"));
    const q = world(); war(q); run(q, bar(q), hooks);
    assert(!hasFlag(q, bar(q), P + "_defending"));
    const untouched = world(), before = structuredClone(untouched); run(untouched, bar(untouched), hooks);
    assert.deepEqual(untouched, before);
});
for (const tag of ["ZES", "OLV"]) test(tag + " actual treaty acceptance hook revokes its issued war goal immediately", () => {
    const accept = prop(parse(read("common/scripted_effects/HSM_BAR_diplomacy.txt")), "HSM_BAR_dip_" + tag + "_accept");
    const body = prop(accept, "if");
    const index = body.findIndex(n => n.key === "set_country_flag" && n.value === "HSM_BAR_" + tag + "_agreement");
    assert(index >= 0); assert(walk([body[index + 1]]).some(n => n.key === P + "_maintain"));
    const w = world(); bar(w).focuses.add(P + "_" + tag + "_hearing");
    assert(completeFocus(w, P + "_" + tag + "_mandate")); assert(bar(w).goals.has(tag));
    run(w, bar(w), body.slice(index, index + 2)); assert(!bar(w).goals.has(tag));
    const unrelated = world(); bar(unrelated).goals.add(tag);
    run(unrelated, bar(unrelated), body.slice(index, index + 2)); assert(bar(unrelated).goals.has(tag));
});
test("localization parity, BOM, all IDs and all referenced localization keys", () => {
    const locales = ["english", "russian"].map(language => {
        const file = path.join(mod, "localisation", language, P + "_l_" + language + ".yml");
        assert.equal(fs.readFileSync(file).subarray(0, 3).toString("hex"), "efbbbf");
        const lines = fs.readFileSync(file, "utf8").trim().split(/\r?\n/).slice(1);
        const keys = lines.map(line => { const m = /^ ([\w.]+):0 "(?:[^"\\]|\\.)*"$/.exec(line); assert(m, line); return m[1]; });
        assert.equal(new Set(keys).size, keys.length); return new Set(keys);
    });
    assert.deepEqual([...locales[0]].sort(), [...locales[1]].sort());
    const needed = [P + "_policy", ...Object.keys(focuses).flatMap(k => [k, k + "_desc"]), ...Object.keys(decisions).flatMap(k => [k, k + "_desc"])];
    for (const folder of ["events", "common/national_focus", "common/decisions", "common/scripted_triggers", "common/scripted_effects", "common/on_actions"]) {
        for (const n of walk(load(folder))) {
            if (["title", "desc", "name", "text", "tooltip", "custom_effect_tooltip", "has_country_flag", "has_state_flag", "flag", "set_country_flag", "set_state_flag"].includes(n.key) && typeof n.value === "string" && n.value.startsWith(P)) needed.push(n.value);
        }
    }
    for (const key of needed) assert(locales[0].has(key), "Missing " + key);
});
test("no automatic war, transfer, puppet, foreign-core removal or WIT war goal", () => {
    for (const source of [effects, events, focuses]) {
        const nodes = walk(Object.values(source).flat());
        for (const k of ["declare_war_on", "annex_country", "transfer_state", "puppet", "remove_core_of"]) assert(!nodes.some(n => n.key === k), k);
        for (const n of nodes.filter(n => n.key === "create_wargoal")) assert(["ZES", "OLV"].includes(prop(n.value, "target")));
    }
});
test("all scripted calls are literal yes/no; fixtures reject former argument forwarding", () => {
    for (const folder of ["common/scripted_triggers", "common/scripted_effects", "common/on_actions", "common/national_focus", "common/decisions", "events"]) {
        const definitions = load(folder);
        const nodes = definitions.flatMap(n => Array.isArray(n.value) ? walk(n.value) : [n]);
        for (const n of nodes) {
            if (triggers[n.key] || effects[n.key]) assert(["yes", "no"].includes(n.value), n.key + ": argument block");
            assert(!String(n.key).includes("$"), "Unexpanded parameter in key");
            if (typeof n.value === "string") assert(!/\$\w+\$/.test(n.value), "Unexpanded script parameter");
        }
    }
    const w = world();
    assert.throws(() => check(w, bar(w), [{key: P + "_ZES_target", value: [{key: "TAG", value: "ZES"}]}]), /Unsupported scripted trigger arguments/);
});
test("pre-victory focuses and declarations cannot create settlement or registry permissions", () => {
    const w = world();
    for (const [id, f] of Object.entries(focuses)) {
        if (check(w, bar(w), prop(f, "available"))) run(w, bar(w), prop(f, "completion_reward"));
        assert(!hasFlag(w, bar(w), P + "_WIT_victory"), id);
    }
    war(w);
    for (const s of Object.values(w.states)) {
        assert(!hasFlag(w, s, P + "_settlement"));
        assert(!hasFlag(w, s, P + "_registered"));
        assert.equal(s.cores.has("BAR"), s.id === 624);
    }
});
test("fractional compliance and resistance do not slip below documented thresholds", () => {
    for (const [compliance, resistance, allowed] of [[24.9, 35, false], [25, 35.1, false], [25, 35, true]]) {
        const w = integratedWorld(); Object.assign(w.states[614], {compliance, resistance});
        assert.equal(start(w, "_registry_614"), allowed);
    }
    for (const [compliance, resistance, allowed] of [[59.9, 10, false], [60, 10.1, false], [60, 10, true]]) {
        const w = integratedWorld(); w.states[614].flags.set(P + "_registered", {day: 0}); Object.assign(w.states[614], {compliance, resistance});
        assert.equal(start(w, "_citizenship_614"), allowed);
    }
});

test("native state comparisons use strict operators with NOT, never >= or <=", () => {
    for (const folder of ["common/scripted_triggers", "common/scripted_effects", "common/on_actions", "common/national_focus", "common/decisions", "events"]) {
        for (const n of walk(load(folder))) assert(![">=", "<=", "!="].includes(n.op), folder + ": unsupported comparison " + n.key);
    }
    const w = integratedWorld();
    for (const [key, op, value] of [["compliance", ">=", "25"], ["compliance", ">=", "60"], ["resistance", "<=", "35"], ["resistance", "<=", "10"]]) {
        assert.throws(() => check(w, w.states[614], [{key, op, value}]), /Unsupported native state comparison/);
    }
    assert.throws(() => check(w, w.states[614], [{key: "<", op: "=", value: "25"}]), /Unsupported fixture trigger/);
});

test("OLV labels follow current native country name and do not invent an HRE dependency", () => {
    for (const language of ["english", "russian"]) {
        const text = read("localisation/" + language + "/" + P + "_l_" + language + ".yml");
        for (const suffix of ["_OLV_hearing", "_OLV_mandate", "_OLV_hearing_desc", "_OLV_mandate_desc", "_OLV_mandate_tt", "_OLV_goal", "_OLV_hearing_d", "_OLV_vote_d"]) {
            const line = text.split(/\r?\n/).find(s => s.startsWith(" " + P + suffix + ":"));
            assert(line?.includes("[OLV.GetName"), suffix);
        }
        assert(!/Southern Deer|Южн\S* Олен|50 political power parliamentary vote|голосование .*за 50/.test(text));
    }
    for (const f of Object.values(focuses)) assert(!walk(f).some(n => n.key === "HRE" || n.value === "HRE"));
});

if (process.argv.includes("--native")) {
    const game = process.env.HOI4_GAME_ROOT || "C:/shit/Steam/steamapps/common/Hearts of Iron IV";
    const eaw = process.env.EAW_ROOT || "C:/shit/Steam/steamapps/workshop/content/394360/1826643372";
    const nativeRead = (base, file) => fs.readFileSync(path.join(base, file), "utf8");
    test("installed EaW tags and exact starting WIT state whitelist", () => {
        const tags = nativeRead(eaw, "common/country_tags/00_countries.txt");
        assert.match(tags, /ZES\s*=\s*"countries\/ZebraSettlement.txt"/);
        assert.match(tags, /OLV\s*=\s*"countries\/OleniaVikings.txt"/);
        const owned = [];
        for (const file of fs.readdirSync(path.join(eaw, "history/states"))) {
            if (!file.endsWith(".txt")) continue;
            const text = nativeRead(eaw, "history/states/" + file);
            if (/owner\s*=\s*WIT\b/.test(text)) owned.push(Number(/\bid\s*=\s*(\d+)/.exec(text)[1]));
        }
        assert.deepEqual(owned.sort((a, b) => a - b), states);
        assert.match(nativeRead(eaw, "localisation/english/country_WIT_l_english.yml"), /POLITICS_WHITE_STAR_DESC:[^\n]*estranged brother, Silver Star/);
    });
    test("installed OLV is Austurland with Hreindyraland cosmetics, not a separate HRE tag", () => {
        for (const [language, baseName, cosmeticName] of [
            ["english", "Austurland", "Hreind\u00fdraland"],
            ["russian", "Эйстюрланд", "Хрейндираланд"]
        ]) {
            const countries = nativeRead(eaw, "localisation/" + language + "/countries_griffonia_l_" + language + ".yml");
            assert.match(countries, new RegExp('OLV:0 "' + baseName + '"'));
            const cosmetic = nativeRead(eaw, "localisation/" + language + "/country_OLV_l_" + language + ".yml");
            for (const id of ["kingdom", "rike"]) assert(cosmetic.includes('OLV_' + id + '_neutrality:0 "' + cosmeticName + '"'));
        }
        const source = nativeRead(eaw, "events/Austurland Events.txt");
        assert.match(source, /set_cosmetic_tag\s*=\s*OLV_kingdom/);
        assert.match(source, /set_cosmetic_tag\s*=\s*OLV_rike/);
        assert.match(nativeRead(eaw, "history/countries/OLV - OleniaVikings.txt"), /capital\s*=\s*412/);
    });
    test("native engine documents state comparisons; EaW uses NOT for inclusive compliance", () => {
        const doc = nativeRead(game, "documentation/triggers_documentation.md");
        assert.match(doc, /## compliance[\s\S]*?Example: compliance > 50/);
        assert.match(doc, /## resistance[\s\S]*?Example: resistance > 50/);
        assert.match(nativeRead(eaw, "common/scripted_effects/EAW_resistance_effect.txt"), /NOT\s*=\s*\{\s*compliance < 40\s*\}/);
    });
    test("native on-action contracts: direct target, relation order, victory/defeat scopes", () => {
        const source = nativeRead(game, "common/on_actions/00_on_actions.txt");
        assert.match(source, /#FROM is war target\s+on_declare_war/);
        assert.match(source, /# ROOT is capitulated country, FROM is winner\s+on_capitulation/);
        assert.match(nativeRead(game, "common/on_actions/_documentation.md"), /on_peaceconference_ended[^\r\n]*ROOT is winner, FROM is loser/);
        assert.match(nativeRead(eaw, "common/on_actions/07_nsb_on_actions.txt"), /on_war_relation_added[^\r\n]*1st is on_declare_war/);
    });
    test("every focus sprite has an installed or local standard and shine definition", () => {
        const files = ["goals.gfx", "goals_shine.gfx"].map(f => nativeRead(game, "interface/" + f)).join("\n") +
            nativeRead(eaw, "interface/focus/focus_generic.gfx") + nativeRead(eaw, "interface/focus/shine/focus_generic_shine.gfx") +
            fs.readdirSync(path.join(mod, "interface")).filter(f => f.endsWith(".gfx")).map(f => read("interface/" + f)).join("\n");
        for (const f of Object.values(focuses)) for (const suffix of ["", "_shine"]) assert(new RegExp("name\\s*=\\s*\\\"?" + prop(f, "icon") + suffix + "(?:\\\"|\\s)").test(files), prop(f, "icon") + suffix);
    });
    test("research categories and decision icons exist in installed definitions", () => {
        const categories = nativeRead(eaw, "common/technology_tags/00_technology.txt");
        for (const source of [load("common/national_focus"), load("events")]) {
            for (const n of walk(source).filter(n => n.key === "add_tech_bonus")) assert(new RegExp("\\b" + prop(n.value, "category") + "\\b").test(categories), prop(n.value, "category"));
        }
        const sprites = nativeRead(game, "interface/decisions.gfx");
        for (const d of Object.values(decisions)) assert(sprites.includes("GFX_decision_" + prop(d, "icon")));
        assert(sprites.includes("GFX_decision_category_generic_political_actions"));
    });
    test("actual province bitmap confirms BAR land borders ZES, OLV and WIT", () => {
        const owner = new Map(), provOwner = new Map();
        for (const file of fs.readdirSync(path.join(eaw, "history/states"))) {
            if (!file.endsWith(".txt")) continue;
            const state = prop(parse(nativeRead(eaw, "history/states/" + file), true), "state");
            const tag = prop(prop(state, "history"), "owner");
            for (const p of prop(state, "provinces")) provOwner.set(Number(p.value), tag);
        }
        for (const line of nativeRead(eaw, "map/definition.csv").trim().split(/\r?\n/)) {
            const [id, r, g, b] = line.split(";").map(Number);
            owner.set((r << 16) | (g << 8) | b, provOwner.get(id));
        }
        const bmp = fs.readFileSync(path.join(eaw, "map/provinces.bmp"));
        assert.equal(bmp.toString("ascii", 0, 2), "BM"); assert.equal(bmp.readUInt16LE(28), 24); assert.equal(bmp.readUInt32LE(30), 0);
        const offset = bmp.readUInt32LE(10), width = bmp.readInt32LE(18), height = Math.abs(bmp.readInt32LE(22)), stride = (width * 3 + 3) & ~3;
        const colour = i => (bmp[i + 2] << 16) | (bmp[i + 1] << 8) | bmp[i];
        const barColours = new Set([...owner].filter(([, tag]) => tag === "BAR").map(([rgb]) => rgb));
        const neighbours = new Set();
        for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
            const at = offset + y * stride + x * 3;
            if (!barColours.has(colour(at))) continue;
            for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) if (x + dx >= 0 && x + dx < width && y + dy >= 0 && y + dy < height) neighbours.add(owner.get(colour(at + dx * 3 + dy * stride)));
        }
        for (const tag of ["WIT", "ZES", "OLV"]) assert(neighbours.has(tag), "No land border: " + tag);
        console.log("Native BAR neighbours: " + [...neighbours].filter(Boolean).sort().join(", "));
    });
}
console.log(`Barrad Collegium frontiers: ${passed} scenarios passed, ${failed} failed.`);
console.log("Deterministic script fixtures and optional installed-source checks; live HOI4 callback timing remains unverified.");
if (failed) process.exitCode = 1;
