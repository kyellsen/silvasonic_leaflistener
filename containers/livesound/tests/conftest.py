import asyncio
import sys
from pathlib import Path

import pytest

# Add src to sys.path so we can import from src.live
# This assumes the test execution root is the project root or the container root
# We want to be able to import "src.live"
container_root = Path(__file__).parent.parent
sys.path.insert(0, str(container_root))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
