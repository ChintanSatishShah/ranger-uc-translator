"""
Quick Test Runner - Fast inline testing without shell execution
Run with: python -c "from tests import quick_test; quick_test.run()"
Or directly: cd tests && python quick_test.py
"""

import json
import sys
import os
from pathlib import Path
import time

# Add parent directory (project root) to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.parser import RangerPolicyParser
from src.translator import EnhancedPolicyTranslator
from src.validator import RangerPolicyValidator
from src.config import TranslationConfig

def run(verbose=True):
    """Run quick test suite on all samples."""
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    samples_dir = Path("samples")
    if not samples_dir.exists():
        print(f"Error: samples/ directory not found in {os.getcwd()}")
        return False
    
    sample_files = sorted(list(samples_dir.glob("*.json")))
    if not sample_files:
        print(f"Error: No sample files found")
        return False
    
    if verbose:
        print(f"{'='*80}")
        print(f"RANGER TO UC TRANSLATOR - QUICK TEST")
        print(f"{'='*80}\n")
    
    # Create shared instances
    validator = RangerPolicyValidator()
    parser = RangerPolicyParser()
    config = TranslationConfig(catalog="main", apply_grants=True)
    translator = EnhancedPolicyTranslator(config)
    
    results = []
    total_start = time.time()
    
    for i, sample_file in enumerate(sample_files, 1):
        start = time.time()
        
        if verbose:
            print(f"[{i:2d}/{len(sample_files)}] {sample_file.name:25s} ", end="", flush=True)
        
        try:
            with open(sample_file, "r") as f:
                data = json.load(f)
            
            # Validation
            if 'policies' in data:
                for policy in data['policies']:
                    validator.validate_policy_json(policy)
            
            # Parsing
            parser.parse_json(data)
            policies = parser.policies
            
            # Set tag metadata if available (for tag-based policies)
            if 'tagDefinitions' in data and 'resourceTags' in data:
                translator.set_tag_metadata(data['tagDefinitions'], data['resourceTags'])
            
            # Translation
            uc_policies = translator.translate_all(policies)
            
            # Extract SQL statements from UCPolicy objects
            sql_statements = []
            for uc_policy in uc_policies:
                sql_statements.extend(uc_policy.sql_statements)
            
            elapsed = (time.time() - start) * 1000
            results.append({
                'passed': True, 
                'file': sample_file.name,
                'policies': len(policies), 
                'sql': len(sql_statements), 
                'time': elapsed
            })
            
            if verbose:
                print(f"✓ {len(policies):2d} → {len(sql_statements):2d} SQL ({elapsed:4.0f}ms)")
            
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            results.append({
                'passed': False, 
                'file': sample_file.name,
                'error': str(e), 
                'time': elapsed
            })
            
            if verbose:
                print(f"✗ Error: {str(e)[:50]}")
    
    total_time = (time.time() - total_start) * 1000
    passed = sum(1 for r in results if r['passed'])
    total_policies = sum(r.get('policies', 0) for r in results)
    total_sql = sum(r.get('sql', 0) for r in results)
    
    if verbose:
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Tests:     {passed}/{len(sample_files)} passed")
        print(f"Policies:  {total_policies} translated")
        print(f"SQL:       {total_sql} statements generated")
        print(f"Time:      {total_time:.0f}ms ({total_time/1000:.2f}s)")
        print(f"Avg/test:  {total_time/len(sample_files):.0f}ms")
        print(f"{'='*80}\n")
        
        if passed == len(sample_files):
            print("✓ All tests passed!")
        else:
            print(f"✗ {len(sample_files)-passed} test(s) failed:")
            for r in results:
                if not r['passed']:
                    print(f"   - {r['file']}: {r.get('error', 'Unknown error')}")
    
    return passed == len(sample_files)

if __name__ == "__main__":
    success = run(verbose=True)
    sys.exit(0 if success else 1)
