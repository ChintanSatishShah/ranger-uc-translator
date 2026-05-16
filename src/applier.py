"""
Policy applier module for executing Unity Catalog policies.
Executes translated SQL statements via Databricks SQL.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from .translator import UCPolicy
from .config import TranslationConfig, AUDIT_TABLES
import pandas as pd

@dataclass
class ApplyResult:
    """Result of applying a single policy."""
    policy_id: str
    policy_type: str
    status: str  # success, error, skipped
    message: str
    sql_statements: List[str]
    executed_count: int
    error_details: Optional[str] = None

class PolicyApplier:
    """Applies translated policies to Unity Catalog."""
    
    def __init__(self, config: TranslationConfig, spark_session=None):
        self.config = config
        self.spark = spark_session
        self.results: List[ApplyResult] = []
    
    def apply_policies(self, policies: List[UCPolicy], dry_run: bool = True) -> List[ApplyResult]:
        """Apply all translated policies."""
        self.results = []
        
        for policy in policies:
            result = self._apply_single_policy(policy, dry_run)
            self.results.append(result)
        
        return self.results
    
    def _apply_single_policy(self, policy: UCPolicy, dry_run: bool) -> ApplyResult:
        """Apply a single policy."""
        if dry_run:
            return ApplyResult(
                policy_id=policy.policy_id,
                policy_type=policy.policy_type,
                status="skipped",
                message="Dry run - not executed",
                sql_statements=policy.sql_statements,
                executed_count=0
            )
        
        executed_count = 0
        errors = []
        
        for sql in policy.sql_statements:
            try:
                self._execute_sql(sql)
                executed_count += 1
            except Exception as e:
                error_msg = f"Error executing SQL: {str(e)}"
                errors.append(error_msg)
                
                if not self.config.skip_errors:
                    return ApplyResult(
                        policy_id=policy.policy_id,
                        policy_type=policy.policy_type,
                        status="error",
                        message=f"Failed after {executed_count} statements",
                        sql_statements=policy.sql_statements,
                        executed_count=executed_count,
                        error_details="; ".join(errors)
                    )
        
        if errors:
            return ApplyResult(
                policy_id=policy.policy_id,
                policy_type=policy.policy_type,
                status="partial",
                message=f"Completed with errors: {executed_count}/{len(policy.sql_statements)} successful",
                sql_statements=policy.sql_statements,
                executed_count=executed_count,
                error_details="; ".join(errors)
            )
        
        return ApplyResult(
            policy_id=policy.policy_id,
            policy_type=policy.policy_type,
            status="success",
            message=f"Successfully executed {executed_count} statements",
            sql_statements=policy.sql_statements,
            executed_count=executed_count
        )
    
    def _execute_sql(self, sql: str):
        """Execute a single SQL statement."""
        if self.spark:
            self.spark.sql(sql)
        else:
            # If no spark session, use databricks SQL warehouse
            from databricks import sql
            # This would need connection configuration
            raise NotImplementedError("SQL warehouse execution not yet implemented")
    
    def log_to_audit_table(self, results: List[ApplyResult]):
        """Log application results to audit table."""
        if not self.spark:
            return
        
        # Prepare audit records
        records = []
        for result in results:
            records.append({
                "timestamp": datetime.now().isoformat(),
                "policy_id": result.policy_id,
                "policy_type": result.policy_type,
                "status": result.status,
                "message": result.message,
                "executed_count": result.executed_count,
                "total_statements": len(result.sql_statements),
                "error_details": result.error_details
            })
        
        # Write to Delta table
        df = pd.DataFrame(records)
        spark_df = self.spark.createDataFrame(df)
        
        audit_table = AUDIT_TABLES["uc_policies_applied"]
        spark_df.write.mode("append").saveAsTable(audit_table)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of apply results."""
        total = len(self.results)
        success = len([r for r in self.results if r.status == "success"])
        errors = len([r for r in self.results if r.status == "error"])
        partial = len([r for r in self.results if r.status == "partial"])
        skipped = len([r for r in self.results if r.status == "skipped"])
        
        return {
            "total_policies": total,
            "success": success,
            "errors": errors,
            "partial": partial,
            "skipped": skipped,
            "success_rate": f"{(success/total*100):.1f}%" if total > 0 else "0%",
            "total_statements_executed": sum(r.executed_count for r in self.results)
        }
    
    def generate_report(self) -> pd.DataFrame:
        """Generate detailed report of results."""
        data = []
        for result in self.results:
            data.append({
                "Policy ID": result.policy_id,
                "Type": result.policy_type,
                "Status": result.status,
                "Message": result.message,
                "Executed": result.executed_count,
                "Total SQL": len(result.sql_statements),
                "Errors": result.error_details or "-"
            })
        
        return pd.DataFrame(data)

class AuditLogger:
    """Logger for audit trail."""
    
    def __init__(self, spark_session):
        self.spark = spark_session
    
    def log_translation(self, ranger_policy_count: int, uc_policy_count: int, 
                       errors: List[str], metadata: Dict[str, Any]):
        """Log translation activity."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "activity": "translation",
            "ranger_policy_count": ranger_policy_count,
            "uc_policy_count": uc_policy_count,
            "error_count": len(errors),
            "errors": "; ".join(errors) if errors else None,
            "metadata": str(metadata)
        }
        
        df = pd.DataFrame([record])
        spark_df = self.spark.createDataFrame(df)
        
        audit_table = AUDIT_TABLES["translation_log"]
        spark_df.write.mode("append").saveAsTable(audit_table)
    
    def log_ranger_policies(self, policies_json: str):
        """Log raw Ranger policies."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "policies_json": policies_json,
            "upload_source": "ui"
        }
        
        df = pd.DataFrame([record])
        spark_df = self.spark.createDataFrame(df)
        
        audit_table = AUDIT_TABLES["ranger_policies_raw"]
        spark_df.write.mode("append").saveAsTable(audit_table)
