# Greifwald parsed-source tests

Run `python -B -X utf8 tools/Test-Greifwald.py`; the standard `--eaw` and `--game`
arguments select installed references. The bundled Python works if the Windows
Store alias does not. `Harness` runs interpreter self-checks independently of
incoming focus/event files. Missing production files fail the full suite; they
are not silently skipped.

The suite executes production focus rewards, scripted effects, event choices,
timed flags and explicitly dispatched daily hooks through the existing strict
Grover interpreter. The adapter adds generic primitives only. Fixtures start
with AET's actual homeland 495/496 and just 378/382 in Herzland. Native core sets,
outside wars, ruler replacement and the clock are fixture inputs; campaign
progress is earned through production scripts. Unknown executable operations
raise. Tooltips do not execute their previewed rewards.

Coverage includes protecting foreign guardians and neutralizing retired custody offers, unknown versus
confirmed death, partial territorial handover, age and war gates, unit shares,
death during regency, original Trimmel identity, legal settlement and stale
choices, native Grover protection, focus imports/graph and EN/RU localisation.
The opening regression invalidates the delayed packet through temporary ruler
replacement, restores the government before the 45-day queue expires, then
verifies one retry and one reward despite repeated daily hooks and stale choices.
Reviewer regressions exercise fractional balances across all nineteen paid
choices, including both the 50- and 100-PP contract-revision contexts, stale closure after union/restoration or war, repeated mandate review
and refusal, delayed gift recovery, and the congress legitimacy gate. They also
execute safe first options and restore the Count/civic council across governments
using native party roles. Foreign custody cannot be transferred by dossier review,
old pending-request flags, queued offers or already-open acceptance options.
Rescue from absent GRI still requires Griffenheim and no surviving custodian.
This is not an engine scheduler, UI, AI or multiplayer simulation.

The 2026-10-31 correction pass adds coverage for all twelve paid internal packets'
free deferral at low and ample funds, actual queued retries, and zero AI deferral
weight once the most expensive option is affordable. It tests the removal of the
refusal reward, inherited GRI bureaucracy and its scoped save repair, actual-transfer
only compact rewards and their historical save migration, and the absence of that
reward in either direct or former-regency union completion. Narrative checks verify
exclusive death/absence and direct/former-regency descriptions plus the restored
court's policy callbacks. Preview evaluation uses a separate fixture so a visible
cost cannot silently become a second actual debit.

## Latest source run, 2026-10-31

Using the installed reference at
`C:/shit/Steam/steamapps/workshop/content/394360/1826643372` and bundled Python:

- Full Greifwald suite: **65 tests passed**, exit 0 (89.578 seconds).
- Grover compatibility: **42 tests passed**, exit 0.
- Formables: **13 tests passed**, exit 0.
- `Build-Greifwald.py --check`: seven generated files, zero stale outputs.
- EN/RU record, BOM, key, formatting and numeric parity: campaign 114, story
  203 and system 102 keys per language. These are the six AET localization files,
  not a global mod-localization audit.
- `Bind-GreifwaldArt.py --check`: 72 approved assets, zero pending files.
  The complete pre-existing art tree's SHA-256 inventory is unchanged.

Additional regressions cover old-save rewards after GRI annexation, subjection or
war with AET, all six restored-government focus gates, and invalidation of scheduled
or already-open restored-court scenes after ruler replacement, subjection or
capitulation. Source-model results do not establish engine UI or scheduler behaviour.

## Source runs before the correction pass

- Grover compatibility: 42 tests pass.
- Formables: 13 tests pass, including all six new pragmatic-AET guard insertions
  (two category-visible, two decision-visible, two decision-available).
- Greifwald after removal of diplomatic custody: all 51 tests pass in one run.
  Five tests for the retired request/consent route were replaced with three
  regressions for foreign-guardian protection and inert old-save offers.
  No scenario is skipped or converted into an expected failure. Coverage includes
  complete regency, treaty-union and legal-settlement routes, opening/gift retries,
  and every paid choice at cost minus 0.5, exact cost, and cost plus 0.5.
- Focus graph, clearance against actual native positions, imports, EN/RU
  localisation/BOM, and definition/flag-reference checks pass.

## Integration notes for main

Artwork pass, 2026-10-30: `Test-GreifwaldArt.py --check` passes all 72 approved
assets and binding targets (31 added focuses, 41 spirits including the dynamic
modifier). Source/export hashes, dimensions, alpha and sprite references pass;
the native idea override preserves all bytes outside picture values.
`Build-Greifwald.py --check` reports seven files, zero stale outputs. All 51
Greifwald scenario tests pass after binding. Contact sheets were reviewed by
main and an independent reviewer; HOI4 rendering remains untested.

- Affordability now uses `NOT = { has_political_power < cost }`, which rejects
  fractional shortfalls as well as integer ones. Absent-GRI recovery scopes the original
  character explicitly through GRI. Unsupported comparison operators and
  unknown executable primitives still fail; the checks were not relaxed.
  Infrastructure comparison is supported: the
  `building_count_trigger` documentation explicitly uses `<Building> < <int>`.
- The pending-disagreement queue regression passes after the production timer
  fix. It executes the real judgement choice and repeated daily reconciliation.
  `Rewards.test_daily_reconciliation_does_not_duplicate_a_pending_disagreement`
  checks that event 15 remains a single pending packet.
- Final fixture corrections use insufficient funds for the free dismissal,
  compare workshop fallback bonuses against the existing refugee bonus, and
  inspect the two actual formation decisions and their category guards. They
  do not change production guards or stub native predicates.
- With expanded ownership authorization, the shared loader now reads real
  `HSM_AET*.txt` definitions and creates an absent AET fixture. The Grover suite
  also verifies that this real predicate protects an actual AET household.
  All prior Grover assertions remain: 42 tests pass. Formable tests preserve
  the exact upstream delta and test the conditional original-AET + realpolitik
  exclusion, including rejecting a blanket AET ban: 13 tests pass.
- The AET adapter supports the generic country `on_daily` hook, real installed
  `decrease_poverty`/`decrease_illiteracy` helpers, and scoped `PREV` war-goal
  removal. The native country alias is resolved through the global empire
  target. Random-country selection chooses the first eligible fixture country;
  random distribution itself is outside this test's scope.
  Foreign custody callbacks are retained as inert save-compatibility entries;
  automatic engine window expiry is not simulated.
- Structured `promote_character` uses parsed native leader roles and ideology
  groups. Promoting an opposition party head does not replace the ruler, and
  the Count's multiple native roles require an explicit ideology. AET sources
  reject unsupported `default_option`; the conservative action is tested as
  the first actual option instead.
