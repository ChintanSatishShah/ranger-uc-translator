"""
Validation module for Ranger policies and Unity Catalog SQL statements.
Provides input validation, SQL validation, and error reporting.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

@dataclass
class ValidationResult:
    """Result of validation check."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def add_error(self, error: str):
        """Add validation error."""
        self.is_valid = False
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        """Add validation warning."""
        self.warnings.append(warning)

class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"  # Fail on any error or warning
    NORMAL = "normal"  # Fail on errors only
    PERMISSIVE = "permissive"  # Allow all, just log

class RangerPolicyValidator:
    """Validator for Ranger policy JSON structures."""
    
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        self.level = level
    
    def validate_policy_json(self, policy_data: Dict[str, Any]) -> ValidationResult:
        """Validate a single Ranger policy JSON structure."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Required fields check
        required_fields = ['id', 'name', 'service', 'resources']
        for field in required_fields:
            if field not in policy_data:
                result.add_error(f"Missing required field: {field}")
        
        # ID validation
        if 'id' in policy_data:
            if not isinstance(policy_data['id'], int):
                result.add_error(f"Policy ID must be integer, got {type(policy_data['id'])}")
        
        # Name validation
        if 'name' in policy_data:
            if not policy_data['name'] or not isinstance(policy_data['name'], str):
                result.add_error("Policy name must be non-empty string")
        
        # Resources validation
        if 'resources' in policy_data:
            resources_result = self._validate_resources(policy_data['resources'])
            result.errors.extend(resources_result.errors)
            result.warnings.extend(resources_result.warnings)
            if not resources_result.is_valid:
                result.is_valid = False
        
        # Policy items validation
        if 'policyItems' in policy_data:
            items_result = self._validate_policy_items(policy_data['policyItems'])
            result.errors.extend(items_result.errors)
            result.warnings.extend(items_result.warnings)
            if not items_result.is_valid:
                result.is_valid = False
        
        # Row filter validation
        if 'rowFilterPolicyItems' in policy_data:
            rf_result = self._validate_row_filter_items(policy_data['rowFilterPolicyItems'])
            result.errors.extend(rf_result.errors)
            result.warnings.extend(rf_result.warnings)
            if not rf_result.is_valid:
                result.is_valid = False
        
        # Masking validation
        if 'dataMaskPolicyItems' in policy_data:
            mask_result = self._validate_masking_items(policy_data['dataMaskPolicyItems'])
            result.errors.extend(mask_result.errors)
            result.warnings.extend(mask_result.warnings)
            if not mask_result.is_valid:
                result.is_valid = False
        
        # At least one policy item type should exist
        has_items = any(k in policy_data for k in ['policyItems', 'rowFilterPolicyItems', 'dataMaskPolicyItems'])
        if not has_items:
            result.add_warning("Policy has no policy items (no permissions defined)")
        
        return result
    
    def _validate_resources(self, resources: Dict[str, Any]) -> ValidationResult:
        """Validate resources section."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not resources:
            result.add_error("Resources section is empty")
            return result
        
        for res_name, res_data in resources.items():
            if not isinstance(res_data, dict):
                result.add_error(f"Resource '{res_name}' must be a dictionary")
                continue
            
            # Check for values
            if 'values' not in res_data:
                result.add_error(f"Resource '{res_name}' missing 'values' field")
            elif not isinstance(res_data['values'], list):
                result.add_error(f"Resource '{res_name}' values must be a list")
            elif len(res_data['values']) == 0:
                result.add_warning(f"Resource '{res_name}' has empty values list")
        
        return result
    
    def _validate_policy_items(self, items: List[Dict]) -> ValidationResult:
        """Validate policy items (ACL)."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not isinstance(items, list):
            result.add_error("policyItems must be a list")
            return result
        
        for idx, item in enumerate(items):
            # Check for users or groups
            has_principals = ('users' in item and item['users']) or ('groups' in item and item['groups'])
            if not has_principals:
                result.add_warning(f"Policy item {idx} has no users or groups")
            
            # Check for accesses
            if 'accesses' not in item:
                result.add_error(f"Policy item {idx} missing 'accesses' field")
            elif not isinstance(item['accesses'], list):
                result.add_error(f"Policy item {idx} accesses must be a list")
            elif len(item['accesses']) == 0:
                result.add_error(f"Policy item {idx} has empty accesses list")
            else:
                # Validate each access
                for access in item['accesses']:
                    if 'type' not in access:
                        result.add_error(f"Policy item {idx} access missing 'type'")
        
        return result
    
    def _validate_row_filter_items(self, items: List[Dict]) -> ValidationResult:
        """Validate row filter policy items."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not isinstance(items, list):
            result.add_error("rowFilterPolicyItems must be a list")
            return result
        
        for idx, item in enumerate(items):
            # Check for users or groups
            has_principals = ('users' in item and item['users']) or ('groups' in item and item['groups'])
            if not has_principals:
                result.add_warning(f"Row filter item {idx} has no users or groups")
            
            # Check for filter expression
            if 'rowFilterInfo' not in item:
                result.add_error(f"Row filter item {idx} missing 'rowFilterInfo'")
            elif 'filterExpr' not in item['rowFilterInfo']:
                result.add_error(f"Row filter item {idx} missing filter expression")
            elif not item['rowFilterInfo']['filterExpr']:
                result.add_error(f"Row filter item {idx} has empty filter expression")
        
        return result
    
    def _validate_masking_items(self, items: List[Dict]) -> ValidationResult:
        """Validate masking policy items."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not isinstance(items, list):
            result.add_error("dataMaskPolicyItems must be a list")
            return result
        
        valid_mask_types = ['MASK', 'MASK_SHOW_LAST_4', 'MASK_SHOW_FIRST_4', 'MASK_HASH', 
                           'MASK_NULL', 'MASK_DATE_SHOW_YEAR', 'CUSTOM']
        
        for idx, item in enumerate(items):
            # Check for users or groups
            has_principals = ('users' in item and item['users']) or ('groups' in item and item['groups'])
            if not has_principals:
                result.add_warning(f"Masking item {idx} has no users or groups")
            
            # Check for mask info
            if 'dataMaskInfo' not in item:
                result.add_error(f"Masking item {idx} missing 'dataMaskInfo'")
            elif 'dataMaskType' not in item['dataMaskInfo']:
                result.add_error(f"Masking item {idx} missing mask type")
            else:
                mask_type = item['dataMaskInfo']['dataMaskType']
                if mask_type not in valid_mask_types:
                    result.add_warning(f"Masking item {idx} has unknown mask type: {mask_type}")
        
        return result

class UCSQLValidator:
    """Validator for Unity Catalog SQL statements."""
    
    def __init__(self):
        self.valid_privileges = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 
                                'DROP', 'USAGE', 'EXECUTE', 'MODIFY', 'ALL PRIVILEGES']
    
    def validate_sql_statement(self, sql: str) -> ValidationResult:
        """Validate a Unity Catalog SQL statement."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not sql or not sql.strip():
            result.add_error("SQL statement is empty")
            return result
        
        sql_upper = sql.strip().upper()
        
        # Check statement type
        if sql_upper.startswith('GRANT'):
            self._validate_grant_statement(sql, result)
        elif sql_upper.startswith('CREATE OR REPLACE FUNCTION'):
            self._validate_function_statement(sql, result)
        elif sql_upper.startswith('ALTER TABLE'):
            self._validate_alter_statement(sql, result)
        elif sql_upper.startswith('CREATE TAG'):
            self._validate_tag_statement(sql, result)
        else:
            result.add_warning(f"Unknown SQL statement type: {sql[:30]}...")
        
        return result
    
    def _validate_grant_statement(self, sql: str, result: ValidationResult):
        """Validate GRANT statement."""
        # Check for TO clause
        if ' TO ' not in sql.upper():
            result.add_error("GRANT statement missing TO clause")
        
        # Check for ON clause
        if ' ON ' not in sql.upper():
            result.add_error("GRANT statement missing ON clause")
        
        # Check privilege is valid
        privilege_part = sql.upper().split('GRANT')[1].split('ON')[0].strip()
        if privilege_part not in self.valid_privileges:
            result.add_warning(f"Potentially invalid privilege: {privilege_part}")
    
    def _validate_function_statement(self, sql: str, result: ValidationResult):
        """Validate function creation statement."""
        # Check for RETURN clause
        if 'RETURN' not in sql.upper():
            result.add_error("Function missing RETURN clause")
        
        # Check for proper naming
        if '.' not in sql:
            result.add_warning("Function should use fully qualified name (catalog.schema.function)")
    
    def _validate_alter_statement(self, sql: str, result: ValidationResult):
        """Validate ALTER TABLE statement."""
        sql_upper = sql.upper()
        
        # Check for proper ALTER types
        valid_alter_ops = ['SET ROW FILTER', 'ALTER COLUMN', 'SET MASK', 'SET TAGS']
        has_valid_op = any(op in sql_upper for op in valid_alter_ops)
        
        if not has_valid_op:
            result.add_warning("ALTER statement has unknown operation type")
    
    def _validate_tag_statement(self, sql: str, result: ValidationResult):
        """Validate tag creation statement."""
        if 'IF NOT EXISTS' not in sql.upper():
            result.add_warning("CREATE TAG should use IF NOT EXISTS for idempotency")

def generate_validation_report(policy_results: Dict[str, ValidationResult]) -> str:
    """Generate formatted validation report."""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("VALIDATION REPORT")
    report_lines.append("=" * 80)
    
    total = len(policy_results)
    valid = sum(1 for r in policy_results.values() if r.is_valid)
    total_errors = sum(len(r.errors) for r in policy_results.values())
    total_warnings = sum(len(r.warnings) for r in policy_results.values())
    
    report_lines.append(f"\nTotal Policies: {total}")
    report_lines.append(f"Valid: {valid} ({valid/total*100:.1f}%)")
    report_lines.append(f"Invalid: {total - valid} ({(total-valid)/total*100:.1f}%)")
    report_lines.append(f"Total Errors: {total_errors}")
    report_lines.append(f"Total Warnings: {total_warnings}")
    
    # Details for invalid policies
    if total - valid > 0:
        report_lines.append(f"\n{'-' * 80}")
        report_lines.append("INVALID POLICIES DETAILS:")
        report_lines.append('-' * 80)
        
        for policy_name, result in policy_results.items():
            if not result.is_valid:
                report_lines.append(f"\n{policy_name}:")
                for error in result.errors:
                    report_lines.append(f"  ❌ {error}")
                for warning in result.warnings:
                    report_lines.append(f"  ⚠️  {warning}")
    
    report_lines.append("\n" + "=" * 80)
    return "\n".join(report_lines)
