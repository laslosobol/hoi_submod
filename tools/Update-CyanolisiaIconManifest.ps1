param(
    [string[]] $FocusIds,
    [switch] $MarkDone,
    [switch] $ResolveFix,
    [switch] $MigrateHashes,
    [switch] $Check,
    [string] $RepositoryRoot
)

if ($PSVersionTable.PSVersion -lt [version]'7.2' -or -not $IsWindows) {
    throw 'Cyanolisia icon manifest tools require PowerShell 7.2+ on Windows (run with pwsh).'
}

$ErrorActionPreference = 'Stop'
$root = if ($RepositoryRoot) { [System.IO.Path]::GetFullPath($RepositoryRoot) }
    else { Split-Path -Parent $PSScriptRoot }
. (Join-Path $PSScriptRoot 'CyanolisiaIconManifest.Common.ps1')
$manifestPath = Join-Path $root 'docs/icon-generation-manifest.md'
$manifest = [System.IO.File]::ReadAllText($manifestPath)
$focusPaths = @(
    'mod/HoISubmod/common/national_focus/CYA.txt',
    'mod/HoISubmod/common/national_focus/HSM_CYA_development.txt',
    'mod/HoISubmod/common/national_focus/HSM_CYA_development_expansion.txt'
)

if ($MarkDone -and -not $FocusIds.Count) {
    throw '-MarkDone requires -FocusIds and completed visual QA.'
}
if ($ResolveFix -and -not $FocusIds.Count) {
    throw '-ResolveFix requires -FocusIds and confirmation of the repair.'
}
if ($MigrateHashes -and ($FocusIds.Count -or $MarkDone -or $ResolveFix -or $Check)) {
    throw '-MigrateHashes is a one-time standalone operation.'
}
if (-not $MigrateHashes -and -not $Check -and -not $FocusIds.Count) {
    throw 'Supply -MigrateHashes, -Check, or -FocusIds.'
}

function Clean-Cell([string] $value) {
    if (-not $value) { return '-' }
    return (($value -replace '\s+', ' ' -replace '\|', '/') -replace '^\s+|\s+$', '')
}

function Parse-Registry([string] $content) {
    $rows = @{}
    $section = [regex]::Match($content, '(?s)## Inventory\s+.*?(?=\n## Audit history)').Value
    if (-not $section) { throw 'Focus inventory section missing.' }
    foreach ($line in ($section -split "`n")) {
        if ($line -notmatch '^\| `(\w+)` \|') {
            if ($line -match '^\| ' -and $line -notmatch '^\| (?:ID |--- )') {
                throw "Malformed focus manifest row: $line"
            }
            continue
        }
        $cells = @($line.Trim().Trim('|').Split('|') | ForEach-Object { $_.Trim() })
        if ($cells.Count -notin @(10, 13)) { throw "Invalid focus manifest row: $line" }
        $id = $cells[0].Trim('`')
        if ($rows.ContainsKey($id)) { throw "Duplicate manifest entry: $id" }
        $rows[$id] = [pscustomobject]@{
            Id = $id; Name = $cells[1]; Definition = $cells[2]
            Source = $cells[3].Trim('`'); Tga = $cells[4].Trim('`')
            Gfx = $cells[5].Trim('`')
            Status = $cells[6]; References = $cells[7]
            Art = $cells[8]; Next = $cells[9]
            PngHash = if ($cells.Count -eq 13) { $cells[10].Trim('`') } else { '-' }
            TgaHash = if ($cells.Count -eq 13) { $cells[11].Trim('`') } else { '-' }
            Technical = if ($cells.Count -eq 13) { $cells[12] } else { '-' }
            RawLine = $line.TrimEnd("`r")
            SchemaColumns = $cells.Count
        }
    }
    return $rows
}

$focuses = [System.Collections.Generic.List[object]]::new()
foreach ($path in $focusPaths) {
    $content = [System.IO.File]::ReadAllText((Join-Path $root $path))
    $tokens = Get-ClausewitzTokens $content
    $stack = [System.Collections.Generic.List[string]]::new()
    $id = $null
    $icon = $null
    for ($i = 0; $i -lt $tokens.Count; $i++) {
        $token = $tokens[$i]
        if ($token -eq '}') {
            if (-not $stack.Count) { throw "Unbalanced focus braces in $path" }
            if ($stack.Count -eq 1 -and $stack[0] -eq 'shared_focus') {
                if ($id -notmatch '^\w+$' -or $icon -notmatch '^\w+$') {
                    throw "Focus without valid ID or icon in $path"
                }
                $focuses.Add([pscustomobject]@{ Id = $id; Icon = $icon; File = $path })
            }
            $stack.RemoveAt($stack.Count - 1)
            continue
        }
        if ($i + 2 -ge $tokens.Count -or $tokens[$i + 1] -ne '=') { continue }
        $value = $tokens[$i + 2]
        if ($value -eq '{') {
            $stack.Add($token)
            if ($stack.Count -eq 1 -and $token -eq 'shared_focus') {
                $id = $null
                $icon = $null
            }
        } elseif ($stack.Count -eq 1 -and $stack[0] -eq 'shared_focus') {
            if ($token -eq 'id') {
                if ($id) { throw "Duplicate focus ID field in $path" }
                $id = $value.Trim('"')
            } elseif ($token -eq 'icon') {
                if ($icon) { throw "Duplicate focus icon field in $path" }
                $icon = $value.Trim('"')
            }
        }
        $i += 2
    }
    if ($stack.Count) { throw "Unbalanced focus braces in $path" }
}
$focusById = @{}
foreach ($focus in $focuses) {
    if ($focusById.ContainsKey($focus.Id)) { throw "Duplicate focus definition: $($focus.Id)" }
    $focusById[$focus.Id] = $focus
}

$spriteText = [System.IO.File]::ReadAllText((Join-Path $root 'mod/HoISubmod/interface/focus/HSM_CYA_focus.gfx'))
$sprites = @{}
foreach ($match in [regex]::Matches($spriteText, '(?s)spriteType\s*=\s*\{([^{}]+)\}')) {
    $body = $match.Groups[1].Value
    $name = [regex]::Match($body, '\bname\s*=\s*(\w+)').Groups[1].Value
    $texture = [regex]::Match($body, 'textureFile\s*=\s*"([^"]+)"').Groups[1].Value
    if (-not $name -or -not $texture -or $sprites.ContainsKey($name)) {
        throw "Missing or duplicate sprite in $($match.Value)"
    }
    $sprites[$name] = $texture
}

$names = @{}
foreach ($path in @(
    'mod/HoISubmod/localisation/english/hsm_cyanolisia_l_english.yml',
    'EaW/localisation/english/country_CYA_l_english.yml'
)) {
    $content = [System.IO.File]::ReadAllText((Join-Path $root $path))
    foreach ($match in [regex]::Matches($content, '(?m)^\s*(\w+):0\s+"([^"]*)"')) {
        if (-not $names.ContainsKey($match.Groups[1].Value)) {
            $names[$match.Groups[1].Value] = $match.Groups[2].Value
        }
    }
}

$readme = [System.IO.File]::ReadAllText((Join-Path $root 'art/README.md'))
$descriptions = @{}
foreach ($match in [regex]::Matches($readme, '(?ms)^\- `([^`]+\.png)`: (.*?)(?=^\- `|^## |\z)')) {
    $descriptions[[System.IO.Path]::GetFileNameWithoutExtension($match.Groups[1].Value)] =
        Clean-Cell $match.Groups[2].Value
}

$old = Parse-Registry $manifest
if (-not $old.Count) { throw 'Focus inventory is empty.' }

function Get-References([string] $id) {
    $refs = [System.Collections.Generic.List[string]]::new()
    $refs.Add('focus localization/effects')
    if ($id -match 'dawnclaw|fugitive|colonel') { $refs.Add('Dawnclaw portrait/iron cross') }
    if ($id -match 'grover|crown|imperial|griffonheim|griffenheim') {
        $refs.Add('Grover portrait or GRI flag as context requires')
    }
    if ($id -match 'sicameon|asterion|minotaur|evi|river|hill') {
        $refs.Add('relevant EaW neighbor flag')
    }
    if ($refs.Count -eq 1) { $refs.Add('CYA flag if heraldry is needed') }
    return ($refs -join '; ')
}

function New-Row($focus) {
    $id = $focus.Id
    $prior = $old[$id]
    $target = if ($id.StartsWith('HSM_CYA_')) { $id } else { "HSM_CYA_$id" }
    $custom = $focus.Icon.StartsWith('GFX_HSM_CYA_')
    $source = "art/source/$target.png"
    $tga = "mod/HoISubmod/gfx/interface/goals/$target.tga"
    $status = 'MISSING'
    $technical = '-'
    $pngHash = if ($prior) { $prior.PngHash } else { '-' }
    $tgaHash = if ($prior) { $prior.TgaHash } else { '-' }
    $issue = if ($prior -and $prior.Next -ne '-') { $prior.Next }
        else { 'Generate; visual and technical QA.' }
    if ($custom) {
        $texture = $sprites[$focus.Icon]
        if ($texture) {
            $stem = [System.IO.Path]::GetFileNameWithoutExtension($texture)
            $source = if ($prior -and $prior.Source -ne '-') { $prior.Source }
                else { "art/source/$stem.png" }
            foreach ($candidate in @("art/source/$stem.png", "art/source/$($stem -replace '^HSM_CYA_', '').png")) {
                if ([System.IO.File]::Exists((Join-Path $root $candidate))) {
                    $source = $candidate
                    break
                }
            }
            $tga = "mod/HoISubmod/$texture"
        }
        $problem = if (-not $texture) { 'Sprite definition missing' }
            elseif ($texture -notmatch '^gfx/interface/goals/[^/]+\.tga$') { 'Unexpected sprite texture path' }
            else {
                $pngProblem = Test-IconPng (Join-Path $root $source) 99 86
                if ($pngProblem) { $pngProblem } else { Test-IconTga (Join-Path $root $tga) 99 86 }
            }
        if ($problem) {
            $status = 'NEEDS_FIX'
            $technical = $problem
        } else {
            $actualPngHash = Get-IconHash (Join-Path $root $source)
            $actualTgaHash = Get-IconHash (Join-Path $root $tga)
            $drift = @()
            if (Test-IconHash $pngHash) {
                if ($pngHash -ne $actualPngHash) { $drift += 'PNG SHA-256 changed' }
            } elseif ($pngHash -ne '-') { throw "Invalid PNG SHA-256 for $id" }
            if (Test-IconHash $tgaHash) {
                if ($tgaHash -ne $actualTgaHash) { $drift += 'TGA SHA-256 changed' }
            } elseif ($tgaHash -ne '-') { throw "Invalid TGA SHA-256 for $id" }
            $technical = if ($drift.Count) { $drift -join '; ' } else { 'valid' }

            if ($MarkDone -and $FocusIds -contains $id) {
                if ($prior -and $prior.Status -eq 'NEEDS_FIX' -and -not $ResolveFix) {
                    throw "Explicit -ResolveFix required before confirming $id"
                }
                $status = 'DONE'
                $pngHash = $actualPngHash
                $tgaHash = $actualTgaHash
                $technical = 'valid'
                if (-not $prior -or $prior.Next -eq '-') { $issue = 'Visual QA confirmed; PNG/TGA/GFX validated.' }
                else { $issue = Set-IconNextAction $issue 'Visual QA confirmed; PNG/TGA/GFX validated.' }
            } elseif ($prior -and $prior.Status -eq 'NEEDS_FIX' -and -not $ResolveFix) {
                $status = 'NEEDS_FIX'
            } elseif ($prior -and $prior.Status -eq 'DONE') {
                if ($pngHash -eq '-' -or $tgaHash -eq '-') {
                    if (-not $MigrateHashes) { throw "Unpinned DONE asset: $id; run -MigrateHashes" }
                    $pngHash = $actualPngHash
                    $tgaHash = $actualTgaHash
                    $status = 'DONE'
                } else {
                    $status = if ($drift.Count) { 'NEEDS_REVIEW' } else { 'DONE' }
                }
            } else {
                $status = 'NEEDS_REVIEW'
                if (-not $prior -or $prior.Next -eq '-') { $issue = 'Confirm art, lore and 99x86 readability.' }
            }
            if ($ResolveFix -and $FocusIds -contains $id -and $prior.Status -eq 'NEEDS_FIX') {
                $issue = Resolve-IconDefectNote $prior.Next ([bool]$MarkDone)
            }
        }
    } elseif ([System.IO.File]::Exists((Join-Path $root $source)) -or
        [System.IO.File]::Exists((Join-Path $root $tga))) {
        $status = 'NEEDS_FIX'
        $technical = 'Custom source/export exists but focus still uses provisional GFX'
        if (-not $prior -or $prior.Next -eq '-') {
            $issue = 'Existing art is not exported/linked; review it, then export TGA and register GFX.'
        }
    } elseif ($prior -and $prior.Status -eq 'NOT_REQUIRED') {
        $status = 'NOT_REQUIRED'
    } elseif ($prior -and $prior.Status -eq 'NEEDS_FIX') {
        $status = 'NEEDS_FIX'
        $technical = 'Planned art absent; explicit repair review required'
    }
    if ($MarkDone -and $FocusIds -contains $id -and $status -ne 'DONE') {
        throw "Cannot mark unlinked or invalid focus DONE: $id"
    }
    if ($ResolveFix -and $FocusIds -contains $id) {
        if (-not $prior -or $prior.Status -ne 'NEEDS_FIX') {
            throw "No recorded NEEDS_FIX to resolve: $id"
        }
        if ($status -eq 'NEEDS_FIX') { throw "Technical problem still blocks $id" }
    }
    $name = if ($names.ContainsKey($id)) { $names[$id] } else { "[localization missing: $id]" }
    $refs = if ($prior -and $prior.References -ne '-') { $prior.References }
        else { Get-References $id }
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($source)
    $art = if ($prior -and $prior.Art -ne '-') { $prior.Art }
        elseif ($descriptions.ContainsKey($stem)) { $descriptions[$stem] }
        else { 'Batch art brief pending; apply global style and heraldry rules.' }
    if ($id -eq 'HSM_CYA_the_countess_alone' -and -not $prior -and $status -eq 'NEEDS_REVIEW') {
        $issue = 'Earlier bust/chair concern; inspect current composition at 99x86.'
    }
    return [pscustomobject]@{
        Id = $id; Name = Clean-Cell $name
        Definition = if ($focus.File.EndsWith('/CYA.txt')) { 'CYA' }
            elseif ($focus.File.EndsWith('/HSM_CYA_development.txt')) { 'DEV' } else { 'EXP' }
        Source = $source; Tga = $tga; Gfx = $focus.Icon
        Status = $status; References = Clean-Cell $refs
        Art = Clean-Cell $art; Next = Clean-Cell $issue
        PngHash = $pngHash; TgaHash = $tgaHash; Technical = Clean-Cell $technical
    }
}

$rows = [System.Collections.Generic.List[object]]::new()
foreach ($focus in $focuses) {
    if ($FocusIds.Count -and $FocusIds -notcontains $focus.Id) {
        if (-not $old.ContainsKey($focus.Id)) { throw "Manifest entry missing: $($focus.Id)" }
        $rows.Add($old[$focus.Id])
    } else {
        $rows.Add((New-Row $focus))
    }
}
if ($FocusIds.Count) {
    foreach ($id in $FocusIds) {
        if (-not $focusById.ContainsKey($id)) { throw "Unknown focus ID: $id" }
    }
}

$counts = @{}
foreach ($status in @('DONE', 'NEEDS_REVIEW', 'NEEDS_FIX', 'MISSING', 'NOT_REQUIRED')) {
    $counts[$status] = @($rows | Where-Object Status -EQ $status).Count
}
if (($counts.Values | Measure-Object -Sum).Sum -ne $focuses.Count) {
    throw 'Status totals do not match focus count.'
}

$summary = "Focuses: $($focuses.Count); DONE=$($counts.DONE); NEEDS_REVIEW=$($counts.NEEDS_REVIEW); NEEDS_FIX=$($counts.NEEDS_FIX); MISSING=$($counts.MISSING); NOT_REQUIRED=$($counts.NOT_REQUIRED)"

function Format-Row($row) {
    return "| ``$($row.Id)`` | $($row.Name) | $($row.Definition) | ``$($row.Source)`` | ``$($row.Tga)`` | ``$($row.Gfx)`` | $($row.Status) | $($row.References) | $($row.Art) | $($row.Next) | ``$($row.PngHash)`` | ``$($row.TgaHash)`` | $($row.Technical) |"
}

if ($Check) {
    if ($old.Count -ne $focuses.Count) { throw "Manifest has $($old.Count) rows; focus files have $($focuses.Count)." }
    if ($manifest -notmatch [regex]::Escape("Inventory status: $summary")) {
        throw 'Manifest status summary is stale.'
    }
    foreach ($row in $rows) {
        if ($row.Status -notin @('DONE', 'NEEDS_REVIEW', 'NEEDS_FIX', 'MISSING', 'NOT_REQUIRED')) {
            throw "Invalid status: $($row.Id)"
        }
        $recorded = $old[$row.Id]
        if ($recorded.SchemaColumns -ne 13) { throw "Unmigrated focus row: $($row.Id)" }
        foreach ($field in @('Name', 'Definition', 'Source', 'Tga', 'Gfx', 'Status', 'PngHash', 'TgaHash', 'Technical')) {
            if ($recorded.$field -ne $row.$field) {
                throw "Stale $field for $($row.Id): $($recorded.$field) != $($row.$field)"
            }
        }
        if (-not $row.References -or -not $row.Art -or -not $row.Next -or
            $row.Art -match 'New national spirit sources \(64x64 exports\):') {
            throw "Art metadata missing or contaminated: $($row.Id)"
        }
        if ($row.Status -eq 'DONE' -and (-not (Test-IconHash $row.PngHash) -or
            -not (Test-IconHash $row.TgaHash) -or $row.Technical -ne 'valid')) {
            throw "DONE confirmation missing or stale: $($row.Id)"
        }
    }
    Write-Output "Checked manifest coverage. $summary"
    return
}

$result = $manifest
$oldHeader = '| ID | Focus name | Def | PNG source | In-game TGA | Current GFX | Status | References | Composition / heraldry | Defect / next |'
$newHeader = '| ID | Focus name | Def | PNG source | In-game TGA | Current GFX | Status | References | Composition / heraldry | Defect / next | QA PNG SHA-256 | QA TGA SHA-256 | Technical |'
$oldDivider = '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |'
$newDivider = '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |'
if ($MigrateHashes) {
    $result = Replace-ManifestLine $result ("$oldHeader`n$oldDivider") ("$newHeader`n$newDivider")
} elseif ($result -match "(?m)^$([regex]::Escape($oldHeader))\r?$") {
    throw 'Run -MigrateHashes before incremental updates.'
}
foreach ($row in $rows) {
    if (-not $MigrateHashes -and $FocusIds -notcontains $row.Id) { continue }
    $prior = $old[$row.Id]
    $result = Replace-ManifestLine $result $prior.RawLine (Format-Row $row)
}
$oldSummary = [regex]::Match($result, '(?m)^Inventory status: [^\r\n]*').Value
if (-not $oldSummary) { throw 'Focus status summary missing.' }
$result = Replace-ManifestLine $result $oldSummary "Inventory status: $summary"
$changed = Write-ManifestIfChanged $manifestPath $manifest $result
Write-Output "Focus manifest $(if ($changed) { 'updated' } else { 'unchanged' }). $summary"
