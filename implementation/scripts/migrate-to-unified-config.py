#!/usr/bin/env python3
"""
Migrate from scattered .env configuration to unified config system.

Usage:
    python implementation/scripts/migrate-to-unified-config.py [--dry-run] [--force]

Options:
    --dry-run    Preview changes without modifying files
    --force      Overwrite existing graphiti.config.json without prompting
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple


# =============================================================================
# CONFIGURATION MAPPINGS
# =============================================================================

# Environment variable to config path mappings
# Format: "ENV_VAR": ("config.path.to.field", type_converter)
ENV_VAR_MAPPINGS = {
    # Database - Neo4j
    "NEO4J_URI": ("database.neo4j.uri", str),
    "NEO4J_USER": ("database.neo4j.user", str),
    "NEO4J_DATABASE": ("database.neo4j.database", str),

    # Database - FalkorDB
    "FALKORDB_URI": ("database.falkordb.uri", str),
    "FALKORDB_GRAPH_NAME": ("database.falkordb.graph_name", str),

    # Database - Backend selection
    "GRAPHITI_DB_BACKEND": ("database.backend", str),

    # LLM - General
    "MODEL_NAME": ("llm.default_model", str),
    "SEMAPHORE_LIMIT": ("llm.semaphore_limit", int),

    # LLM - Azure OpenAI
    "AZURE_OPENAI_ENDPOINT": ("llm.azure_openai.endpoint", str),
    "AZURE_OPENAI_API_VERSION": ("llm.azure_openai.api_version", str),
    "AZURE_OPENAI_DEPLOYMENT_NAME": ("llm.azure_openai.deployment_name", str),

    # Embedder
    "EMBEDDER_MODEL_NAME": ("embedder.model", str),
    "EMBEDDING_DIM": ("embedder.embedding_dim", int),

    # Embedder - Azure
    "AZURE_EMBEDDER_DEPLOYMENT_NAME": ("embedder.azure_openai.deployment_name", str),
}

# Secrets that should stay in .env (not in config file)
SECRETS = [
    "NEO4J_PASSWORD",
    "FALKORDB_PASSWORD",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
]

# Provider detection based on env vars
def detect_llm_provider(env_vars: Dict[str, str]) -> str:
    """Detect which LLM provider is being used."""
    if "AZURE_OPENAI_ENDPOINT" in env_vars:
        return "azure_openai"
    elif "ANTHROPIC_API_KEY" in env_vars and "OPENAI_API_KEY" not in env_vars:
        return "anthropic"
    else:
        return "openai"  # Default

def detect_embedder_provider(env_vars: Dict[str, str]) -> str:
    """Detect which embedder provider is being used."""
    if "AZURE_OPENAI_ENDPOINT" in env_vars and "AZURE_EMBEDDER_DEPLOYMENT_NAME" in env_vars:
        return "azure_openai"
    else:
        return "openai"  # Default


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def read_env_file(path: str = '.env') -> Dict[str, str]:
    """
    Parse .env file into dictionary.

    Args:
        path: Path to .env file

    Returns:
        Dict of environment variable key-value pairs
    """
    env_vars = {}

    if not Path(path).exists():
        print(f"[WARNING]  .env file not found at: {path}")
        return env_vars

    with open(path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                env_vars[key] = value
            else:
                print(f"[WARNING]  Skipping invalid line {line_num}: {line}")

    return env_vars


def set_nested_value(config: Dict[str, Any], path: str, value: Any) -> None:
    """
    Set value in nested dict using dot-notation path.

    Args:
        config: Configuration dictionary
        path: Dot-separated path (e.g., "database.neo4j.uri")
        value: Value to set

    Example:
        set_nested_value(config, "database.neo4j.uri", "bolt://localhost:7687")
    """
    keys = path.split('.')
    current = config

    # Navigate to parent
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    # Set value
    current[keys[-1]] = value


def generate_config_from_env(env_vars: Dict[str, str]) -> Dict[str, Any]:
    """
    Generate graphiti.config.json from environment variables.

    Args:
        env_vars: Dictionary of environment variables

    Returns:
        Complete configuration dictionary
    """
    # Load template as base
    template_path = Path('implementation/config/graphiti.config.json')

    if template_path.exists():
        with open(template_path) as f:
            config = json.load(f)
        print(f"[OK] Loaded template from: {template_path}")
    else:
        # Minimal default if template not found
        config = {
            "database": {"backend": "neo4j", "neo4j": {}, "falkordb": {}},
            "llm": {"openai": {}, "azure_openai": {}, "anthropic": {}},
            "embedder": {"openai": {}, "azure_openai": {}},
            "memory_filter": {"enabled": True},
        }
        print("[WARNING]  Template not found, using minimal defaults")

    # Apply environment variable mappings
    applied_count = 0
    for env_key, (config_path, type_converter) in ENV_VAR_MAPPINGS.items():
        if env_key in env_vars:
            value = env_vars[env_key]

            # Convert type
            try:
                if type_converter == bool:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif type_converter == int:
                    value = int(value)
                # str needs no conversion

                set_nested_value(config, config_path, value)
                applied_count += 1
                print(f"  [OK] Mapped: {env_key} → {config_path}")
            except (ValueError, TypeError) as e:
                print(f"  [WARNING]  Failed to convert {env_key}: {e}")

    # Auto-detect providers
    llm_provider = detect_llm_provider(env_vars)
    embedder_provider = detect_embedder_provider(env_vars)

    set_nested_value(config, "llm.provider", llm_provider)
    set_nested_value(config, "embedder.provider", embedder_provider)
    print(f"  [OK] Detected LLM provider: {llm_provider}")
    print(f"  [OK] Detected embedder provider: {embedder_provider}")

    print(f"\n[OK] Applied {applied_count} environment variable mappings")

    return config


def extract_secrets(env_vars: Dict[str, str]) -> str:
    """
    Create minimal .env file with only secrets.

    Args:
        env_vars: Dictionary of environment variables

    Returns:
        Content of new minimal .env file
    """
    lines = [
        "# Graphiti Secrets (generated by migration)",
        "# Structural config in graphiti.config.json",
        "",
    ]

    found_secrets = []
    for secret in SECRETS:
        if secret in env_vars:
            lines.append(f"{secret}={env_vars[secret]}")
            found_secrets.append(secret)

    if not found_secrets:
        lines.append("# No secrets found in original .env")

    print(f"\n[OK] Extracted {len(found_secrets)} secrets")
    for secret in found_secrets:
        print(f"  [OK] {secret}")

    return '\n'.join(lines) + '\n'


def backup_old_files() -> Tuple[list, list]:
    """
    Backup old configuration files with timestamp.

    Returns:
        Tuple of (backed_up_files, missing_files)
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backed_up = []
    missing = []

    files_to_backup = [
        '.env',
        'graphiti-filter.config.json',
    ]

    for filename in files_to_backup:
        if Path(filename).exists():
            backup_name = f"{filename}.backup.{timestamp}"
            shutil.copy(filename, backup_name)
            backed_up.append(filename)
            print(f"  [OK] Backed up: {filename} → {backup_name}")
        else:
            missing.append(filename)

    if backed_up:
        print(f"\n[OK] Backed up {len(backed_up)} files")
    if missing:
        print(f"[INFO]  Not found (skipped): {', '.join(missing)}")

    return backed_up, missing


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate generated configuration.

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    errors = []

    # Check required top-level keys
    required_keys = ["database", "llm", "embedder"]
    for key in required_keys:
        if key not in config:
            errors.append(f"Missing required key: {key}")

    # Check database backend
    if "database" in config:
        backend = config["database"].get("backend")
        if backend not in ["neo4j", "falkordb"]:
            errors.append(f"Invalid database backend: {backend}")

    # Check LLM provider
    if "llm" in config:
        provider = config["llm"].get("provider")
        if provider not in ["openai", "azure_openai", "anthropic"]:
            errors.append(f"Invalid LLM provider: {provider}")

    if errors:
        print("\n[ERROR] Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("\n[OK] Configuration validation passed")
    return True


# =============================================================================
# MAIN MIGRATION FUNCTION
# =============================================================================

def migrate(dry_run: bool = False, force: bool = False) -> int:
    """
    Main migration function.

    Args:
        dry_run: If True, preview changes without modifying files
        force: If True, overwrite existing files without prompting

    Returns:
        Exit code (0 = success, 1 = error)
    """
    print("=" * 70)
    print("Graphiti Configuration Migration Tool")
    print("=" * 70)
    print()

    # Safety checks
    config_path = Path('graphiti.config.json')
    if config_path.exists() and not force and not dry_run:
        print(f"[WARNING]  {config_path} already exists!")
        response = input("   Overwrite? (y/N): ").strip().lower()
        if response != 'y':
            print("\n[ERROR] Migration aborted by user")
            return 1

    # Step 1: Read old .env
    print("\n" + "-" * 70)
    print("Step 1: Reading .env file")
    print("-" * 70)
    env_vars = read_env_file('.env')

    if not env_vars:
        print("\n[WARNING]  No environment variables found")
        print("   Nothing to migrate!")
        return 0

    print(f"[OK] Found {len(env_vars)} environment variables")

    # Step 2: Generate config
    print("\n" + "-" * 70)
    print("Step 2: Generating unified configuration")
    print("-" * 70)
    config = generate_config_from_env(env_vars)

    # Step 3: Validate
    print("\n" + "-" * 70)
    print("Step 3: Validating configuration")
    print("-" * 70)
    if not validate_config(config):
        return 1

    # Step 4: Extract secrets
    print("\n" + "-" * 70)
    print("Step 4: Creating minimal .env")
    print("-" * 70)
    new_env = extract_secrets(env_vars)

    # Preview mode
    if dry_run:
        print("\n" + "=" * 70)
        print("DRY RUN MODE - No files will be modified")
        print("=" * 70)

        print("\nNew graphiti.config.json:")
        print("-" * 70)
        print(json.dumps(config, indent=2)[:1000])
        if len(json.dumps(config, indent=2)) > 1000:
            print("... (truncated, full output would be written)")

        print("\nNew .env:")
        print("-" * 70)
        print(new_env)

        print("\nDry run complete. Run without --dry-run to apply changes.")
        return 0

    # Step 5: Backup
    print("\n" + "-" * 70)
    print("Step 5: Backing up old files")
    print("-" * 70)
    backup_old_files()

    # Step 6: Write new files
    print("\n" + "-" * 70)
    print("Step 6: Writing new configuration")
    print("-" * 70)

    # Write graphiti.config.json
    with open('graphiti.config.json', 'w') as f:
        json.dump(config, f, indent=2)
    print(f"  [OK] Created: graphiti.config.json")

    # Write minimal .env
    with open('.env', 'w') as f:
        f.write(new_env)
    print(f"  [OK] Created: .env (minimal)")

    # Success
    print("\n" + "=" * 70)
    print("Migration Complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Review graphiti.config.json")
    print("  2. Test: python -m mcp_server.graphiti_mcp_server")
    print("  3. Commit graphiti.config.json to git (DO NOT commit .env)")
    print("\nBackup files created with timestamp suffix (.backup.YYYYMMDD_HHMMSS)")
    print("\n")

    return 0


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    # Parse command line arguments
    dry_run = '--dry-run' in sys.argv
    force = '--force' in sys.argv

    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)

    # Run migration
    exit_code = migrate(dry_run=dry_run, force=force)
    sys.exit(exit_code)
