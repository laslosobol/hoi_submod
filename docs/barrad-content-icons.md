# Barrad Content Icon Integration

`tools/data/barrad-content-icons.json` maps content IDs to reviewed source motifs.
`tools/Build-BarradContentIcons.cjs` consumes that inventory without changing it.
The workspace build completed on 2026-10-08. All 135 Barrad focuses, 32 ideas and
6 dynamic modifiers now reference custom artwork; thematic reuse is intentional.

## Commands

Run from the repository root on Windows, with Node and PowerShell 7.2+ (`pwsh`)
on PATH:

```powershell
# Read-only integration check.
node tools/Build-BarradContentIcons.cjs --check

# Independent tooling tests: conversion happens only in a disposable fixture.
node tools/Test-BarradContentIcons.cjs

# Original 45 Service-art checks, unchanged.
pwsh -NoProfile -File tools/Test-BarradArt.ps1

# Re-export after an intentional source/mapping change, then review the artwork.
node tools/Build-BarradContentIcons.cjs
node tools/Build-BarradContentIcons.cjs --check
pwsh -NoProfile -File tools/Test-BarradArt.ps1
```

`--root PATH` selects an explicit alternate repository, primarily for fixtures.
`--check` is strictly read-only, including on failure: it does not export,
normalize files, patch mappings, update hashes or bless missing art. A successful
check establishes technical integrity, not artistic approval or in-game QA.

## Generated Files

Paths below are relative to `mod/HoISubmod`. Motif names are taken from the
current JSON each run; idea/modifier entries can be appended without changing
the builder. The inventory has 81 focus mappings, 32 ideas, 6 modifiers,
38 new goal textures and 29 idea textures. The other 54 focuses already used
the existing Service or cover artwork.

| Output | Contents |
| --- | --- |
| `gfx/interface/goals/HSM_BAR_<art_motif>.tga` | 99x86, every distinct `art_*` motif used anywhere in the JSON |
| `gfx/interface/ideas/HSM_BAR_<motif>.tga` | 64x64, every distinct motif used by an idea or dynamic modifier, including reused `dir_*`/`cover_*` artwork |
| `interface/HSM_BAR_content_icons.gfx` | `GFX_HSM_BAR_<art_motif>` standard sprites |
| `interface/HSM_BAR_content_icons_shine.gfx` | Matching `_shine` sprites with both masks pointing to the goal TGA |
| `interface/HSM_BAR_content_ideas.gfx` | `GFX_idea_HSM_BAR_<motif>` sprites |

Initial goal motifs (all receive `HSM_BAR_` prefix and `.tga` extension):

```text
art_anomalies art_artillery art_assembly art_beyond art_bridge art_budget
art_chorus art_collegium art_contact art_deer art_field art_friendship
art_grid art_guard art_hospital art_housing art_inspection art_kasa
art_last_minute art_lesson art_manufactory art_memorial art_mortal_life
art_peer_review art_precision art_prosthesis art_refugees art_registry
art_representation art_republic art_rift art_ritual_brake art_scales
art_teacher art_tutelage art_ward art_water art_wittenland
```

Initial idea motifs (same prefix/extension, in the `ideas` directory):

```text
art_anomalies art_artillery art_beyond art_bridge art_chorus art_collegium
art_grid art_guard art_hospital art_last_minute art_manufactory
art_peer_review art_refugees art_republic art_rift art_ritual_brake
art_tutelage art_ward dir_activation dir_agency dir_custody_law
dir_evidence dir_normalization dir_remains dir_seal_labs dir_storage
dir_training dir_watchmen dir_world
```

The build prints its complete current output/patch list. It reuses
`tools/Convert-ToHoi4Tga.ps1` for all conversion. It never regenerates the
existing `dir_*`/`cover_*` goal textures or their Service standard/shine files.

## Definition Edits

Only direct scalar `icon` values on the 81 mapped focus definitions are changed.
The common-group ID is `HSM_BAR_<suffix>`; other groups use
`HSM_BAR_<group>_<suffix>`. The empty frontiers suffix resolves to
`HSM_BAR_mtc_frontiers`. Conditional Service focus icons are checked but not
patched. Ideas are located by exact ID and only their direct `picture` changes;
dynamic modifiers are located by exact ID and only their direct `icon` changes.

The existing Clausewitz parser from `Test-BarradArchiveSkin.cjs` validates
definitions and nesting. Token offsets select only the chosen scalar span;
comments, strings, nested rewards, BOMs and line endings remain intact.
Duplicate definitions, missing direct fields and mapped conditional fields fail.

`HSM_BAR_mtk_research` in `HSM_BAR_mtk_projects.txt` is checked against the JSON
and the owner generator's in-memory output. Neither that generated file nor
`Build-BarradCollegiumProjects.cjs` is written by this tool. Drift must be fixed
through that generator.

## Validation And Ownership

Before any build writes, every required PNG is decoded and checked for minimum
99x86 dimensions, the existing 8192x8192 upper bound, and both transparent and
opaque alpha. All 45 reviewed Service PNG and TGA hashes are compared with
`docs/barrad-icon-manifest.md`; the manifest is never rewritten.

The proposed mappings and sprite registrations must pass before conversion.
Converted TGAs are staged outside the repository, checked for exact dimensions,
32-bit alpha and complete payloads, then published. Changed inputs during
conversion abort publication. Unchanged outputs are not rewritten.

Both current-file checking and build preflight cover every `HSM_BAR_*` focus,
idea and dynamic-modifier definition in their respective content directories,
including IDs not listed in the JSON. Any remaining foreign icon is an error
requiring an explicit mapping. All custom focus choices must have unique standard
and shine registrations; all idea/modifier references need registered custom
sprites with the expected texture paths and dimensions.

`HSM_BAR_residencies_methods` uses the existing world-network artwork exported
at idea size. Further additions are subject to the same complete coverage check.

The fixture suite covers positive conversion, idempotence, successful/failing
read-only checks, missing/corrupt PNGs, missing standard/shine sprites, bad
masks, corrupt/opaque TGAs, hash drift, unmapped additions, duplicate IDs,
nesting and generator ownership. The original 45-check test is unchanged.

Verification on 2026-10-08: **16 fixture scenarios passed, 0 failed**;
the unchanged Service-art suite reports **45 passed, 0 failed**. The actual
workspace `--check` passed after exporting all 67 textures and three registries.
Source and native-size dark/light sheets were visually reviewed. Approval
revisions, repairs and preview links are in [the art manifest](barrad-icon-manifest.md).
Actual HOI4 rendering remains unverified.
