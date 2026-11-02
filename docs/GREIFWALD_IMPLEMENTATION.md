# Greifwald: Debt to the Crown

Implementation contract (2026-10-27), artwork added 2026-10-30. New authored continuation of pragmatic Count Cloudet, with no continental war goals or player resource meters. Original AET regional, anarchist, prelate and changeling programmes remain available. The artwork pass covers only added focuses and all national spirits; see [art register](../art/greifwald/README.md).

## Ownership and scope

Main owns triggers/effects/on-actions/ideas/dynamic modifiers, AET native tree hook, native Grover guards, formable guards and integration. Narrative worker owns `events/HSM_AET_story.txt` and `localisation/{english,russian}/HSM_AET_story_l_*.yml`. Focus worker owns `common/national_focus/HSM_AET_campaign.txt` and `localisation/{english,russian}/HSM_AET_campaign_l_*.yml`. Reviewed artwork and sprite bindings are recorded separately in `art/greifwald/manifest.json`.

## Focus interface

All IDs are HSM_AET_<suffix>; each completion calls HSM_AET_finish_<suffix>. Twenty-one main focuses: opening, refuge, home_budget, congress; mandate, household, court_accounts, service, working_table, prepare; obituary, interim, delegates, union, revenues, succession, winter; workshops, roads, scholars, demobilisation. Four additional crisis focuses: letters, audience, hearing, signature.

Availability predicates: HSM_AET_can_open, HSM_AET_active, HSM_AET_can_mandate, HSM_AET_regency, HSM_AET_can_union, HSM_AET_union_work, HSM_AET_can_prepare, HSM_AET_can_finish_union, HSM_AET_crisis, HSM_AET_can_hear, HSM_AET_can_sign. Wrap predicates in concise custom_trigger_tooltip; expose native effect_tooltip for direct rewards and explicit country_event effects where possible. Actual guarded/idempotent effects owned by main. Hidden technical flags must not leak. Decisions and descriptions are narrative prose, reward text separate.

Layout starts at x=56, outside native AET layout. Opening -> refuge -> home_budget -> congress. Mandate -> household/court_accounts -> service -> working_table -> prepare. Obituary -> interim -> delegates -> union -> revenues -> succession -> winter. No mutual exclusion between life/death roots: death during a regency opens the union continuation. Four development focuses follow congress, workshops/roads then scholars/demobilisation. Final prepare/winter require all four plus their political predecessor. Letters -> audience -> hearing -> signature is a separate crisis column. A focus requiring an earlier choice checks that choice's *_done flag using a short tooltip. Completion effects check context again.

## Narrative interface

Events `HSM_AET.<n>`, every option must revalidate the same event-context predicate (delayed windows can outlive regime/custody). Provide a free fallback option when the predicate is false; text key HSM_AET_context_lost in the story localization. Effects listed below perform their own guards. Options wrap technical effects in hidden_effect and show a concise authored effect tooltip or native effect_tooltip. Unknown age/location must never be treated as death; adult Grover uses adult text.

| ID | Trigger | Purpose | Choice effect suffixes (HSM_AET_) |
|---|---|---|---|
| 1 | active | Unanswered letters, Imperial ties / changed neutral-Aquileian policy | accept_relief |
| 2 | active | Refugees and the actual household; never assert local Grover when absent | receive_refugees |
| 3 | active | Home communities demand limits on spending | home_public / home_credit |
| 4 | can_congress | Representatives accept a limited territorial administration | sign_congress |
| 10 | can_mandate | Lawful guardianship or adult transition; protected private guest can decline | accept_mandate / decline_mandate |
| 11 | regency | Ordinary schooling / court education; adult equivalent civic visits | school_open / school_court |
| 12 | regency | Public budget / patron finance | accounts_public / accounts_patron |
| 13 | regency | Constitutional army / contracts with officers; no continental oath | service_law / service_contract |
| 14 | regency | Complaint against court financier | judge_patron / protect_patron |
| 15 | regency | First disagreement recalls real patron/service choices; child's question vs adult objection | revise_contracts / uphold_contracts |
| 16 | can_prepare | Sign a binding future handover and disclosed territorial/military terms | sign_handover |
| 17 | restored_pair | Coronation/handover aftermath in AET, original Grover already moved | acknowledge_handover |
| 20 | can_union | Confirmed death and mourning, including memories if earlier guardianship | acknowledge_death |
| 21 | union_work | End dynastic guardianship, limited interim administration | accept_interim |
| 22 | union_work | Small county vs larger Herzland, constituent representation | delegates_equal / delegates_population |
| 23 | union_work | State union by consent of administered lands; Count's local title is not imperial succession | sign_union |
| 24 | union_work | Shared revenue, local budgets | revenues_local / revenues_central |
| 25 | union_work | Hereditary county and non-hereditary union presidency | succession_assembly / succession_council |
| 26 | can_finish_union | First winter budget and first real test of institutions | conclude_union |
| 27 | regency | Cost of an emperor: child offers personal jewel; adult offers estate income | gift_private / gift_public |
| 30 | crisis | Changed signature, forgotten promises; Grover if local else civic secretary | investigate_open / investigate_quiet |
| 31 | crisis | Locked audience: original CHN_trimmel is exposed; no assertion original Cloudet dead/alive | record_identity |
| 32 | can_hear | Public hearing: restore available real Count, otherwise civic council; or openly ratify Trimmel under binding restrictions | dismiss_impostor / ratify_trimmel |
| 33 | can_sign | Sign under one's own name, settlement/compensation; wording depends on outcome | settle_identity |
| 40 | always false | Retired foreign custody offer, retained only to close stale save windows safely | inert offer_custody / refuse_custody |
| 41 | active | Legacy receipt; no current gameplay dispatch | acknowledge_reply |
| 42 | active | Legacy receipt; no current gameplay dispatch | acknowledge_reply |

Event trigger names expand to HSM_AET_<predicate>. Event 40 trigger and options run in foreign host scope, FROM=AET; all others AET. Cost disclosures in tooltips must match effects. Public home budget costs 50 PP vs credit 25 PP; public court accounts 50 PP vs patrons 25 PP; patron judgement 75 PP vs protection +35 PP. Contract revision costs 100 PP after protecting the patron, otherwise 50 PP; upholding contracts gives 25 PP. Handover costs 50 PP; delegates/union constitutional choices 35 PP; death/interim/no-op acknowledgements are free; open investigation 25 PP vs quiet 10 PP; dismissal 50 PP vs ratification 75 PP; identity settlement 35 PP. Unaffordable options are hidden by native event triggers, so every paid internal event also offers free deferral with a summary of all alternatives and their costs. It preserves the unresolved choice for the existing retry schedule. No forced negative PP or automatic irreversible choice is introduced. Public trials retain the free dismissal alternative at insufficient funds.

Use original Count Cloudet and CHN_trimmel only when actually present. The impostor crisis is deterministic, starts on observed replacement, suspends legal ratification/handover, leaves domestic development playable. Two permanent outcomes: restore the actual available Count (otherwise a civic caretaker), or publicly ratify Trimmel as a constrained protector under his own identity. Choosing a quiet investigation increases later disclosure costs rather than hiding the crisis indefinitely. Grover's testimony or civic records refer to previous choices. No automatic killing, magic replacement or new character portrait.

## Territory and household

Only owned and fully controlled states in the existing fixed Herzland boundary qualify for the treaty. Griffenheim (382) is required for a territorial settlement; no requirement to conquer all 38 states. Original AET homeland 495/496 and Adelart are outside the transfer set. Preparatory relief is possible without custody. Regency requires the actual local Grover; a missing character is never created. Rescue from the dissolved imperial court requires absent GRI, actual capital possession, no living custodian and the original character still assigned to GRI. A living foreign regent does not surrender custody through diplomacy.

Native maturity date applies. Prepare focus finishes the main narrative before majority; daily reconciliation hands over only at peace with adult local original Grover, valid mandate, actual controlled territorial set, no live GRI and cleared impostor crisis. Restored GRI uses a peaceful reconstruction tree, exact owned-state transfer, a disclosed quarter of army/air/stockpile, never ships or officers. Independent alliance needs existing faction leader consent if AET is not faction leader. Permanent union cores are earned through actual programme; provisional regency cores are tracked and removed on handover/interruption. No claim to third-party lands. A sovereign household cannot be moved by a stale consent.

One consolidated dynamic national spirit derives bonuses from completed policy flags. Internal derived modifier values are not player resources: never spent, accumulated over time or displayed as progress meters. Recovery actions are discrete, no repeatable resource-grinding decisions. Triggers/effects must be covered by parsed-source scenario tests; engine playtesting remains a separate validation boundary.

## Final implementation details

The original AET trees each import the campaign and identity-crisis roots. Their native focus bodies are preserved. The native Grover protection predicates now also recognize real AET custody and AET-restored GRI; this preserves the existing event-entry and already-open-option protections. The two generic empire/Aquileia formation decisions are hidden only for original AET after choosing `AET_realpolitik`; anarchist and prelate routes keep their original rules.

The foreign shelter decision has been removed. Retired request/accept/refuse effect IDs are inert, and the old offer's predicate is always false. This protects a living foreign regent even if a previous save contains pending-request flags, a queued offer or an already-open acceptance option. Ordinary dossier review can locate Grover but cannot obtain him from another surviving court. Existing local custody is not retroactively undone.

The identity hearing has a free dismissal without compensation when the treasury cannot fund either paid settlement; postponing to fund ratification remains possible at any balance. Dismissal restores the real Count only if his original character remains available. Otherwise it installs a civic caretaker using an existing generic portrait. Public ratification renames the real `CHN_trimmel` to his own title and uses his existing native portrait. Quiet investigation incurs an additional stability loss at disclosure. Foreign ancestry is not the legal issue: impersonation, broken undertakings and unaccountable command are.

Regency relief may be closed explicitly, with a confirmation event. A locally present original Grover remains protected as a private guest even after closure. Interrupted mandates have a free, cooldown-bound dossier review; reopening does not replay completed education, factories or policy rewards. Confirmed death permits the obituary/union route even after the living branch has begun.

The independent restored GRI gets six peaceful focuses: oath, workshops, army accountability, schools, court debts and settlement. Existing AET faction membership is preserved. If another country leads that faction, the leader receives an explicit invitation request; refusal leaves reciprocal guarantees and military access without silently adding GRI to its alliance.

The release package on the Desktop and the Workshop item are not part of this source change. A development playtest must use this checkout's `mod/HoISubmod` path; verify the launcher's actual descriptor before testing.

## Review corrections, 2026-10-31

- Internal paid choices may always be postponed without costs, rewards or a policy flag. Existing queue timers dispatch another offer. The AI stops considering deferral once it can afford the most expensive settlement; this source weighting is not an observed AI campaign result.
- Refusing a mandate grants no stability. Reviewing and accepting it can no longer produce an extra reward for a temporary refusal.
- Protecting a patron and then reversing that protection costs 65 PP net, before its temporary daily penalty, compared with 50 PP for judgement followed by upholding the lawful contracts. Reversing earlier protection no longer reaches the same settled policy more cheaply. Judgement followed by further revision still costs more and grants a separate immediate stability increase.
- Restored GRI removes inherited `GRI_bureaucracy` through its first reconstruction focus. A daily repair removes it from older restored saves only if that focus is already complete; original GRI and unfinished restoration are unaffected.
- Actual handover earns AET permanent +10% production-efficiency cap and +5% research speed in its existing compact. Signing preparatory papers alone earns neither. Treaty-union completion earns neither. Maintenance recognises an already completed legitimate handover in older saves. Grover's native adulthood date remains unchanged; the reward is for fulfilling that deferred obligation, not an acceleration of his age.
- Refugee scenes distinguish confirmed death from unknown whereabouts. Interim union scenes distinguish a former regency from direct entry into the death route. Grover's restored biography and foreign dossier no longer invent childhood residence or a still-serving regent for an adult sovereign.
- Existing educational, military, judicial and Trimmel choices produce distinct restoration callbacks. Their constitutional destination remains shared; no continental conquest programme is added.
- Trimmel's exposure and constrained appointment have documentary evidence, institutional leverage and a motive for accepting the settlement. Union scenes express concrete disputes instead of repeatedly announcing that the Count is not an emperor.
- Requirements are concise status checks; native immediate rewards and explicit permanent bonuses remain outside narrative descriptions. Identity-crisis penalties and their removal are disclosed separately from immediate stability changes. EN/RU place names, political titles and awkward translations are reconciled.

The approved art, portraits and icon bindings are outside this correction pass.

Validation for this pass: 65 Greifwald, 42 Grover-compatibility and 13 formable
tests passed against the installed EaW reference; generated-source consistency
and the six AET localization files passed their checks. Art bindings have no
pending changes and the art-tree inventory matches the pre-edit audit. See
[test evidence](GREIFWALD_TESTS.md) for commands, scope and engine limitations.

## Engine acceptance pass

Source tests do not run the HOI4 event scheduler or render the focus tree. Use a separate test save with this checkout enabled:

1. Select pragmatic AET and check the new roots to the right of the native tree. `Letters without Reply` becomes available during the imperial crisis. Relief can begin before custody; the territorial congress requires peace, lawful government and ownership of Griffenheim after GRI ceases to exist.
2. Leave Grover with a living foreign custodian. No shelter-transfer decision should appear, and dossier review must not move him, including when that country is at war, capitulated or a subject. Any old offer left in a save must be inert. Separately verify rescue of the original character from absent GRI when AET owns Griffenheim and no living custodian exists.
3. Complete the living branch while Grover is a minor. Preparation must remain saved until his native majority date, peace and controlled territory permit handover. Confirm original AET homes remain AET, only its owned Herzland states pass to independent GRI, and GRI receives its six-focus reconstruction tree. If another country leads AET's alliance, that leader must receive the membership request.
4. Confirm Grover's death during an unfinished regency. Temporary cores and the mandate must be removed; the obituary and union continuation must remain available. A missing or foreign Grover without confirmed death must not open the union branch.
5. Install the actual Trimmel through the native branch. Ratification and handover must stop until investigation, hearing and signature are resolved. Check both restoring Cloudet and ratifying Trimmel, plus the civic-council fallback when Cloudet is absent. The latter must become the actual ruler, not merely receive a name change.
6. Inspect events, focus effects and decision tooltips at insufficient, fractional and ample political power. At the hearing, 50 PP must allow dismissal AND deferral to save for 75-PP ratification; 0 PP must allow deferral instead of forcing uncompensated dismissal. Patron revision must charge/show 100 PP after protection and 50 PP otherwise. Postponed offers must recover; repeated review/refusal must not farm stability. Keep an old closure window open while forming the union and verify that it cannot terminate the established state.
7. In restored GRI, verify that the first reconstruction focus previews and removes inherited bureaucracy. In a pre-update save where that focus was already completed, the daily repair should remove it without replaying the focus reward. A native GRI campaign must retain its usual bureaucracy progression.
8. Confirm that preparing a minor's future handover adds no production/research reward. Actual transfer adds the two compact components once; reopening the save and daily maintenance must not stack them. A completed pre-update handover should gain them even if relations with GRI have since deteriorated. The death-route union must not receive them.
9. Read the direct-to-union and former-guardian interim scenes, confirmed-dead refugee scene, adult arrival and foreign dossier. Compare the restored court's open/court education, army charter/contracts, judged/protected patron and Trimmel callbacks. Replace Grover before a pending restored-court event arrives: it must not narrate him still governing.

Foreign custody offers are retired. Alliance admission and mission closure retain conservative first options, matching native timeout behaviour. Exact affordability uses `NOT = { has_political_power < cost }`; no unsupported comparison operator or rounded-down spending threshold is needed.

## Source validation, 2026-10-27

- Greifwald after removal of diplomatic custody: all 51 tests pass. Retired diplomacy tests are replaced with foreign-guardian and old-save protection regressions. Full route execution covers the regency, union and Trimmel settlements; see `GREIFWALD_TESTS.md` for scope and limitations.
- Existing content: 102 base Verenia tests, 42 Grover tests and 13 formation tests pass.
- Generated-source check: seven files, zero stale outputs. Tracked diff whitespace check passes.
- Initial asset audit: all 28 placeholder sprites and three reused portrait paths resolved in the mod, EaW or the installed game. The later artwork pass replaces the added focus and national-spirit icons with 72 reviewed assets; portraits remain reused. Its dedicated validation checks all targets, hashes, alpha and native definition preservation.
- HOI4 UI rendering, automatic event timeout behaviour, AI campaign pacing and multiplayer remain engine playtest checks; the source harness does not claim to validate them.
