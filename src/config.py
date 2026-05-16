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
    "create": "CREATE",
    "drop": "DROP",
    "alter": "ALTER",
    "all": "ALL PRIVILEGES",
    "admin": "ALL PRIVILEGES"
}

# Ranger to UC resource type mapping
RESOURCE_TYPE_MAPPING = {
    "database": "schema",
    "table": "table",
    "column": "column",
    "udf": "function"
}

# Column masking function templates
MASKING_FUNCTIONS = {
    "MASK_NONE": "column_value",  # No masking - return original value
    "MASK": "CASE WHEN is_account_group_member('{group}') THEN {{column}} ELSE 'XXXXX' END",
    "MASK_SHOW_LAST_4": "CASE WHEN is_account_group_member('{group}') THEN {{column}} ELSE CONCAT(REPEAT('X', LENGTH({{column}})-4), RIGHT({{column}}, 4)) END",
    "MASK_SHOW_FIRST_4": "CASE WHEN is_account_group_member('{group}') THEN {{column}} ELSE CONCAT(LEFT({{column}}, 4), REPEAT('X', LENGTH({{column}})-4)) END",
    "MASK_HASH": "CASE WHEN is_account_group_member('{group}') THEN {{column}} ELSE SHA2({{column}}, 256) END",
    "MASK_NULL": "CASE WHEN is_account_group_member('{group}') THEN {{column}} ELSE NULL END",
    "MASK_DATE_SHOW_YEAR": "CASE WHEN is_account_group_member('{group}') THEN {{column}} ELSE MAKE_DATE(YEAR({{column}}), 1, 1) END"
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
        return PRIVILEGE_MAPPING.get(ranger_privilege.lower(), ranger_privilege.upper())

# Default configuration instance
default_config = TranslationConfig()
