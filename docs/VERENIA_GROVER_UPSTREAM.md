# Restored GRI: integration contract and native lifecycle audit

Audit date: 2026-10-24. Sources are the installed EaW at
`C:/shit/Steam/steamapps/workshop/content/394360/1826643372` and game at
`C:/shit/Steam/steamapps/common/Hearts of Iron IV`. Line numbers below refer to
the installed EaW files, not prospective submod overrides. No installed files
were edited and no game was launched.

## Parent integration: priority findings

The restored focus tree alone does not stop already queued events or native
decisions. The parent must guard these entry points in its native overrides:

| Native entry point | Exact collision | Smallest applicable guard |
| --- | --- | --- |
| `events/GriffonianEmpire Events.txt:138`, `imperial.3` | No event trigger. Promotes `GRI_regency_council`, adds the child idea, sets the old emperor's death flags, completes `GRI_emperor_passed`, and broadcasts the original succession. A delivered old event would overwrite the adult settlement. | Exclude ROOT with `HSM_VER_GRO_restored` in its event trigger and recheck around mutating option effects. |
| Same file:20,65,94,116, events `imperial.1`, `.2`, `.30`, `.300` | `.1 -> .2 -> .3` is the startup chain. Polling `.30` can independently start `.3` after 1007.3.15 when the global old-emperor death flag is absent; `.300` starts the April Fools succession. Neither polling event checks the restored marker. | Add the ROOT exclusion to all four entry triggers; retain their native conditions. Do not clear `GRI_emperor_dead` to simulate a new reign. |
| Same file:1093, `imperial.44` | Polls after 1021.5.21 with `tag = GRI`, completed `GRI_eros` or `GRI_eagleclaw`, and control of **389**. Has no custody/child-idea check. Rewrites Grover's portraits and adds/promotes despotist and fascist roles; the Duchess option also queues `grover.15`. | Exclude restored ROOT in trigger and option effects. Clearing old focus history is useful but should not be the sole protection. |
| Same file:3737, `imperial.123` | Polls for original GRI, adult Grover as ruler, peace, completed `GRI_core_south` and `GRI_core_frontier`, and NOT `imperial_grover_focus`. The new tree satisfies that last condition. Applies -40% stability, -40% war support, -100 PP and loads `imperial_grover_focus`. | Explicit restored ROOT exclusion in trigger and option. Parent must load `HSM_VER_GRO_restored_empire` once with `keep_completed = no`. |
| Same file:2010,2082,2135,2164, `imperial.73` through `.76` | `GRI_industry_modern` queues `.73` in its **select_effect** (`common/national_focus/GRI.txt:106`). Delayed chain promotes Dawnclaw, retires original Grover, sets `GRI_grover_vi_dead`, breaks vassal relations and loads `imperial_army_focus`. These events have no restored/custody guard. | Exclude restored ROOT at each delivered event and each mutating option; guarding only the initial caller does not protect a pre-existing queue. |
| `events/Grover_Events.txt:5,158,344`, `grover.1` through `.14`, `.17` | Duchess and Archon childhood chains are triggered-only, with no event triggers, dates, character ownership or child-idea checks. Delays are 729/730 days; `.2` and `.9` also schedule `.17`, which removes manpower and stability. Loading a new tree does not itself provide a guard on these event definitions. | Add a restored ROOT exclusion to the childhood events. For custody correctness also require `has_character = GRI_emperor_grover_vi`, the child idea and a pre-majority date at delivery, using the parent's agreed age boundary. Recheck scheduling effects in options. |
| Same file:588,732, `grover.32`, `.40` | Sets **global** `GRI_grover_vi_dead`, then searches `every_possible_country` for Grover and retires him wherever found. These are ANG/PYT events, so a guard only on event ROOT's restored flag is ineffective. | Guard the whole event/effect against protected restored GRI holding the original character; do not just filter the character loop, since the global death flag would still be set. |
| Same file:644,756, `grover.35`, `.41` | Adds `GRI_grover_vi` to the recipient, then globally finds the character and changes nationality to ROOT. This can take the adult out of restored GRI and reintroduce a child spirit elsewhere. | Use the same protected-holder exclusion on the entire event/effect. Do not recreate Grover to repair a stolen original. |
| `common/decisions/GRI_decisions.txt:132`, `GRI_demand_land`; `events/GriffonianEmpire Events.txt:1876,1950,1977`, `imperial.70` through `.72` | The decision expressly targets **allies/subjects**, gated by completed `GRI_empire_rising`. It can demand any retained Vereni state with a GRI/other native Herzland core. `.70` accepts/refuses; `.71` transfers states, `.72` ejects the target from its faction, removes a NAP, creates an annexation goal and adds conquest AI. Being coalition allies does not prevent this chain. | Exclude restored GRI in the decision's `visible` and `target_root_trigger`, and recheck its `complete_effect`. At `.70`, guard the **FROM requester**; at `.71/.72`, guard **ROOT requester**. Revalidate option effects for an already-open demand. |

Country-local exclusion (merge into an existing trigger/limit, do not replace it):

```hoi4
NOT = { has_country_flag = HSM_VER_GRO_restored }
```

Cross-country custody exclusion for `grover.32/.35/.40/.41`:

```hoi4
NOT = {
    GRI = {
        has_country_flag = HSM_VER_GRO_restored
        has_character = GRI_emperor_grover_vi
    }
}
```

The parent may extend that protected-holder predicate to its ERI/EYR custody
phase. The specific predicate above protects the adult restored holder. Event
triggers prevent new delivery; option-effect guards additionally cover an
event window already open when restoration occurs. Preserve legitimate native
outcomes when Grover is not in protected custody. Do not use a new global death
flag or falsely set the existing death flag as a shortcut.

## Other inspected native interactions

- `common/on_actions/eaw_GRI_on_actions.txt:2`: startup saves
  `griffonian_empire` and `global.griffonian_empire_var`, queues `imperial.1`
  after 6 days plus random hours, and `.60` after 186 days plus random hours.
  `.60` is a writer flavour event, not regency. There is no native daily GRI age
  scheduler in this file. Adding a restored exclusion around startup scheduling
  is useful defence, but cannot cancel an already-delivered event chain.
- The same on-action file's `on_subject_free:19`, `on_annex:28` and
  `on_release_as_puppet:50` concern cosmetics and the global empire target.
  Annexing **GRD** reassigns the target to GRI. None directly reinstalls the
  regency. Do not replace the entire on-action file merely to stop age events.
- `common/on_actions/eaw_on_daily_on_actions.txt:141`: the empire target is
  repaired only when missing or its current country does not exist. A living
  former claimant can therefore keep the target. The parent's explicit target
  and variable assignment to restored GRI is necessary and already present in
  the restoration effect inspected during this audit.
- `common/on_actions/eaw_statefall_on_actions.txt:535` is Griffenheim fall
  news; it does not start Grover's regency. Native `389` conditions in
  `imperial.44` and BRZ's coronation are literal Griffonstone checks, despite
  the misleading Griffenheim comment in the BRZ hook. The restored factory
  preference uses actual Griffenheim state **382**.
- `common/on_actions/eaw_BRZ_on_actions.txt:114` onward uses `BRZ_grover_vi`
  for age scenes; at 689 the coronation also requires BRZ to hold the original
  character and state 389. Transfer out of BRZ prevents a new BRZ coronation,
  but the earlier age branches do not require character ownership: an orphaned
  `BRZ_grover_vi` idea can still produce childhood scenes there. If BRZ was an
  earlier custodian, remove that stale custodial idea or guard its scheduler
  against the protected holder. Previously queued foreign custody scenes are
  a distinct issue, not fixed by the restored tree.
- `grover.42` (`Grover_Events.txt:780`) polls only for ANG, fascist government,
  states 382 and 389, and the fake-Grover idea or the original character plus
  child idea. It cannot directly run in restored GRI. The fake character branch
  is unrelated; the true-character branch becomes relevant if `.35` steals him.
- Callers of global destructive/custody scenes are in
  `common/decisions/griffon_decisions.txt:1597,1624,2348,2360`; PYT can also
  queue `.41` from `events/Greifenmarschen Events.txt:1346` (`marschen.26`).
  Guarding only a formable decision misses the latter and existing queues.
- `imperial.137` (`GriffonianEmpire Events.txt:4174`) requires adult ruling
  Grover and `GRI_chose_eros`; it retires Eros and sets his death flag. It does
  not overwrite Grover or his tree. A restored exclusion is optional narrative
  hygiene if retaining old GRI flags; it is not the critical regency guard.
- Original Grover in `common/characters/GRI.txt:1312` is a single character
  token with a child portrait and no inherent country-leader role. The parent's
  original-token transfer, adult portrait and constitutional role are required;
  the restored follow-up never recruits, generates, retires or transfers him.

## Reclamation and decision boundaries

`common/national_focus/GRI.txt:2804` (`GRI_strike_lakes`) explicitly creates
annexation goals against **both ERI and EYR**, plus other regional states. It
does not protect a coalition partner in its reward. The restored tree imports
none of the native shared focuses. Keep it loaded and guard `.76/.123`, which
can replace it. Tree selection weight alone cannot defeat an explicit native
`load_focus_tree` effect.

`keep_completed = no` removes the intended old-focus prerequisites, but does
not by itself establish that old flags, claims, wargoals, timed decisions or
event queues have been cleared. The parent should clear outstanding reclamation
wargoals/claims against its recognised partner in the restoration transaction.
The follow-up does not change borders or alliances to compensate for them.

Also inspect retained `griffon_can_demand_east_frontier` and
`GRI_empire_rising_flag`: `GRI_demand_frontier` / `GRI_offer_peace`
(`GRI_decisions.txt:1768,1859`) and the mandate-release decisions use flags,
not merely the active tree. The frontier demand normally excludes griffon
countries, so ERI/EYR are not its ordinary targets. Mandate access nevertheless
accepts original GRI unconditionally in
`common/scripted_triggers/EAW_GRI_scripted_triggers.txt:1`. A restored-country
exclusion in the mandate access predicate is the smallest way to prevent
irrelevant foreign mandates; do not erase a shared global empire flag that
other countries still need. The new follow-up offers no foreign mandates.

The generic `form_griffon_empire` decision already excludes original GRI in
`allowed`. `reclaim_eastern_peripherie` at
`common/decisions/griffon_decisions.txt:5184` is limited to JFT/JEB/JRR/VIN,
so it is **not** an original-GRI entry point despite naming ERI as a target.
`common/ai_strategy/GRI.txt:1` lists native Herzland vassals/dynamic tags, not
ERI/EYR, and excludes existing GRI faction partners; this is not a reason to
add new forced diplomatic actions to the restored content.

This is a bounded audit of the requested Grover file, GRI early events, relevant
on-actions and immediate callers. Other countries' formation events also have
global original-character scans (for example in Yale, Aquileia and Bronzehill).
They warrant a separate broader custody audit if the parent promises protection
against every foreign formation route. No such global guarantee is asserted by
this subtask, and no native override was edited here.

## Follow-up contract

- Entry: parent sets `HSM_VER_GRO_restored` on GRI before transferring states,
  moves the original Grover, installs the adult constitutional monarch, copies
  memories and explicitly loads `HSM_VER_GRO_restored_empire` once with
  `keep_completed = no`. ERI/EYR remains the host's country.
- Ten ordinary, nonrepeatable focuses; no native shared-focus imports, age
  scheduler, generated counters, territorial claims, wargoals or forced
  diplomacy. The diplomatic focus checks `HSM_VER_GRO_partner_ERI/EYR`, a
  living partner and peace, so a faction leader's later decision does not
  automatically force anyone back into a faction.
- Factory rewards choose owned, fully controlled 382 with capacity, then an
  owned/controlled capital with capacity, then another owned/controlled state
  with capacity. They grant one extra shared slot and one completed factory.
  If no location qualifies, research replaces construction. All choices are
  evaluated at focus completion; no delayed building job can reward a captor.
- Research university adds one slot only below five and always grants research
  bonuses. The homeland defence and industry branches remain usable when the
  diplomatic partner disappears; no final focus requires the embassy branch.
- Scenes `hsm_ver_grover_restored.1` through `.4` are focus-triggered and
  fire-only-once, with restored-country, independence, leader and completed-focus
  guards. Descriptions read copied education, law, route and service memories.
  The oath and charter choices revise the parent's existing court/law legacy
  ideas on GRI only; they do not rewrite the host's history or political setup.
- Oath options select `HSM_VER_GRO_open_court_legacy` or
  `HSM_VER_GRO_managed_court_legacy`. Charter options select
  `HSM_VER_GRO_rule_of_law` or `HSM_VER_GRO_patrons_legacy`. Each removes the
  opposite idea, retains the historical memory flags and rechecks restored GRI,
  independence and Grover's rule when clicked. These are the sole lasting
  choice rewards from the focus-triggered scenes; there are no resource payouts.
- Two new ideas, `HSM_VER_GRO_restored_public_service` and
  `HSM_VER_GRO_restored_civic_settlement`, belong to the courts and final
  settlement focuses. They affect domestic construction/repair and industrial
  efficiency/research respectively. They do not duplicate the parent's eight
  idea IDs. No one-off PP or stability rewards remain in the restored content.
- Factory branch conditions, random-state filters and the research-slot cap
  use `hidden_trigger`; ordinary rewards remain native, visible effects. The
  rare arsenal placement outside Griffenheim/the capital has one compact,
  fully quantified result summary to avoid duplicating the full construction
  tooltip. Government/partner requirements also use short named tooltips.

## Verification

Integration note (2026-10-24): the native guards identified above are implemented
by `tools/Build-VereniaGroverGuards.py`. The maintained overrides protect 15
imperial events, 19 childhood/custody events, three imperial decisions and the
Reichsmandate-access trigger, including already-open option effects. The guards
also protect a recovered household before the mandate is accepted. They preserve
the previous CYA changes; see `VERENIA_GROVER_TESTS.md` for AST comparisons and
110 protected event/household cases. This is bounded protection of the audited
chains, not a claim to cover every foreign event that mentions Grover.

Passed using the bundled Python runtime with `-B -X utf8`:

- Seven existing `tools/Test-Verenia.py` integration checks, with
  `package_files` scoped in memory to the three new script files: engine-keyword
  rejection, parse, event-call resolution, scripted-call resolution, installed
  sprite existence, research-category existence and whitespace/conflict checks.
- The existing installed-modifier-documentation check, including the engine's
  generated building modifier names, passes for the current HSM idea files.
- A parser-based check of the ten-focus acyclic graph, unique coordinates,
  exact country selector, absence of native shared focuses, hidden reward
  limits, idea references and forbidden character/territory/diplomacy mutations.
- Both localisation files are UTF-8 BOM, have 52 matching nonempty keys, cover
  every script reference and do not collide with current workspace localisation.
  New focus/tree/event IDs also do not collide with workspace definitions.
- Eighteen factory fixtures execute the production AST using the existing
  `tools/Test-VereniaDevelopment.py` interpreter, extended in memory for fixed
  state/capital scopes: preferred site, foreign/occupied preferred state,
  foreign/occupied capital, capacity fallback, all-full, foreign-only and mixed
  control cases for each factory type. Only the selected owned/controlled state
  changes; otherwise exactly the documented research fallback is awarded.
- Three research-slot cap fixtures; six ERI/EYR partner-existence/war cases;
  four invalid-government cases; all ten focuses completed in prerequisite
  order with a second completion rejected by the harness.
- Eight inherited-idea/choice combinations, repeated-selection idempotence,
  32 stale-option cases and 20 narrative-variant checks. Every constitutional
  choice leaves exactly one idea from its pair; invalid governments receive no
  changes, and every scene selects exactly one description.

No test files were added outside the assigned scope. The fixture adapters only
extend the existing parsers/interpreter for this bounded check; they do not
model the engine's event UI or scheduling internals.
Engine event-queue persistence and rendered tooltips remain unverified without
launching HOI4; no runtime results are claimed.
