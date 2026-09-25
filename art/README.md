# Cyanolisia art sources

The PNGs in `art/source` are the generated high-resolution sources. The game
loads the TGA exports under `mod/HoISubmod/gfx`. All six images were generated
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

All icon prompts requested one centered, hand-painted grand-strategy emblem,
transparent background, clear silhouette at 99x86, and no lettering or frame.

Example export:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Convert-ToHoi4Tga.ps1 -Source art/source/evi_governorate_codes.png -Destination mod/HoISubmod/gfx/interface/goals/HSM_CYA_evi_governorate_codes.tga -Width 99 -Height 86
```
