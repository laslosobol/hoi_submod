"use strict";
// Run: node tools/Test-BarradArchive.cjs
// Static and fixture checks, not a rendering or HOI4 engine acceptance test.
// Optional: HOI4_PATH / EAW_PATH override the installed dependency locations.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const {parse, field, loadArchiveAssets, resolveAsset, spriteDimensions, fontDefinition} = require("./Test-BarradArchiveSkin.cjs");
const repo = path.resolve(__dirname, "..");
const mod = path.join(repo, "mod/HoISubmod");
const eaw = process.env.EAW_PATH || "C:/shit/Steam/steamapps/workshop/content/394360/1826643372";
const cases = "rock titan entity amulet reactor crown chalice phylactery darkheart grover rosa herald sombra echo marsh compass plants".split(" ");
const photoCases = "rock titan entity amulet reactor crown chalice darkheart echo marsh compass plants".split(" ");
const specimenPhotos = new Set(["crown", "chalice", "darkheart"]);
const copyCases = new Set(["rock", "entity", "reactor", "crown", "echo", "marsh"]);
const read = p => fs.readFileSync(path.join(mod, p), "utf8");
const prop = (b, k) => b.find(n => n.key === k)?.value;
const defs = b => Object.fromEntries(b.map(n => [n.key, n.value]));
const gui = prop(parse(read("interface/HSM_BAR_archive.gui")), "guiTypes");
const scripts = defs(prop(parse(read("common/scripted_guis/HSM_BAR_archive.txt")), "scripted_gui"));
const window = scripts.HSM_BAR_archive_window;
const launcher = scripts.HSM_BAR_archive_launcher;
const triggers = defs(prop(window, "triggers"));
const effects = defs(prop(window, "effects"));
const refresh = prop(parse(read("common/scripted_effects/HSM_BAR_archive.txt")), "HSM_BAR_archive_refresh");
const texts = Object.fromEntries(parse(read("common/scripted_localisation/HSM_BAR_archive.txt")).map(n => [prop(n.value, "name"), n.value.filter(x => x.key === "text").map(x => x.value)]));
const helpers = defs(["copies", "regions"].flatMap(name => parse(read("common/scripted_triggers/HSM_BAR_archive_" + name + ".txt"))));
for (const name of ["HSM_BAR_service_gui_actor", "HSM_BAR_service_gui_available"]) {
    helpers[name] = prop(parse(read("common/scripted_triggers/HSM_BAR_service_gui.txt")), name);
    assert(Array.isArray(helpers[name]), "Missing operations-window actor contract");
}
const archiveVariables = new Set(["open", "region", "page", "case", "document", "copy"].map(key => "HSM_BAR_archive_" + key));
const handoffVariables = new Set(["HSM_BAR_service_gui_open", "HSM_BAR_service_gui_region"]);
const regions = ["local", "equus", "griffonia", "north", "riverlands", "zebrica"];
const regionalCases = [["rock", "titan", "entity", "amulet", "reactor", "echo", "compass", "plants"],
    ["sombra", "darkheart", "crown"], ["grover", "herald", "crown"], ["rosa", "chalice", "phylactery"], ["marsh"], ["zebrica", "crown"]];
const caseRows = {rock: 0, titan: 1, entity: 2, amulet: 3, reactor: 0, echo: 1, compass: 2, plants: 3,
    sombra: 0, darkheart: 1, crown: 2, grover: 0, herald: 1, rosa: 0, chalice: 1, phylactery: 2, marsh: 0, zebrica: 0};
function locate(s, c, region = regionalCases.findIndex(group => group.includes(c)) + 1) {
    assert(regionalCases[region - 1]?.includes(c), "Invalid fixture region/case");
    s.vars.HSM_BAR_archive_region = region;
    s.vars.HSM_BAR_archive_page = region === 1 ? Math.floor(regionalCases[0].indexOf(c) / 4) + 1 : 1;
    // Generic Crown evidence is not regional provenance; fixture opens its branch.
    if (c === "crown") s.flags.add("HSM_BAR_region_" + regions[region - 1] + "_open");
}
let assetCache;
const archiveAssets = () => assetCache ||= loadArchiveAssets();
function localisation(lang) {
    const rows = new Map();
    const files = fs.readdirSync(path.join(mod, "localisation", lang)).filter(file => new RegExp(`^HSM_BAR_archive(?:_\\w+)?_l_${lang}\\.yml$`).test(file)).sort();
    assert(files.includes(`HSM_BAR_archive_l_${lang}.yml`), "Missing base archive localisation");
    for (const file of files) {
        const source = read(`localisation/${lang}/${file}`);
        assert.equal(source.charCodeAt(0), 0xFEFF, "Missing localisation UTF-8 BOM: " + file);
        assert(source.startsWith(`\uFEFFl_${lang}:`));
        for (const line of source.split(/\r?\n/).slice(1)) {
            if (!line.trim() || line.trimStart().startsWith("#")) continue;
            const m = line.match(/^ (HSM_BAR_archive_\w+):0 "([^"\r\n]*)"$/);
            assert(m, "Malformed localisation: " + line);
            assert(!rows.has(m[1]), "Duplicate localisation: " + m[1]);
            rows.set(m[1], m[2]);
        }
    }
    return rows;
}
const locales = [localisation("english"), localisation("russian")];
// Validate the separate outcome contract without copying mechanical prose into documents.
const outcomeTexts = Object.fromEntries(parse(read("common/scripted_localisation/HSM_BAR_case_outcomes.txt")).map(n => [prop(n.value, "name"), n.value.filter(x => x.key === "text").map(x => x.value)]));
const outcomeLocales = ["english", "russian"].map(lang => new Map([...read(`localisation/${lang}/HSM_BAR_case_outcomes_l_${lang}.yml`).matchAll(/^ (\w+):0 "(.*)"\r?$/gm)].map(m => [m[1], m[2]])));
function expanded(text, lang, stack = []) {
    assert.equal(typeof text, "string");
    return text.replace(/\[ROOT\.(GetHSMBAROutcome\w+)\]/g, (_, getter) => {
        assert(!stack.includes(getter), "Recursive outcome getter: " + getter);
        assert(outcomeTexts[getter], "Missing outcome getter: " + getter);
        // The pane scrolls: check every possible leaf for font/word bounds, without
        // inventing a fixture implementation of another component's game logic.
        return outcomeTexts[getter].map(b => {
            const key = prop(b, "localization_key");
            assert(outcomeLocales[lang].has(key), "Missing outcome localization: " + key);
            return expanded(outcomeLocales[lang].get(key), lang, [...stack, getter]);
        }).join("\\n");
    }).replace(/\$(\w+)\$/g, (_, key) => {
        assert(!stack.includes(key), "Recursive localization: " + key);
        const value = locales[lang].get(key) ?? outcomeLocales[lang].get(key);
        assert.notEqual(value, undefined, "Missing localization: " + key);
        return expanded(value, lang, [...stack, key]);
    });
}
function fresh() {
    return {tag: "BAR", ai: false, capitulated: false, subject: false, controlsCapital: true, flags: new Set(["HSM_BAR_active", "HSM_BAR_directorate", "HSM_BAR_service_founded", "HSM_BAR_region_local_open"]), vars: {}, access: new Set()};
}
function validateCondition(nodes, stack = []) {
    assert(Array.isArray(nodes), "Missing trigger block");
    for (const {key: k, value: v, op} of nodes) {
        assert.equal(op, "=", "Unexpected trigger operator: " + k);
        if (["AND", "OR", "NOT"].includes(k)) {
            if (k === "NOT") assert.equal(v.length, 1);
            validateCondition(v, stack);
        } else if (Object.hasOwn(helpers, k)) {
            assert(["yes", "no"].includes(v));
            assert(!stack.includes(k), "Recursive scripted trigger: " + k);
            validateCondition(helpers[k], [...stack, k]);
        } else if (k === "check_variable") {
            assert.equal(v.length, 1);
            assert(archiveVariables.has(v[0].key), "Unexpected trigger variable: " + v[0].key);
            assert(["=", ">", "<"].includes(v[0].op), "Unsupported variable comparison");
            assert(Number.isFinite(Number(v[0].value)));
        } else if (k === "has_variable") assert(archiveVariables.has(v));
        else if (["is_ai", "is_subject", "has_capitulated"].includes(k) || /^HSM_BAR_cases_\w+_access$/.test(k)) assert(["yes", "no"].includes(v));
        else if (k === "controls_state") assert.equal(v, "624", "Fixture only models Barrad capital control");
        else assert(["tag", "has_country_flag"].includes(k) && typeof v === "string", "Unknown trigger: " + k);
    }
}
function condition(nodes, s) {
    validateCondition(nodes);
    return evaluate(nodes);
    function evaluate(nodes) { return nodes.every(({key: k, value: v}) => {
        if (k === "AND") return evaluate(v);
        if (k === "OR") return v.some(n => evaluate([n]));
        if (k === "NOT") return !evaluate(v);
        if (Object.hasOwn(helpers, k)) return evaluate(helpers[k]) === (v === "yes");
        if (k === "tag") return s.tag === v;
        if (k === "is_ai") return s.ai === (v === "yes");
        if (k === "is_subject") return s.subject === (v === "yes");
        if (k === "has_capitulated") return s.capitulated === (v === "yes");
        if (k === "controls_state") return s.controlsCapital;
        if (k === "has_country_flag") return s.flags.has(v);
        if (k === "has_variable") return Object.hasOwn(s.vars, v);
        if (k === "check_variable") {
            assert.equal(v.length, 1);
            const a = s.vars[v[0].key] || 0, b = Number(v[0].value);
            if (v[0].op === "=") return a === b;
            if (v[0].op === ">") return a > b;
            if (v[0].op === "<") return a < b;
        }
        if (/^HSM_BAR_cases_\w+_access$/.test(k)) return s.access.has(k) === (v === "yes");
        throw Error("Unknown trigger: " + k);
    }); }
}
function run(nodes, s) {
    for (const {key: k, value: v} of nodes) {
        if (k === "HSM_BAR_archive_refresh") {
            assert.equal(v, "yes"); run(refresh, s); continue;
        }
        if (k === "if") {
            if (condition(prop(v, "limit"), s)) run(v.filter(n => n.key !== "limit"), s);
            continue;
        }
        if (k === "clear_variable") {
            assert(archiveVariables.has(v) || handoffVariables.has(v) || ["HSM_BAR_fielddesk_open", "HSM_BAR_investigation_open"].includes(v)); delete s.vars[v]; continue;
        }
        if (k === "HSM_BAR_service_gui_refresh") {
            assert.equal(v, "yes");
            // Parent-owned console reconstruction is verified by its own suite.
            s.operationsRefreshRequests = (s.operationsRefreshRequests || 0) + 1;
            continue;
        }
        assert(["set_variable", "add_to_variable", "subtract_from_variable"].includes(k), "Non-presentation effect: " + k);
        assert.equal(v.length, 1);
        const name = v[0].key, rhs = v[0].value;
        const value = name === "HSM_BAR_service_gui_region" && rhs === "HSM_BAR_archive_region" ? s.vars[rhs] || 0 : Number(rhs);
        assert(archiveVariables.has(name) || handoffVariables.has(name)); assert(Number.isFinite(value));
        if (k === "set_variable") s.vars[name] = value;
        if (k === "add_to_variable") s.vars[name] = (s.vars[name] || 0) + value;
        if (k === "subtract_from_variable") s.vars[name] = (s.vars[name] || 0) - value;
    }
}
function textKey(name, s) {
    const options = texts[name]; assert(options, "Missing scripted text: " + name);
    const entry = options.find(b => !prop(b, "trigger") || condition(prop(b, "trigger"), s));
    assert(entry, "No default text: " + name); return prop(entry, "localization_key");
}
function widgetVisible(name, s) {
    const trigger = triggers[name + "_visible"];
    return !trigger || condition(trigger, s);
}
function visiblePhotos(s) {
    const widgets = gui.find(n => prop(n.value, "name") === "HSM_BAR_archive_window").value;
    return widgets.filter(n => n.key === "iconType" && widgetVisible(prop(n.value, "name"), s))
        .map(n => prop(n.value, "name").replace("HSM_BAR_archive_photo_", ""));
}
function open(s) { run(prop(launcher, "effects")[0].value, s); }
function walk(nodes, visit) {
    for (const n of nodes) { visit(n); if (Array.isArray(n.value)) walk(n.value, visit); }
}
let passed = 0, failed = 0;
function test(name, body) {
    if (require.main !== module) return;
    try { body(); passed++; console.log("PASS " + name); }
    catch (e) { failed++; console.error("FAIL " + name + "\n" + e.stack); }
}
test("player-only Service scope, independent political-panel launcher, no stale dirty cache", () => {
    assert.equal(prop(launcher, "parent_window_token"), "politics_tab");
    for (const b of [launcher, window]) {
        assert.equal(prop(b, "context_type"), "player_context");
        assert.equal(prop(b, "dirty"), undefined);
        assert.equal(prop(b, "parent_window_name"), undefined);
        const good = fresh(); open(good); assert(condition(prop(b, "visible"), good));
        for (const flag of ["HSM_BAR_active", "HSM_BAR_directorate", "HSM_BAR_service_founded", "HSM_BAR_region_local_open"]) {
            const bad = fresh(); open(bad); bad.flags.delete(flag); assert(!condition(prop(b, "visible"), bad));
        }
        const ai = fresh(); open(ai); ai.ai = true; assert(!condition(prop(b, "visible"), ai));
        const foreign = fresh(); open(foreign); foreign.tag = "EQS"; assert(!condition(prop(b, "visible"), foreign));
    }
    assert(!condition(prop(window, "visible"), fresh()));
});
test("no case is visible initially, with a world-state flag, or from selected-country state", () => {
    for (let i = 0; i < cases.length; i++) {
        const s = fresh(); open(s); locate(s, cases[i]);
        s.flags.add(`HSM_BAR_case_${cases[i]}_exists`);
        assert(!condition(triggers[`HSM_BAR_archive_case_${cases[i]}_visible`], s));
        run(effects[`HSM_BAR_archive_case_${cases[i]}_click`], s);
        assert.equal(s.vars.HSM_BAR_archive_case, undefined);
        assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_inaugural");
    }
});
for (const [i, c] of cases.entries()) test(c + ": staged disclosure, locked tabs, retained documents, no cross-case leakage", () => {
    for (const stage of ["known", "investigated", "studied"]) {
        const s = fresh(); open(s); locate(s, c);
        s.flags.add(stage === "studied" ? `HSM_BAR_study_${c}_done` : `HSM_BAR_case_${c}_${stage}`);
        assert(condition(triggers[`HSM_BAR_archive_case_${c}_visible`], s));
        run(effects[`HSM_BAR_archive_case_${c}_click`], s);
        assert.equal(s.vars.HSM_BAR_archive_case, i + 1);
        assert.equal(textKey("GetHSMBARArchiveTitle", s), `HSM_BAR_archive_${c}_title`);
        const level = {known: 1, investigated: 2, studied: 3}[stage];
        for (let doc = 1; doc <= 3; doc++) {
            assert.equal(condition(triggers[`HSM_BAR_archive_doc_${doc}_click_enabled`], s), doc <= level);
            s.vars.HSM_BAR_archive_document = 1;
            run(effects[`HSM_BAR_archive_doc_${doc}_click`], s);
            assert.equal(s.vars.HSM_BAR_archive_document, doc <= level ? doc : 1);
            // Force a stale/forged selected tab: scripted text still must not disclose it.
            s.vars.HSM_BAR_archive_document = doc;
            assert.equal(textKey("GetHSMBARArchiveBody", s), doc <= level ? `HSM_BAR_archive_${c}_${["", "intake", "field", "study"][doc]}` : "HSM_BAR_archive_locked");
        }
        s.vars.HSM_BAR_archive_page = 99;
        assert(!condition(triggers[`HSM_BAR_archive_case_${c}_visible`], s));
        const other = (i + 1) % cases.length; s.vars.HSM_BAR_archive_case = other + 1;
        assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_locked");
    }
});
test("Zebrica closure is not a discovery, a specimen or a completed study", () => {
    const s = fresh(); open(s); locate(s, "zebrica");
    assert(!condition(triggers.HSM_BAR_archive_case_zebrica_visible, s));
    s.flags.add("HSM_BAR_case_zebrica_known");
    assert(condition(triggers.HSM_BAR_archive_case_zebrica_visible, s));
    run(effects.HSM_BAR_archive_case_zebrica_click, s);
    assert.equal(s.vars.HSM_BAR_archive_case, 18);
    assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_zebrica_intake");
    assert(!condition(triggers.HSM_BAR_archive_doc_2_click_enabled, s));
    s.flags.add("HSM_BAR_case_zebrica_inconclusive"); s.flags.add("HSM_BAR_case_zebrica_closed");
    assert(condition(triggers.HSM_BAR_archive_doc_2_click_enabled, s));
    run(effects.HSM_BAR_archive_doc_2_click, s);
    assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_zebrica_closure");
    assert.equal(textKey("GetHSMBARArchiveDocumentTitle", s), "HSM_BAR_archive_closure_title");
    assert.equal(textKey("GetHSMBARArchive_zebrica_Status", s), "HSM_BAR_archive_status_inconclusive");
    assert(!condition(triggers.HSM_BAR_archive_doc_3_click_enabled, s));
    run(effects.HSM_BAR_archive_doc_3_click, s); assert.equal(s.vars.HSM_BAR_archive_document, 2);
    s.vars.HSM_BAR_archive_document = 3;
    assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_locked");
    assert(!read("common/scripted_guis/HSM_BAR_archive.txt").includes("HSM_BAR_study_zebrica_done"));
    for (const [lang, loc] of locales.entries()) assert(!expanded(loc.get("HSM_BAR_archive_zebrica_closure"), lang).includes("$"));
});
test("verified foreign rumours unlock only intake; crown knowledge never implies instance custody", () => {
    for (const c of ["crown", "chalice", "phylactery", "darkheart", "grover", "rosa", "herald", "sombra"]) {
        const s = fresh(); open(s); const i = cases.indexOf(c);
        locate(s, c);
        s.flags.add(`HSM_BAR_case_${c}_rumor`);
        assert(condition(triggers[`HSM_BAR_archive_case_${c}_visible`], s));
        run(effects[`HSM_BAR_archive_case_${c}_click`], s);
        assert.equal(textKey("GetHSMBARArchiveBody", s), `HSM_BAR_archive_${c}_intake`);
        assert.equal(textKey(`GetHSMBARArchive_${c}_Status`, s), "HSM_BAR_archive_status_intake");
        assert.equal(textKey("GetHSMBARArchiveAccess", s), "HSM_BAR_archive_access_intake");
        assert.equal(textKey("GetHSMBARArchiveIndexNote", s), "HSM_BAR_archive_index_filed");
        for (const doc of [2, 3]) {
            assert(!condition(triggers[`HSM_BAR_archive_doc_${doc}_click_enabled`], s));
            run(effects[`HSM_BAR_archive_doc_${doc}_click`], s);
            assert.equal(s.vars.HSM_BAR_archive_document, 1);
            s.vars.HSM_BAR_archive_document = doc;
            assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_locked");
            s.vars.HSM_BAR_archive_document = 1;
        }
        assert(!s.flags.has(`HSM_BAR_case_${c}_known`));
        assert(!s.flags.has(`HSM_BAR_case_${c}_secured`));
    }
    assert(!read("common/scripted_guis/HSM_BAR_archive.txt").includes("global.HSM_BAR_case_crowns"));
    assert(!read("common/scripted_localisation/HSM_BAR_archive.txt").includes("global.HSM_BAR_case_crowns"));
});
test("paging boundaries, back/close/reopen and empty-page notice", () => {
    const s = fresh(); open(s);
    assert.equal(textKey("GetHSMBARArchiveIndexNote", s), "HSM_BAR_archive_index_empty");
    run(effects.HSM_BAR_archive_prev_click, s); assert.equal(s.vars.HSM_BAR_archive_page, 1);
    s.flags.add("HSM_BAR_case_rock_known");
    assert.equal(textKey("GetHSMBARArchiveIndexNote", s), "HSM_BAR_archive_index_filed");
    run(effects.HSM_BAR_archive_case_rock_click, s);
    run(effects.HSM_BAR_archive_back_click, s);
    assert.equal(s.vars.HSM_BAR_archive_case, undefined); assert.equal(s.vars.HSM_BAR_archive_document, undefined);
    assert.equal(s.vars.HSM_BAR_archive_page, 1);
    run(effects.HSM_BAR_archive_case_rock_click, s); run(effects.HSM_BAR_archive_next_click, s);
    assert.equal(s.vars.HSM_BAR_archive_case, undefined); assert.equal(s.vars.HSM_BAR_archive_document, undefined);
    assert.equal(textKey("GetHSMBARArchiveIndexNote", s), "HSM_BAR_archive_index_empty");
    for (let n = 0; n < 10; n++) run(effects.HSM_BAR_archive_next_click, s);
    assert.equal(s.vars.HSM_BAR_archive_page, 2);
    for (let n = 0; n < 10; n++) run(effects.HSM_BAR_archive_prev_click, s);
    assert.equal(s.vars.HSM_BAR_archive_page, 1);
    run(effects.HSM_BAR_archive_close_click, s); assert.deepEqual(s.vars, {});
    open(s); assert.equal(s.vars.HSM_BAR_archive_page, 1);
});
test("all click effects only mutate archive presentation or the explicit operations handoff", () => {
    for (const b of [launcher, window]) for (const effect of prop(b, "effects")) {
        const variables = new Set(archiveVariables);
        if (effect.key === "HSM_BAR_archive_operations_click") for (const v of handoffVariables) variables.add(v);
        if (effect.key === "HSM_BAR_archive_open_click") variables.add("HSM_BAR_service_gui_open");
        walk(effect.value, n => {
            if (n.key === "clear_variable") assert(variables.has(n.value)
                || ["HSM_BAR_fielddesk_open", "HSM_BAR_investigation_open"].includes(n.value) && ["HSM_BAR_archive_open_click", "HSM_BAR_archive_operations_click"].includes(effect.key),
                "Unexpected archive variable: " + n.value);
            else if (["set_variable", "add_to_variable", "subtract_from_variable"].includes(n.key)) {
                assert.equal(n.value.length, 1); assert(variables.has(n.value[0].key), "Unexpected archive variable: " + n.value[0].key);
            } else if (n.key === "HSM_BAR_service_gui_refresh") {
                assert.equal(effect.key, "HSM_BAR_archive_operations_click"); assert.equal(n.value, "yes");
            } else if (!Array.isArray(n.value)) {
                assert(["has_country_flag", "has_variable", "tag", "is_ai"].includes(n.key) || variables.has(n.key) || Object.hasOwn(helpers, n.key), "Unexpected state write: " + n.key);
            } else assert(["if", "limit", "OR", "AND", "NOT", "check_variable"].includes(n.key), "Unexpected command: " + n.key);
        });
        const s = fresh(); open(s); const before = [...s.flags]; run(effect.value, s); assert.deepEqual([...s.flags], before);
    }
});
test("all GUI widgets, handlers, tooltips and dynamic text resolve", () => {
    const windows = Object.fromEntries(gui.map(n => [prop(n.value, "name"), n.value]));
    for (const b of [launcher, window]) {
        const widgets = windows[prop(b, "window_name")]; assert(widgets);
        const names = new Set(widgets.filter(n => Array.isArray(n.value)).map(n => prop(n.value, "name")));
        for (const n of prop(b, "effects")) assert(names.has(n.key.replace(/_click$/, "")), n.key);
        for (const n of prop(b, "triggers") || []) assert(names.has(n.key.replace(/_click_enabled$|_visible$/, "")), n.key);
    }
    walk(gui, n => {
        if (!["text", "buttonText", "pdx_tooltip"].includes(n.key)) return;
        if (n.value.startsWith("[")) assert(texts[n.value.slice(1, -1)], n.value);
        else for (const loc of locales) assert(loc.has(n.value), "Missing localisation " + n.value);
    });
    for (const options of Object.values(texts)) {
        assert.equal(prop(options.at(-1), "trigger"), undefined);
        for (const b of options) for (const loc of locales) assert(loc.has(prop(b, "localization_key")), prop(b, "localization_key"));
    }
    assert.deepEqual([...locales[0].keys()].sort(), [...locales[1].keys()].sort());
});
test("89 distinct in-world documents, safe redactions, real authors and no copied project prose", () => {
    const mechanical = /political power|research bonus|laboratory project|gameplay|политическ.*власт|бонус.*исследован|лабораторн[а-яё]*\s+проект|игров[а-я]+/i;
    assert(mechanical.test("Лабораторный проект"));
    assert(!mechanical.test("ЛАБОРАТОРНАЯ ЗАПИСЬ\\nПеречёркнутый проект оставлен здесь."));
    for (const [lang, loc] of locales.entries()) {
        const documents = [];
        for (const c of cases) {
            assert(loc.get(`HSM_BAR_archive_${c}_title`).length <= 30);
            const entries = ["intake", "field", "study"].map(stage => loc.get(`HSM_BAR_archive_${c}_${stage}`));
            assert.equal(new Set(entries).size, 3);
            documents.push(...entries);
        }
        documents.push(loc.get("HSM_BAR_archive_zebrica_intake"), loc.get("HSM_BAR_archive_zebrica_closure"));
        for (const c of copyCases) for (const stage of ["intake", "field", "study"]) {
            for (const suffix of ["restricted", "sealed"]) documents.push(loc.get(`HSM_BAR_archive_${c}_${stage}_${suffix}`));
        }
        assert.equal(documents.length, 89);
        assert.equal(new Set(documents).size, 89);
        for (const text of documents) {
            assert(text.length >= 240 && text.length <= 1400, "Unbounded or placeholder document");
            assert(!/[\[\]$]/.test(text), "Raw redaction syntax or localization copying in document");
            assert(!mechanical.test(text), "Mechanical narration in document: " + text.slice(0,80));
        }
        const all = documents.join("\n");
        for (const name of lang ? ["Марта Кшемень", "Северин Ольха", "Ядвига Врона", "Ирма Кальк"] : ["Marta Krzemien", "Seweryn Olcha", "Jadwiga Wrona", "Irma Kalk"]) {
            assert(all.toLowerCase().includes(name.toLowerCase()), "Missing recurring author: " + name);
        }
        for (const token of ["short", "long", "cut"]) assert(all.includes(`£HSM_BAR_redact_${token}£`), "Missing redaction style: " + token);
        assert(all.includes(lang ? "БР-003" : "BR-003"), "No cross-case narrative");
    }
    assert(locales[0].get("HSM_BAR_archive_echo_study").includes("ordinary acoustic"));
    assert(locales[0].get("HSM_BAR_archive_marsh_study").includes("ordinary chemical"));
    assert(locales[0].get("HSM_BAR_archive_compass_study").includes("magnetised"));
    assert(locales[0].get("HSM_BAR_archive_grover_study").includes("No examination of a body"));
    assert(locales[0].get("HSM_BAR_archive_rosa_study").includes("No autopsy"));
    assert(locales[0].get("HSM_BAR_archive_herald_study").includes("no accessible remains"));
});
test("redactions retain white-square counts on dark backing and distinct excisions without missing glyphs", () => {
    const gfx = parse(read("interface/HSM_BAR_archive_redactions.gfx"), true);
    const sprites = Object.fromEntries(prop(gfx, "spriteTypes").map(n => [prop(n.value, "name"), n.value]));
    for (const [kind, width] of Object.entries({short: 50, long: 74, cut: 148})) {
        const b = sprites[`GFX_HSM_BAR_redact_${kind}`]; assert(b);
        const bytes = fs.readFileSync(path.join(mod, prop(b, "texturefile")));
        assert.equal(bytes[0], 0); assert.equal(bytes[1], 0); assert.equal(bytes[2], 2);
        assert.equal(bytes.readUInt16LE(12), width); assert.equal(bytes.readUInt16LE(14), 18);
        assert.equal(bytes[16], 32); assert.equal(bytes[17], 8);
        assert.equal(bytes.length, 18 + width * 18 * 4);
        let ink = 0, clear = 0, white = 0, dark = 0;
        for (let i = 18; i < bytes.length; i += 4) {
            if (bytes[i + 3]) {
                ink++;
                const [b, g, r] = bytes.subarray(i, i + 3);
                assert.equal(b, g, kind + ": nonneutral redaction"); assert.equal(g, r, kind + ": nonneutral redaction");
                if (r === 255) { assert.notEqual(kind, "cut", "Excisions use dark outlines"); white++; }
                else { assert(r <= 96, kind + ": insufficient dark backing/outline"); dark++; }
                assert.equal(bytes[i + 3], kind === "cut" ? 190 : 255);
            } else clear++;
        }
        assert(clear > 0); assert(ink > 100);
        assert(dark > 0, kind + ": missing backing/outline on light paper");
        if (kind !== "cut") {
            assert.equal(white, kind === "short" ? 400 : 600, "Four or six solid ten-pixel white squares");
            assert.equal(ink, (width - 2) * 12, "Opaque backing retains a transparent margin");
        }
    }
    for (const [key, en] of locales[0]) {
        const ru = locales[1].get(key); assert.notEqual(ru, undefined);
        const tokens = text => [...text.matchAll(/£([^£]+)£/g)].map(m => m[1]);
        assert.deepEqual(tokens(en), tokens(ru), key + ": mismatched redaction placement");
        for (const text of [en, ru]) {
            for (const token of tokens(text)) assert(sprites["GFX_" + token], key + ": unregistered inline sprite");
            assert(!/«(?:СКРЫТ(?:О|А|Ы)?|WITHHELD|УДАЛЕН(?:О|А|Ы)?|REMOVED)(?:\s[^»]*)?»/i.test(text), key + ": old redaction placeholder");
            assert(!/[■█]/u.test(text), key + ": unsupported bitmap-font square");
        }
    }
    assert(locales[0].get("HSM_BAR_archive_compass_intake").includes("UNKNOWN"));
    assert(locales[1].get("HSM_BAR_archive_compass_intake").includes("НЕИЗВЕСТЕН"));
    assert(locales[0].get("HSM_BAR_archive_marsh_intake").includes("£HSM_BAR_redact_long£"));
    assert(locales[1].get("HSM_BAR_archive_marsh_intake").includes("£HSM_BAR_redact_long£"));
});

test("public case numbers and cross-references agree with the shared research-report order", () => {
    const reportOrder = "rock titan entity amulet plants reactor crown chalice phylactery darkheart grover rosa herald sombra echo marsh compass zebrica".split(" ");
    for (const [lang, loc] of locales.entries()) {
        const prefix = lang ? "БР" : "BR";
        for (const [i, c] of reportOrder.entries()) {
            assert(loc.get(`HSM_BAR_archive_${c}_title`).startsWith(`${prefix}-${String(i + 1).padStart(3, "0")} |`));
        }
        for (const [key, text] of loc) {
            if (!/_(intake|field|study|closure)(?:_(restricted|sealed))?$/.test(key)) continue;
            for (const m of text.matchAll(/(?:BR|БР)-(\d+)/g)) {
                assert.equal(m[1].length, 3, key + ": noncanonical case number");
                assert(Number(m[1]) >= 1 && Number(m[1]) <= reportOrder.length, key + ": unknown cross-reference");
            }
        }
        for (const [key, number] of [["entity_field", "015"], ["echo_study", "003"]]) {
            assert(["", "_restricted", "_sealed"].some(suffix => loc.get("HSM_BAR_archive_" + key + suffix).includes(prefix + "-" + number)),
                key + ": missing cross-case reference from all copies");
        }
        assert(loc.get("HSM_BAR_archive_darkheart_field").includes(prefix + "-014"));
        assert(loc.get("HSM_BAR_archive_sombra_field").includes(prefix + "-010"));
    }
});
test("study/intake flags and live access predicates resolve to their existing producers", () => {
    const sources = ["common/scripted_effects/HSM_BAR_anomalies.txt", "common/scripted_effects/HSM_BAR_cases.txt"].map(read).join("\n");
    const casePredicates = defs(parse(read("common/scripted_triggers/HSM_BAR_cases.txt")));
    for (const c of cases) {
        for (const flag of [`HSM_BAR_case_${c}_known`, `HSM_BAR_study_${c}_done`]) {
            assert(new RegExp("set_country_flag\\s*=\\s*" + flag + "\\b").test(sources), "No producer for " + flag);
        }
        assert(casePredicates[`HSM_BAR_cases_${c}_access`], "Missing live access predicate: " + c);
    }
});
test("working class and risk do not change just because research finishes; Guardian is a secondary role", () => {
    for (const c of cases) {
        const s = fresh(); s.flags.add(`HSM_BAR_case_${c}_known`); open(s);
        locate(s, c);
        run(effects[`HSM_BAR_archive_case_${c}_click`], s);
        const before = textKey("GetHSMBARArchiveClassification", s);
        assert.equal(before, `HSM_BAR_archive_class_${c}`);
        s.flags.add(`HSM_BAR_study_${c}_done`);
        assert.equal(textKey("GetHSMBARArchiveClassification", s), before);
        s.access.add(`HSM_BAR_cases_${c}_access`);
        assert(!["HSM_BAR_archive_access_intake", "HSM_BAR_archive_access_unavailable"].includes(textKey("GetHSMBARArchiveAccess", s)));
        s.access.clear();
        assert.equal(textKey("GetHSMBARArchiveAccess", s), "HSM_BAR_archive_access_unavailable");
        assert.equal(textKey("GetHSMBARArchiveClassification", s), before);
    }
    const loc = locales[0];
    for (const className of ["Hearth", "Lunar Circle", "Winter Watch", "Starless"]) assert([...loc.values()].some(v => v.includes(className)));
    assert(loc.get("HSM_BAR_archive_class_amulet").includes("Hearth / Guardian"));
    assert(!read("common/scripted_localisation/HSM_BAR_archive.txt").match(/HSM_BAR_archive_class_(studied|field|intake)/));
});
test("Results is a fourth tab: per-case delegated output, unknown-case and foreign-player protection", () => {
    for (const [i, c] of [...cases, "zebrica"].entries()) {
        const s = fresh(); open(s); locate(s, c); s.vars.HSM_BAR_archive_case = i + 1;
        assert(!condition(triggers.HSM_BAR_archive_doc_4_click_enabled, s));
        run(effects.HSM_BAR_archive_doc_4_click, s); assert.equal(s.vars.HSM_BAR_archive_document, undefined);
        s.vars.HSM_BAR_archive_document = 4;
        assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_locked");
        s.flags.add(`HSM_BAR_case_${c}_known`);
        assert(condition(triggers.HSM_BAR_archive_doc_4_click_enabled, s));
        run(effects.HSM_BAR_archive_doc_4_click, s);
        assert.equal(textKey("GetHSMBARArchiveBody", s), `HSM_BAR_archive_${c}_results`);
        assert.equal(textKey("GetHSMBARArchiveRecordNote", s), "HSM_BAR_archive_results_note");
        for (const [lang, loc] of locales.entries()) {
            assert.equal(loc.get(`HSM_BAR_archive_${c}_results`), `[ROOT.GetHSMBAROutcome_${c}]`);
            assert(!expanded(loc.get(`HSM_BAR_archive_${c}_results`), lang).match(/[\[\]$]/));
        }
        s.tag = "EQS";
        assert(!condition(triggers.HSM_BAR_archive_doc_4_click_enabled, s));
        assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_locked");
        for (const getter of ["GetHSMBARArchiveTitle", "GetHSMBARArchiveClassification", "GetHSMBARArchiveAccess"]) assert.equal(textKey(getter, s), "HSM_BAR_archive_private");
    }
    const z = outcomeTexts.GetHSMBAROutcome_zebrica;
    assert(z && z.some(b => prop(b, "localization_key") === "HSM_BAR_outcome_inconclusive"));
    assert(locales[0].get("HSM_BAR_archive_zebrica_closure").includes("No authenticated specimen"));
});
test("founding memorandum on empty archive, no formation-day access, retained studies after access loss", () => {
    const s = fresh(); open(s);
    assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_inaugural");
    s.flags.delete("HSM_BAR_service_founded");
    assert(!condition(prop(launcher, "visible"), s)); assert(!condition(prop(window, "visible"), s));
    assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_locked");
    s.flags.add("HSM_BAR_service_founded"); s.flags.add("HSM_BAR_study_rock_done");
    s.vars.HSM_BAR_archive_case = 1; s.vars.HSM_BAR_archive_document = 3;
    assert.equal(textKey("GetHSMBARArchiveAccess", s), "HSM_BAR_archive_access_unavailable");
    assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_rock_study");
});
test("photo releases require the selected case's inquiry; bench specimens require completed study", () => {
    for (const [i, c] of [...cases, "zebrica"].entries()) {
        for (const stage of ["none", "exists", "rumor", "known", "secured", "investigated", "studied"]) {
            const s = fresh(); open(s);
            locate(s, c); s.vars.HSM_BAR_archive_case = i + 1; s.vars.HSM_BAR_archive_document = 1;
            if (stage !== "none") s.flags.add(stage === "studied" ? `HSM_BAR_study_${c}_done` : `HSM_BAR_case_${c}_${stage}`);
            const released = photoCases.includes(c) && (stage === "studied" || stage === "investigated" && !specimenPhotos.has(c));
            const label = c + ": " + stage;
            assert.equal(widgetVisible("HSM_BAR_archive_doc_5", s), released, label);
            assert.equal(condition(triggers.HSM_BAR_archive_doc_5_click_enabled, s), released, label);
            assert.deepEqual(visiblePhotos(s), [], label);
            const before = structuredClone(s);
            run(effects.HSM_BAR_archive_doc_5_click, s);
            if (released) before.vars.HSM_BAR_archive_document = 5;
            assert.deepEqual(s, before, label + ": only presentation selection may change");
            s.vars.HSM_BAR_archive_document = 5;
            assert.deepEqual(visiblePhotos(s), released ? [c] : [], label);
            assert.equal(widgetVisible("HSM_BAR_archive_photo_caption", s), released, label);
            assert.equal(textKey("GetHSMBARArchivePhotoCaption", s), released ? `HSM_BAR_archive_photo_${c}_caption` : "HSM_BAR_archive_photo_unavailable", label);
            for (const name of ["document_title", "document_body"]) assert.equal(widgetVisible("HSM_BAR_archive_" + name, s), !released, label);
            assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_locked", label);
        }
    }
});

test("wrong-case flags and invalid selections never disclose a plate or caption", () => {
    for (const source of photoCases) for (const stage of ["investigated", "studied"]) {
        for (const id of [undefined, -1, 0, ...cases.map((_, i) => i + 1), 18, 19, 999]) {
            const s = fresh(); open(s);
            locate(s, source);
            if (id !== undefined) s.vars.HSM_BAR_archive_case = id;
            s.vars.HSM_BAR_archive_document = 5;
            s.flags.add(stage === "studied" ? `HSM_BAR_study_${source}_done` : `HSM_BAR_case_${source}_investigated`);
            const released = id === cases.indexOf(source) + 1 && (stage === "studied" || !specimenPhotos.has(source));
            assert.deepEqual(visiblePhotos(s), released ? [source] : []);
            assert.equal(condition(triggers.HSM_BAR_archive_doc_5_click_enabled, s), released);
            assert.equal(textKey("GetHSMBARArchivePhotoCaption", s), released ? `HSM_BAR_archive_photo_${source}_caption` : "HSM_BAR_archive_photo_unavailable");
        }
    }
});

test("photo controls, captions and sprites independently reject lost Service scope and closed windows", () => {
    const revoke = [
        s => { s.tag = "EQS"; }, s => { s.ai = true; },
        ...["HSM_BAR_active", "HSM_BAR_directorate", "HSM_BAR_service_founded", "HSM_BAR_region_local_open"].map(flag => s => s.flags.delete(flag)),
        s => { delete s.vars.HSM_BAR_archive_open; }
    ];
    for (const c of photoCases) for (const change of revoke) {
        const s = fresh(); open(s);
        s.flags.add(`HSM_BAR_study_${c}_done`);
        locate(s, c); s.vars.HSM_BAR_archive_case = cases.indexOf(c) + 1;
        s.vars.HSM_BAR_archive_document = 5;
        assert.deepEqual(visiblePhotos(s), [c]);
        change(s);
        assert(!widgetVisible("HSM_BAR_archive_doc_5", s));
        assert(!condition(triggers.HSM_BAR_archive_doc_5_click_enabled, s));
        assert(!widgetVisible("HSM_BAR_archive_photo_caption", s));
        assert.deepEqual(visiblePhotos(s), []);
        assert.equal(textKey("GetHSMBARArchivePhotoCaption", s), "HSM_BAR_archive_photo_unavailable");
        s.vars.HSM_BAR_archive_document = 1;
        const before = structuredClone(s);
        run(effects.HSM_BAR_archive_doc_5_click, s); assert.deepEqual(s, before);
    }
});

test("photo selection resets on case/page/back/close/reopen and all four documents restore scrolling prose", () => {
    const s = fresh(); open(s);
    for (const c of cases) s.flags.add(`HSM_BAR_study_${c}_done`);
    s.flags.add("HSM_BAR_case_zebrica_known");
    function select(c) {
        const id = [...cases, "zebrica"].indexOf(c);
        locate(s, c);
        run(effects[`HSM_BAR_archive_case_${c}_click`], s);
        assert.equal(s.vars.HSM_BAR_archive_document, 1);
        assert.deepEqual(visiblePhotos(s), []);
        assert(widgetVisible("HSM_BAR_archive_document_body", s));
    }
    for (const c of [...cases, "zebrica"]) {
        select("rock"); run(effects.HSM_BAR_archive_doc_5_click, s);
        select(c);
        run(effects.HSM_BAR_archive_doc_5_click, s);
        assert.deepEqual(visiblePhotos(s), photoCases.includes(c) ? [c] : []);
    }
    for (const c of photoCases) {
        select(c);
        for (let tab = 1; tab <= 4; tab++) {
            run(effects.HSM_BAR_archive_doc_5_click, s);
            assert.deepEqual(visiblePhotos(s), [c]);
            assert(!widgetVisible("HSM_BAR_archive_document_body", s));
            run(effects[`HSM_BAR_archive_doc_${tab}_click`], s);
            assert.equal(s.vars.HSM_BAR_archive_document, tab);
            assert.deepEqual(visiblePhotos(s), []);
            assert(!widgetVisible("HSM_BAR_archive_photo_caption", s));
            assert.equal(widgetVisible("HSM_BAR_archive_document_title", s), !(copyCases.has(c) && tab <= 3));
            assert(widgetVisible("HSM_BAR_archive_document_body", s));
            assert.equal(textKey("GetHSMBARArchiveBody", s), `HSM_BAR_archive_${c}_${["", "intake", "field", "study", "results"][tab]}`);
        }
    }
    for (const action of ["prev", "next", "back", "close"]) {
        select(action === "next" ? "rock" : "reactor"); run(effects.HSM_BAR_archive_doc_5_click, s);
        run(effects[`HSM_BAR_archive_${action}_click`], s);
        assert.equal(s.vars.HSM_BAR_archive_case, undefined);
        assert.equal(s.vars.HSM_BAR_archive_document, undefined);
        assert.deepEqual(visiblePhotos(s), []);
        assert(!widgetVisible("HSM_BAR_archive_photo_caption", s));
        open(s); assert.deepEqual(visiblePhotos(s), []);
        assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_inaugural");
    }
    select("rock"); run(effects.HSM_BAR_archive_doc_5_click, s); open(s);
    assert.deepEqual(visiblePhotos(s), []);
    // A permission change while the plate is open restores the locked leaf immediately.
    select("rock"); run(effects.HSM_BAR_archive_doc_5_click, s);
    s.flags.delete("HSM_BAR_study_rock_done");
    assert.deepEqual(visiblePhotos(s), []);
    assert(widgetVisible("HSM_BAR_archive_document_body", s));
    assert.equal(textKey("GetHSMBARArchiveBody", s), "HSM_BAR_archive_locked");
});

test("historical plates survive loss of site/specimen access without flags, custody, rewards or resource writes", () => {
    for (const c of photoCases) for (const stage of specimenPhotos.has(c) ? ["studied"] : ["investigated", "studied"]) {
        const s = fresh(); open(s);
        s.flags.add(stage === "studied" ? `HSM_BAR_study_${c}_done` : `HSM_BAR_case_${c}_investigated`);
        s.flags.add(`HSM_BAR_case_${c}_secured`);
        s.access.add(`HSM_BAR_cases_${c}_access`);
        locate(s, c); s.vars.HSM_BAR_archive_case = cases.indexOf(c) + 1;
        s.vars.HSM_BAR_research_budget = 37; s.vars.political_power = 111;
        run(effects.HSM_BAR_archive_doc_5_click, s);
        assert.deepEqual(visiblePhotos(s), [c]);
        s.flags.delete(`HSM_BAR_case_${c}_secured`); s.access.clear();
        const before = structuredClone(s);
        for (let repeat = 0; repeat < 3; repeat++) run(effects.HSM_BAR_archive_doc_5_click, s);
        assert.deepEqual(s, before);
        assert.deepEqual(visiblePhotos(s), [c]);
        assert.equal(textKey("GetHSMBARArchivePhotoCaption", s), `HSM_BAR_archive_photo_${c}_caption`);
        assert.equal(textKey("GetHSMBARArchiveAccess", s), "HSM_BAR_archive_access_unavailable");
        assert.equal(textKey("GetHSMBARArchiveRecordNote", s), "HSM_BAR_archive_record_note");
    }
});

test("bilingual photo captions use public case IDs, inquiry dates and documentary subjects", () => {
    for (const [lang, loc] of locales.entries()) for (const c of photoCases) {
        const caption = loc.get(`HSM_BAR_archive_photo_${c}_caption`);
        assert(caption.startsWith(loc.get(`HSM_BAR_archive_${c}_title`).split(" |")[0] + " |"));
        assert(caption.includes(lang ? "Архив на дату проверки." : "Archive, as of inquiry date."));
        assert(!/[\[\]$]/.test(caption));
        assert(caption.length < 190);
    }
    for (const [key, patterns] of Object.entries({
        compass: [/merchant.*case/i, /removed fastener/i, /blind-comparison/i],
        marsh: [/water and sediment jars/i, /light in the middle sample/i],
        amulet: [/copied boundary survey/i, /schematic/i, /not requisitioned/i],
        titan: [/drawing/i, /no intact Titan/i],
        entity: [/no entity visible/i],
        darkheart: [/umbrum/i, /partly withheld/i, /not the original Crystal Heart/i]
    })) for (const pattern of patterns) assert.match(locales[0].get(`HSM_BAR_archive_photo_${key}_caption`), pattern);
    for (const c of ["compass", "marsh"]) {
        assert(!/magnetic stone|spirit|ghost/i.test(locales[0].get(`HSM_BAR_archive_photo_${c}_caption`)));
        assert(!/магнитн.*камень|призрак|дух[аиов]?\b/i.test(locales[1].get(`HSM_BAR_archive_photo_${c}_caption`)));
        // Field-accessible photographs record observations, not unreleased study conclusions.
        assert(!/ordinary chemical reaction|magnetised/i.test(locales[0].get(`HSM_BAR_archive_photo_${c}_caption`)));
        assert(!/химическ|намагниченн/i.test(locales[1].get(`HSM_BAR_archive_photo_${c}_caption`)));
    }
    for (const c of [...cases, "zebrica"].filter(c => !photoCases.includes(c))) {
        for (const loc of locales) assert(!loc.has(`HSM_BAR_archive_photo_${c}_caption`));
        assert.equal(triggers[`HSM_BAR_archive_photo_${c}_visible`], undefined);
    }
});

test("32 skin selectors follow only region/case/document/copy variables with safe defaults and equal bounds", () => {
    const source = parse(read("common/scripted_localisation/HSM_BAR_archive_skin.txt"));
    const selectors = new Map();
    const {sprites} = archiveAssets();
    const properties = prop(window, "properties"); assert(properties, "Missing scripted image properties");
    const variables = new Set(["HSM_BAR_archive_region", "HSM_BAR_archive_case", "HSM_BAR_archive_document", "HSM_BAR_archive_copy"]);
    for (const node of source) {
        assert.equal(node.key, "defined_text");
        const name = prop(node.value, "name"); assert(name && !selectors.has(name), "Missing/duplicate image selector");
        const choices = node.value.filter(n => n.key === "text").map(n => n.value);
        assert.equal(choices.length, 2, name + ": selected image plus default image");
        assert(prop(choices[0], "trigger"), name + ": selection must be conditional");
        assert.equal(prop(choices[1], "trigger"), undefined, name + ": unconditional fallback required");
        walk(node.value, n => {
            assert(["name", "text", "trigger", "localization_key", "check_variable", "has_variable", "AND", "OR", "NOT", ...variables].includes(n.key), name + ": selector reads/writes unrelated state: " + n.key);
            if (n.key === "has_variable") assert(variables.has(n.value));
            if (n.key === "check_variable") assert(n.value.length === 1 && variables.has(n.value[0].key));
        });
        selectors.set(name, choices);
    }
    assert.equal(selectors.size, 32);
    const targets = [...[...cases, "zebrica"].map((c, i) => ({widget: "HSM_BAR_archive_case_" + c, getter: `GetHSMBARArchiveCase${c}Skin`, variable: "HSM_BAR_archive_case", value: i + 1, role: "index", size: {w: 261, h: 34}})),
        ...Array.from({length: 5}, (_, i) => ({widget: "HSM_BAR_archive_doc_" + (i + 1), getter: `GetHSMBARArchiveDoc${i + 1}Skin`, variable: "HSM_BAR_archive_document", value: i + 1, role: i === 4 ? "photo" : "tab", size: {w: i === 4 ? 36 : 141, h: i === 4 ? 36 : 34}})),
        ...Array.from({length: 3}, (_, i) => ({widget: "HSM_BAR_archive_copy_" + (i + 1), getter: `GetHSMBARArchiveCopy${i + 1}Skin`, variable: "HSM_BAR_archive_copy", value: i + 1, role: "edition", size: {w: 192, h: 30}})),
        ...Array.from({length: 6}, (_, i) => ({widget: "HSM_BAR_archive_region_" + (i + 1), getter: `GetHSMBARArchiveRegion${i + 1}Skin`, variable: "HSM_BAR_archive_region", value: i + 1, role: "tab", size: {w: 141, h: 34}}))];
    const widgets = gui.find(n => prop(n.value, "name") === "HSM_BAR_archive_window").value;
    assert.equal(properties.length, targets.length, "Expected 18 case, five document, three copy and six region image properties");
    for (const target of targets) {
        const entry = properties.filter(n => n.key === target.widget); assert.equal(entry.length, 1, target.widget);
        assert.equal(entry[0].value.length, 1, target.widget + ": only image may change");
        const image = prop(entry[0].value, "image");
        assert.equal(typeof image, "string"); assert.match(image, /^\[GetHSMBARArchive\w+Skin\]$/);
        const getter = image.slice(1, -1); assert.equal(getter.toLowerCase(), target.getter.toLowerCase());
        const choices = selectors.get(getter); assert(choices, "Missing selector: " + getter);
        const base = "GFX_HSM_BAR_archive_" + target.role;
        assert.deepEqual(choices.map(b => prop(b, "localization_key")), [base + "_selected", base]);
        for (const b of choices) assert.deepEqual(spriteDimensions(sprites, prop(b, "localization_key")), target.size);
        const widget = widgets.find(n => Array.isArray(n.value) && prop(n.value, "name") === target.widget); assert(widget);
        assert.equal(prop(widget.value, "quadTextureSprite"), base);
        if (target.role !== "photo") assert.equal(prop(widget.value, "buttonFont"), "HSM_BAR_archive_ink");
        for (const selectedCase of [undefined, -1, 0, ...Array.from({length: 19}, (_, i) => i + 1), 999]) {
            for (const doc of [undefined, -1, 0, 1, 2, 3, 4, 5, 6, 999]) for (const page of [1, 5]) {
                const s = fresh(); open(s); s.vars.HSM_BAR_archive_page = page;
                if (selectedCase !== undefined) s.vars.HSM_BAR_archive_case = selectedCase;
                if (doc !== undefined) s.vars.HSM_BAR_archive_document = doc;
                const before = structuredClone(s);
                const chosen = choices.find(b => !prop(b, "trigger") || condition(prop(b, "trigger"), s));
                assert(chosen, getter + ": no default image");
                const selected = s.vars[target.variable] === target.value || target.role === "edition" && target.value === 1;
                assert.equal(prop(chosen, "localization_key"), base + (selected ? "_selected" : ""), `${getter}: case ${selectedCase}, doc ${doc}, page ${page}`);
                assert.deepEqual(s, before, getter + ": image selection must be read-only");
            }
        }
    }
});

test("paper geometry and case index placement retain their skin layout contract", () => {
    const w = gui.find(n => prop(n.value, "name") === "HSM_BAR_archive_window").value;
    const widget = name => w.find(n => Array.isArray(n.value) && prop(n.value, "name") === "HSM_BAR_archive_" + name)?.value;
    for (const key of ["classification", "access"]) {
        const b = widget(key); assert(b);
        assert.equal(Number(prop(prop(b, "position"), "x")), 350, key);
        assert.equal(Number(prop(b, "maxWidth")), 600, key);
    }
    for (const [key, rect] of Object.entries({case_title: [350, 136, 600, 34], document_title: [350, 310, 600, 30], photo_caption: [350, 606, 600, 32], record_note: [24, 644, 264, 36]})) {
        const b = widget(key); assert(b);
        assert.deepEqual([Number(prop(prop(b, "position"), "x")), Number(prop(prop(b, "position"), "y")), Number(prop(b, "maxWidth")), Number(prop(b, "maxHeight"))], rect, key);
    }
    const back = widget("back"); assert(back);
    assert.equal(Number(prop(prop(back, "position"), "x")), 112);
    assert.equal(Number(prop(prop(back, "position"), "y")), 548);
    for (const [i, c] of [...cases, "zebrica"].entries()) {
        const b = widget("case_" + c); assert(b);
        assert.equal(Number(prop(prop(b, "position"), "x")), 24);
        assert.equal(Number(prop(prop(b, "position"), "y")), 170 + caseRows[c] * 92);
        assert.equal(prop(b, "quadTextureSprite"), "GFX_HSM_BAR_archive_index");
        assert.equal(prop(b, "buttonFont"), "HSM_BAR_archive_ink");
    }
});

test("navigation stays on cloth; paper content clears the actual top-sheet edges", () => {
    const children = gui.find(n => prop(n.value, "name") === "HSM_BAR_archive_window").value;
    const {sprites} = archiveAssets();
    const box = key => {
        const widget = children.find(n => Array.isArray(n.value) && prop(n.value, "name") === "HSM_BAR_archive_" + key)?.value;
        assert(widget, key); assert.equal(prop(widget, "scale"), undefined, key + ": native-size hitbox");
        const position = prop(widget, "position"), sprite = prop(widget, "quadTextureSprite");
        const size = sprite ? spriteDimensions(sprites, sprite) : {w: Number(prop(widget, "maxWidth")), h: Number(prop(widget, "maxHeight"))};
        return {x: Number(prop(position, "x")), y: Number(prop(position, "y")), ...size};
    };
    const close = box("close"), back = box("back");
    assert.deepEqual(close, {x: 944, y: 20, w: 36, h: 36});
    assert.equal(1000 - close.x - close.w, 20);
    assert.deepEqual(back, {x: 112, y: 548, w: 36, h: 36});
    const prev = box("prev"), next = box("next");
    assert.deepEqual(prev, {x: 24, y: 548, w: 36, h: 36});
    assert.deepEqual(next, {x: 68, y: 548, w: 36, h: 36});
    assert.equal(next.x - prev.x - prev.w, 8);
    assert.equal(back.x - next.x - next.w, 8);
    for (const [role, count, width, y] of [["doc", 4, 141, 260], ["copy", 3, 192, 306]]) {
        for (let i = 1; i <= count; i++) assert.deepEqual(box(role + "_" + i), {x: 350 + (width + 12) * (i - 1), y, w: width, h: role === "doc" ? 34 : 30});
        const last = box(role + "_" + count); assert.equal(last.x + last.w, 950);
    }
    const photo = box("doc_5");
    assert.deepEqual(photo, {x: 204, y: 548, w: 36, h: 36});
    assert(photo.x - back.x - back.w >= 32, "Separate navigation from attachments");
    for (const c of ["echo", "entity", "reactor"]) {
        const audio = box("audio_" + c);
        assert.deepEqual(audio, {x: 248, y: 548, w: 36, h: 36});
        assert.equal(audio.x - photo.x - photo.w, 8);
        assert(audio.x + audio.w <= 288, "Attachment must clear the spine");
    }
    // The textured stack is larger than the flat writing area, particularly at y=112/634.
    const assertPaper = (b, name) => assert(b.x >= 350 && b.x + b.w <= 956 && b.y >= 136 && b.y + b.h <= 640, name + ": outside clean top-sheet inset");
    for (const key of ["case_title", "classification", "access", "document_title", "document_body", "photo_caption",
        "doc_1", "doc_2", "doc_3", "doc_4", "copy_1", "copy_2", "copy_3"]) assertPaper(box(key), key);
    for (const node of children.filter(n => n.key === "iconType")) {
        const pos = prop(node.value, "position");
        assertPaper({x: Number(prop(pos, "x")), y: Number(prop(pos, "y")), ...spriteDimensions(sprites, prop(node.value, "spriteType"))}, prop(node.value, "name"));
    }
    assert.throws(() => assertPaper({x: 394, y: 112, w: 556, h: 34}, "old title"), /clean top-sheet/);
    assert.throws(() => assertPaper({x: 866, y: 634, w: 36, h: 36}, "old media"), /clean top-sheet/);
});

test("installed native patterns and all referenced sprites/textures exist", () => {
    const pattern = fs.readFileSync(path.join(eaw, "common/scripted_guis/eaw_bar_scripetd_guis.txt"), "utf8");
    assert(pattern.includes("context_type = player_context")); assert(pattern.includes("clear_variable = bar_pen_screen_show"));
    const welcome = fs.readFileSync(path.join(eaw, "common/scripted_guis/eaw_welcome_screen.txt"), "utf8");
    assert(welcome.includes("parent_window_token = politics_tab")); assert(welcome.includes("_visible ="));
    const {sprites} = archiveAssets();
    walk(gui, n => {
        if (!["spriteType", "quadTextureSprite"].includes(n.key)) return;
        const b = sprites[n.value]; assert(b, "Missing registered sprite: " + n.value);
        const texture = field(b, "texturefile"); assert(texture, n.value);
        const file = resolveAsset(texture);
        const size = spriteDimensions(sprites, n.value);
        if (n.value.startsWith("GFX_HSM_BAR_archive_photo_")) {
            assert.equal(path.extname(file).toLowerCase(), ".tga");
            assert.deepEqual(size, {w: 600, h: 300}, n.value + ": plate dimensions");
            assert.equal(Number(field(b, "noOfFrames") || 1), 1, n.value + ": single plate");
        }
    });
});
test("1080p-compatible window, exclusive plates and non-overlapping visible controls with original scrolling prose", () => {
    const w = gui.find(n => prop(n.value, "name") === "HSM_BAR_archive_window").value;
    const size = prop(w, "size"); const width = Number(prop(size, "width")), height = Number(prop(size, "height"));
    assert.equal(width, 1000); assert.equal(height, 700);
    assert.equal(prop(w, "orientation"), "center"); assert.equal(prop(w, "origo"), "center");
    for (const [screenW, screenH] of [[1920, 1080], [1600, 900], [1366, 768], [1280, 720]]) {
        assert(width < screenW); assert((screenH - height) / 2 >= (screenH === 720 ? 10 : 30));
    }
    const boxes = w.filter(n => n.key === "instantTextboxType").map(n => {
        const p = prop(n.value, "position"); return {name: prop(n.value, "name"), x: Number(prop(p, "x")), y: Number(prop(p, "y")), w: Number(prop(n.value, "maxWidth")), h: Number(prop(n.value, "maxHeight"))};
    });
    for (const b of boxes) { assert(b.x >= 0 && b.y >= 0 && b.x + b.w <= width && b.y + b.h <= height, b.name); }
    const {sprites} = archiveAssets();
    for (const n of w.filter(n => n.key === "buttonType" && !prop(n.value, "name").startsWith("HSM_BAR_archive_input_"))) {
        const size = spriteDimensions(sprites, prop(n.value, "quadTextureSprite")), pos = prop(n.value, "position");
        assert.equal(prop(n.value, "scale"), undefined, "Controls must retain their real texture dimensions");
        const explicit = prop(n.value, "size");
        if (explicit) assert.deepEqual({w: Number(prop(explicit, "x")), h: Number(prop(explicit, "y"))}, size);
        boxes.push({name: prop(n.value, "name"), x: Number(prop(pos, "x")), y: Number(prop(pos, "y")),
            ...size});
    }
    const photos = w.filter(n => n.key === "iconType");
    assert.deepEqual(photos.map(n => prop(n.value, "name")).sort(), photoCases.map(c => "HSM_BAR_archive_photo_" + c).sort());
    for (const {value: b} of photos) {
        const pos = prop(b, "position"), name = prop(b, "name");
        assert.equal(prop(b, "spriteType"), name.replace("HSM_BAR_", "GFX_HSM_BAR_"));
        assert.equal(Number(prop(pos, "x")), 350); assert.equal(Number(prop(pos, "y")), 300);
        assert.equal(prop(b, "scale"), undefined); assert.equal(prop(b, "alwaystransparent"), "yes");
        assert(triggers[name + "_visible"]);
        const size = spriteDimensions(sprites, prop(b, "spriteType"));
        assert.deepEqual(size, {w: 600, h: 300});
        boxes.push({name, x: 350, y: 300, ...size});
    }
    for (const b of boxes) assert(b.x >= 0 && b.y >= 0 && b.x + b.w <= width && b.y + b.h <= height, b.name);
    for (const stage of ["known", "investigated", "studied"]) for (let region = 1; region <= 6; region++) for (let page = 1; page <= (region === 1 ? 2 : 1); page++) {
        const s = fresh(); open(s); s.vars.HSM_BAR_archive_region = region; s.vars.HSM_BAR_archive_page = page;
        for (const c of cases) s.flags.add(stage === "studied" ? `HSM_BAR_study_${c}_done` : `HSM_BAR_case_${c}_${stage}`);
        s.flags.add("HSM_BAR_case_zebrica_known");
        for (let id = 0; id <= 19; id++) for (let doc = 0; doc <= 5; doc++) {
            if (id) s.vars.HSM_BAR_archive_case = id; else delete s.vars.HSM_BAR_archive_case;
            s.vars.HSM_BAR_archive_document = doc;
            const visible = boxes.filter(b => widgetVisible(b.name, s));
            for (let i = 0; i < visible.length; i++) for (let j = i + 1; j < visible.length; j++) {
                const a = visible[i], b = visible[j];
                assert(!(a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h),
                    a.name + " overlaps " + b.name + ` (page ${page}, case ${id}, tab ${doc}, ${stage})`);
            }
        }
    }
    const body = w.find(n => Array.isArray(n.value) && prop(n.value, "name") === "HSM_BAR_archive_document_body").value;
    assert.equal(prop(body, "scrollbartype"), "standardtext_slider");
    assert.equal(prop(body, "font"), "HSM_BAR_archive_body");
    assert.equal(Number(prop(prop(body, "position"), "x")), 350);
    assert.equal(Number(prop(prop(body, "position"), "y")), 350);
    assert.equal(Number(prop(body, "maxWidth")), 606);
    assert.equal(Number(prop(body, "maxHeight")), 274);
});
test("two full-size mouse shields leave all four document tabs and the photo control reachable", () => {
    const w = gui.find(n => prop(n.value, "name") === "HSM_BAR_archive_window").value;
    assert.equal(prop(w, "click_to_front"), "yes");
    const children = w.filter(n => Array.isArray(n.value));
    const {sprites} = archiveAssets();
    const shields = children.filter(n => /HSM_BAR_archive_input_(floor|shield)/.test(prop(n.value, "name")));
    assert.equal(shields.length, 2);
    const firstControl = children.findIndex(n => prop(n.value, "name") === "HSM_BAR_archive_close");
    for (const n of shields) {
        assert.equal(n.key, "buttonType");
        assert(children.indexOf(n) < firstControl);
        assert.equal(prop(n.value, "alwaystransparent"), "no");
        assert.equal(Number(prop(prop(n.value, "size"), "x")), 1000);
        assert.equal(Number(prop(prop(n.value, "size"), "y")), 700);
        assert.equal(Number(prop(prop(n.value, "position"), "x")), 0);
        assert.equal(Number(prop(prop(n.value, "position"), "y")), 0);
        assert.deepEqual(spriteDimensions(sprites, prop(n.value, "quadTextureSprite")), {w: 1000, h: 700});
        assert.equal(effects[prop(n.value, "name") + "_click"], undefined, "Background must have no gameplay command");
        assert.equal(triggers[prop(n.value, "name") + "_visible"], undefined, "Input guards must always cover the open window");
        assert.equal(triggers[prop(n.value, "name") + "_click_enabled"], undefined, "Input guards must not be disabled");
    }
    for (const n of children.filter(n => n.key === "buttonType" && !shields.includes(n))) {
        assert(children.indexOf(n) > children.indexOf(shields[1]), prop(n.value, "name") + ": shield obscures control");
        assert(effects[prop(n.value, "name") + "_click"], prop(n.value, "name") + ": missing click handler");
    }
    const nativeShield = fs.readFileSync(path.join(eaw, "interface/eaw_intelligence_agency_blocker.gui"), "utf8");
    assert(nativeShield.includes("two buttons to capture the click"));
    for (let n = 1; n <= 4; n++) {
        const tab = children.find(b => prop(b.value, "name") === "HSM_BAR_archive_doc_" + n);
        assert(tab); assert(children.indexOf(tab) > children.indexOf(shields[1]));
        assert.equal(Number(prop(prop(tab.value, "position"), "x")), 350 + 153 * (n - 1));
        assert.equal(Number(prop(prop(tab.value, "position"), "y")), 260);
        assert.deepEqual(spriteDimensions(sprites, prop(tab.value, "quadTextureSprite")), {w: 141, h: 34});
    }
    const attachment = children.find(b => prop(b.value, "name") === "HSM_BAR_archive_doc_5");
    assert(attachment); assert(children.indexOf(attachment) > children.indexOf(shields[1]));
    assert.deepEqual(spriteDimensions(sprites, prop(attachment.value, "quadTextureSprite")), {w: 36, h: 36});
    assert.equal(Number(prop(prop(attachment.value, "position"), "x")), 204);
    assert.equal(Number(prop(prop(attachment.value, "position"), "y")), 548);
    assert.equal(prop(attachment.value, "pdx_tooltip"), "HSM_BAR_archive_photos_tt");
    const close = children.find(b => prop(b.value, "name") === "HSM_BAR_archive_close");
    assert.equal(prop(close.value, "shortcut"), "ESCAPE");
});
test("resolved mod/native texture bounds and EN/RU bitmap-font advances fit the layout", () => {
    const {sprites, fonts: definitions} = archiveAssets();
    const dimensions = name => spriteDimensions(sprites, name);
    const fonts = {};
    function font(name, lang) {
        const key = name + lang; if (fonts[key]) return fonts[key];
        const chosen = fontDefinition(definitions, name, lang);
        const advances = new Map(); let lineHeight = 0;
        for (const {value} of prop(chosen, "fontfiles")) {
            const fnt = fs.readFileSync(resolveAsset(value + ".fnt"), "utf8");
            lineHeight = Math.max(lineHeight, Number(fnt.match(/common lineHeight=(\d+)/)[1]));
            for (const m of fnt.matchAll(/^char id=(\d+)\s+.*?xadvance=(-?\d+)/gm)) {
                if (!advances.has(Number(m[1]))) advances.set(Number(m[1]), Number(m[2]));
            }
        }
        const colors = new Set((prop(chosen, "textcolors") || []).map(n => n.key));
        return fonts[key] = {lineHeight, width(text) {
            return (text.match(/§.|£[^£]+£|./gu) || []).reduce((n, ch) => {
                if (ch.startsWith("§")) {
                    assert(ch[1] === "!" || colors.has(ch[1]), `${key}: unsupported text color ${ch}`); return n;
                }
                if (ch.startsWith("£")) {
                    assert(ch.length > 2 && ch.endsWith("£"), "Unclosed inline sprite: " + ch);
                    const icon = dimensions("GFX_" + ch.slice(1, -1));
                    assert(icon.h <= lineHeight, `${key}: inline sprite too tall`); return n + icon.w;
                }
                const advance = advances.get(ch.codePointAt(0)); assert.notEqual(advance, undefined, `${key}: missing glyph ${ch}`); return n + advance;
            }, 0);
        }};
    }
    for (const top of gui) {
        const size = prop(top.value, "size");
        for (const n of top.value.filter(n => ["buttonType", "instantTextboxType"].includes(n.key))) {
            const b = n.value, pos = prop(b, "position"), x = Number(prop(pos, "x")), y = Number(prop(pos, "y"));
            const explicitSize = prop(b, "size");
            const box = n.key === "buttonType" ? explicitSize ? {w: Number(prop(explicitSize, "x")), h: Number(prop(explicitSize, "y"))} : dimensions(prop(b, "quadTextureSprite")) : {w: Number(prop(b, "maxWidth")), h: Number(prop(b, "maxHeight"))};
            if (size) assert(x + box.w <= Number(prop(size, "width")) && y + box.h <= Number(prop(size, "height")), prop(b, "name"));
            else assert(x + box.w <= 420, "Archive launcher overlaps native EaW welcome button at x=420");
            const text = prop(b, "text") || prop(b, "buttonText"); if (!text) continue;
            const keys = text.startsWith("[") ? texts[text.slice(1, -1)].map(v => prop(v, "localization_key")) : [text];
            for (let lang = 0; lang < 2; lang++) {
                const metrics = font(prop(b, "font") || prop(b, "buttonFont"), ["english", "russian"][lang]);
                for (const key of keys) {
                    const text = expanded(locales[lang].get(key), lang), width = box.w - (n.key === "buttonType" ? 16 : 0);
                    if (n.key === "buttonType") assert(metrics.width(text) <= width, key + ": button label too wide");
                    else {
                        let lines = 0;
                        for (const paragraph of text.split("\\n")) {
                            let used = 0; lines++;
                            for (const word of paragraph.split(/\s+/)) {
                                assert(metrics.width(word) <= width, key + ": word overflows");
                                const next = metrics.width((used ? " " : "") + word);
                                if (used + next > width) { lines++; used = metrics.width(word); } else used += next;
                            }
                        }
                        if (!prop(b, "scrollbartype")) assert(lines * metrics.lineHeight <= box.h, `${key}: ${lines * metrics.lineHeight}px text exceeds ${box.h}px height`);
                    }
                }
            }
        }
    }
});
module.exports = {parse, prop, read, gui, scripts, window, launcher, triggers, effects, texts, helpers, locales,
    cases, copyCases, archiveVariables, handoffVariables, regions, regionalCases, caseRows, locate, fresh, condition, validateCondition, run, textKey, widgetVisible, visiblePhotos, open, walk, refresh};
if (require.main === module) {
console.log(`Barrad archive: ${passed} scenario groups passed, ${failed} failed; 18 cases, 53 base documents + 36 copies + founding memorandum, separate outcome panel, 12 gated photo attachments, EN/RU.`);
console.log("Static/fixture validation only. In-game rendering, UI scaling and live click handling require a playtest.");
if (failed) process.exitCode = 1;
}
