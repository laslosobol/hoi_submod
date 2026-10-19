"use strict";

// node tools/Test-BarradMeterRetirement.cjs
// Read-only script/localization audit and old-save fixtures, not an HOI4 runtime test.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const { parse, prop } = require("./Test-BarradArchiveSkin.cjs");
const F = require("./Test-BarradCases.cjs");
const meters = ["HSM_BAR_public_trust", "HSM_BAR_capacity"];
const retired = /\bHSM_BAR_(?:public_trust|capacity)\b/;
const obsoleteTooltip = /\bHSM_BAR_(?:collegium_(?:trust|capacity)_\w+_tt|service_capacity_\w+_tt)\b/;
const coreFile = "common/scripted_effects/HSM_BAR_core_effects.txt";
const cleanupPaths = [
    ["HSM_BAR_initialize_common"],
    ["HSM_BAR_core_refresh", "hidden_effect"],
    ["HSM_BAR_dissolve_institutions"]
];
const cleanupKey = (parents, meter) => [...parents, meter].join("/");
const expectedCleanups = cleanupPaths.flatMap(parents => meters.map(m => cleanupKey(parents, m))).sort();

function auditScript(nodes, file, parents = [], cleanups = []) {
    for (const n of nodes) {
        assert(!retired.test(n.key), file + ": retired meter key " + n.key);
        assert(!obsoleteTooltip.test(n.key), file + ": obsolete reward tooltip " + n.key);
        if (Array.isArray(n.value)) auditScript(n.value, file, [...parents, n.key], cleanups);
        else if (typeof n.value === "string") {
            assert(!obsoleteTooltip.test(n.value), file + ": obsolete reward tooltip " + n.value);
            if (!retired.test(n.value)) continue;
            assert.equal(file, coreFile, "Retired meter outside core cleanup: " + file);
            assert(n.key === "clear_variable" && n.op === "=" && meters.includes(n.value), "Retired meter read/write: " + n.key + " = " + n.value);
            assert(cleanupPaths.some(p => JSON.stringify(p) === JSON.stringify(parents)), "Conditional, scoped or misplaced cleanup: " + parents.join("/"));
            cleanups.push(cleanupKey(parents, n.value));
        }
    }
    return cleanups;
}
function auditLocalization(source, file) {
    // Check even unreferenced keys: hiding a dead display does not retire it.
    const active = source.split(/\r?\n/).filter(line => !/^\s*#/.test(line)).join("\n");
    assert(!retired.test(active), file + ": retired meter localization/display");
    assert(!obsoleteTooltip.test(active), file + ": obsolete reward tooltip definition/reference");
    const plain = active.replace(/\u00a7./g, "");
    assert(!/(?:public trust|institutional capacity)\s*:/i.test(plain), file + ": obsolete meter display label");
    assert(!/\b\d+(?:\.\d+)?\s+(?:capacity|trust)\b|\b(?:capacity|trust)\s*(?:>=?|<=?|[=:+-])\s*\d/i.test(plain), file + ": obsolete numeric meter reward/threshold");
    assert(!/(?:\u043e\u0431\u0449\u0435\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0435\s+\u0434\u043e\u0432\u0435\u0440\u0438\u0435|\u0438\u043d\u0441\u0442\u0438\u0442\u0443\u0446\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u044b\u0439\s+\u043f\u043e\u0442\u0435\u043d\u0446\u0438\u0430\u043b)\s*:/i.test(plain), file + ": obsolete Russian meter label");
    assert(!/\d+\s+(?:\u043f\u043e\u0442\u0435\u043d\u0446\u0438\u0430\u043b\w*|\u0434\u043e\u0432\u0435\u0440\u0438\w*)/i.test(plain), file + ": obsolete Russian meter threshold");
}
function files(dir) {
    return fs.readdirSync(path.join(F.mod, dir), { withFileTypes: true }).flatMap(entry => {
        const file = path.posix.join(dir, entry.name);
        return entry.isDirectory() ? files(file) : /\.(?:txt|gui|gfx|yml)$/i.test(file) ? [file] : [];
    });
}
let passed = 0, failed = 0, checked = 0;
function scenario(name, fn) {
    try { fn(); passed++; console.log("PASS: " + name); }
    catch (e) { failed++; console.error("FAIL: " + name + "\n" + e.stack); }
}
scenario("all Barrad scripts and localization retire meters except six unconditional core clears", () => {
    const cleanups = [], errors = [];
    for (const dir of ["common", "events", "history", "interface", "localisation"]) for (const file of files(dir)) {
        const source = fs.readFileSync(path.join(F.mod, file), "utf8");
        if (!/HSM_BAR/i.test(file) && !/HSM_BAR/i.test(source)) continue;
        checked++;
        try {
            if (file.endsWith(".yml")) auditLocalization(source, file);
            else auditScript(parse(source, true), file, [], cleanups);
        } catch (e) { errors.push(e.message); }
    }
    assert(checked > 100, "Barrad content scan lost coverage");
    assert.deepEqual(errors, []);
    assert.deepEqual(cleanups.sort(), expectedCleanups, "Missing or duplicated entry/refresh/dissolution cleanup");
});
for (const meter of meters) {
    scenario(meter + ": hidden writes, indirect reads, thresholds, bindings and scripted displays are rejected", () => {
        const snippets = [
            `set_variable = { ${meter} = 100 }`, `add_to_variable = { ${meter} = 5 }`,
            `subtract_from_variable = { ${meter} = 2 }`, `multiply_variable = { ${meter} = 0.5 }`,
            `set_temp_variable = { ${meter} = 100 }`, `set_variable = { HSM_BAR_fixture = ${meter} }`,
            `set_variable = { var = HSM_BAR_fixture value = global.${meter} }`,
            `check_variable = { var = ${meter} value = 40 compare = greater_than_or_equals }`,
            `check_variable = { ${meter} > 40 }`, `has_variable = ${meter}`,
            `clamp_variable = { var = ${meter} min = 0 max = 100 }`,
            `research_speed_factor = ${meter}`, `text = "[?ROOT.${meter}|0]/100"`
        ];
        for (const snippet of snippets) {
            const source = `HSM_BAR_core_refresh = { hidden_effect = { ${snippet} } }`;
            assert.throws(() => auditScript(parse(source), coreFile), /Retired meter|retired meter/, snippet);
        }
    });
    scenario(meter + ": cleanup cannot move into a condition, foreign scope, another helper or another file", () => {
        const clear = `clear_variable = ${meter}`;
        for (const source of [clear,
            `HSM_BAR_other = { ${clear} }`,
            `HSM_BAR_core_refresh = { hidden_effect = { BAR = { ${clear} } } }`,
            `HSM_BAR_core_refresh = { hidden_effect = { if = { limit = { always = yes } ${clear} } } }`,
            `HSM_BAR_core_refresh = { hidden_effect = { clear_variable = { var = ${meter} } } }`
        ]) assert.throws(() => auditScript(parse(source), coreFile));
        assert.throws(() => auditScript(parse(`HSM_BAR_initialize_common = { ${clear} }`), "common/scripted_effects/HSM_BAR_other.txt"), /outside core cleanup/);
    });
}
scenario("all three allowed cleanup paths delete arbitrary old-save values and preserve unrelated data", () => {
    const core = parse(fs.readFileSync(path.join(F.mod, coreFile), "utf8"));
    for (const parents of cleanupPaths) {
        const body = parents.reduce((nodes, key) => prop(nodes, key), core);
        const clears = body.filter(n => n.key === "clear_variable" && meters.includes(n.value));
        assert.deepEqual(clears.map(n => n.value).sort(), [...meters].sort());
        for (const value of [undefined, -999.25, 0, 40, 50, 100, 999.25]) {
            const w = F.world(); w.root.vars.HSM_BAR_fixture_value = 17;
            const original = structuredClone(w);
            if (value !== undefined) for (const m of meters) w.root.vars[m] = value;
            // Execute the actual unconditional cleanup statements, not unrelated entry politics.
            F.run(clears, w); assert.deepEqual(w, original);
            F.run(clears, w); assert.deepEqual(w, original);
        }
    }
});
scenario("obsolete EN/RU labels, numeric thresholds and dead reward tooltip references fail the audit", () => {
    const texts = [
        'HSM_BAR_title:0 "[?HSM_BAR_capacity|0]/100"',
        'HSM_BAR_title:0 "Public trust: 50/100"',
        'HSM_BAR_title:0 "Institutional capacity: +5"',
        'HSM_BAR_title:0 "Requires 45 capacity and 50 trust"',
        'HSM_BAR_title:0 "Trust >= 50"',
        'HSM_BAR_title:0 "\u041e\u0431\u0449\u0435\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0435 \u0434\u043e\u0432\u0435\u0440\u0438\u0435: +5"',
        'HSM_BAR_title:0 "45 \u043f\u043e\u0442\u0435\u043d\u0446\u0438\u0430\u043b\u0430 \u0438 50 \u0434\u043e\u0432\u0435\u0440\u0438\u044f"',
        'HSM_BAR_collegium_trust_plus_5_tt:0 "Unused old reward"',
        'HSM_BAR_title:0 "$HSM_BAR_service_capacity_five_tt$"'
    ];
    for (const text of texts) assert.throws(() => auditLocalization(text, "fixture.yml"));
    for (const key of ["HSM_BAR_collegium_capacity_plus_6_tt", "HSM_BAR_collegium_trust_minus_3_tt", "HSM_BAR_service_capacity_ten_tt"]) {
        assert.throws(() => auditScript(parse(`hidden_effect = { custom_effect_tooltip = ${key} }`), "fixture.txt"), /obsolete reward tooltip/);
    }
});
scenario("retained Service spirit IDs, concrete research outputs, ordinary prose and comments are allowed", () => {
    auditScript(parse("HSM_BAR_service_capacity = { research_speed_factor = HSM_BAR_service_research } # HSM_BAR_capacity"), "fixture.txt");
    auditLocalization('HSM_BAR_service_capacity_desc:0 "The archive earns public trust through its work."\n# HSM_BAR_capacity', "fixture.yml");
    assert.throws(() => parse("broken = {"), /Unclosed block/);
    assert.throws(() => F.run(F.parse("hidden_effect = { invented_effect = yes }"), F.world()), /Unsupported effect/);
    assert.throws(() => F.test(F.parse("invented_predicate = yes"), F.world()), /Unsupported predicate/);
});
console.log(`Barrad meter retirement: ${passed} scenarios passed; ${failed} failed; ${checked} content files checked.`);
process.exitCode = failed ? 1 : 0;
