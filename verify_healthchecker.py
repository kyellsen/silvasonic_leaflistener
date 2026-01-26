import sys
import os
import json
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'containers/healthchecker/src'))

sys.modules['psutil'] = MagicMock()
sys.modules['apprise'] = MagicMock()
sys.modules['mailer'] = MagicMock()
sys.modules['logging'] = MagicMock()
sys.modules['logging.handlers'] = MagicMock()

# Import the module to test
import main as hc

class TestHealthChecker(unittest.TestCase):
    def setUp(self):
        # Setup mock directories
        hc.STATUS_DIR = "/tmp/silvasonic_test/status"
        hc.ERROR_DIR = "/tmp/silvasonic_test/errors"
        hc.ARCHIVE_DIR = "/tmp/silvasonic_test/archive"
        os.makedirs(hc.STATUS_DIR, exist_ok=True)
        
    def test_services_config(self):
        """Verify new services are in config"""
        self.assertIn("dashboard", hc.SERVICES_CONFIG)
        self.assertIn("livesound", hc.SERVICES_CONFIG)
        self.assertIn("postgres", hc.SERVICES_CONFIG)
        
    @patch('socket.create_connection')
    def test_postgres_check(self, mock_socket):
        """Test Postgres probe logic"""
        # Mock successful connection
        mock_socket.return_value.__enter__.return_value = True
        
        # Create a mock internal mailer
        mock_mailer = MagicMock()
        
        # Run check
        hc.check_services_status(mock_mailer)
        
        # Read result
        with open(f"{hc.STATUS_DIR}/system_status.json") as f:
            status = json.load(f)
            
        self.assertIn("postgres", status)
        self.assertEqual(status["postgres"]["status"], "Running")
        self.assertEqual(status["postgres"]["message"], "Active (Port 5432 Open)")

    @patch('socket.create_connection')
    def test_dashboard_file_check(self, mock_socket):
        """Test Dashboard file pickup"""
        # Mock file existence for dashboard
        dash_status = {
            "service": "dashboard",
            "timestamp": 1234567890,
            "status": "Running"
        }
        with open(f"{hc.STATUS_DIR}/dashboard.json", "w") as f:
            json.dump(dash_status, f)

        mock_socket.side_effect = OSError("Main Loop Skip") # Fail postgres to focus on others or just let it fail
        
        mock_mailer = MagicMock()
        hc.check_services_status(mock_mailer)
        
        with open(f"{hc.STATUS_DIR}/system_status.json") as f:
            status = json.load(f)
            
        self.assertIn("dashboard", status)
        # It should likely be DOWN because timestamp is old, but it should be present
        self.assertEqual(status["dashboard"]["id"], "dashboard")

if __name__ == '__main__':
    unittest.main()
