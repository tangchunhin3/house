import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models import Property, ScrapeSession
from app.scrapers.base import PlaywrightSession
from app.scrapers.centaline import CentalineScraper
from app.scrapers.house_28se import House28SeScraper
from app.scrapers.house730 import House730Scraper
from app.scrapers.ricacorp import RicacorpScraper
from app.scrapers.midland import MidlandScraper


logger = logging.getLogger(__name__)

REQUEST_SCRAPERS = [
    House28SeScraper,
]

PLAYWRIGHT_SCRAPERS = [
    CentalineScraper,
    RicacorpScraper,
    MidlandScraper,
    House730Scraper,
]

ALL_SCRAPERS = [(cls, True) for cls in REQUEST_SCRAPERS] + [(cls, False) for cls in PLAYWRIGHT_SCRAPERS]

MIN_PRICE = 500000
MAX_PRICE = 500000000


def get_source_names() -> list[str]:
    return [s.SOURCE_NAME for s in REQUEST_SCRAPERS + PLAYWRIGHT_SCRAPERS]


def _update_session_scrapers(db, session_id: int, name: str, found: int, inserted: int, error: str = "") -> None:
    sess = db.query(ScrapeSession).filter(ScrapeSession.id == session_id).first()
    if not sess:
        return
    results = json.loads(sess.scraper_results) if sess.scraper_results else {}
    results[name] = {"found": found, "inserted": inserted, "error": error, "done": True}
    sess.scraper_results = json.dumps(results)
    db.commit()


def _insert_properties(db, source_name: str, props: list[dict], is_search: bool = False) -> int:
    seen = set()
    unique = []
    for p in props:
        if p["price"] < MIN_PRICE or p["price"] > MAX_PRICE:
            continue
        if not p.get("source_url"):
            continue
        url = p["source_url"]
        if url in seen:
            continue
        seen.add(url)
        unique.append(p)

    if not is_search:
        db.query(Property).filter(Property.source == source_name).delete()

    now = datetime.utcnow()
    inserted = 0
    for p in unique:
        p["scraped_at"] = now
        if is_search:
            existing = db.query(Property).filter(
                Property.source_url == p["source_url"]
            ).first()
            if existing:
                for k, v in p.items():
                    setattr(existing, k, v)
                inserted += 1
                continue
        db.add(Property(**p))
        inserted += 1
    db.commit()
    return inserted


def _run_request_scraper(scraper_cls, session_id: Optional[int] = None, keyword: str = "", is_search: bool = False) -> tuple[str, int, int, str]:
    name = scraper_cls.SOURCE_NAME
    try:
        scraper = scraper_cls(keyword=keyword)
        props = scraper.scrape()
        db = SessionLocal()
        try:
            n = _insert_properties(db, name, props, is_search=is_search)
        finally:
            db.close()
        if session_id:
            db2 = SessionLocal()
            try:
                _update_session_scrapers(db2, session_id, name, len(props), n)
            finally:
                db2.close()
        return name, len(props), n, ""
    except Exception as e:
        err = str(e)
        if session_id:
            db2 = SessionLocal()
            try:
                _update_session_scrapers(db2, session_id, name, 0, 0, err)
            finally:
                db2.close()
        return name, 0, 0, err


async def run_all_scrapers(session_id: Optional[int] = None, keyword: str = "") -> dict:
    db = SessionLocal()
    try:
        is_search = bool(keyword)
        if session_id:
            sess = db.query(ScrapeSession).filter(ScrapeSession.id == session_id).first()
        else:
            sess = ScrapeSession(status="running", scraper_results="{}")
            db.add(sess)
            db.commit()
            db.refresh(sess)
            session_id = sess.id

        errors = []
        total_found = 0

        # Phase 1: request-based scrapers (parallel)
        with ThreadPoolExecutor(max_workers=3) as pool:
            loop = asyncio.get_running_loop()
            tasks = [
                loop.run_in_executor(pool, _run_request_scraper, cls, session_id, keyword, is_search)
                for cls in REQUEST_SCRAPERS
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                    logger.error(f"Request scraper failed: {result}")
                else:
                    source_name, found, inserted, err = result
                    total_found += found
                    if err:
                        errors.append(f"{source_name}: {err}")
                    else:
                        logger.info(f"{source_name}: {found} found, {inserted} inserted")

        # Refresh session to include Phase-1 scraper_results (28Hse) committed by _run_request_scraper.
        # Without this refresh, the identity map returns the stale sess object (scraper_results="{}"),
        # and _update_session_scrapers below would overwrite the Phase-1 results at the final commit.
        db.refresh(sess)

        # Phase 2: Playwright-based scrapers (each in its own browser session)
        for scraper_cls in PLAYWRIGHT_SCRAPERS:
            name = scraper_cls.SOURCE_NAME
            try:
                channel = getattr(scraper_cls, 'PLAYWRIGHT_CHANNEL', None)
                async with PlaywrightSession(channel=channel) as pw:
                    scraper = scraper_cls(pw, keyword=keyword)
                    props = await scraper.scrape()
                    db2 = SessionLocal()
                    try:
                        n = _insert_properties(db2, name, props, is_search=is_search)
                    finally:
                        db2.close()
                total_found += len(props)
                _update_session_scrapers(db, session_id, name, len(props), n)
                logger.info(f"{name}: {len(props)} found, {n} inserted")
            except Exception as e:
                db.rollback()
                err = str(e)
                errors.append(f"{name}: {err}")
                _update_session_scrapers(db, session_id, name, 0, 0, err)
                logger.error(f"{name} failed: {e}")

        total = db.query(Property).count()
        sess.status = "completed"
        sess.finished_at = datetime.utcnow()
        sess.total_found = total
        sess.total_new = total
        if errors:
            sess.errors = "\n".join(str(e) for e in errors)
        db.commit()

        return {"session_id": sess.id, "total": total, "errors": errors}
    finally:
        db.close()
