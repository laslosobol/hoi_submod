"use strict";
// Run: node tools/Test-BarradArchiveCopies.cjs
// Real parsed contracts with synthetic country state, not an HOI4 emulator.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const {parse, prop, read, gui, scripts, window, launcher, triggers, effects, texts, helpers, locales,
    cases, copyCases, archiveVariables, fresh, condition, validateCondition, run, textKey,
    widgetVisible, visiblePhotos, open, locate, handoffVariables} = require("./Test-BarradArchive.cjs");
const prefix = "HSM_BAR_archive_", copyVar = prefix + "copy";
const helperName = "HSM_BAR_archive_copies_available", helperCall = parse(helperName + " = yes");
const stages = ["intake", "field", "study"], copies = [undefined, -1, 0, 1, 2, 3, 4, 999];
const suffix = copy => copy === 2 ? "_restricted" : copy === 3 ? "_sealed" : "";
const body = texts.GetHSMBARArchiveBody, keyOf = block => prop(block, "localization_key");
const isVariant = key => /_(intake|field|study)_(restricted|sealed)$/.test(key);
const variants = [...copyCases].flatMap(c => stages.flatMap(stage => ["restricted", "sealed"].map(copy => `${prefix}${c}_${stage}_${copy}`)));
const digest = value => crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
// Preserve the pre-region document snapshot, allowing only the added regional guard
// and the operations office's explicit zero selection to behave like no selection.
function beforeRegions(nodes) {
    return nodes.filter(n => !/^HSM_BAR_archive_case_\w+_listed$/.test(n.key)).map(n => {
        if (n.key === "OR" && n.value.length === 2 && n.value[0].key === "NOT"
            && prop(n.value[0].value, "has_variable") === prefix + "case"
            && prop(n.value[1].value, prefix + "case") === "0") return n.value[0];
        return {...n, value: Array.isArray(n.value) ? beforeRegions(n.value) : n.value};
    });
}
function originalClickSnapshot(name, nodes) {
    const navigation = /HSM_BAR_archive_(prev|next)_click/.exec(name);
    return nodes.flatMap(n => {
        if (name === prefix + "open_click" && n.key === "clear_variable" && ["HSM_BAR_fielddesk_open", "HSM_BAR_investigation_open"].includes(n.value)) return [];
        if ((n.key === "clear_variable" && [prefix + "region", "HSM_BAR_service_gui_open"].includes(n.value))
            || n.key === "set_variable" && prop(n.value, prefix + "region") !== undefined) return [];
        const listed = /^HSM_BAR_archive_case_(\w+)_listed$/.exec(n.key);
        if (listed) return /^HSM_BAR_archive_case_\w+_click$/.test(name)
            ? [...parse(`check_variable = { HSM_BAR_archive_page = ${Math.floor([...cases, "zebrica"].indexOf(listed[1]) / 4) + 1} }`), ...helpers[prefix + "history_" + listed[1]]] : [];
        if (navigation && n.key === "limit") return [{...n, value: parse(`check_variable = { HSM_BAR_archive_page ${navigation[1] === "prev" ? "> 1" : "< 5"} }`)}];
        return [{...n, value: Array.isArray(n.value) ? originalClickSnapshot(name, n.value) : n.value}];
    });
}
const selectCopy = (s, copy) => { if (copy === undefined) delete s.vars[copyVar]; else s.vars[copyVar] = copy; };
function fixture(c, doc, flags = []) {
    const s = fresh(); open(s);
    s.vars[prefix + "case"] = [...cases, "zebrica"].indexOf(c) + 1;
    locate(s, c);
    if (doc !== undefined) s.vars[prefix + "document"] = doc;
    for (const flag of flags) s.flags.add(flag === "studied" ? `HSM_BAR_study_${c}_done` : `HSM_BAR_case_${c}_${flag}`);
    return s;
}
function assertControls(s, available, label) {
    assert.equal(condition(helperCall, s), available, label + ": helper");
    for (const copy of [1, 2, 3]) {
        const name = prefix + "copy_" + copy;
        assert.equal(widgetVisible(name, s), available, label + ": visibility");
        assert.equal(condition(triggers[name + "_click_enabled"], s), available, label + ": enabled");
        const actual = structuredClone(s), expected = structuredClone(s);
        if (available) expected.vars[copyVar] = copy;
        run(effects[name + "_click"], actual);
        assert.deepEqual(actual, expected, label + ": gated click may only set copy");
    }
}
let passed = 0, failed = 0;
function test(name, fn) {
    try { fn(); passed++; console.log("PASS " + name); }
    catch (error) { failed++; console.error("FAIL " + name + "\n" + error.stack); }
}

test("strict evaluator rejects unknown commands in unreachable branches and scripted helpers", () => {
    const s = fresh(); open(s);
    for (const source of ["tag = EQS invented_permission = yes", "OR = { tag = BAR invented_permission = yes }",
        "HSM_BAR_archive_other_helper = yes", "check_variable = { HSM_BAR_secrecy = 3 }",
        "check_variable = { HSM_BAR_archive_copy != 2 }", "HSM_BAR_archive_copies_available = maybe"])
        assert.throws(() => condition(parse(source), s), undefined, source);
    for (const source of ["add_political_power = 1", "set_variable = { HSM_BAR_archive_secrecy = 3 }"])
        assert.throws(() => run(parse(source), s));
    const original = helpers[helperName];
    try {
        helpers[helperName] = parse("tag = EQS invented_permission = yes");
        assert.throws(() => condition(helperCall, s), /Unknown trigger/);
        helpers[helperName] = helperCall;
        assert.throws(() => condition(helperCall, s), /Recursive scripted trigger/);
    } finally { helpers[helperName] = original; }
});

test("36 variants retain original disclosure guards and row order beneath regional guards", () => {
    const baseRows = body.filter(block => !isVariant(keyOf(block)));
    // Frozen before the copy implementation, including row order and every original guard.
    assert.equal(digest(baseRows.map(value => ({key: "text", op: "=", value: beforeRegions(value)}))),
        "ba9491920da133a266dcb4a0afd1cca89a1d215eda6af74fd5c389dff5653d07", "Original body dispatch changed");
    assert.deepEqual(body.filter(block => isVariant(keyOf(block))).map(keyOf).sort(), variants.toSorted());
    for (const c of copyCases) for (const stage of stages) {
        const baseKey = `${prefix}${c}_${stage}`, index = body.findIndex(block => keyOf(block) === baseKey);
        assert(index >= 2, baseKey);
        const guard = prop(body[index], "trigger");
        assert.deepEqual(body.slice(index - 2, index).map(keyOf).sort(), [baseKey + "_restricted", baseKey + "_sealed"]);
        for (const copy of [2, 3]) {
            const variant = body.find(block => keyOf(block) === baseKey + suffix(copy)), variantGuard = prop(variant, "trigger");
            const selection = variantGuard.filter(n => n.key === "check_variable" && prop(n.value, copyVar) !== undefined);
            assert.deepEqual(selection, parse(`check_variable = { ${copyVar} = ${copy} }`), baseKey + suffix(copy));
            assert.deepEqual(variantGuard.filter(n => !selection.includes(n)), guard, baseKey + ": changed original guard");
            assert.deepEqual(variant.filter(n => n.key !== "trigger"), parse(`localization_key = ${baseKey}${suffix(copy)}`));
        }
    }
});

test("helper has the full window gate and exactly 18 actual case/stage guards; buttons use it exclusively", () => {
    assert.deepEqual(parse(read("common/scripted_triggers/HSM_BAR_archive_copies.txt")).map(n => n.key), [helperName]);
    const helper = helpers[helperName]; validateCondition(helper);
    const choices = helper.filter(n => n.key === "OR"); assert.equal(choices.length, 1);
    assert.deepEqual(helper.filter(n => n.key !== "OR"), prop(window, "visible"));
    assert.equal(choices[0].value.length, 18);
    const guards = body.filter(block => [...copyCases].some(c => stages.some(stage => keyOf(block) === `${prefix}${c}_${stage}`)))
        .map(block => ({key: "AND", op: "=", value: prop(block, "trigger")}));
    assert.deepEqual(choices[0].value, guards, "Helper must retain each document's actual release guard");
    for (const copy of [1, 2, 3]) {
        const name = prefix + "copy_" + copy;
        assert.deepEqual(triggers[name + "_visible"], helperCall);
        assert.deepEqual(triggers[name + "_click_enabled"], helperCall);
        assert.deepEqual(effects[name + "_click"], parse(`if = { limit = { ${helperName} = yes } set_variable = { ${copyVar} = ${copy} } }`));
    }
});

for (const c of copyCases) test(c + ": dispatch and clicks respect every knowledge combination, stage and copy", () => {
    const flags = ["known", "investigated", "studied", "rumor"];
    for (let mask = 0; mask < 16; mask++) for (const doc of [undefined, -1, 0, 1, 2, 3, 4, 5, 6, 999]) {
        const stateFlags = flags.filter((_, i) => mask & (1 << i));
        const level = stateFlags.includes("studied") ? 3 : stateFlags.includes("investigated") ? 2
            : stateFlags.includes("known") || c === "crown" && stateFlags.includes("rumor") ? 1 : 0;
        const available = Number.isInteger(doc) && doc >= 1 && doc <= Math.min(3, level);
        const s = fixture(c, doc, stateFlags), label = `${c}, flags ${stateFlags}, doc ${doc}`;
        assertControls(s, available, label);
        const metadata = ["GetHSMBARArchiveTitle", "GetHSMBARArchiveClassification", "GetHSMBARArchiveAccess", "GetHSMBARArchiveRecordNote"];
        const originalMetadata = metadata.map(name => textKey(name, s));
        for (const copy of copies) {
            selectCopy(s, copy);
            const expected = available ? `${prefix}${c}_${stages[doc - 1]}${suffix(copy)}`
                : doc === 4 && level ? `${prefix}${c}_results` : prefix + "locked";
            assert.equal(textKey("GetHSMBARArchiveBody", s), expected, label + ", copy " + copy);
            assert.deepEqual(metadata.map(name => textKey(name, s)), originalMetadata, label + ": copy changes case type/access");
        }
        if (doc !== 5) assert.equal(widgetVisible(prefix + "document_title", s), !available, label + ": heading");
    }
});

test("wrong-case evidence, custody/world facts and invalid selections cannot release copies", () => {
    for (const target of copyCases) for (const source of cases.filter(c => c !== target)) for (const doc of [1, 2, 3]) {
        const s = fixture(target, doc, ["exists", "secured"]);
        s.flags.add(`HSM_BAR_case_${source}_known`); s.flags.add(`HSM_BAR_case_${source}_investigated`); s.flags.add(`HSM_BAR_study_${source}_done`);
        s.access.add(`HSM_BAR_cases_${target}_access`);
        assertControls(s, false, `${source} evidence on ${target}`);
        for (const copy of [2, 3]) { selectCopy(s, copy); assert.equal(textKey("GetHSMBARArchiveBody", s), prefix + "locked"); }
    }
    for (const id of [undefined, -1, 0, 19, 999]) for (const doc of [1, 2, 3]) {
        const s = fixture("rock", doc, ["studied"]);
        if (id === undefined) delete s.vars[prefix + "case"]; else s.vars[prefix + "case"] = id;
        selectCopy(s, 3); assertControls(s, false, "invalid case " + id);
        assert.equal(textKey("GetHSMBARArchiveBody", s), prefix + (id === undefined || id === 0 ? "inaugural" : "locked"));
    }
});

test("controls independently reject non-BAR, AI, revoked Service/region scope and closed archives", () => {
    const revocations = [s => { s.tag = "EQS"; }, s => { s.ai = true; },
        ...["active", "directorate", "service_founded", "region_local_open"].map(flag => s => s.flags.delete("HSM_BAR_" + flag))];
    for (const c of copyCases) for (const doc of [1, 2, 3]) for (const revoke of revocations) {
        const s = fixture(c, doc, ["studied"]); selectCopy(s, 3); revoke(s);
        assertControls(s, false, c + ": revoked scope"); assert.equal(textKey("GetHSMBARArchiveBody", s), prefix + "locked");
    }
    for (const c of copyCases) {
        const s = fixture(c, 2, ["studied"]); selectCopy(s, 3); delete s.vars[prefix + "open"];
        assertControls(s, false, c + ": closed");
    }
});

test("last recorded documents retain editions after access loss without inventing the next stage", () => {
    for (const c of copyCases) for (const [flag, doc] of [["known", 1], ["investigated", 2], ["studied", 3]]) {
        const s = fixture(c, doc, [flag, "secured"]); s.access.add(`HSM_BAR_cases_${c}_access`);
        s.vars.HSM_BAR_research_budget = 37; s.vars.political_power = 111;
        s.flags.delete(`HSM_BAR_case_${c}_secured`); s.access.clear();
        const before = structuredClone(s);
        for (const copy of [1, 2, 3]) {
            run(effects[prefix + "copy_" + copy + "_click"], s);
            assert.equal(textKey("GetHSMBARArchiveBody", s), `${prefix}${c}_${stages[doc - 1]}${suffix(copy)}`);
            assert.equal(textKey("GetHSMBARArchiveAccess", s), prefix + (doc === 1 ? "access_intake" : "access_unavailable"));
        }
        delete s.vars[copyVar]; assert.deepEqual(s, before);
        if (doc < 3) {
            s.vars[prefix + "document"] = doc + 1;
            assertControls(s, false, c + ": next stage remains locked");
            assert.equal(textKey("GetHSMBARArchiveBody", s), prefix + "locked");
        }
    }
});

test("selection resets on open, every case, page, back and close; document changes retain it", () => {
    for (const copy of [1, 2, 3]) {
        for (const c of [...cases, "zebrica"]) {
            const s = fixture(c, 1, c === "zebrica" ? ["known"] : ["studied"]); selectCopy(s, copy);
            run(effects[prefix + "case_" + c + "_click"], s);
            assert.equal(s.vars[copyVar], undefined, c + ": case reset");
        }
        for (const action of ["prev", "next", "back", "close", "open"]) {
            const s = fixture("reactor", 2, ["studied"]); selectCopy(s, copy);
            if (action === "next") s.vars.HSM_BAR_archive_page = 1;
            if (action === "open") open(s); else run(effects[prefix + action + "_click"], s);
            assert.equal(s.vars[copyVar], undefined, action + ": reset");
        }
        for (const c of copyCases) {
            const s = fixture(c, 1, ["studied"]); selectCopy(s, copy);
            for (const doc of [2, 3, 4, 5, 1]) {
                run(effects[prefix + "doc_" + doc + "_click"], s);
                assert.equal(s.vars[prefix + "document"], doc);
                assert.equal(s.vars[copyVar], copy, c + ": document preserves copy");
                assert.equal(condition(helperCall, s), doc <= 3);
                if (doc === 4) assert(widgetVisible(prefix + "document_title", s), "Results heading remains visible");
                if (doc === 5) assert.deepEqual(visiblePhotos(s), [c]);
            }
        }
    }
    const s = fixture("rock", 1, ["known"]); selectCopy(s, 3);
    for (const doc of [2, 3, 5]) {
        const before = structuredClone(s); run(effects[prefix + "doc_" + doc + "_click"], s); assert.deepEqual(s, before);
    }
    open(s); assert.equal(s.vars[copyVar], undefined);
    run(effects[prefix + "case_rock_click"], s);
    assert.equal(textKey("GetHSMBARArchiveBody", s), prefix + "rock_intake");
});

test("other cases, Results, photos and outcome bonuses are independent of copy selection", () => {
    for (const c of [...cases, "zebrica"]) for (const doc of [1, 2, 3, 4, 5]) {
        if (copyCases.has(c) && doc <= 3) continue;
        const s = fixture(c, doc, ["known", "investigated", "studied", "inconclusive", "closed"]);
        const original = textKey("GetHSMBARArchiveBody", s), photos = visiblePhotos(s);
        for (const copy of copies) {
            selectCopy(s, copy);
            assert.equal(textKey("GetHSMBARArchiveBody", s), original); assert.deepEqual(visiblePhotos(s), photos);
            assertControls(s, false, `${c}, doc ${doc}`);
        }
    }
    // Pre-copy AST snapshots preserve existing Results/bonus dispatch and presentation.
    assert.equal(digest(body.filter(b => /_results$/.test(keyOf(b))).map(value => ({key: "text", op: "=", value: beforeRegions(value)}))),
        "4f84112c79c53dcb5dad9722e2e25ddd968b6ed50edc254420f9da22dd9f5bca");
    assert.equal(digest(parse(read("common/scripted_localisation/HSM_BAR_case_outcomes.txt"))),
        "7f4abed90774dfeb3a45fe5f0ea507cb7d8b3fa3fbe400bd0ed91e6c33660f4d", "Outcome/bonus dispatch changed");
    for (const locale of locales) assert.equal(digest([...locale].filter(([key]) => /_results$/.test(key))),
        "6050cf8e0ce483f86b52f3c9674bb11d449991b21acd36a363fc2567ec8d5831", "Results localization changed");
});

test("copies preserve legacy document clicks; regional navigation and console handoff remain presentation-only", () => {
    const stripCopyReset = nodes => nodes.filter(n => !(n.key === "clear_variable" && n.value === copyVar))
        .map(n => ({...n, value: Array.isArray(n.value) ? stripCopyReset(n.value) : n.value}));
    const originalEffects = Object.entries(scripts).map(([name, block]) => [name,
        stripCopyReset(prop(block, "effects").filter(n => !/^HSM_BAR_archive_(copy_[123]|audio_(echo|entity|reactor)|region_[1-6]|operations)_click$/.test(n.key))
            .map(n => ({...n, value: originalClickSnapshot(n.key, n.value)})))]);
    assert.equal(digest(originalEffects), "e9b94f361d3f156517c2d3ee8b35569c08b01ba03592b4510a1a2e4ce65ae184", "Existing click behavior changed");
    function validateEffects(nodes, handler) {
        const allowed = new Set(archiveVariables);
        if (handler === prefix + "operations_click") for (const name of handoffVariables) allowed.add(name);
        if (handler === prefix + "open_click") allowed.add("HSM_BAR_service_gui_open");
        for (const n of nodes) {
            if (n.key === "if") {
                assert.equal(n.value.filter(child => child.key === "limit").length, 1);
                validateCondition(prop(n.value, "limit")); validateEffects(n.value.filter(child => child.key !== "limit"), handler);
            } else if (n.key === "clear_variable") assert(allowed.has(n.value)
                || ["HSM_BAR_fielddesk_open", "HSM_BAR_investigation_open"].includes(n.value) && [prefix + "open_click", prefix + "operations_click"].includes(handler));
            else if (n.key === "HSM_BAR_service_gui_refresh") { assert.equal(handler, prefix + "operations_click"); assert.equal(n.value, "yes"); }
            else {
                assert(["set_variable", "add_to_variable", "subtract_from_variable"].includes(n.key), "Unexpected state change: " + n.key);
                assert.equal(n.value.length, 1); assert(allowed.has(n.value[0].key));
            }
        }
    }
    for (const block of [launcher, window]) for (const effect of prop(block, "effects")) validateEffects(effect.value, effect.key);
    const mod = path.resolve(__dirname, "../mod/HoISubmod");
    const allowed = new Set(["common/scripted_guis/HSM_BAR_archive.txt", "common/scripted_localisation/HSM_BAR_archive.txt",
        "common/scripted_localisation/HSM_BAR_archive_skin.txt", "common/scripted_guis/HSM_BAR_service_gui.txt",
        "common/scripted_effects/HSM_BAR_archive.txt"]);
    function scan(dir) {
        for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
            const file = path.join(dir, entry.name);
            if (entry.isDirectory()) scan(file);
            else if (entry.name.endsWith(".txt") && /\bHSM_BAR_archive_copy\b/.test(fs.readFileSync(file, "utf8"))) {
                const relative = path.relative(mod, file).replaceAll(path.sep, "/");
                assert(allowed.has(relative), "Copy selection leaked into gameplay: " + relative);
            }
        }
    }
    scan(path.join(mod, "common")); scan(path.join(mod, "events"));
});

test("copy skins default safely, remain read-only and occupy the specified fixed positions", () => {
    const skins = Object.fromEntries(parse(read("common/scripted_localisation/HSM_BAR_archive_skin.txt"))
        .map(n => [prop(n.value, "name"), n.value.filter(n => n.key === "text").map(n => n.value)]));
    const widgets = gui.find(n => prop(n.value, "name") === prefix + "window").value;
    for (const copy of copies) {
        const s = fixture("rock", 1, ["known"]); selectCopy(s, copy); const before = structuredClone(s);
        for (const i of [1, 2, 3]) {
            const choices = skins[`GetHSMBARArchiveCopy${i}Skin`]; assert(choices);
            const chosen = choices.find(b => !prop(b, "trigger") || condition(prop(b, "trigger"), s));
            assert.equal(keyOf(chosen), "GFX_" + prefix + "edition" + ((copy === 2 || copy === 3 ? copy : 1) === i ? "_selected" : ""));
        }
        assert.deepEqual(s, before);
    }
    for (const [i, x] of [350, 554, 758].entries()) {
        const widget = widgets.find(n => Array.isArray(n.value) && prop(n.value, "name") === prefix + "copy_" + (i + 1));
        assert.equal(widget.key, "buttonType");
        assert.deepEqual(prop(widget.value, "position"), parse(`x = ${x} y = 306`));
        assert.equal(prop(widget.value, "quadTextureSprite"), "GFX_" + prefix + "edition");
        assert.equal(prop(widget.value, "buttonFont"), prefix + "ink"); assert.equal(prop(widget.value, "scale"), undefined);
    }
});

test("EN/RU copies contain distinct substantive prose, matching redactions and no player-as-employee directions", () => {
    assert.deepEqual([...locales[0].keys()].sort(), [...locales[1].keys()].sort());
    for (const locale of locales) {
        assert.deepEqual([...locale.keys()].filter(isVariant).sort(), variants.toSorted());
        for (const c of copyCases) for (const stage of stages) {
            const keys = ["", "_restricted", "_sealed"].map(suffix => `${prefix}${c}_${stage}${suffix}`);
            const prose = keys.map(key => locale.get(key)); assert.equal(new Set(prose).size, 3, keys[0] + ": duplicate copy");
            const normalized = prose.map(text => text.replace(/\u00a3[^\u00a3]+\u00a3/g, " ").replace(/\u00a7./g, " ")
                .split("\\n").filter(line => line.trim().length > 80).join(" ").toLowerCase());
            for (let a = 0; a < 3; a++) for (let b = a + 1; b < 3; b++) {
                assert(normalized[a].length > 150 && normalized[b].length > 150, keys[0] + ": missing substantive prose");
                const tokens = text => new Set(text.match(/[\p{L}]{3,}/gu));
                const left = tokens(normalized[a]), right = tokens(normalized[b]);
                assert([...left].filter(token => !right.has(token)).length >= 12 && [...right].filter(token => !left.has(token)).length >= 12,
                    keys[0] + ": only header/redaction differences");
            }
            for (const [index, text] of prose.entries()) {
                assert(!/[\[\]$]/.test(text), keys[index] + ": unresolved markup");
                assert(!/political power|research bonus|click (?:here|to)|your clearance|you (?:must|should) (?:report|submit|classify)/i.test(text),
                    keys[index] + ": gameplay or employee address");
                assert(!/\u0431\u043e\u043d\u0443\u0441.*\u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d|\u043d\u0430\u0436\u043c\u0438\u0442\u0435|\u0432\u0430\u0448 \u0434\u043e\u043f\u0443\u0441\u043a/i.test(text),
                    keys[index] + ": gameplay or clearance address");
            }
        }
    }
    for (const key of variants) {
        const marks = text => text.match(/\u00a3HSM_BAR_redact_\w+\u00a3/g) || [];
        assert.deepEqual(marks(locales[0].get(key)), marks(locales[1].get(key)), key + ": redaction parity");
    }
    for (const c of ["echo", "marsh"]) for (const stage of ["intake", "field"]) for (const suffix of ["", "_restricted", "_sealed"]) {
        const key = `${prefix}${c}_${stage}${suffix}`;
        const premature = c === "echo" ? /ordinary acoustic|confirmed.*(?:acoustic|resonan)|proved.*(?:acoustic|resonan)/i
            : /ordinary chemical|confirmed.*chemical|proved.*chemical|chemiluminescen/i;
        assert(!premature.test(locales[0].get(key)), key + ": premature study conclusion");
        const russianPremature = c === "echo" ? /\u043e\u0431\u044b\u0447\u043d\S*\s+\u0430\u043a\u0443\u0441\u0442\u0438\u0447\u0435\u0441\u043a|\u0430\u043a\u0443\u0441\u0442\u0438\u0447\u0435\u0441\u043a\S*\s+\u0432\u044b\u0432\u043e\u0434/i
            : /\u043e\u0431\u044b\u0447\u043d\S*\s+\u0445\u0438\u043c\u0438\u0447\u0435\u0441\u043a|\u0445\u0435\u043c\u0438\u043b\u044e\u043c\u0438\u043d\u0435\u0441\u0446/i;
        assert(!russianPremature.test(locales[1].get(key)), key + ": premature Russian study conclusion");
    }
});

console.log(`Barrad archive copies: ${passed} scenario groups passed, ${failed} failed; six cases / 18 stages / 36 additional documents.`);
console.log("Static dispatch, state, layout and prose checks only; final narrative review and in-game acceptance remain manual.");
if (failed) process.exitCode = 1;
