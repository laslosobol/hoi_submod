"use strict";

// Run: node tools/Test-BarradModifierTooltips.cjs
// Static tooltip reachability plus deterministic cached-value fixtures, not an HOI4 renderer.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const F = require("./Test-BarradCases.cjs");
const { read, parse, prop, dictionary, world, access, flag, effect, run, ids, mod } = F;
const maintenance = new Set(["HSM_BAR_core_refresh", "HSM_BAR_refresh_service_training", "HSM_BAR_refresh_case_outcomes", "HSM_BAR_collegium_refresh"]);
const outcome = "HSM_BAR_anomalous_research", service = "HSM_BAR_service_capacity", collegium = "HSM_BAR_collegium_services";
const scripts = {};
const files = dir => fs.readdirSync(path.join(mod, dir)).filter(name => /^HSM_BAR.*\.txt$/.test(name));
for (const file of files("common/scripted_effects")) {
    for (const [name, body] of Object.entries(dictionary(read("common/scripted_effects/" + file)))) {
        assert(!Object.hasOwn(scripts, name), "Duplicate scripted effect " + name);
        scripts[name] = body;
    }
}
const focuses = Object.fromEntries(files("common/national_focus").flatMap(file => read("common/national_focus/" + file))
    .filter(n => n.key === "shared_focus").map(n => [prop(n.value, "id"), prop(n.value, "completion_reward")]));
const finalDecisions = dictionary(read("common/decisions/HSM_BAR_anomalies.txt").flatMap(n => n.value));

// Visit both conditional branches: inactive branches may still appear in an engine preview.
// Keep every non-metadata node; unfamiliar commands cannot silently disappear from this trace.
function trace(nodes, definitions = scripts, calls = [], hidden = false, out = []) {
    assert(Array.isArray(nodes), "Expected effect block");
    for (const n of nodes) {
        if (["limit", "trigger", "ai_chance", "name"].includes(n.key)) continue;
        if (n.key === "hidden_effect") trace(n.value, definitions, calls, true, out);
        else if (Object.hasOwn(definitions, n.key)) {
            assert.equal(n.value, "yes", "Unexpected scripted-effect arguments: " + n.key);
            assert(!calls.includes(n.key), "Recursive scripted effect: " + [...calls, n.key].join(" -> "));
            trace(definitions[n.key], definitions, [...calls, n.key], hidden, out);
        } else {
            out.push({ key: n.key, value: n.value, calls, hidden });
            if (Array.isArray(n.value)) trace(n.value, definitions, calls, hidden, out);
        }
    }
    return out;
}
function assertSilent(nodes, definitions = scripts) {
    const rows = trace(nodes, definitions);
    const leaked = rows.filter(n => !n.hidden && n.calls.some(name => maintenance.has(name)));
    assert.deepEqual(leaked.map(n => n.calls.join(" -> ") + ": " + n.key), [], "Visible maintenance leaked into parent tooltip");
    return rows;
}
const call = name => parse(name + " = yes");
const visibleTooltips = nodes => assertSilent(nodes).filter(n => !n.hidden && n.key === "custom_effect_tooltip").map(n => n.value);
const close = (actual, expected, label) => assert(Math.abs(actual - expected) < 1e-9, label + ": " + actual + " != " + expected);
const install = (w, name) => run(parse("add_dynamic_modifier = { modifier = " + name + " }"), w);
const cached = (w, name, key) => {
    assert(w.root.modifiers.has(name), "Modifier absent: " + name);
    assert(Object.hasOwn(w.root.modifierCache[name], key), "Missing cached stat: " + key);
    return w.root.modifierCache[name][key];
};
function serviceWorld(lar = false) {
    const w = world(lar);
    effect("HSM_BAR_core_refresh", w);
    assert(w.root.modifiers.has(service), "Core refresh must install the founded Service");
    return w;
}
function studied(w, id) {
    access(w, id);
    effect("HSM_BAR_cases_" + id + "_complete", w);
    assert(w.root.flags.has("HSM_BAR_study_" + id + "_done"));
}
function withoutCommand(nodes, command) {
    return nodes.filter(n => n.key !== command).map(n => ({ ...n, value: Array.isArray(n.value) ? withoutCommand(n.value, command) : n.value }));
}
function withRuntimeEffect(name, replacement, fn) {
    const original = F.effects[name];
    F.effects[name] = replacement;
    try { fn(); } finally { F.effects[name] = original; }
}
function localization(language) {
    const dir = path.join(mod, "localisation", language), keys = new Map(), rewards = new Set();
    const rewardFile = "HSM_BAR_rewards_l_" + language + ".yml";
    assert(fs.existsSync(path.join(dir, rewardFile)), "Missing rewards localization: " + language);
    for (const file of fs.readdirSync(dir).filter(name => /^HSM_BAR.*\.yml$/.test(name))) {
        const bytes = fs.readFileSync(path.join(dir, file));
        if (file === rewardFile) assert.equal(bytes.subarray(0, 3).toString("hex"), "efbbbf", "Rewards localization needs UTF-8 BOM");
        const lines = bytes.toString("utf8").replace(/^\uFEFF/, "").split(/\r?\n/);
        assert.equal(lines[0], "l_" + language + ":", "Wrong locale header: " + file);
        for (const [index, line] of lines.entries()) {
            if (index === 0 || !line.trim() || /^\s*#/.test(line)) continue;
            const match = /^\s*([^ #:\s]+):\d*\s+"(.*)"\s*$/.exec(line);
            assert(match, "Malformed localization " + file + ":" + (index + 1));
            assert(!keys.has(match[1]), "Duplicate localization " + match[1]);
            keys.set(match[1], match[2]);
            if (file === rewardFile) rewards.add(match[1]);
        }
    }
    return { keys, rewards };
}
const references = text => [...text.matchAll(/\$([^$]+)\$/g)].map(m => m[1]);
function resolveLocalization(key, keys, chain = []) {
    assert(keys.has(key), "Missing localization " + [...chain, key].join(" -> "));
    assert(!chain.includes(key), "Recursive localization " + [...chain, key].join(" -> "));
    const rendered = keys.get(key).replace(/\$([^$]+)\$/g, (_, nested) => resolveLocalization(nested, keys, [...chain, key]));
    assert(!rendered.includes("$"), "Unresolved localization reference in " + key);
    return rendered;
}
let passed = 0, failed = 0, parentCount = 0;
function scenario(name, fn) {
    try { fn(); passed++; console.log("PASS: " + name); }
    catch (e) { failed++; console.error("FAIL: " + name + "\n" + e.stack); }
}

scenario("all four maintenance helpers hide their entire transitive effect preview", () => {
    for (const name of maintenance) {
        const rows = assertSilent(call(name));
        assert(rows.length > 0, "Empty maintenance body: " + name);
        assert(rows.every(n => n.hidden), name);
    }
});
scenario("focus and decision parents cannot expose nested maintenance", () => {
    const parents = Object.entries(focuses);
    for (const file of files("common/decisions")) {
        for (const category of read("common/decisions/" + file)) {
            for (const decision of category.value.filter(n => Array.isArray(n.value))) {
                for (const key of ["complete_effect", "remove_effect", "cancel_effect", "timeout_effect"]) {
                    const body = prop(decision.value, key);
                    if (body) parents.push([decision.key + "/" + key, body]);
                }
            }
        }
    }
    for (const [name, body] of parents) {
        assert(body, "Missing reward block: " + name);
        const rows = assertSilent(body);
        if (rows.some(n => n.calls.some(k => maintenance.has(k)))) parentCount++;
    }
    assert(parentCount > 50, "Parent coverage unexpectedly disappeared");
});
scenario("every study choice retains its specific visible reward tooltip", () => {
    assert.equal(ids.length, 17);
    for (const [index, id] of ids.entries()) {
        const options = F.events["hsm_bar_cases." + (index + 1)].filter(n => n.key === "option");
        for (const [suffix, mode] of [["a", "apply"], ["b", "reserve"]]) {
            const option = options.find(n => prop(n.value, "name") === "hsm_bar_cases." + (index + 1) + "." + suffix);
            assert(option, "Missing " + id + " choice " + mode);
            assert.deepEqual(visibleTooltips(option.value), ["HSM_BAR_outcome_" + id + "_" + mode + "_tt"]);
        }
    }
});
scenario("all seventeen final dispositions retain visible reward tooltips", () => {
    const expected = [];
    for (const id of ["rock", "titan", "entity", "amulet", "plants"]) {
        for (const mode of ["protect", "restrict"]) expected.push([id + "_" + mode, "HSM_BAR_case_" + id + "_" + mode + "_tt"]);
    }
    for (const id of ["chalice", "phylactery", "darkheart"]) expected.push([id + "_seal", "HSM_BAR_case_" + id + "_seal_tt"]);
    for (const id of ["grover", "rosa", "herald", "sombra"]) expected.push([id + "_review", "HSM_BAR_outcome_" + id + "_reviewed_tt"]);
    assert.equal(expected.length, 17);
    for (const [id, tooltip] of expected) {
        const visible = visibleTooltips(prop(finalDecisions["HSM_BAR_case_" + id], "complete_effect"));
        assert.equal(visible.filter(k => k === tooltip).length, 1, id + " lost or duplicated its reward tooltip");
    }
});
scenario("focus unlock and milestone research tooltips remain visible and resolve all EN/RU references", () => {
    const mappings = [
        ["HSM_BAR_transition_survey", "HSM_BAR_unlock_public_survey_tt", "HSM_BAR_public_survey"],
        ["HSM_BAR_transition_cabinet", "HSM_BAR_unlock_decode_records_tt", "HSM_BAR_decode_records"],
        ["HSM_BAR_transition_descent", "HSM_BAR_unlock_first_descent_tt", "HSM_BAR_first_descent"],
        ["HSM_BAR_dir_archives", "HSM_BAR_unlock_recover_science_tt", "HSM_BAR_recover_science"],
        ...["equus", "griffonia", "north", "riverlands", "zebrica"].map(id => ["HSM_BAR_dir_" + id, "HSM_BAR_unlock_" + id + "_tt", "HSM_BAR_cases_" + id]),
        ["HSM_BAR_dir_liaison", "HSM_BAR_unlock_smile_tt", "HSM_BAR_contact_smile"],
        ["HSM_BAR_dir_remains", "HSM_BAR_unlock_remains_tt", null],
        ...["seal_labs", "storage", "suppression_lab"].map(id => ["HSM_BAR_dir_" + id, "HSM_BAR_service_research_labs_tt", service]),
        ["HSM_BAR_dir_archives", "HSM_BAR_service_research_archives_tt", service]
    ];
    const english = localization("english"), russian = localization("russian");
    const expected = [...new Set(mappings.map(([, key]) => key))].sort();
    assert.equal(expected.length, 13);
    for (const { keys, rewards } of [english, russian]) {
        assert.deepEqual([...rewards].sort(), expected, "Unexpected or missing rewards localization keys");
        for (const [focus, tooltip, target] of mappings) {
            assert.equal(visibleTooltips(focuses[focus]).filter(key => key === tooltip).length, 1, focus + " missing its visible reward");
            const raw = keys.get(tooltip), rendered = resolveLocalization(tooltip, keys);
            assert(rendered.trim().length > 0, "Empty tooltip " + tooltip);
            assert(!/[\[\]]/.test(rendered), "Unresolved scripted localization in " + tooltip);
            assert.deepEqual(references(raw), target ? [target] : [], "Wrong referenced decision, category or spirit: " + tooltip);
            if (target) assert(rendered.includes(resolveLocalization(target, keys)), "Missing resolved target name");
        }
        for (const [milestone, percent] of [["labs", "1"], ["archives", "2"]]) {
            const raw = keys.get("HSM_BAR_service_research_" + milestone + "_tt");
            assert.deepEqual([...raw.matchAll(/\u00a7G([+-]\d+(?:\.\d+)?%?)\u00a7!/g)].map(m => m[1]), ["+" + percent + "%"], "Wrong milestone research amount");
            assert(!raw.includes(outcome), "Service research tooltip names the case-outcome spirit");
        }
    }
    for (const key of expected) assert.deepEqual(references(english.keys.get(key)), references(russian.keys.get(key)), "EN/RU reference mismatch: " + key);
});
scenario("localization resolver follows nested references and rejects missing or cyclic targets", () => {
    const keys = new Map([["tooltip", "Unlock $label$"], ["label", "$name$"], ["name", "Archive"]]);
    assert.equal(resolveLocalization("tooltip", keys), "Unlock Archive");
    keys.delete("name");
    assert.throws(() => resolveLocalization("tooltip", keys), /Missing localization tooltip -> label -> name/);
    keys.set("name", "$tooltip$");
    assert.throws(() => resolveLocalization("tooltip", keys), /Recursive localization/);
    keys.set("name", "$unterminated");
    assert.throws(() => resolveLocalization("tooltip", keys), /Unresolved localization/);
});
scenario("sealed labs immediately raise cached research by 0.01 without creating outcomes", () => {
    const w = serviceWorld(), before = cached(w, service, "research_speed_factor");
    const ledger = structuredClone(w.root.modifierCache[outcome]);
    run(focuses.HSM_BAR_dir_seal_labs, w);
    assert(!Object.hasOwn(w.root.vars, "HSM_BAR_capacity"));
    close(w.root.vars.HSM_BAR_service_research, 0.01, "Derived research");
    close(cached(w, service, "research_speed_factor") - before, 0.01, "Immediate focus reward");
    assert.deepEqual(w.root.modifierCache[outcome], ledger);
    assert.equal(w.root.modifierInstalls[outcome], 1);
    assert.equal(w.root.modifierInstalls[service], 1);
    assert(![...w.root.flags].some(f => /^HSM_BAR_study_/.test(f)));
});
scenario("all four research milestones ignore obsolete scores and immediately cache their fixed award once", () => {
    for (const [id, amount] of [["seal_labs", 0.01], ["storage", 0.01], ["suppression_lab", 0.01], ["archives", 0.02]]) {
        const focus = "HSM_BAR_dir_" + id;
        for (const value of [-999, 0, 20, 95, 98, 100, 999]) {
            const w = serviceWorld();
            w.root.vars.HSM_BAR_capacity = value; w.root.vars.HSM_BAR_public_trust = value;
            const before = cached(w, service, "research_speed_factor"), ledger = structuredClone(w.root.modifierCache[outcome]);
            run(focuses[focus], w);
            for (const meter of ["HSM_BAR_capacity", "HSM_BAR_public_trust"]) assert(!Object.hasOwn(w.root.vars, meter), focus);
            close(cached(w, service, "research_speed_factor") - before, amount, "Milestone research gain");
            assert(!w.root.focuses.has(focus), "Immediate reward needed completed-focus status");
            assert(w.root.flags.has("HSM_BAR_service_training_" + id));
            w.root.focuses.add(focus);
            const bonuses = structuredClone(w.root.bonuses);
            for (let i = 0; i < 5; i++) effect("HSM_BAR_core_refresh", w);
            close(cached(w, service, "research_speed_factor"), amount, "Flag plus focus counted twice");
            assert.deepEqual(w.root.bonuses, bonuses, "Refresh repeated coupons");
            assert.deepEqual(w.root.modifierCache[outcome], ledger, "Milestone fabricated case rewards");
            assert.equal(w.root.modifierInstalls[outcome], 1);
        }
    }
});
scenario("the names focus applies only its detection training while preserving the event and anomaly ledger", () => {
    const w = serviceWorld(true); studied(w, "rock"); effect("HSM_BAR_cases_rock_apply", w);
    const before = structuredClone({ cache: w.root.modifierCache, installs: w.root.modifierInstalls, vars: w.root.vars, flags: w.root.flags, pp: w.root.pp });
    before.cache[service].own_operative_detection_chance_factor = -0.05;
    before.vars.HSM_BAR_service_own_detection = -0.05;
    before.flags.add("HSM_BAR_service_training_names");
    run(focuses.HSM_BAR_dir_names, w);
    assert.deepEqual({ cache: w.root.modifierCache, installs: w.root.modifierInstalls, vars: w.root.vars, flags: w.root.flags, pp: w.root.pp }, before);
    assert.equal(w.root.events.at(-1), "hsm_bar_core.2");
});
scenario("outcomes install once, update an existing cache, suspend, restore and remove immediately", () => {
    const w = serviceWorld(); studied(w, "rock");
    close(cached(w, outcome, "production_speed_infrastructure_factor"), 0, "Initial ledger");
    effect("HSM_BAR_cases_rock_apply", w);
    close(cached(w, outcome, "production_speed_infrastructure_factor"), 0.04, "Applied rock");
    close(cached(w, outcome, "supply_consumption_factor"), 0.01, "Applied rock supply");
    for (let i = 0; i < 5; i++) effect("HSM_BAR_refresh_case_outcomes", w);
    assert.equal(w.root.modifierInstalls[outcome], 1);
    w.states[624].controller = "YAL";
    effect("HSM_BAR_refresh_case_outcomes", w);
    assert(Object.values(w.root.modifierCache[outcome]).every(v => v === 0), "Lost access left cached effects");
    w.states[624].controller = "BAR";
    effect("HSM_BAR_refresh_case_outcomes", w);
    close(cached(w, outcome, "production_speed_infrastructure_factor"), 0.04, "Recovered rock");
    flag(w, "region_local_open", "coexistence", "project_wards_done");
    run(prop(finalDecisions.HSM_BAR_case_rock_protect, "complete_effect"), w);
    close(cached(w, outcome, "production_speed_infrastructure_factor"), 0.02, "Final disposition");
    close(cached(w, outcome, "supply_consumption_factor"), 0, "Replaced preliminary reward");
    assert.equal(w.root.modifierInstalls[outcome], 1);
    w.root.flags.delete("HSM_BAR_active");
    const updates = w.root.modifierUpdates;
    effect("HSM_BAR_refresh_case_outcomes", w);
    assert(!w.root.modifiers.has(outcome));
    assert.equal(w.root.modifierCache[outcome], undefined);
    assert(w.root.modifierUpdates > updates, "Removal skipped the forced update");
    assert(w.root.flags.has("HSM_BAR_study_rock_applied"), "History was erased");
    flag(w, "active"); effect("HSM_BAR_refresh_case_outcomes", w);
    assert.equal(w.root.modifierInstalls[outcome], 2, "Reactivation must install the absent modifier");
    close(cached(w, outcome, "production_speed_infrastructure_factor"), 0.02, "Reactivated final reward");
});
scenario("old saves clear all four obsolete variables and stale service PP while preserving milestone research and outcomes", () => {
    for (const cover of [-987.5, -1, 0, 39, 70, 100, 456.25]) {
        for (const coordination of [-12.75, 0, 8.125]) {
            for (const route of ["directorate", "collegium"]) {
                const w = serviceWorld(); studied(w, "entity"); effect("HSM_BAR_cases_entity_apply", w);
                flag(w, "service_training_seal_labs");
                if (route === "collegium") {
                    w.root.flags.delete("HSM_BAR_directorate"); flag(w, "collegium", "collegium_initialized", "collegium_school_open");
                    effect("HSM_BAR_collegium_refresh", w); install(w, collegium);
                }
                effect("HSM_BAR_core_refresh", w);
                const expected = structuredClone({ cache: w.root.modifierCache, vars: w.root.vars, flags: w.root.flags, pp: w.root.pp, installs: w.root.modifierInstalls });
                w.root.vars.HSM_BAR_cover_integrity = cover;
                w.root.vars.HSM_BAR_service_coordination = coordination;
                w.root.vars.HSM_BAR_capacity = cover;
                w.root.vars.HSM_BAR_public_trust = coordination;
                // A loaded legacy save may still contain an ineligible Service spirit.
                w.root.modifiers.add(service);
                w.root.modifierCache[service] = { ...w.root.modifierCache[service], political_power_gain: coordination };
                const updates = w.root.modifierUpdates;
                effect("HSM_BAR_core_refresh", w);
                assert(!Object.hasOwn(w.root.vars, "HSM_BAR_cover_integrity"));
                assert(!Object.hasOwn(w.root.vars, "HSM_BAR_service_coordination"));
                assert(!Object.hasOwn(w.root.vars, "HSM_BAR_capacity"));
                assert(!Object.hasOwn(w.root.vars, "HSM_BAR_public_trust"));
                assert(!Object.hasOwn(w.root.modifierCache[service] || {}, "political_power_gain"), "Stale service PP survived cleanup");
                assert.equal(w.root.modifierCache[service]?.political_power_gain ?? 0, 0);
                assert(w.root.modifierUpdates > updates, "Save migration skipped forced cache refresh");
                assert.deepEqual({ cache: w.root.modifierCache, vars: w.root.vars, flags: w.root.flags, pp: w.root.pp, installs: w.root.modifierInstalls }, expected);
                if (route === "directorate") {
                    close(cached(w, service, "research_speed_factor"), 0.01, "Milestone research preserved");
                    close(cached(w, outcome, "research_speed_factor"), 0.01, "Entity case research preserved");
                } else {
                    assert(!w.root.modifiers.has(service));
                    assert.equal(w.root.vars.HSM_BAR_service_research, 0);
                    close(cached(w, collegium, "research_speed_factor"), 0.03, "Collegium research preserved");
                }
                effect("HSM_BAR_core_refresh", w);
                assert.deepEqual(w.root.modifierCache, expected.cache, "Repeated migration changed rewards");
            }
        }
    }
});
scenario("all seventeen reserves refresh outcomes without cover, service PP or extra one-off rewards", () => {
    for (const id of ids) {
        for (const cover of [undefined, -215.5, 70, 999]) {
            const w = serviceWorld(); studied(w, id);
            if (cover !== undefined) {
                w.root.vars.HSM_BAR_cover_integrity = cover;
                w.root.vars.HSM_BAR_service_coordination = (cover - 50) * 0.002;
                w.root.modifierCache[service].political_power_gain = 6.5;
            }
            const before = { pp: w.root.pp, bonuses: structuredClone(w.root.bonuses) };
            const updates = w.root.modifierUpdates;
            effect("HSM_BAR_cases_" + id + "_reserve", w);
            assert(!Object.hasOwn(w.root.vars, "HSM_BAR_cover_integrity"), id);
            assert(!Object.hasOwn(w.root.vars, "HSM_BAR_service_coordination"), id);
            assert(!Object.hasOwn(w.root.modifierCache[service], "political_power_gain"), id + " obsolete service PP");
            close(cached(w, service, "research_speed_factor"), 0, id + " invented milestone research");
            for (const meter of ["HSM_BAR_capacity", "HSM_BAR_public_trust"]) assert(!Object.hasOwn(w.root.vars, meter));
            assert.deepEqual({ pp: w.root.pp, bonuses: w.root.bonuses }, before, id + " invented reward");
            assert(w.root.modifierUpdates > updates, id + " skipped forced refresh");
            assert(Object.values(w.root.modifierCache[outcome]).some(v => v !== 0), id + " reserve ledger missing");
            assert.equal(w.root.modifierInstalls[outcome], 1);
            const after = structuredClone(w.root);
            effect("HSM_BAR_cases_" + id + "_reserve", w);
            assert.deepEqual(w.root, after, id + " replay changed state");
        }
    }
});
scenario("Collegium direct and core refreshes update cached civilian and wartime values", () => {
    const w = world(); w.root.flags.delete("HSM_BAR_directorate"); flag(w, "collegium", "collegium_initialized");
    effect("HSM_BAR_collegium_refresh", w); install(w, collegium);
    assert(Object.values(w.root.modifierCache[collegium]).every(v => v === 0), "Unearned institutional services");
    flag(w, "collegium_school_open", "collegium_independent_archive", "collegium_clinic_access", "grid_program");
    effect("HSM_BAR_collegium_refresh", w);
    close(cached(w, collegium, "research_speed_factor"), 0.03, "School research");
    close(cached(w, collegium, "stability_factor"), 0.07, "Archive and clinic stability");
    close(cached(w, collegium, "production_speed_industrial_complex_factor"), 0.05, "Civilian construction");
    flag(w, "collegium_cohort_trained", "collegium_research_board", "collegium_workshops_equipped");
    effect("HSM_BAR_core_refresh", w);
    close(cached(w, collegium, "research_speed_factor"), 0.08, "Research milestones");
    close(cached(w, collegium, "production_speed_industrial_complex_factor"), 0.1, "Equipped workshops");
    flag(w, "collegium_wartime", "collegium_defence_protocol"); w.root.war = true;
    effect("HSM_BAR_core_refresh", w);
    close(cached(w, collegium, "production_speed_industrial_complex_factor"), 0, "Wartime clears construction");
    close(cached(w, collegium, "supply_consumption_factor"), -0.08, "Wartime supply");
    close(cached(w, collegium, "army_org_regain"), 0.08, "Wartime recovery");
    close(cached(w, collegium, "stability_factor"), 0.05, "Emergency mandate tradeoff");
    flag(w, "collegium_reserve_equipped", "collegium_clinic_rounds_done", "collegium_emergency_mandate");
    effect("HSM_BAR_core_refresh", w);
    close(cached(w, collegium, "supply_consumption_factor"), -0.13, "Equipped reserve supply");
    close(cached(w, collegium, "army_org_regain"), 0.13, "Clinic rounds recovery");
    close(cached(w, collegium, "stability_factor"), 0.07, "Mandated emergency stability");
    w.root.war = false; effect("HSM_BAR_core_refresh", w);
    close(cached(w, collegium, "supply_consumption_factor"), 0, "Peace clears supply");
    close(cached(w, collegium, "army_org_regain"), 0, "Peace clears recovery");
    close(cached(w, collegium, "production_speed_industrial_complex_factor"), 0.1, "Peace restores construction even with a stale wartime flag");
    w.root.flags.delete("HSM_BAR_collegium_wartime"); effect("HSM_BAR_core_refresh", w);
    close(cached(w, collegium, "production_speed_industrial_complex_factor"), 0.1, "Civilian allocation remains stable");
    assert.equal(w.root.modifierInstalls[collegium], 1);
});
scenario("negative controls reject exposed helpers, unknown hidden commands and stale caches", () => {
    for (const name of maintenance) {
        const wrapper = scripts[name];
        assert.equal(wrapper.length, 1, "Maintenance body must be entirely hidden");
        assert.equal(wrapper[0].key, "hidden_effect");
        const broken = { ...scripts, [name]: wrapper[0].value };
        assert.throws(() => assertSilent(call(name), broken), /Visible maintenance leaked/);
    }
    assert.throws(() => run(parse("hidden_effect = { unsupported_barrad_command = yes }"), world()), /Unsupported effect/);
    assert.throws(() => run(parse("clear_variable = { var = HSM_BAR_cover_integrity }"), world()), /Expected scalar variable name/);
    assert.throws(() => F.test(parse("unsupported_barrad_predicate = yes"), world()), /Unsupported predicate/);
    assert.throws(() => run(parse("force_update_dynamic_modifier = no"), world()), /Expected values/);
    const w = serviceWorld();
    assert(F.test(parse("has_dynamic_modifier = " + outcome), w));
    assert(F.test(parse("has_dynamic_modifier = { modifier = " + outcome + " }"), w));
    assert(!F.test(parse("has_dynamic_modifier = " + collegium), w));
    const broken = withoutCommand(F.effects.HSM_BAR_refresh_case_outcomes, "force_update_dynamic_modifier");
    withRuntimeEffect("HSM_BAR_refresh_case_outcomes", broken, () => {
        run(focuses.HSM_BAR_dir_seal_labs, w);
        close(w.root.vars.HSM_BAR_service_research, 0.01, "Variables still execute");
        assert.throws(() => close(cached(w, service, "research_speed_factor"), 0.01, "Stale cache"), /Stale cache/);
        studied(w, "rock"); effect("HSM_BAR_cases_rock_apply", w);
        close(w.root.vars.HSM_BAR_outcome_infra, 0.04, "Ledger still executes");
        assert.throws(() => close(cached(w, outcome, "production_speed_infrastructure_factor"), 0.04, "Stale outcome"), /Stale outcome/);
    });
    effect("HSM_BAR_core_refresh", w);
    close(cached(w, service, "research_speed_factor"), 0.01, "Forced refresh restored");
    close(cached(w, outcome, "production_speed_infrastructure_factor"), 0.04, "Ledger cache restored");
});

console.log(`Barrad modifier tooltips: ${passed} scenarios passed; ${failed} failed; ${parentCount} maintenance-bearing focus/decision parents checked.`);
console.log("Boundary: script visibility and explicit cache invalidation are modelled; native tooltip rendering still requires a playtest.");
process.exitCode = failed ? 1 : 0;
