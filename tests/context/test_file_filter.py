"""
Test file filtering implementation.
"""

from pathlib import Path
from code_understanding.context.file_filter import FileFilter


def test_check_common_patterns():
    """Test the static common pattern checker."""
    # Test a few common patterns we know should be ignored
    assert FileFilter.check_common_patterns(".git/config") == True
    assert FileFilter.check_common_patterns(".idea/workspace.xml") == True

    # Test a regular file that shouldn't be ignored
    assert FileFilter.check_common_patterns("src/main.py") == False
