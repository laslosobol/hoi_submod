# Aquileian regions: provincial programmes and a national settlement

Implementation contract, revised 2026-11-01. The latest expanded focus and
seamless transition contract is [AQUILEIAN_POSTWAR_CAMPAIGNS.md](AQUILEIAN_POSTWAR_CAMPAIGNS.md).
Earlier test counts below are historical and do not validate that expansion.
Scope: Rila/JEB, Westkeep/JRR,
Pridea/JFT and Vinovia/VIN. Source of intent: the existing workbook
`outputs/01a0cedc-8cc7-7800-b208-c4b9449f4226/griffonia-regional-paths-and-policy.xlsx`,
sheet `Аквелія та Таррін`, E5:F19. Tarrin, Flowena and the Vivienne/MER proposal
are separate programmes. This pass creates no artwork or player resource meters.

The latest user clarification supersedes the older autonomy reading: the split
is **leadership of all Aquileia versus support for an existing national movement**,
not a permanent separatist provincial end state. Local institutions prepare a
national programme. See `AQUILEIAN_REGIONS_LORE_ROUTES.md` for the fifteen-route
canon/inference matrix; its national leadership proposals are authored additions.

## Native foundation and authored additions

The installed EaW reference is the Workshop path in `EAW_UPSTREAM.md`.
Its preparation decisions select broad allegiance and support organisations.
Club influence is not a native final-government selector; flags can coexist.
Our fifteen programmes are authored postwar choices derived from the surviving
native political forces, not an unrestricted prewar selection or a government
assigned from whichever influence variable happens to be largest. A one-time
snapshot records the native outcome and political context for that selection.
The native revolution alone resolves its support contest, including immediate
victory and ties; the submod does not run a competing preparation system.

JEB: royal, constitutional Michel, moderate clubs, Cocardiers.
JRR: Jeanne absolutist, Jeanne's coalition, Colette.
JFT: Dennis, communes, Enfants Terribles, FJA coalition.
VIN: Gadiffer, ABC, Chevaliers, SIS.

Jeanne the marquise is not JER_jeanne (Jeanne Lavolière). An authored character
uses an existing generic portrait. Collective administrations likewise avoid
assigning unproven movement membership to native individuals. Native Michel,
Gadiffer, Dennis and Colette retain their identities. A constituent settlement,
not a support decision alone, installs a new government.

## Playable sequence

1. A namespaced regional tree wins country selection only for these four original
   tags. All copied generic focuses have been replaced with four authored local
   foundations per region and twelve additional economic/military/civic focuses
   per political programme. The native generic tree is not replaced globally.
2. Native events and the existing decisions in each region own all prewar
   allegiance, organisation support and preparations. Completing JER's native
   activation focus registers surviving participants with `HSM_AQR_started`;
   registration awards nothing. It does not complete an authored prewar root,
   choose a programme, move support or grant troops. An additive read-only panel
   uses one native split M/R bar in a regional decision category to display
   existing monarchist and revolutionary support from the campaign's start,
   while JER exists and no native revolution start/end flag is set. Panel access
   does not require JER's activation focus or participant registration. It has
   no action buttons or separate resource and does not replace the native
   preparation interface.
3. `HSM_AQR_record_native_outcome` records the result once native resolution has
   occurred and invokes `HSM_AQR_snapshot_native_politics`. The local native
   winner takes precedence over the national victor. Peaceful immediate outcomes
   without a local winner flag use the native global result, frozen once so later
   national restoration cannot rewrite the province's history. The mission-timeout
   hook records after the native local comparison; a daily fallback covers
   immediate outcomes after their native end-event option actually executes.
   Recording an outcome during the revolution does not yet open postwar content.
4. The existing `HSM_AQR_opening` ID now means **After the Revolution**, an
   automatically completed postwar root. It requires the native revolution to be
   finished, a known native outcome and functioning local rule; peace or the
   resulting leadership war permits the opening. Local rule
   means an existing, non-capitulated participant that is independent or a subject
   of JER; a foreign overlord does not qualify. Completion must not consume or
   interrupt the country's normal focus work. Settlement events `HSM_AQR.410`
   through `HSM_AQR.413` then offer a programme grounded in that region's frozen
   native political forces. Selection and later execution must recheck the actual
   local winning camp, current administration and any required living character.
   The defeated camp does not receive a mandate through an old choice or an
   unrestricted fallback. The existing postwar programme branches remain intact.
5. A single central incorporation event offers immediate support of the existing
   national government or refusal and immediate war for national leadership.
   A human region may continue as AI JER; a human-controlled JER is never taken
   over. There is no separate congress/approval/confirmation chain or 100-PP fee.
   Native focus requests and a daily fallback share guarded delivery. Ratification
   may proceed during the resulting leadership war. Proclamation still requires
   an absent JER, independence, peace and owned/controlled capital 377. See the
   expanded contract for concurrent regions, stale demands and save migration.
6. Proclamation adopts native Aquileian cosmetics and heartland claims/cores,
   without the native decision's unconditional annexation of other regions.
   Remaining regions receive a real accession offer. Third-party subjects and
   foreign territory cannot be acquired by that invitation. Refusal remains a
   refusal; coercion requires a separate, visible war goal and normal diplomacy.
   Republican programmes use `JER_REPUBLIC`, including neutral Cocardiers and
   Chevaliers. Native `JER_JFT_formed_fascism` explicitly means a kingdom and must
   not be applied to Les Enfants Terribles. The six royal/constitutional programmes
   use `HSM_AQR_KINGDOM`: native `JER_formed_democratic` incorrectly names Michel's
   constitutional settlement and Jeanne's royal coalition republics. Daily
   maintenance repairs legacy JER_formed/JER_JFT_formed identities and mismatched
   managed republican/royal cosmetics on sovereign, ratified AQR nations;
   it does not change governments, replay rewards or overwrite later imperial or
   foreign puppet cosmetics. Existing EaW republican flags and map colour are reused;
   the royal cosmetic reuses the actual Discret flag and native kingdom colour.
7. National reconstruction adds housing, demobilisation, food supply and peripheral
   settlement to both regional-led and native Aquileia. Three temporary crisis
   stages are removed through the work; they do not become a new resource meter.
   Pomovarra, Flowena, Greifwald, Fezera and the Northern Tribes receive bounded,
   voluntary invitations. Stale/unanswered offers can be recalled after expiry;
   explicit refusals remain binding. Later cores require actual ownership/control.
   After military victory, an optional restoration returns to the real JER tag
   and original national movement. Available living Discrets or a surviving
   republican leadership are required; dead/foreign-held characters are not
   recreated. Existing compatible national history is preserved. Choosing our
   own programme keeps the regional-led national tree and route epilogues.
8. Herzland settlement follows native Aquileia's border/JHZ precedent, confined
   to actually owned and fully controlled land. A foreign sovereign JHZ cannot
   be overwritten. Border integration and a dependent Herzland government are
   political work after victory, not a continental annexation button. The regional
   variant integrates the common four-state border (378, 399, 447, 497); it does
   not copy the much larger thirteen-state carveout of native royal Aquileia.

### Removed preparation layer

The sixty authored preparation focuses, the old prewar opening behaviour and
the submod's paid influence actions are removed. There are no authored preparation
rifles, manpower, militia divisions, central-support/opposition spirits or sabotage
penalties. Native preparation decisions, their costs and their effects are
unchanged. The old preparation balance document and preparation prose files, if
still present, describe the superseded design and do not authorize active content.
This removal does not remove postwar reconstruction crisis spirits, the provincial
compact or any of the fifteen existing postwar/national programmes.

### Frozen political context and programme selection

`aquileian_native_settlement.py` copies the relevant native movement values and
political flags once, after the outcome is recorded. These internal snapshot
values are historical evidence, not another influence economy. Uninitialised
values are recorded as zero; real negative values are retained. The live camp
must be unambiguous and agree with the recorded camp. Existing native characters
must still be available where required. A selection grants only permission to
pursue the programme: it does not install its government, complete its focuses,
ratify its constitution or award its rewards.

| Region / event | Basis for the postwar discussion |
| --- | --- |
| JEB / `HSM_AQR.410` | Royal victory permits the royal programme. Revolutionary candidates are the strongest eligible named movements among constitutional reconciliation with Michel, moderate clubs and Cocardiers; tied leaders remain selectable. Marais leadership changes the coalition narrative, never expands the candidate set to every programme. |
| JRR / `HSM_AQR.411` | Royal victory requires the recorded `JRR_absolutist` flag for Jeanne's absolutist programme or `JRR_reformism` for her coalition. Both flags permit both; neither flag permits neither. Bassot's countercoup does not itself restore her administration. Revolutionary victory permits Colette's civil settlement while her character remains available. |
| JFT / `HSM_AQR.412` | Royal victory permits Dennis. Revolutionary selection is restricted to the strongest prepared named movements among communes, Enfants Terribles and FJA; ties are allowed. A native organisation flag remains evidence even at zero influence. |
| VIN / `HSM_AQR.413` | Royal victory permits Gadiffer. Revolutionary selection is restricted to the strongest prepared named movements among ABC, Chevaliers and SIS; ties are allowed. Missing initial influence values do not erase a movement introduced by its native flag. |

Selection first respects the actual native winning camp, then the strongest
prepared named movements within that camp; ties leave a real choice. There is
**no unprepared fallback that offers every programme**. Marais coalition prose
does not bypass the strongest-named-movement restriction or create a new route.
JRR's royal options require their own recorded native flags. Sole native-ruler
programmes retain their actual-camp and character requirements. If no eligible
candidate exists, no unrestricted selection is offered. Michel's constitutional
reconciliation and Jeanne's return remain programme work, not accomplished facts.

Before queuing the initial next-day event, set the permanent
`HSM_AQR_native_settlement_requested` flag. It has no expiry; it prevents repeated
automatic requests even if delivery fails, the player defers or timed guards
expire. The seven-day queued guard and thirty-day displayed-event pending guard
remain additional controls, not substitutes for that permanent request flag.
Deferral is free. Each region has a free
`HSM_AQR_native_settlement_retry_{TAG}` decision to resume an eligible unfinished
discussion, with a seven-day re-enable interval. Only an explicit eligible retry
clears the request/presented flags before queuing and setting the request flag
again. Daily maintenance never resets it. Selection effects recheck their
candidate and refuse to overwrite an already valid mandate. A compatible
previously ratified programme is recognised; migration of obsolete unratified
route locks remains the main integration's responsibility.

## Engine and interface requirements

All offers recheck sender, recipient, sovereignty, war and territorial context at
delivery and execution. Refusal/deferral comes before acceptance for external
offers. Retry timers are discrete flags, not a new player economy. Unaffordable
internal choices must retain a free deferral; exact fractional PP boundaries and
idempotent rewards require source coverage. No nested technical flags in public tooltips.
Narrative descriptions contain prose; effects and requirements disclose mechanics.

Native annexation via JER_the_triumph and JER_integrate_the_loyal must not silently
remove an active regional campaign. HSM_AQR.30 supplies a guarded demand with
explicit continuation choices, free deferral and no template/character deletion
before acceptance. A regional player accepting incorporation into a human-led
JER receives an explicit game-over warning; the other player's country is never
taken over. This is distinct from the removed option for a province to annex JER
by agreement. The unguarded native aquileia.54 and its war callbacks are retained only
for nonparticipating countries. Other JER programmes remain intact.
The generic imperial/Aquileian formation decisions and unite_aquileia_proper are
guarded for the four participants: the latter silently declared several wars.
Proclamation keeps native JER_formed for all four, including Pridea's separate
cosmetic identity. Actual completed unification sets uniting_aquileia_proper so
the subsequent native Aquileian regional-expansion decisions remain reachable.

The regional compact consolidates earned programme/development modifiers. A new
political mandate replaces its predecessor's policy component, not the factories
or literacy already earned. No new art bindings are required.

The support panel's visibility matches the native regional preparation categories:
JER must exist, and `JER_revolution_begun`, `JER_revolution_ended` and
`JER_revolution_ended_2` must all be unset. It is available from the campaign's
start without a completed JER root focus, `HSM_AQR_started` or
`HSM_AQR_mechanic_active`. Reward-free registration and the political snapshot
remain separate: the snapshot is still taken at the native outcome, never when
the panel first appears. Each `HSM_AQR_support_{TAG}` category belongs to its
original regional tag and binds directly to that country's `monarchist_support`
and `revolutionary_support`. Display one shared split M/R bar, not two separate
progress bars. Its native split sprite is driven by local monarchist support;
the tooltip reports both actual native values without introducing a new counter.
It does not read or change JER's selected-country pointer. The native progress
sprite and frame are reused, with additive GUI, scripted-GUI and category files only;
native country-selection and influence-action widgets are not copied. Engine
layout, category sizing and click-through behaviour still need observation.

There is one narrow native category override:
`common/decisions/categories/JER_decision_categories.txt`. Native Rila's
`JER_JEB_committee_of_public_safety_category` lacks a phase visibility guard, so
`build_native_category_overlay` adds only
`visible = { NOT = { has_country_flag = HSM_AQR_native_outcome_recorded } }`.
This closes paid committee-seat allocation after the snapshot, when it can no
longer affect programme eligibility. The other three regions' existing category
phase guards are untouched. The emitted file adds the generated header and this
one visibility block; it does not alter native decisions, prices or seat effects.
The separate mission-timeout observation callback remains the only decision-body
insertion.

## Authoring and ownership

`tools/data/aquileian-regions/{TAG}.json` owns route-specific EN/RU prose.
`tools/Build-AquileianRegions.py` owns generated scripts and localization, with
an explicit read-only `--check`. Runtime transitions may use an authored companion.
The integration is split between the following helpers; their presence does not
by itself establish successful generation or engine validation:

| Source | Responsibility |
| --- | --- |
| `tools/aquileian_native_phase.py` | Reward-free registration; native preparation/running/finished gates; one-time outcome recording; automatic postwar opening; narrowly guarded Rilan committee category overlay. |
| `tools/aquileian_native_settlement.py` | Snapshot of native political forces; guarded postwar selection events `HSM_AQR.410`–`.413` and programme eligibility. |
| `tools/aquileian_support_gui.py` | Additive read-only regional support panel using existing native M/R values; visible from the start while JER exists and native start/end flags are unset, independent of registration/root completion; no influence actions. |
| `tools/aquileian_loyalty.py`, `aquileian_restoration.py`, `aquileian_reconstruction.py` | Retained national leadership, handover/restoration and reconstruction content. |
| `tools/Build-AquileianNativeHooks.py` | Minimal activation/absorption hooks and the shared recovery root in native JER trees. |
| `tools/Build-AquileianPreparationHooks.py` | One observation callback after native mission-timeout resolution, in the regional scope. Its historical name does not imply an authored preparation system. |

The native hook builders preserve reviewed native bytes outside their specific
insertions and reject unreviewed upstream drift. They do not rewrite native
regional preparation choices, comparisons, tie handling or event outcomes.
The category helper separately checks the installed file against the reference
snapshot and its pinned hash before inserting the Rilan visibility guard.
Existing AET and VER work is preserved.

Source scenarios and native override comparisons are required; they do not
establish observed HOI4 scheduling, UI layout, AI campaign balance or multiplayer
behaviour. Historical results and the new verification requirements appear below.

## Retained content and source provenance

- All 15 postwar programmes and their national/border continuations remain in
  scope, with constitutional A/B prose. Only the applicable country/programme
  is selectable. The current build contains **265 authored focuses, 112 event
  definitions, 1,499 localization keys per language and 29 generated files**.
  Retired takeover and approval events remain inert for queued-save compatibility.
  Camp-specific scenes distinguish native royal and revolutionary outcomes without
  granting unprepared movements an unrestricted programme menu.
- The 44 previously imported nonpolitical generic focuses have been removed.
  Four authored local foundations per region and twelve economic/military/civic
  focuses per programme replace them. The global generic focus tree is untouched.
  See `AQUILEIAN_POSTWAR_CAMPAIGNS.md` for the current structure and source tests.
- Matching EN/RU localization and UTF-8 BOM remain required; existing images only.
  Government identity, party names, elections, costs and modifiers are disclosed
  separately from narrative descriptions. Native effect previews display ordinary
  rewards, while internal flags and derived modifier arithmetic remain hidden.
- Postwar programme settlement takes 14/21/21 days. Ratification
  costs exactly 50 PP and can be deferred freely. Local reform normally takes
  35 days; national reconstruction takes 42. A defeated programme loses only its
  policy component: earned factories, literacy and development remain.
- Constitutional A: +5% stability, +10% PP gain. B: +10% factory output, +5% army
  organisation, -5% stability. The programme's distinct bonuses and later common
  institutions stack once in HSM_AQR_compact. Example completed AQR-only maxima
  across separate routes: communes-B +30% factory output; Colette-B +20% army
  organisation; Enfants +20% production-efficiency cap. These are not one combined
  government. These earlier compact-only figures exclude the new programme
  economy/military spirits, native spirits and event choices; they are not total
  national modifier ceilings for the expanded campaign.
- JER native baseline SHA256:
  `7b415747f52bc315efa7aa68637c1694348203aa0b751e8788543f8e7983b1b4`.
  Build-AquileianNativeHooks.py compares the installed Workshop file with the
  snapshot and refuses drift. Two absorption fields and two activation callbacks
  are patched; all six native trees also import the independent recovery root.
  A separate byte-guarded JER_decisions override adds one timeout observation
  callback after native local allegiance is resolved. Its reviewed baseline is
  `9d8b2a9ddbbb3093ee72b7c6bd9da4b9cb18b7feb23f445a243ddcb1b508a5d8`.
  Instant outcomes use the daily fallback after a native end-event option executes.
- Native `JER_decision_categories.txt` baseline SHA256:
  `44919731bd90a46320306b4725c0b4896b8d86cfe74c437c9404db33c6afac1d`.
  `aquileian_native_phase.build_native_category_overlay` requires an exact
  installed/snapshot match and preserves the source text outside the single
  Rilan committee visibility insertion. The main builder emits the override.
- Native sources: JER_decisions.txt and `events/Aquileia Events.txt` political outcomes;
  generic_griffon.txt; JER.txt; griffon_decisions.txt; JER_parliament_decisions.txt;
  country_JER localization; regional characters/histories; the GUI/scripted-GUI
  `eaw_jer_revolution` definitions and their existing sprites. These identify the
  reviewed source context; validation results are recorded separately below.

## Source verification and engine checklist

**Current verification, 2026-11-01:**

- Full `Test-AquileianRegions.py`: **95 tests passed in 68.357 seconds**, exit 0;
  log: `tmp/AQR-playtest-corrections-tests.log`.
- Single-bar `Test-AquileianSupportGUI.py`: **10 tests passed**. Geometry checks
  use one native split bar in an 86-pixel container; they do not prove rendering.
- Generation is current: 15 programmes, 71 authored focuses, 66 event IDs
  (including two inert legacy IDs), 807 keys per language and 16 generated files.
- Both native hook checks passed against the installed reference above.
- Regression coverage rejects invalid comparison grammar, reuses existing leader
  roles, keeps frozen movement ranking independent of later character loss,
  prevents duplicate delivery and automatic requeues, and validates fresh scopes
  after a player switch. All fifteen routes exercise centre support and actual
  leadership war, including once-only costs and proclamation after victory.

These are source and modeled-scenario results. The user's log establishes the old
runtime failures; no fresh engine launch, UI render or war playtest was performed.

National-identity follow-up on the same date: **23 targeted tests passed in
16.384 seconds** (`NationalIdentity National Inventory`), recorded in
`tmp/AQR-national-identity-tests.log`. The 95-test full run above precedes this
narrow correction. Follow-up coverage includes all fifteen programmes under both
constitutions, unchanged governments, legacy-save repair, preservation of later
cosmetics, EN/RU republican names and all native flag sizes. The user subsequently
clarified that "commune" meant Pridea's revolutionary route generally. The pictured
Enfants Terribles government is therefore consistent with the report; the reported
defect is its kingdom identity, not an established government substitution.

All-region identity follow-up: **24 targeted tests passed in 24.249 seconds**
(`NationalIdentity National Inventory`, exit 0), recorded in
`tmp/AQR-all-regions-identity-tests.log`. The source/model matrix covers all fifteen
programmes under both constitutional choices and migration from all four managed
cosmetics without ruler, government, election, territory or reward changes. It also
checks EN/RU royal names, exact native flag copies in all sizes and the complete
new RGB definition. Final colour binding uses the existing
`common/countries/cosmetic.txt`, beside the VER definitions. After this binding
adjustment, **16 tests passed in 8.269 seconds** (`NationalIdentity Inventory`,
exit 0; `tmp/AQR-identity-bindings-tests.log`). The final generator check passed
with 819 keys/language, 28 output files and zero stale files. These are source/model
checks, not an HOI4 rendering/save-load test.

| Region | Republican national programmes | Royal national programmes |
| --- | --- | --- |
| Rila / JEB | Moderate clubs, Cocardiers | Royal Michel, constitutional Michel |
| Westkeep / JRR | Colette | Absolutist Jeanne, Jeanne's coalition |
| Pridea / JFT | Communes, Enfants Terribles, FJA | Dennis |
| Vinovia / VIN | ABC, Chevaliers, SIS | Gadiffer |

The additional confirmed naming failures were the two harmonic constitutional
monarchies. The old royal formation cosmetics also had no matching national flag
files in the installed reference or submod. `HSM_AQR_KINGDOM` binds the native
`gfx/flags/JER_neutrality.tga` and its medium/small versions explicitly for all
ideologies, preventing regional-flag fallback. The exports are byte-for-byte copies;
no new artwork or portrait changes were made. Their provenance is the installed EaW
path in `EAW_UPSTREAM.md` (descriptor supports 1.19.*), inspected 2026-11-01:

| Size | Pixels | SHA-256 of native source and exported copies |
| --- | --- | --- |
| Normal | 82 × 52 | `0bae8f43cc72e19cd5ef9a9a5069915ab3e66e9e80b774461f6b5b6fdbd1b4b8` |
| Medium | 41 × 26 | `ba642344d0d6ae5c8c0bf464ba30ef379b1f57f57d852b3784b959358b753423` |
| Small | 10 × 7 | `03f76073e9feef291314725de9b652e1dfa652e10cdef953bf9568332b5d13a4` |

The inspected royal artwork is burgundy with golden Discret heraldry; the native
republican flags are blue-white-red with a golden griffon. Royal map/UI colour is
152/60/85; republican colour is 84/104/181. Native `JER_formed` and
`JER_JFT_formed` country flags remain for integration compatibility. The installed
script search found no additional active cosmetic-tag consumers relevant to these
regional campaigns; the native imperial-formation decision excludes all four tags.

Historical source results, **2026-11-01, before these playtest corrections**:

- Full `Test-AquileianRegions.py`: **85 tests passed in 70.096 seconds**;
  log: `tmp/AQR-native-integration-tests.log`.
- `Test-AquileianSupportGUI.py`: **10 tests passed**, including 64 visibility
  combinations, country-local values and rejection of changed native bindings.
- `Build-AquileianRegions.py --check`: **0 stale files**; 15 programmes,
  71 authored focuses, 812 keys per language, 16 generated files; event inventory: 66.
- Both native hook builder `--check` commands passed against the installed EaW
  reference and reviewed hashes recorded above.
- The first full run exposed two outdated fixture assumptions: comparing timed
  flags across elapsed days and expecting legacy programme replacement before
  the next daily opening tick. That revision changed fixtures to compare a
  clock-only baseline and exercise queued event timing while retaining their state
  and reward assertions. This did not address engine grammar acceptance.

Those passes missed invalid HOI4 trigger grammar. They are historical source/model
evidence, not a current passing validation or proof that the engine loaded the
generated definitions correctly.

### Observed parser failure and required correction

The user's actual [error.log](<C:/Users/laslo/OneDrive/Documents/Paradox Interactive/Hearts of Iron IV/logs/error.log:255>),
lines 255–302, records cascading unexpected-token and invalid-value errors in
`common/scripted_triggers/HSM_AQR_regions.txt`. The identified cause was unsupported
`>=` shorthand inside `check_variable`. The corrected settlement helper uses the
documented explicit comparison form, for example:

```text
check_variable = {
    var = HSM_AQR_native_value_JEB_michel
    value = HSM_AQR_native_value_JEB_moderate_revolutionary_clubs
    compare = greater_than_or_equals
}
```

The log is observed engine failure evidence. Reading the corrected helper is
source inspection, not proof of a successful post-fix game load. Fresh verification
must reject the unsupported shorthand, confirm generated triggers load without
this error cascade, and exercise their candidate restrictions in the engine.
The former 85-test suite did not establish engine grammar compatibility.

Required source coverage includes the native phase gates, one-time political
snapshot, immediate resolution, native ties, local/global outcome divergence,
all fifteen programme eligibilities and both constitutional choices. Retain
fractional PP boundaries, free deferral, stale event/decision guards, absent
characters, once-only rewards, modifier replacement, development, territory
conservation, JER demands and national restoration coverage. Verify that the
GUI only reads native values through one split bar and that no removed preparation
grant/action or peaceful JER-annexation offer remains reachable. Cover strict
candidate evidence, ties, absent JRR flags, Marais prose without broader eligibility,
and the permanent request flag before scheduling. Source/model tests do not prove
native event scheduling or rendering.

Commands (use a working Python executable and the installed EaW path):

```text
python -B -X utf8 tools/Build-AquileianRegions.py --eaw EAW_ROOT --check
python -B -X utf8 tools/Test-AquileianRegions.py --eaw EAW_ROOT
python -B -X utf8 tools/Test-AquileianSupportGUI.py --eaw EAW_ROOT
python -B -X utf8 tools/aquileian_base_tree.py --eaw EAW_ROOT
python -B -X utf8 tools/Build-AquileianNativeHooks.py --eaw EAW_ROOT --check
python -B -X utf8 tools/Build-AquileianPreparationHooks.py --eaw EAW_ROOT --check
python -B -X utf8 tools/Test-VereniaFormables.py --eaw EAW_ROOT
```

The listed builder `--check` modes do not write generated files. The regional
builder without `--check` writes outputs and removes its obsolete generated
preparation-ideas file; the native hook builders use explicit `--apply` for writes.
The base-tree command runs its read-only self-check. Run validation only after
the integration is ready, with the installed reference recorded in the result.

Historical evidence, **2026-11-01, before the native-integration redesign**:
the previous implementation recorded a passing source suite and native builder
checks in `tmp/AQR-preparation-final-tests.log`. That run included the now-removed
per-path preparation and paid replies. It is an archive of the old design, not
current validation, and its counts must not be reused as the new inventory.

### Planned engine scenarios

All cases below are **planned, not engine observed**. Use new campaigns and record
the submod revision, installed EaW version, enabled mods, country and starting save.
Retain before/after saves, relevant event/GUI screenshots and game logs. Use normal
progression to establish reachability; label any isolated forced setup separately.
Old saves containing removed preparation focuses or spirits need their own
migration test and are not promised compatible by this contract.

1. **PHASE — all four regions.** Begin before JER's preparation activation and
   work on an ordinary native-derived focus. Complete either native activation
   focus and advance through a daily tick. Registration must provide no support,
   PP, rifles, manpower, troops or spirits, and the authored postwar root must stay
   incomplete. Use the native regional decisions normally and verify their native
   costs/effects. Observe war onset: no authored preparation grants or sabotage
   scenes may appear. An early settlement event or interrupted working focus fails
   this case.
2. **PANEL — native support display.** For JEB, JRR, JFT and VIN, compare the
   additive panel with JER's native M/R values from a new campaign, before any
   JER activation focus or `HSM_AQR_started` registration. Repeat after activation,
   a native support decision and save/reload. Opening, hovering and closing the interface
   must change nothing. Check native controls remain clickable and no extra
   influence buttons appear. Exactly one split M/R bar must be visible, with both
   values correctly represented in its tooltip. The panel must not display another region's values
   or cover the native interface. Check it closes if JER ceases to exist or any
   native revolution start/end flag is set. Earlier panel availability must not
   take an early political snapshot or open postwar content.
   In Rila, verify committee-seat decisions remain available during preparation
   but their category closes when `HSM_AQR_native_outcome_recorded` is set.
   Westkeep, Pridea and Vinovia must retain their native category phase guards.
3. **SNAPSHOT — ordinary and immediate resolution.** Let the native mission
   expire, then separately obtain both native peaceful immediate outcomes.
   Record local winner flags and political forces at resolution; advance through
   delayed native events and daily maintenance, then save/reload. The snapshot
   must be taken once and survive later changes to national government/global
   outcome flags. Before the immediate end-event option executes there must be
   no invented result. Repeated maintenance must not resnapshot altered forces.
4. **TIES — native comparison.** Arrange equal native M/R support using a clearly
   labelled isolated setup; also cover a nearby royal and revolutionary majority.
   Resolve through the actual native mission. Its revolutionary tie outcome must
   remain unchanged. The postwar selector must follow that result rather than a
   previously expressed allegiance, largest organisation flag or GUI inference.
   Separately tie the leading movements within the winning camp: all eligible
   tied leaders should be offered, with no automatic programme assignment.
   Rila's leading/tied Marais coalition must still offer only the strongest named
   candidates, never all programmes. Test zero-value but flagged organisations in
   Pridea/Vinovia and genuinely unprepared movements: missing evidence must not
   unlock every path. For royal JRR test each native political flag, both flags
   and neither; absent flags must not create their corresponding choices.
5. **DEFEAT — local versus national result.** Run a region whose initial supported
   camp loses the local native contest, and a separate case where the local winner
   loses nationally. Check actual surviving government, peace and local-rule
   eligibility before expecting a selection. No locally defeated camp gets an
   unrestricted programme menu. Conversely, a surviving local winner must not be
   silently replaced solely because the opposite camp prevailed in the capital.
6. **OPENING — postwar readiness.** End the revolution while the region is still
   fighting an unrelated war, capitulated or under a foreign overlord; the root
   and selector must wait. Restore peace and qualifying local rule, then advance daily maintenance
   and event delivery. `HSM_AQR_opening` must complete automatically once, without
   interrupting an active focus. Inspect each event in `HSM_AQR.410`–`.413` and
   compare available programmes with the frozen native political context.
   Separately refuse central incorporation before ratification: this specific
   leadership war must allow the opening, selector and programme progression.
7. **STALE — deferred or already-open selections.** Open a programme event, then
   separately lose a required character, local rule or peace before clicking.
   Also keep an older event open while a valid programme is selected elsewhere.
   Invalid clicks must not install a defeated/unavailable programme, charge again
   or overwrite an active mandate. Check free deferral and permitted reopening
   after conditions recover, without regenerating the snapshot or duplicating
   rewards. Force failed delivery and separately defer a displayed event; advance
   beyond the seven-day queue and thirty-day pending guards, then save/reload.
   The permanent requested flag must block automatic repetition. Only an explicit
   eligible retry may queue another event. Cover all fifteen programmes with a
   compatible native setup.
8. **POSTWAR — retained progression.** Complete both constitutional choices in
   separate runs, including insufficient PP, delayed ratification and save/reload
   with an offer open. Check development and modifier consolidation, plus JER's
   native absorption hooks racing the automatic postwar offer. Exactly one live
   incorporation demand should offer joining the incumbent or immediate war;
   there is no live free-deferral option. A stale offer allows harmless dismissal.
   No acceptance reward, army transfer or war may execute twice.
   Complete consent/refusal regional accessions and the national epilogue; inspect
   native effect previews, tooltip size, tree layout and government identity.
   Complete each programme's economic, military and civic chains: each spirit
   upgrades in place; modern society is reachable; science-led programmes can
   reach five research slots. Five-slot old saves get research bonuses instead
   of a sixth slot or an inaccessible final focus. Open a new story scene, then
   lose its government: dismissal must remain possible without granting rewards.
9. **NATION — leadership and restoration.** Support existing JER and complete the
   playable handover; confirm its incumbent and focus progress survive. Separately
   choose war for national leadership and progress through the normal campaign
   gates. There must be no peaceful offer or stale event that annexes JER into
   the province. Another human's JER slot cannot be taken; incorporation of a
   regional player into that centre retains its explicit game-over choice.
   After victory restore living Moriset, Vivienne after his death, a provisional
   republic and an existing republican successor. Check native focus history,
   character ownership, party/elections, tree reload and no repeated succession.
   Releasing/restoring a regional country must not manufacture a new local result
   from the restored national government. Dead or foreign-held leaders stay
   unavailable. Paid reconstruction and its cleared crisis stages must survive
   handover without being awarded or charged again.
10. **PERIPHERY / HERZLAND — retained safeguards.** Test delivery during war,
    unanswered offer expiry and recall after peace, explicit permanent refusal,
    foreign subjects/factions and disputed control. Inspect recovery in every
    native JER tree. Check new JHZ, an existing own subject holding Griffenheim
    and foreign sovereign JHZ; no foreign land may be stolen or cored. Finish an
    AI-run revolution to observe timing and programme selection separately from
    source arithmetic.

Source tests do not establish engine scheduling, AI pacing, combat balance,
UI rendering, save migration or multiplayer safety. Those claims require the
observations above and an explicit result attached to each case.
