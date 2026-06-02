import json
from typing import Optional
from math import sqrt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, cast, Float, nullslast

from app.database import get_db
from app.models import Property, ScrapeSession
from app.schemas import (
    PropertyListResponse,
    PropertyResponse,
    SourcesResponse,
    StatsResponse,
)

router = APIRouter(prefix="/api", tags=["properties"])


@router.get("/properties", response_model=PropertyListResponse)
def list_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    source: Optional[str] = Query(None, description="Filter by source name"),
    min_price: Optional[int] = Query(None, ge=0),
    max_price: Optional[int] = Query(None, ge=0),
    min_bedrooms: Optional[int] = Query(None, ge=0),
    estate_name: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("newest", regex="^(price_asc|price_desc|newest|area_asc|area_desc)$"),
    is_transaction: Optional[bool] = Query(False),
    db: Session = Depends(get_db),
):
    q = db.query(Property)

    if is_transaction:
        q = q.filter(Property.is_transaction.is_(True))
    else:
        q = q.filter(Property.is_transaction.isnot(True))

    if source:
        sources = [s.strip() for s in source.split(",")]
        q = q.filter(Property.source.in_(sources))
    if min_price is not None:
        q = q.filter(Property.price >= min_price)
    if max_price is not None:
        q = q.filter(Property.price <= max_price)
    if min_bedrooms is not None:
        q = q.filter(Property.bedrooms >= min_bedrooms)
    if estate_name:
        q = q.filter(Property.estate_name.ilike(f"%{estate_name}%"))

    if sort_by == "price_asc":
        q = q.order_by(Property.price.asc())
    elif sort_by == "price_desc":
        q = q.order_by(Property.price.desc())
    elif sort_by in ("area_asc", "area_desc"):
        q = q.filter(Property.area_sqft.isnot(None), Property.area_sqft > 0)
        if sort_by == "area_asc":
            q = q.order_by(nullslast(Property.area_sqft.asc()))
        else:
            q = q.order_by(nullslast(Property.area_sqft.desc()))
    else:
        q = q.order_by(desc(Property.scraped_at), desc(Property.id))

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    return PropertyListResponse(
        items=[PropertyResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/transactions", response_model=PropertyListResponse)
def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    source: Optional[str] = Query(None, description="Filter by source name"),
    min_price: Optional[int] = Query(None, ge=0),
    max_price: Optional[int] = Query(None, ge=0),
    min_bedrooms: Optional[int] = Query(None, ge=0),
    estate_name: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("price_desc", regex="^(price_asc|price_desc|newest)$"),
    db: Session = Depends(get_db),
):
    return list_properties(
        page=page, page_size=page_size, source=source,
        min_price=min_price, max_price=max_price,
        min_bedrooms=min_bedrooms, estate_name=estate_name,
        sort_by=sort_by, is_transaction=True, db=db,
    )


@router.get("/properties/{property_id}", response_model=PropertyResponse)
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return PropertyResponse.model_validate(prop)


@router.get("/sources", response_model=SourcesResponse)
def list_sources(db: Session = Depends(get_db)):
    rows = db.query(Property.source, func.count(Property.id)).group_by(Property.source).all()
    return SourcesResponse(sources=[{"name": r[0], "count": r[1]} for r in rows])


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Property.id)).scalar() or 0
    min_p = db.query(func.min(Property.price)).scalar() or 0
    max_p = db.query(func.max(Property.price)).scalar() or 0
    avg_p = db.query(func.avg(Property.price)).scalar() or 0.0
    by_source = dict(db.query(Property.source, func.count(Property.id)).group_by(Property.source).all())
    return StatsResponse(
        total_properties=total,
        min_price=min_p,
        max_price=max_p,
        avg_price=round(avg_p, 0),
        by_source=by_source,
    )


@router.get("/sessions", response_model=list)
def list_sessions(limit: int = Query(10, le=50), db: Session = Depends(get_db)):
    sessions = db.query(ScrapeSession).order_by(desc(ScrapeSession.id)).limit(limit).all()
    return [
        {
            "id": s.id,
            "started_at": s.started_at.isoformat(),
            "finished_at": s.finished_at.isoformat() if s.finished_at else None,
            "status": s.status,
            "total_found": s.total_found,
            "total_new": s.total_new,
            "errors": s.errors,
            "scraper_results": json.loads(s.scraper_results) if s.scraper_results else {},
        }
        for s in sessions
    ]


@router.get("/sessions/current")
def get_current_session(db: Session = Depends(get_db)):
    s = db.query(ScrapeSession).order_by(desc(ScrapeSession.id)).first()
    if not s:
        return None
    return {
        "id": s.id,
        "started_at": s.started_at.isoformat(),
        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
        "status": s.status,
        "total_found": s.total_found,
        "total_new": s.total_new,
        "errors": s.errors,
        "scraper_results": json.loads(s.scraper_results) if s.scraper_results else {},
    }


@router.get("/estates")
def list_estates(search: str = Query("", max_length=100), db: Session = Depends(get_db)):
    q = db.query(Property.estate_name, func.count(Property.id).label("cnt"))
    if search:
        q = q.filter(Property.estate_name.ilike(f"%{search}%"))
    q = q.filter(Property.estate_name.isnot(None))
    q = q.group_by(Property.estate_name).order_by(func.count(Property.id).desc()).limit(50)
    return [{"name": r[0], "count": r[1]} for r in q.all()]


@router.get("/estates/{name}/analysis")
def get_estate_analysis(name: str, db: Session = Depends(get_db)):
    props = db.query(Property).filter(
        Property.estate_name.ilike(f"%{name}%"),
        Property.area_sqft.isnot(None),
        Property.area_sqft > 0,
        Property.price > 0,
    ).all()

    if not props:
        raise HTTPException(status_code=404, detail=f"No data for estate: {name}")

    prices = [p.price for p in props]
    sqft_prices = [p.price / p.area_sqft for p in props]
    n = len(sqft_prices)
    avg_sqft_price = sum(sqft_prices) / n
    std_sqft_price = sqrt(sum((x - avg_sqft_price) ** 2 for x in sqft_prices) / n) if n > 1 else 0

    return {
        "estate_name": name,
        "total_listings": n,
        "avg_price": round(sum(prices) / n) if n else 0,
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
        "avg_呎價": round(avg_sqft_price),
        "min_呎價": round(min(sqft_prices)) if sqft_prices else 0,
        "max_呎價": round(max(sqft_prices)) if sqft_prices else 0,
        "std_呎價": round(std_sqft_price),
        "expected_呎價_range": {
            "low": round(avg_sqft_price - std_sqft_price),
            "high": round(avg_sqft_price + std_sqft_price),
        },
        "sources": dict(db.query(Property.source, func.count(Property.id)).filter(
            Property.estate_name.ilike(f"%{name}%")
        ).group_by(Property.source).all()),
        "listings": [{
            "id": p.id,
            "price": p.price,
            "area_sqft": p.area_sqft,
            "呎價": round(p.price / p.area_sqft) if p.area_sqft else 0,
            "bedrooms": p.bedrooms,
            "floor": p.floor,
            "source": p.source,
            "source_url": p.source_url,
        } for p in sorted(props, key=lambda x: x.price / x.area_sqft)],
    }
