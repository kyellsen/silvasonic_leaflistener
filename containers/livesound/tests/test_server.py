import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from silvasonic_livesound.live.server import app, processor


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Silvasonic Brain Live" in response.text


@pytest.mark.asyncio
async def test_websocket_spectrogram(client):
    """Test WebSocket connection and data reception."""
    # Mock processor.subscribe_spectrogram to return a dummy queue
    mock_queue = asyncio.Queue()
    await mock_queue.put([1, 2, 3])  # Fake spectrogram frame

    with patch.object(processor, "subscribe_spectrogram", return_value=mock_queue) as mock_sub:
        with patch.object(processor, "unsubscribe_spectrogram") as mock_unsub:
            with client.websocket_connect("/ws/spectrogram?source=test_mic") as websocket:
                data = websocket.receive_json()
                assert data["type"] == "spectrogram"
                assert data["data"] == [1, 2, 3]
                assert data["source"] == "test_mic"

            mock_sub.assert_called_with("test_mic")
            mock_unsub.assert_called()


@pytest.mark.asyncio
async def test_stream_endpoint_ffmpeg_mock(client):
    """Test the audio streaming endpoint by mocking the subprocess."""

    # Needs to mock asyncio.create_subprocess_exec used in audio_stream_generator
    # And processor.subscribe_audio

    mock_audio_queue = asyncio.Queue()
    await mock_audio_queue.put(b"audio_chunk_1")
    await mock_audio_queue.put(b"audio_chunk_2")

    # Mock Process
    mock_proc = AsyncMock()
    mock_proc.stdin = AsyncMock()
    mock_proc.stdout = AsyncMock()
    # Simulate reading stdout (MP3 output)
    mock_proc.stdout.read.side_effect = [b"mp3_frame_1", b"mp3_frame_2", b""]
    mock_proc.returncode = None
    # terminate is NOT async in asyncio.subprocess.Process
    from unittest.mock import Mock

    mock_proc.terminate = Mock()

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        with patch.object(processor, "subscribe_audio", return_value=mock_audio_queue):
            with patch(
                "silvasonic_livesound.live.server.feed_input", new_callable=AsyncMock
            ) as _:  # Prevent actual feeding loop
                response = client.get("/stream?source=test_mic")
                assert response.status_code == 200

                # Consume stream (response.content contains full body)
                assert b"mp3_frame_1" in response.content
                assert b"mp3_frame_2" in response.content

                # Verify FFmpeg called
                mock_exec.assert_called_once()
                args = mock_exec.call_args[0]
                assert "ffmpeg" in args
