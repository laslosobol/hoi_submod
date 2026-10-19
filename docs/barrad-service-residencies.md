# Service Residencies and the Convoy Network

## Narrative Scope

Five regional investigations continue the already-authored residency openings in `hsm_bar_service.20` through `.24`. Zebrica has two paid stages and a source choice that changes its later account and reward. These are field investigations, corrected claims and limited scientific findings, not extra entries in the eighteen-object archive. They grant no custody, study flags, magical-containment knowledge, ruler captures or fabricated remains.

| Residency | Existing opening | Continuation |
| --- | --- | --- |
| Equus | Healer, incomplete circle, closed room | A blocked flue explains the illness. The resemblance between inscriptions remains unproven; choose consensual clinical publication or field inspection methods. |
| Griffonia | Erased accession, missing cabinet, carpenter | Humidity explains the noise; commercial records expose substitution. Choose casting research or preserve the acquisition trail. |
| North | Irma Kalk and a light across the water | Paired observations reproduce refraction. A night without weather records stays unresolved. Choose optical research or reconnaissance methods. |
| Riverlands | Compass deviation at a river bend | Reproducible readings identify iron carried aboard the ferry. Choose logistics research or instrument checks for field engineers. |
| Zebrica | A traveller described through an incomplete song | Fund the keeper/interpreter or independently check a dealer's transcription. The second investigation distinguishes an inherited duty and error-checking oral practice from an invented immortal and forged evidence. No object or body is conjured into existence. |

Local performers and correspondents retain permission over recordings and information. Commercial evidence can change the later trafficking scene but never gates that story behind completing the regional list. Public scientific exchanges are limited and anonymous where requested; they do not disclose the Service to a foreign government.

## The Returning Antagonist

The sole existing-event edit adds a tooltip and guarded `HSM_BAR_residencies_begin` call to each option of `hsm_bar_core.6`. The old rewards and `HSM_BAR_cult_channel_retained` remain intact. The daily pulse also discovers an already-finished ending in an existing save.

1. **Retained intermediary / closed channel:** separate investigations cost 40 PP / 28 days or 50 PP / 35 days. A live channel yields different intelligence and risk; the closed route uses records and consenting contacts without bringing the retired witness back.
2. **Second consignment:** after a 30-day interval, spend 50 PP and 35 days on a documented commercial dispute. Choose impoundment or controlled movement of an inert substitute. There is no unknown object or prisoner in the replacement crate.
3. **Replacement supplier:** after a further 60-day interval, spend 35 PP and 28 days checking the next approach. A source deliberately left exposed receives the promised withdrawal; otherwise the witnesses remain out of contact. Choose protective closure or a funded replacement watch.
4. **Periodic review:** initially available 180 days after the settlement. Further reviews cost 25 PP and 21 days, with a 180-day cooldown from activation. They revise the current protective/watch policy without replaying research awards, reviving the old source or stacking benefits. Cancellation still consumes the paid review and its interval.

The cell returns through new intermediaries; it is not depicted as a canonical worldwide hierarchy. A matched invocation and specific documentary evidence connect these perpetrators to the earlier Maar-affiliated cell. Fraudulent antiques, ordinary dealers and different religious practices are not automatically treated as evidence of cult membership.

## Effects and Lifecycle

- Four single-stage regional assignments cost 25-30 PP and 28-35 days. Zebrica costs 35 PP / 28 days followed by 40 PP / 42 days. Regional results choose a single-use 50% research coupon or a modest persistent method; Zebrica's first interview gives no reward by itself.
- Persistent results are recomputed in the separate `HSM_BAR_residencies_methods` modifier, using `GFX_idea_HSM_BAR_dir_world`. The art builder owns that sprite's registration. No new currency, secrecy meter or global resource exists. Regional contributions remain when the antagonist policy changes.
- The retained-source intelligence bonus temporarily includes +5% own-operative capture chance with La Resistance. Final settlement removes that risk and **replaces**, rather than adds to, earlier antagonist contributions. Closed-channel investigation has no such live-source risk.
- Final paid watch: daily PP -0.03, network gain +5% and operation outcome +5% with La Resistance; without it, reconnaissance +2%. Protective closure: supply use -1%, agency defence +1 with La Resistance; without it, reconnaissance +1%. Regional methods are additional and separately bounded.
- All starts, full-duration completions and event choices revalidate the actor. Cancellation clears running markers, grants no result and does not refund the native decision cost. Ordinary cancelled assignments can be paid for and attempted again; they are not `fire_only_once` traps.
- Ready reports survive suspension, but pending delivery markers and active work are cleared. Returning Service access can reissue an unanswered completed report, never complete an aborted investigation. Research coupons and mutually exclusive choices are once-only. Dynamic tooltips select the actual DLC/source result.
- Actor: BAR/original BAR, active Directorate and founded Service, not Collegium, independent, not capitulated, owns and controls state 624. Regional assignments additionally require their existing residency-opening flag and the concluded opening conversation. No random foreign ruler or global war condition is introduced.

## Integration Ownership

The component uses new `HSM_BAR_residencies.txt` files under scripted triggers/effects, decisions/categories, dynamic modifiers, on-actions and events, with new EN/RU localization, `tools/Test-BarradResidencies.cjs` and this document. Existing-file edits are the four-line addition across the two event-6 options in `events/HSM_BAR_core.txt` and a guarded teardown hook in `common/scripted_effects/HSM_BAR_core_effects.txt`. No archive, operation, focus, graphic, research-project or normalization file was edited.

`HSM_BAR_residencies_pulse = yes` runs through this component's `on_daily_BAR`; its own `on_capitulation` tears down derived state. `HSM_BAR_dissolve_institutions` now calls `HSM_BAR_residencies_teardown` when either `HSM_BAR_residencies_initialized` or the original `HSM_BAR_residencies_started` marker exists. Every successful assignment start sets the initialization flag, covering regional work before the convoy ending. Failed starts do not initialize anything. The MTC project teardown remains the first statement; residency cleanup precedes clearing the shared route flags. Do not add another daily pulse.

Teardown is idempotent: remove the component modifier, zero derived variables, cancel running assignments and clear pending deliveries. Concluded findings, source choices, report-ready flags and already-earned research coupons remain intact. It neither clears shared Service flags nor overwrites another module's variables. EN/RU prose describes the investigation; costs, reward replacement and replay rules remain in dedicated tooltips.

## Evidence and Verification

These investigations, suppliers, outcomes and scientific applications are **authored extensions**, not claims about pre-existing canonical objects. Their precise narrative starting points are the submod's `localisation/english/HSM_BAR_service_story_l_english.yml` keys `.20.d` through `.24.d`, and `HSM_BAR_core_l_english.yml` keys `hsm_bar_core.4.d` through `.6.d`. The installed EaW `localisation/english/country_GRI_l_english.yml:330` (`imperial.128.d`) establishes Maarites as a named religious group; it does **not** establish this invented trafficking organisation. Angriver accusations and April Fools content were not treated as evidence of its activities.

Native modifier names are checked against installed HOI4 `documentation/modifiers_documentation.md`; technology categories against installed EaW `common/technology_tags/00_technology.txt`. The flag-age contract is documented in `documentation/triggers_documentation.md` under `has_country_flag`; actual less-than use is in native `common/scripted_triggers/BUL_scripted_triggers.txt:142`.

Checks are deterministic execution of the actual scripts, not an engine playtest:

- `node tools/Test-BarradResidencies.cjs --native`: 122 passed, 0 failed, including guarded dissolution before the convoy ending, preserved MTC-first order, all eleven assignments under eleven revoked actor conditions, cancellation and modifier enable/remove predicates.
- `node tools/Test-BarradServiceRewards.cjs`: 195 passed, 0 failed.
- `node tools/Test-BarradPhases.cjs`: 53 groups passed, 0 failed.
- `node tools/Test-BarradDevelopment.cjs`: 92 passed, 0 failed.
- `node tools/Test-BarradCollegiumProjects.cjs`: 1391 passed, 0 failed.
- `node tools/Test-BarradCivic.cjs`: 101 passed, 0 failed.
- `node tools/Test-BarradCollegiumFrontiers.cjs`: 83 passed, 0 failed.
- `node tools/Test-BarradServiceStory.cjs`: 37 groups passed, 0 failed.
- `node tools/Test-BarradCases.cjs`: 26 passed, 0 failed; the existing anomaly progression remains unchanged.
- `node tools/Test-BarradArchive.cjs`: 44 groups passed, 0 failed; eighteen cases and disclosure boundaries preserved.
- `pwsh -NoProfile -File tools/Test-BarradContent.ps1`: 325 passed, 0 failed after art integration. The earlier missing-sprite diagnostic was resolved by registering `GFX_idea_HSM_BAR_art_collegium` and `GFX_idea_HSM_BAR_dir_world`, not by suppressing validation.

Remaining verification: native decision timing/cancellation and repeated-review UI. The integrated regression results are recorded in [the readiness pass](barrad-readiness-pass.md).
