"use strict";

// Original fictional field recordings, synthesized locally without voices or samples.
const fs = require("node:fs");
const path = require("node:path");
const rate = 44100, duration = 9;
const cases = ["echo", "entity", "reactor"];
function buildRecording(caseId) {
    if (!cases.includes(caseId)) throw Error("Unknown recording: " + caseId);
    const samples = new Float64Array(rate * duration);
    let seed = 1789 + cases.indexOf(caseId) * 104729, air = 0, rumble = 0;
    function noise() {
        seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
        return seed / 2147483648 - 1;
    }
    const sin = (hz, t) => Math.sin(2 * Math.PI * hz * t);
    for (let i = 0; i < samples.length; i++) {
        const t = i / rate, n = noise();
        air += 0.12 * (n - air);
        rumble += 0.004 * (n - rumble);
        let v = 0.026 * air + 0.003 * n;
        if (caseId === "echo") {
            v += 0.45 * rumble * (0.8 + 0.2 * sin(0.18, t));
            v += 0.011 * sin(137 + 0.4 * sin(0.4, t), t);
        } else if (caseId === "entity") {
            v += 0.55 * rumble;
            v += 0.012 * (sin(72, t) + sin(73.4, t)) * (0.65 + 0.3 * sin(0.22, t));
            v += 0.005 * sin(211, t) * Math.pow(Math.max(0, sin(0.31, t)), 3);
            // Spliced low-level silence, not an invented supernatural answer.
            if ((t > 3.5 && t < 3.74) || (t > 6.25 && t < 6.4)) v *= 0.12;
        } else {
            v += 0.32 * rumble;
            const flutter = t + 0.0005 * sin(0.61, t) + 0.00015 * sin(6.1, t);
            v += (0.025 * sin(96, flutter) + 0.012 * sin(192, flutter) + 0.006 * sin(384, flutter)) * (0.8 + 0.15 * sin(1.9, t));
            v += 0.025 * air * Math.pow(Math.max(0, sin(3.8, t)), 8);
        }
        samples[i] = v;
    }
    function strike(at, amplitude, pitch, decay) {
        const start = Math.round(at * rate), length = Math.ceil(decay * 7 * rate);
        for (let j = 0; j < length && start + j < samples.length; j++) {
            const t = j / rate, attack = Math.min(1, t / 0.004);
            const body = sin(pitch, t) + 0.41 * sin(pitch * 2.37, t) + 0.18 * sin(pitch * 4.13, t);
            samples[start + j] += amplitude * attack * (body * Math.exp(-t / decay) + 0.3 * noise() * Math.exp(-t / 0.017));
        }
    }
    if (caseId === "echo") {
        for (const at of [1.2, 1.52, 4.6, 4.92, 6.7]) {
            strike(at, 0.09, 247, 0.055);
            for (let bounce = 1; bounce <= 4; bounce++) strike(at + bounce * 0.192, 0.09 * Math.pow(0.5, bounce), 247, 0.08);
        }
    } else if (caseId === "entity") {
        for (const [at, amp] of [[1.4, 0.045], [2.05, 0.025], [4.4, 0.065], [6.8, 0.035]]) {
            strike(at, amp, 118, 0.22);
            strike(at + 0.43, amp * 0.26, 118, 0.32);
        }
    } else {
        for (let at = 0.72; at < 8.2; at += 0.79) strike(at, 0.035, 573, 0.034);
        strike(4.24, 0.05, 183, 0.18);
        strike(7.11, 0.04, 183, 0.18);
    }
    // DC blocking and cosine fades avoid boundary clicks; bounded peak leaves headroom.
    let previous = 0, filtered = 0, peak = 0;
    for (let i = 0; i < samples.length; i++) {
        const input = samples[i];
        filtered = input - previous + 0.995 * filtered;
        previous = input;
        const edge = Math.min(1, i / (rate * 0.45), (samples.length - 1 - i) / (rate * 0.65));
        samples[i] = filtered * (0.5 - 0.5 * Math.cos(Math.PI * edge));
        peak = Math.max(peak, Math.abs(samples[i]));
    }
    const bytes = Buffer.alloc(44 + samples.length * 2);
    bytes.write("RIFF", 0); bytes.writeUInt32LE(bytes.length - 8, 4); bytes.write("WAVEfmt ", 8);
    bytes.writeUInt32LE(16, 16); bytes.writeUInt16LE(1, 20); bytes.writeUInt16LE(1, 22);
    bytes.writeUInt32LE(rate, 24); bytes.writeUInt32LE(rate * 2, 28);
    bytes.writeUInt16LE(2, 32); bytes.writeUInt16LE(16, 34);
    bytes.write("data", 36); bytes.writeUInt32LE(samples.length * 2, 40);
    const gain = Math.min(3, 0.48 / peak);
    for (let i = 0; i < samples.length; i++) bytes.writeInt16LE(Math.round(samples[i] * gain * 32767), 44 + i * 2);
    return bytes;
}
if (require.main === module) {
    const output = path.resolve(__dirname, "../mod/HoISubmod/sound/HSM_BAR/archive");
    fs.mkdirSync(output, { recursive: true });
    for (const caseId of cases) {
        const bytes = buildRecording(caseId);
        fs.writeFileSync(path.join(output, caseId + ".wav"), bytes);
        console.log(`${caseId}.wav: ${duration}s, mono PCM16, ${rate}Hz, ${bytes.length} bytes`);
    }
}
module.exports = { buildRecording, cases, rate, duration };
