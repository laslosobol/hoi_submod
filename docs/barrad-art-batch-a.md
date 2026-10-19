# Barrad Service Art Batch A

Completed 2026-10-01. Scope: first 17 internal icons in `art/barrad-service-art-brief.md`, charter through riverlands. Built-in image generation only: 17 individual new assets and 3 targeted edits. No CLI/API fallback.

## Deliverables

- Source pattern: `art/source/HSM_BAR_dir_<suffix>.png`.
- Runtime pattern: `mod/HoISubmod/gfx/interface/goals/HSM_BAR_dir_<suffix>.tga`.
- Reviewed contact sheet: `art/previews/HSM_BAR_batch_a_99x86.png`, assembled from decoded final TGA pixels at native 99x86, not resized source previews.
- Material reference only: `art/source/HSM_CYA_crown_in_trust.png`. Its royal subjects and heraldry were not reused.
- No focus scripts, GFX definitions, CYA manifests or other workers' assets changed.

## Review

"Reviewed" means source and native-size export visually inspected; it is not an in-game rendering test or a manifest approval operation.

| ID | PNG dimensions | Fully transparent source pixels | Status | Actual review notes |
|---|---|---:|---|---|
| `HSM_BAR_dir_charter` | 1345x1169 | 32.30% | Reviewed | Dossier, crossed key and compass seal; inventory and redactions populated. |
| `HSM_BAR_dir_names` | 1345x1169 | 35.50% | Reviewed | Layered ledgers have ink rows and coded tabs; clearly different from the charter. |
| `HSM_BAR_dir_seal_labs` | 1346x1169 | 35.63% | Reviewed | Stone entrance, lamp and measured survey; no magical forcefield. |
| `HSM_BAR_dir_watchmen` | 1345x1169 | 38.59% | Reviewed | Three envelopes, engraved seals and lens; no human anatomy. |
| `HSM_BAR_dir_evidence` | 1345x1169 | 33.84% | Reviewed | Faceted specimen vial in numbered cradle; populated custody tags. |
| `HSM_BAR_dir_training` | 1345x1169 | 24.19% | Reviewed | Tongs, sealed chest, goggles and evacuation diagram; no hands. |
| `HSM_BAR_dir_register` | 1345x1169 | 30.24% | Reviewed | Three drawers with populated index cards; repaired empty labels to 01/02/03. |
| `HSM_BAR_dir_radio` | 1345x1169 | 27.01% | Reviewed | Radio, cipher rotor and punched tape retain a distinct mechanical silhouette. |
| `HSM_BAR_dir_archives` | 1345x1169 | 29.14% | Reviewed | Scorched notebook and lens show conflicting annotated measurements. |
| `HSM_BAR_dir_agency` | 1345x1169 | 32.68% | Reviewed | Repaired blank doorplate with engraved mercantile compass mark; hidden lock retained. |
| `HSM_BAR_dir_storage` | 1345x1169 | 23.87% | Reviewed | Physical vault and padded compartments; no magical containment imagery. |
| `HSM_BAR_dir_foreign_mandate` | 1345x1169 | 39.93% | Reviewed | Repaired abstract continent shapes to a plain meridian globe with five route pins; no Earth geography. |
| `HSM_BAR_dir_world` | 1345x1169 | 38.83% | Reviewed | Exactly five telegraph terminals and central lockbox; no globe or map. |
| `HSM_BAR_dir_equus` | 1345x1169 | 42.55% | Reviewed | Unflagged steamer inside compass ring; evidence prism and sealed pouch. |
| `HSM_BAR_dir_griffonia` | 1345x1169 | 29.53% | Reviewed | Broken archaeological griffon relief, not a national coat of arms; excavation grid. |
| `HSM_BAR_dir_north` | 1345x1169 | 32.91% | Reviewed | Snow-dusted lantern, schematic pass survey and numbered sample tube. |
| `HSM_BAR_dir_riverlands` | 1345x1169 | 30.81% | Reviewed | Survey wheel, optical level and measured river chart; no recognizable Earth geography. |

## Technical Checks

All 17 PNGs decoded successfully: valid PNG signature, 8-bit RGBA (IHDR type 6), nonblank bodies, genuine alpha background and antialiased edges. All 17 TGAs passed header/payload/alpha checks: 99x86, uncompressed type 2, 32-bit BGRA, 8 alpha bits, bottom-origin, 34,074 bytes each. Every exported TGA corner has alpha 0.

Generated alpha was preserved. Most body pixels are nearly opaque rather than exactly 255; the body check counts alpha >=245, with separate checks for fully transparent background and intermediate edge pixels. Riverlands has one source corner pixel at alpha 1; it is absent from the TGA (all four export corners alpha 0). No opaque background rectangle, visible corner residue, human hands, arbitrary fleurs-de-lis or flag symbols found during visual review.

Three explicit repairs were completed and rechecked: numbered the register's originally empty drawer labels; populated the agency's originally blank company plate; removed every continent silhouette from the foreign-mandate globe, leaving meridians and schematic routes. The final contact sheet was rebuilt after these edits.

## Prompt Set

Subjects are the first 17 entries of the finalized art brief. Shared generation direction: one isolated hand-painted HOI4 miniature per call; charcoal iron, antique brass, muted teal, warm ivory and restrained crimson; crisp focal silhouette legible at 99x86; genuine transparent background; no floor or rectangular backdrop, human anatomy, arbitrary heraldry, fleur-de-lis, flags, logos or watermarks. Populate documents with inventory rows, survey diagrams or measured annotations. Use the reference only for material and paint finish, never its crown, throne or royal subject.

Final regional constraints: no Earth geography; foreign mandate uses a plain meridian globe with five pins and schematic route arcs; Equus uses an unflagged ship miniature; Griffonia uses an archaeological fragment, not a coat of arms; north and riverlands use local schematic survey marks.

Export command used for each final source (PowerShell 7):

```powershell
pwsh -NoProfile -File tools/Convert-ToHoi4Tga.ps1 -Source art/source/HSM_BAR_dir_<suffix>.png -Destination mod/HoISubmod/gfx/interface/goals/HSM_BAR_dir_<suffix>.tga -Width 99 -Height 86
```

GFX/shine registration and full-game integration are the parent task's responsibility. No commit performed.

