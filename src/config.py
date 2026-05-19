"""
Configuration module for Ranger to Unity Catalog policy translation.
Defines default mappings and configurable settings.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

# Default Unity Catalog settings
DEFAULT_CATALOG = "main"
DEFAULT_SCHEMA = "ranger_migration"

# Audit table names
AUDIT_TABLES = {
    "ranger_policies_raw": f"{DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.ranger_policies_raw",
    "translation_log": f"{DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.translation_log",
    "uc_policies_applied": f"{DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.uc_policies_applied",
    "mapping_config": f"{DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.mapping_config"
}

# Ranger to UC privilege mapping
PRIVILEGE_MAPPING = {
    "select": "SELECT",
    "read": "SELECT",
    "update": "MODIFY",
    "write": "MODIFY",
    "create": "CREATE",       # remapped context-sensitively in translator
    "drop": "MANAGE",         # UC has no DROP privilege; MANAGE is the closest equivalent
    "alter": "ALTER",
    "all": "ALL PRIVILEGES",
    "admin": "ALL PRIVILEGES"
}

# Ranger path/storage access types → UC External Location privileges
EXTERNAL_LOCATION_PRIVILEGE_MAPPING = {
    "read": "READ FILES",
    "write": "WRITE FILES",
    "execute": "READ FILES",   # closest UC equivalent for execute on a path
    "all": "ALL PRIVILEGES",
}

# Ranger to UC resource type mapping
RESOURCE_TYPE_MAPPING = {
    "database": "schema",
    "table": "table",
    "column": "column",
    "udf": "function"
}

# Column masking function expressions
# These are just the masking expressions - the translator builds the full CASE statement
MASKING_FUNCTIONS = {
    "MASK_NONE": "{column}",
    "MASK": "'XXXXX'",
    "MASK_SHOW_LAST_4": "CONCAT(REPEAT('X', LENGTH({column})-4), RIGHT({column}, 4))",
    "MASK_SHOW_FIRST_4": "CONCAT(LEFT({column}, 4), REPEAT('X', LENGTH({column})-4))",
    "MASK_HASH": "SHA2(CAST({column} AS STRING), 256)",
    "MASK_NULL": "NULL",
    "MASK_DATE_SHOW_YEAR": "MAKE_DATE(YEAR({column}), 1, 1)",
    "MASK_TIMESTAMP_SHOW_DATE": "DATE_TRUNC('DAY', {column})",
    "MASK_REDACT": "'[REDACTED]'"
}

# SQL parameter and return types for each masking function.
# Used to generate correctly-typed CREATE FUNCTION signatures.
MASKING_FUNCTION_TYPES = {
    "MASK_NONE":              {"param_type": "STRING",    "return_type": "STRING"},
    "MASK":                   {"param_type": "STRING",    "return_type": "STRING"},
    "MASK_SHOW_LAST_4":       {"param_type": "STRING",    "return_type": "STRING"},
    "MASK_SHOW_FIRST_4":      {"param_type": "STRING",    "return_type": "STRING"},
    "MASK_HASH":              {"param_type": "STRING",    "return_type": "STRING"},
    "MASK_NULL":              {"param_type": "STRING",    "return_type": "STRING"},
    "MASK_DATE_SHOW_YEAR":    {"param_type": "DATE",      "return_type": "DATE"},
    "MASK_TIMESTAMP_SHOW_DATE": {"param_type": "TIMESTAMP", "return_type": "TIMESTAMP"},
    "MASK_REDACT":            {"param_type": "STRING",    "return_type": "STRING"},
}

@dataclass
class TranslationConfig:
    """Configuration for policy translation."""
    catalog: str = DEFAULT_CATALOG
    schema: str = DEFAULT_SCHEMA
    dry_run: bool = True
    batch_size: int = 50
    skip_errors: bool = True
    create_tags: bool = True
    apply_grants: bool = True
    apply_row_filters: bool = True
    apply_column_masks: bool = True
    
    # Custom mappings (can be overridden by user)
    resource_mapping: Optional[Dict[str, str]] = None
    principal_mapping: Optional[Dict[str, str]] = None
    privilege_mapping: Optional[Dict[str, str]] = None
    
    def get_resource_mapping(self, ranger_resource: str) -> str:
        """Get UC resource path from Ranger resource path."""
        if self.resource_mapping and ranger_resource in self.resource_mapping:
            return self.resource_mapping[ranger_resource]
        
        # Default: assume Ranger paths map to catalog.schema.table
        # Example: /db/schema/table -> catalog.schema.table
        parts = ranger_resource.strip('/').split('/')
        if len(parts) == 1:
            return f"{self.catalog}.{parts[0]}"
        elif len(parts) == 2:
            return f"{self.catalog}.{parts[0]}.{parts[1]}"
        elif len(parts) >= 3:
            return f"{parts[0]}.{parts[1]}.{parts[2]}"
        return ranger_resource
    
    def get_principal_mapping(self, ranger_principal: str) -> str:
        """Get UC principal from Ranger user/group."""
        if self.principal_mapping and ranger_principal in self.principal_mapping:
            return self.principal_mapping[ranger_principal]
        return ranger_principal
    
    def get_privilege_mapping(self, ranger_privilege: str) -> str:
        """Get UC privilege from Ranger permission."""
        if self.privilege_mapping and ranger_privilege in self.privilege_mapping:
            return self.privilege_mapping[ranger_privilege]
        # Strip service prefix (e.g. "hive:select" -> "select")
        normalized = ranger_privilege.lower()
        if ':' in normalized:
            normalized = normalized.split(':', 1)[1]
        return PRIVILEGE_MAPPING.get(normalized, normalized.upper())

# Default configuration instance
default_config = TranslationConfig()
