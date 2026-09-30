# Cyanolisian Secondary Paths

## Frontier March

The Countess retains political authority; Dawnclaw becomes a contained military
adviser. Training, supply, reconnaissance, entrenchment and administration improve
the three national programmes. The route does not require continental conquest.

- Opening the outback softens the harsh recruitment restriction; recognised
  councils remove exceptional minority penalties without replacing better rights.
- District reserves and market roads lead to a budget choice between civilian
  development and a professional defensive army.
- Market roads or the Evi embassies unlock offers to MIT, SIC, GRW, BRF, GRY and
  LUS. Acceptance creates a non-aggression pact and trade opinion, not annexation.
- Blackhollow receives an optional subordination offer. Refusal allows a war goal.
  If another state holds its territory, a county-specific war goal targets
  the actual owner, excluding our subjects and faction partners.
- County garrisons and the autonomy statute require ownership and control of
  states 490, 606, 489 and 532 by CYA or its subjects. The civil or military
  settlement modifies programmes through the event choice.
- The peaceful March finale does not depend on conquering Blackhollow.

## Imperial Administration

Available after refusing Dawnclaw asylum, dismissing him, or his assassination.
The cabinet restores the Countess's neutral government and retains the shared
programmes. Procurement and administrative reforms no longer impose permanent
micro-ideas or restore suppressed-minority policy.

The continuation covers civil-service training, freight administration, a common
service charter and a choice of imperial correspondence or technical exchange.
These reforms work even if no imperial household ever arrives. The existing
decision to join a neighbouring GRI faction remains separate from the exile plot.

## The Court in Exile

This is a new alternate-history extension, not a claim about a canonical flight.
Only the Administration can open it, by completing `HSM_CYA_safe_harbour`.

Eligibility is deliberately conservative:

1. CYA is independent, has not capitulated, and is led by the Countess.
2. Grover is alive, below majority on 1021.5.21, has not reigned elsewhere, and
   still belongs to the defeated GRI court. Dawnclaw is not at the host court.
3. GRI is annexed or capitulated. Its actual surviving ruler is Eros VII or
   Gabriela Eagleclaw, still present as a character. Eros's death flag is checked.
4. Another country owns and controls Griffenheim and has declared imperial
   succession. It does not already hold Grover or his childhood spirit.
5. Bronzehill and known pending Angriver/Greifenmarschen/Yale custody or execution routes are
   excluded, rather than pre-empting their EaW events.

The daily hook schedules an offer after fourteen days. Eligibility is checked
again by the event, its acceptance option and the transfer effect. Refusal closes
the offer. Acceptance transfers the original characters from GRI, removes the
old court's childhood spirit, gives it to CYA and costs 50 PP. There are no copied
characters, cleared death flags, automatic wars or changes of CYA's ruler.

The regent supervises Grover's household; the Countess governs Cyanolisia.
`HSM_CYA_court_in_exile` establishes their division of responsibilities.
`HSM_CYA_exile_restoration_staff` unlocks a decision for a capital-specific war
goal against its actual owner, excluding our subjects and faction partners.

At majority, `HSM_CYA_exile_coronation` requires local custody, independence and
peace, not reconquest. Its event switches the ruling ideology to neutrality and
promotes the original Grover as constitutional monarch. The Countess transfers
authority; no puppet-Grover alternative is offered on this route. A ceremony
interrupted after opening can be resumed through a decision.

## Source Boundaries and Verification

- `EaW/common/characters/GRI.txt`: Eros and Grover character identities.
- `EaW/common/national_focus/GRI.txt`: Gabriela's transfer and the Eros regency.
- `EaW/events/Grover_Events.txt`, events `grover.32/.35/.40/.41`: executions
  and successor custody transfers; not overridden by this extension.
- `EaW/common/decisions/griffon_decisions.txt`: successor flags and those events.
- `EaW/events/Yale.txt`, events `yale.770/.88/.103/.104/.135`: additional
  custody and execution chains reserved for their base-mod routes.
- `EaW/events/GriffonianEmpire Events.txt`: regency and adult Grover precedents.
- `EaW/events/CrystalEmpire.txt`: diplomatic non-aggression effect syntax.

Regression scenarios are in `tools/Test-CyanolisiaFocusFlow.ps1`; narrative,
localization and script checks are in `tools/Test-CyanolisiaNarrative.ps1`.
They do not replace an in-game campaign, character-transfer or queued-event test.
All eleven new focuses have dedicated PNG sources, 99x86 TGA exports and
standard/shine sprites. Source and native-size visual checks passed; their
manifest rows are DONE. In-game verification remains pending. Historical
approvals of other assets are unchanged; prompts are in
`art/secondary-paths-icon-prompts.md`.
