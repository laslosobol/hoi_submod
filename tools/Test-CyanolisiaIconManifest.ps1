if ($PSVersionTable.PSVersion -lt [version]'7.2' -or -not $IsWindows) {
    throw 'Cyanolisia icon manifest tests require PowerShell 7.2+ on Windows (run with pwsh).'
}

$ErrorActionPreference = 'Stop'
$focusScript = Join-Path $PSScriptRoot 'Update-CyanolisiaIconManifest.ps1'
$spiritScript = Join-Path $PSScriptRoot 'Update-CyanolisiaSpiritManifest.ps1'
$tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$fixture = Join-Path $tempRoot ("cya-icon-manifest-test-$([guid]::NewGuid().ToString('N'))")
$manifestPath = Join-Path $fixture 'docs/icon-generation-manifest.md'
$focusPng = Join-Path $fixture 'art/source/HSM_CYA_test_focus.png'
$focusTga = Join-Path $fixture 'mod/HoISubmod/gfx/interface/goals/HSM_CYA_test_focus.tga'
$spiritPng = Join-Path $fixture 'art/source/HSM_CYA_shared.png'
$spiritTga = Join-Path $fixture 'mod/HoISubmod/gfx/interface/ideas/HSM_CYA_shared.tga'
$focusGfxPath = Join-Path $fixture 'mod/HoISubmod/interface/focus/HSM_CYA_focus.gfx'
$ideaPath = Join-Path $fixture 'mod/HoISubmod/common/ideas/HSM_CYA_ideas.txt'
$tests = [System.Collections.Generic.List[string]]::new()

function Put([string] $relative, [string] $content) {
    $path = Join-Path $fixture $relative
    [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($path)) | Out-Null
    [System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))
}

function Assert([bool] $condition, [string] $message) {
    if (-not $condition) { throw $message }
}

function Expect-Failure([scriptblock] $action, [string] $name) {
    $failed = $false
    $before = [System.IO.File]::ReadAllText($manifestPath)
    $beforeTime = [System.IO.File]::GetLastWriteTimeUtc($manifestPath)
    try { & $action | Out-Null } catch { $failed = $true }
    Assert $failed "Expected failure: $name"
    Assert ([System.IO.File]::ReadAllText($manifestPath) -ceq $before) "Failed operation modified manifest: $name"
    Assert ([System.IO.File]::GetLastWriteTimeUtc($manifestPath) -eq $beforeTime) "Failed operation touched manifest timestamp: $name"
    $tests.Add($name)
}

function Assert-ReadOnlyCheck([scriptblock] $action, [string] $name) {
    $before = [System.IO.File]::ReadAllText($manifestPath)
    $beforeTime = [System.IO.File]::GetLastWriteTimeUtc($manifestPath)
    & $action | Out-Null
    Assert ([System.IO.File]::ReadAllText($manifestPath) -ceq $before) "Successful check modified manifest: $name"
    Assert ([System.IO.File]::GetLastWriteTimeUtc($manifestPath) -eq $beforeTime) "Successful check touched manifest timestamp: $name"
    $tests.Add($name)
}

function Write-TestPng([string] $path, [int] $width, [int] $height, [int] $shade = 50,
    [bool] $alpha = $true) {
    Add-Type -AssemblyName System.Drawing
    $bitmap = [System.Drawing.Bitmap]::new($width, $height,
        [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try {
        $bitmap.SetPixel(0, 0, [System.Drawing.Color]::FromArgb(255, $shade, 80, 100))
        if ($alpha) { $bitmap.SetPixel(1, 0, [System.Drawing.Color]::Transparent) }
        else { $bitmap.SetPixel(1, 0, [System.Drawing.Color]::FromArgb(255, $shade, 80, 100)) }
        $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally { $bitmap.Dispose() }
}

function Write-TestTga([string] $path, [int] $width, [int] $height, [int] $shade = 50) {
    $bytes = [byte[]]::new(18 + 4 * $width * $height)
    $bytes[2] = 2
    $bytes[12] = [byte]($width -band 255)
    $bytes[13] = [byte]($width -shr 8)
    $bytes[14] = [byte]($height -band 255)
    $bytes[15] = [byte]($height -shr 8)
    $bytes[16] = 32
    $bytes[17] = 8
    $bytes[18] = [byte]$shade
    $bytes[21] = 255
    [System.IO.File]::WriteAllBytes($path, $bytes)
}

$focusText = @'
shared_focus = {
    id = HSM_CYA_test_focus
    icon = GFX_HSM_CYA_test_focus
}
shared_focus = {
    id = HSM_CYA_second_focus
    icon = GFX_goal_generic_army_doctrines
}
'@
$focusGfx = @'
spriteTypes = {
    spriteType = {
        name = GFX_HSM_CYA_test_focus
        textureFile = "gfx/interface/goals/HSM_CYA_test_focus.tga"
    }
}
'@
$ideasText = @'
ideas = {
    country = {
        # HSM_CYA_comment_fake = { picture = HSM_CYA_shared }
        HSM_CYA_first_idea = {
            allowed = { nested = { HSM_CYA_nested_fake = { picture = wrong } } }
            removal_cost = -1
            picture = HSM_CYA_shared
        }
        HSM_CYA_second_idea = {
            picture = HSM_CYA_shared
            modifier = { stability_factor = 0.01 }
        }
    }
}
'@
$ideaGfx = @'
spriteTypes = {
    spriteType = {
        name = GFX_idea_HSM_CYA_shared
        textureFile = "gfx/interface/ideas/HSM_CYA_shared.tga"
    }
}
'@
$dynamicText = @'
HSM_CYA_industrial_program_dynamic_modifier = {
    icon = GFX_idea_HSM_CYA_industrial_program
}
HSM_CYA_military_program_dynamic_modifier = {
    icon = GFX_idea_HSM_CYA_military_program
}
HSM_CYA_imperial_legitimacy_dynamic_modifier = {
    icon = GFX_idea_HSM_CYA_imperial_legitimacy
}
'@

try {
    [System.IO.Directory]::CreateDirectory($fixture) | Out-Null
    Put 'mod/HoISubmod/common/national_focus/CYA.txt' $focusText
    Put 'mod/HoISubmod/common/national_focus/HSM_CYA_development.txt' ''
    Put 'mod/HoISubmod/common/national_focus/HSM_CYA_development_expansion.txt' ''
    Put 'mod/HoISubmod/interface/focus/HSM_CYA_focus.gfx' $focusGfx
    Put 'mod/HoISubmod/common/ideas/HSM_CYA_ideas.txt' $ideasText
    Put 'mod/HoISubmod/interface/ideas/HSM_CYA_ideas.gfx' $ideaGfx
    Put 'mod/HoISubmod/common/dynamic_modifiers/HSM_CYA_dynamic_modifiers.txt' $dynamicText
    Put 'mod/HoISubmod/localisation/english/hsm_cyanolisia_l_english.yml' @'
 HSM_CYA_test_focus:0 "Test Focus"
 HSM_CYA_second_focus:0 "Second Focus"
 HSM_CYA_first_idea:0 "First Idea"
 HSM_CYA_second_idea:0 "Second Idea"
'@
    Put 'EaW/localisation/english/country_CYA_l_english.yml' ''
    Put 'art/README.md' '# Test source notes'
    foreach ($path in @($focusPng, $focusTga, $spiritPng, $spiritTga)) {
        [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($path)) | Out-Null
    }

    function Restore-Assets {
        Write-TestPng $focusPng 99 86
        Write-TestTga $focusTga 99 86
        Write-TestPng $spiritPng 64 64
        Write-TestTga $spiritTga 64 64
    }
    Restore-Assets

    function New-Baseline {
        $pngHash = (Get-FileHash -LiteralPath $focusPng -Algorithm SHA256).Hash.ToLowerInvariant()
        $tgaHash = (Get-FileHash -LiteralPath $focusTga -Algorithm SHA256).Hash.ToLowerInvariant()
        $lines = @(
            '# Fixture',
            '## Inventory',
            'Inventory status: Focuses: 2; DONE=1; NEEDS_REVIEW=0; NEEDS_FIX=0; MISSING=1; NOT_REQUIRED=0',
            '| ID | Focus name | Def | PNG source | In-game TGA | Current GFX | Status | References | Composition / heraldry | Defect / next | QA PNG SHA-256 | QA TGA SHA-256 | Technical |',
            '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |',
            "| ``HSM_CYA_test_focus`` | Test Focus | CYA | ``art/source/HSM_CYA_test_focus.png`` | ``mod/HoISubmod/gfx/interface/goals/HSM_CYA_test_focus.tga`` | ``GFX_HSM_CYA_test_focus`` | DONE | Manual heraldry reference | Manual composition note | Artist approved this version. | ``$pngHash`` | ``$tgaHash`` | valid |",
            '| `HSM_CYA_second_focus` | Second Focus | CYA | `art/source/HSM_CYA_second_focus.png` | `mod/HoISubmod/gfx/interface/goals/HSM_CYA_second_focus.tga` | `GFX_goal_generic_army_doctrines` | MISSING | Manual border reference | Distinct border motif. | Generate later. | `-` | `-` | - |',
            '## Audit history',
            'Fixture history.',
            '<!-- BEGIN SPIRIT INVENTORY -->',
            'Spirit inventory status: Ideas: 2 uses; DONE=0; NEEDS_REVIEW=2; NEEDS_FIX=0; MISSING=0; NOT_REQUIRED=0',
            '| Idea ID | Name | Current picture | PNG source | In-game TGA | GFX | Status | References | Composition / heraldry | Defect / next | QA PNG SHA-256 | QA TGA SHA-256 | Technical |',
            '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |',
            '| `HSM_CYA_first_idea` | First Idea | `HSM_CYA_shared` | `art/source/HSM_CYA_shared.png` | `mod/HoISubmod/gfx/interface/ideas/HSM_CYA_shared.tga` | `GFX_idea_HSM_CYA_shared` | NEEDS_REVIEW | First use reference | First use art note. | Review first use. | `-` | `-` | valid |',
            '| `HSM_CYA_second_idea` | Second Idea | `HSM_CYA_shared` | `art/source/HSM_CYA_shared.png` | `mod/HoISubmod/gfx/interface/ideas/HSM_CYA_shared.tga` | `GFX_idea_HSM_CYA_shared` | NEEDS_REVIEW | Second use reference | Second use art note. | Review second use. | `-` | `-` | valid |',
            '<!-- END SPIRIT INVENTORY -->'
        )
        return ($lines -join "`n") + "`n"
    }
    $baseline = New-Baseline
    function Reset-Fixture {
        Restore-Assets
        Put 'docs/icon-generation-manifest.md' $baseline
        Put 'mod/HoISubmod/common/national_focus/CYA.txt' $focusText
        [System.IO.File]::WriteAllText($focusGfxPath, $focusGfx, [System.Text.UTF8Encoding]::new($false))
        [System.IO.File]::WriteAllText((Join-Path $fixture 'mod/HoISubmod/interface/ideas/HSM_CYA_ideas.gfx'),
            $ideaGfx, [System.Text.UTF8Encoding]::new($false))
        [System.IO.File]::WriteAllText($ideaPath, $ideasText, [System.Text.UTF8Encoding]::new($false))
    }
    Reset-Fixture

    Assert-ReadOnlyCheck { & $focusScript -RepositoryRoot $fixture -Check } 'focus -Check success is read-only'
    Assert-ReadOnlyCheck { & $spiritScript -RepositoryRoot $fixture -Check } 'spirit -Check success is read-only'
    $before = [System.IO.File]::GetLastWriteTimeUtc($manifestPath)
    & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus | Out-Null
    & $spiritScript -RepositoryRoot $fixture -IdeaIds HSM_CYA_first_idea | Out-Null
    Assert ([System.IO.File]::ReadAllText($manifestPath) -ceq $baseline) 'No-op sync changed manifest text.'
    Assert ([System.IO.File]::GetLastWriteTimeUtc($manifestPath) -eq $before) 'No-op sync touched manifest timestamp.'
    $tests.Add('no-op sync and both read-only checks')

    Reset-Fixture
    Write-TestPng $focusPng 99 86 75
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -Check } 'PNG drift detected by -Check'
    & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus | Out-Null
    $content = [System.IO.File]::ReadAllText($manifestPath)
    Assert ($content -match 'HSM_CYA_test_focus.*?\| NEEDS_REVIEW \|.*?PNG SHA-256 changed') 'PNG drift did not demote DONE.'
    Assert ($content.Contains('Artist approved this version.')) 'PNG drift erased approval note.'
    $tests.Add('PNG replacement demotes DONE')

    Reset-Fixture
    Write-TestTga $focusTga 99 86 75
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -Check } 'TGA drift detected by -Check'
    & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus | Out-Null
    Assert ([System.IO.File]::ReadAllText($manifestPath) -match 'HSM_CYA_test_focus.*?\| NEEDS_REVIEW \|.*?TGA SHA-256 changed') 'TGA drift did not demote DONE.'
    $tests.Add('TGA replacement demotes DONE')

    Reset-Fixture
    $approvedPngHash = (Get-FileHash -LiteralPath $focusPng -Algorithm SHA256).Hash.ToLowerInvariant()
    Put 'docs/icon-generation-manifest.md' ($baseline.Replace($approvedPngHash, 'invalid-hash'))
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -Check } 'invalid approval hash rejected by -Check'

    Reset-Fixture
    Remove-Item -LiteralPath $focusPng -Force
    & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus | Out-Null
    Assert ([System.IO.File]::ReadAllText($manifestPath) -match 'HSM_CYA_test_focus.*?\| NEEDS_FIX \|.*?Source PNG missing') 'Missing confirmed PNG did not become NEEDS_FIX.'
    $tests.Add('missing confirmed asset becomes NEEDS_FIX')

    Reset-Fixture
    $broken = $baseline.Replace('| DONE | Manual heraldry reference | Manual composition note | Artist approved this version.',
        '| NEEDS_FIX | Manual heraldry reference | Manual composition note | Human hand artifact; repaint before approval.')
    $broken = $broken.Replace('DONE=1; NEEDS_REVIEW=0; NEEDS_FIX=0; MISSING=1', 'DONE=0; NEEDS_REVIEW=0; NEEDS_FIX=1; MISSING=1')
    [System.IO.File]::WriteAllText($manifestPath, $broken, [System.Text.UTF8Encoding]::new($false))
    & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus | Out-Null
    Assert ([System.IO.File]::ReadAllText($manifestPath) -match 'HSM_CYA_test_focus.*?\| NEEDS_FIX \|.*?Human hand artifact') 'Artistic NEEDS_FIX was lost.'
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus -MarkDone } 'NEEDS_FIX needs explicit resolution'
    & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus -ResolveFix | Out-Null
    $resolved = [System.IO.File]::ReadAllText($manifestPath)
    Assert ($resolved -match 'HSM_CYA_test_focus.*?\| NEEDS_REVIEW \|.*?Resolved \d{4}-\d\d-\d\d: Human hand artifact; repaint before approval.; Next: Confirm repaired art') 'ResolveFix did not separate historical defect from next action.'
    Assert ($resolved -notmatch 'Next: Human hand artifact') 'Resolved defect remains active.'
    $tests.Add('artistic NEEDS_FIX preserved until explicit resolution')

    & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus -MarkDone | Out-Null
    $approved = [System.IO.File]::ReadAllText($manifestPath)
    Assert ($approved -match 'Resolved \d{4}-\d\d-\d\d: Human hand artifact.*?Next: Visual QA confirmed') 'Reapproval erased resolution history or left stale next action.'
    $tests.Add('resolved feedback survives later approval')

    $cycleTwo = $approved.Replace('Next: Visual QA confirmed; PNG/TGA/GFX validated.',
        'Active: Empty wax seal; repaint before approval.; Next: Repaint seal.')
    $cycleTwo = $cycleTwo.Replace('DONE=1; NEEDS_REVIEW=0; NEEDS_FIX=0; MISSING=1',
        'DONE=0; NEEDS_REVIEW=0; NEEDS_FIX=1; MISSING=1')
    $cycleTwo = $cycleTwo.Replace('| DONE | Manual heraldry reference | Manual composition note |',
        '| NEEDS_FIX | Manual heraldry reference | Manual composition note |')
    [System.IO.File]::WriteAllText($manifestPath, $cycleTwo, [System.Text.UTF8Encoding]::new($false))
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus -MarkDone } 'second defect requires explicit repair'
    & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus -ResolveFix | Out-Null
    $twiceResolved = [System.IO.File]::ReadAllText($manifestPath)
    $focusRow = @($twiceResolved -split "`n" | Where-Object { $_ -match '^\| `HSM_CYA_test_focus` \|' })[0]
    Assert ($focusRow -match 'Resolved \d{4}-\d\d-\d\d: Human hand artifact.*Resolved \d{4}-\d\d-\d\d: Empty wax seal') 'Two defect histories were not preserved.'
    Assert ($focusRow -match '\| NEEDS_REVIEW \|' -and $focusRow -notmatch '\| DONE \|') 'Second repair was silently approved.'
    Assert ([regex]::Matches($focusRow, '; Next: ').Count -eq 1) 'Second repair retained multiple active next actions.'
    Assert ($focusRow -match '; Next: Confirm repaired art') 'Second repair has wrong next action.'
    & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus -MarkDone | Out-Null
    $reapproved = [System.IO.File]::ReadAllText($manifestPath)
    Assert ($reapproved -match 'Empty wax seal.*?Next: Visual QA confirmed' -and $reapproved -match 'HSM_CYA_test_focus.*?\| DONE \|') 'Explicit second approval did not complete.'
    $tests.Add('two artistic repair cycles retain history and require reapproval')

    Reset-Fixture
    & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus | Out-Null
    Assert ([System.IO.File]::ReadAllText($manifestPath) -match 'HSM_CYA_second_focus.*?\| MISSING \| Manual border reference \| Distinct border motif') 'Other focus row changed.'
    & $spiritScript -RepositoryRoot $fixture -IdeaIds HSM_CYA_first_idea -MarkDone | Out-Null
    $content = [System.IO.File]::ReadAllText($manifestPath)
    Assert ($content -match 'HSM_CYA_first_idea.*?\| DONE \|') 'First shared use was not approved.'
    Assert ($content -match 'HSM_CYA_second_idea.*?\| NEEDS_REVIEW \| Second use reference \| Second use art note') 'Second shared use lost its separate review.'
    & $spiritScript -RepositoryRoot $fixture -Check | Out-Null
    $tests.Add('single-ID updates and shared asset with distinct review notes')

    Write-TestTga $spiritTga 64 64 75
    Expect-Failure { & $spiritScript -RepositoryRoot $fixture -Check } 'shared TGA drift detected'
    & $spiritScript -RepositoryRoot $fixture -IdeaIds HSM_CYA_first_idea | Out-Null
    $content = [System.IO.File]::ReadAllText($manifestPath)
    Assert ($content -match 'HSM_CYA_first_idea.*?\| NEEDS_REVIEW \|.*?valid; TGA SHA-256 changed') 'Shared TGA drift did not demote approved use.'
    Assert ($content -match 'HSM_CYA_second_idea.*?\| NEEDS_REVIEW \| Second use reference') 'Shared TGA drift overwrote other use.'
    & $spiritScript -RepositoryRoot $fixture -Check | Out-Null
    $tests.Add('shared TGA drift preserves per-use review')

    Reset-Fixture
    & $spiritScript -RepositoryRoot $fixture -IdeaIds HSM_CYA_first_idea -MarkDone | Out-Null
    Write-TestPng $spiritPng 64 64 75
    Expect-Failure { & $spiritScript -RepositoryRoot $fixture -Check } 'shared PNG drift detected'
    & $spiritScript -RepositoryRoot $fixture -IdeaIds HSM_CYA_first_idea | Out-Null
    $content = [System.IO.File]::ReadAllText($manifestPath)
    Assert ($content -match 'HSM_CYA_first_idea.*?\| NEEDS_REVIEW \|.*?valid; PNG SHA-256 changed') 'Shared PNG drift did not demote approved use.'
    Assert ($content -match 'HSM_CYA_second_idea.*?\| NEEDS_REVIEW \| Second use reference \| Second use art note\. \| Review second use\.') 'Shared PNG drift overwrote independent review.'
    & $spiritScript -RepositoryRoot $fixture -Check | Out-Null
    $tests.Add('shared PNG drift preserves per-use review')

    [System.IO.File]::WriteAllBytes($spiritPng, [byte[]](137,80,78,71,13,10,26,10,1,2,3))
    Expect-Failure { & $spiritScript -RepositoryRoot $fixture -Check } 'shared corrupt PNG detected'
    Expect-Failure { & $spiritScript -RepositoryRoot $fixture -IdeaIds HSM_CYA_first_idea } 'shared corrupt PNG requires both IdeaIds'
    & $spiritScript -RepositoryRoot $fixture -IdeaIds HSM_CYA_first_idea,HSM_CYA_second_idea | Out-Null
    $content = [System.IO.File]::ReadAllText($manifestPath)
    Assert ($content -match 'HSM_CYA_first_idea.*?\| NEEDS_FIX \|.*?Source PNG cannot be decoded') 'First shared use missed PNG failure.'
    Assert ($content -match 'HSM_CYA_second_idea.*?\| NEEDS_FIX \|.*?Source PNG cannot be decoded') 'Second shared use missed PNG failure.'
    $tests.Add('shared PNG technical failure synchronized across uses')

    Reset-Fixture
    Put 'mod/HoISubmod/common/ideas/HSM_CYA_ideas.txt' @'
ideas={ country={
  # HSM_CYA_comment_fake={picture=HSM_CYA_shared}
  HSM_CYA_first_idea={ modifier={ HSM_CYA_nested_fake={picture=wrong} }
    allowed={always=no} # picture = wrong
    picture = HSM_CYA_shared }
  HSM_CYA_second_idea = {
    removal_cost = -1
    # quoted braces must not create ideas
    picture=HSM_CYA_shared
  }
}}
'@
    & $spiritScript -RepositoryRoot $fixture -Check | Out-Null
    $tests.Add('Clausewitz spacing, comments, nested blocks, delayed picture')

    Reset-Fixture
    Put 'mod/HoISubmod/common/national_focus/CYA.txt' @'
# shared_focus = { id = HSM_CYA_comment_fake icon = wrong }
shared_focus = {
    text = "shared_focus = { id = HSM_CYA_string_fake icon = wrong }"
    nested = { id = HSM_CYA_nested_fake icon = wrong }
    icon = "GFX_HSM_CYA_test_focus" # icon = wrong
    id = HSM_CYA_test_focus
}
shared_focus={id=HSM_CYA_second_focus icon=GFX_goal_generic_army_doctrines}
'@
    & $focusScript -RepositoryRoot $fixture -Check | Out-Null
    $tests.Add('focus parser ignores comments, strings and nested fields')

    Reset-Fixture
    [System.IO.File]::WriteAllBytes($focusPng, [byte[]](137,80,78,71,13,10,26,10,1,2,3))
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -Check } 'corrupt PNG rejected by check'
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus -MarkDone } 'corrupt PNG cannot be approved'
    & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus | Out-Null
    Assert ([System.IO.File]::ReadAllText($manifestPath) -match 'HSM_CYA_test_focus.*?\| NEEDS_FIX \|.*?Source PNG cannot be decoded') 'Corrupt PNG did not become NEEDS_FIX.'
    $tests.Add('corrupt PNG becomes NEEDS_FIX')

    Reset-Fixture
    Write-TestPng $focusPng 20 20
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -Check } 'undersized PNG rejected'
    Reset-Fixture
    Write-TestPng $focusPng 99 86 50 $false
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -Check } 'opaque PNG rejected'

    Reset-Fixture
    $badTga = [System.IO.File]::ReadAllBytes($focusTga)
    $badTga[16] = 24
    [System.IO.File]::WriteAllBytes($focusTga, $badTga)
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -Check } 'invalid TGA rejected by check'
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus -MarkDone } 'invalid TGA cannot be approved'

    Reset-Fixture
    Remove-Item -LiteralPath $spiritPng -Force
    Expect-Failure { & $spiritScript -RepositoryRoot $fixture -Check } 'missing spirit source rejected'
    Expect-Failure { & $spiritScript -RepositoryRoot $fixture -IdeaIds HSM_CYA_first_idea,HSM_CYA_second_idea -MarkDone } 'missing spirit source cannot be approved'

    Reset-Fixture
    Put 'mod/HoISubmod/common/national_focus/CYA.txt' ($focusText + $focusText)
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -Check } 'duplicate focus definition rejected'
    Reset-Fixture
    Put 'mod/HoISubmod/common/ideas/HSM_CYA_ideas.txt' ($ideasText.Replace('HSM_CYA_second_idea = {', 'HSM_CYA_first_idea = {'))
    Expect-Failure { & $spiritScript -RepositoryRoot $fixture -Check } 'duplicate idea definition rejected'

    Reset-Fixture
    Put 'docs/icon-generation-manifest.md' ($baseline.Replace('Manual composition note |', 'Manual composition note | unexpected |'))
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -Check } 'malformed focus manifest row rejected'
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus } 'malformed focus row blocks sync'
    Reset-Fixture
    Put 'docs/icon-generation-manifest.md' ($baseline.Replace('Second use art note. |', 'Second use art note. | unexpected |'))
    Expect-Failure { & $spiritScript -RepositoryRoot $fixture -Check } 'malformed spirit manifest row rejected'

    Reset-Fixture
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_unknown } 'unknown focus ID rejected'
    Expect-Failure { & $spiritScript -RepositoryRoot $fixture -IdeaIds HSM_CYA_unknown } 'unknown idea ID rejected'

    Reset-Fixture
    [System.IO.File]::WriteAllText($focusGfxPath, $focusGfx.Replace('HSM_CYA_test_focus.tga', 'missing_texture.tga'))
    Expect-Failure { & $focusScript -RepositoryRoot $fixture -Check } 'broken GFX detected'
    & $focusScript -RepositoryRoot $fixture -FocusIds HSM_CYA_test_focus | Out-Null
    Assert ([System.IO.File]::ReadAllText($manifestPath) -match 'HSM_CYA_test_focus.*?\| NEEDS_FIX \|') 'Broken GFX did not become NEEDS_FIX.'
    $tests.Add('missing GFX texture becomes NEEDS_FIX')

    Reset-Fixture
    $ideaGfxPath = Join-Path $fixture 'mod/HoISubmod/interface/ideas/HSM_CYA_ideas.gfx'
    [System.IO.File]::WriteAllText($ideaGfxPath, $ideaGfx.Replace('HSM_CYA_shared.tga', 'missing_spirit.tga'))
    Expect-Failure { & $spiritScript -RepositoryRoot $fixture -Check } 'broken spirit GFX detected'
    Expect-Failure { & $spiritScript -RepositoryRoot $fixture -IdeaIds HSM_CYA_first_idea } 'shared technical defect requires both IdeaIds'
    & $spiritScript -RepositoryRoot $fixture -IdeaIds HSM_CYA_first_idea,HSM_CYA_second_idea | Out-Null
    Assert ([System.IO.File]::ReadAllText($manifestPath) -match 'HSM_CYA_first_idea.*?\| NEEDS_FIX \|') 'Broken spirit GFX did not become NEEDS_FIX.'
    Assert ([System.IO.File]::ReadAllText($manifestPath) -match 'HSM_CYA_second_idea.*?\| NEEDS_FIX \|') 'Shared technical state was not synchronized.'
    $tests.Add('missing spirit GFX texture becomes NEEDS_FIX')

    Reset-Fixture
    $legacy = $baseline -replace ' \| QA PNG SHA-256 \| QA TGA SHA-256 \| Technical \|', ' |'
    $legacy = $legacy -replace '(?m)(\| Defect / next \|)(?: --- \|){3}', '$1'
    $legacyLines = @($legacy -split "`n" | ForEach-Object {
        if ($_ -match '^\| `HSM_CYA_') {
            $parts = @($_.Trim().Trim('|').Split('|') | ForEach-Object { $_.Trim() })
            if ($parts.Count -eq 13) { '| ' + (($parts[0..9]) -join ' | ') + ' |' } else { $_ }
        } elseif ($_ -match '^\| --- \|') {
            '| ' + ((@('---') * 10) -join ' | ') + ' |'
        } else { $_ }
    })
    $legacy = $legacyLines -join "`n"
    [System.IO.File]::WriteAllText($manifestPath, $legacy, [System.Text.UTF8Encoding]::new($false))
    & $focusScript -RepositoryRoot $fixture -MigrateHashes | Out-Null
    & $spiritScript -RepositoryRoot $fixture -MigrateHashes | Out-Null
    & $focusScript -RepositoryRoot $fixture -Check | Out-Null
    & $spiritScript -RepositoryRoot $fixture -Check | Out-Null
    Assert ([System.IO.File]::ReadAllText($manifestPath) -match 'HSM_CYA_test_focus.*?\| DONE \|.*?[0-9a-f]{64}') 'Hash migration reset DONE.'
    $tests.Add('one-time checksum migration preserves DONE')

    Reset-Fixture
    Assert-ReadOnlyCheck { & $focusScript -RepositoryRoot $fixture -Check } 'repeated focus -Check read-only'
    Assert-ReadOnlyCheck { & $spiritScript -RepositoryRoot $fixture -Check } 'repeated spirit -Check read-only'
    $tests.Add('repeated -Check is read-only')

    $tests | ForEach-Object { Write-Output "PASS $_" }
    Write-Output "Passed $($tests.Count) manifest scenarios."
} finally {
    $resolved = [System.IO.Path]::GetFullPath($fixture)
    if (-not $resolved.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
        [System.IO.Path]::GetFileName($resolved) -notlike 'cya-icon-manifest-test-*') {
        throw "Unsafe test cleanup path: $resolved"
    }
    if ([System.IO.Directory]::Exists($resolved)) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
