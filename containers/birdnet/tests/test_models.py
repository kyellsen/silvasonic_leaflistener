from datetime import datetime

import pytest
from pydantic import ValidationError
from silvasonic_birdnet.models import BirdDetection


def test_bird_detection_defaults():
    """Test default values."""
    bd = BirdDetection(
        filename="test.wav", filepath="/tmp/test.wav", start_time=0.0, end_time=5.0, confidence=0.8
    )
    assert bd.timestamp is not None
    assert isinstance(bd.timestamp, datetime)
    assert bd.confidence == 0.8


# @pytest.mark.skip(reason="Pydantic validation not triggering on init for SQLModel currently")
def test_validation():
    """Test validators."""
    # Negative end time
    with pytest.raises(ValidationError):
        BirdDetection(
            filename="test.wav",
            filepath="/tmp/test.wav",
            start_time=0.0,
            end_time=-1.0,  # Invalid
            confidence=0.8,
        )

    # Confidence out of range
    with pytest.raises(ValidationError):
        BirdDetection(
            filename="test.wav",
            filepath="/tmp/test.wav",
            start_time=0.0,
            end_time=1.0,
            confidence=1.5,  # Invalid
        )

    # Test assignment validation (enabled by config now)
    bd = BirdDetection(
        filename="test.wav",
        filepath="/tmp/test.wav",
        start_time=0.0,
        end_time=1.0,
        confidence=0.8,
    )
    with pytest.raises(ValidationError):
        bd.confidence = 1.5


def test_aliases():
    """Test lat/lon aliases."""
    bd = BirdDetection(
        filename="test.wav",
        filepath="/tmp/test.wav",
        start_time=0.0,
        end_time=1.0,
        confidence=0.8,
        lat=52.5,
        lon=13.4,
    )

    # Check alias mapping to DB fields
    assert bd.latitude == 52.5
    assert bd.longitude == 13.4

    # Check property getters
    assert bd.lat == 52.5
    assert bd.lon == 13.4

    # Check property setters
    bd.lat = 50.0
    assert bd.latitude == 50.0

    bd.lon = 10.0
    assert bd.longitude == 10.0
