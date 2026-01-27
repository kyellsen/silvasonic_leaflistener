from unittest.mock import AsyncMock, patch

import pytest
from silvasonic_controller.podman_client import PodmanOrchestrator


@pytest.mark.asyncio
async def test_list_recorders(mock_subprocess) -> None:
    orc = PodmanOrchestrator()
    sample_json = '[{"Names": "silvasonic_recorder_1"}]'

    process_mock = mock_subprocess(stdout_bytes=sample_json.encode())

    with patch(
        "asyncio.create_subprocess_exec", new_callable=lambda: AsyncMock(return_value=process_mock)
    ):
        result = await orc.list_active_recorders()
        assert len(result) == 1
        assert result[0]["Names"] == "silvasonic_recorder_1"


@pytest.mark.asyncio
async def test_list_recorders_empty(mock_subprocess) -> None:
    orc = PodmanOrchestrator()
    process_mock = mock_subprocess(stdout_bytes=b"")

    with patch(
        "asyncio.create_subprocess_exec", new_callable=lambda: AsyncMock(return_value=process_mock)
    ):
        result = await orc.list_active_recorders()
        assert result == []


@pytest.mark.asyncio
async def test_list_recorders_json_error(mock_subprocess) -> None:
    orc = PodmanOrchestrator()
    process_mock = mock_subprocess(stdout_bytes=b"INVALID JSON {{")

    with patch(
        "asyncio.create_subprocess_exec", new_callable=lambda: AsyncMock(return_value=process_mock)
    ):
        result = await orc.list_active_recorders()
        assert result == []


@pytest.mark.asyncio
async def test_spawn_recorder(mock_subprocess) -> None:
    orc = PodmanOrchestrator()
    process_mock = mock_subprocess(returncode=0)

    with patch(
        "asyncio.create_subprocess_exec", new_callable=lambda: AsyncMock(return_value=process_mock)
    ) as mock_exec:
        success = await orc.spawn_recorder(
            name="test_mic", profile_slug="rode_nt", device_path="/dev/snd/pcmC1D0c", card_id="1"
        )
        assert success

        # Verify call arguments
        # Call 0 is the call to create_subprocess_exec
        args = mock_exec.call_args[0]
        # args[0] is the program ("podman"), rest are args
        cmd_args = list(args)
        assert "podman" in cmd_args
        assert "run" in cmd_args
        assert "--device" in cmd_args
        # Check if port is calculated correctly (12000 + 1)
        assert any("LIVE_STREAM_PORT=12001" in str(a) for a in cmd_args)


@pytest.mark.asyncio
async def test_spawn_port_fallback(mock_subprocess) -> None:
    orc = PodmanOrchestrator()
    process_mock = mock_subprocess(returncode=0)

    with patch(
        "asyncio.create_subprocess_exec", new_callable=lambda: AsyncMock(return_value=process_mock)
    ) as mock_exec:
        await orc.spawn_recorder("mic", "slug", "path", "not_int")
        args = mock_exec.call_args[0]
        assert any("LIVE_STREAM_PORT" in str(a) for a in args)


@pytest.mark.asyncio
async def test_spawn_host_src(mock_subprocess) -> None:
    orc = PodmanOrchestrator()
    process_mock = mock_subprocess(returncode=0)

    with patch(
        "asyncio.create_subprocess_exec", new_callable=lambda: AsyncMock(return_value=process_mock)
    ) as mock_exec:
        with patch.dict("os.environ", {"HOST_RECORDER_SRC": "/host/src"}):
            await orc.spawn_recorder("mic", "slug", "path", "1")

            # Convert args tuple to single flat list of strings to search easily
            # But wait, create_subprocess_exec takes (*args), so call_args[0] is ('podman', 'run', ...)
            all_args = mock_exec.call_args[0]

            # Check for volume mount
            found = False
            for i, arg in enumerate(all_args):
                if arg == "-v":
                    # Check next arg
                    if i + 1 < len(all_args) and "/host/src:/app/src:z" in all_args[i + 1]:
                        found = True
                        break
            assert found


@pytest.mark.asyncio
async def test_spawn_exception() -> None:
    orc = PodmanOrchestrator()
    with patch("asyncio.create_subprocess_exec", side_effect=Exception("Boom")):
        assert await orc.spawn_recorder("mic", "s", "p", "1") is False


@pytest.mark.asyncio
async def test_stop_recorder(mock_subprocess) -> None:
    orc = PodmanOrchestrator()
    process_mock = mock_subprocess(returncode=0)

    with patch(
        "asyncio.create_subprocess_exec", new_callable=lambda: AsyncMock(return_value=process_mock)
    ) as mock_exec:
        await orc.stop_recorder("my_container")
        assert mock_exec.call_count == 2  # stop + rm
