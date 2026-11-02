# Greifwald art register

72 distinct generated icons for the working Greifwald content:

| Scope | Count | Export |
| --- | ---: | --- |
| Added AET campaign and Trimmel focuses | 25 | 99x86 RGBA TGA |
| Added restored-GRI reconstruction focuses | 6 | 99x86 RGBA TGA |
| Native AET national spirits | 38 | 64x64 RGBA TGA |
| New restored-GRI national spirits | 2 | 64x64 RGBA TGA |
| Consolidated AET dynamic national spirit | 1 | 64x64 RGBA TGA |

Native focus art, portraits, advisors and companies are outside this artwork
change. The Desktop release package and Workshop upload are also unchanged.

## Sources and review

Each asset was generated individually with the native imagegen tool.
`generation/<id>.json` retains the exact prompt, output path and revision history;
rejected earlier revisions are not exported. `source/` contains byte-identical
copies of accepted original PNGs. `manifest.json` maps them to game targets,
textures and sprites, including source/export SHA256 hashes and visual approval.
`briefs.json` is the complete target inventory; `native-spirit-briefs.json`
records native descriptions and semantic references used for the spirit art.

Five contact sheets in `previews/` show all exports at native size and 3x on dark
and light backgrounds. Main and independent visual reviews covered all 72 icons.
Corrections removed an invented shield crest, a malformed book illustration and
a fleur-de-lis architectural detail. Earlier opaque scene generations were
rejected and regenerated as isolated transparent icons. The closed-audience,
hearing and black-banner icons intentionally retain darker materials; their
fine details should be checked against the actual game background.

The mechanical export trims only fully transparent margins, fits the result
inside the native size with a two-pixel inset, and writes uncompressed 32-bit
RGBA TGA. It does not remove backgrounds, repaint, recolor or sharpen artwork.

## Palette and heraldry

The references in `reference/` are lossless conversions of the existing game
flags. Greifwald uses charcoal, ivory and cobalt, with natural material colors
and selective brass. Its existing diamond device is not replaced with an
invented griffon or lily. Most icons depict objects with plain seals and shields
rather than introducing new national arms.

Restored imperial icons use ivory, orange-red cloth and pointed gold coronets,
without Aquileian lilies. Native Aquileian military-advisor cloth follows the
blue-white-red palette without assigning a specific royal emblem. Anarchist
spirits use black cloth; Maar-related spirits use violet, blackened iron and
silver; changeling subjects use teal, silver and charcoal. Economic subjects
retain wood, wheat, stone and machinery colors. Gold is an accent or real metal
material, not a uniform tint across the set.

## Binding and validation

`tools/Bind-GreifwaldArt.py` binds only reviewed, hash-matched assets and writes
the dedicated `mod/HoISubmod/interface/HSM_AET_art.gfx`, including focus shine
sprites. The native `zzz_AET_ideas.txt` override changes only the approved
picture fields. Stats, conditions and effects are preserved. The campaign
builder reads the same approved manifest for its generated icon fields, so
rebuilding does not restore placeholder sprites.

```text
python -B -X utf8 tools/Prepare-GreifwaldArt.py
python -B -X utf8 tools/Bind-GreifwaldArt.py --check
python -B -X utf8 tools/Test-GreifwaldArt.py --check
python -B -X utf8 tools/Build-Greifwald.py --check
python -B -X utf8 tools/Test-Greifwald.py --eaw EaW
```

Art checks cover all 72 targets, hashes, image dimensions, alpha, sprite
collisions and unchanged native gameplay definitions. Source checks and contact
sheets do not render the HOI4 UI; an engine appearance check remains pending.

Final source run, 2026-10-30: all 72 assets/targets pass the art validator;
all 51 Greifwald scenario tests pass; all seven builder outputs are current.
The read-only preparation audit preserves all 72 visual approvals. The binder's
13 isolated fixture tests passed during tool preparation; the exporter approval
persistence regression also passed after fixing serialization of validated rows.
