# Foreign Fieldwork Desk

Bounded human Service GUI for the existing reconnaissance, archive, relic and
remains operations. All new game files use `HSM_BAR_fielddesk*`. The only existing
game file changed by this slice is `common/operations/HSM_BAR_operations.txt`:
each operation's `visible` receives `is_ai = yes`. Requirements and native
completion callbacks remain intact, including already-running native operations.

## Integration

- Open: close `HSM_BAR_service_gui_open`, set `HSM_BAR_fielddesk_open = 1`, retain
  `HSM_BAR_service_gui_region`, then call `HSM_BAR_fielddesk_refresh = yes`.
- Regions: 1 local, 2 Equus, 3 Griffonia, 4 north, 5 Riverlands, 6 Zebrica.
- Back and Close clear the fielddesk variable, set `HSM_BAR_service_gui_open = 1`
  and call `HSM_BAR_service_gui_refresh = yes`.
- Integrated in `common/on_actions/HSM_BAR_core_on_actions.txt`: `on_daily_BAR`
  calls `HSM_BAR_fielddesk_pulse = yes`, guarded only by the country flag
  `HSM_BAR_fielddesk_initialized`. This is outside and before the `HSM_BAR_active`
  branch, so a closed menu or lost route cannot prevent cancellation.
- Integrated in `HSM_BAR_dissolve_institutions` in
  `common/scripted_effects/HSM_BAR_core_effects.txt`: the initialized-flag guard
  calls `HSM_BAR_fielddesk_teardown = yes` after MTC cleanup and before route
  flags are cleared. Refresh sets the flag; teardown clears it. Repeated teardown
  is harmless, and countries that never opened the desk do not enter its hooks.
- Main owns hiding the legacy human targeted decisions. No legacy decision,
  registry, case, research, archive, MTC or shared lifecycle file is edited here.
- `HSM_BAR_fielddesk_factories` and dynamic modifier `HSM_BAR_fielddesk_assignment`
  are a separate reservation. Do not add their value to the Service modifier too.

## Orders

| Assignment | PP paid | Days | Reserved civilian factories |
| --- | ---: | ---: | ---: |
| Reconnaissance | 20 | 14 | 1 |
| Archive retrieval | 30 | 21 | 2 |
| Relic retrieval | 60 | 30 | 3 |
| Remains recovery | 60 | 21 | 2 |

PP and durations retain the existing fallback expeditions. Factory counts match
the corresponding native operation, reserved for the full GUI assignment.
Successful relic/remains retrieval also retains the registry's 20 PP diplomatic
incident. Both costs are explicit in the UI. No agency, operative, equipment,
trust, capacity or DLC requirement is added. All four DLC combinations use the
same path. One assignment is active at a time.

The selected country and active assignment destination are separate persistent
country variables. Browsing, pagination, closing and reopening do not redirect
the order. Active missions have an invisible category and `visible = no`; their
timers, completion and cancellation are independent of GUI visibility. Paid
starts activate the missions directly. Cleanup uses native `remove_mission`,
which does not run completion/timeout callbacks. The dated running flag rejects
early stale timeout callbacks, and consuming it before registry completion
prevents duplicate rewards. Cancellation refunds only a running order's recorded
payment and removes only the fielddesk modifier.

## Scope Contract

Public `HSM_BAR_operation_*_target` predicates and `HSM_BAR_operation_*_complete`
effects remain authoritative. The desk does not duplicate the registry.

1. BAR dispatches a hidden recipient event on a candidate/selected/order country.
2. That event runs with the foreign country as ROOT and BAR as FROM. It sends an
   hidden country event with no requested delay back to BAR.
3. The BAR receiver now has ROOT = BAR and FROM = the foreign sender. Only there
   does the desk evaluate crown-sensitive predicates or call public completion.

No artificial assignment to ROOT/FROM or delayed completion event is used. Sender
and stored target must match. The relay is based on installed EaW
`events/Celestial_State.txt` (`daring_adventure.100 -> .101`, `.102 -> .103`) and
`events/ChangelingHarmony.txt` (`thoraxian.4 -> .5`). The latter receiver grants
access to FROM; the former reads the previous recipient's state variable via
FROM. Installed engine docs describe `activate_mission`, `remove_mission`,
variable targets, array operations and `days_mission_timeout@<mission>`.

These sources establish the recipient/sender scope pattern, not a documented
guarantee of synchronous execution. An event's `immediate` block describes its
effects on delivery; that name alone does not prove when delivery happens.
All relay calls omit delay parameters. Every BAR receiver assigns its check
region from current presentation state or the frozen request/order immediately
before evaluating predicates; nothing relies on a variable set in an earlier
callback surviving unchanged. The pending request lock, frozen target/region,
current eligibility checks and consumed completion flag also pass fixture tests
with queued FIFO and reversed delivery, including duplicate returns, target
loss, selection changes and teardown between the two relay hops. These are
adversarial fixture checks, not evidence of the live engine's scheduler.

The list contains existing, non-capitulated current custodians with a known
regional lead. Original country tags are not substituted for territorial
control. Crowns use their recorded physical site and continent (europe/asia/
africa in EaW), including a disappeared origin country. Local and Riverlands
have no invented foreign-target operation. Region filtering is presentation;
each registry operation still resolves every qualifying case at its country
target, exactly like the native operation. Launch region is frozen for later
eligibility checks.

Daily and final checks cancel lost mandate/route, capitulation, missing targets,
lost territory or invalidated leads. Worn crowns are never extractable. Remains
require the original forensic mandate, completed science, investigated Grover
case and confirmed recoverable bones; resurrection and living leaders exclude
them. No corpse or ruler transfer is invented.

## Verification

`node tools/Test-BarradFielddesk.cjs` runs source-driven fixtures against the
actual registry predicates and effects, native scope-bridge contracts, all four
DLC combinations, selection persistence, hidden-menu completion, fractional PP,
stale dispatch, cancellation/refund, duplicate/replayed callbacks, control/route
loss, crown origin/site changes, forensic exclusions, bilingual keys and native
bitmap-font/asset bounds. Source contracts verify both initialized-flag lifecycle
guards, daily placement outside the active branch, and teardown ordering after
MTC but before flag clearing. Unknown fixture predicates and effects fail closed.

`python tools/HSM_BAR_fielddesk_preview.py` renders six 1000x700 ready/running/
empty EN/RU fixtures under `art/previews/HSM_BAR_fielddesk_*.png`, reusing the
existing archive renderer, actual widget source, eligibility fixtures, textures
and bitmap fonts. The renderer uses `--preview-json` on the test file and does
not run its regression scenarios. No art is generated or changed.

This is not a live engine acceptance claim. Required in-game acceptance: open
from Service in EN/RU, page/select a real lead, dispatch and close, save/reload,
verify the displayed timer and factory reservation, complete each order with
ROOT/FROM logging, invalidate territory/route during an order, and confirm no
mission category or human native operation appears. Repeat with no DLC and both
DLCs. Daily and teardown hooks are integrated and covered by source contracts.
