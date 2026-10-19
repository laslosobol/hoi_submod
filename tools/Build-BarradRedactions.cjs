"use strict";
// Deterministic inline UI marks, not generated artwork. Run with Node.js.
const fs = require("node:fs");
const path = require("node:path");
const output = path.resolve(__dirname, "../mod/HoISubmod/gfx/interface/HSM_BAR/archive");
fs.mkdirSync(output, {recursive: true});
for (const [name, width] of [["short", 50], ["long", 74], ["cut", 148]]) {
    const height = 18;
    const bytes = Buffer.alloc(18 + width * height * 4);
    bytes[2] = 2;
    bytes.writeUInt16LE(width, 12);
    bytes.writeUInt16LE(height, 14);
    bytes[16] = 32;
    bytes[17] = 8;
    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
        let alpha = 0;
        let tone = 255;
        if (name !== "cut") {
            if (x >= 1 && x < width - 1 && y >= 3 && y < 15) { alpha = 255; tone = 65; }
            if (x >= 2 && x < width - 2 && (x - 2) % 12 < 10 && y >= 4 && y < 14) { alpha = 255; tone = 255; }
        } else {
            tone = 80;
            const nick = (x >= 31 && x <= 33) || (x >= 89 && x <= 91) ? 1 : 0;
            if (x >= 4 && x < width - 4 && (y === 4 + nick || y === 13 - nick)) alpha = 190;
            const edge = [0, 1, 2, 1, 0][y % 5];
            if (y >= 4 && y <= 13 && (x === 2 + edge || x === width - 3 - edge)) alpha = 190;
        }
        if (!alpha) continue;
        const i = 18 + ((height - 1 - y) * width + x) * 4;
        bytes[i] = bytes[i + 1] = bytes[i + 2] = tone;
        bytes[i + 3] = alpha;
    }
    fs.writeFileSync(path.join(output, "redact_" + name + ".tga"), bytes);
    console.log(`Wrote redact_${name}.tga (${width}x${height})`);
}
