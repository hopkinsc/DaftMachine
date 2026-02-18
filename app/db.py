from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_url: Mapped[str] = mapped_column(String(400), unique=True, index=True)
    address: Mapped[str] = mapped_column(String(240))
    property_type: Mapped[str] = mapped_column(String(80), default="unknown")
    bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    asking_price: Mapped[float] = mapped_column(Float)
    estimated_monthly_rent: Mapped[float] = mapped_column(Float)
    rent_method: Mapped[str] = mapped_column(String(80), default="heuristic")
    gross_yield: Mapped[float] = mapped_column(Float)
    flagged: Mapped[int] = mapped_column(Integer, default=0)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    status: Mapped[str] = mapped_column(String(40), default="ok")
    listings_seen: Mapped[int] = mapped_column(Integer, default=0)
    listings_upserted: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(400), default="")


engine = create_engine(settings.db_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
