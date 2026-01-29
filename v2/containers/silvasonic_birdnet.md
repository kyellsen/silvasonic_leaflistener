# Container: silvasonic_birdnet

## 1. Das Problem / Die Lücke
Wir zeichnen tausende Stunden Audio auf. Kein Mensch kann das alles anhören. Wir benötigen eine automatisierte Klassifizierung, um zu wissen, *welche* Vögel wann und wo singen.

## 2. Nutzen für den User
*   **Biodiversitäts-Monitoring**: Erstellt automatisch Listen erkannter Arten.
*   **Filterung**: Ermöglicht dem User, gezielt nach "Amsel" oder "Rotkehlchen" zu suchen, statt stundenlang Rauschen zu hören.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **Datenbank**: Polling auf Tabelle `recordings` (WHERE `analyzed_bird=false`).
    *   **Dateisystem**: Liest Audio-Dateien (bevorzugt 48kHz "Low Res" für Performance).
*   **Processing**:
    *   **Inference**: Lässt das BirdNET-Modell (TFLite) über die Audio-Daten laufen.
    *   **Filterung**: Wendet Confidence-Thresholds an.
*   **Outputs**:
    *   **Datenbank**: Schreibt Ergebnisse in Tabelle `detections` und setzt Flag `analyzed_bird=true`.
    *   **Redis**: Publiziert interessante Funde auf `alerts` (optional, z.B. bei seltenen Arten).

## 4. Abgrenzung (Out of Scope)
*   **Kein Recording**: Nimmt kein Audio auf.
*   **Kein Fledermaus-Detektor**: BirdNET ist nur für Vögel (und einige andere hörbare Tiere) trainiert, nicht für Ultraschall.
*   **Kein Training**: Nutzt das vortrainierte Modell, lernt nicht selbst dazu.

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: Python 3.11+
*   **Wichtige Komponenten**:
    *   `birdnet-analyzer` (Python Library / TFLite Runtime)
    *   `librosa` (Audio Loading)
    *   `psycopg2` (DB)

## 6. Kritische Punkte
*   **CPU-Last**: Analyse ist teuer. Der Container muss im `podman-compose.yml` ggf. limitiert werden (CPU Quota), damit er nicht das Recording ("Tier 0") beeinträchtigt.
*   **Modell-Version**: BirdNET aktualisiert Modelle regelmäßig. Diese sind oft fest im Image verbacken. Updates erfordern Container-Neubau.
