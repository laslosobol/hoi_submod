# Zypressen Imperial Continuation

## Integration and Ownership

Root: `HSM_ZYP_victory_roll`, absolute `(58, 0)`. Import this root **only** in
the native `avian_fascists` tree. Parent has supplied that import; this package
does not edit `AVI.txt`, native events, shared scripts, README or other tests.
All 17 focuses use absolute coordinates within `x=56..60`, `y=0..11`.
There are 15 events, 8 ideas, 3 recovery/review decisions and 1 decision category.
English and Russian localization use UTF-8 BOM and identical keys.

Owned scripts all have basename `HSM_VER_zypressen.txt`: national_focus,
scripted_triggers, scripted_effects, on_actions, ideas, decisions,
decisions/categories, and events. Other owned outputs are the two corresponding
localization files, this document, and `tools/Test-VereniaZypressen.py`.

## Canonical Sources

Inspected installation: `C:/shit/Steam/steamapps/workshop/content/394360/1826643372`.

- `common/national_focus/AVI.txt`: `avian_fascists`, `declare_the_kingdom`,
  `form_the_archduchy`, `reform_the_kingdom_of_griffonstone`, and
  `a_zypressen_on_the_imperial_throne`. The last grants a `take_state_focus`
  war goal on GRI for state 382. It does **not** perform an imperial coronation.
- `events/Avian Events.txt`: `avian.15` establishes the militarist victory;
  `avian.20` proclaims the Kingdom of Verenia, names Kaiser Trubach, applies
  the native `AVI_dynasty` cosmetic and creates the native faction. None is
  replaced here. The new ceremony establishes a distinct imperial milestone
  and chancery, not another native kingdom proclamation or a cosmetic rewrite.
- `common/decisions/AVI_decisions.txt` and its category: the existing
  `puppet_kingdoms_n_stuff` system releases dependent dynastic governments.
  This package does not duplicate, bypass or alter that creation system.
- `common/characters/AVI.txt`, `localisation/english/country_AVI_l_english.yml`
  (`TRU_desc`, native character names, dynastic release tooltips), and its
  Russian counterpart establish Trubach's military/dynastic ambition. New
  coronation, institutional, freight and muster scenes are authored fiction;
  no new politicians or precise degrees of kinship are invented.
- `common/scripted_effects/00_scripted_effects.txt`,
  `core_all_herzland_states`, defines the nine original-core countries used
  to delimit Herzland. Their installed `history/states` records provide the
  fixed 38-state snapshot below. This package never invokes the coring effect.
- Existing Grover character `GRI_emperor_grover_vi` and death flag
  `GRI_grover_vi_dead` are read only. No custody, guardianship, regency, transfer,
  retirement, replacement or dynasty restoration is performed.
- Game `common/wargoals/00_invasion.txt` supplies `take_state_focus` and
  `annex_everything`. The latter is a normal conquest **war goal**, not an
  annexation effect. Exact existing goal/event/idea assets are reused.

## Entry and Continuity

Entry requires original/current AVI, existence, independence, fascism, ruling
Trubach (`ruling_only = yes`), the completed native throne-war-goal focus, no
capitulation, peace, and settled ownership/full control of every Herzland state
by AVI or its subjects. Occupation of somebody else's capital, an allied
capital, or an extinct GRI tag alone is insufficient. A native dependent Free
City of Griffenheim can satisfy the capital requirement. Existing saves that
already achieved the settlement need no retrospective war-history flag.

Herzland snapshot: 378, 382, 397, 398, 399, 402, 405, 411, 422, 423, 424, 433,
434, 437, 439, 440, 441, 443, 447, 458, 479, 486, 492, 497, 498, 506, 520,
538, 539, 545, 546, 547, 554, 555, 568, 665, 666, 674.

The root sets `HSM_ZYP_started`. The daily hook is inert without that flag,
including all unrelated native and negotiated Avian routes. The ceremony must
be accepted to set `HSM_ZYP_crowned`; postponement waits 60 days. Undelivered
coronation invitations expire after 30 days and can be reissued by decision.
Subsequent work requires the ruling independent government, coronation and
effective capital control. Temporary capital loss pauses the chancery and
institutional benefits; it is not a new coronation or custody transfer.

## Focus Order

| Suffix after `HSM_ZYP_` | Position | Main consequence |
|---|---|---|
| victory_roll | 58,0 | Entry milestone and settlement scene |
| imperial_coronation | 58,1 | New coronation choice |
| household_register | 56,2 | Factual Grover scene; 1x75% electronics |
| rolls_of_the_crowns | 60,2 | Choose the institutional proposal |
| repair_the_arteries | 56,3 | 2x100% support; civilian investment or railway board |
| commissions_not_orders | 60,3 | Invite eligible native dependent rulers |
| arsenals_and_workshops | 56,4 | Military factory/slot or research fallback; 2x100% industry |
| common_colleges | 60,4 | 2x100% electronics; 1x100% to each consenting crown |
| the_muster_dispute | 58,5 | Permanent cadre or limited-rotation choice |
| western_campaign | 58,6 | Western-owner war goals, no declaration |
| reconstruction_contracts | 56,7 | Civilian factory/slot or fallback; 2x100% construction |
| northern_campaign | 60,7 | Northern-owner war goals after western settlement |
| southern_campaign | 58,8 | Southern-owner goals after north and reconstruction |
| eastern_campaign | 58,9 | Eastern-owner goals after preceding settlements |
| seats_for_new_crowns | 60,10 | Later eligible native rulers invited; 1x100% industry |
| accounts_after_campaign | 56,10 | Account review and settled industrial orders |
| crown_and_countries | 58,11 | Epilogue; 40 army XP and 2x100% support |

## Agreements and Rewards

All 35 installed rulers are matched to their actual native tag/character pair,
including Flowena and Griffonstone from focuses, and the differently named
BRF, FAT and ANG appointees. Only the **ruling** character counts. They must
remain AVI subjects; ordinary fascist puppets and former party leaders do not
qualify. Native releases elsewhere, including Nova Griffonia and Meridiennes,
can join the institutions; this does not add overseas campaign demands.

The imperial proposal is either autonomous administration or negotiated common
ministries. Each recipient can refuse. Centralisation may receive an autonomous
counteroffer, which requires a separate imperial acceptance. Neither acceptance
changes autonomy level, borders, cores, leaders or the existing subject relation.
Centralisation is a real delegation of industrial/technical functions with a
different modifier bundle, not annexation disguised as a family compact.

Offers and counteroffers have 30-day pending flags; all event windows are 13
days. Invitations use a 90-day recipient cooldown. Silence never signs; no
required progression depends on acceptance. Reopening invites only eligible
unsigned countries without pending business/cooldown, including newly created
native subjects. Signed countries are not charged or rewarded repeatedly.

| Idea | Exact modifiers |
|---|---|
| imperial_chancery | Stability +5%, PP factor +5% |
| autonomous_crown | Stability +7%, civilian construction +10%, PP factor -5% |
| common_ministries | Factory output +10%, research +3%, daily PP -0.10 |
| dynastic_exchange | Research +5%, production efficiency gain +8%, PP factor -5% |
| railway_board | Supply consumption -10%, infrastructure construction +15% |
| professional_muster | Army organisation +8%, planning speed +10%, stability -4% |
| limited_muster | Supply consumption -10%, training time -10% |
| settled_orders | Production efficiency cap +5%, civilian construction +10% |

Coronation additionally grants +7% immediate stability once. Signing grants
one 100% industry research bonus once per recipient. The colleges' electronics
grant also reaches later signatories, once ever. Temporary capitulation pauses
agreement benefits, retaining consent; restored access never repeats research.
Changing ruler, overlord or imperial government, or war against AVI, voids the
agreement. Daily refreshes guard every persistent `add_ideas` against re-adds.

Factory effects select only owned, fully controlled land with available
capacity, add one slot and one factory, or award a 100% relevant research bonus
if no suitable state exists. The freight scene's civilian option also grants
one construction bonus; the alternative gives the railway board. The muster
choices concern AVI's own forces: permanent cadre plus 30 XP, or limited
rotations plus one support bonus. No subject manpower or units are seized.

## Campaign Geography and Safeguards

Regional lists are the union of installed native release-decision territories:

- West: FEZ, LAK, JFT, VIN, JEB, JER, ARA.
- North: FAT, VED, HAU, TRD.
- South: FRN, TAL, FAL, SIC, WNG.
- East: HLQ, LNS, LUS, GRY, GRU, HLR, CYA, BRF.

These are bounded pan-Griffonian campaign corridors, not a declaration that
every state on the continent has been conquered. Scripts target **current
owners**, even if all original tags disappeared. Independent owners receive
state-focused goals. A hostile independent overlord whose subject owns regional
land, but which owns none itself, receives a general conquest goal against the
overlord instead; peace-conference outcomes still determine the regional result.
This explicitly permits confronting overseas puppet masters without generating
an invalid state-focused demand on a country owning none of those states.

No script declares war. AVI, its subjects, faction allies, subjects of faction
allies, capitulated opponents and countries already at war with AVI are excluded
from new targets. The first unresolved unlocked region alone is reviewed.
Current war goals are not duplicated. Review costs 35 PP, has a 90-day cooldown,
and is available only when an eligible opponent lacks a goal. Later regions
require the earlier regions to have no outside owner, plus peace. Allied
ownership is an agreed settlement, **not** annexation or dynastic membership.
If an earlier frontier changes again, review returns to that unresolved theatre.

## Events and Tests

Namespace `hsm_ver_zypressen`; IDs 0,1,2,3,4,5,6,7,10,11,12,20,21,22,23.
Event 3 has exclusive dead/local/foreign/unknown descriptions; death overrides
stale character presence. Event 10 has central/autonomous proposal descriptions.
No new named politicians, invented marriages or precise relatives are asserted.

Run `python -B tools/Test-VereniaZypressen.py`. It imports the actual parser and
base fixture from `Test-Verenia.py`, extends only operations this package uses,
and rejects unsupported predicates/effects. It executes production rewards,
reply handlers and the gated daily hook. Coverage includes native source parity,
entry/ownership, consent/counteroffers/refusal/expiry, occupation and succession,
retry/idempotence, factory fallback, factual Grover variants, staged dynamic
owner/foreign-overlord goals, full no-acceptance progression, localization/BOM,
asset references and forbidden sovereignty/custody operations. It reports a
missing parent import without editing shared files. These are fixtures and static
checks; no in-game playthrough or rendered focus-tree inspection is claimed.
