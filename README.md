# Equestria at War: Expanded Stories

An unofficial Hearts of Iron IV submod that expands the stories and gameplay of
countries in Equestria at War: national focuses, political paths, events,
decisions, national spirits, and military and economic development.

**IMPORTANT: AI-ASSISTED RESEARCH PROJECT.** This is a personal exploration of
what AI can and cannot do in game modding. Code, narrative writing, localization,
and artwork are developed with substantial AI assistance, under the author's
direction and review. This is an experimental alpha, not a promise of error-free
content or an official EaW release.

The current playable expansion focuses on Cyanolisia. Additional countries are
planned; they are not advertised as already implemented. In-game localization
is available in English and Russian. Start a new campaign when testing releases.

Current release: **0.5.2**. See [PATCH_NOTES.md](PATCH_NOTES.md) for release history.

Steam Workshop: [Equestria at War: Expanded Stories](https://steamcommunity.com/sharedfiles/filedetails/?id=3810937281).

Source and feedback: [GitHub](https://github.com/laslosobol/hoi_submod).
[Suggestions](https://github.com/laslosobol/hoi_submod/issues/new?title=%5BSuggestion%5D%20)
and [bug reports](https://github.com/laslosobol/hoi_submod/issues/new?title=%5BBug%5D%20)
are welcome. For bugs, include mod/game/EaW versions, the playset, reproduction
steps, and relevant screenshots or logs.

Workshop descriptions are maintained in `workshop/description_en.txt` and
`workshop/description_uk.txt`; see `workshop/UPLOAD.txt` for the upload layout.
The Workshop preview is `mod/HoISubmod/thumbnail.png`.
The checkout name, `HoISubmod` directory and `HSM_` script IDs remain technical
identifiers so that existing tools and references keep working.

The playable mod root is:

```text
mod/HoISubmod/
```

Put game content under that folder, then create a local launcher descriptor from:

```text
launcher/HoISubmod.mod.example
```

Use it as the local `HoISubmod.mod` launcher descriptor, with `path` pointing to this checkout's `mod/HoISubmod` folder. Enable both `Equestria at War` and `Equestria at War: Expanded Stories` in the launcher, with EaW above the submod in the playset.

## Layout

```text
mod/HoISubmod/
  descriptor.mod              # packaged mod descriptor, no local path
  common/                     # shared game database files currently used by the submod
  events/                     # event files
  history/                    # country startup hooks
  localisation/english/       # text shown in-game

launcher/
  HoISubmod.mod.example       # local launcher descriptor template

docs/
  STRUCTURE.md                # folder purpose and modding notes
  EAW_UPSTREAM.md             # upstream EaW reference
```

## Notes

- This template declares `Equestria at War` as a dependency in both descriptors.
- Upstream EaW development repo: https://github.com/EaW-Team/equestria_dev
- No `replace_path` entries are included by default. Prefer same-path file overrides or new files first; add `replace_path` only when you intentionally replace a whole loaded directory.
- Localization files should use HoI4's expected encoding for your game version. If text fails to load, check `Documents/Paradox Interactive/Hearts of Iron IV/logs/error.log`.

## Narrative and Focus Validation

Run with PowerShell 7.2+ on Windows, with the reference dependency in `EaW/`:

```powershell
pwsh -NoProfile -File tools/Test-CyanolisiaNarrative.ps1
pwsh -NoProfile -File tools/Test-CyanolisiaFocusFlow.ps1
```

For purely editorial changes, the narrative test also accepts `-CompareHead` to check that focus layout, icons and art approvals are unchanged. Do not use that option for intentional focus-graph changes. The focus-flow suite checks graph references, route layouts and selected progression predicates using deterministic fixtures; neither suite replaces an in-game playthrough.

The same-path event overrides `GriffonianEmpire Events.txt` and `Cyanolisia Events.txt` preserve the reference files except for `imperial.99` and the entry guards of `cyan.9`, `cyan.10`, `cyan.11`. Reconcile them with upstream when updating EaW; do not replace them with duplicate event IDs in a differently named file. See `docs/cyanolisia-lore-audit.md` for the audit and authorized implementation notes.
