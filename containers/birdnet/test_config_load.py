import os
import sys
from pathlib import Path

import yaml

# Verify PyYAML is importable
try:
    import yaml
except ImportError:
    print("PyYAML not installed. Test cannot run directly.")
    sys.exit(1)

# Add src to path
sys.path.insert(0, str(Path.cwd()))

def test_config_load():
    # 1. Create a temp config file
    config_data = {
        'birdnet': {
            'min_confidence': 0.85,
            'latitude': 52.5,
            'longitude': 13.4,
            'week': 12,
            'overlap': 1.5,
            'sensitivity': 1.25,
            'threads': 4
        }
    }

    temp_config = Path("temp_test_config.yml")
    with open(temp_config, 'w') as f:
        yaml.dump(config_data, f)

    try:
        # 2. Set env var to point to it
        os.environ["CONFIG_FILE"] = str(temp_config.absolute())

        # 3. Import Config
        # We need to re-import or import after setting env var?
        # Config instantiates 'config' object at module level.
        # We can just instantiate a new Config class.
        from src.config import Config
        cfg = Config()

        # 4. Verify values
        # Note: floating point comparison
        assert abs(cfg.MIN_CONFIDENCE - 0.85) < 0.001, f"Expected 0.85, got {cfg.MIN_CONFIDENCE}"
        assert abs(cfg.LATITUDE - 52.5) < 0.001, f"Expected 52.5, got {cfg.LATITUDE}"
        assert cfg.THREADS == 4, f"Expected 4, got {cfg.THREADS}"

        print("SUCCESS: Config loaded correctly from YAML.")

    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if temp_config.exists():
            temp_config.unlink()

if __name__ == "__main__":
    test_config_load()
