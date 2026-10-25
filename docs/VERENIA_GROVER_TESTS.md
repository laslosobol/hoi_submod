# Grover Regression and Native Protection Audit

Owned files: `tools/Test-VereniaGrover.py` and this document. This audit does not
edit production, the installed game, native EaW, launcher files, or other tests.
No game is launched.

## Run

From the repository root:

```powershell
& 'C:/Users/laslo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 tools/Test-VereniaGrover.py
& 'C:/Users/laslo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 tools/Build-VereniaGroverGuards.py --check
```

The suite inherits the parser and strict scoped interpreter through
`Test-VereniaSpirit.py`, `Test-VereniaUnification.py`, `Test-VereniaForce.py`, and
`Test-VereniaRegency.py`. `--eaw PATH` and `--game PATH` select the installed
reference inputs. Unittest class/method selectors are accepted, for example
`NativeProtection` or
`EntryAndCustody.test_declining_living_local_grover_allows_civil_fallback`.

## Model Boundaries

Triggers, effects, focus rewards, event options, and Grover daily/annex hooks are
parsed from production and executed. The fixture supplies prior unification,
territory, government, character custody, and resources. It does not replace
the production campaign with a parallel implementation. Unknown executed
operations fail; unsupported state effects raise explicitly. Scripted effects
are expanded in their actual scope, including state scope and `PREV`.

The fixed 38-state Herzland set is independently checked against installed
original cores of GRI, BRZ, STW, KAT, ANG, YAL, ROU, PYT and FEA. Strategic region
164 membership is read from native province lists. The fixture retains all six
Verenian states and two unrelated sentinel states, including foreign-owned land.
Each of the 38 states and five required House homelands is individually tested
with the wrong owner and wrong controller for both ERI and EYR.

The transfer model changes owner/controller for each executed state transfer,
moves the original character object between country rosters, and records every
tree load and unit transfer. Unit pools use divisible numeric quantities to
verify the quarter-share contract; actual division selection, rounding, air-wing
handling, stockpile composition, and engine on-actions are not simulated.
Random-state construction chooses the first eligible state deterministically.
Event delivery and daily ticks are explicit. Native event scheduling, engine
country creation callbacks, idea-cancel timing, UI rendering, and save migration
require separate engine testing.

The real spirit interpreter executes the generated ledger effects for the two
partnership ideas. Both hosts must receive ownership flags and exact modifier
arithmetic; restored GRI must receive the ordinary ideas through those same
effects, without a Verenian ledger. Unknown `HSM_VER_SP_*` calls are never no-ops.
The two temporary guardianship/transition and four original court-legacy ideas
stay outside that ledger.
The restored tree's own additional ideas are checked by reference and executed
through its actual focus rewards.

## Coverage

- Entry: independence, dukes, original tag, neutrality, union, route history,
  war/capitulation, every required state, previous restoration, and existing GRI.
- Custody: recovery only from absent GRI; original character transfer; dead,
  foreign, unknown, and duplicate foreign custody; no fabricated character.
- Civil fallback: unavailable-custody completion, voluntary decline with living
  local child/adult Grover, unchanged custody, no imperial restoration, the sole
  matching private-guest description, interruption close decision, and one-time
  civil rewards. Actual focus AI weights prefer the mandate when Grover is local
  and permit the civil fallback when his whereabouts are unknown.
- Staged cores: capital-region stage, remaining Herzland stage, provenance only
  for new host cores, preservation of old cores, no Verenian states in the 38,
  and cleanup even after a marked state changes owner.
- Choices: pending flag required, acceptance before expiry, rejection after
  expiry, alternate-option replay denial, daily retry, cooldown, and inert stale
  choices after interruption.
- Handover: adulthood boundary, delayed peace, preparation/articles, all five
  homelands, all 38 Herzland states, and no overwrite of an existing GRI.
- Settlement: exact 38-state transfer, preserved other owners and old host
  cores, removal of GRI cores/claims only in the six Verenian states, technology
  inheritance through `PREV`, global imperial targets, old war-goal cleanup,
  and host/imperial capitals.
- Independence and alliance: new faction, existing host-led faction, and host
  as a member of another faction; original Grover as monarch; explicit new tree.
- Replay: quarter army/air/stockpile transfer, no ships/officers, home factories
  or full-slot research fallback, and final rewards occur once.
- Memories: both Houses, both routes, and all eight education/petition/service
  combinations. Each of the 32 completed paths selects its accession prose from
  actual copied flags.
- Integration: script/flag/event/focus/tree/idea references, EN/RU localisation
  syntax/BOM/parity, host imports, all ten restored focus rewards, and installed
  documentation for the new state/transfer operations.

## Native Guards

The suite audits 15 imperial events, 19 childhood/custody events, three GRI
decisions, and `GRI_has_access_to_reichsmandates`. It executes actual protected
event triggers, immediate effects, and already-open options. A trigger-only
guard is insufficient: option effects must independently remain inert. The
protected household cases include ERI and EYR before and after mandate acceptance,
and restored GRI, with different event ROOTs. The 110 event/household cases assert
no global death flag, character transfer, or other fixture mutation.
`imperial.70` is checked with restored GRI as `FROM`.

Normal native gates remain true. Removing only the added guard predicates and
effect wrappers reproduces the complete pre-Grover AST, including the existing
CYA overrides. For the three previously tracked files the baseline is commit
`ff58d4bc7635cc84abd3d329f0248af15ada04bc`; `events/Grover_Events.txt` uses installed
EaW because no prior submod override existed. This comparison requires that
baseline commit to remain available. It checks all existing entries, not only
the modified events. The builder's `--check` runs read-only, reports zero stale
files, and is checked not to modify the four override files.

## Final Verification

2026-10-24 result: all 37 Grover test methods pass, including the full English
and Russian reference checks. There are no interpreter errors or unresolved
findings in this bounded audit. All five native-protection tests pass; the
builder reports `0 stale native guard files`. The existing full spirit suite
also passes all 29 tests with 80 generated components.

The voluntary-decline production bug was fixed by the production owner, not by
this audit. Both hosts can now choose the civil compact with a living local
child or adult Grover, leave his custody intact, and prevent later mandate
acceptance. The real guest-description and AI-weight checks also pass.

Missing companion files fail explicitly rather than silently skipping the
integration checks. All files are now present. The accession memory-name
mismatch seen during concurrent authoring was corrected by its author, and all
32 memory/prose cases pass. The tests and this document are the only files owned
by this audit; production changes remain with their respective authors.

## Final Integration Pass

The parent reran 16 complete scenario suites after integrating the authoring:
`Test-Verenia`, Avian, AvianRelations, Commonwealth, Crisis, Development, Flags,
Force, Formables, Grover, Identity, Regency, Routes, Spirit, Unification and
Zypressen. All 618 test methods passed. The complete tree/coordinate check
found and prompted a fix for the new branch overlapping the language branch;
the Grover root now occupies the former imperial position at x=54. Exactly eight
replaced imperial focus IDs remain unattached for legacy saves, explicitly
enumerated by the graph test; other unattached focuses still fail.

The strict focus-hover audit also passed against installed game and EaW
localisations: 262 focuses, two existing hidden legacy IDs, no reference or
source-budget violations. The narrative audit's UI-only `audit` function passed
for 303 event options and 25 decisions, with no estimated external references.
This caught and fixed the interrupted-mandate decision's technical effect dump.
Both builders report zero stale files, and `git diff --check` passes.

The old `Test-VereniaNativeUI.py` frozen gameplay hashes and the default
`Test-VereniaNarrativeUI.py` pre-feature equivalence snapshot do not pass for
this expanded content: they assert that gameplay has not changed since the
earlier UI-only repair, whereas this task deliberately changes it. Their
baselines were not regenerated to conceal those differences. UI-only checks
were run separately from historical gameplay equivalence, not reported as a
pass of those historical assertions. New native guards separately retain the
pre-Grover AST-preservation checks described above.
