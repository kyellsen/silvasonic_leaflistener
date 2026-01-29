# Container: silvasonic_redis

## 1. Das Problem / Die Lücke
Die Container müssen in Echtzeit kommunizieren (z.B. "Neues Audio-Level für VU-Meter", "Heartbeat von Container X"), ohne die persistente Datenbank mit hochfrequenten Schreibzugriffen zu belasten.

## 2. Nutzen für den User
*   **Responsiveness**: Das Dashboard zeigt den Live-Status (Online/Offline) und Audio-Pegel sofort an.
*   **Robustheit**: Dient als Puffer/Queue, falls die Hauptdatenbank kurzzeitig überlastet oder nicht erreichbar ist.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   `SET` / `HSET`: Status-Updates (Heartbeats) und Live-Metriken (VU-Meter).
    *   `PUBLISH`: Events auf dem Kanal `alerts`.
*   **Processing**:
    *   In-Memory Key-Value Storage.
    *   Pub/Sub Message Brokerage.
    *   Eviction alter Keys (LRU Policy).
*   **Outputs**:
    *   `GET`: Status-Abfragen durch `monitor` und `dashboard`.
    *   `SUBSCRIBE`: Echtzeit-Events an `monitor` (für Notifications).

## 4. Abgrenzung (Out of Scope)
*   **Keine Persistenz**: Daten in Redis sind flüchtig. Nach einem Neustart sind Queues/Status leer (by design).
*   **Keine Komplexen Queries**: Kein Ersatz für SQL-Abfragen.
*   **Kein File-Cache**: Speichert keine großen Blobs wie Bilder oder Audio.

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: `redis:7-alpine`
*   **Wichtige Komponenten**:
    *   Redis Server

## 6. Kritische Punkte
*   **Memory Management**: Muss limitiert sein (`--maxmemory 128mb`), um nicht den Host-RAM zu fressen (OOM Killer).
*   **Security**: Standardmäßig hat Redis kein Passwort im internen Netz. Sollte isoliert bleiben.
