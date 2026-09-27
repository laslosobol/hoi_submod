param(
    [Parameter(Mandatory = $true)] [string[]] $FocusIds
)

$root = Split-Path -Parent $PSScriptRoot
$focusText = @(
    'CYA.txt',
    'HSM_CYA_development.txt',
    'HSM_CYA_development_expansion.txt'
) | ForEach-Object {
    [System.IO.File]::ReadAllText((Join-Path $root "mod/HoISubmod/common/national_focus/$_"))
}
$gfx = [System.IO.File]::ReadAllText((Join-Path $root 'mod/HoISubmod/interface/focus/HSM_CYA_focus.gfx'))
$failures = [System.Collections.Generic.List[string]]::new()

foreach ($id in $FocusIds) {
    if ($id -notmatch '^HSM_CYA_\w+$') {
        $failures.Add("Invalid focus ID: $id")
        continue
    }

    $focusMatches = @(
        foreach ($text in $focusText) {
            [regex]::Matches($text, '(?ms)^shared_focus\s*=\s*\{(.*?)(?=^shared_focus\s*=\s*\{|\z)') |
                Where-Object { $_.Groups[1].Value -match "(?m)^\s*id\s*=\s*$id\s*$" }
        }
    )
    if ($focusMatches.Count -ne 1) {
        $failures.Add("Focus icon missing or duplicated: $id")
        continue
    }
    $sprite = [regex]::Match($focusMatches[0].Groups[1].Value, '(?m)^\s*icon\s*=\s*(\w+)').Groups[1].Value
    if (-not $sprite.StartsWith('GFX_HSM_CYA_')) {
        $failures.Add("Focus does not use custom sprite: $id")
        continue
    }

    $spriteBlocks = @([regex]::Matches($gfx, '(?s)spriteType\s*=\s*\{([^{}]+)\}') |
        Where-Object { $_.Groups[1].Value -match "(?m)^\s*name\s*=\s*$sprite\s*$" })
    if ($spriteBlocks.Count -ne 1) {
        $failures.Add("Sprite missing or duplicated: $sprite")
        continue
    }
    $texture = [regex]::Match($spriteBlocks[0].Groups[1].Value, 'textureFile\s*=\s*"([^"]+)"').Groups[1].Value
    if ($texture -notmatch '^gfx/interface/goals/[^/]+\.tga$') {
        $failures.Add("Unexpected sprite texture: $sprite")
        continue
    }

    $stem = [System.IO.Path]::GetFileNameWithoutExtension($texture)
    $png = Join-Path $root "art/source/$stem.png"
    if (-not [System.IO.File]::Exists($png)) {
        $legacyName = $stem -replace '^HSM_CYA_', ''
        $png = Join-Path $root "art/source/$legacyName.png"
    }
    $tga = Join-Path $root "mod/HoISubmod/$texture"
    if (-not [System.IO.File]::Exists($png) -or -not [System.IO.File]::Exists($tga)) {
        $failures.Add("PNG/TGA missing: $id")
        continue
    }

    $bytes = [System.IO.File]::ReadAllBytes($tga)
    $width = $bytes[12] + 256 * $bytes[13]
    $height = $bytes[14] + 256 * $bytes[15]
    if ($bytes[2] -ne 2 -or $bytes[16] -ne 32 -or $bytes[17] -ne 8 -or
        $width -ne 99 -or $height -ne 86 -or $bytes.Length -ne 18 + 4 * 99 * 86) {
        $failures.Add("Bad 32-bit 99x86 TGA: $id")
        continue
    }
    $hasTransparent = $false
    $hasOpaque = $false
    for ($i = 21; $i -lt $bytes.Length; $i += 4) {
        if ($bytes[$i] -eq 0) { $hasTransparent = $true }
        if ($bytes[$i] -eq 255) { $hasOpaque = $true }
        if ($hasTransparent -and $hasOpaque) { break }
    }
    if (-not ($hasTransparent -and $hasOpaque)) {
        $failures.Add("Alpha bounds missing: $id")
    }
}

if ($failures.Count) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 1
}
Write-Output "Validated $($FocusIds.Count) focus sprites and PNG/TGA exports."
