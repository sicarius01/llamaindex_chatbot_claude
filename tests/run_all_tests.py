#!/usr/bin/env python
"""
Run all tests for the LlamaIndex Chatbot project
"""

import sys
import os
import unittest
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))


def run_tests():
    """Run all test modules"""
    print("="*60)
    print(" RUNNING ALL TESTS FOR LLAMAINDEX CHATBOT")
    print("="*60)
    print()
    
    # List of test modules to run
    test_modules = [
        'test_config_loader',
        'test_logger',
        'test_memory',
        'test_sql_validator_standalone',
        'test_md_parser_core',
    ]
    
    # Test results
    results = {}
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    # Run each test module
    for module_name in test_modules:
        print(f"\n{'='*50}")
        print(f" Running: {module_name}")
        print('='*50)
        
        try:
            # Import and run the test module
            test_module = __import__(module_name)
            
            # Create test suite
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(test_module)
            
            # Run tests
            runner = unittest.TextTestRunner(verbosity=1)
            result = runner.run(suite)
            
            # Store results
            results[module_name] = {
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'success': result.wasSuccessful()
            }
            
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            
        except Exception as e:
            print(f"  ERROR: Failed to run {module_name}: {str(e)}")
            results[module_name] = {
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'success': False
            }
            total_errors += 1
    
    # Print summary
    print("\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)
    print()
    
    # Print results table
    print(f"{'Module':<35} {'Tests':<10} {'Status'}")
    print("-"*60)
    
    for module_name, result in results.items():
        status = "PASS" if result['success'] else "FAIL"
        status_color = "[OK]" if result['success'] else "[FAIL]"
        
        tests_info = f"{result['tests_run']} tests"
        if result['failures'] > 0:
            tests_info += f", {result['failures']} failures"
        if result['errors'] > 0:
            tests_info += f", {result['errors']} errors"
        
        print(f"{module_name:<35} {tests_info:<20} {status_color}")
    
    print("-"*60)
    print(f"Total: {total_tests} tests, {total_failures} failures, {total_errors} errors")
    
    # Overall status
    if total_failures == 0 and total_errors == 0:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[FAILURE] {total_failures + total_errors} test(s) failed")
        return 1


def check_environment():
    """Check that the environment is properly set up"""
    print("Checking environment...")
    
    # Check Python version
    python_version = sys.version_info
    print(f"  Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check required directories
    required_dirs = [
        'agent',
        'data',
        'data/schema_docs',
        'logs',
        'parsers',
        'utils',
        'tests'
    ]
    
    for dir_name in required_dirs:
        dir_path = parent_dir / dir_name
        if dir_path.exists():
            print(f"  [OK] Directory exists: {dir_name}")
        else:
            print(f"  [MISSING] Directory not found: {dir_name}")
    
    # Check config file
    config_file = parent_dir / 'config.yaml'
    if config_file.exists():
        print(f"  [OK] Config file exists: config.yaml")
    else:
        print(f"  [MISSING] Config file not found: config.yaml")
    
    print()


if __name__ == '__main__':
    # Stay in parent directory for config file access
    os.chdir(parent_dir)
    
    # Check environment
    check_environment()
    
    # Add tests directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent))
    
    # Run tests
    exit_code = run_tests()
    
    sys.exit(exit_code)