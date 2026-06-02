# AGENTS.md

## Project

屯門樓盤搜尋 — scrapes property listings (買樓) across 6 HK agencies for Tuen Mun district. Python FastAPI backend + React frontend.

## URLs

| URL | Type | Data |
|-----|------|------|
| https://associates-ccd-watts-injuries.trycloudflare.com | Local (cloudflared) | **All 5 agencies** (full scrape) |
| https://house-production-2eb1.up.railway.app | Railway (production) | 28Hse only (Playwright blocked on cloud IPs) |

Use the **local tunnel URL** for full data. Railway serves as always-on public API with 28Hse data.

## Quick start

```bash
# Backend (serves both API and built frontend)
cd backend && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# → http://localhost:8000

# Expose to internet
cloudflared tunnel --url http://localhost:8000
# → https://*.trycloudflare.com

# Rebuild frontend after changes:
cd frontend && npm run build
```

## Backend structure

| Path | Purpose |
|------|---------|
| `app/scrapers/*.py` | One scraper class per agency (Playwright or requests) |
| `app/scraper_manager.py` | Runs all scrapers, dedupes by `source_url`, writes DB |
| `app/routers/properties.py` | `GET /api/properties` with pagination & filters |
| `app/routers/scrape.py` | `POST /api/scrape` + `POST /api/search?q=keyword` |
| `app/main.py` | FastAPI entrypoint, APScheduler daily scrape on startup |

## Scraping

- **Order:** Request-based (28Hse) → Playwright (Centaline → Ricacorp → Midland → House730)
- **Deduplication:** by `source_url` — deletes all existing records for that source before inserting
- **28Hse** uses `requests` + `BeautifulSoup` (fast). All others use Playwright headless Chromium.
- A daily scrape runs automatically at server start (interval: `24h`, configurable in `.env`)
- Manual trigger: `POST /api/scrape` or click "重新爬取" in UI
- **Keyword search:** `POST /api/search?q=柏瓏` — scrapes each agency's search results for that keyword

## API

| Endpoint | Notes |
|----------|-------|
| `GET /api/properties` | Filters: `source`, `min_price`, `max_price`, `min_bedrooms`, `estate_name`, `sort_by`, `page`, `page_size` |
| `GET /api/sources` | Returns `[{name, count}]` per agency |
| `GET /api/stats` | Total, price range, avg, breakdown by source |
| `POST /api/scrape` | Async — returns `{session_id, status}` immediately |
| `POST /api/search?q=` | Keyword-targeted scrape (async) |
| `GET /api/sessions` | Last 10 scrape runs with counts |
| `GET /api/sessions/current` | Most recent scrape session with per-scraper results |

## Available scrapers

| Agency | File | Type |
|--------|------|------|
| 中原 Centaline | `scrapers/centaline.py` | Playwright |
| 利嘉閣 Ricacorp | `scrapers/ricacorp.py` | Playwright |
| 美聯 Midland | `scrapers/midland.py` | Playwright |
| 28Hse | `scrapers/house_28se.py` | Requests (fast) |
| House730 | `scrapers/house730.py` | Playwright |

## Frontend

- React 18 + Vite + Tailwind + TanStack Query
- Search bar at top — type estate name → triggers `POST /api/search?q=XXX` + auto-sets filter
- Filter bar: estate name, source, price range, bedrooms, sort
- Tabs: 放盤 + 成交紀錄
- Scrape progress panel (shown during active scrape)

## Known quirks

- Scrapers rely on CSS selectors and text patterns (價格 in 萬, 房/呎) — site layout changes may break them
- The first scheduled scrape after startup logs a "missed run time" warning; it still fires on the next interval
- Playwright runs Chromium headless; set `PLAYWRIGHT_HEADLESS=false` in `.env` for debugging
- PostgreSQL database — connection string in `.env`
- 28Hse scraper fetches ~1300+ listings from 2 Tuen Mun area URLs; other scrapers fetch less

## Resume next time

```bash
# Start backend
cd backend && source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
curl http://localhost:8000/health

# Expose to internet
cloudflared tunnel --url http://localhost:8000
# → https://*.trycloudflare.com | grep URL from /tmp/cloudflared.log

# Or rebuild frontend after changes:
cd frontend && npm run build
```

## Production build

- Built frontend at `frontend/dist/` served by FastAPI on same port
- No Vite dev server needed
- CORS allows `*` (same-origin in production)
- Static assets mounted at `/assets`, all other non-API routes serve `index.html` (SPA catch-all)
