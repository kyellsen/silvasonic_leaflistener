# Silvasonic Tools

This directory contains standalone tools for development and diagnostics.

## Audio Mocking (File Injection)

For local development or testing without hardware, you can use the **File Mock** strategy. This allows you to "inject" audio files as if they were coming from a live microphone.

1.  Ensure you are running with `MOCK_HARDWARE=true` or use the `file_mock` profile.
2.  Drop `.flac` or `.wav` files into the mock input directory (default: `/data/mock_input`).
3.  The Recorder service will detect these files and stream them in real-time (paced by sample rate) to the rest of the system.
4.  Files will be played in a loop or sequence.

_Note: The system requires `numpy` and `soundfile` to be installed in the environment._

## Audio Device Discovery

If you are setting up new hardware (e.g. Røde NT USB, Ultramic), use the helper script to find the correct ALSA configuration string:

```bash
python3 tools/find_audio_devices.py
```

This will list recognized capture devices and suggest the `hw:X,Y` string to use in your microphone profile (e.g. `hw:1,0`).
