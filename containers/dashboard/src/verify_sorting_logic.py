def verify_logic():
    # Mock Data (Simulating HealthCheckerService.get_system_metrics())
    raw_containers = {
        "silvasonic-recorder": {"name": "silvasonic-recorder", "status": "Running"},
        "silvasonic-uploader": {"name": "silvasonic-uploader", "status": "Idle"},
        "silvasonic-sound-analyser": {"name": "silvasonic-sound-analyser", "status": "Running"},
        "silvasonic-birdnet": {"name": "silvasonic-birdnet", "status": "Running"},
        "silvasonic-weather": {"name": "silvasonic-weather", "status": "Running"},
        # postgres usually doesn't have suffix? Let's assume standard
        "postgres": {"name": "postgres", "status": "Running"}, 
        "silvasonic-healthchecker": {"name": "silvasonic-healthchecker", "status": "Running"},
        "random-junk": {"name": "random", "status": "Off"}
    }

    # --- LOGIC START (Copied from main.py) ---
    # Define Sort Order & Display Names
    # Order: Recorder, Carrier, LiveSound, Birdnet, Weather, PostgressDB, HealthChecker
    container_config = [
        {"key": "recorder", "name": "Recorder"},
        {"key": "uploader", "name": "Carrier"},
        {"key": "sound_analyser", "name": "LiveSound"},
        {"key": "birdnet", "name": "Birdnet"},
        {"key": "weather", "name": "Weather"},
        {"key": "postgres", "name": "PostgressDB"},
        {"key": "healthchecker", "name": "HealthChecker"},
    ]
    
    containers = []
    
    # helper to find container by fuzzy key
    def find_container(key_fragment, source_dict):
        for k, v in source_dict.items():
            if key_fragment in k:
                return v
        return None

    for config in container_config:
        # Try exact match first, then fuzzy
        c = raw_containers.get(config["key"])
        if not c:
            c = find_container(config["key"], raw_containers)
        
        if c:
            # Clone to avoid mutating original if cached
            c_copy = c.copy()
            c_copy["display_name"] = config["name"]
            containers.append(c_copy)
        else:
            # Optional: Add placeholder if missing? Or skip.
            pass

    # Add any others that weren't in the config?
    # Logic: simple Reorder.
    
    # Let's just pass the sorted list.
    containers_sorted = containers
    # --- LOGIC END ---

    print("Resulting Order and Names:")
    for c in containers_sorted:
        print(f"{c['display_name']} ({c['name']})")

    expected_names = [
        "Recorder",
        "Carrier",
        "LiveSound",
        "Birdnet",
        "Weather",
        "PostgressDB",
        "HealthChecker"
    ]
    
    actual_names = [c["display_name"] for c in containers_sorted]
    
    if actual_names == expected_names:
        print("\nSUCCESS: Logic matches requirements.")
    else:
        print(f"\nFAILURE: Expected {expected_names}, got {actual_names}")
        exit(1)

if __name__ == "__main__":
    verify_logic()
