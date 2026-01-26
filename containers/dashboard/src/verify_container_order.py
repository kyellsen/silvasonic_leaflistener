import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mocking services before import since main.py imports them at top level
# We need to make sure we can import main without errors
with patch("src.services.HealthCheckerService") as MockHealth, \
     patch("src.services.BirdNetService") as MockBird, \
     patch("src.services.CarrierService") as MockCarrier, \
     patch("src.services.RecorderService") as MockRec, \
     patch("src.services.SystemService") as MockSys:

    from src.main import dashboard
    
    # Setup mock data
    mock_metrics = {
        "recorder": {"name": "silvasonic-recorder", "status": "Running"},
        "uploader": {"name": "silvasonic-uploader", "status": "Idle"},
        "sound_analyser": {"name": "silvasonic-sound-analyser", "status": "Running"},
        "birdnet": {"name": "silvasonic-birdnet", "status": "Running"},
        "weather": {"name": "silvasonic-weather", "status": "Running"},
        "postgres": {"name": "silvasonic-postgres", "status": "Running"},
        "healthchecker": {"name": "silvasonic-healthchecker", "status": "Running"},
        "random_container": {"name": "silvasonic-random", "status": "Running"} # Should be ignored or handled?
    }
    
    MockHealth.get_system_metrics.return_value = mock_metrics
    MockSys.get_stats.return_value = {"cpu": 10, "ram_percent": 20, "disk_percent": 30}
    MockBird.get_recent_detections.return_value = []
    MockBird.get_stats.return_value = {}
    MockCarrier.get_status.return_value = {}
    MockRec.get_status.return_value = {}
    
    # Mock Request and Templates
    mock_request = MagicMock()
    
    # We need to spy on the 'render' call to inspect context
    # main.py does: return render(request, "index.html", context)
    # We can patch 'src.main.render'
    
    with patch("src.main.render") as mock_render:
        # Run dashboard route handler
        # It's async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(dashboard(mock_request, auth=True))
        
        # Check args
        args, kwargs = mock_render.call_args
        context = args[2]
        containers_sorted = context["containers"]
        
        print("Required Order: Recorder, Carrier, LiveSound, Birdnet, Weather, PostgressDB, HealthChecker")
        
        print("Actual Order:")
        for i, c in enumerate(containers_sorted):
            print(f"{i+1}. {c.get('display_name')} (Key: {c.get('name')})")
            
        # Assertion
        expected_order = [
            "Recorder",
            "Carrier",
            "LiveSound",
            "Birdnet",
            "Weather",
            "PostgressDB",
            "HealthChecker"
        ]
        
        actual_order = [c.get("display_name") for c in containers_sorted]
        
        if actual_order == expected_order:
            print("\nSUCCESS: Order matches!")
        else:
            print(f"\nFAILURE: Order mismatch.\nExpected: {expected_order}\nActual:   {actual_order}")
            exit(1)
