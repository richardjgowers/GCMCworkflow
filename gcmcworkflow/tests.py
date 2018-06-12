"""For running tests from inside python shell"""
import os
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))

def run_tests():
    return pytest.main(['-v', os.path.join(HERE, 'tests')])
