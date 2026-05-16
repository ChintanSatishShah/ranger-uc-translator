"""
Unified translator for converting Ranger policies to Unity Catalog policies.
Handles ACL, row filters, column masks, and tag-based policies.
Merged from translator.py and translator_enhanced.py for better maintainability.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .parser import RangerPolicy, PolicyType, RangerPolicyItem, RangerRowFilterItem, RangerMaskingItem
from .config import TranslationConfig, MASKING_FUNCTIONS
from . import utils

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
        is_first_stmt = True
        for item in policy.policy_items:
            for user in item.users:
                uc_user = self.config.get_principal_mapping(user)
                principals.append(f"user:{uc_user}")
                for access in item.accesses:
                    privilege = self.config.get_privilege_mapping(access['type'])
                    sql = f"GRANT {privilege} ON {resource} TO `{uc_user}`"
                    # Add policy metadata to first statement only
                    if is_first_stmt:
                        sql_statements.append(utils.format_sql_statement(
                            sql, 
                            policy_name=policy.name,
                            policy_id=str(policy.id),
                            policy_description=policy.description
                        ))
                        is_first_stmt = False
                    else:
                        sql_statements.append(utils.format_sql_statement(sql))
            
            for group in item.groups:
                uc_group = self.config.get_principal_mapping(group)
                principals.append(f"group:{uc_group}")
                for access in item.accesses:
                    privilege = self.config.get_privilege_mapping(access['type'])
                    sql = f"GRANT {privilege} ON {resource} TO `{uc_group}`"
                    # Add policy metadata to first statement only
                    if is_first_stmt:
                        sql_statements.append(utils.format_sql_statement(
                            sql,
                            policy_name=policy.name,
                            policy_id=str(policy.id),
                            policy_description=policy.description
                        ))
                        is_first_stmt = False
                    else:
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
        is_first_stmt = True
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
            
            # Add policy metadata to first statement only
            if is_first_stmt:
                sql_statements.append(utils.format_sql_statement(
                    create_filter,
                    policy_name=policy.name,
                    policy_id=str(policy.id),
                    policy_description=policy.description
                ))
                is_first_stmt = False
            else:
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
        is_first_stmt = True
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
                
                # Add policy metadata to first statement only
                if is_first_stmt:
                    sql_statements.append(utils.format_sql_statement(
                        create_mask,
                        policy_name=policy.name,
                        policy_id=str(policy.id),
                        policy_description=policy.description
                    ))
                    is_first_stmt = False
                else:
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

class EnhancedPolicyTranslator(PolicyTranslator):
    """Enhanced translator with tag policy support."""
    
    def __init__(self, config: TranslationConfig):
        super().__init__(config)
        self.tag_definitions = {}
        self.resource_tags = {}
    
    def set_tag_metadata(self, tag_definitions: Dict[str, Any], resource_tags: Dict[str, List[str]]):
        """Set tag definitions and resource mappings."""
        self.tag_definitions = tag_definitions
        self.resource_tags = resource_tags
    
    def translate_all(self, policies: List[RangerPolicy]) -> List[UCPolicy]:
        """Enhanced translate_all with tag support."""
        self.translated_policies = []
        self.errors = []
        
        for policy in policies:
            try:
                # Check if this is a tag-based policy
                is_tag_policy = 'tag' in policy.resources
                
                if is_tag_policy:
                    # Tag-based policies need special handling
                    uc_policies = self._translate_tag_policy(policy)
                    if uc_policies:
                        self.translated_policies.extend(uc_policies)
                elif policy.policy_type == PolicyType.ACCESS:
                    uc_policy = self._translate_acl(policy)
                    if uc_policy:
                        self.translated_policies.append(uc_policy)
                elif policy.policy_type == PolicyType.ROW_FILTER:
                    uc_policy = self._translate_row_filter(policy)
                    if uc_policy:
                        self.translated_policies.append(uc_policy)
                elif policy.policy_type == PolicyType.COLUMN_MASK:
                    uc_policy = self._translate_column_mask(policy)
                    if uc_policy:
                        self.translated_policies.append(uc_policy)
                else:
                    self.errors.append(f"Unknown policy type: {policy.policy_type}")
                    continue
                
            except Exception as e:
                self.errors.append(f"Error translating policy {policy.id}: {str(e)}")
        
        return self.translated_policies
    
    def _translate_tag_policy(self, policy: RangerPolicy) -> List[UCPolicy]:
        """Translate tag-based Ranger policy to UC governed tags and policies."""
        if 'tag' not in policy.resources:
            self.errors.append(f"Tag policy {policy.id} has no tag resource")
            return []
        
        # Extract tag name
        tag_resource = policy.resources['tag']
        if not tag_resource.values:
            self.errors.append(f"Tag policy {policy.id} has empty tag values")
            return []
        
        tag_name = tag_resource.values[0]
        
        # Find all resources with this tag
        tagged_resources = []
        for resource, tags in self.resource_tags.items():
            if tag_name in tags:
                tagged_resources.append(resource)
        
        if not tagged_resources:
            self.errors.append(f"Tag policy {policy.id}: No resources found with tag '{tag_name}'")
            return []
        
        # Create UC policies for each tagged resource
        uc_policies = []
        
        # First, create the tag definition
        tag_policy = self._create_tag_definition(policy, tag_name)
        if tag_policy:
            uc_policies.append(tag_policy)
        
        # Then create policies for each resource based on policy type
        for resource in tagged_resources:
            uc_resource = self._map_ranger_resource_to_uc(resource)
            if not uc_resource:
                self.errors.append(f"Could not map resource '{resource}' to UC format")
                continue
            
            # Create a modified policy for this specific resource
            resource_policy = self._create_resource_policy(policy, uc_resource, tag_name)
            if resource_policy:
                uc_policies.append(resource_policy)
        
        return uc_policies
    
    def _create_tag_definition(self, policy: RangerPolicy, tag_name: str) -> Optional[UCPolicy]:
        """Create UC tag definition."""
        sql_statements = []
        
        # Create tag if it doesn't exist
        create_tag_sql = f"CREATE TAG IF NOT EXISTS {self.config.catalog}.{self.config.schema}.{tag_name}"
        
        # Add tag attributes if available
        if tag_name in self.tag_definitions:
            tag_info = self.tag_definitions[tag_name]
            attributes = tag_info.get('attributeDefs', {})
            if attributes:
                attr_comment = f"Tag attributes: {', '.join(f'{k}={v}' for k, v in attributes.items())}"
                create_tag_sql += f" COMMENT '{attr_comment}'"
        
        sql_statements.append(utils.format_sql_statement(create_tag_sql))
        
        return UCPolicy(
            policy_id=f"{policy.id}_tag_def",
            policy_type="TAG_DEFINITION",
            sql_statements=sql_statements,
            description=f"Tag definition for {tag_name}",
            resource=f"{self.config.catalog}.{self.config.schema}.{tag_name}",
            principals=[]
        )
    
    def _create_resource_policy(self, policy: RangerPolicy, uc_resource: str, tag_name: str) -> Optional[UCPolicy]:
        """Create UC policy for a tagged resource."""
        sql_statements = []
        principals = []
        
        # Apply tag to resource
        apply_tag_sql = f"ALTER TABLE {uc_resource} SET TAGS ('{self.config.catalog}.{self.config.schema}.{tag_name}' = 'true')"
        sql_statements.append(utils.format_sql_statement(apply_tag_sql))
        
        # If it's an access policy, create GRANT statements
        if policy.policy_items:
            for item in policy.policy_items:
                for user in item.users:
                    uc_user = self.config.get_principal_mapping(user)
                    principals.append(f"user:{uc_user}")
                    for access in item.accesses:
                        privilege = self.config.get_privilege_mapping(access['type'])
                        sql = f"GRANT {privilege} ON {uc_resource} TO `{uc_user}`"
                        sql_statements.append(utils.format_sql_statement(sql))
                
                for group in item.groups:
                    uc_group = self.config.get_principal_mapping(group)
                    principals.append(f"group:{uc_group}")
                    for access in item.accesses:
                        privilege = self.config.get_privilege_mapping(access['type'])
                        sql = f"GRANT {privilege} ON {uc_resource} TO `{uc_group}`"
                        sql_statements.append(utils.format_sql_statement(sql))
        
        # If it's a masking policy
        if policy.masking_items:
            # Extract column name from resource (format: db.table.column)
            parts = uc_resource.split('.')
            if len(parts) == 4:  # catalog.schema.table.column
                catalog, schema, table, column = parts
                table_resource = f"{catalog}.{schema}.{table}"
                
                for item in policy.masking_items:
                    mask_type = item.mask_type
                    from config import MASKING_FUNCTIONS
                    mask_template = MASKING_FUNCTIONS.get(mask_type, MASKING_FUNCTIONS['MASK'])
                    
                    func_name = utils.generate_masking_function_name(table, column, mask_type)
                    
                    mask_principals = []
                    for user in item.users:
                        uc_user = self.config.get_principal_mapping(user)
                        mask_principals.append(uc_user)
                        principals.append(f"user:{uc_user}")
                    
                    for group in item.groups:
                        uc_group = self.config.get_principal_mapping(group)
                        mask_principals.append(uc_group)
                        principals.append(f"group:{uc_group}")
                    
                    mask_expr = mask_template.format(group=mask_principals[0] if mask_principals else 'users')
                    mask_expr = mask_expr.replace('{column}', column)
                    
                    create_mask = f"""
CREATE OR REPLACE FUNCTION {catalog}.{schema}.{func_name}(column_value STRING)
RETURN {mask_expr}
""".strip()
                    
                    apply_mask = f"ALTER TABLE {table_resource} ALTER COLUMN {utils.sanitize_identifier(column)} SET MASK {func_name}"
                    
                    sql_statements.append(utils.format_sql_statement(create_mask))
                    sql_statements.append(utils.format_sql_statement(apply_mask))
        
        return UCPolicy(
            policy_id=f"{policy.id}_resource",
            policy_type="TAG_POLICY",
            sql_statements=sql_statements,
            description=f"Tag-based policy for {uc_resource} (tag: {tag_name})",
            resource=uc_resource,
            principals=principals
        )
    
    def _map_ranger_resource_to_uc(self, resource: str) -> Optional[str]:
        """Map Ranger resource format to UC format.
        
        Ranger format examples:
          - db.table => catalog.db.table
          - db.table.column => catalog.db.table.column
          - schema.* => catalog.schema.*
        """
        parts = resource.split('.')
        
        if len(parts) == 2:
            # db.table format
            return f"{self.config.catalog}.{parts[0]}.{parts[1]}"
        elif len(parts) == 3:
            # db.table.column format
            return f"{self.config.catalog}.{parts[0]}.{parts[1]}.{parts[2]}"
        elif len(parts) == 1:
            # Just db/schema
            return f"{self.config.catalog}.{parts[0]}"
        else:
            return None
