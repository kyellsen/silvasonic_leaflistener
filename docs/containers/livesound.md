# Container: Livesound

## 1. Das Problem / Die Lücke
Wissenschaftler und Techniker müssen oft "reinhören", um die Audioqualität zu prüfen oder spezifische akustische Phänomene in Echtzeit zu beobachten (z.B. Fledermaus-Rufe mittels Heterodyning). Das Herunterladen von fertigen FLAC-Dateien ist dafür zu langsam. Es wird ein Weg benötigt, den Live-Audio-Stream direkt vom Mikrofon mit minimaler Latenz an einen Browser oder externen Player zu senden, eventuell mit Echtzeit-Filtern.

## 2. Nutzen für den User
*   **Live-Monitoring:** Ermöglicht das Anhören des Mikrofons in Echtzeit aus der Ferne.
*   **Expert Analysis:** Bietet spezialisierte Filter (z.B. Frequenzverschiebung), um Ultraschall hörbar zu machen.
*   **Qualitätskontrolle:** Sofortiges Erkennen von Störgeräuschen oder Mikrofon-Defekten.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   Shared Memory / Audio Stream vom Recorder (oder direktes ALSA-Loopback, je nach Implementierung).
    *   HTTP-Requests für Stream-Zugriff.
*   **Processing:**
    *   Transcoding: Wandelt den rohen PCM-Stream in streaming-fähige Formate (MP3, OGG, MJPEG für Spektrogramme).
    *   Signal Processing: Wenden von Filtern wie Bandpass, Highpass oder Heterodyning an.
    *   Webserver: Bereitstellung eines Streaming-Endpoints (Port 8000).
*   **Outputs:**
    *   HTTP Audio Stream.
    *   (Optional) Echtzeit-Spektrogramm-Bilder.

## 4. Abgrenzung (Out of Scope)
*   Speichert **KEINE** Audio-Dateien dauerhaft (Aufgabe von `recorder`).
*   Ersetzt **NICHT** die klassische Vogelbestimmung (Aufgabe von `birdnet` auf statischen Dateien).
*   Ist **NICHT** die primäre User-Oberfläche (Aufgabe von `dashboard`, Livesound wird dort eingebettet).
