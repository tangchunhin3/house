from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PropertyResponse(BaseModel):
    id: int
    title: str
    price: int
    area_sqft: Optional[float] = None
    bedrooms: Optional[int] = None
    floor: Optional[str] = None
    estate_name: Optional[str] = None
    address: Optional[str] = None
    district: str
    source: str
    source_url: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    is_transaction: bool = False
    scraped_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PropertyListResponse(BaseModel):
    items: list[PropertyResponse]
    total: int
    page: int
    page_size: int


class ScrapeTriggerResponse(BaseModel):
    session_id: int
    status: str
    message: str


class ScrapeSessionResponse(BaseModel):
    id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    total_found: int
    total_new: int
    errors: Optional[str] = None


class SourcesResponse(BaseModel):
    sources: list[dict]


class StatsResponse(BaseModel):
    total_properties: int
    min_price: int
    max_price: int
    avg_price: float
    by_source: dict
