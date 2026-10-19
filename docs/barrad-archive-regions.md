# Service Archive Regional Index

The archive remains a historical reader. Selecting a branch, dossier, document,
copy or photograph does not discover evidence, grant access, create custody,
start fieldwork or award research. Existing narrative documents, copies,
redactions, recordings, photographs and delegated Results text are preserved.

## Region Contract

`HSM_BAR_archive_region` shares the operations console's numeric contract:

| ID | Branch | Dossiers |
| --- | --- | --- |
| 1 | Local | Page 1: rock, titan, entity, amulet. Page 2: reactor, echo, compass, plants. |
| 2 | Equus | sombra, darkheart, crown cross-reference |
| 3 | Griffonia | grover, herald, crown cross-reference |
| 4 | North | rosa, chalice, phylactery |
| 5 | Riverlands | marsh |
| 6 | Zebrica | zebrica, crown cross-reference |

Membership follows the existing case progression and regional rumor definitions,
not anomaly classification. Existing numeric case IDs 1..18 are unchanged.
`HSM_BAR_archive_page` is separate from region: only Local has a second page.
The political-panel launcher defaults to Local, page 1.

Each tab requires its actual `HSM_BAR_region_<name>_open` flag or retained
historical evidence for one of its region-specific dossiers. Generic Crown
history is deliberately excluded from this tab-unlock condition. Opening a branch alone reveals no
unknown cases. Global existence, present custody and live access are not archival
evidence. Original per-stage disclosure checks remain in place. Historical records
survive loss of foreign branch access or specimen access; the original Service
reader actor gate remains required.

The Crown file is genuinely multi-origin. BAR's generic history flags do not
retain which regional report supplied a particular paragraph. Consequently it is
one shared historical cross-reference in Equus, Griffonia and Zebrica, not three
regional specimens. A known Crown record exposes the same explicitly labelled
cross-reference only in an already-available branch, never unlocking a foreign
tab by itself. No regional provenance, physical site
or custody is inferred from tab selection. Local central-programme operations
are not provenance and do not make Crown a Local archive dossier. The dedicated
visible index label and tooltip state this distinction in both languages.
The existing branch-open flags are persistent mandates: production does not
clear them on custody or territorial access loss. Thus a previously opened Crown
index remains readable after that loss. Generic legacy Crown history with no
opened branch or independent regional records does not invent a regional index;
it becomes readable when an eligible branch is available. No history is erased.

## Console Integration

The Operations button occupies existing cloth header space at x=789, y=18, with
the existing 141x34 tab texture. Six regional tabs use that same texture at
x=24+153*n, y=64. No new image assets or sprite definitions are required.

`HSM_BAR_archive_operations_available` combines the archive actor, a valid
available archive region, and the main-owned `HSM_BAR_service_gui_available`.
It therefore respects the console's human BAR, active Directorate, founded
Service, non-capitulated, non-subject and state-624-control requirements.

The archive callback copies region into `HSM_BAR_service_gui_region`, sets
`HSM_BAR_service_gui_open = 1`, calls `HSM_BAR_service_gui_refresh = yes`, then
clears archive open/selection/document/copy state. Console reconstruction and
action eligibility remain main-owned. No action is started by this callback.

For reverse navigation, set archive region from the console, page 1, case from
console subject (0 office, 1..18 existing case IDs), document 1, clear copy, set
archive open and close the console. **Call `HSM_BAR_archive_refresh = yes` last.**
This opening-only helper:

- Requires the existing archive reader actor and an open archive.
- Returns an unavailable or invalid region to Local with no selected dossier.
- Uses Local page 2 for case IDs 5, 14, 16 and 17; otherwise page 1.
- Keeps only a historically known subject belonging to the current region/page.
- Clears unknown, stale, wrong-region or office selections to the memorandum.
- Resets document to 1 and clears copy, without modifying history or gameplay.

Read-only `HSM_BAR_archive_case_<case>_listed` predicates gate each dossier's
index, metadata, prose, photos, copies and audio independently. The aggregate
`HSM_BAR_archive_selection_available` also requires the selected numeric case.
Thus forged/stale state cannot disclose a document even before refresh. Generic
local Crown subject 6 is cleared; a genuine regional Crown link may use 2/3/6.
Refreshing does not manufacture a region-specific Crown record.

## Verification

Run from the repository root:

```powershell
node tools/Test-BarradArchive.cjs
node tools/Test-BarradArchiveCopies.cjs
node tools/Test-BarradArchiveAudio.cjs
node tools/Test-BarradArchiveSkin.cjs
node tools/Test-BarradArchiveRegions.cjs
pwsh -NoProfile -File tools/Test-BarradArchivePhotos.ps1
python tools/Preview-BarradArchive.py --language english
python tools/Preview-BarradArchive.py --language russian
```

Use an installed Python with Pillow; the Windows Store alias alone is insufficient.
`HOI4_PATH` and `EAW_PATH` can override dependency locations. The renderer reads
native font atlases, glyph advances, kerning, textures, GUI geometry and scripted
visibility. It writes only `art/previews/HSM_BAR_archive_skin_*.png`: 12 fixtures
per language including all regions, copies, Results, a photograph and Crown.
PNG metadata records source hashes, state and text bounds.

The regional suite checks all region/subject combinations, branch/history gates,
local paging, wrong-region and forged-state disclosure, exact handoff order,
opening normalization, read-only state, source membership and selected tab skins.
Frozen hashes retain all 122 historical document/caption lines per language.
Existing copy and outcome snapshots remain unchanged after projecting out only
the separately tested regional routing. Existing bitmap-font, geometry, texture,
photo and PCM checks remain in the original suites.

These are parsed-contract, asset and static-rendering checks, not an HOI4 engine
playtest. Native scaling, scrolling, hover/input behavior and audio playback still
need in-game acceptance. No optional comparison pilot or console action migration
is implemented by this archive change.

## Changed Files

Production files, relative to `mod/HoISubmod`:

```text
interface/HSM_BAR_archive.gui
common/scripted_guis/HSM_BAR_archive.txt
common/scripted_effects/HSM_BAR_archive.txt
common/scripted_triggers/HSM_BAR_archive_regions.txt
common/scripted_triggers/HSM_BAR_archive_copies.txt
common/scripted_localisation/HSM_BAR_archive.txt
common/scripted_localisation/HSM_BAR_archive_skin.txt
localisation/english/HSM_BAR_archive_regions_l_english.yml
localisation/russian/HSM_BAR_archive_regions_l_russian.yml
```

Support files: `tools/Test-BarradArchive.cjs`,
`tools/Test-BarradArchiveCopies.cjs`, `tools/Test-BarradArchiveAudio.cjs`,
`tools/Test-BarradArchiveRegions.cjs`, `tools/Preview-BarradArchive.py`, and this
document. The existing Skin and Photos tests were run without edits. Rendered
PNG previews are outputs, not new game art. No Service-console, MTC, shared core,
research, source-art or shared implementation-document edits are included.
