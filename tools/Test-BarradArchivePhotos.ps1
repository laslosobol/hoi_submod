#Requires -Version 7.2
param([string] $PreviewPath)
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'Archive photo validation requires PowerShell 7.2+ on Windows.' }
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$keys = @('rock', 'titan', 'entity', 'amulet', 'reactor', 'crown', 'chalice', 'darkheart', 'echo', 'marsh', 'compass', 'plants')
$gfx = [IO.File]::ReadAllText((Join-Path $root 'mod/HoISubmod/interface/HSM_BAR_archive_photos.gfx'))
$sprites = [regex]::Matches($gfx, '(?s)spriteType\s*=\s*\{([^{}]*)\}')
if ($sprites.Count -ne $keys.Count) { throw 'Expected exactly twelve photographic sprites.' }
$failures = [Collections.Generic.List[string]]::new()
$passed = 0
$sheet = $null
$canvas = $null
$font = $null
if ($PreviewPath) {
    $sheet = [Drawing.Bitmap]::new(1800, 1328)
    $canvas = [Drawing.Graphics]::FromImage($sheet)
    $canvas.Clear([Drawing.Color]::FromArgb(24, 24, 24))
    $font = [Drawing.Font]::new('Arial', 14)
}
try {
    for ($index = 0; $index -lt $keys.Count; $index++) {
        $key = $keys[$index]
        $stream = $null
        $image = $null
        $expected = $null
        $actual = $null
        try {
            $png = Join-Path $root "art/source/HSM_BAR_archive_photo_$key.png"
            $texture = "gfx/interface/HSM_BAR/archive/photo_$key.tga"
            $tga = Join-Path $root "mod/HoISubmod/$texture"
            $matchesForKey = @($sprites | Where-Object { $_.Groups[1].Value -match ('name\s*=\s*"GFX_HSM_BAR_archive_photo_' + $key + '"') })
            if ($matchesForKey.Count -ne 1 -or $matchesForKey[0].Groups[1].Value -notmatch ('texturefile\s*=\s*"' + [regex]::Escape($texture) + '"')) {
                throw 'Sprite must uniquely reference its own texture.'
            }
            $stream = [IO.File]::OpenRead($png)
            $signature = [byte[]]::new(8)
            if ($stream.Read($signature, 0, 8) -ne 8 -or [Convert]::ToHexString($signature) -ne '89504E470D0A1A0A') { throw 'Invalid PNG signature.' }
            $stream.Position = 0
            $image = [Drawing.Image]::FromStream($stream, $false, $true)
            if ($image.Width -lt 600 -or $image.Height -lt 300 -or $image.Width -gt 8192 -or $image.Width -ne 2 * $image.Height) { throw 'Source must be a decodable 2:1 landscape PNG of at least 600x300.' }
            $expected = [Drawing.Bitmap]::new(600, 300, [Drawing.Imaging.PixelFormat]::Format32bppArgb)
            $g = [Drawing.Graphics]::FromImage($expected)
            try {
                $g.Clear([Drawing.ColorTranslator]::FromHtml('#171717'))
                $g.CompositingMode = [Drawing.Drawing2D.CompositingMode]::SourceOver
                $g.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $g.SmoothingMode = [Drawing.Drawing2D.SmoothingMode]::HighQuality
                $g.PixelOffsetMode = [Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                $g.DrawImage($image, [Drawing.RectangleF]::new(0, 0, 600, 300))
                $g.Flush()
            } finally { $g.Dispose() }
            $bytes = [IO.File]::ReadAllBytes($tga)
            if ($bytes.Length -ne 720018 -or $bytes[0] -ne 0 -or $bytes[1] -ne 0 -or $bytes[2] -ne 2 -or
                [BitConverter]::ToUInt16($bytes, 12) -ne 600 -or [BitConverter]::ToUInt16($bytes, 14) -ne 300 -or
                $bytes[16] -ne 32 -or $bytes[17] -ne 8) { throw 'Invalid uncompressed 600x300 BGRA bottom-origin TGA.' }
            $actual = [Drawing.Bitmap]::new(600, 300, [Drawing.Imaging.PixelFormat]::Format32bppArgb)
            $luminance = [Collections.Generic.HashSet[int]]::new()
            for ($y = 0; $y -lt 300; $y++) {
                for ($x = 0; $x -lt 600; $x++) {
                    $i = 18 + ((299 - $y) * 600 + $x) * 4
                    if ($bytes[$i + 3] -ne 255) { throw "Unexpected transparency at $x,$y." }
                    $p = $expected.GetPixel($x, $y)
                    if ($bytes[$i] -ne $p.B -or $bytes[$i + 1] -ne $p.G -or $bytes[$i + 2] -ne $p.R) { throw "PNG/TGA pixel drift or orientation error at $x,$y." }
                    [void]$luminance.Add([int]($p.GetBrightness() * 255))
                    $actual.SetPixel($x, $y, $p)
                }
            }
            if ($luminance.Count -lt 64) { throw 'Image has insufficient tonal variation; check for blank/corrupt output.' }
            if ($canvas) {
                $column = $index % 3
                $row = [int][Math]::Floor($index / 3)
                $canvas.DrawImageUnscaled($actual, $column * 600, $row * 332)
                $canvas.DrawString($key, $font, [Drawing.Brushes]::White, [single]($column * 600 + 8), [single]($row * 332 + 305))
            }
            $passed++
            Write-Output "PASS: $key PNG decode, full-size conversion, opaque TGA, sprite, all pixels, tonal range"
        } catch {
            $failures.Add("$key : $($_.Exception.Message)")
            Write-Output "FAIL: $($failures[-1])"
        } finally {
            if ($actual) { $actual.Dispose() }
            if ($expected) { $expected.Dispose() }
            if ($image) { $image.Dispose() }
            if ($stream) { $stream.Dispose() }
        }
    }
    if ($PreviewPath -and $failures.Count -eq 0) {
        $fullPath = [IO.Path]::GetFullPath($PreviewPath)
        [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($fullPath))
        $sheet.Save($fullPath, [Drawing.Imaging.ImageFormat]::Png)
        Write-Output "Preview: $fullPath"
    }
} finally {
    if ($font) { $font.Dispose() }
    if ($canvas) { $canvas.Dispose() }
    if ($sheet) { $sheet.Dispose() }
}
Write-Output "Barrad archive photos: $passed asset scenarios passed; $($failures.Count) failed."
if ($failures.Count) { throw ($failures -join "`n") }
