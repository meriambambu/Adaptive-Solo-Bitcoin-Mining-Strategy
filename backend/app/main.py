import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.braiins.client import BraiinsClient
from app.config import get_settings
from app.db.database import get_db, init_db
from app.dependencies import set_client
from app.strategy.adaptive import run_strategy_cycle

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── WebSocket connection manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info("WS client connected (%d total)", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.remove(ws)
        logger.info("WS client disconnected (%d total)", len(self._connections))

    async def broadcast(self, payload: Any) -> None:
        if not self._connections:
            return
        message = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)


manager = ConnectionManager()

# ── Scheduler + strategy job ──────────────────────────────────────────────────

scheduler = AsyncIOScheduler()
_braiins_client: BraiinsClient | None = None


async def _strategy_job() -> None:
    cfg = get_settings()
    db_gen = get_db()
    db = next(db_gen)
    try:
        result = await run_strategy_cycle(_braiins_client, db)  # type: ignore[arg-type]
        await manager.broadcast({"type": "strategy_update", "data": result})
    except Exception as exc:
        logger.error("Scheduler strategy error: %s", exc)
    finally:
        try:
            db_gen.close()
        except StopIteration:
            pass


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _braiins_client
    cfg = get_settings()
    logger.info("Starting Adaptive Bitcoin Mining Bot | settings: %s", cfg.safe_dict())

    init_db()

    _braiins_client = BraiinsClient()
    set_client(_braiins_client)

    scheduler.add_job(
        _strategy_job,
        trigger="interval",
        seconds=cfg.poll_interval,
        id="adaptive_strategy",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Strategy scheduler started — interval: %ds", cfg.poll_interval)

    yield

    scheduler.shutdown(wait=False)
    await _braiins_client.aclose()
    logger.info("Shutdown complete")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Adaptive Bitcoin Mining API",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

cfg = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[cfg.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

from app.api import market, orders, settings, strategy  # noqa: E402

app.include_router(orders.router)
app.include_router(market.router)
app.include_router(settings.router)
app.include_router(strategy.router)


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "strategy_enabled": get_settings().strategy_enabled}
