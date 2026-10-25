# The Verenian Regency: Erie and Eyrie

This replaces Erie's imported civilian Griffenheim continuation with a shared, route-aware Grover campaign in both ducal trees. Legacy imperial files remain for existing saves and Avian dependencies; they no longer form Erie's visible continuation. Avian's own limited settlement and Zypressen campaign are unchanged.

## Narrative Contract

Four remembered entry routes: Erie/diplomacy (a bilingual, accountable court), Erie/war (a ward among the victors), Eyrie/diplomacy (lawful succession without restoring old abuses), Eyrie/war (the limits of military tutelage). Original EaW anchors remain the equal ducal claims, the rulers' stubbornness, and Grover V's childhood under self-interested regents. New scenes are authored continuation, not upstream canon.

Education, a petition against our own supporters, and military arrangements leave distinct memories. Both military and diplomatic routes ultimately restore an independent allied Empire, not a puppet or a personal union. A minor has a guardian; an adult who arrives late or awaits a safe handover is treated as an adult. No new visible numerical resource exists.

## Entry and Custody

- Original ERI/EYR, the original ruling duke, independent unified Verenia, five controlled ducal home states, peace, and full ownership/control of the 38-state Herzland boundary.
- GRI must not exist. This is a factual postwar territorial settlement, not invented proof of a past defensive war. Older qualifying saves do not need retrospective victory flags.
- Only the original `GRI_emperor_grover_vi` counts. Confirmed death takes precedence over residual character assignment. A living foreign host is never overwritten or solicited by this programme.
- The household file can recover the character from annexed GRI only if no living country has him and all Herzland is genuinely held. Missing assignment is unknown, not presumed death or permission to create another Grover.
- A free, cooldown-bound household review can reconsider changed circumstances. Dead/foreign/unknown cases have a separate civilian ending; interrupted guardianship has an explicit closure decision. The host can also voluntarily decline the mandate while Grover is alive locally: he remains a protected private guest, and that choice permanently closes the regency branch. No civilian ending invents a monarch or annexes a foreign court.

## Territory and Succession

The fixed 38-state boundary is shared with the audited Zypressen Herzland snapshot. It excludes all six Verenian states. Capital-region registration and district registration mark only newly added ERI/EYR cores with separate state provenance flags. Existing cores are never marked. Loss of custody, death, political overthrow or a separately restored GRI ends the mandate and removes programme cores, even on subsequently lost territory.

While the mandate operates, `HSM_VER_REGENCY` retains Verenia's established flag and map colour, with its own name. Two factories (or capped-state research alternatives) are built in the actual Verenian homes 391 and 401, so reconstruction is not all lost at handover.

The last focus prepares succession without requiring 1021. Adulthood follows native `date > 1021.5.21`; guardianship benefits end then, even during war or unfinished preparations. The actual handover waits for completed articles, the prepared crown, peace, living local adult Grover, the legitimate government, and full territorial control. Occupation never transfers an enemy-owned state. No existing GRI government is overwritten.

The handover is one-shot and deliberately does not use `release = GRI`:

1. Mark the restored GRI before country creation; transfer exactly the host's 38 Herzland states. Old imperial cores elsewhere cannot select extra land.
2. Remove only the host's provenance-marked programme cores. Retain every pre-existing host core and all territory outside the fixed boundary.
3. Ensure GRI independence, move the original character, set his adult portrait and constitutional-monarch role, inherit the custodian's technology, and load `HSM_VER_GRO_restored_empire` rather than the old reclamation tree.
4. Join the existing alliance without moving its members, or create the agreed new alliance. Transfer a disclosed quarter of land formations, aircraft and equipment stockpile; no ships or officers. This is a treaty share, not a claim to identify soldiers' ethnic origins.
5. GRI renounces cores/claims and standard conquest goals against the three Houses. The host returns to the shared Verenian cosmetic and its original ducal capital. Grover's policy memories remain in the restored Empire.
6. Bilateral economic and defence institutions require an actual independent allied partnership. Their Verenian contributions are included in the existing unified national spirit; GRI uses ordinary ideas. Breaking the relationship cancels the benefits.

## Restrictions and Presentation

Generic Empire succession is blocked only for ERI/EYR. Aquileia formation is blocked only for ERI/AVI, irrespective of cosmetic identity. Other countries and the Avian Zypressen imperial route are preserved. Exact upstream deltas are documented separately in `VERENIA_FORMABLES.md`.

Narrative descriptions contain no reward lists. Requirements use concise named tooltips, effects expose costs and the eventual independent handover, and no new icons are generated. Russian and English are paired. Regent naming reuses the established Verenian flag at all three sizes.

## Verification Boundary

See `VERENIA_GROVER_TESTS.md` for parsed-source scenarios and `VERENIA_GROVER_UPSTREAM.md` for the native event-chain audit. These are not a game-engine playthrough. Before release test a fresh ERI and EYR campaign, both routes, a late-adult entry, an unavailable household, an ongoing war at majority, save/reload, and actual army/stockpile transfers. Inspect event portrait/name rendering, no duplicate childhood chain, faction membership, state ownership/core removal, and the restored GRI focus tree.
