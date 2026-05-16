"""
Ranger to Unity Catalog Policy Translation Engine

A comprehensive solution for migrating Apache Ranger policies to Databricks Unity Catalog.
Supports ACL, Row Filters, Column Masking, and Tag-based policies.
"""

__version__ = "1.0.0"
__author__ = "Ranger UC Translator Team"
__license__ = "Apache 2.0"

# Import main classes for convenient access
from .parser import RangerPolicyParser, PolicyType
from .translator import PolicyTranslator, TagPolicyTranslator, UCPolicy
from .applier import PolicyApplier, ApplyResult, AuditLogger
from .config import TranslationConfig, default_config

__all__ = [
    # Parser
    'RangerPolicyParser',
    'PolicyType',
    
    # Translator
    'PolicyTranslator',
    'TagPolicyTranslator',
    'UCPolicy',
    
    # Applier
    'PolicyApplier',
    'ApplyResult',
    'AuditLogger',
    
    # Config
    'TranslationConfig',
    'default_config',
]
