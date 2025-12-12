"""
Scripts directory - skipped from pytest test discovery.
"""
import pytest

# Mark this directory to be skipped by pytest
pytestmark = pytest.mark.skip(reason="Scripts directory - not part of test suite")
