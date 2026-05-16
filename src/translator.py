"""
Ranger Policy Translator
Translates Apache Ranger policies to Unity Catalog SQL statements.
"""
from typing import List, Optional, Dict
from dataclasses import dataclass
from .parser import RangerPolicy, PolicyType
from .config import TranslationConfig, MASKING_FUNCTIONS
from . import utils


@dataclass
class UCPolicy:
    """Unity Catalog Policy representation."""
    policy_id: str
    policy_type: str
    sql_statements: List[str]
    description: str
    resource: str
    principals: List[str]


class PolicyTranslator:
    """Base translator for Ranger policies."""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.errors = []
    
    def translate(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate a single Ranger policy to UC format."""
        if policy.policy_type == PolicyType.ACCESS:
            return self._translate_access(policy)
        elif policy.policy_type == PolicyType.ROW_FILTER:
            return self._translate_row_filter(policy)
        elif policy.policy_type == PolicyType.COLUMN_MASK:
            return self._translate_column_mask(policy)
        else:
            self.errors.append(f"Unsupported policy type: {policy.policy_type}")
            return None
    
    def translate_all(self, policies: List[RangerPolicy]) -> List[UCPolicy]:
        """Translate multiple Ranger policies."""
        uc_policies = []
        for policy in policies:
            uc_policy = self.translate(policy)
            if uc_policy:
                uc_policies.append(uc_policy)
        return uc_policies
    
    def _build_resource_path(self, resources: Dict) -> Optional[str]:
        """Build UC resource path from Ranger resources.
        
        Handles three cases:
        1. Tag-based policies: Uses placeholder <table_with_TAG_NAME>
        2. Table with database: catalog.database.table
        3. Table without database: catalog.default_schema.table
        """
        # Check if this is a tag-based policy (uses 'tag' instead of 'table')
        tag_resource = resources.get('tag')
        if tag_resource and tag_resource.values:
            # Create placeholder for tag-based resources
            tag_names = '_'.join(tag_resource.values)  # Handle multiple tags
            catalog = self.config.catalog
            schema = self.config.schema
            placeholder = f"<table_with_{tag_names}>"
            self.errors.append(
                f"Tag-based policy detected. Replace placeholder '{catalog}.{schema}.{placeholder}' "
                f"with actual table name(s) that have tag(s): {', '.join(tag_resource.values)}"
            )
            return f"{catalog}.{schema}.{placeholder}"
        
        # Standard table-based policy
        table_resource = resources.get('table')
        
        # Table is mandatory for non-tag policies
        if not table_resource or not table_resource.values:
            return None
        
        table = table_resource.values[0]
        
        # Database is optional
        db_resource = resources.get('database')
        catalog = self.config.catalog
        
        if db_resource and db_resource.values:
            # Database provided: use it as UC schema
            database = db_resource.values[0]
            schema = database  # Ranger database maps to UC schema
            return f"{catalog}.{schema}.{table}"
        else:
            # No database: use configured schema as fallback
            schema = self.config.schema
            return f"{catalog}.{schema}.{table}"
    
    def _translate_access(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate Ranger access policy to UC GRANT statements."""
        if not policy.policy_items:
            return None
        
        sql_statements = []
        principals = []
        
        # Build UC resource path
        resource = self._build_resource_path(policy.resources)
        if not resource:
            self.errors.append(f"Could not determine resource for policy {policy.id}")
            return None
        
        # Generate GRANT statements
        is_first_stmt = True
        for item in policy.policy_items:
            privileges = [self.config.get_privilege_mapping(acc['type']) 
                         for acc in item.accesses if acc.get('isAllowed', True)]
            
            if not privileges:
                continue
            
            # Grant to users
            for user in item.users:
                uc_user = self.config.get_principal_mapping(user)
                principals.append(f"user:{uc_user}")
                
                for privilege in privileges:
                    grant_sql = f"GRANT {privilege} ON {resource} TO `{uc_user}`"
                    
                    # Add policy metadata to first statement only
                    if is_first_stmt:
                        sql_statements.append(utils.format_sql_statement(
                            grant_sql,
                            policy_name=policy.name,
                            policy_id=str(policy.id),
                            policy_description=policy.description
                        ))
                        is_first_stmt = False
                    else:
                        sql_statements.append(utils.format_sql_statement(grant_sql))
            
            # Grant to groups
            for group in item.groups:
                uc_group = self.config.get_principal_mapping(group)
                principals.append(f"group:{uc_group}")
                
                for privilege in privileges:
                    grant_sql = f"GRANT {privilege} ON {resource} TO `{uc_group}`"
                    sql_statements.append(utils.format_sql_statement(grant_sql))
        
        if not sql_statements:
            return None
        
        return UCPolicy(
            policy_id=str(policy.id),
            policy_type="ACCESS",
            sql_statements=sql_statements,
            description=policy.description or f"Access policy for {resource}",
            resource=resource,
            principals=principals
        )
    
    def _translate_row_filter(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate Ranger row filter to UC row filter functions."""
        if not policy.row_filter_items:
            return None
        
        sql_statements = []
        principals = []
        
        # Build UC resource path
        resource = self._build_resource_path(policy.resources)
        if not resource:
            self.errors.append(f"Could not determine resource for policy {policy.id}")
            return None
        
        parts = resource.split('.')
        if len(parts) != 3:
            self.errors.append(f"Invalid table path for row filter: {resource}")
            return None
        
        catalog, schema, table = parts
        
        # Generate row filter for each filter item
        is_first_stmt = True
        
        for idx, item in enumerate(policy.row_filter_items):
            if not item.filter_expr:
                continue
            
            # Generate function name
            func_name = utils.generate_row_filter_function_name(table, policy.id, idx)
            
            # Create row filter function
            create_filter = f"""CREATE OR REPLACE FUNCTION {catalog}.{schema}.{func_name}(row_data ANY TYPE)
RETURN {item.filter_expr}"""
            
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
            
            # Build principal list for ALTER TABLE
            principal_list = []
            for user in item.users:
                uc_user = self.config.get_principal_mapping(user)
                principal_list.append(f"`{uc_user}`")
                principals.append(f"user:{uc_user}")
            
            for group in item.groups:
                uc_group = self.config.get_principal_mapping(group)
                principal_list.append(f"`{uc_group}`")
                principals.append(f"group:{uc_group}")
            
            if principal_list:
                apply_filter = f"ALTER TABLE {resource} SET ROW FILTER {func_name} ON ({', '.join(principal_list)})"
                sql_statements.append(utils.format_sql_statement(apply_filter))
        
        if not sql_statements:
            return None
        
        return UCPolicy(
            policy_id=str(policy.id),
            policy_type="ROW_FILTER",
            sql_statements=sql_statements,
            description=policy.description or f"Row filter policy for {resource}",
            resource=resource,
            principals=principals
        )
    
    def _translate_column_mask(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate Ranger column masking to UC column mask functions with conditional logic."""
        if not policy.masking_items:
            return None
        
        # Check if this is a tag-based masking policy (handled by subclass)
        tag_resource = policy.resources.get('tag')
        if tag_resource and tag_resource.values:
            # Base class doesn't handle tag-based masking - let subclass override
            tag_names = ', '.join(tag_resource.values)
            self.errors.append(
                f"Tag-based column masking policy {policy.id} requires tag metadata. "
                f"Use EnhancedPolicyTranslator with tag metadata for tags: {tag_names}"
            )
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
        
        # Generate masking function for each column with conditional logic
        is_first_stmt = True
        
        for column in columns:
            # Separate MASK_NONE items from other mask types
            mask_none_items = []
            mask_apply_items = []
            
            for item in policy.masking_items:
                if item.mask_type == "MASK_NONE":
                    mask_none_items.append(item)
                else:
                    mask_apply_items.append(item)
            
            # Collect all MASK_NONE users and groups (they see original value)
            mask_none_users = []
            mask_none_groups = []
            for item in mask_none_items:
                mask_none_users.extend(item.users)
                mask_none_groups.extend(item.groups)
            
            # Get masking rules for users who should see masked data
            default_mask_type = "MASK_REDACT"  # Default if no specific mask defined
            
            if mask_apply_items:
                # Use the first mask_apply_item's mask type as default
                default_mask_type = mask_apply_items[0].mask_type
                
                # Collect users/groups from mask_apply_items
                for item in mask_apply_items:
                    for user in item.users:
                        uc_user = self.config.get_principal_mapping(user)
                        principals.append(f"user:{uc_user}")
                    for group in item.groups:
                        uc_group = self.config.get_principal_mapping(group)
                        principals.append(f"group:{uc_group}")
            
            # Generate mask function name
            func_name = utils.generate_masking_function_name(table, column, default_mask_type)
            
            # Get masking function from config
            mask_func = MASKING_FUNCTIONS.get(default_mask_type, "REDACT")
            
            # Build CASE statement for conditional masking
            conditions = []
            
            # Add conditions for MASK_NONE users (no masking)
            if mask_none_users:
                if len(mask_none_users) == 1:
                    conditions.append(f"WHEN is_account_group_member('{mask_none_users[0]}') THEN {column}")
                else:
                    user_list = "', '".join(mask_none_users)
                    conditions.append(f"WHEN current_user() IN ('{user_list}') THEN {column}")
            
            # Add conditions for MASK_NONE groups (no masking)
            for group in mask_none_groups:
                uc_group = self.config.get_principal_mapping(group)
                conditions.append(f"WHEN is_account_group_member('{uc_group}') THEN {column}")
            
            # Default: apply masking
            conditions.append(f"ELSE {mask_func}({column})")
            
            case_statement = "\n    ".join(conditions)
            
            # Create masking function with CASE logic
            create_func = f"""CREATE OR REPLACE FUNCTION {catalog}.{schema}.{func_name}({column} STRING)
RETURN CASE
    {case_statement}
END"""
            
            # Add policy metadata to first statement only
            if is_first_stmt:
                sql_statements.append(utils.format_sql_statement(
                    create_func,
                    policy_name=policy.name,
                    policy_id=str(policy.id),
                    policy_description=policy.description
                ))
                is_first_stmt = False
            else:
                sql_statements.append(utils.format_sql_statement(create_func))
            
            # Apply mask to column for all users
            apply_mask = f"ALTER TABLE {resource} ALTER COLUMN {column} SET MASK {func_name}"
            sql_statements.append(utils.format_sql_statement(apply_mask))
        
        if not sql_statements:
            return None
        
        return UCPolicy(
            policy_id=str(policy.id),
            policy_type="COLUMN_MASK",
            sql_statements=sql_statements,
            description=policy.description or f"Column masking policy for {resource}",
            resource=resource,
            principals=principals
        )


class EnhancedPolicyTranslator(PolicyTranslator):
    """Enhanced translator with tag-based policy support."""
    
    def __init__(self, config: TranslationConfig):
        super().__init__(config)
        self.tag_definitions = {}
        self.resource_tags = {}
    
    def set_tag_metadata(self, tag_definitions: Dict, resource_tags: Dict):
        """Set tag metadata for tag-based policies."""
        self.tag_definitions = tag_definitions
        self.resource_tags = resource_tags
    
    def translate(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate Ranger policy with tag support."""
        if policy.policy_type == PolicyType.TAG:
            return self._translate_tag_policy(policy)
        else:
            return super().translate(policy)
    
    def _translate_column_mask(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Override to handle tag-based column masking."""
        if not policy.masking_items:
            return None
        
        # Check if this is a tag-based masking policy
        tag_resource = policy.resources.get('tag')
        if tag_resource and tag_resource.values:
            # Handle tag-based column masking
            return self._translate_tag_based_column_mask(policy)
        
        # Fall back to standard column masking
        return super()._translate_column_mask(policy)
    
    def _translate_tag_based_column_mask(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate tag-based column masking to UC column mask functions."""
        tag_resource = policy.resources.get('tag')
        if not tag_resource or not tag_resource.values:
            return None
        
        policy_tags = tag_resource.values
        
        # Find all columns that have any of these tags
        tagged_columns = []
        for resource_path, tags in self.resource_tags.items():
            if any(tag in tags for tag in policy_tags):
                # Parse resource path as database.table.column
                parts = resource_path.split('.')
                if len(parts) == 3:
                    database, table, column = parts
                    tagged_columns.append({
                        'database': database,
                        'table': table,
                        'column': column,
                        'tags': tags
                    })
        
        if not tagged_columns:
            self.errors.append(
                f"No columns found with tags: {', '.join(policy_tags)} for policy {policy.id}"
            )
            return None
        
        sql_statements = []
        principals = []
        catalog = self.config.catalog
        
        # Get masking rules
        mask_none_users = []
        mask_none_groups = []
        default_mask_type = "MASK_HASH"  # Default for tag-based masking
        
        for item in policy.masking_items:
            if item.mask_type == "MASK_NONE":
                mask_none_users.extend(item.users)
                mask_none_groups.extend(item.groups)
            else:
                default_mask_type = item.mask_type
                # Collect principals
                for user in item.users:
                    uc_user = self.config.get_principal_mapping(user)
                    principals.append(f"user:{uc_user}")
                for group in item.groups:
                    uc_group = self.config.get_principal_mapping(group)
                    principals.append(f"group:{uc_group}")
        
        # Get masking function from config
        mask_func = MASKING_FUNCTIONS.get(default_mask_type, "SHA2")
        
        # Generate masking SQL for each tagged column
        is_first_stmt = True
        
        for col_info in tagged_columns:
            database = col_info['database']
            table = col_info['table']
            column = col_info['column']
            
            # Build full table path
            full_table = f"{catalog}.{database}.{table}"
            
            # Generate mask function name
            func_name = utils.generate_masking_function_name(table, column, default_mask_type)
            
            # Build CASE statement for conditional masking
            conditions = []
            
            # Add conditions for MASK_NONE users (no masking)
            if mask_none_users:
                if len(mask_none_users) == 1:
                    conditions.append(f"WHEN is_account_group_member('{mask_none_users[0]}') THEN {column}")
                else:
                    user_list = "', '".join(mask_none_users)
                    conditions.append(f"WHEN current_user() IN ('{user_list}') THEN {column}")
            
            # Add conditions for MASK_NONE groups (no masking)
            for group in mask_none_groups:
                uc_group = self.config.get_principal_mapping(group)
                conditions.append(f"WHEN is_account_group_member('{uc_group}') THEN {column}")
            
            # Default: apply masking
            conditions.append(f"ELSE {mask_func}({column})")
            
            case_statement = "\n    ".join(conditions)
            
            # Create masking function
            create_func = f"""CREATE OR REPLACE FUNCTION {catalog}.{database}.{func_name}({column} STRING)
RETURN CASE
    {case_statement}
END"""
            
            # Add policy metadata to first statement only
            if is_first_stmt:
                sql_statements.append(utils.format_sql_statement(
                    create_func,
                    policy_name=policy.name,
                    policy_id=str(policy.id),
                    policy_description=f"Tag-based masking for tags: {', '.join(policy_tags)}"
                ))
                is_first_stmt = False
            else:
                sql_statements.append(utils.format_sql_statement(create_func))
            
            # Apply mask to column
            apply_mask = f"ALTER TABLE {full_table} ALTER COLUMN {column} SET MASK {func_name}"
            sql_statements.append(utils.format_sql_statement(apply_mask))
        
        if not sql_statements:
            return None
        
        return UCPolicy(
            policy_id=str(policy.id),
            policy_type="COLUMN_MASK",
            sql_statements=sql_statements,
            description=f"Tag-based column masking for tags: {', '.join(policy_tags)}",
            resource=f"TAGS:{','.join(policy_tags)}",
            principals=principals
        )
    
    def _translate_tag_policy(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate tag-based policy to UC tag and grant statements."""
        if not policy.policy_items:
            return None
        
        # Get tag name from resources
        tag_resource = policy.resources.get('tag')
        if not tag_resource or not tag_resource.values:
            self.errors.append(f"Tag policy {policy.id} missing tag resource")
            return None
        
        tag_name = tag_resource.values[0]
        
        # Get resources that have this tag
        tagged_resources = []
        for resource_path, tags in self.resource_tags.items():
            if tag_name in tags:
                tagged_resources.append(resource_path)
        
        if not tagged_resources:
            self.errors.append(f"No resources found with tag {tag_name}")
            return None
        
        sql_statements = []
        principals = []
        
        # Create tag if it doesn't exist
        catalog = self.config.catalog
        create_tag = f"CREATE TAG IF NOT EXISTS {catalog}.{tag_name}"
        sql_statements.append(utils.format_sql_statement(
            create_tag,
            policy_name=policy.name,
            policy_id=str(policy.id),
            policy_description=policy.description
        ))
        
        # Apply tag to resources
        for resource in tagged_resources:
            alter_table = f"ALTER TABLE {resource} SET TAGS ('{tag_name}' = 'true')"
            sql_statements.append(utils.format_sql_statement(alter_table))
        
        # Generate grants for tagged resources
        for item in policy.policy_items:
            privileges = [self.config.get_privilege_mapping(acc['type']) 
                         for acc in item.accesses if acc.get('isAllowed', True)]
            
            if not privileges:
                continue
            
            for resource in tagged_resources:
                # Grant to users
                for user in item.users:
                    uc_user = self.config.get_principal_mapping(user)
                    principals.append(f"user:{uc_user}")
                    
                    for privilege in privileges:
                        grant_sql = f"GRANT {privilege} ON {resource} TO `{uc_user}`"
                        sql_statements.append(utils.format_sql_statement(grant_sql))
                
                # Grant to groups
                for group in item.groups:
                    uc_group = self.config.get_principal_mapping(group)
                    principals.append(f"group:{uc_group}")
                    
                    for privilege in privileges:
                        grant_sql = f"GRANT {privilege} ON {resource} TO `{uc_group}`"
                        sql_statements.append(utils.format_sql_statement(grant_sql))
        
        return UCPolicy(
            policy_id=str(policy.id),
            policy_type="TAG",
            sql_statements=sql_statements,
            description=policy.description or f"Tag-based policy for {tag_name}",
            resource=f"TAG:{tag_name}",
            principals=principals
        )
