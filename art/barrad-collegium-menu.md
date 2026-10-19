# Collegium Faculty Journals

Four original laboratory folios for the friendship-route research menu, implemented on
2026-10-07. This is an open academic archive, not the Service's censored casebook.
Project rules, the original 24 projects and two optional joint dossiers are documented
in [Collegium research journals](../docs/barrad-collegium-projects.md).

## Artwork

| Faculty | PNG source in art/source | Material and apparatus |
| --- | --- | --- |
| Viira | HSM_BAR_mtk_viira.png | Cyan-grey linen, nickel, prism and optical interference plate |
| Leopold | HSM_BAR_mtk_leopold.png | Graphite workshop board, brass, crystal drive and measuring tool |
| Silver Star | HSM_BAR_mtk_silver.png | Burgundy clinical folio, ampoules, gauge and instrument case |
| Asinti | HSM_BAR_mtk_asinti.png | Pine-green cloth, ritual tray, empty vessel and suspended weight |

Sources were generated with the built-in image tool; the three later faculties used the
accepted Viira image as a layout reference. Runtime backgrounds are opaque 1000x700
32-bit TGAs in `gfx/interface/HSM_BAR/mtk/<faculty>.tga`. There are no baked labels,
hands, characters, censorship marks or heraldry. Apparatus illustrations establish each
faculty's discipline; no separate project photograph is presented as historical evidence.

Nineteen code-native control textures use Lucide 1.8.0 symbols and Sharp 0.35.4 at 4x
sampling: eight faculty states, eight project states, two document states and one action
plate. Editable SVGs and the Lucide license are in `art/source/HSM_BAR_mtk_controls/`;
the license also ships beside the TGAs. The approved archive close button and native
font assets are reused. Buttons use native hover/pressed/disabled shaders; backgrounds
use the static shader. Selection changes remain visible without resizing hitboxes.

The 1000x700 window has a fixed left index and one clean writing surface. Live paper
content stays inside x=334..946, y=184..654. Nothing is placed on layered paper edges.
Narrative body and the separate technical ledger use the same 612x296 scrolling
viewport on different pages; numerical effects never overlay a narrative document.
Faculty tabs occupy a separate dark header band.

The interactive experiment revision retains four original backgrounds and adds eight
294x40 faculty-themed choice sprites plus one 32x32 Lucide calculator control.
There are 32 sprites in total: four backgrounds and 28 controls.
Seven compact project buttons plus **Laboratory** stop at y=506, before
the apparatus illustrations. Joint dossiers appear in both participating faculties.
The laboratory has apparatus choices at y=344, controls at y=438, and workshop
scheduling at y=528. On reaching the observation checkpoint, a report replaces the
preparation controls and two authored follow-up actions occupy y=528. Starts and
cancellation remain at y=618, visible only in the laboratory. The calculator at
(910,222) opens the technical ledger; it does not mutate gameplay state.
Each opus exposes an **Origins** button on its paper header and a scrolling collection
of its five actual preparation conclusions; incomplete reports remain undisclosed.

## Rebuild and Verify

Run from the repository root, with PowerShell 7.2+ on Windows:

```powershell
foreach ($faculty in 'viira', 'leopold', 'silver', 'asinti') {
    pwsh -NoProfile -File tools/Convert-ToHoi4Tga.ps1 -Source "art/source/HSM_BAR_mtk_$faculty.png" -Destination "mod/HoISubmod/gfx/interface/HSM_BAR/mtk/$faculty.tga" -Width 1000 -Height 700 -Background '#25332c'
}
$env:NODE_PATH = Join-Path $HOME '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
node tools/Build-BarradCollegiumSkin.cjs
node tools/Build-BarradCollegiumMenu.cjs --check
node tools/Build-BarradCollegiumProjects.cjs --check
node tools/Test-BarradCollegiumMenu.cjs
node tools/Test-BarradCollegiumProjects.cjs --native
python tools/Preview-BarradCollegium.py
```

Remove `--check` only when deliberately regenerating gameplay or presentation text.
Python needs Pillow; Lucide/Sharp are build-only. Native fonts, shader definitions and
character/modifier contracts are read from the installed HOI4/EaW source, not copied.

Pre-balance-pass verification on 2026-10-10: 70 menu groups and 1566 gameplay/native-contract scenarios
passed. The preview checks 466 EN/RU states and saves 54 static images in
`art/previews/HSM_BAR_mtk_*.png`; 181 states require scrolling. Existing four faculty
skins were reused, not regenerated. New protocol, joint and opus-origin views were
visually inspected. Tests cover actual glyph widths,
safe writing bounds, distinct selected sprites, contrast, alpha/format, guarded
disclosure and starts, all-five prerequisites, paired-lab exclusion, cancellation and
duplicate callbacks. No live widget covers the lower-left apparatus area.
The existing archive, institutional Collegium and integration suites also pass.

These are **static source-based previews, not HOI4 screenshots**. Native scrollbar/input
behavior, UI scaling, save/load and scheduler interleaving remain unverified. Restart
HOI4 after adding GUI/GFX files; test the friendship ending and complete the oath.

The later balance revision removes the application pair, retains two method controls,
and expands the budget and protocol text regions without moving the existing index,
tabs or illustrations. Updated checks pass 1,749 project scenarios and 97 menu groups.
The revised preview renders 362 bilingual states into 54 images; 75 states require
scrolling and no non-scrolling label is clipped. Completed old-save application flags
no longer select a different result. The user clarified that "text-only" referred to
missing interaction, not a rendering bug; the subsequent laboratory workflow adds
preparation, timed observations and authored follow-up choices for all 26 projects.

Interactive-workflow verification: 3,506 project scenarios and 360 menu groups pass.
The final renderer checks 4,002 bilingual states and saves 204 previews; 50 states
require scrolling, with no clipped non-scrolling text. Prepared laboratories,
checkpoint actions, verification orders, completed reports and technical ledgers
are included. All four faculty appearances were inspected from these static renders.
The completed ledger shows the result and released reservations, not a future bill.
This is still not native HOI4 rendering/input or a live save/reload test.

## Generation Prompts

The following are the accepted prompts, retained for provenance. The initial rejected
Leopold image was not installed.

### Viira

```text
Production raster UI background texture for a 1930s fantasy research college, DEPARTMENT OF VIIRA, magic and consciousness research. Landscape exactly 10:7 aspect, destination game size 1000x700. Flat orthographic top-down, crisply axis aligned. NOT a screenshot, NO written text or UI controls anywhere. A refined cyan-grey linen laboratory folio with pale nickel fittings, layered translucent vellum overlays and subtle prismatic glass accents, distinctly intellectual and optical rather than occult. Restrained tactile realistic painted game art, high craftsmanship.
Layout mandatory: full 1000x700 rectangle, opaque; edge border <=12px. Top band x16..984 y16..90 is DARK graphite/cyan fabric and entirely blank for white live headings. Horizontal navigation band y96..154 entirely blank dark cyan fabric. Left sidebar x16..288 y160..594 dark graphite/cyan fabric completely blank for six live project rows and progress. Main document surface x306..980 y162..680: ONE broad unlined very light cool-grey smooth vellum sheet, not a stack, uninterrupted blank usable x326..958 y178..658 for black live text/buttons. No grids, artwork, objects, pseudo-writing, seals, decorative lines or shadows in usable region. Gentle transparent layering only outside that usable region. Along the bottom of left sidebar, x30..268 y606..672 ONLY, a small detailed optical research apparatus: clear faceted prism, adjustable nickel stands and a tiny circular smoked-glass interference plate, no writing. Never cross into any blank region. A few fine etched spectral arc details confined to outermost right edge x980..995. No purple, no gold ornament, no mysterious orbs, no flags/heraldry, no hands/characters, no text, numbers, symbols resembling writing, no censor marks, no buttons baked into texture. All objects photographed straight overhead, clean functional collegiate laboratory not secret service.
```

### Leopold

```text
Edit this game UI background into LEOPOLD'S engineering department while preserving EXACT geometry and empty regions of the reference. The large blank paper sheet, header, navigation strip, and left sidebar must stay exactly in place. Replace blue cloth with charcoal graphite drafting-board enamel; thin nickel and muted brass edges; paper pale neutral-grey. Replace ONLY the small optical apparatus in the BOTTOM LEFT with a equally small magocrystal gear motor with a ruby crystal, two gears and a caliper, confined to the SAME apparatus footprint. Do NOT enlarge apparatus upward. Do not add ANY crests, griffons, heraldry, clocks, or instruments in the header. All header and sidebar space above apparatus absolutely empty. No text, numbers, controls, paper marks or diagrams on reading surface. Distinct engineering workshop material and minor wear only at margins, not blue-purple. Flat orthographic, same10:7 size, opaque.
```

### Silver Star

```text
Edit this production game UI material background into SILVER STAR'S CLINICAL THAUMATURGY AND NECROMANTIC MEDICINE department. Preserve EXACT panel geometry, proportions and ALL blank areas of the reference. Top header and navigation and left sidebar remain dark for white live text, but change to deep burgundy medical ledger cloth, with cool polished nickel fittings and thin porcelain edge inlays, NOT gold ornate fantasy decoration. Broad right document surface remains one clean almost-white clinical paper sheet, entirely empty for black live text. No ruled lines, graphs, text or marks on that paper.
Replace only the optical apparatus at bottom left with a small clinical laboratory still-life occupying exactly the same footprint: sealed clear-glass specimen ampoules in a white ceramic rack, a compact early20th-century pressure gauge, small stoppered bottle and dull silver instrument case, no human anatomical shapes, no blood, no gore, no living creatures. A faint restrained green-blue magical fluorescence inside ONE tiny ampoule, no floating glow orbs. No objects ABOVE bottom apparatus zone, no crests in header, no text, no symbols, no numbers, no buttons. Keep completely blank writing space x330..950 y180..658 of destination1000x700. Same10:7 opaque orthographic flat-lay.
```

### Asinti

```text
Edit this production game UI background into ASINTI'S RITUAL AND OTHERWORLD CONTACT DEPARTMENT. Preserve EXACT geometry, rectangular bounds and blank regions of the reference. Replace blue fabric with very dark pine-green woven ritual cloth, with subtle geometric woven edge patterns, blackened pewter fittings rather than gold. Main right document page becomes one clean pale flax-grey smooth research sheet, NOT brown parchment, fully empty for black live text, no diagrams or words on its reading surface. Header, navigation strip, sidebar above apparatus remain dark and ENTIRELY EMPTY for live labels and buttons.
Replace ONLY the bottom-left optical apparatus with a small contained still-life fitting SAME footprint: a shallow black stone experimental tray with fine white chalk concentric interrupted ritual rings and three small smooth upright stones, an empty glass vessel and a modest plumb-bob boundary measurement instrument. Controlled scientific ritual experiment, no magical orbs, no demonic faces, no skulls or exotic caricatures, no borrowed real-world religious symbols. No illustrations ABOVE that bottom-left footprint. No crests, text, numbers, buttons, or censorship marks anywhere. Detailed tactile collegiate scientific equipment, distinct from a secret-service archive. Flat orthographic same10:7 opaque texture; usable right blank surface x330..950 y180..658 at1000x700 remains wholly unobstructed.
```

