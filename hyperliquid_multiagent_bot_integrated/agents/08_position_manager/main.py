from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from shared.hyperliquid_trader import HyperliquidTrader
from shared.config import HYPERLIQUID_TESTNET
from shared.models import Position, ServiceStatus
from shared.logging_config import setup_logger

app = FastAPI(title="Position Manager - Hyperliquid")
logger = setup_logger("position_manager")

trader = HyperliquidTrader(testnet=HYPERLIQUID_TESTNET)


class OpenRequest(BaseModel):
    symbol: str
    side: str                   # "long" | "short"
    size_usd: float
    max_risk_pct: float = 2.0
    note: Optional[str] = None


class CloseRequest(BaseModel):
    symbol: str


class PositionsResponse(BaseModel):
    ok: bool
    positions: List[Position]


@app.get("/health", response_model=ServiceStatus)
def health() -> ServiceStatus:
    return ServiceStatus(ok=True, details={"service": "position_manager"})


@app.post("/open_position")
def open_position(req: OpenRequest) -> Dict[str, Any]:
    if req.size_usd <= 0:
        raise HTTPException(status_code=400, detail="Invalid size_usd")

    side = req.side.lower()
    if side not in {"long", "short"}:
        raise HTTPException(status_code=400, detail="Invalid side")

    logger.info(f"Opening {side} {req.symbol} size=${req.size_usd:.2f} risk={req.max_risk_pct}%")
    resp = trader.open_position(
        symbol=req.symbol,
        side=side,
        usd_amount=req.size_usd,
        sl_pct=req.max_risk_pct / 100.0,
    )
    return {"ok": True, "result": resp}


@app.post("/close_position")
def close_position(req: CloseRequest) -> Dict[str, Any]:
    logger.info(f"Closing position on {req.symbol}")
    resp = trader.close_position(req.symbol)
    return {"ok": True, "result": resp}


@app.get("/positions", response_model=PositionsResponse)
def get_positions():
    raw_positions = trader.get_open_positions()
    positions = [Position(**p) for p in raw_positions]
    return PositionsResponse(ok=True, positions=positions)


@app.post("/tick_trailing")
def tick_trailing() -> Dict[str, Any]:
    updated = trader.update_trailing_stops()
    logger.info(f"Trailing updated for {len(updated)} positions")
    return {"ok": True, "updated": updated}
