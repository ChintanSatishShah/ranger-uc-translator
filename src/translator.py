"""
Ranger Policy Translator
Translates Apache Ranger policies to Unity Catalog SQL statements.
"""
from typing import List, Optional, Dict, Union
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
        
        catalog = self.config.catalog
        db_resource = resources.get('database')
        table_resource = resources.get('table')
        udf_resource = resources.get('udf')
        url_resource = resources.get('url')

        db_val = db_resource.values[0] if (db_resource and db_resource.values) else None
        table_val = table_resource.values[0] if (table_resource and table_resource.values) else None

        # URL/S3 policy: no UC equivalent — caller will emit a "not translatable" note
        if url_resource and not table_resource:
            return None

        # UDF-only policy: maps to UC FUNCTION grant
        if udf_resource and udf_resource.values and not table_resource:
            schema = db_val or self.config.schema
            udf = udf_resource.values[0]
            return f"FUNCTION {catalog}.{schema}.{udf}"

        # Catalog-wide: database=* with no specific table
        if db_val == '*' and (not table_val or table_val == '*'):
            return f"CATALOG {catalog}"

        # Schema-level: database specified but no table (or table=*)
        if db_val and (not table_val or table_val == '*'):
            return f"SCHEMA {catalog}.{db_val}"

        # Table-level
        if table_val:
            schema = db_val or self.config.schema
            return f"{catalog}.{schema}.{table_val}"

        return None
    
    def _translate_access(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate Ranger access policy to UC GRANT statements."""
        if not policy.policy_items:
            return None
        
        sql_statements = []
        principals = []
        
        # Build UC resource path
        resource = self._build_resource_path(policy.resources)
        if not resource:
            res_types = list(policy.resources.keys())
            msg = (
                f"Policy '{policy.name}' (id={policy.id}) cannot be translated to Unity Catalog.\n"
                f"-- Reason: resource types {res_types} have no Unity Catalog equivalent.\n"
                f"-- Ranger resource types like 'path', 'topic', 'cluster', 'entity', 'url'\n"
                f"-- are specific to HDFS, Kafka, Atlas, or S3 and do not map to UC objects."
            )
            self.errors.append(f"Not translatable — '{policy.name}' (id={policy.id}): resource types {res_types} have no UC equivalent.")
            return UCPolicy(
                policy_id=str(policy.id),
                policy_type="NOT_TRANSLATABLE",
                sql_statements=[utils.format_sql_statement(f"-- NOT TRANSLATABLE: {msg}", policy_name=policy.name, policy_id=str(policy.id), policy_description=policy.description)],
                description=f"Cannot translate policy '{policy.name}' to Unity Catalog",
                resource=str(res_types),
                principals=[]
            )

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

            # Grant to roles (mapped to UC groups/service principals)
            for role in (item.roles or []):
                uc_role = self.config.get_principal_mapping(role)
                principals.append(f"role:{uc_role}")

                for privilege in privileges:
                    grant_sql = f"GRANT {privilege} ON {resource} TO `{uc_role}`"
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
            res_types = list(policy.resources.keys())
            self.errors.append(f"Not translatable — '{policy.name}' (id={policy.id}): resource types {res_types} have no UC equivalent.")
            return UCPolicy(
                policy_id=str(policy.id),
                policy_type="NOT_TRANSLATABLE",
                sql_statements=[utils.format_sql_statement(
                    f"-- NOT TRANSLATABLE: Policy '{policy.name}' (id={policy.id})\n"
                    f"-- Reason: resource types {res_types} have no Unity Catalog equivalent.",
                    policy_name=policy.name, policy_id=str(policy.id), policy_description=policy.description
                )],
                description=f"Cannot translate row filter policy '{policy.name}' to Unity Catalog",
                resource=str(res_types),
                principals=[]
            )

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
            
            # Apply row filter to table for specified users/groups
            apply_filter = f"ALTER TABLE {resource} SET ROW FILTER {func_name} ON ({', '.join(principal_list)})"
            sql_statements.append(utils.format_sql_statement(apply_filter))
        
        if not sql_statements:
            return None
        
        return UCPolicy(
            policy_id=str(policy.id),
            policy_type="ROW_FILTER",
            sql_statements=sql_statements,
            description=policy.description or f"Row filter for {resource}",
            resource=resource,
            principals=principals
        )
    
    def _translate_column_mask(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate Ranger column masking policy to UC masking functions."""
        if not policy.masking_items:
            return None
        
        sql_statements = []
        principals = []
        
        # Build UC resource path
        resource = self._build_resource_path(policy.resources)
        if not resource:
            res_types = list(policy.resources.keys())
            self.errors.append(f"Not translatable — '{policy.name}' (id={policy.id}): resource types {res_types} have no UC equivalent.")
            return UCPolicy(
                policy_id=str(policy.id),
                policy_type="NOT_TRANSLATABLE",
                sql_statements=[utils.format_sql_statement(
                    f"-- NOT TRANSLATABLE: Policy '{policy.name}' (id={policy.id})\n"
                    f"-- Reason: resource types {res_types} have no Unity Catalog equivalent.",
                    policy_name=policy.name, policy_id=str(policy.id), policy_description=policy.description
                )],
                description=f"Cannot translate column mask policy '{policy.name}' to Unity Catalog",
                resource=str(res_types),
                principals=[]
            )

        parts = resource.split('.')
        if len(parts) != 3:
            self.errors.append(f"Invalid table path for column masking: {resource}")
            return None
        
        catalog, schema, table = parts
        
        # Get column(s) from resources
        column_resource = policy.resources.get('column')
        if not column_resource or not column_resource.values:
            self.errors.append(f"No columns specified for masking in policy {policy.id}")
            return None
        
        columns = column_resource.values
        
        # For each column, create masking function based on policy items
        is_first_stmt = True
        
        for column in columns:
            # Collect all masking rules for this column
            mask_none_users = []
            mask_none_groups = []
            default_mask_type = None
            
            for item in policy.masking_items:
                mask_type = item.mask_type
                
                # Ranger MASK_NONE means no masking for these users/groups
                if mask_type == 'MASK_NONE':
                    mask_none_users.extend(item.users)
                    mask_none_groups.extend(item.groups)
                else:
                    # Use the first non-NONE mask type as default
                    if not default_mask_type:
                        default_mask_type = mask_type
                    
                    # Collect principals who can see masked data
                    for user in item.users:
                        uc_user = self.config.get_principal_mapping(user)
                        principals.append(f"user:{uc_user}")
                    
                    for group in item.groups:
                        uc_group = self.config.get_principal_mapping(group)
                        principals.append(f"group:{uc_group}")
            
            # Generate mask function name
            func_name = utils.generate_masking_function_name(table, column, default_mask_type)
            
            # Get masking function from config
            mask_func = MASKING_FUNCTIONS.get(default_mask_type, MASKING_FUNCTIONS["MASK_REDACT"])
            
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
            # Replace {column} placeholder in mask expression
            masked_expr = mask_func.replace("{column}", column)
            conditions.append(f"ELSE {masked_expr}")
            
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
            description=policy.description or f"Column masking for {resource}",
            resource=resource,
            principals=principals
        )


class EnhancedPolicyTranslator(PolicyTranslator):
    """Enhanced policy translator with support for tag-based policies."""
    
    def __init__(self, config: TranslationConfig):
        super().__init__(config)
        self.tag_definitions = {}
        self.resource_tags = {}
    
    def set_tag_metadata(self, tag_definitions: Union[Dict, List], resource_tags: Union[Dict, List]):
        """Set tag metadata for resolving tag-based policies.
        
        Args:
            tag_definitions: Dictionary or list of tag definitions from Ranger export
            resource_tags: Dictionary or list of resource tags from Ranger export
        """
        # Handle tag_definitions as either dict or list
        if isinstance(tag_definitions, dict):
            # Already a dict: {tag_name: {name, attributeDefs}}
            self.tag_definitions = tag_definitions
        elif isinstance(tag_definitions, list):
            # Convert list to dict
            self.tag_definitions = {tag['name']: tag for tag in tag_definitions}
        else:
            self.tag_definitions = {}
        
        # Handle resource_tags as either dict or list
        if isinstance(resource_tags, dict):
            # Already a dict: {resource_path: [tag1, tag2]}
            self.resource_tags = resource_tags
        elif isinstance(resource_tags, list):
            # Convert list to dict (assuming list of objects with resource and tags fields)
            self.resource_tags = {}
            for item in resource_tags:
                resource = item.get('resource', {})
                tags = item.get('tags', [])
                # Build resource path from components
                database = resource.get('database', '')
                table = resource.get('table', '')
                columns = resource.get('column', [])
                if table:
                    for column in columns if columns else ['*']:
                        path = f"{database}.{table}.{column}" if database else f"{table}.{column}"
                        self.resource_tags[path] = tags
        else:
            self.resource_tags = {}
    
    def _get_tagged_columns(self, tag_name: str) -> List[Dict]:
        """Find all columns tagged with the specified tag.
        
        Returns:
            List of dicts with keys: database, table, column
        """
        tagged_columns = []
        
        # Iterate through resource_tags dict
        for resource_path, tags in self.resource_tags.items():
            # Check if this resource has the specified tag
            if tag_name in tags:
                # Parse resource path: expected format is "database.table.column"
                parts = resource_path.split('.')
                
                if len(parts) == 3:
                    database, table, column = parts
                elif len(parts) == 2:
                    # No database specified, use default schema
                    table, column = parts
                    database = self.config.schema
                else:
                    # Invalid format, skip
                    continue
                
                # Skip wildcard columns
                if column != '*':
                    tagged_columns.append({
                        'database': database,
                        'table': table,
                        'column': column
                    })
        
        return tagged_columns
    
    def translate(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate a single Ranger policy to UC format.
        
        Overrides parent to handle tag-based column masking policies.
        """
        # Check if this is a tag-based column masking policy
        if policy.policy_type == PolicyType.COLUMN_MASK:
            tag_resource = policy.resources.get('tag')
            if tag_resource and tag_resource.values:
                # This is a tag-based policy
                return self._translate_tag_based_column_mask(policy)
        
        # Otherwise use parent implementation
        return super().translate(policy)
    
    def _translate_tag_based_column_mask(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate tag-based column masking policy to UC masking functions.
        
        Tag-based policies don't specify table/column explicitly but reference
        data classified by tags (e.g., PII, SENSITIVE). This creates template
        functions that need manual adjustment for specific tables.
        """
        if not policy.masking_items:
            return None
        
        sql_statements = []
        principals = []
        
        # Get tag from resources
        tag_resource = policy.resources.get('tag')
        if not tag_resource or not tag_resource.values:
            self.errors.append(f"No tag specified for masking in policy {policy.id}")
            return None
        
        tag_name = tag_resource.values[0]
        catalog = self.config.catalog
        schema = self.config.schema
        
        # Collect masking rules
        mask_none_users = []
        mask_none_groups = []
        default_mask_type = None
        
        for item in policy.masking_items:
            mask_type = item.mask_type
            
            if mask_type == 'MASK_NONE':
                mask_none_users.extend(item.users)
                mask_none_groups.extend(item.groups)
            else:
                if not default_mask_type:
                    default_mask_type = mask_type
                
                for user in item.users:
                    uc_user = self.config.get_principal_mapping(user)
                    principals.append(f"user:{uc_user}")
                
                for group in item.groups:
                    uc_group = self.config.get_principal_mapping(group)
                    principals.append(f"group:{uc_group}")
        
        # Get masking function from config
        mask_func = MASKING_FUNCTIONS.get(default_mask_type, MASKING_FUNCTIONS["MASK_HASH"])
        
        # Find columns with this tag
        tagged_columns = self._get_tagged_columns(tag_name)
        
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
            # Replace {column} placeholder in mask expression
            masked_expr = mask_func.replace("{column}", column)
            conditions.append(f"ELSE {masked_expr}")
            
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
                    policy_description=policy.description
                ))
                is_first_stmt = False
            else:
                sql_statements.append(utils.format_sql_statement(create_func))
            
            # Apply mask to column
            apply_mask = f"ALTER TABLE {full_table} ALTER COLUMN {column} SET MASK {func_name}"
            sql_statements.append(utils.format_sql_statement(apply_mask))
        
        if not sql_statements:
            self.errors.append(
                f"Tag-based policy for tag '{tag_name}'. No tagged resources found in metadata. "
                f"Query your data catalog to find tables/columns with this tag."
            )
        
        return UCPolicy(
            policy_id=str(policy.id),
            policy_type="COLUMN_MASK_TAG",
            sql_statements=sql_statements,
            description=policy.description or f"Tag-based column masking for {tag_name}",
            resource=f"{catalog}.{schema}.<table_with_{tag_name}>",
            principals=principals
        )
