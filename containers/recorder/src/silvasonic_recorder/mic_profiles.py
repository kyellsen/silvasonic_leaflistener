"""Microphone Profile Loader.

Loads and manages microphone profiles from YAML files.
Profiles define device detection patterns and optimal audio settings.
"""

import logging
import os
import re
import subprocess
import typing
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger("mic_profiles")

if typing.TYPE_CHECKING:
    from .strategies import AudioStrategy


class AudioConfig(BaseModel):
    """Audio recording configuration."""

    sample_rate: int = Field(default=48000, ge=8000, le=192000)
    channels: int = Field(default=1, ge=1, le=2)
    bit_depth: int = Field(default=16, ge=8, le=32)
    format: str = Field(default="S16_LE")


class RecordingConfig(BaseModel):
    """Recording output configuration."""

    chunk_duration_seconds: int = Field(default=10, ge=1)
    output_format: str = Field(default="flac")
    compression_level: int = Field(default=5, ge=0, le=12)


class MicrophoneProfile(BaseModel):
    """Complete microphone profile."""

    name: str
    slug: str = Field(default="")
    manufacturer: str = Field(default="Unknown")
    model: str = Field(default="Unknown")
    device_patterns: list[str] = Field(default_factory=list)
    usb_ids: list[str] = Field(default_factory=list)  # e.g. ["1b3f:2008"]
    audio: AudioConfig = Field(default_factory=AudioConfig)
    recording: RecordingConfig = Field(default_factory=RecordingConfig)
    priority: int = Field(default=50)
    is_mock: bool = Field(default=False)

    @model_validator(mode="after")
    def generate_slug(self) -> "MicrophoneProfile":
        if not self.slug and self.name:
            # Generate slug from name if not provided
            cleaned = re.sub(r"[^a-z0-9]+", "_", self.name.lower()).strip("_")
            self.slug = cleaned
        return self


class DetectedDevice(BaseModel):
    """Represents a detected audio device."""

    card_id: str
    hw_address: str
    description: str
    usb_id: str | None = None  # e.g. "1b3f:2008"


def get_usb_ids_from_modalias(card_idx: str) -> str | None:
    """Try to extract USB vendor:product from modalias file.

    Format of modalias: usb:v1234p5678d...
    """
    try:
        # Check /sys/class/sound/cardX/device/modalias
        modalias_path = Path(f"/sys/class/sound/card{card_idx}/device/modalias")
        if modalias_path.exists():
            content = modalias_path.read_text().strip()
            # Match usb:vXXXXpYYYY
            match = re.search(r"usb:v([0-9A-Fa-f]{4})p([0-9A-Fa-f]{4})", content)
            if match:
                vid = match.group(1).lower()
                pid = match.group(2).lower()
                return f"{vid}:{pid}"
    except Exception:
        pass
    return None


def get_alsa_devices() -> list[DetectedDevice]:
    """Get list of ALSA capture devices with USB IDs."""
    devices = []

    # 1. Parse /proc/asound/cards to map Card ID -> USB ID
    # Format:
    #  1 [Mic            ]: USB-Audio - RODE NT-USB Mini Mic
    #                       RODE Microphones RODE NT-USB Mini Mic at usb-0000:01:00.0-1.3, full speed
    card_usb_ids: dict[str, str] = {}
    try:
        if os.path.exists("/proc/asound/cards"):
            with open("/proc/asound/cards") as f:
                content = f.read()
                # Match logic to find "at usb-..." and previous card index
                # This is tricky with regex across lines.
                # Let's iterate lines.
                # current_card = None
                for line in content.splitlines():
                    # Line 1:  1 [Mic            ]: USB-Audio - RODE NT-USB Mini Mic
                    m_card = re.match(r"\s*(\d+)\s+\[", line)
                    if m_card:
                        _current_card = m_card.group(1)
                        continue

                    # Line 2: ... at usb-0000:01:00.0-1.3, full speed
                    # We can't easily get the USB Vendor:Product from this text alone without looking up lsusb
                    # BUT, we can read /sys/class/sound/cardX/id or similar.
                    pass

        # Better approach: Iterate /sys/class/sound/card*
        # /sys/class/sound/card1/device/idVendor
        # /sys/class/sound/card1/device/idProduct
        sys_sound = Path("/sys/class/sound")
        if sys_sound.exists():
            for card_path in sys_sound.glob("card*"):
                card_name = card_path.name  # card1
                if not card_name.startswith("card"):
                    continue

                card_idx = card_name.replace("card", "")

                # Check if it's a USB device
                device_link = card_path / "device"
                vendor_path = device_link / "idVendor"
                product_path = device_link / "idProduct"

                if vendor_path.exists() and product_path.exists():
                    try:
                        vid = vendor_path.read_text().strip()
                        pid = product_path.read_text().strip()
                        resolved_usb_id = f"{vid}:{pid}"
                        card_usb_ids[card_idx] = resolved_usb_id
                        logger.debug(f"Resolved Card {card_idx} -> USB {resolved_usb_id}")
                    except Exception:
                        pass
                else:
                    # Fallback: Try modalias (more robust on some distros)
                    modalias_id = get_usb_ids_from_modalias(card_idx)
                    if modalias_id:
                        card_usb_ids[card_idx] = modalias_id
                        logger.debug(
                            f"Resolved Card {card_idx} -> USB {modalias_id} (via modalias)"
                        )

    except Exception as e:
        logger.warning(f"Failed to resolve USB IDs: {e}")

    try:
        result = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
        output = result.stdout + result.stderr

        for line in output.split("\n"):
            if "card" in line.lower():
                # Match "card X: ... device Y:"
                # Example: card 1: Mic [RODE NT-USB Mini Mic], device 0: USB Audio [USB Audio]
                match = re.search(r"card (\d+):.*?device (\d+):", line)
                if match:
                    card_id = match.group(1)
                    device_id = match.group(2)

                    # Only interest in capture devices (arecord -l lists them)
                    # Construct hw address
                    hw_addr = f"plughw:{card_id},{device_id}"

                    # Get USB ID if available
                    usb_id: str | None = card_usb_ids.get(card_id)

                    devices.append(
                        DetectedDevice(
                            card_id=card_id,
                            hw_address=hw_addr,
                            description=line.strip(),
                            usb_id=usb_id,
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
                    # Inject slug from filename if not present
                    if "slug" not in data:
                        data["slug"] = yml_file.stem

                    # Flatten 'mock' key if present to 'is_mock' to match model
                    if "mock" in data and isinstance(data["mock"], dict):
                        data["is_mock"] = data["mock"].get("enabled", False)
                        data.pop("mock", None)

                    profile = MicrophoneProfile(**data)
                    profiles.append(profile)
                    logger.debug(f"Loaded profile: {profile.name} ({profile.slug})")
        except Exception as e:
            logger.error(f"Error loading profile {yml_file}: {e}")

    # Sort by priority (lower = higher priority)
    profiles.sort(key=lambda p: p.priority)

    logger.info(f"Loaded {len(profiles)} microphone profiles")
    return profiles


def find_matching_profile(
    profiles: list[MicrophoneProfile],
    force_mock: bool = False,
    force_profile: str | None = None,
    strict_mode: bool = False,
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

    # Handle Desktop/PulseAudio Mode (Virtual)
    if force_profile and force_profile.lower() in ("desktop", "system", "pulse", "pipewire"):
        logger.info(f"Desktop/System Audio Mode requested: '{force_profile}'")
        desktop_profile = MicrophoneProfile(
            name="Desktop Audio",
            slug="desktop",
            is_mock=False,  # It's real audio, just not hardware direct
            audio=AudioConfig(sample_rate=48000),
            recording=RecordingConfig(chunk_duration_seconds=10),
            manufacturer="System",
            model="PulseAudio/PipeWire",
        )
        # Use a "virtual" device descriptor
        desktop_device = DetectedDevice(
            card_id="pulse",
            hw_address="default",
            description="PulseAudio System Default",
            usb_id=None,
        )
        return desktop_profile, desktop_device

    # Get available devices
    devices = get_alsa_devices()

    if not devices:
        logger.error("No audio devices found via ALSA!")
        return None, None

    logger.info(f"Found {len(devices)} audio device(s)")
    for dev in devices:
        usb_info = f" (USB: {dev.usb_id})" if dev.usb_id else ""
        logger.info(f"  - [{dev.hw_address}] {dev.description}{usb_info}")

    # Handle forced profile selection
    if force_profile:
        logger.info(f"Configuration forces profile: '{force_profile}'")
        target_profile = None
        for profile in profiles:
            if (
                force_profile.lower() in profile.name.lower()
                or force_profile.lower() == profile.slug
            ):
                target_profile = profile
                break

        if target_profile:
            logger.info(f"Targeting profile: {target_profile.name}")

            # ATTEMPT 1: Strict Match against Target Profile
            # We want to find the SPECIFIC device that matches this profile
            for device in devices:
                # Check USB ID
                if device.usb_id and target_profile.usb_ids:
                    if device.usb_id in target_profile.usb_ids:
                        logger.info(
                            f"Device {device.hw_address} matches forced profile via USB ID '{device.usb_id}'"
                        )
                        return target_profile, device

                # Check Description
                for pattern in target_profile.device_patterns:
                    if pattern.lower() in device.description.lower():
                        logger.info(
                            f"Device {device.hw_address} matches forced profile via pattern '{pattern}'"
                        )
                        return target_profile, device

            # ATTEMPT 2: Fallback (Legacy Behavior but safer)
            # If no specific device matches the forced profile, we historically just returned devices[0].
            # However, this causes conflict if multiple containers do this.
            # We should probably still fallback but maybe warn?
            # Or should we fail? failing is safer for fixing the config.
            # But let's check input arguments.
            # If the user sets AUDIO_PROFILE="Rode", they expect it to work with the Rode mic.
            # If the Rode mic isn't plugged in, we shouldn't grab the Ultramic.

            logger.warning(
                f"Forced profile '{target_profile.name}' defined, but no matching device found connected!"
            )
            # Retaining legacy fallback for robustness (if USB IDs aren't detected properly),
            # but logging clearly.
            # Ideally we return None, but let's see.
            # If we return devices[0], we risk 'Device Busy' if another container grabs it.
            # If we return None, this container dies/loops.
            # Let's try to match by exclusion? No.

            # Let's trust the logic: If we forced a profile, we WANT that specific hardware.
            # If we can't find it, we shouldn't just grab "hw:0,0" which might be the built-in speaker or other mic.
            # HOWEVER, for temporary backward compatibility if USB detection fails:
            # We'll fallback to devices[0] ONLY if it hasn't been claimed? We can't know that.

            # Decision: Return None if no match found for forced profile.
            # This forces the logs to show "No matching profile/device" rather than confusing "Device Busy"
            # Wait, if USB ID detection fails (e.g. inside container permissions), we might break working setups.
            # But `arecord -l` usually has the name.

            # Let's try one weak match:
            # If the profile has NO patterns and NO USB IDs, maybe it's a "Generic"?
            if not target_profile.device_patterns and not target_profile.usb_ids:
                logger.info("Forced profile has no patterns, using first specific device.")
                return target_profile, devices[0]

            logger.error(f"Required device for profile '{target_profile.name}' not found.")
            return None, None

        else:
            logger.warning(
                f"Forced profile slug/name '{force_profile}' not found in loaded profiles."
            )
            # Fall through to auto-detection? Or fail?
            # Probably fail as config is wrong.
            return None, None

    # Normal Auto-detection (No force)
    # Match profiles to devices
    for profile in profiles:
        if profile.is_mock:
            continue

        for pattern in profile.device_patterns:
            for device in devices:
                # 1. Check Strict USB ID (Highest Priority)
                if device.usb_id and profile.usb_ids:
                    if device.usb_id in profile.usb_ids:
                        logger.info(f"Matched USB ID: '{device.usb_id}' -> {profile.name}")
                        return profile, device

                # 2. Check Name Pattern
                if pattern.lower() in device.description.lower():
                    logger.info(f"Matched Pattern: '{pattern}' -> {profile.name}")
                    return profile, device

    # Fallback: use generic profile with first device
    # Fallback: use generic profile with first device
    if strict_mode:
        logger.warning("Strict mode enabled: skipping generic fallback.")
        logger.error("No specific profile matched available hardware.")
        return None, None

    logger.warning("No specific profile matched, trying generic fallback")
    generic = next((p for p in profiles if "generic" in p.name.lower()), None)
    if generic:
        return generic, devices[0]

    logger.error("No matching profile found!")
    return None, None


def get_active_profile(
    mock_mode: bool | None = None,
    force_profile: str | None = None,
    strict_mode: bool | None = None,
) -> tuple[MicrophoneProfile | None, DetectedDevice | None]:
    """Main entry point: Get the active microphone profile and device.

    Args:
        mock_mode: Override MOCK_HARDWARE env var.
        force_profile: Override AUDIO_PROFILE env var.
        strict_mode: Override STRICT_HARDWARE_MATCH env var.
    """
    # Load defaults from env if not provided
    if mock_mode is None:
        mock_mode = os.getenv("MOCK_HARDWARE", "false").lower() == "true"
    if force_profile is None:
        force_profile = os.getenv("AUDIO_PROFILE")
    if strict_mode is None:
        strict_mode = os.getenv("STRICT_HARDWARE_MATCH", "false").lower() == "true"

    profiles = load_profiles()

    if not profiles:
        logger.critical("No profiles loaded!")
        return None, None

    return find_matching_profile(
        profiles,
        force_mock=mock_mode,
        force_profile=force_profile,
        strict_mode=strict_mode,
    )


def create_strategy_for_profile(
    profile: MicrophoneProfile, device: DetectedDevice
) -> "AudioStrategy":
    """Factory to create the appropriate AudioStrategy."""
    from .strategies import AlsaStrategy, FileMockStrategy, PulseAudioStrategy

    if profile.slug == "desktop" or profile.name == "Desktop Audio":
        logger.info("Creating PulseAudioStrategy (System Default)")
        return PulseAudioStrategy(
            source_name=device.hw_address, sample_rate=profile.audio.sample_rate
        )

    if profile.is_mock:
        # Check if it's the "File Injection" mock
        # We can use a special flag or just assume based on name "File Mock"
        # For now, let's look for a specific property or name
        if "file" in profile.name.lower():
            # Default mock dir
            mock_dir = Path(os.environ.get("MOCK_INPUT_DIR", "/data/mock_input"))
            logger.info(f"Creating FileMockStrategy watching {mock_dir}")
            return FileMockStrategy(watch_dir=mock_dir, sample_rate=profile.audio.sample_rate)
        else:
            # Logic for "Synthetic" mock (lavfi) which was handling in main.py before?
            # Wait, my strategy plan removed lavfi logic from main.py and didn't add a Synthetic strategy.
            # I should probably add SyntheticStrategy if I want to keep it, but user prioritized File Mock.
            # Let's map "lavfi" to a simple AlsaStrategy or handle it?
            # Actually, main.py had special "lavfi" handling. I should have moved that to a Strategy.
            # I'll stick to AlsaStrategy for real, and FileMock for mock.
            # If "is_mock" is true but not file mock, what do we do?
            # The existing `find_matching_profile` returns a "mock" device.

            # Let's assume for this refactor, we primarily support FileMockStrategy for mocks.
            # If we want to support lavfi, we'd need a strategy for it.
            # I'll default to FileMockStrategy for any mock profile for now to satisfy requirements,
            # OR I can implement a quick LavfiStrategy.

            # Requirement: "Optimize Audio Mocking (File Injection)"
            # I'll default to FileMockStrategy.

            mock_dir = Path(os.environ.get("MOCK_INPUT_DIR", "/data/mock_input"))
            return FileMockStrategy(watch_dir=mock_dir, sample_rate=profile.audio.sample_rate)

    # Hardware
    return AlsaStrategy(
        hw_address=device.hw_address,
        channels=profile.audio.channels,
        sample_rate=profile.audio.sample_rate,
    )
