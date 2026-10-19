# Collegium Research Journals

The journal owns the 24 faculty projects and two optional joint dossiers. Native
missions supply hidden timers; all player actions are in the journal. No additional
currency is introduced. Documents describe authored research, not established EaW lore.

## Current Research Contract

The 2026-10-10 playtest revision removes civilian/field applications entirely.
A completed project has one authored result and no daily PP upkeep. Old application
flags no longer change costs or modifiers. Failed experiments still give no permanent
bonus, but their signed conclusions remain required knowledge for the faculty's opus.

**Laboratory** is the operational view; the four document tabs remain read-only.
The faculty must be idle and its head alive and present to change the preparation.
A paid trial freezes the apparatus, control procedure and workshop schedule.

## Interactive Experiments

All 26 projects have their own bilingual experiment script in
`tools/data/barrad-collegium-experiments.json`. Each offers two apparatus choices and
two control procedures. The four combinations produce different first observations.
After the first series the player chooses one of two follow-up procedures; each has
its own duration, PP cost and signed report for the selected preparation. There is no
new currency, success meter or random reroll. Conclusions and permanent rewards retain
their authored limits: no protocol makes the Revolver Howitzer viable.

The GUI flow is theory -> preparation -> paid first series -> observation checkpoint
-> paid verification -> signed result. First-series completion does not grant the
result. At the checkpoint the faculty and workshops remain reserved until a response
is chosen or the experiment is cancelled. The two choices quote their actual costs
and duration in tooltips. Closing the window never cancels a running series.

The preparation is saved as flags, then copied into paid-contract flags on launch.
Follow-up callbacks validate the response, preparation, access and elapsed time.
Duplicate callbacks cannot pay rewards twice or finish a newly restarted experiment.
Cancellation removes every associated timer, frees the faculty/workshops and retains
only already-signed research. A joint experiment holds both faculties throughout.

Narrative documents no longer carry an inline modifier box. A calculator icon beside
the status opens a separate **Technical Summary** with the completed contribution and
budget. Unknown results remain undisclosed. No civilian/departmental application
selector or upkeep charge has been reintroduced.

## Workshop Contract

| Stage | Preparatory or joint project | Magnum Opus |
| --- | --- | --- |
| Theory | One civilian factory | Two civilian factories |
| Sequential trials | One civilian factory | Two civilian factories |
| Instrumented trials | Two factories; +15 PP; seven fewer trial days | Three factories; +35 PP; 21 fewer trial days |

Factories are reserved only while work is active, not consumed. Completion or
cancellation releases them immediately. A joint stage occupies both participating
faculties but pays one invoice and reserves one shared set of workshops. Losing
homeland access or a participating head cancels unfinished work. A clinical moratorium
blocks new Silver Star trials without interrupting admitted care.

Every new ordinary stage is 14 days longer and costs 10 PP more than before this
revision; every new opus stage is 28 days longer and costs 20 PP more.
The explicit project catalog is `tools/data/barrad-collegium-projects.json`.
The journal quotes the actual PP, duration and factory requirement before a paid start.
Cancellation gives no refund; starting again creates a new, fully paid contract.

## Results

The result appears with its signed conclusion, not before testing. Representative
contributions to **Collegium Research Results**:

| Project | Permanent contribution |
| --- | --- |
| Field Atlas | Research speed +5% |
| Shared Senses | Reconnaissance +10% |
| Self-Repair | Attrition -10% |
| Crystal Drive | Factory output +5% |
| Sorting Engine | Efficiency growth +10% |
| Necrotic Suture | Trickleback +5% |
| Tissue Bank | Trickleback +5% |
| Ritual Brake | Stability +5% |
| Chorus | Magical infantry organisation +15%; research speed +5% |
| Manufactory | Factory output +15%; efficiency growth +10% |
| Last Minute | Trickleback +15%; recovery +10% |
| Contact | Research speed +5%; reconnaissance +10% |

All 26 completed projects together contribute: research +18%, reconnaissance +25%,
experience loss -15%, magical infantry organisation +20%, recovery +25%, attrition -10%,
factory output +20%, efficiency growth +25%, trickleback +25%, stability +5% and
supply consumption -10%. These are project-only totals; civic and institutional
modifiers are separate. Refresh recomputes from completed flags and cannot stack twice.

Revolver Howitzer, Sleep Lecture, Ageless Sleep and Silent Witness remain failures.
Instrumentation changes the Howitzer's signed trial report, never its failed outcome.
Last Minute is emergency stabilisation, not immortality; Contact is a limited exchange,
not a universal portal or enslavement.

## Joint Dossiers and Origins

| Joint project | Faculties | Required conclusions | Theory / trials | Base PP |
| --- | --- | --- | --- | --- |
| Borrowed Touch | Leopold + Silver Star | Prosthetics; Phantom Pain | 35 / 56 days | 35 / 55 |
| An End Written In | Viira + Asinti | Spell Notation; Ritual Brake | 42 / 49 days | 40 / 50 |

Borrowed Touch grants -5% experience loss and +5% recovery, without curing all phantom
pain. An End Written In grants -5% supply consumption and +5% magical infantry
organisation, without universal magical suppression. Joint projects appear in both
faculties but do not replace any of the five opus prerequisites.

Each opus's **Origins** view binds the actual five preparatory conclusions, including
the failed hypothesis, into an individual covering note. Unfinished conclusions are
not disclosed early.

## Pacing

Five preparations plus the opus, sequentially within each faculty. Other faculties
can operate concurrently if factories are available; joint work and interruptions add
time. No automatic PP income is assumed. The table is the base theory/first-series
schedule, before the six interactive follow-ups; their additional days and PP depend
on each preparation and response. Time spent awaiting a player response is unbounded.

| Faculty | Base days | Base PP | Instrumented days | Instrumented PP |
| --- | ---: | ---: | ---: | ---: |
| Viira | 581 | 465 | 525 | 575 |
| Leopold | 511 | 515 | 455 | 625 |
| Silver Star | 644 | 490 | 588 | 600 |
| Asinti | 651 | 495 | 595 | 605 |

## Save Compatibility

Completed projects keep their completion flags and receive the unified, rebalanced
result on refresh. No second invoice, application tax or daily upkeep is imposed.

The original 78 mission IDs remain stable; interactive verification adds eight hidden
timers per project (208 in total). New paid stages set a stage-specific
`_revised_contract` flag. Already-running stages without that flag retain their old
minimum completion time and factory reservation (zero for old ordinary work, one for
old instrumented trials). New attempts use the revised contract. Cancellation and
teardown clear the marker; late callbacks cannot finish a restarted contract early.
Native save scheduling still needs in-game confirmation.

Already-running legacy trials finish without an unexpected interactive checkpoint.
The GUI opts new trials into the interactive contract; the existing AI start effect
retains its automatic sequence. Old completed reports remain readable without
inventing experimental choices retroactively.

The owned weekly AI hook starts at most one paid stage per week in peacetime,
uses sequential trials, reserves 100 PP and obeys the same faculty, route, homeland,
factory and opus prerequisites as the player. It never starts work for a human.

## Sources and Verification

Runtime definitions are generated by `Build-BarradCollegiumProjects.cjs` and
`Build-BarradCollegiumMenu.cjs`; the catalog owns project identities and budgets.
Original faculty prose and four laboratory backgrounds are retained. The new
experimental observations and follow-up reports supplement the original documents.

Installed HOI4 `documentation/effects_documentation.md`,
`modifiers_documentation.md` and `triggers_documentation.md` define native contracts.
EaW `common/characters/BAR.txt` and `common/scripted_effects/EAW_BAR_effect.txt`
supply faculty identities and life flags; `common/on_actions/_documentation.md`
documents the country-specific daily/weekly hooks.

Run the following after changing generated content:

- `node tools/Build-BarradCollegiumProjects.cjs --check`
- `node tools/Build-BarradCollegiumMenu.cjs --check`
- `node tools/Test-BarradCollegiumProjects.cjs --native`
- `node tools/Test-BarradCollegiumMenu.cjs`
- `node tools/Test-BarradCollegiumExperiments.cjs`
- `python tools/Preview-BarradCollegium.py`

Fixtures exercise emitted effects and native identifiers, but are not the HOI4 engine.
Rendered previews likewise are source-based images, not in-game screenshots.

Earlier balance-pass verification on 2026-10-10: all 41 commands passed in
`dist/barrad-investigations-20261010/final-20261010-162541-435/results.json`.
Focused results: 1,749 project scenarios, 97 menu groups, 207 frontier scenarios,
106 civic scenarios and 14 cross-module modifier scenarios, all passing. The preview
checked 362 bilingual states and saved 54 images without clipping non-scrolling text.
The earlier intermediate run remains preserved with its two superseded test failures.

The playtest error log also led to bounded native syntax corrections in fielddesk
pagination, normalization capital assignment/country existence, and archive text-sprite
definitions. Their focused suites pass. No live game was relaunched or controlled;
the user subsequently clarified that "text-only" described the lack of interactive
experiments, not a rendering defect. The new laboratory workflow addresses that
design issue; its native rendering and input still require an in-game playtest.

The interactive revision passes 3,506 project scenarios and 360 menu groups, including
all 26 projects, four preparations and two responses. The generated-script fixtures
cover checkpoint/verification persistence, elapsed-time guards, cancellation and
restarts, paired faculties, lost access, fixed failures and legacy/AI completion.
The renderer checks 4,002 EN/RU states and saves 204 previews, with no clipped
non-scrolling text. Numerical effects are tested exclusively in the technical ledger.

Final cross-module run: **41 commands passed, zero failed**, recorded in
`dist/barrad-investigations-20261010/final-20261010-174614-727/results.json`.
The preceding run is preserved: its failures were stale generated menu prose during
the final editorial pass and a missing experiment-catalog dependency in the icon
tool's isolated fixture. Outputs were regenerated and the fixture now copies that
dependency; no production validation was disabled.
