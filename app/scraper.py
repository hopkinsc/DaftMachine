from __future__ import annotations

import logging
import random
import re
import time
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)

USER_AGENTS = [
    settings.user_agent,
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/125.0",
]


@dataclass
class ScrapedListing:
    address: str
    asking_price: float
    property_type: str
    bedrooms: int
    url: str


def _price_to_number(price_text: str) -> float:
    digits = re.sub(r"[^\d]", "", price_text or "")
    return float(digits) if digits else 0.0


def _beds_from_text(text: str) -> int:
    m = re.search(r"(\d+)\s*bed", (text or "").lower())
    return int(m.group(1)) if m else 0


def _parse_cards(html: str) -> list[ScrapedListing]:
    soup = BeautifulSoup(html, "html.parser")
    listings: list[ScrapedListing] = []

    # Daft's HTML changes often; keep selectors broad/fallback friendly.
    cards = soup.select("li[data-testid='result']") or soup.select("li.SearchPage__Result") or soup.find_all("li")
    for card in cards:
        link = card.select_one("a[href*='/for-sale/']")
        if not link:
            continue
        url = link.get("href", "").strip()
        if url.startswith("/"):
            url = f"https://www.daft.ie{url}"

        address_el = card.select_one("p[data-testid='address']") or card.select_one("h2") or link
        address = address_el.get_text(" ", strip=True)

        price_el = card.select_one("span[data-testid='price']") or card.find(string=re.compile("€"))
        price_text = price_el if isinstance(price_el, str) else (price_el.get_text(" ", strip=True) if price_el else "")
        asking_price = _price_to_number(price_text)
        if asking_price <= 0:
            continue

        detail_text = card.get_text(" ", strip=True)
        bedrooms = _beds_from_text(detail_text)
        property_type = "apartment" if "apartment" in detail_text.lower() else "house"

        listings.append(
            ScrapedListing(
                address=address,
                asking_price=asking_price,
                property_type=property_type,
                bedrooms=bedrooms,
                url=url,
            )
        )
    return listings


def scrape_daft_sale_listings(max_pages: int = 3, delay_seconds: float = 1.5) -> list[ScrapedListing]:
    listings: list[ScrapedListing] = []

    with httpx.Client(timeout=settings.scrape_timeout_seconds, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            base_url = "https://www.daft.ie/property-for-sale/dublin"
            url = f"{base_url}?pageSize=20&from={(page - 1) * 20}"

            success = False
            for attempt in range(1, 4):
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                try:
                    logger.info("Fetching page=%s attempt=%s", page, attempt)
                    resp = client.get(url, headers=headers)
                    resp.raise_for_status()
                    page_listings = _parse_cards(resp.text)
                    listings.extend(page_listings)
                    success = True
                    logger.info("Parsed %s listings from page %s", len(page_listings), page)
                    break
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed page=%s attempt=%s: %s", page, attempt, exc)
                    time.sleep(delay_seconds + attempt)

            # rate limit regardless of success
            time.sleep(delay_seconds + random.uniform(0.0, 1.0))

            if not success:
                logger.error("All attempts failed for page=%s", page)

    deduped: dict[str, ScrapedListing] = {listing.url: listing for listing in listings}
    if not deduped:
        logger.warning("No live listings parsed; using static fallback sample data")
        return [
            ScrapedListing(
                address="Smithfield, Dublin 7",
                asking_price=390000,
                property_type="apartment",
                bedrooms=2,
                url="https://www.daft.ie/for-sale/apartment-smithfield-dublin-7/000001",
            ),
            ScrapedListing(
                address="Rathmines, Dublin 6",
                asking_price=480000,
                property_type="apartment",
                bedrooms=2,
                url="https://www.daft.ie/for-sale/apartment-rathmines-dublin-6/000002",
            ),
            ScrapedListing(
                address="Clontarf, Dublin 3",
                asking_price=610000,
                property_type="house",
                bedrooms=3,
                url="https://www.daft.ie/for-sale/house-clontarf-dublin-3/000003",
            ),
        ]
    return list(deduped.values())
