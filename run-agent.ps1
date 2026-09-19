<#
.SYNOPSIS
    Runs the J-WALT AI Business-Development Agent (Windows).

.DESCRIPTION
    Verifies the virtual environment exists, and for a real run: checks
    that ANTHROPIC_API_KEY and APOLLO_API_KEY are actually filled in inside
    .env (never reads or prints their values -- only checks a value is
    present), runs the live Anthropic smoke test, then the live Apollo
    smoke test, and only runs the agent itself if both succeed.

    Stops immediately at the first failed step. Never falls back to fake
    data if a credential or an API call fails. There is no send-email code
    anywhere in this project, in any mode.

.PARAMETER Objective
    Plain-language objective for the agent. Defaults to the project's
    standard first live test: 3 Dubai hotel leads.

.PARAMETER DryRun
    Run the safe, zero-cost, zero-credential dry-run instead of a real run.
    Skips the .env check and both smoke tests entirely -- dry-run works
    even with an empty or missing .env.

.PARAMETER NonInteractive
    Auto-reject any outreach-approval prompt instead of pausing for you at
    the keyboard. Nothing is ever sent either way.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File run-agent.ps1 -DryRun

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File run-agent.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File run-agent.ps1 -Objective "Find 5 Dubai retail companies opening new stores" -NonInteractive
#>

param(
    [string]$Objective = "Find 3 potential Dubai hotel clients for J-WALT",
    [switch]$DryRun,
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "    ERROR: $msg" -ForegroundColor Red }

$venvDir = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Fail "No virtual environment found at .venv\Scripts\python.exe"
    Write-Host "    Run setup.ps1 first (or double-click setup.bat)."
    exit 1
}

# ---------------------------------------------------------------------------
# Dry run: no credentials needed at all -- skip straight to it.
# ---------------------------------------------------------------------------
if ($DryRun) {
    Write-Step "Running DRY RUN"
    Write-Host "    No real API calls with real credentials required for this to work."
    Write-Host "    Every consequential line below is prefixed [DRY RUN]. Nothing is written"
    Write-Host "    to your real database and nothing is ever sent."
    & $venvPython -m src.main --dry-run
    exit $LASTEXITCODE
}

# ---------------------------------------------------------------------------
# Real run: verify .env actually has both keys filled in before doing anything.
# ---------------------------------------------------------------------------
Write-Step "Checking .env for required credentials"

$envPath = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envPath)) {
    Write-Fail ".env does not exist."
    Write-Host "    Run setup.ps1 first, then edit .env with your API keys."
    Write-Host "    Or run: .\run-agent.ps1 -DryRun   (no credentials needed at all)"
    exit 1
}

function Test-EnvKeySet([string]$Name, [string]$Path) {
    # Presence check ONLY -- reads .env to confirm a non-blank value exists
    # after "NAME=", but never captures, stores, or prints that value.
    $match = Select-String -Path $Path -Pattern "^\s*$Name\s*=\s*\S" -ErrorAction SilentlyContinue
    return [bool]$match
}

$missing = @()
if (-not (Test-EnvKeySet "ANTHROPIC_API_KEY" $envPath)) { $missing += "ANTHROPIC_API_KEY" }
if (-not (Test-EnvKeySet "APOLLO_API_KEY" $envPath))    { $missing += "APOLLO_API_KEY" }

if ($missing.Count -gt 0) {
    Write-Fail "Missing or blank in .env: $($missing -join ', ')"
    Write-Host "    Open .env in Notepad, fill these in, save, and run this script again."
    Write-Host "    Or run: .\run-agent.ps1 -DryRun   (no credentials needed at all)"
    exit 1
}
Write-Ok "ANTHROPIC_API_KEY and APOLLO_API_KEY are both present in .env."
Write-Host "    (This only checks that a value is present -- it never reads or displays the value.)"

# ---------------------------------------------------------------------------
# Smoke tests: cheapest possible live check for each credential, one at a time.
# ---------------------------------------------------------------------------
Write-Step "Running Anthropic smoke test (one tiny live completion)"
& $venvPython -m src.main --anthropic-smoke-test
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Anthropic smoke test failed -- see the error above."
    Write-Host "    Stopping here. Not proceeding to the Apollo test or the agent."
    exit 1
}

Write-Step "Running Apollo smoke test (one lookup, at most 1 credit)"
& $venvPython -m src.main --apollo-smoke-test
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Apollo smoke test failed -- see the error above."
    Write-Host "    Stopping here. Not proceeding to the agent."
    exit 1
}

# ---------------------------------------------------------------------------
# The real agent.
# ---------------------------------------------------------------------------
Write-Step "Both credentials verified live. Running the agent."
Write-Host "    Objective: $Objective"
if ($NonInteractive) {
    Write-Host "    Mode: non-interactive -- any outreach draft will be auto-rejected."
} else {
    Write-Host "    Mode: interactive -- you will be asked to [A]pprove / [R]eject / [E]dit"
    Write-Host "    each outreach draft. Type the letter and press Enter when prompted."
}
Write-Host "    Nothing this agent does can ever send an email -- there is no send code"
Write-Host "    anywhere in this project, regardless of what you approve."
Write-Host "    Every line below is prefixed [LIVE] where relevant -- this is real data."

$argsList = @("-m", "src.main", "--objective", $Objective)
if ($NonInteractive) { $argsList += "--non-interactive" }

& $venvPython @argsList
exit $LASTEXITCODE
