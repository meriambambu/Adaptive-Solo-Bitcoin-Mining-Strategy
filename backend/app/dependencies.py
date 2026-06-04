"""Shared FastAPI dependencies."""

from app.braiins.client import BraiinsClient

_client: BraiinsClient | None = None


def set_client(client: BraiinsClient) -> None:
    global _client
    _client = client


def get_client() -> BraiinsClient:
    if _client is None:
        raise RuntimeError("BraiinsClient not initialized")
    return _client
