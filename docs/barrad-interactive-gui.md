# Barrad Interactive Research

Integrated on 2026-10-10. The dedicated interfaces separate operational choices
from reading documents. No trust, secrecy, institutional-capacity or replacement
currency was added. Existing artwork, historical findings and fixed failed
experiments are retained.

## Service

The politics-panel launcher opens a six-region console: Barrad, Equus,
Griffonia, the North, Riverlands and Zebrica. Operational region tabs require
their established branch. Only authored, currently visible work and running
assignments populate the case list; this is not a list of every country.

The console lists 124 existing action contracts, including 73 legacy timers. Costs,
story requirements, cooldowns and completion effects come from the existing
definitions. These remain the AI's original decision route. Human Service
duplicates are hidden, including the case-study/institute project interface;
the dedicated research actions work with or without Gotterdammerung. The
existing facility requirement still applies when that DLC is enabled.

Seven local inquiries now open [authored investigations](barrad-investigations.md)
instead of launching the legacy timer. Two documents, six selectable excerpts,
an evidence-based hypothesis and three expedition protocols replace the direct
start for rock, Titan, entity, amulet, vegetation, echo and compass. Their new
protocol costs/durations are explicit; old in-flight GUI timers may still finish.
The original simple inquiry remains for AI, not a human shortcut.

Assignments show cost, duration and remaining time. Closing the menu does not
cancel work. Duplicate starts are rejected; completion rechecks access. Explicit
recall pays no reward or refund. Reservations in Unseen Service count only active
assignments and are immediately released at completion/cancellation. A separate
active-work view includes jobs outside the currently selected region.

The regional archive is read-only: editions, photos, audio and recorded outcomes
remain available independently of current physical access. Opening a dossier
does not authorize an expedition. Invalid deep links reset to a regional index,
not an unknown object's report. Regional cross-references do not create relics.

[Foreign assignments](HSM_BAR_fielddesk.md) use a separate target-selection page.
The destination is frozen when ordered; actual registry predicates govern
reconnaissance, archive retrieval, relic retrieval and remains recovery.
No intelligence-agency screen or La Resistance is needed for these assignments.
The existing agency remains useful for ordinary espionage and institutional
bonuses. Native anomaly operations remain defined for AI and old callbacks, but
are hidden from the human player. Fielddesk cancellation follows its explicit
recorded-payment refund rule, unlike local research cancellation.

## Collegium

The four faculty journals separate narrative documents from a laboratory view.
All 26 projects now have apparatus and control-procedure choices, four possible
first observations, and two follow-up procedures whose timing, cost and reports
depend on that preparation. Civilian/departmental application selectors are
removed. Numerical rewards and budgets occupy a separate calculator/ledger view.
Two joint projects are included: Borrowed Touch and An End Written In.
Both appear in their participating journals, but share one dossier, payment and
result. They require specific completed studies and occupy both faculties,
including while an observation awaits the player's follow-up order. The first
series no longer completes a human-launched project automatically. No extra
resource, progress meter or outcome reroll has been added.

Each Magnum Opus has an Origins view of its five actual preparation conclusions.
Unfinished conclusions remain unavailable. Joint projects never replace these
prerequisites. The instrumented howitzer trial has a distinct report but remains
a failure. See [costs, results and cancellation](barrad-collegium-projects.md).

## Boundaries

Focuses still establish institutions, regional mandates and political direction.
Civilian government, general development and diplomatic policy retain their
existing focus/decision interfaces. The initial Republic investigations also
remain decisions until the Service exists. This pass moves specialist casework
and faculty project control, not every state action, into GUI.

Free-form evidence linking, a construction-style containment editor and a map
with draggable objects are not implemented. The current system uses authored
choices, existing case predicates, native scripted GUI and native mission timers.

New-campaign acceptance is required. This is not a migration of running legacy
decisions or institute projects: their old timers do not have the new GUI payment
snapshots. Do not start a duplicate assignment in an old test save. Completed
case flags and documents have not been reset.

## Verification

Windows tools: PowerShell 7.6.5, Node 24.19.0; Python/Pillow for bitmap fixtures.
Exact regression commands, exit codes and complete logs are in
`dist/barrad-gui-20261010/results.json` and that directory's individual logs.
The final run passed all **37 commands: 33 suites and four builder checks**.
Dedicated coverage passed 142 Service scenarios, 18 Fielddesk groups, 23 archive
region groups, 1566 Collegium project scenarios and 70 Collegium menu groups.
Initial integration failures were an AI-only operation predicate missing from
the old fixture and a missing icon on the temporary Fielddesk factory modifier;
both are fixed, with the existing approved icon reused. Earlier narrow checks
also corrected the new reservation binding and preserved MTC-first teardown.
The dedicated checks are:

```powershell
node tools/Build-BarradServiceGui.cjs --check
node tools/Test-BarradServiceGui.cjs
node tools/Test-BarradFielddesk.cjs
node tools/Test-BarradCollegiumProjects.cjs --native
node tools/Test-BarradCollegiumMenu.cjs
node tools/Test-BarradArchive.cjs
node tools/Test-BarradArchiveRegions.cjs
```

`Preview-BarradServiceGui.py`, `HSM_BAR_fielddesk_preview.py`,
`Preview-BarradArchive.py` and `Preview-BarradCollegium.py` render source-driven
fixtures with the actual textures and bitmap fonts. They are not HOI4 captures.

Required live acceptance: new Barrad campaign in EN/RU, both routes, every region,
opening/closing and scrolling, paid start/cancel/return, save/reload during a job,
simultaneous factory reservations, loss of access, and joint-faculty locking.
Check all DLC combinations. Native GUI hit-testing, timer ordering and event
relay scopes have not been verified in a running game.
