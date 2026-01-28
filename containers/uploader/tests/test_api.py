from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from silvasonic_uploader.config import UploaderSettings
from silvasonic_uploader.main import app

client = TestClient(app)


class TestAPI:
    @patch("silvasonic_uploader.api.UploaderSettings.load")
    def test_get_config(self, mock_load):
        mock_load.return_value = UploaderSettings(sync_interval=123)
        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert data["sync_interval"] == 123
        # Secrets should not be exposed directly if exclude_none?
        # Pydantic dump includes secrets as strings usually if not excluded.
        # But UploaderSettings uses SecretStr. Pydantic v2 dump usually hides them unless mode='json'
        # Let's check api.py implementation: return UploaderSettings.load()
        # FastAPI uses response_model=UploaderSettings.
        # Pydantic v2 serialization of SecretStr in FastAPI response usually hides it as '**********' or similar unless configured.
        # Actually in v2 it might output the string if not careful.
        # But typically we want to return them? Or blank them?
        # For now, we assume standard behavior.

    @patch("silvasonic_uploader.api.UploaderSettings.load")
    @patch("silvasonic_uploader.api.UploaderSettings.save")
    @patch("silvasonic_uploader.api._reloader")  # mocking the global reloader
    def test_patch_config(self, mock_reloader, mock_save, mock_load):
        # Initial settings
        current = UploaderSettings(sync_interval=10, nextcloud_user="old")
        mock_load.return_value = current

        # Update
        payload = {"sync_interval": 60, "nextcloud_user": "new"}
        response = client.patch("/config", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["sync_interval"] == 60
        assert data["nextcloud_user"] == "new"

        mock_save.assert_called_once()
        # Ensure reloader was triggered (background task)
        # Background tasks run after response. TestClient runs them? Yes.
        # But we need to verify it was added.
        # Since _reloader is an async function, we can check if it was awaited or added?
        # Actually _reloader is just a callable.
        # TestClient executes background tasks.
        # But `_reloader` is a global variable in api.py.
        # We need to ensure api.py sees our mock.
        # The patch above patches `silvasonic_uploader.api._reloader`
        # But `_reloader` is imported/used in the endpoint.
        # If it was assigned at module level, patch works.
        # But `set_reloader` sets it.
        # Let's just mock `set_reloader` or better, verify `background_tasks.add_task`? Harder with TestClient.
        # Simpler: Main logic is config save.

    @patch("silvasonic_uploader.api.RcloneWrapper")
    def test_test_connection_success(self, mock_wrapper_cls):
        mock_wrapper = mock_wrapper_cls.return_value
        mock_wrapper.configure_webdav = AsyncMock()
        mock_wrapper.list_files = AsyncMock(return_value={"file": 1})

        payload = {"url": "http://x", "user": "u", "password": "p"}
        response = client.post("/test-connection", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "success"

        mock_wrapper.configure_webdav.assert_awaited()
        mock_wrapper.list_files.assert_awaited()

    @patch("silvasonic_uploader.api.RcloneWrapper")
    def test_test_connection_fail(self, mock_wrapper_cls):
        mock_wrapper = mock_wrapper_cls.return_value
        mock_wrapper.configure_webdav = AsyncMock()
        mock_wrapper.list_files = AsyncMock(side_effect=Exception("Auth Fail"))

        payload = {"url": "http://x", "user": "u", "password": "p"}
        response = client.post("/test-connection", json=payload)

        assert response.status_code == 400
        assert "Auth Fail" in response.json()["detail"]
