"use strict";
// Run: node tools/Test-BarradArchiveSkin.cjs
// Static asset checks; visual composition and live input still need an in-game playtest.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const repo = path.resolve(__dirname, "..");
const mod = path.join(repo, "mod/HoISubmod");
const game = process.env.HOI4_PATH || "C:/shit/Steam/steamapps/common/Hearts of Iron IV";
const eaw = process.env.EAW_PATH || "C:/shit/Steam/steamapps/workshop/content/394360/1826643372";

function parse(source, allowListValues = false) {
    const tokens = (source.match(/"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}]|[<>=!]+|[^\s{}<>=!#"]+/g) || []).filter(t => !t.startsWith("#"));
    const unquote = s => s?.startsWith('"') ? s.slice(1, -1) : s;
    let i = 0;
    function block(nested = false) {
        const out = [];
        while (i < tokens.length && tokens[i] !== "}") {
            const key = tokens[i++];
            assert.notEqual(key, "{", "Unexpected opening brace");
            if (allowListValues && !["=", "<", ">", "<=", ">=", "!="].includes(tokens[i])) {
                out.push({key: null, op: null, value: unquote(key)}); continue;
            }
            const op = tokens[i++];
            assert(["=", "<", ">", "<=", ">=", "!="].includes(op), `Unsupported syntax: ${key} ${op}`);
            let value = tokens[i++];
            if (value === "{") { value = block(true); assert.equal(tokens[i++], "}", "Unclosed block"); }
            else { assert.notEqual(value, "}", "Missing assignment value"); value = unquote(value); }
            assert.notEqual(value, undefined, "Truncated assignment");
            out.push({key, op, value});
        }
        if (!nested) assert.equal(i, tokens.length, "Unexpected closing brace");
        return out;
    }
    return block();
}
const prop = (b, k) => b.find(n => n.key === k)?.value;
const field = (b, k) => b.find(n => n.key?.toLowerCase() === k.toLowerCase())?.value;
function resolveAsset(file) {
    assert.equal(typeof file, "string", "Missing texture/font path");
    const result = [mod, eaw, game].map(root => path.join(root, file)).find(p => fs.existsSync(p));
    assert(result, "Missing asset: " + file);
    return result;
}
function loadArchiveAssets() {
    const sources = [resolveAsset("interface/core.gfx"), resolveAsset("interface/general_stuff.gfx"),
        resolveAsset("interface/browser.gfx"), resolveAsset("interface/eaw_state_lore.gfx"),
        ...fs.readdirSync(path.join(mod, "interface")).filter(file => file.endsWith(".gfx")).sort()
            .map(file => path.join(mod, "interface", file))];
    const sprites = {}, fonts = [], modNames = new Set();
    for (const file of new Set(sources)) {
        const source = parse(fs.readFileSync(file, "utf8"), true);
        for (const n of prop(source, "spriteTypes") || []) {
            const name = prop(n.value, "name");
            assert(name, "Unnamed sprite: " + file);
            if (file.startsWith(mod + path.sep)) {
                assert(!modNames.has(name), "Duplicate mod sprite: " + name); modNames.add(name);
            }
            sprites[name] = n.value;
        }
        fonts.push(...prop(source, "bitmapfonts") || []);
    }
    return {sprites, fonts};
}
function readTga(bytes, label = "TGA") {
    assert(bytes.length >= 18, label + ": truncated header");
    assert.equal(bytes[0], 0, label + ": unexpected image ID");
    assert.equal(bytes[1], 0, label + ": color maps are unsupported");
    assert.equal(bytes[2], 2, label + ": expected uncompressed true-color TGA");
    assert(bytes.subarray(3, 12).every(n => n === 0), label + ": nonzero color-map/origin fields");
    const w = bytes.readUInt16LE(12), h = bytes.readUInt16LE(14);
    assert(w > 0 && h > 0, label + ": empty image");
    assert.equal(bytes[16], 32, label + ": expected 32-bit BGRA");
    assert([8, 40].includes(bytes[17]), label + ": expected eight alpha bits and bottom/top origin");
    assert.equal(bytes.length, 18 + w * h * 4, label + ": truncated or excess pixel data");
    const topOrigin = (bytes[17] & 32) !== 0;
    return {w, h, pixel(x, y) {
        assert(Number.isInteger(x) && Number.isInteger(y) && x >= 0 && y >= 0 && x < w && y < h, label + ": sample outside frame");
        const offset = 18 + ((topOrigin ? y : h - 1 - y) * w + x) * 4;
        return [bytes[offset + 2], bytes[offset + 1], bytes[offset], bytes[offset + 3]];
    }};
}
function spriteDimensions(sprites, name) {
    const b = sprites[name]; assert(b, "Missing registered sprite: " + name);
    const texture = field(b, "texturefile"), file = resolveAsset(texture);
    const bytes = fs.readFileSync(file);
    let w, h;
    if (path.extname(file).toLowerCase() === ".tga") ({w, h} = readTga(bytes, name));
    else {
        assert.equal(path.extname(file).toLowerCase(), ".dds", name + ": unsupported texture format");
        assert(bytes.length >= 128, name + ": truncated DDS header");
        assert.equal(bytes.subarray(0, 4).toString(), "DDS ", name + ": invalid DDS signature");
        assert.equal(bytes.readUInt32LE(4), 124, name + ": invalid DDS header size");
        w = bytes.readUInt32LE(16); h = bytes.readUInt32LE(12);
    }
    const frames = Number(field(b, "noOfFrames") ?? 1);
    assert(Number.isInteger(frames) && frames > 0, name + ": invalid frame count");
    assert(w > 0 && h > 0 && w % frames === 0, name + ": frames do not divide texture width");
    return {w: w / frames, h};
}
function fontDefinition(fonts, name, lang = "english") {
    const choices = fonts.filter(n => prop(n.value, "name") === name);
    const chosen = choices.filter(n => prop(n.value, "languages")?.some(v => v.value === `l_${lang}`)).at(-1)
        || choices.filter(n => !prop(n.value, "languages")).at(-1);
    assert(chosen, "Missing font: " + name + "/" + lang);
    return chosen.value;
}
function luminance(rgb) {
    const linear = rgb.slice(0, 3).map(v => { const c = v / 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; });
    return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
}
function fontColor(b) {
    const value = prop(b, "color");
    assert.match(value || "", /^0x[\da-f]{8}$/i, "Expected ARGB font color");
    const argb = Number(value);
    assert.equal(argb >>> 24, 255, "Font ink must be opaque");
    return [argb >>> 16 & 255, argb >>> 8 & 255, argb & 255];
}
function contrast(a, b) { return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); }
function assertContrast(image, rect, colors, label, light = true) {
    const samples = [];
    for (let y = rect.y + 2; y < rect.y + rect.h - 2; y += 3) for (let x = rect.x + 2; x < rect.x + rect.w - 2; x += 3) {
        const pixel = image.pixel(x, y);
        assert.equal(pixel[3], 255, label + ": text surface must be opaque");
        samples.push(luminance(pixel));
    }
    assert(samples.length > 0, label + ": no contrast samples");
    // Allow local paper grain and markings, but require readable contrast over 95% of the text surface.
    if (light) assert(samples.filter(n => n >= 0.45).length / samples.length >= 0.95, label + ": paper is not light");
    for (const [name, rgb] of Object.entries(colors)) {
        const ink = luminance(rgb), ratios = samples.map(n => contrast(n, ink)).sort((a, b) => a - b);
        const lower = ratios[Math.floor(ratios.length * 0.05)];
        assert(lower >= 4.5, `${label}: ${name} contrast ${lower.toFixed(2)}:1 is below 4.5:1`);
    }
}
function framePixels(image, index, width) {
    assert(Number.isInteger(index) && index >= 0 && (index + 1) * width <= image.w, "Frame outside texture");
    const pixels = [];
    for (let y = 0; y < image.h; y++) for (let x = 0; x < width; x++) pixels.push(image.pixel(index * width + x, y));
    return pixels;
}
function assertArtwork(image, name) {
    const pixels = framePixels(image, 0, image.w);
    const visible = pixels.filter(p => p[3] > 0), opaque = pixels.filter(p => p[3] === 255);
    assert(opaque.length >= image.w * image.h * 0.1, name + ": insufficient opaque content");
    assert(new Set(visible.map(p => p.slice(0, 3).join(","))).size >= 2, name + ": blank/flat artwork");
}
function assertDistinct(a, b, name) {
    assert.deepEqual({w: a.w, h: a.h}, {w: b.w, h: b.h}, name + ": selected sprite changed dimensions");
    let different = 0;
    for (let y = 0; y < a.h; y++) for (let x = 0; x < a.w; x++) {
        const p = a.pixel(x, y), q = b.pixel(x, y);
        // Invisible RGB noise must not count as a visible selection indicator.
        if (Math.abs(p[3] - q[3]) >= 8 || p.slice(0, 3).some((c, k) => Math.abs(c * p[3] / 255 - q[k] * q[3] / 255) >= 8)) different++;
    }
    assert(different >= Math.max(4, Math.ceil(a.w * a.h * 0.005)), name + ": selected artwork is not visibly distinct");
}

module.exports = {parse, prop, field, resolveAsset, loadArchiveAssets, readTga, spriteDimensions, fontDefinition,
    fontColor, assertContrast, assertArtwork, assertDistinct};

if (require.main === module) {
    let passed = 0, failed = 0, checkedAssets = 0, checkedFrames = 0;
    function test(name, body) {
        try { body(); passed++; console.log("PASS " + name); }
        catch (e) { failed++; console.error("FAIL " + name + "\n" + e.stack); }
    }
    test("TGA validation rejects corrupt dimensions/alpha/data and invisible-only selection differences", () => {
        const bytes = Buffer.alloc(18 + 4 * 2 * 4);
        bytes[2] = 2; bytes.writeUInt16LE(4, 12); bytes.writeUInt16LE(2, 14); bytes[16] = 32; bytes[17] = 8;
        for (let i = 18; i < bytes.length; i += 4) { bytes[i] = i; bytes[i + 3] = 255; }
        const bottom = readTga(bytes);
        assert.deepEqual(bottom.pixel(0, 0), [0, 0, 34, 255]);
        const topBytes = Buffer.from(bytes); topBytes[17] = 40;
        assert.deepEqual(readTga(topBytes).pixel(0, 0), [0, 0, 18, 255]);
        assert.throws(() => bottom.pixel(4, 0), /outside frame/);
        assert.throws(() => framePixels(bottom, 2, 2), /outside texture/);
        for (const [offset, value] of [[1, 1], [2, 10], [12, 0], [16, 24], [17, 0]]) {
            const bad = Buffer.from(bytes); bad[offset] = value; assert.throws(() => readTga(bad));
        }
        assert.throws(() => readTga(bytes.subarray(0, -1)), /pixel data/);
        assert.throws(() => readTga(bytes.subarray(0, 12)), /header/);
        assert.throws(() => assertDistinct(bottom, bottom, "duplicate"), /not visibly distinct/);
        assert.throws(() => assertDistinct({w: 4, h: 4, pixel: () => [0, 0, 0, 0]}, {w: 4, h: 4, pixel: () => [255, 255, 255, 0]}, "invisible"), /not visibly distinct/);
        assert.throws(() => assertArtwork({w: 4, h: 4, pixel: () => [255, 255, 255, 0]}, "empty"), /opaque content/);
    });

    test("native button shader supplies four visual states; static background uses the same shader in every state", () => {
        const button = fs.readFileSync(resolveAsset("gfx/FX/buttonstate.shader"), "utf8");
        const background = fs.readFileSync(resolveAsset("gfx/FX/static_button.shader"), "utf8");
        for (const [effect, shader] of Object.entries({Up: "Up", Down: "Down", Disable: "Disable", Over: "Over"})) {
            assert.match(button, new RegExp(`Effect\\s+${effect}\\s*\\{[^}]*PixelShader\\s*=\\s*"PixelShader${shader}"`));
            assert.match(background, new RegExp(`Effect\\s+${effect}\\s*\\{[^}]*PixelShader\\s*=\\s*"PixelShaderUp"`));
        }
        const programs = Object.fromEntries([...button.matchAll(/MainCode\s+(PixelShader\w+)\s*\[\[([\s\S]*?)\]\]/g)].map(m => [m[1], m[2]]));
        for (const shader of ["Up", "Down", "Disable", "Over"]) assert.match(programs["PixelShader" + shader], /tex2D\(\s*MapTexture,\s*v\.vTexCoord\s*\)/);
        assert.match(programs.PixelShaderDown, /OutColor\.rgb\s*-=.*MixColor\.rgb/);
        assert.match(programs.PixelShaderOver, /OutColor\.rgb\s*\+=.*MixColor\.rgb/);
        assert.match(programs.PixelShaderDisable, /float\s+Grey\s*=\s*dot\(\s*OutColor\.rgb/);
        assert.match(programs.PixelShaderDisable, /OutColor\.rgb\s*=\s*float3\(Grey,\s*Grey,\s*Grey\)/);
    });

    test("textSpriteType rejects legacy_lazy_load while native spriteType may use it", () => {
        function validate(source) {
            for (const n of prop(source, "spriteTypes") || []) if (n.key === "textSpriteType") {
                assert.equal(field(n.value, "legacy_lazy_load"), undefined,
                    prop(n.value, "name") + ": legacy_lazy_load is invalid in textSpriteType");
            }
        }
        const core = parse(fs.readFileSync(path.join(game, "interface/core.gfx"), "utf8"), true);
        const nativeText = prop(core, "spriteTypes").find(n => prop(n.value, "name") === "GFX_error_log_button");
        assert.equal(nativeText.key, "textSpriteType");
        assert.equal(field(nativeText.value, "legacy_lazy_load"), undefined);
        assert(prop(core, "spriteTypes").some(n => n.key === "spriteType" && field(n.value, "legacy_lazy_load") === "no"));
        validate(core);
        for (const value of ["yes", "no"]) assert.throws(() => validate(parse(
            `spriteTypes = { textSpriteType = { name = "bad" legacy_lazy_load = ${value} } }`)), /legacy_lazy_load is invalid/);
        validate(parse('spriteTypes = { spriteType = { name = "valid" legacy_lazy_load = no } }'));
        validate(parse(fs.readFileSync(path.join(mod, "interface/HSM_BAR_archive_skin.gfx"), "utf8"), true));
    });

    let assets, skin, widgets, specs;
    test("skin GFX registers the folder, index, document/copy tabs, navigation, photo and audio controls", () => {
        skin = parse(fs.readFileSync(path.join(mod, "interface/HSM_BAR_archive_skin.gfx"), "utf8"), true);
        assets = loadArchiveAssets();
        const gui = prop(parse(fs.readFileSync(path.join(mod, "interface/HSM_BAR_archive.gui"), "utf8")), "guiTypes");
        const w = gui.find(n => prop(n.value, "name") === "HSM_BAR_archive_window"); assert(w);
        widgets = Object.fromEntries(w.value.filter(n => Array.isArray(n.value)).map(n => [prop(n.value, "name"), n.value]));
        specs = new Map([["GFX_HSM_BAR_archive_folder", [1000, 700, 1]], ["GFX_HSM_BAR_archive_index", [261, 34, 1]], ["GFX_HSM_BAR_archive_tab", [141, 34, 1]],
            ["GFX_HSM_BAR_archive_edition", [192, 30, 1]], ["GFX_HSM_BAR_archive_edition_selected", [192, 30, 1]],
            ["GFX_HSM_BAR_archive_audio", [36, 36, 1]]]);
        for (const key of ["prev", "next", "back", "close", "doc_5"]) {
            const b = widgets["HSM_BAR_archive_" + key]; assert(b, key);
            const name = prop(b, "quadTextureSprite");
            assert.match(name, /^GFX_HSM_BAR_archive_/, key + ": requires a scoped sprite binding");
            assert(!specs.has(name), key + ": requires its own icon artwork");
            specs.set(name, [36, 36, 1]);
        }
        assert.equal(prop(widgets.HSM_BAR_archive_doc_5, "quadTextureSprite"), "GFX_HSM_BAR_archive_photo");
        for (const c of ["echo", "entity", "reactor"]) {
            const b = widgets["HSM_BAR_archive_audio_" + c]; assert(b, c + ": missing audio control");
            assert.equal(prop(b, "quadTextureSprite"), "GFX_HSM_BAR_archive_audio");
            assert.equal(prop(b, "scale"), undefined, c + ": preserve native audio bounds");
        }
        for (const [name, width] of [["index", 261], ["tab", 141], ["photo", 36]]) specs.set("GFX_HSM_BAR_archive_" + name + "_selected", [width, name === "photo" ? 36 : 34, 1]);
        const registered = new Set((prop(skin, "spriteTypes") || []).map(n => prop(n.value, "name")));
        for (const name of specs.keys()) assert(registered.has(name), "Missing skin sprite: " + name);
    });
    if (specs && assets) for (const [name, [w, h, frames]] of specs) test(name + ": single-frame format, alpha, bounds, nonblank artwork and native shader", () => {
        const b = assets.sprites[name]; assert(b, name);
        assert.equal(Number(field(b, "noOfFrames") ?? 1), frames, name + ": frame count");
        const texture = field(b, "texturefile");
        const file = resolveAsset(texture);
        assert.equal(path.extname(texture).toLowerCase(), ".tga");
        assert(file.startsWith(mod + path.sep), name + ": custom texture must be supplied by the mod");
        const image = readTga(fs.readFileSync(file), name);
        assert.deepEqual({w: image.w, h: image.h}, {w: w * frames, h});
        assertArtwork(image, name);
        assert.deepEqual(spriteDimensions(assets.sprites, name), {w, h});
        assert.equal(field(b, "effectFile"), name.endsWith("_folder") ? "gfx/FX/static_button.lua" : "gfx/FX/buttonstate.lua");
        assert(!b.some(n => /animation/i.test(n.key)), name + ": sprite animation is not part of the skin");
        checkedAssets++; checkedFrames += frames;
    });

    test("custom control glyphs are distinct, antialiased and inset within equal-size buttons", () => {
        const controls = ["previous", "next", "back", "close", "photo", "audio"].map(name => {
            const file = resolveAsset(field(assets.sprites["GFX_HSM_BAR_archive_" + name], "texturefile"));
            const image = readTga(fs.readFileSync(file)), pixels = framePixels(image, 0, image.w);
            assert(new Set(pixels.map(p => p[3])).size >= 8, name + ": missing edge antialiasing");
            const glyph = [];
            for (let y = 0; y < image.h; y++) for (let x = 0; x < image.w; x++) {
                const p = image.pixel(x, y);
                if (p[3] >= 250 && luminance(p) > 0.7) glyph.push({x, y});
            }
            assert(glyph.length >= 16, name + ": unreadable or missing pale glyph");
            assert(glyph.every(p => p.x >= 7 && p.x < 29 && p.y >= 6 && p.y < 29), name + ": glyph touches its rim");
            return {name, image};
        });
        for (let i = 0; i < controls.length; i++) for (let j = i + 1; j < controls.length; j++) {
            assertDistinct(controls[i].image, controls[j].image, controls[i].name + "/" + controls[j].name);
        }
        assert(fs.existsSync(path.join(mod, "gfx/interface/HSM_BAR/archive/Lucide-LICENSE.txt")), "Ship the glyph license with the runtime assets");
    });

    test("index, document and photo selections have separate visibly distinct artwork", () => {
        assert(assets, "Skin registration must succeed first");
        for (const role of ["index", "tab", "photo", "edition"]) {
            const names = ["GFX_HSM_BAR_archive_" + role, "GFX_HSM_BAR_archive_" + role + "_selected"];
            const files = names.map(name => resolveAsset(field(assets.sprites[name], "texturefile")));
            assert.notEqual(files[0], files[1], role + ": selected artwork needs its own file");
            assertDistinct(...files.map(file => readTga(fs.readFileSync(file))), role);
        }
    });

    test("folder background and both mouse guards share an unanimated full-size texture", () => {
        assert(assets && widgets, "Skin registration must succeed first");
        for (const key of ["background", "input_floor", "input_shield"]) {
            const b = widgets["HSM_BAR_archive_" + key]; assert(b, key);
            assert.equal(prop(b, "quadTextureSprite"), "GFX_HSM_BAR_archive_folder");
        }
        const b = assets.sprites.GFX_HSM_BAR_archive_folder;
        assert.equal(field(b, "effectFile"), "gfx/FX/static_button.lua");
        assert(!b.some(n => /animation/i.test(n.key)), "Folder background must not animate");
        assert.deepEqual(spriteDimensions(assets.sprites, "GFX_HSM_BAR_archive_folder"), {w: 1000, h: 700});
    });

    test("archive fonts use native Latin/Cyrillic assets and opaque dark ink", () => {
        assert(assets && skin, "Skin registration must succeed first");
        const expected = {ink: ["hoi4_typewriter16", "hoi_16typewriter", "hoi_16typewriter_cryllic"], heading: ["hoi4_typewriter22", "hoi_22typewriter", "hoi_22typewriter_cryllic"], body: ["hoi_18", "hoi_18_cryllic"]};
        const skinFonts = new Set((prop(skin, "bitmapfonts") || []).map(n => prop(n.value, "name")));
        for (const key of ["ink", "heading"]) assert(skinFonts.has("HSM_BAR_archive_" + key));
        const redactions = parse(fs.readFileSync(path.join(mod, "interface/HSM_BAR_archive_redactions.gfx"), "utf8"), true);
        assert((prop(redactions, "bitmapfonts") || []).some(n => prop(n.value, "name") === "HSM_BAR_archive_body"));
        for (const [key, native] of Object.entries(expected)) for (const lang of ["english", "russian"]) {
            const b = fontDefinition(assets.fonts, "HSM_BAR_archive_" + key, lang);
            assert.deepEqual(prop(b, "fontfiles").map(n => n.value), native.map(name => "gfx/fonts/" + name));
            assert(luminance(fontColor(b)) <= 0.12, key + ": ink is not dark");
            for (const {value} of prop(b, "fontfiles")) {
                const fnt = fs.readFileSync(resolveAsset(value + ".fnt"), "utf8");
                assert.match(fnt, /^common lineHeight=\d+/m);
                assert.match(fnt, /^char id=\d+\s+.*xadvance=/m);
                // Native HOI fonts bind an atlas by fontfiles basename; BMFont page names may be stale or absent.
                const atlas = fs.readFileSync(resolveAsset(value + ".dds"));
                assert(atlas.length >= 128); assert.equal(atlas.subarray(0, 4).toString(), "DDS ");
                assert.equal(atlas.readUInt32LE(16), Number(fnt.match(/\bscaleW=(\d+)/)[1]), value + ": atlas width");
                assert.equal(atlas.readUInt32LE(12), Number(fnt.match(/\bscaleH=(\d+)/)[1]), value + ": atlas height");
            }
        }
        const body = fontDefinition(assets.fonts, "HSM_BAR_archive_body"), native = fontDefinition(assets.fonts, "hoi_18mbs");
        for (const key of ["G", "R", "Y", "H", "T", "g"]) {
            const color = prop(prop(body, "textcolors"), key)?.map(n => Number(n.value));
            assert(color?.length === 3 && color.every(n => Number.isInteger(n) && n >= 0 && n <= 255), "Missing/invalid body color: " + key);
            assert(luminance(color) <= 0.18, key + ": body color is too light");
            const old = prop(prop(native, "textcolors"), key)?.map(n => Number(n.value));
            if (old) assert(luminance(color) < luminance(old), key + ": body color was not darkened");
        }
    });

    test("light paper and control labels contrast with dark ink; folder status labels stay light", () => {
        assert(assets && widgets, "Skin registration must succeed first");
        const folder = readTga(fs.readFileSync(resolveAsset(field(assets.sprites.GFX_HSM_BAR_archive_folder, "texturefile"))));
        const failures = [];
        const checkContrast = (...args) => { try { assertContrast(...args); } catch (e) { failures.push(e.message); } };
        const paper = {case_title: "heading", classification: "ink", access: "ink", document_title: "heading",
            document_body: "body", photo_caption: "ink"};
        for (const [key, role] of Object.entries(paper)) {
            const b = widgets["HSM_BAR_archive_" + key]; assert(b, key);
            const name = prop(b, "font");
            // Document subheadings may use either native-sized ink or the typewriter heading.
            if (key === "document_title") assert(["HSM_BAR_archive_ink", "HSM_BAR_archive_heading"].includes(name));
            else assert.equal(name, "HSM_BAR_archive_" + role);
            const font = fontDefinition(assets.fonts, name), colors = {base: fontColor(font)};
            if (key === "document_body") for (const color of prop(font, "textcolors") || []) colors[color.key] = color.value.map(n => Number(n.value));
            const pos = prop(b, "position");
            checkContrast(folder, {x: Number(prop(pos, "x")), y: Number(prop(pos, "y")), w: Number(prop(b, "maxWidth")), h: Number(prop(b, "maxHeight"))}, colors, key);
        }
        const ink = fontColor(fontDefinition(assets.fonts, "HSM_BAR_archive_ink"));
        for (const [name, w] of [["index", 261], ["tab", 141], ["edition", 192]]) for (const suffix of ["", "_selected"]) {
            const image = readTga(fs.readFileSync(resolveAsset(field(assets.sprites["GFX_HSM_BAR_archive_" + name + suffix], "texturefile"))));
            checkContrast(image, {x: 8, y: 6, w: w - 16, h: 22}, {ink}, name + suffix);
        }
        const statuses = Object.entries(widgets).filter(([name]) => /^HSM_BAR_archive_case_\w+_status$/.test(name));
        assert.equal(statuses.length, 18);
        for (const [name, b] of [...statuses, ["HSM_BAR_archive_record_note", widgets.HSM_BAR_archive_record_note]]) {
            assert.equal(prop(b, "font"), "hoi_16mbs", name + ": retain native light status font");
            const rgb = fontColor(fontDefinition(assets.fonts, prop(b, "font")));
            assert(luminance(rgb) >= 0.8, name + ": status is not light");
            const pos = prop(b, "position");
            checkContrast(folder, {x: Number(prop(pos, "x")), y: Number(prop(pos, "y")), w: Number(prop(b, "maxWidth")), h: Number(prop(b, "maxHeight"))}, {status: rgb}, name, false);
        }
        assert.equal(failures.length, 0, failures.join("\n"));
    });
    console.log(`Barrad archive skin: ${passed} scenario groups passed, ${failed} failed; ${checkedAssets} textures / ${checkedFrames} frames validated.`);
    console.log("Static pixel/font validation only; no game rendering or live input acceptance is implied.");
    if (failed) process.exitCode = 1;
}
