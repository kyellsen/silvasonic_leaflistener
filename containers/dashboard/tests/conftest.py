import sys
from unittest.mock import MagicMock

# Mock the database handler before any service imports it
# This prevents create_async_engine from running and potentially connecting/hanging
if "silvasonic_dashboard.services.database" not in sys.modules:
    mock_db_module = MagicMock()
    # Ensure db.get_connection() returns a Context Manager
    mock_db = MagicMock()
    mock_db_module.db = mock_db
    sys.modules["silvasonic_dashboard.services.database"] = mock_db_module
