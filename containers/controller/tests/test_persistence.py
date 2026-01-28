import os
import shutil
import tempfile

import pytest
from silvasonic_controller.persistence import ControllerEvent, LocalQueue, PersistenceManager


@pytest.fixture
def temp_db_path():
    # Create a temp directory
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "queue.db")
    yield db_path
    # Cleanup
    shutil.rmtree(tmp_dir)


@pytest.mark.asyncio
async def test_local_queue_operations(temp_db_path):
    queue = LocalQueue(db_path=temp_db_path)
    await queue.init()

    # Test Empty Peek
    batch = await queue.peek_batch()
    assert len(batch) == 0

    # Test Enqueue
    event = ControllerEvent(event_type="test_event", payload={"foo": "bar"}, timestamp=12345.6)
    await queue.enqueue(event)

    # Test Peek
    batch = await queue.peek_batch()
    assert len(batch) == 1
    assert batch[0][1].event_type == "test_event"
    assert batch[0][1].payload == {"foo": "bar"}

    # Test Ack
    msg_id = batch[0][0]
    await queue.ack_batch([msg_id])

    batch = await queue.peek_batch()
    assert len(batch) == 0

    await queue.close()


@pytest.mark.asyncio
async def test_persistence_manager_init():
    pm = PersistenceManager()
    # Mock queue init to avoid real File I/O in this test or rely on default?
    # Better to mock for unit test of manager logic, but here we just check structure.
    # Let's trust the integration test above.
    assert pm.running is True
