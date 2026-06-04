from decimal import Decimal
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Braiins API key — never expose this outside the backend
    braiins_api_key: str

    # Strategy parameters (all editable at runtime via /api/settings)
    top_n: int = 5
    max_bid_price: Decimal = Decimal("0.60")
    min_bid_price: Decimal = Decimal("0.10")
    upper_buffer: Decimal = Decimal("0.01")
    lower_margin: Decimal = Decimal("0.005")
    price_step: Decimal = Decimal("0.005")
    poll_interval: int = 60
    strategy_enabled: bool = True

    # App
    port: int = 8000
    frontend_origin: str = "http://localhost:5173"
    database_url: str = "sqlite:///./data/mining.sqlite"
    log_level: str = "INFO"

    @field_validator("poll_interval")
    @classmethod
    def clamp_poll_interval(cls, v: int) -> int:
        return max(30, v)

    @field_validator("braiins_api_key")
    @classmethod
    def must_not_be_placeholder(cls, v: str) -> str:
        if v.startswith("your_"):
            raise ValueError("Replace BRAIINS_API_KEY placeholder in .env before starting")
        return v

    def safe_dict(self) -> dict:
        """Return settings dict with credentials redacted — safe for logging."""
        d = self.model_dump()
        d["braiins_api_key"] = "***"
        return d


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
