from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, Text

from app.database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(256), nullable=False)
    price = Column(Integer, nullable=False)
    area_sqft = Column(Float, nullable=True)
    bedrooms = Column(Integer, nullable=True)
    floor = Column(String(64), nullable=True)
    estate_name = Column(String(128), nullable=True)
    address = Column(String(256), nullable=True)
    district = Column(String(64), default="屯門")
    source = Column(String(64), nullable=False)
    source_url = Column(String(512), nullable=False, unique=True)
    image_url = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    is_transaction = Column(Boolean, default=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "price": self.price,
            "area_sqft": self.area_sqft,
            "bedrooms": self.bedrooms,
            "floor": self.floor,
            "estate_name": self.estate_name,
            "address": self.address,
            "district": self.district,
            "source": self.source,
            "source_url": self.source_url,
            "image_url": self.image_url,
            "description": self.description,
            "is_transaction": self.is_transaction,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
        }


class ScrapeSession(Base):
    __tablename__ = "scrape_sessions"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="running")
    total_found = Column(Integer, default=0)
    total_new = Column(Integer, default=0)
    errors = Column(Text, nullable=True)
    scraper_results = Column(Text, nullable=True)
