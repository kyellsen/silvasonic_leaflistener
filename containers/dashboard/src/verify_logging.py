
import logging
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure src can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

# Mock dependencies before importing services
sys.modules["psutil"] = MagicMock()
sys.modules["shutil"] = MagicMock()
sys.modules["sqlalchemy"] = MagicMock()
sys.modules["sqlalchemy.ext.asyncio"] = MagicMock()
sys.modules["sqlalchemy.orm"] = MagicMock()
sys.modules["src.settings"] = MagicMock()

# Now import services
from src.services import SystemService, logger


class TestLogging(unittest.TestCase):
    def setUp(self):
        self.log_capture =  unittest.mock.MagicMock()
        logger.addHandler(self.log_capture)
        logger.setLevel(logging.ERROR)

    def test_get_stats_logging(self):
        # Setup psutil to raise generic exception
        sys.modules["psutil"].cpu_percent.side_effect = Exception("Test CPU Error")

        # Call the method
        stats = SystemService.get_stats()

        # Assertions
        # 1. It should not crash (return valid dict with 0s)
        self.assertEqual(stats["cpu"], 0)

        # 2. It should log the error
        # Check if any error log was emitted
        error_logged = False
        # The Mock handler handle method calls? No, we need a real handler or patch logger.error

    def test_logger_call(self):
        with patch.object(logger, 'error') as mock_log:
            # Force error in something simple, e.g. SystemService CPU part
            sys.modules["psutil"].cpu_percent.side_effect = Exception("Boom")

            SystemService.get_stats()

            # Check call
            mock_log.assert_called()
            args, _ = mock_log.call_args
            self.assertIn("Error getting CPU stats", args[0])
            self.assertIn("Boom", str(args[0]))
            print("\n[SUCCESS] Logger 'error' was called with message: ", args[0])

if __name__ == '__main__':
    unittest.main()
