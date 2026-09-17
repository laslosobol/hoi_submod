# Cyanolisia Dawnclaw Path Skeleton

This submod currently wires the Dawnclaw content through events and decisions to avoid overriding the upstream `CYA.txt` focus tree. Future focus files can call the same flags, events, and ideas listed here.

## Shared Entry

Existing hook:

```text
GRI completes GRI_industry_modern / Die Kleine Sauberung
If Dawnclaw does not become GRI leader, CYA gets hsm_cyanolisia.1
```

Accepting asylum recruits and auto-appoints `HSM_CYA_ferdinand_dawnclaw`.

## Route 1: Blackrock County / Defensive Advisor

Flag:

```text
HSM_CYA_path_blackrock_county
```

Core content:

```text
HSM_CYA_blackrock_county_policy
HSM_CYA_form_blackrock_county
HSM_CYA_prepare_border_claims
HSM_CYA_integrate_minotaur_outback
```

Focus skeleton:

```text
Hide The Fugitive
The Blackrock Plan
Fortify Against Minotauria
Watch Sicameon
Defensive Victory Claims
The County Of Blackrock
Native Minotaur Settlement
```

## Route 2: Marriage / Court Power Struggle

Flag:

```text
HSM_CYA_path_marriage
```

Power variables:

```text
HSM_CYA_dawnclaw_dominance
HSM_CYA_countess_dominance
```

Dominance flags:

```text
HSM_CYA_dawnclaw_dominant
HSM_CYA_countess_dominant
```

Focus skeleton:

```text
An Unlikely Marriage
Two Signatures, One Court
Security To The Colonel
The Countess' Civil Cabinet
Outback Policing
Outback Integration
The Revealed Exile
The Hidden Assistant
The Countess Alone
The Colonel's Household
```

Dawnclaw dominance reveals his presence to the Empire and gives stronger military/internal-security content. Countess dominance keeps his presence hidden for longer and leans into industry and integrative minotaur policy.

## Route 3: Imperial Administration

Flag:

```text
HSM_CYA_path_imperial_administration
```

This route is used if Dawnclaw is assassinated or if the player chooses the low-content administrative fallback. It should be short, bureaucratic, and security-focused.

Focus skeleton:

```text
Seal The Room
Imperial Papers, Cyanolisian Hands
Quiet Administrative Reform
No More Foreign Guests
```

## Assassination / Hiding Loop

Decision:

```text
HSM_CYA_maintain_dawnclaw_cover
```

Important flags:

```text
HSM_CYA_dawnclaw_identity_secured
HSM_CYA_dawnclaw_revealed_to_empire
HSM_CYA_dawnclaw_dead
```

If his identity is not secured or is revealed, `hsm_cyanolisia.10` can fire and force the player to spend political power or lose him.
