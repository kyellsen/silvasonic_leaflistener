import os

import soundfile as sf

from .base import BaseAnalyzer


class MetaAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "meta"

    def analyze(self, filepath: str):
        # Check file size first
        size_bytes = os.path.getsize(filepath)

        # Read header via soundfile (fast, no full load)
        info = sf.info(filepath)

        return {
            "duration_sec": info.duration,
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "file_size_bytes": size_bytes,
            "format": info.format
        }
