param(
    [string[]] $IdeaIds,
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
$ideaPath = 'mod/HoISubmod/common/ideas/HSM_CYA_ideas.txt'
$gfxPath = 'mod/HoISubmod/interface/ideas/HSM_CYA_ideas.gfx'

if ($MarkDone -and -not $IdeaIds.Count) {
    throw '-MarkDone requires -IdeaIds and completed visual QA.'
}
if ($ResolveFix -and -not $IdeaIds.Count) {
    throw '-ResolveFix requires -IdeaIds and confirmation of the repair.'
}
if ($MigrateHashes -and ($IdeaIds.Count -or $MarkDone -or $ResolveFix -or $Check)) {
    throw '-MigrateHashes is a one-time standalone operation.'
}
if (-not $MigrateHashes -and -not $Check -and -not $IdeaIds.Count) {
    throw 'Supply -MigrateHashes, -Check, or -IdeaIds.'
}

function Clean-Cell([string] $value) {
    if (-not $value) { return '-' }
    return (($value -replace '\s+', ' ' -replace '\|', '/') -replace '^\s+|\s+$', '')
}

$ideasText = [System.IO.File]::ReadAllText((Join-Path $root $ideaPath))
$ideas = [System.Collections.Generic.List[object]]::new()
$ideaById = @{}
# Track only direct children of ideas.country; quoted strings and comments are inert.
$tokens = Get-ClausewitzTokens $ideasText
$stack = [System.Collections.Generic.List[string]]::new()
$currentId = $null
$currentPicture = $null
for ($i = 0; $i -lt $tokens.Count; $i++) {
    $token = $tokens[$i]
    if ($token -eq '}') {
        if ($stack.Count -eq 3 -and $stack[0] -eq 'ideas' -and
            $stack[1] -eq 'country' -and $currentId -eq $stack[2]) {
            if (-not $currentPicture) { throw "Idea picture missing: $currentId" }
            if ($ideaById.ContainsKey($currentId)) { throw "Duplicate idea definition: $currentId" }
            $idea = [pscustomobject]@{ Id = $currentId; Picture = $currentPicture }
            $ideas.Add($idea)
            $ideaById[$currentId] = $idea
            $currentId = $null
            $currentPicture = $null
        }
        if (-not $stack.Count) { throw 'Unbalanced idea braces.' }
        $stack.RemoveAt($stack.Count - 1)
        continue
    }
    if ($i + 2 -ge $tokens.Count -or $tokens[$i + 1] -ne '=') { continue }
    $value = $tokens[$i + 2]
    if ($value -eq '{') {
        $stack.Add($token)
        if ($stack.Count -eq 3 -and $stack[0] -eq 'ideas' -and
            $stack[1] -eq 'country' -and $token -match '^HSM_CYA_\w+$') {
            $currentId = $token
            $currentPicture = $null
        }
    } elseif ($token -eq 'picture' -and $stack.Count -eq 3 -and
        $stack[0] -eq 'ideas' -and $stack[1] -eq 'country' -and
        $currentId -eq $stack[2]) {
        $currentPicture = $value.Trim('"')
    }
    $i += 2
}
if ($stack.Count) { throw 'Unbalanced idea braces.' }

$gfx = [System.IO.File]::ReadAllText((Join-Path $root $gfxPath))
$sprites = @{}
foreach ($match in [regex]::Matches($gfx, '(?s)spriteType\s*=\s*\{([^{}]+)\}')) {
    $body = $match.Groups[1].Value
    $name = [regex]::Match($body, '\bname\s*=\s*(\w+)').Groups[1].Value
    $texture = [regex]::Match($body, 'textureFile\s*=\s*"([^"]+)"').Groups[1].Value
    if (-not $name -or -not $texture -or $sprites.ContainsKey($name)) {
        throw "Missing or duplicate sprite in $($match.Value)"
    }
    $sprites[$name] = $texture
}

$names = @{}
$locText = [System.IO.File]::ReadAllText((Join-Path $root 'mod/HoISubmod/localisation/english/hsm_cyanolisia_l_english.yml'))
foreach ($match in [regex]::Matches($locText, '(?m)^\s*(\w+):0\s+"([^"]*)"')) {
    $names[$match.Groups[1].Value] = $match.Groups[2].Value
}

$readme = [System.IO.File]::ReadAllText((Join-Path $root 'art/README.md'))
$descriptions = @{}
foreach ($match in [regex]::Matches($readme, '(?ms)^\- `([^`]+\.png)`: (.*?)(?=^\- `|^## |^\s*$|\z)')) {
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($match.Groups[1].Value)
    $descriptions[$stem] = Clean-Cell $match.Groups[2].Value
}

$sectionMatch = [regex]::Match($manifest, '(?s)<!-- BEGIN SPIRIT INVENTORY -->(.*?)<!-- END SPIRIT INVENTORY -->')
if (-not $sectionMatch.Success) { throw 'Spirit inventory markers missing.' }
$old = @{}
foreach ($line in ($sectionMatch.Groups[1].Value -split "`n")) {
    if ($line -notmatch '^\| `(\w+)` \|') {
        if ($line -match '^\| ' -and $line -notmatch '^\| (?:Idea ID |--- )') {
            throw "Malformed spirit manifest row: $line"
        }
        continue
    }
    $cells = @($line.Trim().Trim('|').Split('|') | ForEach-Object { $_.Trim() })
    if ($cells.Count -notin @(10, 13)) { throw "Invalid spirit row: $line" }
    $id = $cells[0].Trim('`')
    if ($old.ContainsKey($id)) { throw "Duplicate spirit manifest entry: $id" }
    $old[$id] = [pscustomobject]@{
        Id = $id; Name = $cells[1]; Picture = $cells[2].Trim('`')
        Source = $cells[3].Trim('`'); Tga = $cells[4].Trim('`')
        Gfx = $cells[5].Trim('`'); Status = $cells[6]
        References = $cells[7]; Art = $cells[8]; Next = $cells[9]
        PngHash = if ($cells.Count -eq 13) { $cells[10].Trim('`') } else { '-' }
        TgaHash = if ($cells.Count -eq 13) { $cells[11].Trim('`') } else { '-' }
        Technical = if ($cells.Count -eq 13) { $cells[12] } else { '-' }
        RawLine = $line.TrimEnd("`r")
        SchemaColumns = $cells.Count
    }
}
if (-not $old.Count) { throw 'Spirit inventory is empty.' }

function Get-References([string] $id) {
    $refs = [System.Collections.Generic.List[string]]::new()
    $refs.Add('idea effects/localization')
    if ($id -eq 'HSM_CYA_imperial_legitimacy_dynamic_modifier_dummy_idea') {
        $refs.Add('CYA cross/charter; not Grover portrait')
        return ($refs -join '; ')
    }
    if ($id -match 'dawnclaw|fugitive|colonel') { $refs.Add('Dawnclaw portrait/iron cross') }
    if ($id -match 'grover|imperial|griffenheim|griffonian|crown') {
        $refs.Add('Grover portrait or GRI flag only as context requires')
    }
    if ($id -match 'sicameon|asterion|minotaur|evi|river|hill') {
        $refs.Add('relevant EaW neighbor flag')
    }
    if ($refs.Count -eq 1) { $refs.Add('CYA flag if heraldry is needed') }
    return ($refs -join '; ')
}

function New-Row($idea) {
    $id = $idea.Id
    $prior = $old[$id]
    $picture = $idea.Picture
    $custom = $picture.StartsWith('HSM_CYA_')
    $source = "art/source/$id.png"
    $tga = "mod/HoISubmod/gfx/interface/ideas/$id.tga"
    $sprite = '-'
    $status = 'MISSING'
    $technical = '-'
    $pngHash = if ($prior) { $prior.PngHash } else { '-' }
    $tgaHash = if ($prior) { $prior.TgaHash } else { '-' }
    $issue = if ($prior -and $prior.Next -ne '-') { $prior.Next }
        else { 'Generate 64x64 art, then review and link.' }
    if ($custom) {
        $sprite = "GFX_idea_$picture"
        $texture = $sprites[$sprite]
        if ($texture) {
            $stem = [System.IO.Path]::GetFileNameWithoutExtension($texture)
            $source = if ($prior -and $prior.Source -ne '-') { $prior.Source }
                else { "art/source/$stem.png" }
            $candidates = @("art/source/$stem.png")
            if ($stem -eq 'cya_grover_regency') {
                $candidates += 'art/source/countess_regency_for_grover.png'
            }
            foreach ($candidate in $candidates) {
                if ([System.IO.File]::Exists((Join-Path $root $candidate))) {
                    $source = $candidate
                    break
                }
            }
            $tga = "mod/HoISubmod/$texture"
        }
        $problem = if (-not $texture) { 'Sprite definition missing' }
            elseif ($texture -notmatch '^gfx/interface/ideas/[^/]+\.tga$') { 'Unexpected sprite texture path' }
            else {
                $pngProblem = Test-IconPng (Join-Path $root $source) 64 64
                if ($pngProblem) { $pngProblem } else { Test-IconTga (Join-Path $root $tga) 64 64 }
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
            $technical = if ($drift.Count) { "valid; $($drift -join '; ')" } else { 'valid' }

            if ($MarkDone -and $IdeaIds -contains $id) {
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
                if (-not $prior -or $prior.Next -eq '-') { $issue = 'Confirm art, lore and 64x64 readability.' }
            }
            if ($ResolveFix -and $IdeaIds -contains $id -and $prior.Status -eq 'NEEDS_FIX') {
                $issue = Resolve-IconDefectNote $prior.Next ([bool]$MarkDone)
            }
        }
    } elseif ([System.IO.File]::Exists((Join-Path $root $source)) -or
        [System.IO.File]::Exists((Join-Path $root $tga))) {
        $status = 'NEEDS_FIX'
        $technical = 'Custom source/export exists but idea still uses provisional picture'
        if (-not $prior -or $prior.Next -eq '-') {
            $issue = 'Source/export exists but picture is still provisional; review and link.'
        }
    } elseif ($prior -and $prior.Status -eq 'NOT_REQUIRED') {
        $status = 'NOT_REQUIRED'
    } elseif ($prior -and $prior.Status -eq 'NEEDS_FIX') {
        $status = 'NEEDS_FIX'
        $technical = 'Planned art absent; explicit repair review required'
    }
    if ($MarkDone -and $IdeaIds -contains $id -and $status -ne 'DONE') {
        throw "Cannot mark unlinked or invalid idea DONE: $id"
    }
    if ($ResolveFix -and $IdeaIds -contains $id) {
        if (-not $prior -or $prior.Status -ne 'NEEDS_FIX') {
            throw "No recorded NEEDS_FIX to resolve: $id"
        }
        if ($status -eq 'NEEDS_FIX') { throw "Technical problem still blocks $id" }
    }
    $name = if ($names.ContainsKey($id)) { $names[$id] } else { "[localization missing: $id]" }
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($source)
    $art = if ($prior -and $prior.Art -ne '-') { $prior.Art }
        elseif ($descriptions.ContainsKey($stem)) { $descriptions[$stem] }
        else { 'Batch art brief pending; apply global style and heraldry rules.' }
    if ($id -eq 'HSM_CYA_imperial_legitimacy_dynamic_modifier_dummy_idea' -and
        $art -notmatch 'Do not use Grover') {
        $art += ' Do not use Grover portrait or crown for imperial legitimacy.'
    }
    if ($picture -eq 'HSM_CYA_grover_regency' -and $issue -notmatch 'Intentionally shared') {
        $issue += ' Intentionally shared with the other Grover regency idea.'
    }
    return [pscustomobject]@{
        Id = $id; Name = Clean-Cell $name; Picture = $picture
        Source = $source; Tga = $tga; Gfx = $sprite; Status = $status
        References = if ($id -eq 'HSM_CYA_imperial_legitimacy_dynamic_modifier_dummy_idea') {
            if ($prior -and $prior.References -ne '-') { $prior.References } else { Get-References $id }
        } elseif ($prior -and $prior.References -ne '-') { $prior.References }
            else { Get-References $id }
        Art = Clean-Cell $art; Next = Clean-Cell $issue
        PngHash = $pngHash; TgaHash = $tgaHash; Technical = Clean-Cell $technical
    }
}

$rows = [System.Collections.Generic.List[object]]::new()
foreach ($idea in $ideas) {
    if ($IdeaIds.Count -and $IdeaIds -notcontains $idea.Id) {
        if (-not $old.ContainsKey($idea.Id)) { throw "Spirit manifest entry missing: $($idea.Id)" }
        $rows.Add($old[$idea.Id])
    } else {
        $rows.Add((New-Row $idea))
    }
}
if ($IdeaIds.Count) {
    foreach ($id in $IdeaIds) {
        if (-not $ideaById.ContainsKey($id)) { throw "Unknown idea ID: $id" }
    }
    foreach ($group in @($ideas | Where-Object { $_.Picture.StartsWith('HSM_CYA_') } | Group-Object Picture)) {
        if ($group.Count -lt 2 -or -not @($group.Group | Where-Object { $IdeaIds -contains $_.Id }).Count) {
            continue
        }
        foreach ($use in $group.Group) {
            if ($IdeaIds -contains $use.Id) { continue }
            $current = New-Row $use
            $recorded = $old[$use.Id]
            if ($current.Status -ne $recorded.Status -or
                $current.Technical -ne $recorded.Technical -or
                $current.Source -ne $recorded.Source -or
                $current.Tga -ne $recorded.Tga -or
                $current.Gfx -ne $recorded.Gfx) {
                throw "Shared asset changed; include all affected IdeaIds for $($group.Name)"
            }
        }
    }
}
$counts = @{}
foreach ($status in @('DONE', 'NEEDS_REVIEW', 'NEEDS_FIX', 'MISSING', 'NOT_REQUIRED')) {
    $counts[$status] = @($rows | Where-Object Status -EQ $status).Count
}
if (($counts.Values | Measure-Object -Sum).Sum -ne $ideas.Count) {
    throw 'Spirit status totals do not match idea use count.'
}
$summary = "Ideas: $($ideas.Count) uses; DONE=$($counts.DONE); NEEDS_REVIEW=$($counts.NEEDS_REVIEW); NEEDS_FIX=$($counts.NEEDS_FIX); MISSING=$($counts.MISSING); NOT_REQUIRED=$($counts.NOT_REQUIRED)"

function Format-Row($row) {
    return "| ``$($row.Id)`` | $($row.Name) | ``$($row.Picture)`` | ``$($row.Source)`` | ``$($row.Tga)`` | ``$($row.Gfx)`` | $($row.Status) | $($row.References) | $($row.Art) | $($row.Next) | ``$($row.PngHash)`` | ``$($row.TgaHash)`` | $($row.Technical) |"
}

if ($Check) {
    if ($old.Count -ne $ideas.Count) { throw "Manifest has $($old.Count) spirit rows; ideas file has $($ideas.Count)." }
    if ($sectionMatch.Groups[1].Value -notmatch [regex]::Escape("Spirit inventory status: $summary")) {
        throw "Spirit status summary is stale. Expected: $summary"
    }
    foreach ($idea in $ideas) {
        $current = New-Row $idea
        $recorded = $old[$idea.Id]
        if ($recorded.SchemaColumns -ne 13) { throw "Unmigrated spirit row: $($idea.Id)" }
        if ($current.Status -notin @('DONE', 'NEEDS_REVIEW', 'NEEDS_FIX', 'MISSING', 'NOT_REQUIRED')) {
            throw "Invalid spirit status: $($idea.Id)"
        }
        foreach ($field in @('Name', 'Picture', 'Source', 'Tga', 'Gfx', 'Status', 'PngHash', 'TgaHash', 'Technical')) {
            if ($recorded.$field -ne $current.$field) {
                throw "Stale spirit $field for $($idea.Id)"
            }
        }
        if (-not $current.References -or -not $current.Art -or -not $current.Next -or
            $current.Art -match 'New national spirit sources \(64x64 exports\):') {
            throw "Spirit art metadata missing or contaminated: $($idea.Id)"
        }
        if ($current.Status -eq 'DONE' -and (-not (Test-IconHash $current.PngHash) -or
            -not (Test-IconHash $current.TgaHash) -or $current.Technical -ne 'valid')) {
            throw "DONE spirit confirmation missing or stale: $($idea.Id)"
        }
    }
    foreach ($group in @($rows | Where-Object { $_.Picture.StartsWith('HSM_CYA_') } | Group-Object Picture)) {
        if ($group.Count -lt 2) { continue }
        $first = $group.Group[0]
        foreach ($use in $group.Group) {
            if ($use.Source -ne $first.Source -or $use.Tga -ne $first.Tga -or
                $use.Gfx -ne $first.Gfx -or
                ($use.Technical -split ';')[0] -ne ($first.Technical -split ';')[0]) {
                throw "Shared spirit asset disagrees across uses: $($group.Name)"
            }
        }
    }
    $dynamicText = [System.IO.File]::ReadAllText((Join-Path $root 'mod/HoISubmod/common/dynamic_modifiers/HSM_CYA_dynamic_modifiers.txt'))
    foreach ($kind in @('industrial_program', 'military_program', 'imperial_legitimacy')) {
        $block = [regex]::Match($dynamicText,
            "(?ms)^HSM_CYA_${kind}_dynamic_modifier\s*=\s*\{(.*?)(?=^HSM_CYA_\w+\s*=\s*\{|\z)")
        $icon = "GFX_idea_HSM_CYA_$kind"
        if (-not $block.Success -or $block.Groups[1].Value -notmatch "(?m)^\s*icon\s*=\s*$icon\s*$") {
            throw "Dynamic spirit icon missing or mismatched: $kind"
        }
    }
    Write-Output "Checked spirit manifest. $summary"
    return
}

$section = $sectionMatch.Value
$oldHeader = '| Idea ID | Name | Current picture | PNG source | In-game TGA | GFX | Status | References | Composition / heraldry | Defect / next |'
$newHeader = '| Idea ID | Name | Current picture | PNG source | In-game TGA | GFX | Status | References | Composition / heraldry | Defect / next | QA PNG SHA-256 | QA TGA SHA-256 | Technical |'
$oldDivider = '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |'
$newDivider = '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |'
if ($MigrateHashes) {
    $section = Replace-ManifestLine $section ("$oldHeader`n$oldDivider") ("$newHeader`n$newDivider")
} elseif ($section -match "(?m)^$([regex]::Escape($oldHeader))\r?$") {
    throw 'Run -MigrateHashes before incremental spirit updates.'
}
foreach ($row in $rows) {
    if (-not $MigrateHashes -and $IdeaIds -notcontains $row.Id) { continue }
    $section = Replace-ManifestLine $section $old[$row.Id].RawLine (Format-Row $row)
}
$oldSummary = [regex]::Match($section, '(?m)^Spirit inventory status: [^\r\n]*').Value
if (-not $oldSummary) { throw 'Spirit status summary missing.' }
$section = Replace-ManifestLine $section $oldSummary "Spirit inventory status: $summary"
$result = $manifest.Substring(0, $sectionMatch.Index) + $section +
    $manifest.Substring($sectionMatch.Index + $sectionMatch.Length)
$changed = Write-ManifestIfChanged $manifestPath $manifest $result
Write-Output "Spirit manifest $(if ($changed) { 'updated' } else { 'unchanged' }). $summary"
