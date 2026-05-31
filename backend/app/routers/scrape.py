import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import ScrapeSession
from app.schemas import ScrapeTriggerResponse
from app.scraper_manager import run_all_scrapers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scrape"])


@router.post("/scrape", response_model=ScrapeTriggerResponse)
async def trigger_scrape(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    sess = ScrapeSession(status="running")
    db.add(sess)
    db.commit()
    db.refresh(sess)

    session_id = sess.id

    async def _run():
        try:
            await run_all_scrapers(session_id=session_id)
        except Exception as e:
            logger.error(f"Scrape session {session_id} failed: {e}")
            _db = SessionLocal()
            try:
                s = _db.query(ScrapeSession).filter(ScrapeSession.id == session_id).first()
                if s:
                    s.status = "failed"
                    s.finished_at = datetime.utcnow()
                    s.errors = str(e)
                    _db.commit()
            finally:
                _db.close()

    background_tasks.add_task(_run)

    return ScrapeTriggerResponse(
        session_id=session_id,
        status="running",
        message=f"Scrape session #{session_id} started",
    )


@router.post("/search", response_model=ScrapeTriggerResponse)
async def trigger_search(background_tasks: BackgroundTasks, q: str, db: Session = Depends(get_db)):
    sess = ScrapeSession(status="running")
    db.add(sess)
    db.commit()
    db.refresh(sess)

    session_id = sess.id

    async def _run():
        try:
            await run_all_scrapers(session_id=session_id, keyword=q)
        except Exception as e:
            logger.error(f"Search session {session_id} failed: {e}")
            _db = SessionLocal()
            try:
                s = _db.query(ScrapeSession).filter(ScrapeSession.id == session_id).first()
                if s:
                    s.status = "failed"
                    s.finished_at = datetime.utcnow()
                    s.errors = str(e)
                    _db.commit()
            finally:
                _db.close()

    background_tasks.add_task(_run)

    return ScrapeTriggerResponse(
        session_id=session_id,
        status="running",
        message=f"Search session #{session_id} started",
    )
