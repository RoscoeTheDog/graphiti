"""
Test Neo4j connection using environment variables.

This script tests the Neo4j connection for Graphiti development.
It reads credentials from environment variables:
- NEO4J_URI
- NEO4J_USER
- NEO4J_PASSWORD

On Windows, if environment variables are not found in the current session,
it will attempt to load them from machine-level (system-wide) environment variables.
"""

import os
import sys
from datetime import datetime

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j package not installed")
    print("Please run: uv pip install neo4j")
    sys.exit(1)


def load_windows_machine_env_vars():
    """Load machine-level environment variables on Windows."""
    if sys.platform != 'win32':
        return

    try:
        import winreg

        # Open the Machine environment variables registry key
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
            0,
            winreg.KEY_READ
        )

        # List of variables to load
        var_names = ['NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD', 'NEO4J_DATABASE']

        for var_name in var_names:
            try:
                value, _ = winreg.QueryValueEx(key, var_name)
                # Only set if not already in environment
                if var_name not in os.environ:
                    os.environ[var_name] = value
            except FileNotFoundError:
                # Variable doesn't exist in registry, skip it
                pass

        winreg.CloseKey(key)
    except Exception as e:
        # If we can't read from registry, just continue with existing env vars
        pass


def test_connection():
    """Test Neo4j connection using environment variables."""
    # On Windows, attempt to load machine-level environment variables
    if sys.platform == 'win32':
        print("Loading environment variables from Windows registry...")
        load_windows_machine_env_vars()
        print("")

    # Read from environment variables
    uri = os.environ.get('NEO4J_URI')
    user = os.environ.get('NEO4J_USER')
    password = os.environ.get('NEO4J_PASSWORD')
    database = os.environ.get('NEO4J_DATABASE')

    # Show loaded variables
    print("Environment variables loaded:")
    print(f"  NEO4J_URI      : {uri or '(not set)'}")
    print(f"  NEO4J_USER     : {user or '(not set)'}")
    print(f"  NEO4J_PASSWORD : {'***set***' if password else '(not set)'}")
    print(f"  NEO4J_DATABASE : {database or '(not set)'}")
    print("")

    # Validate environment variables
    if not uri:
        print("ERROR: NEO4J_URI environment variable not set")
        sys.exit(1)
    if not user:
        print("ERROR: NEO4J_USER environment variable not set")
        sys.exit(1)
    if not password:
        print("ERROR: NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    print(f"Attempting to connect to Neo4j at {uri}...")
    print(f"Username: {user}")
    print("")

    try:
        # Create driver
        driver = GraphDatabase.driver(uri, auth=(user, password))

        # Test connection with a simple query
        with driver.session() as session:
            result = session.run("RETURN 'Connection successful!' as message, datetime() as timestamp")
            record = result.single()
            print(f"[OK] {record['message']}")
            print(f"     Timestamp: {record['timestamp']}")

        driver.close()
        print("")
        print("[OK] Neo4j connection test PASSED")
        return True

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print("")
        print("Troubleshooting:")
        print("1. Verify Neo4j service is running: Get-Service Neo4j")
        print("2. Check Neo4j Browser works: http://localhost:7474")
        print("3. Verify credentials are correct")
        print("4. Check environment variables are set")
        sys.exit(1)


if __name__ == "__main__":
    test_connection()
