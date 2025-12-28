#!/usr/bin/env bash
#
# Standalone uninstall script for Graphiti MCP Bootstrap Service on Linux
#
# Description:
#   This script removes the Graphiti MCP Bootstrap Service and cleans up
#   installation files. It can run WITHOUT Python or the repository being present,
#   making it suitable for recovery scenarios.
#
#   Follows XDG Base Directory Specification (v2.1 architecture):
#   - Install Dir: ${XDG_DATA_HOME:-~/.local/share}/graphiti
#     Contains: lib/ (mcp_server, graphiti_core), .venv/, bin/
#   - Config Dir: ${XDG_CONFIG_HOME:-~/.config}/graphiti
#     Contains: graphiti.config.json
#   - State Dir: ${XDG_STATE_HOME:-~/.local/state}/graphiti
#     Contains: logs/, data/
#
#   What it does:
#   - Stops and disables systemd user service: graphiti-bootstrap.service
#   - Removes service file: ~/.config/systemd/user/graphiti-bootstrap.service
#   - Reloads systemd daemon
#   - Deletes install dir: ~/.local/share/graphiti (.venv, lib, bin)
#   - Deletes state dir logs: ~/.local/state/graphiti/logs
#   - Optionally preserves config and data directories
#
# Usage:
#   ./uninstall_linux.sh              # Interactive mode
#   ./uninstall_linux.sh --force      # Skip prompts, preserve config/data
#   ./uninstall_linux.sh --delete-all # Remove everything including config/data
#   ./uninstall_linux.sh --dry-run    # Preview actions without executing
#   ./uninstall_linux.sh --help       # Show help
#
# Manual removal if script fails:
#   1. systemctl --user stop graphiti-bootstrap
#   2. systemctl --user disable graphiti-bootstrap
#   3. rm ~/.config/systemd/user/graphiti-bootstrap.service
#   4. systemctl --user daemon-reload
#   5. rm -rf ~/.local/share/graphiti    # Install dir (venv, lib, bin)
#   6. rm -rf ~/.config/graphiti         # Config dir (graphiti.config.json)
#   7. rm -rf ~/.local/state/graphiti    # State dir (logs, data)
#   8. Remove from Claude config: ~/.config/Claude/claude_desktop_config.json
#   9. Remove from PATH in ~/.bashrc or ~/.zshrc
#
# Version: 1.0.0
# Created: 2025-12-23
# Part of: Graphiti MCP Server (https://github.com/getzep/graphiti)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Flags
FORCE=false
DELETE_ALL=false
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --delete-all)
            DELETE_ALL=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force       Skip prompts, preserve config/data"
            echo "  --delete-all  Remove everything including config/data"
            echo "  --dry-run     Preview actions without executing"
            echo "  --help        Show this help message"
            echo ""
            echo "Interactive mode (default): Prompts before deleting config/data"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Helper functions
step() {
    echo -e "${CYAN}==> $1${NC}"
}

success() {
    echo -e "${GREEN}[OK] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[!] $1${NC}"
}

error() {
    echo -e "${RED}[X] $1${NC}"
}

# Banner
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN} Graphiti MCP Uninstall (Linux)${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    warning "DRY RUN MODE - No changes will be made"
    echo ""
fi

# Define paths following XDG Base Directory Specification (v2.1 architecture)
XDG_DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
XDG_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
XDG_STATE="${XDG_STATE_HOME:-$HOME/.local/state}"

# Install directory: Contains lib/, .venv/, bin/
INSTALL_DIR="$XDG_DATA/graphiti"
# Config directory: Contains graphiti.config.json
CONFIG_DIR="$XDG_CONFIG/graphiti"
# State directory: Contains logs/, data/
STATE_DIR="$XDG_STATE/graphiti"

# Specific paths within each directory
VENV_DIR="$INSTALL_DIR/.venv"
LIB_DIR="$INSTALL_DIR/lib"           # contains mcp_server, graphiti_core
BIN_DIR="$INSTALL_DIR/bin"
LOGS_DIR="$STATE_DIR/logs"
DATA_DIR="$STATE_DIR/data"
CONFIG_FILE="$CONFIG_DIR/graphiti.config.json"

SERVICE_NAME="graphiti-bootstrap"

# Service directory (respect XDG_CONFIG_HOME)
SERVICE_DIR="$XDG_CONFIG/systemd/user"
SERVICE_FILE="$SERVICE_DIR/${SERVICE_NAME}.service"

# Track exit code
EXIT_CODE=0

# STEP 1: Stop and disable systemd service
step "Checking for systemd service '$SERVICE_NAME'..."

if [ -f "$SERVICE_FILE" ]; then
    # Check if service is running
    if systemctl --user is-active "$SERVICE_NAME" &>/dev/null; then
        step "Stopping service '$SERVICE_NAME'..."
        if [ "$DRY_RUN" = false ]; then
            if systemctl --user stop "$SERVICE_NAME" 2>&1; then
                success "Service stopped"
            else
                warning "Failed to stop service (may already be stopped)"
            fi
        else
            echo "[DRY RUN] Would stop service"
        fi
    else
        warning "Service '$SERVICE_NAME' not running"
    fi

    # Disable service
    step "Disabling service '$SERVICE_NAME'..."
    if [ "$DRY_RUN" = false ]; then
        if systemctl --user disable "$SERVICE_NAME" 2>&1; then
            success "Service disabled"
        else
            warning "Failed to disable service (may already be disabled)"
        fi
    else
        echo "[DRY RUN] Would disable service"
    fi

    # Remove service file
    step "Removing service file..."
    if [ "$DRY_RUN" = false ]; then
        if rm "$SERVICE_FILE" 2>&1; then
            success "Service file removed: $SERVICE_FILE"
        else
            error "Failed to remove service file: $SERVICE_FILE"
            EXIT_CODE=1
        fi
    else
        echo "[DRY RUN] Would remove: $SERVICE_FILE"
    fi

    # Reload systemd daemon
    step "Reloading systemd daemon..."
    if [ "$DRY_RUN" = false ]; then
        if systemctl --user daemon-reload 2>&1; then
            success "Systemd daemon reloaded"
        else
            warning "Failed to reload systemd daemon"
        fi
    else
        echo "[DRY RUN] Would reload systemd daemon"
    fi
else
    warning "Service file not found: $SERVICE_FILE (service may not be installed)"
fi

# STEP 2: Delete directories
echo ""
step "Cleaning up installation directories..."

delete_dir() {
    local dir_path=$1
    local dir_name=$2

    if [ -d "$dir_path" ]; then
        echo "Deleting: $dir_name - $dir_path"
        if [ "$DRY_RUN" = false ]; then
            if rm -rf "$dir_path" 2>&1; then
                success "Deleted: $dir_name"
            else
                error "Failed to delete $dir_name"
                EXIT_CODE=1
            fi
        else
            echo "[DRY RUN] Would delete: $dir_path"
        fi
    else
        echo "Not found: $dir_name - $dir_path (skipping)"
    fi
}

delete_dir "$VENV_DIR" "Virtual environment (.venv)"
delete_dir "$LIB_DIR" "Library packages (lib/)"
delete_dir "$BIN_DIR" "Wrapper scripts (bin/)"
delete_dir "$LOGS_DIR" "Service logs (logs/)"

# STEP 3: Handle config and data (preserve by default)
echo ""
step "Checking for user data and configuration..."

PRESERVE_ITEMS=()
if [ -f "$CONFIG_FILE" ]; then
    PRESERVE_ITEMS+=("$CONFIG_FILE|Configuration file (graphiti.config.json)")
fi
if [ -d "$DATA_DIR" ]; then
    PRESERVE_ITEMS+=("$DATA_DIR|User data (data/)")
fi

if [ ${#PRESERVE_ITEMS[@]} -gt 0 ]; then
    if [ "$DELETE_ALL" = true ]; then
        warning "DeleteAll flag set - removing config and data"
        for item in "${PRESERVE_ITEMS[@]}"; do
            IFS='|' read -r path name <<< "$item"
            echo "Deleting: $name - $path"
            if [ "$DRY_RUN" = false ]; then
                if rm -rf "$path" 2>&1; then
                    success "Deleted: $name"
                else
                    error "Failed to delete $name"
                    EXIT_CODE=1
                fi
            else
                echo "[DRY RUN] Would delete: $path"
            fi
        done
    elif [ "$FORCE" = true ]; then
        warning "Preserving config and data (use --delete-all to remove)"
        for item in "${PRESERVE_ITEMS[@]}"; do
            IFS='|' read -r path name <<< "$item"
            echo "Preserved: $name - $path"
        done
    else
        # Interactive mode - ask user
        warning "Found user data and configuration:"
        for item in "${PRESERVE_ITEMS[@]}"; do
            IFS='|' read -r path name <<< "$item"
            echo "  - $name: $path"
        done
        echo ""
        read -p "Delete config and data? (y/N): " -r response
        if [[ $response =~ ^[Yy]$ ]]; then
            for item in "${PRESERVE_ITEMS[@]}"; do
                IFS='|' read -r path name <<< "$item"
                echo "Deleting: $name - $path"
                if [ "$DRY_RUN" = false ]; then
                    if rm -rf "$path" 2>&1; then
                        success "Deleted: $name"
                    else
                        error "Failed to delete $name"
                        EXIT_CODE=1
                    fi
                else
                    echo "[DRY RUN] Would delete: $path"
                fi
            done
        else
            warning "Preserving config and data"
            for item in "${PRESERVE_ITEMS[@]}"; do
                IFS='|' read -r path name <<< "$item"
                echo "Preserved: $name - $path"
            done
        fi
    fi
else
    echo "No config or data found to preserve"
fi

# STEP 4: Clean up XDG directories if empty
echo ""

cleanup_empty_dir() {
    local dir_path=$1
    local dir_desc=$2

    if [ -d "$dir_path" ]; then
        if [ -z "$(ls -A "$dir_path")" ]; then
            step "Removing empty $dir_desc..."
            if [ "$DRY_RUN" = false ]; then
                if rmdir "$dir_path" 2>&1; then
                    success "Deleted: $dir_path"
                else
                    warning "Failed to delete $dir_path"
                fi
            else
                echo "[DRY RUN] Would delete: $dir_path"
            fi
        else
            warning "$dir_desc is not empty - leaving directory intact"
            echo "Remaining files:"
            find "$dir_path" -type f -o -type d | sed 's/^/  - /'
        fi
    fi
}

# Clean up all three XDG directories if empty
cleanup_empty_dir "$INSTALL_DIR" "install directory ($INSTALL_DIR)"
cleanup_empty_dir "$CONFIG_DIR" "config directory ($CONFIG_DIR)"
cleanup_empty_dir "$STATE_DIR" "state directory ($STATE_DIR)"

# STEP 5: Manual steps (Claude config, PATH)
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN} Manual Steps Required${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

warning "The following steps must be completed manually:"
echo ""

echo -e "${CYAN}1. Remove from Claude Desktop MCP configuration:${NC}"
echo "   - Open: ~/.config/Claude/claude_desktop_config.json"
echo "   - Remove the 'graphiti' entry from mcpServers"
echo ""

echo -e "${CYAN}2. Remove from PATH (if added):${NC}"
echo "   - Edit ~/.bashrc or ~/.zshrc"
echo "   - Remove line: export PATH=\"\$HOME/.local/share/graphiti/bin:\$PATH\""
echo "   - Run: source ~/.bashrc (or source ~/.zshrc)"
echo ""

echo -e "${CYAN}3. Restart Claude Desktop to apply changes${NC}"
echo ""

# Final summary
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN} Uninstall Summary${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    warning "DRY RUN completed - no changes were made"
else
    if [ $EXIT_CODE -eq 0 ]; then
        success "Uninstall completed successfully"
    else
        warning "Uninstall completed with errors (see above)"
    fi
fi

echo ""
echo "For support, visit: https://github.com/getzep/graphiti/issues"
echo ""

exit $EXIT_CODE
