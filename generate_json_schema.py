"""Generate JSON schema from Pydantic models for IDE support."""

import json
from pathlib import Path

from mcp_server.unified_config import GraphitiConfig

# Generate schema
schema = GraphitiConfig.model_json_schema()

# Write to file
schema_path = Path("graphiti.config.schema.json")
with open(schema_path, "w") as f:
    json.dump(schema, f, indent=2)

print(f"Generated JSON schema: {schema_path}")
print(f"Schema has {len(schema.get('properties', {}))} top-level properties")
