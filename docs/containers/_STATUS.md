# Container Documentation Status

Matches between Code and Documentation/Concept.

| Container | Status | Issues / Deviations from V2 Concept |
| :--- | :--- | :--- |
| **birdnet** | ✅ Compliant | Uses Redis `alerts` channel for notifications. |
| **controller** | ✅ Compliant | Matches V2 concept (DB Config, Redis Heartbeat, Podman Orchestration). |
| **dashboard** | ✅ Compliant | Reads recordings from DB, status from Redis. No FS listing. |
| **db** | ✅ Compliant | Schema matches V2 (Hypertables: recordings, detections, measurements). |
| **gateway** | ✅ Compliant | Routes `/` to dashboard and `/stream` to livesound. |
| **monitor** | ✅ Compliant | Listens to Redis `alerts` and `status:*`. |
| **processor** | ✅ Compliant | Matches V2 (Indexer, Thumbnailer, Janitor with 80/90% thresholds). |
| **recorder** | ✅ Compliant | Full V2 compliance (Dual-Stream High/Low Res + Icecast Stream). |
| **uploader** | ✅ Compliant | Matches V2 (Offline FLAC compression, Rclone, DB Status Update). |
| **weather** | ✅ Compliant | Fetches OpenMeteo data every 20m and stores in DB. |
