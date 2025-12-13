# Neo4j Community Edition Environment Variables Setup Script
# DEPRECATED: Use setup-neo4j-community-wizard.ps1 instead
#
# This script is kept for reference but is no longer the recommended installation method.
# The new wizard includes all functionality from this script plus:
# - Prerequisite validation
# - Automatic Neo4j detection
# - Virtual environment creation
# - Service installation
# - .claude.json configuration
# - Connection testing
#
# Migration: Run setup-neo4j-community-wizard.ps1 (as Administrator)

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "DEPRECATED SCRIPT" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "This script is deprecated. Please use the new wizard instead:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  .\setup-neo4j-community-wizard.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "The wizard includes environment variable setup plus:" -ForegroundColor White
Write-Host "- Prerequisite validation" -ForegroundColor Gray
Write-Host "- Auto-install of missing components (Chocolatey, Java, uv)" -ForegroundColor Gray
Write-Host "- Neo4j installation detection" -ForegroundColor Gray
Write-Host "- Virtual environment creation" -ForegroundColor Gray
Write-Host "- Service installation and startup" -ForegroundColor Gray
Write-Host "- .claude.json configuration" -ForegroundColor Gray
Write-Host "- Connection testing" -ForegroundColor Gray
Write-Host ""
$continue = Read-Host "Continue anyway? (y/N)"
if ($continue -ne 'y' -and $continue -ne 'Y') {
    Write-Host "Exiting. Please run setup-neo4j-community-wizard.ps1 instead" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Neo4j Community Edition - Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "1. Right-click PowerShell" -ForegroundColor White
    Write-Host "2. Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "3. Run this script again" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Setting up environment variables for Neo4j Community Edition (Local)..." -ForegroundColor Green
Write-Host ""
Write-Host "These will be set at MACHINE level (system-wide)." -ForegroundColor Cyan
Write-Host ""

# Get current values (if any)
$currentUri = [Environment]::GetEnvironmentVariable('NEO4J_URI', 'Machine')
$currentUser = [Environment]::GetEnvironmentVariable('NEO4J_USER', 'Machine')
$currentPassword = [Environment]::GetEnvironmentVariable('NEO4J_PASSWORD', 'Machine')
$currentDatabase = [Environment]::GetEnvironmentVariable('NEO4J_DATABASE', 'Machine')

Write-Host "Current values:" -ForegroundColor Yellow
Write-Host "  NEO4J_URI      : $currentUri"
Write-Host "  NEO4J_USER     : $currentUser"
Write-Host "  NEO4J_PASSWORD : $(if ($currentPassword) { '***set***' } else { '(not set)' })"
Write-Host "  NEO4J_DATABASE : $currentDatabase"
Write-Host ""

# Prompt for each variable
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "Enter new values (or press Enter to keep current):" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

# NEO4J_URI
Write-Host "NEO4J_URI" -ForegroundColor Green
Write-Host "  For local Neo4j Community Edition: bolt://localhost:7687" -ForegroundColor Gray
Write-Host "  For Neo4j Aura (cloud): neo4j+ssc://xxxxx.databases.neo4j.io" -ForegroundColor Gray
$inputUri = Read-Host "  Enter NEO4J_URI [$currentUri]"
if ([string]::IsNullOrWhiteSpace($inputUri)) {
    $inputUri = $currentUri
}
if ([string]::IsNullOrWhiteSpace($inputUri)) {
    $inputUri = "bolt://localhost:7687"  # Default to local
}
Write-Host ""

# NEO4J_USER
Write-Host "NEO4J_USER" -ForegroundColor Green
Write-Host "  Default username is typically: neo4j" -ForegroundColor Gray
$inputUser = Read-Host "  Enter NEO4J_USER [$currentUser]"
if ([string]::IsNullOrWhiteSpace($inputUser)) {
    $inputUser = $currentUser
}
if ([string]::IsNullOrWhiteSpace($inputUser)) {
    $inputUser = "neo4j"  # Default username
}
Write-Host ""

# NEO4J_PASSWORD
Write-Host "NEO4J_PASSWORD" -ForegroundColor Green
Write-Host "  Enter the password you set when first logging into Neo4j Browser" -ForegroundColor Gray
Write-Host "  (or 'password' for simple dev environments)" -ForegroundColor Gray
$inputPassword = Read-Host "  Enter NEO4J_PASSWORD"
if ([string]::IsNullOrWhiteSpace($inputPassword)) {
    if (-not [string]::IsNullOrWhiteSpace($currentPassword)) {
        Write-Host "  Keeping current password (not displayed)" -ForegroundColor Yellow
        $inputPassword = $currentPassword
    } else {
        Write-Host "  ERROR: Password cannot be empty!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}
Write-Host ""

# NEO4J_DATABASE
Write-Host "NEO4J_DATABASE" -ForegroundColor Green
Write-Host "  Default database name is: neo4j" -ForegroundColor Gray
$inputDatabase = Read-Host "  Enter NEO4J_DATABASE [$currentDatabase]"
if ([string]::IsNullOrWhiteSpace($inputDatabase)) {
    $inputDatabase = $currentDatabase
}
if ([string]::IsNullOrWhiteSpace($inputDatabase)) {
    $inputDatabase = "neo4j"  # Default database
}
Write-Host ""

# Confirm before setting
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "Review your settings:" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "  NEO4J_URI      : $inputUri" -ForegroundColor White
Write-Host "  NEO4J_USER     : $inputUser" -ForegroundColor White
Write-Host "  NEO4J_PASSWORD : $inputPassword" -ForegroundColor White
Write-Host "  NEO4J_DATABASE : $inputDatabase" -ForegroundColor White
Write-Host ""

$confirm = Read-Host "Set these values? (Y/N)"
if ($confirm -ne "Y" -and $confirm -ne "y") {
    Write-Host "Cancelled. No changes made." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 0
}

# Set environment variables
Write-Host ""
Write-Host "Setting environment variables..." -ForegroundColor Green

try {
    [Environment]::SetEnvironmentVariable('NEO4J_URI', $inputUri, 'Machine')
    Write-Host "  [OK] NEO4J_URI = $inputUri" -ForegroundColor Green

    [Environment]::SetEnvironmentVariable('NEO4J_USER', $inputUser, 'Machine')
    Write-Host "  [OK] NEO4J_USER = $inputUser" -ForegroundColor Green

    [Environment]::SetEnvironmentVariable('NEO4J_PASSWORD', $inputPassword, 'Machine')
    Write-Host "  [OK] NEO4J_PASSWORD = ***set***" -ForegroundColor Green

    [Environment]::SetEnvironmentVariable('NEO4J_DATABASE', $inputDatabase, 'Machine')
    Write-Host "  [OK] NEO4J_DATABASE = $inputDatabase" -ForegroundColor Green

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Environment Variables Set Successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to set environment variables!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Verification
Write-Host "Verifying settings..." -ForegroundColor Cyan
Write-Host ""
$verifyUri = [Environment]::GetEnvironmentVariable('NEO4J_URI', 'Machine')
$verifyUser = [Environment]::GetEnvironmentVariable('NEO4J_USER', 'Machine')
$verifyPassword = [Environment]::GetEnvironmentVariable('NEO4J_PASSWORD', 'Machine')
$verifyDatabase = [Environment]::GetEnvironmentVariable('NEO4J_DATABASE', 'Machine')

Write-Host "Current system environment variables:" -ForegroundColor Yellow
Write-Host "  NEO4J_URI      : $verifyUri"
Write-Host "  NEO4J_USER     : $verifyUser"
Write-Host "  NEO4J_PASSWORD : $(if ($verifyPassword) { '***set***' } else { '(ERROR: not set!)' })"
Write-Host "  NEO4J_DATABASE : $verifyDatabase"
Write-Host ""

if ($verifyUri -eq $inputUri -and $verifyUser -eq $inputUser -and $verifyPassword -eq $inputPassword -and $verifyDatabase -eq $inputDatabase) {
    Write-Host "Verification: PASSED" -ForegroundColor Green
} else {
    Write-Host "WARNING: Verification mismatch!" -ForegroundColor Yellow
    Write-Host "Variables may require a system restart to take full effect." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Restart PowerShell" -ForegroundColor White
Write-Host "   (Environment variables won't be available in current session)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Restart Claude Code" -ForegroundColor White
Write-Host "   (So it picks up the new environment variables)" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Test Neo4j connection:" -ForegroundColor White
Write-Host "   cd C:\Users\Admin\Documents\GitHub\graphiti" -ForegroundColor Gray
Write-Host "   uv run python test_neo4j_connection.py" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Try using Graphiti MCP tools in Claude Code" -ForegroundColor White
Write-Host "   - add_memory" -ForegroundColor Gray
Write-Host "   - search_memory_nodes" -ForegroundColor Gray
Write-Host "   - search_memory_facts" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to exit"
