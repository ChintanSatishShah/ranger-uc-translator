"""
Ranger Policy Translator
Translates Apache Ranger policies to Unity Catalog SQL statements.
"""
from typing import List, Optional, Dict, Union
from dataclasses import dataclass
from .parser import RangerPolicy, PolicyType
from .config import (
    TranslationConfig, MASKING_FUNCTIONS, MASKING_FUNCTION_TYPES,
    EXTERNAL_LOCATION_PRIVILEGE_MAPPING
)
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
    
    def _is_path_policy(self, policy: RangerPolicy) -> bool:
        """True if this policy governs file paths (HDFS, S3, URL) → UC External Location."""
        return bool(
            policy.resources.get('path') or
            policy.resources.get('url')
        ) and not policy.resources.get('table')

    def translate(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate a single Ranger policy to UC format."""
        if self._is_path_policy(policy):
            return self._translate_path_policy(policy)
        if policy.policy_type == PolicyType.ACCESS:
            return self._translate_access(policy)
        elif policy.policy_type == PolicyType.ROW_FILTER:
            return self._translate_row_filter(policy)
        elif policy.policy_type == PolicyType.COLUMN_MASK:
            return self._translate_column_mask(policy)
        else:
            self.errors.append(f"Unsupported policy type: {policy.policy_type}")
            return None

    def _translate_path_policy(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate HDFS/S3 path policy to UC External Location grants."""
        path_resource = policy.resources.get('path') or policy.resources.get('url')
        if not path_resource or not path_resource.values:
            return None

        paths = path_resource.values
        sql_statements = []
        principals = []
        is_first = True

        for path in paths:
            # Derive a syntactically-valid External Location placeholder identifier.
            # Angle-bracket notation (<...>) is not a valid SQL identifier even in backticks,
            # so we use a plain prefixed name and document the original path in a comment.
            import re as _re
            slug = path.strip('/').replace('/', '_').replace('*', 'all').replace('{USER}', 'USER') or 'root'
            slug = _re.sub(r'[^a-zA-Z0-9_]', '_', slug)
            ext_loc_name = f"ext_loc_{slug}"  # valid SQL identifier — replace with actual UC External Location name

            for item in (policy.policy_items or []):
                privileges = [
                    EXTERNAL_LOCATION_PRIVILEGE_MAPPING.get(a['type'].lower(), a['type'].upper())
                    for a in item.accesses if a.get('isAllowed', True) and a.get('type')
                ]
                if not privileges:
                    continue

                for principal in list(item.users) + list(item.groups) + list(item.roles or []):
                    uc_principal = self.config.get_principal_mapping(principal)
                    principals.append(uc_principal)
                    for priv in privileges:
                        grant_sql = f"GRANT {priv} ON EXTERNAL LOCATION `{ext_loc_name}` TO `{uc_principal}`"
                        if is_first:
                            sql_statements.append(utils.format_sql_statement(
                                grant_sql,
                                policy_name=policy.name,
                                policy_id=str(policy.id),
                                policy_description=(
                                    f"{policy.description or ''}\n"
                                    f"-- NOTE: Replace '{ext_loc_name}' with the actual UC External Location name\n"
                                    f"-- that corresponds to the Ranger path: {path}"
                                ).strip()
                            ))
                            is_first = False
                        else:
                            sql_statements.append(utils.format_sql_statement(grant_sql))

        if not sql_statements:
            return None

        return UCPolicy(
            policy_id=str(policy.id),
            policy_type="EXTERNAL_LOCATION",
            sql_statements=sql_statements,
            description=f"External Location grant for path(s): {paths}",
            resource=f"EXTERNAL LOCATION {paths}",
            principals=principals
        )
    
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

        # URL/S3 policy: handled separately as External Location grant
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
            # Wildcard tables or HBase-style "NAMESPACE:table" patterns cannot be expressed
            # as a single UC table reference — fall back to schema-level grant.
            import re as _re
            if '*' in table_val or ':' in table_val or _re.search(r'[^a-zA-Z0-9_`\-]', table_val):
                return f"SCHEMA {catalog}.{schema}"
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
            # Explain why each resource type cannot be translated
            reasons = {
                'topic': "Kafka topics are managed by Kafka ACLs, not Unity Catalog.",
                'cluster': "Kafka cluster admin is managed by Kafka ACLs, not Unity Catalog.",
                'consumergroup': "Kafka consumer groups are managed by Kafka ACLs, not Unity Catalog.",
                'delegationtoken': "Kafka delegation tokens are not a Unity Catalog concept.",
                'entity': "Apache Atlas entity governance does not map to Unity Catalog SQL.",
                'entity-type': "Apache Atlas entity types do not map to Unity Catalog SQL.",
                'entity-classification': "Atlas classifications differ from UC tags — manual mapping required.",
                'hiveservice': "Hive service-level admin has no direct Unity Catalog equivalent.",
            }
            reason_lines = [reasons.get(rt, f"'{rt}' has no Unity Catalog equivalent.") for rt in res_types]
            msg = (
                f"-- NOT TRANSLATABLE: Policy '{policy.name}' (id={policy.id})\n"
                + "\n".join(f"-- {r}" for r in reason_lines)
            )
            self.errors.append(f"Not translatable — '{policy.name}' (id={policy.id}): {'; '.join(reason_lines)}")
            return UCPolicy(
                policy_id=str(policy.id),
                policy_type="NOT_TRANSLATABLE",
                sql_statements=[utils.format_sql_statement(msg, policy_name=policy.name, policy_id=str(policy.id), policy_description=policy.description)],
                description=f"Cannot translate policy '{policy.name}' to Unity Catalog",
                resource=str(res_types),
                principals=[]
            )

        # Determine the correct Databricks SQL object-type keyword for this resource.
        # SCHEMA/CATALOG/FUNCTION already embed their keyword; plain 3-part paths are TABLE.
        is_table_level = not resource.startswith(('CATALOG ', 'SCHEMA ', 'FUNCTION ', 'EXTERNAL LOCATION '))
        if is_table_level:
            grant_resource = f"TABLE {resource}"
        else:
            grant_resource = resource

        def _remap_privilege(privilege: str, is_table: bool) -> str:
            """Remap privileges invalid at table level to their correct UC equivalent.

            In Databricks UC, CREATE is not a table-level privilege.
            GRANT CREATE TABLE must target a SCHEMA. We emit a SCHEMA-level
            grant with a comment rather than invalid GRANT CREATE ON TABLE.
            """
            if is_table and privilege == 'CREATE':
                return None  # handled separately below as schema-level CREATE TABLE
            return privilege

        def _schema_from_resource(resource_path: str) -> str:
            """Extract catalog.schema from a 3-part table path."""
            parts = resource_path.split('.')
            return '.'.join(parts[:2]) if len(parts) >= 2 else resource_path

        # Generate GRANT statements
        is_first_stmt = True
        for item in policy.policy_items:
            raw_privileges = [self.config.get_privilege_mapping(acc['type'])
                              for acc in item.accesses if acc.get('isAllowed', True)]

            privileges = [_remap_privilege(p, is_table_level) for p in raw_privileges]
            has_create = is_table_level and 'CREATE' in raw_privileges

            if not any(p for p in privileges if p) and not has_create:
                continue

            all_principals = (
                [('user', self.config.get_principal_mapping(u)) for u in item.users] +
                [('group', self.config.get_principal_mapping(g)) for g in item.groups] +
                [('role', self.config.get_principal_mapping(r)) for r in (item.roles or [])]
            )
            for ptype, pname in all_principals:
                principals.append(f"{ptype}:{pname}")

            for ptype, pname in all_principals:
                # Regular privileges (SELECT, MODIFY, etc.)
                for privilege in privileges:
                    if privilege is None:
                        continue
                    grant_sql = f"GRANT {privilege} ON {grant_resource} TO `{pname}`"
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

                # CREATE at table level → remap to CREATE TABLE on SCHEMA
                if has_create:
                    schema_path = _schema_from_resource(resource)
                    create_sql = (
                        f"-- NOTE: Ranger 'create' on a table maps to UC schema-level privilege.\n"
                        f"-- Granting CREATE TABLE on the parent schema instead.\n"
                        f"GRANT CREATE TABLE ON SCHEMA {schema_path} TO `{pname}`"
                    )
                    sql_statements.append(utils.format_sql_statement(create_sql))
        
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
        sql_keywords = {'AND', 'OR', 'NOT', 'NULL', 'TRUE', 'FALSE', 'IS', 'IN',
                        'LIKE', 'BETWEEN', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END'}

        for idx, item in enumerate(policy.row_filter_items):
            if not item.filter_expr:
                continue

            func_name = utils.generate_row_filter_function_name(table, policy.id, idx)
            qualified_func = f"{catalog}.{schema}.{func_name}"

            # Extract column names referenced in the filter expression for the function
            # signature and the ON (...) clause of ALTER TABLE SET ROW FILTER.
            import re as _re
            col_matches = _re.findall(
                r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|!=|<>|<=|>=|<|>|(?:\s+(?:IN|LIKE|IS)\s))',
                item.filter_expr, _re.IGNORECASE
            )
            filter_cols = [c for c in col_matches if c.upper() not in sql_keywords]
            # Remove duplicates while preserving order
            seen = set()
            filter_cols = [c for c in filter_cols if not (c in seen or seen.add(c))]

            if filter_cols:
                params = ', '.join(f"{col} STRING" for col in filter_cols)
                on_clause = ', '.join(filter_cols)
            else:
                params = ""
                on_clause = ""

            # Build CASE branches: each principal gets its own WHEN clause
            # restricting to the filter expression; everyone else sees all rows (ELSE TRUE).
            when_clauses = []
            for u in item.users:
                uc_u = self.config.get_principal_mapping(u)
                principals.append(f"user:{uc_u}")
                if item.filter_expr.strip():
                    when_clauses.append(
                        f"    WHEN current_user() = '{uc_u}'\n      THEN {item.filter_expr}"
                    )
            for g in item.groups:
                uc_g = self.config.get_principal_mapping(g)
                principals.append(f"group:{uc_g}")
                if item.filter_expr.strip():
                    when_clauses.append(
                        f"    WHEN is_account_group_member('{uc_g}')\n      THEN {item.filter_expr}"
                    )

            if when_clauses:
                case_body = "CASE\n" + "\n".join(when_clauses) + "\n    ELSE TRUE\n  END"
                filter_body = case_body
            elif item.filter_expr.strip():
                filter_body = item.filter_expr
            else:
                filter_body = "TRUE"

            create_filter = (
                f"CREATE OR REPLACE FUNCTION {qualified_func}({params})\n"
                f"RETURNS BOOLEAN\n"
                f"RETURN\n  {filter_body}"
            )

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

            # principals already appended inside when_clauses loop above
            apply_filter = (
                f"ALTER TABLE {resource}\n"
                f"SET ROW FILTER {qualified_func}\n"
                f"ON ({on_clause})"
            )
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
            # Collect masking rules: MASK_NONE means "pass-through" (see real value).
            # All other mask types become the ELSE branch (masked expression).
            passthrough_whens = []   # WHEN ... THEN column  (no masking)
            default_mask_type = None

            for item in policy.masking_items:
                mask_type = item.mask_type
                if mask_type == 'MASK_NONE':
                    for u in item.users:
                        uc_u = self.config.get_principal_mapping(u)
                        passthrough_whens.append(
                            f"    WHEN current_user() = '{uc_u}'\n      THEN {column}"
                        )
                    for g in item.groups:
                        uc_g = self.config.get_principal_mapping(g)
                        passthrough_whens.append(
                            f"    WHEN is_account_group_member('{uc_g}')\n      THEN {column}"
                        )
                else:
                    if not default_mask_type:
                        default_mask_type = mask_type
                    for u in item.users:
                        principals.append(f"user:{self.config.get_principal_mapping(u)}")
                    for g in item.groups:
                        principals.append(f"group:{self.config.get_principal_mapping(g)}")

            if not default_mask_type:
                default_mask_type = "MASK_REDACT"

            func_name = utils.generate_masking_function_name(table, column, default_mask_type)
            qualified_func = f"{catalog}.{schema}.{func_name}"
            mask_func = MASKING_FUNCTIONS.get(default_mask_type, MASKING_FUNCTIONS["MASK_REDACT"])
            masked_expr = mask_func.replace("{column}", column)

            # Use correct SQL data types for the function signature based on masking type.
            # e.g. MASK_DATE_SHOW_YEAR operates on DATE columns and returns DATE.
            type_meta = MASKING_FUNCTION_TYPES.get(
                default_mask_type, {"param_type": "STRING", "return_type": "STRING"}
            )
            param_type = type_meta["param_type"]
            return_type = type_meta["return_type"]

            # Build function body: CASE with passthrough WHENs then masked ELSE.
            # If no passthrough rules exist, skip the CASE and return the masked
            # expression directly (avoids invalid "CASE ELSE ... END" with no WHEN).
            if passthrough_whens:
                when_block = "\n".join(passthrough_whens)
                func_body = (
                    f"CASE\n{when_block}\n    ELSE {masked_expr}\n  END"
                )
            else:
                func_body = masked_expr

            create_func = (
                f"CREATE OR REPLACE FUNCTION {qualified_func}({column} {param_type})\n"
                f"RETURNS {return_type}\n"
                f"RETURN\n  {func_body}"
            )

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

            # Fully qualified function name required in ALTER TABLE
            apply_mask = (
                f"ALTER TABLE {resource}\n"
                f"ALTER COLUMN {column}\n"
                f"SET MASK {qualified_func}"
            )
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
            
            func_name = utils.generate_masking_function_name(table, column, default_mask_type)
            masked_expr = mask_func.replace("{column}", column)

            # Build WHEN clauses for MASK_NONE principals (see real value)
            passthrough_whens = []
            for u in mask_none_users:
                passthrough_whens.append(
                    f"    WHEN current_user() = '{u}'\n      THEN {column}"
                )
            for g in mask_none_groups:
                uc_g = self.config.get_principal_mapping(g)
                passthrough_whens.append(
                    f"    WHEN is_account_group_member('{uc_g}')\n      THEN {column}"
                )

            if passthrough_whens:
                when_block = "\n".join(passthrough_whens)
                func_body = f"CASE\n{when_block}\n    ELSE {masked_expr}\n  END"
            else:
                func_body = masked_expr

            qualified_func = f"{catalog}.{database}.{func_name}"
            type_meta = MASKING_FUNCTION_TYPES.get(
                default_mask_type, {"param_type": "STRING", "return_type": "STRING"}
            )
            create_func = (
                f"CREATE OR REPLACE FUNCTION {qualified_func}({column} {type_meta['param_type']})\n"
                f"RETURNS {type_meta['return_type']}\n"
                f"RETURN\n  {func_body}"
            )

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

            apply_mask = (
                f"ALTER TABLE {full_table}\n"
                f"ALTER COLUMN {column}\n"
                f"SET MASK {qualified_func}"
            )
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
