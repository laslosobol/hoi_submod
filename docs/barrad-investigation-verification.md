# Barrad investigation integration: independent baseline

Verification on 2026-10-10, Windows PowerShell **7.6.5**, Node **v24.19.0**. The full post-emission regression run passed **41/41 commands**, with **0 failures**. After the final status-only refinement, the three requested checks passed again: **3/3 commands, 0 failures**. This records source/test verification, not live HOI4 acceptance.

## Final status-only recheck

The main integrator's final refinement displays an inconclusive protocol as a limited report instead of ready. The 490x20 main Service row now uses four concise `row_pending`, `row_ready`, `row_accepted` and `row_limited` localization states; the investigation window retains the full sentences. The corresponding investigation assertion and regenerated native outputs were included in this verification. The builder, assertion and emitted EN selectors were independently read to confirm this is the short-row version, not the preceding full-sentence row snapshot.

Only the requested three checks were rerun, from **15:08:02 to 15:08:08 UTC+03:00**, as recorded by the local runner clock:

| Exact command | Final status-only result |
| --- | --- |
| `node tools/Build-BarradInvestigations.cjs --check` | PASS: 9 files; seven investigations, 42 evidence excerpts, 21 protocols |
| `node tools/Test-BarradInvestigations.cjs` | PASS: 209 scenarios / 0 failed |
| `pwsh -NoProfile -File tools/Test-BarradContent.ps1` | PASS: 365 checks / 0 failed; 135 focuses, 179 new events, 3973 English keys |

All three exit codes are zero. Full output and exact timestamps are retained in [status-only results](C:/Users/laslo/RiderProjects/HoISubmod/dist/barrad-investigations-20261010/statusfinal-20261010-150802-205/results.json), with sibling logs and environment metadata. This follow-up covers the final status refinement; it does not claim another full 41-command run or live visual acceptance. No gameplay or test changes were made by the verifier.

```powershell
pwsh -NoProfile -File dist/barrad-investigations-20261010/Run-ExistingBaseline.ps1 -Mode StatusFinal
```

## Final post-emission result

After the main integrator emitted the investigation outputs and authorized their two new checks, the complete baseline was rerun from **15:03:40 to 15:05:54 UTC+03:00**. This is the final full-baseline result, superseding the incomplete-build observation below; the later status-only recheck is recorded above.

```powershell
pwsh -NoProfile -File dist/barrad-investigations-20261010/Run-ExistingBaseline.ps1 -Mode Final
```

- All 39 commands in the initial table passed again. The content suite now reports **365 passed / 0 failed**; the previous unresolved helper is resolved.
- `node tools/Build-BarradInvestigations.cjs --check`: **PASS**, 9 generated files, seven investigations, 42 evidence excerpts, 21 protocols.
- `node tools/Test-BarradInvestigations.cjs`: **209 passed / 0 failed**, seven cases and 21 protocols. The main integrator had expanded the suite beyond the previously reported 202 scenarios before this invocation.
- Staff: **14 groups passed**, **28 images decoded**. Social survey: **113 scenarios passed**. Service GUI: **142 scenarios passed**. Archive / Skin / Copies / Regions: **44 / 22 / 17 / 23 groups passed**.
- No current failure output to report. No test expectation or implementation was changed by the verifier to obtain this result.

Full per-command output, timestamps, exact commands and environment are retained in [final results](C:/Users/laslo/RiderProjects/HoISubmod/dist/barrad-investigations-20261010/final-20261010-150340-183/results.json), with sibling `.log` files and `environment.json`. Initial and intermediate logs remain intact. Visual QA/layout refinement was concurrent; later changes are not implicitly covered by an earlier command's result.

## Scope and result

Read-only review of staff changes, followed by all **37** commands recorded in `dist/barrad-gui-20261010/results.json`, plus the staff and social-survey suites. Baseline ran from **14:54:16 to 14:56:32 UTC+03:00**: **38 passed / 1 failed commands**. All requested commands executed. No test or content fixes were made.

The single failed suite was the whole-content reference check, with **356 passing checks and one unresolved-helper check**. The main integrator confirmed that investigation output had not yet been emitted. This is an **expected incomplete-build observation**, not a confirmed implementation defect. Do not bypass the check or generate files from this verification task.

## Staff review

No confirmed ordinary-path staff regression found in the reviewed snapshot.

- Compared the complete parsed `zzz_BAR_ideas.txt` and `BAR_organization.txt` overrides with installed EaW: only the intended **10 idea pictures / 8 MIO icons** differ. Native gates, traits, costs, templates and bonuses remain unchanged.
- Checked the nine portrait assignments, `has_character` guards, once-only application, route-exit restoration and reentry. No character recruitment, resurrection or role replacement is performed.
- Reviewed EN/RU company selectors and native-name fallbacks, five high-command aliases, tag/route scope and localization BOM/uniqueness.
- Independently read installed `effects_documentation.md:7555` for `set_portraits` and `common/on_actions/_documentation.md:10` for `on_daily_TAG`. The own startup/daily hook uses supported forms.
- **14 staff scenario groups passed; all 28 resolved images physically decoded.** Inspected the existing staff contact sheet; no new preview or art was generated.
- Residual acceptance checks: actual advisor-screen refresh, MIO scripted-name evaluation and text width, with and without Arms Against Tyranny. Source tests and a static contact sheet do not prove those engine behaviors.

Sources reviewed: installed EaW `common/characters/BAR.txt`, `history/countries/BAR - Baard.txt`, `common/ideas/zzz_BAR_ideas.txt`, `common/military_industrial_organization/organizations/BAR_organization.txt`; current `HSM_BAR_staff` effects, triggers, on-actions, scripted localization, GFX and both replacement localization files.

## Initial command results

Each row has a full same-stem `.log` in `dist/barrad-investigations-20261010`. Counts are each suite's own scenarios, groups or assertions; they are not interchangeable and are not summed into an artificial overall scenario count.

| Exact command | Result |
| --- | --- |
| `node tools/Test-BarradStaff.cjs` | PASS: 14 groups, 28 decoded images |
| `node tools/Test-BarradSocialSurvey.cjs` | PASS: 113 scenarios |
| `pwsh -NoProfile -File tools/Test-BarradCollegium.ps1` | PASS: 5832 assertions |
| `pwsh -NoProfile -File tools/Test-BarradContent.ps1` | FAIL: 356 checks passed, 1 failed; pending investigation emission |
| `pwsh -NoProfile -File tools/Test-BarradDiplomacy.ps1` | PASS: 38 groups |
| `pwsh -NoProfile -File tools/Test-BarradLegacyDecisions.ps1` | PASS: 50 scenarios |
| `pwsh -NoProfile -File tools/Test-BarradAnomalies.ps1` | PASS: 38 checks |
| `pwsh -NoProfile -File tools/Test-BarradArt.ps1` | PASS: 45 scenarios |
| `pwsh -NoProfile -File tools/Test-BarradArchivePhotos.ps1` | PASS: 12 scenarios |
| `node tools/Test-BarradCivic.cjs --native` | PASS: 104 scenarios |
| `node tools/Test-BarradCollegiumFrontiers.cjs --native` | PASS: 88 scenarios |
| `node tools/Test-BarradCollegiumProjects.cjs --native` | PASS: 1566 scenarios |
| `node tools/Test-BarradCollegiumMenu.cjs` | PASS: 70 groups |
| `node tools/Test-BarradDevelopment.cjs` | PASS: 92 scenarios |
| `node tools/Test-BarradNativeContracts.cjs` | PASS: 23 scenarios |
| `node tools/Test-BarradPhases.cjs` | PASS: 55 groups |
| `node tools/Test-BarradServiceRewards.cjs` | PASS: 208 scenarios |
| `node tools/Test-BarradModifierTooltips.cjs` | PASS: 14 scenarios |
| `node tools/Test-BarradServiceStory.cjs` | PASS: 37 groups |
| `node tools/Test-BarradSecrecy.cjs` | PASS: 16 groups |
| `node tools/Test-BarradCaseOutcomes.cjs` | PASS: 217 scenarios |
| `node tools/Test-BarradResearchOperations.cjs` | PASS: 383 assertions |
| `node tools/Test-BarradNormalization.cjs` | PASS: 57 scenarios |
| `node tools/Test-BarradCases.cjs` | PASS: 27 scenarios |
| `node tools/Test-BarradFocusPresentation.cjs` | PASS: 129 checks |
| `node tools/Test-BarradArchive.cjs` | PASS: 44 groups |
| `node tools/Test-BarradArchiveSkin.cjs` | PASS: 22 groups |
| `node tools/Test-BarradArchiveCopies.cjs` | PASS: 17 groups |
| `node tools/Test-BarradArchiveAudio.cjs` | PASS: 18 groups |
| `node tools/Test-BarradResidencies.cjs --native` | PASS: 122 scenarios |
| `node tools/Test-BarradContentIcons.cjs` | PASS: 16 fixture scenarios |
| `node tools/Build-BarradCollegiumProjects.cjs --check` | PASS: 8 generated gameplay files |
| `node tools/Build-BarradCollegiumMenu.cjs --check` | PASS: 4 departments / 26 projects |
| `node tools/Build-BarradContentIcons.cjs --check` | PASS: read-only production asset checks |
| `node tools/Test-BarradMeterRetirement.cjs` | PASS: 8 scenarios |
| `node tools/Build-BarradServiceGui.cjs --check` | PASS: 9 files / 124 actions |
| `node tools/Test-BarradServiceGui.cjs` | PASS: 142 scenarios |
| `node tools/Test-BarradFielddesk.cjs` | PASS: 18 groups |
| `node tools/Test-BarradArchiveRegions.cjs` | PASS: 23 groups |

## Exact pending-build failure

```text
FAIL: All custom effect and trigger calls resolve : Undefined helper HSM_BAR_investigation_pulse
Barrad integration: 356 passed; 1 failed; 135 focuses; 179 new events; 3740 English keys.
Exception: C:\Users\laslo\RiderProjects\HoISubmod\tools\Test-BarradContent.ps1:277
Line |
 277 |  if ($failed.Count) { throw ($failed -join "`n") }
     |                       ~~~~~~~~~~~~~~~~~~~~~~~~~~
     | All custom effect and trigger calls resolve : Undefined helper HSM_BAR_investigation_pulse
```

The pending call is in `common/on_actions/HSM_BAR_core_on_actions.txt:17`. This check reports its first undefined helper; it does not establish that no other pending references exist. Investigation code remains owned by the main integrator.

One repeat of `pwsh -NoProfile -File tools/Test-BarradContent.ps1` at **14:56:48** reproduced the same error (**356 / 1**, 3742 English keys). Logs are retained as `Test-BarradContent-recheck.log` and `baseline-recheck.json`, not substituted for the initial result.

At **14:57:29-14:57:35**, repeats of `Test-BarradServiceGui.cjs`, `Test-BarradArchive.cjs`, `Test-BarradArchiveRegions.cjs` and `Test-BarradArchiveCopies.cjs` all passed: **142, 44, 23 and 17**, respectively. Their `-recheck.log` files and `presentation-recheck-results.json` preserve this later snapshot. No read-only presentation test failure was observed.

## Reproducible runner and boundaries

The runner is `dist/barrad-investigations-20261010/Run-ExistingBaseline.ps1`. PowerShell parsing and its full `Final` execution passed. It retains original failures, creates timestamped log folders, checks every exit code, and exits nonzero on any suite failure. It never runs previews or writable production builders. The investigation checks were added only after the main integrator's explicit authorization.

```powershell
pwsh -NoProfile -File dist/barrad-investigations-20261010/Run-ExistingBaseline.ps1 -Mode Baseline
pwsh -NoProfile -File dist/barrad-investigations-20261010/Run-ExistingBaseline.ps1 -Mode Affected
pwsh -NoProfile -File dist/barrad-investigations-20261010/Run-ExistingBaseline.ps1 -Mode Final
```

`Baseline` repeats the original 39-command list. `Affected` runs 12 existing integration, GUI/archive, fielddesk, phase, development, survey and staff suites plus the two authorized investigation checks. `Final` runs the complete 39-command list plus those two checks. `StatusFinal` runs only the investigation builder check, investigation suite and content suite, in that order. All modes except `Baseline` refuse to start until the investigation effects/triggers/GUI and EN/RU outputs exist. This is a precondition, not a test bypass or a passing result. All 41 full-baseline invocations and all three status-only invocations ran; none was skipped.

Only this report, the authorized runner and result logs were written. No gameplay, staff code, GUI, test expectations, manifest, art or shared scripts were edited. Builders ran only with `--check`; the existing icon regression suite creates and deletes its own disposable temporary fixture, not workspace content. No commit. The workspace was changing concurrently, so these timed results are not a frozen revision or certification of later edits.
