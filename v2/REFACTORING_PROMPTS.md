# 🤖 Silvasonic V2 Refactoring Prompts

Copy these prompts to trigger the refactoring for a specific container.

---

## 1. Gateway (Caddy)
```text
Refactor the `silvasonic_gateway` container.
1. Read `v2/containers/silvasonic_gateway.md` for the spec.
2. Check existing `containers/gateway/Caddyfile`.
3. Update `containers/gateway/Caddyfile` to match the spec (Routes `/` -> dashboard, `/stream` -> livesound, Basic Auth).
4. Update `podman-compose.yml` for `silvasonic_gateway` (Image: `caddy:alpine`, Restart: `always`, Volumes).
5. Verify no root permissions are needed (assume host sysctl is set).
6. Update `v2/REFACTORING_STATUS.md`.
```

## 2. Database (TimescaleDB)
```text
Refactor the `silvasonic_database` container.
1. Read `v2/containers/silvasonic_database.md` for the spec.
2. Check `containers/db/init/*.sql` and `postgresql.conf`.
3. IMPLEMENT the missing SQL schemas:
   - `recordings` (Hypertable)
   - `detections` (Hypertable)
   - `measurements` (Hypertable)
   - `service_state` (Table)
   - `devices` (Table)
4. Update `postgresql.conf` with performance tunings (`synchronous_commit = off`, etc.).
5. Update `podman-compose.yml` (Image `timescale/timescaledb:latest-pg16`, Environment vars).
6. Update `v2/REFACTORING_STATUS.md`.
```

## 3. Redis
```text
Refactor the `silvasonic_redis` container.
1. Read `v2/containers/silvasonic_redis.md` for the spec.
2. Ensure persistence is configured (AOF/RDB).
3. Update `podman-compose.yml` (Image `redis:alpine`, Command with memory limits).
4. Update `v2/REFACTORING_STATUS.md`.
```

## 4. Tailscale
```text
Refactor the `silvasonic_tailscale` container.
1. Read `v2/containers/silvasonic_tailscale.md`.
2. Update `podman-compose.yml` (Privileges, Auth Key, State Volume).
3. Update `v2/REFACTORING_STATUS.md`.
```

## 5. Controller (The Manager)
```text
Refactor the `silvasonic_controller` container.
1. Read `v2/containers/silvasonic_controller.md`.
2. THIS IS A COMPLEX REFACTOR.
3. Remove FastAPI/Uvicorn code.
4. Implement `pyudev` monitoring loop.
5. Implement Redis Heartbeat.
6. Ensure `podman run` calls use the correct User/Groups for rootless Recorders.
7. Update `Dockerfile` and `podman-compose.yml` (Privileged mode).
8. Update `v2/REFACTORING_STATUS.md`.
```

## 6. Processor (The Brain)
```text
Implement the `silvasonic_processor` container.
1. Read `v2/containers/silvasonic_processor.md`.
2. Create `containers/processor/src/` structure.
3. Implement `main.py` (Loop), `indexer.py` (File Scan), `janitor.py` (Cleanup).
4. Ensure it connects to DB to insert Recordings.
5. Add `Dockerfile` and update `podman-compose.yml`.
6. Update `v2/REFACTORING_STATUS.md`.
```
