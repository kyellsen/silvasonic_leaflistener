"""Microphone Profile Loader.

Loads and manages microphone profiles from YAML files.
Profiles define device detection patterns and optimal audio settings.
"""

import logging
import os
import re
import subprocess
import typing
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger("mic_profiles")


@dataclass
class AudioConfig:
    """Audio recording configuration."""

    sample_rate: int = 48000
    channels: int = 1
    bit_depth: int = 16
    format: str = "S16_LE"


@dataclass
class RecordingConfig:
    """Recording output configuration."""

    chunk_duration_seconds: int = 30
    output_format: str = "flac"
    compression_level: int = 5


@dataclass
class MicrophoneProfile:
    """Complete microphone profile."""

    name: str
    slug: str = ""  # URL-safe identifier for folder names
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    device_patterns: list[str] = field(default_factory=list)
    audio: AudioConfig = field(default_factory=AudioConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    priority: int = 50
    is_mock: bool = False

    def __post_init__(self) -> None:
        """Clean up data after initialization."""
        if not self.slug:
            # Generate slug from name
            self.slug = re.sub(r"[^a-z0-9]+", "_", self.name.lower()).strip("_")

    @classmethod
    def from_dict(cls, data: dict[str, typing.Any], filename: str = "") -> "MicrophoneProfile":
        """Create profile from dictionary (parsed YAML)."""
        audio_data = data.get("audio", {})
        recording_data = data.get("recording", {})
        mock_data = data.get("mock", {})

        # Use filename without extension as slug if not specified
        slug = data.get("slug", "")
        if not slug and filename:
            slug = Path(filename).stem

        return cls(
            name=data.get("name", "Unknown"),
            slug=slug,
            manufacturer=data.get("manufacturer", "Unknown"),
            model=data.get("model", "Unknown"),
            device_patterns=data.get("device_patterns", []),
            audio=AudioConfig(
                sample_rate=audio_data.get("sample_rate", 48000),
                channels=audio_data.get("channels", 1),
                bit_depth=audio_data.get("bit_depth", 16),
                format=audio_data.get("format", "S16_LE"),
            ),
            recording=RecordingConfig(
                chunk_duration_seconds=recording_data.get("chunk_duration_seconds", 30),
                output_format=recording_data.get("output_format", "flac"),
                compression_level=recording_data.get("compression_level", 5),
            ),
            priority=data.get("priority", 50),
            is_mock=mock_data.get("enabled", False),
        )


@dataclass
class DetectedDevice:
    """Represents a detected audio device."""

    card_id: str
    hw_address: str
    description: str


def get_alsa_devices() -> list[DetectedDevice]:
    """Get list of ALSA capture devices."""
    devices = []
    try:
        result = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
        output = result.stdout + result.stderr

        for line in output.split("\n"):
            if "card" in line.lower():
                # Match "card X: ... device Y:"
                match = re.search(r"card (\d+):.*?device (\d+):", line)
                if match:
                    card_id = match.group(1)
                    device_id = match.group(2)
                    devices.append(
                        DetectedDevice(
                            card_id=card_id,
                            hw_address=f"plughw:{card_id},{device_id}",
                            description=line.strip(),
                        )
                    )
    except Exception as e:
        logger.error(f"Error querying ALSA devices: {e}")

    return devices


def load_profiles(profiles_dir: Path | None = None) -> list[MicrophoneProfile]:
    """Load all microphone profiles from YAML files."""
    if profiles_dir is None:
        profiles_dir = Path(__file__).parent / "microphones"

    profiles = []

    if not profiles_dir.exists():
        logger.error(f"Profiles directory not found: {profiles_dir}")
        return []

    for yml_file in sorted(profiles_dir.glob("*.yml")):
        try:
            with open(yml_file) as f:
                data = yaml.safe_load(f)
                if data:
                    profile = MicrophoneProfile.from_dict(data, str(yml_file))
                    profiles.append(profile)
                    logger.debug(f"Loaded profile: {profile.name} ({profile.slug})")
        except Exception as e:
            logger.error(f"Error loading profile {yml_file}: {e}")

    # Sort by priority (lower = higher priority)
    profiles.sort(key=lambda p: p.priority)

    logger.info(f"Loaded {len(profiles)} microphone profiles")
    return profiles


def find_matching_profile(
    profiles: list[MicrophoneProfile], force_mock: bool = False, force_profile: str | None = None
) -> tuple[MicrophoneProfile | None, DetectedDevice | None]:
    """Find a profile that matches an available audio device.

    Returns:
        Tuple of (matched_profile, device) or (None, None)
    """
    # Handle mock mode
    if force_mock:
        for profile in profiles:
            if profile.is_mock:
                logger.info(f"Mock mode: Using profile '{profile.name}'")
                mock_device = DetectedDevice(
                    card_id="mock", hw_address="mock", description="Mock Virtual Device"
                )
                return profile, mock_device

        # Create default mock if no mock profile found
        logger.warning("No mock profile found, creating default")
        mock_profile = MicrophoneProfile(
            name="Default Mock",
            slug="mock",
            is_mock=True,
            audio=AudioConfig(sample_rate=48000),
            recording=RecordingConfig(chunk_duration_seconds=10),
        )
        mock_device = DetectedDevice(
            card_id="mock", hw_address="mock", description="Mock Virtual Device"
        )
        return mock_profile, mock_device

    # Handle forced profile selection
    if force_profile:
        for profile in profiles:
            if (
                force_profile.lower() in profile.name.lower()
                or force_profile.lower() == profile.slug
            ):
                logger.info(f"Forced profile: {profile.name}")
                devices = get_alsa_devices()
                if devices:
                    return profile, devices[0]
                logger.warning("Forced profile but no devices found")
                return None, None

    # Auto-detection
    devices = get_alsa_devices()

    if not devices:
        logger.error("No audio devices found!")
        return None, None

    logger.info(f"Found {len(devices)} audio device(s)")
    for dev in devices:
        logger.info(f"  - [{dev.card_id}] {dev.description}")

    # Match profiles to devices
    for profile in profiles:
        if profile.is_mock:
            continue

        for pattern in profile.device_patterns:
            for device in devices:
                if pattern.lower() in device.description.lower():
                    logger.info(f"Matched: '{pattern}' -> {profile.name}")
                    return profile, device

    # Fallback: use generic profile with first device
    logger.warning("No specific profile matched, trying generic fallback")
    generic = next((p for p in profiles if "generic" in p.name.lower()), None)
    if generic:
        return generic, devices[0]

    logger.error("No matching profile found!")
    return None, None


def get_active_profile() -> tuple[MicrophoneProfile | None, DetectedDevice | None]:
    """Main entry point: Get the active microphone profile and device.

    Environment variables:
        MOCK_HARDWARE: Set to 'true' for mock mode
        AUDIO_PROFILE: Force a specific profile by name/slug
    """
    mock_mode = os.getenv("MOCK_HARDWARE", "false").lower() == "true"
    force_profile = os.getenv("AUDIO_PROFILE")

    profiles = load_profiles()

    if not profiles:
        logger.critical("No profiles loaded!")
        return None, None

    return find_matching_profile(profiles, force_mock=mock_mode, force_profile=force_profile)
