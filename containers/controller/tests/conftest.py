import sys
from unittest.mock import MagicMock

# Mock system dependencies that might not be present in the test environment
module_mock = MagicMock()
sys.modules["pyudev"] = module_mock
sys.modules["psutil"] = module_mock

# Ensure we can import them
