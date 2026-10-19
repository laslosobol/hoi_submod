# Barrad Readiness Pass: 2026-10-08

Historical verification snapshot. Trust/capacity mechanics were subsequently removed
on 2026-10-10; current progression is documented in [implementation notes](barrad-implementation.md)
and [Collegium contracts](HSM_BAR_collegium.md). The results below describe the earlier revision.

## Delivered

- **Collegium:** two independent policy choices per faculty, with actual time/PP/factory/upkeep tradeoffs; different faculty pacing; conservative paid AI participation. All 20 preparations, four opuses, authored failures and prerequisite gates remain. Eight institutional focus descriptions were expanded in EN/RU with specific scientific and civilian scenes. [Project contracts](barrad-collegium-projects.md).
- **Service:** five substantive residency investigations, including a two-stage Zebrican account; three returning-antagonist episodes and a recurring policy review. Ten events and eleven assignments preserve earlier source choices and give bounded, non-stacking methods/research rewards. No added secrecy meter or fabricated anomaly custody. [Narrative and lifecycle](barrad-service-residencies.md).
- **Normalization:** three invasion formation types, territory-sensitive final reinforcement, permanent reinforcement termination after loss of breach control, and defeat cleanup. Existing finite-wave and state-transfer safeguards remain. [Contracts and module limitations](barrad-normalization.md).
- **Art:** 38 newly generated transparent sources; 38 goal exports with standard/shine pairs and 29 idea exports. All 135 focuses, 32 ideas and six dynamic modifiers now use custom artwork, with contextual reuse. Original 45 Service source/goal revisions are intact. [Review, hashes and previews](barrad-icon-manifest.md).
- No Cyanolisia gameplay edits, approval migration, release export, version bump or commit.

The integrated inventory is **135 focuses, 170 events and 3184 English keys**, with matching Russian localization coverage. Eighteen anomaly archive cases remain implemented; the larger catalog is not claimed complete.

## Verification

Windows, **PowerShell 7.6.5**, **Node 24.19.0**, installed HOI4/EaW source contracts.
Commands below ran from the repository root. **29 suites and three builder checks passed, zero failing commands.** Counts are each tool's units; assertions, scenario groups and asset checks are not interchangeable.

| Exact command | Passing result |
| --- | --- |
| `pwsh -NoProfile -File tools/Test-BarradCollegium.ps1` | 3361 assertions |
| `pwsh -NoProfile -File tools/Test-BarradContent.ps1` | 325 checks |
| `pwsh -NoProfile -File tools/Test-BarradDiplomacy.ps1` | 38 groups |
| `pwsh -NoProfile -File tools/Test-BarradLegacyDecisions.ps1` | 50 groups |
| `pwsh -NoProfile -File tools/Test-BarradAnomalies.ps1` | 38 checks |
| `pwsh -NoProfile -File tools/Test-BarradArt.ps1` | 45 assets |
| `pwsh -NoProfile -File tools/Test-BarradArchivePhotos.ps1` | 12 assets |
| `node tools/Test-BarradCivic.cjs --native` | 104 scenarios |
| `node tools/Test-BarradCollegiumFrontiers.cjs --native` | 88 scenarios |
| `node tools/Test-BarradCollegiumProjects.cjs --native` | 1393 scenarios |
| `node tools/Test-BarradCollegiumMenu.cjs` | 57 groups |
| `node tools/Test-BarradDevelopment.cjs` | 92 scenarios |
| `node tools/Test-BarradNativeContracts.cjs` | 23 scenarios |
| `node tools/Test-BarradPhases.cjs` | 53 groups |
| `node tools/Test-BarradServiceRewards.cjs` | 195 scenarios |
| `node tools/Test-BarradModifierTooltips.cjs` | 14 scenarios |
| `node tools/Test-BarradServiceStory.cjs` | 37 groups |
| `node tools/Test-BarradSecrecy.cjs` | 16 groups |
| `node tools/Test-BarradCaseOutcomes.cjs` | 217 scenarios |
| `node tools/Test-BarradResearchOperations.cjs` | 379 assertions |
| `node tools/Test-BarradNormalization.cjs` | 57 scenarios |
| `node tools/Test-BarradCases.cjs` | 26 scenarios |
| `node tools/Test-BarradFocusPresentation.cjs` | 129 contracts |
| `node tools/Test-BarradArchive.cjs` | 44 groups |
| `node tools/Test-BarradArchiveSkin.cjs` | 22 groups |
| `node tools/Test-BarradArchiveCopies.cjs` | 17 groups |
| `node tools/Test-BarradArchiveAudio.cjs` | 18 groups |
| `node tools/Test-BarradResidencies.cjs --native` | 122 scenarios |
| `node tools/Test-BarradContentIcons.cjs` | 16 scenarios |
| `node tools/Build-BarradCollegiumProjects.cjs --check` | 8 generated files |
| `node tools/Build-BarradCollegiumMenu.cjs --check` | 4 faculties / 24 projects / 96 pages per language |
| `node tools/Build-BarradContentIcons.cjs --check` | 81 mappings / 32 ideas / 6 modifiers |

Additional checks:

- `C:/Users/laslo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe tools/Preview-BarradCollegium.py`: 216 bilingual states, 16 rendered previews, no clipped non-scrolling text; 50 states intentionally scroll.
- The same Python runtime running `tools/Preview-BarradContentIcons.py` produced native-size dark/light contact sheets; all 38 goal and 29 idea exports were visually inspected.
- `git diff --check`: passed for tracked changes. Git reports existing LF/CRLF normalization warnings; untracked Barrad files are covered by the content tests, not this command.
- Detailed command output is retained locally in ignored `dist/barrad-review-20261008/`.

The first complete run exposed two old tests that searched only inherited artwork and a secrecy fixture unaware of the new guarded continuation. Sprite resolution now includes actual local registries. The secrecy fixture executes the real start effect and actor trigger and asserts both convoy choices reach it; unknown predicates/effects still fail. The full suite was rerun after these fixes. The earlier missing Collegium sprite was resolved by real registration/export, not a test exemption.

## Remaining Acceptance

This is **ready for a fresh-campaign playtest, not certified for release**. No live HOI4 session or clean engine error log is claimed.

- Exercise actual GUI clicks, tooltips, scrollbars, factory reservation refresh, paid mission timing and save/reload; test both human and AI research and campaign costs.
- Walk both stages of each route, neighbour warfare/peace outcomes, renewed convoy choices, global activation and the finite invasion.
- Global suppression still affects three dedicated magical equipment archetypes, not magic-bearing modules on otherwise ordinary designs. No verified native per-module combat selector was found.
- Foreign focus text is viewer-aware; icon concealment remains the documented single-player approximation, not secure per-client multiplayer masking.
- NML still uses provisional native rebel flags and the unknown-leader portrait. Event illustrations and journal photographs are not claimed to be individually unique custom icons.
