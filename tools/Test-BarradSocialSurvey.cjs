"use strict";

// Executes the small survey contract and installed native tier helpers, not HOI4.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const { parse, read, prop, dictionary, mod } = require("./Test-BarradCases.cjs");
const eaw = process.env.EAW_ROOT || "C:/shit/Steam/steamapps/workshop/content/394360/1826643372";
const native = file => parse(fs.readFileSync(path.join(eaw, file), "utf8"));
const walk = nodes => nodes.flatMap(n => [n, ...(Array.isArray(n.value) ? walk(n.value) : [])]);
const many = (nodes, key) => nodes.filter(n => n.key === key);
const poverty = ["poverty", "poverty1", "poverty2", "poverty3", "poverty4", "poverty5", "no_poverty"];
const literacy = ["lack_of_scientists", "lack_of_scientists1", "lack_of_scientists2", "lack_of_scientists3", "no_lack_of_scientists"];
const effectFile = read("common/scripted_effects/HSM_BAR_social_survey.txt");
const effects = dictionary(effectFile);
for (const id of ["decrease_poverty", "decrease_illiteracy"])
    effects[id] = prop(native("common/scripted_effects/EAW_misc_effect.txt"), id);
const triggers = Object.assign({}, ...["development", "collegium_triggers", "civic_triggers", "mtc_frontiers"]
    .map(name => dictionary(read("common/scripted_triggers/HSM_BAR_" + name + ".txt"))));
const files = ["common", "republic", "directorate", "collegium", "civic", "mtc_frontiers"];
const focusNodes = files.flatMap(file => read("common/national_focus/HSM_BAR_" + file + ".txt"));
const focuses = dictionary(many(focusNodes, "shared_focus").map(n => ({ key: prop(n.value, "id"), value: n.value })));
const trees = dictionary(many(focusNodes, "focus_tree").map(n => ({ key: prop(n.value, "id"), value: n.value })));
const root = "HSM_BAR_common_reconstruction", marker = "HSM_BAR_social_survey_assessed";
const event = prop(read("events/HSM_BAR_social_survey.txt"), "country_event");
const ideaTraits = {};
for (const file of ["_poverty_ideas.txt", "_lack_of_scientist_ideas.txt"]) {
    for (const node of walk(native("common/ideas/" + file))) {
        if (Array.isArray(node.value) && prop(node.value, "traits"))
            ideaTraits[node.key] = prop(node.value, "traits").map(n => n.key);
    }
}
function world(route = "collegium", poor = "no_poverty", literate = "no_lack_of_scientists") {
    return { tag: "BAR", originalTag: "BAR", flags: new Set(["HSM_BAR_active", "HSM_BAR_" + route]),
        ideas: new Set([poor, literate, "pre_industrial_society", "better_science_base", "unrelated_idea"].filter(Boolean)),
        done: new Set(), owner: "BAR", controller: "BAR", capitulated: false, subject: false,
        pp: 0, events: [], tree: null };
}
function condition(nodes, s) {
    assert(Array.isArray(nodes));
    return nodes.every(({ key, value: v, op }) => {
        assert.equal(op, "=", "Unexpected comparator " + key);
        if (["AND", "hidden_trigger"].includes(key)) return condition(v, s);
        if (key === "OR") return v.some(n => condition([n], s));
        if (["NOT", "NOR"].includes(key)) return !v.some(n => condition([n], s));
        if (key === "custom_trigger_tooltip") return condition(v.filter(n => n.key !== "tooltip"), s);
        if (key === "always") return v === "yes";
        if (key === "tag") return s.tag === v;
        if (key === "original_tag") return s.originalTag === v;
        if (key === "exists") return v === "yes";
        if (key === "has_country_flag") return s.flags.has(v);
        if (key === "has_completed_focus") return s.done.has(v);
        if (key === "has_idea") return s.ideas.has(v);
        if (key === "has_idea_with_trait") return [...s.ideas].some(id => ideaTraits[id]?.includes(v));
        if (key === "has_capitulated") return s.capitulated === (v === "yes");
        if (key === "is_subject") return s.subject === (v === "yes");
        if (key === "owns_state" || key === "controls_state") {
            assert.equal(v, "624"); return s[key === "owns_state" ? "owner" : "controller"] === s.tag;
        }
        if (Object.hasOwn(triggers, key)) { assert.equal(v, "yes"); return condition(triggers[key], s); }
        throw Error("Unmodelled survey predicate " + key);
    });
}
function run(nodes, s) {
    assert(Array.isArray(nodes));
    let branch = false;
    for (const { key, value: v, op } of nodes) {
        assert.equal(op, "=", "Unexpected effect comparator " + key);
        if (key === "if" || key === "else_if") {
            if (key === "if") branch = false;
            if (!branch && condition(prop(v, "limit"), s)) { branch = true; run(v.filter(n => n.key !== "limit"), s); }
        } else if (key === "else") { if (!branch) run(v, s); branch = true; }
        else if (key === "hidden_effect") run(v, s);
        else if (key === "set_country_flag") { assert.equal(typeof v, "string"); s.flags.add(v); }
        else if (key === "add_ideas" || key === "remove_ideas") {
            for (const id of Array.isArray(v) ? v.map(n => n.key) : [v]) s.ideas[key === "add_ideas" ? "add" : "delete"](id);
        } else if (key === "swap_ideas") {
            assert.equal(v.length, 2); s.ideas.delete(prop(v, "remove_idea")); s.ideas.add(prop(v, "add_idea"));
        } else if (key === "country_event") s.events.push({ id: prop(v, "id"), days: Number(prop(v, "days")) });
        else if (key === "add_political_power") s.pp += Number(v);
        else if (key === "custom_effect_tooltip") assert.equal(typeof v, "string");
        else if (Object.hasOwn(effects, key)) { assert.equal(v, "yes"); run(effects[key], s); }
        else throw Error("Unmodelled survey effect " + key);
    }
}
const assess = s => run(effects.HSM_BAR_social_survey_assess, s);
const ready = (id, s) => !s.done.has(id) && many(focuses[id], "prerequisite")
    .every(group => group.value.some(n => s.done.has(n.value))) && condition(prop(focuses[id], "available") || [], s);
function members(tree) {
    const included = new Set(many(tree, "shared_focus").map(n => n.value));
    let changed;
    do {
        changed = false;
        for (const [id, focus] of Object.entries(focuses)) {
            const parents = many(focus, "prerequisite").flatMap(n => n.value.map(p => p.value));
            if (!included.has(id) && parents.some(p => included.has(p))) { included.add(id); changed = true; }
        }
    } while (changed);
    return included;
}
let passed = 0, failed = 0;
function test(name, fn) {
    try { fn(); passed++; console.log("PASS: " + name); }
    catch (error) { failed++; console.error("FAIL: " + name + "\n" + error.stack); }
}
test("strict model rejects unknown effects and predicates", () => {
    assert.throws(() => run(parse("invented_effect = yes"), world()), /Unmodelled/);
    assert.throws(() => condition(parse("invented_trigger = yes"), world()), /Unmodelled/);
});
test("installed Barrad history plus native startup reproduces the misleading best tiers", () => {
    const history = native("history/countries/BAR - Baard.txt");
    const s = world(); s.ideas.clear(); run(many(history, "add_ideas"), s);
    assert(![...poverty, ...literacy].some(id => s.ideas.has(id)));
    const startup = native("common/on_actions/eaw_on_startup_general_on_actions.txt");
    for (const id of ["no_poverty", "no_lack_of_scientists"]) {
        const setup = walk(startup).filter(n => n.key === "if" && prop(n.value, "add_ideas") === id);
        assert.equal(setup.length, 1); run(setup, s); assert(s.ideas.has(id));
    }
    assert(s.ideas.has("pre_industrial_society") && s.ideas.has("better_science_base"));
});
test("baseline is native Barrad precedent, not invented statistics or replacement ideas", () => {
    const e = many(native("events/Barrad Events.txt"), "country_event").find(n => prop(n.value, "id") === "barrad_ccamb.6");
    assert(e);
    const grants = walk(e.value).filter(n => n.key === "add_ideas").map(n => n.value);
    for (const id of ["poverty1", "lack_of_scientists1"]) { assert(grants.includes(id)); assert(ideaTraits[id]); }
    assert.deepEqual(walk(effectFile).filter(n => n.key === "add_ideas").map(n => n.value), ["poverty1", "lack_of_scientists1"]);
    assert(!walk(effectFile).some(n => /variable|research_slot|technology|society_development|science_base/.test(n.key)));
});
for (const route of ["collegium", "directorate"]) {
    for (const p of [...poverty, null]) for (const l of [...literacy, null]) test(`${route}: ${p}/${l} corrected once, poorer tiers retained`, () => {
        const s = world(route, p, l), expectedP = poverty.indexOf(p) === 0 ? p : "poverty1";
        const expectedL = literacy.indexOf(l) === 0 ? l : "lack_of_scientists1";
        assess(s);
        assert.deepEqual([...s.ideas].filter(id => poverty.includes(id)), [expectedP]);
        assert.deepEqual([...s.ideas].filter(id => literacy.includes(id)), [expectedL]);
        for (const id of ["pre_industrial_society", "better_science_base", "unrelated_idea"]) assert(s.ideas.has(id));
        assert(s.flags.has(marker)); assert.equal(s.events.length, 1);
        const after = structuredClone(s); assess(s); assert.deepEqual(s, after);
    });
    test(route + ": native improvements remain intact on replay, return and tree changes", () => {
        const s = world(route); assess(s);
        for (let i = 0; i < 7; i++) for (const helper of ["decrease_poverty", "decrease_illiteracy"]) run(effects[helper], s);
        assert(s.ideas.has("no_poverty") && s.ideas.has("no_lack_of_scientists"));
        for (const tree of Object.keys(trees)) { s.tree = tree; const before = structuredClone(s); assess(s); assert.deepEqual(s, before); }
        s.flags.delete("HSM_BAR_active"); const absent = structuredClone(s); assess(s); assert.deepEqual(s, absent);
        s.flags.add("HSM_BAR_active"); const returned = structuredClone(s); assess(s); assert.deepEqual(s, returned);
    });
}
for (const [name, change] of Object.entries({
    "native path": s => s.flags.clear(), "inactive": s => s.flags.delete("HSM_BAR_active"),
    "no new route": s => s.flags.delete("HSM_BAR_collegium"), "foreign tag": s => { s.tag = "WIT"; },
    "capitulated": s => { s.capitulated = true; }, "occupied": s => { s.controller = "WIT"; },
    "not owner": s => { s.owner = "WIT"; }
})) test(name + " cannot mutate social tiers or consume the one-time guard", () => {
    const s = world(); change(s); const before = structuredClone(s); assess(s); assert.deepEqual(s, before);
});
test("one first focus in both starting trees; no cross-route shared descendant leakage", () => {
    for (const [route, tree, next] of [["collegium", "HSM_BAR_collegium_tree", "HSM_BAR_collegium_oath"],
        ["directorate", "HSM_BAR_republic_tree", "HSM_BAR_transition_republic"]]) {
        const s = world(route), included = members(trees[tree]);
        assert.deepEqual([...included].filter(id => ready(id, s)), [root]);
        run(prop(focuses[root], "completion_reward"), s); s.done.add(root);
        assert(ready(next, s)); assert(s.flags.has(marker)); assert.equal(s.pp, 50);
        const excluded = route === "collegium" ? ["HSM_BAR_transition_republic", "HSM_BAR_dir_charter", "HSM_BAR_collegium_future_root"]
            : ["HSM_BAR_collegium_oath", "HSM_BAR_civic_republic", "HSM_BAR_mtc_frontiers", "HSM_BAR_dir_charter"];
        for (const id of excluded) assert(!included.has(id), tree + " leaked " + id);
        assert.equal(many(focuses[next], "prerequisite").length, 0, "Use availability, not a shared descendant link");
    }
});
test("all five trees keep one shared survey and remain nonoverlapping and acyclic", () => {
    assert.equal(Object.keys(trees).length, 5);
    for (const [id, tree] of Object.entries(trees)) {
        assert.equal(many(tree, "shared_focus").filter(n => n.value === root).length, 1, id);
        const included = members(tree), positions = new Set(), stack = new Set(), visited = new Set();
        function visit(focusId) {
            assert(!stack.has(focusId), "Cycle " + focusId); if (visited.has(focusId)) return;
            stack.add(focusId);
            for (const group of many(focuses[focusId], "prerequisite")) for (const ref of group.value) {
                assert(included.has(ref.value)); visit(ref.value);
            }
            stack.delete(focusId); visited.add(focusId);
        }
        for (const focusId of included) {
            visit(focusId); const f = focuses[focusId]; assert(!prop(f, "relative_position_id"));
            const pos = prop(f, "x") + "," + prop(f, "y"); assert(!positions.has(pos), id + " overlap " + focusId); positions.add(pos);
        }
    }
});
test("one caller, no startup/pulse/reset hook, no assessment-marker clearing", () => {
    const callers = [];
    for (const dir of ["common", "events"]) for (const name of fs.readdirSync(path.join(mod, dir), { recursive: true })) {
        if (!name.endsWith(".txt")) continue;
        const nodes = walk(read(dir + "/" + name));
        assert(!nodes.some(n => n.key === "clr_country_flag" && n.value === marker), "One-time marker cleared by " + name);
        if (nodes.some(n => n.key === "HSM_BAR_social_survey_assess" && n.value === "yes")) callers.push(name.replaceAll("\\", "/"));
    }
    assert.deepEqual(callers, ["national_focus/HSM_BAR_common.txt"]);
    assert.equal(walk(prop(focuses[root], "completion_reward")).filter(n => n.key === "HSM_BAR_social_survey_assess").length, 1);
    assert(!fs.existsSync(path.join(mod, "history/countries/BAR - Baard.txt")), "Native history unexpectedly overridden");
    const completed = world(); completed.done.add(root); assert(!ready(root, completed));
});
test("report is once-only presentation; dismissing it cannot reset later progress", () => {
    const s = world(); assert(!condition(prop(event, "trigger"), s)); assess(s);
    assert.equal(s.events[0].id, prop(event, "id")); assert.equal(s.events[0].days, 1);
    assert(condition(prop(event, "trigger"), s)); run(prop(event, "immediate"), s);
    assert(!condition(prop(event, "trigger"), s));
    assert.deepEqual(prop(event, "option").map(n => n.key), ["name"]);
    const invalid = world(); assess(invalid); invalid.flags.clear(); assert(!condition(prop(event, "trigger"), invalid));
});
test("EN/RU localization has BOM, complete references, real native labels and an installed illustration", () => {
    const refs = walk([...effectFile, ...event]).filter(n => ["title", "desc", "name", "custom_effect_tooltip"].includes(n.key)).map(n => n.value);
    for (const language of ["english", "russian"]) {
        const bytes = fs.readFileSync(path.join(mod, "localisation", language, `HSM_BAR_social_survey_l_${language}.yml`));
        assert(bytes.subarray(0, 3).equals(Buffer.from([239, 187, 191])));
        const text = bytes.toString("utf8"), keys = [...text.matchAll(/^ ([\w.]+):0 ".*"\r?$/gm)].map(m => m[1]);
        assert.equal(new Set(keys).size, keys.length); for (const ref of refs) assert(keys.includes(ref), ref);
        const installed = fs.readFileSync(path.join(eaw, "localisation", language, `eaw_ideas_l_${language}.yml`), "utf8");
        for (const ref of text.matchAll(/\$([^$]+)\$/g)) assert(installed.includes(" " + ref[1] + ":0"), ref[1]);
        assert(text.includes("\\n\\n"));
    }
    const sprites = walk(native("interface/eaw_eventpictures.gfx"));
    assert(sprites.some(n => n.key === "name" && n.value === prop(event, "picture")));
});
console.log(`RESULT: ${passed} passed, ${failed} failed; installed EaW: ${eaw}; no in-game execution.`);
if (failed) process.exitCode = 1;
