#!/usr/bin/env bash
#
# Standalone uninstall script for Graphiti MCP Bootstrap Service on macOS
#
# Description:
#   This script removes the Graphiti MCP Bootstrap Service and cleans up
#   installation files. It can run WITHOUT Python or the repository being present,
#   making it suitable for recovery scenarios.
#
#   v2.1 Architecture (macOS Library convention):
#   - Install Dir: ~/Library/Application Support/Graphiti (lib/, .venv/, bin/)
#   - Config Dir:  ~/Library/Preferences/Graphiti (graphiti.config.json)
#   - Logs Dir:    ~/Library/Logs/Graphiti (service logs)
#   - Cache Dir:   ~/Library/Caches/Graphiti (runtime data)
#
#   What it does:
#   - Unloads and removes launchd plist: ~/Library/LaunchAgents/com.graphiti.bootstrap.plist
#   - Deletes ~/Library/Application Support/Graphiti/.venv/ (virtual environment)
#   - Deletes ~/Library/Application Support/Graphiti/lib/ (deployed packages)
#   - Deletes ~/Library/Application Support/Graphiti/bin/ (wrapper scripts)
#   - Deletes ~/Library/Logs/Graphiti/ (service logs)
#   - Optionally preserves ~/Library/Caches/Graphiti/ and ~/Library/Preferences/Graphiti/graphiti.config.json
#
# Usage:
#   ./uninstall_macos.sh              # Interactive mode
#   ./uninstall_macos.sh --force      # Skip prompts, preserve config/data
#   ./uninstall_macos.sh --delete-all # Remove everything including config/data
#   ./uninstall_macos.sh --dry-run    # Preview actions without executing
#   ./uninstall_macos.sh --help       # Show help
#
# Manual removal if script fails:
#   1. launchctl unload ~/Library/LaunchAgents/com.graphiti.bootstrap.plist
#   2. rm ~/Library/LaunchAgents/com.graphiti.bootstrap.plist
#   3. rm -rf ~/Library/Application\ Support/Graphiti
#   4. rm -rf ~/Library/Preferences/Graphiti
#   5. rm -rf ~/Library/Logs/Graphiti
#   6. rm -rf ~/Library/Caches/Graphiti
#   7. Remove from Claude config: ~/Library/Application Support/Claude/claude_desktop_config.json
#   8. Remove from PATH in ~/.zshrc or ~/.bash_profile
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
echo -e "${CYAN} Graphiti MCP Uninstall (macOS)${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    warning "DRY RUN MODE - No changes will be made"
    echo ""
fi

# Define paths - v2.1 macOS Library convention
INSTALL_DIR="$HOME/Library/Application Support/Graphiti"
CONFIG_DIR="$HOME/Library/Preferences/Graphiti"
LOGS_DIR="$HOME/Library/Logs/Graphiti"
CACHE_DIR="$HOME/Library/Caches/Graphiti"

VENV_DIR="$INSTALL_DIR/.venv"
LIB_DIR="$INSTALL_DIR/lib"  # contains mcp_server, graphiti_core
BIN_DIR="$INSTALL_DIR/bin"
DATA_DIR="$CACHE_DIR"
CONFIG_FILE="$CONFIG_DIR/graphiti.config.json"

SERVICE_ID="com.graphiti.bootstrap"
PLIST_PATH="$HOME/Library/LaunchAgents/${SERVICE_ID}.plist"

# Track exit code
EXIT_CODE=0

# STEP 1: Unload and remove launchd service
step "Checking for launchd service '$SERVICE_ID'..."

if [ -f "$PLIST_PATH" ]; then
    # Check if service is loaded
    if launchctl list | grep -q "$SERVICE_ID"; then
        step "Unloading service '$SERVICE_ID'..."
        if [ "$DRY_RUN" = false ]; then
            if launchctl unload "$PLIST_PATH" 2>&1; then
                success "Service unloaded"
            else
                warning "Failed to unload service (may already be stopped)"
            fi
        else
            echo "[DRY RUN] Would unload service"
        fi
    else
        warning "Service '$SERVICE_ID' not loaded (may already be stopped)"
    fi

    # Remove plist file
    step "Removing plist file..."
    if [ "$DRY_RUN" = false ]; then
        if rm "$PLIST_PATH" 2>&1; then
            success "Plist removed: $PLIST_PATH"
        else
            error "Failed to remove plist: $PLIST_PATH"
            EXIT_CODE=1
        fi
    else
        echo "[DRY RUN] Would remove: $PLIST_PATH"
    fi
else
    warning "Plist not found: $PLIST_PATH (service may not be installed)"
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
delete_dir "$LIB_DIR" "Deployed packages (lib/)"
delete_dir "$BIN_DIR" "Wrapper scripts (bin/)"
delete_dir "$LOGS_DIR" "Service logs (Library/Logs/Graphiti)"

# STEP 3: Handle config and data (preserve by default)
echo ""
step "Checking for user data and configuration..."

PRESERVE_ITEMS=()
if [ -f "$CONFIG_FILE" ]; then
    PRESERVE_ITEMS+=("$CONFIG_FILE|Configuration file (Preferences/Graphiti/graphiti.config.json)")
fi
if [ -d "$DATA_DIR" ]; then
    PRESERVE_ITEMS+=("$DATA_DIR|User data (Caches/Graphiti)")
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

# STEP 4: Clean up v2.1 directories if empty
echo ""

cleanup_if_empty() {
    local dir_path=$1
    local dir_name=$2

    if [ -d "$dir_path" ]; then
        if [ -z "$(ls -A "$dir_path")" ]; then
            step "Removing empty $dir_name directory..."
            if [ "$DRY_RUN" = false ]; then
                if rmdir "$dir_path" 2>&1; then
                    success "Deleted: $dir_name"
                else
                    warning "Failed to delete $dir_name"
                fi
            else
                echo "[DRY RUN] Would delete: $dir_path"
            fi
        else
            warning "$dir_name is not empty - leaving directory intact"
            echo "Remaining files:"
            find "$dir_path" -type f -o -type d | head -20 | sed 's/^/  - /'
        fi
    fi
}

# Clean up all v2.1 directories if empty
cleanup_if_empty "$INSTALL_DIR" "Library/Application Support/Graphiti"
cleanup_if_empty "$CONFIG_DIR" "Library/Preferences/Graphiti"
cleanup_if_empty "$LOGS_DIR" "Library/Logs/Graphiti"
cleanup_if_empty "$CACHE_DIR" "Library/Caches/Graphiti"

# STEP 5: Manual steps (Claude config, PATH)
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN} Manual Steps Required${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

warning "The following steps must be completed manually:"
echo ""

echo -e "${CYAN}1. Remove from Claude Desktop MCP configuration:${NC}"
echo "   - Open: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "   - Remove the 'graphiti' entry from mcpServers"
echo ""

echo -e "${CYAN}2. Remove from PATH (if added):${NC}"
echo "   - Edit ~/.zshrc or ~/.bash_profile"
echo "   - Remove line: export PATH=\"$BIN_DIR:\$PATH\""
echo "   - Run: source ~/.zshrc (or source ~/.bash_profile)"
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
