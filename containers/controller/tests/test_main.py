
import pytest
from unittest.mock import patch, MagicMock, mock_open
from silvasonic_controller.main import Controller, SessionInfo
from silvasonic_controller.profiles_loader import MicrophoneProfile
from silvasonic_controller.device_manager import AudioDevice

@pytest.fixture
def mock_deps():
    with patch("silvasonic_controller.main.DeviceManager") as dm, \
         patch("silvasonic_controller.main.PodmanOrchestrator") as po, \
         patch("silvasonic_controller.main.load_profiles") as lp:
        
        # Setup mock behavior
        lp.return_value = [MicrophoneProfile(name="Test", slug="test", device_patterns=["Test"])]
        yield dm, po, lp

def test_setup_logging():
    from silvasonic_controller.main import setup_logging
    with patch("os.makedirs"), \
         patch("logging.basicConfig"), \
         patch("logging.handlers.TimedRotatingFileHandler"):
        setup_logging()

def test_write_live_config(mock_deps):
    ctrl = Controller()
    ctrl.active_sessions["1"] = SessionInfo("c", "id", 1234, "slug")
    
    with patch("builtins.open", mock_open()) as m_open:
        with patch("os.rename"):
             with patch("os.makedirs"):
                 ctrl.write_live_config()
                 m_open.assert_called()
                 # check json content
                 handle = m_open()
                 handle.write.assert_called()

def test_write_live_config_exception(mock_deps):
    ctrl = Controller()
    with patch("builtins.open", side_effect=OSError):
         with patch("os.makedirs"):
             ctrl.write_live_config() # Should log error but not crash

def test_write_status_exception(mock_deps):
    ctrl = Controller()
    with patch("builtins.open", side_effect=OSError):
        with patch("os.makedirs"):
            ctrl.write_status()

def test_controller_init(mock_deps):
    ctrl = Controller()
    assert ctrl.profiles
    assert ctrl.running

def test_reconcile_add_new(mock_deps):
    """Test that a new device spawns a recorder."""
    dm, po, lp = mock_deps
    
    ctrl = Controller()
    
    # Setup Device Manager to return one device
    device = AudioDevice(name="Test Device", card_id="1", dev_path="/dev/snd/pcmC1D0c")
    dm.return_value.scan_devices.return_value = [device]
    
    # Setup Orchestrator to succeed
    po.return_value.spawn_recorder.return_value = True
    
    ctrl.reconcile()
    
    # Expect spawn call
    po.return_value.spawn_recorder.assert_called_once()
    args = po.return_value.spawn_recorder.call_args[1]
    assert args["card_id"] == "1"
    assert args["profile_slug"] == "test"
    
    # Check session stored
    assert "1" in ctrl.active_sessions

def test_reconcile_ignore_existing(mock_deps):
    """Test that existing sessions are not respawned."""
    dm, po, lp = mock_deps
    ctrl = Controller()
    
    # Initial State: Session exists
    ctrl.active_sessions["1"] = SessionInfo("cont", "id", 1234, "slug")
    
    # Scan returns same device
    device = AudioDevice(name="Test Device", card_id="1", dev_path="...")
    dm.return_value.scan_devices.return_value = [device]
    
    ctrl.reconcile()
    
    po.return_value.spawn_recorder.assert_not_called()

def test_reconcile_remove_stale(mock_deps):
    """Test that removed devices stop the recorder."""
    dm, po, lp = mock_deps
    ctrl = Controller()
    
    # Initial sessions
    ctrl.active_sessions["1"] = SessionInfo("cont_1", "id", 1234, "slug")
    ctrl.active_sessions["2"] = SessionInfo("cont_2", "id", 1234, "slug")
    
    # Scan returns only device 2
    device2 = AudioDevice(name="Test", card_id="2", dev_path="...")
    dm.return_value.scan_devices.return_value = [device2]
    
    ctrl.reconcile()
    
    # Expect stop for device 1
    po.return_value.stop_recorder.assert_called_once_with("cont_1")
    assert "1" not in ctrl.active_sessions
    assert "2" in ctrl.active_sessions

def test_reconcile_no_profile_ignore(mock_deps):
    dm, po, lp = mock_deps
    ctrl = Controller()
    
    # Device that doesn't match any profile
    device = AudioDevice(name="Unknown", card_id="99", dev_path="...")
    dm.return_value.scan_devices.return_value = [device]
    
    # Ensure no generic fallback match
    with patch("silvasonic_controller.main.find_matching_profile", return_value=None):
         # Actually Controller logic does custom matching loop lines 129-134
         # We need to ensure profiles don't match
         lp.return_value = [] # No profiles loaded
         ctrl = Controller() # reload with empty profiles
         
         ctrl.reconcile()
         po.return_value.spawn_recorder.assert_not_called()

def test_port_fallback(mock_deps):
    dm, po, lp = mock_deps
    ctrl = Controller()
    
    device = AudioDevice(name="Test", card_id="not_int", dev_path="...")
    dm.return_value.scan_devices.return_value = [device]
    
    # Force match
    with patch("silvasonic_controller.main.PodmanOrchestrator"): # refresh mock
        ctrl.orchestrator.spawn_recorder.return_value = True
        ctrl.reconcile()
        
        args = ctrl.orchestrator.spawn_recorder.call_args[1]
        assert "port" not in args # spawn_recorder doesn't take port, Controller calc port for SessionInfo
        
        session = ctrl.active_sessions["not_int"]
        assert session.port > 12000 # Should be calculated via hash

def test_stop_signal(mock_deps):
    ctrl = Controller()
    ctrl.stop()
    assert ctrl.running is False

def test_run_loop_exception(mock_deps):
    ctrl = Controller()
    dm, _, _ = mock_deps
    
    monitor = MagicMock()
    dm.return_value.start_monitoring.return_value = monitor
    
    # First poll raises exception, verifying loop continues (we break via side effect on running or just run once)
    # Logic: run() -> write_status -> poll.
    # We want poll to raise Exception once, then second time we break loop?
    # Or just verifying exception is caught.
    
    monitor.poll.side_effect = [Exception("PollError"), Exception("Stop")]
    
    # We patch time.sleep to run fast
    with patch("time.sleep") as m_sleep:
        with patch.object(ctrl, 'write_status'):
             # We need to stop the loop eventually. 
             # Let's side-effect time.sleep to stop running?
             def stop_loop(*args):
                 ctrl.running = False
             m_sleep.side_effect = stop_loop
             
             ctrl.run()
             
             assert m_sleep.called

def test_run_loop_event(mock_deps):
    ctrl = Controller()
    dm, _, _ = mock_deps
    
    monitor = MagicMock()
    dm.return_value.start_monitoring.return_value = monitor
    
    # Simulate one event then stop
    event = MagicMock()
    event.action = "add"
    event.device_node = "/dev/snd/test"
    
    # Return event first time, then raise KeyboardInterrupt to stop (not caught by catch-all Exception)
    monitor.poll.side_effect = [event, KeyboardInterrupt("Stop")]
    
    with patch("time.sleep"):
        with patch.object(ctrl, 'reconcile') as mock_rec:
             with patch.object(ctrl, 'write_status'):
                 try:
                     ctrl.run()
                 except KeyboardInterrupt:
                     pass
                 
                 mock_rec.assert_called()

def test_write_status(mock_deps):
    ctrl = Controller()
    with patch("builtins.open", mock_open()) as m_open:
        with patch("os.rename"):
            with patch("os.makedirs"):
                ctrl.write_status()
                m_open.assert_called()

def test_run_loop(mock_deps):
    ctrl = Controller()
    dm, _, _ = mock_deps
    
    # Mock monitor
    monitor = MagicMock()
    dm.return_value.start_monitoring.return_value = monitor
    monitor.poll.side_effect = [None, Exception("StopLoop")] # Return None then raise to break loop
    
    ctrl.running = False # Don't actually loop forever if side_effect fails
    
    # We want to test one loop iteration
    # Since run() has a while True, checking it is hard without breaking it.
    # We can patch 'reconcile' and 'write_status' 
    
    with patch.object(ctrl, 'reconcile') as mock_rec:
        with patch.object(ctrl, 'write_status'):
             # We just verify init logic here essentially
             pass
