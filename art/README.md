# Cyanolisia art sources

The PNGs in `art/source` are the generated high-resolution sources. The game
loads the TGA exports under `mod/HoISubmod/gfx`. All eleven images were generated
with the built-in image generation tool, then resized with
`tools/Convert-ToHoi4Tga.ps1`.

## Prompt set

- `cya_directorate_flag.png`: Flat 82:52 fictional Cyanolisian Directorate
  flag; iron-charcoal field, old-gold cross inherited from Cyanolisia, crimson
  shield at the crossing, simplified ivory griffon wing and talon. No text,
  folds, pole, border, or real-world political emblems. The export composites
  the generated image over opaque `#17191b`.
- `evi_governorate_codes.png`: HOI4-style transparent focus icon of an
  iron-bound military law ledger, crimson griffon-wing seal, Evi valley maps,
  antique gold and charcoal.
- `countess_regency_for_grover.png`: Transparent focus icon of Grover's small
  golden coronet on a blue-and-ivory regency charter, protected by a white
  griffon wing. The Countess safeguards the crown rather than claiming it.
- `question_of_grover.png`: Transparent focus icon of a golden crown on dark
  iron balance scales, with a blue royal charter and a red sealed military
  decree in the pans.
- `one_griffonia_under_the_crown.png`: Transparent focus icon of a golden
  imperial crown above a united Griffonian map, white wings and blue ribbon;
  lawful unification for Grover VI.
- `one_griffonia_under_claw.png`: Transparent focus icon of an armored griffon
  talon gripping an imperial crown over a map, with crimson military pennants;
  Dawnclaw's command of united Griffonia.
- `countess_union_mandate.png`: Transparent focus icon of three provincial
  charters with blue seals beneath a protective white griffon wing and compass;
  the Countess's lawful mandate to unite Griffonia.
- `imperial_interregnum.png`: Transparent focus icon of an empty iron throne,
  crimson banner, map, and marshal's baton; Dawnclaw's post-Grover interregnum.
- `cya_industrial_program.png`: Transparent national spirit icon with an iron
  cog, railway wheel, foundry chimney, and rails for the industrial programme.
- `cya_military_program.png`: Transparent national spirit icon with a griffon
  shield, crossed officer batons, and crimson command pennant for the military
  programme.
- `cya_imperial_legitimacy.png`: Transparent national spirit icon with a
  provincial charter, griffon-wing wax seal, and judicial balance. It avoids
  Grover's portrait and crown.

All icon prompts requested one centered, hand-painted grand-strategy emblem,
transparent background, clear silhouette at 99x86, and no lettering or frame.
The three national spirit prompts requested the same treatment at 64x64.
The Grover regency spirit reuses `countess_regency_for_grover.png` at 64x64.

Example export:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Convert-ToHoi4Tga.ps1 -Source art/source/evi_governorate_codes.png -Destination mod/HoISubmod/gfx/interface/goals/HSM_CYA_evi_governorate_codes.tga -Width 99 -Height 86
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Convert-ToHoi4Tga.ps1 -Source art/source/cya_imperial_legitimacy.png -Destination mod/HoISubmod/gfx/interface/ideas/cya_imperial_legitimacy.tga -Width 64 -Height 64
```
