# Aquileian native settlement

Contract revised 2026-11-01 after the user's native-integration playtest.
**The 95-test and 10-GUI-check results below describe the earlier integration.**
The expanded focus/transition contract now lives in
[AQUILEIAN_POSTWAR_CAMPAIGNS.md](AQUILEIAN_POSTWAR_CAMPAIGNS.md); its checks are separate.
Native preparation replaces our former prewar focuses and influence decisions.
This document records the current selection rules and observed failure evidence;
the earlier source pass is historical, not validation of the corrections.

## Native inputs and fifteen programmes

The **actual local winning camp** overrides preparatory intent. M = royal;
R = revolutionary. Broad native allegiance flags are
`JER_<TAG>_monarchist` / `JER_<TAG>_revolutionary`; they are historical inputs,
not permission to offer a programme of the defeated camp.

| Programme | Camp | Native input / character |
| --- | --- | --- |
| `JEB_royal` | M | `JEB_duke_michel_discret` |
| `JEB_constitutional` | R | `JEB_michel`; available `JEB_duke_michel_discret` |
| `JEB_moderate` | R | `JEB_moderate_revolutionary_clubs` |
| `JEB_cocardiers` | R | `JEB_extremist_revolutionary_clubs` |
| `JRR_absolutist` | M | `JRR_absolutist` |
| `JRR_coalition` | M | `JRR_reformism` |
| `JRR_colette` | R | `JRR_colonel_colette_solide` |
| `JFT_dennis` | M | `JFT_baron_dennis_discret` |
| `JFT_communes` | R | `JER_JFT_commie_supp`; `JFT_second_commune_influence` |
| `JFT_enfants` | R | `JER_JFT_fash_supp`; `JFT_les_enfants_terribles` |
| `JFT_fja` | R | `JER_JFT_dem_supp`; `JFT_FJA_socdems` |
| `VIN_gadiffer` | M | `VIN_duke_gadiffer_discret` |
| `VIN_abc` | R | `JER_VIN_movements1`; `VIN_abc_influence` |
| `VIN_chevaliers` | R | `JER_VIN_movements2`; `VIN_chevaliers_influence` |
| `VIN_sis` | R | `JER_VIN_movements3`; `VIN_students_influence` |

JEB also records **`JEB_other_clubs`**, the Marais/nonaffiliated group.
JEB's native revolutionary opening initialises moderate/Michel/extremist/other
seats to **58/27/102/39**. JFT/VIN organisation flags can coexist. VIN introduction
events set flags without initialising faction influence: flagged zero-score
movements remain genuine candidates.

## Native facts versus authored settlement rules

**Native:** the named flags, influence variables, characters, preparatory choices
and actual camp outcome. **Authored:** translating those inputs into our fifteen
postwar programmes; native EaW does not itself implement this selection algorithm.

- Freeze political inputs once at actual revolution resolution. Later native
  committee decisions cannot alter the frozen result.
- Offer only the actual native winning camp's strongest prepared named movements
  and all tied eligible leaders. For JFT/VIN,
  an organisation flag qualifies even at zero; a positive frozen score also
  preserves evidence in a save lacking its expected flag.
- A **Marais lead or top tie** changes JEB's coalition narrative, but candidates
  remain restricted to the strongest eligible named movements. It does not open
  all revolutionary programmes, silently assign Marais seats to moderates or
  create a sixteenth route.
- **No unprepared all-programme fallback.** Missing preparatory evidence does not
  grant a new mandate or a choice of every route. Royal JRR requires the frozen
  `JRR_absolutist` flag for the absolutist programme and `JRR_reformism` for the
  coalition: both flags permit both, neither flag permits neither. Sole native-ruler
  programmes retain their actual-camp and character guards.
- Named native characters must be available in the regional country. The helper
  does not recreate or import them. Existing compatible ratified routes survive.
- Michel's constitutional choice authorises reconciliation; later focuses
  negotiate his invitation/return. Royal JRR acknowledges Bassot's countercoup
  and authorises negotiations for Jeanne, not her immediate installation.
  Colette retains command while its civil obligations are negotiated.

## Installed-source provenance

Reference: `C:/shit/Steam/steamapps/workshop/content/394360/1826643372`.
Descriptor compatibility `1.19.*` is a HOI4 version declaration, not an EaW
release identifier. Research was bounded to these regional political inputs.

- **JEB:** [aquileia_two.1–2](<C:/shit/Steam/steamapps/workshop/content/394360/1826643372/events/Aquileia Events.txt:9976>) supplies allegiance, initial committee seats and club activation. [Committee localization](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/localisation/english/country_JER_l_english.yml:2159) names the four groups; line 2163 identifies the Marais support action. [aquileia.10](<C:/shit/Steam/steamapps/workshop/content/394360/1826643372/events/Aquileia Events.txt:380>) is the revolutionary outcome.
- **JRR:** [aquileia.94](<C:/shit/Steam/steamapps/workshop/content/394360/1826643372/events/Aquileia Events.txt:4850>) chooses allegiance; [aquileia.101](<C:/shit/Steam/steamapps/workshop/content/394360/1826643372/events/Aquileia Events.txt:5100>) sets absolutist/reformist flags; [aquileia.11](<C:/shit/Steam/steamapps/workshop/content/394360/1826643372/events/Aquileia Events.txt:533>) promotes Bassot.
- **JFT:** [aquileia.83](<C:/shit/Steam/steamapps/workshop/content/394360/1826643372/events/Aquileia Events.txt:4430>) chooses allegiance; [aquileia.88–90](<C:/shit/Steam/steamapps/workshop/content/394360/1826643372/events/Aquileia Events.txt:4635>) sets movement flags and changes the three influence variables.
- **VIN:** [aquileia.73](<C:/shit/Steam/steamapps/workshop/content/394360/1826643372/events/Aquileia Events.txt:4039>) chooses allegiance; [aquileia.76–78](<C:/shit/Steam/steamapps/workshop/content/394360/1826643372/events/Aquileia Events.txt:4150>) sets movement flags; [native repeaters](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/common/decisions/VIN_decisions.txt:124) redistribute faction influence.
- **Outcome:** [JER_revolution_mission](C:/shit/Steam/steamapps/workshop/content/394360/1826643372/common/decisions/JER_decisions.txt:108) resolves M>R as royal and ties as revolutionary. Main also records native instantaneous peaceful outcomes.

## Selection API and request lifecycle

`build_native_settlement(L,trig,effect,once,tt,event,option,config,route_data)`
returns four retry decision blocks for existing provincial affairs.

Exports: `HSM_AQR_snapshot_native_politics`,
`HSM_AQR_queue_native_settlement`, and
`HSM_AQR_native_eligible_<RID>`. Snapshotting follows main's
`HSM_AQR_native_outcome_recorded`; queuing follows the postwar opening and
local-rule checks, at peace or during the region's incorporation-refusal war
against JER. Events **410–413** serve JEB/JRR/JFT/VIN.
Selection records `HSM_AQR_native_mandate_<RID>`; it grants no rewards, changes
no native support, and installs no government. Existing programme work remains.

Set the permanent `HSM_AQR_native_settlement_requested` flag **before** queuing
the next-day event. It must survive failed delivery, deferral, timed-guard expiry
and save/reload. Daily maintenance does not clear it or queue a repeated request.
The seven-day queued flag and thirty-day pending flag are additional guards;
neither replaces the permanent request flag. An explicit eligible
`HSM_AQR_native_settlement_retry_<TAG>` decision clears the request/presented
flags and queues again, immediately setting the request flag anew. Candidate,
phase, local-rule and no-valid-mandate checks still apply at selection/retry.

## Support display and national direction

The regional GUI displays **one shared split monarchist/revolutionary bar**, not
two independent bars. It uses the native split sprite, local monarchist support
for its frame and both actual local M/R values in the tooltip. There are no new
buttons, support actions or counters. Panels are available from campaign start
while JER exists and `JER_revolution_begun`, `JER_revolution_ended` and
`JER_revolution_ended_2` are unset, without a completed JER root or
`HSM_AQR_started`. Political inputs are still snapshotted only at the outcome.

The separate national direction is **support the existing centre or wage war for
leadership of Aquileia**. Supporting the centre must retain the playable handover
to native JER with its incumbent and national progress intact. A province must
not receive a peaceful offer to annex JER or assume its leadership by agreement.
This does not remove voluntary incorporation of a province into the centre.
`tools/aquileian_loyalty.py` now implements this split. The war choice ends JER
subordination and shared faction membership, cancels bilateral obligations and
declares annexation war immediately. The newer one-event transition supersedes
its former 100-PP fee and approval chain; see the expanded campaign contract.

## Playtest failure and verification status

The user's [engine error log](<C:/Users/laslo/OneDrive/Documents/Paradox Interactive/Hearts of Iron IV/logs/error.log:255>),
lines 255–302, records cascading parse failures in generated
`common/scripted_triggers/HSM_AQR_regions.txt`. The identified cause was invalid
`>=` shorthand inside `check_variable`. The corrected helper now emits explicit
`var`, `value` and `compare = greater_than_or_equals` fields. A fresh engine load
must establish that the definitions parse and their conditions work as intended.

The **85-test source pass on 2026-11-01 predates these corrections** and missed
this engine grammar defect. Earlier GUI and builder passes are likewise historical.
The corrected full suite passed **95 tests in 68.357 seconds**; see
`tmp/AQR-playtest-corrections-tests.log`. Ten focused single-bar GUI tests also
passed. The observed log proves a failure in the earlier build; the corrected
sources have not yet been loaded and exercised in HOI4.

Required checks include actual-winner versus defeated-camp selection, strongest
prepared movements and ties, Marais prose without broader options, absent JRR
flags, no unprepared fallback, stale clicks and failed delivery with no automatic
repeat after guard expiry. Recheck the single-bar UI, centre-support handover and
absence of both live and stale peaceful JER-annexation paths. Detailed planned
scenarios remain in `AQUILEIAN_REGIONS_IMPLEMENTATION.md`.

Main owns phase/migration integration and runtime generation; Curie owns prose;
Dirac owns integration testing. Earlier bounded parsing/candidate checks were
source/model evidence only. **No successful post-correction engine validation is
claimed.**
