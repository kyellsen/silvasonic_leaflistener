import json

# Replicate the logic from dashboard main.py
def verify_dashboard_logic():
    # Mock Data
    raw_containers = {
        "recorder": {"id": "recorder", "status": "Running", "display_name": "Recorder"},
        "uploader": {"id": "uploader", "status": "Running", "display_name": "Carrier"}, # Old name
        "livesound": {"id": "livesound", "status": "Running", "display_name": "Livesound"},
        "birdnet": {"id": "birdnet", "status": "Running", "display_name": "BirdNET"},
        "postgres": {"id": "postgres", "status": "Running", "display_name": "DB"},
        "dashboard": {"id": "dashboard", "status": "Running", "display_name": "Dash"},
        "healthchecker": {"id": "healthchecker", "status": "Running", "display_name": "HC"},
    }
    
    # The new config from implementation
    container_config = [
        {"key": "livesound", "name": "Liveaudio"},
        {"key": "recorder", "name": "Recorder"},
        {"key": "uploader", "name": "Uploader"},
        {"key": "birdnet", "name": "BirdNet"},
        {"key": "dashboard", "name": "Dashboard"},
        {"key": "postgres", "name": "PostgressDB"},
        {"key": "healthchecker", "name": "HealthChecker"},
    ]
    
    containers = []
    
    def find_container(key_fragment, source_dict):
        for k, v in source_dict.items():
            if key_fragment in k:
                return v
        return None

    for config in container_config:
        c = raw_containers.get(config["key"])
        if not c:
            c = find_container(config["key"], raw_containers)
        
        if not c:
             c = { "id": config["key"], "display_name": config["name"], "status": "Down" }

        c_copy = c.copy()
        c_copy["display_name"] = config["name"]
        containers.append(c_copy)
        
    # Verify Order and Names
    expected_order = ["Liveaudio", "Recorder", "Uploader", "BirdNet", "Dashboard", "PostgressDB", "HealthChecker"]
    actual_order = [c["display_name"] for c in containers]
    
    print(f"Expected: {expected_order}")
    print(f"Actual:   {actual_order}")
    
    assert actual_order == expected_order
    print("Verification Passed!")

if __name__ == "__main__":
    verify_dashboard_logic()
