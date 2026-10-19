# Barrad Magotechnical Collegium

The Collegium continues the friendship ending under civilian oversight. Its institutional
story lives in HSM_BAR_collegium files; the four-faculty research menu and its projects
live in HSM_BAR_mtk files. Neither component appoints a new political leader or changes
the Service's anomaly archive.

## Integration contract

Main owns the native barrad_end.2 divergence, Ambrosius's defeat, all four surviving
characters, barrad_endgame = 1, political leadership, common research/facility setup,
and the HSM_BAR_common_reconstruction shared branch at x >= 24.

Country-scope entry order:

1. Set HSM_BAR_active and HSM_BAR_collegium.
2. Call HSM_BAR_collegium_initialize = yes.
3. Load HSM_BAR_collegium_tree with keep_completed = yes.

HSM_BAR_collegium_initialize is idempotent. It installs one provisional idea and one
dynamic service modifier. The initial root calls it again as a safeguard. The existing
HSM_BAR_collegium_pulse hook now only restores civilian allocation at peace, reports that
return once, and refreshes concrete service benefits. There is no monthly resource drain.
HSM_BAR_collegium_refresh rebuilds five modifier outputs from named completed programmes
and allocation policy. Those outputs are neither spendable nor read by progress gates.

The retired HSM_BAR_public_trust and HSM_BAR_capacity variables have no reads, writes,
labels or displays in this component. Shared core owns clearing obsolete save values.
Call HSM_BAR_collegium_cancel_programs = yes during institutional dissolution, before
route flags are cleared, if HSM_BAR_collegium_initialized is present. This clears eight
pending programme flags and refunds only personnel with recorded new assignment flags.
Shared institutional dissolution calls that hook before clearing route flags.

This component does not create a country leader or alter politics. Main's
BAR_captain_gasienica remains the civic chair. The tutelage ending gives the four
executive direction of college programmes; it does not promote them to collective
country leaders or remove the civic chair. All three endings preserve their friendship,
patient refusal, independent records and a court capable of intervention.

## Project interface and fallback

Produced programme flags:

- HSM_BAR_clinic_program: focus HSM_BAR_collegium_clinic.
- HSM_BAR_grid_program: focus HSM_BAR_collegium_grid.
- HSM_BAR_wards_program: focus HSM_BAR_collegium_wards.

These mark service programmes, not completed magical inventions. The separate research
component need not gate projects on them. Only that component grants:

- HSM_BAR_project_clinic_done: accepted by longevity and bodycraft.
- HSM_BAR_project_grid_done: accepted by civilian reserve.
- HSM_BAR_project_wards_done: accepted by ritual ethics.

Every advanced gate still accepts its existing completed institute-project flag.
The no-DLC alternatives are specific completed work:

- Clinic: HSM_BAR_clinic_program, patient_rights, inspectors, and completed focus
  HSM_BAR_collegium_life.
- Grid: HSM_BAR_grid_program, public_budget and school_open.
- Wards: HSM_BAR_wards_program, consent and inspectors.

Unprefixed flags above use HSM_BAR_collegium_. No focus grants project completion,
technology or a facility. Main supplies HSM_BAR_institute_open and its associated
magical technology/facility for the separate project system. The 24 faculty projects
and all-five-preparations-before-Opus contract are untouched.

The first report requires independent_archive, inspectors, public_budget,
HSM_BAR_clinic_program and school_open. Assembly additionally requires the civic cabinet,
report_answered, peer_review, patient_rights and consent, alongside its existing focus
prerequisites. Neither branch choice, DLC, a war nor an optional paid programme is needed
for the main endings. Choosing independent charter hearings adds a 21-day deliberation
before the three charter focuses; accepting published amendments allows immediate work.

## Tree membership

The research menu below supplements these trees; it does not replace their institutional
programmes or the separate magical-institute projects.

Both trees explicitly include the common reconstruction, civic republic and frontier
roots once. EaW brings their descendants with them. The 37 institutional/scientific
focuses use absolute x = 0..17, leaving the common and new political branches clear.
Costs are 4 or 5 weeks (28/35 days). The future tree retains all 18 initial institutional
focuses and adds 19. Three mutually exclusive charters leave 31 institutional focuses
and four optional applications available in one campaign.

All 37 require the active independent Collegium, no capitulation and owned/controlled
homeland state 624. The charter assembly also requires the new civilian cabinet; no
war or territorial conquest is required for the institutional ending. The three charters
govern the Collegium, not competing replacements for the republic's government.
See [civil government](barrad-collegium-civic.md) and
[regional policy](barrad-collegium-frontiers.md).

School, wards, grid, clinical follow-up, district repairs, teachers, wartime logistics
and peer review grant relevant research bonuses. Land restoration now also adds one
infrastructure level in state 624 without declaring magical contamination healed.
Four final applications require completed Chorus, Manufactory, Last Minute or Contact
trials respectively; no focus completes any of the 24 journal projects. Their benefits
are limited research coupons, separate from the projects' permanent research modifier.

The future root has no prerequisite linking it into the initial tree's shared descendant
closure; it instead requires HSM_BAR_collegium_second_stage. Focus HSM_BAR_collegium_future
sets that flag and loads HSM_BAR_collegium_future_tree with keep_completed = yes. This
prevents the later branches from being auto-included early.

Initial explicit list:

- HSM_BAR_collegium_oath
- HSM_BAR_collegium_names
- HSM_BAR_collegium_silver
- HSM_BAR_collegium_leopold
- HSM_BAR_collegium_asinti
- HSM_BAR_collegium_viira
- HSM_BAR_collegium_records
- HSM_BAR_collegium_life
- HSM_BAR_collegium_clinic
- HSM_BAR_collegium_wards
- HSM_BAR_collegium_school
- HSM_BAR_collegium_grid
- HSM_BAR_collegium_land
- HSM_BAR_collegium_refugees
- HSM_BAR_collegium_oversight
- HSM_BAR_collegium_budget
- HSM_BAR_collegium_report
- HSM_BAR_collegium_future

Additional future list:

- HSM_BAR_collegium_future_root
- HSM_BAR_collegium_longevity
- HSM_BAR_collegium_bodycraft
- HSM_BAR_collegium_ethics
- HSM_BAR_collegium_teachers
- HSM_BAR_collegium_civil_reserve
- HSM_BAR_collegium_war_reserve
- HSM_BAR_collegium_peer_review
- HSM_BAR_collegium_memorial
- HSM_BAR_collegium_assembly
- HSM_BAR_collegium_open
- HSM_BAR_collegium_republic
- HSM_BAR_collegium_tutelage
- HSM_BAR_collegium_lasting
- HSM_BAR_collegium_students
- HSM_BAR_collegium_applied_chorus
- HSM_BAR_collegium_applied_manufactory
- HSM_BAR_collegium_applied_last_minute
- HSM_BAR_collegium_applied_contact

## Scenes and decisions

There are 24 triggered scenes in namespace HSM_BAR_collegium, each with a state/resource
consequence. Scenes 1-10 establish accountability and the joint services; 11-16 test
mature institutions; 17 gives a separate ending text for each constitution; 18 restores
civilian priorities; 19 is the students' epilogue; 20 debates emergency authority;
21 addresses another patient complaint; 22 returns repaired land to its farmers;
23 tests an exit from a protective ward; 24 remembers victims without claiming their
forgiveness. Most have two materially different options. Refusing an experiment remains
permitted under every constitutional settlement.

There are eleven decisions. The repeatable petition grinder is removed. Eight timed
programmes can grant their concrete result only once; interrupted work may be retried,
but completed programmes disappear. Existing IDs remain for native timer compatibility.

| Programme | PP / days | Resources and result |
| --- | --- | --- |
| train_cohort | 15 / 35 | Assign 200 personnel, returned once; research +0.5% and one 50% electronics coupon |
| equip_workshops | 20 / 35 | One factory and 25 support equipment; civilian factory construction +1% |
| clinic_rounds | 15 / 35 | 25 support equipment; one 50% hospital coupon and wartime recovery +2% |
| repair_fields | 30 / 42 | One factory and 100 assigned personnel, returned once; civilian factory construction +1%, scene .22 |
| settlement_houses | 40 / 35 | One factory; 500 adult volunteers, no implied consent to experiments |
| onward_travel | 20 / 21 | 20 support equipment; stability +3% |
| seek_mandate | 0 / 21 | Public approval removes the active wartime emergency stability penalty |
| maintain_reserve | 15 / 35 | 50 support equipment; wartime supply consumption -2% |

The other three decisions hear the clinic complaint and switch wartime/civilian allocation;
all are free. All programmes revalidate institutional access at start and completion.
Recorded personnel return on cancellation without returning consumed equipment or PP.
Completion/refund replay cannot award the result twice. A cleanup call before route
removal clears pending starts even while the old route still appears active.

The institutional spirit uses explicit, bounded contributions, with matching tooltips:

| Completed work or policy | Contribution |
| --- | --- |
| independent_archive; inspectors | Stability +1% each |
| clinic_access / clinic_followup | Stability +2% / research +0.5% |
| school_open; research_board; peer_review | Research +1%, +0.5%, +1% |
| cohort_trained; grid_workshops | Research +0.5% each |
| HSM_BAR_grid_program; civil_reserve | Civilian factory construction +2% each |
| grid_households; workshops_equipped; fields_repaired | Civilian factory construction +1% each |

Construction contributions apply only under civilian allocation. Wartime allocation
replaces them with supply consumption -4% and army recovery +4%. reserve_equipped adds
another -2% supply; clinic_rounds_done adds +2% recovery. Without emergency_mandate,
stability is reduced by a fixed 2% while the wartime transfer is active. No resource is
consumed monthly. An immediate standing authorisation accepts that tradeoff; choosing
the residents' mandate first requires 21 days of deliberation. Peace or a free civilian
allocation decision returns the civilian services.

Numeric currency options were removed from all 24 scenes. Their narrative and flags
remain, with substantive research coupons, service policies, refugee programmes,
consent safeguards and clinical pauses replacing obsolete point awards. PP fees remain
only for explicit compensation/independent supervision, not retired scores. Compensation
after the first report pauses new trial recruitment for 30 days; the later complaint can
pause it for 60 days. Existing treatment continues. Most research choices trade a broader
pair of 50-75% coupons against a narrower, stronger coupon or a different discipline.

One constitutional idea replaces the provisional idea. The three endings trade a modest
research/stability benefit, civilian political/output benefits, or stronger research with
a PP penalty and more restricted public control. At most two institutional national modifiers are active together.
Separate special-project rewards are outside this component's ownership.

## Faculty Research Menu

After `HSM_BAR_collegium_oath`, the human Barrad player's political panel gains a journal
button. Its four departments have distinct generated laboratory folios, shared native
controls and readable EN/RU documents without redactions. The window is 1000x700;
long reports use native scrolling, not reduced text size. No new numeric meter is added.

| Faculty | Five preparatory projects | Magnum Opus |
| --- | --- | --- |
| Viira | Field Atlas; Shared Senses; The Sleeping Lecture; Crystal Memory; Spell Notation | The Chorus |
| Leopold | Crystal Prosthetics; Self-Repair; Revolver Howitzer; Crystal Drive; The Sorting Engine | The Manufactory |
| Silver Star | Necrotic Suture; Tissue Bank; Ageless Sleep; Spell Sterilisation; Phantom Pain | The Last Minute |
| Asinti | Ritual Brake; Silent Witness; Memory of Place; Threshold Compass; Empty Vessel | Contact |

Each project has a proposal, theoretical report, trial record and conclusion: **96 pages
per language**. Reports include competing explanations, unsuccessful trials and comments
between the four colleagues. These inventions and experiments are an authored continuation,
not pre-existing EaW canon. Department identity reflects the local character biographies
listed below; the friendship route deliberately changes how they treat others.

The proposal is available immediately. Budgets and durations vary by project and faculty.
Idle faculties choose sequential or instrumented trials and civilian or field application;
the paid trial snapshots both choices. Instrumentation costs more PP and reserves one
civilian factory for a shorter trial. Civilian dissemination costs more upfront; field
application has different rewards and continuing PP upkeep. Fixed failures stay failures.
Every department may run one stage at a time; different departments work concurrently.
The menu starts native timed missions, which appear with their countdowns in decisions.
All projects work without special-project DLC; these are not duplicate institute projects.
AI can start one paid stage per week in peacetime while preserving a 100 PP reserve;
it uses sequential, civilian application and the same eligibility checks as the player.
See [project policies, pacing and verification](barrad-collegium-projects.md).

All five preparatory projects of the same department must finish before its opus starts.
A completed negative result counts; cancellation does not. The Sleeping Lecture, Revolver
Howitzer, Ageless Sleep and Silent Witness give **no reward**. Partial results have limited
applications; Asinti's opus remains a partial success. The Last Minute stabilizes dying
patients temporarily; it does not grant immortality or resurrect the dead.

Reports unlock after their stage completes. Trial outcomes and numerical applications
remain hidden until trials finish. Applied results are shown separately beneath the
document and accumulated in `HSM_BAR_mtk_research`, independent of the institutional
service modifier and the Service's anomalous-research modifier. Refresh recalculates
from completed flags; revisiting a page, replaying a callback or refreshing cannot stack
bonuses. Existing clinic moratorium prevents new Silver Star trials, not ongoing care.

Work needs owned and controlled homeland state 624, the living and present faculty head,
an active Collegium, the oath and no capitulation. Loss of access cancels the paid stage
without a refund; restarting pays again. Completed documents survive temporary access
loss. The existing dissolution effect tears down missions and results synchronously.

Canonical project IDs, times and costs: `tools/data/barrad-collegium-projects.json`.
Gameplay generation: `tools/Build-BarradCollegiumProjects.cjs`; presentation generation:
`tools/Build-BarradCollegiumMenu.cjs`. Handwritten documents are not generated by either.
See [art sources and preview workflow](../art/barrad-collegium-menu.md).

## Local sources

Checked the local EaW dependency, not a web summary:

- EaW/localisation/english/country_BAR_l_english.yml:27-30, the four category biographies:
  Silver's mortality/paranoia and envy of White Star; Leopold's illness and original wish
  to help; Asinti's enslavement followed by experiments on living subjects; Viira's
  exceptional deer magic and ambitions.
- The same file:1350-1352, barrad_end.2: the four defeat Ambrosius, repent and are killed
  by the crowd in the original ending. Main's alternate event is the deliberate
  divergence. Sparing them begins public obligations, not unlimited rule.
- The same file:1355-1363, barrad_friends.1/.2/.3: Silver learns to sit with Viira,
  discusses mortality with Leopold and considers helping Asinti prevent suffering.
  These establish friendship as plausible without rewriting the earlier abuses.
- EaW/events/Barrad Events.txt:520 onward, native barrad_end.2 and friendship events.
- EaW/common/national_focus/BAR.txt:1 onward, staged trees with shared roots.
- EaW/common/decisions/supply_decisions.txt:1 onward, timed native factory commitments.
- EaW/common/technologies/support.txt:1202 onward, the hospital_tech category.

The new scenes are original continuation text. They do not imply that the four acquired
an immortal, divine, lich or otherwise transformed form.

## Verification

Run: pwsh -NoProfile -File tools/Test-BarradCollegium.ps1

The test parses all eight owned Clausewitz files, validates tree lists, stage isolation,
prerequisites, coordinates, 28/35-day costs, preserved completion, event reachability,
localisation keys and UTF-8 BOM, EN/RU parity, and inherited focus/shine/idea/event sprites.
It models first-option and last-option playthroughs for each of the three endings, with
no DLC or completed special projects, and checks that all 31 compatible institutional
focuses reach the epilogue. The civilian cabinet is an explicit external boundary,
validated by its own civic suite; a separate check rejects the assembly without it.
Optional application tests reject an unfinished Magnum Opus or theory without trials.
No meter values, recovery grinding or optional programme completions are injected into
those walks. The test checks exact milestone contributions, repeated pulses without
upkeep, policy exclusions, mandate timing, restoration at peace and inactive-route zeroes.
Programme fixtures verify resource boundaries, recorded starts, unique completion/refund,
cancellation on loss of route, homeland, independence or control, synchronous cleanup
before route removal, and no fabricated refund for a legacy callback without evidence.

The model does not simulate native PP income, the whole common tree, military defeat,
save serialization or actual engine execution. In-game focus rendering, save/load,
event-window text layout, dynamic-modifier refresh timing and campaign balance still need
a live game session. No engine verification is claimed.

## Files

- common/national_focus/HSM_BAR_collegium.txt
- common/scripted_effects/HSM_BAR_collegium_effects.txt
- common/scripted_triggers/HSM_BAR_collegium_triggers.txt
- common/ideas/HSM_BAR_collegium_ideas.txt
- common/dynamic_modifiers/HSM_BAR_collegium_modifiers.txt
- common/decisions/HSM_BAR_collegium_decisions.txt
- common/decisions/categories/HSM_BAR_collegium_categories.txt
- events/HSM_BAR_collegium_events.txt
- localisation/english/HSM_BAR_collegium_l_english.yml
- localisation/russian/HSM_BAR_collegium_l_russian.yml

The paths above are relative to mod/HoISubmod. The research menu additionally uses
`interface/HSM_BAR_mtk.gui` and `.gfx`, the HSM_BAR_mtk scripted GUI/localisation/trigger
files, HSM_BAR_mtk_projects gameplay files, and twelve HSM_BAR_mtk EN/RU localisation
files. Institutional dissolution in `common/scripted_effects/HSM_BAR_core_effects.txt`
now invokes project, civic-government and frontier cleanup; accepted Kasa/Southern Deer
agreements in `HSM_BAR_diplomacy.txt` immediately reconcile frontier war goals.

Faculty verification on 2026-10-07: project fixtures with `--native` passed 930 scenarios;
menu tests passed 33 groups; integration passed 267 checks; the existing Collegium suite
passed 2964 assertions. Both builders' `--check` commands verify generated text without
rewriting it. The preview checked 216 bilingual states and produced 16 static images;
50 states require native scrolling. All four faculty skins were visually inspected.
These checks do not establish native scheduler ordering, save/load, live input or UI-scale
behavior. Those still require a restarted game and playtesting.

## Civic and Frontier Verification, 2026-10-08

This is the earlier civic/frontier checkpoint. The subsequent project-policy and
custom-art integration is verified in [the readiness pass](barrad-readiness-pass.md).

The follow-up adds 31 focuses (16 civic, 11 frontier, four optional applications),
13 events and 16 frontier decisions. Existing charters determine Collegium governance,
not replacement of the civilian government. Both tree stages retain the new branches.
No new artwork, release export or commit accompanies this change.

Windows verification: all 20 suites below passed with zero failures. Counts mix
assertions and scenario groups; they are not a single campaign-coverage percentage.

| Command | Passed |
| --- | ---: |
| `pwsh -NoProfile -File tools/Test-BarradCollegium.ps1` | 3361 |
| `node tools/Test-BarradCivic.cjs --native` | 104 |
| `node tools/Test-BarradCollegiumFrontiers.cjs --native` | 88 |
| `pwsh -NoProfile -File tools/Test-BarradContent.ps1` | 315 |
| `node tools/Test-BarradCollegiumProjects.cjs --native` | 930 |
| `node tools/Test-BarradCollegiumMenu.cjs` | 33 |
| `node tools/Test-BarradDevelopment.cjs` | 92 |
| `pwsh -NoProfile -File tools/Test-BarradDiplomacy.ps1` | 38 |
| `node tools/Test-BarradNativeContracts.cjs` | 23 |
| `node tools/Test-BarradPhases.cjs` | 53 |
| `node tools/Test-BarradServiceRewards.cjs` | 195 |
| `node tools/Test-BarradModifierTooltips.cjs` | 14 |
| `node tools/Test-BarradServiceStory.cjs` | 37 |
| `node tools/Test-BarradSecrecy.cjs` | 16 |
| `node tools/Test-BarradCaseOutcomes.cjs` | 217 |
| `node tools/Test-BarradResearchOperations.cjs` | 379 |
| `node tools/Test-BarradNormalization.cjs` | 47 |
| `pwsh -NoProfile -File tools/Test-BarradLegacyDecisions.ps1` | 50 |
| `pwsh -NoProfile -File tools/Test-BarradAnomalies.ps1` | 38 |
| `node tools/Test-BarradCases.cjs` | 26 |

Integration inventory: 135 Barrad focuses, 160 events, 2821 English keys, with EN/RU
parity and installed sprites checked. Native peace-conference timing, live focus
layout, save/load and military balance still require an HOI4 playtest.

## Meter Retirement Verification, 2026-10-10

The retirement changes only the Collegium effects/triggers/decisions/focuses/events,
its EN/RU localisation, its test and this document. The dynamic-modifier definition and
all art bindings remain unchanged. No faculty project generator or project runtime was
edited. Shared core, Service and cross-component tests are parent-owned.

| Command | Result |
| --- | --- |
| `pwsh -NoProfile -File tools/Test-BarradCollegium.ps1` | PASS: 5825 assertions |
| `node tools/Test-BarradCollegiumProjects.cjs --native` | PASS: 1393 scenarios |
| `node tools/Test-BarradCollegiumMenu.cjs` | PASS: 57 groups |

All six first/last-option charter walks finish the 31 compatible institutional focuses
without DLC, war, optional paid work or meter manipulation. The four optional research
applications still need completed Magnum Opus trials. The complete shared regression
also passed; see [integrated verification](barrad-implementation.md#meter-retirement-verification).

### Old-save boundary

Existing timed decision IDs were retained, but pre-retirement running programmes lack
the new pending and personnel-assignment evidence. Their completion must not invent a
new milestone or an unproven refund. In particular, an old train_cohort may already have
spent 200 manpower; this patch does not silently reimburse it without proof. The model
asserts that conservative behavior.

Native scheduling, cancellation ordering, old in-flight timer continuation and release
of their native factory reservation are unverified in a running game. Completed focus
and narrative flags continue to contribute their listed concrete benefits; retired
meter balances are not converted into work, bonuses or currency. The unrelated faculty
project save contract remains unchanged. New campaign playtesting is recommended.
