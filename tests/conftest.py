"""Pytest configuration and fixtures."""
import pytest
import os
import asyncio
from app.storage import Storage
from app.config import config


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
async def setup_test_db():
    """Setup test database before each test."""
    # Use in-memory database for tests
    test_db_path = ":memory:"
    original_db_url = config.DATABASE_URL
    config.DATABASE_URL = f"sqlite:///{test_db_path}"
    
    # Ensure WEBHOOK_SECRET is set for tests
    if not config.WEBHOOK_SECRET:
        config.WEBHOOK_SECRET = "test_secret_key"
    
    # Initialize storage
    storage = Storage(config.DATABASE_URL)
    await storage.init_db()
    
    yield
    
    # Restore original config
    config.DATABASE_URL = original_db_url
