"use strict";

// Source-contract checks against the installed engine and EaW, not a game-engine emulator.
// node tools/Test-BarradNativeContracts.cjs [--game-root PATH] [--eaw-root PATH]
// Numeric complexity examples in the shipped markdown are stale: live project files
// use sp_complexity.*, and the 2026-10-01 engine log rejects 15 and 25 as categories.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "..");
const mod = path.join(root, "mod/HoISubmod");
function argument(name, fallback) {
    const index = process.argv.indexOf(name);
    if (index < 0) return fallback;
    if (!process.argv[index + 1] || process.argv[index + 1].startsWith("--")) {
        throw Error("Missing path after " + name);
    }
    return path.resolve(process.argv[index + 1]);
}
const game = argument("--game-root", process.env.HOI4_GAME_ROOT ||
    "C:/shit/Steam/steamapps/common/Hearts of Iron IV");
const eaw = argument("--eaw-root", process.env.EAW_ROOT ||
    "C:/shit/Steam/steamapps/workshop/content/394360/1826643372");
const read = file => fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "");
const normalized = text => text.replace(/\r\n/g, "\n").trimEnd();

// Retain duplicate keys and bare-list entries; comments and quoted braces are inert.
function parse(text) {
    const tokens = text.match(/"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}]|[<>!=]=?|[^\s{}=<>!#"]+/g)
        ?.filter(token => !token.startsWith("#")) || [];
    let cursor = 0;
    function block(nested) {
        const result = [];
        while (cursor < tokens.length && tokens[cursor] !== "}") {
            const key = tokens[cursor++];
            if (key === "{") {
                result.push({ key: null, op: null, value: block(true) });
            } else if (["=", "<", ">", "<=", ">=", "!="].includes(tokens[cursor])) {
                const op = tokens[cursor++];
                const token = tokens[cursor++];
                if (!token || token === "}") throw Error("Missing value for " + key);
                result.push({ key, op, value: token === "{" ? block(true) : token });
            } else {
                result.push({ key, op: null, value: null });
            }
        }
        if (nested && tokens[cursor++] !== "}") throw Error("Unclosed block");
        return result;
    }
    const result = block(false);
    if (cursor !== tokens.length) throw Error("Unexpected closing brace");
    return result;
}
function one(nodes, key) {
    const matches = nodes.filter(node => node.key === key);
    assert.equal(matches.length, 1, "Expected exactly one " + key);
    return matches[0].value;
}
const children = (nodes, key) => nodes.filter(node => node.key === key);
function walk(nodes) {
    return nodes.flatMap(node => [node, ...(Array.isArray(node.value) ? walk(node.value) : [])]);
}
const parsed = file => parse(read(file));
let passed = 0;
let failed = 0;
function test(name, run) {
    try {
        run();
        passed++;
        console.log("PASS: " + name);
    } catch (error) {
        failed++;
        console.error("FAIL: " + name + "\n" + error.stack);
    }
}

// Required source files fail loudly, rather than silently falling back to guessed schemas.
const triggerDoc = read(path.join(game, "documentation/triggers_documentation.md"));
const documented = new Set([...triggerDoc.matchAll(/^## (\w+)\r?$/gm)].map(match => match[1]));
const constantRelative = "common/script_constants/special_project_constants.txt";
const constantFile = fs.existsSync(path.join(eaw, constantRelative))
    ? path.join(eaw, constantRelative) : path.join(game, constantRelative);
const complexities = one(parsed(constantFile), "sp_complexity");
const baseTech = read(path.join(eaw, "common/technologies/barrad_tech.txt"));
const localTech = read(path.join(mod, "common/technologies/barrad_tech.txt"));
const baseTechnologies = one(parse(baseTech), "technologies");
const technologies = one(parse(localTech), "technologies");
const gateFile = path.join(mod, "common/scripted_triggers/HSM_BAR_recovered_science.txt");
const gate = one(parsed(gateFile), "HSM_BAR_recovered_science_access");
const requiredFlags = ["HSM_BAR_active", "HSM_BAR_directorate",
    "HSM_BAR_service_founded", "HSM_BAR_recovered_archives"];
const alive = ["barrad_asinti_alive", "barrad_silver_star_alive",
    "barrad_leopold_alive", "barrad_viira_alive"];
const recoverable = baseTechnologies.filter(tech => tech.key.startsWith("tech_bar_") &&
    children(tech.value, "dependencies").length);

function validateComplexity(value) {
    assert.match(value, /^sp_complexity\.[a-z_]+$/, "complexity must name an installed constant");
    const definition = one(complexities, value.split(".")[1]);
    const min = Number(one(definition, "min"));
    const max = Number(one(definition, "max"));
    assert(Number.isInteger(min) && Number.isInteger(max) && min > 0 && max >= min);
}
// Deliberately fail closed. Only the country predicates actually used by this gate
// are interpreted; their names must also exist in the installed engine documentation.
function condition(node, state) {
    const { key, op, value } = node;
    assert.equal(op, "=", "Non-equality in research gate: " + key);
    if (key === "ROOT") return all(value, state);
    if (key === "OR") return value.some(child => condition(child, state));
    if (key === "custom_trigger_tooltip") {
        assert.equal(typeof one(value, "tooltip"), "string");
        return all(value.filter(child => child.key !== "tooltip"), state);
    }
    if (key === "HSM_BAR_recovered_science_access") {
        assert.equal(value, "yes");
        return all(gate, state);
    }
    assert(documented.has(key), "Undocumented trigger: " + key);
    switch (key) {
        case "tag": return state.tag === value;
        case "original_tag": return state.originalTag === value;
        case "has_country_flag": return state.flags.has(value);
        case "has_tech": return state.techs.has(value);
        default: throw Error("Unsupported research predicate: " + key);
    }
}
function all(nodes, state) { return nodes.every(node => condition(node, state)); }
const state = () => ({ tag: "BAR", originalTag: "BAR", flags: new Set(requiredFlags), techs: new Set() });
const canAccess = (id, scenario) => all(one(one(technologies, id), "allow"), scenario);

test("installed documentation and live content support the chosen native syntax", () => {
    for (const name of ["has_manpower", "has_tech", "has_country_flag", "tag", "original_tag"]) {
        assert(documented.has(name), name);
    }
    assert(!documented.has("manpower"));
    const artillery = one(parsed(path.join(eaw, "common/technologies/artillery.txt")), "technologies");
    assert(artillery.filter(tech => Array.isArray(tech.value)).some(tech => children(tech.value, "allow").some(allow =>
        children(allow.value, "ROOT").some(scope => children(scope.value, "has_tech").length))));
    const magical = read(path.join(eaw, "common/special_projects/projects/magical_projects.txt"));
    assert.match(magical, /complexity\s*=\s*sp_complexity\.small\b/);
    validateComplexity("sp_complexity.small");
});

for (const [filename, count] of [["HSM_BAR_cases.txt", 17], ["HSM_BAR_research_projects.txt", 6]]) {
    test(filename + ": all projects use existing structured complexity constants", () => {
        const projects = parsed(path.join(mod, "common/special_projects/projects", filename));
        assert.equal(projects.length, count);
        for (const project of projects) {
            validateComplexity(one(project.value, "complexity"));
            assert.equal(one(project.value, "complexity"), "sp_complexity.small");
            assert.equal(one(project.value, "specialization"), "specialization_magical");
            assert(Number(one(project.value, "prototype_time")) > 0);
        }
    });
}
for (const invalid of ["15", "25", "sp_complexity.nonexistent", "sp_complexity.schema"]) {
    test("reject invalid complexity " + invalid, () => assert.throws(() => validateComplexity(invalid)));
}

const decisions = one(parsed(path.join(mod, "common/decisions/HSM_BAR_collegium_decisions.txt")),
    "HSM_BAR_collegium_programs");
test("Collegium manpower gates use has_manpower and preserve reservation thresholds", () => {
    assert.equal(walk(decisions).filter(node => node.key === "manpower").length, 0);
    const reserved = decisions.filter(decision => children(decision.value, "available")
        .some(available => children(available.value, "has_manpower").length));
    assert.equal(reserved.length, 2);
    for (const decision of reserved) {
        const predicate = children(one(decision.value, "available"), "has_manpower")[0];
        assert.equal(predicate.op, ">");
        const threshold = Number(predicate.value);
        assert([99, 199].includes(threshold));
        const start = one(one(decision.value, "complete_effect"), "if");
        assert(children(one(start, "limit"), "NOT").some(n => n.value.length === 1 &&
            n.value[0].key === "has_country_flag" && n.value[0].op === "=" &&
            n.value[0].value === decision.key + "_pending"));
        assert.equal(children(one(start, "limit"), "has_manpower")[0].value, String(threshold));
        const payment = Number(one(start, "add_manpower"));
        assert.equal(payment, -threshold - 1);
        assert(children(start, "set_country_flag").some(n => n.value === decision.key + "_staff_assigned"));
        for (const callback of ["remove_effect", "cancel_effect"]) {
            const refunds = children(one(decision.value, callback), "if")
                .filter(n => children(n.value, "add_manpower").length);
            assert.equal(refunds.length, 1);
            const refund = refunds[0].value;
            assert.equal(one(one(refund, "limit"), "has_country_flag"), decision.key + "_staff_assigned");
            assert.equal(one(refund, "add_manpower"), String(-payment));
            assert.equal(one(refund, "clr_country_flag"), decision.key + "_staff_assigned");
        }
    }
});
test("legacy manpower trigger is rejected by the installed trigger vocabulary", () => {
    assert.throws(() => condition({ key: "manpower", op: "=", value: "200" }, state()),
        /Undocumented trigger/);
});

test("only 31 documented research technologies have their life-marker prerequisite replaced", () => {
    assert.equal(recoverable.length, 31);
    const counts = Object.fromEntries(alive.map(key => [key, 0]));
    for (const tech of recoverable) {
        const dependency = one(tech.value, "dependencies");
        assert.equal(dependency.length, 1);
        assert(alive.includes(dependency[0].key));
        counts[dependency[0].key]++;
        const updated = one(technologies, tech.key);
        assert.equal(children(updated, "dependencies").length, 0);
        assert.equal(one(updated, "research_cost"), one(tech.value, "research_cost"));
        assert.deepEqual(updated.filter(node => node.key !== "allow"),
            tech.value.filter(node => node.key !== "dependencies"));
        assert.deepEqual(one(one(updated, "allow"), "ROOT"), [{ key: "OR", op: "=", value: [
            { key: "has_tech", op: "=", value: dependency[0].key },
            { key: "HSM_BAR_recovered_science_access", op: "=", value: "yes" }
        ] }]);
    }
    assert.deepEqual(Object.values(counts), [10, 7, 8, 6]);
});
test("all remaining technology text is unchanged apart from line endings", () => {
    const expected = normalized(baseTech).replace(
        /\t\tdependencies = \{\n\t\t\t(barrad_\w+_alive) = 1\n\t\t\}/g,
        (_, marker) => "\t\tallow = {\n\t\t\tROOT = {\n\t\t\t\tOR = {\n" +
            "\t\t\t\t\thas_tech = " + marker + "\n" +
            "\t\t\t\t\tHSM_BAR_recovered_science_access = yes\n\t\t\t\t}\n\t\t\t}\n\t\t}");
    assert.equal(normalized(localTech), expected);
    assert.deepEqual(technologies.map(tech => tech.key), baseTechnologies.map(tech => tech.key));
});
test("existing non-Service routes preserve eligibility for every combination of surviving Pentarchs", () => {
    for (let mask = 0; mask < 16; mask++) {
        const legacy = state();
        legacy.flags.clear();
        alive.forEach((marker, index) => { if (mask & (1 << index)) legacy.techs.add(marker); });
        for (const tech of recoverable) {
            const marker = one(tech.value, "dependencies")[0].key;
            assert.equal(canAccess(tech.key, legacy), legacy.techs.has(marker), tech.key + ":" + mask);
        }
    }
});
test("analysed archives reopen all four research branches without any alive tech", () => {
    const recovered = state();
    for (const tech of recoverable) assert(canAccess(tech.key, recovered), tech.key);
    assert.equal(recovered.techs.size, 0, "Eligibility must not grant technology");
});
for (const missing of requiredFlags) {
    test("missing " + missing + " blocks recovered access", () => {
        const incomplete = state();
        incomplete.flags.delete(missing);
        for (const tech of recoverable) assert(!canAccess(tech.key, incomplete), tech.key);
    });
}
test("flag copies cannot reopen research for another country or civil-war origin", () => {
    for (const field of ["tag", "originalTag"]) {
        const foreign = state();
        foreign[field] = "WIT";
        for (const tech of recoverable) assert(!canAccess(tech.key, foreign));
    }
});
test("alive flags are not substituted for EaW alive technologies", () => {
    const incorrect = state();
    incorrect.flags = new Set(alive);
    for (const tech of recoverable) assert(!canAccess(tech.key, incorrect));
});
test("personal powers, artificial bodies and life-marker definitions remain untouched", () => {
    const untouched = baseTechnologies.filter(tech => !recoverable.includes(tech));
    assert.equal(untouched.length, 21);
    for (const tech of untouched) assert.deepEqual(one(technologies, tech.key), tech.value, tech.key);
    for (const id of ["bar_leopold_new_body", "barrad_silver_horde", "BAR_viira_nukes",
        "BAR_viira_spells_sub_zero", "BAR_viira_spells_gravity", "BAR_viira_spells_teleport",
        "BAR_knights", "BAR_knights2", "BAR_knights_upgrade"]) {
        assert.equal(one(one(one(technologies, id), "allow"), "always"), "no", id);
    }
    assert(!walk(gate).some(node => /^(set_technology|set_country_flag|recruit_character)$/.test(node.key)));
});
test("Ambrosius root and research-folder access remain supplied by original EaW history", () => {
    const history = parsed(path.join(eaw, "history/countries/BAR - Baard.txt"));
    assert(children(history, "set_technology").some(node =>
        children(node.value, "tech_bar_ancient_knowledge").some(tech => tech.value === "1")));
    const race = parsed(path.join(eaw, "common/scripted_triggers/EAW_race_triggers.txt"));
    assert.equal(one(one(race, "has_barrad_race_tech"), "original_tag"), "BAR");
    const paths = children(one(technologies, "tech_bar_ancient_knowledge"), "path");
    assert.deepEqual(paths.map(node => one(node.value, "leads_to_tech")),
        ["tech_bar_asinti", "tech_bar_silver", "tech_bar_matarial_science", "tech_bar_viira"]);
});
test("research-gate evaluator rejects invented syntax instead of accepting unknown predicates", () => {
    for (const key of ["has_recovered_magic", "research_requirements", "political_power"]) {
        assert.throws(() => condition({ key, op: "=", value: "yes" }, state()));
    }
});
test("EN/RU recovered-science tooltips are present, unique and UTF-8 BOM encoded", () => {
    const expected = ["HSM_BAR_recovered_science_access_tt", "HSM_BAR_recovered_science_unlocked_tt"];
    for (const language of ["english", "russian"]) {
        const file = path.join(mod, "localisation", language, "HSM_BAR_recovered_science_l_" + language + ".yml");
        const bytes = fs.readFileSync(file);
        assert.equal(bytes.subarray(0, 3).toString("hex"), "efbbbf");
        const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
        assert(text.startsWith("l_" + language + ":"));
        const lines = text.trimEnd().split(/\r?\n/).slice(1);
        assert.equal(lines.length, 2);
        assert.deepEqual(lines.map(line => {
            const match = line.match(/^ ([A-Za-z0-9_]+):0 "[^"\r\n]+"$/);
            assert(match, line);
            return match[1];
        }), expected);
    }
});

console.log(`${passed} passed, ${failed} failed scenarios. Installed-source contracts only; in-game research UI remains a playtest.`);
if (failed) process.exitCode = 1;
