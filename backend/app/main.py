import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import properties, scrape
from app.scraper_manager import run_all_scrapers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

scheduler = AsyncIOScheduler()


async def scheduled_scrape():
    logger.info("Starting scheduled daily scrape")
    try:
        result = await run_all_scrapers()
        logger.info(f"Scheduled scrape done: {result}")
    except Exception as e:
        logger.error(f"Scheduled scrape failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized")
    scheduler.add_job(
        scheduled_scrape,
        "interval",
        hours=settings.scrape_interval_hours,
        id="daily_scrape",
        next_run_time=None,
    )
    scheduler.start()
    logger.info(f"Scheduler started (interval={settings.scrape_interval_hours}h)")
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="屯門樓盤 Scraper", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(properties.router)
app.include_router(scrape.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve built frontend (API routes must be defined above this)
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("health"):
        return HTMLResponse(status_code=404)
    index_path = FRONTEND_DIST / "index.html"
    if not index_path.exists():
        return HTMLResponse("Frontend not built", status_code=503)
    return HTMLResponse(index_path.read_text())
