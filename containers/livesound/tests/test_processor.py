import asyncio
from unittest.mock import MagicMock, patch

import pytest

# Assuming src is in path via conftest
from silvasonic_livesound.live.processor import AudioIngestor


@pytest.mark.asyncio
async def test_ingestor_initialization():
    with patch("silvasonic_livesound.live.processor.settings") as mock_settings:
        mock_settings.HOST = "0.0.0.0"
        mock_settings.LISTEN_PORTS = {"test_mic": 9999}
        mock_settings.CHUNK_SIZE = 4096
        mock_settings.FFT_WINDOW = 2048

        with patch("socket.socket") as mock_socket_cls:
            ingestor = AudioIngestor()

            # Verify socket binding
            assert "test_mic" in ingestor.sockets

            mock_sock_instance = mock_socket_cls.return_value
            mock_sock_instance.bind.assert_called_with(("0.0.0.0", 9999))


@pytest.mark.asyncio
async def test_subscribe_spectrogram():
    ingestor = AudioIngestor()

    # Test valid subscription
    q = await ingestor.subscribe_spectrogram("default")
    assert isinstance(q, asyncio.Queue)
    assert q in ingestor._spectrogram_queues["default"]

    # Test unsubscribe
    ingestor.unsubscribe_spectrogram(q, "default")
    assert q not in ingestor._spectrogram_queues["default"]


@pytest.mark.asyncio
async def test_subscribe_audio():
    ingestor = AudioIngestor()

    q = await ingestor.subscribe_audio("default")
    assert isinstance(q, asyncio.Queue)
    assert q in ingestor._audio_queues["default"]

    ingestor.unsubscribe_audio(q, "default")
    assert q not in ingestor._audio_queues["default"]


@pytest.mark.asyncio
async def test_ingest_loop_logic():
    """Verify that data received on the socket is put into the appropriate queues."""
    with patch("silvasonic_livesound.live.processor.settings") as mock_settings:
        mock_settings.HOST = "0.0.0.0"
        mock_settings.LISTEN_PORTS = {"test_mic": 9999}
        mock_settings.CHUNK_SIZE = 1024  # Custom chunk size for this test
        mock_settings.SAMPLE_RATE = 48000
        mock_settings.FFT_WINDOW = 2048
        mock_settings.HOP_LENGTH = 512

        with patch("socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value = mock_sock

            ingestor = AudioIngestor()
        ingestor.running = True
        ingestor.loop = asyncio.get_running_loop()

        # Subscribe to audio
        audio_q = await ingestor.subscribe_audio("test_mic")

        # Prepare mock data
        # We need chunk_size * 2 * 2 (safety buffer)
        fake_audio = b"\x00" * 1024

        # Custom side effect to break the loop
        def breaking_recv(*args):
            # First call: return data
            if mock_sock.recvfrom.call_count == 1:
                return (fake_audio, ("127.0.0.1", 12345))
            # Second call: stop loop and raise to exit recv
            ingestor.running = False
            raise Exception("Stop Loop")

        mock_sock.recvfrom.side_effect = breaking_recv

        # Run
        with patch.object(ingestor, "_broadcast_safe") as mock_broadcast:
            ingestor._ingest_loop("test_mic", mock_sock)

            # Checks
            assert mock_broadcast.called
            # Check call args: (queues_set, data)
            args, _ = mock_broadcast.call_args
            assert audio_q in args[0]
            assert args[1] == fake_audio


@pytest.mark.asyncio
async def test_dynamic_update_sources():
    ingestor = AudioIngestor()
    ingestor.running = True

    with patch("socket.socket") as mock_socket_cls:
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock

        # Update with new source
        new_ports = {"new_mic": 8888}

        with patch("threading.Thread") as mock_thread:
            ingestor.update_sources(new_ports)

            assert "new_mic" in ingestor.sockets
            mock_sock.bind.assert_called_with(("0.0.0.0", 8888))
            assert mock_thread.called  # Should start a new thread
