"""
Parser module for Ranger policy JSON files.
Handles parsing and validation of Ranger policies, service definitions, and resource tags.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class PolicyType(Enum):
    """Ranger policy types."""
    ACCESS = "access"
    ROW_FILTER = "rowFilter"
    COLUMN_MASK = "columnMask"
    TAG = "tag"

@dataclass
class RangerResource:
    """Represents a Ranger resource (database, table, column, etc.)."""
    type: str  # database, table, column, udf
    values: List[str]
    is_excludes: bool = False
    is_recursive: bool = False

@dataclass
class RangerPolicyItem:
    """Represents a Ranger policy item (permissions for users/groups/roles)."""
    users: List[str]
    groups: List[str]
    accesses: List[Dict[str, Any]]
    roles: List[str] = None
    delegate_admin: bool = False
    conditions: List[Dict[str, Any]] = None

@dataclass
class RangerRowFilterItem:
    """Represents a Ranger row filter policy item."""
    users: List[str]
    groups: List[str]
    filter_expr: str
    conditions: List[Dict[str, Any]] = None

@dataclass
class RangerMaskingItem:
    """Represents a Ranger column masking policy item."""
    users: List[str]
    groups: List[str]
    mask_type: str  # MASK, MASK_SHOW_LAST_4, MASK_HASH, etc.
    mask_condition: Optional[str] = None
    conditions: List[Dict[str, Any]] = None

@dataclass
class RangerPolicy:
    """Represents a complete Ranger policy."""
    id: int
    name: str
    policy_type: PolicyType
    service: str
    resources: Dict[str, RangerResource]
    policy_items: List[RangerPolicyItem] = None
    deny_policy_items: List[RangerPolicyItem] = None
    allow_exceptions: List[RangerPolicyItem] = None
    deny_exceptions: List[RangerPolicyItem] = None
    row_filter_items: List[RangerRowFilterItem] = None
    masking_items: List[RangerMaskingItem] = None
    is_enabled: bool = True
    is_audit_enabled: bool = True
    description: str = ""

@dataclass
class RangerTag:
    """Represents a Ranger resource tag."""
    type: str
    attributes: Dict[str, str]

class RangerPolicyParser:
    """Parser for Ranger policy JSON files."""
    
    def __init__(self):
        self.policies: List[RangerPolicy] = []
        self.tags: Dict[str, RangerTag] = {}
        self.parse_errors: List[str] = []
    
    def parse_file(self, file_path: str) -> bool:
        """Parse Ranger policy JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return self.parse_json(data)
        except Exception as e:
            self.parse_errors.append(f"Error reading file: {str(e)}")
            return False
    
    def parse_json(self, data: Dict[str, Any]) -> bool:
        """Parse Ranger policy JSON data."""
        try:
            # ACL provider test format: testCases[].servicePolicies
            if 'testCases' in data:
                for tc in data['testCases']:
                    sp = tc.get('servicePolicies', {})
                    self._parse_service_policies(sp)
                return len(self.parse_errors) == 0

            self._parse_service_policies(data)
            return len(self.parse_errors) == 0
        except Exception as e:
            self.parse_errors.append(f"Error parsing JSON: {str(e)}")
            return False

    def _parse_service_policies(self, data: Dict[str, Any]):
        """Parse policies from a servicePolicies block or root export."""
        if 'policies' in data:
            for policy_data in data['policies']:
                policy = self._parse_policy(policy_data)
                if policy:
                    self.policies.append(policy)
        elif 'policyItems' in data or 'dataMaskPolicyItems' in data or 'rowFilterPolicyItems' in data:
            policy = self._parse_policy(data)
            if policy:
                self.policies.append(policy)

        # tagPolicyInfo.tagPolicies (policyengine format: array)
        if 'tagPolicyInfo' in data:
            for policy_data in data['tagPolicyInfo'].get('tagPolicies', []):
                policy = self._parse_policy(policy_data)
                if policy:
                    self.policies.append(policy)

        # tagPolicies as dict with nested policies array (aclprovider format)
        if 'tagPolicies' in data and isinstance(data['tagPolicies'], dict):
            for policy_data in data['tagPolicies'].get('policies', []):
                policy = self._parse_policy(policy_data)
                if policy:
                    self.policies.append(policy)

        if 'tagDefinitions' in data:
            for tag_name, tag_data in data['tagDefinitions'].items():
                self.tags[tag_name] = RangerTag(
                    type=tag_name,
                    attributes=tag_data.get('attributeDefs', {})
                )
    
    def _parse_policy(self, policy_data: Dict[str, Any]) -> Optional[RangerPolicy]:
        """Parse a single Ranger policy."""
        try:
            # Numeric policyType field (0=access, 1=mask, 2=rowfilter) takes precedence
            numeric_type = policy_data.get('policyType')
            if numeric_type == 1 or 'dataMaskPolicyItems' in policy_data:
                policy_type = PolicyType.COLUMN_MASK
            elif numeric_type == 2 or 'rowFilterPolicyItems' in policy_data:
                policy_type = PolicyType.ROW_FILTER
            else:
                policy_type = PolicyType.ACCESS

            resources = {}
            for res_name, res_data in policy_data.get('resources', {}).items():
                resources[res_name] = RangerResource(
                    type=res_name,
                    values=res_data.get('values', []),
                    is_excludes=res_data.get('isExcludes', False),
                    is_recursive=res_data.get('isRecursive', False)
                )

            policy_items = None
            deny_policy_items = None
            allow_exceptions = None
            deny_exceptions = None
            row_filter_items = None
            masking_items = None

            if policy_type == PolicyType.ACCESS:
                policy_items = self._parse_policy_items(policy_data.get('policyItems', []))
                deny_policy_items = self._parse_policy_items(policy_data.get('denyPolicyItems', []))
                allow_exceptions = self._parse_policy_items(policy_data.get('allowExceptions', []))
                deny_exceptions = self._parse_policy_items(policy_data.get('denyExceptions', []))
            elif policy_type == PolicyType.ROW_FILTER:
                row_filter_items = self._parse_row_filter_items(policy_data.get('rowFilterPolicyItems', []))
            elif policy_type == PolicyType.COLUMN_MASK:
                masking_items = self._parse_masking_items(policy_data.get('dataMaskPolicyItems', []))

            return RangerPolicy(
                id=policy_data.get('id', 0),
                name=policy_data.get('name', ''),
                policy_type=policy_type,
                service=policy_data.get('service', ''),
                resources=resources,
                policy_items=policy_items,
                deny_policy_items=deny_policy_items,
                allow_exceptions=allow_exceptions,
                deny_exceptions=deny_exceptions,
                row_filter_items=row_filter_items,
                masking_items=masking_items,
                is_enabled=policy_data.get('isEnabled', True),
                is_audit_enabled=policy_data.get('isAuditEnabled', True),
                description=policy_data.get('description', '')
            )
        except Exception as e:
            self.parse_errors.append(f"Error parsing policy: {str(e)}")
            return None
    
    def _parse_policy_items(self, items_data: List[Dict]) -> List[RangerPolicyItem]:
        """Parse standard policy items (ACL)."""
        items = []
        for item_data in items_data:
            items.append(RangerPolicyItem(
                users=item_data.get('users', []),
                groups=item_data.get('groups', []),
                roles=item_data.get('roles', []),
                accesses=item_data.get('accesses', []),
                delegate_admin=item_data.get('delegateAdmin', False),
                conditions=item_data.get('conditions', [])
            ))
        return items
    
    def _parse_row_filter_items(self, items_data: List[Dict]) -> List[RangerRowFilterItem]:
        """Parse row filter policy items."""
        items = []
        for item_data in items_data:
            items.append(RangerRowFilterItem(
                users=item_data.get('users', []),
                groups=item_data.get('groups', []),
                filter_expr=item_data.get('rowFilterInfo', {}).get('filterExpr', ''),
                conditions=item_data.get('conditions', [])
            ))
        return items
    
    def _parse_masking_items(self, items_data: List[Dict]) -> List[RangerMaskingItem]:
        """Parse column masking policy items."""
        items = []
        for item_data in items_data:
            mask_info = item_data.get('dataMaskInfo', {})
            items.append(RangerMaskingItem(
                users=item_data.get('users', []),
                groups=item_data.get('groups', []),
                mask_type=mask_info.get('dataMaskType', 'MASK'),
                mask_condition=mask_info.get('conditionExpr'),
                conditions=item_data.get('conditions', [])
            ))
        return items
    
    def get_policies_by_type(self, policy_type: PolicyType) -> List[RangerPolicy]:
        """Get all policies of a specific type."""
        return [p for p in self.policies if p.policy_type == policy_type]
    
    def get_policy_summary(self) -> Dict[str, int]:
        """Get summary of parsed policies."""
        return {
            "total": len(self.policies),
            "access": len(self.get_policies_by_type(PolicyType.ACCESS)),
            "row_filter": len(self.get_policies_by_type(PolicyType.ROW_FILTER)),
            "column_mask": len(self.get_policies_by_type(PolicyType.COLUMN_MASK)),
            "errors": len(self.parse_errors)
        }
