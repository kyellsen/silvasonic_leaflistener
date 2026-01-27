import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Mock system dependencies that might not be present in the test environment
module_mock = MagicMock()
sys.modules["pyudev"] = module_mock
sys.modules["psutil"] = module_mock


# AsyncIO Helper for subprocess mocking
@pytest.fixture
def mock_subprocess():
    """Returns a factory for a mock Process object."""

    def _create_mock_process(stdout_bytes=b"", stderr_bytes=b"", returncode=0):
        process = AsyncMock()
        process.stdout.read.return_value = stdout_bytes
        process.stderr.read.return_value = stderr_bytes
        process.communicate.return_value = (stdout_bytes, stderr_bytes)
        process.returncode = returncode
        process.wait.return_value = None
        return process

    return _create_mock_process
