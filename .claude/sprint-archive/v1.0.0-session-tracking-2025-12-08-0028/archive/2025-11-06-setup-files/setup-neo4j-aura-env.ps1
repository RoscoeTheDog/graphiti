# Graphiti Environment Setup Script
# Automatically configures Neo4j Aura environment variables for Graphiti MCP server
# Supports both Windows PowerShell and cross-platform scenarios

#Requires -Version 5.1

# ============================================
# CONFIGURATION
# ============================================
$CREDENTIALS_FILE = "credentials.txt"
$SCRIPT_DIR = $PSScriptRoot

# ============================================
# ADMIN ELEVATION CHECK
# ============================================
function Test-IsAdmin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Request-AdminElevation {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host " ADMINISTRATOR PRIVILEGES REQUIRED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "This script needs to set system-level environment variables." -ForegroundColor Yellow
    Write-Host "Attempting to restart with administrator privileges..." -ForegroundColor Yellow
    Write-Host ""

    # Restart the script with admin privileges
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Check for admin privileges
if (-not (Test-IsAdmin)) {
    Request-AdminElevation
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Graphiti Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Running with Administrator privileges: YES" -ForegroundColor Green
Write-Host "Script directory: $SCRIPT_DIR" -ForegroundColor Gray
Write-Host ""

# ============================================
# CREDENTIALS FILE CHECK
# ============================================
$credentialsPath = Join-Path $SCRIPT_DIR $CREDENTIALS_FILE

Write-Host "Looking for credentials file: $CREDENTIALS_FILE" -ForegroundColor Cyan
Write-Host "Expected location: $credentialsPath" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $credentialsPath)) {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host " CREDENTIALS FILE NOT FOUND" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create a file named '$CREDENTIALS_FILE' in this directory:" -ForegroundColor Yellow
    Write-Host "  $SCRIPT_DIR" -ForegroundColor White
    Write-Host ""
    Write-Host "The file should contain your Neo4j Aura credentials in this format:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io" -ForegroundColor White
    Write-Host "  NEO4J_USERNAME=neo4j" -ForegroundColor White
    Write-Host "  NEO4J_PASSWORD=your-generated-password" -ForegroundColor White
    Write-Host "  NEO4J_DATABASE=neo4j" -ForegroundColor White
    Write-Host ""
    Write-Host "You can download this file when creating a Neo4j Aura instance at:" -ForegroundColor Yellow
    Write-Host "  https://console.neo4j.io" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host "[OK] Found credentials file" -ForegroundColor Green
Write-Host ""

# ============================================
# PARSE CREDENTIALS FILE
# ============================================
Write-Host "Parsing credentials..." -ForegroundColor Cyan

$credentials = @{}
$requiredKeys = @('NEO4J_URI', 'NEO4J_USERNAME', 'NEO4J_PASSWORD')

Get-Content $credentialsPath | ForEach-Object {
    $line = $_.Trim()
    # Skip comments and empty lines
    if ($line -and -not $line.StartsWith('#')) {
        if ($line -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            $credentials[$key] = $value
        }
    }
}

# Validate required credentials
$missingKeys = @()
foreach ($key in $requiredKeys) {
    if (-not $credentials.ContainsKey($key) -or -not $credentials[$key]) {
        $missingKeys += $key
    }
}

if ($missingKeys.Count -gt 0) {
    Write-Host "[FAIL] Missing required credentials:" -ForegroundColor Red
    foreach ($key in $missingKeys) {
        Write-Host "  - $key" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Please ensure your credentials.txt file contains all required fields." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host "[OK] All required credentials found" -ForegroundColor Green
Write-Host ""

# ============================================
# VM COMPATIBILITY CHECK - URI SCHEME FIX
# ============================================
$originalUri = $credentials['NEO4J_URI']
$isVM = $false

# Check if running in a VM (basic heuristic)
$computerSystem = Get-WmiObject -Class Win32_ComputerSystem
if ($computerSystem.Model -match 'Virtual|VMware|VirtualBox|QEMU|Hyper-V|Proxmox') {
    $isVM = $true
    Write-Host "[INFO] Virtual Machine detected: $($computerSystem.Model)" -ForegroundColor Yellow
}

# Fix URI scheme for VMs
if ($originalUri -like 'neo4j+s://*') {
    if ($isVM) {
        $fixedUri = $originalUri -replace '^neo4j\+s://', 'neo4j+ssc://'
        $credentials['NEO4J_URI'] = $fixedUri
        Write-Host "[FIX] Changed URI scheme for VM compatibility:" -ForegroundColor Yellow
        Write-Host "  FROM: $originalUri" -ForegroundColor Gray
        Write-Host "  TO:   $fixedUri" -ForegroundColor Green
        Write-Host "  (neo4j+ssc:// accepts self-signed certificates)" -ForegroundColor Cyan
    } else {
        Write-Host "[INFO] Using neo4j+s:// (bare metal system)" -ForegroundColor Cyan
    }
} elseif ($originalUri -like 'neo4j+ssc://*') {
    Write-Host "[OK] Using neo4j+ssc:// (VM-compatible)" -ForegroundColor Green
}
Write-Host ""

# ============================================
# SET ENVIRONMENT VARIABLES
# ============================================
Write-Host "Setting system environment variables..." -ForegroundColor Cyan
Write-Host ""

# Map Neo4j credentials to environment variables
$envVars = @{
    'NEO4J_URI' = $credentials['NEO4J_URI']
    'NEO4J_USER' = $credentials['NEO4J_USERNAME']
    'NEO4J_PASSWORD' = $credentials['NEO4J_PASSWORD']
}

# Add database if present
if ($credentials.ContainsKey('NEO4J_DATABASE')) {
    $envVars['NEO4J_DATABASE'] = $credentials['NEO4J_DATABASE']
}

# Set each variable
foreach ($varName in $envVars.Keys) {
    $value = $envVars[$varName]
    try {
        [Environment]::SetEnvironmentVariable($varName, $value, 'Machine')

        if ($varName -match 'PASSWORD') {
            $masked = $value.Substring(0, [Math]::Min(10, $value.Length)) + "***"
            Write-Host "[OK] $varName = $masked" -ForegroundColor Green
        } else {
            Write-Host "[OK] $varName = $value" -ForegroundColor Green
        }
    } catch {
        Write-Host "[FAIL] Failed to set $varName : $_" -ForegroundColor Red
    }
}

Write-Host ""

# ============================================
# VALIDATION
# ============================================
Write-Host "Validating environment variables..." -ForegroundColor Cyan
Write-Host ""

$validationPassed = $true

foreach ($varName in $envVars.Keys) {
    $value = [Environment]::GetEnvironmentVariable($varName, 'Machine')

    if ($value -eq $envVars[$varName]) {
        Write-Host "[OK] $varName verified" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $varName verification failed" -ForegroundColor Red
        $validationPassed = $false
    }
}

Write-Host ""

# ============================================
# CHECK FOR OPENAI API KEY
# ============================================
Write-Host "Checking for OpenAI API key..." -ForegroundColor Cyan

$openaiKey = [Environment]::GetEnvironmentVariable('OPENAI_API_KEY', 'Machine')

if ($openaiKey) {
    $masked = $openaiKey.Substring(0, [Math]::Min(10, $openaiKey.Length)) + "***"
    Write-Host "[OK] OPENAI_API_KEY found: $masked" -ForegroundColor Green
} else {
    Write-Host "[WARNING] OPENAI_API_KEY not found" -ForegroundColor Yellow
    Write-Host "          Graphiti requires an OpenAI API key for LLM operations." -ForegroundColor Yellow
    Write-Host "          Set it with:" -ForegroundColor Yellow
    Write-Host "          [Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-...', 'Machine')" -ForegroundColor White
}

Write-Host ""

# ============================================
# FINAL SUMMARY
# ============================================
Write-Host "========================================" -ForegroundColor Cyan
if ($validationPassed) {
    Write-Host " SETUP COMPLETE!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Environment variables successfully configured." -ForegroundColor Green
    Write-Host ""
    Write-Host "NEXT STEPS:" -ForegroundColor Yellow
    Write-Host "  1. Restart Claude Code (or any application using these variables)" -ForegroundColor White
    Write-Host "  2. The Graphiti MCP server should now connect to Neo4j Aura" -ForegroundColor White
    Write-Host ""

    if ($isVM) {
        Write-Host "VM Note: URI scheme automatically adjusted to neo4j+ssc://" -ForegroundColor Cyan
        Write-Host "         This prevents SSL certificate routing errors." -ForegroundColor Cyan
        Write-Host ""
    }
} else {
    Write-Host " SETUP FAILED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Some environment variables could not be set." -ForegroundColor Red
    Write-Host "Please review the errors above." -ForegroundColor Red
    Write-Host ""
}

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
