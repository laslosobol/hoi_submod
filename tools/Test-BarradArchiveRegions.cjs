"use strict";
// Parsed production contracts and synthetic player state; not native UI acceptance.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const {parse: parseGameplay} = require("./Test-BarradCases.cjs");
const {parse, prop, read, gui, triggers, effects, helpers, texts, cases, archiveVariables,
    fresh, open, run, condition, textKey, visiblePhotos, widgetVisible, walk, refresh} = require("./Test-BarradArchive.cjs");
const prefix = "HSM_BAR_archive_";
const names = ["local", "equus", "griffonia", "north", "riverlands", "zebrica"];
const membership = [["rock", "titan", "entity", "amulet", "reactor", "echo", "compass", "plants"],
    ["sombra", "darkheart", "crown"], ["grover", "herald", "crown"], ["rosa", "chalice", "phylactery"],
    ["marsh"], ["zebrica", "crown"]];
const allCases = [...cases, "zebrica"];
const testCall = name => parse(name + " = yes");
const click = (s, name) => run(effects[prefix + name + "_click"], s);
const enabled = (s, name) => condition(triggers[prefix + name + "_click_enabled"], s);
const pageFor = (region, c) => region === 1 && membership[0].indexOf(c) >= 4 ? 2 : 1;
const listed = s => allCases.filter(c => condition(testCall(prefix + "case_" + c + "_listed"), s));
function fixture(region = 1, c, stage = "known") {
    const s = fresh(); open(s);
    s.vars[prefix + "region"] = region;
    s.vars[prefix + "page"] = pageFor(region, c);
    s.vars[prefix + "document"] = 1;
    if (c) {
        s.vars[prefix + "case"] = allCases.indexOf(c) + 1;
        s.flags.add(stage === "studied" ? `HSM_BAR_study_${c}_done` : `HSM_BAR_case_${c}_${stage}`);
    }
    return s;
}
function gameplay(s) {
    const clone = structuredClone(s);
    delete clone.operationsRefreshRequests;
    for (const key of Object.keys(clone.vars)) if (archiveVariables.has(key)
        || ["HSM_BAR_service_gui_open", "HSM_BAR_service_gui_region", "HSM_BAR_fielddesk_open", "HSM_BAR_investigation_open"].includes(key)) delete clone.vars[key];
    return clone;
}
function seedGameplay(s) {
    s.vars.political_power = 173;
    s.vars.HSM_BAR_research_budget = 41;
    s.flags.add("HSM_BAR_case_crown_exists");
    s.access.add("HSM_BAR_cases_crown_access");
    return gameplay(s);
}
function closedSelection(s) {
    assert.equal(textKey("GetHSMBARArchiveBody", s), prefix + "locked");
    for (const [getter, fallback] of [["Title", "no_selection"], ["Classification", "class_none"],
        ["Access", "access_none"], ["PhotoCaption", "photo_unavailable"]])
        assert.equal(textKey("GetHSMBARArchive" + getter, s), prefix + fallback);
    assert.deepEqual(visiblePhotos(s), []);
    for (const name of ["copy_1", "copy_2", "copy_3", "audio_echo", "audio_entity", "audio_reactor"])
        assert(!widgetVisible(prefix + name, s), name);
    for (const name of ["doc_1", "doc_2", "doc_3", "doc_4", "doc_5", "copy_1", "copy_2", "copy_3"]) {
        assert(!enabled(s, name), name);
        const before = structuredClone(s); click(s, name); assert.deepEqual(s, before);
    }
}
let passed = 0, failed = 0;
function test(name, fn) {
    try { fn(); passed++; console.log("PASS " + name); }
    catch (error) { failed++; console.error("FAIL " + name + "\n" + error.stack); }
}

test("six region IDs and all 18 dossiers match authored regional sources", () => {
    assert.equal(new Set(membership.flat()).size, 18);
    const rumours = parse(read("common/decisions/HSM_BAR_cases_rumors.txt"));
    for (const [i, name] of names.entries()) {
        const category = prop(rumours, "HSM_BAR_cases_" + name);
        assert(Array.isArray(category), name);
        for (const decision of category) {
            assert(decision.key.startsWith("HSM_BAR_rumor_"));
            const c = decision.key.replace("HSM_BAR_rumor_", "").replace(/_equus$|_griffonia$|_zebrica$/, "");
            assert(membership[i].includes(c), decision.key);
        }
    }
    const producers = new Set();
    for (const file of ["common/national_focus/HSM_BAR_directorate.txt", "common/scripted_effects/HSM_BAR_phases.txt"])
        walk(parseGameplay(read(file)), n => { if (n.key === "set_country_flag") producers.add(n.value); });
    for (const name of names) assert(producers.has("HSM_BAR_region_" + name + "_open"));
    const s = fixture();
    for (const c of allCases) s.flags.add(`HSM_BAR_case_${c}_known`);
    for (let region = 1; region <= 6; region++) for (const page of [1, 2, 3, 0, 99]) {
        s.vars[prefix + "region"] = region; s.vars[prefix + "page"] = page;
        const expected = membership[region - 1].filter(c => pageFor(region, c) === page);
        assert.deepEqual(listed(s).sort(), expected.toSorted(), `${region}/${page}`);
    }
});

test("new archive defaults to Local; only actual branch flags enable empty foreign tabs", () => {
    const s = fresh(); s.vars.HSM_BAR_service_gui_open = 1; open(s);
    assert.equal(s.vars[prefix + "region"], 1); assert.equal(s.vars[prefix + "page"], 1);
    assert.equal(s.vars.HSM_BAR_service_gui_open, undefined);
    assert.equal(textKey("GetHSMBARArchiveBody", s), prefix + "inaugural");
    for (let region = 1; region <= 6; region++) assert.equal(enabled(s, "region_" + region), region === 1);
    for (let region = 2; region <= 6; region++) {
        const before = structuredClone(s); click(s, "region_" + region); assert.deepEqual(s, before);
        s.flags.add("HSM_BAR_region_" + names[region - 1] + "_open");
        assert(enabled(s, "region_" + region)); click(s, "region_" + region);
        assert.deepEqual(listed(s), []); assert.equal(s.vars[prefix + "region"], region);
    }
});

for (let region = 1; region <= 6; region++) test(names[region - 1] + ": retained evidence opens only its real historical index", () => {
    for (const c of membership[region - 1]) for (const stage of c === "zebrica" ? ["known"] : ["known", "investigated", "studied"]) {
        const s = fixture(region, c, stage);
        if (c === "crown") s.flags.add("HSM_BAR_region_" + names[region - 1] + "_open");
        const before = seedGameplay(s);
        assert(enabled(s, "region_" + region));
        const actual = listed(s); assert.deepEqual(actual, [c]);
        click(s, "case_" + c);
        assert.equal(textKey("GetHSMBARArchiveBody", s), prefix + c + "_intake");
        assert.deepEqual(gameplay(s), before);
        for (let other = 2; other <= 6; other++)
            assert.equal(enabled(s, "region_" + other), c === "crown" ? other === region : membership[other - 1].includes(c), c + "/" + other);
    }
});

test("global existence, custody, live access and other case evidence cannot disclose unknown cases", () => {
    for (let region = 1; region <= 6; region++) {
        const s = fixture(region);
        for (const c of allCases) {
            s.flags.add(`HSM_BAR_case_${c}_exists`); s.flags.add(`HSM_BAR_case_${c}_secured`);
            s.access.add(`HSM_BAR_cases_${c}_access`);
        }
        assert.deepEqual(listed(s), []);
        for (let other = 2; other <= 6; other++) assert(!enabled(s, "region_" + other));
        for (const c of allCases) { const before = structuredClone(s); click(s, "case_" + c); assert.deepEqual(s, before); }
    }
});

test("all six tabs reset stale selection, editions and local pagination without gameplay writes", () => {
    for (let region = 1; region <= 6; region++) {
        const s = fixture(1, "reactor", "studied"), before = seedGameplay(s);
        s.flags.add("HSM_BAR_region_" + names[region - 1] + "_open");
        const expected = gameplay(s);
        s.vars[prefix + "copy"] = 3; s.vars[prefix + "document"] = 5;
        click(s, "region_" + region);
        assert.equal(s.vars[prefix + "region"], region); assert.equal(s.vars[prefix + "page"], 1);
        for (const key of ["case", "copy", "document"]) assert.equal(s.vars[prefix + key], undefined);
        assert.deepEqual(gameplay(s), expected); assert.equal(before.vars.political_power, 173);
    }
    const revocations = [s => s.tag = "EQS", s => s.ai = true, s => delete s.vars[prefix + "open"],
        ...["active", "directorate", "service_founded", "region_local_open"].map(f => s => s.flags.delete("HSM_BAR_" + f))];
    for (const revoke of revocations) for (let region = 1; region <= 6; region++) {
        const s = fixture(); s.flags.add("HSM_BAR_region_" + names[region - 1] + "_open"); revoke(s);
        assert(!enabled(s, "region_" + region)); const before = structuredClone(s);
        click(s, "region_" + region); assert.deepEqual(s, before);
    }
});

test("pagination is strictly Local 1..2; foreign and malformed pages cannot spill dossiers", () => {
    for (let region = 1; region <= 6; region++) for (const page of [0, 1, 2, 3, 99]) {
        const s = fixture(region); s.vars[prefix + "page"] = page;
        assert.equal(enabled(s, "prev"), region === 1 && page === 2);
        assert.equal(enabled(s, "next"), region === 1 && page === 1);
        for (const action of ["prev", "next"]) if (!enabled(s, action)) {
            const before = structuredClone(s); click(s, action); assert.deepEqual(s, before);
        }
    }
});

test("Crown is one shared historical cross-reference in 2/3/6, never a fabricated regional specimen", () => {
    const s = fixture(2, "crown", "rumor");
    for (let region = 2; region <= 6; region++) assert(!enabled(s, "region_" + region));
    closedSelection(s);
    for (const region of [2, 3, 6]) {
        s.flags.add("HSM_BAR_region_" + names[region - 1] + "_open");
        const before = seedGameplay(s);
        click(s, "region_" + region); assert.deepEqual(listed(s), ["crown"]);
        click(s, "case_crown"); assert.equal(textKey("GetHSMBARArchiveBody", s), prefix + "crown_intake");
        assert(!enabled(s, "doc_2")); assert(!enabled(s, "doc_5"));
        assert.deepEqual(gameplay(s), before);
    }
    for (const region of [1, 4, 5]) {
        s.vars[prefix + "region"] = region;
        assert.deepEqual(listed(s), []); closedSelection(s);
    }
    const widgets = gui.find(n => prop(n.value, "name") === prefix + "window").value;
    const crown = widgets.find(n => Array.isArray(n.value) && prop(n.value, "name") === prefix + "case_crown").value;
    assert.equal(prop(crown, "pdx_tooltip"), prefix + "crown_crossref_tt");
    assert.equal(prop(crown, "buttonText"), prefix + "crown_crossref_title");
});

test("generic Crown history cannot unlock never-opened branches; opened indexes survive custody/access loss", () => {
    for (const stage of ["rumor", "known", "investigated", "studied"]) for (const region of [2, 3, 6]) {
        const s = fixture(region, "crown", stage);
        for (let other = 2; other <= 6; other++) assert(!enabled(s, "region_" + other));
        assert.deepEqual(listed(s), []); closedSelection(s);
        s.flags.add("HSM_BAR_region_" + names[region - 1] + "_open");
        s.access.clear(); s.flags.delete("HSM_BAR_case_crown_secured");
        assert(enabled(s, "region_" + region)); assert.deepEqual(listed(s), ["crown"]);
        assert.equal(textKey("GetHSMBARArchiveBody", s), prefix + "crown_intake");
    }
    // Source branch flags are persistent mandates, not current territorial access.
    const mod = path.resolve(__dirname, "../mod/HoISubmod");
    function scan(dir) {
        for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
            const file = path.join(dir, entry.name);
            if (entry.isDirectory()) scan(file);
            else if (/^HSM_BAR_.*\.txt$/i.test(entry.name)) walk(parseGameplay(fs.readFileSync(file, "utf8")), n => {
                if (n.key === "clr_country_flag") assert(!/^HSM_BAR_region_(equus|griffonia|zebrica)_open$/.test(n.value),
                    "Branch-history lifecycle changed; preserve archive access explicitly: " + file);
            });
        }
    }
    scan(path.join(mod, "common")); scan(path.join(mod, "events"));
});

test("forged region/page selections independently suppress prose, metadata, results, plates, copies and audio", () => {
    for (const c of allCases) for (let region = 1; region <= 6; region++) for (const page of [1, 2, 99]) {
        if (membership[region - 1].includes(c) && page === pageFor(region, c)) continue;
        const s = fixture(region, c, c === "zebrica" ? "known" : "studied");
        s.vars[prefix + "page"] = page; s.vars[prefix + "copy"] = 3;
        for (const doc of [1, 2, 3, 4, 5]) { s.vars[prefix + "document"] = doc; closedSelection(s); }
    }
});

test("Operations copies region, opens console, refreshes once and closes archive in that order", () => {
    const body = prop(effects[prefix + "operations_click"], "if");
    assert.deepEqual(body, parse(`limit = { HSM_BAR_archive_operations_available = yes }
        clear_variable = HSM_BAR_fielddesk_open
        clear_variable = HSM_BAR_investigation_open
        set_variable = { HSM_BAR_service_gui_region = HSM_BAR_archive_region }
        set_variable = { HSM_BAR_service_gui_open = 1 } HSM_BAR_service_gui_refresh = yes
        clear_variable = HSM_BAR_archive_open clear_variable = HSM_BAR_archive_case
        clear_variable = HSM_BAR_archive_document clear_variable = HSM_BAR_archive_copy`));
    for (let region = 1; region <= 6; region++) {
        const s = fixture(region, membership[region - 1][0]); s.vars[prefix + "copy"] = 3;
        s.vars.HSM_BAR_fielddesk_open = 1;
        const before = seedGameplay(s); assert(enabled(s, "operations")); click(s, "operations");
        assert.equal(s.vars.HSM_BAR_service_gui_region, region); assert.equal(s.vars.HSM_BAR_service_gui_open, 1);
        assert.equal(s.operationsRefreshRequests, 1);
        assert.equal(s.vars.HSM_BAR_fielddesk_open, undefined);
        for (const key of ["open", "case", "document", "copy"]) assert.equal(s.vars[prefix + key], undefined);
        assert.deepEqual(gameplay(s), before);
    }
});

test("archive launcher closes operational windows permanently; their presentation variables are clear-only", () => {
  for (const window of ["HSM_BAR_fielddesk_open", "HSM_BAR_investigation_open"]) {
    const s = fresh();
    s.vars[window] = 1;
    s.vars.HSM_BAR_fielddesk_page = 3;
    const before = seedGameplay(s);
    open(s); assert.equal(s.vars[window], undefined);
    click(s, "close"); assert.equal(s.vars[window], undefined);
    assert.deepEqual(gameplay(s), before);
    for (const effect of ["set_variable", "add_to_variable", "subtract_from_variable"])
        assert.throws(() => run(parse(`${effect} = { ${window} = 1 }`), s));
    assert.throws(() => condition(parse(`has_variable = ${window}`), s));
  }
});

test("Operations honors the real main-console actor gate and rejects invalid or unopened regions", () => {
    const invalid = [s => s.tag = "EQS", s => s.ai = true, s => s.subject = true, s => s.capitulated = true,
        s => s.controlsCapital = false, s => delete s.vars[prefix + "open"],
        ...["active", "directorate", "service_founded"].map(f => s => s.flags.delete("HSM_BAR_" + f)),
        ...[undefined, -1, 0, 2, 7, 99].map(region => s => s.vars[prefix + "region"] = region)];
    for (const revoke of invalid) {
        const s = fixture(); s.vars.HSM_BAR_fielddesk_open = 1; revoke(s); assert(!enabled(s, "operations"));
        const before = structuredClone(s); click(s, "operations"); assert.deepEqual(s, before);
    }
});

test("main reverse link invokes archive normalization after copying subject/region and opening", () => {
    const scripts = prop(parseGameplay(read("common/scripted_guis/HSM_BAR_service_gui.txt")), "scripted_gui");
    const window = prop(scripts, "HSM_BAR_service_gui_window");
    const callback = prop(prop(window, "effects"), "HSM_BAR_service_gui_archive_click");
    const body = prop(callback, "if");
    assert.deepEqual(prop(body, "limit"), testCall("HSM_BAR_service_gui_available"));
    const writes = body.filter(n => n.key === "set_variable");
    assert(writes.some(n => prop(n.value, prefix + "region") === "HSM_BAR_service_gui_region"));
    assert(writes.some(n => prop(n.value, prefix + "case") === "HSM_BAR_service_gui_subject"));
    assert(writes.some(n => prop(n.value, prefix + "open") === "1"));
    assert(body.some(n => n.key === "clear_variable" && n.value === "HSM_BAR_service_gui_open"));
    assert.deepEqual(body.at(-1), testCall("HSM_BAR_archive_refresh")[0]);
    assert.equal(body.filter(n => n.key === "HSM_BAR_archive_refresh").length, 1);
});

test("deep-link refresh validates every region/subject, fixes Local page 2 and returns stale selections to office", () => {
    for (let region = 1; region <= 6; region++) for (let subject = 0; subject <= 19; subject++) {
        const s = fixture(region), c = allCases[subject - 1];
        s.flags.add("HSM_BAR_region_" + names[region - 1] + "_open");
        for (const name of allCases) s.flags.add(`HSM_BAR_case_${name}_known`);
        s.vars[prefix + "case"] = subject; s.vars[prefix + "page"] = 1;
        s.vars[prefix + "copy"] = 3; s.vars[prefix + "document"] = 5;
        const before = seedGameplay(s); run(testCall("HSM_BAR_archive_refresh"), s);
        const valid = membership[region - 1].includes(c);
        assert.equal(s.vars[prefix + "case"], valid ? subject : undefined);
        assert.equal(s.vars[prefix + "page"], valid ? pageFor(region, c) : 1);
        assert.equal(s.vars[prefix + "document"], 1); assert.equal(s.vars[prefix + "copy"], undefined);
        assert.equal(textKey("GetHSMBARArchiveBody", s), prefix + (valid ? c + "_intake" : "inaugural"));
        assert.deepEqual(gameplay(s), before);
        const stable = structuredClone(s); run(refresh, s); assert.deepEqual(s, stable);
    }
});

test("deep-link refresh cannot turn unknown evidence or invalid actors into a dossier", () => {
    for (let region = 1; region <= 6; region++) for (const c of membership[region - 1]) {
        const s = fixture(region); s.vars[prefix + "case"] = allCases.indexOf(c) + 1;
        run(refresh, s); assert.equal(s.vars[prefix + "case"], undefined);
        assert.equal(s.vars[prefix + "region"], 1); assert.equal(textKey("GetHSMBARArchiveBody", s), prefix + "inaugural");
    }
    for (const region of [undefined, -1, 0, 7, 99]) {
        const s = fixture(1, "rock"); s.vars[prefix + "region"] = region;
        run(refresh, s); assert.equal(s.vars[prefix + "region"], 1); assert.equal(s.vars[prefix + "case"], undefined);
    }
    for (const revoke of [s => s.tag = "EQS", s => s.ai = true, s => delete s.vars[prefix + "open"],
        s => s.flags.delete("HSM_BAR_service_founded")]) {
        const s = fixture(1, "rock"); revoke(s); const before = structuredClone(s); run(refresh, s); assert.deepEqual(s, before);
    }
    function validate(nodes) {
        for (const n of nodes) {
            if (n.key === "if") {
                condition(prop(n.value, "limit"), fixture()); validate(n.value.filter(x => x.key !== "limit"));
            } else if (n.key === "clear_variable") assert(archiveVariables.has(n.value));
            else { assert.equal(n.key, "set_variable"); assert.equal(n.value.length, 1);
                assert(archiveVariables.has(n.value[0].key)); assert(Number.isFinite(Number(n.value[0].value))); }
        }
    }
    validate(refresh);
});

test("all case-bound getters and click predicates retain their own regional guard", () => {
    function validate(nodes) {
        for (const n of nodes) if (n.key === "check_variable" && prop(n.value, prefix + "case") !== undefined) {
            const id = Number(prop(n.value, prefix + "case"));
            if (id === 0) continue; // Office memorandum, never a dossier.
            assert.equal(prop(nodes, prefix + "case_" + allCases[id - 1] + "_listed"), "yes", "Unguarded subject " + id);
        } else if (Array.isArray(n.value)) validate(n.value);
    }
    for (const choices of Object.values(texts)) for (const choice of choices) validate(prop(choice, "trigger") || []);
    for (const nodes of [...Object.values(triggers), ...Object.values(effects)]) validate(nodes);
});

test("historical text and captions retain both frozen pre-region language snapshots", () => {
    const digests = {english: "230d5e3450cac738f4f6e7d2d2d66619f9f2508195f52d3a3ccf0c33f92576f0",
        russian: "694767993058994cc1cef88a559006d8bf67c6998c1be97aa670b04ff343df94"};
    for (const [language, digest] of Object.entries(digests)) {
        const dir = path.resolve(__dirname, "../mod/HoISubmod/localisation", language);
        const lines = fs.readdirSync(dir).filter(f => /^HSM_BAR_archive.*\.yml$/.test(f))
            .flatMap(f => fs.readFileSync(path.join(dir, f), "utf8").split(/\r?\n/))
            .filter(line => /^ HSM_BAR_archive_\w*(?:_(?:intake|field|study|closure|results|caption)(?:_(?:restricted|sealed))?|_inaugural):0 /.test(line)).sort();
        assert.equal(lines.length, 122);
        assert.equal(crypto.createHash("sha256").update(lines.join("\n")).digest("hex"), digest, language);
    }
});

test("six fixed region controls select correctly; strict fixtures still reject unknown commands", () => {
    const selectors = parse(read("common/scripted_localisation/HSM_BAR_archive_skin.txt"));
    const widgets = gui.find(n => prop(n.value, "name") === prefix + "window").value;
    for (let region = 1; region <= 6; region++) {
        const w = widgets.find(n => Array.isArray(n.value) && prop(n.value, "name") === prefix + "region_" + region);
        assert.equal(w.key, "buttonType");
        assert.deepEqual(prop(w.value, "position"), parse(`x = ${24 + (region - 1) * 153} y = 64`));
        const selector = selectors.find(n => prop(n.value, "name") === `GetHSMBARArchiveRegion${region}Skin`);
        for (const selected of [undefined, 0, 1, 2, 3, 4, 5, 6, 99]) {
            const s = fixture(); s.vars[prefix + "region"] = selected;
            const entry = selector.value.filter(n => n.key === "text").find(n => condition(prop(n.value, "trigger") || [], s));
            assert.equal(prop(entry.value, "localization_key"), "GFX_" + prefix + "tab" + (selected === region ? "_selected" : ""));
        }
    }
    for (const source of ["OR = { tag = BAR invented_read = yes }", "HSM_BAR_archive_selection_available = maybe"])
        assert.throws(() => condition(parse(source), fixture()));
    assert.throws(() => run(parse("set_country_flag = HSM_BAR_case_crown_secured"), fixture()));
    assert.throws(() => run(parse("HSM_BAR_archive_invented_refresh = yes"), fixture()));
});

console.log(`Barrad archive regions: ${passed} scenario groups passed, ${failed} failed; six branches, 18 dossiers, guarded console handoff.`);
console.log("Static state/layout contracts only. Native rendering, scrolling and clicks still require a game playtest.");
if (failed) process.exitCode = 1;
