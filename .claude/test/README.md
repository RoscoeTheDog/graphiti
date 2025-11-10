# Test Scripts

**Purpose:** Ephemeral testing scripts for development and CI/CD validation.

**Category:** test (ephemeral)
**Policy:** Files in this directory are temporary and used for sprint testing, connection validation, and CI/CD verification.

---

## Files

### test_neo4j_community_connection.py
**Purpose:** Test Neo4j connection using environment variables
**Usage:**
```bash
# Set environment variables first
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password

# Run test
python .claude/test/test_neo4j_community_connection.py
```

**Description:** Validates Neo4j connection for Graphiti development. On Windows, attempts to load machine-level environment variables if not found in session.

---

### docker-compose.test.yml
**Purpose:** Docker Compose configuration for CI/CD testing
**Usage:**
```bash
# Used in CI/CD workflows
docker-compose -f .claude/test/docker-compose.test.yml up
```

**Description:** Defines test services (graphiti-service + Neo4j) for automated testing in GitHub Actions.

---

## Notes

- **Migration Date:** 2025-11-06 - Migrated from root directory to .claude/test/
- **Original Location:** Root directory (cluttered)
- **New Location:** .claude/test/ (organized, ephemeral)
- **Integration Tests:** Located in tests/ directory (permanent)
- **These Tests:** Development/validation scripts (ephemeral)

---

**Last Updated:** 2025-11-06
