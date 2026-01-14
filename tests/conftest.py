"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def suppress_banners():
    """Automatically suppress banner output in all tests."""
    with patch('converter.banners.display_welcome_banner'), \
         patch('converter.banners.display_step_separator'), \
         patch('converter.banners.display_completion_banner'):
        yield
