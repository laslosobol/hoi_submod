"use strict";

// Run: node tools/Test-BarradFocusPresentation.cjs [--fixtures-only]
// Static contract checks, not a HOI4 renderer or an MP privacy guarantee.
// Text selectors use the documented localization Scope.Player promotion.
// Icons intentionally retain the documented SP-only is_ai approximation.
// Actual sprite/texture existence is checked by Test-BarradContent.ps1 after art
// integration. Here, both sprite branch bindings and their order are checked.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const root = path.join(__dirname, "..", "mod", "HoISubmod");
const helper = "HSM_BAR_show_service_identity";
const args = process.argv.slice(2);
assert(args.every(arg => arg === "--fixtures-only"), "Unknown command-line argument");
const fixtureOnly = args.includes("--fixtures-only");
let passed = 0, failed = 0;
function test(name, body) {
    try { body(); passed++; console.log("PASS " + name); }
    catch (error) { failed++; console.error("FAIL " + name + "\n" + error.stack); }
}

// The existing Barrad tests use the same small assignment/block subset. Keep
// quotes/comments intact and inspect direct children, never nested decoy keys.
function parse(text) {
    const scanner = /"(?:\\.|[^"\\])*"|#[^\r\n]*|\s+|[{}]|(?:<=|>=|!=|=|<|>)|[^\s{}=<>!#"]+/gy;
    const tokens = [];
    let offset = 0;
    while (offset < text.length) {
        scanner.lastIndex = offset;
        const match = scanner.exec(text);
        assert(match, "Invalid or unterminated token at offset " + offset);
        offset = scanner.lastIndex;
        if (!/^\s|^#/.test(match[0])) tokens.push(match[0]);
    }
    let i = 0;
    function block(nested = false) {
        const out = [];
        while (i < tokens.length && tokens[i] !== "}") {
            const key = tokens[i++];
            assert(!["{", "=", "<", ">", "<=", ">=", "!="].includes(key), "Missing assignment key");
            if (!["=", "<", ">", "<=", ">=", "!="].includes(tokens[i])) {
                assert(nested, "Unassigned top-level token " + key);
                out.push({key, op: null, value: null});
                continue;
            }
            const op = tokens[i++];
            let value = tokens[i++];
            assert(value !== undefined && value !== "}", "Missing value for " + key);
            if (value === "{") {
                value = block(true);
                assert.equal(tokens[i++], "}", "Unclosed block " + key);
            } else {
                assert(!["=", "<", ">", "<=", ">=", "!="].includes(value), "Invalid value for " + key);
            }
            out.push({key, op, value});
        }
        if (!nested) assert.equal(i, tokens.length, "Unexpected closing brace");
        return out;
    }
    return block();
}
const read = file => parse(fs.readFileSync(path.join(root, file), "utf8"));
function field(nodes, key, required = true) {
    assert(Array.isArray(nodes), "Expected a block containing " + key);
    const found = nodes.filter(node => node.key === key);
    assert(found.length <= 1, "Duplicate field " + key);
    if (required) assert.equal(found.length, 1, "Missing field " + key);
    if (found.length) assert.equal(found[0].op, "=", "Invalid assignment for " + key);
    return found[0]?.value;
}
function sprites(focus) {
    const icon = field(focus, "icon");
    if (typeof icon === "string") {
        assert(/^GFX_\w+$/.test(icon), "Invalid scalar sprite");
        return {dynamic: false, branches: [{sprite: icon, condition: "yes"}]};
    }
    assert(Array.isArray(icon) && icon.length, "Empty icon selector");
    const seen = new Set();
    const branches = icon.map(node => {
        assert.equal(node.op, "=", "Invalid icon assignment");
        assert(/^GFX_\w+$/.test(node.key), "Invalid sprite branch " + node.key);
        assert(!seen.has(node.key), "Duplicate sprite branch " + node.key);
        seen.add(node.key);
        assert(Array.isArray(node.value) || ["yes", "no"].includes(node.value), "Invalid icon condition");
        return {sprite: node.key, condition: node.value};
    });
    return {dynamic: true, branches};
}
function assertFocus(focus) {
    const id = field(focus, "id"), selector = sprites(focus);
    assert(/^HSM_BAR_dir_\w+$/.test(id), "Unexpected Service focus ID");
    assert.equal(field(focus, "dynamic"), "yes", "Missing dynamic = yes");
    assert(selector.dynamic, "Expected conditional icon");
    assert.equal(selector.branches.length, 2, "Expected exactly internal and cover branches");
    const [internal, cover] = selector.branches;
    assert.equal(internal.sprite, "GFX_" + id, "Wrong internal sprite or branch order");
    assert.deepEqual(internal.condition, parse(helper + " = yes"), "Internal icon bypasses published helper");
    assert(/^GFX_HSM_BAR_cover_\w+$/.test(cover.sprite), "Missing civilian cover sprite");
    assert.equal(cover.condition, "yes", "Cover must be an unconditional final fallback");
    return selector;
}
function texts(selector) {
    assert.equal(field(selector, "name").startsWith("GetHSMBAR_"), true, "Wrong selector namespace");
    const choices = selector.filter(node => node.key === "text");
    assert.equal(choices.length, 2, "Expected exactly internal and cover texts");
    for (const choice of choices) assert.equal(choice.op, "=");
    assert.deepEqual(field(choices[0].value, "trigger"), parse("tag = BAR"), "Text must test Player tag, not country AI");
    assert.equal(field(choices[1].value, "trigger", false), undefined, "Cover text must be unconditional");
    const keys = choices.map(choice => field(choice.value, "localization_key"));
    assert(keys.every(key => typeof key === "string" && /^HSM_BAR_\w+$/.test(key)), "Invalid text key");
    assert.notEqual(keys[0], keys[1], "Internal and cover text keys are identical");
    return keys;
}
function localization(language) {
    const dir = path.join(root, "localisation", language), keys = new Map();
    for (const name of fs.readdirSync(dir).filter(name => /^HSM_BAR.*\.yml$/.test(name)).sort()) {
        const content = fs.readFileSync(path.join(dir, name), "utf8");
        for (const [index, line] of content.replace(/^\uFEFF/, "").split(/\r?\n/).entries()) {
            if (!line.trim() || /^\s*#|^l_(english|russian):\s*$/.test(line)) continue;
            const match = /^\s*([^ #:\s]+):\d*\s+"(.*)"\s*$/.exec(line);
            assert(match, `Malformed localization ${name}:${index + 1}`);
            assert(!keys.has(match[1]), "Duplicate localization " + match[1]);
            keys.set(match[1], match[2]);
        }
    }
    return keys;
}

const validFocus = `id = HSM_BAR_dir_fixture
icon = {
 GFX_HSM_BAR_dir_fixture = { ${helper} = yes }
 GFX_HSM_BAR_cover_fixture = yes
}
dynamic = yes`;
const validText = `name = GetHSMBAR_fixture
text = { trigger = { tag = BAR } localization_key = HSM_BAR_fixture_secret }
text = { localization_key = HSM_BAR_fixture_cover }`;
test("fixture: scalar icon reader remains supported", () => {
    assert.deepEqual(sprites(parse("icon = GFX_example")), {
        dynamic: false, branches: [{sprite: "GFX_example", condition: "yes"}]
    });
});
test("fixture: conditional icons retain direct-child order", () => {
    assert.equal(assertFocus(parse(validFocus)).branches[1].sprite, "GFX_HSM_BAR_cover_fixture");
});
test("fixture: nested conditions, comments, quoted braces and fake icons stay isolated", () => {
    const body = parse(`icon = {
 GFX_first = { OR = { tag = BAR NOT = { is_ai = yes } } }
 GFX_last = yes
}
completion_reward = { icon = GFX_nested log = "brace } # icon = GFX_quoted" }
# icon = GFX_comment`);
    assert.deepEqual(sprites(body).branches.map(branch => branch.sprite), ["GFX_first", "GFX_last"]);
    assert.deepEqual(sprites(body).branches[0].condition, parse("OR = { tag = BAR NOT = { is_ai = yes } }"));
});
test("fixture: bare focus lists do not break token reading", () => {
    const body = parse(validFocus + " search_filters = { FOCUS_FILTER_RESEARCH FOCUS_FILTER_POLITICAL }");
    assertFocus(body);
});
for (const [name, source] of [
    ["unclosed block", "icon = { GFX_a = yes"],
    ["extra closing brace", "icon = GFX_a }"],
    ["unterminated string", 'icon = "GFX_a'],
    ["missing value", "icon ="],
    ["invalid operator", "icon == GFX_a"]
]) test("fixture rejects " + name, () => assert.throws(() => parse(source)));
for (const [name, source] of [
    ["empty selector", "icon = { }"],
    ["duplicate icon field", "icon = GFX_a icon = GFX_b"],
    ["duplicate sprite branch", "icon = { GFX_a = yes GFX_a = no }"],
    ["non-sprite branch", "icon = { BAD = yes }"],
    ["invalid condition", "icon = { GFX_a = maybe }"]
]) test("fixture rejects " + name, () => assert.throws(() => sprites(parse(source))));
for (const [name, source] of [
    ["missing dynamic", validFocus.replace("dynamic = yes", "dynamic = no")],
    ["unconditional secret", validFocus.replace(`{ ${helper} = yes }`, "yes")],
    ["wrong helper", validFocus.replace(helper, "HSM_BAR_not_the_gate")],
    ["conditional fallback", validFocus.replace("GFX_HSM_BAR_cover_fixture = yes", "GFX_HSM_BAR_cover_fixture = { tag = BAR }")],
    ["wrong paired sprite", validFocus.replace("GFX_HSM_BAR_dir_fixture", "GFX_HSM_BAR_dir_other")],
    ["fallback first", validFocus.replace(`GFX_HSM_BAR_dir_fixture = { ${helper} = yes }\n GFX_HSM_BAR_cover_fixture = yes`, `GFX_HSM_BAR_cover_fixture = yes\n GFX_HSM_BAR_dir_fixture = { ${helper} = yes }`)]
]) test("fixture rejects " + name, () => assert.throws(() => assertFocus(parse(source))));
test("fixture: Player selector has a real unconditional cover", () => {
    assert.deepEqual(texts(parse(validText)), ["HSM_BAR_fixture_secret", "HSM_BAR_fixture_cover"]);
});
test("fixture rejects AI-gated text, conditional cover and duplicate text keys", () => {
    assert.throws(() => texts(parse(validText.replace("tag = BAR", "BAR = { is_ai = no }"))));
    assert.throws(() => texts(parse(validText.replace("text = { localization_key", "text = { trigger = { tag = BAR } localization_key"))));
    assert.throws(() => texts(parse(validText.replace("HSM_BAR_fixture_cover", "HSM_BAR_fixture_secret"))));
});

if (!fixtureOnly) {
    let trigger, focuses, selectors, loc;
    test("published icon helper is exactly the documented BAR AI/route check", () => {
        const file = read("common/scripted_triggers/HSM_BAR_presentation.txt");
        assert.equal(file.length, 1, "Unexpected presentation triggers");
        trigger = field(file, helper);
        assert.deepEqual(trigger, parse("BAR = { is_ai = no has_country_flag = HSM_BAR_directorate }"));
        const comment = fs.readFileSync(path.join(root, "common/scripted_triggers/HSM_BAR_presentation.txt"), "utf8");
        assert(/single-player/.test(comment) && /NOT per-viewer secrecy in multiplayer/.test(comment), "Missing explicit MP limitation");
    });
    function identity(nodes, bar, scope = "BAR") {
        return nodes.every(node => {
            assert.equal(node.op, "=");
            if (node.key === "BAR") return identity(node.value, bar, "BAR");
            if (node.key === "tag") return scope === node.value;
            if (node.key === "is_ai") { assert.equal(scope, "BAR"); return bar.ai === (node.value === "yes"); }
            if (node.key === "has_country_flag") { assert.equal(scope, "BAR"); return bar.flags.has(node.value); }
            throw Error("Unsupported presentation condition " + node.key);
        });
    }
    test("published helper: active human BAR internal; AI BAR and inactive route covered", () => {
        assert(trigger, "Published trigger did not load");
        assert(identity(trigger, {ai: false, flags: new Set(["HSM_BAR_directorate"])}));
        assert(!identity(trigger, {ai: true, flags: new Set(["HSM_BAR_directorate"])}));
        assert(!identity(trigger, {ai: false, flags: new Set()}));
    });
    test("known MP limitation: icon helper is identical for BAR and foreign viewers", () => {
        assert(trigger, "Published trigger did not load");
        const bar = {ai: false, flags: new Set(["HSM_BAR_directorate"])};
        assert(identity(trigger, bar, "BAR"));
        assert(identity(trigger, bar, "EQS"), "This is explicitly not a per-viewer icon gate");
        assert(identity(parse("tag = BAR"), bar, "BAR"));
        assert(!identity(parse("tag = BAR"), bar, "EQS"));
    });
    test("production has exactly 34 unique Service focuses", () => {
        focuses = read("common/national_focus/HSM_BAR_directorate.txt")
            .filter(node => node.key === "shared_focus").map(node => node.value);
        assert.equal(focuses.length, 34);
        assert.equal(new Set(focuses.map(focus => field(focus, "id"))).size, 34);
    });
    test("load published Player selectors and EN/RU localization without duplicates", () => {
        selectors = new Map();
        const dir = path.join(root, "common", "scripted_localisation");
        for (const name of fs.readdirSync(dir).filter(name => /^HSM_BAR.*\.txt$/.test(name)).sort()) {
            for (const node of read("common/scripted_localisation/" + name)) {
                if (node.key !== "defined_text") continue;
                const id = field(node.value, "name");
                if (!id.startsWith("GetHSMBAR_")) continue;
                assert(!selectors.has(id), "Duplicate selector " + id);
                selectors.set(id, node.value);
            }
        }
        loc = {english: localization("english"), russian: localization("russian")};
        assert.equal(selectors.size, 68, "Expected 34 title/description pairs");
    });
    for (const focus of focuses || []) {
        const id = field(focus, "id"), short = id.replace(/^HSM_BAR_dir_/, "");
        test("paired internal/cover dynamic sprites: " + id, () => assertFocus(focus));
        for (const suffix of ["", "_desc"]) {
            const selector = "GetHSMBAR_" + short + suffix;
            test("Player selector and EN/RU branches: " + selector, () => {
                assert(selectors?.has(selector), "Missing published selector " + selector);
                const keys = texts(selectors.get(selector));
                for (const language of ["english", "russian"]) {
                    assert.equal(loc?.[language].get(id + suffix), "[Player." + selector + "]", "Wrong Player wrapper: " + language);
                    for (const key of keys) assert(loc[language].get(key)?.trim(), "Missing or empty " + language + " text " + key);
                    assert.notEqual(loc[language].get(keys[0]), loc[language].get(keys[1]), "Identical internal/cover wording: " + language);
                }
            });
        }
    }
}
console.log(`Barrad focus presentation: ${passed} passed; ${failed} failed${fixtureOnly ? " (fixtures only; production NOT checked)" : "; 34 focus contracts expected"}.`);
console.log("Engine rendering, focus localization caching and simultaneous MP behavior: UNVERIFIED. Sprite file existence: delegated to integration checks.");
if (failed) process.exitCode = 1;
