"use strict";

// node tools/Test-BarradServiceRewards.cjs [--game-root PATH]
// Execute actual scripts with the strict, cached-modifier case fixture. Not an HOI4 playtest.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const assert = require("node:assert/strict");
const F = require("./Test-BarradCases.cjs");
const { parse, read, prop, dictionary, run, test, effect, mod } = F;
const helper = "HSM_BAR_refresh_service_training", spirit = "HSM_BAR_service_capacity";
const prefix = "HSM_BAR_service_", focusPrefix = "HSM_BAR_dir_", flagPrefix = prefix + "training_";
const outcome = "HSM_BAR_anomalous_research";
const source = read("common/national_focus/HSM_BAR_directorate.txt");
const focuses = dictionary(source.filter(n => n.key === "shared_focus").map(n => ({ key: prop(n.value, "id"), value: n.value })));
const rewards = Object.fromEntries(Object.entries(focuses).map(([id, body]) => [id.slice(focusPrefix.length), prop(body, "completion_reward")]));
const helpers = dictionary(read("common/scripted_effects/HSM_BAR_service_rewards.txt"));
const core = dictionary(read("common/scripted_effects/HSM_BAR_core_effects.txt"));
const modifier = prop(read("common/dynamic_modifiers/HSM_BAR_core.txt"), spirit);
for (const id of ["HSM_BAR_adopt_coexistence", "HSM_BAR_adopt_normalization", "HSM_BAR_dissolve_institutions"]) F.effects[id] = core[id];
F.effects.HSM_BAR_collegium_remove_constitution = prop(read("common/scripted_effects/HSM_BAR_collegium_effects.txt"), "HSM_BAR_collegium_remove_constitution");
const walk = nodes => nodes.flatMap(n => [n, ...(Array.isArray(n.value) ? walk(n.value) : [])]);
const hash = data => crypto.createHash("sha256").update(JSON.stringify(data)).digest("hex");
const close = (a, b, label) => assert(Math.abs(a - b) < 1e-9, label + ": " + a + " != " + b);

// Independent reward contract. Never derive expected amounts from production script writes.
const upgrades = {
    charter: { lar: { upgrade: -0.1 } }, names: { lar: { own_detection: -0.05 } },
    watchmen: { lar: { network: 0.1 } }, evidence: { lar: { outcome: 0.05 } },
    training: { lar: { capture: -0.1 } }, register: { common: { research: 0.01 } },
    radio: { lar: { crypto: 1 }, legacy: { encryption: 1 } },
    agency: { lar: { slots: 1 }, legacy: { decryption: 1 } }, storage: { lar: { cost: -0.05 } },
    foreign_mandate: { lar: { slots: 1 } }, world: { lar: { upgrade: -0.1, network: 0.05 } },
    equus: { lar: { network: 0.05, own_detection: -0.05 } },
    griffonia: { lar: { network: 0.05, decrypt_power: 0.05 } },
    north: { lar: { network: 0.05, capture: -0.05 } },
    riverlands: { lar: { network: 0.05, upgrade: -0.05 } },
    zebrica: { lar: { network: 0.05, cost: -0.05 } }, liaison: { lar: { own_detection: -0.05 } },
    trafficking: { lar: { outcome: 0.05 } }, rulers: { lar: { decrypt_power: 0.1 }, legacy: { decryption: 1 } },
    countercult: { lar: { enemy_detection: 0.2, defense: 1 } }, foreign_protocol: { lar: { cost: -0.05 } },
    commission: { common: { research: 0.01 } }, coexistence: { lar: { enemy_detection: 0.1 } },
    normalization: { lar: { decrypt_power: 0.1 } }, quiet_watch: { lar: { own_detection: -0.1 } },
    sealed_orders: { lar: { crypto: 1 }, legacy: { encryption: 1 } }
};
const researchMilestones = { seal_labs: 0.01, archives: 0.02, storage: 0.01, suppression_lab: 0.01 };
const awardIds = [...new Set([...Object.keys(upgrades), ...Object.keys(researchMilestones)])];
const stats = {
    research: "research_speed_factor", network: "intel_network_gain_factor",
    own_detection: "own_operative_detection_chance_factor", capture: "own_operative_capture_chance_factor",
    enemy_detection: "enemy_operative_detection_chance_factor", defense: "intelligence_agency_defense",
    upgrade: "agency_upgrade_time", cost: "operation_cost", outcome: "operation_outcome",
    slots: "operative_slot", crypto: "crypto_strength", decrypt_power: "decryption_power_factor",
    encryption: "encryption", decryption: "decryption"
};
const technology = {
    charter: [["electronics", 0.5, 1]], seal_labs: [["industry", 0.5, 1]],
    evidence: [["electronics", 0.5, 1]], training: [["hospital_tech", 0.5, 1]],
    radio: [["electronics", 0.5, 1]], archives: [["electronics", 1, 1]], world: [["electronics", 0.5, 1]],
    remains: [["hospital_tech", 0.5, 1]], open_report: [["industry", 0.5, 2]], suppression_lab: [["electronics", 1, 1]]
};
const zero = () => Object.fromEntries(Object.keys(stats).map(k => [k, 0]));
function expected(ids, lar) {
    const result = zero();
    for (const id of new Set(ids)) {
        result.research += researchMilestones[id] || 0;
        const spec = upgrades[id] || {};
        for (const part of [spec.common, spec[lar ? "lar" : "legacy"]]) {
            for (const [key, value] of Object.entries(part || {})) result[key] += value;
        }
    }
    return result;
}
function world(lar = true) {
    const w = F.world(false), s = w.root;
    if (lar) w.dlc.add("La Resistance");
    for (const tag of ["EQS", "WIT", "ZES", "OLV"]) w.countries[tag] = { ...structuredClone(w.countries.AAA), id: tag };
    for (const c of Object.values(w.countries)) c.opinions = new Set();
    effect("HSM_BAR_core_refresh", w);
    return w;
}
function assertStats(w, wanted, cached = true) {
    for (const [field, key] of Object.entries(stats)) {
        assert(Object.hasOwn(w.root.vars, prefix + field), "Missing derived variable " + field);
        close(w.root.vars[prefix + field], wanted[field], "Variable " + field);
        if (cached) {
            assert(w.root.modifiers.has(spirit), "Service modifier not installed");
            assert(Object.hasOwn(w.root.modifierCache[spirit], key), "Missing cache stat " + key);
            close(w.root.modifierCache[spirit][key], wanted[field], "Cache " + key);
        }
    }
}
const ledger = w => structuredClone({
    flags: [...w.root.flags].filter(f => /^HSM_BAR_(study_|case_|project_)/.test(f)).sort(),
    vars: Object.fromEntries(Object.entries(w.root.vars).filter(([k]) => k.startsWith("HSM_BAR_outcome_"))),
    cache: w.root.modifierCache[outcome], globalFlags: w.flags, globalVars: w.vars, crowns: w.crowns,
    pp: w.root.pp, bonuses: w.root.bonuses
});
const progress = (w, id, mode) => {
    if (mode === "completed") w.root.focuses.add(focusPrefix + id);
    else w.root.flags.add(flagPrefix + id);
};
let passed = 0, failed = 0;
function scenario(name, fn) {
    try { fn(); passed++; console.log("PASS: " + name); }
    catch (error) { failed++; console.error("FAIL: " + name + "\n" + error.stack); }
}

scenario("all 34 focus layouts, identities, gates, prerequisites and tree selectors are preserved", () => {
    assert.equal(Object.keys(rewards).length, 34);
    const unchanged = source.map(n => n.key === "shared_focus" ? { ...n, value: n.value.filter(c => c.key !== "completion_reward") } : n);
    assert.equal(hash(unchanged), "526d5ce2a463781841be8a8b7500ed0c2c7c7ed637815b22c3971d60e0e353dd");
});
scenario("existing story effects, flags, radio research and agency creation remain intact without meters", () => {
    function original(nodes, id) {
        return nodes.flatMap(n => {
            if (n.key === "custom_effect_tooltip") return [];
            if (n.key === "set_country_flag" && typeof n.value === "string" && n.value.startsWith(flagPrefix)) return [];
            if (n.key === "add_tech_bonus" && id !== "radio") return [];
            if (Array.isArray(n.value)) {
                const value = original(n.value, id);
                if (["if", "else_if", "else", "hidden_effect"].includes(n.key) && !value.some(c => c.key !== "limit")) return [];
                return [{ ...n, value }];
            }
            return [n];
        });
    }
    const payload = Object.entries(rewards).map(([id, body]) => [focusPrefix + id, original(body, id)]);
    // The old snapshot reconstructs exactly by restoring only the four retired capacity writes.
    assert.equal(hash(payload), "be4c7dcef1d2ada3281905aba394575cce43d76d0e9a484a1ed53ad624aa5e01");
    assert(!walk(source).some(n => ["add_political_power", "add_stability"].includes(n.key)), "Flat focus filler was retained");
});
scenario("one hidden helper owns only service variables and installs or removes only the service modifier", () => {
    assert.deepEqual(Object.keys(helpers), [helper]);
    assert.equal(helpers[helper].length, 1);
    assert.equal(helpers[helper][0].key, "hidden_effect");
    const allowed = new Set(["hidden_effect", "if", "else_if", "else", "limit", "AND", "OR", "NOT", "tag", "has_country_flag", "has_completed_focus", "has_capitulated", "has_dlc", "has_dynamic_modifier", "modifier", "set_variable", "add_to_variable", "multiply_variable", "add_dynamic_modifier", "remove_dynamic_modifier", ...Object.keys(stats).map(k => prefix + k)]);
    for (const n of walk(helpers[helper])) assert(allowed.has(n.key), "Unexpected helper command/data " + n.key);
    for (const n of walk(helpers[helper]).filter(n => ["add_dynamic_modifier", "remove_dynamic_modifier"].includes(n.key))) assert.equal(prop(n.value, "modifier"), spirit);
    assert(!JSON.stringify(helpers).match(/HSM_BAR_(outcome|study|case|project|cover_integrity|service_coordination)/));
    const body = prop(core.HSM_BAR_core_refresh, "hidden_effect");
    const index = body.findIndex(n => n.key === helper), last = body.findIndex(n => n.key === "HSM_BAR_refresh_case_outcomes");
    for (const meter of ["HSM_BAR_capacity", "HSM_BAR_public_trust"]) {
        const cleanup = body.findIndex(n => n.key === "clear_variable" && n.value === meter);
        assert(cleanup >= 0 && index > cleanup && last > index, "Training must follow old-save cleanup and precede the case-ledger forced cache refresh");
    }
    assert.equal(body.filter(n => n.key === helper).length, 1);
    assert(!walk(helpers[helper]).some(n => n.key === "force_update_dynamic_modifier"));
});
scenario("only agreed training modifiers and the GUI factory reservation bind to exact variables", () => {
    const actual = modifier.filter(n => !["icon", "enable", "remove_trigger"].includes(n.key));
    assert.equal(actual.length, Object.keys(stats).length + 1);
    for (const [field, key] of Object.entries(stats)) assert.equal(prop(actual, key), prefix + field, key);
    assert.equal(prop(actual, "civilian_factory_use"), "HSM_BAR_service_gui_factories");
    const w = world(false);
    w.root.vars.HSM_BAR_service_gui_factories = 3;
    effect("HSM_BAR_core_refresh", w);
    assert.equal(w.root.vars.HSM_BAR_service_gui_factories, 3, "Training refresh must not erase active assignment reservations");
});

for (const lar of [false, true]) {
    for (const mode of ["flag", "completed"]) {
        for (const id of awardIds) scenario(`${lar ? "LaR" : "native"} ${mode}: ${id} gives its exact isolated award and refreshes the cache`, () => {
            const w = world(lar), before = ledger(w);
            progress(w, id, mode); effect("HSM_BAR_core_refresh", w);
            assertStats(w, expected([id], lar));
            assert.equal(w.root.modifierInstalls[spirit], 1);
            assert.deepEqual(ledger(w), before, "Training changed an anomaly, study, PP or research coupon");
            assert.equal(w.root.focuses.has(focusPrefix + id), mode === "completed");
        });
    }
    for (const id of Object.keys(rewards)) scenario(`${lar ? "LaR" : "native"} actual ${id} completion applies before the focus is marked completed`, () => {
        const w = world(lar), beforeLedger = ledger(w), previousBonuses = w.root.bonuses.length;
        run(rewards[id], w);
        assert(!w.root.focuses.has(focusPrefix + id));
        assert.equal(w.root.agency, id === "agency" && lar, "Unexpected agency creation");
        if (awardIds.includes(id)) assert(w.root.flags.has(flagPrefix + id), "Missing immediate award flag");
        assertStats(w, expected([id], lar));
        for (const meter of ["HSM_BAR_capacity", "HSM_BAR_public_trust"]) assert(!Object.hasOwn(w.root.vars, meter), "Focus recreated " + meter);
        const coupons = w.root.bonuses.slice(previousBonuses).map(b => {
            const nodes = JSON.parse(b);
            assert.deepEqual(nodes.map(n => n.key).sort(), ["bonus", "category", "name", "uses"]);
            assert.equal(typeof prop(nodes, "name"), "string");
            return [prop(nodes, "category"), Number(prop(nodes, "bonus")), Number(prop(nodes, "uses"))];
        });
        assert.deepEqual(coupons, technology[id] || [], "Wrong one-off research award");
        const afterLedger = ledger(w); afterLedger.bonuses = beforeLedger.bonuses;
        assert.deepEqual(afterLedger, beforeLedger, "Focus completed a study or granted anomaly bonuses");
        const cached = structuredClone(w.root.modifierCache[spirit]), bonuses = structuredClone(w.root.bonuses);
        w.root.focuses.add(focusPrefix + id);
        for (let i = 0; i < 5; i++) effect("HSM_BAR_core_refresh", w);
        assert.deepEqual(w.root.modifierCache[spirit], cached);
        assert.deepEqual(w.root.bonuses, bonuses, "Refresh replayed research coupons");
    });
    for (const branch of ["coexistence", "normalization"]) scenario(`${lar ? "LaR" : "native"} ${branch} maximum is bounded without completing exclusive branches together`, () => {
        const w = world(lar), excluded = branch === "coexistence" ? ["normalization", "sealed_orders"] : ["coexistence", "quiet_watch"];
        const active = awardIds.filter(id => !excluded.includes(id));
        for (const id of active) progress(w, id, "completed");
        effect("HSM_BAR_core_refresh", w);
        const wanted = zero();
        wanted.research = 0.07;
        if (lar) Object.assign(wanted, { network: 0.4, own_detection: branch === "coexistence" ? -0.25 : -0.15, capture: -0.15, enemy_detection: branch === "coexistence" ? 0.3 : 0.2, defense: 1, upgrade: -0.25, cost: -0.15, outcome: 0.1, slots: 2, crypto: branch === "coexistence" ? 1 : 2, decrypt_power: branch === "coexistence" ? 0.15 : 0.25 });
        else Object.assign(wanted, { encryption: branch === "coexistence" ? 1 : 2, decryption: 2 });
        assertStats(w, wanted);
        assert.equal(w.root.bonuses.length, 0, "Old completed focuses retroactively awarded research coupons");
        assert(!w.root.flags.has("HSM_BAR_project_suppression_done"));
        assert(!test(F.triggers.HSM_BAR_suppression_knowledge_ready, w));
        const before = ledger(w), cache = structuredClone(w.root.modifierCache);
        for (let i = 0; i < 100; i++) effect("HSM_BAR_core_refresh", w);
        assertStats(w, wanted); assert.deepEqual(ledger(w), before); assert.deepEqual(w.root.modifierCache, cache);
        assert.equal(w.root.modifierInstalls[spirit], 1);
    });
}

scenario("flag plus completed focus counts once; stale derived values never accumulate", () => {
    const w = world(true);
    const ids = ["register", "commission", "charter", "radio", ...Object.keys(researchMilestones)];
    for (const id of ids) { progress(w, id, "flag"); progress(w, id, "completed"); }
    for (const field of Object.keys(stats)) w.root.vars[prefix + field] = 999;
    effect("HSM_BAR_core_refresh", w);
    assertStats(w, expected(ids, true));
    const updates = w.root.modifierUpdates, cache = structuredClone(w.root.modifierCache);
    for (let i = 0; i < 5; i++) effect(helper, w);
    assertStats(w, expected(ids, true));
    assert.equal(w.root.modifierUpdates, updates, "Standalone helper forced redundant cache work");
    assert.deepEqual(w.root.modifierCache, cache);
});
scenario("obsolete save scores cannot grant research or change milestone awards", () => {
    for (const lar of [false, true]) for (const value of [-999, 0, 40, 100, 999]) {
        const w = world(lar);
        for (const ids of [[], Object.keys(researchMilestones)]) {
            for (const id of ids) progress(w, id, "flag");
            w.root.vars.HSM_BAR_capacity = value; w.root.vars.HSM_BAR_public_trust = value;
            effect("HSM_BAR_core_refresh", w);
            assertStats(w, expected(ids, lar));
            for (const meter of ["HSM_BAR_capacity", "HSM_BAR_public_trust"]) assert(!Object.hasOwn(w.root.vars, meter));
        }
    }
});
scenario("maintenance refresh is reached by the actual daily core pulse", () => {
    assert(core.HSM_BAR_core_pulse.some(n => n.key === "HSM_BAR_core_refresh" && n.value === "yes"));
});
for (const [name, mutate] of [
    ["inactive", w => w.root.flags.delete("HSM_BAR_active")],
    ["Collegium", w => { w.root.flags.delete("HSM_BAR_directorate"); F.flag(w, "collegium"); }],
    ["pre-Service", w => w.root.flags.delete("HSM_BAR_service_founded")],
    ["capitulated", w => { w.root.capitulated = true; }],
    ["foreign", w => { w.root = w.countries.YAL; w.root.flags = new Set(w.countries.BAR.flags); w.root.focuses = new Set(w.countries.BAR.focuses); w.root.vars = structuredClone(w.countries.BAR.vars); w.root.modifiers = new Set(w.countries.BAR.modifiers); w.root.modifierCache = structuredClone(w.countries.BAR.modifierCache); }]
]) scenario(`${name} has zero derived training, no service modifier and no stale cache`, () => {
    const w = world(true); progress(w, "register", "completed"); progress(w, "radio", "flag"); effect("HSM_BAR_core_refresh", w);
    mutate(w);
    assert(!test(prop(modifier, "enable"), w), "Modifier remains enabled");
    assert(test(prop(modifier, "remove_trigger"), w), "Invalid modifier removal gate rejected");
    effect("HSM_BAR_core_refresh", w);
    assertStats(w, zero(), false);
    assert(!w.root.modifiers.has(spirit)); assert.equal(w.root.modifierCache[spirit], undefined);
});
scenario("dissolution removes the service immediately and later refresh cannot restore it", () => {
    const w = world(true); progress(w, "register", "completed"); progress(w, "charter", "flag"); effect("HSM_BAR_core_refresh", w);
    effect("HSM_BAR_dissolve_institutions", w);
    assert(!w.root.modifiers.has(spirit)); assert.equal(w.root.modifierCache[spirit], undefined);
    assertStats(w, zero(), false);
    effect("HSM_BAR_core_refresh", w);
    assertStats(w, zero(), false); assert(!w.root.modifiers.has(spirit));
    assert(w.root.focuses.has(focusPrefix + "register")); assert(w.root.flags.has(flagPrefix + "charter"));
});
scenario("branch loss and restoration reconstruct permanent awards without retroactive coupons", () => {
    const w = world(true); progress(w, "register", "completed"); progress(w, "agency", "flag"); effect("HSM_BAR_core_refresh", w);
    w.root.flags.delete("HSM_BAR_directorate"); F.flag(w, "collegium"); effect("HSM_BAR_core_refresh", w);
    assertStats(w, zero(), false); assert(!w.root.modifiers.has(spirit));
    w.root.flags.delete("HSM_BAR_collegium"); F.flag(w, "directorate"); effect("HSM_BAR_core_refresh", w);
    assertStats(w, expected(["register", "agency"], true));
    assert.equal(w.root.modifierInstalls[spirit], 2); assert.equal(w.root.bonuses.length, 0);
});
scenario("DLC toggles clear obsolete spy or native stats instead of retaining both", () => {
    const w = world(true); for (const id of ["radio", "agency", "rulers", "sealed_orders", "register"]) progress(w, id, "completed");
    const ids = ["radio", "agency", "rulers", "sealed_orders", "register"];
    for (const lar of [true, false, true, false]) {
        w.dlc[lar ? "add" : "delete"]("La Resistance"); effect("HSM_BAR_core_refresh", w);
        assertStats(w, expected(ids, lar)); assert.equal(w.root.bonuses.length, 0);
    }
});
scenario("all seventeen case outcomes survive training and remain independently removable", () => {
    for (const id of F.ids) {
        const w = world(true); F.access(w, id); effect("HSM_BAR_cases_" + id + "_complete", w); effect("HSM_BAR_cases_" + id + "_apply", w);
        const before = ledger(w);
        progress(w, "register", "flag"); progress(w, "names", "completed"); effect("HSM_BAR_core_refresh", w);
        assert.deepEqual(ledger(w), before, id + " ledger changed");
        const training = structuredClone(w.root.modifierCache[spirit]);
        effect("HSM_BAR_refresh_case_outcomes", w);
        assert.deepEqual(w.root.modifierCache[spirit], training, id + " ledger overwrote service training");
    }
});
scenario("strict evaluator rejects unknown commands, malformed flags and stale caches; DLC checks use exact names", () => {
    assert.throws(() => run(parse("unknown_service_effect = yes"), world()), /Unsupported effect/);
    assert.throws(() => test(parse("unknown_service_trigger = yes"), world()), /Unsupported predicate/);
    assert.throws(() => run(parse("set_country_flag = { flags = invalid }"), world()), /Unsupported flag/);
    const w = world(true); assert(test(parse('has_dlc = "La Resistance"'), w));
    assert.throws(() => test(parse("has_dlc = { name = invalid }"), w), /Expected DLC name/);
    assert(!test(parse('has_dlc = "Gotterdammerung"'), w));
    assert(!test(parse("has_completed_focus = HSM_BAR_dir_names"), w));
    const original = F.effects.HSM_BAR_refresh_case_outcomes;
    const strip = nodes => nodes.filter(n => n.key !== "force_update_dynamic_modifier").map(n => ({ ...n, value: Array.isArray(n.value) ? strip(n.value) : n.value }));
    try {
        F.effects.HSM_BAR_refresh_case_outcomes = strip(original);
        progress(w, "names", "flag"); effect("HSM_BAR_core_refresh", w);
        assert.throws(() => assertStats(w, expected(["names"], true)), /Cache own_operative_detection/);
    } finally { F.effects.HSM_BAR_refresh_case_outcomes = original; }
    effect("HSM_BAR_core_refresh", w); assertStats(w, expected(["names"], true));
});

scenario("modifier names, native localization types and research categories exist in the installed engine", () => {
    const arg = process.argv.indexOf("--game-root");
    if (arg >= 0) assert(process.argv[arg + 1] && !process.argv[arg + 1].startsWith("--"), "Missing --game-root path");
    const game = arg >= 0 ? process.argv[arg + 1] : process.env.HOI4_GAME_ROOT || "C:/shit/Steam/steamapps/common/Hearts of Iron IV";
    const documentation = fs.readFileSync(path.join(game, "documentation/modifiers_documentation.md"), "utf8");
    const names = new Set([...documentation.matchAll(/^## (\w+)\r?$/gm)].map(m => m[1]));
    const loc = fs.readFileSync(path.join(game, "localisation/english/modifiers_l_english.yml"), "utf8");
    for (const key of Object.values(stats)) {
        assert(names.has(key), "Undocumented modifier " + key);
        assert(new RegExp("^\\s*(?:MODIFIER_" + key.toUpperCase() + "|" + key + "):.*", "m").test(loc), "Missing native label " + key);
    }
    for (const key of ["crypto_strength", "operative_slot"]) assert(documentation.includes("## " + key + "\n\n* Number with 0 decimal places"));
    assert.match(loc, /MODIFIER_CRYPTO_STRENGTH:.*Cryptology Level/);
    assert.match(loc, /MODIFIER_OWN_OPERATIVE_DETECTION_CHANCE_FACTOR:.*factor/);
    assert.match(loc, /enemy_operative_detection_chance_factor_tt:.*\$RIGHT\|\+=%\$/);
    const categories = parse(fs.readFileSync(path.join(game, "common/technology_tags/00_technology.txt"), "utf8"));
    const tagNames = new Set(walk(categories).map(n => n.key));
    for (const category of ["electronics", "industry", "hospital_tech"]) assert(tagNames.has(category), "Unknown research category " + category);
});

scenario("EN/RU Service tooltips name the correct spirit and show exact percentage versus level amounts", () => {
    const integerFields = new Set(["defense", "slots", "crypto", "encryption", "decryption"]);
    const expectedTips = new Map();
    for (const [id, spec] of Object.entries(upgrades)) {
        expectedTips.set("HSM_BAR_service_upgrade_" + id + "_tt", spec.common || spec.lar);
        if (spec.legacy) expectedTips.set("HSM_BAR_service_upgrade_" + id + "_legacy_tt", spec.legacy);
    }
    const expectedKeys = [...expectedTips.keys(), ...Object.keys(technology).filter(id => id !== "radio").map(id => "HSM_BAR_service_research_" + id)].sort();
    for (const language of ["english", "russian"]) {
        const bytes = fs.readFileSync(path.join(mod, "localisation", language, "HSM_BAR_service_rewards_l_" + language + ".yml"));
        assert.equal(bytes.subarray(0, 3).toString("hex"), "efbbbf");
        const lines = bytes.toString("utf8").replace(/^\uFEFF/, "").split(/\r?\n/), texts = new Map();
        assert.equal(lines[0], "l_" + language + ":");
        for (const line of lines.slice(1).filter(line => line.trim() && !/^\s*#/.test(line))) {
            const m = /^\s*([^\s:]+):\d*\s+"(.*)"\s*$/.exec(line);
            assert(m, "Malformed Service reward localization");
            assert(!texts.has(m[1]), "Duplicate Service reward key"); texts.set(m[1], m[2]);
        }
        assert.deepEqual([...texts.keys()].sort(), expectedKeys);
        for (const [key, values] of expectedTips) {
            const text = texts.get(key);
            assert.deepEqual([...text.matchAll(/\$([^$]+)\$/g)].map(m => m[1]), [spirit], "Wrong reward target");
            const actual = [...text.matchAll(/\u00a7G([+-]\d+(?:\.\d+)?%?)\u00a7!/g)].map(m => m[1]).sort();
            const wanted = Object.entries(values).map(([field, value]) => (value >= 0 ? "+" : "") + Number((value * (integerFields.has(field) ? 1 : 100)).toFixed(6)) + (integerFields.has(field) ? "" : "%")).sort();
            assert.deepEqual(actual, wanted, language + ": " + key);
            if (Object.hasOwn(values, "outcome")) {
                assert(language === "english" ? /bonus outcome chance/i.test(text) : /(?:\u0434\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044c\u043d|\u0431\u043e\u043d\u0443\u0441)/i.test(text), "Operation outcome mislabeled as ordinary success");
            }
        }
    }
});
scenario("focus tooltip branches display only the rewards actually available with the selected DLC", () => {
    function visible(nodes, w) {
        const out = []; let taken = false;
        for (const n of nodes) {
            if (n.key === "if" || n.key === "else_if") {
                if (n.key === "if") taken = false;
                if (!taken && test(prop(n.value, "limit"), w)) { taken = true; out.push(...visible(n.value.filter(c => c.key !== "limit"), w)); }
            } else if (n.key === "else") { if (!taken) out.push(...visible(n.value, w)); taken = true; }
            else if (n.key === "custom_effect_tooltip" && n.value.startsWith("HSM_BAR_service_upgrade_")) out.push(n.value);
        }
        return out;
    }
    for (const lar of [false, true]) for (const [id, body] of Object.entries(rewards)) {
        const spec = upgrades[id], wanted = [];
        if (spec?.common || (lar && spec?.lar)) wanted.push("HSM_BAR_service_upgrade_" + id + "_tt");
        else if (spec?.legacy) wanted.push("HSM_BAR_service_upgrade_" + id + "_legacy_tt");
        assert.deepEqual(visible(body, world(lar)), wanted, id + " tooltip contradicts DLC-specific reward");
    }
});

console.log(`Barrad Service rewards: ${passed} scenarios passed; ${failed} failed.`);
console.log("Boundary: deterministic script/cache fixtures and installed-source contracts; no native UI or game runtime verification.");
process.exitCode = failed ? 1 : 0;
