from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):  # type: ignore[misc]
    pass


class SystemService(Base):
    __tablename__ = "system_services"

    service_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    image: Mapped[str] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    category: Mapped[str] = mapped_column(String(20))  # 'core', 'addon', 'recorder'
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class SystemConfig(Base):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    path_high: Mapped[str | None] = mapped_column(String, nullable=True)  # Path to 384kHz file
    path_low: Mapped[str | None] = mapped_column(String, nullable=True)  # Path to 48kHz file
    device_id: Mapped[str] = mapped_column(String, nullable=False)

    # Metadata
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    samplerate_hz: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # State flags
    uploaded: Mapped[bool] = mapped_column(Boolean, default=False)
    analyzed_bird: Mapped[bool] = mapped_column(Boolean, default=False)
    analyzed_bat: Mapped[bool] = mapped_column(Boolean, default=False)
