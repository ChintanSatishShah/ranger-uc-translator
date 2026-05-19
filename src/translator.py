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
    
    @staticmethod
    def _quote_id(name: str) -> str:
        """Backtick-quote a SQL identifier that contains hyphens or other special chars."""
        import re as _re
        if _re.search(r'[^a-zA-Z0-9_]', name):
            return f"`{name}`"
        return name

    def _build_resource_path(self, resources: Dict) -> Optional[str]:
        """Build UC resource path from Ranger resources."""
        # Tag-based policies are resolved by EnhancedPolicyTranslator via resource_tags
        tag_resource = resources.get('tag')
        if tag_resource and tag_resource.values:
            tag_names = '_'.join(tag_resource.values)
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
            return f"FUNCTION {catalog}.{self._quote_id(schema)}.{self._quote_id(udf)}"

        # Catalog-wide: database=* with no specific table
        if db_val == '*' and (not table_val or table_val == '*'):
            return f"CATALOG {catalog}"

        # Schema-level: database specified but no table (or table=*)
        if db_val and (not table_val or table_val == '*'):
            return f"SCHEMA {catalog}.{self._quote_id(db_val)}"

        # Table-level
        if table_val:
            schema = db_val or self.config.schema
            # Wildcard tables or HBase-style "NAMESPACE:table" patterns cannot be expressed
            # as a single UC table reference — fall back to schema-level grant.
            import re as _re
            if '*' in table_val or ':' in table_val or _re.search(r'[^a-zA-Z0-9_`\-]', table_val):
                return f"SCHEMA {catalog}.{self._quote_id(schema)}"
            return f"{catalog}.{self._quote_id(schema)}.{self._quote_id(table_val)}"

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
            """Remap privileges to valid UC equivalents.

            - CREATE at table level → None (handled separately as CREATE TABLE ON SCHEMA)
            - CREATE at schema level → CREATE TABLE (GRANT CREATE TABLE ON SCHEMA is the UC form)
            """
            if privilege == 'CREATE':
                if is_table:
                    return None  # emitted separately as GRANT CREATE TABLE ON SCHEMA
                return 'CREATE TABLE'  # GRANT CREATE TABLE ON SCHEMA is valid UC syntax
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

        # UC only supports ONE active row filter per table.
        # Merge all filter items into a single function with a CASE statement where
        # each WHEN branch handles a specific principal's filter expression.
        import re as _re
        sql_keywords = {'AND', 'OR', 'NOT', 'NULL', 'TRUE', 'FALSE', 'IS', 'IN',
                        'LIKE', 'BETWEEN', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
                        'CURRENT_DATE', 'CURRENT_TIMESTAMP', 'CURRENT_USER'}

        # Collect all WHEN clauses and all referenced columns across every item
        all_when_clauses = []
        all_filter_cols_ordered = []
        seen_cols: set = set()

        for item in policy.row_filter_items:
            if not item.filter_expr:
                continue
            col_matches = _re.findall(
                r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|!=|<>|<=|>=|<|>|(?:\s+(?:IN|LIKE|IS)\s))',
                item.filter_expr, _re.IGNORECASE
            )
            for c in col_matches:
                if c.upper() not in sql_keywords and c not in seen_cols:
                    seen_cols.add(c)
                    all_filter_cols_ordered.append(c)

            for u in item.users:
                uc_u = self.config.get_principal_mapping(u)
                principals.append(f"user:{uc_u}")
                all_when_clauses.append(
                    f"    WHEN current_user() = '{uc_u}'\n      THEN {item.filter_expr}"
                )
            for g in item.groups:
                uc_g = self.config.get_principal_mapping(g)
                principals.append(f"group:{uc_g}")
                all_when_clauses.append(
                    f"    WHEN is_account_group_member('{uc_g}')\n      THEN {item.filter_expr}"
                )

        if not all_when_clauses and not policy.row_filter_items:
            return None

        # Single function name for the whole policy (not per-item)
        func_name = utils.generate_row_filter_function_name(table, policy.id, 0)
        qualified_func = f"{catalog}.{schema}.{func_name}"

        params = ', '.join(f"{c} STRING" for c in all_filter_cols_ordered)
        on_clause = ', '.join(all_filter_cols_ordered)

        if all_when_clauses:
            filter_body = "CASE\n" + "\n".join(all_when_clauses) + "\n    ELSE TRUE\n  END"
        elif policy.row_filter_items and policy.row_filter_items[0].filter_expr:
            filter_body = policy.row_filter_items[0].filter_expr
        else:
            filter_body = "TRUE"

        create_filter = (
            f"CREATE OR REPLACE FUNCTION {qualified_func}({params})\n"
            f"RETURNS BOOLEAN\n"
            f"RETURN\n  {filter_body}"
        )
        sql_statements.append(utils.format_sql_statement(
            create_filter,
            policy_name=policy.name,
            policy_id=str(policy.id),
            policy_description=policy.description
        ))

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
    
    def generate_tag_sql(self) -> List[str]:
        """Generate ALTER TABLE SET TAGS statements from resource_tags + tag_definitions.

        Each Ranger resource tag becomes a UC tag key='true' pair.
        Tag definition attributes are included as additional key-value pairs.
        Column-level tags use ALTER TABLE ... ALTER COLUMN ... SET TAGS.
        Table-level tags use ALTER TABLE ... SET TAGS.

        When no resource_tags are available for a given tag, a placeholder
        statement is emitted so the operator knows a tag needs to be applied.
        """
        sql_statements = []
        catalog = self.config.catalog

        # ── Partition resource_tags by table vs column paths ────────────────────
        table_level: dict = {}   # "schema.table" → [tag, ...]
        column_level: dict = {}  # "schema.table" → {"col" → [tag, ...]}

        for resource_path, tags in self.resource_tags.items():
            parts = resource_path.split('.')
            if len(parts) == 2:
                table_level.setdefault(resource_path, []).extend(tags)
            elif len(parts) == 3:
                schema, table, column = parts
                tkey = f"{schema}.{table}"
                column_level.setdefault(tkey, {}).setdefault(column, []).extend(tags)

        def _tag_pairs(tag_names: list) -> str:
            """Build the 'key' = 'value' CSV for SET TAGS."""
            pairs = []
            seen_keys: set = set()
            for tname in tag_names:
                key = tname.lower()
                if key not in seen_keys:
                    seen_keys.add(key)
                    pairs.append(f"'{key}' = 'true'")
                # Include tag definition attributes (e.g. level, category)
                tdef = self.tag_definitions.get(tname, {})
                attrs = tdef.get('attributeDefs', {}) if isinstance(tdef, dict) else {}
                for attr_k, attr_v in attrs.items():
                    akey = attr_k.lower()
                    if akey not in seen_keys:
                        seen_keys.add(akey)
                        pairs.append(f"'{akey}' = '{attr_v}'")
            return ', '.join(pairs)

        def _uc_table(schema: str, table: str) -> str:
            return f"{catalog}.{self._quote_id(schema)}.{self._quote_id(table)}"

        header_done = False

        def _append_tagged(sql: str, *, first: bool = False) -> None:
            nonlocal header_done
            if first or not header_done:
                sql_statements.append(utils.format_sql_statement(
                    sql,
                    policy_name="Tag Propagation",
                    policy_description=(
                        "Apply Unity Catalog tags to tables/columns based on "
                        "Ranger resourceTags metadata. Run this before access grants."
                    )
                ))
                header_done = True
            else:
                sql_statements.append(utils.format_sql_statement(sql))

        # ── Table-level tags ────────────────────────────────────────────────────
        for tkey in sorted(table_level):
            parts = tkey.split('.')
            schema, table = parts[0], parts[1]
            pairs = _tag_pairs(table_level[tkey])
            _append_tagged(f"ALTER TABLE {_uc_table(schema, table)} SET TAGS ({pairs})",
                           first=not header_done)

        # ── Column-level tags ───────────────────────────────────────────────────
        for tkey in sorted(column_level):
            parts = tkey.split('.')
            schema, table = parts[0], parts[1]
            for col in sorted(column_level[tkey]):
                pairs = _tag_pairs(column_level[tkey][col])
                _append_tagged(
                    f"ALTER TABLE {_uc_table(schema, table)} "
                    f"ALTER COLUMN {col} SET TAGS ({pairs})"
                )

        # ── Fallback: tag definitions with no matching resourceTags ─────────────
        # Emit a placeholder statement so the operator knows these tags exist.
        all_resource_tags_flat = set()
        for tags in self.resource_tags.values():
            all_resource_tags_flat.update(tags)
        for tname in sorted(self.tag_definitions):
            if tname not in all_resource_tags_flat:
                pairs = _tag_pairs([tname])
                _append_tagged(
                    f"-- TODO: No resourceTags found for tag '{tname}'.\n"
                    f"-- Apply this tag to the relevant table(s)/column(s):\n"
                    f"ALTER TABLE {catalog}.{self.config.schema}.<table_name> "
                    f"SET TAGS ({pairs})"
                )

        return sql_statements

    def _get_tagged_column_infos(self, tag_name: str) -> List[Dict]:
        """Return [{database, table, column}] for every resource_tags entry carrying tag_name."""
        result = []
        for resource_path, tags in self.resource_tags.items():
            if tag_name not in tags:
                continue
            parts = resource_path.split('.')
            if len(parts) == 3:
                database, table, column = parts
            elif len(parts) == 2:
                table, column = parts
                database = self.config.schema
            else:
                continue
            if column != '*':
                result.append({'database': database, 'table': table, 'column': column})
        return result


    def _get_tagged_tables(self, policy_tags: set) -> dict:
        """Return {schema.table -> set(matching_tags)} for all resources whose tags
        intersect with policy_tags.  Handles both schema.table and schema.table.column paths."""
        tagged_tables = {}
        for resource_path, tags in self.resource_tags.items():
            matching = set(tags) & policy_tags
            if not matching:
                continue
            parts = resource_path.split('.')
            table_key = '.'.join(parts[:2]) if len(parts) >= 2 else resource_path
            tagged_tables.setdefault(table_key, set()).update(matching)
        return tagged_tables

    def translate(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate a single Ranger policy to UC format."""
        tag_resource = policy.resources.get('tag')
        if tag_resource and tag_resource.values:
            # Tag-based policy — dispatch by primary type, then emit supplemental items
            if policy.policy_type == PolicyType.COLUMN_MASK:
                return self._translate_tag_based_column_mask(policy)
            # ACCESS (and ROW_FILTER declared as access) → real table grants
            return self._translate_tag_based_access(policy)

        return super().translate(policy)

    def _translate_tag_based_access(self, policy: RangerPolicy) -> Optional[UCPolicy]:
        """Translate a tag-based ACCESS policy into GRANT statements.

        Looks up resource_tags to resolve actual table paths for every tag in the policy.
        Falls back to a placeholder comment when no tag metadata is available.
        Also emits supplemental row-filter functions and masking functions if the same
        policy carries rowFilterPolicyItems / dataMaskPolicyItems for other principals.
        """
        tag_resource = policy.resources.get('tag')
        policy_tags = set(tag_resource.values)
        catalog = self.config.catalog

        tagged_tables = self._get_tagged_tables(policy_tags)
        sql_statements = []
        principals = []
        is_first = True

        # ── Helper to append a formatted statement ─────────────────────────────
        def _append(sql, *, with_header=False):
            nonlocal is_first
            if with_header or is_first:
                sql_statements.append(utils.format_sql_statement(
                    sql,
                    policy_name=policy.name,
                    policy_id=str(policy.id),
                    policy_description=policy.description
                ))
                is_first = False
            else:
                sql_statements.append(utils.format_sql_statement(sql))

        # ── ACCESS grants ───────────────────────────────────────────────────────
        if policy.policy_items:
            if tagged_tables:
                for table_key in sorted(tagged_tables):
                    parts = table_key.split('.')
                    schema, table = parts[0], parts[1]
                    uc_table = f"{catalog}.{self._quote_id(schema)}.{self._quote_id(table)}"
                    is_table_level = True

                    for item in policy.policy_items:
                        raw_privs = [self.config.get_privilege_mapping(a['type'])
                                     for a in item.accesses if a.get('isAllowed', True)]
                        if not raw_privs:
                            continue
                        all_p = (
                            [('user', self.config.get_principal_mapping(u)) for u in item.users] +
                            [('group', self.config.get_principal_mapping(g)) for g in item.groups] +
                            [('role', self.config.get_principal_mapping(r)) for r in (item.roles or [])]
                        )
                        for ptype, pname in all_p:
                            principals.append(f"{ptype}:{pname}")
                        for _, pname in all_p:
                            for priv in raw_privs:
                                if is_table_level and priv == 'CREATE':
                                    _append(
                                        f"-- NOTE: Ranger 'create' maps to schema-level privilege.\n"
                                        f"GRANT CREATE TABLE ON SCHEMA {catalog}.{schema} TO `{pname}`"
                                    )
                                else:
                                    _append(f"GRANT {priv} ON TABLE {uc_table} TO `{pname}`")
            else:
                # No tag metadata — emit placeholder GRANTs with a clear note
                tag_list = '_'.join(sorted(policy_tags))
                placeholder = f"{catalog}.{self.config.schema}.<table_with_{tag_list}>"
                note = (
                    f"-- NOTE: No resourceTags metadata found for tag(s): {', '.join(sorted(policy_tags))}.\n"
                    f"-- Replace the placeholder with the actual table(s) that carry these tags."
                )
                for item in policy.policy_items:
                    raw_privs = [self.config.get_privilege_mapping(a['type'])
                                 for a in item.accesses if a.get('isAllowed', True)]
                    all_p = (
                        [('user', self.config.get_principal_mapping(u)) for u in item.users] +
                        [('group', self.config.get_principal_mapping(g)) for g in item.groups] +
                        [('role', self.config.get_principal_mapping(r)) for r in (item.roles or [])]
                    )
                    for ptype, pname in all_p:
                        principals.append(f"{ptype}:{pname}")
                    for _, pname in all_p:
                        for priv in raw_privs:
                            if priv == 'CREATE':
                                schema_path = f"{catalog}.{self.config.schema}"
                                _append(
                                    f"-- NOTE: Ranger 'create' maps to schema-level privilege.\n"
                                    f"GRANT CREATE TABLE ON SCHEMA {schema_path} TO `{pname}`"
                                )
                            else:
                                _append(f"{note}\nGRANT {priv} ON TABLE {placeholder} TO `{pname}`")

        # ── Deny policy items (UC has no SQL DENY — document as comment) ────────
        if policy.deny_policy_items:
            deny_lines = [
                "-- DENY POLICY (not directly expressible in Databricks UC SQL):",
                "-- The following principals were DENIED access in Ranger.",
                "-- Implement via UC row/column filters or explicit permission exclusion.",
            ]
            for item in policy.deny_policy_items:
                for u in item.users:
                    deny_lines.append(f"--   DENY user: {u}")
                for g in item.groups:
                    deny_lines.append(f"--   DENY group: {g}")
            _append('\n'.join(deny_lines))

        # ── Supplemental row-filter items (e.g. from a mixed tag policy) ────────
        if policy.row_filter_items and tagged_tables:
            import re as _re
            sql_keywords = {'AND', 'OR', 'NOT', 'NULL', 'TRUE', 'FALSE', 'IS', 'IN',
                            'LIKE', 'BETWEEN', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END'}
            for table_key in sorted(tagged_tables):
                parts = table_key.split('.')
                schema, table = parts[0], parts[1]
                uc_table = f"{catalog}.{self._quote_id(schema)}.{self._quote_id(table)}"
                for idx, item in enumerate(policy.row_filter_items):
                    if not item.filter_expr:
                        continue
                    func_name = utils.generate_row_filter_function_name(table, policy.id, idx)
                    qualified_func = f"{catalog}.{schema}.{func_name}"
                    col_matches = _re.findall(
                        r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|!=|<>|<=|>=|<|>|(?:\s+(?:IN|LIKE|IS)\s))',
                        item.filter_expr, _re.IGNORECASE
                    )
                    filter_cols = list(dict.fromkeys(
                        c for c in col_matches if c.upper() not in sql_keywords
                    ))
                    params = ', '.join(f"{c} STRING" for c in filter_cols) if filter_cols else ""
                    on_clause = ', '.join(filter_cols)
                    when_clauses = []
                    for u in item.users:
                        uc_u = self.config.get_principal_mapping(u)
                        principals.append(f"user:{uc_u}")
                        when_clauses.append(
                            f"    WHEN current_user() = '{uc_u}'\n      THEN {item.filter_expr}"
                        )
                    for g in item.groups:
                        uc_g = self.config.get_principal_mapping(g)
                        principals.append(f"group:{uc_g}")
                        when_clauses.append(
                            f"    WHEN is_account_group_member('{uc_g}')\n      THEN {item.filter_expr}"
                        )
                    if when_clauses:
                        body = "CASE\n" + "\n".join(when_clauses) + "\n    ELSE TRUE\n  END"
                    else:
                        body = item.filter_expr or "TRUE"
                    _append(
                        f"CREATE OR REPLACE FUNCTION {qualified_func}({params})\n"
                        f"RETURNS BOOLEAN\n"
                        f"RETURN\n  {body}"
                    )
                    _append(
                        f"ALTER TABLE {uc_table}\n"
                        f"SET ROW FILTER {qualified_func}\n"
                        f"ON ({on_clause})"
                    )

        # ── Supplemental masking items ───────────────────────────────────────────
        if policy.masking_items and tagged_tables:
            for table_key in sorted(tagged_tables):
                parts = table_key.split('.')
                schema, table = parts[0], parts[1]
                uc_table = f"{catalog}.{self._quote_id(schema)}.{self._quote_id(table)}"
                # Collect unique column names tagged under this table from resource_tags
                tagged_columns_for_table = []
                for rpath, rtags in self.resource_tags.items():
                    rparts = rpath.split('.')
                    if (len(rparts) == 3 and
                            rparts[0] == schema and rparts[1] == table and
                            set(rtags) & policy_tags):
                        col = rparts[2]
                        if col not in tagged_columns_for_table:
                            tagged_columns_for_table.append(col)
                if not tagged_columns_for_table:
                    tagged_columns_for_table = ['<column>']

                default_mask_type = next(
                    (it.mask_type for it in policy.masking_items if it.mask_type != 'MASK_NONE'),
                    'MASK_REDACT'
                )
                mask_func = MASKING_FUNCTIONS.get(default_mask_type, MASKING_FUNCTIONS['MASK_REDACT'])
                type_meta = MASKING_FUNCTION_TYPES.get(
                    default_mask_type, {"param_type": "STRING", "return_type": "STRING"}
                )
                passthrough_whens = []
                for item in policy.masking_items:
                    if item.mask_type == 'MASK_NONE':
                        for u in item.users:
                            uc_u = self.config.get_principal_mapping(u)
                            passthrough_whens.append(
                                f"    WHEN current_user() = '{uc_u}'\n      THEN {{col}}"
                            )
                        for g in item.groups:
                            uc_g = self.config.get_principal_mapping(g)
                            passthrough_whens.append(
                                f"    WHEN is_account_group_member('{uc_g}')\n      THEN {{col}}"
                            )
                    else:
                        for u in item.users:
                            principals.append(f"user:{self.config.get_principal_mapping(u)}")
                        for g in item.groups:
                            principals.append(f"group:{self.config.get_principal_mapping(g)}")

                for col in tagged_columns_for_table:
                    masked_expr = mask_func.replace('{column}', col)
                    whens = [w.replace('{col}', col) for w in passthrough_whens]
                    if whens:
                        func_body = "CASE\n" + "\n".join(whens) + f"\n    ELSE {masked_expr}\n  END"
                    else:
                        func_body = masked_expr
                    func_name = utils.generate_masking_function_name(table, col, default_mask_type)
                    qualified_func = f"{catalog}.{schema}.{func_name}"
                    _append(
                        f"CREATE OR REPLACE FUNCTION {qualified_func}({col} {type_meta['param_type']})\n"
                        f"RETURNS {type_meta['return_type']}\n"
                        f"RETURN\n  {func_body}"
                    )
                    _append(
                        f"ALTER TABLE {uc_table}\n"
                        f"ALTER COLUMN {col}\n"
                        f"SET MASK {qualified_func}"
                    )

        if not sql_statements:
            return None

        return UCPolicy(
            policy_id=str(policy.id),
            policy_type="ACCESS_TAG",
            sql_statements=sql_statements,
            description=policy.description or f"Tag-based access for: {', '.join(sorted(policy_tags))}",
            resource=f"TAG {', '.join(sorted(policy_tags))}",
            principals=list(dict.fromkeys(principals))
        )
    
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
        tagged_columns = self._get_tagged_column_infos(tag_name)
        
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
