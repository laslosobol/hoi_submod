# Barrad Archive Skin

Presentation of the existing 1000x700 archive. Case evidence, rewards and progression remain unchanged. The follow-up adds found-document editions and three historical audio attachments.

- Cloth folder with a clean paper reading area; live EN/RU text and native scrolling.
- Paper index cards and document tabs; the current case and document have a burgundy selection mark.
- Native button shader supplies hover, pressed and disabled states. The folder uses the native static shader so background clicks do not flash the entire page.
- Dark ink and readable green/red result colors on paper. White redaction squares retain dark backing; removed passages use a dark cut-strip outline.
- Existing 600x300 attachments remain unchanged. Header, index and document body remain separate; all click shields stay behind the controls.
- Matching 36x36 dark metal controls use antialiased Lucide symbols. Page arrows and return occupy the left side of the cloth toolbar; photo/audio occupy its right side. Close retains a 20px outer inset. No icon buttons sit on the paper stack.
- The case heading begins at y=136, inside the top sheet. Paper content stays within x=350..956, y=136..640; document and edition rows share a 600px width with 12px gaps. The recovered-copy note sits on the cloth below the index note.

## Assets

The folder background was generated with the built-in image tool, not the API CLI:

- Source: `art/source/HSM_BAR_archive_folder.png`.
- Game texture: `mod/HoISubmod/gfx/interface/HSM_BAR/archive/folder.tga`, 1000x700, opaque 32-bit bottom-origin TGA.
- Six deterministic paper textures and seven metal control textures (including selected-photo state) are built by `tools/Build-BarradArchiveControls.cjs`. Controls use Lucide 1.8.0 glyphs and Sharp 0.35.4 to render at 4x before downsampling to native size. No new image generation is used for these controls.
- Editable control SVGs and the Lucide license live in `art/source/HSM_BAR_archive_controls/`; the license is also distributed alongside the game TGAs. Navigation no longer depends on the stock HOI4 arrow/back/close textures.
- Three inline redaction marks are built by `node tools/Build-BarradRedactions.cjs`.
- Sprites and local fonts: `interface/HSM_BAR_archive_skin.gfx` and `interface/HSM_BAR_archive_redactions.gfx`.
- Selection selectors read archive variables; they never write case state. The new copy variable is presentation-only and resets when leaving a case.

Convert the background with PowerShell 7.2+:

```powershell
pwsh -NoProfile -File tools/Convert-ToHoi4Tga.ps1 -Source art/source/HSM_BAR_archive_folder.png -Destination mod/HoISubmod/gfx/interface/HSM_BAR/archive/folder.tga -Width 1000 -Height 700 -Background '#25332c'
```

Rebuild controls using Node with `lucide` and `sharp` available. In the configured bundled runtime:

```powershell
$env:NODE_PATH = Join-Path $HOME '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
node tools/Build-BarradArchiveControls.cjs
```

These packages are build-only; the game and regression suites use the supplied TGAs.

Native source references: EaW `interface/eaw_intelligence_agency_blocker.gui` for paired mouse shields, `common/scripted_guis/eaw_alerts.txt` for image properties, and installed HOI4 `interface/core.gfx`, `gfx/FX/buttonstate.shader`, `gfx/FX/static_button.shader` for fonts and button states. No dependency fonts or textures are copied into the release.

## Verification

The inset/control correction passed five focused suites on Windows / PowerShell 7.6.5 / Node 24.19.0: Content (246), Archive (44), ArchiveSkin (22), ArchiveCopies (17), ArchiveAudio (18); zero failures. Archive checks cover access, selection, EN/RU text fitting, visible-element overlap, native-size hitboxes and the clean top-sheet inset, rejecting the former edge-overlapping positions. Skin checks cover all 14 custom textures, distinct antialiased glyphs, shader states and text contrast. Copy tests retain the original dispatch guards; audio tests validate PCM and read-only playback. Gameplay, wording and playback behavior remain unchanged.

`tools/Preview-BarradArchive.py` uses Python/Pillow and the existing Node parser to render actual GUI coordinates, source text, selectors, native glyphs and textures. It writes six deterministic `art/previews/HSM_BAR_archive_skin_*.png` fixtures per language: investigated dossier, results, photo attachment and three reactor document editions. Run with a Python environment containing Pillow:

```powershell
python tools/Preview-BarradArchive.py --language russian
python tools/Preview-BarradArchive.py --language english
node tools/Test-BarradArchive.cjs
node tools/Test-BarradArchiveSkin.cjs
node tools/Test-BarradArchiveCopies.cjs
node tools/Test-BarradArchiveAudio.cjs
```

All twelve fixtures rendered without clipped text. Russian dossier/photo and English Results fixtures were visually inspected at 1000x700 after the navigation correction. Geometry checks include a 1280x720 canvas as well as 1366x768, 1600x900 and 1920x1080. These are **static source-based previews, not HOI4 screenshots or live UI-scaling tests**. Live input, scrollbar behavior, UI scaling, native rendering and sound playback still need an in-game check after fully restarting HOI4. The skin adds no gameplay or save migration. [Field recording provenance and limitations](barrad-archive-audio.md).

## Generation Prompt

```text
Use case: ui-mockup, production game UI background texture ONLY, no finished UI text.
Create a high-quality photorealistic flat-lay archival dossier interface background for a secret research service in a 1930s fantasy strategy game. Landscape aspect ratio 10:7, ideally 1500x1050. It will be precisely resized to 1000x700 pixels. Orthographic straight-on view, perfectly axis-aligned, no tilted perspective.
Composition with strict proportions: full rectangular dark desaturated forest-green clothbound office folder filling the entire canvas edge to edge, thin worn cloth edges and subtle stitching. Top horizontal area from y0 to y105 of target 700 is uninterrupted very dark green fabric with subtle embossed border, completely empty, for live title and subtitle. Left column x0 to x298 extends downward in the same dark green folder material and is completely empty for interactive document index cards. A narrow vertical binding fold at x298..312 below y106, with TWO tiny aged-brass staple fasteners confined to that narrow gutter at y150 and y620.
Right page area from x310 to x982, y108 to y690: a stack of clean cool off-white archival paper, with faint grain, tiny edge wear, subtle layered paper corners and soft shallow shadows. Main top sheet almost pure light grey ivory, even brightness, utterly blank from x320..964 y112..674. No writing lines, boxes, printing or marks on its reading area. Paper is not yellow, not brown, not parchment. No grunge over usable content. The folder base visible at outer margin. Highly refined tactile materials, restrained microtexture, crisp readable surface for black live text. Broad paper reading area and narrower dark folder index. All elements stay within rectangular canvas.
No text, letters, numbers, pseudo-writing, symbols, stamps, heraldry, logos, fleur-de-lis, characters, hands, weapons, pens, wax seals, magnifying glasses, extra loose objects, drawn buttons, divider lines in reading area. Do not add any interface components. This is only the photographic material skin under real game controls. Opaque background.
```

