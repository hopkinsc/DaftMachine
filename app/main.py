from __future__ import annotations

import logging
from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.config import settings
from app.db import Listing, get_session, init_db
from app.service import health_payload, metrics_payload, opportunities_payload, run_scrape_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="DaftMachine")
templates = Jinja2Templates(directory="app/templates")
scheduler = BackgroundScheduler(timezone="UTC")


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    summary = run_scrape_job()
    logger.info("Initial scrape run complete: %s", summary)

    scheduler.add_job(run_scrape_job, "interval", hours=settings.scrape_interval_hours, id="scrape_job", replace_existing=True)
    scheduler.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    scheduler.shutdown(wait=False)


@app.get("/health")
def health() -> dict:
    return health_payload()


@app.get("/opportunities")
def opportunities() -> list[dict]:
    return opportunities_payload()


@app.get("/metrics")
def metrics() -> dict:
    return metrics_payload()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    health = health_payload()
    metrics = metrics_payload()
    opportunities = opportunities_payload()

    with get_session() as session:
        total = session.query(Listing).count()
        latest = session.scalar(select(Listing.scraped_at).order_by(Listing.scraped_at.desc()))

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "health": health,
            "metrics": metrics,
            "opportunities": opportunities,
            "total": total,
            "updated_at": latest.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC") if isinstance(latest, datetime) else "n/a",
        },
    )
