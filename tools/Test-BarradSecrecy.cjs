"use strict";
// Run: node tools/Test-BarradSecrecy.cjs
// Small, strict fixture evaluator for retired-cover cleanup and liaison gates.
// It does not model HOI4 scheduling or prove that the engine accepts the scripts.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const root = path.join(__dirname, "..", "mod", "HoISubmod");
function read(file) {
    const t = fs.readFileSync(path.join(root, file), "utf8")
        .match(/"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}]|[<>=!]+|[^\s{}<>=!#"]+/g)
        .filter(x => !x.startsWith("#"));
    let i = 0;
    function block(nested = false) {
        const out = [];
        while (i < t.length && t[i] !== "}") {
            const key = t[i++], op = t[i++];
            assert(["=", "<", ">", ">=", "<="].includes(op), "Unknown syntax: " + key + " " + op);
            let value = t[i++];
            if (value === "{") { value = block(true); assert.equal(t[i++], "}"); }
            out.push({key, op, value});
        }
        if (!nested) assert.equal(i, t.length, "Unexpected closing brace");
        return out;
    }
    return block();
}
const prop = (b, k) => b.find(n => n.key === k)?.value;
const defs = b => Object.fromEntries(b.map(n => [n.key, n.value]));
const effects = { ...defs(read("common/scripted_effects/HSM_BAR_core_effects.txt")), ...defs(read("common/scripted_effects/HSM_BAR_service_rewards.txt")) };
const triggers = defs(read("common/scripted_triggers/HSM_BAR_core_triggers.txt"));
effects.HSM_BAR_residencies_begin = prop(read("common/scripted_effects/HSM_BAR_residencies.txt"), "HSM_BAR_residencies_begin");
triggers.HSM_BAR_residencies_actor = prop(read("common/scripted_triggers/HSM_BAR_residencies.txt"), "HSM_BAR_residencies_actor");
const decisions = defs(prop(read("common/decisions/HSM_BAR_core.txt"), "HSM_BAR_service_affairs"));
const eventDefs = read("events/HSM_BAR_core.txt").concat(read("events/HSM_BAR_smile.txt"));
const events = Object.fromEntries(eventDefs.filter(n => n.key === "country_event").map(n => [prop(n.value, "id"), n.value]));
const modifier = prop(read("common/dynamic_modifiers/HSM_BAR_core.txt"), "HSM_BAR_service_capacity");
const country = () => ({flags: new Set(), focuses: new Set(), dlc: new Set(), modifiers: new Set(), capitulated: false, vars: {}, ideas: new Set(), pp: 0, wars: new Set(), exists: true, government: "democratic", leader: "", original: "", subject: false, owned: new Set(), controlled: new Set()});
function world() {
    const w = {BAR: country(), EQS: country(), CRY: country()};
    for (const [tag, s] of Object.entries(w)) s.original = tag;
    w.BAR.owned.add(624); w.BAR.controlled.add(624);
    for (const f of ["active", "directorate", "service_founded", "liaison_open"]) w.BAR.flags.add("HSM_BAR_" + f);
    w.CRY.leader = "CRY_sombra";
    return w;
}
function condition(nodes, w, tag = "BAR") {
    const s = w[tag];
    return nodes.every(n => {
        const {key: k, value: v, op} = n;
        if (k === "AND") return condition(v, w, tag);
        if (k === "custom_trigger_tooltip") return condition(v.filter(x => x.key !== "tooltip"), w, tag);
        if (k === "OR") return v.some(x => condition([x], w, tag));
        if (k === "NOT") return !v.some(x => condition([x], w, tag));
        if (w[k]) return condition(v, w, k);
        if (triggers[k]) { assert.equal(v, "yes"); return condition(triggers[k], w, tag); }
        if (k === "tag") return tag === v;
        if (k === "original_tag") return s.original === v;
        if (k === "is_subject") { assert(["yes", "no"].includes(v)); return s.subject === (v === "yes"); }
        if (k === "owns_state") return s.owned.has(Number(v));
        if (k === "controls_state") return s.controlled.has(Number(v));
        if (k === "exists") return s.exists === (v === "yes");
        if (k === "has_government") return s.government === v;
        if (k === "has_war_with") return s.wars.has(v);
        if (k === "has_country_flag") return s.flags.has(v);
        if (k === "has_completed_focus") { assert.equal(typeof v, "string"); return s.focuses.has(v); }
        if (k === "has_dlc") { assert.equal(typeof v, "string"); return s.dlc.has(v.replace(/^"|"$/g, "")); }
        if (k === "has_capitulated") { assert(["yes", "no"].includes(v)); return s.capitulated === (v === "yes"); }
        if (k === "has_dynamic_modifier") return s.modifiers.has(Array.isArray(v) ? prop(v, "modifier") : v);
        if (k === "has_idea") return s.ideas.has(v);
        if (k === "has_country_leader") {
            assert.equal(prop(v, "ruling_only"), "yes");
            return s.leader === prop(v, "character");
        }
        if (k === "check_variable") {
            if (prop(v, "var")) {
                const a = s.vars[prop(v, "var")] || 0, b = Number(prop(v, "value"));
                assert.equal(prop(v, "compare"), "greater_than_or_equals");
                return a >= b;
            }
            assert.equal(v.length, 1);
            const {key, value, op} = v[0], a = s.vars[key] || 0, b = Number(value);
            if (op === "<") return a < b;
            if (op === ">") return a > b;
            if (op === "=") return a === b;
            throw Error("Unsupported variable comparison " + op);
        }
        throw Error("Unknown condition " + k + " " + op);
    });
}
const external = new Set(["HSM_BAR_anomalies_pulse", "HSM_BAR_collegium_refresh", "HSM_BAR_refresh_case_outcomes"]);
function run(nodes, w, tag = "BAR") {
    const s = w[tag];
    let branch = false;
    for (const n of nodes) {
        const {key: k, value: v} = n;
        if (k === "if" || k === "else_if") {
            if (k === "if") branch = false;
            if (!branch && condition(prop(v, "limit"), w, tag)) {
                branch = true; run(v.filter(x => x.key !== "limit"), w, tag);
            }
        } else if (k === "else") {
            if (!branch) run(v, w, tag);
            branch = true;
        } else if (k === "hidden_effect") run(v, w, tag);
        else if (w[k]) run(v, w, k);
        else if (k === "set_country_flag") s.flags.add(Array.isArray(v) ? prop(v, "flag") : v);
        else if (k === "clr_country_flag") s.flags.delete(v);
        else if (k === "add_ideas") s.ideas.add(v);
        else if (k === "remove_ideas") s.ideas.delete(v);
        else if (k === "add_dynamic_modifier" || k === "remove_dynamic_modifier") {
            assert.deepEqual(v.map(n => n.key), ["modifier"]);
            s.modifiers[k === "add_dynamic_modifier" ? "add" : "delete"](prop(v, "modifier"));
        }
        else if (k === "clear_variable") {
            assert.equal(typeof v, "string");
            assert(/^HSM_BAR_\w+$/.test(v));
            delete s.vars[v];
        }
        else if (k === "add_political_power") s.pp += Number(v);
        else if (k === "clamp_variable") {
            const name = prop(v, "var");
            s.vars[name] = Math.max(Number(prop(v, "min")), Math.min(Number(prop(v, "max")), s.vars[name] || 0));
        } else if (["set_variable", "add_to_variable", "subtract_from_variable", "multiply_variable"].includes(k)) {
            assert.equal(v.length, 1);
            const name = v[0].key, rhs = v[0].value;
            const number = Number.isNaN(Number(rhs)) ? (s.vars[rhs] || 0) : Number(rhs);
            if (k === "set_variable") s.vars[name] = number;
            else if (k === "add_to_variable") s.vars[name] = (s.vars[name] || 0) + number;
            else if (k === "subtract_from_variable") s.vars[name] = (s.vars[name] || 0) - number;
            else s.vars[name] = (s.vars[name] || 0) * number;
        } else if (external.has(k)) {
            // Tested elsewhere; no fixture behavior is invented for these helpers.
            assert.equal(v, "yes");
        } else if (effects[k]) { assert.equal(v, "yes"); run(effects[k], w, tag); }
        else if (!["name", "ai_chance", "country_event", "custom_effect_tooltip"].includes(k)) {
            throw Error("Unknown effect " + k);
        }
    }
}
function choose(id, option, w, tag = "BAR") {
    const b = events[id].find(n => n.key === "option" && prop(n.value, "name") === id + "." + option);
    assert(b, "Missing option"); run(b.value, w, tag);
}
let passed = 0, failed = 0;
function test(name, body) {
    try { body(); passed++; console.log("PASS " + name); }
    catch (e) { failed++; console.error("FAIL " + name + "\n" + e.stack); }
}
const retired = /HSM_BAR_(?:cover_integrity|service_coordination|initialize_cover|rotate_fronts)/;
const cleanupFile = "common/scripted_effects/HSM_BAR_core_effects.txt";
function auditRetired(nodes, file, parents = [], cleanups = []) {
    for (const n of nodes) {
        assert(!retired.test(n.key), file + ": retired key " + n.key);
        if (Array.isArray(n.value)) auditRetired(n.value, file, [...parents, n.key], cleanups);
        else if (typeof n.value === "string" && retired.test(n.value)) {
            assert.equal(file, cleanupFile, "Retired reference outside save cleanup: " + file);
            assert.equal(n.key, "clear_variable", "Retired variable used by " + n.key);
            assert.deepEqual(parents, ["HSM_BAR_core_refresh", "hidden_effect"], "Cleanup must be unconditional and hidden");
            assert(["HSM_BAR_cover_integrity", "HSM_BAR_service_coordination"].includes(n.value), "Invalid cleanup target");
            cleanups.push(n.value);
        }
    }
    return cleanups;
}
function sourceFiles(dir) {
    return fs.readdirSync(path.join(root, dir), { withFileTypes: true }).flatMap(entry => {
        const file = path.posix.join(dir, entry.name);
        return entry.isDirectory() ? sourceFiles(file) : /\.(?:txt|gui|gfx|yml)$/.test(entry.name) ? [file] : [];
    });
}
test("numeric cover has no reads, writes, gates or UI beyond two hidden save cleanups", () => {
    const { parse } = require("./Test-BarradCases.cjs"), cleanups = [];
    for (const dir of ["common", "events", "history", "interface", "localisation"]) {
        for (const file of sourceFiles(dir)) {
            const text = fs.readFileSync(path.join(root, file), "utf8");
            if (file.endsWith(".yml")) {
                const active = text.split(/\r?\n/).filter(line => !/^\s*#/.test(line)).join("\n");
                assert(!retired.test(active), "Retired localization/UI reference: " + file);
                assert(!/cover integrity|над[её]жност[ьи]\s+прикрытия/i.test(active), "Retired numeric meter label: " + file);
            } else auditRetired(parse(text), file, [], cleanups);
        }
    }
    assert.deepEqual(cleanups.sort(), ["HSM_BAR_cover_integrity", "HSM_BAR_service_coordination"]);
});
test("absence audit rejects hidden writes, indirect reads, gates and UI references", () => {
    const { parse } = require("./Test-BarradCases.cjs");
    for (const code of [
        "set_variable = { HSM_BAR_cover_integrity = 70 }",
        "add_to_variable = { HSM_BAR_cover_integrity = 3 }",
        "set_variable = { HSM_BAR_other = HSM_BAR_cover_integrity }",
        "check_variable = { var = HSM_BAR_cover_integrity value = 40 compare = greater_than_or_equals }",
        "has_variable = HSM_BAR_cover_integrity",
        'text = "[?HSM_BAR_cover_integrity]"',
        "political_power_gain = HSM_BAR_service_coordination",
        "clamp_variable = { var = HSM_BAR_cover_integrity min = 0 max = 100 }"
    ]) assert.throws(() => auditRetired(parse("HSM_BAR_core_refresh = { hidden_effect = { " + code + " } }"), cleanupFile));
    assert.throws(() => auditRetired(parse("clear_variable = HSM_BAR_cover_integrity"), cleanupFile));
    assert.throws(() => run(parse("unsupported_barrad_effect = yes"), world()), /Unknown effect/);
    assert.throws(() => condition(parse("unsupported_barrad_condition = yes"), world()), /Unknown condition/);
});
test("service initializes once, cleans retired penalty and preserves research progress", () => {
    const w = world(), s = w.BAR;
    s.ideas.add("HSM_BAR_displaced_families"); s.flags.add("HSM_BAR_project_wards_done");
    assert.equal(effects.HSM_BAR_initialize_cover, undefined);
    run(effects.HSM_BAR_initialize_service, w);
    assert(!Object.hasOwn(s.vars, "HSM_BAR_cover_integrity")); assert(!s.ideas.has("HSM_BAR_displaced_families"));
    assert(s.flags.has("HSM_BAR_covert_structure_initialized"));
    const before = structuredClone(w);
    run(effects.HSM_BAR_initialize_service, w);
    assert.deepEqual(w, before); assert(s.flags.has("HSM_BAR_project_wards_done"));
    const legacy = world(); legacy.BAR.flags.add("HSM_BAR_covert_structure_initialized");
    const old = structuredClone(legacy); run(effects.HSM_BAR_initialize_service, legacy); assert.deepEqual(legacy, old);
});
test("refresh clears obsolete save variables and retains concrete research milestones", () => {
    assert.equal(prop(modifier, "political_power_gain"), undefined);
    assert.equal(prop(modifier, "research_speed_factor"), "HSM_BAR_service_research");
    for (const value of [-20, 0, 50, 70, 100, 150]) {
        const w = world(), s = w.BAR; s.vars.HSM_BAR_cover_integrity = value; s.vars.HSM_BAR_capacity = value;
        s.vars.HSM_BAR_public_trust = value;
        s.vars.HSM_BAR_service_coordination = value * 0.123;
        s.flags.add("HSM_BAR_service_training_seal_labs");
        s.focuses.add("HSM_BAR_dir_archives");
        run(effects.HSM_BAR_core_refresh, w);
        assert(!Object.hasOwn(s.vars, "HSM_BAR_cover_integrity"));
        assert(!Object.hasOwn(s.vars, "HSM_BAR_service_coordination"));
        assert(!Object.hasOwn(s.vars, "HSM_BAR_capacity"));
        assert(!Object.hasOwn(s.vars, "HSM_BAR_public_trust"));
        assert.equal(s.vars.HSM_BAR_service_research, 0.03);
        assert.equal(s.pp, 0);
        const after = structuredClone(w); run(effects.HSM_BAR_core_refresh, w); assert.deepEqual(w, after);
    }
});
test("procurement preserves narrative choice without meter rewards or fees", () => {
    const a = world(), b = world(); choose("hsm_bar_core.1", "a", a); choose("hsm_bar_core.1", "b", b);
    assert.equal(a.BAR.pp, 0); assert.equal(b.BAR.pp, 0);
    assert(a.BAR.flags.has("HSM_BAR_split_ledgers")); assert(b.BAR.flags.has("HSM_BAR_borrowed_accounts"));
    for (const w of [a, b]) for (const name of ["cover_integrity", "capacity", "public_trust"]) assert(!Object.hasOwn(w.BAR.vars, "HSM_BAR_" + name));
});
test("former meter-only core choices are free and retain replay history", () => {
    for (const id of [1, 2, 5, 6, 9, 10]) {
        const w = world(); choose("hsm_bar_core." + id, "a", w);
        assert.equal(w.BAR.pp, 0, "Obsolete fee on core." + id + ".a");
        assert(w.BAR.flags.has("HSM_BAR_core_" + id + "_done"));
        const after = structuredClone(w); choose("hsm_bar_core." + id, "a", w); assert.deepEqual(w, after);
    }
    for (const [id, cost] of [[11, 40], [13, 25], [15, 75]]) {
        const w = world(); w.BAR.flags.add("HSM_BAR_suppression_live");
        choose("hsm_bar_core." + id, "a", w);
        assert.equal(w.BAR.pp, -cost, "Retained core." + id + ".a cost changed");
    }
    for (const resolved of [false, true]) {
        const w = world();
        if (resolved) { w.BAR.flags.add("HSM_BAR_suppression_live"); w.BAR.flags.add("HSM_BAR_suppression_resolved"); }
        choose("hsm_bar_core.13", "a", w);
        assert.equal(w.BAR.pp, 0, "Inactive or resolved trial still charges its opening fee");
    }
});
test("rotating fronts maintenance decision is removed", () => {
    assert.equal(decisions.HSM_BAR_rotate_fronts, undefined);
});
test("all service event choices are inert after dissolution", () => {
    for (let i = 1; i <= 15; i++) {
        const w = world(); w.BAR.flags.delete("HSM_BAR_active");
        assert(!condition(prop(events["hsm_bar_core." + i], "trigger"), w));
        for (const n of events["hsm_bar_core." + i].filter(n => n.key === "option")) {
            const before = structuredClone(w); run(n.value, w); assert.deepEqual(w, before);
        }
    }
});
test("service choices require founding and cannot be collected twice", () => {
    for (let i = 1; i <= 15; i++) {
        const id = "hsm_bar_core." + i;
        for (const option of events[id].filter(n => n.key === "option")) {
            const w = world(); w.BAR.flags.add("HSM_BAR_suppression_live");
            run(option.value, w);
            assert(w.BAR.flags.has("HSM_BAR_core_" + i + "_done"));
            if (i === 6) assert(w.BAR.flags.has("HSM_BAR_residencies_started"), "Both convoy endings start the guarded continuation");
            const after = structuredClone(w); run(option.value, w); assert.deepEqual(w, after);
            const early = world(); early.BAR.flags.delete("HSM_BAR_service_founded");
            assert(!condition(prop(events[id], "trigger"), early));
            const before = structuredClone(early); run(option.value, early); assert.deepEqual(early, before);
        }
    }
});
test("courier and transfer timers cannot outlive the hidden institution", () => {
    for (const id of ["HSM_BAR_trace_couriers", "HSM_BAR_watched_transfer"]) {
        const w = world(); w.BAR.flags.delete("HSM_BAR_active");
        assert(condition(prop(decisions[id], "cancel_trigger"), w));
        const before = structuredClone(w); run(prop(decisions[id], "remove_effect"), w); assert.deepEqual(w, before);
    }
});
test("liaison absent before Sombra, after his defeat, without mandate or with hostile Equestria", () => {
    const d = decisions.HSM_BAR_contact_smile;
    assert(condition(prop(d, "visible"), world()));
    for (const mutate of [
        w => w.CRY.leader = "", w => w.CRY.exists = false,
        w => w.BAR.flags.delete("HSM_BAR_liaison_open"), w => w.BAR.flags.delete("HSM_BAR_directorate"),
        w => w.BAR.flags.delete("HSM_BAR_active"), w => w.EQS.government = "fascism",
        w => w.EQS.exists = false, w => w.BAR.wars.add("EQS")
    ]) { const w = world(); mutate(w); assert(!condition(prop(d, "visible"), w)); }
});
test("liaison ignores old cover values while retaining cooldown and compromised-channel gates", () => {
    const d = decisions.HSM_BAR_contact_smile, w = world();
    assert(condition(prop(d, "available"), w));
    for (const value of [-987.5, 0, 39, 40, 70, 999]) {
        w.BAR.vars.HSM_BAR_cover_integrity = value;
        assert(condition(prop(d, "available"), w), "Obsolete cover gates liaison at " + value);
    }
    for (const f of ["HSM_BAR_smile_contact_cooldown", "HSM_BAR_smile_compromised"]) {
        w.BAR.flags.add(f); assert(!condition(prop(d, "available"), w)); w.BAR.flags.delete(f);
    }
});
test("already open acceptance rechecks actual Sombra and request lifetime", () => {
    const valid = world(); valid.BAR.flags.add("HSM_BAR_smile_request_pending");
    choose("hsm_bar_smile.1", "a", valid, "EQS"); assert(valid.BAR.flags.has("HSM_BAR_smile_partner"));
    for (const mutate of [w => w.CRY.leader = "", w => w.BAR.flags.delete("HSM_BAR_active"), w => w.BAR.flags.delete("HSM_BAR_smile_request_pending"), w => w.BAR.flags.add("HSM_BAR_smile_compromised")]) {
        const w = world(); w.BAR.flags.add("HSM_BAR_smile_request_pending"); mutate(w);
        choose("hsm_bar_smile.1", "a", w, "EQS"); assert(!w.BAR.flags.has("HSM_BAR_smile_partner"));
    }
});
test("contact alone grants no war aid; completed shared wards and current war required", () => {
    const w = world(), s = w.BAR;
    s.flags.add("HSM_BAR_smile_partner");
    assert(!condition(triggers.HSM_BAR_sombra_cooperation, w));
    s.flags.add("HSM_BAR_project_wards_done"); choose("hsm_bar_smile.3", "a", w);
    assert(s.flags.has("HSM_BAR_wards_shared")); assert(!condition(triggers.HSM_BAR_sombra_cooperation, w));
    w.EQS.wars.add("CRY"); assert(condition(triggers.HSM_BAR_sombra_cooperation, w));
    w.CRY.leader = ""; assert(!condition(triggers.HSM_BAR_sombra_cooperation, w));
    w.CRY.leader = "CRY_sombra"; s.flags.add("HSM_BAR_smile_compromised");
    assert(!condition(triggers.HSM_BAR_sombra_cooperation, w));
});
test("trial-site isolation retains exact repair costs and branch consequences without meter losses", () => {
    for (const option of ["a", "b"]) {
        const a = world(), b = world(); choose("hsm_bar_core.11", "a", a); choose("hsm_bar_core.11", "b", b);
        a.BAR.pp = b.BAR.pp = 0;
        for (const w of [a, b]) { w.BAR.flags.add("HSM_BAR_suppression_live"); w.BAR.ideas.add("HSM_BAR_suppression_crisis"); }
        choose("hsm_bar_core.12", option, a); choose("hsm_bar_core.12", option, b);
        for (const w of [a, b]) {
            for (const name of ["cover_integrity", "capacity", "public_trust"]) assert(!Object.hasOwn(w.BAR.vars, "HSM_BAR_" + name));
            assert(w.BAR.flags.has("HSM_BAR_core_12_done"));
            assert.equal(w.BAR.flags.has("HSM_BAR_suppression_aborted"), option === "a");
            assert.equal(w.BAR.flags.has("HSM_BAR_suppression_escalated"), option === "b");
            assert.equal(w.BAR.flags.has("HSM_BAR_suppression_live"), option === "b");
            assert.equal(w.BAR.ideas.has("HSM_BAR_suppression_crisis"), option === "b");
            const after = structuredClone(w); choose("hsm_bar_core.12", option, w); assert.deepEqual(w, after);
        }
        if (option === "a") { assert.equal(a.BAR.pp, -40); assert.equal(b.BAR.pp, -75); }
        else { assert.equal(a.BAR.pp, 0); assert.equal(b.BAR.pp, 0); }
    }
});
test("ending either ends broad suppression or compromises operational liaison", () => {
    const a = world(), b = world();
    for (const w of [a,b]) { w.BAR.flags.add("HSM_BAR_normalization"); w.BAR.ideas.add("HSM_BAR_suppression_crisis"); }
    choose("hsm_bar_core.15", "a", a); choose("hsm_bar_core.15", "b", b);
    assert(a.BAR.flags.has("HSM_BAR_coexistence")); assert(!a.BAR.flags.has("HSM_BAR_normalization"));
    assert(!a.BAR.ideas.has("HSM_BAR_suppression_crisis"));
    assert(b.BAR.flags.has("HSM_BAR_smile_compromised")); assert(b.BAR.ideas.has("HSM_BAR_suppression_crisis"));
    assert(b.BAR.flags.has("HSM_BAR_global_authorized"));
    assert(!b.BAR.flags.has("HSM_BAR_service_settled"));
    assert(!a.BAR.flags.has("HSM_BAR_global_authorized"));
});
console.log("Secrecy regression: " + passed + " scenario groups passed; " + failed + " failed.");
if (failed) process.exitCode = 1;
