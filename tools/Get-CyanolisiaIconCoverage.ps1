param([switch] $ListPending)

$root = Split-Path -Parent $PSScriptRoot
$focusFiles = @(
    'mod/HoISubmod/common/national_focus/CYA.txt',
    'mod/HoISubmod/common/national_focus/HSM_CYA_development.txt',
    'mod/HoISubmod/common/national_focus/HSM_CYA_development_expansion.txt'
)
$focuses = foreach ($file in $focusFiles) {
    $content = [System.IO.File]::ReadAllText((Join-Path $root $file))
    foreach ($match in [regex]::Matches($content, '(?ms)^shared_focus\s*=\s*\{(.*?)(?=^shared_focus\s*=\s*\{|\z)')) {
        $body = $match.Groups[1].Value
        $id = [regex]::Match($body, '(?m)^\s*id\s*=\s*(\w+)').Groups[1].Value
        $icon = [regex]::Match($body, '(?m)^\s*icon\s*=\s*(\w+)').Groups[1].Value
        [pscustomobject]@{ Type = 'Focus'; Id = $id; CurrentIcon = $icon; Custom = $icon.StartsWith('GFX_HSM_CYA_'); File = $file }
    }
}

$ideaFile = 'mod/HoISubmod/common/ideas/HSM_CYA_ideas.txt'
$ideaContent = [System.IO.File]::ReadAllText((Join-Path $root $ideaFile))
$ideas = foreach ($match in [regex]::Matches($ideaContent, '(?m)^\t\t(HSM_CYA_\w+)\s*=\s*\{\s*picture\s*=\s*(\w+)')) {
    $id = $match.Groups[1].Value
    $picture = $match.Groups[2].Value
    [pscustomobject]@{ Type = 'Idea'; Id = $id; CurrentIcon = $picture; Custom = $picture.StartsWith('HSM_CYA_'); File = $ideaFile }
}

$customFocuses = @($focuses | Where-Object Custom).Count
$customIdeas = @($ideas | Where-Object Custom).Count
Write-Output "Focuses: $customFocuses / $(@($focuses).Count) custom"
Write-Output "Ideas: $customIdeas / $(@($ideas).Count) custom uses"

if ($ListPending) {
    @($focuses) + @($ideas) | Where-Object { -not $_.Custom } | Sort-Object Type, Id | Format-Table Type, Id, CurrentIcon, File -AutoSize
}
