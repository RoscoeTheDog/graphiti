<#
.SYNOPSIS
    Standalone uninstall script for Graphiti MCP Bootstrap Service on Windows (v2.1)

.DESCRIPTION
    This PowerShell script removes the Graphiti MCP Bootstrap Service and cleans up
    installation files. It can run WITHOUT Python or the repository being present,
    making it suitable for recovery scenarios.

    v2.1 Architecture:
    - Install Dir: %LOCALAPPDATA%\Programs\Graphiti (contains .venv, lib, bin)
    - Config/State Dir: %LOCALAPPDATA%\Graphiti (contains config, logs, data)

    What it does:
    - Stops and removes NSSM service 'GraphitiBootstrap'
    - Deletes %LOCALAPPDATA%\Programs\Graphiti\.venv\ (virtual environment)
    - Deletes %LOCALAPPDATA%\Programs\Graphiti\lib\ (deployed packages: mcp_server, graphiti_core)
    - Deletes %LOCALAPPDATA%\Programs\Graphiti\bin\ (wrapper scripts)
    - Deletes %LOCALAPPDATA%\Graphiti\logs\ (service logs)
    - Optionally preserves %LOCALAPPDATA%\Graphiti\data\ and %LOCALAPPDATA%\Graphiti\config\graphiti.config.json

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
    Version: 2.1.0
    Created: 2025-12-23
    Updated: 2025-12-27 (v2.1 architecture)
    Part of: Graphiti MCP Server (https://github.com/getzep/graphiti)

    Manual removal if script fails:
    1. nssm stop GraphitiBootstrap
    2. nssm remove GraphitiBootstrap confirm
    3. rd /s /q %LOCALAPPDATA%\Programs\Graphiti
    4. rd /s /q %LOCALAPPDATA%\Graphiti
    5. Remove from Claude config: %APPDATA%\Claude\claude_desktop_config.json
    6. Remove from PATH if added
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
$IsAdmin = Test-Administrator
if (-not $IsAdmin) {
    Write-Warning "Running without administrator privileges."
    Write-Host "Service removal will be skipped. For complete uninstall, run as Administrator."
    Write-Host ""
}

# Define paths (v2.1 architecture)
# Install Dir: Contains .venv, lib (packages), bin (wrapper scripts)
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\Graphiti"
# State Dir: Contains config, logs, data (user data)
$StateDir = Join-Path $env:LOCALAPPDATA "Graphiti"

# Install directory contents
$VenvDir = Join-Path $InstallDir ".venv"
$LibDir = Join-Path $InstallDir "lib"
$BinDir = Join-Path $InstallDir "bin"

# State directory contents
$ConfigDir = Join-Path $StateDir "config"
$LogsDir = Join-Path $StateDir "logs"
$DataDir = Join-Path $StateDir "data"
$ConfigFile = Join-Path $ConfigDir "graphiti.config.json"

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

if ($IsAdmin) {
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
} else {
    Write-Warning "Skipping service removal (requires Administrator)"
    Write-Host "To remove service, re-run this script as Administrator"
    Write-Host ""
}

# STEP 2: Delete directories
Write-Host ""
Write-Step "Cleaning up installation directories..."

$DirsToDelete = @(
    @{ Path = $VenvDir; Name = "Virtual environment (.venv)" },
    @{ Path = $LibDir; Name = "Deployed packages (lib/)" },
    @{ Path = $BinDir; Name = "Wrapper scripts (bin/)" },
    @{ Path = $LogsDir; Name = "Service logs (logs/)" }
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
        # Also delete the config directory if -DeleteAll
        if (Test-Path $ConfigDir) {
            Write-Host "Deleting: Config directory (config/)"
            if (-not $DryRun) {
                try {
                    Remove-Item -Path $ConfigDir -Recurse -Force -ErrorAction Stop
                    Write-Success "Deleted: Config directory"
                } catch {
                    Write-Error "Failed to delete config directory: $_"
                    $ExitCode = 1
                }
            } else {
                Write-Host "[DRY RUN] Would delete: $ConfigDir"
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
            # Also delete the config directory
            if (Test-Path $ConfigDir) {
                Write-Host "Deleting: Config directory (config/)"
                if (-not $DryRun) {
                    try {
                        Remove-Item -Path $ConfigDir -Recurse -Force -ErrorAction Stop
                        Write-Success "Deleted: Config directory"
                    } catch {
                        Write-Error "Failed to delete config directory: $_"
                        $ExitCode = 1
                    }
                } else {
                    Write-Host "[DRY RUN] Would delete: $ConfigDir"
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

# STEP 4: Clean up installation and state directories if empty
Write-Host ""
Write-Step "Checking for empty directories to clean up..."

# Clean up Install Dir ($env:LOCALAPPDATA\Programs\Graphiti) if empty
if (Test-Path $InstallDir) {
    $remainingFiles = Get-ChildItem -Path $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
    if ($remainingFiles.Count -eq 0) {
        Write-Host "Removing empty install directory..."
        if (-not $DryRun) {
            try {
                Remove-Item -Path $InstallDir -Force -ErrorAction Stop
                Write-Success "Deleted: $InstallDir"
            } catch {
                Write-Warning "Failed to delete install directory: $_"
            }
        } else {
            Write-Host "[DRY RUN] Would delete: $InstallDir"
        }
    } else {
        Write-Warning "Install directory not empty - leaving intact: $InstallDir"
        Write-Host "Remaining files:"
        Get-ChildItem -Path $InstallDir -Recurse -Force | ForEach-Object {
            Write-Host "  - $($_.FullName)"
        }
    }
}

# Clean up State Dir ($env:LOCALAPPDATA\Graphiti) if empty
if (Test-Path $StateDir) {
    $remainingFiles = Get-ChildItem -Path $StateDir -Recurse -Force -ErrorAction SilentlyContinue
    if ($remainingFiles.Count -eq 0) {
        Write-Host "Removing empty state directory..."
        if (-not $DryRun) {
            try {
                Remove-Item -Path $StateDir -Force -ErrorAction Stop
                Write-Success "Deleted: $StateDir"
            } catch {
                Write-Warning "Failed to delete state directory: $_"
            }
        } else {
            Write-Host "[DRY RUN] Would delete: $StateDir"
        }
    } else {
        Write-Warning "State directory not empty - leaving intact: $StateDir"
        Write-Host "Remaining files:"
        Get-ChildItem -Path $StateDir -Recurse -Force | ForEach-Object {
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
Write-Host "   - Remove the 'graphiti-memory' entry from mcpServers"
Write-Host ""

Write-Host "2. Remove from PATH (if added):" -ForegroundColor $InfoColor
Write-Host "   - Open System Properties > Environment Variables"
Write-Host "   - Remove: $BinDir"
Write-Host "   - Or run: [Environment]::SetEnvironmentVariable('PATH', ([Environment]::GetEnvironmentVariable('PATH', 'User') -replace [regex]::Escape('$BinDir;'), ''), 'User')"
Write-Host ""

Write-Host "3. Restart Claude Desktop to apply changes" -ForegroundColor $InfoColor
Write-Host ""

Write-Host "v2.1 Paths Reference:" -ForegroundColor $InfoColor
Write-Host "   - Install Dir: $InstallDir"
Write-Host "   - State Dir:   $StateDir"
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
