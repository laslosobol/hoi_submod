# Barrad Collegium: Civil Government

## Scope

Sixteen shared focuses at x40/44/48, y0-8, with 28/35-day durations. Five original EN/RU scenes establish durable public policies. This is the administration of the Republic, not another research council or a duplicate of the College's internal oversight/budget. Gasienica remains the civilian head; the four surviving scholars advise government without owning ministries. All three existing College charters remain compatible, including scientific tutelage over the College itself.

No new resource, meter, research completion, free core, annexation, leader change or war goal is introduced here. Existing EaW/vanilla icons and their shine sprites are reused. Territorial policy is prospective and does not assume a war has already happened.

## Integration Contract

- Explicitly include `shared_focus = HSM_BAR_civic_republic` in **both** `HSM_BAR_collegium_tree` and `HSM_BAR_collegium_future_tree`. Its descendants follow the shared-focus graph. The root deliberately has no prerequisite linking it into another tree automatically.
- `HSM_BAR_civic_cabinet` is reachable in stage one. It requires the municipal settlement, a salaried civil service, national accounts and the judicial settlement. It never requires College stage two, its assembly, foreign diplomacy or a war. The main module may therefore require it for `HSM_BAR_collegium_assembly` without a cycle.
- `HSM_BAR_civic_foreign_office` follows the cabinet. Completion sets the existing `HSM_BAR_diplomacy_open` flag, enabling standard envoys. The separate frontier branch can require this completed focus.
- `HSM_BAR_civic_refresh = yes` recomputes only civic derived variables and installs/removes `HSM_BAR_civic_government`. Safe to repeat; it does not schedule events.
- `HSM_BAR_civic_pulse = yes` refreshes and issues unresolved scenes. **Already called by this module's own `on_daily_BAR` hook; no additional daily hook is required.** Focus completion calls it immediately.
- Institutional dissolution calls `HSM_BAR_civic_teardown = yes` once civic government has been established. It removes the civic modifier, zeros derived values and clears pending scenes. It preserves historical completion and policy flags. It deliberately does not clear the shared diplomacy flag owned by the parent module.
- Availability requires BAR/original BAR, the active Collegium path without Directorate, the completed oath, independence, no capitulation, and ownership/control of state 624. The modifier also disables itself when these conditions fail. Daily maintenance handles suspension and return.

The balance pass also owns the existing Collegium effects, ideas, modifiers, decisions, EN/RU base localization and `tools/Test-BarradCollegium.ps1`. Project builders/generated content, shared core, GUI, frontier content and other countries remain integration-owner files. No new currencies or progress gates were added; failed project outcomes were not changed. Existing wartime allocation and its public mandate are constitutional choices, not the per-project civilian/field-use feature being removed separately.

## Focus Progression

IDs below follow `HSM_BAR_civic_`. Statistics are permanent contributions to the separate **Civil Government** dynamic national modifier, not one-off stability or political-power gifts.

| ID | Days | Result |
| --- | --- | --- |
| republic | 28 | Establishes the civil administration and opens the branch |
| municipalities | 28 | Scene 1: local or district representation |
| registry | 28 | Mobilisation speed +10% |
| courts | 35 | Scene 2: circuit courts or permanent bench |
| civil_service | 35 | Political-power gain +8% |
| accounts | 28 | Political-power gain +5% |
| cabinet | 35 | Political-power gain +5%; external assembly dependency |
| defence | 35 | Scene 3: civilian control with local reserves or central depots |
| procurement | 35 | Scene 4: open tenders or framework contracts |
| foreign_office | 28 | Relations-maintenance cost -10%; opens standard envoys |
| appeals | 28 | Resistance target -2%; stability +3% |
| local_works | 35 | Infrastructure construction speed +10% |
| inspectors | 28 | Political-power gain +5% |
| territorial_representation | 35 | Scene 5: local statutes or common civic franchise |
| equal_services | 35 | Compliance growth +0.02 |
| ordinary_state | 35 | Stability +5%; political-power gain +5% |

Resistance target is a fractional input, displayed as a percentage: `-0.02` means -2 percentage points, not `-2` (-200%). Compliance-growth inputs remain unchanged (`0.02`, `-0.02`, `0.04`); they were not multiplied alongside the other rewards. Civil government does not bypass the frontier module's separate territorial requirements.

## Lasting Settlements

Each settlement records `<focus>_settled` and exactly one policy flag, all prefixed `HSM_BAR_civic_`. It cannot be replayed or reversed by a delayed event. The available-condition descriptions are localized custom trigger tooltips.

| Scene | First policy | Alternative policy |
| --- | --- | --- |
| 1, municipalities | `local_mandates`: construction +5%, political-power gain -3% | `district_mandates`: political-power gain +5%, stability -2% |
| 2, courts | `circuit_courts`: resistance target -5%, political-power gain -2% | `permanent_bench`: stability +4%, compliance growth -0.02 |
| 3, defence | `local_reserve`: core defence +10%, training time +3% | `central_depots`: supply use -8%, army recovery +5%, political-power gain -3% |
| 4, procurement | `open_tenders`: construction +7%, production-efficiency growth -3% | `framework_orders`: factory output +8%, supply use -5%, production-efficiency cap -2% |
| 5, territorial representation | `local_statutes`: compliance growth +0.04, political-power gain -3% | `equal_franchise`: stability +3%, resistance target -3%, factory output -1% |

Across all 32 civic policy combinations: political-power gain +17% to +33%, stability +6% to +15%, general construction 0 to +12%, resistance target -10% to -2%, and raw compliance growth 0 to +0.06. Supply use bottoms at -13%, recovery peaks at +5%, factory output at +8%, and core defence at +10%. Infrastructure construction always adds +10% on top of general construction. All values are recomputed from flags, never accumulated on each pulse. Partial-path drawbacks can precede later compensating institutions.

Scenes are dispatched immediately after a guarded focus completion, not through delayed unguarded rewards. Every option revalidates current access, pending status and prior settlement. If access is lost, pending scenes are cleared; an unresolved scene can be reissued after access returns. This preserves a way forward without awarding a choice made while the government was unavailable.

## Collegium Services and Stack Budget

Programme costs, durations, one-time completion flags, equipment consumption and personnel refunds are unchanged. Permanent bonuses require the recorded funded completion; cancellation and stale callbacks still award nothing. Existing topic-specific research discounts also remain.

| Completed institution/programme | Public Services contribution |
| --- | --- |
| Independent archive / inspectors | +3% stability each |
| Ordinary clinic appointments OR long-term follow-up | +4% stability OR +2% research |
| School / research board / peer review | +3% / +2% / +3% research |
| Funded teaching cohort (15 PP, 35 days, 200 personnel temporarily assigned) | +3% research, existing one-use 50% electronics discount |
| Grid / civil power reserve | +5% civilian-factory construction each under civilian allocation |
| Household grid priority OR workshop hours | +5% civilian-factory construction OR +2% research |
| Funded workshops (20 PP, 35 days, 1 civilian factory, 25 support equipment) | +5% civilian-factory construction under civilian allocation |
| Funded drainage (30 PP, 42 days, 1 civilian factory, 100 personnel temporarily assigned) | +5% civilian-factory construction under civilian allocation |
| Funded medical rounds (15 PP, 35 days, 25 support equipment) | +5% recovery under wartime allocation, existing one-use 50% hospital discount |
| Funded reserve (15 PP, 35 days, 50 support equipment) | -5% supply consumption under wartime allocation |

Wartime allocation replaces all of this spirit's civilian construction with -8% supply use and +8% recovery before paid improvements. The existing -2% stability cost without a public mandate and the 21-day mandate hearings remain. Peace restores civilian allocation; there is no recurring fee.

Charters remain mutually exclusive: open college +5% research/+5% stability; parliamentary college +0.20 daily political power/+8% efficiency cap; tutelage +10% research/-0.15 daily political power. Flat daily PP is not the civic PP percentage modifier.

The 48 reachable charter/clinic/grid/funded/allocation fixtures establish these **per-stat ceilings, not one simultaneously attainable build**:

- Services alone: +15% research, +10% stability, +25% civilian-factory construction in civilian allocation; -13% supply/+13% recovery in wartime allocation.
- Services plus one charter: research at most +25%, stability at most +15%; other service ceilings unchanged.
- Adding civic government: civilian-factory construction at most +37%, infrastructure construction +22%, wartime supply -26%, recovery +18%, stability +30%, core defence +10%. Republic efficiency cap is +6% with framework orders, otherwise +8%.
- These are **owned-content contributions only**, excluding shared development, frontier, anomaly and all 26 project rewards handled by the integration owner. Research-maximising workshop priority sacrifices 5 points of civilian construction; clinic follow-up sacrifices 4 stability. Construction-maximising tenders cannot also supply framework-contract bonuses.

The research ceiling is deliberately tighter than construction: several contributions affect every research slot, while construction support affects only civilian factories and disappears during military allocation. This is a bounded balance proposal, not a claim of combat-tested final balance.

## Validation and Sources

Run `node tools/Test-BarradCivic.cjs --native`. `HOI4_GAME_ROOT` and `EAW_ROOT` override the installed-source locations. The suite reuses the existing lightweight Clausewitz parser and executes the actual new scripts in a strict bounded fixture. It covers all 32 complete policy combinations, missing prerequisites, route/capitulation/subject/home-state guards, delayed/repeated choices, suspension/recovery, modifier caches, repeated refreshes, localized visible conditions and EN/RU parity. This is not an HOI4 runtime or visual playtest.

The installed engine's `documentation/modifiers_documentation.md`, `triggers_documentation.md`, `effects_documentation.md`, `common/buildings/00_buildings.txt`, and installed graphical definitions ground the mechanics and asset references. EaW `localisation/russian/country_BAR_l_russian.yml:1898` has `BAR_gasienica:0 "Гасеница"`; line 2374 has `bar_cpt_gasienica:0 "Капитан Гасеница"`. Civic prose follows that spelling; English retains the established module spelling Gasienica. Any differing spelling in older College prose belongs to the integration pass, not a new canonical distinction.

### Resistance Unit Evidence and Compatibility

- Installed HOI4 `localisation/english/modifiers_l_english.yml:1347` renders `resistance_target_tt` with `$RIGHT|-=%1$`; `common/occupation_laws/occupation_laws.txt:200` uses `resistance_target = -0.15`.
- Installed EaW `common/occupation_laws/occupation_laws.txt:353` likewise uses `-0.15`. The engine documentation's generic "Number with 0 decimal places" entry alone did not establish the scale; these actual shipped sources do.
- `HSM_BAR_civic_effects.txt` now writes `-0.02`, `-0.05`, `-0.03`, replacing `-2`, `-5`, `-3`. EN/RU tooltips now include the percentage sign. Appeals plus circuit courts correctly yields -7%, with a full civic ceiling of -10% rather than -1000%.
- Existing saves rebuild from the same historical flags on the next civic daily refresh, replacing a cached `-7` with `-0.07`. No statuses, choices or project progress are reset. A dedicated test covers this repair and a second idempotent pulse.
- A repository scan of runtime common/events and Barrad tools/data found no other Barrad `resistance_target` writer or binding outside the civic files; no out-of-ownership unit correction is pending.

Balance-pass checks: `node tools/Test-BarradCivic.cjs --native`: **106 passed / 0 failed**; `pwsh -NoProfile -File tools/Test-BarradCollegium.ps1`: **7,319 assertions passed**; `node tools/Test-BarradNativeContracts.cjs`: **23 passed / 0 failed**. Both localizations retain BOM, exact-value tests and key parity. The Collegium test now resolves the actual installed EaW root (override with `-EaWRoot`). Full engine behaviour, save/load UI and combat balance still need an in-game playtest.

### Cross-module Integration

`Test-BarradModifierTooltips.cjs` was updated to the exact new school, clinic,
workshop and wartime values. Its 14 scenarios now pass, including preservation of
institutional bonuses through the shared core refresh and the absence of stale caches.
The earlier two failures were obsolete numerical expectations, retained in the
intermediate verification logs rather than hidden.

The 26-project catalogue separately contributes up to +18% research, +20% factory
output, +25% production-efficiency growth, +25% recovery and -10% supply consumption.
For example, the research ceiling across services, one charter and all projects is
+43%, excluding shared development and other EaW content. These maxima require the
actual completed project outcomes; failed projects contribute no permanent modifier.
