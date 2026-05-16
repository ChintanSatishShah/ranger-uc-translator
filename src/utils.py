"""
Utility functions for Ranger to Unity Catalog policy translation.
"""

import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd

def sanitize_identifier(name: str) -> str:
    """Sanitize SQL identifier by escaping special characters."""
    # If identifier contains special chars, wrap in backticks
    if re.search(r'[^a-zA-Z0-9_]', name) or name[0].isdigit():
        return f"`{name}`"
    return name

def parse_resource_path(path: str) -> Dict[str, Optional[str]]:
    """Parse Ranger resource path into catalog, schema, table components."""
    parts = path.strip('/').split('/')
    result = {"catalog": None, "schema": None, "table": None, "column": None}
    
    if len(parts) >= 1:
        result["catalog"] = parts[0]
    if len(parts) >= 2:
        result["schema"] = parts[1]
    if len(parts) >= 3:
        result["table"] = parts[2]
    if len(parts) >= 4:
        result["column"] = parts[3]
    
    return result

def build_uc_resource_path(catalog: Optional[str], schema: Optional[str], 
                          table: Optional[str], column: Optional[str] = None) -> str:
    """Build Unity Catalog resource path."""
    parts = []
    if catalog:
        parts.append(sanitize_identifier(catalog))
    if schema:
        parts.append(sanitize_identifier(schema))
    if table:
        parts.append(sanitize_identifier(table))
    
    path = ".".join(parts)
    
    if column:
        path = f"{path}({sanitize_identifier(column)})"
    
    return path

def extract_principals(policy_item: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract users and groups from Ranger policy item."""
    principals = []
    
    # Extract users
    for user in policy_item.get('users', []):
        principals.append({"type": "user", "name": user})
    
    # Extract groups
    for group in policy_item.get('groups', []):
        principals.append({"type": "group", "name": group})
    
    return principals

def format_sql_statement(sql: str, policy_name: Optional[str] = None, 
                        policy_id: Optional[str] = None, 
                        policy_description: Optional[str] = None) -> str:
    """
    Format SQL statement for readability with optional policy metadata.
    
    Args:
        sql: The SQL statement to format
        policy_name: Optional Ranger policy name
        policy_id: Optional Ranger policy ID  
        policy_description: Optional policy description
        
    Returns:
        Formatted SQL with metadata comments
    """
    # Build header comment with policy metadata
    header_lines = []
    if policy_name or policy_id:
        header_lines.append("-- " + "=" * 78)
        if policy_name:
            header_lines.append(f"-- Ranger Policy: {policy_name}")
        if policy_id:
            header_lines.append(f"-- Policy ID: {policy_id}")
        if policy_description:
            # Wrap long descriptions
            desc_lines = [policy_description[i:i+70] for i in range(0, len(policy_description), 70)]
            header_lines.append(f"-- Description: {desc_lines[0]}")
            for line in desc_lines[1:]:
                header_lines.append(f"--              {line}")
        header_lines.append("-- " + "=" * 78)
    
    # Format the SQL statement
    sql = sql.strip()
    
    # Remove excessive whitespace
    sql = re.sub(r'\s+', ' ', sql)
    
    # Add proper line breaks for readability
    # Break before major keywords
    sql = re.sub(r'\s+(FROM|WHERE|AND|OR|GROUP BY|ORDER BY|HAVING|LIMIT)\s+', r'\n  \1 ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\s+(INNER|LEFT|RIGHT|FULL|CROSS)\s+JOIN\s+', r'\n  \1 JOIN ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\s+(ON|TO|SET)\s+', r'\n  \1 ', sql, flags=re.IGNORECASE)
    
    # Ensure semicolon at end
    if not sql.strip().endswith(';'):
        sql = sql.strip() + ';'
    
    # Combine header and SQL
    if header_lines:
        return '\n'.join(header_lines) + '\n' + sql
    else:
        return sql

def create_audit_record(policy_id: str, policy_type: str, status: str, 
                       message: str, sql_statements: Optional[List[str]] = None) -> Dict[str, Any]:
    """Create audit record for logging."""
    return {
        "timestamp": datetime.now().isoformat(),
        "policy_id": policy_id,
        "policy_type": policy_type,
        "status": status,
        "message": message,
        "sql_statements": sql_statements or [],
        "statement_count": len(sql_statements) if sql_statements else 0
    }

def validate_uc_identifier(identifier: str) -> bool:
    """Validate Unity Catalog identifier format."""
    # Check for catalog.schema.table format
    parts = identifier.split('.')
    if len(parts) < 2 or len(parts) > 3:
        return False
    
    # Check each part is valid
    for part in parts:
        # Remove backticks if present
        clean_part = part.strip('`')
        if not clean_part or not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', clean_part):
            if not (part.startswith('`') and part.endswith('`')):
                return False
    
    return True

def extract_table_from_filter(filter_expr: str) -> Optional[str]:
    """Extract table reference from row filter expression."""
    # Look for {table} or {TABLE} placeholder
    match = re.search(r'\{table\}|\{TABLE\}', filter_expr, re.IGNORECASE)
    if match:
        return match.group(0)
    return None

def parse_condition_to_sql(condition: Dict[str, Any]) -> str:
    """Convert Ranger condition to SQL WHERE clause."""
    # This is a simplified parser - extend based on actual Ranger condition format
    if 'type' in condition and condition['type'] == 'expression':
        return condition.get('values', ['TRUE'])[0]
    
    # Handle simple key-value conditions
    conditions = []
    for key, values in condition.items():
        if isinstance(values, list) and values:
            if len(values) == 1:
                conditions.append(f"{key} = '{values[0]}'")
            else:
                values_str = ", ".join([f"'{v}'" for v in values])
                conditions.append(f"{key} IN ({values_str})")
    
    return " AND ".join(conditions) if conditions else "TRUE"

def generate_masking_function_name(table: str, column: str, mask_type: str) -> str:
    """Generate consistent naming for masking functions."""
    # Remove special chars and create valid function name
    clean_table = re.sub(r'[^a-zA-Z0-9_]', '_', table)
    clean_column = re.sub(r'[^a-zA-Z0-9_]', '_', column)
    clean_mask = re.sub(r'[^a-zA-Z0-9_]', '_', mask_type.lower())
    
    return f"mask_{clean_table}_{clean_column}_{clean_mask}"

def generate_row_filter_function_name(table: str, policy_id, item_idx) -> str:
    """Generate consistent naming for row filter functions."""
    # Convert all inputs to strings FIRST
    table_str = str(table)
    policy_id_str = str(policy_id)
    item_idx_str = str(item_idx)
    
    # Then sanitize to create valid function name
    clean_table = re.sub(r'[^a-zA-Z0-9_]', '_', table_str)
    clean_policy = re.sub(r'[^a-zA-Z0-9_]', '_', policy_id_str)
    clean_idx = re.sub(r'[^a-zA-Z0-9_]', '_', item_idx_str)
    
    return f"rf_{clean_table}_{clean_policy}_{clean_idx}"

def safe_json_loads(json_str: str) -> Optional[Dict]:
    """Safely load JSON string with error handling."""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None

def dataframe_to_markdown(df: pd.DataFrame, max_rows: int = 50) -> str:
    """Convert DataFrame to markdown table for display."""
    if len(df) > max_rows:
        df = df.head(max_rows)
        truncated = True
    else:
        truncated = False
    
    md = df.to_markdown(index=False)
    
    if truncated:
        md += f"\n\n*Showing first {max_rows} of {len(df)} rows*"
    
    return md
