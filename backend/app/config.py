from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql:///properties"
    scrape_interval_hours: int = 24
    playwright_headless: bool = True
    request_delay_seconds: float = 0.5
    max_pages: int = 50
    playwright_max_pages: int = 15

    class Config:
        env_file = ".env"


settings = Settings()
