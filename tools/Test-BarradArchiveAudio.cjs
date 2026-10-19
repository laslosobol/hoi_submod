"use strict";
// Static sound registration and actual PCM checks; not an in-engine listening test.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const {buildRecording, cases, rate, duration} = require("./Build-BarradArchiveAudio.cjs");
const {parse} = require("./Test-BarradCases.cjs");
const {prop, read, gui, effects, triggers, fresh, open, locate, condition, run} = require("./Test-BarradArchive.cjs");
const mod = path.resolve(__dirname, "../mod/HoISubmod");
const asset = parse(read("sound/HSM_BAR_archive.asset"));
const widgets = gui.find(n => prop(n.value, "name") === "HSM_BAR_archive_window").value;
const ids = {echo: 14, entity: 3, reactor: 5};
let passed = 0, failed = 0;
function test(name, fn) {
    try { fn(); passed++; console.log("PASS " + name); }
    catch (e) { failed++; console.error("FAIL " + name + "\n" + e.stack); }
}
function pcm(bytes) {
    assert(bytes.length >= 44);
    assert.equal(bytes.toString("ascii", 0, 4), "RIFF");
    assert.equal(bytes.readUInt32LE(4), bytes.length - 8);
    assert.equal(bytes.toString("ascii", 8, 16), "WAVEfmt ");
    assert.equal(bytes.readUInt32LE(16), 16);
    assert.equal(bytes.readUInt16LE(20), 1, "PCM required");
    assert.equal(bytes.readUInt16LE(22), 1, "mono required");
    assert.equal(bytes.readUInt32LE(24), rate);
    assert.equal(bytes.readUInt32LE(28), rate * 2);
    assert.equal(bytes.readUInt16LE(32), 2);
    assert.equal(bytes.readUInt16LE(34), 16);
    assert.equal(bytes.toString("ascii", 36, 40), "data");
    assert.equal(bytes.readUInt32LE(40), bytes.length - 44);
    assert.equal((bytes.length - 44) / 2, rate * duration);
    return Array.from({length: (bytes.length - 44) / 2}, (_, i) => bytes.readInt16LE(44 + i * 2) / 32768);
}
function fixture(caseId, stage = "investigated") {
    const s = fresh(); open(s);
    locate(s, caseId);
    s.vars.HSM_BAR_archive_case = ids[caseId];
    s.vars.HSM_BAR_archive_document = 2;
    s.flags.add(stage === "study" ? `HSM_BAR_study_${caseId}_done` : `HSM_BAR_case_${caseId}_${stage}`);
    return s;
}
for (const c of cases) {
    const name = "HSM_BAR_archive_audio_" + c;
    const sound = asset.find(n => n.key === "sound" && prop(n.value, "name") === "HSM_BAR_archive_recording_" + c)?.value;
    const effect = asset.find(n => n.key === "soundeffect" && prop(n.value, "name") === name)?.value;
    const bytes = fs.readFileSync(path.join(mod, "sound", prop(sound, "file")));
    test(c + ": native GUI registration, no loops or same-clip stacking", () => {
        assert.equal(prop(sound, "file"), `HSM_BAR/archive/${c}.wav`);
        assert.equal(prop(prop(effect, "sounds"), "sound"), prop(sound, "name"));
        assert.equal(prop(effect, "loop"), "no");
        assert.equal(prop(effect, "is3d"), "no");
        assert.equal(prop(effect, "max_audible"), "1");
        assert.equal(prop(effect, "max_audible_behaviour"), "fail");
        assert(Number(prop(effect, "volume")) <= 0.65);
        const button = widgets.find(n => n.key === "buttonType" && prop(n.value, "name") === name)?.value;
        assert.equal(prop(button, "clicksound"), name);
        assert.equal(prop(button, "pdx_tooltip"), name + "_tt");
        assert.equal(prop(button, "quadTextureSprite"), "GFX_HSM_BAR_archive_audio");
        assert.deepEqual(effects[name + "_click"], [], "Playback must not alter game state");
        const s = fixture(c), before = structuredClone(s); run(effects[name + "_click"], s); assert.deepEqual(s, before);
    });
    test(c + ": decodable PCM16 with bounded peak, DC and fades", () => {
        const values = pcm(bytes);
        let peak = 0, sum = 0, squares = 0, maxStep = 0;
        for (let i = 0; i < values.length; i++) {
            peak = Math.max(peak, Math.abs(values[i])); sum += values[i]; squares += values[i] ** 2;
            if (i) maxStep = Math.max(maxStep, Math.abs(values[i] - values[i - 1]));
        }
        const rms = Math.sqrt(squares / values.length), mean = sum / values.length;
        assert(peak > 0.08 && peak <= 0.481, "Blank/clipped or unexpected peak: " + peak);
        assert(rms > 0.005 && rms < 0.15, "Unexpected RMS: " + rms);
        assert(Math.abs(mean) < 0.001, "DC offset: " + mean);
        assert(maxStep < 0.22, "Abrupt sample discontinuity: " + maxStep);
        assert.equal(values[0], 0); assert.equal(values.at(-1), 0);
        for (const edge of [values.slice(0, 441), values.slice(-441)]) assert(edge.every(v => Math.abs(v) < 0.002), "Missing fade");
        console.log(`  ${duration}s; peak=${peak.toFixed(4)}, RMS=${rms.toFixed(4)}, DC=${mean.toExponential(2)}`);
    });
    test(c + ": reproducible original asset, distinct nonempty recording", () => {
        assert(bytes.equals(buildRecording(c)), "Audio asset drift: rebuild or review the change");
        for (const other of cases.filter(x => x !== c)) assert(!bytes.equals(buildRecording(other)));
    });
    test(c + ": investigation required; historical playback survives loss of current access", () => {
        for (const suffix of ["visible", "click_enabled"]) {
            const guard = triggers[name + "_" + suffix]; assert(guard);
            for (const stage of ["investigated", "study"]) {
                const s = fixture(c, stage); assert(condition(guard, s));
                s.access.clear(); assert(condition(guard, s));
                for (const copy of [undefined, 1, 2, 3, 99]) {
                    s.vars.HSM_BAR_archive_copy = copy; assert(condition(guard, s));
                }
            }
            assert(!condition(guard, fixture(c, "known")));
            assert(!condition(guard, fixture(c, "rumor")));
            for (const doc of [0, 1, 3, 4, 5, 99]) {
                const s = fixture(c); s.vars.HSM_BAR_archive_document = doc; assert(!condition(guard, s));
            }
            for (let id = 0; id <= 19; id++) {
                if (id === ids[c]) continue;
                const s = fixture(c); s.vars.HSM_BAR_archive_case = id; assert(!condition(guard, s));
            }
        }
    });
    test(c + ": foreign, AI, closed archive and missing Service gates cannot expose playback", () => {
        for (const suffix of ["visible", "click_enabled"]) {
            const guard = triggers[name + "_" + suffix];
            for (const flag of fresh().flags) {
                const s = fixture(c); s.flags.delete(flag); assert(!condition(guard, s));
            }
            const foreign = fixture(c); foreign.tag = "EQS"; assert(!condition(guard, foreign));
            const ai = fixture(c); ai.ai = true; assert(!condition(guard, ai));
            const closed = fixture(c); delete closed.vars.HSM_BAR_archive_open; assert(!condition(guard, closed));
        }
    });
}
test("sound identifiers are unique; UI category contains only the three attachments", () => {
    assert.equal(asset.length, 7);
    for (const type of ["sound", "soundeffect"]) {
        const names = asset.filter(n => n.key === type).map(n => prop(n.value, "name"));
        assert.equal(names.length, 3); assert.equal(new Set(names).size, 3);
    }
    const category = prop(asset, "category"); assert.equal(prop(category, "name"), "UI");
    assert.deepEqual(prop(category, "soundeffects").map(n => n.key), cases.map(c => "HSM_BAR_archive_audio_" + c));
});
test("audio tooltips have BOM, EN/RU parity, valid redaction keys and explicit duration", () => {
    for (const language of ["english", "russian"]) {
        const source = read(`localisation/${language}/HSM_BAR_archive_audio_l_${language}.yml`);
        assert(source.startsWith(`\uFEFFl_${language}:`));
        const lines = source.trimEnd().split(/\r?\n/).slice(1);
        assert.equal(lines.length, 3);
        const seen = new Set();
        for (const line of lines) {
            const m = line.match(/^ (HSM_BAR_archive_audio_(echo|entity|reactor)_tt):0 "([^"\r\n]*)"$/);
            assert(m, "Malformed audio tooltip: " + line); assert(!seen.has(m[1])); seen.add(m[1]);
            assert(m[3].includes("9 "));
            assert(!m[3].includes("$"), "Audio tooltip has an unresolved localization substitution");
            for (const ref of m[3].matchAll(/£(\w+)£/g)) assert(read("interface/HSM_BAR_archive_redactions.gfx").includes(`name = \"GFX_${ref[1]}\"`), "Unknown redaction sprite: " + ref[1]);
        }
    }
});
test("corrupt or incompatible WAV headers are rejected", () => {
    const bytes = buildRecording("echo");
    assert.throws(() => pcm(bytes.subarray(0, 30)));
    for (const offset of [0, 4, 8, 16, 20, 22, 24, 28, 32, 34, 36, 40]) {
        const bad = Buffer.from(bytes); bad[offset] ^= 0xff; assert.throws(() => pcm(bad));
    }
});
console.log(`Barrad archive audio: ${passed} scenario groups passed, ${failed} failed; three original 9-second field recordings.`);
console.log("No native playback or subjective listening quality is certified by this suite.");
if (failed) process.exitCode = 1;
