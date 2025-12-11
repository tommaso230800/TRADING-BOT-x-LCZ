from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import time

from shared.config import HYPERLIQUID_TESTNET
from shared.hyperliquid_trader import HyperliquidTrader
from shared.models import ServiceStatus
from shared.logging_config import setup_logger

logger = setup_logger("position_manager")

app = FastAPI(title="Position Manager – Hyperliquid")

# Trader Hyperliquid (usa testnet/mainnet da env)
trader = HyperliquidTrader(testnet=HYPERLIQUID_TESTNET)


class OpenPositionRequest(BaseModel):
    symbol: str
    side: str          # "long" / "short"
    size_usd: float
    max_risk_pct: float = 2.0   # per ora solo informativo


class ClosePositionRequest(BaseModel):
    symbol: str


class PositionOut(BaseModel):
    symbol: str
    side: str
    size_usd: float
    entry_price: float
    pnl: float
    leverage: float
    ts_open: int


class PositionsResponse(BaseModel):
    ok: bool
    positions: List[PositionOut]


class SimpleResponse(BaseModel):
    ok: bool
    detail: str
    extra: Dict[str, Any] = {}


class TrailingResponse(BaseModel):
    ok: bool
    trailing: List[Dict[str, Any]]


@app.get("/health", response_model=ServiceStatus)
def health() -> ServiceStatus:
    return ServiceStatus(ok=True, details={"service": "position_manager"})


@app.get("/positions", response_model=PositionsResponse)
def get_positions() -> PositionsResponse:
    raw_positions = trader.get_open_positions()
    now = int(time.time())

    out: List[PositionOut] = []
    for p in raw_positions:
        symbol = p["symbol"]
        side = p["side"]
        entry = float(p["entry_price"])
        lev = float(p["leverage"])
        unrealized = float(p["unrealizedPnl"])

        size_usd = float(p["size"]) * entry if entry > 0 else 0.0

        out.append(
            PositionOut(
                symbol=symbol,
                side=side,
                size_usd=size_usd,
                entry_price=entry,
                pnl=unrealized,
                leverage=lev,
                ts_open=now,  # non abbiamo il ts reale, mettiamo now
            )
        )

    return PositionsResponse(ok=True, positions=out)


@app.post("/open_position", response_model=SimpleResponse)
def open_position(req: OpenPositionRequest) -> SimpleResponse:
    symbol = req.symbol.upper()
    side = req.side.lower().strip()

    if side not in {"long", "short"}:
        raise HTTPException(status_code=400, detail="side deve essere 'long' o 'short'.")

    if req.size_usd <= 0:
        raise HTTPException(status_code=400, detail="size_usd deve essere > 0.")

    logger.info(
        f"▶️ Richiesta OPEN {symbol} {side} size={req.size_usd:.2f} USD (max_risk={req.max_risk_pct}%)"
    )

    sl_pct = float(req.max_risk_pct) / 100.0

    res = trader.open_position(symbol=symbol, side=side, usd_amount=req.size_usd, sl_pct=sl_pct)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=f"Errore apertura posizione: {res.get('error')}")

    return SimpleResponse(ok=True, detail="Position opened", extra={"response": res.get("response")})


@app.post("/close_position", response_model=SimpleResponse)
def close_position(req: ClosePositionRequest) -> SimpleResponse:
    symbol = req.symbol.upper()
    logger.info(f"▶️ Richiesta CLOSE {symbol}")

    res = trader.close_position(symbol)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=f"Errore chiusura posizione: {res.get('error')}")

    return SimpleResponse(ok=True, detail="Position closed", extra={"response": res.get("response")})


@app.post("/tick_trailing", response_model=TrailingResponse)
def tick_trailing() -> TrailingResponse:
    logger.info("🔁 Tick trailing stops (update_trailing_stops)")
    try:
        trailing_info = trader.update_trailing_stops()
    except Exception as e:
        logger.error(f"❌ Errore in update_trailing_stops: {e}")
        raise HTTPException(status_code=500, detail="Errore nel trailing stop")

    return TrailingResponse(ok=True, trailing=trailing_info)
