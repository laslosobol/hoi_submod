#Requires -Version 7.2
param()
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'CyanolisiaIconManifest.Common.ps1')
$mod = Join-Path $root 'mod/HoISubmod'
$focus = [IO.File]::ReadAllText((Join-Path $mod 'common/national_focus/HSM_BAR_directorate.txt'))
$ids = @([regex]::Matches($focus, '\bGFX_(HSM_BAR_(?:dir|cover)_\w+)\s*=') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
$gfx = [IO.File]::ReadAllText((Join-Path $mod 'interface/HSM_BAR_service_icons.gfx'))
$shine = [IO.File]::ReadAllText((Join-Path $mod 'interface/HSM_BAR_service_icons_shine.gfx'))
$failures = [Collections.Generic.List[string]]::new()
$passed = 0
foreach ($id in $ids) {
    try {
        $png = Join-Path $root "art/source/$id.png"
        $tga = Join-Path $mod "gfx/interface/goals/$id.tga"
        $pngError = Test-IconPng $png 99 86
        if ($pngError) { throw $pngError }
        $tgaError = Test-IconTga $tga 99 86
        if ($tgaError) { throw $tgaError }
        $texture = "gfx/interface/goals/$id.tga"
        if ([regex]::Matches($gfx, 'name\s*=\s*"GFX_' + $id + '"').Count -ne 1) { throw 'Standard sprite must be unique' }
        if (-not $gfx.Contains('texturefile = "' + $texture + '"')) { throw 'Wrong standard texture' }
        if ([regex]::Matches($shine, 'name\s*=\s*"GFX_' + $id + '_shine"').Count -ne 1) { throw 'Shine sprite must be unique' }
        if ([regex]::Matches($shine, 'animationmaskfile\s*=\s*"' + [regex]::Escape($texture) + '"').Count -ne 2) { throw 'Both shine masks must match the source TGA' }
        $passed++
        Write-Output "PASS: $id PNG/TGA/standard/shine"
    } catch { $failures.Add("$id : $($_.Exception.Message)"); Write-Output "FAIL: $($failures[-1])" }
}
if (-not $ids.Count) { throw 'No Barrad custom icons found' }
Write-Output "Barrad art: $passed asset scenarios passed; $($failures.Count) failed."
if ($failures.Count) { throw ($failures -join "`n") }
