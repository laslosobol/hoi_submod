# Barrad: After the Pentarchy

Reworked against the installed EaW source snapshot on 2026-10-06. This is new-campaign content, not a migration of an existing Barrad ending. The Cyanolisia gameplay files are unchanged.

Latest integration: [dedicated research interfaces, 2026-10-10](barrad-interactive-gui.md), following [meter retirement](#meter-retirement-verification). Service casework and foreign assignments now have dedicated GUIs; faculty controls and two joint projects live in the Collegium journal. Political focuses and civilian programmes retain their existing interfaces. The [2026-10-08 readiness pass](barrad-readiness-pass.md) records the preceding baseline. Earlier test counts below describe their dated checkpoints.

## Meter Retirement Verification

On 2026-10-10, all 30 Barrad regression suites and three builders' `--check` commands passed on Windows with PowerShell 7.6.5 and Node 24.19.0. Exact commands and individual logs are recorded locally in `dist/barrad-meter-removal-20261010/results.json`. The initial run exposed three outdated fixture assumptions: direct rather than guarded personnel reservations, missing `clear_variable` execution, and missing Collegium access predicates. Those models were corrected, with refund/access/old-variable assertions retained or added, and the affected suites rerun successfully.

The Collegium suite passed 5825 assertions, including six no-DLC ending walks; Service rewards passed 208 scenarios. The new retirement audit passed eight scenarios across 197 content files and allows the two retired variables only in six unconditional cleanup statements. Project/menu/icon builders remain consistent with their sources. No artwork was regenerated.

These are source and deterministic fixture checks, not a live HOI4 playtest. Old running Collegium decisions lack the new assignment evidence; no personnel refund or completion reward is fabricated for them. Their native timer/factory-release behavior remains unverified. See [the old-save boundary](HSM_BAR_collegium.md#old-save-boundary); use a new campaign for acceptance testing.

## Entry and Trees

The native friendship requirements still lead to `barrad_end.2`. Ambrosius dies in both options. The player either spares the four guests under civilian oversight or follows the original killing of the Pentarchy and establishes a civilian republic. The covert Service emerges later from the republic's land-recovery commission. Other original routes remain available before this ending.

For playtesting, launch HOI4 with `-debug` and use **DEBUG: Trigger the friendship ending** in EaW's existing Debug decisions category. The free, instant, once-only decision opens `barrad_end.2` with both choices intact, bypassing relationship/focus requirements. It is visible only to the human Barrad player before an ending, with the native `barrad_endgame` value still zero; it never resets an active submod route. Use a separate test save. Added regression coverage passed in `node tools/Test-BarradPhases.cjs` (53 groups) and `pwsh -NoProfile -File tools/Test-BarradContent.ps1` (211 checks); engine execution still requires playtesting.

There are **135 new focuses**, all 28 or 35 days:

- **Collegium: 37**, across `HSM_BAR_collegium_tree` and `HSM_BAR_collegium_future_tree`. Four personal arcs, public accountability, civilian projects, wartime obligations and three scientific charters. Progress depends on completed work and policy choices, not trust or capacity scores. Eight institutional focuses grant specialised research bonuses; land work builds infrastructure. Four optional applications require the corresponding completed faculty Magnum Opus, without blocking the institutional ending.
- **Civil government: 16**, shared by both Collegium stages. Municipal authority, courts, an accountable cabinet, procurement and public services develop separately from the four scholars. Five policy scenes shape a bounded Civil Government modifier. Cabinet formation requires neither war nor the later scientific charter. See [civic government](barrad-collegium-civic.md).
- **Collegium frontiers: 11**, shared by both Collegium stages after the civilian foreign office. Kasa and Southern Deer campaigns require explicit parliamentary authorization; treaties and friendly relationships block offensive goals. Wittenland integration requires a recorded direct attack and defensive victory, followed by paid provincial registration and citizenship. See [frontiers and victory rules](barrad-collegium-frontiers.md).
- **Republic transition: 9**, in `HSM_BAR_republic_tree`. Village councils and relief houses precede a field survey, recovered laboratory records and the first underground expedition. Six timed decisions cover these investigations, archive recovery and two stages of land rehabilitation. Only the final transition focus founds the Service, after the expedition's rescue choice.
- **Service: 34**, across `HSM_BAR_directorate_tree` and `HSM_BAR_directorate_world_tree`. S.C.P., the Service for Containment and Preservation, works behind a civilian government which does not know it controls the hidden network. Local casework and partial land recovery precede five regional offices. Foreign findings enable the final rehabilitation programme. Doctrine review follows completed studies, land recovery and the cult investigation. Focuses authorize institutions and policy; none completes a case study or awards magical knowledge.
- **Common: 28**, for paid reconstruction, living standards, schools, industrial production, civilian science, defence and negotiations with neighbours. Native EaW effects improve poverty, literacy, society development and the science base. Technical school, polytechnic and research council each add one research slot only below five: the native two-slot start can reach five without anomaly research or a foreign story outcome.

Four repeatable civilian programmes unlock through the land register, village schools, power grid and civilian laboratories. Living standards and school expansion cost 50 political power and take 120 days; industrial investment and research grants cost 75 and take 180. Each completes one native tier improvement and disappears at its relevant maximum. Programmes can run during war, but loss of owned/controlled Barrad state 624, capitulation or institutional dissolution cancels them without the improvement. A running flag prevents duplicate completion rewards. Unlocks read completed focuses, so old completed land-register focuses still open the new programme without replaying their rewards. The former native Barrad society decision is excluded only on our routes; its original cost, timing and effects remain intact elsewhere.

Two short civilian scenes accompany the polytechnic and research council. Development does not heal magical contamination, reveal anomalies, grant occult knowledge or replace the route-specific land-recovery story. No additional national meter is introduced.

Second stages use `load_focus_tree` with `keep_completed = yes`. Their independent roots prevent shared-focus descendant expansion from showing future content prematurely. Common content remains visible in both stages. Coordinates occupy separate areas. Entry removes obsolete relationship spirits, Ambrosius's research modifiers and inherited trade/volunteer restrictions. Gasienica chairs the provisional government; the spared four are not automatically made rulers.

The native `Barrad Events.txt` override changes the friendship ending and adds active-route exclusions to 62 queued events which otherwise change the tree, kill its characters or restore obsolete relationship spirits. Their original contents are preserved behind those guards. The raid-victory callback keeps its cleanup while suppressing old relationship rewards. Native annexation, puppeting and release still reset Barrad; matching teardown hooks remove the expansion's active institutions and diplomatic commitments without erasing neighbours' settlement history.

Both new routes exclude all 15 decisions in Ambrosius's native diplomatic category, including completion callbacks. Five options in three already-queued diplomatic events also recheck BAR's active-route flag. Apart from the society-decision exclusion described above, other native categories and original callback payloads are preserved. Entry and the daily pulse clear the obsolete diplomatic unlock flag.

The Service's secrecy is narrative, not a numeric resource. There is no cover meter, cover-derived political-power modifier, liaison threshold or front-rotation maintenance decision. Trust and institutional capacity were also removed from both routes on 2026-10-10. Maintenance clears the retired variables in continuing campaigns; this does not establish general old-save compatibility. No current choice awards the retired collective-repression spirit. Neither route requires filling an abstract institutional meter.

The existing **Unseen Service** spirit collects institutional capabilities, separately from Anomalous Research. Local training protects operatives, evidence handling improves bonus operation outcomes, and regional offices develop networks with distinct secondary benefits. Cipher channels and analysis improve cryptology; the counter-cult department strengthens counterintelligence. La Resistance gates espionage-specific bonuses; cipher channels, analysis and sealed orders instead improve native encryption/decryption without it. Research speed comes directly from completed institutions: secured laboratories +1%, archives +2%, specimen storage +1%, suppression laboratory +1%, and another +1% each from the register and review commission. These are explicit focus rewards, not a replacement currency. Nine focuses add ten research-bonus uses for electronics, industry or field hospitals; the existing radio research bonus remains. Story unlocks, doctrine consequences and anomaly-study requirements are preserved.

Institutional bonuses are recalculated from completion flags or completed focuses, never accumulated on each refresh. Completion flags make new rewards immediate; completed-focus checks restore permanent capabilities in older Service saves without regranting research bonuses. The spirit is inactive before Service formation, on the Collegium route and after capitulation or dissolution. This limited recovery is not a general save-compatibility guarantee.

Ten transition scenes and twenty rewritten Service scenes follow original characters: physician Marta Krzemien, former assistant Seweryn Olcha, field agent Jadwiga Wrona, northern director Irma Kalk and civilian administrator Michal Zawisza. These characters and Alder Ford are authorial additions, not claims about EaW canon. Gasienica remains the native head of government. Retrieval priorities create lasting policies and a later, choice-sensitive account; shared accounts produce delayed exposure; useful findings may wait for independent replication. Core and Service choices are replay-guarded and inert after institutional dissolution.

The transition preserves inhabited villages and damaged land rather than treating Barrad as an empty desert. Partial recovery replaces native climate penalties in state 624 with a smaller monitored-soil modifier after rock and vegetation studies and a 45-day programme. Final recovery requires the riverland marsh study, amulet study and wards project, then 75 days of work. It removes climate penalties only from owned, controlled homeland states 624/625/626; it does not magically reclaim occupied territory. The foreign mandate requires partial recovery and recovered archives; final doctrine requires completed rehabilitation.

## Research and Operations

The Collegium also has an owner-only four-faculty journal after its oath: 20 preparatory
projects, four Magnum Opus projects and two optional joint projects, with EN/RU documents.
Every opus requires all five completed preparations of its department, including failed
experiments. Menu actions run paid native timed missions; accepted results accumulate
in a separate Collegium research modifier. See [project rules](HSM_BAR_collegium.md#faculty-research-menu)
and [department artwork](../art/barrad-collegium-menu.md). These programmes do not replace
the following institute projects and need no DLC. Faculty methodology and application
policies trade political power, time, factory use and upkeep. AI can begin one paid
stage weekly in peacetime while retaining 100 PP; outcomes and prerequisite gates are
the same as the player's. See [policy costs and lifecycle](barrad-collegium-projects.md).

Seventeen specific case studies supplement the six existing institute projects (clinical thaumaturgy, a civilian grid, wards, containment, forensics and suppression). Human Service research uses the dedicated console's paid assignments. The original magical-specialization projects and no-DLC decisions remain the AI backend; the Collegium's institute path is unchanged. A completed study opens a findings report and a once-only application/retention choice. Mundane explanations can yield practical research bonuses; an inconclusive lead cannot.

For the Service, wards and containment require studies of Living Stone, the underground response and the naturally explained shaft echo. Forensics additionally needs the Titan and misleading compass studies; suppression additionally needs the amulet-boundary study. The suppression project still needs completed forensics, normalization and laboratory authorization. All mandatory evidence is obtainable locally without a foreign random event. See [case progression and flag contract](barrad-case-progression.md). Collegium eligibility is preserved.

Institute establishment unlocks the facility technology and, with Gotterdammerung, attempts construction in an eligible controlled state and supplies a scientist plus an initial breakthrough reserve. Construction can be retried if the original location was unavailable.

Recovering the Pentarchy's archives takes 45 days after Service formation. A narrow `barrad_tech.txt` override then permits 31 research technologies across the four original branches. Research costs, paths and exclusive choices remain intact; personal powers, bodies and alive-marker technologies remain untouched. No technologies or resurrected pentarchs are granted. All 23 special projects use the installed `sp_complexity.small` constant instead of unsupported numeric complexity values.

Without Gotterdammerung, paid 120-180-day programmes feed the same guarded completion effects and choices. The Collegium's main institutional story uses concrete completed-work alternatives to project gates, without trust/capacity thresholds.

Four dedicated Fielddesk assignments cover reconnaissance, archives, relic retrieval and documented remains for the human Service player, regardless of La Resistance. Five regional offices unlock the corresponding operational tabs. A checked rumour and current evidence must identify the target before foreign assignments appear; opening an office does not expose every country. All assignments recheck the target on completion. The original native operations and fallback decisions remain for AI. Local and openly purchased mundane samples do not require a fabricated foreign raid.

Five paid regional continuations develop the residency-opening scenes through mundane
explanations and unresolved evidence. Zebrica's two-stage inquiry contrasts a dealer's
claim with an account controlled by local performers. A three-part continuation of
the convoy investigation revisits the player's treatment of the intermediary, followed
by a paid policy review. Ten new events and eleven assignments preserve old choices
and award bounded research/method benefits without adding archive objects or a secrecy
currency. See [residencies and the returning network](barrad-service-residencies.md).

The first playtest exposed unsupported argument-block calls to scripted effects, an invalid inclusive variable comparison and a fixture that incorrectly simulated parameter substitution. Anomaly calls now use literal effects and the documented comparison form. The fixture rejects the former syntax. All 13 timed anomaly decisions explain their actual conditional outcome; a failed investigation reports failure at runtime instead of presenting failure as its ordinary completion tooltip.

## Anomaly Coverage

**18 archive cases are implemented, not all 51 catalog entries.** They include the existing canonical dossiers, a conditional reactor inquiry, three authored mundane investigations (shaft echo, marsh lights and misleading compass), and an inconclusive Zebrican provenance inquiry. Seventeen cases have laboratory studies; the inconclusive inquiry ends without a specimen, study or bonus. Existence, manifestation, rumour verification, field investigation, study, application and current access remain separate facts. Crowns are independent country-origin instances, not one global object.

Rosa, the Herald and Sombra have no invented recoverable corpse. Grover II's positively documented bones before resurrection are recoverable; taking them prevents the native experiment from using the same remains. A defeated ruler does not automatically become a body. More post-defeat forensic stories would require explicit evidence or a separately authored recovery event, not a capitulation check disguised as proof.

See [case coverage and source hooks](HSM_BAR_anomalies_coverage.txt), [the 51-entry research catalog](barrad-anomaly-catalog.md), and [Collegium details](HSM_BAR_collegium.md).

## Archive and Presentation

Service formation unlocks a dossier button in Barrad's political panel, with the first expedition's rock lead already recorded. The owner-only archive contains five index pages and 53 rewritten in-world documents, released by actual progress. Reports do not substitute project instructions for narrative. Hearth, Lunar Circle, Winter Watch and Starless describe containment uncertainty; Guardian denotes a protective role, separately from danger and custody. Unknown evidence remains explicitly unknown.

The 1000x700 archive is skinned as a cloth folder with paper index cards, selected document tabs and a light reading sheet. Live native EN/RU glyphs use dark ink and contrasting result colors; text remains scrollable and photographs retain their full 600x300 size. White redaction squares have a dark backing, while excised passages use a dark cut-strip and muted note. `node tools/Build-BarradArchiveControls.cjs` and `node tools/Build-BarradRedactions.cjs` rebuild the deterministic controls/marks. The generated material, prompt and source references are recorded in [the archive skin brief](../art/barrad-archive-skin.md). Selection properties read presentation variables only; case access and rewards are unchanged.

The reader now encounters a recovered archive rather than being addressed as a Service employee. Six cases (rock, lower presence, reactor, crown, shaft echo and marsh lights) have three surviving editions of each intake, field and study document: circulation copy, restricted copy and sealed file. Eighteen base texts were rewritten and 36 variants added in each language. Editions differ in omissions and institutional framing, not just redaction length. Even sealed copies retain missing material; ordinary acoustics and chemistry remain ordinary explanations. These are historical distribution levels, **not player clearance or a secrecy meter**. Switching editions cannot skip investigation/study gates, change Results or grant evidence.

The echo, lower-presence and reactor field files have a play icon for a nine-second, non-voice historical recording. These original synthesized sound props use native GUI one-shots with guarded access and no gameplay effects. Same-clip overlap is suppressed; no pause/stop transport is provided. [Audio sources, reproduction and limitations](../art/barrad-archive-audio.md).

Archive navigation uses matching 36x36 metal controls with antialiased Lucide glyphs, not the stock back/close buttons. Navigation and photo/audio occupy separate groups on the left cloth toolbar; the case heading and all paper content stay inside the clean top-sheet inset (x=350..956, y=136..640). The recovered-copy note also moves onto the cloth. Document tabs and edition selectors share a 600px width with 12px gutters. The correction passed Content 246, Archive 44, ArchiveSkin 22, ArchiveCopies 17 and ArchiveAudio 18 with no failures; twelve EN/RU previews regenerated without clipping. Tests reject the former edge-overlapping positions and check text bounds, distinct control glyphs and overlap down to a 1280x720 canvas. Actual engine input and UI scaling still require playtesting; no wording, case state or reward logic changed.

Each dossier also has a separate **Results** tab: a concise status and case-specific programme title, color-coded current contributions, and recorded costs/rewards. Suspended effects show zero instead of inactive nominal bonuses; unrecorded historical payments are not invented. The mutable **Anomalous Research** spirit sums case outcomes, including mundane findings and object-disposition tradeoffs. Its helper recalculates from flags instead of stacking rewards on repeated refresh. A terminal object disposition supersedes its interim study policy. Losing access suspends physical benefits without deleting knowledge or the document history; dissolution removes the spirit. Archive clicks only change presentation variables, never evidence or rewards.

Modifier maintenance is hidden from focus, decision and event tooltips. Recalculation installs Anomalous Research only when absent and immediately refreshes dynamic modifiers; it is not itself a reward. Service focuses describe their actual institutional upgrades, while case choices retain explicit anomaly-contribution tooltips. Reserving a study refreshes its case contribution without an extra resource reward or political-power fee. Focus unlocks name the relevant decisions. Removing secrecy does not change case bonuses or complete an anomaly study through an unrelated focus. Story-choice fees that bought only cover points were removed with those points.

Twelve cases now include a separate photographic attachment button beside Results: field photographs, copied technical drawings and secured-specimen plates, four selectively redacted. Images are 600x300 with EN/RU captions. Field attachments require investigation or completed study; Crown, Chalice and Dark Heart photographs require completed study. They remain dated historical records after loss of physical access. Other cases have no empty photo placeholders. Prose retains its full scrolling area; opening a photograph never grants knowledge, custody or bonuses. Source prompts and the case list are in [the photo brief](../art/barrad-archive-photo-brief.md).

All 34 Service focuses have internal and civilian-cover names/descriptions in EN/RU. Text selectors use the installed engine's documented `Player` localization promotion. Dynamic icons use the established EaW syntax. Their `BAR = { is_ai = no }` condition is explicitly an **SP approximation**, not per-viewer secrecy in MP: foreign clients can receive the internal icon when BAR is human-controlled. Focus title caching, observer/tag switching and simultaneous MP rendering still need engine testing. This is UI presentation, not protection against inspecting mod files or effect tooltips.

The art set preserves the 34 individual internal icons and 11 shared civilian motifs,
and adds 38 reviewed source illustrations. All 135 focuses, 32 ideas and six dynamic
modifiers use custom artwork, with deliberate thematic reuse. All focus icons have
standard and shine sprites. Sources, prompts, repairs and revision hashes are recorded
in [the Barrad art manifest](barrad-icon-manifest.md). Cyanolisia's approved art inventory
is not modified.

## Diplomacy and Commitments

Wittenland, Kasa and Austurland can negotiate inspections, guarantees or concessions. Refusal can still lead to war. Existing wars are not cancelled, native countdowns are respected, and peaceful settlement does not award occupation rewards. Gryphus retains its hostile option with a warning. Narrow source overrides cover these countries' original invasion and post-Barrad progression paths.

Contact with S.M.I.L.E. appears only after Sombra actually rules the Crystal Empire and the foreign liaison focus is completed. A cutout offers technical cooperation without revealing the network's control of Barrad. S.M.I.L.E. may accept or refuse. Full warding research enables assistance only while Equestria fights the actually ruling Sombra. The combat bonus is removed when those circumstances end. Concealing operational dangers from the partner or war with Equestria breaks cooperation. A temporary volunteer-dispatch window is available through ordinary diplomacy: HOI4's permission is country-wide, not recipient-specific, and revoking it cannot recall divisions already sent.

Normalization starts with a hidden local trial. Isolating its site reduces subsequent repair costs compared with a connected gallery. The player may reject the programme or authorize a global extension after review. Five regional installations and completed suppression research precede a separate activation decision. The resulting global penalty reaches every existing or newly released country, including Barrad. After initial success, failing barriers lead to an actual, finite invasion by the new NML country. The player may restore the barriers or fight with conventional means; restoring magic does not erase invading units. World consequences survive Barrad's defeat.

**Equipment limitation:** the implemented global effect targets EaW's dedicated magical infantry, artillery and tank archetypes. There is no verified per-module combat selector for existing modular air/naval/tank designs; those components are **not** currently debuffed. Ordinary vehicles are not broadly penalized as a substitute. This part of the larger design remains incomplete. The invaders and barrier story are original submod fiction, not established EaW history. Neither doctrine turns the Service into a publicly acknowledged police government.

The finite invasion now uses three formation types with supporting units. The final
wave responds to territorial expansion; loss of all breach control stops further
scripted reinforcements. Defeat removes the invader spirit. State-transfer safeguards,
initial wave limits and surviving enemy units after restoration remain intact.

## Validation and Playtest

Commands from the repository root, with PowerShell 7.2+ on Windows and Node.js:

```powershell
pwsh -NoProfile -File tools/Test-BarradContent.ps1
pwsh -NoProfile -File tools/Test-BarradCollegium.ps1
pwsh -NoProfile -File tools/Test-BarradAnomalies.ps1
pwsh -NoProfile -File tools/Test-BarradDiplomacy.ps1
pwsh -NoProfile -File tools/Test-BarradLegacyDecisions.ps1
node tools/Test-BarradSecrecy.cjs
node tools/Test-BarradResearchOperations.cjs
node tools/Test-BarradServiceStory.cjs
node tools/Test-BarradCases.cjs
node tools/Test-BarradCaseOutcomes.cjs
node tools/Test-BarradModifierTooltips.cjs
node tools/Test-BarradDevelopment.cjs
node tools/Test-BarradServiceRewards.cjs
node tools/Test-BarradArchive.cjs
node tools/Test-BarradArchiveSkin.cjs
node tools/Test-BarradArchiveCopies.cjs
node tools/Test-BarradArchiveAudio.cjs
node tools/Test-BarradFocusPresentation.cjs
node tools/Test-BarradPhases.cjs
node tools/Test-BarradNativeContracts.cjs
node tools/Test-BarradNormalization.cjs
pwsh -NoProfile -File tools/Test-BarradArt.ps1
pwsh -NoProfile -File tools/Test-BarradArchivePhotos.ps1
pwsh -NoProfile -File tools/Test-CyanolisiaFocusFlow.ps1
pwsh -NoProfile -File tools/Test-CyanolisiaNarrative.ps1
```

The suites check script structure, references, localization parity/BOM, focus membership/coordinates, native sprites including focus shine, narrowly scoped source overrides, reachable Collegium endings, research and operation completion guards, custody transitions and neighbour negotiations. The deterministic fixture interpreters are not the HOI4 engine.

Verified on Windows, PowerShell 7.6.5 and Node.js 24.19.0, 2026-10-06:

| Suite | Passed | Failed |
| --- | ---: | ---: |
| Barrad integration | 208 checks | 0 |
| Collegium | 2,019 assertions | 0 |
| Anomaly registry | 38 scenario groups | 0 |
| Neighbour diplomacy | 38 scenario groups | 0 |
| Native diplomatic exclusions | 48 scenario groups | 0 |
| Secret network and liaison | 13 scenario groups | 0 |
| Research and operations | 379 assertions | 0 |
| Service story | 36 scenario groups | 0 |
| Case progression | 26 scenarios | 0 |
| Case outcomes | 109 scenarios | 0 |
| Dossier archive | 34 scenario groups | 0 |
| Focus presentation | 129 assertions | 0 |
| Four-phase progression | 51 scenario groups | 0 |
| Native research contracts | 23 scenarios | 0 |
| Global normalization | 47 scenarios | 0 |
| Custom art | 45 asset scenarios | 0 |
| Cyanolisia focus flow | 175 checks | 0 |
| Cyanolisia narrative | 45 checks | 0 |

2026-10-07 development and Service-reward follow-up: all 20 Barrad suites listed above passed on Windows, with zero failures. Service rewards: 195 scenarios; development: 92; integration: 240 checks (104 focuses, 147 events, 2,246 English keys); native decision exclusions: 50 groups; modifier tooltips: 14 scenarios and 111 maintenance-bearing focus/decision parents. Reward coverage checks exact cached bonuses, DLC variants, exclusive-doctrine totals, immediate completion, old-save recovery, teardown, repeat refresh, anomaly-ledger independence and EN/RU numeric tooltips against installed modifier definitions. Development coverage executes installed EaW tier helpers, reaches all four maximum levels on both routes, caps research slots at five, and checks cancellation, occupation, dissolution, replay and parallel programmes. The remaining story, research, diplomacy, archive and art suites also passed. The two unchanged Cyanolisia suites and HOI4 itself were not run.

The registry contains 147 new event definitions, including news and hidden dispatch/result events. This is not a claim of 147 independent narrative scenes. The copied source versions of Barrad, Yale, generic fantasy events, Crystal Empire, Dread League and the WIT/ZES trees were previously hash-checked against the installed Workshop dependency and matched; narrowly scoped override-preservation tests continue to check our changes against those source copies.

Integration failures found during this pass were repaired: old fixtures lacked the new Service-foundation gate, the event scanner did not include news events, and the anomaly suite assumed retired one-time rewards and untranslated tooltip aliases. Tests now evaluate the actual new contracts and resolve those aliases. Research fixtures also use native NOR semantics for `NOT`; no unknown engine predicates are accepted as successful conditions. The earlier playtest's numeric project complexity and invalid manpower/political-power predicates were corrected against installed documentation. All 18 suites above passed after integration.

In-game verification remains required: reach the real friendship ending in a new game, test both second-stage transitions and save/reload, inspect focus/decision/event tooltips, run one operation and both research interfaces, and exercise a neighbour ultimatum while its old timer is already active. In particular, verify agent `FROM` scopes in the operations UI, facility placement and scientist assignment. Balance and full campaign duration are not validated by static tests.

For this correction, fully restart HOI4 and start a fresh campaign. Walk Republic survey/records/first expedition, Service founding, local studies and partial land recovery before the foreign transition. Verify recovered research access, the named agency, homeland recovery and both doctrines. In the archive, check the initial rock lead, five pages, locked documents, Results tab, mouse shielding, scrolling and save/reload at the intended UI scale. Compare a dossier's current contributions with the aggregated national spirit, then lose and regain physical access. Inspect internal/foreign focus text and icons, Ambrosius-category exclusions and the lead-filtered operation list. Exercise global activation, each ending, NML spawning and newly released-country penalties; see [normalization contracts and limitations](barrad-normalization.md). No post-fix engine session or clean new `error.log` is claimed.

Existing Service focus art is reused, including for the new transition focuses. The archive follow-up adds twelve generated photographic attachments, not new focus icons. NML uses the native generic rebel flags as a provisional contact marker. The Cyanolisia art approvals are untouched. No release version, Workshop export or Git commit is produced by this task.

The photographic follow-up reran `node tools/Test-BarradArchive.cjs` (40 groups), `pwsh -NoProfile -File tools/Test-BarradContent.ps1` (208 checks) and `node tools/Test-BarradCaseOutcomes.cjs` (109 scenarios), all passing. `pwsh -NoProfile -File tools/Test-BarradArchivePhotos.ps1 -PreviewPath art/previews/HSM_BAR_archive_photos.png` passed all 12 asset scenarios: PNG decoding, dimensions, GFX references, full-pixel PNG/TGA equivalence, orientation, opacity and nonblank tonal variation. The contact sheet was visually reviewed at the 600x300 game texture size. No live HOI4 rendering is claimed. Default photo validation is read-only; only the optional preview parameter writes a contact sheet.

2026-10-07 found-copy/audio follow-up: Content 246, Archive 43, ArchiveSkin 21, ArchiveCopies 17, ArchiveAudio 18, CaseOutcomes 217, Secrecy 16, FocusPresentation 129, Art 45 and ArchivePhotos 12 passed with zero failures. Twelve EN/RU source-based previews rendered without clipping; all six edition previews plus Results/photo examples were visually reviewed. Restore of the sealed BR-003 cross-reference fixed the two narrative regression failures caused by redacting it in every edition. Audio validation covers actual PCM, registration and gated read-only controls; native playback is still unverified. Check the three edition buttons, retained stage locks and play icons on the echo, lower-presence and reactor field files after a full game restart. No clearance meter, gameplay changes, commit or Workshop export accompanies this follow-up.
