<#
.SYNOPSIS
    Standalone uninstall script for Graphiti MCP Bootstrap Service on Windows

.DESCRIPTION
    This PowerShell script removes the Graphiti MCP Bootstrap Service and cleans up
    installation files. It can run WITHOUT Python or the repository being present,
    making it suitable for recovery scenarios.

    What it does:
    - Stops and removes NSSM service 'GraphitiBootstrap'
    - Deletes ~/.graphiti/.venv/ (virtual environment)
    - Deletes ~/.graphiti/mcp_server/ (deployed package)
    - Deletes ~/.graphiti/bin/ (wrapper scripts)
    - Deletes ~/.graphiti/logs/ (service logs)
    - Optionally preserves ~/.graphiti/data/ and ~/.graphiti/graphiti.config.json

.PARAMETER Force
    Skip user prompts and delete everything except config/data (default behavior)

.PARAMETER DeleteAll
    Delete EVERYTHING including config and data (use with caution)

.PARAMETER DryRun
    Preview actions without executing them

.PARAMETER Help
    Show this help message

.EXAMPLE
    .\uninstall_windows.ps1
    # Interactive mode - prompts before deleting config/data

.EXAMPLE
    .\uninstall_windows.ps1 -Force
    # Skip prompts, preserve config/data

.EXAMPLE
    .\uninstall_windows.ps1 -DeleteAll
    # Remove everything including config/data (complete uninstall)

.EXAMPLE
    .\uninstall_windows.ps1 -DryRun
    # Preview what would be deleted without actually deleting

.NOTES
    Version: 1.0.0
    Created: 2025-12-23
    Part of: Graphiti MCP Server (https://github.com/getzep/graphiti)

    Manual removal if script fails:
    1. nssm stop GraphitiBootstrap
    2. nssm remove GraphitiBootstrap confirm
    3. rd /s /q %USERPROFILE%\.graphiti
    4. Remove from Claude config: %APPDATA%\Claude\claude_desktop_config.json
    5. Remove from PATH if added
#>

param(
    [switch]$Force,
    [switch]$DeleteAll,
    [switch]$DryRun,
    [switch]$Help
)

# Show help if requested
if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit 0
}

# Colors for output
$ErrorColor = "Red"
$WarningColor = "Yellow"
$SuccessColor = "Green"
$InfoColor = "Cyan"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor $InfoColor
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor $SuccessColor
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor $WarningColor
}

function Write-Error {
    param([string]$Message)
    Write-Host "[X] $Message" -ForegroundColor $ErrorColor
}

function Test-Administrator {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Banner
Write-Host ""
Write-Host "========================================" -ForegroundColor $InfoColor
Write-Host " Graphiti MCP Uninstall (Windows)" -ForegroundColor $InfoColor
Write-Host "========================================" -ForegroundColor $InfoColor
Write-Host ""

if ($DryRun) {
    Write-Warning "DRY RUN MODE - No changes will be made"
    Write-Host ""
}

# Check for admin rights (required for service removal)
if (-not (Test-Administrator)) {
    Write-Error "This script requires administrator privileges to remove services."
    Write-Host ""
    Write-Host "Please run PowerShell as Administrator and try again:" -ForegroundColor $WarningColor
    Write-Host "  1. Right-click PowerShell" -ForegroundColor $WarningColor
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor $WarningColor
    Write-Host "  3. Re-run this script" -ForegroundColor $WarningColor
    Write-Host ""
    exit 1
}

# Define paths
$GraphitiDir = Join-Path $env:USERPROFILE ".graphiti"
$VenvDir = Join-Path $GraphitiDir ".venv"
$PackageDir = Join-Path $GraphitiDir "mcp_server"
$BinDir = Join-Path $GraphitiDir "bin"
$LogsDir = Join-Path $GraphitiDir "logs"
$ConfigFile = Join-Path $GraphitiDir "graphiti.config.json"
$DataDir = Join-Path $GraphitiDir "data"

$ServiceName = "GraphitiBootstrap"

# Track success/failure
$ExitCode = 0

# STEP 1: Stop and remove NSSM service
Write-Step "Checking for NSSM service '$ServiceName'..."

# Find NSSM
$NssmPath = $null
$NssmLocations = @(
    "nssm",  # In PATH
    "C:\Program Files\NSSM\nssm.exe",
    "C:\Program Files (x86)\NSSM\nssm.exe",
    (Join-Path $env:USERPROFILE "scoop\shims\nssm.exe")
)

foreach ($loc in $NssmLocations) {
    try {
        $resolved = Get-Command $loc -ErrorAction SilentlyContinue
        if ($resolved) {
            $NssmPath = $resolved.Source
            break
        }
    } catch {
        # Try next location
    }
}

if ($NssmPath) {
    Write-Host "Found NSSM: $NssmPath"

    # Check if service exists
    $statusOutput = & $NssmPath status $ServiceName 2>&1
    $serviceExists = $LASTEXITCODE -eq 0

    if ($serviceExists) {
        # Stop service
        Write-Step "Stopping service '$ServiceName'..."
        if (-not $DryRun) {
            $stopOutput = & $NssmPath stop $ServiceName 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Service stopped"
            } else {
                Write-Warning "Failed to stop service (may already be stopped)"
            }
        } else {
            Write-Host "[DRY RUN] Would stop service"
        }

        # Remove service
        Write-Step "Removing service '$ServiceName'..."
        if (-not $DryRun) {
            $removeOutput = & $NssmPath remove $ServiceName confirm 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Service removed"
            } else {
                Write-Error "Failed to remove service: $removeOutput"
                $ExitCode = 1
            }
        } else {
            Write-Host "[DRY RUN] Would remove service"
        }
    } else {
        Write-Warning "Service '$ServiceName' not found (may not be installed)"
    }
} else {
    Write-Warning "NSSM not found - skipping service removal"
    Write-Host "If service exists, remove manually:"
    Write-Host "  1. Install NSSM from https://nssm.cc/"
    Write-Host "  2. Run: nssm stop $ServiceName"
    Write-Host "  3. Run: nssm remove $ServiceName confirm"
    Write-Host ""
}

# STEP 2: Delete directories
Write-Host ""
Write-Step "Cleaning up installation directories..."

$DirsToDelete = @(
    @{ Path = $VenvDir; Name = "Virtual environment (.venv)" },
    @{ Path = $PackageDir; Name = "Deployed package (mcp_server)" },
    @{ Path = $BinDir; Name = "Wrapper scripts (bin)" },
    @{ Path = $LogsDir; Name = "Service logs (logs)" }
)

foreach ($dir in $DirsToDelete) {
    if (Test-Path $dir.Path) {
        Write-Host "Deleting: $($dir.Name) - $($dir.Path)"
        if (-not $DryRun) {
            try {
                Remove-Item -Path $dir.Path -Recurse -Force -ErrorAction Stop
                Write-Success "Deleted: $($dir.Name)"
            } catch {
                Write-Error "Failed to delete $($dir.Name): $_"
                $ExitCode = 1
            }
        } else {
            Write-Host "[DRY RUN] Would delete: $($dir.Path)"
        }
    } else {
        Write-Host "Not found: $($dir.Name) - $($dir.Path) (skipping)"
    }
}

# STEP 3: Handle config and data (preserve by default)
Write-Host ""
Write-Step "Checking for user data and configuration..."

$PreserveItems = @()
if (Test-Path $ConfigFile) {
    $PreserveItems += @{ Path = $ConfigFile; Name = "Configuration file (graphiti.config.json)" }
}
if (Test-Path $DataDir) {
    $PreserveItems += @{ Path = $DataDir; Name = "User data (data/)" }
}

if ($PreserveItems.Count -gt 0) {
    if ($DeleteAll) {
        Write-Warning "DeleteAll flag set - removing config and data"
        foreach ($item in $PreserveItems) {
            Write-Host "Deleting: $($item.Name) - $($item.Path)"
            if (-not $DryRun) {
                try {
                    if (Test-Path $item.Path -PathType Container) {
                        Remove-Item -Path $item.Path -Recurse -Force -ErrorAction Stop
                    } else {
                        Remove-Item -Path $item.Path -Force -ErrorAction Stop
                    }
                    Write-Success "Deleted: $($item.Name)"
                } catch {
                    Write-Error "Failed to delete $($item.Name): $_"
                    $ExitCode = 1
                }
            } else {
                Write-Host "[DRY RUN] Would delete: $($item.Path)"
            }
        }
    } elseif ($Force) {
        Write-Warning "Preserving config and data (use -DeleteAll to remove)"
        foreach ($item in $PreserveItems) {
            Write-Host "Preserved: $($item.Name) - $($item.Path)"
        }
    } else {
        # Interactive mode - ask user
        Write-Warning "Found user data and configuration:"
        foreach ($item in $PreserveItems) {
            Write-Host "  - $($item.Name): $($item.Path)"
        }
        Write-Host ""
        $response = Read-Host "Delete config and data? (y/N)"
        if ($response -match '^[Yy]') {
            foreach ($item in $PreserveItems) {
                Write-Host "Deleting: $($item.Name) - $($item.Path)"
                if (-not $DryRun) {
                    try {
                        if (Test-Path $item.Path -PathType Container) {
                            Remove-Item -Path $item.Path -Recurse -Force -ErrorAction Stop
                        } else {
                            Remove-Item -Path $item.Path -Force -ErrorAction Stop
                        }
                        Write-Success "Deleted: $($item.Name)"
                    } catch {
                        Write-Error "Failed to delete $($item.Name): $_"
                        $ExitCode = 1
                    }
                } else {
                    Write-Host "[DRY RUN] Would delete: $($item.Path)"
                }
            }
        } else {
            Write-Warning "Preserving config and data"
            foreach ($item in $PreserveItems) {
                Write-Host "Preserved: $($item.Name) - $($item.Path)"
            }
        }
    }
} else {
    Write-Host "No config or data found to preserve"
}

# STEP 4: Clean up ~/.graphiti if empty
Write-Host ""
if (Test-Path $GraphitiDir) {
    $remainingFiles = Get-ChildItem -Path $GraphitiDir -Recurse -Force -ErrorAction SilentlyContinue
    if ($remainingFiles.Count -eq 0) {
        Write-Step "Removing empty ~/.graphiti directory..."
        if (-not $DryRun) {
            try {
                Remove-Item -Path $GraphitiDir -Force -ErrorAction Stop
                Write-Success "Deleted: ~/.graphiti"
            } catch {
                Write-Warning "Failed to delete ~/.graphiti: $_"
            }
        } else {
            Write-Host "[DRY RUN] Would delete: $GraphitiDir"
        }
    } else {
        Write-Warning "~/.graphiti is not empty - leaving directory intact"
        Write-Host "Remaining files:"
        Get-ChildItem -Path $GraphitiDir -Recurse -Force | ForEach-Object {
            Write-Host "  - $($_.FullName)"
        }
    }
}

# STEP 5: Manual steps (Claude config, PATH)
Write-Host ""
Write-Host "========================================" -ForegroundColor $InfoColor
Write-Host " Manual Steps Required" -ForegroundColor $InfoColor
Write-Host "========================================" -ForegroundColor $InfoColor
Write-Host ""

Write-Warning "The following steps must be completed manually:"
Write-Host ""

Write-Host "1. Remove from Claude Desktop MCP configuration:" -ForegroundColor $InfoColor
Write-Host "   - Open: $env:APPDATA\Claude\claude_desktop_config.json"
Write-Host "   - Remove the 'graphiti' entry from mcpServers"
Write-Host ""

Write-Host "2. Remove from PATH (if added):" -ForegroundColor $InfoColor
Write-Host "   - Open System Properties > Environment Variables"
Write-Host "   - Remove: $BinDir"
Write-Host "   - Or run: [Environment]::SetEnvironmentVariable('PATH', ([Environment]::GetEnvironmentVariable('PATH', 'User') -replace [regex]::Escape('$BinDir;'), ''), 'User')"
Write-Host ""

Write-Host "3. Restart Claude Desktop to apply changes" -ForegroundColor $InfoColor
Write-Host ""

# Final summary
Write-Host ""
Write-Host "========================================" -ForegroundColor $InfoColor
Write-Host " Uninstall Summary" -ForegroundColor $InfoColor
Write-Host "========================================" -ForegroundColor $InfoColor
Write-Host ""

if ($DryRun) {
    Write-Warning "DRY RUN completed - no changes were made"
} else {
    if ($ExitCode -eq 0) {
        Write-Success "Uninstall completed successfully"
    } else {
        Write-Warning "Uninstall completed with errors (see above)"
    }
}

Write-Host ""
Write-Host "For support, visit: https://github.com/getzep/graphiti/issues"
Write-Host ""

exit $ExitCode
