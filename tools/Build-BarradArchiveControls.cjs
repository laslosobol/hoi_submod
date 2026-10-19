"use strict";
// Paper tabs and antialiased metal controls. The folder artwork is generated separately.
const fs = require("node:fs");
const path = require("node:path");
const sharp = require("sharp");
const lucide = require("lucide");
const output = path.resolve(__dirname, "../mod/HoISubmod/gfx/interface/HSM_BAR/archive");
const source = path.resolve(__dirname, "../art/source/HSM_BAR_archive_controls");
fs.mkdirSync(output, { recursive: true });
fs.mkdirSync(source, { recursive: true });
const border = [129, 137, 124, 255], red = [132, 48, 48, 255];
function build(name, width, height, kind, selected = false) {
    const bytes = Buffer.alloc(18 + width * height * 4);
    bytes[2] = 2; bytes.writeUInt16LE(width, 12); bytes.writeUInt16LE(height, 14);
    bytes[16] = 32; bytes[17] = 8;
    function pixel(x, y, color) {
        if (x < 0 || y < 0 || x >= width || y >= height) return;
        const i = 18 + ((height - 1 - y) * width + x) * 4;
        [bytes[i], bytes[i + 1], bytes[i + 2], bytes[i + 3]] = [color[2], color[1], color[0], color[3]];
    }
    function rect(x, y, w, h, color) {
        for (let py = y; py < y + h; py++) for (let px = x; px < x + w; px++) pixel(px, py, color);
    }
    function line(x, y, endX, endY, color, weight = 1) {
        const dx = Math.abs(endX - x), sx = x < endX ? 1 : -1;
        const dy = -Math.abs(endY - y), sy = y < endY ? 1 : -1;
        let error = dx + dy;
        for (;;) {
            rect(x, y, weight, weight, color);
            if (x === endX && y === endY) break;
            const next = 2 * error;
            if (next >= dy) { error += dy; x += sx; }
            if (next <= dx) { error += dx; y += sy; }
        }
    }
    rect(3, 5, width - 4, height - 5, [12, 20, 16, 90]);
    const base = selected ? [242, 242, 229] : kind === "tab" ? [201, 211, 195] : [223, 226, 212];
    for (let y = 2; y < height - 2; y++) for (let x = 1; x < width - 2; x++) {
        if (y < 5 && (x < 5 - y || x > width - 6 + y)) continue;
        const grain = ((x * 17 + y * 31) % 7) - 3;
        pixel(x, y, [...base.map(v => v + grain), 255]);
    }
    line(4, 1, width - 5, 1, border);
    line(1, 5, 1, height - 3, border);
    line(width - 3, 5, width - 3, height - 3, border);
    line(2, height - 3, width - 3, height - 3, selected ? red : border);
    if (kind === "index") {
        rect(4, 5, selected ? 4 : 2, height - 12, selected ? red : [113, 128, 109, 255]);
        line(width - 13, 3, width - 4, 12, [177, 181, 165, 255]);
    } else if (kind === "tab") {
        if (selected) rect(6, height - 5, width - 13, 2, red);
    }
    fs.writeFileSync(path.join(output, name + ".tga"), bytes);
    console.log(`${name}.tga ${width}x${height}`);
}
for (const selected of [false, true]) {
    const suffix = selected ? "_selected" : "";
    build("index" + suffix, 261, 34, "index", selected);
    build("tab" + suffix, 141, 34, "tab", selected);
    build("edition" + suffix, 192, 30, "tab", selected);
}

async function buildIcon(name, icon, selected = false) {
    const glyph = icon.map(([tag, attrs]) => `<${tag} ${Object.entries(attrs).map(([k, v]) => `${k}="${v}"`).join(" ")}/>`).join("");
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 36 36">
<defs>
  <linearGradient id="rim" x2="0" y2="1"><stop stop-color="#b9b8a5"/><stop offset=".48" stop-color="#74796f"/><stop offset="1" stop-color="#414a43"/></linearGradient>
  <linearGradient id="face" x2="0" y2="1"><stop stop-color="${selected ? "#77504a" : "#4c5851"}"/><stop offset="1" stop-color="${selected ? "#482f2c" : "#26332d"}"/></linearGradient>
</defs>
<rect x="1" y="2" width="34" height="33" rx="5" fill="#111b16" fill-opacity=".65"/>
<rect x="1.5" y="1.5" width="33" height="32" rx="4" fill="url(#rim)" stroke="#19241e"/>
<rect x="3" y="3" width="30" height="29" rx="3" fill="url(#face)" stroke="${selected ? "#d0b477" : "#909789"}" stroke-width=".6"/>
<path d="M6 4h24" stroke="#e0dfcd" stroke-opacity=".25"/>
<g transform="translate(7 6.5) scale(.9166667)" fill="none" stroke="#f1efdb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${glyph}</g>
${selected ? '<path d="M12 30h12" stroke="#e1c48a" stroke-width="1.5" stroke-linecap="round"/>' : ""}
</svg>\n`;
    // Render at 4x before downsampling so diagonal strokes remain smooth at native game size.
    const rgba = await sharp(Buffer.from(svg), {density: 288}).resize(36, 36).ensureAlpha().raw().toBuffer();
    const bytes = Buffer.alloc(18 + 36 * 36 * 4);
    bytes[2] = 2; bytes.writeUInt16LE(36, 12); bytes.writeUInt16LE(36, 14);
    bytes[16] = 32; bytes[17] = 8;
    for (let y = 0; y < 36; y++) for (let x = 0; x < 36; x++) {
        const src = (y * 36 + x) * 4, dst = 18 + ((35 - y) * 36 + x) * 4;
        bytes[dst] = rgba[src + 2]; bytes[dst + 1] = rgba[src + 1]; bytes[dst + 2] = rgba[src]; bytes[dst + 3] = rgba[src + 3];
    }
    fs.writeFileSync(path.join(source, name + ".svg"), svg);
    fs.writeFileSync(path.join(output, name + ".tga"), bytes);
    console.log(`${name}.tga 36x36 (Lucide, 4x antialiasing)`);
}
async function main() {
    for (const [name, icon] of [["previous", lucide.ChevronLeft], ["next", lucide.ChevronRight], ["back", lucide.Undo2],
        ["close", lucide.X], ["photo", lucide.Image], ["audio", lucide.Play]]) await buildIcon(name, icon);
    await buildIcon("photo_selected", lucide.Image, true);
    const license = path.join(path.dirname(require.resolve("lucide/package.json")), "LICENSE");
    fs.copyFileSync(license, path.join(source, "Lucide-LICENSE.txt"));
    fs.copyFileSync(license, path.join(output, "Lucide-LICENSE.txt"));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
