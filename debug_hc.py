import sys
import os
from unittest.mock import MagicMock

# Mock libs
sys.modules['psutil'] = MagicMock()
sys.modules['apprise'] = MagicMock()
sys.modules['mailer'] = MagicMock()
sys.modules['logging'] = MagicMock()
sys.modules['logging.handlers'] = MagicMock()

sys.path.append(os.path.join(os.getcwd(), 'containers/healthchecker/src'))

print("Importing main...")
try:
    import main
    print("Import success")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
