import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Environment configs
LOG_DIR = os.getenv("LOG_DIR", "/var/log/silvasonic")
AUDIO_DIR = os.getenv("AUDIO_DIR", "/data/recording")
ARTIFACTS_DIR = os.getenv("ARTIFACTS_DIR", "/data/processed/artifacts")
CLIPS_DIR = "/data/db/results/clips"

# App Info
VERSION = "0.1.0"
