from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
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
