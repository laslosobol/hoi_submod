# HoI4 EaW Submod Structure

## Descriptor Files

`mod/HoISubmod/descriptor.mod` is the descriptor that belongs inside the mod package.

`launcher/HoISubmod.mod.example` is a template for the local launcher descriptor. Copy it to:

```text
Documents/Paradox Interactive/Hearts of Iron IV/mod/HoISubmod.mod
```

Then edit the `path` value so it points to this checkout's `mod/HoISubmod` directory.

## Dependency

The descriptors use:

```text
dependencies={
    "Equestria at War"
}
```

The dependency name must match EaW's launcher display name. In the launcher playset, load `Equestria at War` above `HoISubmod`.

## Folder Guide

`common/` contains database-style definitions used by HoI4 systems. Common subfolders in this template cover decisions, ideas, focuses, characters, scripted triggers/effects, technologies, units, and on-actions.

`events/` contains country, news, and narrative event files.

`history/` contains starting-state data: countries, states, units, and generals/admirals.

`localisation/english/` contains player-facing strings. Keep key prefixes consistent, for example `HSM_` for this submod.

`gfx/` contains image assets and generated sprite references. Use the nested folders for flags, leaders, focus icons, idea icons, and event art.

`interface/` contains `.gui` and `.gfx` files. Add sprite definitions here when new art needs to be referenced by script.

`country_metadata/` and `portraits/` are included because the upstream EaW repository uses those top-level folders. Keep submod additions compatible with EaW's conventions when touching country-specific presentation or portrait content.

`map/` is present for rare map-adjacent work. Most submods should avoid touching it unless the design explicitly needs map changes.

`scenario_tests/` is available for save/scenario validation files if the submod grows large enough to need repeatable checks.

`tutorial/` is available for tutorial-facing content if needed. Most submods can leave it empty.

## Replace Path Policy

No `replace_path` is enabled by default. For an EaW submod, replacing entire directories can accidentally erase base EaW content.

Use `replace_path` only when all of these are true:

1. The submod intentionally owns the whole directory being replaced.
2. The replacement folder contains every file needed by that game system.
3. The same `replace_path` line is added to both `descriptor.mod` and the launcher `.mod` file.

## Naming

Suggested internal prefix:

```text
HSM
```

Examples:

```text
HSM_my_decision_category
HSM_country_event.1
HSM_focus_my_new_path
```
