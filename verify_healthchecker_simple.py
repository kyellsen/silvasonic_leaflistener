import sys
import os
import json
from unittest.mock import MagicMock, patch

# Mock dependencies
sys.modules['psutil'] = MagicMock()
sys.modules['apprise'] = MagicMock()
sys.modules['mailer'] = MagicMock()
sys.modules['logging'] = MagicMock()
sys.modules['logging.handlers'] = MagicMock()

# Add path
sys.path.append(os.path.join(os.getcwd(), 'containers/healthchecker/src'))

try:
    import main as hc
    
    # Setup Dirs
    hc.STATUS_DIR = "/tmp/silvasonic_test/status"
    hc.ERROR_DIR = "/tmp/silvasonic_test/errors"
    hc.ARCHIVE_DIR = "/tmp/silvasonic_test/archive"
    os.makedirs(hc.STATUS_DIR, exist_ok=True)
    
    # 1. Test Services Config
    missing = []
    for svc in ["dashboard", "livesound", "postgres"]:
        if svc not in hc.SERVICES_CONFIG:
            missing.append(svc)
            
    if missing:
        raise Exception(f"Missing services in config: {missing}")
        
    # 2. Test Postgres Probe
    # We patch socket in 'main' module namespace if it was imported as 'socket'
    # Actually main.py has 'import socket', so we patch 'main.socket' or 'socket.create_connection'
    
    with patch('socket.create_connection') as mock_socket:
        mock_socket.return_value.__enter__.return_value = True
        
        mock_mailer = MagicMock()
        hc.check_services_status(mock_mailer)
        
        # Read Status
        with open(f"{hc.STATUS_DIR}/system_status.json") as f:
            status = json.load(f)
            
        if "postgres" not in status:
            raise Exception("Postgres status not generated")
            
        if status["postgres"]["status"] != "Running":
            raise Exception(f"Postgres status is {status['postgres']['status']}, expected Running")
            
        # Check Dashboard presence (simulated from missing file -> "Down"?)
        if "dashboard" not in status:
             # Just checking key presence
             raise Exception("Dashboard key missing in system status")

    with open("verification_result.txt", "w") as f:
        f.write("SUCCESS")

except Exception as e:
    with open("verification_result.txt", "w") as f:
        f.write(f"FAILURE: {e}")
    sys.exit(1)
