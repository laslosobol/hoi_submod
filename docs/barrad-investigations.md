# Service Investigations

The local Service cases `rock`, `titan`, `entity`, `amulet`, `plants`, `echo` and
`compass` now have authored comparisons and expedition protocols. Other casework
retains its existing workflow; this is not a claim that every foreign dossier
already has a comparison puzzle.

## Interaction

1. Open the investigation from its regional case row or the Investigation button.
2. Read two attached documents and mark one of three excerpts in each. Comparing
   the relevant pair records a working hypothesis. An unhelpful pair produces a
   case-specific explanation without spending political power or granting evidence.
3. Choose one of three methods and authorize the expedition. Each description
   states what its instruments or control procedure can actually establish.
4. Read the returned report. Two methods can establish sufficient field evidence;
   one exposes a methodological limitation. The latter does not unlock research.
   Another method can be funded, retaining both reports in the same file.
5. Laboratory research and final disposition still use the existing case effects
   and Anomalous Research results. Comparing documents alone grants no scientific
   knowledge, custody, research bonus or national-spirit contribution.

No new currency, trust level, secrecy meter or success percentage exists. Selection
variables only control presentation. Historical hypothesis/report flags record
which authored material has been earned, not an accumulating resource.

## Authority and Persistence

- Protocols cost 20-35 political power and take 14-28 days, as displayed before
  dispatch. One protocol per case can run; different cases are independent.
- An active method is frozen. Closing a window does not cancel the mission.
- Explicit recall and loss of access pay no reward or refund. Early, repeated or
  obsolete callbacks cannot finish a new attempt. Completion rechecks current access.
- A completed protocol cannot be repeated. A conclusive method ends fieldwork for
  that case; an inconclusive report allows a different paid method.
- The old human direct-start shortcut is disabled for these seven cases. Existing
  GUI missions still complete through their original authority and block concurrent
  protocol work. AI keeps its native decision route.
- Already-investigated cases are not reset or re-rewarded. Their existing archive
  remains authoritative; new expedition prose is not retroactively fabricated.
- Teardown cancels active work but preserves signed hypotheses and reports.
- Reading the archive closes the operational window without authorizing anything.
  Opening/closing the file is free. Actual dispatch has a separate button.

## Sources and Maintenance

`tools/data/barrad-investigations.json` contains EN/RU documents, relevant pairs,
methods, prices, durations and reports. The existing archive and case-completion
effects are the narrative/gameplay boundary. The new field accounts are authored
submod material, not newly claimed canonical EaW incidents.

`tools/Build-BarradInvestigations.cjs` emits nine native script/GUI/localization files.
It copies existing access and completion contracts rather than implementing a
second research or reward system. Existing folder textures, controls and bitmap
fonts are reused. No new art generation was necessary.

```powershell
node tools/Build-BarradInvestigations.cjs --check
node tools/Test-BarradInvestigations.cjs
node tools/Test-BarradServiceGui.cjs
node tools/Test-BarradArchiveRegions.cjs
```

Verified on Windows with PowerShell 7.6.5 and Node 24.19.0: all 41 regression
commands passed, followed by three passing checks after the compact-status
refinement. Investigations passed 209 scenarios; the social survey passed 113.
Exact commands and retained logs are in [the verification report](barrad-investigation-verification.md).

`tools/Preview-BarradInvestigations.py` rendered 224 EN/RU states and checked
4,166 text placements plus 112 fixed titles, with no detected layout issues.
Its exhaustive output defaults to ignored `dist/barrad-investigations-20261010/previews`;
six representative screenshots remain in `art/previews`. The main Service preview
also passed 403 text-fit checks per rendered view. These are native-asset fixtures,
not screenshots from a running game.

Static fixtures execute parsed scripts, and the source-driven preview uses native
textures/fonts. Neither substitutes for HOI4 hit testing, scrolling or save/load.
Live acceptance should cover both languages, inconclusive-then-conclusive work,
recall/retry, loss of capital/access during work, old completed cases, and a save
made with an expedition underway. Start a fresh campaign for the first social
assessment; there is no migration of running native decisions/projects.
