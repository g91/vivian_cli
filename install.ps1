<#
.SYNOPSIS
    Vivian CLI - Windows Install Script
.DESCRIPTION
    Installs Vivian AI CLI on Windows. Creates vivian and ai commands
    accessible from any terminal (PowerShell, CMD, Windows Terminal).
.PARAMETER System
    Install system-wide (requires admin).
.PARAMETER Dev
    Editable pip install for development.
.PARAMETER Uninstall
    Remove Vivian CLI from the system.
.EXAMPLE
    .\install.ps1
.EXAMPLE
    .\install.ps1 -System
.EXAMPLE
    .\install.ps1 -Uninstall
#>

param(
    [switch]$System,
    [switch]$Dev,
    [switch]$Uninstall,
    [switch]$Help
)

function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Write-Banner {
    Write-Color "==============================================" "Cyan"
    Write-Color "   VIVIAN CLI - AI-Powered Terminal Assistant  " "Cyan"
    Write-Color "==============================================" "Cyan"
}

if ($Help) {
    Write-Host "Usage: .\install.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -System      Install system-wide (requires admin)"
    Write-Host "  -Dev         Editable pip install (for development)"
    Write-Host "  -Uninstall   Remove Vivian CLI"
    Write-Host "  -Help        Show this help"
    exit 0
}

$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($System) {
    $InstallDir = "$env:ProgramFiles\vivian_cli"
    $BinDir = "$env:ProgramFiles\vivian_cli\bin"
    $NeedsAdmin = $true
} else {
    $InstallDir = "$env:LOCALAPPDATA\vivian_cli"
    $BinDir = "$env:LOCALAPPDATA\vivian_cli\bin"
    $NeedsAdmin = $false
}

$ConfigDir = "$env:USERPROFILE\.vivian"
$VenDir = "$InstallDir\venv"

if ($NeedsAdmin) {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Color "ERROR: System install requires Administrator privileges." "Red"
        Write-Color "Run PowerShell as Administrator and try again." "Yellow"
        exit 1
    }
}

if ($Uninstall) {
    Write-Color "Uninstalling Vivian CLI..." "Yellow"

    foreach ($pathVar in @("User", "Machine")) {
        $currentPath = [Environment]::GetEnvironmentVariable("PATH", $pathVar)
        if ($currentPath -like "*$BinDir*") {
            $newPath = ($currentPath -split ";" | Where-Object { $_ -ne $BinDir }) -join ";"
            [Environment]::SetEnvironmentVariable("PATH", $newPath, $pathVar)
            Write-Color "  Removed from $pathVar PATH" "Green"
        }
    }

    if (Test-Path $InstallDir) {
        Remove-Item -Recurse -Force $InstallDir
        Write-Color "  Removed $InstallDir" "Green"
    }

    if (Test-Path $ConfigDir) {
        $answer = Read-Host "Remove config directory ($ConfigDir)? [y/N]"
        if ($answer -eq "y" -or $answer -eq "Y") {
            Remove-Item -Recurse -Force $ConfigDir
            Write-Color "  Removed $ConfigDir" "Green"
        } else {
            Write-Color "  Kept $ConfigDir" "Yellow"
        }
    }

    Write-Color "Vivian CLI uninstalled. Restart your terminal." "Green"
    exit 0
}

Write-Banner
Write-Host ""
Write-Color "Installing Vivian CLI..." "White"
Write-Host ""
Write-Color "  Install mode:  $(if ($System) { 'System' } else { 'User' })" "Blue"
Write-Color "  Source:        $SourceDir" "Blue"
Write-Color "  Install dir:   $InstallDir" "Blue"
Write-Color "  Binary dir:    $BinDir" "Blue"
Write-Host ""

Write-Color "[1/6] Checking Python..." "White"

$pythonCmd = $null
$pyVer     = $null

# Check py launcher with explicit version first, then generic commands
$pythonCandidates = @(
    @{ Cmd = "py";         Args = "-3.12" },
    @{ Cmd = "py";         Args = "-3.11" },
    @{ Cmd = "py";         Args = "-3.10" },
    @{ Cmd = "python3.12"; Args = $null   },
    @{ Cmd = "python3.11"; Args = $null   },
    @{ Cmd = "python3.10"; Args = $null   },
    @{ Cmd = "python3";    Args = $null   },
    @{ Cmd = "python";     Args = $null   }
)

foreach ($entry in $pythonCandidates) {
    $cmd = $entry.Cmd; $arg = $entry.Args
    $label = if ($arg) { "$cmd $arg" } else { $cmd }
    Write-Color "  [DBG] Trying: $label" "DarkGray"
    try {
        # Resolve full path — skip if not found
        $resolved = Get-Command $cmd -ErrorAction SilentlyContinue
        if (-not $resolved) {
            Write-Color "  [DBG]   -> not found in PATH, skipping" "DarkGray"
            continue
        }
        Write-Color "  [DBG]   -> resolved: $($resolved.Source)" "DarkGray"

        # Skip Windows Store stubs — they open the Store UI or hang
        if ($resolved.Source -like "*WindowsApps*") {
            Write-Color "  [DBG]   -> Windows Store stub, skipping" "DarkYellow"
            continue
        }

        # Use the full resolved path to avoid any PATH re-lookup at invocation time
        $exePath = $resolved.Source
        $verArgs = if ($arg) { @($arg, "--version") } else { @("--version") }
        Write-Color "  [DBG]   -> invoking (5s timeout): $exePath $($verArgs -join ' ')" "DarkGray"

        # Run in a background job with a 5-second timeout — guards against
        # broken installs, missing DLLs, or UAC dialogs causing a hang
        $job = Start-Job -ScriptBlock { param($p, $a); & $p @a 2>&1 } -ArgumentList $exePath, $verArgs
        if (-not (Wait-Job $job -Timeout 5)) {
            Remove-Job $job -Force
            Write-Color "  [DBG]   -> timed out after 5s, skipping" "DarkYellow"
            continue
        }
        $ver = (Receive-Job $job) -join " "
        Remove-Job $job -ErrorAction SilentlyContinue
        Write-Color "  [DBG]   -> output:   $ver" "DarkGray"

        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]; $minor = [int]$Matches[2]
            Write-Color "  [DBG]   -> parsed:   $major.$minor" "DarkGray"
            if ($major -ge 3 -and $minor -ge 10) {
                $pythonCmd = $exePath   # use full path so later steps don't re-lookup
                $pyVer     = $ver.Trim()
                Write-Color "  [DBG]   -> SELECTED" "Green"
                break
            } else {
                Write-Color "  [DBG]   -> too old ($major.$minor < 3.10), skipping" "DarkYellow"
            }
        } else {
            Write-Color "  [DBG]   -> version string not recognised, skipping" "DarkYellow"
        }
    } catch {
        Write-Color "  [DBG]   -> exception: $_" "Red"
    }
}

# ── Auto-install Python 3.12 via winget if not found ──────────────────────────
if (-not $pythonCmd) {
    Write-Color "  Python 3.10+ not found. Attempting auto-install via winget..." "Yellow"
    $wingetOk = $false
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        try {
            Write-Color "  Running: winget install Python.Python.3.12" "Gray"
            winget install --id Python.Python.3.12 --source winget `
                --silent --accept-package-agreements --accept-source-agreements
            $wingetOk = $true
            Write-Color "  Python 3.12 installed via winget." "Green"
            # Refresh PATH for this session
            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                        [System.Environment]::GetEnvironmentVariable("PATH", "User")
            # Re-detect after install
            foreach ($testCmd in @("py -3.12", "python3.12", "python")) {
                try {
                    $parts = $testCmd.Split(" ")
                    $v = & $parts[0] @($parts[1..99] | Where-Object { $_ }) "--version" 2>&1
                    if ($v -match "Python 3\.(1[0-9]|[2-9]\d)") {
                        $pythonCmd = $testCmd; $pyVer = $v.ToString(); break
                    }
                } catch {}
            }
        } catch {
            Write-Color "  winget install failed: $_" "Red"
        }
    } else {
        Write-Color "  winget not available on this system." "Yellow"
    }

    if (-not $pythonCmd) {
        Write-Color "ERROR: Python 3.10+ is required and could not be installed automatically." "Red"
        Write-Host ""
        Write-Color "Please install manually, then re-run this script:" "Yellow"
        Write-Color "  winget install Python.Python.3.12" "Cyan"
        Write-Color "  https://www.python.org/downloads/release/python-3129/" "Cyan"
        Write-Color "  Microsoft Store: search for 'Python 3.12'" "Cyan"
        Write-Host ""
        Write-Color "Tip: check 'Add Python to PATH' in the installer." "Yellow"
        exit 1
    }
}

Write-Color "  OK Found: $pythonCmd  ($pyVer)" "Green"

Write-Color "[2/6] Creating directories..." "White"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

Write-Color "  OK Directories created" "Green"

Write-Color "[3/6] Copying Vivian CLI source..." "White"

if ($Dev) {
    Write-Color "  Dev mode: using source directly from $SourceDir" "Yellow"
    $ActualSource = $SourceDir
} else {
    $exclude = @("install.sh", "install.ps1", "venv", "__pycache__", ".git", ".gitignore")
    Get-ChildItem -Path $SourceDir -Exclude $exclude | Copy-Item -Destination $InstallDir -Recurse -Force
    $ActualSource = $InstallDir
}

Write-Color "  OK Source copied to $InstallDir" "Green"

Write-Color "[4/6] Setting up Python environment..." "White"

if (-not (Test-Path $VenDir)) {
    & $pythonCmd -m venv $VenDir
}

$venvPython = "$VenDir\Scripts\python.exe"
$venvPip = "$VenDir\Scripts\pip.exe"

Write-Color "  Upgrading pip..." "Gray"
& $venvPython -m pip install --upgrade pip -q

# ── Optional extras prompt ─────────────────────────────────────────────────
Write-Host ""
Write-Color "  Optional feature packs  (add later: pip install -e `".[extra]`")" "White"
Write-Host ""

$extras = @("dev")  # dev tools on by default
$ansDev = Read-Host "  Install dev tools? (pytest, black, ruff) [Y/n]"
if ($ansDev -match "^[Nn]") { $extras = @() }

$ansPv = Read-Host "  Install screen-capture/vision tools? (opencv, Pillow, mss) [y/N]"
if ($ansPv -match "^[Yy]") { $extras += "parsecvision" }

$ansDma = Read-Host "  Install DMA/PCILeech support? (memprocfs, Windows) [y/N]"
if ($ansDma -match "^[Yy]") { $extras += "dma" }

$extrasStr  = if ($extras.Count -gt 0) { "[" + ($extras -join ",") + "]" } else { "" }
$installTgt = if ($Dev) { "-e `"$ActualSource$extrasStr`"" } else { "`"$ActualSource$extrasStr`"" }

Write-Host ""
Write-Color "  Installing dependencies..." "Gray"
Invoke-Expression "& `$venvPip install $installTgt -q"

Write-Color "  OK Python environment ready" "Green"

Write-Color "[5/6] Creating vivian and ai commands..." "White"

$vivianBat = @"
@echo off
set VIVIAN_HOME=$InstallDir
set VIVIAN_LAUNCH_DIR=%CD%
"$VenDir\Scripts\python.exe" "$InstallDir\cli_main.py" --cwd "%VIVIAN_LAUNCH_DIR%" %*
"@

$vivianBat | Out-File -FilePath "$BinDir\vivian.bat" -Encoding ASCII
$vivianBat | Out-File -FilePath "$BinDir\ai.bat" -Encoding ASCII

Write-Color "  OK Wrapper scripts created:" "Green"
Write-Color "    $BinDir\vivian.bat" "Cyan"
Write-Color "    $BinDir\ai.bat" "Cyan"

Write-Color "[6/6] Adding to PATH..." "White"

$pathTarget = if ($System) { "Machine" } else { "User" }
$currentPath = [Environment]::GetEnvironmentVariable("PATH", $pathTarget)

if ($currentPath -notlike "*$BinDir*") {
    $newPath = "$currentPath;$BinDir"
    [Environment]::SetEnvironmentVariable("PATH", $newPath, $pathTarget)
    $env:PATH = "$env:PATH;$BinDir"
    Write-Color "  OK Added to $pathTarget PATH" "Green"
    Write-Color "  Restart your terminal for the change to take full effect." "Yellow"
} else {
    Write-Color "  OK Already in PATH" "Green"
}

Write-Host ""
Write-Color "==============================================" "Green"
Write-Color "   Vivian CLI installed successfully!          " "Green"
Write-Color "==============================================" "Green"
Write-Host ""
Write-Color "  Quick start:" "White"
Write-Color "    vivian              Start interactive AI assistant" "Cyan"
Write-Color "    vivian -p hello     One-shot query" "Cyan"
Write-Color "    ai                  Same as vivian (alias)" "Cyan"
Write-Host ""
Write-Color "  Pentesting tools:" "White"
Write-Color "    vivian -p auto_pwn 10.10.10.5" "Cyan"
Write-Color "    vivian -p quick_scan 192.168.1.0/24" "Cyan"
Write-Host ""
Write-Color "  Config: $ConfigDir\config.json" "Cyan"
Write-Color "  Install: $InstallDir" "Cyan"
Write-Host ""
Write-Color "  Tip: Restart your terminal to use vivian from anywhere" "Yellow"
Write-Host ""
