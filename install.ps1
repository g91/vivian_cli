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
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 10) {
                $pythonCmd = $cmd
                break
            }
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Color "ERROR: Python 3.10+ is required but not found." "Red"
    Write-Host ""
    Write-Color "Install Python from: https://www.python.org/downloads/" "Yellow"
    Write-Color "Or: winget install Python.Python.3.12" "Yellow"
    Write-Color "Make sure to check 'Add Python to PATH' during installation." "Yellow"
    exit 1
}

Write-Color "  OK Found $pythonCmd $ver" "Green"

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

Write-Color "  Installing dependencies..." "Gray"
if ($Dev) {
    & $venvPip install -e $ActualSource -q
} else {
    & $venvPip install "prompt_toolkit>=3.0.0" -q
}

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
