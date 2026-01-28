import logging
import unittest
from unittest.mock import AsyncMock, MagicMock

from silvasonic_controller.device_manager import AudioDevice, DeviceManager
from silvasonic_controller.main import Controller
from silvasonic_controller.podman_client import PodmanOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)


class TestControllerAdoption(unittest.IsolatedAsyncioTestCase):
    async def test_adoption_success(self):
        """Test that the controller adopts an existing container with valid labels."""

        # Mocks
        mock_dm = MagicMock(spec=DeviceManager)
        mock_dm.scan_devices = AsyncMock(
            return_value=[AudioDevice(name="Test Mic", card_id="1", dev_path="/dev/snd/pcmC1D0c")]
        )

        mock_podman = MagicMock(spec=PodmanOrchestrator)

        # Simulate an EXISTING container for Card 1
        mock_podman.list_active_recorders = AsyncMock(
            return_value=[
                {
                    "Names": ["silvasonic_recorder_test_1"],
                    "Labels": {
                        "managed_by": "silvasonic-controller",
                        "card_id": "1",
                        "silvasonic.profile": "test_profile",
                        "silvasonic.port": "12001",
                        "silvasonic.rec_id": "test_profile_1",
                    },
                }
            ]
        )

        mock_podman.spawn_recorder = AsyncMock()
        mock_podman.stop_recorder = AsyncMock()

        # Initialize Controller
        controller = Controller(mock_dm, mock_podman)

        # Mock profiles to ensure profile matching logic works if needed
        # (Though adoption should bypass profile matching for EXISTING sessions)
        controller.profiles = []

        # --- EXECUTE ---
        # 1. Adopt orphans
        await controller.adopt_orphans()

        # Verify adoption happened
        self.assertIn("1", controller.active_sessions)
        session = controller.active_sessions["1"]
        self.assertEqual(session.rec_id, "test_profile_1")
        self.assertEqual(session.container_name, "silvasonic_recorder_test_1")

        # 2. Reconcile (Should NOT spawn new)
        await controller.reconcile()

        mock_podman.spawn_recorder.assert_not_called()
        print("\n✅ Test Passed: Container was adopted and NOT re-spawned.")

    async def test_adoption_failure_restarts_container(self):
        """Test that the controller restarts a container if labels are missing (legacy)."""

        # Mocks
        mock_dm = MagicMock(spec=DeviceManager)
        # Device exists
        mock_dm.scan_devices = AsyncMock(
            return_value=[
                AudioDevice(name="Generic Mic", card_id="2", dev_path="/dev/snd/pcmC2D0c")
            ]
        )

        mock_podman = MagicMock(spec=PodmanOrchestrator)

        # Simulate a LEGACY container (missing silvasonic.* labels)
        mock_podman.list_active_recorders = AsyncMock(
            return_value=[
                {
                    "Names": ["silvasonic_recorder_legacy"],
                    "Labels": {
                        "managed_by": "silvasonic-controller",
                        # Missing other labels
                        "card_id": "2",
                    },
                }
            ]
        )

        mock_podman.spawn_recorder = AsyncMock(return_value=True)  # Success spawning
        mock_podman.stop_recorder = AsyncMock()

        controller = Controller(mock_dm, mock_podman)

        # Need a profile to match "Generic Mic" so spawn works
        from silvasonic_controller.profiles_loader import MicrophoneProfile

        profile = MicrophoneProfile(name="Generic Mic", slug="generic", device_patterns=["Generic"])
        controller.profiles = [profile]

        # --- EXECUTE ---
        # 1. Adopt orphans
        await controller.adopt_orphans()

        # Verify it was NOT adopted
        self.assertNotIn("2", controller.active_sessions)

        # 2. Reconcile (Should SPAWN new because it wasn't adopted)
        await controller.reconcile()

        mock_podman.spawn_recorder.assert_called_once()
        print("\n✅ Test Passed: Legacy container ignored and new one spawned.")


if __name__ == "__main__":
    unittest.main()
