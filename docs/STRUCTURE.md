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

`common/` contains database-style definitions used by HoI4 systems. This project currently keeps only the folders that have real content, such as decisions, ideas, characters, and on-actions.

`events/` contains country, news, and narrative event files.

`history/` contains starting-state data. This submod currently uses country history only to recruit the Dawnclaw advisor character at game start.

`localisation/english/` contains player-facing strings. Keep key prefixes consistent, for example `HSM_` for this submod.

Create `gfx/` and `interface/` only when adding new art or sprite definitions. Current content reuses existing EaW/HoI4 assets.

Create EaW-specific folders such as `country_metadata/` and `portraits/` only when touching country presentation or portrait content.

Create `map/`, `scenario_tests/`, `tutorial/`, `music/`, and `sound/` only when the design explicitly needs them.

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
