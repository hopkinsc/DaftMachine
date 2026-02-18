from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Approximate fallback monthly rents by Dublin postcode family.
POSTCODE_RENTS = {
    "Dublin 1": 2200,
    "Dublin 2": 2600,
    "Dublin 3": 2300,
    "Dublin 4": 2800,
    "Dublin 6": 2500,
    "Dublin 7": 2350,
    "Dublin 8": 2300,
    "Dublin 9": 2200,
    "Dublin 12": 2100,
    "Dublin 14": 2450,
    "Dublin 15": 2100,
    "Dublin 18": 2400,
    "Dublin 24": 2050,
}

BEDROOM_HEURISTIC = {
    1: 1800,
    2: 2200,
    3: 2600,
    4: 3200,
}


@dataclass
class RentEstimate:
    monthly_rent: float
    method: str


def estimate_rent(address: str, bedrooms: int) -> RentEstimate:
    """
    RTB integration placeholder with deterministic fallbacks.
    In production, wire RTB API/csv here and return method='rtb'.
    """
    # Fallback 1: postcode lookup from address.
    normalized = address or ""
    for postcode, monthly_rent in POSTCODE_RENTS.items():
        if postcode.lower() in normalized.lower():
            logger.info("Rent estimate using postcode fallback: %s", postcode)
            return RentEstimate(monthly_rent=float(monthly_rent), method="postcode_fallback")

    # Fallback 2: bedroom heuristic.
    monthly = BEDROOM_HEURISTIC.get(max(1, min(4, bedrooms)), 2200)
    logger.info("Rent estimate using bedroom heuristic for %s beds", bedrooms)
    return RentEstimate(monthly_rent=float(monthly), method="bedroom_heuristic")
