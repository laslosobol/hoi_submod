# Cyanolisian Regional Campaigns

## Source Basis

- `EaW/common/national_focus/GRI.txt`: `GRI_strike_north` -> northern political settlement -> `GRI_core_the_north`; `GRI_strike_west` -> trade cities/oil fields -> `GRI_core_west`; southern rubber and frontier ports follow the first wave of reintegration.
- `EaW/common/national_focus/BRZ.txt`: `BRZ_annex_wingbardy`, `BRZ_secure_the_southern_coast`, and `BRZ_the_southern_integration` distinguish military objectives, regional development and post-war administration.
- `EaW/history/countries`: FAT capital 485, AVI 470, JER 377, WNG 371 and GRU 512 anchor local construction. Western oil states 493/494 and southern rubber states 371/373 follow GRI's corresponding development focuses.

## Implemented Sequence

Both marriage outcomes now have three waves, while Grover's separate coronation chronology remains unchanged:

1. Northern, central/lake and western campaigns, each followed by a 28-35-day local reconstruction and integration focus.
2. Western reconstruction unlocks the southern campaign; lake reconstruction independently unlocks the Griffonian Frontier. Neither waits for the entire first wave. Karthin's workshops/rubber and Gryphus's port/eastern roads follow territorial control.
3. The reconstructed Frontier unlocks separate Riverlands and Beorgfordas campaigns. The eastern settlement uses existing imperial commissariats, not pony cores. The final continental focus still rechecks ownership and control of all relevant territory.

The Countess emphasises courts, contracts and civilian reconstruction; Dawnclaw emphasises garrisons, arsenals and supply. The 14 added focuses use existing custom art selected for those roles. No additional national spirits are created. Variable changes remain visible in event options; regional core-eligibility lists have compact localized summaries.

Campaigns bypass only when their original territories are actually held by us or our subjects. War goals follow current owners, including third-party conquerors, rather than only surviving original tags. Reconstruction does not bypass, so its development and integration rewards remain obtainable after an earlier conquest. Local integration uses EaW's original-core/compliance mechanism, never instant cores; Asterion and pony countries are excluded.

## Institutions and Peace

- Events 54-56 resolve the northern, lake and western settlements. Each route has two exclusive choices per region, recorded permanently and recalled in Grover's council. A focus no longer grants its old automatic modifier bundle before the player chooses.
- Event 53 now lets a ruling Grover guarantee charters, establish civilian oversight of the staff, or prioritize provincial recovery. Earlier institutions and lessons grant conditional benefits, but no schooling flag is required to select a policy. The existing Kaiv, Midoria and Gryphus callbacks remain.
- Event 57 gives the puppet emperor either a civilian petition office or staff-supervised audiences. It does not change the ruler.
- Three 30-day, 50-PP commissions follow actual unification: demobilization (58), reconstruction (59), and the distribution of authority (60). War or lost control cancels a commission. An open event can be deferred if conditions change; pending and completed choices prevent duplicate rewards.
- The final settlement distinguishes living, puppet and dead Grover. The Countess's duty to transfer power is unchanged. Succession statutes do not recruit a fictional heir or replace the current ruler.

The eight late regional/circuit/finale focuses on each route retain local construction/resources and integration, but no longer stack unconditional national percentages. For example, this removes cumulative +12% core attack and -10% supply consumption from Dawnclaw's eight rewards, and +8% compliance growth from the Countess's. Alternatives are finite research grants, army experience and mutually exclusive institutional choices. These are sums of the affected rewards, not claims about the complete campaign's final stats; the earlier development tree and initial program values are unchanged.

## Changed Borders

The imperial settlement decision category provides seven regional claim renewals (35 PP, 90-day cooldown) after their campaigns, plus a continental renewal after both circuits (50 PP). They retarget current owners, allowing recovery from third-party annexation or a subject's later independence. Existing war goals, our subjects and current enemies are skipped.

An independent ally owning Griffonian territory may receive a voluntary subject-status proposal (75 PP, 180-day target cooldown). Event 61 rechecks peace, independence and the alliance before acceptance; refusal transfers nothing. Faction leaders cannot accept while leading the alliance. These decisions do not bypass truces or permit war against current allies: refusal still requires normal diplomatic changes before military action. The compact grants no cores and does not replace pony commissariat decisions.

## Blackhollow

The override now uses the exact dependency path `common/decisions/CYA_decisions.txt`. Only `CYA_blackhollow_republic` changes: it is hidden, unavailable and cancelled on the marriage or imperial-administration route, with a guarded completion effect for already-running decisions. All other base decisions are preserved. The former duplicate `HSM_CYA_blackhollow_override.txt` is removed.

## Verification

Run with PowerShell 7.2+ on Windows:

```powershell
pwsh -NoProfile -File tools/Test-CyanolisiaFocusFlow.ps1
pwsh -NoProfile -File tools/Test-CyanolisiaNarrative.ps1
pwsh -NoProfile -File tools/Update-CyanolisiaIconManifest.ps1 -Check
pwsh -NoProfile -File tools/Update-CyanolisiaSpiritManifest.ps1 -Check
```

These are static and fixture-based checks, not an in-game playthrough. Test both political outcomes, changed territorial owners, allied acceptance/refusal, the pony commissariats, and cancellation/restart of the peace commissions in game. New event text and the updated focus connectors also need an in-game visual check.
