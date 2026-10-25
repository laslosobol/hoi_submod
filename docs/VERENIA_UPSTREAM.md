# Verenia Upstream Overrides

Source: installed EaW at `C:/shit/Steam/steamapps/workshop/content/394360/1826643372`, copied on 2026-10-21. These are complete same-path overrides under `mod/HoISubmod`, not additional definitions. Native definition IDs, coordinates and icons are preserved. The deliberate prerequisite/mutual-exclusion changes for the second Winterfest are listed below. The initial Avian tree imports constitutional preparation, common institutional unification and optional Herzland settlement. Only the fascist tree imports the Zypressen continuation.

Original SHA-256 hashes:

- `common/national_focus/AVI.txt`: `30ccdb5161b675e977154aaaa5e3e4b0bbf6b1fde86c9e7b240bf7a47cf7d04d`
- `events/Avian Events.txt`: `63a0555c31dcff18bccf569989aa2a2448958a34b4c5a610837723ab36ea06c1`
- `common/decisions/ERI_decisions.txt`: `7782c99318b718eacd01d5d3342a68bfacb98d4d88d199475af983423891dc2b`

## Shared Verenian Cosmetic (2026-10-24)

`common/countries/cosmetic.txt` is an additional same-path override copied from the installed EaW version on 2026-10-24. Original SHA-256: `a845fa3a1f996b77cae290f678bcc06b940be3118c975da118bfec177f1294b8`. All upstream entries are preserved; only `HSM_VER_UNIFIED` is appended, with map and UI colour `rgb { 62 137 124 }`. Rebase this file when EaW changes its cosmetic colours; do not replace it with a file containing only our entry.

The common unification effect assigns this cosmetic to ERI, EYR or AVI without changing the actual country tag, government or ruler. EN/RU localisation supplies the shared name Verenia for all four ideologies, and `gfx/flags/` supplies the base cosmetic flag in normal, medium and small sizes. Source and generation provenance are in `art/source/HSM_VER_UNIFIED.png` and `art/verenia-flag-prompt.txt`.

On the existing daily maintenance hook, a living House with `HSM_VER_UNI_founded` and one of the old `HSM_VER_UNI_ERI/EYR/AVI` cosmetics receives the shared cosmetic. Other identities, including later imperial cosmetics, are not overwritten. Existing saves therefore migrate on the next game day after loading the updated mod. The legacy name keys remain available for compatibility.

`tools/Test-VereniaUnification.py` checks all three founders, migration and replay, exclusion of unrelated identities, preservation of every upstream colour entry, both localisation files and the three opaque TGA exports. These are static and scoped-script checks, not an engine-rendering test.

## Exact Deltas

The 2026-10-24 unified-spirit revision routes permanent native Intergigantes idea grants, swaps and relevant checks through `HSM_VER_SP_*`. The original recipients and pre-union values are unchanged; an already-founded recipient stores the component in the common national spirit. Later communist/fascist replacement ideas use the same routing. Economic-market and military-exercise previews name all recipients but show their identical effects once. The 70-day scientific exchange remains an ordinary timed idea. `zzz_AVI_ideas.txt` is read by the generator/test tooling as a coefficient source, not overridden; after an EaW update run `Build-VereniaSpirit.py --check` and audit any changed native values before regenerating. Advisor/designer, research-sharing and one-shot rewards are not converted.

The 2026-10-23 route repair also supplies explicit `value = 1` for the two HSM-owned block-form flags added to `events/Avian Events.txt`. Native flag assignments are unchanged. All Verenia block-form assignments now receive the same structural check in `tools/Test-VereniaFlags.py`; a missing value must not be silently accepted by the script fixture.

`common/decisions/ERI_decisions.txt`:

- `ERI_border_skirmish` and `EYR_border_skirmish`: new availability and completion guards require the rival to exist, invalid negotiated peace, and neither side's treaty/armistice flag. Either side's flag blocks a race during agreement updates.
- `ERI_create_wargoal`: equivalent availability guards; `remove_effect` rechecks the rival's existence, different tag, no bilateral war, treaty/armistice protection, the initiator's independence, rivalry idea, no existing goal, and no `had_war_with_rival` before the unchanged 50/50 war-goal roll.
- Those three decisions retain the old `ending_the_rivalry` visibility restriction outside an active ERI campaign. During that campaign, flags determine whether an offer became binding. The rivalry idea remains required; no effect restores it. Timeouts and `ERI_white_peace` are unchanged.

`common/national_focus/AVI.txt`:

- Only the initial `avian` tree imports `HSM_AVI_three_separate_seals`, `HSM_VER_UNI_convention` and `HSM_VER_REG_after_defence`. Only `avian_fascists` imports `HSM_ZYP_victory_roll`. The other three trees retain their original imports. New branches live in separate `HSM_VER_*.txt` files; original imports remain unchanged.
- `full_integration` no longer excludes the HSM root or dispatches `avian.5`. Its original prerequisites, cost, coordinates and icon remain; completion now opens the constitutional campaign without changing another country's autonomy.
- `the_second_winterfest_ball` reciprocally excludes `HSM_AVI_three_separate_seals`. Its prerequisites are `(tripartite_legion OR technological_cooperation) AND (leaders_field_marshalls OR unified_railroad_network)`, so the original crisis remains accessible without the obsolete puppet shortcut. Its native reward remains. Constitutional and crisis routes cannot both be selected normally.
- `ending_the_rivalry`: calls `HSM_VER_offer_armistice` in AVI scope when ERI's campaign is active or either House has signed the treaty. Otherwise its original peace/truce effects remain.
- `treaty_of_friendship`: the same branch calls `HSM_VER_offer_treaty` in AVI scope. Rivalry removal, core concessions, truce, opinions, and the original news remain in the legacy branch; the shared accepted-treaty effect owns negotiated settlement. The 25 PP reward remains.
- `annual_hunting_trip`, `weekly_luncheons`, `winterfest_ball`, `scion_swap`, and `treaty_of_friendship`: during the active campaign, availability requires either both existing Houses' armistice flags or valid negotiated peace, plus the original no-war checks.
- `the_intergigantes_tripartite`, `unified_intelligence_agency`, `annual_military_exercises`, `unified_railroad_network`, `technological_cooperation`, and `full_integration`: active-campaign availability additionally requires valid negotiated peace. Original faction and other restrictions remain.
- No new puppet-integration requests or premature integration news are sent by `full_integration`. Queued legacy requests require the shared native-integration context, which rejects a completed constitutional root.
- `the_intergigantes_tripartite` does not replace an existing foreign faction. It can bypass when all three consenting charter partners already share a military alliance.

`events/Avian Events.txt`:

- `avian.1/.2`: preserve an existing faction and recheck independence, AVI leadership, bilateral peace and recipient faction membership before accepting. An existing faction member is never transferred to another faction by the invitation. Treaty signatories may decline without the legacy PP punishment.
- `avian.5`: retains the old acceptance/refusal options and rewards. Treaty or charter signatories receive `HSM_VER_keep_equal_union`, with no PP/opinion penalty or subjugation response. Acceptance retains nonzero AI weight for signatories, increased for explicit native post-ball AI plans. A free first/default deferral option prevents silence from becoming submission. A 90-day retry guard and a separate AVI decision permit renewed proposals without compulsory consent. The event requires a live independent recipient, completed native integration and no incompatible Avian route.
- Accepting records a 45-day local consent flag `HSM_VER_avian_vassalisation_accepted`; refusal or keeping equality clears it. `avian.6` rechecks both parties exist, remain independent and have not capitulated, the sender is not at war with AVI, and the old Avian government is still eligible. All recipients need explicit unexpired consent before integrated-puppet status. The response consumes the flag; absence of a treaty is not inferred consent.
- `avian.15` and `avian.17`: each House is annexed, and its ruler retired, only inside its own `exists = yes` / `is_subject_of = AVI` branch. Existing independent Houses instead call `HSM_VER_avian_crisis_response` in their own ERI/EYR scope, regardless of membership. Other overlords' subjects are untouched.
- Coup faction cleanup requires AVI leadership, `faction_template_AVI_INTERGIGANTES_FACTION`, and no other surviving faction members. The installed faction documentation and rules confirm `has_faction_template` support.
- `avian.10` dispatches a one-time seven-day emergency response to eligible Houses. Its first battle is delayed fourteen days and queued only once. Medical aid and support for the lawful government have distinct costs and consequences. `avian.15/.16/.17` record the outcome and initiate the aftermath. Military/technocrat victory descriptions no longer claim control or execution of surviving foreign Houses. Actual Avian subjects retain their native annexation outcome.
- `avian.18` preserves native victory selection; when House aid creates a highest-score tie involving loyalists, their additional support resolves it in their favour. The inclusive comparisons use `NOT = { check_variable = { loyalist_effort < ... } }`, not unsupported inline `>=` tokens. No other faction is denied a strict victory, and there is no new meter.
- `avian.20` moves the capital to state 391 only when Avian actually owns and controls it. It creates the dynastic faction only outside an existing faction, preserving surviving independent partners' alliance. These guards matter when a queued coup resolves after a House has become independent; normal incorporation of both subjects still permits the native outcome.

## Shared Interfaces And Verification

External hooks: country-scope trigger `HSM_VER_negotiated_peace_valid`; AVI-scope effects `HSM_VER_offer_armistice` and `HSM_VER_offer_treaty`; ERI/EYR-scope effect `HSM_VER_avian_crisis_response`. Shared flags read: `HSM_VER_campaign_active` on ERI, `HSM_VER_armistice` and `HSM_VER_treaty_signed` on the Houses, and `HSM_VER_charter_signed` on the offer recipient. These overrides never grant treaty or charter signatures.

New localisation key: `HSM_VER_keep_equal_union` (main agent supplies localisation). The consent flag is internal to `avian.5/.6` and needs no localisation. The main agent's `HSM_VER_start_campaign` adopts completed base `treaty_of_friendship` while both Houses are free and at peace; no override reintroduces rivalry or infers a charter from friendship.

Replay boundaries: these overrides add no repeatable focuses or new counters. A House can contribute one point to the existing native loyalist effort only once during the emergency. Keeping equality awards nothing, and a signatory's vassalisation response consumes its consent. The main charter effects reject already-signed offers and consumed ratifications. Native friendship is imported once when ERI's campaign starts, except after a recorded treaty breach.

`tripartite_legion` and `leaders_field_marshalls` retain their subject prerequisites. The second Winterfest has the separate alternate prerequisites above, preserving the native political crisis without requiring the constitutional union to recreate vassalisation. Its exclusion with the HSM root prevents the new regional campaign from silently unlocking a coup. Event guards continue to protect independent Houses from queued/directly fired annexation scenes.

Initial override review passed 501 assertions in a temporary scoped harness before final integration. The permanent `tools/Test-Verenia.py` suite now covers the integrated definition inventory, native focus metadata with the explicit integration exclusion, equal-status option, live vassalisation consent, faction invitations, border-skirmish guards, localization and replay/retry logic. `tools/Test-VereniaAvian.py` checks the new root's tree boundaries and branch behaviour. These suites check script structure and modeled conditions, not the game engine. A game load/error-log check and accepted/refused mediation, legacy friendship adoption and queued-coup playtests remain necessary. Rebase these three overrides against future installed EaW updates using the hashes above.

## Confirmed Parser Repair (2026-10-23)

The supplied engine log exposed a false green in the original crisis fixtures: they accepted `political_power`, `non_aggression_pact` and shorthand `>=` despite engine errors. The only native-file change in this repair is the pair of inclusive loyalist comparisons in `avian.18`; IDs, other options and native event ordering are untouched. Crisis-local predicates now use documented `has_political_power`; the compact uses `diplomatic_relation` with `relation = non_aggression_pact`, as in installed vanilla and EaW. `create_non_aggression_pact` has no entry in the installed effects documentation and was not substituted without evidence.

`tools/Test-VereniaCrisis.py` now passes 85 tests. Its added engine-contract checks read the installed trigger/effect documentation independently of the scenario interpreter, inspect the complete owned source files, and reject mutations recreating the logged errors. Existing 243 battle/aid combinations still pass. Full references, repair scope and verification limitations are recorded in `VERENIA_CRISIS_CONTRACT.md`. A fresh engine launch/error-log check is still required; these tests do not certify an error-free game load. The original upstream hashes above remain unchanged because this repair does not update the source baseline.
