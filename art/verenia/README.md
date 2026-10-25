# Verenian Art Register

This register covers ERI, EYR, AVI and their shared Verenian content only.
Cyanolisia and Barrad are outside this register's scope. Batch 01 generation used
the built-in imagegen tool, one asset per call. Its exact prompts are in
`batch-01.json`; later batches have their own `batch-XX.json` manifests.

## Batch 01: Integrated, Runtime Check Pending

| Target | Source | Game use |
| --- | --- | --- |
| Duke Vincent Erie | vincent-v2.png | 156x210 leader, 65x67 advisor |
| Duke Iovinus Eyrie | iovinus-v3.png | 156x210 leader, 65x67 advisor |
| Lady Katrina Avian | katrina-v2.png | 156x210 leader |
| Trubach von Zypressen | trubach-v2.png | 156x210 commander, 65x67 advisor |
| Three Houses Corporation | corporation.png | 64x64 industrial concern |
| One Verenian State | union-v2.png | 99x86 focus, standard and shine sprites |
| The Verenian Regency | regency.png | 99x86 focus, standard and shine sprites |
| United Verenia | spirit.png | 64x64 unified dynamic national spirit |

Eight distinct assets, eleven game textures. Unique native portrait/company
texture paths are overridden without replacing character definitions or generic
portraits. No stats, prerequisites, effects or company availability changed.
The unified spirit generator now owns the new sprite reference.

Source and native-size visual review passed. Transparent exterior checked;
exports are uncompressed 32-bit RGBA TGA. `batch-01-native-preview.png` displays
exports at their actual sizes. `batch-01-hashes.json` records source/export SHA256.
No game session was launched and runtime appearance is not yet verified.

## Heraldry

References are lossless PNG conversions of existing game flags and portraits.
ERI: ivory crescent and bird on a dark field. EYR: golden bird and disc on blue.
AVI: white-edged red cross on blue, with its native central shield.
Unified Verenia: emerald field, gold-edged ivory band, red shield with an ivory
left-facing rampant winged griffon, three gold six-point stars, no crown.
Unification and spirit art preserve that heraldic composition. Portraits use
plain backgrounds so no invented arms are introduced. The corporation uses
industrial apparatus, not a new national coat of arms. The regency uses an
empty throne, key and hourglass, not a claim to Grover's crown.

## Rejected / Unused Sources

The earlier unversioned vincent, iovinus, katrina, grover_adult, charter and
unification PNGs are NOT integrated: heraldic/identity review remains failed or
pending. Earlier trubach.png is also unused; batch 01 uses trubach-v2.png.
iovinus-v2.png is rejected because the generator mistook a background flag
element for a crest; iovinus-v3.png removes it. Reference PNGs are never exports.

## Remaining Work

All scheduled artwork has been generated and visually reviewed. Consult
`progress.json` for reconciled integration counts, completed batches, pending
original and native-spirit brief IDs, unintegrated records and any active blockers.
In-game appearance and runtime reconciliation remain unverified.
Manufacturer, generated-advisor and MIO coverage is recorded separately there.
The batch 01 section above is a historical record, not the current completion
summary.

Use each `batch-XX.json` manifest and its `batch-XX-hashes.json` baseline for the
batch's sources, exports and review evidence. Manifest presence alone does not
prove integration: progress counts require approval, matching hashes and live
bindings. Reconcile with `tools/Update-VereniaArtProgress.py --apply`, then verify
with `--check`. These counts do not replace visual review or in-game checks.

Use 8-12 targets per batch with semantic review first. Do not substitute one
generic image for an entire branch or count existing EaW artwork as new art.
Keep balance changes separate. Newly generated portraits must preserve known
identity; no invented state insignia, human hands, arbitrary crowns or lilies.

## Expanded Artwork Pass

The built-in image generator has now been used for all scheduled targets.
Successful sources are reviewed individually and again at their native game
sizes. Exact prompts and approvals are retained in batches 01-64,
`company-exports.json`, `company-neutral-exports.json`, `mio-exports.json`, and
`generated-advisors-01.json` through `generated-advisors-03.json`.
`generated-advisor-art-prompts.json` contains the full 30-template prompt set.

The new standard-advisor portraits use plain clothing and differentiated feather
colours. Army olive/khaki, naval blue and aviation blue-grey/brown remain distinct.
These templates supplement the named portraits; they do not introduce new named
characters or alter advisor traits, costs or availability. MIO artwork reuses
nine manufacturer images and adds a separate general-aircraft emblem, without
changing organization trees or progression.

Twenty-four earlier source generations were blocked by the image service:
18 focuses, five country spirits and one infantry manufacturer. All now have
reviewed neutral alternate artwork using workshop, research, correspondence,
training and communications motifs. The infantry manufacturer image also covers
its corresponding MIO. Exact final prompts are in batches 61-64 and
`company-neutral-exports.json`; initial alternate concepts are preserved in
`neutral-compositions.json`. Earlier rejection records remain in timestamped
`generation-blockers-archive-*.json` files; only unresolved items belong in
`generation-blockers.json`. Unused translucent lathe/telephone/map variants are
not exported; manifests select the corrected versions.
No alternative generation service or paid API fallback was used.

The runtime artwork reconciler is restricted to ERI/EYR/AVI and runs at startup
and weekly. In-game appearance, existing-save reconciliation, and later-created
countries still require runtime testing. Static checks alone do not establish
that those engine paths work.

## Verification

`tools/Build-VereniaArt.py` exports the manifest and builds the native-size sheet.
It refuses to overwrite a differing existing texture. `--check` validates exact
pixels, dimensions, TGA encoding, alpha and stored hashes without writing.
`tools/Test-Verenia.py` also resolves submod sprites and verifies custom texture
and shine references. `tools/Build-VereniaSpirit.py --check` checks regeneration.
