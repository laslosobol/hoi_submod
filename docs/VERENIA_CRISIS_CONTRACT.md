# Verenia: Neighbours Through the Avian Crisis

## Scope

Finish the agreed regional integration, not new technocrat/Foundation campaign trees. Native Second Winterfest Ball still requires both Houses to be Avian subjects. An independent House may witness a queued crisis after independence; the equal-union path does not acquire a new compulsory coup. Existing native annexation of actual Avian subjects is retained. Independent Houses cannot be annexed by the coup.

Sources: installed EaW `common/national_focus/AVI.txt` (`pursue_true_neutrality`, `the_second_winterfest_ball`, `permit_local_elections`, `foundation_allowed`); `events/Avian Events.txt` (`avian.10` through `.19`, `.24`); `localisation/english/country_AVI_l_english.yml` (matching descriptions). The source establishes the violent ball, three competing factions, loyalist liberalisation, and the separate isolation/Foundation route. Border hospitals, negotiations, correspondence and their aftermath are new authored scenes, not asserted canon.

## Story and Mechanics

- Native `avian.10` opens a seven-day response for existing, non-capitulated Houses that are independent or actual Avian subjects. The first native battle follows fourteen days after Avian acknowledges the attack, leaving response time in multiplayer. The subsequent native sequence remains intact; the only winner-selection addition resolves newly possible highest-score loyalist ties when actual House aid caused them.
- Emergency hospital assistance costs 25 PP and supplies a temporary recovery spirit to Avian. Support for the lawful government costs 40 PP and contributes exactly one point per House to the existing native `loyalist_effort`, not a new meter. Guarding one's own territory is free. No divisions are deleted or moved.
- Military/technocrat victory keeps the native treatment of actual subjects. Independent Houses receive a regime-specific demand (`hsm_verenia.95`): defend sovereignty, seek a civilian border compact, or explicitly accept suzerainty when both sides are at peace and faction conditions permit it. Refusal itself never declares war.
- Loyalist victory acknowledges the Houses' earlier conduct. Independent Houses can propose a limited compact; subjects receive an aftermath without free independence. The later native election receives a separate response, not restoration of an aristocratic ruler.
- True neutrality sends a letter to each House: respect the distance, or negotiate limited civilian transit without a military union. Foundation admission generates its own border consequence; no secret Foundation information is given to neighbouring rulers.
- A proposed compact costs 35 PP once per attempt. Avian explicitly accepts/refuses in a separate event. It creates no faction, subject, territorial transfer or core. Acceptance grants a non-aggression pact and civilian cooperation (+10% infrastructure construction, +5% factory output) while the signed arrangement remains valid. It does not restore the old three-House charter.
- Each House has its own pending offer, government snapshot, 90-day retry guard and consent. Offers expire after 30 days with a 45-day flag fallback. Event windows are 13 days, shorter than the retry interval. Capitulation pauses signed benefits; bilateral war, subjugation, annexation or a change of Avian political route/ruler invalidates the compact. Subsequent talks require a new signature. The diplomatic non-aggression pact remains governed by normal engine rules; a pre-existing pact is never removed by these scripts.
- A sixty-day settlement report, or a later independent-border ending after refusing supremacy, closes the personal/regional story. These are narrative consequences, not repeated reward dispensers.
- Native integration is still available by actual consent: AI treaty signatories retain nonzero acceptance weight, explicit post-ball AI plans favour it, and a 35 PP diplomatic retry can send a new offer after 90 days. Free deferral is the first/default response; neither silence nor the absence of a previous treaty counts as consent. Acceptance is revalidated before both the recipient's answer and Avian's application of subject status.
- No new numerical meters, focus art, country-history edits, Barrad/Cyanolisia changes or workbook edits.

## Files and Validation

Implementation lives in `HSM_VER_crisis.txt` under events, scripted effects/triggers, on actions, ideas and decisions/categories, together with scoped native hooks, the expanded `hsm_verenia.95`, and existing diplomacy invitation guards. Prefix `HSM_VER_CR_`, namespace `hsm_ver_crisis`. This completion stage adds 15 events (one hidden deadline), two diplomatic retry decisions and three spirits; it does not add filler focuses or new artwork.

`localisation/{english,russian}/HSM_VER_crisis_l_*.yml` contains 156 matching keys per language with UTF-8 BOM. After the engine-compatibility repair below, `tools/Test-VereniaCrisis.py` passes 85 tests, including all 243 allocations of native battle choices and zero/one/two House contributions. Native coronation capital/faction guards are checked structurally; the scenario interpreter does not emulate that whole native event. Hospital assistance cannot extend an already running emergency programme, and signing a civilian compact cannot reissue an existing non-aggression pact.

## Engine Parse Repair (2026-10-23)

The supplied HOI4 `logs/error.log`, around lines 500-555, reported five invalid `political_power` triggers, one invalid `non_aggression_pact` effect, and parser failures beginning at `avian.18` lines 860-861. The following `country_event`/`option` errors were downstream of the malformed comparisons, not evidence that event keywords themselves were unsupported.

- Replaced all five PP predicates in the crisis triggers, effects and event options with `has_political_power`. Existing thresholds, 25/40/35 PP costs and effect-side revalidation remain unchanged.
- Replaced the compact's pact effect with `diplomatic_relation = { country = AVI relation = non_aggression_pact active = yes }`. The existing `has_non_aggression_pact_with` guard still prevents reissuing an existing pact. The suggested `create_non_aggression_pact` was not found in installed engine documentation or the inspected installed game/EaW scripts; it was not introduced as another unverified alias.
- Replaced both `loyalist_effort >= ...` shorthand comparisons in `avian.18` with `NOT = { check_variable = { loyalist_effort < ... } }`. Inclusive highest-score tie handling still requires a started crisis and actual House aid; strict native winners are unchanged.

Verified local references, under `C:/shit/Steam/steamapps/common/Hearts of Iron IV`:

- `documentation/triggers_documentation.md:4547`: `has_political_power`, country scope.
- `documentation/triggers_documentation.md:2110`: `check_variable`; documented shorthand uses `=`, `>` and `<`. Inclusive comparison is available through the long-form `compare = greater_than_or_equals`, not an inline `>=` token.
- `documentation/effects_documentation.md:3564`: `diplomatic_relation` with `country`, `relation`, `active`.
- `common/scripted_effects/DEN_scripted_effects.txt:2577`: native non-aggression-pact creation using that block.
- Installed EaW `common/scripted_effects/EAW_WNG_effect.txt:42`: the same pact-creation form.

The previous 75 tests were falsely green for these errors because the fixture explicitly accepted the bogus PP/pact commands and unsupported shorthand operators. The fixture now models the documented commands and rejects those aliases. Seven new independent source/documentation tests inspect all four owned script files, including unexecuted branches, and mutate corrected code back to the invalid forms to prove rejection. Three additional fixture regressions reject the old commands/operators and verify negated less-than equality semantics. This is a bounded guard for the reported keyword/comparison families, not full engine validation.

Verified command: `python -B -X utf8 tools/Test-VereniaCrisis.py -q` (85 tests, passed). No new HOI4 launch or clean post-fix engine log was obtained in this repair; that runtime check remains outstanding. No force/main-diplomacy, CYA or GOY files were changed by this repair.

## Verification Boundary

Parsed source scenarios must cover both Houses independently, every native route, subject/independent/third-party-subject status, replay, dropped events, obsolete replies, concurrent negotiations, war, annexation, occupation, democracy after loyalist victory, and invalidation/re-negotiation. Runtime presentation, native event scheduling, AI pacing, saves and campaign balance still require an actual game playtest; source checks are not that playtest.
