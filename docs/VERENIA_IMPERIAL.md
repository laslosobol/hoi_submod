# Verenia: Optional Griffenheim Settlement

Legacy contract: the 2026-10-24 Grover revision replaces the ERI tree import with
`HSM_VER_GRO_open_court` and adds the same route-aware campaign to EYR. See
`VERENIA_GROVER.md`. The definitions below remain for old save/event references
and the Avian shared predicates; they are not the new ducal campaign.

## Integration

Include `shared_focus = HSM_VER_IMP_settlement` in the new ERI tree. It is already present in `mod/HoISubmod/common/national_focus/HSM_ERI.txt` at implementation review. Root position is absolute x=48, y=0. All eight focuses use absolute x=46, 48 or 50; y=0..4. This is a separate far-right branch, beyond both mutually-exclusive regional routes. No ordinary development or diplomatic focus depends on it; its actual defensive/postwar requirements are unchanged.

Required existing interfaces:

- `HSM_VER_charter_signed` on each actually consenting ERI/EYR/AVI participant.
- `HSM_VER_union_established` on ERI after implementing common institutions.
- `HSM_VER_charter_valid` from `common/scripted_triggers/HSM_VER_diplomacy.txt`. This live check is deliberately required: historical ERI signatures cannot substitute for an existing, independent, non-capitulated EYR with a valid bilateral treaty.
- `HSM_VER_charter_suspended`, when present, excludes a participant and invalidates ERI's institutions. This extension never sets or clears external charter flags.

No additional events, decisions or effects need to be called by the main branch. The extension installs its own declaration, capitulation, uncapitulation, peace-conference and ERI daily hooks. Existing saves without recorded provenance cannot backfill eligibility from occupation or ownership.

## Exact Entry Predicates

1. `on_declare_war`: ROOT must have both `tag = GRI` and `original_tag = GRI`; FROM must be an existing original ERI/EYR/AVI with its own charter signature and no suspension. ERI must also be an actual signatory. The union need not yet be completed when attacked. Joining another aggressor's war does not create a record.
2. The declaring GRI receives `HSM_VER_IMP_recorded_aggressor`, the direct victim receives `HSM_VER_IMP_attacked_signatory`, and ERI receives `HSM_VER_IMP_defensive_war_recorded`. A new qualifying declaration clears old defeat/peace certificates. A charter member's subsequent declaration against original GRI also clears old defeat/peace certificates.
3. `on_capitulation_immediate`: ROOT must be that original GRI with the aggressor record. ERI must still be a signatory, have the recorded declaration, and have a defensive war against ROOT with no offensive war against it. At least one recorded victim must also still be a signatory defending against ROOT with no offensive war against it. FROM, the victor, must defend against ROOT with no offensive war against it, and be ERI or fighting alongside ERI. This sets ERI's `HSM_VER_IMP_defeat_recorded`.
4. `on_uncapitulation` clears ERI's defeat/peace certificates if original GRI recovers while still at war with ERI. Daily cleanup clears stale victim records after their defensive war ends. A separate peace by ERI without a certified conference clears its defeat certificate. When no recorded victim or ERI remains at war, unresolved declaration/defeat provenance is discarded.
5. `on_peaceconference_ended`: ROOT must be original ERI, FROM must be original GRI with its aggressor record, and ERI must have both the declaration and defeat certificates. Neither side may have EaW's `bypass_on_peaceconference_ended` flag. This sets `HSM_VER_IMP_peace_recorded`. A conference involving a different winner or loser cannot substitute.
6. At entry, acceptance, all focus completions and active-mandate checks: ERI exists, is independent, has not capitulated, has no war, has its charter signature, has implemented the union, has no charter suspension, and passes the main `HSM_VER_charter_valid` check.
7. ERI must both own and control state 382 (Griffenheim). Occupation without ownership, subject ownership/control, faction membership or owning some other capital never suffices. Original GRI must be nonexistent or at peace. Every surviving actual charter signatory must be at peace and not capitulated.

These deliberately conservative checks require an actual capitulation followed by a certified peace. A white peace or an unsupported scripted victory without those native hooks does not qualify. No speculative fallback manufactures victory records.

## Content and Outcomes

| Focus | Position | Result |
| --- | --- | --- |
| HSM_VER_IMP_settlement | 24,0 | Event .1: accept or decline the optional civilian mandate |
| HSM_VER_IMP_household_record | 22,1 | Event .2: six evidence/age-specific Grover descriptions and acknowledgements |
| HSM_VER_IMP_city_contracts | 26,1 | Event .3: one civilian factory and slot in owned Griffenheim, or two 75% construction research bonuses; capped city falls back to one 100% industry bonus |
| HSM_VER_IMP_open_archives | 22,2 | Two 50% industry research bonuses after the household record |
| HSM_VER_IMP_technical_agreement | 26,2 | Event .4 invites only eligible independent EYR/AVI signatories; consent is checked again on acceptance |
| HSM_VER_IMP_public_accounts | 24,3 | Event .5 publishes the audit; both final choices unlock even with no foreign signature |
| HSM_VER_IMP_last_year | 22,4 | Mutually exclusive final 365-day programme, then automatic civilian legacy |
| HSM_VER_IMP_return_the_keys | 26,4 | Immediate civilian handover and legacy, with event .6 after 30 days |

The initial mandate costs 50 PP and provides +30% repair speed at -0.10 daily PP for at most 730 days. The final programme replaces it, costs another 50 PP and provides +50% repair speed, +3% research speed and -0.20 daily PP for exactly one additional 365-day authorization. There is no renewal loop. At successful expiry it is replaced by the two-year civilian legacy: +2% research speed and +5% production efficiency gain.

Immediate handover removes the mandate, returns 75 PP, adds 2% stability and grants that same two-year civilian legacy immediately. These are administrative choices, not territorial releases or transfers. At most one reconstruction idea is present at a time.

An unreviewed initial mandate expires without the completion legacy. Loss of peace, actual Griffenheim control/ownership, or live charter institutions interrupts either mandate without a completion reward. The ERI daily check closes it once and selects the appropriate event .6 epilogue. Already earned factories/research are retained. The final-year, voluntary-handover, interrupted and unreviewed-expiry epilogues are distinct.

The separate technical protocol provides +2% research speed and +5% production efficiency gain for 730 days to each consenting partner and ERI. A second acceptance cannot refresh ERI's timer. Its idea explicitly uses `cancel = { NOT = { HSM_VER_IMP_protocol_valid = yes } }`; the trigger checks live institutions, consent, independence and peace. Losing EYR invalidates the main bilateral charter and therefore cancels ERI's and AVI's protocol benefits as well. Cancelled benefits are not automatically regranted. Refusal has no penalty and does not alter charter membership.

## Grover and Custody

This implementation is intentionally noncustodial. It does not transfer, recruit, generate, retire, promote, rename or change portraits of any character, add imperial offices, grant titles, appoint a regent, change CYA flags, or call native household-transfer effects. It never infers custody from the capital. Local presence describes only an already-existing character assignment, not a new grant of authority.

Inspected native references: `events/Grover_Events.txt` (especially grover.32/.35/.40/.41/.42), `events/GriffonianEmpire Events.txt`, `common/characters/GRI.txt`, and `common/scripted_triggers/EAW_GRI_scripted_triggers.txt`. Inspected HSM helpers: `HSM_CYA_displaced_court_available`, `HSM_CYA_grover_in_our_custody`, `HSM_CYA_grover_reigns_anywhere`, `HSM_CYA_grover_reigns_abroad`, and `HSM_CYA_grover_household_can_transfer`. CYA helpers depend on their own route/ROOT/host contracts; none is repurposed to authorize ERI custody.

- `GRI_grover_vi_dead` is authoritative and overrides residual character presence.
- Living local minor: ERI already has `GRI_emperor_grover_vi`, no death flag, and not `date > 1021.5.21`. Existing household arrangements are acknowledged; no new guardianship is granted.
- Living local adult: same existing character/no-death proof and `date > 1021.5.21`, matching native succession timing. The text explicitly rejects a new regency.
- Living foreign minor/adult: an existing foreign country has that exact character, ERI does not, and no death flag exists. Separate age-specific texts defer to the existing host. CYA is treated as any other actual host and remains untouched.
- Unknown: no confirmed death and no proven living host in an existing country. A character still assigned to an annexed country is insufficient proof. The text does not declare death, invent custody or restore a person.

No host-consent flow or real regency is claimed. This is a finished reconstruction/diplomatic fallback, not an unimplemented promise of later dynastic content.

## Owned Files and Flags

All implementation files are named `HSM_VER_imperial.txt` under `mod/HoISubmod/common/national_focus`, `scripted_triggers`, `scripted_effects`, `on_actions`, `ideas`, and `mod/HoISubmod/events`. Localization sources are `mod/HoISubmod/localisation/english/HSM_VER_imperial_l_english.yml` and `mod/HoISubmod/localisation/russian/HSM_VER_imperial_l_russian.yml`, both UTF-8 BOM, with 70 matching keys. No icon assets, base AVI overrides, CYA files or main diplomacy files are changed by this extension.

All written flags use the `HSM_VER_IMP_` prefix. Provenance flags are listed above. ERI's lifecycle flags are `offer_resolved`, `settlement_declined`, `mandate_active`, timed `mandate_deadline`, `fate_recorded`, `contracts_awarded`, `protocol_offered`, `audit_published`, `final_choice`, `mandate_extended`, `mandate_ended`, `voluntary_handover`, `programme_finished`, `mandate_interrupted`, `mandate_lapsed`, and `epilogue_delivered`. Protocol participants use `protocol_answered` and `protocol_signed`. There are no new global flags, campaign counters, territorial goals or persistent variables.

## Validation

Passed 20 focused checks against the actual parsed scripts, including positive and rejected war provenance, historical-signature/live-EYR regression, idea cancellation, six mutually exclusive Grover descriptions/options, stale invitations and construction choices, mandate replacement/expiry/interruption and reward idempotence. Both localization files passed BOM, syntax, key parity and reference coverage. All used focus/event/idea art tokens exist in installed EaW or vanilla assets. The four modifier tokens were checked against installed `documentation/modifiers_documentation.md`; construction, timed ideas, research, state-slot and war-scope tokens against installed docs/base examples.

This is static and modeled script validation, not an HOI4 engine playthrough. No game was launched. Native on-action firing order, focus rendering and save/load behaviour still require a live game smoke test. The model fails on unsupported predicates rather than assuming them true; it does not simulate the engine's scheduler or national-focus UI.

## Regression Suite

Run from the repository root with PowerShell 7.2 or later:

```powershell
pwsh -NoProfile -File tools/Test-VereniaImperial.ps1
```

The suite parses the actual scripts and reuses the existing Clausewitz parser from the Cyanolisia focus-flow tools. It models only the predicates and effects used by this package; it is not an HOI4 runtime emulator.

