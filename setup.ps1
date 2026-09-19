<#
.SYNOPSIS
    One-time setup for the J-WALT AI Business-Development Agent on Windows.

.DESCRIPTION
    Checks for Python 3.11+ and Git, creates a virtual environment (.venv),
    installs dependencies, creates .env from .env.example if it doesn't
    already exist, verifies the project imports correctly, and runs the
    full test suite (no network access, no API credits used).

    Never writes an API key into any file itself -- .env is created empty
    (copied from .env.example) for you to fill in by hand. Never sends
    email. Never overwrites an existing .env.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File setup.ps1

    Or just double-click setup.bat, which runs exactly this command for you.
#>

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    WARNING: $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "    ERROR: $msg" -ForegroundColor Red }

$hadWarning = $false

# ---------------------------------------------------------------------------
Write-Step "Checking for Python 3.11+"

$pythonExe = $null
foreach ($candidate in @("python", "py")) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    try {
        $versionOutput = (& $candidate --version) 2>&1 | Out-String
        $versionOutput = $versionOutput.Trim()
    } catch {
        continue
    }
    if ($versionOutput -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -eq 3 -and $minor -ge 11) {
            $pythonExe = $candidate
            Write-Ok "$versionOutput (found via '$candidate')"
            break
        } else {
            Write-Warn "$versionOutput found via '$candidate', but this project needs Python 3.11 or newer."
        }
    }
}

if (-not $pythonExe) {
    Write-Fail "Python 3.11+ was not found on PATH."
    Write-Host "    Install it from https://www.python.org/downloads/"
    Write-Host "    IMPORTANT: check the 'Add python.exe to PATH' box on the first install screen."
    Write-Host "    Then close this window and run setup again."
    exit 1
}

# ---------------------------------------------------------------------------
Write-Step "Checking for Git (optional -- only needed to pull future updates)"

$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($gitCmd) {
    $gitVersion = (& git --version) 2>&1 | Out-String
    Write-Ok $gitVersion.Trim()
} else {
    Write-Warn "Git was not found on PATH. It is NOT required to run the agent from the files"
    Write-Warn "you already have, but you'll want it later to pull updates. Install from"
    Write-Warn "https://git-scm.com/download/win if you want that. Continuing without it."
    $hadWarning = $true
}

# ---------------------------------------------------------------------------
Write-Step "Creating the virtual environment (.venv)"

$venvDir = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (Test-Path $venvPython) {
    Write-Ok ".venv already exists -- reusing it."
} else {
    & $pythonExe -m venv $venvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPython)) {
        Write-Fail "Failed to create the virtual environment. See any error above."
        exit 1
    }
    Write-Ok "Created .venv"
}

# ---------------------------------------------------------------------------
Write-Step "Installing dependencies (this can take a minute or two)"

& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Dependency installation failed. Scroll up for the pip error above."
    exit 1
}
Write-Ok "Dependencies installed."

# ---------------------------------------------------------------------------
Write-Step "Setting up your .env file"

$envPath = Join-Path $PSScriptRoot ".env"
$envExamplePath = Join-Path $PSScriptRoot ".env.example"

if (Test-Path $envPath) {
    Write-Ok ".env already exists -- leaving it exactly as-is (this script never overwrites it)."
} else {
    Copy-Item $envExamplePath $envPath
    Write-Ok "Created .env from .env.example."
    Write-Warn "It still has BLANK API keys (ANTHROPIC_API_KEY and APOLLO_API_KEY)."
    Write-Warn "Opening it in Notepad now -- fill both in, then save and close Notepad."
    Start-Process -FilePath "notepad.exe" -ArgumentList $envPath
    Read-Host "    Press Enter here once you've saved .env (or press Enter now to do this later)"
}

# ---------------------------------------------------------------------------
Write-Step "Verifying the project imports correctly"

$importOutput = (& $venvPython -c "import src.main") 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Fail "The project failed to import:"
    Write-Host $importOutput
    exit 1
}
Write-Ok "Project imports successfully."

# ---------------------------------------------------------------------------
Write-Step "Running the test suite (no network access, no API credits used)"

& $venvPython -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Some tests failed -- see output above. Setup will not be marked complete."
    exit 1
}
Write-Ok "All tests passed."

# ---------------------------------------------------------------------------
Write-Host "`n============================================================" -ForegroundColor Cyan
if ($hadWarning) {
    Write-Host "Setup complete (with a non-fatal warning above)." -ForegroundColor Yellow
} else {
    Write-Host "Setup complete!" -ForegroundColor Green
}
Write-Host "Next step: double-click run-agent.bat"
Write-Host "  (or run: powershell -ExecutionPolicy Bypass -File run-agent.ps1)"
Write-Host "============================================================`n"
