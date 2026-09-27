if ($PSVersionTable.PSVersion -lt [version]'7.2' -or -not $IsWindows) {
    throw 'Cyanolisia icon manifest tools require PowerShell 7.2+ on Windows (run with pwsh).'
}

function Get-IconHash([string] $path) {
    if (-not [System.IO.File]::Exists($path)) { return '-' }
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Test-IconHash([string] $hash) {
    return $hash -match '^[0-9a-f]{64}$'
}

function Test-IconPng([string] $path, [int] $minWidth, [int] $minHeight) {
    if (-not [System.IO.File]::Exists($path)) { return 'Source PNG missing' }
    try {
        $stream = [System.IO.File]::OpenRead($path)
        try {
            $signature = [byte[]]::new(8)
            if ($stream.Read($signature, 0, 8) -ne 8 -or
                [Convert]::ToHexString($signature) -ne '89504E470D0A1A0A') {
                return 'Source is not a PNG'
            }
            $stream.Position = 0
            Add-Type -AssemblyName System.Drawing
            $image = [System.Drawing.Image]::FromStream($stream, $false, $true)
            try {
                if ($image.Width -lt $minWidth -or $image.Height -lt $minHeight -or
                    $image.Width -gt 8192 -or $image.Height -gt 8192) {
                    return "Source PNG dimensions must be at least ${minWidth}x${minHeight} and at most 8192x8192"
                }
                $bitmap = [System.Drawing.Bitmap]::new($image.Width, $image.Height,
                    [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
                try {
                    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                    try { $graphics.DrawImage($image, 0, 0, $image.Width, $image.Height) }
                    finally { $graphics.Dispose() }
                    $rect = [System.Drawing.Rectangle]::new(0, 0, $bitmap.Width, $bitmap.Height)
                    $bits = $bitmap.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadOnly,
                        [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
                    try {
                        $pixels = [byte[]]::new([Math]::Abs($bits.Stride) * $bitmap.Height)
                        [System.Runtime.InteropServices.Marshal]::Copy($bits.Scan0, $pixels, 0, $pixels.Length)
                        $transparent = $false
                        $opaque = $false
                        for ($i = 3; $i -lt $pixels.Length; $i += 4) {
                            if ($pixels[$i] -eq 0) { $transparent = $true }
                            if ($pixels[$i] -eq 255) { $opaque = $true }
                            if ($transparent -and $opaque) { break }
                        }
                        if (-not ($transparent -and $opaque)) { return 'Source PNG alpha bounds missing' }
                    } finally { $bitmap.UnlockBits($bits) }
                } finally { $bitmap.Dispose() }
            } finally { $image.Dispose() }
        } finally { $stream.Dispose() }
    } catch {
        return 'Source PNG cannot be decoded'
    }
    return $null
}

function Test-IconTga([string] $path, [int] $width, [int] $height) {
    if (-not [System.IO.File]::Exists($path)) { return 'TGA missing' }
    $bytes = [System.IO.File]::ReadAllBytes($path)
    if ($bytes.Length -ne (18 + 4 * $width * $height) -or $bytes[0] -ne 0 -or
        $bytes[1] -ne 0 -or $bytes[2] -ne 2 -or
        $bytes[12] + 256 * $bytes[13] -ne $width -or
        $bytes[14] + 256 * $bytes[15] -ne $height -or
        $bytes[16] -ne 32 -or ($bytes[17] -band 15) -ne 8) {
        return "TGA must be uncompressed 32-bit ${width}x${height} with alpha"
    }
    $transparent = $false
    $opaque = $false
    for ($i = 21; $i -lt $bytes.Length; $i += 4) {
        if ($bytes[$i] -eq 0) { $transparent = $true }
        if ($bytes[$i] -eq 255) { $opaque = $true }
        if ($transparent -and $opaque) { break }
    }
    if (-not ($transparent -and $opaque)) { return 'TGA alpha bounds missing' }
    return $null
}

function Get-ClausewitzTokens([string] $content) {
    return ,@([regex]::Matches($content, '"(?:\\.|[^"\\])*"|#[^\r\n]*|[{}=]|[^\s{}=#"]+') |
        ForEach-Object { $_.Value } | Where-Object { -not $_.StartsWith('#') })
}

function Resolve-IconDefectNote([string] $note, [bool] $approved) {
    $withoutNext = $note -replace '; Next: [^;]*$', ''
    if ($withoutNext -match '^(?<history>.*); Active: (?<defect>.+)$') {
        $history = "$($Matches.history); "
        $defect = $Matches.defect
    } elseif ($withoutNext -match '^Resolved \d{4}-\d\d-\d\d:') {
        throw 'Record a new artistic defect as Active: <defect>; Next: <action> before -ResolveFix.'
    } else {
        $history = ''
        $defect = $withoutNext
    }
    $action = if ($approved) { 'Visual QA confirmed; PNG/TGA/GFX validated.' }
        else { 'Confirm repaired art, lore and game-size readability.' }
    return "$($history)Resolved $(Get-Date -Format 'yyyy-MM-dd'): $defect; Next: $action"
}

function Set-IconNextAction([string] $note, [string] $action) {
    if ($note -match '; Next: [^;]*$') {
        return ($note -replace '; Next: [^;]*$', "; Next: $action")
    }
    return $note
}

function Replace-ManifestLine([string] $content, [string] $oldLine, [string] $newLine) {
    $first = $content.IndexOf($oldLine, [System.StringComparison]::Ordinal)
    if ($first -lt 0) { throw "Manifest row not found: $oldLine" }
    if ($content.IndexOf($oldLine, $first + $oldLine.Length, [System.StringComparison]::Ordinal) -ge 0) {
        throw "Manifest row is duplicated: $oldLine"
    }
    if ($oldLine -eq $newLine) { return $content }
    return $content.Substring(0, $first) + $newLine + $content.Substring($first + $oldLine.Length)
}

function Write-ManifestIfChanged([string] $path, [string] $oldContent, [string] $newContent) {
    if ($oldContent -ceq $newContent) { return $false }
    $temporary = Join-Path ([System.IO.Path]::GetDirectoryName($path)) ('.' + [System.IO.Path]::GetFileName($path) + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        [System.IO.File]::WriteAllText($temporary, $newContent, [System.Text.UTF8Encoding]::new($false))
        [System.IO.File]::Move($temporary, $path, $true)
    } finally {
        if ([System.IO.File]::Exists($temporary)) { [System.IO.File]::Delete($temporary) }
    }
    return $true
}
