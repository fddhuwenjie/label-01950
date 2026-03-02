"""
Pytest configuration and fixtures.
"""
import pytest
import pytest_asyncio

from app.services.linter_service import LinterService


# Configure pytest-asyncio to use function scope by default
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def fresh_linter_service():
    """Create a fresh LinterService instance for each test."""
    service = LinterService()
    yield service
    service.shutdown()
