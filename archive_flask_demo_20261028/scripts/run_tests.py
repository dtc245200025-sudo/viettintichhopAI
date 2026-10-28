import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if __name__ == '__main__':
    exit_code = pytest.main(["-v", "tests"])
    sys.exit(exit_code)

