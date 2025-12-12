"""
Run graphs directory - skipped from pytest test discovery.
"""
import pytest

# Mark this directory to be skipped by pytest
pytestmark = pytest.mark.skip(reason="Run graphs directory - not part of test suite")
