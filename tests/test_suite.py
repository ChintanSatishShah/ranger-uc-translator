
"""
End-to-End Test Suite for Ranger to UC Translator
Tests all sample files through validation and translation pipeline
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.parser import RangerPolicyParser
from src.translator import EnhancedPolicyTranslator
from src.validator import RangerPolicyValidator
from src.config import TranslationConfig

@dataclass
class TestResult:
    """Result of a single test."""
    sample_file: str
    validation_passed: bool
    validation_errors: List[str]
    validation_warnings: List[str]
    parsing_passed: bool
    parsing_error: str
    policies_count: int
    translation_passed: bool
    translation_error: str
    sql_statements_count: int
    total_time_ms: float
    
    @property
    def passed(self) -> bool:
        """Overall test pass/fail."""
        return self.validation_passed and self.parsing_passed and self.translation_passed

def run_test_for_sample(sample_path: Path, validator: RangerPolicyValidator, 
                        parser: RangerPolicyParser, translator: EnhancedPolicyTranslator) -> TestResult:
    """Run end-to-end test for a single sample file using shared objects."""
    import time
    start_time = time.time()
    
    result = TestResult(
        sample_file=sample_path.name,
        validation_passed=False,
        validation_errors=[],
        validation_warnings=[],
        parsing_passed=False,
        parsing_error="",
        policies_count=0,
        translation_passed=False,
        translation_error="",
        sql_statements_count=0,
        total_time_ms=0
    )
    
    try:
        # Load JSON
        with open(sample_path, "r") as f:
            policy_data = json.load(f)
        
        # Step 1: Validation - validate individual policies in the export
        try:
            # Check if this is an export format with 'policies' array
            if 'policies' in policy_data and isinstance(policy_data['policies'], list):
                # Validate each individual policy
                all_valid = True
                all_errors = []
                all_warnings = []
                
                for idx, policy in enumerate(policy_data['policies']):
                    validation_result = validator.validate_policy_json(policy)
                    if not validation_result.is_valid:
                        all_valid = False
                        all_errors.extend([f"Policy {idx}: {err}" for err in validation_result.errors])
                    all_warnings.extend([f"Policy {idx}: {warn}" for warn in validation_result.warnings])
                
                result.validation_passed = all_valid
                result.validation_errors = all_errors
                result.validation_warnings = all_warnings
            else:
                # Single policy format
                validation_result = validator.validate_policy_json(policy_data)
                result.validation_passed = validation_result.is_valid
                result.validation_errors = validation_result.errors
                result.validation_warnings = validation_result.warnings
                
        except Exception as e:
            result.validation_passed = False
            result.validation_errors = [f"Validation exception: {str(e)}"]
        
        # Step 2: Parsing
        try:
            parser.parse_json(policy_data)
            policies = parser.policies
            result.policies_count = len(policies)
            result.parsing_passed = True
        except Exception as e:
            result.parsing_passed = False
            result.parsing_error = str(e)
        
        # Step 3: Translation (only if parsing succeeded)
        if result.parsing_passed:
            try:
                sql_statements = translator.translate_all(policies)
                result.sql_statements_count = len(sql_statements)
                result.translation_passed = True
            except Exception as e:
                result.translation_passed = False
                result.translation_error = str(e)
    
    except Exception as e:
        result.validation_errors = [f"File loading error: {str(e)}"]
    
    result.total_time_ms = (time.time() - start_time) * 1000
    return result

def run_all_tests() -> Tuple[List[TestResult], Dict[str, int]]:
    """Run tests for all sample files."""
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    samples_dir = Path("samples")
    
    if not samples_dir.exists():
        print(f"Error: samples/ directory not found")
        return [], {}
    
    sample_files = sorted(list(samples_dir.glob("*.json")))
    
    if not sample_files:
        print(f"Error: No sample files found in samples/")
        return [], {}
    
    print(f"\n{'='*80}")
    print(f"RANGER TO UC TRANSLATOR - END-TO-END TEST SUITE")
    print(f"{'='*80}")
    print(f"\nFound {len(sample_files)} sample files")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nInitializing shared objects (validator, parser, translator)...")
    
    # Create shared instances (reused across all tests for better performance)
    validator = RangerPolicyValidator()
    parser = RangerPolicyParser()
    config = TranslationConfig(
        catalog="main",
        apply_grants=True
    )
    translator = EnhancedPolicyTranslator(config)
    
    print(f"Running tests...\n")
    
    results = []
    for i, sample_file in enumerate(sample_files, 1):
        print(f"[{i}/{len(sample_files)}] Testing {sample_file.name}...", end=" ", flush=True)
        result = run_test_for_sample(sample_file, validator, parser, translator)
        results.append(result)
        
        if result.passed:
            print(f"✓ PASS ({result.total_time_ms:.0f}ms)")
        else:
            print(f"✗ FAIL ({result.total_time_ms:.0f}ms)")
    
    # Calculate summary statistics
    stats = {
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "validation_failed": sum(1 for r in results if not r.validation_passed),
        "parsing_failed": sum(1 for r in results if not r.parsing_passed),
        "translation_failed": sum(1 for r in results if not r.translation_passed),
        "total_policies": sum(r.policies_count for r in results),
        "total_sql_statements": sum(r.sql_statements_count for r in results),
        "total_time_ms": sum(r.total_time_ms for r in results)
    }
    
    return results, stats

def print_detailed_results(results: List[TestResult], stats: Dict[str, int]):
    """Print detailed test results."""
    
    check_mark = "✓ PASS"
    cross_mark = "✗ FAIL"
    
    print(f"\n\n{'='*80}")
    print(f"DETAILED TEST RESULTS")
    print(f"{'='*80}\n")
    
    for result in results:
        status = check_mark if result.passed else cross_mark
        val_icon = "✓" if result.validation_passed else "✗"
        parse_icon = "✓" if result.parsing_passed else "✗"
        trans_icon = "✓" if result.translation_passed else "✗"
        
        print(f"{status} - {result.sample_file}")
        print(f"   Validation: {val_icon} | Parsing: {parse_icon} | Translation: {trans_icon}")
        print(f"   Policies: {result.policies_count} | SQL Statements: {result.sql_statements_count} | "
              f"Time: {result.total_time_ms:.0f}ms")
        
        # Show errors/warnings if any
        if result.validation_errors:
            print(f"   Validation Errors:")
            for error in result.validation_errors[:3]:  # Show first 3
                print(f"      - {error}")
        
        if result.validation_warnings:
            print(f"   Validation Warnings: {len(result.validation_warnings)}")
        
        if result.parsing_error:
            print(f"   Parsing Error: {result.parsing_error}")
        
        if result.translation_error:
            print(f"   Translation Error: {result.translation_error}")
        
        print()
    
    print(f"{'='*80}")
    print(f"SUMMARY STATISTICS")
    print(f"{'='*80}\n")
    print(f"Total Tests:          {stats['total']}")
    print(f"Passed:               {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
    print(f"Failed:               {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
    
    if stats['failed'] > 0:
        print(f"\nFailure Breakdown:")
        if stats['validation_failed'] > 0:
            print(f"   - Validation failures: {stats['validation_failed']}")
        if stats['parsing_failed'] > 0:
            print(f"   - Parsing failures:    {stats['parsing_failed']}")
        if stats['translation_failed'] > 0:
            print(f"   - Translation failures: {stats['translation_failed']}")
    
    print(f"\nTranslation Statistics:")
    print(f"   - Total policies translated:    {stats['total_policies']}")
    print(f"   - Total SQL statements generated: {stats['total_sql_statements']}")
    print(f"   - Average SQL per policy:        {stats['total_sql_statements']/max(stats['total_policies'],1):.1f}")
    print(f"\nPerformance:")
    print(f"   - Total execution time:  {stats['total_time_ms']:.0f}ms ({stats['total_time_ms']/1000:.2f}s)")
    print(f"   - Average per sample:    {stats['total_time_ms']/stats['total']:.0f}ms")
    print(f"   - Throughput:            {stats['total']/max(stats['total_time_ms']/1000, 0.001):.1f} samples/sec")
    
    print(f"\n{'='*80}")
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    results, stats = run_all_tests()
    
    if not results:
        print("No tests were run")
        sys.exit(1)
    
    print_detailed_results(results, stats)
    
    # Exit with appropriate code
    if stats['failed'] == 0:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print(f"✗ {stats['failed']} test(s) failed")
        sys.exit(1)
