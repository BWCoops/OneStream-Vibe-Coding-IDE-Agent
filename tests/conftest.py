"""Root-level pytest configuration and marker definitions."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers to avoid warnings."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require running services)")
    config.addinivalue_line("markers", "e2e: End-to-end smoke tests (require full environment)")
    config.addinivalue_line("markers", "slow: Tests that take more than a few seconds")
