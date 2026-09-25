param(
    [Parameter(Mandatory = $true)] [string] $Source,
    [Parameter(Mandatory = $true)] [string] $Destination,
    [Parameter(Mandatory = $true)] [int] $Width,
    [Parameter(Mandatory = $true)] [int] $Height,
    [string] $Background
)

Add-Type -AssemblyName System.Drawing

$sourceImage = [System.Drawing.Image]::FromFile((Resolve-Path -LiteralPath $Source).Path)
$bitmap = [System.Drawing.Bitmap]::new($Width, $Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)

try {
    if ($Background) {
        $graphics.Clear([System.Drawing.ColorTranslator]::FromHtml($Background))
    } else {
        $graphics.Clear([System.Drawing.Color]::Transparent)
    }

    $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

    $scale = [Math]::Min($Width / $sourceImage.Width, $Height / $sourceImage.Height)
    $drawWidth = $sourceImage.Width * $scale
    $drawHeight = $sourceImage.Height * $scale
    $rect = [System.Drawing.RectangleF]::new(
        [float](($Width - $drawWidth) / 2),
        [float](($Height - $drawHeight) / 2),
        [float]$drawWidth,
        [float]$drawHeight
    )
    $graphics.DrawImage($sourceImage, $rect)
    $graphics.Flush()

    $bytes = New-Object byte[] (18 + 4 * $Width * $Height)
    $bytes[2] = 2
    $bytes[12] = [byte]($Width -band 0xff)
    $bytes[13] = [byte](($Width -shr 8) -band 0xff)
    $bytes[14] = [byte]($Height -band 0xff)
    $bytes[15] = [byte](($Height -shr 8) -band 0xff)
    $bytes[16] = 32
    $bytes[17] = 8

    $index = 18
    for ($y = $Height - 1; $y -ge 0; $y--) {
        for ($x = 0; $x -lt $Width; $x++) {
            $pixel = $bitmap.GetPixel($x, $y)
            $bytes[$index++] = $pixel.B
            $bytes[$index++] = $pixel.G
            $bytes[$index++] = $pixel.R
            $bytes[$index++] = $pixel.A
        }
    }

    $parent = Split-Path -Parent $Destination
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    [System.IO.File]::WriteAllBytes((Join-Path (Resolve-Path -LiteralPath $parent).Path (Split-Path -Leaf $Destination)), $bytes)
} finally {
    $graphics.Dispose()
    $bitmap.Dispose()
    $sourceImage.Dispose()
}
