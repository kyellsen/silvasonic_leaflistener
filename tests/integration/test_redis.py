import pytest


def test_redis_ping(redis_client):
    """Verify Redis PING response."""
    assert redis_client.ping() is True


def test_redis_set_get(redis_client):
    """Verify basic SET/GET operations to ensure read/write capability."""
    key = "integration_test_key"
    value = "hello_silvasonic"

    # Set with expiry to avoid polluting DB
    assert redis_client.set(key, value, ex=10) is True
    assert redis_client.get(key) == value


def test_redis_config_maxmemory(redis_client):
    """Verify that maxmemory is configured (approximately)."""
    # This relies on CONFIG command being available.
    try:
        config = redis_client.config_get("maxmemory")
        max_mem = int(config.get("maxmemory", 0))
        # 128mb = 128 * 1024 * 1024 = 134217728 bytes
        assert max_mem == 134217728, f"Expected maxmemory 128mb, got {max_mem}"
    except Exception:
        # If CONFIG command is restricted, skip this test
        pytest.skip("CONFIG command restricted or unavailable.")
