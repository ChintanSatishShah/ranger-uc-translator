"""
Translation engine for converting Ranger policies to Unity Catalog policies.
Handles ACL, row filters, column masks, and tag-based policies.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from parser import RangerPolicy, PolicyType, RangerPolicyItem, RangerRowFilterItem, RangerMaskingItem
from config import TranslationConfig, MASKING_FUNCTIONS
import utils

@dataclass
class UCPolicy:
    """Represents a Unity Catalog policy (SQL statement)."""
    policy_id: str
    policy_type: str
    sql_statements: List[str]
    description: str
    resource: str
    principals: List[str]

class PolicyTranslator:
    """Base translator for Ranger to UC policies."""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.translated_policies: List[UCPolicy] = []
        self.errors: List[str] = []
    
    def translate_all(self, policies: List[RangerPolicy]) -> List[UCPolicy]:
        """Translate all Ranger policies."""
        self.translated_policies = []
        self.errors = []
        
        for policy in policies:
            try:
                if policy.policy_type == PolicyType.ACCESS:
                    uc_policy = self._translate_acl(policy)
                elif policy.policy_type == PolicyType.ROW_FILTER:
                    uc_policy = self._translate_row_filter(policy)
                elif policy.policy_type == PolicyType.COLUMN_MASK:
                    uc_policy = self._translate_column_mask(policy)
                else:
                    self.errors.append(f"Unknown policy type: {policy.policy_type}")
                    continue
                
                if uc_policy:
                    self.translated_policies.append(uc_policy)
            except Exception as e:
                self.errors.append(f"Error translating policy {policy.id}: {str(e)}")
        
        return self.translated_policies
    
    def _translate_acl(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate Ranger ACL policy to UC GRANT statements."""
        if not policy.policy_items:
            return None
        
        sql_statements = []
        principals = []
        
        # Build UC resource path
        resource = self._build_resource_path(policy.resources)
        if not resource:
            self.errors.append(f"Could not determine resource for policy {policy.id}")
            return None
        
        # Generate GRANT statements for each policy item
        for item in policy.policy_items:
            for user in item.users:
                uc_user = self.config.get_principal_mapping(user)
                principals.append(f"user:{uc_user}")
                for access in item.accesses:
                    privilege = self.config.get_privilege_mapping(access['type'])
                    sql = f"GRANT {privilege} ON {resource} TO `{uc_user}`"
                    sql_statements.append(utils.format_sql_statement(sql))
            
            for group in item.groups:
                uc_group = self.config.get_principal_mapping(group)
                principals.append(f"group:{uc_group}")
                for access in item.accesses:
                    privilege = self.config.get_privilege_mapping(access['type'])
                    sql = f"GRANT {privilege} ON {resource} TO `{uc_group}`"
                    sql_statements.append(utils.format_sql_statement(sql))
        
        return UCPolicy(
            policy_id=str(policy.id),
            policy_type="ACL",
            sql_statements=sql_statements,
            description=policy.description or f"ACL policy for {resource}",
            resource=resource,
            principals=principals
        )
    
    def _translate_row_filter(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate Ranger row filter to UC row filter."""
        if not policy.row_filter_items:
            return None
        
        sql_statements = []
        principals = []
        
        # Build UC resource path (must be a table)
        resource = self._build_resource_path(policy.resources)
        if not resource or '.' not in resource:
            self.errors.append(f"Row filter requires table resource for policy {policy.id}")
            return None
        
        # Extract table parts
        parts = resource.split('.')
        if len(parts) != 3:
            self.errors.append(f"Invalid table path for row filter: {resource}")
            return None
        
        catalog, schema, table = parts
        
        # Generate row filter for each item
        for idx, item in enumerate(policy.row_filter_items):
            filter_name = f"rf_{table}_{policy.id}_{idx}"
            filter_expr = item.filter_expr
            
            # Collect principals for this filter
            filter_principals = []
            for user in item.users:
                uc_user = self.config.get_principal_mapping(user)
                filter_principals.append(f"`{uc_user}`")
                principals.append(f"user:{uc_user}")
            
            for group in item.groups:
                uc_group = self.config.get_principal_mapping(group)
                filter_principals.append(f"`{uc_group}`")
                principals.append(f"group:{uc_group}")
            
            # Create row filter function
            create_filter = f"""
CREATE OR REPLACE FUNCTION {catalog}.{schema}.{filter_name}(row ROW({table}))
RETURN IF(
  is_account_group_member('{filter_principals[0] if filter_principals else "users"}'),
  {filter_expr},
  FALSE
)
""".strip()
            
            # Attach filter to table
            attach_filter = f"ALTER TABLE {resource} SET ROW FILTER {filter_name} ON ({', '.join(filter_principals)})"
            
            sql_statements.append(utils.format_sql_statement(create_filter))
            sql_statements.append(utils.format_sql_statement(attach_filter))
        
        return UCPolicy(
            policy_id=str(policy.id),
            policy_type="ROW_FILTER",
            sql_statements=sql_statements,
            description=policy.description or f"Row filter policy for {resource}",
            resource=resource,
            principals=principals
        )
    
    def _translate_column_mask(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate Ranger column masking to UC column mask functions."""
        if not policy.masking_items:
            return None
        
        sql_statements = []
        principals = []
        
        # Build UC resource path
        resource = self._build_resource_path(policy.resources)
        if not resource:
            self.errors.append(f"Could not determine resource for masking policy {policy.id}")
            return None
        
        # Extract column from resources
        column_resource = policy.resources.get('column')
        if not column_resource or not column_resource.values:
            self.errors.append(f"Column masking requires column resource for policy {policy.id}")
            return None
        
        columns = column_resource.values
        parts = resource.split('.')
        if len(parts) != 3:
            self.errors.append(f"Invalid table path for column masking: {resource}")
            return None
        
        catalog, schema, table = parts
        
        # Generate masking function for each item and column
        for item in policy.masking_items:
            mask_type = item.mask_type
            
            # Get masking template
            mask_template = MASKING_FUNCTIONS.get(mask_type, MASKING_FUNCTIONS['MASK'])
            
            for column in columns:
                func_name = utils.generate_masking_function_name(table, column, mask_type)
                
                # Collect principals
                mask_principals = []
                for user in item.users:
                    uc_user = self.config.get_principal_mapping(user)
                    mask_principals.append(uc_user)
                    principals.append(f"user:{uc_user}")
                
                for group in item.groups:
                    uc_group = self.config.get_principal_mapping(group)
                    mask_principals.append(uc_group)
                    principals.append(f"group:{uc_group}")
                
                # Build masking expression
                mask_expr = mask_template.format(group=mask_principals[0] if mask_principals else 'users')
                mask_expr = mask_expr.replace('{column}', column)
                
                # Create masking function
                create_mask = f"""
CREATE OR REPLACE FUNCTION {catalog}.{schema}.{func_name}(column_value STRING)
RETURN {mask_expr}
""".strip()
                
                # Apply mask to column
                apply_mask = f"ALTER TABLE {resource} ALTER COLUMN {utils.sanitize_identifier(column)} SET MASK {func_name}"
                
                sql_statements.append(utils.format_sql_statement(create_mask))
                sql_statements.append(utils.format_sql_statement(apply_mask))
        
        return UCPolicy(
            policy_id=str(policy.id),
            policy_type="COLUMN_MASK",
            sql_statements=sql_statements,
            description=policy.description or f"Column masking policy for {resource}",
            resource=resource,
            principals=principals
        )
    
    def _build_resource_path(self, resources: Dict[str, Any]) -> Optional[str]:
        """Build Unity Catalog resource path from Ranger resources."""
        # Try to construct catalog.schema.table path
        database = resources.get('database')
        table = resources.get('table')
        
        if not database:
            return None
        
        db_values = database.values if database.values else []
        table_values = table.values if table and table.values else []
        
        if not db_values:
            return None
        
        # Use first value from each resource
        db_name = db_values[0]
        
        if table_values:
            table_name = table_values[0]
            # Assume database maps to schema, use default catalog
            return f"{self.config.catalog}.{db_name}.{table_name}"
        else:
            # Schema level
            return f"{self.config.catalog}.{db_name}"
    
    def get_summary(self) -> Dict[str, Any]:
        """Get translation summary."""
        return {
            "total_translated": len(self.translated_policies),
            "by_type": {
                "ACL": len([p for p in self.translated_policies if p.policy_type == "ACL"]),
                "ROW_FILTER": len([p for p in self.translated_policies if p.policy_type == "ROW_FILTER"]),
                "COLUMN_MASK": len([p for p in self.translated_policies if p.policy_type == "COLUMN_MASK"])
            },
            "total_sql_statements": sum(len(p.sql_statements) for p in self.translated_policies),
            "errors": len(self.errors)
        }

class TagPolicyTranslator:
    """Translator for Ranger tag-based policies to UC governed tags."""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.tag_sql: List[str] = []
        self.errors: List[str] = []
    
    def translate_tags(self, tags: Dict[str, Any], resource_tags: Dict[str, List[str]]) -> List[str]:
        """Translate Ranger tags to UC governed tags."""
        self.tag_sql = []
        
        # Create tag definitions
        for tag_name, tag_info in tags.items():
            create_tag = f"CREATE TAG IF NOT EXISTS {self.config.catalog}.{self.config.schema}.{tag_name}"
            self.tag_sql.append(utils.format_sql_statement(create_tag))
        
        # Apply tags to resources
        for resource, tag_list in resource_tags.items():
            uc_resource = self.config.get_resource_mapping(resource)
            for tag in tag_list:
                apply_tag = f"ALTER TABLE {uc_resource} SET TAGS ('{self.config.catalog}.{self.config.schema}.{tag}' = 'true')"
                self.tag_sql.append(utils.format_sql_statement(apply_tag))
        
        return self.tag_sql
