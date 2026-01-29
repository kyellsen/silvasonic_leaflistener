
# Container Spec: silvasonic_controller

> **Rolle:** Hardware-Supervisor und Container-Orchestrator.
> **Tier:** Tier 0 (Vital) – Verwaltet die Recorder.

## 1. Executive Summary
* **Problem:** USB-Mikrofone werden dynamisch angesteckt/abgezogen (Hotplug). Normale Container sehen diese Hardware-Events nicht.
* **Lösung:** Ein privilegierter Controller überwacht Udev-Events und startet/stoppt dynamisch `recorder`-Container für jedes Mikrofon.

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `python:3.11-slim-bookworm` | Basis für Python-Logic (`pyudev`, `podman` bindings). |
| **Security Context** | `Privileged` | **Ausnahme:** Muss Host-Hardware (USB Bus) sehen und Podman-Socket steuern. |
| **Restart Policy** | `always` | Muss Events permanent überwachen. |
| **Ports** | `None` | Keine externen Ports. |
| **Volumes** | - `/run/podman/podman.sock:/run/podman/podman.sock`<br>- `/dev/bus/usb:/dev/bus/usb`<br>- `/app/mic_profiles:/app/mic_profiles` | Docker Socket Control und USB Access. |
| **Dependencies** | `silvasonic_database`, `silvasonic_redis` | Braucht DB für Config, Redis für Heartbeat. |

## 3. Interfaces & Datenfluss
* **Inputs (Trigger):**
    *   *Udev Events:* USB Device Plug/Unplug.
    *   *Redis:* Befehle (z.B. "Restart all Recorders").
* **Outputs (Actions):**
    *   *Container Ops:* Spawnt `silvasonic_recorder` Container via Podman API.
    *   *Redis:* Meldet Status `status:controller`.

## 4. Konfiguration (Environment Variables)
*   `PODMAN_SOCKET_URL`: Pfad zum Socket.
*   `LOG_LEVEL`: `INFO`.

## 5. Abgrenzung (Out of Scope)
*   Verarbeitet KEIN Audio (Das macht der Recorder).
*   Schreibt KEINE Audio-Dateien.

## 6. Architecture & Code Best Practices
*   **Library:** `dbus-next` oder `pyudev` für Hardware-Detection.
*   **Safe Spawn:** Muss sicherstellen, dass Recorder als User `pi` (via `--user` Flag im API Call) laufen, obwohl Controller Root ist.
*   **Healthcheck:** Prüfen ob Verbindung zu Podman Socket steht.

## 7. Kritische Analyse
*   **Alternative:** Alles in einem Container ("Monolith"). Verworfen wegen Stabilität: Wenn Audio-Engine crasht, soll Controller (Manager) überleben.
