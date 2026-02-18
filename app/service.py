from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.config import settings
from app.db import Listing, ScrapeRun, get_session
from app.estimator import estimate_rent
from app.scraper import scrape_daft_sale_listings

logger = logging.getLogger(__name__)


@dataclass
class ScrapeSummary:
    status: str
    listings_seen: int
    listings_upserted: int
    note: str


def _calculate_gross_yield(asking_price: float, monthly_rent: float) -> float:
    if asking_price <= 0:
        return 0.0
    return (monthly_rent * 12 / asking_price) * 100


def run_scrape_job() -> ScrapeSummary:
    start = datetime.now(UTC)
    status = "ok"
    note = ""
    seen = 0
    upserted = 0

    try:
        scraped = scrape_daft_sale_listings(max_pages=3)
        seen = len(scraped)

        with get_session() as session:
            for row in scraped:
                rent = estimate_rent(row.address, row.bedrooms)
                gross_yield = _calculate_gross_yield(row.asking_price, rent.monthly_rent)
                flagged = int(
                    gross_yield >= settings.yield_threshold
                    and row.asking_price < settings.max_price
                    and row.bedrooms >= settings.min_bedrooms
                )

                existing = session.scalar(select(Listing).where(Listing.source_url == row.url))
                if existing:
                    existing.address = row.address
                    existing.asking_price = row.asking_price
                    existing.property_type = row.property_type
                    existing.bedrooms = row.bedrooms
                    existing.estimated_monthly_rent = rent.monthly_rent
                    existing.rent_method = rent.method
                    existing.gross_yield = gross_yield
                    existing.flagged = flagged
                    existing.scraped_at = datetime.now(UTC)
                else:
                    session.add(
                        Listing(
                            source_url=row.url,
                            address=row.address,
                            asking_price=row.asking_price,
                            property_type=row.property_type,
                            bedrooms=row.bedrooms,
                            estimated_monthly_rent=rent.monthly_rent,
                            rent_method=rent.method,
                            gross_yield=gross_yield,
                            flagged=flagged,
                            scraped_at=datetime.now(UTC),
                        )
                    )
                upserted += 1
            session.commit()

            if seen == 0:
                status = "degraded"
                note = "scraper returned no listings"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scrape job failed")
        status = "degraded"
        note = str(exc)

    with get_session() as session:
        session.add(
            ScrapeRun(
                started_at=start,
                completed_at=datetime.now(UTC),
                status=status,
                listings_seen=seen,
                listings_upserted=upserted,
                note=note,
            )
        )
        session.commit()

    return ScrapeSummary(status=status, listings_seen=seen, listings_upserted=upserted, note=note)


def health_payload() -> dict:
    with get_session() as session:
        latest_run = session.scalar(select(ScrapeRun).order_by(ScrapeRun.completed_at.desc()))
        listing_count = session.scalar(select(func.count(Listing.id))) or 0

    if latest_run:
        delta = datetime.now(UTC) - latest_run.completed_at
        minutes = int(delta.total_seconds() // 60)
        status = "ok" if latest_run.status == "ok" else "degraded"
    else:
        minutes = -1
        status = "degraded"

    return {
        "status": status,
        "last_scrape_minutes_ago": minutes,
        "listings_count": int(listing_count),
    }


def metrics_payload() -> dict:
    with get_session() as session:
        total = session.scalar(select(func.count(Listing.id))) or 0
        avg_yield = session.scalar(select(func.avg(Listing.gross_yield))) or 0.0
        max_yield = session.scalar(select(func.max(Listing.gross_yield))) or 0.0

    return {
        "count_scanned": int(total),
        "average_yield": round(float(avg_yield), 2),
        "highest_yield": round(float(max_yield), 2),
    }


def opportunities_payload() -> list[dict]:
    with get_session() as session:
        rows = session.scalars(
            select(Listing).where(Listing.flagged == 1).order_by(Listing.gross_yield.desc())
        ).all()

    return [
        {
            "address": row.address,
            "asking_price": row.asking_price,
            "bedrooms": row.bedrooms,
            "property_type": row.property_type,
            "estimated_monthly_rent": row.estimated_monthly_rent,
            "gross_yield": round(row.gross_yield, 2),
            "url": row.source_url,
            "rent_method": row.rent_method,
            "scraped_at": row.scraped_at.isoformat(),
        }
        for row in rows
    ]
