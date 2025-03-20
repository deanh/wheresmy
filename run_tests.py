#!/usr/bin/env python3
"""
Test runner for the wheresmy project.
Run this script to execute all tests.
"""

import unittest
import sys
import os

if __name__ == "__main__":
    # Add the project root to the Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Discover and run all tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Exit with error code if tests failed
    sys.exit(not result.wasSuccessful())