# Aquileian regional campaigns — expanded postwar content

Current design revision, 2026-11-01. Supersedes the imported generic branches and
multi-step national congress described in earlier implementation notes.

## Playable structure

Rila, Westkeep, Pridea and Vinovia each retain the native EaW preparation decisions
and their single read-only support bar. Nothing in the new focuses changes those
support scores or invents a second revolution-preparation system.

Four authored local foundations per region provide ordinary civilian and military
work before the revolution. The 44 copied generic economic, educational and
military focuses have been removed from the regional tree; the global native
generic tree is untouched.

All fifteen political programmes retain their three constituent focuses. Each
programme now adds **twelve distinct focuses**: five economic, five military and
two civic. The last two economic/military stages and the second civic stage require
the regional government to have proclaimed Aquileia. Shared national reconstruction,
accession, restoration and bounded Herzland settlement remain available afterwards.

Only the ratified programme's economic/military columns are shown. Ratification
refreshes the focus layout. Four local foundations remain visible from the start;
they do not require selecting a political camp. A one-time layout refresh supports
existing regional trees without replaying completed focus rewards.

Every programme adds three scenes, following economic focus 2, military focus 3
and civic focus 2: **45 bilingual narrative events**, with two concrete responses
each. These are authored continuations grounded in the native movements, not
claims that the scenes already exist in EaW. Event choices recheck the surviving
government and can grant their reward only once.

## One reply to the centre

After native revolutionary resolution, an eligible region receives the central
government's incorporation event. Existing native focus hooks can send that same
event; a daily fallback uses a hidden JER relay to establish the correct sender.
Request/delivery/answer guards prevent duplicate demands from the two sources.

There are two substantive choices:

- Join the existing national government. A human region transfers play to AI JER
  and joins it with territory and armed forces. JER retains its incumbent and
  native political progress. If JER already has a human controller, acceptance
  explicitly ends the separate regional campaign instead of taking over that player.
- Refuse and immediately fight JER for national leadership. Subordination and
  incompatible bilateral obligations are cleared. There is no 100-PP admission
  fee or further congress/confirmation event. This is a real annexation war,
  not an automatic victory or free territorial transfer.

Programme selection and ratification remain possible during this leadership war,
so refusing an early incorporation demand does not block the local government or
military branch. The native winning camp and frozen movement ranking still control
which programmes are eligible. Victory, peace and ownership/control of Aquileia
remain required for proclamation.

Several regions may answer independently. Another region's refusal must not
invalidate the remaining offers merely because JER has entered a war. Invalidated
offers cannot annex a foreign subject or silently transfer control to a different
political government; a stale-only dismissal is separate from the two live choices.
The former congress/approval events are inert for old queued packets.

## Rewards and presentation

Ordinary rewards use native `effect_tooltip`: factories, equipment, research
bonuses, experience, manpower, political power, development changes and event
notifications. Executable effects retain hidden once-only guards. Focus descriptions
contain story, not modifier lists or implementation instructions.

Each route has an economic and a military national spirit with three stages.
Upgrades replace their predecessor, so completing a chain leaves one economic
and one military spirit. Their final modifiers are cumulative values, not three
stacked grants. Changing the ratified programme removes its superseded spirits;
temporary capitulation does not erase earned stages. Existing provincial-institution
bonuses remain in the shared compact. Its variable-backed changes use concise
native modifier names and signed values rather than prose paragraphs.

New route chains take 518–532 base focus days each, before focus-speed modifiers
and interruptions, plus the political and shared national branches. Economic
stages 3 and 5 each advance society development using EaW's native helper. The
economic finale adds a research slot; ABC and SIS can add two from the starting
three. Five is the cap: an existing five-slot government instead receives two
100% industry/electronics research bonuses, without locking its final focus.
Factory grants and research slots are bounded per programme. The timing
is a source estimate, not observed playtest duration. Existing saves may retain
legitimately earned rewards from the removed generic tree, so new campaigns are
needed for a clean balance comparison.

## Source ownership and verification

- `tools/data/aquileian-campaigns/{JEB,JRR,JFT,VIN}.json`: bilingual authored content.
- `tools/aquileian_campaigns.py`: focus wiring, rewards, spirit stages and scenes.
- `tools/aquileian_loyalty.py`: incorporation/war transition and stale-event guards.
- `tools/Build-AquileianRegions.py`: integration and deterministic generated files.
- `tools/aquileian_tooltips.py`: native labels for variable-backed spirit changes.
- `tools/Test-AquileianRegions.py`: production graph/state scenarios and localization.
- `tools/Test-AquileianCampaigns.py`: all programme chains, previews, rewards and scenes.
- `tools/Test-AquileianTransition.py`: focused transition/interleaving scenarios.

Installed reference: the EaW Workshop tree recorded in `EAW_UPSTREAM.md`, not an
external lore summary. No new icons, portraits, player counters, launcher edits,
Workshop packaging, version bump or Git publication belong to this change.

Engine playtest priorities: native victory versus immediate peaceful resolution;
two regional humans answering in different orders; refusal before ratification;
the actual national-idea and event tooltips; new-focus layout after ratification
and save/reload; constitutional versus republican successor identities. Source
tests cannot establish engine event timing, war calls or rendered layout.

Generated inventory: **265 authored focuses, 112 event definitions, 1,499 keys per
language and 29 output files**. Event definitions include the hidden relay and
retired compatibility events; this is not a count of player-facing story scenes.

Recorded source validation:

- Main graph/state/localization suite: **94 tests passed**, 111.053 seconds;
  `tmp/AQR-expanded-regions-tests.log`.
- Dedicated transition suite: **12 tests passed**, 0.183 seconds;
  `tmp/AQR-expanded-transition-tests.log`.
- Final generated inventory/localization rerun: **11 tests passed**, 0.825 seconds;
  `tmp/AQR-expanded-inventory-tests.log`.
- After the remaining Herzland/restoration focus previews were converted:
  **15 inventory and partition tests passed**, 3.193 seconds;
  `tmp/AQR-expanded-final-tests.log`. Core grants and event calls now use native
  previews; the partition explanation uses localized state names instead of IDs.
- Campaign suite: **10 tests passed**, 20.479 seconds;
  `tmp/AQR-expanded-campaigns-tests.log`. Covers all fifteen complete branches,
  replacement spirit stages, modern society, research-slot caps, native
  research-trigger spelling, two choices per live scene and a harmless stale
  dismissal after a government change.

These are parsed source scenarios, not observed HOI4 execution. The final focused
reruns cover the research-trigger correction, mandate-loss cleanup and stale-scene dismissal added
after the full-suite pass. The installed EaW source is checked independently for
`amount_research_slots`; a test model accepting a command is not engine evidence.
The deterministic builder reports zero stale output files; `git diff --check`
also passes. A new campaign is recommended for balance testing, because earned
rewards from the removed generic branches are intentionally not confiscated.
