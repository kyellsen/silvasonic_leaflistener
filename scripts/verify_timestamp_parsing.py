# Mock class provided in snippet to test the logic in isolation or we can import if path allows.
# However, since we are in a dev environment, let's try to import the actual class first.
# If that fails due to dependencies (like birdnet_analyzer), we will mock the structure or just test the method logic.
import sys
from datetime import UTC, datetime

# Check if we can import the module. We need to set pythonpath.
sys.path.append("/mnt/data/dev/packages/silvasonic/containers/birdnet/src")

try:
    # We need to mock config and db to instantiate Analyzer without side effects
    from unittest.mock import MagicMock

    # Mocking external dependencies that might fail on init
    import silvasonic_birdnet.analyzer
    from silvasonic_birdnet.analyzer import BirdNETAnalyzer

    silvasonic_birdnet.analyzer.config = MagicMock()
    silvasonic_birdnet.analyzer.db = MagicMock()
    silvasonic_birdnet.analyzer.bn_analyze = MagicMock()  # Mock the analyzer itself

    analyzer = BirdNETAnalyzer()

    print("Successfully instantiated BirdNETAnalyzer for testing.")

    # Test Cases
    test_files = [
        ("2026-01-28_10-00-00.flac", datetime(2026, 1, 28, 10, 0, 0, tzinfo=UTC)),
        ("2025-12-31_23-59-59.wav", datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)),
        ("invalid_name.mp3", None),
        (
            "2026-01-28_10-00-00_extra.flac",
            None,
        ),  # Strict format check? current impl uses stem directly
    ]

    print("\nRunning Timestamp Parsing Tests:")
    all_passed = True
    for filename, expected in test_files:
        result = analyzer._parse_timestamp_from_filename(filename)

        # Special handling if our implementation is strict on stem vs filename
        # The implementation uses Path(filename).stem.
        # "2026-01-28_10-00-00_extra.flac" stem is "2026-01-28_10-00-00_extra" -> parse fails -> None. Correct.

        status = "PASS" if result == expected else "FAIL"
        if status == "FAIL":
            all_passed = False
            print(f"[{status}] {filename}: Expected {expected}, Got {result}")
        else:
            print(f"[{status}] {filename}")

    if all_passed:
        print("\nAll timestamp parsing tests PASSED.")
    else:
        print("\nSome tests FAILED.")
        exit(1)

except ImportError as e:
    print(f"Failed to import BirdNETAnalyzer: {e}")
    # Fallback: Just test the logic if import fails (unlikely given file structure but good for robustness)
    exit(1)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    exit(1)
