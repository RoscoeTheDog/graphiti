# Neo4j Community Edition Setup Wizard for Graphiti
# Interactive AI-assisted installation guide
# ASCII-compatible output for maximum compatibility
# Non-invasive: Asks for confirmation before ANY system changes

param(
    [string]$Neo4jPath = "",
    [switch]$SkipTests = $false
)

$ErrorActionPreference = "Stop"
$REPO_ROOT = $PSScriptRoot

function Confirm-Action {
    param(
        [string]$Message,
        [string]$DefaultYes = $true
    )

    $prompt = if ($DefaultYes) { "(Y/n)" } else { "(y/N)" }
    $response = Read-Host "$Message $prompt"

    if ($DefaultYes) {
        return ($response -ne 'n' -and $response -ne 'N')
    } else {
        return ($response -eq 'y' -or $response -eq 'Y')
    }
}

# ASCII art banner
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Neo4j Community Edition - Setup Wizard for Graphiti" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This wizard will guide you through setting up Neo4j Community" -ForegroundColor White
Write-Host "Edition as a Windows Service for Graphiti development." -ForegroundColor White
Write-Host ""
Write-Host "Estimated time: 30-40 minutes" -ForegroundColor Gray
Write-Host "Repository: $REPO_ROOT" -ForegroundColor Gray
Write-Host ""
Write-Host "Important: This wizard asks for confirmation before ANY changes" -ForegroundColor Yellow
Write-Host "Press Ctrl+C at any time to cancel" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to begin"

# ============================================================
# STEP 1: Check Prerequisites
# ============================================================

Write-Host ""
Write-Host "Step 1 of 11: Validating Prerequisites" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Gray
Write-Host ""

# Check 1.1: Administrator Privileges
Write-Host "[1.1] Checking for Administrator privileges..." -ForegroundColor Cyan
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    Write-Host "  [OK] Running with Administrator privileges" -ForegroundColor Green
    Write-Host "  - Automatic installation available for Chocolatey and Java" -ForegroundColor Gray
} else {
    Write-Host "  [!] NOT running as Administrator" -ForegroundColor Yellow
    Write-Host "  - You will need to run some commands manually" -ForegroundColor Gray
    Write-Host "  - Chocolatey and Java installation require elevation" -ForegroundColor Gray
}

Write-Host ""

# Check 1.2: Chocolatey
Write-Host "[1.2] Checking for Chocolatey..." -ForegroundColor Cyan
$chocoInstalled = $null -ne (Get-Command choco -ErrorAction SilentlyContinue)

if ($chocoInstalled) {
    $chocoVersion = choco --version 2>&1 | Select-Object -First 1
    Write-Host "  [OK] Chocolatey is installed (version: $chocoVersion)" -ForegroundColor Green
} else {
    Write-Host "  [!] Chocolatey is NOT installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Chocolatey is required to install Java 21." -ForegroundColor Yellow
    Write-Host ""

    if ($isAdmin) {
        if (Confirm-Action "  Install Chocolatey now?") {
            Write-Host ""
            Write-Host "  Installing Chocolatey..." -ForegroundColor Cyan

            Set-ExecutionPolicy Bypass -Scope Process -Force
            [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
            $chocoInstallScript = (New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1')
            Invoke-Expression $chocoInstallScript

            # Refresh environment
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

            $chocoInstalled = $null -ne (Get-Command choco -ErrorAction SilentlyContinue)
            if ($chocoInstalled) {
                Write-Host "  [OK] Chocolatey installed successfully" -ForegroundColor Green
            } else {
                Write-Host "  [ERROR] Chocolatey installation failed" -ForegroundColor Red
                Write-Host "  Please install manually and run this script again" -ForegroundColor Yellow
                exit 1
            }
        } else {
            Write-Host "  Skipping Chocolatey installation" -ForegroundColor Yellow
            Write-Host "  You must install it manually to continue" -ForegroundColor Yellow
            exit 0
        }
    } else {
        Write-Host "  Installation command (run as Administrator in PowerShell):" -ForegroundColor White
        Write-Host ""
        Write-Host "  Set-ExecutionPolicy Bypass -Scope Process -Force;" -ForegroundColor Cyan
        Write-Host "  [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072;" -ForegroundColor Cyan
        Write-Host "  iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  After installation:" -ForegroundColor White
        Write-Host "  1. Close and reopen PowerShell as Administrator" -ForegroundColor Gray
        Write-Host "  2. Run this script again" -ForegroundColor Gray
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host ""

# Check 1.3: Python
Write-Host "[1.3] Checking for Python 3.10+..." -ForegroundColor Cyan
$pythonInstalled = $null -ne (Get-Command python -ErrorAction SilentlyContinue)

if ($pythonInstalled) {
    $pythonVersion = python --version 2>&1
    $versionMatch = $pythonVersion -match 'Python (\d+)\.(\d+)'
    if ($versionMatch) {
        $majorVersion = [int]$matches[1]
        $minorVersion = [int]$matches[2]

        if ($majorVersion -ge 3 -and $minorVersion -ge 10) {
            Write-Host "  [OK] Python is installed ($pythonVersion)" -ForegroundColor Green
        } else {
            Write-Host "  [!] Python version is too old: $pythonVersion" -ForegroundColor Yellow
            Write-Host "  Required: Python 3.10 or newer" -ForegroundColor Gray
            Write-Host "  Download from: https://www.python.org/downloads/" -ForegroundColor Gray
            exit 1
        }
    }
} else {
    Write-Host "  [!] Python is NOT installed" -ForegroundColor Red
    Write-Host "  Python 3.10+ is required for Graphiti MCP server" -ForegroundColor Yellow
    Write-Host "  Download from: https://www.python.org/downloads/" -ForegroundColor Gray
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Check 1.4: uv
Write-Host "[1.4] Checking for uv package manager..." -ForegroundColor Cyan
$uvInstalled = $null -ne (Get-Command uv -ErrorAction SilentlyContinue)

if ($uvInstalled) {
    Write-Host "  [OK] uv is installed" -ForegroundColor Green
} else {
    Write-Host "  [!] uv is NOT installed" -ForegroundColor Yellow
    Write-Host "  Install command: pip install uv" -ForegroundColor Gray
    Write-Host ""

    if (Confirm-Action "  Install uv now?") {
        Write-Host ""
        Write-Host "  Installing uv..." -ForegroundColor Cyan
        python -m pip install uv

        $uvInstalled = $null -ne (Get-Command uv -ErrorAction SilentlyContinue)
        if ($uvInstalled) {
            Write-Host "  [OK] uv installed successfully" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] uv installation failed" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "  Skipping uv installation" -ForegroundColor Yellow
        Write-Host "  You must install it to continue" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""
Write-Host "Prerequisites check complete!" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to continue"

# ============================================================
# STEP 2: Java 21 Installation
# ============================================================

Write-Host ""
Write-Host "Step 2 of 11: Java 21 Installation" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Gray
Write-Host ""

Write-Host "Checking for Java 21..." -ForegroundColor Cyan
$javaInstalled = $null -ne (Get-Command java -ErrorAction SilentlyContinue)
$javaValid = $false

if ($javaInstalled) {
    $javaVersionOutput = java -version 2>&1 | Out-String
    $javaVersionMatch = $javaVersionOutput -match 'version "(\d+)'

    if ($javaVersionMatch) {
        $javaMajorVersion = [int]$matches[1]
        if ($javaMajorVersion -ge 21) {
            Write-Host "  [OK] Java is installed: $($javaVersionOutput -split "`n" | Select-Object -First 1)" -ForegroundColor Green
            $javaValid = $true
        } else {
            Write-Host "  [!] Java version is too old (v$javaMajorVersion)" -ForegroundColor Yellow
            Write-Host "  Required: Java 21 or newer" -ForegroundColor Gray
        }
    }
}

if (-not $javaValid) {
    Write-Host ""
    Write-Host "  Neo4j Community 2025.09.0 requires Java 21" -ForegroundColor Yellow
    Write-Host ""

    if ($isAdmin -and $chocoInstalled) {
        if (Confirm-Action "  Install Java 21 (Eclipse Temurin) via Chocolatey?") {
            Write-Host ""
            Write-Host "  Installing Java 21 via Chocolatey..." -ForegroundColor Cyan
            Write-Host "  Command: choco install temurin21 -y" -ForegroundColor Gray
            Write-Host "  (This may take 2-3 minutes)" -ForegroundColor Gray
            Write-Host ""

            choco install temurin21 -y

            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Host "  [OK] Java 21 installed successfully" -ForegroundColor Green
                Write-Host ""
                Write-Host "  IMPORTANT: PowerShell restart required!" -ForegroundColor Yellow
                Write-Host "  - Environment variables (PATH, JAVA_HOME) are not yet active" -ForegroundColor Gray
                Write-Host "  - Close this window and reopen PowerShell as Administrator" -ForegroundColor Gray
                Write-Host "  - Run this script again to continue from where you left off" -ForegroundColor Gray
                Write-Host ""
                Read-Host "Press Enter to exit"
                exit 0
            } else {
                Write-Host ""
                Write-Host "  [ERROR] Java installation failed" -ForegroundColor Red
                Read-Host "Press Enter to exit"
                exit 1
            }
        } else {
            Write-Host "  Skipping Java installation" -ForegroundColor Yellow
            exit 0
        }
    } else {
        Write-Host "  Installation command (run as Administrator in PowerShell):" -ForegroundColor White
        Write-Host ""
        Write-Host "  choco install temurin21 -y" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  After installation:" -ForegroundColor White
        Write-Host "  1. Close and reopen PowerShell as Administrator" -ForegroundColor Gray
        Write-Host "  2. Run this script again" -ForegroundColor Gray
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host ""
Read-Host "Press Enter to continue"

# ============================================================
# STEP 3: Neo4j Community Edition Detection
# ============================================================

Write-Host ""
Write-Host "Step 3 of 11: Neo4j Community Edition Detection" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Gray
Write-Host ""

Write-Host "Scanning for Neo4j Community Edition installations..." -ForegroundColor Cyan
Write-Host ""

# Scan for Neo4j installations
$neo4jBaseDir = "C:\neo4j"
$detectedVersions = @()

if (Test-Path $neo4jBaseDir) {
    $neo4jDirs = Get-ChildItem -Path $neo4jBaseDir -Directory -Filter "neo4j-community-*" -ErrorAction SilentlyContinue

    foreach ($dir in $neo4jDirs) {
        if (Test-Path "$($dir.FullName)\bin\neo4j.bat") {
            $detectedVersions += [PSCustomObject]@{
                Path = $dir.FullName
                Name = $dir.Name
                Modified = $dir.LastWriteTime
            }
        }
    }
}

# Sort by newest first
$detectedVersions = $detectedVersions | Sort-Object -Property Modified -Descending

if ($detectedVersions.Count -gt 0) {
    Write-Host "  Found $($detectedVersions.Count) Neo4j installation(s):" -ForegroundColor Green
    Write-Host ""

    for ($i = 0; $i -lt $detectedVersions.Count; $i++) {
        $version = $detectedVersions[$i]
        $highlight = if ($i -eq 0) { " (newest)" } else { "" }
        Write-Host "  [$($i + 1)] $($version.Name)$highlight" -ForegroundColor White
        Write-Host "      Path: $($version.Path)" -ForegroundColor Gray
        Write-Host "      Modified: $($version.Modified)" -ForegroundColor Gray
        Write-Host ""
    }

    Write-Host "  [0] Use custom path" -ForegroundColor White
    Write-Host ""

    $selection = Read-Host "  Select Neo4j installation [1-$($detectedVersions.Count), 0 for custom]"

    if ($selection -eq "0") {
        $Neo4jPath = Read-Host "  Enter custom Neo4j path"
    } elseif ([int]$selection -ge 1 -and [int]$selection -le $detectedVersions.Count) {
        $Neo4jPath = $detectedVersions[[int]$selection - 1].Path
    } else {
        Write-Host "  [ERROR] Invalid selection" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [!] No Neo4j installations detected in C:\neo4j\" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  You must download Neo4j Community Edition manually:" -ForegroundColor White
    Write-Host ""
    Write-Host "  Step-by-step:" -ForegroundColor Cyan
    Write-Host "  1. Open browser: https://neo4j.com/deployment-center/#community" -ForegroundColor Gray
    Write-Host "  2. Select: Neo4j Community Edition (latest stable)" -ForegroundColor Gray
    Write-Host "  3. Platform: Windows (.zip)" -ForegroundColor Gray
    Write-Host "  4. Download the ZIP file (~150MB)" -ForegroundColor Gray
    Write-Host "  5. Extract to: C:\neo4j\" -ForegroundColor Gray
    Write-Host "     (This should create: C:\neo4j\neo4j-community-YYYY.XX.X\)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  After extraction, run this script again." -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Validate selected path
if (-not (Test-Path "$Neo4jPath\bin\neo4j.bat")) {
    Write-Host ""
    Write-Host "  [ERROR] Invalid Neo4j installation at: $Neo4jPath" -ForegroundColor Red
    Write-Host "  neo4j.bat not found in bin directory" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "  [OK] Using Neo4j at: $Neo4jPath" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to continue"

# ============================================================
# STEP 4: Virtual Environment Setup
# ============================================================

Write-Host ""
Write-Host "Step 4 of 11: Virtual Environment Setup" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Gray
Write-Host ""

$venvPath = Join-Path $REPO_ROOT "venv"
$venvSkipped = $false

if (Test-Path $venvPath) {
    Write-Host "  [!] Virtual environment already exists at: $venvPath" -ForegroundColor Yellow

    if (Confirm-Action "  Recreate virtual environment?" -DefaultYes $false) {
        Write-Host "  Removing existing venv..." -ForegroundColor Cyan
        Remove-Item -Path $venvPath -Recurse -Force
    } else {
        Write-Host "  Using existing virtual environment" -ForegroundColor Gray
        $venvSkipped = $true
    }
}

if (-not $venvSkipped) {
    Write-Host ""
    Write-Host "  Creating virtual environment at: $venvPath" -ForegroundColor White
    Write-Host ""

    if (Confirm-Action "  Create virtual environment and install dependencies?") {
        Write-Host ""
        Write-Host "  Creating virtual environment..." -ForegroundColor Cyan

        python -m venv $venvPath

        if (Test-Path "$venvPath\Scripts\Activate.ps1") {
            Write-Host "  [OK] Virtual environment created" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] Failed to create virtual environment" -ForegroundColor Red
            exit 1
        }

        Write-Host ""
        Write-Host "  Installing dependencies with uv..." -ForegroundColor Cyan
        Write-Host "  (This may take a few minutes)" -ForegroundColor Gray
        Write-Host ""

        # Activate venv and install
        & "$venvPath\Scripts\Activate.ps1"
        uv sync

        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "  [OK] Dependencies installed successfully" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "  [ERROR] Dependency installation failed" -ForegroundColor Red
            exit 1
        }

        Write-Host ""
        Write-Host "  Validating graphiti-core import..." -ForegroundColor Cyan

        $testImport = & "$venvPath\Scripts\python.exe" -c "import graphiti_core; print('OK')" 2>&1

        if ($testImport -match "OK") {
            Write-Host "  [OK] graphiti-core imports successfully" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] Failed to import graphiti-core" -ForegroundColor Red
            Write-Host "  $testImport" -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "  Skipping virtual environment setup" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""
Read-Host "Press Enter to continue"

# ============================================================
# STEP 5: Neo4j Windows Service Installation
# ============================================================

Write-Host ""
Write-Host "Step 5 of 11: Install Neo4j Windows Service" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Gray
Write-Host ""

Write-Host "Checking for Neo4j service..." -ForegroundColor Cyan
$neo4jService = Get-Service -Name "Neo4j" -ErrorAction SilentlyContinue
$serviceInstallSkipped = $false

if ($neo4jService) {
    Write-Host "  [OK] Neo4j service already installed" -ForegroundColor Green
    Write-Host "  Status: $($neo4jService.Status)" -ForegroundColor Gray
    Write-Host ""

    if (Confirm-Action "  Reinstall the service?" -DefaultYes $false) {
        Write-Host "  Uninstalling existing service first..." -ForegroundColor Yellow
        Stop-Service Neo4j -ErrorAction SilentlyContinue
        Push-Location $Neo4jPath
        & ".\bin\neo4j.bat" windows-service uninstall
        Pop-Location
        $serviceInstallSkipped = $false
    } else {
        Write-Host "  Skipping service installation" -ForegroundColor Gray
        $serviceInstallSkipped = $true
    }
} else {
    Write-Host "  [!] Neo4j service NOT installed" -ForegroundColor Yellow
    $serviceInstallSkipped = $false
}

if (-not $serviceInstallSkipped) {
    Write-Host ""
    Write-Host "  Install Neo4j as Windows Service?" -ForegroundColor White
    Write-Host "  Command: $Neo4jPath\bin\neo4j.bat windows-service install" -ForegroundColor Gray
    Write-Host ""

    if (Confirm-Action "  Proceed with installation?") {
        Write-Host ""
        Write-Host "  Installing service..." -ForegroundColor Cyan

        Push-Location $Neo4jPath
        & ".\bin\neo4j.bat" windows-service install
        Pop-Location

        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Neo4j service installed successfully" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] Service installation failed" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
    } else {
        Write-Host "  Installation cancelled" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""
Read-Host "Press Enter to continue"

# ============================================================
# STEP 6: Start Neo4j Service
# ============================================================

Write-Host ""
Write-Host "Step 6 of 11: Start Neo4j Service" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Gray
Write-Host ""

$neo4jService = Get-Service -Name "Neo4j"

if ($neo4jService.Status -eq 'Running') {
    Write-Host "  [OK] Neo4j service is already running" -ForegroundColor Green
} else {
    Write-Host "  Neo4j service is currently: $($neo4jService.Status)" -ForegroundColor Gray
    Write-Host ""

    if (Confirm-Action "  Start Neo4j service?") {
        Write-Host ""
        Write-Host "  Starting Neo4j service..." -ForegroundColor Cyan
        Start-Service Neo4j

        Write-Host "  Waiting for Neo4j to start... (30 seconds)" -ForegroundColor Gray
        Start-Sleep -Seconds 30

        $neo4jService = Get-Service -Name "Neo4j"
        if ($neo4jService.Status -eq 'Running') {
            Write-Host "  [OK] Neo4j service started successfully" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] Failed to start Neo4j service" -ForegroundColor Red
            Write-Host "  Status: $($neo4jService.Status)" -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "  Skipping service start" -ForegroundColor Yellow
        Write-Host "  You can start it later with: Start-Service Neo4j" -ForegroundColor Gray
        exit 0
    }
}

Write-Host ""
Write-Host "  Testing Neo4j Browser access..." -ForegroundColor Cyan
Write-Host "  URL: http://localhost:7474" -ForegroundColor Gray

try {
    $response = Invoke-WebRequest -Uri "http://localhost:7474" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "  [OK] Neo4j Browser is accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "  [!] Neo4j Browser not accessible yet" -ForegroundColor Yellow
    Write-Host "  This is normal - it may take a minute to fully start" -ForegroundColor Gray
}

Write-Host ""
Read-Host "Press Enter to continue"

# ============================================================
# STEP 7: Set Initial Password
# ============================================================

Write-Host ""
Write-Host "Step 7 of 11: Set Initial Neo4j Password" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Gray
Write-Host ""

Write-Host "  You must set the initial password via Neo4j Browser" -ForegroundColor White
Write-Host ""
Write-Host "  Instructions:" -ForegroundColor Cyan
Write-Host "  1. Open browser: http://localhost:7474" -ForegroundColor Gray
Write-Host "  2. Login with default credentials:" -ForegroundColor Gray
Write-Host "     Username: neo4j" -ForegroundColor Gray
Write-Host "     Password: neo4j" -ForegroundColor Gray
Write-Host "  3. You will be prompted to change password" -ForegroundColor Gray
Write-Host "  4. Set a new password and remember it!" -ForegroundColor Gray
Write-Host ""

if (-not (Confirm-Action "  Have you completed password setup?")) {
    Write-Host "  Please complete password setup and run this script again" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "  Enter your new Neo4j password for configuration:" -ForegroundColor White
$neo4jPassword = Read-Host "  Password" -AsSecureString
$neo4jPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($neo4jPassword))

Write-Host ""
Read-Host "Press Enter to continue"

# ============================================================
# STEP 8: Configure System Environment Variables
# ============================================================

Write-Host ""
Write-Host "Step 8 of 11: Configure System Environment Variables" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Gray
Write-Host ""

Write-Host "  The following environment variables will be set at system level:" -ForegroundColor White
Write-Host ""
Write-Host "  NEO4J_URI      = bolt://localhost:7687" -ForegroundColor Gray
Write-Host "  NEO4J_USER     = neo4j" -ForegroundColor Gray
Write-Host "  NEO4J_PASSWORD = ***hidden***" -ForegroundColor Gray
Write-Host "  NEO4J_DATABASE = neo4j" -ForegroundColor Gray
Write-Host ""

if (Confirm-Action "  Set system environment variables?") {
    Write-Host ""
    Write-Host "  Setting environment variables..." -ForegroundColor Cyan

    [Environment]::SetEnvironmentVariable('NEO4J_URI', 'bolt://localhost:7687', 'Machine')
    Write-Host "  [OK] NEO4J_URI = bolt://localhost:7687" -ForegroundColor Green

    [Environment]::SetEnvironmentVariable('NEO4J_USER', 'neo4j', 'Machine')
    Write-Host "  [OK] NEO4J_USER = neo4j" -ForegroundColor Green

    [Environment]::SetEnvironmentVariable('NEO4J_PASSWORD', $neo4jPasswordPlain, 'Machine')
    Write-Host "  [OK] NEO4J_PASSWORD = ***set***" -ForegroundColor Green

    [Environment]::SetEnvironmentVariable('NEO4J_DATABASE', 'neo4j', 'Machine')
    Write-Host "  [OK] NEO4J_DATABASE = neo4j" -ForegroundColor Green

    Write-Host ""
    Write-Host "  Environment variables configured successfully!" -ForegroundColor Green
} else {
    Write-Host "  Skipping environment variable configuration" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Read-Host "Press Enter to continue"

# ============================================================
# STEP 9: Configure Claude Code MCP Server
# ============================================================

Write-Host ""
Write-Host "Step 9 of 11: Configure Claude Code MCP Server" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Gray
Write-Host ""

$claudeConfigPath = "$env:USERPROFILE\.claude.json"

if (-not (Test-Path $claudeConfigPath)) {
    Write-Host "  [!] .claude.json not found at: $claudeConfigPath" -ForegroundColor Yellow
    Write-Host "  Skipping MCP configuration" -ForegroundColor Gray
    Write-Host "  You can configure it manually later" -ForegroundColor Gray
} else {
    Write-Host "  .claude.json found at: $claudeConfigPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  This will update the graphiti-memory MCP server configuration with:" -ForegroundColor White
    Write-Host "  - Neo4j connection credentials (hardcoded values)" -ForegroundColor Gray
    Write-Host "  - Enable graphiti-memory for this project" -ForegroundColor Gray
    Write-Host ""

    if (Confirm-Action "  Update .claude.json configuration?") {
        Write-Host ""
        Write-Host "  Updating .claude.json..." -ForegroundColor Cyan

        # Create Python script to update configuration
        $updateScript = @"
import json
import sys
from pathlib import Path

config_path = Path(r'$claudeConfigPath')

try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Get OpenAI key from environment or existing config
    openai_key = config.get('mcpServers', {}).get('graphiti-memory', {}).get('env', {}).get('OPENAI_API_KEY', '')

    # Find uv path
    uv_path = r'C:/python313/Scripts/uv.exe'  # Default fallback

    # Update global mcpServers
    if 'mcpServers' not in config:
        config['mcpServers'] = {}

    config['mcpServers']['graphiti-memory'] = {
        'type': 'stdio',
        'command': uv_path,
        'args': [
            'run',
            '--directory',
            r'$REPO_ROOT\mcp_server',
            'graphiti_mcp_server.py',
            '--transport',
            'stdio'
        ],
        'env': {
            'NEO4J_URI': 'bolt://localhost:7687',
            'NEO4J_USER': 'neo4j',
            'NEO4J_PASSWORD': r'$neo4jPasswordPlain',
            'NEO4J_DATABASE': 'neo4j',
            'OPENAI_API_KEY': openai_key,
            'MODEL_NAME': 'gpt-4o-mini'
        }
    }

    # Update project-specific config
    project_key = r'$REPO_ROOT'
    if 'projects' not in config:
        config['projects'] = {}

    if project_key not in config['projects']:
        config['projects'][project_key] = {}

    if 'mcpServers' not in config['projects'][project_key]:
        config['projects'][project_key]['mcpServers'] = {}

    config['projects'][project_key]['mcpServers']['graphiti-memory'] = {
        'enabled': True
    }

    # Create backup
    backup_path = config_path.with_suffix('.json.backup-wizard')
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # Write updated config
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print('[OK] Configuration updated successfully')
    sys.exit(0)

except Exception as e:
    print(f'[ERROR] Failed to update configuration: {e}')
    sys.exit(1)
"@

        $updateScript | Out-File -FilePath "$REPO_ROOT\temp_update_claude_config.py" -Encoding UTF8

        # Run the update script
        $updateResult = & "$venvPath\Scripts\python.exe" "$REPO_ROOT\temp_update_claude_config.py" 2>&1

        # Clean up temp script
        Remove-Item "$REPO_ROOT\temp_update_claude_config.py" -ErrorAction SilentlyContinue

        if ($updateResult -match "\[OK\]") {
            Write-Host "  [OK] .claude.json updated successfully" -ForegroundColor Green
            Write-Host "  Backup created: .claude.json.backup-wizard" -ForegroundColor Gray
        } else {
            Write-Host "  [ERROR] Failed to update .claude.json" -ForegroundColor Red
            Write-Host "  $updateResult" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Skipping .claude.json configuration" -ForegroundColor Yellow
        Write-Host "  You can configure it manually later" -ForegroundColor Gray
    }
}

Write-Host ""
Read-Host "Press Enter to continue"

# ============================================================
# STEP 10: Test Neo4j Connection
# ============================================================

Write-Host ""
Write-Host "Step 10 of 11: Test Neo4j Connection" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Gray
Write-Host ""

$testScript = Join-Path $REPO_ROOT "test_neo4j_community_connection.py"

if (Test-Path $testScript) {
    Write-Host "  Running connection test..." -ForegroundColor Cyan
    Write-Host "  Command: python $testScript" -ForegroundColor Gray
    Write-Host ""

    & "$venvPath\Scripts\python.exe" $testScript

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "  [OK] Connection test PASSED!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "  [!] Connection test FAILED" -ForegroundColor Red
        Write-Host "  Please check your password and Neo4j service status" -ForegroundColor Yellow
        Write-Host "  You can retry with: python $testScript" -ForegroundColor Gray
    }
} else {
    Write-Host "  [!] Test script not found: $testScript" -ForegroundColor Yellow
    Write-Host "  Skipping automated test" -ForegroundColor Gray
}

Write-Host ""
Read-Host "Press Enter to continue"

# ============================================================
# STEP 11: Setup Summary
# ============================================================

Write-Host ""
Write-Host "Step 11 of 11: Setup Summary" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Gray
Write-Host ""

Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Configuration Summary:" -ForegroundColor Cyan
Write-Host "  - Neo4j Path: $Neo4jPath" -ForegroundColor White
Write-Host "  - Neo4j Service: Running as Windows Service" -ForegroundColor White
Write-Host "  - Neo4j Browser: http://localhost:7474" -ForegroundColor White
Write-Host "  - Bolt Connection: bolt://localhost:7687" -ForegroundColor White
Write-Host "  - Database: neo4j" -ForegroundColor White
Write-Host "  - Username: neo4j" -ForegroundColor White
Write-Host "  - Virtual Environment: $venvPath" -ForegroundColor White
Write-Host ""
Write-Host "  Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Restart Claude Code to pick up environment variables" -ForegroundColor Gray
Write-Host "  2. Verify graphiti-memory MCP server connects" -ForegroundColor Gray
Write-Host "  3. Test graphiti tools (add_memory, search_memory_nodes, etc.)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Service Management Commands:" -ForegroundColor Cyan
Write-Host "  - Start:   Start-Service Neo4j" -ForegroundColor Gray
Write-Host "  - Stop:    Stop-Service Neo4j" -ForegroundColor Gray
Write-Host "  - Status:  Get-Service Neo4j" -ForegroundColor Gray
Write-Host "  - Restart: Restart-Service Neo4j" -ForegroundColor Gray
Write-Host ""
Write-Host "  Troubleshooting:" -ForegroundColor Cyan
Write-Host "  - Check logs: $Neo4jPath\logs\neo4j.log" -ForegroundColor Gray
Write-Host "  - Test connection: python $testScript" -ForegroundColor Gray
Write-Host "  - See: CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to exit"
