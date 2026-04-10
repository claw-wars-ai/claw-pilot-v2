param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$RetrievedDirName = 'retrieved-pilot-2026-04-10',
    [string]$BundleDirName = 'escalation-review-2026-04-10'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Utf8File {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [AllowEmptyCollection()]
        [AllowEmptyString()]
        [string[]]$Lines
    )

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }

    $content = ($Lines -join [Environment]::NewLine) + [Environment]::NewLine
    [System.IO.File]::WriteAllText($Path, $content, [System.Text.UTF8Encoding]::new($false))
}

function Get-RelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Base,
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $baseUri = [System.Uri]((Resolve-Path $Base).Path + [IO.Path]::DirectorySeparatorChar)
    $pathUri = [System.Uri](Resolve-Path $Path).Path
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($pathUri).ToString()).Replace('/', '\')
}

$projectRoot = (Resolve-Path $ProjectRoot).Path
$retrievedDir = Join-Path $projectRoot $RetrievedDirName
$bundleDir = Join-Path $projectRoot $BundleDirName
$rootDocsDir = Join-Path $bundleDir 'root-handoff'
$runtimeDocsDir = Join-Path $bundleDir 'runtime-artifacts'
$archivePath = Join-Path $projectRoot ($BundleDirName + '.zip')

if (-not (Test-Path $retrievedDir)) {
    throw "Retrieved artifact directory not found: $retrievedDir"
}

if (Test-Path $bundleDir) {
    Remove-Item -LiteralPath $bundleDir -Recurse -Force
}

if (Test-Path $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}

New-Item -ItemType Directory -Path $rootDocsDir | Out-Null
New-Item -ItemType Directory -Path $runtimeDocsDir | Out-Null

$rootDocs = @(
    'README.md',
    'OBJECTIVE.md',
    'REVIEWER_PROMPT.md',
    'SESSION.md',
    'heartbeat.sh',
    'JOURNEY.md',
    'RESOURCES.md',
    'TOOL_GRANTS.md',
    'OPERATOR_LOG.md'
)

foreach ($doc in $rootDocs) {
    $source = Join-Path $projectRoot $doc
    if (Test-Path $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $rootDocsDir $doc)
    }
}

Get-ChildItem -LiteralPath $retrievedDir -File | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $runtimeDocsDir $_.Name)
}

$runtimeFiles = Get-ChildItem -LiteralPath $runtimeDocsDir -File | Sort-Object Name
$planFiles = $runtimeFiles | Where-Object { $_.Name -like 'HB*_PLAN.md' } | Sort-Object {
    [int]([regex]::Match($_.BaseName, 'HB(\d+)_').Groups[1].Value)
}
$executionFiles = $runtimeFiles | Where-Object { $_.Name -like 'HB*_EXECUTION.md' } | Sort-Object {
    [int]([regex]::Match($_.BaseName, 'HB(\d+)_').Groups[1].Value)
}

$indexLines = @(
    '# Pilot Escalation Bundle',
    '',
    'This bundle collates the local handoff docs and the runtime artifacts retrieved from the Minisforum host on 2026-04-10.',
    '',
    '## Purpose',
    '',
    '- Give an escalation reviewer one place to inspect source documents, runtime logs, and the final state.',
    '- Preserve both the stale handoff copy and the authoritative runtime copy for comparison.',
    '- Provide a single consolidated dossier for LLM review without losing raw evidence.',
    '',
    '## Bundle Layout',
    '',
    '- `root-handoff/`: the local handoff docs that were present before SSH retrieval.',
    '- `runtime-artifacts/`: the authoritative docs copied from `~/claw-pilot/pilot-workspace/` and `~/claw-pilot/heartbeat.log` on the Minisforum host.',
    '- `PILOT_DOSSIER.md`: concatenated review packet with the key docs and the full heartbeat chronology.',
    '- `ESCALATION_PROMPT.md`: a ready-to-use prompt for another LLM.',
    '',
    '## Final Run State',
    '',
    '- Gates: `G1 PASS | G2 PASS | G3 FAIL | G4 FAIL`.',
    '- Verified users: `0 / 10`.',
    '- Live product URL: `https://jdsteel61.github.io/pilot-image-resizer-site/`.',
    '- Build outcome: product shipped; distribution and verification failed.',
    '',
    '## Key Runtime Risks To Review',
    '',
    '- Repeated `openclaw: command not found` failures during early cron heartbeats.',
    '- Surge deployment failed and required operator remediation to GitHub Pages.',
    '- Reviewer auth failed at HB8 because `XAI_API_KEY` was not set.',
    '- `heartbeat.sh` crashed at line 235 during HB14 and HB15 while parsing a tool request.',
    '- Multiple later heartbeats produced approved drafts but no posting proof.',
    '',
    '## Runtime Artifact Inventory',
    ''
)

foreach ($file in $runtimeFiles) {
    $relative = Get-RelativePath -Base $bundleDir -Path $file.FullName
    $indexLines += ('- `{0}` ({1} bytes)' -f $relative.Replace('\', '/'), $file.Length)
}

$promptLines = @(
    '# Escalation Prompt',
    '',
    'Use the bundle contents to perform an escalation review of the Claw Pilot run.',
    '',
    'Required outputs:',
    '- State the true final result in plain terms.',
    '- Separate build success from growth/distribution failure.',
    '- Identify the top 5 process or infra failures that most reduced the chance of success.',
    '- Recommend concrete fixes, ordered by likely impact.',
    '- Call out which fixes are product changes, orchestration changes, operator-policy changes, or measurement changes.',
    '- Highlight any places where the documentation disagrees with the runtime evidence.',
    '',
    'Constraints:',
    '- Prefer authoritative runtime docs in `runtime-artifacts/` over the stale local handoff copy in `root-handoff/` when they conflict.',
    '- Treat approved outreach drafts as drafts unless there is explicit posting evidence.',
    '- Quote filenames and line numbers when making claims.',
    '',
    'Suggested reading order:',
    '1. `PILOT_DOSSIER.md`',
    '2. `runtime-artifacts/RESOURCES.md`',
    '3. `runtime-artifacts/HB20_EXECUTION.md`',
    '4. `runtime-artifacts/heartbeat.log`',
    '5. `runtime-artifacts/TOOL_GRANTS.md`',
    '6. `runtime-artifacts/OPERATOR_LOG.md`'
)

$dossierLines = @(
    '# Pilot Dossier',
    '',
    'This file consolidates the pilot documents most useful for escalation review.',
    '',
    '## Reading Order',
    '',
    '1. Final state and logs',
    '2. Operator and reviewer decisions',
    '3. Heartbeat chronology',
    '4. Original handoff docs',
    '',
    '## Final State Snapshot',
    ''
)

$snapshotFiles = @(
    'RESOURCES.md',
    'JOURNEY.md',
    'TOOL_GRANTS.md',
    'OPERATOR_LOG.md',
    'OUTBOX.md',
    'heartbeat.log'
)

foreach ($name in $snapshotFiles) {
    $path = Join-Path $runtimeDocsDir $name
    if (Test-Path $path) {
        $dossierLines += "### runtime-artifacts/$name"
        $dossierLines += ''
        $dossierLines += '```text'
        $dossierLines += Get-Content -LiteralPath $path
        $dossierLines += '```'
        $dossierLines += ''
    }
}

$dossierLines += '## Heartbeat Chronology'
$dossierLines += ''

foreach ($plan in $planFiles) {
    $number = [regex]::Match($plan.BaseName, 'HB(\d+)_').Groups[1].Value
    $execution = Join-Path $runtimeDocsDir ("HB{0}_EXECUTION.md" -f $number)

    $dossierLines += "### HB$number Plan"
    $dossierLines += ''
    $dossierLines += '```text'
    $dossierLines += Get-Content -LiteralPath $plan.FullName
    $dossierLines += '```'
    $dossierLines += ''

    if (Test-Path $execution) {
        $dossierLines += "### HB$number Execution"
        $dossierLines += ''
        $dossierLines += '```text'
        $dossierLines += Get-Content -LiteralPath $execution
        $dossierLines += '```'
        $dossierLines += ''
    }
}

$dossierLines += '## Runtime Orchestrator'
$dossierLines += ''
$remoteHeartbeat = Join-Path $runtimeDocsDir 'heartbeat.remote.sh'
if (Test-Path $remoteHeartbeat) {
    $dossierLines += '```bash'
    $dossierLines += Get-Content -LiteralPath $remoteHeartbeat
    $dossierLines += '```'
    $dossierLines += ''
}

$dossierLines += '## Original Local Handoff Docs'
$dossierLines += ''

foreach ($doc in (Get-ChildItem -LiteralPath $rootDocsDir -File | Sort-Object Name)) {
    $dossierLines += "### root-handoff/$($doc.Name)"
    $dossierLines += ''
    $dossierLines += '```text'
    $dossierLines += Get-Content -LiteralPath $doc.FullName
    $dossierLines += '```'
    $dossierLines += ''
}

Write-Utf8File -Path (Join-Path $bundleDir 'INDEX.md') -Lines $indexLines
Write-Utf8File -Path (Join-Path $bundleDir 'ESCALATION_PROMPT.md') -Lines $promptLines
Write-Utf8File -Path (Join-Path $bundleDir 'PILOT_DOSSIER.md') -Lines $dossierLines

Compress-Archive -Path (Join-Path $bundleDir '*') -DestinationPath $archivePath -CompressionLevel Optimal

Write-Output "Bundle created: $bundleDir"
Write-Output "Archive created: $archivePath"
