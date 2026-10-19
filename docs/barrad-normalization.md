# Global Normalization Crisis

Additive module; the local 30-day trial and its refusal/continuation remain in
core. This crisis is author fiction, not established EaW history.

## Integration Contract

- Core continuation sets country flag `HSM_BAR_global_authorized`; refusal must
  clear it. This module never grants that authorization or research completion.
- Requires active independent BAR, a founded Service + normalization, no coexistence,
  `HSM_BAR_project_suppression_done` and `HSM_BAR_suppression_knowledge_ready`.
- Five `HSM_BAR_normalization_grid_<region>` decisions (equus, griffonia, north,
  riverlands, zebrica): 50 PP and 35 days each, independently available once that
  regional office is open. Completion sets `HSM_BAR_norm_grid_<region>_done`.
  Interrupted work does not grant readiness and can be restarted.
- `HSM_BAR_global_network_ready` additionally requires all five regional flags,
  all five calibrations and control of state 624.
- `HSM_BAR_normalization_activate`: 100 PP, 14 days; calls
  `HSM_BAR_begin_global_normalization` after validating its in-progress flag.
  Do not call this effect from the local focus or skip the timed decision.
- Ending focuses may test GLOBAL `HSM_BAR_world_barriers_restored` or
  `HSM_BAR_world_normalization_victory`.

## Persistent World Sequence

Day 0: global equipment weakening and a small initial BAR stability gain.
Day 21: failures of the old barriers. Day 42: a real invasion, with one initial
foothold selected from states **625, 102, 558**, in that order. No capital,
occupied state, subject's land or last fully controlled owned state is seized. Original
cores are retained; NML receives a core and capital in the selected state.
If all three sites are unsafe, the same finite list is retried; no substitute
country or invented victory is selected.

NML declares **one scripted war**, against the current owner saved before the
transfer. Standard alliances can still involve other countries. Waves remain
bounded at **4 + 2 + 2 divisions**, or **6 + 3 + 3** when that original owner has
at least 40 divisions. The size tier is fixed before transfer and never grows
with later recruitment. Reinforcements are due 28 and 56 days after the breach,
only at its original controlled aperture.

The 2026-10-08 readiness pass replaces the single six-infantry template with
three locked native templates. Their names are authored military report labels,
not established EaW names, species or explanations of the intruders.

| Template | Native composition | Numbered unit label |
| --- | --- | --- |
| The First Footfalls | 6 infantry, reconnaissance support | Forward Contact |
| The Hollow Line | 8 infantry, engineer support | Holding Contact |
| The Weight Behind | 6 infantry, 1 line artillery, engineer and artillery support | Siege Contact |

| Arrival | Standard breach | Large breach |
| --- | --- | --- |
| Initial | 3 forward, 1 holding | 4 forward, 2 holding |
| Day 28 | 1 holding, 1 siege | 2 holding, 1 siege |
| Day 56, NML controls only its aperture | 2 holding | 3 holding |
| Day 56, NML controls at least two states | 2 siege | 3 siege |

The last two rows are alternatives, selected at the final deadline. Earlier
expansion that has already been reversed does not qualify. Lost full control
of the original aperture sets permanent global flag
`HSM_BAR_world_aperture_closed` on the next daily tick, **before** either wave
check. Even partial enemy occupation closes it. Retaking the aperture later
does not reopen it. This stops future arrivals without awarding victory or
removing existing forces; destruction of the invading army remains necessary.
Loss and recapture entirely between daily ticks cannot be observed by this
polling mechanism. Restoration and actual defeat independently block waves.

There is no relocation, repeated wave, scripted unlimited reserve or
resurrection. Initialization grants 100,000 manpower, 14,000 infantry equipment,
480 artillery and 600 support equipment once. The manpower grant was raised
from 90,000 to cover the largest new formation mix; installed unit requirements
and enabled stockpile models are checked by the suite. Later waves never
replenish these reserves. **8/12 is a scripted spawn cap, not an engine-wide
army cap:** native AI can train troops and use captured industry. Locked
templates prevent redesign; they do not prove a recruitment limit. Native AI
and combat balance still require a campaign test.

All phase clocks/guards are global, driven by the country daily on-action, not
BAR-targeted pending events. BAR's annexation or institutional dissolution does
not erase the catastrophe. If BAR can no longer operate the system, a non-invader
controller of state 624 can decide its fate.
After actual neutralization, daily/release reconciliation also removes NML's
`HSM_BAR_normalization_beyond` spirit, including stale copies on dormant tags.
Restoration alone retains that spirit while the invasion is still fighting.

## Endings And Equipment Scope

- Restore barriers: 100 PP, 35 days. Sets `HSM_BAR_world_barriers_restored`,
  removes weakening globally and stops further scripted waves. Existing armies,
  occupied territory and wars **remain**.
- Press normalization: 150 PP, 28 days. Keeps weakening; grants the temporary,
  costly conventional `HSM_BAR_normalization_steel_defence` programme.
  `HSM_BAR_world_normalization_victory` requires an actual prior incursion and
  its neutralization (capitulation, annexation, loss of all controlled land or
  subjugation), not just decision completion.
- Other defenders can buy the same conventional programme for 50 PP / 21 days.
  Its +10% conventional equipment bonuses cost 8% military output and 0.15 daily
  PP; they expire when the invasion is defeated. The endings are exclusive.

**Implemented weakening:** only EaW's `magical_equipment`,
`magical_artillery_equipment` and `magical_tank_equipment` archetypes, using
native idea `equipment_bonus` with `instant = yes`. No exception for BAR.
Released countries are reconciled by release hooks and daily checks; stale
penalties on dormant tags are removed when those tags return after restoration.

**Not implemented:** per-magical-component penalties on ordinary aircraft,
ships or tank chassis. The installed native API/examples and local `EaW/`
snapshot were inspected again before this pass. No verified mechanism for a
runtime, reversible, conditional per-module combat modifier was found. This is
a hard limit of the supported implementation, not proof that no undocumented
engine mechanism could exist. No module overrides or blanket air/naval/armour
penalties were added. Both languages' activation/idea tooltips retain this limit.

Concrete evidence in the installed sources:

| Source | Finding |
| --- | --- |
| HOI4 `documentation/modifiers_documentation.md`, `module_<EquipmentModule>_design_cost_factor` | Documents module design cost, not a module's runtime combat performance. |
| HOI4 `common/units/equipment/_documentation.md` | Module slots, defaults and count constraints describe equipment designs; they do not document a country/global-condition combat-stat hook. |
| EaW `common/units/equipment/modules/00_tank_modules.txt`, `tank_magic_auto_cannon` | Static numeric `add_stats` for a module on ordinary chassis. |
| EaW `common/units/equipment/modules/00_plane_modules.txt`, `plane_crystal_projectile_module` | Static module/mission stats; mission lists do not establish arbitrary global-flag conditions. |
| EaW `common/units/equipment/modules/00_ship_modules.txt`, `ship_light_crystal_projectile_module` | Static `add_stats`, `multiply_stats` and `add_average_stats`. |

Searches of the installed HOI4/EaW and snapshot module definitions found no
conditional combat-bonus precedent. Treating those module IDs as archetypes in
`equipment_bonus`, or treating design-cost changes as combat penalties, would
not meet the verification requirement. A future implementation must first
demonstrate that an ordinary design with a magical module changes on activation
and reverts on restoration, while a comparable nonmagical design is unaffected.

## Native References And Presentation

- HOI4 `documentation/effects_documentation.md`: `create_unit` (including
  `count`), `transfer_state`, `load_oob`, `division_template`,
  `save_global_event_target_as`, `create_country_leader`.
- HOI4 `documentation/triggers_documentation.md`: timed `has_global_flag`,
  `is_capital`, `num_of_controlled_states`, `has_full_control_of_state`.
- EaW `common/decisions/KIR_decisions.txt`: `can_puppet = no`;
  `common/on_actions/eaw_diplo_popup_on_actions.txt`: country `on_daily`.
- EaW `common/units/equipment/magical_eq.txt`: the three distinct archetypes;
  `common/ideas/zzz_SOL_ideas.txt`: instant equipment bonuses.
- EaW `history/units/DED_1007.txt`, `BAR_1007.txt`: OOB, mixed line/support
  artillery and locked-template precedents. `common/technologies/infantry.txt`,
  `artillery.txt`, `support.txt`: enabled weapons, engineers and reconnaissance.
  The chosen support unlocks are unconditional and do not require the new HQ DLC.
- EaW `history/units/WIT_1007.txt` and
  `common/units/names_divisions/WIT_names_divisions.txt`: native
  `division_names_group`, country restriction and numbered `fallback_name`.
- NML uses byte-identical copies of HOI4's generic `REB.tga` at all three flag
  sizes as a provisional hostile-contact marker, not invented heraldry.
  Its explicit portrait reuses EaW `gfx/leaders/leader_unknown.dds`; all three
  templates retain counter 1. Native template/group names are literal English
  strings, following the installed OOB convention. EN/RU crisis text explains
  the authored classifications, escalation and containment, and all country,
  leader and event localization remains present.
- Art handoff: **no new idea IDs** and no picture/icon/flag edits in this pass.
  Parent retains art ownership for `HSM_BAR_normalization_magic_failure`,
  `HSM_BAR_normalization_steel_defence`, `HSM_BAR_normalization_beyond`.

## Verification

`node tools/Test-BarradNormalization.cjs`: **57 passed, 0 failed**.
The same 57 checks also pass with `EAW_PATH` pointing to the local `EaW/`
snapshot instead of the installed workshop copy.
The suite interprets the actual new scripts, checks missing research/regions,
stale/cancelled decisions, annexation, safe fallback sites, finite waves, both
endings, release cleanup, localizations and installed native syntax/assets.
It fails on unknown interpreted syntax. Set `HOI4_PATH` / `EAW_PATH` if needed.
The new scenarios cover the 39/40 threshold, all three fallback owners,
expansion/lost expansion, partial occupation, capture on either wave deadline
under both country tick orders, permanent closure after recapture, all four
neutralization routes, reserve idempotence, native technology/equipment unlocks
and supply requirements for both maximum-size final-wave alternatives.

Adjacent checks: `node tools/Test-BarradNativeContracts.cjs` **23 passed**;
`node tools/Test-BarradPhases.cjs` **53 passed**, both with zero failures.

These are static/script-level tests, **not an HOI4 playtest**. Native combat,
country spawning/rendering, AI behaviour and immediate equipment recalculation
must be verified in a fresh campaign. This pass changes template names; it does
not migrate an already-spawned NML army in an older save. No existing
core/focus/research/project/service files were edited by this pass.

Fresh-campaign acceptance checks still outstanding:

1. Inspect the three NML templates and numbered formation names after spawn;
   confirm all units arrive equipped and native AI actually uses their roles.
2. Compare contained and expanded fronts at day 56; retake or contest the
   original aperture before a deadline and confirm reinforcement stops.
3. Complete restoration after day 28: the first reinforcement survives, the
   day-56 wave is blocked, and units, wars and territory remain.
4. Exercise BAR dissolution/annexation, control-of-624 succession, NML
   capitulation/annexation/subjugation and later releases; check spirit cleanup.
5. Compare magical-archetype combat stats before activation and after
   restoration, including existing equipment and newly released countries.
   Ordinary chassis with magical modules remain an explicitly unsupported case.
6. Save/reload across the wave deadlines and closure flag; inspect a fresh
   `error.log`. This pass does not claim an engine run or a clean runtime log.
