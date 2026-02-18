# DaftMachine

Production-oriented Dublin rental yield scanner.

## Features
- Scrapes Dublin for-sale listings from Daft (pagination + retries + rotating UA).
- Estimates rent via postcode fallback and bedroom heuristic fallback.
- Calculates gross yield and flags opportunities.
- Persists listings and scrape runs in SQLite (swap DB_URL for Postgres in Railway).
- Exposes API endpoints:
  - `GET /health`
  - `GET /opportunities`
  - `GET /metrics`
- Minimal dashboard at `/`.
- Background scheduler runs scrape every 6 hours (configurable).

## Local run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Environment variables
- `DB_URL` (default: `sqlite:///./daftmachine.db`)
- `SCRAPE_INTERVAL_HOURS` (default: `6`)
- `SCRAPE_TIMEOUT_SECONDS` (default: `25`)
- `SCRAPER_USER_AGENT` (default included)
- `YIELD_THRESHOLD` (default: `6.0`)
- `MAX_PRICE` (default: `1200000`)
- `MIN_BEDROOMS` (default: `2`)

## Railway deployment
1. Install Railway CLI and authenticate:
   ```bash
   railway login
   ```
2. Initialize/link project in repo root:
   ```bash
   railway init
   ```
3. Set env vars:
   ```bash
   railway variables set DB_URL='<postgres-url-or-sqlite-path>' YIELD_THRESHOLD=6.0
   ```
4. Deploy:
   ```bash
   railway up
   ```
5. Verify:
   - `/health` returns 200
   - `/metrics` and `/opportunities` return JSON
   - `/` dashboard renders

## Notes
If Daft changes markup or blocks requests, scraper degrades gracefully and falls back to static sample rows so APIs stay alive while logs indicate degraded mode.
